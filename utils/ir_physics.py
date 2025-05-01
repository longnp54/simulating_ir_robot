import math
import random
import numpy as np
from utils.geometry import distance_between_points, check_line_of_sight

def calculate_ir_signal_strength(transmitter, receiver, simulation=None, tx_pos=None, rx_pos=None):
    """Tính cường độ tín hiệu IR giữa transmitter và receiver"""
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
    dist_pixel = distance_between_points(tx_pos, rx_pos)
    
    # Chuyển đổi khoảng cách từ pixel sang mét
    dist_meter = dist_pixel / simulation.scale if simulation else dist_pixel / 250
    
    # Kiểm tra khoảng cách tối đa
    if dist_pixel > transmitter.beam_distance:
        return 0
    
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
    
    # Tính góc lệch giữa hướng phát và hướng đến receiver
    angle_diff = abs((beam_direction - angle_to_receiver + 180) % 360 - 180)
    
    # Nếu nằm ngoài góc phát, không có tín hiệu
    if angle_diff > transmitter.beam_angle / 2:
        return 0
    
    # Tính góc lệch phát theo radian và tỷ lệ góc
    angle_ratio = angle_diff / (transmitter.beam_angle / 2)
    
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
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # Góc nhận tối đa
    max_reception_angle = receiver.viewing_angle
    
    # Nếu nằm ngoài góc nhận, không có tín hiệu
    if receiver_angle_diff > max_reception_angle / 2:
        return 0
    
    # Tính hệ số góc phát và nhận
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    
    # ---------- CHỈ SỬ DỤNG MÔ HÌNH PATHLOSS ----------
    # Áp dụng mô hình pathloss
    path_loss = calculate_pathloss(
        distance=dist_meter,
        frequency=940e9,  # IR thường ~940nm
        path_loss_exponent=2.0,  # Không gian tự do
        shadow_fading_std=1.5     # Giảm shadow fading để tín hiệu đều hơn
    )
    
    # Chuyển đổi pathloss sang hệ số suy giảm tín hiệu (0-1)
    distance_factor = 10 ** (-path_loss / 10)
    
    # Giới hạn distance_factor không âm
    distance_factor = max(0, min(1, distance_factor))
    
    # Kết hợp các hệ số - chỉ dùng pathloss cho suy giảm khoảng cách
    combined_factor = distance_factor * tx_angle_factor * rx_angle_factor
    
    # Tính cường độ tín hiệu cuối cùng
    sensitivity_factor = receiver.sensitivity / 40.0
    signal_strength = transmitter.strength * combined_factor * sensitivity_factor
    
    # Thêm vào calculate_ir_signal_strength
    print(f"Distance: {dist_meter}m, Raw signal: {transmitter.strength * distance_factor * tx_angle_factor * rx_angle_factor}")
    
    # Kiểm tra ngưỡng
    min_threshold = 3  # Thay vì 8 hoặc 5
    if signal_strength < min_threshold:
        return 0
    
    return max(0, min(100, signal_strength))

def adjust_strength_by_direction(transmitter, receiver, strength):
    """Điều chỉnh cường độ tín hiệu theo hướng phát và thu"""
    # Hệ số điều chỉnh mặc định
    return strength * 0.8

def calculate_ir_signal_strength_rician(transmitter, receiver, simulation, tx_pos=None, rx_pos=None):
    """Tính cường độ tín hiệu IR sử dụng mô hình Rician (có LOS và NLOS)"""
    # Lấy vị trí phát/nhận nếu chưa được cung cấp
    if tx_pos is None or rx_pos is None:
        tx_robot = simulation.get_robot_by_id(transmitter.robot_id)
        rx_robot = simulation.get_robot_by_id(receiver.robot_id)
        
        if tx_robot is None or rx_robot is None:
            return 0
        
        tx_pos = transmitter.get_position(tx_robot.x, tx_robot.y, tx_robot.size, tx_robot.orientation)
        rx_pos = receiver.get_position(rx_robot.x, rx_robot.y, rx_robot.size, rx_robot.orientation)
    
    # Tính khoảng cách
    dist = distance_between_points(tx_pos, rx_pos)
    
    # Giới hạn tối đa
    if dist > transmitter.beam_distance:
        return 0
    
    # Tính các góc phát và nhận
    # Góc phát - từ transmitter đến receiver
    angle_to_receiver = math.degrees(math.atan2(rx_pos[1] - tx_pos[1], rx_pos[0] - tx_pos[0]))
    if angle_to_receiver < 0:
        angle_to_receiver += 360
    transmitter_direction = transmitter.get_beam_direction(simulation.get_robot_by_id(transmitter.robot_id).orientation)
    angle_diff = abs((transmitter_direction - angle_to_receiver + 180) % 360 - 180)
    
    # Góc nhận - từ receiver đến transmitter
    # Calculate the angle from receiver to transmitter
    dx = tx_pos[0] - rx_pos[0]
    dy = tx_pos[1] - rx_pos[1]
    angle_to_transmitter = math.degrees(math.atan2(dy, dx))
    if angle_to_transmitter < 0:
        angle_to_transmitter += 360
    receiver_direction = receiver.get_viewing_direction(simulation.get_robot_by_id(receiver.robot_id).orientation)
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # Kiểm tra nếu nằm trong góc phát và góc nhận
    if angle_diff > transmitter.beam_angle / 2 or receiver_angle_diff > receiver.viewing_angle / 2:
        return 0
    
    # Kiểm tra LOS - thu thập chướng ngại vật
    obstacles = []
    for robot in simulation.robots:
        if robot.id != transmitter.robot_id and robot.id != receiver.robot_id:
            # Tạo đa giác từ vị trí robot
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
    
    # Kiểm tra line of sight
    has_los = check_line_of_sight(tx_pos, rx_pos, obstacles)
    
    # Xác định K-factor dựa trên LOS
    k_factor = 0.0 if has_los else 0.5
    
    # Tính thành phần LOS (trực tiếp)
    los_power = k_factor/(k_factor+1) * transmitter.strength * math.exp(-(dist/transmitter.beam_distance) * 0.8)  # 1.2 -> 0.8
    
    # Tính thành phần NLOS (tán xạ)
    nlos_power = 1 / (k_factor + 1) * transmitter.strength * math.exp(-(dist / transmitter.beam_distance) * 1.6)  # 1.8 -> 1.6 
    
    # Thêm đặc tính góc vào tín hiệu
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    angle_factor = tx_angle_factor * rx_angle_factor
    
    # Kết hợp tín hiệu LOS và NLOS theo mô hình Rician
    signal_strength = (los_power + nlos_power) * angle_factor
    
    # Thêm nhiễu ngẫu nhiên (đặc tính của kênh truyền vô tuyến)
    noise_factor = 1.0 + random.uniform(-0.1, 0.1)
    signal_strength *= noise_factor
    
    # Ngưỡng tối thiểu
    if signal_strength < 8:
        return 0
        
    return min(signal_strength, 100)  # Giới hạn tín hiệu tối đa là 100

def calculate_pathloss(distance, frequency=940e9, path_loss_exponent=1.6, shadow_fading_std=0.1):
    """
    Tính toán suy giảm tín hiệu dựa trên mô hình pathloss (đã điều chỉnh)
    
    Args:
        distance: Khoảng cách giữa transmitter và receiver (m)
        frequency: Tần số của tín hiệu IR (Hz), mặc định là 940 THz
        path_loss_exponent: Giảm từ 2.0 xuống 1.6 để tín hiệu đi xa hơn
        shadow_fading_std: Giảm từ 0.5 xuống 0.1 để giảm hiệu ứng ngẫu nhiên
    """
    # Tính bước sóng (λ) từ tần số
    c = 3e8  # Vận tốc ánh sáng (m/s)
    wavelength = c / frequency
    
    # Tăng khoảng cách tham chiếu để giảm suy hao ban đầu
    reference_distance = 0.2  # Tăng từ 0.1 lên 0.2
    
    # Giảm suy hao cơ bản
    if distance <= reference_distance:
        return 0  # Không suy hao khi quá gần
    
    # Tính pathloss tại khoảng cách tham chiếu (giảm hệ số)
    fspl_ref = 20 * math.log10(4 * math.pi * reference_distance / wavelength)  # Giảm từ 20 xuống 15
    
    # Tính pathloss tại khoảng cách thực tế với hệ số suy giảm thấp hơn
    path_loss = fspl_ref + 10 * path_loss_exponent * math.log10(distance / reference_distance)
    
    # Giảm shadow fading (giảm yếu tố ngẫu nhiên)
    if shadow_fading_std > 0:
        shadow_fading = np.random.normal(0, shadow_fading_std)
        path_loss += shadow_fading
    
    return path_loss * 0.8  # Giảm thêm 20% suy hao tổng thể

# Chuyển đổi pathloss (dB) sang hệ số suy giảm cường độ
def pathloss_to_signal_factor(path_loss):
    """Chuyển đổi pathloss (dB) sang hệ số suy giảm cường độ (0-1)"""
    # Ánh xạ pathloss từ dB sang hệ số tuyến tính
    # pathloss = -10 * log10(power_ratio) => power_ratio = 10^(-pathloss/10)
    return 10 ** (-path_loss / 10)

# Hàm chung tính toán pathloss để đồng bộ giữa hai mục
def calculate_pathloss_rician(distance, has_los=True, frequency=940e9, shadow_fading_std=0.1):
    """
    Tính toán suy hao tín hiệu sử dụng mô hình pathloss theo công thức:
    L(d) = L(d₀) + 10n·log(d/d₀)
    """
    # Tính bước sóng
    c = 3e8  # Vận tốc ánh sáng
    wavelength = c / frequency
    
    # Khoảng cách tham chiếu d₀ = 1m (theo chuẩn)
    reference_distance = 1.0
    
    # Không suy hao khi quá gần
    if distance <= 0.05:  # 5cm
        return 0
        
    # Tính L(d₀) - suy hao tại khoảng cách tham chiếu
    # Công thức: L(d₀) = 20·log₁₀(4π·d₀/λ)
    L_d0 = 20 * math.log10(4 * math.pi * reference_distance / wavelength)
    
    # Chọn hệ số suy giảm đường truyền n phù hợp với môi trường
    # và tùy chỉnh theo khoảng cách
    if distance < 0.2:  # Gần (dưới 20cm)
        path_loss_exponent = 1.8 if has_los else 2.5
    elif distance < 0.5:  # Trung bình (20-50cm)
        path_loss_exponent = 2.0 if has_los else 3.0
    else:  # Xa (trên 50cm)
        path_loss_exponent = 2.5 if has_los else 3.5
    
    # Áp dụng công thức pathloss: L(d) = L(d₀) + 10n·log₁₀(d/d₀)
    path_loss = L_d0 + 10 * path_loss_exponent * math.log10(distance / reference_distance)
    
    # Thêm hiệu ứng shadow fading (suy hao do chướng ngại vật)
    if shadow_fading_std > 0:
        shadow_fading = np.random.normal(0, shadow_fading_std)
        path_loss += shadow_fading
    
    # Áp dụng hệ số giảm suy hao để tín hiệu đi xa hơn trong môi trường mô phỏng
    # Giá trị này có thể điều chỉnh để khớp với kết quả mong muốn
    attenuation_factor = 0.6 if has_los else 0.8
    
    return path_loss * attenuation_factor

# Hàm tính tín hiệu từ khoảng cách (hướng từ khoảng cách -> tín hiệu)
def distance_to_signal_strength(distance, tx_strength, rx_sensitivity, k_factor, angle_factor, has_los=True):
    """
    Tính cường độ tín hiệu từ khoảng cách dựa trên mô hình Pathloss-Rician
    """
    # Nếu khoảng cách rất gần, trả về tín hiệu mạnh
    if distance <= 0.05:  # Dưới 5cm
        return tx_strength * angle_factor * (rx_sensitivity / 50.0) * 0.95
    
    # THÊM VÀO: Đảm bảo khoảng cách gần reference_distance có tín hiệu tối thiểu
    if distance < 0.25:  # Trong khoảng 5cm đến 25cm
        min_signal = 15 + (0.25 - distance) * 200  # Tín hiệu tối thiểu giảm dần từ 55 đến 15
        
    # Tính pathloss với tham số đã điều chỉnh
    path_loss = calculate_pathloss_rician(distance, has_los)
    
    # Chuyển đổi từ pathloss sang hệ số suy giảm (0-1)
    path_loss_factor = 10 ** (-path_loss / 10)
    
    # Tăng k_factor để tạo tín hiệu mạnh hơn khi có LOS
    k_factor = 12.0 if has_los else 0.8  # Tăng từ 10.0 lên 12.0 cho LOS
    
    # Thành phần LOS và NLOS theo mô hình Rician
    los_factor = k_factor / (k_factor + 1)
    nlos_factor = 1 / (k_factor + 1)
    
    # Tính cường độ tín hiệu
    los_component = los_factor * tx_strength * path_loss_factor
    nlos_component = nlos_factor * tx_strength * path_loss_factor * 0.8  # NLOS yếu hơn 20%
    
    signal_strength = (los_component + nlos_component) * angle_factor * (rx_sensitivity / 50.0)
    
    # THÊM VÀO: Áp dụng ngưỡng tối thiểu cho khoảng cách gần
    if distance < 0.25:  # Trong khoảng 25cm
        signal_strength = max(signal_strength, min_signal)
    
    return min(100, max(0, signal_strength))

# Hàm ước lượng khoảng cách từ tín hiệu (hướng từ tín hiệu -> khoảng cách)
def signal_strength_to_distance(signal_strength, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Ước lượng khoảng cách từ cường độ tín hiệu dựa trên mô hình nghịch đảo của Pathloss-Rician
    """
    # Loại bỏ ảnh hưởng của góc và độ nhạy
    normalized_signal = signal_strength / ((rx_sensitivity / 50.0) * angle_factor)
    
    # K-factor dựa trên LOS/NLOS
    k_factor = 6.0 if has_los else 0.5
    
    # Hệ số điều chỉnh dựa trên LOS/NLOS
    los_factor = 0.9 if has_los else 1.2
    
    # Tính toán nghịch đảo của pathloss
    if normalized_signal <= 0:
        return float('inf')  # Không thể ước lượng khoảng cách
        
    # Tỷ lệ tín hiệu so với tín hiệu gốc
    signal_ratio = normalized_signal / tx_strength
    
    # Chuyển đổi tỷ lệ tín hiệu thành suy hao đường truyền
    estimated_path_loss = -10 * math.log10(signal_ratio) / 0.8
    
    # Tham số tính ngược khoảng cách
    c = 3e8
    frequency = 940e9
    wavelength = c / frequency
    reference_distance = 0.2
    path_loss_exponent = 1.8 * los_factor
    
    # Suy hao cơ bản tại khoảng cách tham chiếu
    fspl_ref = 15 * math.log10(4 * math.pi * reference_distance / wavelength)
    
    # Tính khoảng cách từ pathloss
    path_loss_diff = estimated_path_loss - fspl_ref
    if path_loss_diff <= 0:
        return reference_distance
        
    distance = reference_distance * 10 ** (path_loss_diff / (10 * path_loss_exponent))
    
    return distance

def distance_to_signal_strength_rician(distance, beam_distance, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Tính cường độ tín hiệu với suy giảm đều theo chiều dài beam và mô hình Rician
    
    Args:
        distance: Khoảng cách thực tế (m)
        beam_distance: Chiều dài tối đa của beam (m)
        tx_strength: Cường độ phát ban đầu (0-100)
        rx_sensitivity: Độ nhạy của đầu thu (0-100)
        angle_factor: Hệ số góc phát-nhận (0-1)
        has_los: Có đường truyền trực tiếp hay không
    
    Returns:
        Cường độ tín hiệu (0-100)
    """
    # Khi khoảng cách vượt quá beam_distance, không có tín hiệu
    if distance >= beam_distance:
        return 0
    
    # Xử lý đặc biệt cho khoảng cách rất gần (≤ 10cm)
    if distance <= 0.10:
        return tx_strength * angle_factor * (rx_sensitivity / 40.0)  # Tăng độ nhạy bằng cách giảm từ 45.0 xuống 40.0
    
    # === THAY ĐỔI CHÍNH: Sử dụng công thức suy giảm tuyến tính đơn giản theo % chiều dài beam ===
    
    # 1. Tính tỷ lệ % khoảng cách so với chiều dài beam
    distance_ratio = distance / beam_distance  # 0 = gốc beam, 1 = cuối beam
    
    # 2. Áp dụng công thức suy giảm tuyến tính đơn giản
    # Tín hiệu = 100% - (% khoảng cách)^0.6
    # Mũ 0.6 khiến suy giảm chậm hơn mũ 1.0 (tuyến tính)
    # Giảm từ 0.8 xuống 0.6 để suy giảm còn chậm hơn nữa
    signal_factor = (1.0 - distance_ratio) ** 0.6
    
    # 3. Áp dụng mô hình Rician đơn giản hóa chỉ để tạo nhiễu nhẹ
    k_factor = 10.0 if has_los else 0.5
    los_factor = k_factor / (k_factor + 1.0)
    nlos_factor = 1.0 / (k_factor + 1.0)
    
    # 4. Tính thành phần tín hiệu chính
    # Đơn giản hóa, không có sự khác biệt lớn giữa LOS và NLOS
    los_component = los_factor * tx_strength * signal_factor
    nlos_component = nlos_factor * tx_strength * signal_factor * 0.95  # NLOS chỉ yếu hơn 5%
    
    # 5. Kết hợp LOS và NLOS
    # Tăng hệ số nhạy bằng cách giảm mẫu số từ 45.0 xuống 40.0
    signal_strength = (los_component + nlos_component) * angle_factor * (rx_sensitivity / 40.0)
    
    # 6. Thêm nhiễu ngẫu nhiên rất nhỏ để tự nhiên hơn
    noise = random.uniform(-0.5, 0.5) if has_los else random.uniform(-1, 1)
    signal_strength += noise
    
    # 7. Đảm bảo khoảng cách rất gần luôn có tín hiệu mạnh
    # Thay vì dùng nhiều ngưỡng, sử dụng một công thức mượt hơn
    if distance_ratio < 0.3:  # 30% đầu của beam
        min_signal = 100 - (distance_ratio / 0.3) * 50  # Từ 100 xuống 50
        signal_strength = max(signal_strength, min_signal)
    
    return min(100, max(0, signal_strength))

def signal_strength_to_distance_rician(signal_strength, beam_distance, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Ước lượng khoảng cách từ cường độ tín hiệu dựa trên mô hình nghịch đảo
    
    Args:
        signal_strength: Cường độ tín hiệu đo được (0-100)
        beam_distance: Chiều dài tối đa của beam (m)
        tx_strength: Cường độ phát ban đầu (0-100)
        rx_sensitivity: Độ nhạy của đầu thu (0-100)
        angle_factor: Hệ số góc phát-nhận (0-1)
        has_los: Có đường truyền trực tiếp hay không
    
    Returns:
        Khoảng cách ước tính (m)
    """
    # Trường hợp đặc biệt - tín hiệu quá yếu hoặc quá mạnh
    if signal_strength <= 1:
        return beam_distance * 0.95  # Gần như bằng beam_distance
    elif signal_strength >= 95:  # Rất gần nguồn phát
        return 0.05
    
    # Loại bỏ ảnh hưởng của nhiễu và điều chỉnh độ nhạy
    normalized_signal = signal_strength / (angle_factor * (rx_sensitivity / 50.0))
    los_factor = 1.0 if has_los else 0.7
    normalized_signal = normalized_signal / (los_factor * tx_strength)
    
    # Giải phương trình ngược để tìm khoảng cách
    # Chia thành các khoảng để phản ánh sự suy giảm không đều của tín hiệu
    if normalized_signal > 0.7:  # Tín hiệu mạnh - khoảng gần
        # Đảo ngược hàm lũy thừa 0.7
        distance_factor = normalized_signal ** (1/0.7)
        distance = beam_distance * (1.0 - distance_factor)
    elif normalized_signal > 0.3:  # Tín hiệu trung bình - khoảng giữa
        # Đảo ngược hàm tuyến tính
        distance_factor = normalized_signal
        distance = beam_distance * (1.0 - distance_factor)
    else:  # Tín hiệu yếu - khoảng xa
        # Đảo ngược hàm lũy thừa 1.5
        distance_factor = normalized_signal ** (1/1.5)
        distance = beam_distance * (1.0 - distance_factor)
    
    # Thêm nhiễu ngẫu nhiên nhỏ
    noise_factor = random.uniform(0.95, 1.05)
    distance *= noise_factor
    
    # Đảm bảo khoảng cách nằm trong giới hạn hợp lý
    return max(0.05, min(beam_distance, distance))