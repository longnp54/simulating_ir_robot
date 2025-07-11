import tkinter as tk
import math
from tkinter import simpledialog
import random  # Added for random.uniform

class SimulationCanvas(tk.Canvas):
    # Default pixel/m and zoom step ratio
    BASE_SCALE = 250.0
    ZOOM_RATIO = 1.1

    def __init__(self, parent, simulation):
        super().__init__(parent, bg="white")
        self.simulation = simulation
        self.robot_objects = {}
        
        # Adjust zoom factor
        # Initialize zoom_factor based on current simulation.scale
        self.zoom_factor = simulation.scale / self.BASE_SCALE
        # Calculate minimum zoom to display full 4x4m
        window_width = 800  # Assumed default size
        window_height = 600
        
        # Calculate min_zoom to fit 4m×4m in window
        win_w, win_h = window_width, window_height
        env_w = simulation.real_width * self.BASE_SCALE
        env_h = simulation.real_height * self.BASE_SCALE
        self.min_zoom = min(win_w/env_w, win_h/env_h)
        self.max_zoom = 10.0  # Increased max zoom from 3.0 to 10.0
        
        # Set canvas size
        canvas_width = int(simulation.real_width * simulation.scale)
        canvas_height = int(simulation.real_height * simulation.scale)
        self.config(width=canvas_width, height=canvas_height)
        
        # Add mouse events to interact with robots
        self.bind("<Button-1>", self.on_canvas_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.bind("<Right>", self.rotate_selected_clockwise)
        self.bind("<Left>", self.rotate_selected_counterclockwise)
        self.bind("<Control-R>", self.open_rotation_dialog)  # Ctrl+R to open angle input dialog
        self.bind("<MouseWheel>", self.on_mouse_wheel)  # Mouse wheel event (Windows)
        self.bind("<Control-Button-4>", self.on_zoom_in)  # Zoom in (Linux)
        self.bind("<Control-Button-5>", self.on_zoom_out)  # Zoom out (Linux)
        
        # Add zoom shortcut keys
        self.bind("<plus>", self.on_zoom_in)  # + key
        self.bind("<minus>", self.on_zoom_out)  # - key
        self.bind("<equal>", self.on_zoom_in)  # = key
        
        # Add rotation state tracking variables
        self.rotation_handle = None
        self.rotating = False
        
        # Add to existing bind events
        self.bind("<B3-Motion>", self.on_rotation_drag)     # Right mouse drag to rotate
        self.bind("<ButtonPress-3>", self.on_rotation_start)  # Start rotation
        self.bind("<ButtonRelease-3>", self.on_rotation_end)  # End rotation

        self.selected_robot = None
        self.dragging = False
        self.panning = False  # Variable to track view panning state
        self.last_x = 0
        self.last_y = 0
        self.show_signal_lines = True  # Enable display of signal connection lines

        # Add shortcuts for setting fixed angles
        self.bind("<Control-F>", self.set_fixed_angle_for_all)  # Ctrl+F for all robots
        self.bind("<Control-f>", self.set_fixed_angle_for_selected)  # Ctrl+f for selected robot

        from models.path_manager import PathManager
        self.path_manager = PathManager(simulation)
        self.drawing_path = False
        self.waypoints = []
        
        # Bind mouse events
        self.bind("<Button-1>", self.on_canvas_click)
        self.bind("<B1-Motion>", self.on_canvas_drag)
        self.bind("<ButtonRelease-1>", self.on_canvas_release)

    
    def update_canvas(self):
        """Update entire canvas"""
        # Update formation following if path manager is active
        if hasattr(self, 'path_manager') and self.path_manager.active:
            self.update_formation()
        
        # Save current waypoints if they exist
        current_waypoints = None
        if hasattr(self, 'path_manager') and self.path_manager.waypoints:
            current_waypoints = self.path_manager.waypoints.copy()
        
        # Delete all objects on canvas
        self.delete("all")
        self.robot_objects.clear()
        
        # Draw coordinate grid
        self._draw_grid()
        
        # Redraw path if exists
        if current_waypoints:
            self._draw_path(current_waypoints)
        
        # Draw all robots
        for robot in self.simulation.robots:
            self._draw_robot(robot)
        
        # Draw IR signals if simulating
        if self.simulation.running:
            self._draw_ir_signals()
        
        # Display real world information
        self._draw_real_world_info()
        
        # Update size and scale information
        self._update_info()

    def update_formation(self):
        """Update robot positions in column formation using RPA for detection and global coordinates for movement"""
        # Check if path manager is active
        if not hasattr(self, 'path_manager') or not self.path_manager.active:
            return
        
        # Get leader robot ID
        leader_id = self.path_manager.leader_id
        if leader_id is None:
            return
        
        # Get leader robot
        leader = self.simulation.get_robot_by_id(leader_id)
        if not leader:
            return
        
        # Get list of other robots (non-leaders)
        follower_robots = [robot for robot in self.simulation.robots if robot.id != leader_id]
        
        # Sort robots by distance to leader initially
        # Check both for non-existent formation_order and changed robot count
        if not hasattr(self, 'formation_order') or len(self.formation_order) != len(self.simulation.robots):
            # Calculate distances and sort from closest to furthest
            follower_robots.sort(key=lambda r: leader.get_physical_distance_to(r))
            self.formation_order = [leader] + follower_robots
            print(f"Initializing formation: Leader={leader.id}, Followers={[r.id for r in follower_robots]}")
        
        # === ADD OBSTACLE AVOIDANCE FOR LEADER ROBOT ===
        self._handle_leader_obstacle_avoidance(leader, follower_robots)
        
        # Desired distance between robots in formation
        desired_distance = leader.size * 4.0  # Increased from 2.5 to 4.0 times robot size
        
        # Update position of each robot in formation
        for i in range(1, len(self.formation_order)):
            current_robot = self.formation_order[i]
            robot_ahead = self.formation_order[i-1]  # Robot in front
            
            # Debug to check which robot is being updated
            print(f"Updating robot {current_robot.id} following robot {robot_ahead.id}")
            
            # === USE RPA TO DETERMINE RELATIVE POSITION ===
            rpa_result = current_robot.calculate_relative_position_rpa(robot_ahead.id)
            
            if rpa_result is None:
                # If no IR signal detected, don't move
                print(f"Robot {current_robot.id} cannot detect signal from robot {robot_ahead.id}")
                continue
            
            # Get results from RPA - (bearing_angle, distance, confidence) to know if visible
            relative_angle, distance_m, confidence = rpa_result
            
            # Debug RPA info
            print(f"RPA: Robot {current_robot.id} detects robot {robot_ahead.id} at angle {relative_angle:.1f}°, distance {distance_m:.2f}m, confidence {confidence:.2f}")
            
            # === USE GLOBAL COORDINATES FOR MOVEMENT ===
            
            # Calculate distance and direction based on absolute coordinates
            dx = robot_ahead.x - current_robot.x
            dy = robot_ahead.y - current_robot.y
            global_distance = math.sqrt(dx*dx + dy*dy)  # Distance in pixels
            global_angle = math.degrees(math.atan2(dy, dx)) % 360  # Absolute angle
            
            # Calculate desired_distance in pixels
            desired_distance_px = desired_distance
            
            # Add a small buffer zone around the desired distance to prevent jitter
            distance_buffer = desired_distance_px * 0.1  # 10% buffer

            # Calculate direction vectors (normalized)
            if global_distance > 0:  # Prevent division by zero
                direction_x = dx / global_distance
                direction_y = dy / global_distance
            else:
                direction_x, direction_y = 0, 0

            # Move only if outside the buffer zone
            if abs(global_distance - desired_distance_px) > distance_buffer:
                # Calculate speed factor - higher for robots further back in formation
                move_speed_factor = 0.5 if i >= 3 else 0.3
                
                if global_distance > desired_distance_px:
                    # Too far - move forward toward the robot ahead
                    move_distance = min(10.0, (global_distance - desired_distance_px) * move_speed_factor)
                    move_x = direction_x * move_distance
                    move_y = direction_y * move_distance
                else:
                    # Too close - back away from the robot ahead
                    move_distance = min(8.0, (desired_distance_px - global_distance) * move_speed_factor)
                    # Reverse direction to move away
                    move_x = -direction_x * move_distance
                    move_y = -direction_y * move_distance
                    
                    # Add debug message for backing up
                    print(f"Robot {current_robot.id} backing away from Robot {robot_ahead.id}: {move_distance:.2f}px")
                
                # Move the robot
                current_robot.move(move_x, move_y)
            
            # Set direction for robot - point toward robot ahead
            current_angle = current_robot.orientation % 360
            
            # Calculate shortest rotation angle to face robot ahead
            angle_diff = (global_angle - current_angle + 180) % 360 - 180
            
            # Gradually rotate toward global_angle
            if abs(angle_diff) > 2:
                # Increase rotation speed for robots 4th and beyond
                rotation_factor = 0.6 if i >= 3 else 0.4
                rotation_speed = min(20.0, abs(angle_diff) * rotation_factor)
                
                if angle_diff > 0:
                    current_robot.rotate(rotation_speed)
                else:
                    current_robot.rotate(-rotation_speed)

            # === ADD OBSTACLE AVOIDANCE FOR FOLLOWER ROBOT ===
            # Get all other robots for avoidance calculations
            all_robots = [r for r in self.simulation.robots if r.id != current_robot.id]

            # Call the enhanced obstacle avoidance function
            self._handle_follower_obstacle_avoidance(
                current_robot, 
                robot_ahead, 
                all_robots, 
                desired_distance_px
            )

    def _handle_leader_obstacle_avoidance(self, leader, follower_robots):
        """Handle obstacle avoidance for the leader robot - improved version for smoother motion
        and proper alignment of robot's heading with movement direction"""
        # Check if following a path
        if not hasattr(self, 'path_manager') or not self.path_manager.active:
            return
        
        # Initialize tracking variables if not exists
        if not hasattr(self, 'previous_avoidance_vector'):
            self.previous_avoidance_vector = (0, 0, 0)  # x, y, magnitude
        
        # Reduce initial speed
        if not hasattr(self, 'current_speed'):
            self.current_speed = 3.0  # Reduced from 5.0 for slower movement
        
        # Obstacle threshold (increased from 5cm to 8cm)
        obstacle_threshold_m = 0.08
        obstacle_threshold_px = self.simulation.real_distance_to_pixel(obstacle_threshold_m)
        safety_margin = 1.5  # Increased from 1.3 to 1.5
        safety_threshold_px = obstacle_threshold_px * safety_margin
        
        # --- STEP 1: Calculate avoidance forces from nearby robots ---
        avoidance_vector = [0, 0, 0]  # x, y, magnitude
        close_robots = []
        
        for robot in follower_robots:
            # Calculate physical distance between robots
            distance_px = math.sqrt((leader.x - robot.x)**2 + (leader.y - robot.y)**2)
            min_distance_px = safety_threshold_px + (leader.size + robot.size) / 2
            
            if distance_px < min_distance_px:
                # Calculate vector from obstacle to leader
                dx = leader.x - robot.x
                dy = leader.y - robot.y
                
                # Avoid division by zero
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    angle = random.uniform(0, 2 * math.pi)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                else:
                    # Normalize vector
                    magnitude = math.sqrt(dx*dx + dy*dy)
                    dx /= magnitude
                    dy /= magnitude
                
                # Calculate avoidance force inversely proportional to distance 
                # Use inverse square law for more natural physics behavior
                force = (min_distance_px / max(distance_px, 1))**2
                
                # Add to list of close robots
                close_robots.append((dx, dy, force, distance_px, robot.id))
                
                # Add to the avoidance vector
                avoidance_vector[0] += dx * force
                avoidance_vector[1] += dy * force
        
        # Normalize avoidance vector if it exists
        if close_robots:
            avoidance_vector[2] = math.sqrt(avoidance_vector[0]**2 + avoidance_vector[1]**2)
            if avoidance_vector[2] > 0:
                avoidance_vector[0] /= avoidance_vector[2]
                avoidance_vector[1] /= avoidance_vector[2]
        
        # --- STEP 2: Calculate target direction vector ---
        target_vector = [0, 0, 0]  # x, y, magnitude
        
        if self.path_manager.current_waypoint_index < len(self.path_manager.waypoints):
            target_x, target_y = self.path_manager.waypoints[self.path_manager.current_waypoint_index]
            
            # Vector to target
            target_vector[0] = target_x - leader.x
            target_vector[1] = target_y - leader.y
            
            # Normalize target vector
            target_vector[2] = math.sqrt(target_vector[0]**2 + target_vector[1]**2)
            if target_vector[2] > 0:
                target_vector[0] /= target_vector[2]
                target_vector[1] /= target_vector[2]
        
        # --- STEP 3: Smooth the avoidance vector with previous one ---
        # This creates more continuous motion
        if avoidance_vector[2] > 0:
            prev_x, prev_y, prev_mag = self.previous_avoidance_vector
            
            # Stronger smoothing factor for more consistent motion
            # Higher values = smoother but less responsive movement
            smooth_factor = min(0.85, max(0.6, prev_mag * 0.7))  # Increased from 0.8/0.3/0.5
            
            smooth_x = smooth_factor * prev_x + (1 - smooth_factor) * avoidance_vector[0]
            smooth_y = smooth_factor * prev_y + (1 - smooth_factor) * avoidance_vector[1]
            
            # Normalize smoothed vector
            smooth_mag = math.sqrt(smooth_x**2 + smooth_y**2)
            if smooth_mag > 0:
                smooth_x /= smooth_mag
                smooth_y /= smooth_mag
                
            avoidance_vector = [smooth_x, smooth_y, 1.0]
        
        # --- STEP 4: Combine avoidance and target vectors dynamically ---
        final_vector = [0, 0]
        
        if avoidance_vector[2] > 0:
            # Calculate dot product to determine how conflicting the vectors are
            # Dot product near 1: vectors aligned, near -1: vectors opposing
            dot_product = (avoidance_vector[0] * target_vector[0] + 
                        avoidance_vector[1] * target_vector[1])
            
            # Determine weights based on dot product and distance to closest obstacle
            if close_robots:
                closest_distance = min([dist for _, _, _, dist, _ in close_robots])
                # Normalize distance to a 0-1 range where 0 is collision and 1 is at safety threshold
                normalized_distance = min(1.0, closest_distance / safety_threshold_px)
                
                # Calculate base avoidance weight - more weight when closer to obstacle
                # Using exponential function for more natural physics behavior
                base_avoidance_weight = 0.6 + 0.4 * math.exp(-2 * normalized_distance)
                
                # Adjust weights based on vector alignment
                if dot_product < -0.5:  # Highly conflicting directions (>120° angle)
                    # When vectors oppose, prioritize avoidance heavily
                    avoidance_weight = min(0.95, base_avoidance_weight + 0.2)
                elif dot_product < 0:  # Moderately conflicting (90-120° angle)
                    avoidance_weight = min(0.9, base_avoidance_weight + 0.1)
                else:  # Vectors somewhat aligned (<90° angle)
                    # When vectors somewhat align, allow more influence from target
                    avoidance_weight = min(0.85, base_avoidance_weight)
                
                target_weight = 1 - avoidance_weight
                
                # Combine vectors with calculated weights
                final_vector[0] = avoidance_vector[0] * avoidance_weight + target_vector[0] * target_weight
                final_vector[1] = avoidance_vector[1] * avoidance_weight + target_vector[1] * target_weight
                
                # Store current avoidance vector for next frame smoothing
                # Include magnitude information proportional to how close obstacles are
                # Use exponential function for smoother magnitude calculation
                avoidance_magnitude = math.exp(-normalized_distance * 1.5)
                self.previous_avoidance_vector = (avoidance_vector[0], avoidance_vector[1], avoidance_magnitude)
                
                # Adjust speed based on obstacle proximity - smoother deceleration
                min_speed = 0.6  # Reduced from 1.0
                max_speed = 3.0  # Reduced from 5.0
                
                # Speed is proportional to normalized distance with a minimum
                target_speed = min_speed + (max_speed - min_speed) * normalized_distance
            else:
                # No obstacles - use target direction with gentle transition away from avoidance
                prev_x, prev_y, prev_mag = self.previous_avoidance_vector
                
                # Gradually reduce previous avoidance influence
                if prev_mag > 0.01:  # Only if there was significant previous avoidance
                    # Decay previous avoidance influence
                    decay_factor = 0.9  # Reduce by 10% each frame
                    remaining_influence = prev_mag * decay_factor
                    
                    # Scale remaining influence based on dot product with target
                    # Less influence when previous avoidance opposes current target
                    influence_factor = 0.3 * remaining_influence
                    
                    # Combine with target direction
                    final_vector[0] = prev_x * influence_factor + target_vector[0] * (1 - influence_factor)
                    final_vector[1] = prev_y * influence_factor + target_vector[1] * (1 - influence_factor)
                    
                    # Update previous avoidance vector with reduced magnitude
                    self.previous_avoidance_vector = (prev_x, prev_y, remaining_influence)
                else:
                    # No previous avoidance or fully decayed - use pure target
                    final_vector[0] = target_vector[0]
                    final_vector[1] = target_vector[1]
                    self.previous_avoidance_vector = (0, 0, 0)
                
                # When no obstacles and no previous avoidance - use reduced target speed
                target_speed = 3.0  # Reduced from 5.0
        else:
            # No obstacles and no previous avoidance - use target direction
            final_vector[0] = target_vector[0]
            final_vector[1] = target_vector[1]
            self.previous_avoidance_vector = (0, 0, 0)
            target_speed = 3.0  # Reduced from 5.0
        
        # --- STEP 5: Normalize final vector ---
        final_magnitude = math.sqrt(final_vector[0]**2 + final_vector[1]**2)
        if final_magnitude > 0:
            final_vector[0] /= final_magnitude
            final_vector[1] /= final_magnitude
        
        # --- STEP 6: Apply smooth speed changes ---
        # Speed smoothing - gradual acceleration/deceleration
        speed_change_rate = 0.05  # Reduced from 0.1 for smoother transitions
        if target_speed > self.current_speed:
            self.current_speed = min(target_speed, self.current_speed + speed_change_rate)
        else:
            self.current_speed = max(target_speed, self.current_speed - speed_change_rate)
        
        # --- STEP 7: Move the robot with final vector and speed ---
        leader.move(final_vector[0] * self.current_speed, final_vector[1] * self.current_speed)
        
        # --- STEP 8: Smooth rotation towards movement direction ---
        # Calculate angle for robot orientation based on ACTUAL movement direction
        # This ensures the robot's head always faces its travel direction
        
        # Get actual movement vector (could be different from final_vector due to physics)
        # If you don't have access to actual velocity, use the command vector
        movement_x = final_vector[0] * self.current_speed
        movement_y = final_vector[1] * self.current_speed
        
        # Calculate angle from movement direction
        new_angle = math.degrees(math.atan2(movement_y, movement_x)) % 360
        current_angle = leader.orientation
        
        # Calculate shortest rotation path
        angle_diff = (new_angle - current_angle + 180) % 360 - 180
        
        # Adaptive rotation speed:
        # - Faster rotation when angle difference is large
        # - Slower, more precise rotation when nearly aligned
        # - Higher base rotation speed for more responsive turning
        base_rotation_speed = 2.0  # Minimum rotation speed
        max_rotation_speed = 8.0   # Maximum rotation speed (increased from 5.0)
        
        # More responsive rotation coefficient (increased from 0.15)
        rotation_factor = 0.25
        
        # Calculate rotation speed with a non-linear response curve
        # This gives more precise control for small adjustments
        if abs(angle_diff) < 10:
            # Very precise for small angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * 0.1
        elif abs(angle_diff) < 45:
            # Moderate speed for medium angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * rotation_factor
        else:
            # Faster rotation for large angles
            rotation_speed = base_rotation_speed + abs(angle_diff) * rotation_factor * 1.5
        
        # Cap at maximum rotation speed
        rotation_speed = min(max_rotation_speed, rotation_speed)
        
        # Apply rotation in the appropriate direction
        if angle_diff > 0:
            leader.rotate(rotation_speed)
        else:
            leader.rotate(-rotation_speed)

    def _draw_grid(self):
        """Draw coordinate grid"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:  # Canvas not yet rendered
            width = 800
            height = 600
        
        # Draw grid appropriate to scale
        grid_size = int(self.simulation.scale / 2)  # 50cm
        
        for x in range(0, width, grid_size):
            self.create_line(x, 0, x, height, fill="#e0e0e0")
        
        for y in range(0, height, grid_size):
            self.create_line(0, y, width, y, fill="#e0e0e0")
        
        # Comment or remove the following lines to remove the blue 4x4m border
        # env_width = int(self.simulation.real_width * self.simulation.scale)
        # env_height = int(self.simulation.real_height * self.simulation.scale)
        # self.create_rectangle(0, 0, env_width, env_height, outline="blue", width=2)

    def _draw_real_world_info(self):
        """Display information about the real environment"""
        # No display here as it's handled in _update_info
        # This method can be empty or removed
        pass

    def _draw_robot(self, robot):
        """Draw robot on canvas"""
        # Draw square representing robot
        half_size = robot.size / 2
        
        # Color depends on whether robot is selected
        fill_color = "#ADD8E6" if robot != self.selected_robot else "#90EE90"
        
        # Draw main square (rotated)
        corners = robot.get_corner_positions()
        robot_body = self.create_polygon(corners, fill=fill_color, outline="black", width=2,
                                     tags=f"robot_{robot.id}")
        
        # Save robot object ID
        self.robot_objects[robot.id] = robot_body
        

        # Display robot ID and position with improved layout
        real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
        
        # Text stacked more compactly - ID in center
        self.create_text(robot.x, robot.y, text=f"ID {robot.id}", font=("Arial", 9, "bold"))
        
        # Robot position - smaller and below ID
        pos_text = f"{real_x:.2f}m, {real_y:.2f}m"
        self.create_text(robot.x, robot.y + 15, text=pos_text, font=("Arial", 7))
        
        # Angle displayed at bottom
        self.create_text(robot.x, robot.y + 25, text=f"{robot.orientation}°", font=("Arial", 7))
        
        # Draw sensors
        # Color array to distinguish sensors by position
        tx_colors = ["red", "orange", "pink", "purple"]
        # Use fixed black color for all receivers (instead of color array)
        rx_color = "black"  # Fixed black color for all IR receivers
        
        for i, transmitter in enumerate(robot.transmitters):
            tx, ty = transmitter.get_position(robot.x, robot.y, robot.size, robot.orientation)
            
            # Use different colors based on position_index for transmitters
            color_idx = transmitter.position_index % len(tx_colors)
            color = tx_colors[color_idx]
            
            # Draw transmitter sensor with distinct color
            self.create_oval(tx-3, ty-3, tx+3, ty+3, fill=color, 
                            outline="black", tags=f"tx_{robot.id}_{i}")
            
            # Display sensor code if robot is selected
            if robot == self.selected_robot:
                side_names = ["T", "R", "B", "L"]  # Top, Right, Bottom, Left
                label = f"{side_names[transmitter.side]}{transmitter.position_index}"
                self.create_text(tx, ty-8, text=label, font=("Arial", 7), tags=f"tx_label_{robot.id}_{i}")
            
            # Draw beam if simulating and sensor is active
            if transmitter.active:
                # Get beam parameters
                beam_params = transmitter.get_beam_cone(robot.x, robot.y, robot.size, robot.orientation)
                if len(beam_params) >= 5:  # Changed from 3 to 5 parameters
                    start_angle, extent_angle, major_radius, minor_radius, beam_direction = beam_params
                    # Get transmitter position
                    tx, ty = transmitter.get_position(robot.x, robot.y, robot.size, robot.orientation)
                    
                    # Create polygon from transmitter position and points on ellipse
                    polygon_points = [tx, ty]  # First point is transmitter position
                    
                    # Number of points on arc for smooth ellipse
                    num_points = 30  # Increased points for smoother curve
                    
                    # Ensure angles work in Tkinter coordinate system
                    angle_rad_start = math.radians(start_angle)
                    angle_rad_end = math.radians((start_angle + extent_angle) % 360)
                    
                    # If end angle is less than start angle, add 2π
                    if angle_rad_end < angle_rad_start:
                        angle_rad_end += 2 * math.pi
                        
                    # Angle of main ellipse direction
                    main_direction_rad = math.radians(beam_direction)
                    
                    # Create points on beam arc with rounded shape
                    for i in range(num_points + 1):
                        # Angle calculation parts remain unchanged
                        angle_rad = angle_rad_start + (angle_rad_end - angle_rad_start) * i / num_points
                        rel_angle = angle_rad - main_direction_rad
                        
                        # Normalize relative angle to range [-π, π]
                        while rel_angle > math.pi:
                            rel_angle -= 2 * math.pi
                        while rel_angle < -math.pi:
                            rel_angle += 2 * math.pi
                        
                        # Calculate angle ratio (0 at center, 1 at edge)
                        angle_ratio = abs(rel_angle) / (math.radians(extent_angle) / 2)
                        
                        # Fix this part to avoid complex numbers
                        superellipse_n = 2.5
                        angle_ratio_power = angle_ratio ** superellipse_n
                        
                        # Ensure non-negative argument before applying fractional power
                        if angle_ratio_power >= 1:
                            radius_factor = 0
                        else:
                            radius_factor = (1 - angle_ratio_power) ** (1/superellipse_n)
                        
                        # Apply additional cos function for natural rounded shape
                        cos_factor = math.cos(rel_angle * 0.7)
                        radius = major_radius * radius_factor * cos_factor
                        
                        # Calculate point coordinates on arc
                        x = tx + radius * math.cos(angle_rad)
                        y = ty + radius * math.sin(angle_rad)
                        
                        # Add check to ensure x, y are real numbers
                        if isinstance(x, complex):
                            x = x.real
                        if isinstance(y, complex):
                            y = y.real
                        
                        # Add to point list
                        polygon_points.extend([x, y])
                    
                    # Draw beam as polygon
                    self.create_polygon(polygon_points, fill='#FFE0E0', outline=color, width=1,
                                     stipple='gray25', tags=f"beam_{robot.id}_{i}")
        
        for i, receiver in enumerate(robot.receivers):
            rx, ry = receiver.get_position(robot.x, robot.y, robot.size, robot.orientation)
            
            # Use fixed black color for all receivers instead of position_index color
            self.create_oval(rx-3, ry-3, rx+3, ry+3, fill=rx_color, 
                            outline="black", tags=f"rx_{robot.id}_{i}")
            
            # Display sensor code if robot is selected
            if self.selected_robot and receiver.signals:
                side_names = ["T", "R", "B", "L"]
                label = f"{side_names[receiver.side]}{receiver.position_index}"
                self.create_text(rx, ry+8, text=label, font=("Arial", 7), tags=f"rx_label_{robot.id}_{i}")
        
            # Draw receiver viewing area when robot is selected
            if robot == self.selected_robot:
                for receiver in robot.receivers:
                    rx_pos = receiver.get_position(robot.x, robot.y, robot.size, robot.orientation)
                    
                    # Only draw when selected to avoid too many objects on canvas
                    viewing_direction = receiver.get_viewing_direction(robot.orientation)
                    
                    # Draw arc showing reception direction
                    reception_angle = receiver.viewing_angle  # Use correct reception angle from receiver
                    radius = 60  # Arc radius

                    # Recalculate angles for Tkinter coordinate system
                    tk_center_angle = (0 - viewing_direction) % 360  # Changed from 0 to 90 for correct direction
                    tk_start_angle = (tk_center_angle - reception_angle / 2) % 360
                    tk_extent_angle = reception_angle

                    # Change arc drawing approach - draw a thicker single arc for better visibility
                    x0 = rx_pos[0] - radius
                    y0 = rx_pos[1] - radius
                    x1 = rx_pos[0] + radius
                    y1 = rx_pos[1] + radius

                    # Draw main arc with greater thickness for better visibility
                    self.create_arc(x0, y0, x1, y1,
                                   start=tk_start_angle, extent=tk_extent_angle,
                                   style="arc", outline="blue", width=2,
                                   tags=f"rx_dir_{robot.id}_main")

        # Add code to draw coordinate axes
        # ------- Start new code -------
        # Draw robot coordinate axes
        angle_rad = math.radians(robot.orientation)

        # Basic axis length and head axis length
        axis_length = robot.size * 0.6
        head_axis_length = robot.size * 0.9  # Head is longer 

        # Draw X/Head axis (green, longer) - this is the robot's head (0°)
        head_end_x = robot.x + head_axis_length * math.cos(angle_rad)
        head_end_y = robot.y + head_axis_length * math.sin(angle_rad)
        self.create_line(robot.x, robot.y, head_end_x, head_end_y, 
                        fill="green", width=3, arrow=tk.LAST, tags=f"axis_head_{robot.id}")

        # Draw Y axis (blue) - perpendicular to head (90° clockwise)
        y_rad = angle_rad + math.pi/2
        y_end_x = robot.x + axis_length * math.cos(y_rad)
        y_end_y = robot.y + axis_length * math.sin(y_rad)
        self.create_line(robot.x, robot.y, y_end_x, y_end_y, 
                        fill="blue", width=2, arrow=tk.LAST, tags=f"axis_y_{robot.id}")

        # Add axis labels
        self.create_text(head_end_x + 10, head_end_y, text="X/Head", fill="green", font=("Arial", 8))
        self.create_text(y_end_x, y_end_y + 10, text="Y", fill="blue", font=("Arial", 8))
        # ------- End new code -------

        # Add rotation handle for selected robot
        if robot == self.selected_robot:
            # Draw rotation circle at distance from robot center
            rotation_radius = robot.size * 0.75
            handle_x = robot.x + rotation_radius * math.cos(angle_rad + math.pi/4)
            handle_y = robot.y + rotation_radius * math.sin(angle_rad + math.pi/4)
            
        

    def _draw_ir_signals(self):
        """Draw IR signals between robots"""
        # Collect sensor and robot positions
        robot_positions = {}
        tx_positions = []
        rx_positions = []
        
        for robot in self.simulation.robots:
            # Save robot position for can_receive_signal
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
        
        # Collect obstacle information
        obstacles = []
        for robot in self.simulation.robots:
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
        
        # Draw all valid IR signals
        from models.ir_sensor import can_receive_signal
        
        for tx, tx_pos in tx_positions:
            for rx, rx_pos in rx_positions:
                # Skip if same robot
                if tx.robot_id == rx.robot_id:
                    continue
                
                # Use combined Pathloss-Rician model
                can_receive, estimated_distance, signal_strength = can_receive_signal(
                    tx, rx, robot_positions, obstacles)
                
                if can_receive:
                    # Color based on signal strength
                    color, stipple = self._get_signal_color(signal_strength/100)
                    
                    # Line width proportional to signal strength
                    line_width = max(1, min(3, signal_strength / 30))
                    
                    # Draw connection line with glow effect
                    # First draw a wider faded line as background for glow effect
                    glow_width = line_width * 1.5
                    glow_color = f"#{255:02x}{255:02x}{200:02x}"  # Light yellow color
                    
                    self.create_line(tx_pos[0], tx_pos[1], rx_pos[0], rx_pos[1], 
                                   fill=glow_color, width=glow_width, 
                                   stipple='gray75',  # Add stipple for faded effect
                                   tags="ir_signal_glow")
                    
                    # Then draw main line
                    self.create_line(tx_pos[0], tx_pos[1], rx_pos[0], rx_pos[1], 
                                   fill=color, width=line_width, 
                                   dash=(3, 2) if signal_strength < 40 else "", 
                                   stipple=stipple, tags="ir_signal")
                    
                    # Display strength value with font appropriate to signal strength
                    mid_x = (tx_pos[0] + rx_pos[0]) / 2
                    mid_y = (tx_pos[1] + rx_pos[1]) / 2
                    
                    # Adjust font size based on signal strength
                    font_size = max(6, min(9, int(signal_strength / 15)))
                    
                    # Only show background for strong enough signals
                    if signal_strength > 20:
                        self.create_oval(mid_x-15, mid_y-10, mid_x+15, mid_y+10,
                                      fill='white', outline='', tags="ir_signal_bg")
                    
                    self.create_text(mid_x, mid_y, text=f"{signal_strength:.1f}", 
                                   fill="black", font=("Arial", font_size), tags="ir_signal")

    def _get_signal_color(self, strength):
        """Convert signal strength to color with smooth gradation"""
        # Ensure strength is in range [0, 1]
        strength = max(0.0, min(1.0, strength))

        # Expand color spectrum to show more detailed degradation
        if (strength > 0.7):  # Strong signal: green
            # Calculate r and ensure it's not negative
            r_float = 255 * (1 - strength) * 2
            r = max(0, int(r_float)) # Ensure r is not negative
            g = 255
            b = 0
        elif (strength > 0.4):  # Medium signal: yellow
            r = 255
            g = 255
            b = 0
        elif (strength > 0.2):  # Fairly weak signal: orange
            r = 255
            g = 165
            b = 0
        else:  # Very weak signal: red
            r = 255
            # g is already ensured to be non-negative with max(0, ...)
            g = max(0, int(255 * strength * 4))
            b = 0

        # Ensure all color components are in range [0, 255] before formatting
        r = min(255, r)
        g = min(255, g)
        b = min(255, b)

        # Stipple based on signal strength - gradual change rather than abrupt
        if strength < 0.05:
            stipple = 'gray25'  # Very faded for extremely weak signals
        elif strength < 0.15:
            stipple = 'gray50'  # Quite faded for weak signals
        elif strength < 0.3:
            stipple = 'gray75'  # Slightly faded for medium-weak signals
        else:
            stipple = ''  # No fade for medium and strong signals

        # Return valid color
        return f"#{r:02x}{g:02x}{b:02x}", stipple
    
    def on_canvas_click(self, event):
        """Handle mouse click event"""
        if self.drawing_path:
            # Add the waypoint to the list
            x, y = event.x, event.y
            self.waypoints.append((x, y))
            
            # Instead of drawing directly here, clear existing points and redraw all at once
            self.delete('waypoint')
            self._draw_path(self.waypoints)
            
            # Update waypoints in path_manager
            if hasattr(self, 'path_manager'):
                self.path_manager.waypoints = self.waypoints.copy()
                
                # Update real coordinates
                self.path_manager.waypoints_real = []
                for wx, wy in self.waypoints:
                    real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                    self.path_manager.waypoints_real.append((real_x, real_y))
        else:
            # Code for handling robot selection
            robot = self.simulation.get_robot_at(event.x, event.y)
            if robot:
                self.selected_robot = robot
                self.dragging = True
                self.panning = False
                self.last_x = event.x
                self.last_y = event.y
                self.focus_set()
            else:
                self.selected_robot = None
                self.dragging = False
                self.panning = True
                self.last_x = event.x
                self.last_y = event.y
        
        # Update canvas
        self.update_canvas()

    def on_drag(self, event):
        """Handle mouse drag event"""
        if self.dragging and self.selected_robot:
            # Calculate movement distance
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Move selected robot
            self.selected_robot.move(dx, dy)
            
            # Update last position
            self.last_x = event.x
            self.last_y = event.y
            
            # Redraw canvas
            self.update_canvas()
        elif self.panning:
            # Calculate movement distance
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Move all robots (create view panning effect)
            for robot in self.simulation.robots:
                robot.move(dx, dy)
            
            # Update last position
            self.last_x = event.x
            self.last_y = event.y
            
            # Redraw canvas
            self.update_canvas()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel event for smooth zooming"""
        if event.state & 0x4:  # Ctrl key
            # Save mouse cursor position (pixels)
            cursor_x, cursor_y = event.x, event.y
            
            # Convert cursor position to real coordinates (m)
            cursor_real_x, cursor_real_y = self.simulation.pixel_to_real(cursor_x, cursor_y)
            
            # Save real positions of all robots
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Save real positions of path points if any
            path_points_real = []
            if hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
                for i, point in enumerate(self.path_manager.waypoints):
                    if isinstance(point, tuple) and len(point) == 2:
                        real_x, real_y = self.simulation.pixel_to_real(point[0], point[1])
                        path_points_real.append((i, real_x, real_y))
            
            # Update zoom factor similar to zoom_in and zoom_out
            old_zoom = self.zoom_factor
            if event.delta > 0:  # zoom in
                self.zoom_factor = min(self.max_zoom, self.zoom_factor * self.ZOOM_RATIO)
                self.zoom_factor = round(self.zoom_factor, 4)  # Standardize to 4 decimal places
            else:  # zoom out
                self.zoom_factor = max(self.min_zoom, self.zoom_factor / self.ZOOM_RATIO)
                self.zoom_factor = round(self.zoom_factor, 4)  # Standardize to 4 decimal places
            
            # Apply new zoom
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Standardize rounding
            self.simulation.scale = new_scale  # Update scale
            
            # Restore real positions of all robots
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Restore real positions of path points if any
            if path_points_real or hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
                for i, real_x, real_y in path_points_real:
                    if i < len(self.path_manager.waypoints):
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        self.path_manager.waypoints[i] = (new_pixel_x, new_pixel_y)
                
                # Update waypoints_real in path_manager
                if hasattr(self.path_manager, 'waypoints_real'):
                    self.path_manager.waypoints_real = []
                    for wx, wy in self.path_manager.waypoints:
                        real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                        self.path_manager.waypoints_real.append((real_x, real_y))
            
            # Instead of calling update_all_beam_distances, use consistent method
            self.simulation.update_robot_sizes()
            self.update_beam_distances_from_real()
            
            # Redraw canvas
            self.update_canvas()
    
    def on_zoom_in(self, event):
        """Zoom in for Linux"""
        self.zoom_in()
        return "break"  # Prevent event propagation
    
    def on_zoom_out(self, event):
        """Zoom out for Linux"""
        self.zoom_out()
        return "break"  # Prevent event propagation
    
    def zoom_in(self):
        """Zoom in"""
        if self.zoom_factor < self.max_zoom:
            # Save real positions of all robots
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Update zoom factor more precisely (changed from 2 to 4 decimal places)
            self.zoom_factor = min(self.max_zoom, self.zoom_factor * self.ZOOM_RATIO)
            self.zoom_factor = round(self.zoom_factor, 4)  # Increased precision
            
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Increased precision
            self.simulation.scale = new_scale
            
            # Update robot sizes
            self.simulation.update_robot_sizes()
            
            # Restore real positions of robots
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Update beam parameters based on real distances
            self.update_beam_distances_from_real()
            
            # Update canvas
            self.update_canvas()

    # Modify zoom_out() method
    def zoom_out(self):
        """Zoom out canvas"""
        # Calculate minimum zoom to display full 4x4m
        min_zoom = max(0.8, self.min_zoom)
        
        if self.zoom_factor > min_zoom:
            # Save real positions of all robots
            robot_real_positions = []
            for robot in self.simulation.robots:
                real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
                robot_real_positions.append((robot.id, real_x, real_y))
            
            # Update zoom factor and round to avoid precision errors
            self.zoom_factor = max(min_zoom, self.zoom_factor / self.ZOOM_RATIO)
            self.zoom_factor = round(self.zoom_factor, 4)  # Standardize with zoom_in - use 4 decimal places
            
            # Update scale and robot sizes
            new_scale = round(self.BASE_SCALE * self.zoom_factor, 4)  # Standardize with zoom_in
            self.simulation.scale = new_scale
            
            self.simulation.update_robot_sizes()
            
            # Restore real positions of robots
            for robot_id, real_x, real_y in robot_real_positions:
                for robot in self.simulation.robots:
                    if robot.id == robot_id:
                        new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                        robot.x = new_pixel_x
                        robot.y = new_pixel_y
                        break
            
            # Use same method as zoom_in
            self.update_beam_distances_from_real()
            
            # Update canvas
            self.update_canvas()

    def _apply_zoom(self, new_zoom):
        """Apply new zoom level and update everything"""
        # Save real positions of all robots
        robot_real_positions = []
        for robot in self.simulation.robots:
            real_x, real_y = self.simulation.pixel_to_real(robot.x, robot.y)
            robot_real_positions.append((robot.id, real_x, real_y))
        
        # Save real positions of path points if any
        path_points_real = []
        if hasattr(self, 'path_manager') and self.path_manager.active and hasattr(self.path_manager, 'waypoints'):
            for i, point in enumerate(self.path_manager.waypoints):
                if isinstance(point, tuple) and len(point) == 2:
                    real_x, real_y = self.simulation.pixel_to_real(point[0], point[1])
                    path_points_real.append((i, real_x, real_y))
        
        # Update scale for simulation
        new_scale = self.BASE_SCALE * new_zoom
        self.simulation.set_scale(new_scale)
        self.zoom_factor = new_zoom
        
        # Restore real positions of all robots
        for robot_id, real_x, real_y in robot_real_positions:
            for robot in self.simulation.robots:
                if robot.id == robot_id:
                    new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                    robot.x = new_pixel_x
                    robot.y = new_pixel_y
                    break
        
        # Restore real positions of path points if any
        if path_points_real and hasattr(self, 'path_manager') and hasattr(self.path_manager, 'waypoints'):
            for i, real_x, real_y in path_points_real:
                if i < len(self.path_manager.waypoints):
                    new_pixel_x, new_pixel_y = self.simulation.real_to_pixel(real_x, real_y)
                    self.path_manager.waypoints[i] = (new_pixel_x, new_pixel_y)
            
            # Update waypoints_real in path_manager
            if hasattr(self.path_manager, 'waypoints_real'):
                self.path_manager.waypoints_real = []
                for wx, wy in self.path_manager.waypoints:
                    real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                    self.path_manager.waypoints_real.append((real_x, real_y))
        
        # After robots have updated sizes, update beam_distance
        self.update_all_beam_distances()
        
        # Update canvas
        self.update_canvas()

    def update_all_beam_distances(self):
        """Update beam distances with accurate ratio to robot size"""
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                # Initialize base values if not exist
                if not hasattr(transmitter, 'base_beam_distance'):
                    transmitter.base_beam_distance = transmitter.beam_distance
                    transmitter.base_robot_size = robot.size
                    
                    # Calculate ratio between beam_distance and robot.size when initializing
                    # This ratio will be kept constant when zooming
                    transmitter.beam_to_robot_ratio = transmitter.beam_distance / robot.size
                    print(f"Initialize: Robot {robot.id}, beam/size ratio = {transmitter.beam_to_robot_ratio:.2f}")
                
                # Calculate new beam distance maintaining ratio with robot size
                old_distance = transmitter.beam_distance
                
                # Apply fixed ratio to calculate new beam_distance
                new_distance = robot.size * transmitter.beam_to_robot_ratio
                
                # Update new value
                transmitter.beam_distance = new_distance
                
                # Debug log with simple format
                if abs(old_distance - new_distance) > 1:
                    print(f"Robot {robot.id}: size={int(robot.size)}, beam={int(new_distance)}")

    def update_beam_distances_from_real(self):
        """Update beam distances based on saved real distances"""
        for robot in self.simulation.robots:
            for transmitter in robot.transmitters:
                # If real distance exists
                if hasattr(transmitter, 'real_beam_distance'):
                    # Keep exact real distance
                    real_distance = transmitter.real_beam_distance
                    # Convert from meters to pixels at current scale
                    transmitter.beam_distance = self.simulation.real_distance_to_pixel(real_distance)
                    # Debug message
                    print(f"Robot {robot.id}: beam={real_distance}m → {transmitter.beam_distance}px (scale={self.simulation.scale})")

    def open_rotation_dialog(self, event=None):
        """Open angle input dialog for selected robot"""
        if self.selected_robot:
            try:
                # Display dialog requesting angle input
                new_angle = simpledialog.askinteger("Enter Angle", 
                                                  f"Enter rotation angle for Robot {self.selected_robot.id} (0-359):",
                                                  initialvalue=self.selected_robot.orientation,
                                                  minvalue=0, maxvalue=359)
                if new_angle is not None:
                    # Set new angle for robot
                    self.selected_robot.set_orientation(new_angle)
                    self.update_canvas()
            except Exception as e:
                print(f"Error entering angle: {e}")
        return "break"  # Prevent event propagation

    def _update_info(self):
        """Update information displayed on canvas"""
        # Remove all old information
        self.delete("info_text")
        
        # Display selected robot information
        if self.selected_robot:
            # Basic robot information
            info_text = f"Robot {self.selected_robot.id}: ({self.selected_robot.x:.2f}, {self.selected_robot.y:.2f}), orientation: {self.selected_robot.orientation:.1f}°"
            self.create_text(10, 10, text=info_text, anchor=tk.NW, font=("Arial", 10, "bold"), tags="info_text")
            
            # Find nearby robots
            nearby_robots = []
            for robot in self.simulation.robots:
                if robot.id != self.selected_robot.id:
                    # Calculate absolute distance
                    physical_distance = self.selected_robot.get_physical_distance_to(robot)
                    
                    # Calculate relative angle using traditional method
                    angle_rel = self.selected_robot.get_relative_angle_to(robot)
                    
                    # Check for IR signal
                    has_signal = False
                    for receiver in self.selected_robot.receivers:
                        if robot.id in receiver.signals:
                            has_signal = True
                            break
                    
                    # Calculate angle and distance using RPA algorithm if signal exists
                    rpa_result = None
                    relative_coords = None
                    if has_signal:
                        rpa_result = self.selected_robot.calculate_relative_position_rpa(robot.id)
                        if rpa_result:
                            rpa_angle, rpa_distance, confidence = rpa_result
                            # Calculate relative coordinates from RPA angle and absolute distance
                            relative_coords = self.selected_robot.calculate_relative_coordinates(rpa_angle, physical_distance)
                    
                    # Save information
                    nearby_robots.append((robot.id, physical_distance, angle_rel, has_signal, rpa_result, relative_coords))
            
            # Display list of nearby robots
            if nearby_robots:
                # Sort by distance from closest to furthest
                nearby_robots.sort(key=lambda x: x[1])
                
                self.create_text(10, 40, text="Nearby robots:", anchor=tk.NW, font=("Arial", 10, "bold"), tags="info_text")
                
                y_pos = 60
                for robot_info in nearby_robots:
                    robot_id, physical_distance, angle_rel, has_signal, rpa_result, relative_coords = robot_info
                    
                    # Information about absolute distance
                    distance_info = f"Dist: {physical_distance:.2f}m"
                    
                    # Information about relative angle from both methods
                    angle_info = f", Actual angle: {angle_rel:.1f}°"
                    
                    # Add RPA angle if available
                    rpa_angle_info = ""
                    if rpa_result:
                        rpa_angle, rpa_distance, confidence = rpa_result
                        rpa_angle_info = f", Relative angle: {rpa_angle:.1f}°"
                    
                    # Information about relative coordinates
                    rel_coords_info = ""
                    if relative_coords:
                        rel_x, rel_y = relative_coords
                        
                        # Calculate actual coordinates based on actual angle and distance
                        actual_x = physical_distance * math.cos(math.radians(angle_rel))
                        actual_y = physical_distance * math.sin(math.radians(angle_rel))
                        
                        # Display both actual and relative (RPA) coordinates
                        rel_coords_info = f", Actual coords: ({actual_x:.2f}, {actual_y:.2f}), Relative coords: ({rel_x:.2f}, {rel_y:.2f})"
                    
                    # Signal status
                    signal_status = "✓" if has_signal else "✗"
                    
                    # Create display information - add RPA angle
                    nearby_info = f"Robot {robot_id}: {distance_info}{angle_info}{rpa_angle_info}{rel_coords_info} {signal_status}"
                    
                    # Color based on signal status
                    color = "green" if rpa_result else ("black" if has_signal else "gray")
                    
                    self.create_text(10, y_pos, text=nearby_info, anchor=tk.NW, 
                                   font=("Arial", 9), fill=color, tags="info_text")
                    y_pos += 20

    def reset_view(self):
        """Reset view to center of screen"""
        # Calculate center of real environment
        center_real_x = self.simulation.real_width / 2
        center_real_y = self.simulation.real_height / 2
        
        # Calculate center of screen
        canvas_center_x = self.winfo_width() / 2
        canvas_center_y = self.winfo_height() / 2
        
        # Calculate pixel position of environment center
        center_pixel_x, center_pixel_y = self.simulation.real_to_pixel(center_real_x, center_real_y)
        
        # Calculate offset to move
        offset_x = canvas_center_x - center_pixel_x
        offset_y = canvas_center_y - center_pixel_y
        
        # Move all robots
        for robot in self.simulation.robots:
            robot.move(offset_x, offset_y)
        
        self.update_canvas()

    def on_rotation_start(self, event):
        """Start rotating robot on right mouse button down"""
        # Check if a robot is selected
        robot = self.simulation.get_robot_at(event.x, event.y)
        if robot:
            self.selected_robot = robot
        
        # Only start rotating if a robot is selected
        if self.selected_robot:
            # Save starting position
            self.last_x = event.x
            self.last_y = event.y
            self.rotating = True
        
    def on_rotation_drag(self, event):
        """Rotate robot when dragging right mouse button"""
        if not self.rotating or not self.selected_robot:
            return
            
        # Calculate new angle based on mouse position relative to robot center
        robot = self.selected_robot
        dx = event.x - robot.x
        dy = event.y - robot.y
        
        # Only rotate if far enough from center to avoid sudden angle jumps
        distance = math.sqrt(dx*dx + dy*dy)
        if distance < 10:  # Minimum threshold
            return
        
        # Calculate new angle (in degrees)
        new_angle = math.degrees(math.atan2(dy, dx))
        
        # Set new angle for robot
        robot.set_orientation(new_angle)
        
        # Update canvas
        self.update_canvas()
        
    def on_rotation_end(self, event):
        """End rotation when right mouse button is released"""
        self.rotating = False

    def set_fixed_angle_for_selected(self, event=None):
        """Set fixed angle for selected robot"""
        if self.selected_robot:
            try:
                # Display dialog requesting fixed angle input
                fixed_angle = simpledialog.askinteger("Set Fixed Angle", 
                                                     minvalue=0, maxvalue=359,
                                                     initialvalue=0)
                if fixed_angle is not None:
                    # Set new angle for selected robot
                    self.selected_robot.set_orientation(fixed_angle)
                    self.update_canvas()
            except Exception as e:
                print(f"Error setting fixed angle: {e}")
        return "break"  # Prevent event propagation
    
    def set_fixed_angle_for_all(self, event=None):
        """Set fixed angle for all robots"""
        try:
            # Display dialog requesting fixed angle input
            fixed_angle = simpledialog.askinteger("Set Fixed Angle for All", 
                                                "Enter fixed angle for all robots (0-359):",
                                                minvalue=0, maxvalue=359,
                                                initialvalue=0)
            if fixed_angle is not None:
                # Set new angle for all robots
                for robot in self.simulation.robots:
                    robot.set_orientation(fixed_angle)
                self.update_canvas()
        except Exception as e:
            print(f"Error setting fixed angle: {e}")
        return "break"  # Prevent event propagation

    def on_scale_change(self, event=None):
        # when slider beam_angle/beam_distance changes, apply immediately
        self.apply_sensor_params()

    def _animate_ir_signals(self):
        """Create animation effect for IR signals"""
        # Get all signal line objects
        signal_lines = self.find_withtag("ir_signal")
        
        # Change dash style to create movement animation effect
        for line_id in signal_lines:
            # Get current configuration of the line
            config = self.itemconfigure(line_id)
            if 'dash' in config and config['dash'][4] != '':
                current_dash = self.itemcget(line_id, 'dash').split()
                if len(current_dash) >= 2:
                    # Segmented displacement
                    dash = int(current_dash[0])
                    gap = int(current_dash[1])
                    # Reverse dash and gap positions to create movement animation effect
                    self.itemconfigure(line_id, dash=(gap, dash))
        
        # Schedule for next frame if simulating
        if self.simulation.running:
            self.after(150, self._animate_ir_signals)  # Update every 150ms

    def on_canvas_drag(self, event):
        """Handle mouse drag event when drawing path"""
        if self.drawing_path:
            x, y = event.x, event.y
            if self.waypoints:
                # Remove old preview line if exists
                self.delete('preview_line')
                # Draw new preview line from last point to mouse position
                prev_x, prev_y = self.waypoints[-1]
                self.create_line(prev_x, prev_y, x, y, fill='blue', dash=(4, 2), tags='preview_line')
        elif self.dragging and self.selected_robot:
            # Calculate movement distance
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Move selected robot
            self.selected_robot.move(dx, dy)
            
            # Update last position
            self.last_x = event.x
            self.last_y = event.y
            
            # Redraw canvas
            self.update_canvas()
        elif self.panning:
            # Calculate movement distance
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Move all robots and paths (create view panning effect)
            for robot in self.simulation.robots:
                robot.move(dx, dy)
            
            # Update waypoint positions if any
            if hasattr(self, 'path_manager') and self.path_manager.waypoints:
                for i, (wx, wy) in enumerate(self.path_manager.waypoints):
                    self.path_manager.waypoints[i] = (wx + dx, wy + dy)
                    
                    # Update waypoints_real in path_manager
                if hasattr(self.path_manager, 'waypoints_real'):
                    self.path_manager.waypoints_real = []
                    for wx, wy in self.path_manager.waypoints:
                        real_x, real_y = self.simulation.pixel_to_real(wx, wy)
                        self.path_manager.waypoints_real.append((real_x, real_y))
            
            # Update last position
            self.last_x = event.x
            self.last_y = event.y
            
            # Redraw canvas
            self.update_canvas()

    def on_canvas_release(self, event):
        """Handle mouse release event"""
        # Remove preview line if exists
        self.delete('preview_line')
        
        # End drag state
        self.dragging = False
        self.panning = False
        
        # Update canvas
        self.update_canvas()

    def start_drawing_path(self):
        """Start drawing path"""
        self.drawing_path = True
        self.waypoints = []
        self.delete('waypoint')  # Remove old path
        self.delete('drawing_instructions')
        
        # Display instruction message
        x = self.winfo_width() / 2
        y = 30
        self.create_rectangle(x-200, y-15, x+200, y+15, fill='#ffffcc', 
                            outline='#cccccc', tags='drawing_instructions')
        self.create_text(x, y, text="DRAWING PATH - Click to mark waypoints", 
                        font=("Arial", 10, "bold"), fill="red", tags='drawing_instructions')
        
        print("Started drawing path. Click to mark waypoints.")

    def finish_drawing_path(self):
        """Finish drawing path"""
        self.drawing_path = False
        self.delete('drawing_instructions')
        
        if self.waypoints:
            self.path_manager.set_waypoints(self.waypoints.copy())
            print(f"Path completed with {len(self.waypoints)} waypoints.")
            
            # Convert points to real coordinates (meters) for display
            real_waypoints = []
            for x, y in self.waypoints:
                real_x, real_y = self.simulation.pixel_to_real(x, y)
                real_waypoints.append((real_x, real_y))
            
            # Print detailed path information
            print("Waypoint coordinates (meters):")
            for i, (real_x, real_y) in enumerate(real_waypoints):
                print(f"  Point {i+1}: ({real_x:.2f}m, {real_y:.2f}m)")

    def _draw_path(self, waypoints):
        """Draw path from waypoints"""
        if not waypoints:
            return
        
        # Scale various visual elements based on zoom factor
        point_size = 5 / self.zoom_factor  # Adjusted to maintain visual size with zoom
        text_offset = 15 / self.zoom_factor
        line_width = max(1, 3 / self.zoom_factor)  # Ensure line width is at least 1
        
        # Ensure dash pattern values are never less than 1
        dash_pattern = (max(1, int(10 / self.zoom_factor)), max(1, int(4 / self.zoom_factor)))
        
        font_size = max(int(9 / self.zoom_factor), 7)  # Min font size to ensure readability
        distance_offset = 10 / self.zoom_factor
        
        # Draw waypoint markers
        for i, (x, y) in enumerate(waypoints):
            # Draw marker point with size adjusted for zoom
            self.create_oval(x-point_size, y-point_size, x+point_size, y+point_size, 
                             fill='red', outline='black', width=max(1, 2/self.zoom_factor), tags='waypoint')
            
            # Display point order number
            self.create_text(x, y-text_offset, text=f"{i+1}", font=("Arial", font_size, "bold"), 
                            fill="black", tags='waypoint')
        
        # Draw connecting lines between points
        for i in range(1, len(waypoints)):
            prev_x, prev_y = waypoints[i-1]
            x, y = waypoints[i]
            
            self.create_line(prev_x, prev_y, x, y, fill='red', width=line_width, 
                          arrow=tk.LAST, tags='waypoint', 
                          dash=dash_pattern, capstyle=tk.ROUND)
            
            # Display distance between points
            distance_px = math.sqrt((x-prev_x)**2 + (y-prev_y)**2)
            distance_m = self.simulation.pixel_distance_to_real(distance_px)
            mid_x = (prev_x + x) / 2
            mid_y = (prev_y + y) / 2
            self.create_text(mid_x, mid_y-distance_offset, text=f"{distance_m:.2f}m", 
                          font=("Arial", max(int(8 / self.zoom_factor), 6)), fill="blue", tags='waypoint')
        
        # If robot is moving along path, mark current target point
        highlight_size = 10 / self.zoom_factor
        if hasattr(self, 'path_manager') and self.path_manager.active:
            current_idx = self.path_manager.current_waypoint_index
            if (current_idx >= 0 and current_idx < len(waypoints)):
                current_x, current_y = waypoints[current_idx]
                # Draw a larger circle to mark the target waypoint
                self.create_oval(current_x-highlight_size, current_y-highlight_size, 
                              current_x+highlight_size, current_y+highlight_size, 
                              outline='green', width=max(1, 3/self.zoom_factor), 
                              dash=(max(1, int(3/self.zoom_factor)), max(1, int(3/self.zoom_factor))), 
                              tags='waypoint')

    def clear_path(self):
        """Clear current path"""
        if hasattr(self, 'path_manager'):
            self.path_manager.waypoints = []
            self.path_manager.waypoints_real = []
            self.path_manager.current_waypoint_index = 0
        
        self.drawing_path = False
        self.waypoints = []
        self.delete('waypoint')
        self.delete('drawing_instructions')
        self.update_canvas()

    def rotate_selected_clockwise(self, event=None):
        """Rotate selected robot clockwise when right arrow key is pressed"""
        if self.selected_robot:
            # Rotate robot 5 degrees clockwise
            new_angle = (self.selected_robot.orientation + 5) % 360
            self.selected_robot.set_orientation(new_angle)
            self.update_canvas()
        return "break"  # Prevent event propagation

    def rotate_selected_counterclockwise(self, event=None):
        """Rotate selected robot counterclockwise when left arrow key is pressed"""
        if self.selected_robot:
            # Rotate robot 5 degrees counterclockwise
            new_angle = (self.selected_robot.orientation - 5) % 360
            self.selected_robot.set_orientation(new_angle)
            self.update_canvas()
        return "break"  # Prevent event propagation

    def start_path_following(self, leader_id=None):
        """Start leader robot movement along path"""
        if not hasattr(self, 'path_manager'):
            from models.path_manager import PathManager
            self.path_manager = PathManager(self.simulation)
        
        if not self.path_manager.waypoints:
            print("No path available. Please draw a path first.")
            # Could display error message here
            return
        
        # If no leader_id specified, use currently selected robot
        if leader_id is None and self.selected_robot_id:
            leader_id = self.selected_robot_id
        
        if self.path_manager.start(leader_id):
            print(f"Started robot {leader_id} movement along path")
        else:
            print("Cannot start path following movement")

    def on_start_following(self):
        """Start path following movement"""
        # Get leader robot from dropdown (via control_panel)
        if hasattr(self, 'control_panel') and hasattr(self.control_panel, 'path_leader_var'):
            leader_str = self.control_panel.path_leader_var.get()
            if leader_str:
                try:
                    leader_id = int(leader_str.split()[1])
                    # Set leader robot and start movement
                    self.start_path_following(leader_id)
                    return
                except (ValueError, IndexError):
                    pass
        
        # If cannot get from dropdown, use selected robot
        self.start_path_following()

    def _handle_follower_obstacle_avoidance(self, robot, robot_ahead, other_robots, desired_distance_px):
        """
        Handle obstacle avoidance for follower robots in the formation
        
        Args:
            robot: The current follower robot
            robot_ahead: The robot this follower should follow
            other_robots: All other robots to avoid (excluding robot_ahead)
            desired_distance_px: Target following distance in pixels
        """
        # Initialize safety parameters
        safety_margin = 1.2
        obstacle_threshold_px = robot.size + safety_margin * robot.size
        
        # Calculate primary direction vector toward the robot ahead
        dx = robot_ahead.x - robot.x
        dy = robot_ahead.y - robot.y
        global_distance = math.sqrt(dx*dx + dy*dy)
        
        # Normalize the primary direction vector
        if global_distance > 0:
            direction_x = dx / global_distance
            direction_y = dy / global_distance
        else:
            direction_x, direction_y = 0, 0
        
        # Calculate avoidance vectors from all other robots
        avoidance_x, avoidance_y = 0, 0
        avoidance_count = 0
        
        for other_robot in other_robots:
            # Skip if it's the same robot or the robot ahead
            if other_robot.id == robot.id or other_robot.id == robot_ahead.id:
                continue
            
            # Calculate distance to other robot
            other_dx = robot.x - other_robot.x
            other_dy = robot.y - other_robot.y
            other_distance = math.sqrt(other_dx*other_dx + other_dy*other_dy)
            
            # Check if robot is too close
            min_safe_distance = obstacle_threshold_px + other_robot.size / 2
            
            if other_distance < min_safe_distance:
                # Calculate avoidance vector (away from obstacle)
                avoidance_factor = 1.0 - (other_distance / min_safe_distance)
                avoidance_strength = avoidance_factor * min_safe_distance * 0.3  # Reduce factor to avoid moving too fast
                
                # Normalize avoidance direction
                if other_distance > 0:
                    avoidance_x += (other_dx / other_distance) * avoidance_strength
                    avoidance_y += (other_dy / other_distance) * avoidance_strength
                    avoidance_count += 1
        
        # Determine the final movement vector
        move_x, move_y = 0, 0
        move_distance = 0
        
        # First calculate the following component
        if abs(global_distance - desired_distance_px) > desired_distance_px * 0.1:
            # Calculate speed factor
            move_speed_factor = 0.2  # Reduce movement speed for smoother motion
            
            if global_distance > desired_distance_px:
                # Too far - move toward robot ahead
                move_distance = min(8.0, (global_distance - desired_distance_px) * move_speed_factor)
                move_x = direction_x * move_distance
                move_y = direction_y * move_distance
            else:
                # Too close - back away
                move_distance = min(6.0, (desired_distance_px - global_distance) * move_speed_factor)
                move_x = -direction_x * move_distance
                move_y = -direction_y * move_distance
        
        # Apply avoidance if needed
        if avoidance_count > 0:
            # Combine following direction with avoidance
            # When very close to obstacles, prioritize avoidance
            avoidance_weight = min(0.7, 0.3 + avoidance_count * 0.1)
            following_weight = 1.0 - avoidance_weight
            
            # Combine vectors
            final_x = move_x * following_weight + avoidance_x * avoidance_weight
            final_y = move_y * following_weight + avoidance_y * avoidance_weight
            
            # Apply the combined movement
            robot.move(final_x, final_y)
            print(f"Robot {robot.id} avoiding collision with other robots while following {robot_ahead.id}")
        else:
            # No obstacles - just follow the robot ahead
            robot.move(move_x, move_y)

    def cleanup(self):
        """Clear all before closing the visualization"""
        # Stop path manager
        if hasattr(self, 'path_manager'):
            self.path_manager.active = False
            self.path_manager.stop()
        
        # Cancel any animation timers
        if hasattr(self, '_animation_after_id') and self._animation_after_id:
            self.after_cancel(self._animation_after_id)
            self._animation_after_id = None