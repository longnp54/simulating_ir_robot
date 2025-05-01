import tkinter as tk
# Sửa lại như cũ
from ui.visualization import SimulationCanvas  # không phải simulation.ui.visualization
from ui.robot_controls import RobotControlPanel
from tkinter import simpledialog
from ui.scenario_tab import ScenarioTab

class MainApplication(tk.Tk):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        self.title("Mô phỏng Robot Hồng ngoại")
        self.geometry("1000x700")
        
        # Thiết lập cho các widget căn chỉnh theo grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Tạo container chính với hai cột cố định
        main_container = tk.Frame(self)
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Cấu hình container chính
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=0)  # Cố định chiều rộng
        main_container.grid_rowconfigure(0, weight=1)
        
        # Panel canvas (bên trái)
        self.canvas_frame = tk.Frame(main_container)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")  # Đổi pack thành grid
        
        # Tạo canvas mô phỏng
        self.simulation_canvas = SimulationCanvas(self.canvas_frame, self.simulation)
        self.simulation_canvas.parent = self  # Thêm tham chiếu đến parent
        self.simulation_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Panel điều khiển (bên phải) - cố định chiều rộng 250px
        self.control_panel = RobotControlPanel(main_container, self.simulation, self.simulation_canvas)
        self.control_panel.grid(row=0, column=1, sticky="ns")
        
        # Tạo menu
        self._create_menu()
        
        # Thiết lập cập nhật định kỳ và các biến trạng thái
        self._last_state = False
        self._needs_redraw = True
        self.update_interval = 50  # ms
        self._schedule_update()
    
    def _create_menu(self):
        """Tạo menu cho ứng dụng"""
        menubar = tk.Menu(self)
        
        # Menu File
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Simulation", command=self._new_simulation)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
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
        if self.simulation.running:
            self.simulation.update()
        
        # Chỉ update canvas khi cần thiết
        needs_update = self.simulation.running or self._needs_redraw or self._last_state != self.simulation.running
        if needs_update:
            self.simulation_canvas.update_canvas()
            self._needs_redraw = False
            self._last_state = self.simulation.running
        
        # Tăng interval khi không có hoạt động
        interval = 50 if self.simulation.running else 100
        self.after(interval, self._schedule_update)
    
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

    def setup_ui(self):
        # [giữ nguyên code hiện tại]
        
        # Thêm tab mới cho kịch bản điều khiển robot
        self.scenario_tab = ScenarioTab(self.tab_control, self.simulation)
        self.tab_control.add(self.scenario_tab, text="Kịch bản Robot")