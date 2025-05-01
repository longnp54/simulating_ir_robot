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
        obstacles: Danh sách các chướng ngại vật (hình chữ nhật hoặc đa giác)
    Returns:
        True nếu có đường line of sight, False nếu bị chặn
    """
    for obstacle in obstacles:
        # Nếu obstacle là list hoặc tuple của bốn giá trị (x, y, width, height)
        if isinstance(obstacle, (list, tuple)) and len(obstacle) == 4 and all(isinstance(val, (int, float)) for val in obstacle):
            if line_intersects_rectangle(p1, p2, obstacle):
                return False
        # Nếu obstacle là list của các điểm (đa giác)
        elif isinstance(obstacle, list) and all(isinstance(point, (list, tuple)) for point in obstacle):
            if line_intersects_polygon(p1, p2, obstacle):
                return False
    
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

def line_intersects_line(line1_start, line1_end, line2_start, line2_end):
    """Kiểm tra xem hai đoạn thẳng có giao nhau không"""
    # Tính các hệ số phương trình tham số
    x1, y1 = line1_start
    x2, y2 = line1_end
    x3, y3 = line2_start
    x4, y4 = line2_end
    
    # Kiểm tra giao điểm
    denominator = ((y4-y3) * (x2-x1) - (x4-x3) * (y2-y1))
    
    # Nếu đường thẳng song song
    if denominator == 0:
        return False
    
    # Tính tham số giao điểm
    ua = ((x4-x3) * (y1-y3) - (y4-y3) * (x1-x3)) / denominator
    ub = ((x2-x1) * (y1-y3) - (y2-y1) * (x1-x3)) / denominator
    
    # Kiểm tra nếu giao điểm nằm trên cả hai đoạn thẳng
    return (0 <= ua <= 1) and (0 <= ub <= 1)

def line_intersects_rectangle(line_start, line_end, rect):
    """Kiểm tra xem đoạn thẳng có giao với hình chữ nhật không"""
    x, y, width, height = rect
    
    # Bốn đỉnh của hình chữ nhật
    rect_points = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height)
    ]
    
    # Kiểm tra giao điểm với mỗi cạnh của hình chữ nhật
    for i in range(4):
        rect_line_start = rect_points[i]
        rect_line_end = rect_points[(i + 1) % 4]
        
        if line_intersects_line(line_start, line_end, rect_line_start, rect_line_end):
            return True
    
    return False

def line_intersects_polygon(line_start, line_end, polygon_points):
    """Kiểm tra xem đoạn thẳng có giao với đa giác không"""
    n = len(polygon_points)
    
    for i in range(n):
        polygon_line_start = polygon_points[i]
        polygon_line_end = polygon_points[(i + 1) % n]
        
        if line_intersects_line(line_start, line_end, polygon_line_start, polygon_line_end):
            return True
    
    return False