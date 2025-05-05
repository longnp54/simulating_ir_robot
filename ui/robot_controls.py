import math
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox

class RobotControlPanel(tk.Frame):
    def __init__(self, parent, simulation, canvas):
        super().__init__(parent, bg='#f0f0f0', padx=10, pady=10)
        self.simulation = simulation
        self.canvas = canvas
        
        self.parent = parent
        self.simulation = simulation
        self.canvas = canvas
        
        # QUAN TRỌNG: Cố định kích thước và ngăn co lại
        self.config(width=250)
        self.pack_propagate(False)  # Ngăn frame thu nhỏ theo widget con

        # Tạo canvas và scrollbar cho khả năng cuộn
        self.canvas_container = tk.Canvas(self, bg='#f0f0f0', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas_container.yview)
        self.scrollable_frame = tk.Frame(self.canvas_container, bg='#f0f0f0')
        
        # Thiết lập scrollable_frame
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_container.configure(
                scrollregion=self.canvas_container.bbox("all")
            )
        )
        
        # Tạo cửa sổ trong canvas
        self.canvas_container.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_container.configure(yscrollcommand=self.scrollbar.set)
        
        # Đặt canvas và scrollbar vào panel
        self.canvas_container.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Cho phép cuộn bằng chuột
        self.canvas_container.bind_all("<MouseWheel>", self._on_mousewheel)

        # Tạo label
        title_label = tk.Label(self.scrollable_frame, text="Điều khiển Robot", font=("Arial", 12, "bold"), bg='#f0f0f0')
        title_label.pack(pady=(0, 10))
        
        # Frame thêm robot
        add_frame = tk.LabelFrame(self.scrollable_frame, text="Thêm Robot", padx=5, pady=5, bg='#f0f0f0')
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
        remove_frame = tk.LabelFrame(self.scrollable_frame, text="Xóa Robot", padx=5, pady=5, bg='#f0f0f0')
        remove_frame.pack(fill=tk.X, pady=5)
        
        # Combobox chọn robot
        self.robot_var = tk.StringVar()
        self.robot_combobox = ttk.Combobox(remove_frame, textvariable=self.robot_var, state="readonly")
        self.robot_combobox.pack(fill=tk.X, pady=5)
        
        # Nút xóa robot
        self.remove_btn = tk.Button(remove_frame, text="Xóa Robot", command=self.remove_robot)
        self.remove_btn.pack(fill=tk.X, pady=5)
        
        # Nút điều khiển mô phỏng
        sim_frame = tk.LabelFrame(self.scrollable_frame, text="Mô phỏng", padx=5, pady=5, bg='#f0f0f0')
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
        sensor_frame = tk.LabelFrame(self.scrollable_frame, text="Cảm biến IR", padx=5, pady=5, bg='#f0f0f0')
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

        # Thêm vào phương thức __init__ của RobotControlPanel
        zoom_frame = tk.Frame(sim_frame, bg='#f0f0f0')
        zoom_frame.pack(fill=tk.X, pady=5)

        self.zoom_in_btn = tk.Button(zoom_frame, text="Zoom In (+)", command=self.zoom_in)
        self.zoom_in_btn.grid(row=0, column=0, padx=2, pady=5, sticky="ew")

        self.zoom_out_btn = tk.Button(zoom_frame, text="Zoom Out (-)", command=self.zoom_out)
        self.zoom_out_btn.grid(row=0, column=1, padx=2, pady=5, sticky="ew")

        zoom_frame.grid_columnconfigure(0, weight=1)
        zoom_frame.grid_columnconfigure(1, weight=1)

        self.bind("<Configure>", self.on_resize)


        self.update_robot_list()

    
        # Xây dựng giao diện điều khiển
        # self._build_add_robot_controls()     # Đã được xây dựng trực tiếp trong __init__
        # self._build_remove_robot_controls()  # Đã được xây dựng trực tiếp trong __init__
        # self._build_simulation_controls()    # Đã được xây dựng trực tiếp trong __init__
        self._build_path_controls()           # Giữ lại phần vẽ đường đi
        # self._build_sensor_controls()        # Đã được xây dựng trực tiếp trong __init__
    
        # Cập nhật danh sách robot
        self.update_robot_list()

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
        
        # Cập nhật combobox chọn robot
        self.robot_combobox['values'] = robot_list
        if robot_list:
            self.robot_combobox.current(0)
        
        # Chỉ cập nhật combobox cho path_leader_combobox
        if hasattr(self, 'path_leader_combobox'):
            self.path_leader_combobox['values'] = robot_list
            if robot_list:
                self.path_leader_combobox.current(0)
    
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
    
    def toggle_beams(self):
        """Bật/tắt hiển thị chùm tia IR"""
        show_beams = self.show_beams_var.get()
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                transmitter.active = show_beams
        self.canvas.update_canvas()
    
    def toggle_signal_lines(self):
        """Bật/tắt hiển thị đường kết nối tín hiệu IR"""
        self.canvas.show_signal_lines = self.show_signal_lines_var.get()
        self.canvas.update_canvas()
    
    def on_resize(self, event):
        """Xử lý khi cửa sổ thay đổi kích thước"""
        if (event.widget == self):
            self.update_idletasks()
            self.config(width=250)  # Đảm bảo chiều rộng cố định
    
    def update_sensor_ui(self):
        """Cập nhật UI hiển thị thông số cảm biến theo tỷ lệ hiện tại"""
        if self.simulation.robots:
            try:
                sample_tx = self.simulation.robots[0].transmitters[0]
                real_distance = self.simulation.pixel_distance_to_real(sample_tx.beam_distance)
                current_value = self.beam_distance_var.get()
                new_value = round(real_distance, 1)
                if abs(current_value - new_value) > 0.01:
                    self.beam_distance_scale.config(command=None)
                    self.beam_distance_var.set(new_value)
                    self.beam_distance_scale.config(command=self.on_scale_change)
                print(f"Đã cập nhật thanh trượt khoảng cách: {new_value}m")
            except Exception as e:
                print(f"Lỗi khi cập nhật UI cảm biến: {e}")
    
    def on_scale_change(self, event=None):
        """Xử lý khi người dùng điều chỉnh thanh trượt"""
        self.apply_sensor_params()
    
    def zoom_in(self):
        """Phóng to canvas"""
        self.canvas.zoom_in()
    
    def zoom_out(self):
        """Thu nhỏ canvas"""
        self.canvas.zoom_out()
    
    def _add_robot_to_chain(self):
        """Hiển thị cửa sổ để thêm robot vào chuỗi follow"""
        dialog = tk.Toplevel(self)
        dialog.title("Chọn thứ tự robot")
        dialog.geometry("300x400")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Chọn robot theo thứ tự từ trên xuống dưới:").pack(pady=5)
        robot_frame = tk.Frame(dialog)
        robot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar = tk.Scrollbar(robot_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        robot_list = tk.Listbox(robot_frame, selectmode=tk.MULTIPLE, 
                            yscrollcommand=scrollbar.set)
        robot_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=robot_list.yview)
        for robot in self.simulation.robots:
            robot_list.insert(tk.END, f"Robot {robot.id}")
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)
        def on_confirm():
            selected_indices = robot_list.curselection()
            if not selected_indices:
                return
            robot_ids = []
            for idx in selected_indices:
                robot_text = robot_list.get(idx)
                robot_id = int(robot_text.split()[1])
                robot_ids.append(robot_id)
            self.robot_chain = robot_ids
            self.follow_manager.set_follow_chain(robot_ids)
            self._update_chain_display()
            dialog.destroy()
        confirm_btn = tk.Button(btn_frame, text="Xác nhận", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
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

    def _on_mousewheel(self, event):
        """Xử lý sự kiện cuộn chuột"""
        self.canvas_container.yview_scroll(int(-1*(event.delta/120)), "units")

    def _build_path_controls(self):
        """Tạo các điều khiển cho chức năng vẽ đường đi"""
        path_frame = tk.LabelFrame(self.scrollable_frame, text="Vẽ đường đi", padx=5, pady=5, bg='#f0f0f0')
        path_frame.pack(fill=tk.X, pady=5)
        
        # Nút bắt đầu vẽ
        self.start_draw_btn = tk.Button(path_frame, text="Bắt đầu vẽ đường đi", command=self._start_drawing)
        self.start_draw_btn.pack(fill=tk.X, pady=2)
        
        # Nút kết thúc vẽ
        self.finish_draw_btn = tk.Button(path_frame, text="Hoàn thành đường đi", command=self._finish_drawing)
        self.finish_draw_btn.pack(fill=tk.X, pady=2)
        
        # Thêm nút xóa đường đi
        self.clear_path_btn = tk.Button(path_frame, text="Xóa đường đi", command=self._clear_path)
        self.clear_path_btn.pack(fill=tk.X, pady=2)
        
        # Chọn robot dẫn đầu
        tk.Label(path_frame, text="Robot dẫn đầu:", bg='#f0f0f0').pack(anchor='w')
        self.path_leader_var = tk.StringVar()
        self.path_leader_combobox = ttk.Combobox(path_frame, textvariable=self.path_leader_var, state="readonly")
        self.path_leader_combobox.pack(fill=tk.X, pady=2)
        
        # Nút bắt đầu/dừng di chuyển
        button_frame = tk.Frame(path_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=2)
        
        self.start_path_btn = tk.Button(button_frame, text="Bắt đầu di chuyển", command=self._start_path_movement)
        self.start_path_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        self.stop_path_btn = tk.Button(button_frame, text="Dừng di chuyển", command=self._stop_path_movement)
        self.stop_path_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

    def _start_drawing(self):
        """Bắt đầu vẽ đường đi"""
        self.canvas.start_drawing_path()
        
    def _finish_drawing(self):
        """Hoàn thành vẽ đường đi"""
        self.canvas.finish_drawing_path()
        
    def _start_path_movement(self):
        """Bắt đầu di chuyển theo đường đi"""
        leader_str = self.path_leader_var.get()
        if leader_str:
            leader_id = int(leader_str.split()[1])
            if hasattr(self.canvas, 'path_manager'):
                self.canvas.path_manager.start(leader_id)
                print(f"Bắt đầu di chuyển Robot {leader_id} theo đường đã vẽ")
            else:
                print("Lỗi: path_manager chưa được khởi tạo")
        else:
            print("Vui lòng chọn robot dẫn đầu")
            
    def _stop_path_movement(self):
        """Dừng di chuyển theo đường đi"""
        self.canvas.path_manager.stop()

    def _clear_path(self):
        """Xóa đường đi hiện tại"""
        self.canvas.clear_path()
        print("Đã xóa đường đi")

