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
        self.real_beam_distance = 0.6  # Thêm thuộc tính mới lưu khoảng cách thực (mét)
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



