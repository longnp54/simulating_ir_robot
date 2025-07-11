import math
from utils.geometry import distance_between_points, check_line_of_sight
import threading

class IRSensor:
    """Base class for IR sensor types"""
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        self.robot_id = robot_id    # Only store robot ID, not reference
        self.side = side            # 0: top, 1: right, 2: bottom, 3: left
        self.position_index = position_index
        self.rel_x = rel_x
        self.rel_y = rel_y
    
    def get_position(self, robot_x, robot_y, robot_size, robot_orientation):
        """Calculate sensor position based on robot information"""
        half_size = robot_size / 2
        
        # Relative position based on side and position_index
        if self.side == 0:  # top
            rel_x = self.rel_x * half_size
            rel_y = -half_size
        elif self.side == 1:  # right
            rel_x = half_size
            rel_y = self.rel_y * half_size
        elif self.side == 2:  # bottom
            rel_x = self.rel_x * half_size
            rel_y = half_size
        else:  # left
            rel_x = -half_size
            rel_y = self.rel_y * half_size
        
        # Apply rotation based on robot orientation
        import math
        angle_rad = math.radians(robot_orientation)
        rotated_x = rel_x * math.cos(angle_rad) - rel_y * math.sin(angle_rad)
        rotated_y = rel_x * math.sin(angle_rad) + rel_y * math.cos(angle_rad)
        
        # Final position
        return robot_x + rotated_x, robot_y + rotated_y

class IRTransmitter(IRSensor):
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        super().__init__(robot_id, side, position_index, rel_x, rel_y)
        self.beam_angle = 45  # Reduced from 120° to 45° - compatible with error notification
        self.beam_distance = 150  # pixel
        self.real_beam_distance = 0.6  # meters
        self.strength = 100
        self.active = True
        self.beam_direction_offset = 0
    
    def initialize_with_robot_size(self, robot_size):
        """Initialize attributes related to robot size"""
        self.base_robot_size = robot_size
        self.beam_to_robot_ratio = self.beam_distance / robot_size
        
    def get_beam_direction(self, robot_orientation):
        """Calculate beam direction based on robot orientation"""
        base_direction = 0
        if self.side == 0:  # top -> positive X axis
            base_direction = 270
        elif self.side == 1:  # right -> positive Y axis
            base_direction = 0
        elif self.side == 2:  # bottom -> negative X axis
            base_direction = 90
        else:  # left -> negative Y axis
            base_direction = 180
            
        return (base_direction + robot_orientation + self.beam_direction_offset) % 360

    def get_beam_cone(self, robot_x, robot_y, robot_size, robot_orientation):
        """
        Calculate beam cone for drawing on interface
        
        Returns:
            tuple: (start_angle, extent_angle, major_radius, minor_radius)
        """
        # Get transmitter position
        tx_pos = self.get_position(robot_x, robot_y, robot_size, robot_orientation)
        
        # Get beam direction
        beam_direction = self.get_beam_direction(robot_orientation)
        
        # Calculate start angle and beam width
        start_angle = (beam_direction - self.beam_angle / 2) % 360
        
        # Calculate major and minor radius for ellipse
        major_radius = self.beam_distance  # Long radius (along main direction)
        minor_radius = self.beam_distance * 0.6  # Short radius (narrower)
        
        # Return ellipse cone parameters
        return (start_angle, self.beam_angle, major_radius, minor_radius, beam_direction)

    def set_beam_parameters(self, angle, pixel_distance, simulation=None):
        """
        Set beam parameters
        
        Args:
            angle: Transmission angle in degrees
            pixel_distance: Transmission distance in pixels
            simulation: Simulation object for unit conversion (if needed)
        """
        self.beam_angle = angle
        self.beam_distance = pixel_distance
        
        # Save real distance if simulation is available
        if simulation:
            self.real_beam_distance = simulation.pixel_distance_to_real(pixel_distance)

class IRReceiver(IRSensor):
    def __init__(self, robot_id, side, position_index=0, rel_x=0, rel_y=0):
        super().__init__(robot_id, side, position_index, rel_x, rel_y)
        self.sensitivity = 50
        self.viewing_angle = 60
        self.max_distance = 200
        self.real_max_distance = 0.8
        self.direction_offset = 0
        self.signals = {}
        self.signals_lock = threading.Lock()
        self.snr = 0.0  # Add variable to store SNR
    
    def clear_signals(self):
        """Clear all received signals"""
        with self.signals_lock:  # Lock while modifying
            self.signals.clear()
    
    def add_signal(self, transmitter_id, strength):
        """Add signal from a transmitter"""
        with self.signals_lock:  # Lock while modifying
            self.signals[transmitter_id] = strength
    
    def get_total_signal(self):
        """Calculate total signal strength"""
        with self.signals_lock:
            return sum(self.signals.values()) if self.signals else 0

    def get_signals_copy(self):
        """Return safe copy of signals"""
        with self.signals_lock:
            return dict(self.signals) if self.signals else {}
            
    def get_strongest_signal(self):
        """Get strongest signal and corresponding transmitter"""
        with self.signals_lock:
            if not self.signals:
                return None
            
            # Find transmitter_id with highest signal strength
            strongest_tx_id = max(self.signals.items(), key=lambda x: x[1])[0]
            strength = self.signals[strongest_tx_id]
            
            # Return in old format: (sender_id, tx_side, strength)
            return (strongest_tx_id, 0, strength)

    def has_signals(self, min_strength=20):  # Increased from 15 to 20
        """Safely check if there are strong signals"""
        with self.signals_lock:
            # Check if any signal exceeds threshold
            return any(strength >= min_strength for strength in self.signals.values())

    def get_viewing_direction(self, robot_orientation):
        """Get receiver viewing direction, calculated in degrees (0-359)"""
        # Base direction depends on which side of robot the receiver is on
        if self.side == 0:  # Top
            base_direction = 270
        elif self.side == 1:  # Right
            base_direction = 0  
        elif self.side == 2:  # Bottom
            base_direction = 90
        else:  # Left
            base_direction = 180
        
        # Add robot orientation AND direction_offset to get actual direction
        return (base_direction + robot_orientation + self.direction_offset) % 360

    def set_receiver_parameters(self, angle, pixel_distance, simulation=None):
        """
        Set receiver parameters
        
        Args:
            angle: Reception angle in degrees
            pixel_distance: Maximum reception distance in pixels
            simulation: Simulation object for unit conversion (if needed)
        """
        self.viewing_angle = angle
        self.max_distance = pixel_distance
        
        # Save real distance if simulation is available
        if simulation:
            self.real_max_distance = simulation.pixel_distance_to_real(pixel_distance)

    def process_signals(self):
        """Process received signals, analyze overlapping"""
        with self.signals_lock:
            if not self.signals:
                return None
            
            # Find strongest signal
            strongest_tx_id = max(self.signals.items(), key=lambda x: x[1])[0]
            strongest_strength = self.signals[strongest_tx_id]
            
            # Calculate total interference from other signals
            interference = sum(strength for tx_id, strength in self.signals.items() 
                             if tx_id != strongest_tx_id)
            
            # Calculate SNR (Signal-to-Noise Ratio)
            snr = strongest_strength / (interference + 1.0)  # +1 to avoid division by zero
            
            # Save SNR information
            self.snr = snr
            
            # Only accept signal if SNR is high enough
            if snr < 1.5:  # SNR threshold to distinguish signals
                return None
                
            # Return strongest signal and SNR
            return strongest_tx_id, strongest_strength, snr

    def estimate_distance_rician(self, strength, has_los=True):
        """
        DEPRECATED: Use estimate_distance_pathloss_rician instead of this method.
        This method is only kept for compatibility with old code.
        """
        # Redirect call to new method
        return self.estimate_distance_pathloss_rician(strength, has_los)

    def estimate_distance_pathloss_rician(self, signal_strength, has_los=True):
        """
        Estimate distance based on Rician model with uniform attenuation
        """
        from utils.ir_physics import signal_strength_to_distance_rician
        
        # Estimate angle based on average value (actual angle unknown)
        average_angle_factor = 0.7  # Assumed average value
        
        # Use same new estimation function
        beam_distance_meter = 0.8  # Assume 0.8m if no information available
        if hasattr(self, 'real_max_distance'):
            beam_distance_meter = self.real_max_distance
            
        estimated_distance = signal_strength_to_distance_rician(
            signal_strength=signal_strength,
            beam_distance=beam_distance_meter,
            tx_strength=100,  # Assume maximum transmission strength
            rx_sensitivity=self.sensitivity,
            angle_factor=average_angle_factor,
            has_los=has_los
        )
        
        return estimated_distance

# Add to IR signal transmission and reception processing section
from utils.ir_physics import distance_to_signal_strength, signal_strength_to_distance

def can_receive_signal(transmitter, receiver, robot_positions, obstacles=None, debug=False):
    """
    Check and calculate signal from transmitter to receiver
    using Rician model with uniform attenuation
    """
    # Get position and orientation from robot_positions (keep unchanged)
    tx_robot = robot_positions[transmitter.robot_id]
    rx_robot = robot_positions[receiver.robot_id]
    
    # Calculate positions of transmitter and receiver
    tx_pos = transmitter.get_position(tx_robot['x'], tx_robot['y'], 
                                     tx_robot['size'], tx_robot['orientation'])
    rx_pos = receiver.get_position(rx_robot['x'], rx_robot['y'], 
                                  rx_robot['size'], rx_robot['orientation'])
    
    # Calculate distance between transmitter and receiver
    from utils.geometry import distance_between_points, check_line_of_sight
    dist_pixel = distance_between_points(tx_pos, rx_pos)
    
    # Convert distance from pixels to meters
    dist_meter = dist_pixel / 250
    
    # Convert beam_distance from pixels to meters
    beam_distance_meter = transmitter.beam_distance / 250
    
    # Check maximum distance
    if dist_pixel > transmitter.beam_distance:
        return False, 0, 0
    
    # Calculate angle from transmitter to receiver
    import math
    dx = rx_pos[0] - tx_pos[0]
    dy = rx_pos[1] - tx_pos[1]
    angle_to_receiver = math.degrees(math.atan2(dy, dx)) % 360
    
    # Get transmitter beam direction
    beam_direction = transmitter.get_beam_direction(tx_robot['orientation'])
    
    # Calculate angle difference
    angle_diff = abs((beam_direction - angle_to_receiver + 180) % 360 - 180)
    
    # If outside transmission angle, no signal
    if angle_diff > transmitter.beam_angle / 2:
        return False, 0, 0
    
    # Calculate angle from receiver to transmitter
    angle_to_transmitter = (math.degrees(math.atan2(-dy, -dx))) % 360
    
    # Get receiver viewing direction
    receiver_direction = receiver.get_viewing_direction(rx_robot['orientation'])
    
    # Calculate reception angle difference
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # If outside reception angle, no signal
    if receiver_angle_diff > receiver.viewing_angle / 2:
        return False, 0, 0
    
    # Calculate transmission and reception angle factors
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    angle_factor = tx_angle_factor * rx_angle_factor
    
    # Check line of sight
    has_los = True
    if obstacles:
        has_los = check_line_of_sight(tx_pos, rx_pos, obstacles)
    
    # Use new function to calculate signal strength - DO NOT use pathloss
    from utils.ir_physics import distance_to_signal_strength_rician
    
    signal_strength = distance_to_signal_strength_rician(
        distance=dist_meter,
        beam_distance=beam_distance_meter,
        tx_strength=transmitter.strength,
        rx_sensitivity=receiver.sensitivity,
        angle_factor=angle_factor,
        has_los=has_los
    )
    
    # Reduce minimum threshold to display weaker signals
    if signal_strength < 1.5:
        return False, 0, 0
    
    # Estimate distance based on signal
    from utils.ir_physics import signal_strength_to_distance_rician
    estimated_distance = signal_strength_to_distance_rician(
        signal_strength=signal_strength,
        beam_distance=beam_distance_meter, 
        tx_strength=transmitter.strength,
        rx_sensitivity=receiver.sensitivity,
        angle_factor=angle_factor,
        has_los=has_los
    )
    
    return True, estimated_distance, signal_strength

def update_canvas(self):
    """Update entire canvas"""
    # Clear all objects on canvas
    self.delete("all")
    self.robot_objects.clear()  # Clear robot object cache
    
    # Draw coordinate grid
    self._draw_grid()
    
    # Draw all robots
    for robot in self.simulation.robots:
        self._draw_robot(robot)
    
    # Draw IR signals if simulating - ONLY WHEN simulation.running = True
    if self.simulation.running:
        self._draw_ir_signals()