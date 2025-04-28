import math

def distance_between_points(p1, p2=None, y1=None, y2=None):
    """Tính khoảng cách giữa hai điểm
    
    Có thể gọi theo hai cách:
    - distance_between_points(p1, p2) với p1, p2 là các tuple (x, y)
    - distance_between_points(x1, y1, x2, y2) với x1, y1, x2, y2 là các tọa độ đơn
    """
    # Xử lý trường hợp gọi với 4 tham số: (x1, y1, x2, y2)
    if p2 is not None and y1 is not None and y2 is not None:
        x1, x2, y1, y2 = p1, p2, y1, y2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    # Xử lý trường hợp gọi với 2 điểm: (p1, p2)
    elif p2 is not None:
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    # Trường hợp không hợp lệ
    else:
        raise ValueError("Phải có đủ thông số để tính khoảng cách!")

def check_line_of_sight(p1, p2, obstacles):
    """Kiểm tra đường line of sight giữa hai điểm
    
    Args:
        p1: Tọa độ điểm 1 (x, y)
        p2: Tọa độ điểm 2 (x, y)
        obstacles: Danh sách các chướng ngại vật (không dùng trong phiên bản hiện tại)
    Returns:
        True nếu có đường line of sight, False nếu bị chặn
    """
    # Trong phiên bản đơn giản, không có chướng ngại vật
    return True

def calculate_angle(p1, p2):
    """Tính góc giữa hai điểm (theo độ, 0-360)"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # Chuyển về thang 0-360
    angle_deg = (angle_deg + 360) % 360
    
    return angle_deg