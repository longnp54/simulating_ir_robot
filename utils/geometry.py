import math

def distance_between_points(p1, p2=None, y1=None, y2=None):
    """Calculate distance between two points
    
    Can be called in two ways:
    - distance_between_points(p1, p2) with p1, p2 as tuples (x, y)
    - distance_between_points(x1, y1, x2, y2) with x1, y1, x2, y2 as individual coordinates
    """
    # Handle case with 4 parameters: (x1, y1, x2, y2)
    if p2 is not None and y1 is not None and y2 is not None:
        x1, x2, y1, y2 = p1, p2, y1, y2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    # Handle case with 2 points: (p1, p2)
    elif p2 is not None:
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    # Invalid case
    else:
        raise ValueError("Must have sufficient parameters to calculate distance!")

def check_line_of_sight(p1, p2, obstacles):
    """Check line of sight between two points
    
    Args:
        p1: Coordinates of point 1 (x, y)
        p2: Coordinates of point 2 (x, y)
        obstacles: List of obstacles (rectangles or polygons)
    Returns:
        True if line of sight exists, False if blocked
    """
    for obstacle in obstacles:
        # If obstacle is list or tuple of four values (x, y, width, height)
        if isinstance(obstacle, (list, tuple)) and len(obstacle) == 4 and all(isinstance(val, (int, float)) for val in obstacle):
            if line_intersects_rectangle(p1, p2, obstacle):
                return False
        # If obstacle is list of points (polygon)
        elif isinstance(obstacle, list) and all(isinstance(point, (list, tuple)) for point in obstacle):
            if line_intersects_polygon(p1, p2, obstacle):
                return False
    
    return True

def calculate_angle(p1, p2):
    """Calculate angle between two points (in degrees, 0-360)"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # Convert to 0-360 range
    angle_deg = (angle_deg + 360) % 360
    
    return angle_deg

def line_intersects_line(line1_start, line1_end, line2_start, line2_end):
    """Check if two line segments intersect"""
    # Calculate parametric equation coefficients
    x1, y1 = line1_start
    x2, y2 = line1_end
    x3, y3 = line2_start
    x4, y4 = line2_end
    
    # Check intersection point
    denominator = ((y4-y3) * (x2-x1) - (x4-x3) * (y2-y1))
    
    # If lines are parallel
    if denominator == 0:
        return False
    
    # Calculate intersection parameters
    ua = ((x4-x3) * (y1-y3) - (y4-y3) * (x1-x3)) / denominator
    ub = ((x2-x1) * (y1-y3) - (y2-y1) * (x1-x3)) / denominator
    
    # Check if intersection point lies on both line segments
    return (0 <= ua <= 1) and (0 <= ub <= 1)

def line_intersects_rectangle(line_start, line_end, rect):
    """Check if line segment intersects with rectangle"""
    x, y, width, height = rect
    
    # Four vertices of rectangle
    rect_points = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height)
    ]
    
    # Check intersection with each edge of rectangle
    for i in range(4):
        rect_line_start = rect_points[i]
        rect_line_end = rect_points[(i + 1) % 4]
        
        if line_intersects_line(line_start, line_end, rect_line_start, rect_line_end):
            return True
    
    return False

def line_intersects_polygon(line_start, line_end, polygon_points):
    """Check if line segment intersects with polygon"""
    n = len(polygon_points)
    
    for i in range(n):
        polygon_line_start = polygon_points[i]
        polygon_line_end = polygon_points[(i + 1) % n]
        
        if line_intersects_line(line_start, line_end, polygon_line_start, polygon_line_end):
            return True
    
    return False