#!/usr/bin/python3
import cv2
import numpy as np
import math
from pymavlink import mavutil

# Initialize V4L2 Loopback output (720p @ 30 FPS)
cap_out = cv2.VideoWriter('/dev/video10', cv2.VideoWriter_fourcc(*'RAW '), 30, (1280, 720))

# Listen for MAVProxy telemetry on localhost UDP port 14551
connection = mavutil.mavlink_connection('udp:127.0.0.1:14551')
connection.wait_heartbeat()

print("Mavlink Connected")

# Telemetry state variables
roll, pitch = 0.0, 0.0
altitude, airspeed, battery = 0.0, 0.0, 0

def draw_horizon(frame, roll_rad, pitch_deg):
    """Draws a graphical artificial horizon centered on the frame."""
    cx, cy = 640, 360  # Center of 1280x720 frame
    radius = 120       # Size of the horizon circle
    
    # Calculate pitch offset in pixels (scaling factor: 3 pixels per degree)
    pitch_offset = int(pitch_deg * 3)
    
    # Calculate endpoints for the moving horizon line based on roll and pitch
    sin_roll = math.sin(roll_rad)
    cos_roll = math.cos(roll_rad)
    
    # Calculate local center of the tilted pitch line
    line_cx = cx + pitch_offset * sin_roll
    line_cy = cy + pitch_offset * cos_roll
    
    # Generate line bounding coordinates
    dx = 100 * cos_roll
    dy = -100 * sin_roll
    
    p1 = (int(line_cx - dx), int(line_cy - dy))
    p2 = (int(line_cx + dx), int(line_cy + dy))
# Create a clean isolation mask for the horizon display circular boundary
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radius, 255, -1)
    
    # Draw horizon components on a temporary overlay layer
    horizon_layer = np.zeros_like(frame)
    cv2.line(horizon_layer, p1, p2, (0, 255, 0), 2)  # Pitch/Roll moving line
    
    # Draw static aircraft reference crosshair in the absolute center
    cv2.line(horizon_layer, (cx - 20, cy), (cx - 5, cy), (0, 0, 255), 2)
    cv2.line(horizon_layer, (cx + 5, cy), (cx + 20, cy), (0, 0, 255), 2)
    cv2.circle(horizon_layer, (cx, cy), 2, (0, 0, 255), -1)
    
    # Mask out any line data drawn outside the primary horizon dial bounding circle
    cv2.circle(horizon_layer, (cx, cy), radius, (255, 255, 255), 1)
    
    # Apply mask and merge to main canvas
    masked_horizon = cv2.bitwise_and(horizon_layer, horizon_layer, mask=mask)
    return cv2.add(frame, masked_horizon)

while True:
    # Fetch MAVLink messages without blocking completely
    msg = connection.recv_match(type=['ATTITUDE', 'VFR_HUD', 'SYS_STATUS'], blocking=False)
    if msg:
        msg_type = msg.get_type()
        if msg_type == 'ATTITUDE':
            roll = msg.roll        # In Radians
            pitch = math.degrees(msg.pitch) # Convert to Degrees
        elif msg_type == 'VFR_HUD':
            altitude = msg.alt
            airspeed = msg.airspeed
        elif msg_type == 'SYS_STATUS':
            battery = msg.battery_remaining

    # Create a blank black frame frame
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # Render the dynamic artificial horizon graphic layer
    frame = draw_horizon(frame, roll, pitch)

    # Draw Text HUD Elements
    cv2.putText(frame, f"ALT: {altitude:.1f}m", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"SPD: {airspeed:.1f}m/s", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f"BAT: {battery}%", (1080, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Push structured frame to virtual loopback node /dev/video10
    cap_out.write(frame)

