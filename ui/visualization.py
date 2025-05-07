import tkinter as tk
import math
from tkinter import simpledialog
import random  # Added for random.uniform

class SimulationCanvas(tk.Canvas):
    # pixel/m mặc định và hệ số zoom mỗi lần step
    BASE_SCALE = 250.0
    ZOOM_RATIO = 1.1

    def __init__(self, parent, simulation):
        super().__init__(parent, bg="white")
        self.simulation = simulation
        self.robot_objects = {}
        
        # Chỉnh sửa hệ số zoom
        # khởi tạo zoom_factor dựa trên simulation.scale hiện tại
        self.zoom_factor = simulation.scale / self.BASE_SCALE
        # Tính toán mức zoom tối thiểu để hiển thị đủ 4x4m
        window_width = 800  # Giả định kích thước mặc định
        window_height = 600
        
        # Tính min_zoom để vừa khung 4m×4m trong window
        win_w, win_h = window_width, window_height
        env_w = simulation.real_width * self.BASE_SCALE
        env_h = simulation.real_height * self.BASE_SCALE
        self.min_zoom = min(win_w/env_w, win_h/env_h)
        self.max_zoom = 10.0  # Tăng giới hạn zoom in từ 3.0 lên 10.0
        
        # Thiết lập canvas size
        canvas_width = int(simulation.real_width * simulation.scale)
        canvas_height = int(simulation.real_height * simulation.scale)
        self.config(width=canvas_width, height=canvas_height)
        
        # Thêm sự kiện chuột để tương tác với robot
        self.bind("<Button-1>", self.on_canvas_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.bind("<Right>", self.rotate_selected_clockwise)
        self.bind("<Left>", self.rotate_selected_counterclockwise)
        self.bind("<Control-R>", self.open_rotation_dialog)  # Ctrl+R để mở dialog nhập góc
        self.bind("<MouseWheel>", self.on_mouse_wheel)  # Sự kiện con lăn chuột (Windows)
        self.bind("<Control-Button-4>", self.on_zoom_in)  # Zoom in (Linux)
        self.bind("<Control-Button-5>", self.on_zoom_out)  # Zoom out (Linux)
        
        # Thêm phím tắt zoom
        self.bind("<plus>", self.on_zoom_in)  # Phím +
        self.bind("<minus>", self.on_zoom_out)  # Phím -
        self.bind("<equal>", self.on_zoom_in)  # Phím =
        
        # Thêm biến theo dõi trạng thái xoay
        self.rotation_handle = None
        self.rotating = False
        
        # Thêm vào các bind events hiện có
        self.bind("<B3-Motion>", self.on_rotation_drag)     # Chuột phải kéo để xoay
        self.bind("<ButtonPress-3>", self.on_rotation_start)  # Bắt đầu xoay
        self.bind("<ButtonRelease-3>", self.on_rotation_end)  # Kết thúc xoay

        self.selected_robot = None
        self.dragging = False
        self.panning = False  # Biến theo dõi trạng thái đang kéo view
        self.last_x = 0
        self.last_y = 0
        self.show_signal_lines = True  # Bật hiển thị đường kết nối tín hiệu

        # Thêm phím tắt để thiết lập góc cố định
        self.bind("<Control-F>", self.set_fixed_angle_for_all)  # Ctrl+F cho tất cả robot
        self.bind("<Control-f>", self.set_fixed_angle_for_selected)  # Ctrl+f cho robot đang chọn

        from models.path_manager import PathManager
        self.path_manager = PathManager(simulation)
        self.drawing_path = False
        self.waypoints = []
        
        # Bind sự kiện chuột
        self.bind("<Button-1>", self.on_canvas_click)
        self.bind("<B1-Motion>", self.on_canvas_drag)
        self.bind("<ButtonRelease-1>", self.on_canvas_release)

    
    def update_canvas(self):
        """Cập nhật toàn bộ canvas"""
        # Update formation following if path manager is active
        if hasattr(self, 'path_manager') and self.path_manager.active:
            self.update_formation()
        
        # Lưu các waypoints hiện tại nếu có
        current_waypoints = None
        if hasattr(self, 'path_manager') and self.path_manager.waypoints:
            current_waypoints = self.path_manager.waypoints.copy()
        
        # Xóa tất cả các đối tượng trên canvas
        self.delete("all")
        self.robot_objects.clear()
        
        # Vẽ lưới tọa độ
        self._draw_grid()
        
        # Vẽ lại đường đi nếu có
        if current_waypoints:
            self._draw_path(current_waypoints)
        
        # Vẽ tất cả robot
        for robot in self.simulation.robots:
            self._draw_robot(robot)
        
        # Vẽ các tín hiệu IR nếu đang mô phỏng
        if self.simulation.running:
            self._draw_ir_signals()
        
        # Hiển thị thông tin môi trường thật
        self._draw_real_world_info()
        
        # Cập nhật thông tin kích thước và scale
        self._update_info()

    def update_formation(self):
        """Cập nhật vị trí các robot theo đội hình hàng dọc sử dụng RPA để phát hiện và tọa độ global để di chuyển"""
        # Kiểm tra nếu path manager đang hoạt động
        if not hasattr(self, 'path_manager') or not self.path_manager.active:
            return
        
        # Lấy ID của robot dẫn đầu
        leader_id = self.path_manager.leader_id
        if leader_id is None:
            return
        
        # Lấy robot dẫn đầu
        leader = self.simulation.get_robot_by_id(leader_id)
        if not leader:
            return
        
        # Lấy danh sách các robot khác (không phải dẫn đầu)
        follower_robots = [robot for robot in self.simulation.robots if robot.id != leader_id]
        
        # Sắp xếp robot theo khoảng cách đến robot dẫn đầu ban đầu 
        # Kiểm tra cả việc không có formation_order và số lượng robot có thay đổi
        if not hasattr(self, 'formation_order') or len(self.formation_order) != len(self.simulation.robots):
            # Tính khoảng cách và sắp xếp từ gần đến xa
            follower_robots.sort(key=lambda r: leader.get_physical_distance_to(r))
            self.formation_order = [leader] + follower_robots
            print(f"Khởi tạo đội hình: Leader={leader.id}, Followers={[r.id for r in follower_robots]}")
        
        # === THÊM XỬ LÝ TRÁNH VA CHẠM CHO ROBOT LEADER ===
        self._handle_leader_obstacle_avoidance(leader, follower_robots)
        
        # Khoảng cách mong muốn giữa các robot trong đội hình
        desired_distance = leader.size * 2.5  # Khoảng cách 2.5 lần kích thước robot
        
        # Cập nhật vị trí của từng robot theo đội hình
        for i in range(1, len(self.formation_order)):
            current_robot = self.formation_order[i]
            robot_ahead = self.formation_order[i-1]  # Robot phía trước
            
            # Debug để kiểm tra robot nào được cập nhật
            print(f"Cập nhật robot {current_robot.id} theo sau robot {robot_ahead.id}")
            
            # === SỬ DỤNG RPA ĐỂ XÁC ĐỊNH VỊ TRÍ TƯƠNG ĐỐI ===
            rpa_result = current_robot.calculate_relative_position_rpa(robot_ahead.id)
            
            if rpa_result is None:
                # Nếu không nhận được tín hiệu IR, không di chuyển
                print(f"Robot {current_robot.id} không phát hiện được tín hiệu từ robot {robot_ahead.id}")
                continue
            
            # Lấy kết quả từ RPA - (bearing_angle, distance, confidence) để biết có nhìn thấy không
            relative_angle, distance_m, confidence = rpa_result
            
            # Debug thông tin RPA
            print(f"RPA: Robot {current_robot.id} phát hiện robot {robot_ahead.id} ở góc {relative_angle:.1f}°, khoảng cách {distance_m:.2f}m, độ tin cậy {confidence:.2f}")
            
            # === SỬ DỤNG TỌA ĐỘ GLOBAL CHO VIỆC DI CHUYỂN ===
            
            # Tính toán khoảng cách và hướng dựa trên tọa độ tuyệt đối
            dx = robot_ahead.x - current_robot.x
            dy = robot_ahead.y - current_robot.y
            global_distance = math.sqrt(dx*dx + dy*dy)  # Khoảng cách theo pixel
            global_angle = math.degrees(math.atan2(dy, dx)) % 360  # Góc tuyệt đối
            
            # Tính toán desired_distance in pixels
            desired_distance_px = desired_distance
            
            # Add a small buffer zone around the desired distance to prevent jitter
            distance_buffer = desired_distance_px * 0.1  # 10% buffer

            # Calculate direction vectors (normalized)
            if global_distance > 0:  # Prevent division by zero
                direction_x = dx / global_distance
                direction_y = dy / global_distance
            else:
                direction_x, direction_y = 0, 0

            # Move only if outside the buffer zone
            if abs(global_distance - desired_distance_px) > distance_buffer:
                # Calculate speed factor - higher for robots further back in formation
                move_speed_factor = 0.5 if i >= 3 else 0.3
                
                if global_distance > desired_distance_px:
                    # Too far - move forward toward the robot ahead
                    move_distance = min(10.0, (global_distance - desired_distance_px) * move_speed_factor)
                    move_x = direction_x * move_distance
                    move_y = direction_y * move_distance
                else:
                    # Too close - back away from the robot ahead
                    move_distance = min(8.0, (desired_distance_px - global_distance) * move_speed_factor)
                    # Reverse direction to move away
                    move_x = -direction_x * move_distance
                    move_y = -direction_y * move_distance
                    
                    # Add debug message for backing up
                    print(f"Robot {current_robot.id} backing away from Robot {robot_ahead.id}: {move_distance:.2f}px")
                
                # Move the robot
                current_robot.move(move_x, move_y)
            
            # Đặt hướng cho robot - hướng về robot phía trước
            current_angle = current_robot.orientation % 360
            
            # Tính góc xoay ngắn nhất để hướng tới robot phía trước
            angle_diff = (global_angle - current_angle + 180) % 360 - 180
            
            # Xoay dần dần về global_angle
            if abs(angle_diff) > 2:
                # Tăng tốc độ xoay cho robot thứ 4 trở đi
                rotation_factor = 0.6 if i >= 3 else 0.4
                rotation_speed = min(20.0, abs(angle_diff) * rotation_factor)
                
                if angle_diff > 0:
                    current_robot.rotate(rotation_speed)
                else:
                    current_robot.rotate(-rotation_speed)

            # === THÊM XỬ LÝ TRÁNH VA CHẠM CHO ROBOT FOLLOWER ===
            # Get all other robots for avoidance calculations
            all_robots = [r for r in self.simulation.robots if r.id != current_robot.id]

            # Call the enhanced obstacle avoidance function
            self._handle_follower_obstacle_avoidance(
                current_robot, 
                robot_ahead, 
                all_robots, 
                desired_distance_px
            )

    def _handle_leader_obstacle_avoidance(self, leader, follower_robots):
        """Handle obstacle avoidance for the leader robot - improved version for smoother motion
        and proper alignment of robot's heading with movement direction"""
        # Check if following a path
        if not hasattr(self, 'path_manager') or not self.path_manager.active:
            return
        
        # Initialize tracking variables if not exists
        if not hasattr(self, 'previous_avoidance_vector'):
            self.previous_avoidance_vector = (0, 0, 0)  # x, y, magnitude
        
        if not hasattr(self, 'current_speed'):
            self.current_speed = 5.0  # Reduced from 8.0 to 5.0 for slower movement
        
        # Obstacle threshold (increased from 5cm to 8cm)
        obstacle_threshold_m = 0.08
        obstacle_threshold_px = self.simulation.real_distance_to_pixel(obstacle_threshold_m)
        safety_margin = 1.5  # Increased from 1.3 to 1.5
        safety_threshold_px = obstacle_threshold_px * safety_margin
        
        # --- STEP 1: Calculate avoidance forces from nearby robots ---
        avoidance_vector = [0, 0, 0]  # x, y, magnitude
        close_robots = []
        
        for robot in follower_robots:
            # Calculate physical distance between robots
            distance_px = math.sqrt((leader.x - robot.x)**2 + (leader.y - robot.y)**2)
            min_distance_px = safety_threshold_px + (leader.size + robot.size) / 2
            
            if distance_px < min_distance_px:
                # Calculate vector from obstacle to leader
                dx = leader.x - robot.x
                dy = leader.y - robot.y
                
                # Avoid division by zero
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    angle = random.uniform(0, 2 * math.pi)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                else:
                    # Normalize vector
                    magnitude = math.sqrt(dx*dx + dy*dy)
                    dx /= magnitude
                    dy /= magnitude
                
                # Calculate avoidance force inversely proportional to distance 
                # Use inverse square law for more natural physics behavior
                force = (min_distance_px / max(distance_px, 1))**2
                
                # Add to list of close robots
                close_robots.append((dx, dy, force, distance_px, robot.id))
                
                # Add to the avoidance vector
                avoidance_vector[0] += dx * force
                avoidance_vector[1] += dy * force
        
        # Normalize avoidance vector if it exists
        if close_robots:
            avoidance_vector[2] = math.sqrt(avoidance_vector[0]**2 + avoidance_vector[1]**2)
            if avoidance_vector[2] > 0:
                avoidance_vector[0] /= avoidance_vector[2]
                avoidance_vector[1] /= avoidance_vector[2]
        
        # --- STEP 2: Calculate target direction vector ---
        target_vector = [0, 0, 0]  # x, y, magnitude
        
        if self.path_manager.current_waypoint_index < len(self.path_manager.waypoints):
            target_x, target_y = self.path_manager.waypoints[self.path_manager.current_waypoint_index]
            
            # Vector to target
            target_vector[0] = target_x - leader.x
            target_vector[1] = target_y - leader.y
            
            # Normalize target vector
            target_vector[2] = math.sqrt(target_vector[0]**2 + target_vector[1]**2)
            if target_vector[2] > 0:
                target_vector[0] /= target_vector[2]
                target_vector[1] /= target_vector[2]
        
        # --- STEP 3: Smooth the avoidance vector with previous one ---
        # This creates more continuous motion
        if avoidance_vector[2] > 0:
            prev_x, prev_y, prev_mag = self.previous_avoidance_vector
            
            # Stronger smoothing factor for more consistent motion
            # Higher values = smoother but less responsive movement
            smooth_factor = min(0.85, max(0.6, prev_mag * 0.7))  # Increased from 0.8/0.3/0.5
            
            smooth_x = smooth_factor * prev_x + (1 - smooth_factor) * avoidance_vector[0]
            smooth_y = smooth_factor * prev_y + (1 - smooth_factor) * avoidance_vector[1]
            
            # Normalize smoothed vector
            smooth_mag = math.sqrt(smooth_x**2 + smooth_y**2)
            if smooth_mag > 0:
                smooth_x /= smooth_mag
                smooth_y /= smooth_mag
                
            avoidance_vector = [smooth_x, smooth_y, 1.0]
        
        # --- STEP 4: Combine avoidance and target vectors dynamically ---
        final_vector = [0, 0]
        
        if avoidance_vector[2] > 0:
            # Calculate dot product to determine how conflicting the vectors are
            # Dot product near 1: vectors aligned, near -1: vectors opposing
            dot_product = (avoidance_vector[0] * target_vector[0] + 
                        avoidance_vector[1] * target_vector[1])
            
            # Determine weights based on dot product and distance to closest obstacle
            if close_robots:
                closest_distance = min([dist for _, _, _, dist, _ in close_robots])
                # Normalize distance to a 0-1 range where 0 is collision and 1 is at safety threshold
                normalized_distance = min(1.0, closest_distance / safety_threshold_px)
                
                # Calculate base avoidance weight - more weight when closer to obstacle
                # Using exponential function for smoother transition
                base_avoidance_weight = 0.6 + 0.4 * math.exp(-2 * normalized_distance)
                
                # Adjust weights based on vector alignment
                if dot_product < -0.5:  # Highly conflicting directions (>120° angle)
                    # When vectors oppose, prioritize avoidance heavily
                    avoidance_weight = min(0.95, base_avoidance_weight + 0.3)
                elif dot_product < 0:  # Moderately conflicting (90-120° angle)
                    avoidance_weight = min(0.9, base_avoidance_weight + 0.2)
                else:  # Vectors somewhat aligned (<90° angle)
                    # When vectors somewhat align, allow more influence from target
                    avoidance_weight = min(0.85, base_avoidance_weight)
                
                target_weight = 1 - avoidance_weight
                
                # Combine vectors with calculated weights
                final_vector[0] = avoidance_vector[0] * avoidance_weight + target_vector[0] * target_weight
                final_vector[1] = avoidance_vector[1] * avoidance_weight + target_vector[1] * target_weight
                
                # Store current avoidance vector for next frame smoothing
                # Include magnitude information proportional to how close obstacles are
                # Use exponential function for smoother magnitude calculation
                avoidance_magnitude = math.exp(-normalized_distance * 1.5)
                self.previous_avoidance_vector = (avoidance_vector[0], avoidance_vector[1], avoidance_magnitude)
                
                # Adjust speed based on obstacle proximity - smoother deceleration
                min_speed = 1.0  # Reduced from 2.0 to 1.0
                max_speed = 5.0  # Reduced from 8.0 to 5.0
                
                # Speed is proportional to normalized distance with a minimum
                target_speed = min_speed + (max_speed - min_speed) * normalized_distance
            else:
                # No obstacles - use target direction with gentle transition away from avoidance
                prev_x, prev_y, prev_mag = self.previous_avoidance_vector
                
                # Gradually reduce previous avoidance influence
                if prev_mag > 0.01:  # Only if there was significant previous avoidance
                    # Decay previous avoidance influence
                    decay_factor = 0.9  # Reduce by 10% each frame
                    remaining_influence = prev_mag * decay_factor
                    
                    # Scale remaining influence based on dot product with target
                    # Less influence when previous avoidance opposes current target
                    influence_factor = 0.3 * remaining_influence
                    
                    # Combine with target direction
                    final_vector[0] = prev_x * influence_factor + target_vector[0] * (1 - influence_factor)
                    final_vector[1] = prev_y * influence_factor + target_vector[1] * (1 - influence_factor)
                    
                    # Update previous avoidance vector with reduced magnitude
                    self.previous_avoidance_vector = (prev_x, prev_y, remaining_influence)
                else:
                    # No previous avoidance or fully decayed - use pure target
                    final_vector[0] = target_vector[0]
                    final_vector[1] = target_vector[1]
                    self.previous_avoidance_vector = (0, 0, 0)
                
                # Return to normal speed
                target_speed = 5.0  # Reduced from 8.0
        else:
            # No obstacles and no previous avoidance - use target direction
            final_vector[0] = target_vector[0]
            final_vector[1] = target_vector[1]
            self.previous_avoidance_vector = (0, 0, 0)
            target_speed = 5.0  # Reduced from 8.0
        
        # --- STEP 5: Normalize final vector ---
        final_magnitude = math.sqrt(final_vector[0]**2 + final_vector[1]**2)
        if final_magnitude > 0:
            final_vector[0] /= final_magnitude
            final_vector[1] /= final_magnitude
        
        # --- STEP 6: Apply smooth speed changes ---
        # Speed smoothing - gradual acceleration/deceleration
        speed_change_rate = 0.1  # Reduced from 0.15 for smoother transitions
        if target_speed > self.current_speed:
            self.current_speed = min(target_speed, self.current_speed + speed_change_rate)
        else:
            self.current_speed = max(target_speed, self.current_speed - speed_change_rate)
        
        # --- STEP 7: Move the robot with final vector and speed ---
        leader.move(final_vector[0] * self.current_speed, final_vector[1] * self.current_speed)
        
        # --- STEP 8: Smooth rotation towards movement direction ---
        # Calculate angle for robot orientation based on ACTUAL movement direction
        # This ensures the robot's head always faces its travel direction
        
        # Get actual movement vector (could be different from final_vector due to physics)
        # If you don't have access to actual velocity, use the command vector
        movement_x = final_vector[0] * self.current_speed
        movement_y = final_vector[1] * self.current_speed
        
        # Calculate angle from movement direction
        new_angle = math.degrees(math.atan2(movement_y, movement_x)) % 360
        current_angle = leader.orientation
        
        # Calculate shortest rotation path
        angle_diff = (new_angle - current_angle + 180) % 360 - 180
        
        # Adaptive rotation speed:
        # - Faster rotation when angle difference is large
        # - Slower, more precise rotation when nearly aligned
        # - Higher base rotation speed for more responsive turning
        base_rotation_speed = 2.0  # Minimum rotation speed
        max_rotation_speed = 8.0   # Maximum rotation speed (increased from 5.0)
        
        # More responsive rotation coefficient (increased from 0.15)
        rotation_factor = 0.25
        
        # Calculate rotation speed with a non-linear response curve
        # This gives more precise control for small adjustments
        if abs(angle_diff) < 10:
            # Very precise for small angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * 0.1
        elif abs(angle_diff) < 45:
            # Moderate speed for medium angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * rotation_factor
        else:
            # Faster rotation for large angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * rotation_factor * 1.5
        
        # Cap at maximum rotation speed
        rotation_speed = min(max_rotation_speed, rotation_speed)
        
        # Apply rotation in the appropriate direction
        if angle_diff > 0:
            leader.rotate(rotation_speed)
        else:
            leader.rotate(-rotation_speed)

    def _draw_grid(self):
        """Vẽ lưới tọa độ"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:  # Canvas chưa được render
            width = 800
            height = 600
        
        # Vẽ lưới phù hợp với tỉ lệ scale
        grid_size = int(self.simulation.scale / 2)  # 50cm
        
        for x in range(0, width, grid_size):
            self.create_line(x, 0, x, height, fill="#e0e0e0")
        
        for y in range(0, height, grid_size):
            self.create_line(0, y, width, y, fill="#e0e0e0")
        
        # Vẽ khung môi trường 4m x 4m
        env_width = int(self.simulation.real_width * self.simulation.scale)
        env_height = int(self.simulation.real_height * self.simulation.scale)
        self.create_rectangle(0, 0, env_width, env_height, outline="blue", width=2)
    
    def _draw_real_world_info(self):
        """Hiển thị thông tin về môi trường thật"""
        # Không hiển thị thông tin ở đây vì đã có _update_info
        # Phương thức này có thể để trống hoặc xóa đi
        pass

    def _draw_robot(self, robot):
        """Vẽ robot trên canvas"""
        # Vẽ hình vuông đại diện robot
        half_size = robot.size / 2
        
        # Màu sắc tùy thuộc có phải robot được chọn
        fill_color = "#ADD8E6" if robot != self.selected_robot else "#90EE90"
        
        # Vẽ hình vuông chính (đã xoay)
        corners = robot.get_corner_positions()
        robot_body = self.create_polygon(corners, fill=fill_color, outline="black", width=2,
                                     tags=f"robot_{robot.id}")
        
        # Lưu ID đối tượng robot
        self.robot_objects[robot.id] = robot_body
        

        # Hiển thị ID và vị trí của robot theo bố cục tốt hơn
        real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
        
        # Text được xếp chồng lên nhau gọn hơn - ID ở giữa
        self.create_text(robot.x, robot.y, text=f"ID {robot.id}", font=("Arial", 9, "bold"))
        
        # Vị trí robot - để nhỏ hơn và nằm dưới ID
        pos_text = f"{real_x:.2f}m, {real_y:.2f}m"
        self.create_text(robot.x, robot.y + 15, text=pos_text, font=("Arial", 7))
        
        # Góc hiển thị ở cuối
        self.create_text(robot.x, robot.y + 25, text=f"{robot.orientation}°", font=("Arial", 7))
        
        # Vẽ các cảm biến
        # Mảng màu để phân biệt các cảm biến theo vị trí
        tx_colors = ["red", "orange", "pink", "purple"]
        # Sử dụng màu đen cố định cho tất cả đầu thu (thay vì mảng màu)
        rx_color = "black"  # Màu đen cố định cho tất cả đầu nhận IR
        
        for i, transmitter in enumerate(robot.transmitters):
            tx, ty = transmitter.get_position(robot.x, robot.y, robot.size, robot.orientation)
            
            # Sử dụng màu khác nhau dựa vào position_index cho transmitters
            color_idx = transmitter.position_index % len(tx_colors)
            color = tx_colors[color_idx]
            
            # Vẽ cảm biến phát với màu phân biệt
            self.create_oval(tx-3, ty-3, tx+3, ty+3, fill=color, 
                            outline="black", tags=f"tx_{robot.id}_{i}")
            
            # Hiển thị mã cảm biến nếu robot được chọn
            if robot == self.selected_robot:
                side_names = ["T", "R", "B", "L"]  # Top, Right, Bottom, Left
                label = f"{side_names[transmitter.side]}{transmitter.position_index}"
                self.create_text(tx, ty-8, text=label, font=("Arial", 7), tags=f"tx_label_{robot.id}_{i}")
            
            # Vẽ chùm tia nếu đang mô phỏng và cảm biến đang hoạt động
            if transmitter.active:
                # Lấy thông số chùm tia
                beam_params = transmitter.get_beam_cone(robot.x, robot.y, robot.size, robot.orientation)
                if len(beam_params) >= 5:  # Đổi từ 3 sang 5 tham số
                    start_angle, extent_angle, major_radius, minor_radius, beam_direction = beam_params
                    # Lấy vị trí transmitter
                    tx, ty = transmitter.get_position(robot.x, robot.y, robot.size, robot.orientation)
                    
                    # Tạo polygon từ vị trí transmitter và các điểm trên elip
                    polygon_points = [tx, ty]  # Điểm đầu tiên là vị trí transmitter
                    
                    # Số điểm trên cung để tạo hình elip mượt mà
                    num_points = 30  # Tăng số điểm để mượt hơn
                    
                    # Đảm bảo góc làm việc trong hệ tọa độ Tkinter
                    angle_rad_start = math.radians(start_angle)
                    angle_rad_end = math.radians((start_angle + extent_angle) % 360)
                    
                    # Nếu góc kết thúc nhỏ hơn góc bắt đầu, cộng thêm 2π
                    if angle_rad_end < angle_rad_start:
                        angle_rad_end += 2 * math.pi
                        
                    # Góc của hướng chính elip
                    main_direction_rad = math.radians(beam_direction)
                    
                    # Tạo các điểm trên cung chùm tia với hình dạng bo tròn
                    for i in range(num_points + 1):
                        # Các phần tính góc giữ nguyên
                        angle_rad = angle_rad_start + (angle_rad_end - angle_rad_start) * i / num_points
                        rel_angle = angle_rad - main_direction_rad
                        
                        # Chuẩn hóa góc tương đối về khoảng [-π, π]
                        while rel_angle > math.pi:
                            rel_angle -= 2 * math.pi
                        while rel_angle < -math.pi:
                            rel_angle += 2 * math.pi
                        
                        # Tính tỷ lệ góc (0 ở giữa, 1 ở biên)
                        angle_ratio = abs(rel_angle) / (math.radians(extent_angle) / 2)
                        
                        # Sửa phần này để tránh số phức
                        superellipse_n = 2.5
                        angle_ratio_power = angle_ratio ** superellipse_n
                        
                        # Đảm bảo đối số không âm trước khi áp dụng phép lũy thừa phân số
                        if angle_ratio_power >= 1:
                            radius_factor = 0
                        else:
                            radius_factor = (1 - angle_ratio_power) ** (1/superellipse_n)
                        
                        # Áp dụng thêm hàm cos để tạo dạng bo tròn tự nhiên
                        cos_factor = math.cos(rel_angle * 0.7)
                        radius = major_radius * radius_factor * cos_factor
                        
                        # Tính tọa độ điểm trên cung
                        x = tx + radius * math.cos(angle_rad)
                        y = ty + radius * math.sin(angle_rad)
                        
                        # Thêm kiểm tra để đảm bảo x, y là số thực
                        if isinstance(x, complex):
                            x = x.real
                        if isinstance(y, complex):
                            y = y.real
                        
                        # Thêm vào danh sách điểm
                        polygon_points.extend([x, y])
                    
                    # Vẽ chùm tia dưới dạng polygon
                    self.create_polygon(polygon_points, fill='#FFE0E0', outline=color, width=1,
                                     stipple='gray25', tags=f"beam_{robot.id}_{i}")
        
        for i, receiver in enumerate(robot.receivers):
            rx, ry = receiver.get_position(robot.x, robot.y, robot.size, robot.orientation)
            
            # Sử dụng màu đen cố định cho tất cả receivers thay vì màu theo position_index
            self.create_oval(rx-3, ry-3, rx+3, ry+3, fill=rx_color, 
                            outline="black", tags=f"rx_{robot.id}_{i}")
            
            # Hiển thị mã cảm biến nếu robot được chọn
            if self.selected_robot and receiver.signals:
                side_names = ["T", "R", "B", "L"]
                label = f"{side_names[receiver.side]}{receiver.position_index}"
                self.create_text(rx, ry+8, text=label, font=("Arial", 7), tags=f"rx_label_{robot.id}_{i}")
        
            # Vẽ vùng nhận của receiver khi robot được chọn
            if robot == self.selected_robot:
                for receiver in robot.receivers:
                    rx_pos = receiver.get_position(robot.x, robot.y, robot.size, robot.orientation)
                    
                    # Chỉ vẽ khi được chọn để tránh quá nhiều đối tượng trên canvas
                    viewing_direction = receiver.get_viewing_direction(robot.orientation)
                    
                    # Vẽ vòng cung thể hiện hướng nhận
                    reception_angle = receiver.viewing_angle  # Sử dụng đúng góc nhận từ receiver
                    radius = 60  # Bán kính của vòng cung

                    # Tính toán lại góc cho đúng với hệ tọa độ Tkinter
                    tk_center_angle = (0 - viewing_direction) % 360  # Thay đổi từ 0 thành 90 để đúng hướng
                    tk_start_angle = (tk_center_angle - reception_angle / 2) % 360
                    tk_extent_angle = reception_angle

                    # Thay đổi cách vẽ vòng cung - vẽ một vòng cung dày thay vì nhiều vòng cung mỏng
                    x0 = rx_pos[0] - radius
                    y0 = rx_pos[1] - radius
                    x1 = rx_pos[0] + radius
                    y1 = rx_pos[1] + radius

                    # Vẽ vòng cung chính với độ dày lớn để dễ nhìn
                    self.create_arc(x0, y0, x1, y1,
                                   start=tk_start_angle, extent=tk_extent_angle,
                                   style="arc", outline="blue", width=2,
                                   tags=f"rx_dir_{robot.id}_main")

        # Thêm đoạn code vẽ các trục tọa độ
        # ------- Bắt đầu code mới -------
        # Vẽ trục tọa độ của robot
        angle_rad = math.radians(robot.orientation)

        # Độ dài trục cơ bản và trục head
        axis_length = robot.size * 0.6
        head_axis_length = robot.size * 0.9  # Head dài hơn 

        # Vẽ trục X/Head (màu xanh lá, dài hơn) - đây là head của robot (0°)
        head_end_x = robot.x + head_axis_length * math.cos(angle_rad)
        head_end_y = robot.y + head_axis_length * math.sin(angle_rad)
        self.create_line(robot.x, robot.y, head_end_x, head_end_y, 
                        fill="green", width=3, arrow=tk.LAST, tags=f"axis_head_{robot.id}")

        # Vẽ trục Y (màu xanh dương) - vuông góc với head (90° theo chiều kim đồng hồ)
        y_rad = angle_rad + math.pi/2
        y_end_x = robot.x + axis_length * math.cos(y_rad)
        y_end_y = robot.y + axis_length * math.sin(y_rad)
        self.create_line(robot.x, robot.y, y_end_x, y_end_y, 
                        fill="blue", width=2, arrow=tk.LAST, tags=f"axis_y_{robot.id}")

        # Thêm chú thích cho các trục
        self.create_text(head_end_x + 10, head_end_y, text="X/Head", fill="green", font=("Arial", 8))
        self.create_text(y_end_x, y_end_y + 10, text="Y", fill="blue", font=("Arial", 8))
        # ------- Kết thúc code mới -------

        # Thêm nút xoay cho robot được chọn
        if robot == self.selected_robot:
            # Vẽ đường tròn xoay ở khoảng cách từ tâm robot
            rotation_radius = robot.size * 0.75
            handle_x = robot.x + rotation_radius * math.cos(angle_rad + math.pi/4)
            handle_y = robot.y + rotation_radius * math.sin(angle_rad + math.pi/4)
            
        

    def _draw_ir_signals(self):
        """Vẽ tín hiệu IR giữa các robot"""
        # Thu thập vị trí các cảm biến và robot
        robot_positions = {}
        tx_positions = []
        rx_positions = []
        
        for robot in self.simulation.robots:
            # Lưu vị trí robot để dùng cho can_receive_signal
            robot_positions[robot.id] = {
                'x': robot.x, 
                'y': robot.y, 
                'size': robot.size, 
                'orientation': robot.orientation
            }
            
            for tx, pos in robot.get_transmitter_positions():
                tx_positions.append((tx, pos))
            
            for rx, pos in robot.get_receiver_positions():
                rx_positions.append((rx, pos))
        
        # Thu thập thông tin về vật cản
        obstacles = []
        for robot in self.simulation.robots:
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
        
        # Vẽ tất cả các tín hiệu IR hợp lệ
        from models.ir_sensor import can_receive_signal
        
        for tx, tx_pos in tx_positions:
            for rx, rx_pos in rx_positions:
                # Bỏ qua nếu cùng robot
                if tx.robot_id == rx.robot_id:
                    continue
                
                # Sử dụng mô hình kết hợp Pathloss-Rician
                can_receive, estimated_distance, signal_strength = can_receive_signal(
                    tx, rx, robot_positions, obstacles)
                
                if can_receive:
                    # Màu sắc dựa trên cường độ tín hiệu
                    color, stipple = self._get_signal_color(signal_strength/100)
                    
                    # Độ rộng của đường tỷ lệ với cường độ tín hiệu
                    line_width = max(1, min(3, signal_strength / 30))
                    
                    # Vẽ đường kết nối với hiệu ứng phát sáng
                    # Trước tiên vẽ một đường mờ rộng hơn làm nền để tạo cảm giác phát sáng
                    glow_width = line_width * 1.5
                    glow_color = f"#{255:02x}{255:02x}{200:02x}"  # Màu vàng nhạt
                    
                    self.create_line(tx_pos[0], tx_pos[1], rx_pos[0], rx_pos[1], 
                                   fill=glow_color, width=glow_width, 
                                   stipple='gray75',  # Thêm stipple để tạo hiệu ứng mờ
                                   tags="ir_signal_glow")
                    
                    # Sau đó vẽ đường chính
                    self.create_line(tx_pos[0], tx_pos[1], rx_pos[0], rx_pos[1], 
                                   fill=color, width=line_width, 
                                   dash=(3, 2) if signal_strength < 40 else "", 
                                   stipple=stipple, tags="ir_signal")
                    
                    # Hiển thị giá trị cường độ với font phù hợp với cường độ tín hiệu
                    mid_x = (tx_pos[0] + rx_pos[0]) / 2
                    mid_y = (tx_pos[1] + rx_pos[1]) / 2
                    
                    # Tùy chỉnh font size theo cường độ tín hiệu
                    font_size = max(6, min(9, int(signal_strength / 15)))
                    
                    # Chỉ hiển thị nền cho tín hiệu đủ mạnh
                    if signal_strength > 20:
                        self.create_oval(mid_x-15, mid_y-10, mid_x+15, mid_y+10,
                                      fill='white', outline='', tags="ir_signal_bg")
                    
                    self.create_text(mid_x, mid_y, text=f"{signal_strength:.1f}", 
                                   fill="black", font=("Arial", font_size), tags="ir_signal")

    def _get_signal_color(self, strength):
        """Chuyển đổi cường độ tín hiệu thành màu sắc với độ suy giảm đều"""
        # Đảm bảo strength nằm trong khoảng [0, 1]
        strength = max(0.0, min(1.0, strength))

        # Mở rộng phổ màu để thể hiện sự suy giảm chi tiết hơn
        if strength > 0.7:  # Tín hiệu mạnh: xanh lá
            # Tính toán r và đảm bảo nó không âm
            r_float = 255 * (1 - strength) * 2
            r = max(0, int(r_float)) # Đảm bảo r không âm
            g = 255
            b = 0
        elif strength > 0.4:  # Tín hiệu trung bình: vàng
            r = 255
            g = 255
            b = 0
        elif strength > 0.2:  # Tín hiệu khá yếu: cam
            r = 255
            g = 165
            b = 0
        else:  # Tín hiệu rất yếu: đỏ
            r = 255
            # g đã được đảm bảo không âm với max(0, ...)
            g = max(0, int(255 * strength * 4))
            b = 0

        # Đảm bảo tất cả các thành phần màu nằm trong khoảng [0, 255] trước khi định dạng
        r = min(255, r)
        g = min(255, g)
        b = min(255, b)

        # Độ mờ dựa trên cường độ tín hiệu - thay đổi từ từ thay vì đột ngột
        if strength < 0.05:
            stipple = 'gray25'  # Rất mờ cho tín hiệu cực yếu
        elif strength < 0.15:
            stipple = 'gray50'  # Khá mờ cho tín hiệu yếu
        elif strength < 0.3:
            stipple = 'gray75'  # Hơi mờ cho tín hiệu trung bình-yếu
        else:
            stipple = ''  # Không mờ cho tín hiệu trung bình và mạnh

        # Trả về màu hợp lệ
        return f"#{r:02x}{g:02x}{b:02x}", stipple
    
    def on_canvas_click(self, event):
        """Xử lý sự kiện click chuột"""
        if self.drawing_path:
            # Add the waypoint to the list
            x, y = event.x, event.y
            self.waypoints.append((x, y))
            
            # Instead of drawing directly here, clear existing points and redraw all at once
            self.delete('waypoint')
            self._draw_path(self.waypoints)
            
            # Update waypoints in path_manager
            if hasattr(self, 'path_manager'):
                self.path_manager.waypoints = self.waypoints.copy()
                
                # Update real coordinates
                self.path_manager.waypoints_real = []
                for wx, wy in self.waypoints:
                    real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                    self.path_manager.waypoints_real.append((real_x, real_y))
        else:
            # Code for handling robot selection
            robot = self.simulation.get_robot_at(event.x, event.y)
            if robot:
                self.selected_robot = robot
                self.dragging = True
                self.panning = False
                self.last_x = event.x
                self.last_y = event.y
                self.focus_set()
            else:
                self.selected_robot = None
                self.dragging = False
                self.panning = True
                self.last_x = event.x
                self.last_y = event.y
        
        # Update canvas
        self.update_canvas()

    def on_drag(self, event):
        """Xử lý sự kiện kéo chuột"""
        if self.dragging and self.selected_robot:
            # Tính khoảng di chuyển
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Di chuyển robot đang chọn
            self.selected_robot.move(dx, dy)
            
            # Cập nhật vị trí cuối cùng
            self.last_x = event.x
            self.last_y = event.y
            
            # Vẽ lại canvas
            self.update_canvas()
        elif self.panning:
            # Tính khoảng di chuyển
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Di chuyển tất cả robot (tạo hiệu ứng kéo view)
            for robot in self.simulation.robots:
                robot.move(dx, dy)
            
            # Cập nhật vị trí cuối cùng
            self.last_x = event.x
            self.last_y = event.y
            
            # Vẽ lại canvas
            self.update_canvas()

    def on_mouse_wheel(self, event):
        """Xử lý sự kiện cuộn chuột để zoom mượt"""
        if event.state & 0x4:  # Phím Ctrl
            # Lưu vị trí con trỏ chuột (pixel)
            cursor_x, cursor_y = event.x, event.y
            
            # Chuyển đổi vị trí con trỏ sang tọa độ thực (m)
            cursor_real_x, cursor_real_y = self.simulation.pixel_to_real(cursor_x, cursor_y)
            
            # Lưu vị trí thực của tất cả robot
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Lưu vị trí thực của các điểm đường đi nếu có
            path_points_real = []
            if hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
                for i, point in enumerate(self.path_manager.waypoints):
                    if isinstance(point, tuple) and len(point) == 2:
                        real_x, real_y = self.simulation.pixel_to_real(point[0], point[1])
                        path_points_real.append((i, real_x, real_y))
            
            # Cập nhật hệ số zoom giống như zoom_in và zoom_out
            old_zoom = self.zoom_factor
            if event.delta > 0:  # zoom in
                self.zoom_factor = min(self.max_zoom, self.zoom_factor * self.ZOOM_RATIO)
                self.zoom_factor = round(self.zoom_factor, 4)  # Thống nhất làm tròn 4 chữ số thập phân
            else:  # zoom out
                self.zoom_factor = max(self.min_zoom, self.zoom_factor / self.ZOOM_RATIO)
                self.zoom_factor = round(self.zoom_factor, 4)  # Thống nhất làm tròn 4 chữ số thập phân
            
            # Áp dụng zoom mới
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Thống nhất làm tròn
            self.simulation.scale = new_scale  # Cập nhật scale
            
            # Khôi phục vị trí thực của tất cả robot
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Khôi phục vị trí thực của các điểm đường đi nếu có
            if path_points_real or hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
                for i, real_x, real_y in path_points_real:
                    if i < len(self.path_manager.waypoints):
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        self.path_manager.waypoints[i] = (new_pixel_x, new_pixel_y)
                
                # Cập nhật waypoints_real trong path_manager
                if hasattr(self.path_manager, 'waypoints_real'):
                    self.path_manager.waypoints_real = []
                    for wx, wy in self.path_manager.waypoints:
                        real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                        self.path_manager.waypoints_real.append((real_x, real_y))
            
            # Thay vì gọi update_all_beam_distances, sử dụng phương pháp thống nhất
            self.simulation.update_robot_sizes()
            self.update_beam_distances_from_real()
            
            # Vẽ lại canvas
            self.update_canvas()
    
    def on_zoom_in(self, event):
        """Zoom in cho Linux"""
        self.zoom_in()
        return "break"  # Ngăn chặn sự kiện lan truyền
    
    def on_zoom_out(self, event):
        """Zoom out cho Linux"""
        self.zoom_out()
        return "break"  # Ngăn chặn sự kiện lan truyền
    
    def zoom_in(self):
        """Phóng to"""
        if self.zoom_factor < self.max_zoom:
            # Lưu vị trí thực của tất cả robot
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Cập nhật hệ số zoom chính xác hơn (đổi 2 thành 4 chữ số thập phân)
            self.zoom_factor = min(self.max_zoom, self.zoom_factor * self.ZOOM_RATIO)
            self.zoom_factor = round(self.zoom_factor, 4)  # Tăng độ chính xác
            
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Tăng độ chính xác
            self.simulation.scale = new_scale
            
            # Cập nhật kích thước robot
            self.simulation.update_robot_sizes()
            
            # Khôi phục vị trí thực của robot
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Cập nhật các thông số chùm tia dựa trên khoảng cách thực
            self.update_beam_distances_from_real()
            
            # Cập nhật canvas
            self.update_canvas()

    # Sửa phương thức zoom_out()
    def zoom_out(self):
        """Thu nhỏ canvas"""
        # Tính mức zoom tối thiểu để hiển thị đủ 4x4m
        min_zoom = max(0.8, self.min_zoom)
        
        if self.zoom_factor > min_zoom:
            # Lưu vị trí thực của tất cả robot
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Cập nhật hệ số zoom và làm tròn để tránh sai số
            self.zoom_factor = max(min_zoom, self.zoom_factor / self.ZOOM_RATIO)
            self.zoom_factor = round(self.zoom_factor, 4)  # Thống nhất với zoom_in - dùng 4 chữ số thập phân
            
            # Cập nhật tỷ lệ và kích thước robot
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Thống nhất với zoom_in
            self.simulation.scale = new_scale
            
            self.simulation.update_robot_sizes()
            
            # Khôi phục vị trí thực của robot
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Sử dụng cùng một phương pháp với zoom_in
            self.update_beam_distances_from_real()
            
            # Cập nhật canvas
            self.update_canvas()

    def _apply_zoom(self, new_zoom):
        """Áp dụng mức zoom mới và cập nhật mọi thứ"""
        # Lưu vị trí thực của tất cả robot
        robot_real_positions = []
        for robot in self.simulation.robots:
            real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
            robot_real_positions.append((robot.id, real_x, real_y))
        
        # Lưu vị trí thực của các điểm đường đi nếu có
        path_points_real = []
        if hasattr(self, 'path_manager') and self.path_manager.active and hasattr(self.path_manager, 'waypoints'):
            for i, point in enumerate(self.path_manager.waypoints):
                if isinstance(point, tuple) and len(point) == 2:
                    real_x, real_y = self.simulation.pixel_to_real(point[0], point[1])
                    path_points_real.append((i, real_x, real_y))
        
        # Cập nhật scale cho simulation
        new_scale = self.BASE_SCALE * new_zoom
        self.simulation.set_scale(new_scale)
        self.zoom_factor = new_zoom
        
        # Khôi phục vị trí thực của tất cả robot
        for robot_id, real_x, real_y in robot_real_positions:
            for robot in self.simulation.robots:
                if robot.id == robot_id:
                    new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                    robot.x = new_pixel_x
                    robot.y = new_pixel_y
                    break
        
        # Khôi phục vị trí thực của các điểm đường đi nếu có
        if path_points_real and hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
            for i, real_x, real_y in path_points_real:
                if i < len(self.path_manager.waypoints):
                    new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                    self.path_manager.waypoints[i] = (new_pixel_x, new_pixel_y)
            
            # Cập nhật waypoints_real trong path_manager
            if hasattr(self.path_manager, 'waypoints_real'):
                self.path_manager.waypoints_real = []
                for wx, wy in self.path_manager.waypoints:
                    real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                    self.path_manager.waypoints_real.append((real_x, real_y))
        
        # Sau khi robot đã cập nhật kích thước, mới cập nhật beam_distance
        self.update_all_beam_distances()
        
        # Cập nhật canvas
        self.update_canvas()

    def update_all_beam_distances(self):
        """Cập nhật khoảng cách phát theo tỷ lệ chính xác với kích thước robot"""
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                # Khởi tạo giá trị cơ sở nếu chưa có
                if not hasattr(transmitter, 'base_beam_distance'):
                    transmitter.base_beam_distance = transmitter.beam_distance
                    transmitter.base_robot_size = robot.size
                    
                    # Tính tỷ lệ giữa beam_distance và robot.size khi khởi tạo
                    # Tỷ lệ này sẽ được giữ không đổi khi zoom
                    transmitter.beam_to_robot_ratio = transmitter.beam_distance / robot.size
                    print(f"Khởi tạo: Robot {robot.id}, tỷ lệ tia/kích thước = {transmitter.beam_to_robot_ratio:.2f}")
                
                # Tính khoảng cách tia mới duy trì tỷ lệ với kích thước robot
                old_distance = transmitter.beam_distance
                
                # Áp dụng tỷ lệ cố định để tính beam_distance mới
                new_distance = robot.size * transmitter.beam_to_robot_ratio
                
                # Cập nhật giá trị mới
                transmitter.beam_distance = new_distance
                
                # Debug log với định dạng đơn giản
                if abs(old_distance - new_distance) > 1:
                    print(f"Robot {robot.id}: kích thước={int(robot.size)}, tia={int(new_distance)}")

    def update_beam_distances_from_real(self):
        """Cập nhật khoảng cách chùm tia dựa trên khoảng cách thực đã lưu"""
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                # Nếu đã có khoảng cách thực
                if hasattr(transmitter, 'real_beam_distance'):
                    # Giữ nguyên khoảng cách thực chính xác
                    real_distance = transmitter.real_beam_distance
                    # Chuyển đổi từ mét sang pixel theo tỷ lệ hiện tại
                    transmitter.beam_distance = self.simulation.real_distance_to_pixel(real_distance)
                    # Debug message
                    print(f"Robot {robot.id}: beam={real_distance}m → {transmitter.beam_distance}px (scale={self.simulation.scale})")

    def open_rotation_dialog(self, event=None):
        """Mở hộp thoại nhập góc quay cho robot đang chọn"""
        if self.selected_robot:
            try:
                # Hiển thị hộp thoại yêu cầu nhập góc
                new_angle = simpledialog.askinteger("Nhập góc", 
                                                  f"Nhập góc quay cho Robot {self.selected_robot.id} (0-359):",
                                                  initialvalue=self.selected_robot.orientation,
                                                  minvalue=0, maxvalue=359)
                if new_angle is not None:
                    # Đặt góc mới cho robot
                    self.selected_robot.set_orientation(new_angle)
                    self.update_canvas()
            except Exception as e:
                print(f"Lỗi khi nhập góc: {e}")
        return "break"  # Ngăn chặn sự kiện lan truyền

    def _update_info(self):
        """Cập nhật thông tin hiển thị trên canvas"""
        # Xóa tất cả thông tin cũ
        self.delete("info_text")
        
        # Hiển thị thông tin robot đang chọn
        if self.selected_robot:
            # Thông tin cơ bản robot
            info_text = f"Robot {self.selected_robot.id}: ({self.selected_robot.x:.2f}, {self.selected_robot.y:.2f}), hướng: {self.selected_robot.orientation:.1f}°"
            self.create_text(10, 10, text=info_text, anchor=tk.NW, font=("Arial", 10, "bold"), tags="info_text")
            
            # Tìm các robot lân cận
            nearby_robots = []
            for robot in self.simulation.robots:
                if robot.id != self.selected_robot.id:
                    # Tính khoảng cách tuyệt đối
                    physical_distance = self.selected_robot.get_physical_distance_to(robot)
                    
                    # Tính góc tương đối theo cách truyền thống
                    angle_rel = self.selected_robot.get_relative_angle_to(robot)
                    
                    # Kiểm tra tín hiệu IR
                    has_signal = False
                    for receiver in self.selected_robot.receivers:
                        if robot.id in receiver.signals:
                            has_signal = True
                            break
                    
                    # Tính góc và khoảng cách theo thuật toán RPA nếu có tín hiệu
                    rpa_result = None
                    relative_coords = None
                    if has_signal:
                        rpa_result = self.selected_robot.calculate_relative_position_rpa(robot.id)
                        if rpa_result:
                            rpa_angle, rpa_distance, confidence = rpa_result
                            # Tính tọa độ tương đối từ góc RPA và khoảng cách tuyệt đối
                            relative_coords = self.selected_robot.calculate_relative_coordinates(rpa_angle, physical_distance)
                    
                    # Lưu thông tin
                    nearby_robots.append((robot.id, physical_distance, angle_rel, has_signal, rpa_result, relative_coords))
            
            # Hiển thị danh sách robot lân cận
            if nearby_robots:
                # Sắp xếp theo khoảng cách từ gần đến xa
                nearby_robots.sort(key=lambda x: x[1])
                
                self.create_text(10, 40, text="Các robot lân cận:", anchor=tk.NW, font=("Arial", 10, "bold"), tags="info_text")
                
                y_pos = 60
                for robot_info in nearby_robots:
                    robot_id, physical_distance, angle_rel, has_signal, rpa_result, relative_coords = robot_info
                    
                    # Thông tin về khoảng cách tuyệt đối
                    distance_info = f"KC: {physical_distance:.2f}m"
                    
                    # Thông tin về góc tương đối từ cả hai phương pháp
                    angle_info = f", Góc thực: {angle_rel:.1f}°"
                    
                    # Thêm góc RPA nếu có
                    rpa_angle_info = ""
                    if rpa_result:
                        rpa_angle, rpa_distance, confidence = rpa_result
                        rpa_angle_info = f", Góc RPA: {rpa_angle:.1f}°"
                    
                    # Thông tin về tọa độ tương đối
                    rel_coords_info = ""
                    if relative_coords:
                        rel_x, rel_y = relative_coords
                        rel_coords_info = f", Tọa độ tương đối: ({rel_x:.2f}, {rel_y:.2f})"
                    
                    # Trạng thái tín hiệu
                    signal_status = "✓" if has_signal else "✗"
                    
                    # Tạo thông tin hiển thị - thêm góc RPA vào
                    nearby_info = f"Robot {robot_id}: {distance_info}{angle_info}{rpa_angle_info}{rel_coords_info} {signal_status}"
                    
                    # Màu sắc dựa trên trạng thái tín hiệu
                    color = "green" if rpa_result else ("black" if has_signal else "gray")
                    
                    self.create_text(10, y_pos, text=nearby_info, anchor=tk.NW, 
                                   font=("Arial", 9), fill=color, tags="info_text")
                    y_pos += 20

    def reset_view(self):
        """Đặt lại view về trung tâm màn hình"""
        # Tính toán trung tâm của môi trường thực
        center_real_x = self.simulation.real_width / 2
        center_real_y = self.simulation.real_height / 2
        
        # Tính toán trung tâm của màn hình
        canvas_center_x = self.winfo_width() / 2
        canvas_center_y = self.winfo_height() / 2
        
        # Tính toán vị trí pixel của trung tâm môi trường
        center_pixel_x, center_pixel_y = self.simulation.real_to_pixel(center_real_x, center_real_y)
        
        # Tính offset cần di chuyển
        offset_x = canvas_center_x - center_pixel_x
        offset_y = canvas_center_y - center_pixel_y
        
        # Di chuyển tất cả robot
        for robot in self.simulation.robots:
            robot.move(offset_x, offset_y)
        
        self.update_canvas()

    def on_rotation_start(self, event):
        """Bắt đầu xoay robot khi nhấn chuột phải"""
        # Kiểm tra xem có robot được chọn không
        robot = self.simulation.get_robot_at(event.x, event.y)
        if robot:
            self.selected_robot = robot
        
        # Chỉ bắt đầu xoay nếu có robot được chọn
        if self.selected_robot:
            # Lưu vị trí bắt đầu
            self.last_x = event.x
            self.last_y = event.y
            self.rotating = True
        
    def on_rotation_drag(self, event):
        """Xoay robot khi kéo chuột phải"""
        if not self.rotating or not self.selected_robot:
            return
            
        # Tính góc mới dựa trên vị trí chuột so với tâm robot
        robot = self.selected_robot
        dx = event.x - robot.x
        dy = event.y - robot.y
        
        # Chỉ xoay nếu đủ xa từ tâm để tránh nhảy góc đột ngột
        distance = math.sqrt(dx*dx + dy*dy)
        if distance < 10:  # Ngưỡng tối thiểu
            return
        
        # Tính góc mới (theo độ)
        new_angle = math.degrees(math.atan2(dy, dx))
        
        # Đặt góc mới cho robot
        robot.set_orientation(new_angle)
        
        # Cập nhật canvas
        self.update_canvas()
        
    def on_rotation_end(self, event):
        """Kết thúc xoay robot khi thả chuột phải"""
        self.rotating = False

    def set_fixed_angle_for_selected(self, event=None):
        """Đặt góc cố định cho robot đang chọn"""
        if self.selected_robot:
            try:
                # Hiển thị hộp thoại yêu cầu nhập góc cố định
                fixed_angle = simpledialog.askinteger("Đặt góc cố định", 
                                                     f"Nhập góc cố định cho Robot {self.selected_robot.id} (0-359):",
                                                     minvalue=0, maxvalue=359,
                                                     initialvalue=0)
                if fixed_angle is not None:
                    # Đặt góc mới cho robot đã chọn
                    self.selected_robot.set_orientation(fixed_angle)
                    self.update_canvas()
            except Exception as e:
                print(f"Lỗi khi đặt góc cố định: {e}")
        return "break"  # Ngăn chặn sự kiện lan truyền
    
    def set_fixed_angle_for_all(self, event=None):
        """Đặt góc cố định cho tất cả các robot"""
        try:
            # Hiển thị hộp thoại yêu cầu nhập góc cố định
            fixed_angle = simpledialog.askinteger("Đặt góc cố định cho tất cả", 
                                                "Nhập góc cố định cho tất cả robot (0-359):",
                                                minvalue=0, maxvalue=359,
                                                initialvalue=0)
            if fixed_angle is not None:
                # Đặt góc mới cho tất cả robot
                for robot in self.simulation.robots:
                    robot.set_orientation(fixed_angle)
                self.update_canvas()
        except Exception as e:
            print(f"Lỗi khi đặt góc cố định: {e}")
        return "break"  # Ngăn chặn sự kiện lan truyền

    def on_scale_change(self, event=None):
        # khi slider beam_angle/beam_distance thay đổi thì apply ngay
        self.apply_sensor_params()

    def _animate_ir_signals(self):
        """Tạo hiệu ứng chuyển động cho tín hiệu IR"""
        # Lấy tất cả các đối tượng đường tín hiệu
        signal_lines = self.find_withtag("ir_signal")
        
        # Thay đổi kiểu đứt đoạn để tạo hiệu ứng chuyển động
        for line_id in signal_lines:
            # Lấy cấu hình hiện tại của đường
            config = self.itemconfigure(line_id)
            if 'dash' in config and config['dash'][4] != '':
                current_dash = self.itemcget(line_id, 'dash').split()
                if len(current_dash) >= 2:
                    # Dịch chuyển kiểu đứt đoạn
                    dash = int(current_dash[0])
                    gap = int(current_dash[1])
                    # Đảo vị trí dash và gap để tạo hiệu ứng chuyển động
                    self.itemconfigure(line_id, dash=(gap, dash))
        
        # Lên lịch cho frame tiếp theo nếu đang mô phỏng
        if self.simulation.running:
            self.after(150, self._animate_ir_signals)  # Cập nhật mỗi 150ms

    def on_canvas_drag(self, event):
        """Xử lý sự kiện kéo chuột khi vẽ đường đi"""
        if self.drawing_path:
            x, y = event.x, event.y
            if self.waypoints:
                # Xóa đường preview cũ nếu có
                self.delete('preview_line')
                # Vẽ đường preview mới từ điểm cuối đến vị trí chuột
                prev_x, prev_y = self.waypoints[-1]
                self.create_line(prev_x, prev_y, x, y, fill='blue', dash=(4, 2), tags='preview_line')
        elif self.dragging and self.selected_robot:
            # Tính khoảng di chuyển
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Di chuyển robot đang chọn
            self.selected_robot.move(dx, dy)
            
            # Cập nhật vị trí cuối cùng
            self.last_x = event.x
            self.last_y = event.y
            
            # Vẽ lại canvas
            self.update_canvas()
        elif self.panning:
            # Tính khoảng di chuyển
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Di chuyển tất cả robot và các đường đi (tạo hiệu ứng kéo view)
            for robot in self.simulation.robots:
                robot.move(dx, dy)
            
            # Cập nhật vị trí các waypoints nếu có
            if hasattr(self, 'path_manager') and self.path_manager.waypoints:
                for i, (wx, wy) in enumerate(self.path_manager.waypoints):
                    self.path_manager.waypoints[i] = (wx + dx, wy + dy)
                    
                # Cập nhật waypoints_real
                if hasattr(self.path_manager, 'waypoints_real'):
                    self.path_manager.waypoints_real = []
                    for wx, wy in self.path_manager.waypoints:
                        real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                        self.path_manager.waypoints_real.append((real_x, real_y))
            
            # Cập nhật vị trí cuối cùng
            self.last_x = event.x
            self.last_y = event.y
            
            # Vẽ lại canvas
            self.update_canvas()

    def on_canvas_release(self, event):
        """Xử lý sự kiện thả chuột"""
        # Xóa đường preview nếu có
        self.delete('preview_line')
        
        # Kết thúc trạng thái kéo
        self.dragging = False
        self.panning = False
        
        # Cập nhật canvas
        self.update_canvas()

    def start_drawing_path(self):
        """Bắt đầu vẽ đường đi"""
        self.drawing_path = True
        self.waypoints = []
        self.delete('waypoint')  # Xóa đường đi cũ
        self.delete('drawing_instructions')
        
        # Hiển thị thông báo hướng dẫn
        x = self.winfo_width() / 2
        y = 30
        self.create_rectangle(x-200, y-15, x+200, y+15, fill='#ffffcc', 
                            outline='#cccccc', tags='drawing_instructions')
        self.create_text(x, y, text="ĐANG VẼ ĐƯỜNG ĐI - Click chuột để đánh dấu điểm", 
                        font=("Arial", 10, "bold"), fill="red", tags='drawing_instructions')
        
        print("Bắt đầu vẽ đường đi. Click chuột để đánh dấu các điểm.")

    def finish_drawing_path(self):
        """Kết thúc vẽ đường đi"""
        self.drawing_path = False
        self.delete('drawing_instructions')
        
        if self.waypoints:
            self.path_manager.set_waypoints(self.waypoints.copy())
            print(f"Đã hoàn thành đường đi với {len(self.waypoints)} điểm.")
            
            # Chuyển đổi các điểm thành tọa độ thực (mét) để hiển thị
            real_waypoints = []
            for x, y in self.waypoints:
                real_x, real_y = self.simulation.pixel_to_real(x, y)
                real_waypoints.append((real_x, real_y))
            
            # In thông tin chi tiết về đường đi
            print("Tọa độ các điểm (mét):")
            for i, (real_x, real_y) in enumerate(real_waypoints):
                print(f"  Điểm {i+1}: ({real_x:.2f}m, {real_y:.2f}m)")

    def _draw_path(self, waypoints):
        """Vẽ đường đi từ các waypoint"""
        if not waypoints:
            return
        
        # Scale various visual elements based on zoom factor
        point_size = 5 / self.zoom_factor  # Adjusted to maintain visual size with zoom
        text_offset = 15 / self.zoom_factor
        line_width = 3 / self.zoom_factor
        dash_pattern = (int(10 / self.zoom_factor), int(4 / self.zoom_factor))
        font_size = max(int(9 / self.zoom_factor), 7)  # Min font size to ensure readability
        distance_offset = 10 / self.zoom_factor
        
        # Vẽ các điểm waypoint
        for i, (x, y) in enumerate(waypoints):
            # Vẽ điểm đánh dấu với kích thước đã điều chỉnh theo zoom
            self.create_oval(x-point_size, y-point_size, x+point_size, y+point_size, 
                             fill='red', outline='black', width=2/self.zoom_factor, tags='waypoint')
            
            # Hiển thị số thứ tự điểm
            self.create_text(x, y-text_offset, text=f"{i+1}", font=("Arial", font_size, "bold"), 
                            fill="black", tags='waypoint')
        
        # Vẽ đường nối giữa các điểm
        for i in range(1, len(waypoints)):
            prev_x, prev_y = waypoints[i-1]
            x, y = waypoints[i]
            
            self.create_line(prev_x, prev_y, x, y, fill='red', width=line_width, 
                          arrow=tk.LAST, tags='waypoint', 
                          dash=dash_pattern, capstyle=tk.ROUND)
            
            # Hiển thị khoảng cách giữa các điểm
            distance_px = math.sqrt((x-prev_x)**2 + (y-prev_y)**2)
            distance_m = self.simulation.pixel_distance_to_real(distance_px)
            mid_x = (prev_x + x) / 2
            mid_y = (prev_y + y) / 2
            self.create_text(mid_x, mid_y-distance_offset, text=f"{distance_m:.2f}m", 
                          font=("Arial", max(int(8 / self.zoom_factor), 6)), fill="blue", tags='waypoint')
        
            self.create_text(mid_x, mid_y-distance_offset, text=f"{distance_m:.2f}m", 
                          font=("Arial", max(int(8 / self.zoom_factor), 6)), fill="blue", tags='waypoint')
        
        # Nếu đang có robot di chuyển theo đường đi, đánh dấu điểm hiện tại
        highlight_size = 10 / self.zoom_factor
        if hasattr(self, 'path_manager') and self.path_manager.active:
            current_idx = self.path_manager.current_waypoint_index
            if current_idx >= 0 and current_idx < len(waypoints):
                current_x, current_y = waypoints[current_idx]
                # Vẽ một vòng tròn lớn hơn để đánh dấu điểm đang hướng tới
                self.create_oval(current_x-highlight_size, current_y-highlight_size, 
                              current_x+highlight_size, current_y+highlight_size, 
                              outline='green', width=3/self.zoom_factor, 
                              dash=(int(3/self.zoom_factor), int(3/self.zoom_factor)), 
                              tags='waypoint')

    def clear_path(self):
        """Xóa đường đi hiện tại"""
        if hasattr(self, 'path_manager'):
            self.path_manager.waypoints = []
            self.path_manager.waypoints_real = []
            self.path_manager.current_waypoint_index = 0
        
        self.drawing_path = False
        self.waypoints = []
        self.delete('waypoint')
        self.delete('drawing_instructions')
        self.update_canvas()

    def rotate_selected_clockwise(self, event=None):
        """Xoay robot đã chọn theo chiều kim đồng hồ khi nhấn phím mũi tên phải"""
        if self.selected_robot:
            # Xoay robot thêm 5 độ theo chiều kim đồng hồ
            new_angle = (self.selected_robot.orientation + 5) % 360
            self.selected_robot.set_orientation(new_angle)
            self.update_canvas()
        return "break"  # Ngăn chặn sự kiện lan truyền

    def rotate_selected_counterclockwise(self, event=None):
        """Xoay robot đã chọn ngược chiều kim đồng hồ khi nhấn phím mũi tên trái"""
        if self.selected_robot:
            # Xoay robot giảm 5 độ ngược chiều kim đồng hồ
            new_angle = (self.selected_robot.orientation - 5) % 360
            self.selected_robot.set_orientation(new_angle)
            self.update_canvas()
        return "break"  # Ngăn chặn sự kiện lan truyền

    def start_path_following(self, leader_id=None):
        """Bắt đầu cho robot đi theo đường đi và thiết lập đội hình
        Args:
            leader_id: ID của robot dẫn đầu, nếu None sẽ dùng robot được chọn
        """
        if not hasattr(self, 'path_manager'):
            print("Không có path manager")
            return
        
        # Nếu không chỉ định leader_id, sử dụng robot đang chọn
        if leader_id is None and self.selected_robot:
            leader_id = self.selected_robot.id
        
        # Nếu vẫn không có leader_id, không thể tiếp tục
        if leader_id is None:
            print("Vui lòng chọn robot dẫn đầu")
            return
        
        # Bắt đầu di chuyển theo đường đi
        success = self.path_manager.start(leader_id)
        
        if success:
            # Thiết lập thứ tự đội hình
            leader = self.simulation.get_robot_by_id(leader_id)
            if leader:
                follower_robots = [robot for robot in self.simulation.robots if robot.id != leader_id]
                # Sắp xếp theo khoảng cách đến leader
                follower_robots.sort(key=lambda r: leader.get_physical_distance_to(r))
                self.formation_order = [leader] + follower_robots
                
                print(f"Bắt đầu di chuyển theo đội hình với robot {leader_id} dẫn đầu")
        else:
            print(f"Không thể bắt đầu di chuyển với robot {leader_id}")
        
        # Cập nhật canvas
        self.update_canvas()

    def on_start_following(self):
        """Bắt đầu di chuyển theo đường đi"""
        # Lấy robot dẫn đầu từ dropdown (qua control_panel)
        if hasattr(self, 'control_panel') and hasattr(self.control_panel, 'path_leader_var'):
            leader_str = self.control_panel.path_leader_var.get()
            if leader_str:
                try:
                    leader_id = int(leader_str.split()[1])
                    # Thiết lập robot dẫn đầu và bắt đầu di chuyển
                    self.start_path_following(leader_id)
                    return
                except (ValueError, IndexError):
                    pass
        
        # Nếu không lấy được từ dropdown, sử dụng robot được chọn
        self.start_path_following()

    def _handle_follower_obstacle_avoidance(self, robot, robot_ahead, other_robots, desired_distance_px):
        """
        Handle obstacle avoidance for follower robots in the formation
        
        Args:
            robot: The current follower robot
            robot_ahead: The robot this follower should follow
            other_robots: All other robots to avoid (excluding robot_ahead)
            desired_distance_px: Target following distance in pixels
        """
        # Initialize safety parameters
        safety_margin = 1.2
        obstacle_threshold_px = robot.size + safety_margin * robot.size
        
        # Calculate primary direction vector toward the robot ahead
        dx = robot_ahead.x - robot.x
        dy = robot_ahead.y - robot.y
        global_distance = math.sqrt(dx*dx + dy*dy)
        
        # Normalize the primary direction vector
        if global_distance > 0:
            direction_x = dx / global_distance
            direction_y = dy / global_distance
        else:
            direction_x, direction_y = 0, 0
        
        # Calculate avoidance vectors from all other robots
        avoidance_x, avoidance_y = 0, 0
        avoidance_count = 0
        
        for other_robot in other_robots:
            # Skip if it's the same robot or the robot ahead
            if other_robot.id == robot.id or other_robot.id == robot_ahead.id:
                continue
            
            # Calculate distance to other robot
            other_dx = robot.x - other_robot.x
            other_dy = robot.y - other_robot.y
            other_distance = math.sqrt(other_dx*other_dx + other_dy*other_dy)
            
            # Check if robot is too close
            min_safe_distance = obstacle_threshold_px + other_robot.size/2
            
            if other_distance < min_safe_distance:
                # Calculate avoidance vector (away from obstacle)
                avoidance_factor = 1.0 - (other_distance / min_safe_distance)
                avoidance_strength = avoidance_factor * min_safe_distance * 0.5
                
                # Normalize avoidance direction
                if other_distance > 0:
                    avoidance_x += (other_dx / other_distance) * avoidance_strength
                    avoidance_y += (other_dy / other_distance) * avoidance_strength
                    avoidance_count += 1
        
        # Determine the final movement vector
        move_x, move_y = 0, 0
        move_distance = 0
        
        # First calculate the following component
        if abs(global_distance - desired_distance_px) > desired_distance_px * 0.1:
            # Calculate speed factor
            move_speed_factor = 0.3
            
            if global_distance > desired_distance_px:
                # Too far - move toward robot ahead
                move_distance = min(10.0, (global_distance - desired_distance_px) * move_speed_factor)
                move_x = direction_x * move_distance
                move_y = direction_y * move_distance
            else:
                # Too close - back away
                move_distance = min(8.0, (desired_distance_px - global_distance) * move_speed_factor)
                move_x = -direction_x * move_distance
                move_y = -direction_y * move_distance
        
        # Apply avoidance if needed
        if avoidance_count > 0:
            # Combine following direction with avoidance
            # When very close to obstacles, prioritize avoidance
            avoidance_weight = min(0.7, 0.3 + avoidance_count * 0.1)
            following_weight = 1.0 - avoidance_weight
            
            # Combine vectors
            final_x = move_x * following_weight + avoidance_x * avoidance_weight
            final_y = move_y * following_weight + avoidance_y * avoidance_weight
            
            # Apply the combined movement
            robot.move(final_x, final_y)
            print(f"Robot {robot.id} avoiding collision with other robots while following {robot_ahead.id}")
        else:
            # No obstacles - just follow the robot ahead
            robot.move(move_x, move_y)