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
        
        # IMPORTANT: Fix size and prevent shrinking
        self.config(width=250)
        self.pack_propagate(False)  # Prevent frame from shrinking to fit child widgets

        # Create canvas and scrollbar for scrolling capability
        self.canvas_container = tk.Canvas(self, bg='#f0f0f0', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas_container.yview)
        self.scrollable_frame = tk.Frame(self.canvas_container, bg='#f0f0f0')
        
        # Set up scrollable_frame
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_container.configure(
                scrollregion=self.canvas_container.bbox("all")
            )
        )
        
        # Create window in canvas
        self.canvas_container.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_container.configure(yscrollcommand=self.scrollbar.set)
        
        # Place canvas and scrollbar in panel
        self.canvas_container.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Allow scrolling with mouse wheel
        self.canvas_container.bind_all("<MouseWheel>", self._on_mousewheel)

        # Create label
        title_label = tk.Label(self.scrollable_frame, text="Robot Controls", font=("Arial", 12, "bold"), bg='#f0f0f0')
        title_label.pack(pady=(0, 10))
        
        # Add robot frame
        add_frame = tk.LabelFrame(self.scrollable_frame, text="Add Robot", padx=5, pady=5, bg='#f0f0f0')
        add_frame.pack(fill=tk.X, pady=5)
        
        # Coordinate input
        coord_frame = tk.Frame(add_frame, bg='#f0f0f0')
        coord_frame.pack(fill=tk.X)
        
        # Update robot coordinate input section
        tk.Label(coord_frame, text="X (m):", bg='#f0f0f0').grid(row=0, column=0, padx=5, pady=5)
        self.x_entry = tk.Entry(coord_frame, width=5)
        self.x_entry.grid(row=0, column=1, padx=5, pady=5)
        self.x_entry.insert(0, "0.4")  # default value in meters

        tk.Label(coord_frame, text="Y (m):", bg='#f0f0f0').grid(row=0, column=2, padx=5, pady=5)
        self.y_entry = tk.Entry(coord_frame, width=5)
        self.y_entry.grid(row=0, column=3, padx=5, pady=5)
        self.y_entry.insert(0, "0.4")  # default value in meters
        
        # Add robot button
        self.add_btn = tk.Button(add_frame, text="Add Robot", command=self.add_robot)
        self.add_btn.pack(fill=tk.X, pady=5)
        
        # Remove robot frame
        remove_frame = tk.LabelFrame(self.scrollable_frame, text="Remove Robot", padx=5, pady=5, bg='#f0f0f0')
        remove_frame.pack(fill=tk.X, pady=5)
        
        # Robot selection combobox
        self.robot_var = tk.StringVar()
        self.robot_combobox = ttk.Combobox(remove_frame, textvariable=self.robot_var, state="readonly")
        self.robot_combobox.pack(fill=tk.X, pady=5)
        
        # Remove robot button
        self.remove_btn = tk.Button(remove_frame, text="Remove Robot", command=self.remove_robot)
        self.remove_btn.pack(fill=tk.X, pady=5)
        
        # Simulation control buttons
        sim_frame = tk.LabelFrame(self.scrollable_frame, text="Simulation", padx=5, pady=5, bg='#f0f0f0')
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
        
        # Add sensor controls
        sensor_frame = tk.LabelFrame(self.scrollable_frame, text="IR Sensors", padx=5, pady=5, bg='#f0f0f0')
        sensor_frame.pack(fill=tk.X, pady=5)
        
        # Beam angle adjustment
        tk.Label(sensor_frame, text="Beam Angle (°):", bg='#f0f0f0').pack(anchor='w')
        self.beam_angle_var = tk.IntVar(value=60)  # Increased from 45 to 60
        self.beam_angle_scale = tk.Scale(sensor_frame, from_=10, to=180, 
                                       orient=tk.HORIZONTAL, resolution=5,
                                       variable=self.beam_angle_var, 
                                       command=self.on_scale_change,
                                       bg='#f0f0f0')
        self.beam_angle_scale.pack(fill=tk.X)
        
        # Beam distance adjustment
        tk.Label(sensor_frame, text="Beam Distance (m):", bg='#f0f0f0').pack(anchor='w')
        # Convert default value from 200px to meters
        self.beam_distance_var = tk.DoubleVar(value=0.8)  # 0.8m = 200px with scale=250
        self.beam_distance_scale = tk.Scale(sensor_frame, from_=0.2, to=2.0, 
                                          orient=tk.HORIZONTAL, resolution=0.1,
                                          variable=self.beam_distance_var, 
                                          command=self.on_scale_change,
                                          bg='#f0f0f0')
        self.beam_distance_scale.pack(fill=tk.X)
        
        # Outer transmitter angle offset adjustment
        tk.Label(sensor_frame, text="Outer Angle Offset (°):", bg='#f0f0f0').pack(anchor='w')
        self.beam_offset_var = tk.IntVar(value=15)  # Changed from 30° to 15°
        self.beam_offset_scale = tk.Scale(sensor_frame, from_=0, to=60, 
                                      orient=tk.HORIZONTAL, resolution=5,
                                      variable=self.beam_offset_var, 
                                      command=self.on_scale_change,
                                      bg='#f0f0f0')
        self.beam_offset_scale.pack(fill=tk.X)
        
        # Viewing angle adjustment
        tk.Label(sensor_frame, text="Viewing Angle (°):", bg='#f0f0f0').pack(anchor='w')
        self.viewing_angle_var = tk.IntVar(value=80)  # Increased from 60 to 80
        self.viewing_angle_scale = tk.Scale(sensor_frame, from_=10, to=180, 
                                           orient=tk.HORIZONTAL, resolution=5,
                                           variable=self.viewing_angle_var, 
                                           command=self.on_scale_change,
                                           bg='#f0f0f0')
        self.viewing_angle_scale.pack(fill=tk.X)
        
        # Apply sensor parameters button
        self.apply_sensor_btn = tk.Button(sensor_frame, text="Apply Parameters", 
                                        command=self.apply_sensor_params)
        self.apply_sensor_btn.pack(fill=tk.X, pady=5)
        
        # Show/hide beams button
        self.show_beams_var = tk.BooleanVar(value=True)
        self.show_beams_check = tk.Checkbutton(sensor_frame, text="Show Beams", 
                                             variable=self.show_beams_var,
                                             command=self.toggle_beams,
                                             bg='#f0f0f0')
        self.show_beams_check.pack(anchor='w')

        # Added to RobotControlPanel's __init__ method
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

    
        # Build control interface
        # self._build_add_robot_controls()     # Already built directly in __init__
        # self._build_remove_robot_controls()  # Already built directly in __init__
        # self._build_simulation_controls()    # Already built directly in __init__
        self._build_path_controls()           # Keep path drawing part
        # self._build_sensor_controls()        # Already built directly in __init__
    
        # Update robot list
        self.update_robot_list()

    def add_robot(self):
        """Add new robot to simulation"""
        try:
            # Get coordinates from user (already in meters)
            x_m = float(self.x_entry.get())
            y_m = float(self.y_entry.get())
            
            # Limit within environment bounds
            x_m = max(0, min(self.simulation.real_width, x_m))
            y_m = max(0, min(self.simulation.real_height, y_m))
            
            # Convert from meters to pixels
            x_pixel, y_pixel = self.simulation.real_to_pixel(x_m, y_m)
            
            # Create new robot at the converted position
            robot = self.simulation.add_robot(x_pixel, y_pixel)
            
            # Update robot list
            self.update_robot_list()
            
            # Apply current sensor parameters to new robot
            angle = self.beam_angle_var.get()
            viewing_angle = self.viewing_angle_var.get()  # Get viewing angle from slider
            real_distance = self.beam_distance_var.get()
            pixel_distance = self.simulation.real_distance_to_pixel(real_distance)
            
            # Apply parameters to all transmitters of new robot
            for transmitter in robot.transmitters:
                # Save real distance
                transmitter.real_beam_distance = real_distance
                # Apply pixel parameters
                transmitter.set_beam_parameters(angle, pixel_distance, self.simulation)

            # In add_robot() method, after applying angle and distance parameters:
            offset_angle = self.beam_offset_var.get()  # Get current offset angle
            # Apply offset angle to transmitters - synchronize with robot.py
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
            
            # Apply to receivers
            for receiver in robot.receivers:
                receiver.real_max_distance = real_distance
                receiver.set_receiver_parameters(viewing_angle, pixel_distance, self.simulation)
            
            # Update canvas
            self.canvas.update_canvas()
            
        except ValueError:
            # Display error message if input is invalid
            print("Error: Please enter valid coordinates!")
    
    def remove_robot(self):
        """Remove robot from simulation"""
        selection = self.robot_var.get()
        if selection:
            robot_id = int(selection.split()[1])  # Get ID from string "Robot X"
            self.simulation.remove_robot(robot_id)
            self.canvas.update_canvas()
            self.update_robot_list()
    
    def update_robot_list(self):
        """Update robot list in combobox"""
        robot_list = [f"Robot {robot.id}" for robot in self.simulation.robots]
        
        # Update robot selection combobox
        self.robot_combobox['values'] = robot_list
        if robot_list:
            self.robot_combobox.current(0)
        
        # Only update combobox for path_leader_combobox
        if hasattr(self, 'path_leader_combobox'):
            self.path_leader_combobox['values'] = robot_list
            if robot_list:
                self.path_leader_combobox.current(0)
    
    def start_simulation(self):
        """Start simulation"""
        self.simulation.start()
    
    def stop_simulation(self):
        """Stop simulation"""
        self.simulation.stop()
    
    def reset_simulation(self):
        """Reset simulation"""
        self.simulation.reset()
        self.canvas.update_canvas()
        self.update_robot_list()
    
    def apply_sensor_params(self):
        """Apply sensor parameters to all robots"""
        angle = self.beam_angle_var.get()
        real_distance = self.beam_distance_var.get()
        pixel_distance = self.simulation.real_distance_to_pixel(real_distance)
        offset_angle = self.beam_offset_var.get()
        viewing_angle = self.viewing_angle_var.get()
        print(f"Applying parameters: beam angle={angle}°, viewing angle={viewing_angle}°, distance={real_distance}m, offset angle={offset_angle}°")
        
        for robot in self.simulation.robots:
            # Apply to transmitters
            for transmitter in robot.transmitters:    
                # Save real distance
                transmitter.real_beam_distance = real_distance
                # Apply angle and distance parameters
                transmitter.set_beam_parameters(angle, pixel_distance, self.simulation)
                
                # Fix offset angle application for synchronization
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
            
            # Add application for receivers - use viewing angle from slider
            for receiver in robot.receivers:
                receiver.real_max_distance = real_distance
                receiver.set_receiver_parameters(viewing_angle, pixel_distance, self.simulation)
    
    def toggle_beams(self):
        """Toggle IR beam display"""
        show_beams = self.show_beams_var.get()
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                transmitter.active = show_beams
        self.canvas.update_canvas()
    
    def toggle_signal_lines(self):
        """Toggle IR signal connection lines display"""
        self.canvas.show_signal_lines = self.show_signal_lines_var.get()
        self.canvas.update_canvas()
    
    def on_resize(self, event):
        """Handle window resize"""
        if (event.widget == self):
            self.update_idletasks()
            self.config(width=250)  # Ensure fixed width
    
    def update_sensor_ui(self):
        """Update UI display of sensor parameters according to current scale"""
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
                print(f"Updated distance slider: {new_value}m")
            except Exception as e:
                print(f"Error updating sensor UI: {e}")
    
    def on_scale_change(self, event=None):
        """Handle slider adjustment by user"""
        self.apply_sensor_params()
    
    def zoom_in(self):
        """Zoom in canvas"""
        self.canvas.zoom_in()
    
    def zoom_out(self):
        """Zoom out canvas"""
        self.canvas.zoom_out()
    
    def _add_robot_to_chain(self):
        """Display window to add robot to follow chain"""
        dialog = tk.Toplevel(self)
        dialog.title("Select Robot Order")
        dialog.geometry("300x400")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Select robots in order from top to bottom:").pack(pady=5)
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
        confirm_btn = tk.Button(btn_frame, text="Confirm", command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def _update_chain_display(self):
        """Update display of robot follow chain"""
        if not self.robot_chain:
            self.chain_label.config(text="No robot chain set", fg="gray")
        else:
            chain_text = " → ".join([f"Robot {id}" for id in self.robot_chain])
            self.chain_label.config(text=chain_text, fg="blue")

    def _update_distance(self):
        """Update follow distance"""
        distance = self.distance_var.get()
        self.follow_manager.set_follow_distance(distance)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling event"""
        self.canvas_container.yview_scroll(int(-1*(event.delta/120)), "units")

    def _build_path_controls(self):
        """Create controls for path drawing feature"""
        path_frame = tk.LabelFrame(self.scrollable_frame, text="Path Drawing", padx=5, pady=5, bg='#f0f0f0')
        path_frame.pack(fill=tk.X, pady=5)
        
        # Start drawing button
        self.start_draw_btn = tk.Button(path_frame, text="Start Drawing Path", command=self._start_drawing)
        self.start_draw_btn.pack(fill=tk.X, pady=2)
        
        # Finish drawing button
        self.finish_draw_btn = tk.Button(path_frame, text="Complete Path", command=self._finish_drawing)
        self.finish_draw_btn.pack(fill=tk.X, pady=2)
        
        # Add clear path button
        self.clear_path_btn = tk.Button(path_frame, text="Clear Path", command=self._clear_path)
        self.clear_path_btn.pack(fill=tk.X, pady=2)
        
        # Select leader robot
        tk.Label(path_frame, text="Leader Robot:", bg='#f0f0f0').pack(anchor='w')
        self.path_leader_var = tk.StringVar()
        self.path_leader_combobox = ttk.Combobox(path_frame, textvariable=self.path_leader_var, state="readonly")
        self.path_leader_combobox.pack(fill=tk.X, pady=2)
        
        # Start/stop movement buttons
        button_frame = tk.Frame(path_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=2)
        
        self.start_path_btn = tk.Button(button_frame, text="Start Movement", command=self._start_path_movement)
        self.start_path_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        self.stop_path_btn = tk.Button(button_frame, text="Stop Movement", command=self._stop_path_movement)
        self.stop_path_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

    def _start_drawing(self):
        """Start drawing path"""
        self.canvas.start_drawing_path()
        
    def _finish_drawing(self):
        """Finish drawing path"""
        self.canvas.finish_drawing_path()
        
    def _start_path_movement(self):
        """Start movement along drawn path"""
        leader_str = self.path_leader_var.get()
        if leader_str:
            leader_id = int(leader_str.split()[1])
            if hasattr(self.canvas, 'path_manager'):
                self.canvas.path_manager.start(leader_id)
                print(f"Starting Robot {leader_id} movement along drawn path")
            else:
                print("Error: path_manager not initialized")
        else:
            print("Please select a leader robot")
            
    def _stop_path_movement(self):
        """Stop movement along path"""
        self.canvas.path_manager.stop()

    def _clear_path(self):
        """Clear current path"""
        self.canvas.clear_path()
        print("Path cleared")

