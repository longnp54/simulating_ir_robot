import tkinter as tk
from tkinter import ttk
from ui.visualization import SimulationCanvas
from ui.robot_controls import RobotControlPanel
from tkinter import simpledialog

class MainApplication(tk.Tk):
    def __init__(self, simulation):
        super().__init__()
        
        # Thiết lập cửa sổ
        self.title("Mô phỏng Robot Hồng ngoại")
        self.geometry("1200x700")  # Đảm bảo kích thước đủ rộng cho cả canvas và panel điều khiển
        
        # Lưu trữ ID của các scheduled tasks
        self.scheduled_tasks = []
        
        # Tạo tab control
        self.tab_control = ttk.Notebook(self)
        self.main_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Simulation")
        self.tab_control.pack(expand=1, fill="both")
        
        # Tạo frame chính cho tab simulation và sử dụng grid thay vì pack
        self.main_frame = tk.Frame(self.main_tab)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo khung canvas bên trái (mở rộng)
        self.canvas_frame = tk.Frame(self.main_frame)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo khung điều khiển bên phải (cố định)
        self.control_frame = tk.Frame(self.main_frame, width=250)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_frame.pack_propagate(False)  # Ngăn co lại
        
        # Khởi tạo simulation
        self.simulation = simulation
        
        # Tạo canvas cho mô phỏng
        self.simulation_canvas = SimulationCanvas(self.canvas_frame, self.simulation)
        self.simulation_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Tạo panel điều khiển với parent là control_frame
        self.control_panel = RobotControlPanel(self.control_frame, self.simulation, self.simulation_canvas)
        self.control_panel.pack(fill=tk.BOTH, expand=True)
        
        # Lên lịch cập nhật định kỳ
        self._schedule_update()
        
        # Bind sự kiện đóng cửa sổ
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_menu(self):
        """Tạo menu cho ứng dụng"""
        menubar = tk.Menu(self)
        
        # Menu File
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Simulation", command=self._new_simulation)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command= (self.quit))
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Menu Simulation
        simmenu = tk.Menu(menubar, tearoff=0)
        simmenu.add_command(label="Start", command=self._start_simulation)
        simmenu.add_command(label="Stop", command=self._stop_simulation)
        simmenu.add_command(label="Reset", command=self._reset_simulation)
        menubar.add_cascade(label="Simulation", menu=simmenu)
        
        self.config(menu=menubar)
    
    def _schedule_update(self):
        """Lên lịch cập nhật định kỳ"""
        try:
            # Kiểm tra xem cửa sổ còn tồn tại không
            if not self.winfo_exists():
                return
            
            if self.simulation.running:
                self.simulation.update()
            
            # Update path manager nếu đang hoạt động
            if hasattr(self.simulation_canvas, 'path_manager') and self.simulation_canvas.path_manager.active:
                self.simulation_canvas.path_manager.update()
            
            # Cập nhật canvas
            self.simulation_canvas.update_canvas()
            
            # Lên lịch gọi lại và lưu ID
            task_id = self.after(50, self._schedule_update)
            
            # Lưu task ID vào danh sách
            self.scheduled_tasks.append(task_id)
            # Giới hạn kích thước của danh sách để tránh tràn bộ nhớ
            if len(self.scheduled_tasks) > 5:
                self.scheduled_tasks.pop(0)
                
        except Exception as e:
            print(f"Lỗi trong vòng lặp cập nhật: {e}")
            # Vẫn lên lịch tiếp tục nếu có lỗi, nhưng với tần suất chậm hơn
            task_id = self.after(1000, self._schedule_update)
            self.scheduled_tasks.append(task_id)
    
    def _new_simulation(self):
        """Tạo mô phỏng mới"""
        self.simulation.reset()
        self.simulation_canvas.update_canvas()
    
    def _start_simulation(self):
        """Bắt đầu mô phỏng"""
        self.simulation.start()
    
    def _stop_simulation(self):
        """Dừng mô phỏng"""
        self.simulation.stop()
    
    def _reset_simulation(self):
        """Reset mô phỏng"""
        self.simulation.reset()
        self.simulation_canvas.update_canvas()
        
    def on_window_resize(self, event=None):
        """Xử lý khi thay đổi kích thước"""
        # Đảm bảo control panel vẫn hiển thị
        self.update_idletasks()
        self.control_panel.config(height=self.winfo_height())
    
    def _on_close(self):
        """Xử lý khi đóng cửa sổ - hủy tất cả scheduled tasks"""
        print("Đang đóng ứng dụng...")
        
        # Dừng path manager trước tiên (nếu đang hoạt động)
        if hasattr(self.simulation_canvas, 'path_manager'):
            self.simulation_canvas.path_manager.active = False
            self.simulation_canvas.path_manager.stop()
        
        # Dừng simulation
        if hasattr(self, 'simulation'):
            self.simulation.stop()
        
        # Hủy tất cả scheduled tasks
        for task_id in self.scheduled_tasks:
            try:
                self.after_cancel(task_id)
            except Exception as e:
                print(f"Lỗi khi hủy task: {e}")
        
        # Hủy bất kỳ after callbacks nào khác có thể tồn tại
        for task_id in self.tk.call('after', 'info'):
            try:
                self.after_cancel(int(task_id))
            except Exception:
                pass
        
        # Đảm bảo canvas không còn update
        if hasattr(self, 'simulation_canvas'):
            try:
                # Tắt bất kỳ timers nào trong canvas
                if hasattr(self.simulation_canvas, '_animation_after_id') and self.simulation_canvas._animation_after_id:
                    self.simulation_canvas.after_cancel(self.simulation_canvas._animation_after_id)
                    self.simulation_canvas._animation_after_id = None
            except Exception as e:
                print(f"Lỗi khi dừng animation: {e}")
        
        # Xóa danh sách
        self.scheduled_tasks.clear()
        
        print("Đã hủy tất cả tasks, đóng cửa sổ...")
        # Đóng cửa sổ
        self.destroy()