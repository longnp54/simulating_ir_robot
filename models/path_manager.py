import math
import time

class PathManager:
    """Quản lý đường đi và di chuyển theo waypoints"""
    
    def __init__(self, simulation):
        self.simulation = simulation
        self.waypoints = []  # Danh sách waypoints trong pixel
        self.waypoints_real = []  # Danh sách waypoints trong mét
        self.current_waypoint_index = 0
        self.active = False
        self.leader_id = None
        self.threshold_distance = 10  # Khoảng cách pixel để coi là đã đến waypoint
        self.move_speed = 0.02  # Mét mỗi bước di chuyển
        self.rotation_speed = 5  # Độ mỗi bước xoay
    
    def set_waypoints(self, waypoints):
        """Thiết lập đường đi mới"""
        self.waypoints = waypoints.copy()
        
        # Lưu trữ waypoints dưới dạng tọa độ thực (mét)
        self.waypoints_real = []
        for x, y in waypoints:
            real_x, real_y = self.simulation.pixel_to_real(x, y)
            self.waypoints_real.append((real_x, real_y))
            
        self.current_waypoint_index = 0
        print(f"Đã thiết lập đường đi với {len(waypoints)} điểm")

    def update_waypoints_from_scale(self):
        """Cập nhật lại tọa độ waypoints dựa trên tỷ lệ hiện tại"""
        self.waypoints = []
        for real_x, real_y in self.waypoints_real:
            pixel_x, pixel_y = self.simulation.real_to_pixel(real_x, real_y)
            self.waypoints.append((pixel_x, pixel_y))
    
    def start(self, leader_id=None):
        """Bắt đầu di chuyển theo đường đi"""
        if not self.waypoints:
            print("Không có đường đi. Vui lòng thiết lập trước.")
            return False
        
        if leader_id is not None:
            self.leader_id = leader_id
        
        if self.leader_id is None:
            print("Chưa chọn robot dẫn đầu")
            return False
        
        self.active = True
        self.current_waypoint_index = 0
        print(f"Bắt đầu di chuyển robot {self.leader_id} theo đường đi")
        return True
    
    def stop(self):
        """Dừng di chuyển theo đường đi"""
        self.active = False
        print("Đã dừng di chuyển theo đường đi")
    
    def update(self):
        """Cập nhật vị trí robot dẫn đầu theo đường đi"""
        if not self.active or self.current_waypoint_index >= len(self.waypoints):
            return
        
        leader = self.simulation.get_robot_by_id(self.leader_id)
        if not leader:
            print(f"Không tìm thấy robot ID {self.leader_id}")
            self.active = False
            return
        
        # Lấy waypoint hiện tại
        target_x, target_y = self.waypoints[self.current_waypoint_index]
        
        # Tính khoảng cách từ robot đến waypoint
        dx = target_x - leader.x
        dy = target_y - leader.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Hiển thị thông tin tiến trình di chuyển (thêm vào)
        if hasattr(self, 'last_report_time') and time.time() - self.last_report_time < 1.0:
            # Chỉ báo cáo mỗi giây để tránh spam console
            pass
        else:
            print(f"Robot {self.leader_id} đang di chuyển đến điểm {self.current_waypoint_index+1}/{len(self.waypoints)}")
            print(f"  - Khoảng cách đến điểm tiếp theo: {distance:.1f} pixel ({self.simulation.pixel_distance_to_real(distance):.2f}m)")
            self.last_report_time = time.time()
        
        if distance < self.threshold_distance:
            # Đã đến waypoint, chuyển sang waypoint tiếp theo
            print(f"✓ Robot {self.leader_id} đã đến điểm {self.current_waypoint_index+1}")
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.waypoints):
                print("✓ Đã hoàn thành toàn bộ đường đi!")
                self.active = False
                return
        else:
            # Tính góc từ robot đến waypoint
            angle = math.degrees(math.atan2(dy, dx))
            
            # Tính góc lệch cần xoay
            angle_diff = (angle - leader.orientation) % 360
            if angle_diff > 180:
                angle_diff -= 360
            
            # In thông tin góc
            print(f"  - Góc mục tiêu: {angle:.1f}°, Góc lệch: {angle_diff:.1f}°")
            
            # Xoay robot nếu cần
            if abs(angle_diff) > 5:
                rotation = min(abs(angle_diff), self.rotation_speed) * (1 if angle_diff > 0 else -1)
                leader.rotate(rotation)
                print(f"  - Xoay {rotation:.1f}°")
            else:
                # Di chuyển về phía waypoint
                move_dist = min(self.move_speed, distance/self.simulation.scale)
                leader.move_forward(move_dist)
                print(f"  - Di chuyển về phía trước {move_dist:.3f}m")