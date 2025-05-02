import tkinter as tk
from tkinter import ttk
from models.follow_manager import FollowManager

class RobotControlPanel(tk.Frame):
    def __init__(self, parent, simulation, canvas):
        super().__init__(parent, bg='#f0f0f0', padx=10, pady=10)
        self.parent = parent
        self.simulation = simulation
        self.canvas = canvas
        
        # QUAN TRỌNG: Thêm các dòng này để đảm bảo kích thước cố định
        self.config(width=250)
        self.pack_propagate(False)  # Ngăn frame thu nhỏ theo widget con
        
        # Tạo label
        title_label = tk.Label(self, text="Điều khiển Robot", font=("Arial", 12, "bold"), bg='#f0f0f0')
        title_label.pack(pady=(0, 10))
        
        # Frame thêm robot
        add_frame = tk.LabelFrame(self, text="Thêm Robot", padx=5, pady=5, bg='#f0f0f0')
        add_frame.pack(fill=tk.X, pady=5)
        
        # Nhập tọa độ
        coord_frame = tk.Frame(add_frame, bg='#f0f0f0')
        coord_frame.pack(fill=tk.X)
        
        # Cập nhật phần nhập tọa độ robot
        tk.Label(coord_frame, text="X (m):", bg='#f0f0f0').grid(row=0, column=0, padx=5, pady=5)
        self.x_entry = tk.Entry(coord_frame, width=5)
        self.x_entry.grid(row=0, column=1, padx=5, pady=5)
        self.x_entry.insert(0, "0.4")  # giá trị mặc định bằng mét

        tk.Label(coord_frame, text="Y (m):", bg='#f0f0f0').grid(row=0, column=2, padx=5, pady=5)
        self.y_entry = tk.Entry(coord_frame, width=5)
        self.y_entry.grid(row=0, column=3, padx=5, pady=5)
        self.y_entry.insert(0, "0.4")  # giá trị mặc định bằng mét
        
        # Nút thêm robot
        self.add_btn = tk.Button(add_frame, text="Thêm Robot", command=self.add_robot)
        self.add_btn.pack(fill=tk.X, pady=5)
        
        # Frame xóa robot
        remove_frame = tk.LabelFrame(self, text="Xóa Robot", padx=5, pady=5, bg='#f0f0f0')
        remove_frame.pack(fill=tk.X, pady=5)
        
        # Combobox chọn robot
        self.robot_var = tk.StringVar()
        self.robot_combobox = ttk.Combobox(remove_frame, textvariable=self.robot_var, state="readonly")
        self.robot_combobox.pack(fill=tk.X, pady=5)
        
        # Nút xóa robot
        self.remove_btn = tk.Button(remove_frame, text="Xóa Robot", command=self.remove_robot)
        self.remove_btn.pack(fill=tk.X, pady=5)
        
        # Nút điều khiển mô phỏng
        sim_frame = tk.LabelFrame(self, text="Mô phỏng", padx=5, pady=5, bg='#f0f0f0')
        sim_frame.pack(fill=tk.X, pady=5)
        
        buttons_frame = tk.Frame(sim_frame, bg='#f0f0f0')
        buttons_frame.pack(fill=tk.X)
        
        self.start_btn = tk.Button(buttons_frame, text="Start", command=self.start_simulation)
        self.start_btn.grid(row=0, column=0, padx=2, pady=5, sticky="ew")
        
        self.stop_btn = tk.Button(buttons_frame, text="Stop", command=self.stop_simulation)
        self.stop_btn.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        
        self.reset_btn = tk.Button(buttons_frame, text="Reset", command=self.reset_simulation)
        self.reset_btn.grid(row=0, column=2, padx=2, pady=5, sticky="ew")
        
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        buttons_frame.grid_columnconfigure(2, weight=1)
        
        # Thêm điều khiển cảm biến
        sensor_frame = tk.LabelFrame(self, text="Cảm biến IR", padx=5, pady=5, bg='#f0f0f0')
        sensor_frame.pack(fill=tk.X, pady=5)
        
        # Điều chỉnh góc phát
        tk.Label(sensor_frame, text="Góc phát (°):", bg='#f0f0f0').pack(anchor='w')
        self.beam_angle_var = tk.IntVar(value=60)  # Tăng từ 45 lên 60
        self.beam_angle_scale = tk.Scale(sensor_frame, from_=10, to=180, 
                                       orient=tk.HORIZONTAL, resolution=5,
                                       variable=self.beam_angle_var, 
                                       command=self.on_scale_change,
                                       bg='#f0f0f0')
        self.beam_angle_scale.pack(fill=tk.X)
        
        # Điều chỉnh khoảng cách phát
        tk.Label(sensor_frame, text="Khoảng cách phát (m):", bg='#f0f0f0').pack(anchor='w')
        # Chuyển đổi giá trị mặc định 200px sang mét
        self.beam_distance_var = tk.DoubleVar(value=0.8)  # 0.8m = 200px với scale=250
        self.beam_distance_scale = tk.Scale(sensor_frame, from_=0.2, to=2.0, 
                                          orient=tk.HORIZONTAL, resolution=0.1,
                                          variable=self.beam_distance_var, 
                                          command=self.on_scale_change,
                                          bg='#f0f0f0')
        self.beam_distance_scale.pack(fill=tk.X)
        
        # Điều chỉnh góc lệch cho transmitter ngoài cùng
        tk.Label(sensor_frame, text="Góc lệch ngoài cùng (°):", bg='#f0f0f0').pack(anchor='w')
        self.beam_offset_var = tk.IntVar(value=15)  # Thay đổi từ 30° thành 15°
        self.beam_offset_scale = tk.Scale(sensor_frame, from_=0, to=60, 
                                      orient=tk.HORIZONTAL, resolution=5,
                                      variable=self.beam_offset_var, 
                                      command=self.on_scale_change,
                                      bg='#f0f0f0')
        self.beam_offset_scale.pack(fill=tk.X)
        
        # Điều chỉnh góc nhận
        tk.Label(sensor_frame, text="Góc nhận (°):", bg='#f0f0f0').pack(anchor='w')
        self.viewing_angle_var = tk.IntVar(value=80)  # Tăng từ 60 lên 80
        self.viewing_angle_scale = tk.Scale(sensor_frame, from_=10, to=180, 
                                           orient=tk.HORIZONTAL, resolution=5,
                                           variable=self.viewing_angle_var, 
                                           command=self.on_scale_change,
                                           bg='#f0f0f0')
        self.viewing_angle_scale.pack(fill=tk.X)
        
        # Nút áp dụng thông số cảm biến
        self.apply_sensor_btn = tk.Button(sensor_frame, text="Áp dụng thông số", 
                                        command=self.apply_sensor_params)
        self.apply_sensor_btn.pack(fill=tk.X, pady=5)
        
        # Nút hiển thị/ẩn chùm tia
        self.show_beams_var = tk.BooleanVar(value=True)
        self.show_beams_check = tk.Checkbutton(sensor_frame, text="Hiển thị chùm tia", 
                                             variable=self.show_beams_var,
                                             command=self.toggle_beams,
                                             bg='#f0f0f0')
        self.show_beams_check.pack(anchor='w')

        # Thêm vào sau checkbox "Hiển thị chùm tia" trong phương thức __init__ của RobotControlPanel

        # Đã vô hiệu hóa tùy chọn hiển thị đường tín hiệu
        # self.show_signal_lines_var = tk.BooleanVar(value=False)
        # self.canvas.show_signal_lines = False
        
        # Thêm vào phương thức __init__ của RobotControlPanel
        zoom_frame = tk.Frame(sim_frame, bg='#f0f0f0')
        zoom_frame.pack(fill=tk.X, pady=5)

        self.zoom_in_btn = tk.Button(zoom_frame, text="Zoom In (+)", command=self.zoom_in)
        self.zoom_in_btn.grid(row=0, column=0, padx=2, pady=5, sticky="ew")

        self.zoom_out_btn = tk.Button(zoom_frame, text="Zoom Out (-)", command=self.zoom_out)
        self.zoom_out_btn.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        zoom_frame.grid_columnconfigure(0, weight=1)
        zoom_frame.grid_columnconfigure(1, weight=1)

        # Cập nhật danh sách robot
        self.update_robot_list()
        
        self.bind("<Configure>", self.on_resize)

        # Khởi tạo FollowManager
        self.follow_manager = FollowManager(simulation)
        
        # Thêm frame điều khiển follow
        self.follow_frame = tk.LabelFrame(self, text="Mô phỏng Follow")
        self.follow_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self._build_follow_controls()
    
    def add_robot(self):
        """Thêm robot mới vào mô phỏng"""
        try:
            # Lấy tọa độ từ người dùng (đã nhập bằng mét)
            x_m = float(self.x_entry.get())
            y_m = float(self.y_entry.get())
            
            # Giới hạn trong phạm vi môi trường
            x_m = max(0, min(self.simulation.real_width, x_m))
            y_m = max(0, min(self.simulation.real_height, y_m))
            
            # Chuyển đổi từ mét sang pixel
            x_pixel, y_pixel = self.simulation.real_to_pixel(x_m, y_m)
            
            # Tạo robot mới tại vị trí đã chuyển đổi
            robot = self.simulation.add_robot(x_pixel, y_pixel)
            
            # Cập nhật danh sách robot
            self.update_robot_list()
            
            # Áp dụng thông số cảm biến hiện tại cho robot mới
            angle = self.beam_angle_var.get()
            viewing_angle = self.viewing_angle_var.get()  # Lấy góc nhận từ thanh trượt
            real_distance = self.beam_distance_var.get()
            pixel_distance = self.simulation.real_distance_to_pixel(real_distance)
            
            # Áp dụng thông số cho tất cả transmitter của robot mới
            for transmitter in robot.transmitters:
                # Lưu khoảng cách thực
                transmitter.real_beam_distance = real_distance
                # Áp dụng thông số pixel
                transmitter.set_beam_parameters(angle, pixel_distance, self.simulation)


            # Trong phương thức add_robot(), sau đoạn áp dụng thông số góc và khoảng cách:
            offset_angle = self.beam_offset_var.get()  # Lấy góc lệch hiện tại

            # Áp dụng góc lệch cho các transmitter - đồng bộ với robot.py
            for transmitter in robot.transmitters:
                if transmitter.side == 0:  # top
                    if transmitter.position_index == 0:
                        transmitter.beam_direction_offset = -offset_angle
                    else:
                        transmitter.beam_direction_offset = +offset_angle
                elif transmitter.side == 1:  # right
                    if transmitter.position_index == 0:
                        transmitter.beam_direction_offset = -offset_angle
                    else:
                        transmitter.beam_direction_offset = +offset_angle
                elif transmitter.side == 2:  # bottom
                    if transmitter.position_index == 0:
                        transmitter.beam_direction_offset = +offset_angle
                    else:
                        transmitter.beam_direction_offset = -offset_angle
                elif transmitter.side == 3:  # left
                    if transmitter.position_index == 0:
                        transmitter.beam_direction_offset = +offset_angle
                    else:
                        transmitter.beam_direction_offset = -offset_angle
            
            # Áp dụng cho receiver
            for receiver in robot.receivers:
                receiver.real_max_distance = real_distance
                receiver.set_receiver_parameters(viewing_angle, pixel_distance, self.simulation)
            
            # Cập nhật canvas
            self.canvas.update_canvas()
            
        except ValueError:
            # Hiển thị thông báo lỗi nếu nhập không hợp lệ
            print("Lỗi: Vui lòng nhập tọa độ hợp lệ!")
    
    def remove_robot(self):
        """Xóa robot khỏi mô phỏng"""
        selection = self.robot_var.get()
        if selection:
            robot_id = int(selection.split()[1])  # Lấy ID từ chuỗi "Robot X"
            self.simulation.remove_robot(robot_id)
            self.canvas.update_canvas()
            self.update_robot_list()
    
    def update_robot_list(self):
        """Cập nhật danh sách robot trong combobox"""
        robot_list = [f"Robot {robot.id}" for robot in self.simulation.robots]
        self.robot_combobox['values'] = robot_list
        if robot_list:
            self.robot_combobox.current(0)
    
    def start_simulation(self):
        """Bắt đầu mô phỏng"""
        self.simulation.start()
    
    def stop_simulation(self):
        """Dừng mô phỏng"""
        self.simulation.stop()
    
    def reset_simulation(self):
        """Đặt lại mô phỏng"""
        self.simulation.reset()
        self.canvas.update_canvas()
        self.update_robot_list()
    
    def apply_sensor_params(self):
        """Áp dụng các thông số cảm biến cho tất cả robot"""
        angle = self.beam_angle_var.get()
        real_distance = self.beam_distance_var.get()
        pixel_distance = self.simulation.real_distance_to_pixel(real_distance)
        offset_angle = self.beam_offset_var.get()
        viewing_angle = self.viewing_angle_var.get()
        
        print(f"Áp dụng thông số: góc phát={angle}°, góc nhận={viewing_angle}°, khoảng cách={real_distance}m, góc lệch={offset_angle}°")
        
        for robot in self.simulation.robots:
            # Áp dụng cho transmitter
            for transmitter in robot.transmitters:
                # Lưu khoảng cách thực
                transmitter.real_beam_distance = real_distance
                # Áp dụng thông số góc và khoảng cách
                transmitter.set_beam_parameters(angle, pixel_distance, self.simulation)
                
                # Sửa lại phần áp dụng góc lệch để đồng bộ
                if transmitter.side == 0:  # top
                    if transmitter.position_index == 0:  # left
                        transmitter.beam_direction_offset = -offset_angle
                    else:  # right (position_index == 1)
                        transmitter.beam_direction_offset = +offset_angle
                elif transmitter.side == 1:  # right
                    if transmitter.position_index == 0:  # top
                        transmitter.beam_direction_offset = -offset_angle
                    else:  # bottom (position_index == 1)
                        transmitter.beam_direction_offset = +offset_angle
                elif transmitter.side == 2:  # bottom
                    if transmitter.position_index == 0:  # left
                        transmitter.beam_direction_offset = +offset_angle
                    else:  # right (position_index == 1)
                        transmitter.beam_direction_offset = -offset_angle
                elif transmitter.side == 3:  # left
                    if transmitter.position_index == 0:  # top
                        transmitter.beam_direction_offset = offset_angle
                    else:  # bottom (position_index == 1)
                        transmitter.beam_direction_offset = -offset_angle
            
            # Thêm đoạn áp dụng cho receiver - sử dụng góc nhận từ thanh trượt
            for receiver in robot.receivers:
                receiver.real_max_distance = real_distance
                receiver.set_receiver_parameters(viewing_angle, pixel_distance, self.simulation)
        
        self.canvas.update_canvas()
    
    def toggle_beams(self):
        """Bật/tắt hiển thị chùm tia IR"""
        show_beams = self.show_beams_var.get()
        
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                transmitter.active = show_beams
        
        self.canvas.update_canvas()

    # Thêm phương thức toggle_signal_lines vào lớp RobotControlPanel
    def toggle_signal_lines(self):
        """Bật/tắt hiển thị đường kết nối tín hiệu IR"""
        # Chỉ cần cập nhật canvas để áp dụng thay đổi
        self.canvas.show_signal_lines = self.show_signal_lines_var.get()
        self.canvas.update_canvas()
    
    def on_resize(self, event):
        """Xử lý khi cửa sổ thay đổi kích thước"""
        if (event.widget == self):
            # Đảm bảo control panel vẫn hiển thị
            self.update_idletasks()
            self.config(width=250)  # Đảm bảo chiều rộng cố định

    def update_sensor_ui(self):
        """Cập nhật UI hiển thị thông số cảm biến theo tỷ lệ hiện tại"""
        # Kiểm tra nếu có robots
        if self.simulation.robots:
            try:
                # Lấy khoảng cách phát của robot đầu tiên làm mẫu
                sample_tx = self.simulation.robots[0].transmitters[0]
                real_distance = self.simulation.pixel_distance_to_real(sample_tx.beam_distance)
                
                # Cập nhật giá trị hiển thị trên thanh trượt (không gây sự kiện đệ quy)
                current_value = self.beam_distance_var.get()
                new_value = round(real_distance, 1)
                
                # Chỉ cập nhật nếu giá trị thay đổi đáng kể
                if abs(current_value - new_value) > 0.01:
                    # Tạm dừng gọi lại để tránh sự kiện đệ quy
                    self.beam_distance_scale.config(command=None)
                    self.beam_distance_var.set(new_value)
                    # Khôi phục gọi lại
                    self.beam_distance_scale.config(command=self.on_scale_change)
                    
                print(f"Đã cập nhật thanh trượt khoảng cách: {new_value}m")
                
            except Exception as e:
                print(f"Lỗi khi cập nhật UI cảm biến: {e}")

    def on_scale_change(self, event=None):
        """Xử lý khi người dùng điều chỉnh thanh trượt"""
        # Tự động áp dụng thông số khi thanh trượt thay đổi
        self.apply_sensor_params()

    def zoom_in(self):
        """Phóng to canvas"""
        self.canvas.zoom_in()

    def zoom_out(self):
        """Thu nhỏ canvas"""
        self.canvas.zoom_out()

    def _build_follow_controls(self):
        """Tạo các điều khiển cho tính năng robot follow"""
        # Frame chính
        frame = self.follow_frame
        
        # Label hướng dẫn
        tk.Label(frame, text="Thứ tự robot follow:").pack(anchor="w", padx=5, pady=2)
        
        # Tạo frame chứa các dropdown để chọn thứ tự robot
        chain_frame = tk.Frame(frame)
        chain_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Khởi tạo danh sách robot để chọn
        self.robot_chain = []
        
        # Nút thêm robot vào chuỗi
        add_btn = tk.Button(chain_frame, text="+", width=3, command=self._add_robot_to_chain)
        add_btn.pack(side=tk.LEFT, padx=2)
        
        # Label hiển thị chuỗi robot hiện tại
        self.chain_label = tk.Label(frame, text="Chưa thiết lập chuỗi robot", fg="gray")
        self.chain_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Frame thiết lập khoảng cách
        dist_frame = tk.Frame(frame)
        dist_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(dist_frame, text="Khoảng cách (m):").pack(side=tk.LEFT)
        self.distance_var = tk.DoubleVar(value=0.5)
        distance_entry = tk.Spinbox(dist_frame, from_=0.3, to=1.0, increment=0.1, 
                                textvariable=self.distance_var, width=5)
        distance_entry.pack(side=tk.LEFT, padx=5)
        distance_entry.bind("<Return>", lambda e: self._update_distance())
        
        # Checkbox tự động di chuyển leader
        self.auto_leader_var = tk.BooleanVar(value=False)
        auto_leader_cb = tk.Checkbutton(frame, text="Tự động di chuyển robot dẫn đầu", 
                                    variable=self.auto_leader_var)
        auto_leader_cb.pack(anchor="w", padx=5, pady=2)
        
        # Nút điều khiển
        control_frame = tk.Frame(frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.start_follow_btn = tk.Button(control_frame, text="Bắt đầu", command=self._start_follow)
        self.start_follow_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.stop_follow_btn = tk.Button(control_frame, text="Dừng", command=self._stop_follow)
        self.stop_follow_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def _add_robot_to_chain(self):
        """Hiển thị cửa sổ để thêm robot vào chuỗi follow"""
        dialog = tk.Toplevel(self)
        dialog.title("Chọn thứ tự robot")
        dialog.geometry("300x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame chỉ dẫn
        tk.Label(dialog, text="Chọn robot theo thứ tự từ trên xuống dưới:").pack(pady=5)
        
        # Danh sách các robot hiện có
        robot_frame = tk.Frame(dialog)
        robot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar cho listbox
        scrollbar = tk.Scrollbar(robot_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox hiển thị các robot
        robot_list = tk.Listbox(robot_frame, selectmode=tk.MULTIPLE, 
                            yscrollcommand=scrollbar.set)
        robot_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=robot_list.yview)
        
        # Thêm các robot vào listbox
        for robot in self.simulation.robots:
            robot_list.insert(tk.END, f"Robot {robot.id}")
        
        # Frame chứa nút
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Nút xác nhận
        def on_confirm():
            selected_indices = robot_list.curselection()
            if not selected_indices:
                return
                
            # Xây dựng chuỗi robot mới
            robot_ids = []
            for idx in selected_indices:
                robot_text = robot_list.get(idx)
                robot_id = int(robot_text.split()[1])
                robot_ids.append(robot_id)
            
            # Cập nhật chuỗi và hiển thị
            self.robot_chain = robot_ids
            self.follow_manager.set_follow_chain(robot_ids)
            self._update_chain_display()
            dialog.destroy()
        
        confirm_btn = tk.Button(btn_frame, text="Xác nhận", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Nút hủy
        cancel_btn = tk.Button(btn_frame, text="Hủy", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def _update_chain_display(self):
        """Cập nhật hiển thị chuỗi robot follow"""
        if not self.robot_chain:
            self.chain_label.config(text="Chưa thiết lập chuỗi robot", fg="gray")
        else:
            chain_text = " → ".join([f"Robot {id}" for id in self.robot_chain])
            self.chain_label.config(text=chain_text, fg="blue")

    def _update_distance(self):
        """Cập nhật khoảng cách follow"""
        distance = self.distance_var.get()
        self.follow_manager.set_follow_distance(distance)

    def _start_follow(self):
        """Bắt đầu kịch bản follow"""
        # Cập nhật các thiết lập
        self.follow_manager.set_follow_distance(self.distance_var.get())
        self.follow_manager.enable_leader_auto_movement(self.auto_leader_var.get())
        
        # Bắt đầu kịch bản
        if self.follow_manager.start():
            self.start_follow_btn.config(state=tk.DISABLED)
            self.stop_follow_btn.config(state=tk.NORMAL)
        else:
            import tkinter.messagebox as msgbox
            msgbox.showwarning("Lỗi", "Không thể bắt đầu kịch bản follow.\nHãy chắc chắn đã chọn ít nhất 2 robot.")

    def _stop_follow(self):
        """Dừng kịch bản follow"""
        self.follow_manager.stop()
        self.start_follow_btn.config(state=tk.NORMAL)
        self.stop_follow_btn.config(state=tk.DISABLED)
