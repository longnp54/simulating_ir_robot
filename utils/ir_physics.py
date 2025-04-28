import math
from utils.geometry import distance_between_points, check_line_of_sight

def calculate_ir_signal_strength(transmitter, receiver, simulation=None, tx_pos=None, rx_pos=None):
    """
    Tính toán cường độ tín hiệu IR từ transmitter đến receiver
    Điều kiện: transmitter phải là IRTransmitter và receiver phải là IRReceiver
    """
    # Kiểm tra rõ ràng cả transmitter và receiver
    from models.ir_sensor import IRReceiver, IRTransmitter
    
    # Debug: Kiểm tra xem có đảo ngược vai trò của transmitter và receiver không
    if isinstance(transmitter, IRReceiver):
        print(f"LỖI: Đầu thu (IRReceiver) ID={transmitter.robot_id}, Side={transmitter.side}, Index={transmitter.position_index} đang được dùng làm transmitter!")
        return 0
        
    if isinstance(receiver, IRTransmitter):
        print(f"LỖI: Đầu phát (IRTransmitter) ID={receiver.robot_id}, Side={receiver.side}, Index={receiver.position_index} đang được dùng làm receiver!")
        return 0
    
    # Đảm bảo transmitter là IRTransmitter
    if not isinstance(transmitter, IRTransmitter):
        print(f"DEBUG: Đối tượng không phải IRTransmitter! Type: {type(transmitter).__name__}")
        return 0  # Nếu không phải IRTransmitter thì không có tín hiệu phát
        
    # Đảm bảo receiver là IRReceiver
    if not isinstance(receiver, IRReceiver):
        print(f"DEBUG: Đối tượng không phải IRReceiver! Type: {type(receiver).__name__}")
        return 0  # Nếu không phải IRReceiver thì không nhận tín hiệu
    
    # Tiếp tục với phần kiểm tra hiện tại
    if not hasattr(receiver, 'viewing_angle') or not hasattr(receiver, 'signals'):
        print(f"DEBUG: Receiver không có thuộc tính viewing_angle hoặc signals!")
        return 0
    
    # Nếu transmitter không hoạt động, không có tín hiệu
    if not transmitter.active:
        return 0
    
    # Sử dụng vị trí được cung cấp hoặc tính toán nếu cần
    if tx_pos is None:
        if simulation:
            # Tìm robot có id = transmitter.robot_id
            tx_robot = next((r for r in simulation.robots if r.id == transmitter.robot_id), None)
            if not tx_robot:
                return 0
            tx_pos = transmitter.get_position(tx_robot.x, tx_robot.y, tx_robot.size, tx_robot.orientation)
        else:
            return 0  # Không đủ thông tin để tính vị trí
    
    if rx_pos is None:
        if simulation:
            rx_robot = next((r for r in simulation.robots if r.id == receiver.robot_id), None)
            if not rx_robot:
                return 0
            rx_pos = receiver.get_position(rx_robot.x, rx_robot.y, rx_robot.size, rx_robot.orientation)
        else:
            return 0  # Không đủ thông tin để tính vị trí
    
    # Tính khoảng cách giữa transmitter và receiver
    dist = distance_between_points(tx_pos, rx_pos)
    
    # Nếu nằm ngoài khoảng cách phát, không có tín hiệu
    if dist > transmitter.beam_distance:
        return 0
    
    # Kiểm tra có vật cản không
    if simulation and not check_line_of_sight(tx_pos, rx_pos, [r for r in simulation.robots if r.id != receiver.robot_id]):
        return 0  # Có vật cản, không có tín hiệu
    
    # Tính góc hướng từ transmitter đến receiver
    dx = rx_pos[0] - tx_pos[0]
    dy = rx_pos[1] - tx_pos[1]
    angle_to_receiver = math.degrees(math.atan2(dy, dx))
    if angle_to_receiver < 0:
        angle_to_receiver += 360
    
    # Tính hướng chùm tia của transmitter
    if simulation:
        tx_robot = next((r for r in simulation.robots if r.id == transmitter.robot_id), None)
        if tx_robot:
            beam_direction = transmitter.get_beam_direction(tx_robot.orientation)
        else:
            beam_direction = 0
    else:
        beam_direction = 0
    
    # Tính góc lệch
    angle_diff = min(abs(beam_direction - angle_to_receiver), 
                     360 - abs(beam_direction - angle_to_receiver))
    
    # Nếu nằm ngoài góc beam, không có tín hiệu
    if angle_diff > transmitter.beam_angle / 2:
        return 0
    
    # Tính góc lệch phát theo radian
    rel_angle_rad = math.radians(angle_diff)
    angle_ratio = abs(rel_angle_rad) / (math.radians(transmitter.beam_angle / 2))
    
    # Tham số superellipse cho đầu phát
    n_superellipse = 4.0
    
    # --- Kiểm tra góc nhận của receiver ---
    if simulation:
        rx_robot = next((r for r in simulation.robots if r.id == receiver.robot_id), None)
        if rx_robot:
            receiver_direction = receiver.get_viewing_direction(rx_robot.orientation)
        else:
            receiver_direction = 0
    else:
        receiver_direction = 0
    
    # Tính góc đến transmitter từ receiver
    dx_reverse = tx_pos[0] - rx_pos[0]
    dy_reverse = tx_pos[1] - rx_pos[1]
    angle_to_transmitter = math.degrees(math.atan2(dy_reverse, dx_reverse))
    if angle_to_transmitter < 0:
        angle_to_transmitter += 360
    
    # Tính góc lệch giữa hướng đầu nhận và hướng đến transmitter
    # THAY ĐỔI: Điều chỉnh cách tính góc lệch đơn giản hơn
    angle_diff_direct = abs(receiver_direction - angle_to_transmitter)
    if angle_diff_direct > 180:
        angle_diff_direct = 360 - angle_diff_direct
    receiver_angle_diff = angle_diff_direct
    
    # THAY ĐỔI: Sử dụng góc nhận đầy đủ, không giảm hệ số nữa
    max_reception_angle = receiver.viewing_angle  # Thay đổi từ 0.7 thành 1.0
    
    # THAY ĐỔI: Chỉ hiển thị thông báo debug khi thực sự cần thiết
    if receiver_angle_diff > max_reception_angle / 2:
        # Bỏ thông báo này để giảm spam trong console
        # if simulation and simulation.debug_mode:
        #     print(f"IR REJECT: RX góc lệch={receiver_angle_diff:.1f}° > {max_reception_angle/2:.1f}°")
        return 0

    # Tính tỷ lệ góc lệch so với góc nhận tối đa (0 = chính giữa, 1 = biên)
    rx_angle_ratio = receiver_angle_diff / max_reception_angle

    # Áp dụng hàm phi tuyến để tạo đặc tính giảm dần mượt mà từ trung tâm ra biên
    # Sử dụng hàm cosine cao bậc (hiệu ứng "vòm")
    rx_angle_factor = math.cos(rx_angle_ratio * math.pi/2) ** 4  # Tăng từ mũ 2 lên mũ 4

    # Tăng cường để tạo hiệu ứng rõ ràng hơn - tín hiệu mạnh ở giữa, yếu ở biên
    rx_power_factor = 4.0  # Hệ số mũ điều chỉnh độ dốc của đồ thị
    rx_angle_factor = (1 - rx_angle_ratio ** rx_power_factor) ** (1/rx_power_factor)

    # Kết hợp với hệ số khoảng cách
    distance_factor = 1 - (dist / transmitter.beam_distance) ** 2

    # Tính hệ số góc nhận cuối cùng - cao nhất khi ở chính giữa, thấp nhất ở biên
    rx_direction_factor = rx_angle_factor

    # Thêm debug nếu cần
    if simulation.debug_mode and rx_angle_ratio > 0.8:  # Chỉ in debug cho các góc gần biên
        print(f"IR nhận: góc lệch={receiver_angle_diff:.1f}°, tỷ lệ={rx_angle_ratio:.2f}, hệ số={rx_direction_factor:.2f}")

    # Tính giảm cường độ theo khoảng cách
    distance_factor = 1 - (dist / transmitter.beam_distance) ** 1.5  # Giảm từ 2.2 xuống 1.5
    
    # Cường độ theo góc nhận - thay đổi để nghiêm ngặt hơn
    rel_rx_angle_rad = math.radians(receiver_angle_diff)
    rx_angle_ratio = abs(rel_rx_angle_rad) / (math.radians(max_reception_angle))
    
    # Áp dụng công thức giảm mạnh hơn cho đầu nhận
    n_rx = 4.0  # Tăng cao hơn để tạo đặc tính nhận hẹp
    rx_angle_factor = (1 - rx_angle_ratio ** n_rx) ** (1/n_rx)
    
    # Hệ số cường độ phát
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2  # Giảm từ 4 xuống 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2  # Giảm từ 3 xuống 2
    angle_factor = tx_angle_factor * rx_angle_factor
    
    # Kết hợp các hệ số - nhân thêm hệ số góc nhận
    angle_factor = tx_angle_factor * rx_direction_factor
    
    # Tính cường độ cuối cùng
    sensitivity_factor = receiver.sensitivity / 50.0
    signal_strength = transmitter.strength * distance_factor * angle_factor * sensitivity_factor
    
    # THAY ĐỔI: Giảm ngưỡng tối thiểu
    min_threshold = 8  # Giảm từ 10 xuống 8
    if signal_strength < min_threshold:
        return 0
        
    # Debug hiển thị (nếu cần)
    if simulation.debug_mode and signal_strength > 50:  # Chỉ in debug cho tín hiệu mạnh
        print(f"Tín hiệu: {signal_strength:.1f}, Khoảng cách: {dist:.1f}, Góc TX: {angle_diff:.1f}°, Góc RX: {receiver_angle_diff:.1f}°")
    
    return max(0, min(100, signal_strength))

def adjust_strength_by_direction(transmitter, receiver, strength):
    """Điều chỉnh cường độ tín hiệu theo hướng phát và thu"""
    # Hệ số điều chỉnh mặc định
    return strength * 0.8