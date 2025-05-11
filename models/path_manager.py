import math
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

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
        
        # Thêm các biến để thu thập dữ liệu đánh giá
        self.path_data = {
            'timestamps': [],
            'positions': [],
            'orientations': [],
            'target_angles': [],
            'distances_to_waypoint': [],
            'rotations': [],
            'speeds': []
        }
        self.start_time = None
        self.total_distance = 0
        self.total_rotation = 0
        self.max_deviation = 0
    
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
        
        # Reset evaluation data - make sure all arrays are initialized
        self.path_data = {
            'timestamps': [],
            'positions': [],
            'orientations': [],
            'target_angles': [],
            'distances_to_waypoint': [],
            'rotations': [],
            'speeds': [],
            'waypoint_reached': []
        }
        self.start_time = time.time()
        self.total_distance = 0
        self.total_rotation = 0
        self.max_deviation = 0
        
        self.active = True
        self.current_waypoint_index = 0
        print(f"Bắt đầu di chuyển robot {self.leader_id} theo đường đi")
        return True
    
    def stop(self):
        """Dừng di chuyển theo đường đi"""
        self.active = False
        
        # Đóng cửa sổ đánh giá nếu nó đang mở
        if hasattr(self, 'eval_window') and self.eval_window.winfo_exists():
            try:
                self.eval_window.destroy()
            except Exception as e:
                print(f"Lỗi khi đóng cửa sổ đánh giá: {e}")
        
        # Hoàn thành dữ liệu đánh giá nếu đang chạy một nửa
        if len(self.path_data.get('timestamps', [])) > 0:
            # Đảm bảo arrays có cùng độ dài trước khi lưu
            max_length = max(len(self.path_data.get(key, [])) for key in 
                             ['timestamps', 'positions', 'orientations', 'target_angles', 
                              'distances_to_waypoint', 'speeds', 'rotations'])
            
            for key in ['speeds', 'rotations']:
                while len(self.path_data.get(key, [])) < max_length:
                    self.path_data.setdefault(key, []).append(0)
                    
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
        
        # Thu thập dữ liệu cho đánh giá
        current_time = time.time() - self.start_time
        self.path_data['timestamps'].append(current_time)
        self.path_data['positions'].append((leader.x, leader.y))
        self.path_data['orientations'].append(leader.orientation)
        self.path_data['distances_to_waypoint'].append(distance)
        
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
            
            # Ghi lại thời điểm đạt waypoint này
            if 'waypoint_reached' not in self.path_data:
                self.path_data['waypoint_reached'] = []
            self.path_data['waypoint_reached'].append(self.current_waypoint_index)
            
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.waypoints):
                print("✓ Đã hoàn thành toàn bộ đường đi!")
                self.active = False
                # Hiển thị đánh giá khi hoàn thành
                self.show_evaluation()
                return
        else:
            # Tính góc từ robot đến waypoint
            angle = math.degrees(math.atan2(dy, dx))
            self.path_data['target_angles'].append(angle)
            
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
                self.path_data['rotations'].append(rotation)
                self.path_data['speeds'].append(0)  # Không di chuyển khi đang xoay
                self.total_rotation += abs(rotation)
            else:
                # Di chuyển về phía waypoint
                move_dist = min(self.move_speed, distance/self.simulation.scale)
                leader.move_forward(move_dist)
                print(f"  - Di chuyển về phía trước {move_dist:.3f}m")
                self.path_data['rotations'].append(0)  # Không xoay khi đang di chuyển
                self.path_data['speeds'].append(move_dist)
                self.total_distance += move_dist
                
                # Tính toán độ lệch so với đường thẳng
                if self.current_waypoint_index > 0:
                    prev_waypoint = self.waypoints[self.current_waypoint_index - 1]
                    deviation = self._calculate_deviation_from_line(
                        prev_waypoint, 
                        (target_x, target_y), 
                        (leader.x, leader.y)
                    )
                    self.max_deviation = max(self.max_deviation, deviation)
    
    def _calculate_deviation_from_line(self, point1, point2, robot_pos):
        """Tính toán độ lệch của robot so với đường thẳng nối hai waypoints"""
        x1, y1 = point1
        x2, y2 = point2
        x0, y0 = robot_pos
        
        # Nếu hai điểm trùng nhau, độ lệch là khoảng cách từ robot đến điểm đó
        if x1 == x2 and y1 == y2:
            return math.sqrt((x0-x1)**2 + (y0-y1)**2)
        
        # Tính độ lệch theo công thức khoảng cách từ điểm đến đường thẳng
        numerator = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
        denominator = math.sqrt((y2-y1)**2 + (x2-x1)**2)
        
        return numerator / denominator

    def show_evaluation(self):
        """Hiển thị các đánh giá và biểu đồ sau khi hoàn thành đường đi"""
        # Tạo cửa sổ mới để hiển thị kết quả
        eval_window = tk.Toplevel()
        
        # Lưu trữ tham chiếu đến cửa sổ đánh giá
        self.eval_window = eval_window
        
        eval_window.title(f"Đánh giá kết quả di chuyển - Robot {self.leader_id}")
        eval_window.geometry("800x600")
        
        # Thêm xử lý cho sự kiện đóng cửa sổ
        def on_close():
            if hasattr(self, 'eval_window'):
                delattr(self, 'eval_window')
            eval_window.destroy()
            
        eval_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Tạo notebook (tabbed interface)
        notebook = ttk.Notebook(eval_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab tổng quan
        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Tổng quan")
        
        # Tính toán các số liệu thống kê
        total_time = self.path_data['timestamps'][-1] if self.path_data['timestamps'] else 0
        avg_speed = self.total_distance / total_time if total_time > 0 else 0
        path_length_m = self.total_distance  # đã ở đơn vị mét
        num_rotations = sum(1 for r in self.path_data['rotations'] if abs(r) > 0)
        
        # Hiển thị các số liệu thống kê
        stats_frame = ttk.LabelFrame(overview_tab, text="Thống kê di chuyển")
        stats_frame.pack(fill='x', expand=False, padx=10, pady=10)
        
        ttk.Label(stats_frame, text=f"Tổng thời gian: {total_time:.2f} giây").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Quãng đường đi được: {path_length_m:.2f} mét").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Vận tốc trung bình: {avg_speed:.4f} m/s").grid(row=2, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Tổng góc đã xoay: {self.total_rotation:.1f}°").grid(row=0, column=1, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Số lần xoay: {num_rotations}").grid(row=1, column=1, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Độ lệch tối đa: {self.simulation.pixel_distance_to_real(self.max_deviation):.3f} mét").grid(row=2, column=1, sticky='w', padx=10, pady=5)
        
        # Vẽ đường đi của robot so với waypoints
        self._create_path_plot(overview_tab)
        
        # Tab Vận tốc & Góc xoay
        speed_tab = ttk.Frame(notebook)
        notebook.add(speed_tab, text="Vận tốc & Góc xoay")
        self._create_speed_rotation_plots(speed_tab)
        
        # Tab Sai số
        error_tab = ttk.Frame(notebook)
        notebook.add(error_tab, text="Sai số")
        self._create_error_plots(error_tab)
        
        # Tab phân tích điểm waypoint
        waypoint_tab = ttk.Frame(notebook)
        notebook.add(waypoint_tab, text="Phân tích waypoint")
        self._create_waypoint_analysis(waypoint_tab)
        
        # Nút xuất dữ liệu 
        export_button = ttk.Button(eval_window, text="Xuất dữ liệu", command=self._export_data)
        export_button.pack(side='right', padx=10, pady=10)
    
    def _create_path_plot(self, parent):
        """Vẽ đường đi của robot so với waypoints"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        try:
            # Vẽ đường đi thực tế của robot
            if self.path_data['positions']:
                positions = np.array(self.path_data['positions'])
                
                # Kiểm tra và thiết lập max_y nếu không tồn tại
                max_y = 600  # Giá trị mặc định
                if hasattr(self.simulation, 'max_y'):
                    max_y = self.simulation.max_y
                elif hasattr(self.simulation, 'real_height'):
                    # Tính từ chiều cao thực
                    max_y = self.simulation.real_height * self.simulation.scale
                
                # Chuyển đổi tọa độ Y để phù hợp với hệ tọa độ Descartes
                positions_transformed = positions.copy()
                positions_transformed[:, 1] = max_y - positions_transformed[:, 1]  # Đảo ngược trục Y
                
                ax.plot(positions_transformed[:, 0], positions_transformed[:, 1], 'b-', label='Đường đi thực tế')
            
            # Vẽ các waypoints
            if self.waypoints:
                waypoints = np.array(self.waypoints)
                
                # Sử dụng cùng giá trị max_y
                waypoints_transformed = waypoints.copy()
                waypoints_transformed[:, 1] = max_y - waypoints_transformed[:, 1]  # Đảo ngược trục Y
                
                ax.plot(waypoints_transformed[:, 0], waypoints_transformed[:, 1], 'r--', label='Đường đi lý tưởng')
                ax.scatter(waypoints_transformed[:, 0], waypoints_transformed[:, 1], color='red', zorder=5, label='Waypoints')
                
                # Thêm nhãn số thứ tự cho các waypoints
                for i, (x, y) in enumerate(waypoints_transformed):
                    ax.annotate(f"{i+1}", (x, y), fontsize=10, ha='right')
            
            ax.set_title('Đường đi của robot')
            ax.set_xlabel('X (pixel)')
            ax.set_ylabel('Y (pixel)')
            ax.legend()
            ax.grid(True)
            
            # Đảm bảo tỷ lệ trục X và Y bằng nhau
            ax.set_aspect('equal', 'box')
        except Exception as e:
            # Hiển thị thông báo lỗi thay vì biểu đồ
            ax.text(0.5, 0.5, f"Lỗi khi vẽ biểu đồ: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='red')
            ax.axis('off')
            print(f"Lỗi vẽ biểu đồ: {e}")
        
        # Tạo frame để chứa biểu đồ
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Đặt biểu đồ vào frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_speed_rotation_plots(self, parent):
        """Vẽ biểu đồ vận tốc và góc xoay theo thời gian"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        try:
            # Get data and make sure we have values
            times = self.path_data.get('timestamps', [])
            if not times:
                raise ValueError("Không có dữ liệu thời gian")
                
            # Handle missing or incomplete data
            speeds = self.path_data.get('speeds', [0] * len(times))
            rotations = self.path_data.get('rotations', [0] * len(times))
            
            # Make all arrays the same length by using the shortest length
            min_length = min(len(times), len(speeds), len(rotations))
            if min_length == 0:
                raise ValueError("Mảng dữ liệu rỗng")
                
            times = times[:min_length]
            speeds = speeds[:min_length]
            rotations = rotations[:min_length]
            
            # Now plot with equal-length arrays
            ax1.plot(times, speeds, 'g-')
            ax1.set_title('Vận tốc theo thời gian')
            ax1.set_ylabel('Vận tốc (m/s)')
            ax1.grid(True)
            
            ax2.plot(times, rotations, 'm-')
            ax2.set_title('Góc xoay theo thời gian')
            ax2.set_xlabel('Thời gian (s)')
            ax2.set_ylabel('Góc xoay (độ)')
            ax2.grid(True)
            
        except Exception as e:
            # Show error message
            for ax in [ax1, ax2]:
                ax.text(0.5, 0.5, f"Lỗi khi vẽ biểu đồ: {str(e)}", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=10, color='red')
                ax.axis('off')
            print(f"Lỗi vẽ biểu đồ: {e}")
        
        plt.tight_layout()
        
        # Create frame for chart
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Add figure to frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_error_plots(self, parent):
        """Vẽ biểu đồ các sai số (khoảng cách đến waypoint, sai số góc)"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        # Get all data arrays
        times = self.path_data['timestamps']
        distances = self.path_data['distances_to_waypoint']
        
        # Make sure target_angles and orientations exist
        if 'target_angles' not in self.path_data or len(self.path_data['target_angles']) == 0:
            self.path_data['target_angles'] = [0] * len(times)
        if 'orientations' not in self.path_data or len(self.path_data['orientations']) == 0:
            self.path_data['orientations'] = [0] * len(times)
        
        target_angles = self.path_data['target_angles']
        orientations = self.path_data['orientations']
        
        # Ensure arrays for distance plot have the same length
        min_dist_length = min(len(times), len(distances))
        times_dist = times[:min_dist_length]
        distances = distances[:min_dist_length]
        
        # Ensure arrays for angle plot have the same length
        min_angle_length = min(len(times), len(target_angles), len(orientations))
        times_angle = times[:min_angle_length]
        target_angles = target_angles[:min_angle_length]
        orientations = orientations[:min_angle_length]
        
        # Chuyển từ pixel sang mét
        distances_m = [self.simulation.pixel_distance_to_real(d) for d in distances]
        ax1.plot(times_dist, distances_m, 'b-')
        ax1.set_title('Khoảng cách đến waypoint')
        ax1.set_ylabel('Khoảng cách (m)')
        ax1.grid(True)
        
        # Tính sai số góc
        angle_errors = []
        for i in range(len(target_angles)):
            diff = abs((target_angles[i] - orientations[i]) % 360)
            if diff > 180:
                diff = 360 - diff
            angle_errors.append(diff)
        
        ax2.plot(times_angle, angle_errors, 'r-')
        ax2.set_title('Sai số góc theo thời gian')
        ax2.set_xlabel('Thời gian (s)')
        ax2.set_ylabel('Sai số góc (độ)')
        ax2.grid(True)
        
        plt.tight_layout()
        
        # Tạo frame để chứa biểu đồ
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Đặt biểu đồ vào frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_waypoint_analysis(self, parent):
        """Phân tích thời gian đến từng waypoint và độ chính xác"""
        # Tạo danh sách thời gian đến từng waypoint
        waypoint_times = []
        waypoint_distances = []
        last_time = 0
        
        for i in range(len(self.waypoints)):
            if i < self.current_waypoint_index:
                # Tìm thời điểm đến waypoint này
                # (Giả sử waypoint đạt khi chuyển sang waypoint tiếp theo)
                idx = next((j for j, wp_idx in enumerate(self.path_data.get('waypoint_reached', [])) 
                           if wp_idx == i), None)
                
                if idx is not None:
                    time_to_reach = self.path_data['timestamps'][idx] - last_time
                    waypoint_times.append(time_to_reach)
                    last_time = self.path_data['timestamps'][idx]
                    
                    # Tính khoảng cách lệch khi đến waypoint
                    robot_pos = self.path_data['positions'][idx]
                    waypoint_pos = self.waypoints[i]
                    dist = math.sqrt((robot_pos[0] - waypoint_pos[0])**2 + (robot_pos[1] - waypoint_pos[1])**2)
                    waypoint_distances.append(self.simulation.pixel_distance_to_real(dist))
        
        # Tạo bảng thông tin các waypoint
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('waypoint', 'time', 'distance')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('waypoint', text='Waypoint')
        tree.heading('time', text='Thời gian đến (s)')
        tree.heading('distance', text='Độ lệch (m)')
        
        tree.column('waypoint', width=80)
        tree.column('time', width=150)
        tree.column('distance', width=150)
        
        # Thêm dữ liệu vào bảng
        for i in range(min(len(waypoint_times), len(waypoint_distances))):
            tree.insert('', 'end', values=(
                f'Điểm {i+1}',
                f'{waypoint_times[i]:.2f}',
                f'{waypoint_distances[i]:.3f}'
            ))
        
        # Thông tin tổng quát
        if waypoint_times:
            avg_time = sum(waypoint_times) / len(waypoint_times)
            max_time = max(waypoint_times)
            min_time = min(waypoint_times)
            
            tree.insert('', 'end', values=('Trung bình', f'{avg_time:.2f}', ''))
            tree.insert('', 'end', values=('Tối đa', f'{max_time:.2f}', ''))
            tree.insert('', 'end', values=('Tối thiểu', f'{min_time:.2f}', ''))
        
        tree.pack(fill='both', expand=True)
        
        # Thanh cuộn
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
    
    def _export_data(self):
        """Xuất dữ liệu ra file csv"""
        # Đây là phương thức gốc, bạn có thể phát triển thêm
        print("Tính năng xuất dữ liệu sẽ được triển khai trong phiên bản tới.")