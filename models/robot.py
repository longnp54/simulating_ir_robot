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
        
        # === THAY ĐỔI: Khởi tạo transmitters ===
        self.transmitters = []
        
        # Cài đặt offset từ mép cho cả transmitter và receiver
        sensor_offset_from_edge = 0.2  # 2cm từ mép
        
        # Vị trí tương đối của 3 IR receiver (giữ nguyên)
        receiver_positions = [-0.578, 0.0, 0.578]
        
        # === MỚI: Vị trí tương đối của 2 IR transmitter xen kẽ ===
        # Tính toán để nằm giữa các IR receiver
        transmitter_positions = [-0.289, 0.289]  # Xen kẽ giữa các receiver
        
        # === MỚI: Góc lệch cho IR transmitter ===
        outward_offset_angle = 15  # Góc hướng ra ngoài 15°
        
        # --- Thiết lập transmitters trước ---
        for side in sides:
            if side == 0:  # top
                for i, pos in enumerate(transmitter_positions):
                    rel_x = pos
                    rel_y = -1 + sensor_offset_from_edge
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc lệch ra ngoài
                    if i == 0:  # Transmitter bên trái
                        tx.beam_direction_offset = -outward_offset_angle  # Âm
                    else:  # Transmitter bên phải
                        tx.beam_direction_offset = +outward_offset_angle  # Dương
                    self.transmitters.append(tx)
            elif side == 1:  # right
                for i, pos in enumerate(transmitter_positions):
                    rel_x = 1 - sensor_offset_from_edge
                    rel_y = pos
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc lệch ra ngoài
                    if i == 0:  # Transmitter bên trên
                        tx.beam_direction_offset = +outward_offset_angle
                    else:  # Transmitter bên dưới
                        tx.beam_direction_offset = -outward_offset_angle
                    self.transmitters.append(tx)
            elif side == 2:  # bottom
                for i, pos in enumerate(transmitter_positions):
                    rel_x = pos
                    rel_y = 1 - sensor_offset_from_edge
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc lệch ra ngoài
                    if i == 0:  # Transmitter bên trái
                        tx.beam_direction_offset = outward_offset_angle
                    else:  # Transmitter bên phải
                        tx.beam_direction_offset = -outward_offset_angle
                    self.transmitters.append(tx)
            else:  # left
                for i, pos in enumerate(transmitter_positions):
                    rel_x = -1 + sensor_offset_from_edge
                    rel_y = pos
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Thiết lập góc lệch ra ngoài
                    if i == 0:  # Transmitter bên trên
                        tx.beam_direction_offset = -outward_offset_angle
                    else:  # Transmitter bên dưới
                        tx.beam_direction_offset = outward_offset_angle
                    self.transmitters.append(tx)
        
        # --- Thiết lập receivers sau ---
        self.receivers = []
        rx_outward_offset_angle = 30  # Góc hướng ra ngoài cho receiver
        # [Phần code thiết lập receivers giữ nguyên]
        for side in sides:
            if side == 0:  # top
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = -1 + sensor_offset_from_edge
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Áp dụng góc lệch cho các receiver ngoài cùng
                    if i == 0:  # Receiver bên trái
                        rx.direction_offset = -rx_outward_offset_angle
                    elif i == 2:  # Receiver bên phải
                        rx.direction_offset = rx_outward_offset_angle
                    self.receivers.append(rx)
            elif side == 1:  # right
                for i, pos in enumerate(receiver_positions):
                    rel_x = 1 - sensor_offset_from_edge
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Áp dụng góc lệch cho các receiver ngoài cùng
                    if i == 0:  # Receiver bên trên
                        rx.direction_offset = -rx_outward_offset_angle
                    elif i == 2:  # Receiver bên dưới
                        rx.direction_offset = rx_outward_offset_angle
                    self.receivers.append(rx)
            elif side == 2:  # bottom
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = 1 - sensor_offset_from_edge
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Áp dụng góc lệch cho các receiver ngoài cùng
                    if i == 0:  # Receiver bên trái
                        rx.direction_offset = rx_outward_offset_angle
                    elif i == 2:  # Receiver bên phải
                        rx.direction_offset = -rx_outward_offset_angle
                    self.receivers.append(rx)
            else:  # left
                for i, pos in enumerate(receiver_positions):
                    rel_x = -1 + sensor_offset_from_edge
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Áp dụng góc lệch cho các receiver ngoài cùng
                    if i == 0:  # Receiver bên trên
                        rx.direction_offset = rx_outward_offset_angle
                    elif i == 2:  # Receiver bên dưới
                        rx.direction_offset = -rx_outward_offset_angle
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
        """Ước lượng vị trí dựa trên tín hiệu IR nhận được với mô hình Rician"""
        position_estimates = []
        
        # Tìm vị trí dựa trên tín hiệu IR
        for i, receiver in enumerate(self.receivers):
            processed_signal = receiver.process_signals()
            if processed_signal:
                sender_id, strength, snr = processed_signal
                
                # Xác định có LOS hay không dựa trên SNR
                has_los = snr > 2.5  # SNR cao thường tương ứng với LOS tốt
                
                # ĐỔI: Sử dụng phương pháp mới thay vì phương pháp cũ
                # estimated_distance = receiver.estimate_distance_rician(strength, has_los) 
                estimated_distance = receiver.estimate_distance_pathloss_rician(strength, has_los)
                
                # Thêm vào danh sách ước lượng
                position_estimates.append((sender_id, estimated_distance, i))
        
        # THÊM MỚI: Sử dụng vị trí vật lý khi không có tín hiệu IR
        if not position_estimates and self.simulation:
            for robot in self.simulation.robots:
                if robot.id != self.id:
                    # Tính khoảng cách vật lý
                    dx = robot.x - self.x
                    dy = robot.y - self.y
                    distance_pixel = math.sqrt(dx*dx + dy*dy)
                    distance_m = self.simulation.pixel_distance_to_real(distance_pixel)
                    
                    # Chỉ xét các robot trong khoảng cách hợp lý (3m)
                    if distance_m < 3.0:
                        # Sử dụng mã -1 để chỉ ra rằng đây là ước lượng dựa trên khoảng cách vật lý
                        position_estimates.append((robot.id, distance_m, -1))
        
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

    def get_physical_distance_to(self, other_robot):
        """Tính khoảng cách vật lý đến robot khác theo mét"""
        if not self.simulation:
            return float('inf')
            
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        distance_pixel = math.sqrt(dx*dx + dy*dy)
        return self.simulation.pixel_distance_to_real(distance_pixel)

    def get_bearing_to(self, other_robot):
        """Tính góc tuyệt đối hướng đến robot khác (0-359 độ)"""
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        # Thay đổi từ atan2(-dy, dx) thành atan2(dy, dx)
        angle = math.degrees(math.atan2(dy, dx)) % 360
        return angle

    def get_relative_angle_to(self, other_robot):
        """Tính góc tương đối từ hướng hiện tại đến robot khác (0-359 độ)"""
        absolute_angle = self.get_bearing_to(other_robot)
        relative_angle = (absolute_angle - self.orientation) % 360
        return relative_angle
