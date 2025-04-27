import math

def distance_between_points(p1, p2):
    """Tính khoảng cách giữa hai điểm"""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

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