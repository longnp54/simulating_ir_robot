import tkinter as tk
from tkinter import ttk
from ui.visualization import SimulationCanvas
from ui.robot_controls import RobotControlPanel
from tkinter import simpledialog

class MainApplication(tk.Tk):
    def __init__(self, simulation):
        super().__init__()
        
        # Window setup
        self.title("IR Robot Simulation")
        self.geometry("1200x700")  # Ensure adequate size for both canvas and control panel
        
        # Store IDs of scheduled tasks
        self.scheduled_tasks = []
        
        # Create tab control
        self.tab_control = ttk.Notebook(self)
        self.main_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Simulation")
        self.tab_control.pack(expand=1, fill="both")
        
        # Create main frame for simulation tab and use grid instead of pack
        self.main_frame = tk.Frame(self.main_tab)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left canvas frame (expandable)
        self.canvas_frame = tk.Frame(self.main_frame)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create right control frame (fixed width)
        self.control_frame = tk.Frame(self.main_frame, width=250)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_frame.pack_propagate(False)  # Prevent shrinking
        
        # Initialize simulation
        self.simulation = simulation
        
        # Create canvas for simulation
        self.simulation_canvas = SimulationCanvas(self.canvas_frame, self.simulation)
        self.simulation_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create control panel with control_frame as parent
        self.control_panel = RobotControlPanel(self.control_frame, self.simulation, self.simulation_canvas)
        self.control_panel.pack(fill=tk.BOTH, expand=True)
        
        # Schedule periodic updates
        self._schedule_update()
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self)
        
        # File Menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Simulation", command=self._new_simulation)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=(self.quit))
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Simulation Menu
        simmenu = tk.Menu(menubar, tearoff=0)
        simmenu.add_command(label="Start", command=self._start_simulation)
        simmenu.add_command(label="Stop", command=self._stop_simulation)
        simmenu.add_command(label="Reset", command=self._reset_simulation)
        menubar.add_cascade(label="Simulation", menu=simmenu)
        
        self.config(menu=menubar)
    
    def _schedule_update(self):
        """Schedule periodic updates"""
        try:
            # Check if window still exists
            if not self.winfo_exists():
                return
            
            if self.simulation.running:
                self.simulation.update()
            
            # Update path manager if active
            if hasattr(self.simulation_canvas, 'path_manager') and self.simulation_canvas.path_manager.active:
                self.simulation_canvas.path_manager.update()
            
            # Update canvas
            self.simulation_canvas.update_canvas()
            
            # Schedule callback and save ID
            task_id = self.after(50, self._schedule_update)
            
            # Save task ID to list
            self.scheduled_tasks.append(task_id)
            # Limit list size to avoid memory overflow
            if len(self.scheduled_tasks) > 5:
                self.scheduled_tasks.pop(0)
                
        except Exception as e:
            print(f"Error in update loop: {e}")
            # Still schedule continuation if error occurs, but at a slower rate
            task_id = self.after(1000, self._schedule_update)
            self.scheduled_tasks.append(task_id)
    
    def _new_simulation(self):
        """Create new simulation"""
        self.simulation.reset()
        self.simulation_canvas.update_canvas()
    
    def _start_simulation(self):
        """Start simulation"""
        self.simulation.start()
    
    def _stop_simulation(self):
        """Stop simulation"""
        self.simulation.stop()
    
    def _reset_simulation(self):
        """Reset simulation"""
        self.simulation.reset()
        self.simulation_canvas.update_canvas()
        
    def on_window_resize(self, event=None):
        """Handle window resize"""
        # Ensure control panel remains visible
        self.update_idletasks()
        self.control_panel.config(height=self.winfo_height())
    
    def _on_close(self):
        """Handle window close - cancel all scheduled tasks"""
        print("Closing application...")
        
        # Stop path manager first (if active)
        if hasattr(self.simulation_canvas, 'path_manager'):
            self.simulation_canvas.path_manager.active = False
            self.simulation_canvas.path_manager.stop()
        
        # Stop simulation
        if hasattr(self, 'simulation'):
            self.simulation.stop()
        
        # Cancel all scheduled tasks
        for task_id in self.scheduled_tasks:
            try:
                self.after_cancel(task_id)
            except Exception as e:
                print(f"Error canceling task: {e}")
        
        # Cancel any other after callbacks that might exist
        for task_id in self.tk.call('after', 'info'):
            try:
                self.after_cancel(int(task_id))
            except Exception:
                pass
        
        # Ensure canvas is no longer updating
        if hasattr(self, 'simulation_canvas'):
            try:
                # Turn off any timers in canvas
                if hasattr(self.simulation_canvas, '_animation_after_id') and self.simulation_canvas._animation_after_id:
                    self.simulation_canvas.after_cancel(self.simulation_canvas._animation_after_id)
                    self.simulation_canvas._animation_after_id = None
            except Exception as e:
                print(f"Error stopping animation: {e}")
        
        # Clear list
        self.scheduled_tasks.clear()
        
        print("All tasks canceled, closing window...")
        # Close window
        self.destroy()