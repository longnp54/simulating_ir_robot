from models.ir_sensor import IRTransmitter, IRReceiver
import math

class Robot:
    def __init__(self, robot_id, x=0, y=0, orientation=0):
        self.id = robot_id
        self.x = x
        self.y = y
        self.orientation = orientation
        self.size = 50
        self.simulation = None  # Will be set when robot is added to simulation
        
        # Initialize sensor list with robot ID
        self.transmitters = []
        self.receivers = []
        self._setup_sensors()
    
    def _setup_sensors(self):
        """Set up IR transmitter and receiver sensors for robot"""
        sides = [0, 1, 2, 3]  # (top, right, bottom, left)
        
        # === CHANGE: Initialize transmitters ===
        self.transmitters = []
        
        # Set offset from edge for both transmitter and receiver
        sensor_offset_from_edge = 0.2  # 2cm from edge
        
        # Relative positions of 3 IR receivers (keep unchanged)
        receiver_positions = [-0.578, 0.0, 0.578]
        
        # === NEW: Relative positions of 2 IR transmitters interleaved ===
        # Calculate to place between IR receivers
        transmitter_positions = [-0.289, 0.289]  # Interleaved between receivers
        
        # === NEW: Angle offset for IR transmitters ===
        outward_offset_angle = 15  # Outward angle 15°
        
        # --- Set up transmitters first ---
        for side in sides:
            if side == 0:  # top
                for i, pos in enumerate(transmitter_positions):
                    rel_x = pos
                    rel_y = -1 + sensor_offset_from_edge
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Set outward angle offset
                    if i == 0:  # Left transmitter
                        tx.beam_direction_offset = -outward_offset_angle  # Negative
                    else:  # Right transmitter
                        tx.beam_direction_offset = +outward_offset_angle  # Positive
                    self.transmitters.append(tx)
            elif side == 1:  # right
                for i, pos in enumerate(transmitter_positions):
                    rel_x = 1 - sensor_offset_from_edge
                    rel_y = pos
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Set outward angle offset
                    if i == 0:  # Top transmitter
                        tx.beam_direction_offset = +outward_offset_angle
                    else:  # Bottom transmitter
                        tx.beam_direction_offset = -outward_offset_angle
                    self.transmitters.append(tx)
            elif side == 2:  # bottom
                for i, pos in enumerate(transmitter_positions):
                    rel_x = pos
                    rel_y = 1 - sensor_offset_from_edge
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Set outward angle offset
                    if i == 0:  # Left transmitter
                        tx.beam_direction_offset = outward_offset_angle
                    else:  # Right transmitter
                        tx.beam_direction_offset = -outward_offset_angle
                    self.transmitters.append(tx)
            else:  # left
                for i, pos in enumerate(transmitter_positions):
                    rel_x = -1 + sensor_offset_from_edge
                    rel_y = pos
                    tx = IRTransmitter(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Set outward angle offset
                    if i == 0:  # Top transmitter
                        tx.beam_direction_offset = -outward_offset_angle
                    else:  # Bottom transmitter
                        tx.beam_direction_offset = outward_offset_angle
                    self.transmitters.append(tx)
        
        # --- Set up receivers after ---
        self.receivers = []
        rx_outward_offset_angle = 30  # Outward angle for receiver
        # [Receiver setup code section remains unchanged]
        for side in sides:
            if side == 0:  # top
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = -1 + sensor_offset_from_edge
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Apply angle offset for outer receivers
                    if i == 0:  # Left receiver
                        rx.direction_offset = -rx_outward_offset_angle
                    elif i == 2:  # Right receiver
                        rx.direction_offset = rx_outward_offset_angle
                    self.receivers.append(rx)
            elif side == 1:  # right
                for i, pos in enumerate(receiver_positions):
                    rel_x = 1 - sensor_offset_from_edge
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Apply angle offset for outer receivers
                    if i == 0:  # Top receiver
                        rx.direction_offset = -rx_outward_offset_angle
                    elif i == 2:  # Bottom receiver
                        rx.direction_offset = rx_outward_offset_angle
                    self.receivers.append(rx)
            elif side == 2:  # bottom
                for i, pos in enumerate(receiver_positions):
                    rel_x = pos
                    rel_y = 1 - sensor_offset_from_edge
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Apply angle offset for outer receivers
                    if i == 0:  # Left receiver
                        rx.direction_offset = rx_outward_offset_angle
                    elif i == 2:  # Right receiver
                        rx.direction_offset = -rx_outward_offset_angle
                    self.receivers.append(rx)
            else:  # left
                for i, pos in enumerate(receiver_positions):
                    rel_x = -1 + sensor_offset_from_edge
                    rel_y = pos
                    rx = IRReceiver(self.id, side, i, rel_x=rel_x, rel_y=rel_y)
                    # Apply angle offset for outer receivers
                    if i == 0:  # Top receiver
                        rx.direction_offset = rx_outward_offset_angle
                    elif i == 2:  # Bottom receiver
                        rx.direction_offset = -rx_outward_offset_angle
                    self.receivers.append(rx)

    def move(self, dx, dy):
        """Move robot by an amount (dx, dy)"""
        self.x += dx
        self.y += dy
    
    def set_position(self, x, y):
        """Set new position for robot"""
        self.x = x
        self.y = y
    
    def rotate(self, angle):
        """Rotate robot by an angle (degrees)"""
        self.orientation = (self.orientation + angle) % 360
    
    def set_orientation(self, angle):
        """Set new orientation for robot (degrees)"""
        self.orientation = angle % 360
    
    def get_corner_positions(self):
        """Get coordinates of robot's 4 corners (after rotation)"""
        half_size = self.size / 2
        corners = [
            (-half_size, -half_size),  # Top left corner
            (half_size, -half_size),   # Top right corner
            (half_size, half_size),    # Bottom right corner
            (-half_size, half_size)    # Bottom left corner
        ]
        
        # Rotate corners according to orientation
        angle_rad = math.radians(self.orientation)
        rotated_corners = []
        
        for cx, cy in corners:
            # 2D rotation
            rotated_x = cx * math.cos(angle_rad) - cy * math.sin(angle_rad)
            rotated_y = cx * math.sin(angle_rad) + cy * math.cos(angle_rad)
            
            # Translate to actual position
            actual_x = self.x + rotated_x
            actual_y = self.y + rotated_y
            
            rotated_corners.append((actual_x, actual_y))
        
        return rotated_corners
    
    def contains_point(self, px, py):
        """Check if a point is inside the robot"""
        # Simple method: check distance from center to point
        # (this is approximate since when robot rotates, shape is no longer square relative to coordinate system)
        dx = px - self.x
        dy = py - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        return distance <= self.size / 2
    
    def calculate_relative_position(self, other_robot):
        """Calculate relative position of another robot"""
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Calculate angle (in degrees) from this robot to the other
        angle = math.degrees(math.atan2(dy, dx))
        
        # Relative angle (viewing angle from this robot's direction)
        relative_angle = (angle - self.orientation) % 360
        
        return distance, relative_angle
    
    def triangulate_position(self, bearing_measurements):
        """Estimate position based on bearing angle measurements
        
        bearing_measurements is a list of tuples (robot_id, bearing_angle)
        """
        if len(bearing_measurements) < 2:
            return None  # Need at least 2 bearing angles to triangulate
        
        # Simple triangulation method
        # (In practice, would need more complex algorithm)
        estimated_positions = []
        for robot_id, bearing in bearing_measurements:
            # Find target robot
            target_robot = None
            for robot in self.simulation.robots:
                if robot.id == robot_id:
                    target_robot = robot
                    break
            
            if target_robot:
                # From bearing and target robot position, calculate possible position
                bearing_rad = math.radians(bearing)
                dx = math.cos(bearing_rad)
                dy = math.sin(bearing_rad)
                estimated_positions.append((target_robot.x + dx, target_robot.y + dy))
        
        # Calculate average position
        if estimated_positions:
            avg_x = sum(pos[0] for pos in estimated_positions) / len(estimated_positions)
            avg_y = sum(pos[1] for pos in estimated_positions) / len(estimated_positions)
            return avg_x, avg_y
        
        return None
    
    def estimate_position_from_ir(self):
        """Estimate position based on received IR signals with Rician model"""
        position_estimates = []
        
        # Find position based on IR signals
        for i, receiver in enumerate(self.receivers):
            processed_signal = receiver.process_signals()
            if processed_signal:
                sender_id, strength, snr = processed_signal
                
                # Determine if LOS exists based on SNR
                has_los = snr > 2.5  # High SNR usually corresponds to good LOS
                
                # CHANGE: Use new method instead of old method
                # estimated_distance = receiver.estimate_distance_rician(strength, has_los) 
                estimated_distance = receiver.estimate_distance_pathloss_rician(strength, has_los)
                
                # Add to estimation list
                position_estimates.append((sender_id, estimated_distance, i))
        
        # NEW ADDITION: Use physical position when no IR signal available
        if not position_estimates and self.simulation:
            for robot in self.simulation.robots:
                if robot.id != self.id:
                    # Calculate physical distance
                    dx = robot.x - self.x
                    dy = robot.y - self.y
                    distance_pixel = math.sqrt(dx*dx + dy*dy)
                    distance_m = self.simulation.pixel_distance_to_real(distance_pixel)
                    
                    # Only consider robots within reasonable range (3m)
                    if distance_m < 3.0:
                        # Use code -1 to indicate this is estimation based on physical distance
                        position_estimates.append((robot.id, distance_m, -1))
        
        return position_estimates
    
    def update_sensor_positions(self):
        """Update positions of all sensors"""
        # This method is no longer needed since sensors will calculate position when needed
        pass
    
    def get_transmitter_positions(self):
        """Get positions of all transmitters"""
        positions = []
        for tx in self.transmitters:
            pos = tx.get_position(self.x, self.y, self.size, self.orientation)
            positions.append((tx, pos))
        return positions
    
    def get_receiver_positions(self):
        """Get positions of all receivers"""
        positions = []
        for rx in self.receivers:
            pos = rx.get_position(self.x, self.y, self.size, self.orientation)
            positions.append((rx, pos))
        return positions

    def get_physical_distance_to(self, other_robot):
        """Calculate physical distance to another robot in meters"""
        if not self.simulation:
            return float('inf')
            
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        distance_pixel = math.sqrt(dx*dx + dy*dy)
        return self.simulation.pixel_distance_to_real(distance_pixel)

    def get_bearing_to(self, other_robot):
        """Calculate absolute bearing angle to another robot (0-359 degrees)"""
        dx = other_robot.x - self.x
        dy = other_robot.y - self.y
        # Changed from atan2(-dy, dx) to atan2(dy, dx)
        angle = math.degrees(math.atan2(dy, dx)) % 360
        return angle

    def get_relative_angle_to(self, other_robot):
        """Calculate relative angle from current direction to another robot (0-359 degrees)"""
        absolute_angle = self.get_bearing_to(other_robot)
        relative_angle = (absolute_angle - self.orientation) % 360
        return relative_angle

    def calculate_relative_position_rpa(self, emitter_robot_id):
        """Calculate relative position of signal-emitting robot using RPA algorithm
        
        Process sensors according to continuous circle principle, without interruption at angles.
        Support cases with only 1 or 2 receivers receiving signals.
        
        Args:
            emitter_robot_id: ID of robot emitting signal
            
        Returns:
            tuple: (bearing_angle, distance, confidence) or None if insufficient data
        """
        import math
        
        # Default angle table for each side and position
        # Format: {side: {position_index: angle}}
        DEFAULT_ANGLES = {
            0: {0: 240, 1: 270, 2: 300},  # top
            1: {0: 330, 1: 0, 2: 30},     # right
            2: {0: 120, 1: 90, 2: 60},    # bottom
            3: {0: 210, 1: 180, 2: 150}   # left
        }
        
        # Collect all signals from all receivers
        all_signals = []
        
        for receiver in self.receivers:
            if emitter_robot_id in receiver.signals:
                signal_strength = receiver.signals[emitter_robot_id]
                angle = DEFAULT_ANGLES[receiver.side][receiver.position_index]
                all_signals.append((receiver.side, receiver.position_index, signal_strength, angle, receiver))
        
        # If no signals
        if not all_signals:
            return None
        
        # Find receiver with strongest signal
        strongest_signal = max(all_signals, key=lambda x: x[2])
        strongest_side, strongest_pos, r_0, base_angle, _ = strongest_signal
        
        # Sort all signals by increasing angle
        all_signals.sort(key=lambda x: x[3])
        
        # Number of signals
        total_signals = len(all_signals)
        
        # === SPECIAL CASE: Only 1 receiver receives signal ===
        if total_signals == 1:
            # When only 1 signal, need to rely on angle and signal strength
            theta = 0  # Assume emitter is straight ahead of receiver
            
            # Improvement: Relationship between signal strength and distance
            signal_strength_normalized = r_0 / 100.0  # Assume maximum strength is 100
            # Distance formula inversely proportional to square root of signal strength
            distance = 1.0 / math.sqrt(signal_strength_normalized) if signal_strength_normalized > 0 else 4.0
            
            # Apply angle for strongest receiver
            bearing = base_angle
            
            # Convert to real distance with better correction factor
            scale_factor = 0.15  # Reduce adjustment for more accurate distance
            real_distance = scale_factor * distance
            
            # Limit to reasonable distance
            real_distance = min(3.0, max(0.05, real_distance))
            
            # Set lower confidence since only 1 signal
            confidence = 0.2
            
            # Return result
            relative_bearing = bearing % 360
            return (relative_bearing, real_distance, confidence)
        
        # === SPECIAL CASE: Only 2 receivers receiving signals ===
        elif total_signals == 2:
            # Find position of strongest signal in sorted list
            strongest_index = next(i for i, signal in enumerate(all_signals) 
                                 if signal[0] == strongest_side and signal[1] == strongest_pos)
            
            # Get the remaining signal (will be left or right)
            other_index = 1 - strongest_index
            
            # Determine angle of the remaining signal
            other_angle = all_signals[other_index][3]
            other_signal = all_signals[other_index][2]
            
            # Calculate angle delta between two receivers
            delta_angle = (other_angle - base_angle) % 360
            if delta_angle > 180:
                delta_angle = delta_angle - 360
            
            # Determine r_minus1 and r_1 based on relative position
            if delta_angle > 0:  # Remaining signal is on the right side
                r_1 = other_signal
                
                # Calculate beta_1_right - angle with right receiver
                beta_1_right = min(abs(other_angle - base_angle), 360 - abs(other_angle - base_angle))
                if (other_angle - base_angle) % 360 > 180:
                    beta_1_right = -beta_1_right
                beta_1_right = math.radians(beta_1_right)
                
                # Estimate beta_1_left and r_minus1 (similar to the 3-signal case)
                # Assume symmetric angle and estimated intensity
                beta_1_left = -beta_1_right
                r_minus1 = r_0 * (r_0 / r_1) * 0.7
            else:  # Remaining signal is on the left side
                r_minus1 = other_signal
                
                # Calculate beta_1_left - angle with left receiver
                beta_1_left = min(abs(other_angle - base_angle), 360 - abs(other_angle - base_angle))
                if (base_angle - other_angle) % 360 > 180:
                    beta_1_left = -beta_1_left
                beta_1_left = math.radians(beta_1_left)
                
                # Estimate beta_1_right and r_1 (similar to the 3-signal case)
                beta_1_right = -beta_1_left
                r_1 = r_0 * (r_0 / r_minus1) * 0.7
            
            # Apply formula from algorithm same as the 3-signal case
            if abs(math.degrees(beta_1_right)) < 10 or abs(math.degrees(beta_1_left)) < 10:
                # If angle is too small, use default value
                beta_1 = math.pi / 6
                a = (r_1 + r_minus1 + 2*r_0) / (2 * math.cos(beta_1) + 2)
                b = (r_1 - r_minus1) / (2 * math.sin(beta_1))
            else:
                # Use general formula same as the 3-signal case
                a = (r_1 * math.cos(beta_1_right) + r_minus1 * math.cos(beta_1_left) + 
                    r_0 * (math.cos(beta_1_right) + math.cos(beta_1_left))) / (
                    math.cos(beta_1_right) + math.cos(beta_1_left) + 2)

                denominator = math.sin(beta_1_right) + math.sin(abs(beta_1_left))
                if abs(denominator) < 1e-6:
                    if r_1 > r_minus1:
                        b = 0.15 * a
                    elif r_1 < r_minus1:
                        b = -0.15 * a
                    else:
                        b = 0
                else:
                    b = (r_1 * math.sin(beta_1_right) - r_minus1 * math.sin(abs(beta_1_left))) / denominator
            
            # Calculate theta and distance
            theta = math.degrees(math.atan2(b, a))
            distance = math.sqrt(a*a + b*b)
            
            # Adjust confidence down since we're estimating one of the values
            confidence = min(r_0, other_signal) / max(r_0, other_signal) * 0.8
        
        # === NORMAL CASE: 3+ receivers receiving signals ===
        else:
            # Find position of strongest signal in sorted list
            strongest_index = next(i for i, signal in enumerate(all_signals) 
                                 if signal[0] == strongest_side and signal[1] == strongest_pos)
            
            # Get left and right signals
            left_index = (strongest_index - 1) % total_signals
            r_minus1 = all_signals[left_index][2]
            
            right_index = (strongest_index + 1) % total_signals
            r_1 = all_signals[right_index][2]
            
            # Calculate angles between receivers
            right_angle = all_signals[right_index][3]
            beta_1_right = min(abs(right_angle - base_angle), 360 - abs(right_angle - base_angle))
            if (right_angle - base_angle) % 360 > 180:
                beta_1_right = -beta_1_right
            beta_1_right = math.radians(beta_1_right)
            
            left_angle = all_signals[left_index][3]
            beta_1_left = min(abs(left_angle - base_angle), 360 - abs(left_angle - base_angle))
            if (base_angle - left_angle) % 360 > 180:
                beta_1_left = -beta_1_left
            beta_1_left = math.radians(beta_1_left)
            
            # Apply formula from algorithm
            if abs(math.degrees(beta_1_right)) < 10 or abs(math.degrees(beta_1_left)) < 10:
                # If angle is too small, use default value
                beta_1 = math.pi / 6
                a = (r_1 + r_minus1 + 2*r_0) / (2 * math.cos(beta_1) + 2)
                b = (r_1 - r_minus1) / (2 * math.sin(beta_1))
            else:
                # Use general formula
                a = (r_1 * math.cos(beta_1_right) + r_minus1 * math.cos(beta_1_left) + 
                    r_0 * (math.cos(beta_1_right) + math.cos(beta_1_left))) / (
                    math.cos(beta_1_right) + math.cos(beta_1_left) + 2)

                denominator = math.sin(beta_1_right) + math.sin(abs(beta_1_left))
                if abs(denominator) < 1e-6:
                    if r_1 > r_minus1:
                        b = 0.15 * a
                    elif r_1 < r_minus1:
                        b = -0.15 * a
                    else:
                        b = 0
                else:
                    b = (r_1 * math.sin(beta_1_right) - r_minus1 * math.sin(abs(beta_1_left))) / denominator
            
            # Calculate theta and distance
            theta = math.degrees(math.atan2(b, a))
            distance = math.sqrt(a*a + b*b)
            
            # Calculate confidence
            valid_signals = [r_minus1, r_0, r_1]
            confidence = min(valid_signals) / max(valid_signals) if max(valid_signals) > 0 else 0
        
        # Convert signal strength to real distance (meters)
        scale_factor = 0.3
        real_distance = scale_factor / distance if distance > 0 else 3.0
        
        # Limit distance within reasonable range
        real_distance = min(3.0, max(0.05, real_distance))
        
        # Calculate bearing angle
        bearing = (base_angle + theta) % 360
        absolute_bearing = bearing
        relative_bearing = absolute_bearing % 360
        
        # Print debug log if needed
        print(f"Debug RPA: bearing={bearing}, signals={total_signals}, result={relative_bearing}")
        
        return (relative_bearing, real_distance, confidence)

    def calculate_relative_coordinates(self, angle, distance, is_relative=True):
        """Calculate relative coordinates based on angle and distance
        
        Args:
            angle: Angle (degrees) - can be relative or absolute depending on is_relative
            distance: Distance (meters or pixels)
            is_relative: If True, angle is relative and needs orientation added
                        If False, angle is absolute and doesn't need orientation added
        """
        # Calculate angle in global coordinate system
        if is_relative:
            # If relative angle, add robot's orientation
            global_angle = angle % 360
        else:
            # If absolute angle, use directly   
            global_angle = (self.orientation + angle) % 360
            
        angle_rad = math.radians(global_angle)
        
        # Relative coordinates
        rel_x = distance * math.cos(angle_rad)
        rel_y = distance * math.sin(angle_rad)
        
        return (rel_x, rel_y)

    def move_forward(self, distance=0.02):
        """Move robot forward"""
        if self.simulation:
            px_distance = self.simulation.real_distance_to_pixel(distance)
        else:
            px_distance = distance * 250  # Default 250px/m
        
        angle_rad = math.radians(self.orientation)
        dx = px_distance * math.cos(angle_rad)
        dy = px_distance * math.sin(angle_rad)
        self.move(dx, dy)
    
    def move_backward(self, distance=0.02):
        """Move robot backward"""
        if self.simulation:
            px_distance = self.simulation.real_distance_to_pixel(distance)
        else:
            px_distance = distance * 250  # Default 250px/m
        
        angle_rad = math.radians(self.orientation)
        dx = -px_distance * math.cos(angle_rad)
        dy = -px_distance * math.sin(angle_rad)
        self.move(dx, dy)