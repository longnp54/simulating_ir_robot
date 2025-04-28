import tkinter as tk
import math
from tkinter import simpledialog

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
        self.bind("<ButtonRelease-1>", self.on_release)
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
        
        self.selected_robot = None
        self.dragging = False
        self.panning = False  # Biến theo dõi trạng thái đang kéo view
        self.last_x = 0
        self.last_y = 0
        self.show_signal_lines = False  # Mặc định không hiển thị đường kết nối tín hiệu

    
    def update_canvas(self):
        """Cập nhật toàn bộ canvas"""
        # Xóa tất cả các đối tượng trên canvas
        self.delete("all")
        self.robot_objects.clear()  # Xóa bộ nhớ cache đối tượng robot
        
        # Vẽ lưới tọa độ
        self._draw_grid()
        
        # Vẽ tất cả robot
        for robot in self.simulation.robots:
            self._draw_robot(robot)
        
        # Vẽ các tín hiệu IR nếu đang mô phỏng
        if self.simulation.running:
            self._draw_ir_signals()
        
        # vẽ thêm info môi trường thật
        self._draw_real_world_info()
        
        # Cập nhật thông tin kích thước và scale
        self._update_info()

    
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
        
        # Vẽ chỉ báo hướng (đường kẻ hoặc tam giác nhỏ)
        angle_rad = math.radians(robot.orientation)
        direction_x = robot.x + math.sin(angle_rad) * half_size * 0.8
        direction_y = robot.y - math.cos(angle_rad) * half_size * 0.8
        self.create_line(robot.x, robot.y, direction_x, direction_y, 
                         arrow=tk.LAST, width=2, fill="black")
        
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

    def _draw_ir_signals(self):
        """Vẽ tín hiệu IR giữa các robot"""
        # Thu thập vị trí các cảm biến
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
        
        # Vẽ tất cả các tín hiệu IR hợp lệ
        from utils.ir_physics import calculate_ir_signal_strength
        
        for tx, tx_pos in tx_positions:
            for rx, rx_pos in rx_positions:
                # Bỏ qua nếu cùng robot
                if tx.robot_id == rx.robot_id:
                    continue
                    
                # Tính toán tín hiệu
                signal_strength = calculate_ir_signal_strength(
                    tx, rx, self.simulation, tx_pos=tx_pos, rx_pos=rx_pos)
                
                # THAY ĐỔI: Giảm ngưỡng hiển thị để thấy nhiều tín hiệu hơn
                if signal_strength > 8:  # Giảm từ 15 xuống 8
                    # Màu sắc dựa trên cường độ tín hiệu
                    color = self._get_signal_color(signal_strength/100)
                    
                    # Vẽ đường kết nối
                    self.create_line(tx_pos[0], tx_pos[1], rx_pos[0], rx_pos[1], 
                                    fill=color, width=1, dash=(4, 2), tags="ir_signal")
                    
                    # Tùy chọn: hiển thị giá trị cường độ
                    mid_x = (tx_pos[0] + rx_pos[0]) / 2
                    mid_y = (tx_pos[1] + rx_pos[1]) / 2
                    self.create_text(mid_x, mid_y, text=f"{signal_strength:.1f}", 
                                    fill="black", font=("Arial", 8), tags="ir_signal")

    def _get_signal_color(self, strength):
        """Chuyển đổi cường độ thành màu sắc"""
        # Từ màu vàng (#FFFF00) đến đỏ (#FF0000)
        r = 255
        g = int(255 * (1 - strength))
        b = 0
        
        # Trả về mã màu dạng hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def on_canvas_click(self, event):
        """Xử lý sự kiện click chuột trên canvas"""
        # Tìm robot tại vị trí click
        robot = self.simulation.get_robot_at(event.x, event.y)
        
        if robot:
            # Chọn robot và bắt đầu kéo robot
            self.selected_robot = robot
            self.dragging = True
            self.panning = False
            self.last_x = event.x
            self.last_y = event.y
            # Đặt focus cho canvas để nhận các sự kiện phím
            self.focus_set()
        else:
            # Nếu click vào vùng trống - bắt đầu panning
            self.selected_robot = None
            self.dragging = False
            self.panning = True  # Bắt đầu chế độ panning
            self.last_x = event.x
            self.last_y = event.y
        
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
        elif self.panning:  # Nếu đang ở chế độ panning
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
    
    def on_release(self, event):
        """Xử lý sự kiện thả chuột"""
        self.dragging = False
    
    def rotate_selected_clockwise(self, event):
        """Xoay robot được chọn theo chiều kim đồng hồ"""
        if self.selected_robot:
            self.selected_robot.rotate(15)  # Xoay 15 độ
            self.update_canvas()
    
    def rotate_selected_counterclockwise(self, event):
        """Xoay robot được chọn ngược chiều kim đồng hồ"""
        if self.selected_robot:
            self.selected_robot.rotate(-15)  # Xoay -15 độ
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
        new_scale = self.BASE_SCALE * new_zoom
        
        # Cập nhật scale cho simulation trước
        self.simulation.set_scale(new_scale)
        self.zoom_factor = new_zoom
        
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
        """Cập nhật thông tin kích thước và tỉ lệ"""
        self.delete("info_text")
        
        # Tính toán chiều cao cần thiết cho background
        bg_height = 75  # Chiều cao mặc định
        
        # Nếu có robot được chọn, cần thêm không gian để hiển thị thông tin về robot lân cận
        if self.selected_robot:
            # Đếm số lượng robot lân cận và thêm chiều cao
            nearby_robots_count = len([r for r in self.simulation.robots if r.id != self.selected_robot.id])
            if nearby_robots_count > 0:
                # Mỗi robot lân cận cần khoảng 20px chiều cao + tiêu đề
                bg_height = max(bg_height, 90 + nearby_robots_count * 20)
        
        # Hiển thị gọn gàng với nền mờ
        bg_rect = self.create_rectangle(5, 5, 350, bg_height, fill="white", stipple="gray50", 
                                      outline="gray", tags="info_text")
        
        # Thông tin môi trường cơ bản
        env_width = self.simulation.real_width
        env_height = self.simulation.real_height
        scale = int(self.simulation.scale)
        
        self.create_text(10, 10, text=f"{env_width}m × {env_height}m", 
                        anchor=tk.NW, font=("Arial", 10), tags="info_text")
        self.create_text(10, 30, text=f"{scale} px/m (×{self.zoom_factor:.1f})", 
                        anchor=tk.NW, font=("Arial", 10), tags="info_text")
        
        # Nếu có robot được chọn, hiển thị thông tin chi tiết
        if self.selected_robot:
            # Hiển thị vị trí robot được chọn
            real_x, real_y = self.simulation.pixel_to_real(self.selected_robot.x, self.selected_robot.y)
            robot_info = f"Robot {self.selected_robot.id}: ({real_x:.2f}m, {real_y:.2f}m), {self.selected_robot.orientation}°"
            self.create_text(10, 50, text=robot_info, anchor=tk.NW, 
                           font=("Arial", 10, "bold"), tags="info_text")
            
            # Tìm và hiển thị thông tin về các robot lân cận
            nearby_robots = []
            for robot in self.simulation.robots:
                if robot.id != self.selected_robot.id:
                    # Tính khoảng cách và góc tương đối
                    dx = robot.x - self.selected_robot.x
                    dy = robot.y - self.selected_robot.y
                    
                    # Khoảng cách pixel
                    distance_pixel = math.sqrt(dx*dx + dy*dy)
                    
                    # Chuyển đổi sang mét
                    distance_m = self.simulation.pixel_distance_to_real(distance_pixel)
                    
                    # Giới hạn hiển thị trong khoảng cách hợp lý (4m)
                    if distance_m <= 4.0:  # Kích thước môi trường là 4m x 4m
                        # Tính góc tuyệt đối và tương đối
                        angle_abs = ( math.degrees(math.atan2(-dy, dx))-90) % 360
                        angle_rel = (angle_abs - self.selected_robot.orientation) % 360
                        
                        # Kiểm tra có nhận được tín hiệu IR không
                        has_signal = False
                        for receiver in self.selected_robot.receivers:
                            if robot.id in receiver.signals:
                                has_signal = True
                                break
                        
                        nearby_robots.append((robot.id, distance_m, angle_abs, angle_rel, has_signal))
            
            if nearby_robots:
                # Sắp xếp theo khoảng cách từ gần đến xa
                nearby_robots.sort(key=lambda x: x[1])
                
                # Hiển thị tiêu đề
                self.create_text(10, 70, text="Các robot lân cận:", 
                               anchor=tk.NW, font=("Arial", 10, "bold"), tags="info_text")
                
                # Hiển thị thông tin của mỗi robot lân cận
                y_pos = 90
                for robot_info in nearby_robots:
                    robot_id, distance, angle_abs, angle_rel, has_signal = robot_info
                    
                    # Thêm trạng thái tín hiệu vào thông tin hiển thị
                    signal_status = "✓ (có tín hiệu)" if has_signal else "✗ (ngoài vùng phủ sóng)"
                    nearby_info = f"Robot {robot_id}: cách {distance:.2f}m, góc {angle_abs:.1f}°/{angle_rel:.1f}° {signal_status}"
                    
                    # Sử dụng màu khác để phân biệt robot có/không có tín hiệu
                    text_color = "black" if has_signal else "gray"
                    
                    self.create_text(10, y_pos, text=nearby_info, 
                                   anchor=tk.NW, font=("Arial", 9), fill=text_color,
                                   tags="info_text")
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

def on_scale_change(self, event=None):
    # khi slider beam_angle/beam_distance thay đổi thì apply ngay
    self.apply_sensor_params()