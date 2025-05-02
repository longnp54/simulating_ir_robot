import threading
import time
import math

class FollowManager:
    """Quản lý kịch bản robot di chuyển theo nhau"""
    
    def __init__(self, simulation):
        self.simulation = simulation
        self.running = False
        self.follow_thread = None
        
        # Thiết lập theo dõi
        self.follow_chain = []  # Danh sách ID robot theo thứ tự follow
        self.follow_distance = 0.5  # Khoảng cách giữa các robot (m)
        self.speed = 5  # Tốc độ di chuyển (đơn vị/update)
        
        # Dữ liệu điều khiển robot dẫn đầu
        self.leader_auto_move = False  # Tự động di chuyển robot dẫn đầu
        self.waypoints = []  # Các điểm mà robot dẫn đầu sẽ đi qua
        self.current_waypoint = 0
    
    def set_follow_chain(self, robot_ids):
        """Thiết lập chuỗi robot follow nhau"""
        self.follow_chain = robot_ids.copy()
    
    def set_follow_distance(self, distance):
        """Thiết lập khoảng cách giữa các robot"""
        self.follow_distance = distance
    
    def start(self):
        """Bắt đầu kịch bản follow"""
        if self.running or len(self.follow_chain) < 2:
            return False
        
        self.running = True
        self.follow_thread = threading.Thread(target=self._follow_loop)
        self.follow_thread.daemon = True
        self.follow_thread.start()
        return True
    
    def stop(self):
        """Dừng kịch bản follow"""
        self.running = False
        if self.follow_thread:
            self.follow_thread.join(timeout=1.0)
            self.follow_thread = None
    
    def _follow_loop(self):
        """Vòng lặp chính để thực hiện di chuyển follow"""
        try:
            while self.running:
                # Lấy danh sách robot hiện tại
                robots = {r.id: r for r in self.simulation.robots}
                
                # Kiểm tra xem tất cả các robot trong chuỗi có tồn tại không
                for robot_id in self.follow_chain:
                    if robot_id not in robots:
                        print(f"Robot {robot_id} không tồn tại, dừng kịch bản follow.")
                        self.running = False
                        return
                
                # Di chuyển leader (nếu bật tự động)
                if self.leader_auto_move and self.waypoints:
                    leader_id = self.follow_chain[0]
                    leader = robots[leader_id]
                    target = self.waypoints[self.current_waypoint]
                    
                    # Di chuyển leader đến waypoint hiện tại
                    done = self._move_to_point(leader, target[0], target[1])
                    
                    # Nếu đã đến waypoint, chuyển đến waypoint tiếp theo
                    if done:
                        self.current_waypoint = (self.current_waypoint + 1) % len(self.waypoints)
                
                # Xử lý di chuyển follow cho các robot còn lại
                for i in range(1, len(self.follow_chain)):
                    follower_id = self.follow_chain[i]
                    leader_id = self.follow_chain[i-1]
                    
                    follower = robots[follower_id]
                    leader = robots[leader_id]
                    
                    # Di chuyển follower để follow robot trước nó
                    self._follow_robot(follower, leader)
                
                time.sleep(0.05)  # Đợi một chút trước lần cập nhật tiếp theo
                
        except Exception as e:
            print(f"Lỗi trong kịch bản follow: {e}")
    
    def _follow_robot(self, follower, leader):
        """Điều khiển robot follower di chuyển theo sau robot leader"""
        # Tính toán vị trí mục tiêu phía sau leader
        follow_distance_px = self.simulation.meters_to_pixels(self.follow_distance)
        
        # Tính vị trí đích ở phía sau robot leader
        angle_rad = math.radians(leader.orientation + 180)  # 180 độ so với hướng của leader
        target_x = leader.x - math.cos(angle_rad) * follow_distance_px
        target_y = leader.y - math.sin(angle_rad) * follow_distance_px
        
        # Di chuyển follower đến vị trí này
        self._move_to_point(follower, target_x, target_y)
    
    def _move_to_point(self, robot, target_x, target_y):
        """Di chuyển robot đến điểm đích, trả về True nếu đã đến nơi"""
        # Tính vector hướng đến mục tiêu
        dx = target_x - robot.x
        dy = target_y - robot.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Nếu đã đến đủ gần điểm đích
        if distance < 5:
            return True
        
        # Tính góc hướng đến mục tiêu
        target_angle = math.degrees(math.atan2(dy, dx)) % 360
        
        # Tính góc chênh lệch cần xoay
        current_angle = robot.orientation
        angle_diff = (target_angle - current_angle + 180) % 360 - 180
        
        # Xoay robot để hướng về mục tiêu
        if abs(angle_diff) > 5:
            rotation = min(2, max(-2, angle_diff))  # Giới hạn tốc độ xoay
            robot.rotate(rotation)
            return False  # Chưa đến mục tiêu
        
        # Di chuyển về phía trước với tốc độ phù hợp
        move_distance = min(self.speed, distance)
        move_x = move_distance * math.cos(math.radians(current_angle))
        move_y = move_distance * math.sin(math.radians(current_angle))
        
        robot.move(move_x, move_y)
        return False  # Chưa đến mục tiêu
    
    def set_waypoints(self, waypoints):
        """Thiết lập các điểm mà robot dẫn đầu sẽ đi qua"""
        self.waypoints = waypoints
        self.current_waypoint = 0
    
    def enable_leader_auto_movement(self, enable=True):
        """Bật/tắt tự động di chuyển robot dẫn đầu"""
        self.leader_auto_move = enable
        
        if enable and not self.waypoints:
            # Tạo mặc định một đường tròn nếu chưa có waypoints
            center_x, center_y = 400, 300  # Giả sử là tâm của canvas
            radius = 150
            points = []
            for angle in range(0, 360, 45):  # 8 điểm trên đường tròn
                rad = math.radians(angle)
                x = center_x + radius * math.cos(rad)
                y = center_y + radius * math.sin(rad)
                points.append((x, y))
            self.set_waypoints(points)