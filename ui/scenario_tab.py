import tkinter as tk
from tkinter import ttk, messagebox
import time
import math

class ScenarioTab(ttk.Frame):
    def __init__(self, master, simulation):
        super().__init__(master)
        self.simulation = simulation
        self.selected_robots = []  # Danh sách robot được chọn để điều khiển
        self.recording_path = False  # Trạng thái ghi lại đường đi
        self.path_points = []  # Lưu các điểm đường đi của chuột
        self.path_timestamps = []  # Lưu thời gian cho mỗi điểm
        
        self.playing_scenario = False  # Trạng thái phát lại kịch bản
        self.scenario_start_time = 0  # Thời điểm bắt đầu kịch bản
        
        self.setup_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện tab kịch bản"""
        # Frame chính - chia làm hai phần
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 1. Phần điều khiển bên trái
        control_frame = ttk.LabelFrame(main_frame, text="Điều khiển kịch bản")
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1.1. Chọn robot
        robot_frame = ttk.Frame(control_frame)
        robot_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(robot_frame, text="Chọn robot:").grid(row=0, column=0, sticky=tk.W)
        
        # Combobox cho mỗi robot
        self.robot_vars = []
        for i in range(3):
            robot_var = tk.StringVar()
            robot_combo = ttk.Combobox(robot_frame, textvariable=robot_var, width=10)
            robot_combo.grid(row=0, column=i+1, padx=5)
            self.robot_vars.append(robot_var)
            
            # Khi mở ứng dụng, cập nhật danh sách robot cho combobox
            self.bind("<Map>", lambda e: self.update_robot_lists())
        
        # 1.2. Nút bấm chức năng
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.record_btn = ttk.Button(button_frame, text="Bắt đầu ghi", 
                                     command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = ttk.Button(button_frame, text="Phát kịch bản",
                                  command=self.play_scenario, state=tk.DISABLED)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Xóa kịch bản",
                                   command=self.clear_scenario)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 1.3. Thông tin kịch bản
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.info_label = ttk.Label(info_frame, text="Sẵn sàng ghi kịch bản")
        self.info_label.pack(fill=tk.X)
        
        # 2. Phần canvas bên phải
        self.canvas_frame = ttk.LabelFrame(main_frame, text="Mô phỏng kịch bản")
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Cài đặt các sự kiện chuột cho canvas
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
    def update_robot_lists(self):
        """Cập nhật danh sách robot cho comboboxes"""
        if not self.simulation or not self.simulation.robots:
            return
            
        robot_ids = [f"Robot {robot.id}" for robot in self.simulation.robots]
        
        for combo_var in self.robot_vars:
            current_val = combo_var.get()
            # Cập nhật danh sách giá trị
            parent = combo_var.get_root()
            for widget in parent.winfo_children():
                if isinstance(widget, ttk.Combobox) and widget.cget("textvariable") == str(combo_var):
                    widget["values"] = robot_ids
                    # Giữ lại giá trị hiện tại nếu có
                    if current_val in robot_ids:
                        combo_var.set(current_val)
                    break
    
    def toggle_recording(self):
        """Bắt đầu/dừng ghi đường đi của chuột"""
        if not self.recording_path:
            # Kiểm tra đã chọn đủ 3 robot chưa
            selected_robots = []
            for var in self.robot_vars:
                robot_id_str = var.get()
                if not robot_id_str:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn đủ 3 robot")
                    return
                    
                # Lấy robot từ ID
                robot_id = int(robot_id_str.split(" ")[1])
                robot = None
                for r in self.simulation.robots:
                    if r.id == robot_id:
                        robot = r
                        break
                
                if robot:
                    selected_robots.append(robot)
            
            # Kiểm tra đã chọn đủ
            if len(selected_robots) != 3:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn đủ 3 robot")
                return
            
            # Kiểm tra trùng robot
            if len(set(r.id for r in selected_robots)) != 3:
                messagebox.showwarning("Cảnh báo", "Các robot được chọn phải khác nhau")
                return
                
            # Bắt đầu ghi
            self.selected_robots = selected_robots
            self.path_points = []
            self.path_timestamps = []
            self.recording_path = True
            self.record_btn.config(text="Dừng ghi")
            self.info_label.config(text="Đang ghi kịch bản... Vẽ đường đi trên canvas")
            
            # Vẽ vị trí ban đầu của các robot
            self.canvas.delete("all")
            for i, robot in enumerate(self.selected_robots):
                color = self.get_robot_color(i)
                x, y = self.simulation_to_canvas(robot.x, robot.y)
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=color, tags=f"robot_{i}")
                
        else:
            # Dừng ghi
            self.recording_path = False
            self.record_btn.config(text="Bắt đầu ghi")
            
            # Kích hoạt nút phát nếu có đường đi
            if self.path_points:
                self.play_btn.config(state=tk.NORMAL)
                self.info_label.config(text=f"Đã ghi xong: {len(self.path_points)} điểm")
            else:
                self.info_label.config(text="Không có điểm nào được ghi lại")
    
    def on_mouse_down(self, event):
        """Xử lý sự kiện nhấn chuột"""
        if self.recording_path:
            self.path_points.append((event.x, event.y))
            self.path_timestamps.append(time.time())
            
            # Vẽ điểm đầu tiên
            self.canvas.create_oval(
                event.x-2, event.y-2, event.x+2, event.y+2,
                fill="red", outline="", tags="path"
            )
    
    def on_mouse_drag(self, event):
        """Xử lý sự kiện kéo chuột"""
        if self.recording_path and self.path_points:
            # Vẽ đường nối từ điểm trước đến điểm hiện tại
            prev_x, prev_y = self.path_points[-1]
            self.canvas.create_line(
                prev_x, prev_y, event.x, event.y,
                fill="red", width=2, tags="path"
            )
            
            # Thêm điểm mới
            self.path_points.append((event.x, event.y))
            self.path_timestamps.append(time.time())
    
    def on_mouse_up(self, event):
        """Xử lý sự kiện thả chuột"""
        pass  # Không cần xử lý đặc biệt
    
    def play_scenario(self):
        """Phát lại kịch bản"""
        if not self.path_points or self.playing_scenario:
            return
            
        self.playing_scenario = True
        self.play_btn.config(state=tk.DISABLED)
        self.record_btn.config(state=tk.DISABLED)
        
        # Lưu vị trí ban đầu của các robot
        self.original_positions = [(robot.x, robot.y) for robot in self.selected_robots]
        
        # Bắt đầu phát
        self.scenario_start_time = time.time()
        self.update_scenario_playback()
    
    def update_scenario_playback(self):
        """Cập nhật vị trí robot theo thời gian thực"""
        if not self.playing_scenario:
            return
            
        current_time = time.time()
        elapsed = current_time - self.scenario_start_time
        
        # Tìm điểm tiếp theo trên đường đi dựa trên thời gian
        if not self.path_timestamps:
            self.stop_playback()
            return
            
        first_time = self.path_timestamps[0]
        last_time = self.path_timestamps[-1]
        relative_time = first_time + elapsed
        
        # Kết thúc nếu đã hết đường đi
        if relative_time >= last_time:
            self.stop_playback()
            return
        
        # Tìm 2 điểm để nội suy vị trí hiện tại
        next_idx = 0
        for i, t in enumerate(self.path_timestamps):
            if t > relative_time:
                next_idx = i
                break
        
        prev_idx = max(0, next_idx - 1)
        
        # Nội suy tuyến tính
        if next_idx > prev_idx:
            prev_time = self.path_timestamps[prev_idx]
            next_time = self.path_timestamps[next_idx]
            
            prev_point = self.path_points[prev_idx]
            next_point = self.path_points[next_idx]
            
            # Tỷ lệ nội suy
            if next_time > prev_time:
                ratio = (relative_time - prev_time) / (next_time - prev_time)
            else:
                ratio = 0
                
            # Tính vị trí nội suy
            x = prev_point[0] + ratio * (next_point[0] - prev_point[0])
            y = prev_point[1] + ratio * (next_point[1] - prev_point[1])
            
            # Cập nhật vị trí 3 robot theo quy tắc:
            # Robot 1: theo đúng đường đi
            # Robot 2: lệch 5px sang trái
            # Robot 3: lệch 5px sang phải
            canvas_points = [
                (x, y),  # Robot 1
                (x-10, y+5),  # Robot 2
                (x+10, y-5)   # Robot 3
            ]
            
            # Chuyển đổi từ tọa độ canvas sang tọa độ simulation
            for i, (cx, cy) in enumerate(canvas_points):
                sim_x, sim_y = self.canvas_to_simulation(cx, cy)
                
                # Cập nhật vị trí robot
                self.selected_robots[i].set_position(sim_x, sim_y)
                
                # Cập nhật vị trí trên canvas cho hiển thị
                robot_x, robot_y = self.simulation_to_canvas(sim_x, sim_y)
                color = self.get_robot_color(i)
                
                # Xóa điểm cũ và vẽ điểm mới
                self.canvas.delete(f"robot_{i}")
                self.canvas.create_oval(
                    robot_x-5, robot_y-5, robot_x+5, robot_y+5, 
                    fill=color, tags=f"robot_{i}"
                )
        
        # Tiếp tục cập nhật
        self.after(16, self.update_scenario_playback)  # ~60fps
    
    def stop_playback(self):
        """Dừng phát kịch bản"""
        self.playing_scenario = False
        self.play_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)
        self.info_label.config(text="Kịch bản đã hoàn tất")
    
    def clear_scenario(self):
        """Xóa kịch bản hiện tại"""
        self.path_points = []
        self.path_timestamps = []
        self.canvas.delete("path")
        self.play_btn.config(state=tk.DISABLED)
        self.info_label.config(text="Kịch bản đã được xóa")
        
        # Nếu đang phát, dừng lại
        if self.playing_scenario:
            self.playing_scenario = False
            self.record_btn.config(state=tk.NORMAL)
            
            # Khôi phục vị trí ban đầu
            for i, (orig_x, orig_y) in enumerate(self.original_positions):
                self.selected_robots[i].set_position(orig_x, orig_y)
    
    def simulation_to_canvas(self, sim_x, sim_y):
        """Chuyển đổi tọa độ từ simulation sang canvas"""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Mặc định nếu chưa có kích thước
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 400
            canvas_h = 400
            
        # Lấy kích thước của simulation
        sim_width = self.simulation.width
        sim_height = self.simulation.height
        
        # Tỷ lệ chuyển đổi
        scale_x = canvas_w / sim_width
        scale_y = canvas_h / sim_height
        
        # Chuyển đổi
        canvas_x = sim_x * scale_x
        canvas_y = sim_y * scale_y
        
        return canvas_x, canvas_y
    
    def canvas_to_simulation(self, canvas_x, canvas_y):
        """Chuyển đổi tọa độ từ canvas sang simulation"""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Mặc định nếu chưa có kích thước
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 400
            canvas_h = 400
            
        # Lấy kích thước của simulation
        sim_width = self.simulation.width
        sim_height = self.simulation.height
        
        # Tỷ lệ chuyển đổi
        scale_x = sim_width / canvas_w
        scale_y = sim_height / canvas_h
        
        # Chuyển đổi
        sim_x = canvas_x * scale_x
        sim_y = canvas_y * scale_y
        
        return sim_x, sim_y
        
    def get_robot_color(self, index):
        """Trả về màu cho robot theo index"""
        colors = ["blue", "green", "orange"]
        return colors[index % len(colors)]