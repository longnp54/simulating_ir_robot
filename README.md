# IR ROBOT SIMULATION - COMMUNICATION THROUGH INFRARED SIGNALS

## 1. Introduction

This project simulates a system of robots communicating through infrared (IR) signals, allowing them to determine relative positions and perform tasks such as following predefined paths or moving in formation. The system is designed with an intuitive interface that enables users to interact with robots, set sensor parameters, and monitor simulation results.

![Main application interface](images/main_interface.png)

## 2. Mathematical Models

### 2.1. IR Signal Transmission/Reception Model

#### 2.1.1. Rician Model

The project uses the Rician channel model combined with a pathloss model to simulate infrared signal propagation, representing both Line of Sight (LOS) and Non-Line of Sight (NLOS) transmission paths.

The received signal strength is calculated using:

$$S = \left(\frac{K}{K+1}S_{LOS} + \frac{1}{K+1}S_{NLOS}\right) \cdot A_f \cdot \frac{R_s}{50}$$

Where:
- $S$ is the received signal strength
- $K$ is the Rician factor (K-factor), higher when LOS exists
- $S\_{LOS}$ is the LOS signal component
- $S\_{NLOS}$ is the NLOS signal component
- $A\_f$ is the angle-dependent attenuation factor
- $R\_s$ is the receiver sensitivity

#### 2.1.2. Pathloss Model

The pathloss is calculated using:

$$L(d) = L(d\_0) + 10 \cdot n \cdot \log\_{10}\left(\frac{d}{d\_0}\right) + X\_\sigma$$

Where:
- $L(d)$ is the path loss at distance $d$
- $L(d\_0)$ is the path loss at reference distance $d\_0$
- $n$ is the path loss exponent
- $X\_\sigma$ is the shadow fading component

The value of $L(d\_0)$ is calculated using:

$$L(d\_0) = 20 \cdot \log\_{10}\left(\frac{4\pi d\_0}{\lambda}\right)$$

Where $\lambda$ is the wavelength of the infrared signal.

#### 2.1.3. Angle-Dependent Attenuation Factor

The angle-dependent attenuation factor is calculated based on the angle between the transmitter and receiver directions:

$$A\_f = \cos^n(\theta)$$

Where:
- $\theta$ is the angle between transmitter and receiver directions
- $n$ is the exponent (typically between 1.5 and 2.0)

### 2.2. Relative Position Awareness (RPA)

#### 2.2.1. Triangulation Method

The RPA method uses signal strengths received from multiple receivers to estimate the bearing and distance to the transmitting robot.

When 3 receivers detect signals ($r\_{-1}$, $r\_0$, $r\_1$), with $r\_0$ being the strongest signal, the relative position is calculated as:

$$a = \frac{r\_1 \cdot \cos(\beta\_{1,right}) + r\_{-1} \cdot \cos(\beta\_{1,left}) + r\_0 \cdot (\cos(\beta\_{1,right}) + \cos(\beta\_{1,left}))}{\cos(\beta\_{1,right}) + \cos(\beta\_{1,left}) + 2}$$

$$b = \frac{r\_1 \cdot \sin(\beta\_{1,right}) - r\_{-1} \cdot \sin(|\beta\_{1,left}|)}{\sin(\beta\_{1,right}) + \sin(|\beta\_{1,left}|)}$$

$$\theta = \arctan2(b, a)$$

$$d = \sqrt{a^2 + b^2}$$

$$d\_{real} = \frac{scale_factor}{d}$$

Where:
- $\beta\_{1,right}$ and $\beta\_{1,left}$ are the angles between the strongest receiver and adjacent receivers
- $\theta$ is the relative angle
- $d$ is the distance in signal space
- $d\_{real}$ is the actual distance after applying a scale factor

![Relative position triangulation model](images/triangulation.png)

#### 2.2.2. Signal Strength-Based Estimation

When only 1 or 2 receivers detect a signal, the system uses a simpler estimation method:

$$d\_{real} = \frac{scale_factor}{\sqrt{signal\_strength}}$$

Where $signal\_strength$ is the normalized signal strength.

### 2.3. Path Following Control

#### 2.3.1. Line Deviation

To make a robot follow a straight line between two waypoints, the system calculates the robot's deviation from the line:

$$dev = \frac{|(y_2-y_1)x_0 - (x_2-x_1)y_0 + x_2y_1 - y_2x_1|}{\sqrt{(y_2-y_1)^2 + (x_2-x_1)^2}}$$

Where:
- $(x_1, y_1)$ and $(x_2, y_2)$ are the coordinates of the two waypoints
- $(x_0, y_0)$ is the current robot position

#### 2.3.2. PID Control

The system uses a PID controller to adjust the robot's direction based on deviation and target angle:

$$u(t) = K\_p \cdot e(t) + K\_i \int\_0^t e(\tau) d\tau + K\_d \frac{de(t)}{dt}$$

Where:
- $u(t)$ is the control output (rotation angle)
- $e(t)$ is the error (deviation from path or angle difference)
- $K\_p$, $K\_i$, $K\_d$ are the proportional, integral, and derivative coefficients

## 3. System Architecture

### 3.1. Robot Model

#### 3.1.1. Physical Structure

Each robot is simulated as a square block with 8 IR sensors arranged on its 4 sides:
- 4 IR Transmitters: one on each side
- 4 IR Receivers: one on each side, each receiver consisting of 3 sensors at different positions

![Robot physical structure and sensor positions](images/robot_structure.png)

#### 3.1.2. IR Transmitter

Each IR transmitter has the following parameters:
- Beam angle: the opening angle of the infrared beam
- Beam distance: the maximum distance the signal can travel
- Beam direction offset: the angle offset of the beam relative to the normal of the robot's side

#### 3.1.3. IR Receiver

Each IR receiver has the following parameters:
- Viewing angle: the opening angle within which the receiver can detect signals
- Maximum distance: the maximum distance at which signals can be received
- Sensitivity: the ability to detect weak signals

### 3.2. Path Manager

The Path Manager module allows:
- Defining waypoints for robots
- Calculating deviation from the path
- Controlling robot movement along the path
- Analyzing and evaluating movement results

![Path management interface](imagespath_management.png)

### 3.3. Simulation

The Simulation module manages:
- List of robots
- Conversion ratio between actual size and display size
- Updating robot states in each simulation cycle
- Processing signal transmission between robots

### 3.4. User Interface (UI)

#### 3.4.1. Main Window

Manages the entire interface, including menus and tabs.

#### 3.4.2. Simulation Canvas

Displays robots, IR signals, paths, and allows users to interact directly with objects.

#### 3.4.3. Robot Control Panel

Provides controls to:
- Add/remove robots
- Adjust sensor parameters
- Manage paths
- Start/stop simulation

![Robot control panel](images/robot_control_panel.png)

## 4. IR Signal Physics

### 4.1. Signal Strength Calculation

Signal strength is calculated based on:
- Distance between transmitter and receiver
- Angle between transmitter and receiver directions
- Presence of direct line of sight (LOS)
- Attenuation due to obstacles

The general formula:

$$S = S\_0 \cdot \left(1 - \frac{d}{d\_{max}}\right)^{0.6} \cdot \cos^n(\theta) \cdot \frac{R\_s}{40} \cdot LOS\_{factor}$$

Where:
- $S\_0$ is the signal strength at the source
- $d$ is the distance between transmitter and receiver
- $d\_{max}$ is the maximum transmission distance
- $\theta$ is the angle between transmitter and receiver directions
- $R\_s$ is the receiver sensitivity
- $LOS\_{factor}$ is the adjustment factor for direct line of sight

### 4.2. Obstacle Detection

The system uses a line-of-sight checking algorithm to determine if there are obstacles between the transmitter and receiver:

1. Identify the line connecting the transmitter and receiver
2. Check if this line intersects with any robot
3. If an obstacle is detected, apply an attenuation factor to the signal

![Obstacle detection illustration](images/obstacle_detection.png)

### 4.3. Distance Estimation from Signal Strength

Distance is estimated from signal strength using an inverse formula:

$$d = d\_{max} \cdot \left(1 - \left(\frac{S}{S\_0 \cdot \cos^n(\theta) \cdot \frac{R\_s}{40} \cdot LOS\_{factor}}\right)^{1/0.6}\right)$$

## 5. Key Algorithms

### 5.1. Relative Position Algorithm (RPA)

```
Function CalculateRelativePosition(emitter_robot_id):
    1. Collect all signals from robot with ID emitter_robot_id
    2. Sort signals by strength from high to low
    3. If no signals, return null
    4. If only 1 signal:
       a. Estimate distance based on signal strength
       b. Use receiver direction as relative direction
       c. Set low confidence (0.2)
    5. If 2 signals:
       a. Use simple formula based on 2 signals
       b. Set medium confidence (0.5)
    6. If 3 or more signals:
       a. Apply full triangulation formula
       b. Set high confidence based on ratio between weakest and strongest signal
    7. Return (angle, distance, confidence)
```

### 5.2. Path Following Algorithm

```
Function FollowPath(waypoints):
    1. Initialize current_waypoint = 0
    2. Loop until reaching the last waypoint:
       a. Get current and next waypoint
       b. Calculate target angle from current position to next waypoint
       c. Calculate deviation from straight line connecting the waypoints
       d. Apply PID control to adjust direction
       e. Move robot forward
       f. If close enough to next waypoint:
          i. Increment current_waypoint
          ii. If at last waypoint, terminate
```

### 5.3. Formation Following Algorithm

```
Function FollowLeader(leader_robot, desired_distance, desired_angle):
    1. Use RPA to determine relative position of leader_robot
    2. Calculate distance and angle errors from desired position
    3. Apply PID control to adjust direction and speed
    4. Move robot to achieve desired position
    5. If obstacle detected, perform obstacle avoidance
```

## 6. Analysis and Evaluation Tools

### 6.1. Path Analysis

After a robot completes path following, the system provides analysis tools:
- Actual path versus ideal path chart
- Speed and rotation angle over time chart
- Distance and angle error charts
- Time and accuracy analysis table for each waypoint

![Path analysis](images/path_analysis.png)

### 6.2. IR Signal Visualization

The system provides visual representation of IR signals:
- Beams emitted from transmitters
- Connection lines between transmitters and receivers when signals are detected
- Signal strength represented by color and thickness of connection lines

![IR signal visualization](images/ir_signals.png)

## 7. Installation and Usage Guide

### 7.1. System Requirements

- Python 3.6 or higher
- Libraries: tkinter, matplotlib, numpy, math

### 7.2. Installation

```bash
pip install -r requirements.txt
```

### 7.3. Running the Program

```bash
python main.py
```

### 7.4. Basic Usage Guide

1. Add robots to the simulation via the control panel
2. Adjust sensor parameters as desired
3. Draw paths by clicking on the canvas
4. Select lead robot and start movement
5. Analyze results after completion

![Usage guide](images/usage_guide.png)

## 8. Conclusion and Future Development

This project has successfully built a simulation environment for robots communicating via infrared, allowing research on relative positioning algorithms and movement control. The system can be further developed in the following directions:

1. Adding more complex signal transmission/reception models
2. Integrating AI algorithms for positioning and obstacle avoidance
3. Expanding to 3D simulation
4. Integrating with real robots through hardware interfaces

## 9. References

1. Rappaport, T. S. (2002). Wireless Communications: Principles and Practice.
2. Goldsmith, A. (2005). Wireless Communications.
3. IR Communication Principles and Applications, Texas Instruments.
4. Robot Localization and Navigation using IR Sensors, IEEE Robotics and Automation.


*Note: This document describes the IR robot communication simulation project, developed by [Student Name] under the supervision of [Supervisor Name], [University Name].*