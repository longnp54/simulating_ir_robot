import time
import threading
from models.robot import Robot
from utils.ir_physics import calculate_ir_signal_strength
from models.ir_sensor import can_receive_signal  # Thêm dòng này

class Simulation:
    def __init__(self):
        self.robots = []
        self.obstacles = []
        self.running = False
        self.simulation_thread = None
        self.next_robot_id = 1
        
        # Kích thước môi trường thật (m)
        self.real_width = 4.0  # 4m
        self.real_height = 4.0  # 4m
        
        # Kích thước robot thật (m)
        self.real_robot_size = 0.1  # 10cm
        
        # Tỉ lệ chuyển đổi từ m sang pixel
        self.scale = 250  # Tăng từ 150 lên 250 pixel/m

        self.debug_mode = False  # Thay đổi từ True thành False
    
    def add_robot(self, x=100, y=100, orientation=0):
        """Thêm robot mới vào mô phỏng"""
        robot = Robot(self.next_robot_id, x, y, orientation)
        # Đặt kích thước robot theo tỉ lệ
        robot.size = self.real_robot_size * self.scale
        robot.simulation = self  # Đặt tham chiếu đến simulation
        self.robots.append(robot)
        self.next_robot_id += 1

        return robot
    
    def remove_robot(self, robot_id=None):
        """Xóa robot khỏi mô phỏng"""
        if robot_id is None and self.robots:
            self.robots.pop()  # Xóa robot cuối cùng nếu không chỉ định ID
            return True
        
        for i, robot in enumerate(self.robots):
            if robot.id == robot_id:
                self.robots.pop(i)
                return True
        return False
    
    def start(self):
        """Bắt đầu mô phỏng"""
        if not self.running:
            # Xóa tất cả tín hiệu trước khi bắt đầu
            for robot in self.robots:
                for receiver in robot.receivers:
                    receiver.clear_signals()
                    
            self.running = True
            try:
                self.simulation_thread = threading.Thread(target=self.run_simulation)
                self.simulation_thread.daemon = True
                self.simulation_thread.start()
            except Exception as e:
                print(f"Lỗi khi khởi tạo thread mô phỏng: {e}")
                self.running = False
    
    def stop(self):
        """Dừng mô phỏng"""
        self.running = False
        if self.simulation_thread:
            try:
                # Tăng timeout cho thread join
                self.simulation_thread.join(timeout=3.0)
                if self.simulation_thread.is_alive():
                    print("Cảnh báo: Thread mô phỏng không dừng được. Tiếp tục...")
            except Exception as e:
                print(f"Lỗi khi dừng thread: {e}")
            finally:
                self.simulation_thread = None
    
    def reset(self):
        """Đặt lại mô phỏng"""
        self.stop()
        self.robots.clear()
        self.obstacles.clear()
        self.next_robot_id = 1
    
    def run_simulation(self):
        """Main simulation loop"""
        try:
            iteration_count = 0
            max_iterations = 10000  # Giới hạn số lần lặp để tránh vòng lặp vô hạn
            
            while self.running and iteration_count < max_iterations:
                try:
                    self.update()
                    # Xóa tín hiệu sau mỗi lần cập nhật để tránh tích lũy
                    self._clear_all_signals()
                    time.sleep(0.05)  # 20 FPS simulation rate
                    iteration_count += 1
                except Exception as e:
                    print(f"Lỗi trong vòng lặp mô phỏng: {e}")
                    time.sleep(1)  # Tạm dừng nếu có lỗi để tránh loop quá nhanh
                    
            if iteration_count >= max_iterations:
                print("Cảnh báo: Đã đạt đến giới hạn lặp tối đa. Dừng mô phỏng để tránh vòng lặp vô hạn.")
                self.running = False
                
        except Exception as e:
            print(f"Lỗi nghiêm trọng trong thread mô phỏng: {e}")
            self.running = False
    
    def _clear_all_signals(self):
        """Xóa tất cả tín hiệu IR đã thu nhận để tránh tích lũy"""
        for robot in self.robots:
            for receiver in robot.receivers:
                # Đảm bảo xóa sạch tín hiệu
                receiver.clear_signals()
                # Thêm dòng này để xóa cả estimated_distances nếu có
                if hasattr(receiver, 'estimated_distances'):
                    receiver.estimated_distances = {}
    
    def get_robot_at(self, x, y):
        """Lấy robot tại vị trí (x, y)"""
        for robot in self.robots:
            if robot.contains_point(x, y):
                return robot
        return None
    
    def real_to_pixel(self, real_x, real_y):
        """Chuyển đổi tọa độ thực (m) sang pixel"""
        pixel_x = real_x * self.scale
        pixel_y = real_y * self.scale
        return pixel_x, pixel_y
    
    def pixel_to_real(self, pixel_x, pixel_y):
        """Chuyển đổi tọa độ pixel sang thực (m)"""
        real_x = pixel_x / self.scale
        real_y = pixel_y / self.scale
        return real_x, real_y

    def real_distance_to_pixel(self, real_distance):
        """Chuyển đổi khoảng cách thực (m) sang pixel"""
        return round(real_distance * self.scale, 2)

    def pixel_distance_to_real(self, pixel_distance):
        """Chuyển đổi khoảng cách pixel sang thực (m)"""
        return round(pixel_distance / self.scale, 2)

    def get_robot_by_id(self, robot_id):
        """Lấy robot theo ID"""
        for robot in self.robots:
            if robot.id == robot_id:
                return robot
        return None   
     
    def update(self):
        """Cập nhật một bước mô phỏng"""
        # Xóa tất cả tín hiệu từ vòng lặp trước
        for robot in self.robots:
            for receiver in robot.receivers:
                receiver.clear_signals()
        
        # Thu thập vị trí robot
        robot_positions = {}
        for robot in self.robots:
            robot_positions[robot.id] = {
                'x': robot.x,
                'y': robot.y,
                'size': robot.size,
                'orientation': robot.orientation
            }
        
        # Thu thập vật cản
        obstacles = []
        for robot in self.robots:
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
        
        # Tính tín hiệu giữa các robot
        from models.ir_sensor import can_receive_signal
        
        for tx_robot in self.robots:
            for transmitter in tx_robot.transmitters:
                if not transmitter.active:
                    continue
                    
                for rx_robot in self.robots:
                    if rx_robot.id == tx_robot.id:
                        continue  # Không tính tín hiệu từ robot tới chính nó
                        
                    for receiver in rx_robot.receivers:
                        # Sử dụng mô hình kết hợp Pathloss-Rician
                        can_receive, estimated_distance, signal_strength = can_receive_signal(
                            transmitter, receiver, robot_positions, obstacles)
                        
                        if can_receive:
                            receiver.add_signal(tx_robot.id, signal_strength)
                            # Lưu khoảng cách ước lượng nếu cần
                            if not hasattr(receiver, 'estimated_distances'):
                                receiver.estimated_distances = {}
                            receiver.estimated_distances[tx_robot.id] = estimated_distance
    
        # Các cập nhật khác của mô phỏng...

    def update_robot_sizes(self):
        """Cập nhật kích thước của tất cả robot dựa trên tỷ lệ hiện tại"""
        # Làm tròn scale để tránh hiển thị nhiều chữ số thập phân lẻ
        self.scale = round(self.scale, 2)
        print(f"Cập nhật kích thước robot với tỷ lệ {self.scale}")
        
        for robot in self.robots:
            old_size = robot.size
            robot.size = round(self.real_robot_size * self.scale, 2)  # Làm tròn kích thước
            print(f"Robot {robot.id}: {old_size:.2f} -> {robot.size:.2f}")
            
            # Cập nhật góc phát và khoảng cách phát của cảm biến
            for transmitter in robot.transmitters:
                # Ghi nhớ khoảng cách thực (m)
                real_distance = round(self.pixel_distance_to_real(transmitter.beam_distance), 2)
                # Thiết lập lại khoảng cách phát theo tỷ lệ mới
                pixel_distance = round(self.real_distance_to_pixel(real_distance), 2)
                transmitter.beam_distance = pixel_distance
                
                # Làm tròn khoảng cách thực được lưu
                if hasattr(transmitter, 'real_beam_distance'):
                    transmitter.real_beam_distance = round(transmitter.real_beam_distance, 2)
            
            # Cập nhật vị trí cảm biến
            if hasattr(robot, 'update_sensor_positions'):
                robot.update_sensor_positions()
            
    def set_scale(self, new_scale):
        """Thiết lập tỷ lệ mới và cập nhật kích thước robot"""
        self.scale = new_scale
        self.update_robot_sizes()
        # Không cần gọi update_sensor_positions() ở đây vì đã được gọi trong update_robot_sizes()

    def meters_to_pixels(self, meters):
        """Chuyển đổi từ mét sang pixel"""
        # Giả sử tỉ lệ mô phỏng, điều chỉnh theo ứng dụng của bạn
        return meters * 100  # 1m = 100px

# Nhận simulation qua constructor