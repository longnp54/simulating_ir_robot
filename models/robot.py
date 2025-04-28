from models.ir_sensor import IRTransmitter, IRReceiver
import math

class Robot:
    def __init__(self, robot_id, x=0, y=0, orientation=0):
        self.id = robot_id
        self.x = x
        self.y = y
        self.orientation = orientation
        self.size = 50
        self.simulation = None  # Sẽ được thiết lập khi robot được thêm vào simulation
        
        # Khởi tạo danh sách cảm biến bằng ID robot
        self.transmitters = []
        self.receivers = []
        self._setup_sensors()
    
    def _setup_sensors(self):
        """Thiết lập cảm biến IR thu và phát cho robot"""
        sides = [0, 1, 2, 3]  # (top, right, bottom, left)
        
        # Tạo 3 transmitter mỗi mặt (giữ nguyên phần này)
        for side in sides:
            # Tạo transmitters với ID robot thay vì truyền tham chiếu robot
            if side == 0 or side == 2:  # top or bottom
                tx_center = IRTransmitter(self.id, side, 0, rel_x=0, rel_y=0)
                tx_left = IRTransmitter(self.id, side, 1, rel_x=-0.4, rel_y=0)
                tx_right = IRTransmitter(self.id, side, 2, rel_x=0.4, rel_y=0)
                
                # Đặt offset 30 độ cho các transmitter ngoài cùng
                tx_center.beam_direction_offset = 0  # Transmitter giữa không offset
                
                if side == 0:  # top
                    tx_left.beam_direction_offset = -30  # Hướng lên trái 30°
                    tx_right.beam_direction_offset = 30  # Hướng lên phải 30°
                else:  # bottom
                    tx_left.beam_direction_offset = 30  # Hướng xuống trái 30°
                    tx_right.beam_direction_offset = -30  # Hướng xuống phải 30°
                
                transmitters = [tx_center, tx_left, tx_right]
            else:  # right or left
                tx_center = IRTransmitter(self.id, side, 0, rel_x=0, rel_y=0)
                tx_up = IRTransmitter(self.id, side, 1, rel_x=0, rel_y=-0.4)
                tx_down = IRTransmitter(self.id, side, 2, rel_x=0, rel_y=0.4)
                
                # Đặt offset 30 độ cho các transmitter ngoài cùng
                tx_center.beam_direction_offset = 0  # Transmitter giữa không offset
                
                if side == 1:  # right
                    tx_up.beam_direction_offset = -30  # Hướng phải lên 30°
                    tx_down.beam_direction_offset = 30  # Hướng phải xuống 30°
                else:  # left
                    tx_up.beam_direction_offset = 30  # Hướng trái lên 30°
                    tx_down.beam_direction_offset = -30  # Hướng trái xuống 30°
                
                transmitters = [tx_center, tx_up, tx_down]
            
            # Khởi tạo các thuộc tính liên quan đến kích thước
            for tx in transmitters:
                tx.initialize_with_robot_size(self.size)
                self.transmitters.append(tx)
        
        # Tạo 4 receiver mỗi cạnh, cách cạnh 2cm, xen kẽ với transmitters
        offset_from_edge = 0.2  # 2cm (20% kích thước robot 10cm)
        receiver_positions = [-0.6, -0.2, 0.2, 0.6]  # Vị trí xen kẽ với transmitters
        
        for side in sides:
            if side == 0:  # top
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = -1 + offset_from_edge  # Cách cạnh trên 2cm
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc nhận hẹp hơn
                    rx.viewing_angle = 60  # Thiết lập góc nhận hẹp hơn mặc định
                    self.receivers.append(rx)
            elif side == 1:  # right
                for i, pos in enumerate(receiver_positions):
                    rel_x = 1 - offset_from_edge  # Cách cạnh phải 2cm
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc nhận hẹp hơn
                    rx.viewing_angle = 60  # Thiết lập góc nhận hẹp hơn mặc định
                    self.receivers.append(rx)
            elif side == 2:  # bottom
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = 1 - offset_from_edge  # Cách cạnh dưới 2cm
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc nhận hẹp hơn
                    rx.viewing_angle = 60  # Thiết lập góc nhận hẹp hơn mặc định
                    self.receivers.append(rx)
            else:  # left
                for i, pos in enumerate(receiver_positions):
                    rel_x = -1 + offset_from_edge  # Cách cạnh trái 2cm
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc nhận hẹp hơn
                    rx.viewing_angle = 60  # Thiết lập góc nhận hẹp hơn mặc định
                    self.receivers.append(rx)
    
    def move(self, dx, dy):
        """Di chuyển robot thêm một khoảng (dx, dy)"""
        self.x += dx
        self.y += dy
    
    def set_position(self, x, y):
        """Đặt vị trí mới cho robot"""
        self.x = x
        self.y = y
    
    def rotate(self, angle):
        """Xoay robot thêm một góc (độ)"""
        self.orientation = (self.orientation + angle) % 360
    
    def set_orientation(self, angle):
        """Đặt hướng mới cho robot (độ)"""
        self.orientation = angle % 360
    
    def get_corner_positions(self):
        """Lấy tọa độ 4 góc của robot (sau khi xoay)"""
        half_size = self.size / 2
        corners = [
            (-half_size, -half_size),  # Góc trên trái
            (half_size, -half_size),   # Góc trên phải
            (half_size, half_size),    # Góc dưới phải
            (-half_size, half_size)    # Góc dưới trái
        ]
        
        # Xoay các góc theo orientation
        angle_rad = math.radians(self.orientation)
        rotated_corners = []
        
        for cx, cy in corners:
            # Phép xoay 2D
            rotated_x = cx * math.cos(angle_rad) - cy * math.sin(angle_rad)
            rotated_y = cx * math.sin(angle_rad) + cy * math.cos(angle_rad)
            
            # Dịch chuyển về vị trí thực
            actual_x = self.x + rotated_x
            actual_y = self.y + rotated_y
            
            rotated_corners.append((actual_x, actual_y))
        
        return rotated_corners
    
    def contains_point(self, px, py):
        """Kiểm tra xem một điểm có nằm trong robot không"""
        # Cách đơn giản: kiểm tra khoảng cách từ tâm đến điểm
        # (đây là gần đúng vì khi robot xoay, hình dạng không còn là hình vuông đối với hệ tọa độ)
        dx = px - self.x
        dy = py - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        return distance <= self.size / 2
    
    def calculate_relative_position(self, other_robot):
        """Tính toán vị trí tương đối của robot khác"""
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Tính góc (theo độ) từ robot này đến robot kia
        angle = math.degrees(math.atan2(dy, dx))
        
        # Góc tương đối (góc nhìn từ hướng của robot này)
        relative_angle = (angle - self.orientation) % 360
        
        return distance, relative_angle
    
    def triangulate_position(self, bearing_measurements):
        """Ước lượng vị trí dựa trên các góc bearing đo được
        
        bearing_measurements là danh sách các tuple (robot_id, bearing_angle)
        """
        if len(bearing_measurements) < 2:
            return None  # Cần ít nhất 2 góc bearing để triangulate
        
        # Phương pháp triangulation đơn giản
        # (Trong thực tế sẽ cần thuật toán phức tạp hơn)
        estimated_positions = []
        for robot_id, bearing in bearing_measurements:
            # Tìm robot đích
            target_robot = None
            for robot in self.simulation.robots:
                if robot.id == robot_id:
                    target_robot = robot
                    break
            
            if target_robot:
                # Từ bearing và vị trí robot đích, tính toán vị trí có thể
                bearing_rad = math.radians(bearing)
                dx = math.cos(bearing_rad)
                dy = math.sin(bearing_rad)
                estimated_positions.append((target_robot.x + dx, target_robot.y + dy))
        
        # Tính vị trí trung bình
        if estimated_positions:
            avg_x = sum(pos[0] for pos in estimated_positions) / len(estimated_positions)
            avg_y = sum(pos[1] for pos in estimated_positions) / len(estimated_positions)
            return avg_x, avg_y
        
        return None
    
    def estimate_position_from_ir(self):
        """Ước lượng vị trí dựa trên tín hiệu IR nhận được"""
        position_estimates = []
        
        for i, receiver in enumerate(self.receivers):
            strongest_signal = receiver.get_strongest_signal()
            if strongest_signal:
                sender_id, tx_side, strength = strongest_signal
                # Ước tính khoảng cách dựa trên cường độ
                # (đây chỉ là công thức đơn giản, có thể điều chỉnh)
                estimated_distance = 100 * math.sqrt(100 / strength)
                position_estimates.append((sender_id, estimated_distance, i))
        
        return position_estimates
    
    def update_sensor_positions(self):
        """Cập nhật vị trí của tất cả cảm biến"""
        # Phương thức này không cần nữa vì sensors sẽ tính vị trí khi cần
        pass
    
    def get_transmitter_positions(self):
        """Lấy vị trí của tất cả transmitters"""
        positions = []
        for tx in self.transmitters:
            pos = tx.get_position(self.x, self.y, self.size, self.orientation)
            positions.append((tx, pos))
        return positions
    
    def get_receiver_positions(self):
        """Lấy vị trí của tất cả receivers"""
        positions = []
        for rx in self.receivers:
            pos = rx.get_position(self.x, self.y, self.size, self.orientation)
            positions.append((rx, pos))
        return positions
