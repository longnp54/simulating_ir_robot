import math
from utils.geometry import distance_between_points, check_line_of_sight
import threading

class IRSensor:
    """Lớp cơ sở cho các loại cảm biến IR"""
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        self.robot_id = robot_id    # Chỉ lưu ID robot, không lưu tham chiếu
        self.side = side            # 0: top, 1: right, 2: bottom, 3: left
        self.position_index = position_index
        self.rel_x = rel_x
        self.rel_y = rel_y
    
    def get_position(self, robot_x, robot_y, robot_size, robot_orientation):
        """Tính vị trí cảm biến dựa trên thông tin robot"""
        half_size = robot_size / 2
        
        # Vị trí tương đối dựa trên side và position_index
        if self.side == 0:  # top
            rel_x = self.rel_x * half_size
            rel_y = -half_size
        elif self.side == 1:  # right
            rel_x = half_size
            rel_y = self.rel_y * half_size
        elif self.side == 2:  # bottom
            rel_x = self.rel_x * half_size
            rel_y = half_size
        else:  # left
            rel_x = -half_size
            rel_y = self.rel_y * half_size
        
        # Áp dụng phép quay dựa trên hướng robot
        import math
        angle_rad = math.radians(robot_orientation)
        rotated_x = rel_x * math.cos(angle_rad) - rel_y * math.sin(angle_rad)
        rotated_y = rel_x * math.sin(angle_rad) + rel_y * math.cos(angle_rad)
        
        # Vị trí cuối cùng
        return robot_x + rotated_x, robot_y + rotated_y

class IRTransmitter(IRSensor):
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        super().__init__(robot_id, side, position_index, rel_x, rel_y)
        self.beam_angle = 45
        self.beam_distance = 150  # pixel
        self.real_beam_distance = 0.6  # mét
        self.strength = 100
        self.active = True
        self.beam_direction_offset = 0
    
    def initialize_with_robot_size(self, robot_size):
        """Khởi tạo các thuộc tính liên quan đến kích thước robot"""
        self.base_robot_size = robot_size
        self.beam_to_robot_ratio = self.beam_distance / robot_size
        
    def get_beam_direction(self, robot_orientation):
        """Tính hướng chùm tia dựa trên hướng robot"""
        base_direction = 0
        if self.side == 0:  # top
            base_direction = 270
        elif self.side == 1:  # right
            base_direction = 0
        elif self.side == 2:  # bottom
            base_direction = 90
        else:  # left
            base_direction = 180
            
        return (base_direction + robot_orientation + self.beam_direction_offset) % 360

    def get_beam_cone(self, robot_x, robot_y, robot_size, robot_orientation):
        """
        Tính toán hình nón chùm tia để vẽ trên giao diện
        
        Returns:
            tuple: (start_angle, extent_angle, major_radius, minor_radius)
        """
        # Lấy vị trí của transmitter
        tx_pos = self.get_position(robot_x, robot_y, robot_size, robot_orientation)
        
        # Lấy hướng chùm tia
        beam_direction = self.get_beam_direction(robot_orientation)
        
        # Tính góc bắt đầu và độ rộng của chùm tia
        start_angle = (beam_direction - self.beam_angle / 2) % 360
        
        # Tính bán kính chính và phụ cho hình elip
        major_radius = self.beam_distance  # Bán kính dài (theo hướng chính)
        minor_radius = self.beam_distance * 0.6  # Bán kính ngắn (hẹp hơn)
        
        # Trả về thông số hình nón elip
        return (start_angle, self.beam_angle, major_radius, minor_radius, beam_direction)

    def set_beam_parameters(self, angle, pixel_distance, simulation=None):
        """
        Thiết lập thông số chùm tia
        
        Args:
            angle: Góc phát tính bằng độ
            pixel_distance: Khoảng cách phát tính bằng pixel
            simulation: Đối tượng simulation để chuyển đổi đơn vị (nếu cần)
        """
        self.beam_angle = angle
        self.beam_distance = pixel_distance
        
        # Lưu khoảng cách thực nếu có simulation
        if simulation:
            self.real_beam_distance = simulation.pixel_distance_to_real(pixel_distance)

class IRReceiver(IRSensor):
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        super().__init__(robot_id, side, position_index, rel_x, rel_y)
        self.sensitivity = 50
        self.viewing_angle = 120  # Góc nhìn của đầu nhận IR (độ)
        self.max_distance = 200   # Khoảng cách nhận tối đa (pixel)
        self.real_max_distance = 0.8  # Khoảng cách nhận tối đa (mét)
        self.direction_offset = 0  # Độ lệch hướng nhận (tương tự beam_direction_offset)
        self.signals = {}  # Dictionary để lưu tín hiệu từ các transmitter
        self.signals_lock = threading.Lock()  # Thêm lock để bảo vệ signals
    
    def clear_signals(self):
        """Xóa tất cả tín hiệu nhận được"""
        with self.signals_lock:  # Khóa trong khi sửa đổi
            self.signals.clear()
    
    def add_signal(self, transmitter_id, strength):
        """Thêm tín hiệu từ một transmitter"""
        with self.signals_lock:  # Khóa trong khi sửa đổi
            self.signals[transmitter_id] = strength
    
    def get_total_signal(self):
        """Tính tổng cường độ tín hiệu"""
        with self.signals_lock:
            return sum(self.signals.values()) if self.signals else 0

    def get_signals_copy(self):
        """Trả về bản sao an toàn của signals"""
        with self.signals_lock:
            return dict(self.signals) if self.signals else {}
            
    def get_strongest_signal(self):
        """Lấy tín hiệu mạnh nhất và nguồn phát tương ứng"""
        with self.signals_lock:
            if not self.signals:
                return None
            
            # Tìm transmitter_id có cường độ tín hiệu cao nhất
            strongest_tx_id = max(self.signals.items(), key=lambda x: x[1])[0]
            strength = self.signals[strongest_tx_id]
            
            # Trả về theo format cũ: (sender_id, tx_side, strength)
            return (strongest_tx_id, 0, strength)

    def has_signals(self):
        """Kiểm tra an toàn xem có tín hiệu nào không"""
        with self.signals_lock:
            return bool(self.signals)  # Trả về True nếu dictionary không rỗng

    def get_viewing_direction(self, robot_orientation):
        """Lấy hướng nhìn của receiver, tính theo góc độ (0-359)"""
        # Hướng cơ sở phụ thuộc vào receiver ở cạnh nào của robot
        if self.side == 0:  # Top
            base_direction = 270
        elif self.side == 1:  # Right
            base_direction = 0  
        elif self.side == 2:  # Bottom
            base_direction = 90
        else:  # Left
            base_direction = 180
        
        # Cộng thêm hướng của robot để có hướng thực tế
        return (base_direction + robot_orientation) % 360

    def set_receiver_parameters(self, angle, pixel_distance, simulation=None):
        """
        Thiết lập thông số đầu nhận
        
        Args:
            angle: Góc nhận tính bằng độ
            pixel_distance: Khoảng cách nhận tối đa tính bằng pixel
            simulation: Đối tượng simulation để chuyển đổi đơn vị (nếu cần)
        """
        self.viewing_angle = angle
        self.max_distance = pixel_distance
        
        # Lưu khoảng cách thực nếu có simulation
        if simulation:
            self.real_max_distance = simulation.pixel_distance_to_real(pixel_distance)

# Thêm vào phần code xử lý truyền nhận tín hiệu IR
def can_receive_signal(transmitter, receiver, robot_positions, obstacles=None):
    """
    Kiểm tra và tính toán tín hiệu từ transmitter đến receiver
    """
    # Lấy vị trí và hướng
    tx_robot = robot_positions[transmitter.robot_id]
    rx_robot = robot_positions[receiver.robot_id]
    
    tx_pos = transmitter.get_position(tx_robot['x'], tx_robot['y'], 
                                     tx_robot['size'], tx_robot['orientation'])
    rx_pos = receiver.get_position(rx_robot['x'], rx_robot['y'], 
                                  rx_robot['size'], rx_robot['orientation'])
    
    # Tính góc giữa transmitter và receiver
    angle_to_receiver = math.degrees(math.atan2(rx_pos[1] - tx_pos[1], 
                                               rx_pos[0] - tx_pos[0])) % 360
    
    # Lấy hướng chùm tia transmitter
    beam_direction = transmitter.get_beam_direction(tx_robot['orientation'])
    
    # Tính độ lệch góc giữa hướng chùm tia và hướng đến receiver
    angle_diff = min((beam_direction - angle_to_receiver) % 360, 
                     (angle_to_receiver - beam_direction) % 360)
    
    # Kiểm tra góc nghiêm ngặt (transmitter)
    beam_angle_tolerance = 0.9  # Giảm dung sai xuống 90%
    effective_beam_angle = transmitter.beam_angle * beam_angle_tolerance
    if angle_diff > effective_beam_angle / 2:
        return False, 0, 0
    
    # Kiểm tra hướng nhận của receiver
    rx_direction = receiver.get_viewing_direction(rx_robot['orientation'])
    angle_to_transmitter = (math.degrees(math.atan2(tx_pos[1] - rx_pos[1], 
                                                  tx_pos[0] - rx_pos[0]))) % 360
    
    # Sửa cách tính góc lệch cho chính xác
    rx_angle_diff = min((rx_direction - angle_to_transmitter) % 360, 
                        (angle_to_transmitter - rx_direction) % 360)
    
    # Thắt chặt điều kiện kiểm tra góc nhận
    viewing_angle_tolerance = 0.8  # Giảm dung sai xuống 80%
    effective_viewing_angle = receiver.viewing_angle * viewing_angle_tolerance
    
    # Debug info
    # print(f"RX Dir: {rx_direction}, Angle to TX: {angle_to_transmitter}, Diff: {rx_angle_diff}, Max: {effective_viewing_angle/2}")
    
    # Kiểm tra nghiêm ngặt hơn cho receiver
    if rx_angle_diff > effective_viewing_angle / 2:
        return False, 0, 0
    
    # Tính khoảng cách Euclidean - chỉ dùng để kiểm tra phạm vi
    dist = distance_between_points(tx_pos, rx_pos)
    
    # Kiểm tra khoảng cách tối đa
    if dist > transmitter.beam_distance or dist > receiver.max_distance:
        return False, 0, 0
    
    # Kiểm tra chướng ngại vật
    if obstacles and not check_line_of_sight(tx_pos, rx_pos, obstacles):
        return False, 0, 0
    
    # Tính cường độ tín hiệu dựa trên khoảng cách và góc lệch
    # 1. Thành phần góc - sử dụng cả góc phát và góc nhận
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(rx_angle_diff)) ** 2
    angle_factor = tx_angle_factor * rx_angle_factor  # Kết hợp cả hai yếu tố góc
    
    # 2. Thành phần khoảng cách - giảm theo hàm (1-(d/max_d)^2)
    distance_factor = 1 - (dist / transmitter.beam_distance) ** 2
    
    # 3. Tính cường độ tín hiệu tổng hợp
    signal_strength = transmitter.strength * angle_factor * distance_factor
    
    # Tăng ngưỡng cường độ tối thiểu
    min_threshold = 15  # Tăng để loại bỏ tín hiệu yếu
    if signal_strength < min_threshold:
        return False, 0, 0
    
    # Tính khoảng cách dựa trên cường độ tín hiệu
    intensity_based_distance = transmitter.beam_distance * (1 - math.sqrt(signal_strength / transmitter.strength))
    
    return True, intensity_based_distance, signal_strength




