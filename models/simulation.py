import time
import threading
from models.robot import Robot
from utils.ir_physics import calculate_ir_signal_strength
from models.ir_sensor import can_receive_signal  # Add this line

class Simulation:
    def __init__(self):
        self.robots = []
        self.obstacles = []
        self.running = False
        self.simulation_thread = None
        self.next_robot_id = 1
        
        # Real environment size (m)
        self.real_width = 4.0  # 4m
        self.real_height = 4.0  # 4m
        
        # Add max_x and max_y for coordinate conversion
        self.max_x = self.real_width * 250  # Pixel
        self.max_y = self.real_height * 250  # Pixel
        
        # Real robot size (m)
        self.real_robot_size = 0.1  # 10cm
        
        # Conversion ratio from m to pixels
        self.scale = 250  # Increased from 150 to 250 pixel/m

        self.debug_mode = False  # Changed from True to False
    
    def add_robot(self, x=100, y=100, orientation=0):
        """Add new robot to simulation"""
        robot = Robot(self.next_robot_id, x, y, orientation)
        # Set robot size according to scale
        robot.size = self.real_robot_size * self.scale
        robot.simulation = self  # Set reference to simulation
        self.robots.append(robot)
        self.next_robot_id += 1

        return robot
    
    def remove_robot(self, robot_id=None):
        """Remove robot from simulation"""
        if robot_id is None and self.robots:
            self.robots.pop()  # Remove last robot if no ID specified
            return True
        
        for i, robot in enumerate(self.robots):
            if robot.id == robot_id:
                self.robots.pop(i)
                return True
        return False
    
    def start(self):
        """Start simulation"""
        if not self.running:
            # Clear all signals before starting
            for robot in self.robots:
                for receiver in robot.receivers:
                    receiver.clear_signals()
                    
            self.running = True
            try:
                self.simulation_thread = threading.Thread(target=self.run_simulation)
                self.simulation_thread.daemon = True
                self.simulation_thread.start()
            except Exception as e:
                print(f"Error initializing simulation thread: {e}")
                self.running = False
    
    def stop(self):
        """Stop simulation"""
        self.running = False
        if self.simulation_thread:
            try:
                # Increase timeout for thread join
                self.simulation_thread.join(timeout=3.0)
                if self.simulation_thread.is_alive():
                    print("Warning: Simulation thread could not be stopped. Continuing...")
            except Exception as e:
                print(f"Error stopping thread: {e}")
            finally:
                self.simulation_thread = None
    
    def reset(self):
        """Reset simulation"""
        self.stop()
        self.robots.clear()
        self.obstacles.clear()
        self.next_robot_id = 1
    
    def run_simulation(self):
        """Main simulation loop"""
        try:
            iteration_count = 0
            max_iterations = 10000  # Limit iterations to avoid infinite loops
            
            while self.running and iteration_count < max_iterations:
                try:
                    self.update()
                    # Clear signals after each update to avoid accumulation
                    self._clear_all_signals()
                    time.sleep(0.05)  # 20 FPS simulation rate
                    iteration_count += 1
                except Exception as e:
                    print(f"Error in simulation loop: {e}")
                    time.sleep(1)  # Pause if error occurs to avoid fast looping
                    
            if iteration_count >= max_iterations:
                print("Warning: Reached maximum iteration limit. Stopping simulation to avoid infinite loop.")
                self.running = False
                
        except Exception as e:
            print(f"Critical error in simulation thread: {e}")
            self.running = False
    
    def _clear_all_signals(self):
        """Clear all received IR signals to avoid accumulation"""
        for robot in self.robots:
            for receiver in robot.receivers:
                # Ensure signals are cleared
                receiver.clear_signals()
                # Add this line to also clear estimated_distances if they exist
                if hasattr(receiver, 'estimated_distances'):
                    receiver.estimated_distances = {}
    
    def get_robot_at(self, x, y):
        """Get robot at position (x, y)"""
        for robot in self.robots:
            if robot.contains_point(x, y):
                return robot
        return None
    
    def real_to_pixel(self, real_x, real_y):
        """Convert real coordinates (m) to pixels"""
        pixel_x = real_x * self.scale
        pixel_y = real_y * self.scale
        return pixel_x, pixel_y
    
    def pixel_to_real(self, pixel_x, pixel_y):
        """Convert pixel coordinates to real (m)"""
        real_x = pixel_x / self.scale
        real_y = pixel_y / self.scale
        return real_x, real_y

    def real_distance_to_pixel(self, real_distance):
        """Convert real distance (m) to pixels"""
        return round(real_distance * self.scale, 2)

    def pixel_distance_to_real(self, pixel_distance):
        """Convert pixel distance to real (m)"""
        return round(pixel_distance / self.scale, 2)

    def get_robot_by_id(self, robot_id):
        """Get robot by ID"""
        for robot in self.robots:
            if robot.id == robot_id:
                return robot
        return None   
     
    def update(self):
        """Update one simulation step"""
        # Clear all signals from previous loop
        for robot in self.robots:
            for receiver in robot.receivers:
                receiver.clear_signals()
        
        # Collect robot positions
        robot_positions = {}
        for robot in self.robots:
            robot_positions[robot.id] = {
                'x': robot.x,
                'y': robot.y,
                'size': robot.size,
                'orientation': robot.orientation
            }
        
        # Collect obstacles
        obstacles = []
        for robot in self.robots:
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
        
        # Calculate signals between robots
        from models.ir_sensor import can_receive_signal
        
        for tx_robot in self.robots:
            for transmitter in tx_robot.transmitters:
                if not transmitter.active:
                    continue
                    
                for rx_robot in self.robots:
                    if rx_robot.id == tx_robot.id:
                        continue  # Don't calculate signal from robot to itself
                        
                    for receiver in rx_robot.receivers:
                        # Use combined Pathloss-Rician model
                        can_receive, estimated_distance, signal_strength = can_receive_signal(
                            transmitter, receiver, robot_positions, obstacles)
                        
                        if can_receive:
                            receiver.add_signal(tx_robot.id, signal_strength)
                            # Save estimated distance if needed
                            if not hasattr(receiver, 'estimated_distances'):
                                receiver.estimated_distances = {}
                            receiver.estimated_distances[tx_robot.id] = estimated_distance
    
        # Other simulation updates...

    def update_robot_sizes(self):
        """Update size of all robots based on current scale"""
        # Round scale to avoid displaying many decimal places
        self.scale = round(self.scale, 2)
        print(f"Update robot sizes with scale {self.scale}")
        
        for robot in self.robots:
            old_size = robot.size
            robot.size = round(self.real_robot_size * self.scale, 2)  # Round size
            print(f"Robot {robot.id}: {old_size:.2f} -> {robot.size:.2f}")
            
            # Update transmission angle and distance of sensors
            for transmitter in robot.transmitters:
                # Remember real distance (m)
                real_distance = round(self.pixel_distance_to_real(transmitter.beam_distance), 2)
                # Reset transmission distance according to new scale
                pixel_distance = round(self.real_distance_to_pixel(real_distance), 2)
                transmitter.beam_distance = pixel_distance
                
                # Round stored real distance
                if hasattr(transmitter, 'real_beam_distance'):
                    transmitter.real_beam_distance = round(transmitter.real_beam_distance, 2)
            
            # Update sensor positions
            if hasattr(robot, 'update_sensor_positions'):
                robot.update_sensor_positions()
            
    def set_scale(self, new_scale):
        """Set new scale and update robot sizes"""
        self.scale = new_scale
        
        # Update max_x and max_y according to new scale
        self.max_x = self.real_width * new_scale
        self.max_y = self.real_height * new_scale
        
        self.update_robot_sizes()

    def meters_to_pixels(self, meters):
        """Convert from meters to pixels"""
        # Assume simulation scale, adjust according to your application
        return meters * 100  # 1m = 100px
