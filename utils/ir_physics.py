import math
import random
import numpy as np
from utils.geometry import distance_between_points, check_line_of_sight

def calculate_ir_signal_strength(transmitter, receiver, simulation=None, tx_pos=None, rx_pos=None):
    """Calculate IR signal strength between transmitter and receiver"""
    # Check clearly both transmitter and receiver
    from models.ir_sensor import IRReceiver, IRTransmitter
    
    # Debug: Check if transmitter and receiver roles are reversed
    if isinstance(transmitter, IRReceiver):
        print(f"ERROR: Receiver (IRReceiver) ID={transmitter.robot_id}, Side={transmitter.side}, Index={transmitter.position_index} is being used as transmitter!")
        return 0
        
    if isinstance(receiver, IRTransmitter):
        print(f"ERROR: Transmitter (IRTransmitter) ID={receiver.robot_id}, Side={receiver.side}, Index={receiver.position_index} is being used as receiver!")
        return 0
    
    # Ensure transmitter is IRTransmitter
    if not isinstance(transmitter, IRTransmitter):
        print(f"DEBUG: Object is not IRTransmitter! Type: {type(transmitter).__name__}")
        return 0  # If not IRTransmitter then no signal transmission
        
    # Ensure receiver is IRReceiver
    if not isinstance(receiver, IRReceiver):
        print(f"DEBUG: Object is not IRReceiver! Type: {type(receiver).__name__}")
        return 0  # If not IRReceiver then no signal reception
    
    # Continue with current validation
    if not hasattr(receiver, 'viewing_angle') or not hasattr(receiver, 'signals'):
        print(f"DEBUG: Receiver does not have viewing_angle or signals attribute!")
        return 0
    
    # If transmitter is not active, no signal
    if not transmitter.active:
        return 0
    
    # Use provided position or calculate if needed
    if tx_pos is None:
        if simulation:
            # Find robot with id = transmitter.robot_id
            tx_robot = next((r for r in simulation.robots if r.id == transmitter.robot_id), None)
            if not tx_robot:
                return 0
            tx_pos = transmitter.get_position(tx_robot.x, tx_robot.y, tx_robot.size, tx_robot.orientation)
        else:
            return 0  # Not enough information to calculate position
    
    if rx_pos is None:
        if simulation:
            rx_robot = next((r for r in simulation.robots if r.id == receiver.robot_id), None)
            if not rx_robot:
                return 0
            rx_pos = receiver.get_position(rx_robot.x, rx_robot.y, rx_robot.size, rx_robot.orientation)
        else:
            return 0  # Not enough information to calculate position
    
    # Calculate distance between transmitter and receiver
    dist_pixel = distance_between_points(tx_pos, rx_pos)
    
    # Convert distance from pixels to meters
    dist_meter = dist_pixel / simulation.scale if simulation else dist_pixel / 250
    
    # Check maximum distance
    if dist_pixel > transmitter.beam_distance:
        return 0
    
    # Calculate direction angle from transmitter to receiver
    dx = rx_pos[0] - tx_pos[0]
    dy = rx_pos[1] - tx_pos[1]
    angle_to_receiver = math.degrees(math.atan2(dy, dx))
    if angle_to_receiver < 0:
        angle_to_receiver += 360
    
    # Calculate beam direction of transmitter
    if simulation:
        tx_robot = next((r for r in simulation.robots if r.id == transmitter.robot_id), None)
        if tx_robot:
            beam_direction = transmitter.get_beam_direction(tx_robot.orientation)
        else:
            beam_direction = 0
    else:
        beam_direction = 0
    
    # Calculate beam direction angle difference
    angle_diff = abs((beam_direction - angle_to_receiver + 180) % 360 - 180)
    
    # If outside beam angle, no signal
    if angle_diff > transmitter.beam_angle / 2:
        return 0
    
    # Calculate emission angle in radians and angle ratio
    angle_ratio = angle_diff / (transmitter.beam_angle / 2)
    
    # --- Check receiver viewing angle ---
    if simulation:
        rx_robot = next((r for r in simulation.robots if r.id == receiver.robot_id), None)
        if rx_robot:
            receiver_direction = receiver.get_viewing_direction(rx_robot.orientation)
        else:
            receiver_direction = 0
    else:
        receiver_direction = 0
    
    # Calculate angle to transmitter from receiver
    dx_reverse = tx_pos[0] - rx_pos[0]
    dy_reverse = tx_pos[1] - rx_pos[1]
    angle_to_transmitter = math.degrees(math.atan2(dy_reverse, dx_reverse))
    if angle_to_transmitter < 0:
        angle_to_transmitter += 360
    
    # Calculate angle difference between receiver direction and transmitter direction
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # Maximum reception angle
    max_reception_angle = receiver.viewing_angle
    
    # If outside reception angle, no signal
    if receiver_angle_diff > max_reception_angle / 2:
        return 0
    
    # Calculate transmission and reception angle factors
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    
    # ---------- USE ONLY PATHLOSS MODEL ----------
    # Apply pathloss model
    path_loss = calculate_pathloss(
        distance=dist_meter,
        frequency=940e9,  # IR typically ~940nm
        path_loss_exponent=2.0,  # Free space
        shadow_fading_std=1.5     # Reduce shadow fading for more stable signals
    )
    
    # Convert pathloss to signal attenuation factor (0-1)
    distance_factor = 10 ** (-path_loss / 10)
    
    # Limit distance_factor to non-negative values
    distance_factor = max(0, min(1, distance_factor))
    
    # Combine factors - use only pathloss for distance attenuation
    combined_factor = distance_factor * tx_angle_factor * rx_angle_factor
    
    # Calculate final signal strength
    sensitivity_factor = receiver.sensitivity / 40.0
    signal_strength = transmitter.strength * combined_factor * sensitivity_factor
    
    # Add to calculate_ir_signal_strength
    print(f"Distance: {dist_meter}m, Raw signal: {transmitter.strength * distance_factor * tx_angle_factor * rx_angle_factor}")
    
    # Check threshold
    min_threshold = 3  # Instead of 8 or 5
    if signal_strength < min_threshold:
        return 0
    
    return max(0, min(100, signal_strength))

def adjust_strength_by_direction(transmitter, receiver, strength):
    """Adjust signal strength based on transmission and reception direction"""
    # Default adjustment factor
    return strength * 0.8

def calculate_ir_signal_strength_rician(transmitter, receiver, simulation, tx_pos=None, rx_pos=None):
    """Calculate IR signal strength using Rician model (with LOS and NLOS)"""
    # Get transmitter/receiver positions if not provided
    if tx_pos is None or rx_pos is None:
        tx_robot = simulation.get_robot_by_id(transmitter.robot_id)
        rx_robot = simulation.get_robot_by_id(receiver.robot_id)
        
        if tx_robot is None or rx_robot is None:
            return 0
        
        tx_pos = transmitter.get_position(tx_robot.x, tx_robot.y, tx_robot.size, tx_robot.orientation)
        rx_pos = receiver.get_position(rx_robot.x, rx_robot.y, rx_robot.size, rx_robot.orientation)
    
    # Calculate distance
    dist = distance_between_points(tx_pos, rx_pos)
    
    # Maximum limit
    if dist > transmitter.beam_distance:
        return 0
    
    # Calculate transmission and reception angles
    # Transmission angle - from transmitter to receiver
    angle_to_receiver = math.degrees(math.atan2(rx_pos[1] - tx_pos[1], rx_pos[0] - tx_pos[0]))
    if angle_to_receiver < 0:
        angle_to_receiver += 360
    transmitter_direction = transmitter.get_beam_direction(simulation.get_robot_by_id(transmitter.robot_id).orientation)
    angle_diff = abs((transmitter_direction - angle_to_receiver + 180) % 360 - 180)
    
    # Reception angle - from receiver to transmitter
    # Calculate the angle from receiver to transmitter
    dx = tx_pos[0] - rx_pos[0]
    dy = tx_pos[1] - rx_pos[1]
    angle_to_transmitter = math.degrees(math.atan2(dy, dx))
    if angle_to_transmitter < 0:
        angle_to_transmitter += 360
    receiver_direction = receiver.get_viewing_direction(simulation.get_robot_by_id(receiver.robot_id).orientation)
    receiver_angle_diff = abs((receiver_direction - angle_to_transmitter + 180) % 360 - 180)
    
    # Check if within transmission and reception angles
    if angle_diff > transmitter.beam_angle / 2 or receiver_angle_diff > receiver.viewing_angle / 2:
        return 0
    
    # Check LOS - collect obstacles
    obstacles = []
    for robot in simulation.robots:
        if robot.id != transmitter.robot_id and robot.id != receiver.robot_id:
            # Create polygon from robot position
            robot_polygon = [
                (robot.x - robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y - robot.size/2),
                (robot.x + robot.size/2, robot.y + robot.size/2),
                (robot.x - robot.size/2, robot.y + robot.size/2)
            ]
            obstacles.append(robot_polygon)
    
    # Check line of sight
    has_los = check_line_of_sight(tx_pos, rx_pos, obstacles)
    
    # Determine K-factor based on LOS
    k_factor = 0.0 if has_los else 0.5
    
    # Calculate LOS (direct) component
    los_power = k_factor/(k_factor+1) * transmitter.strength * math.exp(-(dist/transmitter.beam_distance) * 0.8)  # 1.2 -> 0.8
    
    # Calculate NLOS (scattered) component
    nlos_power = 1 / (k_factor + 1) * transmitter.strength * math.exp(-(dist / transmitter.beam_distance) * 1.6)  # 1.8 -> 1.6 
    
    # Add angle characteristics to signal
    tx_angle_factor = math.cos(math.radians(angle_diff)) ** 2
    rx_angle_factor = math.cos(math.radians(receiver_angle_diff)) ** 2
    angle_factor = tx_angle_factor * rx_angle_factor
    
    # Combine LOS and NLOS signals according to Rician model
    signal_strength = (los_power + nlos_power) * angle_factor
    
    # Add random noise (characteristic of wireless transmission channel)
    noise_factor = 1.0 + random.uniform(-0.1, 0.1)
    signal_strength *= noise_factor
    
    # Minimum threshold
    if signal_strength < 8:
        return 0
        
    return min(signal_strength, 100)  # Limit maximum signal to 100

def calculate_pathloss(distance, frequency=940e9, path_loss_exponent=1.6, shadow_fading_std=0.1):
    """
    Calculate signal attenuation based on pathloss model (adjusted)
    
    Args:
        distance: Distance between transmitter and receiver (m)
        frequency: IR signal frequency (Hz), default is 940 THz
        path_loss_exponent: Reduced from 2.0 to 1.6 for longer signal range
        shadow_fading_std: Reduced from 0.5 to 0.1 to minimize random effects
    """
    # Calculate wavelength (λ) from frequency
    c = 3e8  # Speed of light (m/s)
    wavelength = c / frequency
    
    # Increase reference distance to reduce initial path loss
    reference_distance = 0.2  # Increased from 0.1 to 0.2
    
    # Reduce basic attenuation
    if distance <= reference_distance:
        return 0  # No attenuation when too close
    
    # Calculate pathloss at reference distance (reduce factor)
    fspl_ref = 20 * math.log10(4 * math.pi * reference_distance / wavelength)  # Reduced from 20 to 15
    
    # Calculate pathloss at actual distance with lower attenuation factor
    path_loss = fspl_ref + 10 * path_loss_exponent * math.log10(distance / reference_distance)
    
    # Reduce shadow fading (reduce random factor)
    if shadow_fading_std > 0:
        shadow_fading = np.random.normal(0, shadow_fading_std)
        path_loss += shadow_fading
    
    return path_loss * 0.8  # Reduce total attenuation by 20%

# Convert pathloss (dB) to intensity attenuation factor
def pathloss_to_signal_factor(path_loss):
    """Convert pathloss (dB) to intensity attenuation factor (0-1)"""
    # Map pathloss from dB to linear factor
    # pathloss = -10 * log10(power_ratio) => power_ratio = 10^(-pathloss/10)
    return 10 ** (-path_loss / 10)

# Common pathloss calculation function to synchronize between modules
def calculate_pathloss_rician(distance, has_los=True, frequency=940e9, shadow_fading_std=0.1):
    """
    Calculate signal attenuation using pathloss model according to the formula:
    L(d) = L(d₀) + 10n·log(d/d₀)
    """
    # Calculate wavelength
    c = 3e8  # Speed of light
    wavelength = c / frequency
    
    # Reference distance d₀ = 1m (according to standard)
    reference_distance = 1.0
    
    # No attenuation when too close
    if distance <= 0.05:  # 5cm
        return 0
        
    # Calculate L(d₀) - attenuation at reference distance
    # Formula: L(d₀) = 20·log₁₀(4π·d₀/λ)
    L_d0 = 20 * math.log10(4 * math.pi * reference_distance / wavelength)
    
    # Choose path loss exponent n suitable for the environment
    # and customize according to distance
    if distance < 0.2:  # Close (under 20cm)
        path_loss_exponent = 1.8 if has_los else 2.5
    elif distance < 0.5:  # Medium (20-50cm)
        path_loss_exponent = 2.0 if has_los else 3.0
    else:  # Far (over 50cm)
        path_loss_exponent = 2.5 if has_los else 3.5
    
    # Apply pathloss formula: L(d) = L(d₀) + 10n·log₁₀(d/d₀)
    path_loss = L_d0 + 10 * path_loss_exponent * math.log10(distance / reference_distance)
    
    # Add shadow fading effect (attenuation due to obstacles)
    if shadow_fading_std > 0:
        shadow_fading = np.random.normal(0, shadow_fading_std)
        path_loss += shadow_fading
    
    # Apply attenuation reduction factor for longer signal range in simulation
    # This value can be adjusted to match desired results
    attenuation_factor = 0.6 if has_los else 0.8
    
    return path_loss * attenuation_factor

# Function to calculate signal from distance (direction from distance -> signal)
def distance_to_signal_strength(distance, tx_strength, rx_sensitivity, k_factor, angle_factor, has_los=True):
    """
    Calculate signal strength from distance based on Pathloss-Rician model
    """
    # If distance is very close, return strong signal
    if distance <= 0.05:  # Under 5cm
        return tx_strength * angle_factor * (rx_sensitivity / 50.0) * 0.95
    
    # ADDED: Ensure close distance to reference_distance has minimum signal
    if distance < 0.25:  # Within range 5cm to 25cm
        min_signal = 15 + (0.25 - distance) * 200  # Minimum signal decreases gradually from 55 to 15
        
    # Calculate pathloss with adjusted parameters
    path_loss = calculate_pathloss_rician(distance, has_los)
    
    # Convert from pathloss to attenuation factor (0-1)
    path_loss_factor = 10 ** (-path_loss / 10)
    
    # Increase k_factor to create stronger signal when LOS exists
    k_factor = 12.0 if has_los else 0.8  # Increased from 10.0 to 12.0 for LOS
    
    # LOS and NLOS components according to Rician model
    los_factor = k_factor / (k_factor + 1)
    nlos_factor = 1 / (k_factor + 1)
    
    # Calculate signal strength
    los_component = los_factor * tx_strength * path_loss_factor
    nlos_component = nlos_factor * tx_strength * path_loss_factor * 0.8  # NLOS is 20% weaker
    
    signal_strength = (los_component + nlos_component) * angle_factor * (rx_sensitivity / 50.0)
    
    # ADDED: Apply minimum threshold for close distances
    if distance < 0.25:  # Within 25cm range
        signal_strength = max(signal_strength, min_signal)
    
    return min(100, max(0, signal_strength))

# Function to estimate distance from signal (direction from signal -> distance)
def signal_strength_to_distance(signal_strength, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Estimate distance from signal strength based on inverse Pathloss-Rician model
    """
    # Remove influence of angle and sensitivity
    normalized_signal = signal_strength / ((rx_sensitivity / 50.0) * angle_factor)
    
    # K-factor based on LOS/NLOS
    k_factor = 6.0 if has_los else 0.5
    
    # Adjustment factor based on LOS/NLOS
    los_factor = 0.9 if has_los else 1.2
    
    # Calculate inverse of pathloss
    if normalized_signal <= 0:
        return float('inf')  # Cannot estimate distance
        
    # Signal ratio compared to original signal
    signal_ratio = normalized_signal / tx_strength
    
    # Convert signal ratio to path loss
    estimated_path_loss = -10 * math.log10(signal_ratio) / 0.8
    
    # Parameters for reverse distance calculation
    c = 3e8
    frequency = 940e9
    wavelength = c / frequency
    reference_distance = 0.2
    path_loss_exponent = 1.8 * los_factor
    
    # Basic attenuation at reference distance
    fspl_ref = 15 * math.log10(4 * math.pi * reference_distance / wavelength)
    
    # Calculate distance from pathloss
    path_loss_diff = estimated_path_loss - fspl_ref
    if path_loss_diff <= 0:
        return reference_distance
        
    distance = reference_distance * 10 ** (path_loss_diff / (10 * path_loss_exponent))
    
    return distance

def distance_to_signal_strength_rician(distance, beam_distance, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Calculate signal strength with uniform attenuation according to beam length and Rician model
    
    Args:
        distance: Actual distance (m)
        beam_distance: Maximum beam length (m)
        tx_strength: Initial transmission strength (0-100)
        rx_sensitivity: Receiver sensitivity (0-100)
        angle_factor: Transmission-reception angle factor (0-1)
        has_los: Whether direct line of sight exists
    
    Returns:
        Signal strength (0-100)
    """
    # When distance exceeds beam_distance, no signal
    if distance >= beam_distance:
        return 0
    
    # Special handling for very close distances (≤ 10cm)
    if distance <= 0.10:
        return tx_strength * angle_factor * (rx_sensitivity / 40.0)  # Increase sensitivity by reducing from 45.0 to 40.0
    
    # === MAIN CHANGE: Use simple linear attenuation formula according to % beam length ===
    
    # 1. Calculate % distance ratio compared to beam length
    distance_ratio = distance / beam_distance  # 0 = beam origin, 1 = beam end
    
    # 2. Apply simple linear attenuation formula
    # Signal = 100% - (% distance)^0.6
    # Power 0.6 makes attenuation slower than power 1.0 (linear)
    # Reduced from 0.8 to 0.6 for even slower attenuation
    signal_factor = (1.0 - distance_ratio) ** 0.6
    
    # 3. Apply simplified Rician model just for light noise
    k_factor = 10.0 if has_los else 0.5
    los_factor = k_factor / (k_factor + 1.0)
    nlos_factor = 1.0 / (k_factor + 1.0)
    
    # 4. Calculate main signal components
    # Simplified, no major difference between LOS and NLOS
    los_component = los_factor * tx_strength * signal_factor
    nlos_component = nlos_factor * tx_strength * signal_factor * 0.95  # NLOS only 5% weaker
    
    # 5. Combine LOS and NLOS
    # Increase sensitivity factor by reducing denominator from 45.0 to 40.0
    signal_strength = (los_component + nlos_component) * angle_factor * (rx_sensitivity / 40.0)
    
    # 6. Add very small random noise for more natural behavior
    noise = random.uniform(-0.5, 0.5) if has_los else random.uniform(-1, 1)
    signal_strength += noise
    
    # 7. Ensure very close distances always have strong signal
    # Instead of using multiple thresholds, use a smoother formula
    if distance_ratio < 0.3:  # First 30% of beam
        min_signal = 100 - (distance_ratio / 0.3) * 50  # From 100 down to 50
        signal_strength = max(signal_strength, min_signal)
    
    return min(100, max(0, signal_strength))

def signal_strength_to_distance_rician(signal_strength, beam_distance, tx_strength, rx_sensitivity, angle_factor, has_los=True):
    """
    Estimate distance from signal strength based on inverse model
    
    Args:
        signal_strength: Measured signal strength (0-100)
        beam_distance: Maximum beam length (m)
        tx_strength: Initial transmission strength (0-100)
        rx_sensitivity: Receiver sensitivity (0-100)
        angle_factor: Transmission-reception angle factor (0-1)
        has_los: Whether direct line of sight exists
    
    Returns:
        Estimated distance (m)
    """
    # Special cases - signal too weak or too strong
    if signal_strength <= 1:
        return beam_distance * 0.95  # Nearly equal to beam_distance
    elif signal_strength >= 95:  # Very close to source
        return 0.05
    
    # Remove noise influence and adjust sensitivity
    normalized_signal = signal_strength / (angle_factor * (rx_sensitivity / 50.0))
    los_factor = 1.0 if has_los else 0.7
    normalized_signal = normalized_signal / (los_factor * tx_strength)
    
    # Solve inverse equation to find distance
    # Divide into ranges to reflect uneven signal attenuation
    if normalized_signal > 0.7:  # Strong signal - close range
        # Inverse power function 0.7
        distance_factor = normalized_signal ** (1/0.7)
        distance = beam_distance * (1.0 - distance_factor)
    elif normalized_signal > 0.3:  # Medium signal - middle range
        # Inverse linear function
        distance_factor = normalized_signal
        distance = beam_distance * (1.0 - distance_factor)
    else:  # Weak signal - far range
        # Inverse power function 1.5
        distance_factor = normalized_signal ** (1/1.5)
        distance = beam_distance * (1.0 - distance_factor)
    
    # Add small random noise
    noise_factor = random.uniform(0.95, 1.05)
    distance *= noise_factor
    
    # Ensure distance is within reasonable limits
    return max(0.05, min(beam_distance, distance))