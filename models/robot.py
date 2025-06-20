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

    def calculate_relative_position_rpa(self, emitter_robot_id):
        """Tính vị trí tương đối của robot phát tín hiệu theo thuật toán RPA
        
        Xử lý các cảm biến theo nguyên lý vòng tròn liên tục, không ngắt tại các góc.
        Hỗ trợ trường hợp chỉ có 1 hoặc 2 receiver nhận được tín hiệu.
        
        Args:
            emitter_robot_id: ID của robot đang phát tín hiệu
            
        Returns:
            tuple: (bearing_angle, distance, confidence) hoặc None nếu không đủ dữ liệu
        """
        import math
        
        # Bảng góc mặc định cho mỗi cạnh và vị trí
        # Format: {side: {position_index: angle}}
        DEFAULT_ANGLES = {
            0: {0: 240, 1: 270, 2: 300},  # top
            1: {0: 330, 1: 0, 2: 30},     # right
            2: {0: 120, 1: 90, 2: 60},    # bottom
            3: {0: 210, 1: 180, 2: 150}   # left
        }
        
        # Thu thập tất cả tín hiệu từ tất cả receiver
        all_signals = []
        
        for receiver in self.receivers:
            if emitter_robot_id in receiver.signals:
                signal_strength = receiver.signals[emitter_robot_id]
                angle = DEFAULT_ANGLES[receiver.side][receiver.position_index]
                all_signals.append((receiver.side, receiver.position_index, signal_strength, angle, receiver))
        
        # Nếu không có tín hiệu nào
        if not all_signals:
            return None
        
        # Tìm receiver có tín hiệu mạnh nhất
        strongest_signal = max(all_signals, key=lambda x: x[2])
        strongest_side, strongest_pos, r_0, base_angle, _ = strongest_signal
        
        # Sắp xếp tất cả tín hiệu theo góc tăng dần
        all_signals.sort(key=lambda x: x[3])
        
        # Số lượng tín hiệu
        total_signals = len(all_signals)
        
        # === TRƯỜNG HỢP ĐẶC BIỆT: Chỉ có 1 receiver nhận được tín hiệu ===
        if total_signals == 1:
            # Khi chỉ có 1 tín hiệu, ta cần dựa vào góc và cường độ tín hiệu
            theta = 0  # Giả sử nguồn phát nằm thẳng trước receiver
            
            # Cải thiện: Mối quan hệ giữa cường độ tín hiệu và khoảng cách
            signal_strength_normalized = r_0 / 100.0  # Giả sử cường độ tối đa là 100
            # Công thức khoảng cách tỷ lệ nghịch với căn bậc hai của cường độ tín hiệu
            distance = 1.0 / math.sqrt(signal_strength_normalized) if signal_strength_normalized > 0 else 4.0
            
            # Áp dụng góc cho receiver mạnh nhất
            bearing = base_angle
            
            # Chuyển đổi thành khoảng cách thực với hệ số hiệu chỉnh tốt hơn
            scale_factor = 0.15  # Điều chỉnh giảm để khoảng cách chính xác hơn
            real_distance = scale_factor * distance
            
            # Giới hạn khoảng cách hợp lý
            real_distance = min(3.0, max(0.05, real_distance))
            
            # Đặt độ tin cậy thấp hơn vì chỉ có 1 tín hiệu
            confidence = 0.2
            
            # Trả về kết quả
            relative_bearing = bearing % 360
            return (relative_bearing, real_distance, confidence)
        
        # === TRƯỜNG HỢP ĐẶC BIỆT: Chỉ có 2 receiver nhận được tín hiệu ===
        elif total_signals == 2:
            # Tìm vị trí của tín hiệu mạnh nhất trong danh sách đã sắp xếp
            strongest_index = next(i for i, signal in enumerate(all_signals) 
                                 if signal[0] == strongest_side and signal[1] == strongest_pos)
            
            # Lấy tín hiệu còn lại (sẽ là bên trái hoặc bên phải)
            other_index = 1 - strongest_index
            
            # Xác định góc của tín hiệu còn lại
            other_angle = all_signals[other_index][3]
            other_signal = all_signals[other_index][2]
            
            # Tính góc delta giữa hai receiver
            delta_angle = (other_angle - base_angle) % 360
            if delta_angle > 180:
                delta_angle = delta_angle - 360
            
            # Xác định r_minus1 và r_1 dựa trên vị trí tương đối
            if delta_angle > 0:  # Tín hiệu còn lại nằm bên phải
                r_1 = other_signal
                
                # Tính beta_1_right - góc với receiver phải
                beta_1_right = min(abs(other_angle - base_angle), 360 - abs(other_angle - base_angle))
                if (other_angle - base_angle) % 360 > 180:
                    beta_1_right = -beta_1_right
                beta_1_right = math.radians(beta_1_right)
                
                # Ước lượng beta_1_left và r_minus1 (tương tự như trường hợp 3 tín hiệu)
                # Giả định góc đối xứng và cường độ ước lượng
                beta_1_left = -beta_1_right
                r_minus1 = r_0 * (r_0 / r_1) * 0.7
            else:  # Tín hiệu còn lại nằm bên trái
                r_minus1 = other_signal
                
                # Tính beta_1_left - góc với receiver trái
                beta_1_left = min(abs(other_angle - base_angle), 360 - abs(other_angle - base_angle))
                if (base_angle - other_angle) % 360 > 180:
                    beta_1_left = -beta_1_left
                beta_1_left = math.radians(beta_1_left)
                
                # Ước lượng beta_1_right và r_1 (tương tự như trường hợp 3 tín hiệu)
                beta_1_right = -beta_1_left
                r_1 = r_0 * (r_0 / r_minus1) * 0.7
            
            # Áp dụng công thức từ thuật toán giống như trường hợp 3 tín hiệu
            if abs(math.degrees(beta_1_right)) < 10 or abs(math.degrees(beta_1_left)) < 10:
                # Nếu góc quá nhỏ, sử dụng giá trị mặc định
                beta_1 = math.pi / 6
                a = (r_1 + r_minus1 + 2*r_0) / (2 * math.cos(beta_1) + 2)
                b = (r_1 - r_minus1) / (2 * math.sin(beta_1))
            else:
                # Sử dụng công thức tổng quát giống trường hợp 3 tín hiệu
                a = (r_1 * math.cos(beta_1_right) + r_minus1 * math.cos(beta_1_left) + 
                    r_0 * (math.cos(beta_1_right) + math.cos(beta_1_left))) / (
                    math.cos(beta_1_right) + math.cos(beta_1_left) + 2)

                denominator = math.sin(beta_1_right) + math.sin(abs(beta_1_left))
                if abs(denominator) < 1e-6:
                    if r_1 > r_minus1:
                        b = 0.15 * a
                    elif r_1 < r_minus1:
                        b = -0.15 * a
                    else:
                        b = 0
                else:
                    b = (r_1 * math.sin(beta_1_right) - r_minus1 * math.sin(abs(beta_1_left))) / denominator
            
            # Tính theta và khoảng cách
            theta = math.degrees(math.atan2(b, a))
            distance = math.sqrt(a*a + b*b)
            
            # Điều chỉnh độ tin cậy xuống vì chúng ta đang ước lượng một trong các giá trị
            confidence = min(r_0, other_signal) / max(r_0, other_signal) * 0.8
        
        # === TRƯỜNG HỢP BÌNH THƯỜNG: 3+ receiver nhận được tín hiệu ===
        else:
            # Tìm vị trí của tín hiệu mạnh nhất trong danh sách đã sắp xếp
            strongest_index = next(i for i, signal in enumerate(all_signals) 
                                 if signal[0] == strongest_side and signal[1] == strongest_pos)
            
            # Lấy tín hiệu bên trái và bên phải
            left_index = (strongest_index - 1) % total_signals
            r_minus1 = all_signals[left_index][2]
            
            right_index = (strongest_index + 1) % total_signals
            r_1 = all_signals[right_index][2]
            
            # Tính góc giữa các receiver
            right_angle = all_signals[right_index][3]
            beta_1_right = min(abs(right_angle - base_angle), 360 - abs(right_angle - base_angle))
            if (right_angle - base_angle) % 360 > 180:
                beta_1_right = -beta_1_right
            beta_1_right = math.radians(beta_1_right)
            
            left_angle = all_signals[left_index][3]
            beta_1_left = min(abs(left_angle - base_angle), 360 - abs(left_angle - base_angle))
            if (base_angle - left_angle) % 360 > 180:
                beta_1_left = -beta_1_left
            beta_1_left = math.radians(beta_1_left)
            
            # Áp dụng công thức từ thuật toán
            if abs(math.degrees(beta_1_right)) < 10 or abs(math.degrees(beta_1_left)) < 10:
                # Nếu góc quá nhỏ, sử dụng giá trị mặc định
                beta_1 = math.pi / 6
                a = (r_1 + r_minus1 + 2*r_0) / (2 * math.cos(beta_1) + 2)
                b = (r_1 - r_minus1) / (2 * math.sin(beta_1))
            else:
                # Sử dụng công thức tổng quát
                a = (r_1 * math.cos(beta_1_right) + r_minus1 * math.cos(beta_1_left) + 
                    r_0 * (math.cos(beta_1_right) + math.cos(beta_1_left))) / (
                    math.cos(beta_1_right) + math.cos(beta_1_left) + 2)

                denominator = math.sin(beta_1_right) + math.sin(abs(beta_1_left))
                if abs(denominator) < 1e-6:
                    if r_1 > r_minus1:
                        b = 0.15 * a
                    elif r_1 < r_minus1:
                        b = -0.15 * a
                    else:
                        b = 0
                else:
                    b = (r_1 * math.sin(beta_1_right) - r_minus1 * math.sin(abs(beta_1_left))) / denominator
            
            # Tính theta và khoảng cách
            theta = math.degrees(math.atan2(b, a))
            distance = math.sqrt(a*a + b*b)
            
            # Tính độ tin cậy
            valid_signals = [r_minus1, r_0, r_1]
            confidence = min(valid_signals) / max(valid_signals) if max(valid_signals) > 0 else 0
        
        # Chuyển đổi cường độ tín hiệu thành khoảng cách thực (mét)
        scale_factor = 0.3
        real_distance = scale_factor / distance if distance > 0 else 3.0
        
        # Giới hạn khoảng cách trong phạm vi hợp lý
        real_distance = min(3.0, max(0.05, real_distance))
        
        # Tính góc bearing
        bearing = (base_angle + theta) % 360
        absolute_bearing = bearing
        relative_bearing = absolute_bearing % 360
        
        # In ra log debug nếu cần
        print(f"Debug RPA: bearing={bearing}, signals={total_signals}, result={relative_bearing}")
        
        return (relative_bearing, real_distance, confidence)

    def calculate_relative_coordinates(self, angle, distance, is_relative=True):
        """Tính toán tọa độ tương đối dựa trên góc và khoảng cách
        
        Args:
            angle: Góc (độ) - có thể là tương đối hoặc tuyệt đối tùy theo is_relative
            distance: Khoảng cách (mét hoặc pixel)
            is_relative: Nếu True, angle là góc tương đối và cần thêm orientation
                        Nếu False, angle là góc tuyệt đối và không cần thêm orientation
        """
        # Tính góc trong hệ tọa độ toàn cầu
        if is_relative:
            # Nếu là góc tương đối, thêm orientation của robot
            global_angle = angle % 360
        else:
            # Nếu là góc tuyệt đối, sử dụng trực tiếp   
            global_angle = (self.orientation + angle) % 360
            
        angle_rad = math.radians(global_angle)
        
        # Tọa độ tương đối
        rel_x = distance * math.cos(angle_rad)
        rel_y = distance * math.sin(angle_rad)
        
        return (rel_x, rel_y)

    def move_forward(self, distance=0.02):
        """Di chuyển robot tiến về phía trước"""
        if self.simulation:
            px_distance = self.simulation.real_distance_to_pixel(distance)
        else:
            px_distance = distance * 250  # Mặc định 250px/m
        
        angle_rad = math.radians(self.orientation)
        dx = px_distance * math.cos(angle_rad)
        dy = px_distance * math.sin(angle_rad)
        self.move(dx, dy)
    
    def move_backward(self, distance=0.02):
        """Di chuyển robot lùi về phía sau"""
        if self.simulation:
            px_distance = self.simulation.real_distance_to_pixel(distance)
        else:
            px_distance = distance * 250  # Mặc định 250px/m
        
        angle_rad = math.radians(self.orientation)
        dx = -px_distance * math.cos(angle_rad)
        dy = -px_distance * math.sin(angle_rad)
        self.move(dx, dy)