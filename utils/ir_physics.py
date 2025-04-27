import math
from utils.geometry import distance_between_points, check_line_of_sight

def calculate_ir_signal_strength(transmitter, receiver, simulation=None, tx_pos=None, rx_pos=None):
    """
    Tính toán cường độ tín hiệu IR từ transmitter đến receiver
    
    Args:
        transmitter: Đối tượng IRTransmitter
        receiver: Đối tượng IRReceiver
        simulation: Đối tượng Simulation chứa thông tin môi trường
        tx_pos: Vị trí của transmitter (tuple x,y), nếu None sẽ tự tính
        rx_pos: Vị trí của receiver (tuple x,y), nếu None sẽ tự tính
    
    Returns:
        float: Cường độ tín hiệu (0-100)
    """
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
    
    # Tính khoảng cách
    dist = distance_between_points(tx_pos, rx_pos)
    
    # Nếu khoảng cách quá lớn, không có tín hiệu
    if dist > transmitter.beam_distance:
        return 0
    
    # Kiểm tra line of sight
    obstacles = [] if simulation is None else simulation.obstacles
    if not check_line_of_sight(tx_pos, rx_pos, obstacles):
        return 0
    
    # Tính hướng chùm tia
    if simulation:
        tx_robot = next((r for r in simulation.robots if r.id == transmitter.robot_id), None)
        if tx_robot:
            beam_direction = transmitter.get_beam_direction(tx_robot.orientation)
        else:
            beam_direction = 0
    else:
        beam_direction = 0
    
    # Tính góc đến receiver
    dx = rx_pos[0] - tx_pos[0]
    dy = rx_pos[1] - tx_pos[1]
    angle_to_receiver = math.degrees(math.atan2(dy, dx))
    if angle_to_receiver < 0:
        angle_to_receiver += 360
    
    # Tính góc lệch
    angle_diff = min(abs(beam_direction - angle_to_receiver), 
                     360 - abs(beam_direction - angle_to_receiver))
    
    # Nếu nằm ngoài góc beam, không có tín hiệu
    if angle_diff > transmitter.beam_angle / 2:
        return 0
    
    # Tính giảm cường độ theo khoảng cách và góc - sử dụng công thức mới
    distance_factor = 1 - (dist / transmitter.beam_distance) ** 2
    
    # Cường độ theo góc dựa trên biểu đồ bức xạ - sử dụng hàm cos^2
    rel_angle_rad = math.radians(angle_diff)
    # Thay đổi công thức tính angle_factor để bo tròn hơn

    # Sử dụng hàm superellipse để tạo hình dạng bo tròn hơn
    n_superellipse = 2.5  # Tham số điều chỉnh độ bo tròn (>2)
    angle_ratio = abs(rel_angle_rad) / (math.radians(transmitter.beam_angle / 2))
    angle_factor = (1 - angle_ratio ** n_superellipse) ** (1/n_superellipse) * math.cos(rel_angle_rad * 0.7)
    angle_factor = max(0, angle_factor)  # Đảm bảo không âm
    
    # Điều chỉnh công thức tính angle_factor cho giống TSAL6200 hơn
    rel_angle_rad = math.radians(angle_diff)

    # Tăng hệ số superellipse để chùm tia hẹp hơn ở các cạnh
    n_superellipse = 4.0  # Tăng từ 2.5 lên 4.0 để tạo biên dạng nhọn hơn

    # Tính tỷ lệ góc chính xác hơn
    angle_ratio = abs(rel_angle_rad) / (math.radians(transmitter.beam_angle / 2))

    # Điều chỉnh công thức để tạo hình dạng kéo dài như TSAL6200
    # Giảm hệ số trong hàm cos để chùm tia kéo dài hơn
    angle_factor = (1 - angle_ratio ** n_superellipse) ** (1/n_superellipse) * math.cos(rel_angle_rad * 0.5)
    angle_factor = max(0, angle_factor)  # Đảm bảo không âm
    
    # Tính cường độ cuối cùng
    signal_strength = transmitter.strength * distance_factor * angle_factor
    
    return max(0, min(100, signal_strength))

def adjust_strength_by_direction(transmitter, receiver, strength):
    """Điều chỉnh cường độ tín hiệu theo hướng phát và thu"""
    # Hệ số điều chỉnh mặc định
    return strength * 0.8