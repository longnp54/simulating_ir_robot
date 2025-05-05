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
        self.beam_angle = 45  # Giảm từ 120° xuống 45° - phù hợp với thông báo lỗi
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
        if self.side == 0:  # top -> trục X dương
            base_direction = 270
        elif self.side == 1:  # right -> trục Y dương
            base_direction = 0
        elif self.side == 2:  # bottom -> trục X âm
            base_direction = 90
        else:  # left -> trục Y âm
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
        self.viewing_angle = 60
        self.max_distance = 200
        self.real_max_distance = 0.8
        self.direction_offset = 0
        self.signals = {}
        self.signals_lock = threading.Lock()
        self.snr = 0.0  # Thêm biến lưu SNR
    
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

    def has_signals(self, min_strength=20):  # Tăng từ 15 lên 20
        """Kiểm tra an toàn xem có tín hiệu mạnh không"""
        with self.signals_lock:
            # Kiểm tra nếu có bất kỳ tín hiệu nào vượt qua ngưỡng
            return any(strength >= min_strength for strength in self.signals.values())

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
        
        # Cộng thêm hướng của robot VÀ direction_offset để có hướng thực tế
        return (base_direction + robot_orientation + self.direction_offset) % 360

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

    def process_signals(self):
        """Xử lý các tín hiệu nhận được, phân tích chồng lấn"""
        with self.signals_lock:
            if not self.signals:
                return None
            
            # Tìm tín hiệu mạnh nhất
            strongest_tx_id = max(self.signals.items(), key=lambda x: x[1])[0]
            strongest_strength = self.signals[strongest_tx_id]
            
            # Tính tổng nhiễu từ các tín hiệu khác
            interference = sum(strength for tx_id, strength in self.signals.items() 
                             if tx_id != strongest_tx_id)
            
            # Tính SNR (Signal-to-Noise Ratio)
            snr = strongest_strength / (interference + 1.0)  # +1 để tránh chia cho 0
            
            # Lưu thông tin SNR
            self.snr = snr
            
            # Chỉ chấp nhận tín hiệu nếu SNR đủ cao
            if snr < 1.5:  # Ngưỡng SNR để phân biệt tín hiệu
                return None
                
            # Trả về tín hiệu mạnh nhất và SNR
            return strongest_tx_id, strongest_strength, snr

    def estimate_distance_rician(self, strength, has_los=True):
        """
        DEPRECATED: Sử dụng estimate_distance_pathloss_rician thay vì phương thức này.
        Phương thức này chỉ được giữ lại để tương thích với mã cũ.
        """
        # Chuyển hướng gọi đến phương thức mới
        return self.estimate_distance_pathloss_rician(strength, has_los)

    def estimate_distance_pathloss_rician(self, signal_strength, has_los=True):
        """
        Ước tính khoảng cách dựa trên mô hình Rician với suy giảm đều
        """
        from utils.ir_physics import signal_strength_to_distance_rician
        
        # Ước lượng góc dựa trên giá trị trung bình (không biết góc thực tế)
        average_angle_factor = 0.7  # Giá trị trung bình giả định
        
        # Sử dụng cùng một hàm ước lượng mới
        beam_distance_meter = 0.8  # Giả định 0.8m nếu không có thông tin
        if hasattr(self, 'real_max_distance'):
            beam_distance_meter = self.real_max_distance
            
        estimated_distance = signal_strength_to_distance_rician(
            signal_strength=signal_strength,
            beam_distance=beam_distance_meter,
            tx_strength=100,  # Giả định cường độ phát tối đa
            rx_sensitivity=self.sensitivity,
            angle_factor=average_angle_factor,
            has_los=has_los
        )
        
        return estimated_distance

# Thêm vào phần code xử lý truyền nhận tín hiệu IR
from utils.ir_physics import distance_to_signal_strength, signal_strength_to_distance

def can_receive_signal(transmitter, receiver, robot_positions, obstacles=None, debug=False):
    """
    Kiểm tra và tính toán tín hiệu từ transmitter đến receiver
    sử dụng mô hình Rician với suy giảm đều
    """
    # Lấy vị trí và hướng từ robot_positions (giữ nguyên)
    tx_robot = robot_positions[transmitter.robot_id]
    rx_robot = robot_positions[receiver.robot_id]
    
    # Tính vị trí của transmitter và receiver
    tx_pos = transmitter.get_position(tx_robot['x'], tx_robot['y'], 
                                     tx_robot['size'], tx_robot['orientation'])
    rx_pos = receiver.get_position(rx_robot['x'], rx_robot['y'], 
                                  rx_robot['size'], rx_robot['orientation'])
    
    # Tính khoảng cách giữa transmitter và receiver
    from utils.geometry import distance_between_points, check_line_of_sight
    dist_pixel = distance_between_points(tx_pos, rx_pos)
    
    # Chuyển đổi khoảng cách từ pixel sang mét
    dist_meter = dist_pixel / 250
    
    # Chuyển đổi beam_distance từ pixel sang mét
    beam_distance_meter = transmitter.beam_distance / 250
    
    # Kiểm tra khoảng cách tối đa
    if dist_pixel > transmitter.beam_distance:
        return False, 0, 0
    
    # Tính góc từ transmitter đến receiver
    import math
    dx = rx_pos[0] - tx_pos[0]
    dy = rx_pos[1] - tx_pos[1]
    angle_to_receiver = math.degrees(math.atan2(dy, dx)) % 360
    
    # Lấy hướng chùm tia của transmitter
    beam_direction = transmitter.get_beam_direction(tx_robot['orientation'])
    
    # Tính góc lệch
    angle_diff = abs((beam_direction - angle_to_receiver + 180) % 360 - 180)
    
    # Nếu nằm ngoài góc phát, không có tín hiệu
    if angle_diff > transmitter.beam_angle / 2:
        return False, 0, 0
    
    # Tính góc từ receiver đến transmitter
    angle_to_transmitter = (math.degrees(math.atan2(-dy, -dx))) % 360
    
    # Lấy hướng nhận của receiver
    receiver_direction = receiver.get_viewing_direction(rx_robot['orientation'])
    
    # Tính góc lệch nhận
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # Nếu nằm ngoài góc nhận, không có tín hiệu
    if receiver_angle_diff > receiver.viewing_angle / 2:
        return False, 0, 0
    
    # Tính hệ số góc phát và nhận
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    angle_factor = tx_angle_factor * rx_angle_factor
    
    # Kiểm tra line of sight
    has_los = True
    if obstacles:
        has_los = check_line_of_sight(tx_pos, rx_pos, obstacles)
    
    # Sử dụng hàm mới để tính cường độ tín hiệu - KHÔNG sử dụng pathloss
    from utils.ir_physics import distance_to_signal_strength_rician
    
    signal_strength = distance_to_signal_strength_rician(
        distance=dist_meter,
        beam_distance=beam_distance_meter,
        tx_strength=transmitter.strength,
        rx_sensitivity=receiver.sensitivity,
        angle_factor=angle_factor,
        has_los=has_los
    )
    
    # Giảm ngưỡng tối thiểu để hiển thị tín hiệu yếu hơn
    if signal_strength < 1.5:
        return False, 0, 0
    
    # Ước lượng khoảng cách dựa trên tín hiệu
    from utils.ir_physics import signal_strength_to_distance_rician
    estimated_distance = signal_strength_to_distance_rician(
        signal_strength=signal_strength,
        beam_distance=beam_distance_meter, 
        tx_strength=transmitter.strength,
        rx_sensitivity=receiver.sensitivity,
        angle_factor=angle_factor,
        has_los=has_los
    )
    
    return True, estimated_distance, signal_strength

def update_canvas(self):
    """Cập nhật toàn bộ canvas"""
    # Xóa tất cả các đối tượng trên canvas
    self.delete("all")
    self.robot_objects.clear()  # Xóa bộ nhớ cache đối tượng robot
    
    # Vẽ lưới tọa độ
    self._draw_grid()
    
    # Vẽ tất cả robot
    for robot in self.simulation.robots:
        self._draw_robot(robot)
    
    # Vẽ các tín hiệu IR nếu đang mô phỏng - CHỈ KHI simulation.running = True
    if self.simulation.running:
        self._draw_ir_signals()