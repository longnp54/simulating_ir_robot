import math
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

class PathManager:
    """Manage path and movement according to waypoints"""
    
    def __init__(self, simulation):
        self.simulation = simulation
        self.waypoints = []  # List of waypoints in pixels
        self.waypoints_real = []  # List of waypoints in meters
        self.current_waypoint_index = 0
        self.active = False
        self.leader_id = None
        self.threshold_distance = 10  # Pixel distance to consider waypoint reached
        self.move_speed = 0.02  # Meters per movement step
        self.rotation_speed = 5  # Degrees per rotation step
        
        # Add variables to collect evaluation data
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
        """Set new path"""
        self.waypoints = waypoints.copy()
        
        # Store waypoints as real coordinates (meters)
        self.waypoints_real = []
        for x, y in waypoints:
            real_x, real_y = self.simulation.pixel_to_real(x, y)
            self.waypoints_real.append((real_x, real_y))
            
        self.current_waypoint_index = 0
        print(f"Set path with {len(waypoints)} points")

    def update_waypoints_from_scale(self):
        """Update waypoint coordinates based on current scale"""
        self.waypoints = []
        for real_x, real_y in self.waypoints_real:
            pixel_x, pixel_y = self.simulation.real_to_pixel(real_x, real_y)
            self.waypoints.append((pixel_x, pixel_y))
    
    def start(self, leader_id=None):
        """Start moving along the path"""
        if not self.waypoints:
            print("No path available. Please set path first.")
            return False
        
        if leader_id is not None:
            self.leader_id = leader_id
        
        if self.leader_id is None:
            print("No leader robot selected")
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
        print(f"Started moving robot {self.leader_id} along path")
        return True
    
    def stop(self):
        """Stop moving along the path"""
        self.active = False
        
        # Close evaluation window if it's open
        if hasattr(self, 'eval_window') and self.eval_window.winfo_exists():
            try:
                self.eval_window.destroy()
            except Exception as e:
                print(f"Error closing evaluation window: {e}")
        
        # Complete evaluation data if running halfway
        if len(self.path_data.get('timestamps', [])) > 0:
            # Ensure arrays have same length before saving
            max_length = max(len(self.path_data.get(key, [])) for key in 
                             ['timestamps', 'positions', 'orientations', 'target_angles', 
                              'distances_to_waypoint', 'speeds', 'rotations'])
            
            for key in ['speeds', 'rotations']:
                while len(self.path_data.get(key, [])) < max_length:
                    self.path_data.setdefault(key, []).append(0)
                    
        print("Stopped moving along path")
    
    def update(self):
        """Update leader robot position along the path"""
        if not self.active or self.current_waypoint_index >= len(self.waypoints):
            return
        
        leader = self.simulation.get_robot_by_id(self.leader_id)
        if not leader:
            print(f"Cannot find robot ID {self.leader_id}")
            self.active = False
            return
        
        # Get current waypoint
        target_x, target_y = self.waypoints[self.current_waypoint_index]
        
        # Calculate distance from robot to waypoint
        dx = target_x - leader.x
        dy = target_y - leader.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Collect data for evaluation
        current_time = time.time() - self.start_time
        self.path_data['timestamps'].append(current_time)
        self.path_data['positions'].append((leader.x, leader.y))
        self.path_data['orientations'].append(leader.orientation)
        self.path_data['distances_to_waypoint'].append(distance)
        
        # Display movement progress information (added)
        if hasattr(self, 'last_report_time') and time.time() - self.last_report_time < 1.0:
            # Only report every second to avoid console spam
            pass
        else:
            print(f"Robot {self.leader_id} is moving to point {self.current_waypoint_index+1}/{len(self.waypoints)}")
            print(f"  - Distance to next point: {distance:.1f} pixel ({self.simulation.pixel_distance_to_real(distance):.2f}m)")
            self.last_report_time = time.time()
        
        if distance < self.threshold_distance:
            # Reached waypoint, move to next waypoint
            print(f"✓ Robot {self.leader_id} reached point {self.current_waypoint_index+1}")
            
            # Record time when this waypoint was reached
            if 'waypoint_reached' not in self.path_data:
                self.path_data['waypoint_reached'] = []
            self.path_data['waypoint_reached'].append(self.current_waypoint_index)
            
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.waypoints):
                print("✓ Completed entire path!")
                self.active = False
                # Show evaluation when completed
                self.show_evaluation()
                return
        else:
            # Calculate angle from robot to waypoint
            angle = math.degrees(math.atan2(dy, dx))
            self.path_data['target_angles'].append(angle)
            
            # Calculate angle difference needed to rotate
            angle_diff = (angle - leader.orientation) % 360
            if angle_diff > 180:
                angle_diff -= 360
            
            # Print angle information
            print(f"  - Target angle: {angle:.1f}°, Angle difference: {angle_diff:.1f}°")
            
            # Rotate robot if needed
            if abs(angle_diff) > 5:
                rotation = min(abs(angle_diff), self.rotation_speed) * (1 if angle_diff > 0 else -1)
                leader.rotate(rotation)
                print(f"  - Rotate {rotation:.1f}°")
                self.path_data['rotations'].append(rotation)
                self.path_data['speeds'].append(0)  # No movement while rotating
                self.total_rotation += abs(rotation)
            else:
                # Move towards waypoint
                move_dist = min(self.move_speed, distance/self.simulation.scale)
                leader.move_forward(move_dist)
                print(f"  - Move forward {move_dist:.3f}m")
                self.path_data['rotations'].append(0)  # No rotation while moving
                self.path_data['speeds'].append(move_dist)
                self.total_distance += move_dist
                
                # Calculate deviation from straight line
                if self.current_waypoint_index > 0:
                    prev_waypoint = self.waypoints[self.current_waypoint_index - 1]
                    deviation = self._calculate_deviation_from_line(
                        prev_waypoint, 
                        (target_x, target_y), 
                        (leader.x, leader.y)
                    )
                    self.max_deviation = max(self.max_deviation, deviation)
    
    def _calculate_deviation_from_line(self, point1, point2, robot_pos):
        """Calculate robot deviation from straight line connecting two waypoints"""
        x1, y1 = point1
        x2, y2 = point2
        x0, y0 = robot_pos
        
        # If two points are identical, deviation is distance from robot to that point
        if x1 == x2 and y1 == y2:
            return math.sqrt((x0-x1)**2 + (y0-y1)**2)
        
        # Calculate deviation using point-to-line distance formula
        numerator = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
        denominator = math.sqrt((y2-y1)**2 + (x2-x1)**2)
        
        return numerator / denominator

    def show_evaluation(self):
        """Display evaluations and charts after completing the path"""
        # Create new window to display results
        eval_window = tk.Toplevel()
        
        # Store reference to evaluation window
        self.eval_window = eval_window
        
        eval_window.title(f"Movement result evaluation - Robot {self.leader_id}")
        eval_window.geometry("800x600")
        
        # Add handler for window close event
        def on_close():
            if hasattr(self, 'eval_window'):
                delattr(self, 'eval_window')
            eval_window.destroy()
            
        eval_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(eval_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Overview tab
        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        
        # Calculate statistical metrics
        total_time = self.path_data['timestamps'][-1] if self.path_data['timestamps'] else 0
        avg_speed = self.total_distance / total_time if total_time > 0 else 0
        path_length_m = self.total_distance  # already in meters
        num_rotations = sum(1 for r in self.path_data['rotations'] if abs(r) > 0)
        
        # Display statistical metrics
        stats_frame = ttk.LabelFrame(overview_tab, text="Movement statistics")
        stats_frame.pack(fill='x', expand=False, padx=10, pady=10)
        
        ttk.Label(stats_frame, text=f"Total time: {total_time:.2f} seconds").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Distance traveled: {path_length_m:.2f} meters").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Average speed: {avg_speed:.4f} m/s").grid(row=2, column=0, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Total angle rotated: {self.total_rotation:.1f}°").grid(row=0, column=1, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Number of rotations: {num_rotations}").grid(row=1, column=1, sticky='w', padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Maximum deviation: {self.simulation.pixel_distance_to_real(self.max_deviation):.3f} meters").grid(row=2, column=1, sticky='w', padx=10, pady=5)
        
        # Draw robot path vs waypoints
        self._create_path_plot(overview_tab)
        
        # Speed & Rotation tab
        speed_tab = ttk.Frame(notebook)
        notebook.add(speed_tab, text="Speed & Rotation")
        self._create_speed_rotation_plots(speed_tab)
        
        # Error tab
        error_tab = ttk.Frame(notebook)
        notebook.add(error_tab, text="Error")
        self._create_error_plots(error_tab)
        
        # Waypoint analysis tab
        waypoint_tab = ttk.Frame(notebook)
        notebook.add(waypoint_tab, text="Waypoint analysis")
        self._create_waypoint_analysis(waypoint_tab)
        
        # Export data button
        export_button = ttk.Button(eval_window, text="Export data", command=self._export_data)
        export_button.pack(side='right', padx=10, pady=10)
    
    def _create_path_plot(self, parent):
        """Draw robot path vs waypoints"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        try:
            # Draw actual robot path
            if self.path_data['positions']:
                positions = np.array(self.path_data['positions'])
                
                # Check and set max_y if it doesn't exist
                max_y = 600  # Default value
                if hasattr(self.simulation, 'max_y'):
                    max_y = self.simulation.max_y
                elif hasattr(self.simulation, 'real_height'):
                    # Calculate from real height
                    max_y = self.simulation.real_height * self.simulation.scale
                
                # Convert Y coordinates to match Cartesian coordinate system
                positions_transformed = positions.copy()
                positions_transformed[:, 1] = max_y - positions_transformed[:, 1]  # Invert Y axis
                
                ax.plot(positions_transformed[:, 0], positions_transformed[:, 1], 'b-', label='Actual path')
            
            # Draw waypoints
            if self.waypoints:
                waypoints = np.array(self.waypoints)
                
                # Use same max_y value
                waypoints_transformed = waypoints.copy()
                waypoints_transformed[:, 1] = max_y - waypoints_transformed[:, 1]  # Invert Y axis
                
                ax.plot(waypoints_transformed[:, 0], waypoints_transformed[:, 1], 'r--', label='Ideal path')
                ax.scatter(waypoints_transformed[:, 0], waypoints_transformed[:, 1], color='red', zorder=5, label='Waypoints')
                
                # Add sequence number labels for waypoints
                for i, (x, y) in enumerate(waypoints_transformed):
                    ax.annotate(f"{i+1}", (x, y), fontsize=10, ha='right')
            
            ax.set_title('Robot path')
            ax.set_xlabel('X (pixel)')
            ax.set_ylabel('Y (pixel)')
            ax.legend()
            ax.grid(True)
            
            # Ensure X and Y axis scales are equal
            ax.set_aspect('equal', 'box')
        except Exception as e:
            # Display error message instead of chart
            ax.text(0.5, 0.5, f"Error drawing chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='red')
            ax.axis('off')
            print(f"Chart drawing error: {e}")
        
        # Create frame to contain chart
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Place chart in frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_speed_rotation_plots(self, parent):
        """Draw speed and rotation angle charts over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        try:
            # Get data and make sure we have values
            times = self.path_data.get('timestamps', [])
            if not times:
                raise ValueError("No time data")
                
            # Handle missing or incomplete data
            speeds = self.path_data.get('speeds', [0] * len(times))
            rotations = self.path_data.get('rotations', [0] * len(times))
            
            # Make all arrays the same length by using the shortest length
            min_length = min(len(times), len(speeds), len(rotations))
            if min_length == 0:
                raise ValueError("Empty data arrays")
                
            times = times[:min_length]
            speeds = speeds[:min_length]
            rotations = rotations[:min_length]
            
            # Now plot with equal-length arrays
            ax1.plot(times, speeds, 'g-')
            ax1.set_title('Speed over time')
            ax1.set_ylabel('Speed (m/s)')
            ax1.grid(True)
            
            ax2.plot(times, rotations, 'm-')
            ax2.set_title('Rotation angle over time')
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Rotation angle (degrees)')
            ax2.grid(True)
            
        except Exception as e:
            # Show error message
            for ax in [ax1, ax2]:
                ax.text(0.5, 0.5, f"Error drawing chart: {str(e)}", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=10, color='red')
                ax.axis('off')
            print(f"Chart drawing error: {e}")
        
        plt.tight_layout()
        
        # Create frame for chart
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Add figure to frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_error_plots(self, parent):
        """Draw error charts (distance to waypoint, angle error)"""
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
        
        # Convert from pixels to meters
        distances_m = [self.simulation.pixel_distance_to_real(d) for d in distances]
        ax1.plot(times_dist, distances_m, 'b-')
        ax1.set_title('Distance to waypoint')
        ax1.set_ylabel('Distance (m)')
        ax1.grid(True)
        
        # Calculate angle error
        angle_errors = []
        for i in range(len(target_angles)):
            diff = abs((target_angles[i] - orientations[i]) % 360)
            if diff > 180:
                diff = 360 - diff
            angle_errors.append(diff)
        
        ax2.plot(times_angle, angle_errors, 'r-')
        ax2.set_title('Angle error over time')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Angle error (degrees)')
        ax2.grid(True)
        
        plt.tight_layout()
        
        # Create frame to contain chart
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Place chart in frame
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_waypoint_analysis(self, parent):
        """Analyze time to reach each waypoint and accuracy"""
        # Create list of times to reach each waypoint
        waypoint_times = []
        waypoint_distances = []
        last_time = 0
        
        for i in range(len(self.waypoints)):
            if i < self.current_waypoint_index:
                # Find time when this waypoint was reached
                # (Assume waypoint reached when moving to next waypoint)
                idx = next((j for j, wp_idx in enumerate(self.path_data.get('waypoint_reached', [])) 
                           if wp_idx == i), None)
                
                if idx is not None:
                    time_to_reach = self.path_data['timestamps'][idx] - last_time
                    waypoint_times.append(time_to_reach)
                    last_time = self.path_data['timestamps'][idx]
                    
                    # Calculate deviation distance when reaching waypoint
                    robot_pos = self.path_data['positions'][idx]
                    waypoint_pos = self.waypoints[i]
                    dist = math.sqrt((robot_pos[0] - waypoint_pos[0])**2 + (robot_pos[1] - waypoint_pos[1])**2)
                    waypoint_distances.append(self.simulation.pixel_distance_to_real(dist))
        
        # Create waypoint information table
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('waypoint', 'time', 'distance')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        tree.heading('waypoint', text='Waypoint')
        tree.heading('time', text='Time to reach (s)')
        tree.heading('distance', text='Deviation (m)')
        
        tree.column('waypoint', width=80)
        tree.column('time', width=150)
        tree.column('distance', width=150)
        
        # Add data to table
        for i in range(min(len(waypoint_times), len(waypoint_distances))):
            tree.insert('', 'end', values=(
                f'Point {i+1}',
                f'{waypoint_times[i]:.2f}',
                f'{waypoint_distances[i]:.3f}'
            ))
        
        # General information
        if waypoint_times:
            avg_time = sum(waypoint_times) / len(waypoint_times)
            max_time = max(waypoint_times)
            min_time = min(waypoint_times)
            
            tree.insert('', 'end', values=('Average', f'{avg_time:.2f}', ''))
            tree.insert('', 'end', values=('Maximum', f'{max_time:.2f}', ''))
            tree.insert('', 'end', values=('Minimum', f'{min_time:.2f}', ''))
        
        tree.pack(fill='both', expand=True)
        
        # Scroll bar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
    
    def _export_data(self):
        """Export data to csv file"""
        # This is the original method, you can develop it further
        print("Data export feature will be implemented in future version.")