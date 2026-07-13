import cv2
import numpy as np
import time
import threading
from pymavlink import mavutil

# Global dictionary for thread-safe telemetry data
telemetry_data = {
    'fps': 0,
    'altitude': 0.0,
    'roll': 0.0,
    'pitch': 0.0,
    'speed': 0.0,
    'armed': False,
    'battery_percent': -1
}
data_lock = threading.Lock()

def mavlink_receiver_thread(connection_string):
    """Background thread to ingest MAVLink packets from MAVProxy."""
    global telemetry_data
    mav_connection = mavutil.mavlink_connection(connection_string)
    mav_connection.wait_heartbeat()
    print ("Mavlink connected")

    while True:
        try:
            msg = mav_connection.recv_match(blocking=True, timeout=0.1)
            if msg is None:
                continue

            msg_type = msg.get_type()
            with data_lock:
                if msg_type == 'SYS_STATUS':
                    telemetry_data['battery_percent'] = msg.battery_remaining
                elif msg_type == 'BATTERY_STATUS':
                    telemetry_data['battery_percent'] = msg.battery_remaining
                elif msg_type == 'ATTITUDE':
                    telemetry_data['roll'] = np.degrees(msg.roll)
                    telemetry_data['pitch'] = np.degrees(msg.pitch)
                elif msg_type == 'GLOBAL_POSITION_INT':
                    telemetry_data['altitude'] = msg.relative_alt / 1000.0
                elif msg_type == 'VFR_HUD':
                    telemetry_data['speed'] = msg.groundspeed
                elif msg_type == 'HEARTBEAT':
                    is_armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                    telemetry_data['armed'] = bool(is_armed)
        except Exception:
            time.sleep(1)

def draw_hud(frame, telemetry):
    """Draws the graphical HUD overlay onto the raw video frame."""
    h, w, _ = frame.shape
    cx, cy = w // 2, h // 2
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    hud_color = (0, 255, 255) if telemetry['armed'] else (0, 255, 0)
    
    # Central Reticle & Horizon
    cv2.drawMarker(frame, (cx, cy), hud_color, cv2.MARKER_CROSS, 20, 2)
    roll, pitch = telemetry['roll'], telemetry['pitch']
    pitch_offset = int(pitch * 5)
    
    horizon_layer = np.zeros_like(frame)
    cv2.line(horizon_layer, (cx - 100, cy + pitch_offset), (cx - 30, cy + pitch_offset), hud_color, 2)
    cv2.line(horizon_layer, (cx + 30, cy + pitch_offset), (cx + 100, cy + pitch_offset), hud_color, 2)
    
    rot_mat = cv2.getRotationMatrix2D((cx, cy), roll, 1.0)
    rotated_horizon = cv2.warpAffine(horizon_layer, rot_mat, (w, h))
    frame = cv2.addWeighted(frame, 1.0, rotated_horizon, 1.0, 0)
    
    # Battery Gauge UI
    bat = telemetry['battery_percent']
    if bat != -1:
        bat_color = (0, 255, 0) if bat > 50 else ((0, 165, 255) if bat > 25 else (0, 0, 255))
        cv2.rectangle(frame, (w - 150, 25), (w - 50, 45), bat_color, 2)
        cv2.rectangle(frame, (w - 50, 30), (w - 46, 40), bat_color, cv2.FILLED)
        fill_width = int((bat / 100.0) * 96)
        cv2.rectangle(frame, (w - 148, 27), (w - 148 + fill_width, 43), bat_color, cv2.FILLED)
        cv2.putText(frame, f"BAT: {bat}%", (w - 150, 65), font, 0.5, bat_color, 2)

    # Telemetry Text
    cv2.putText(frame, f"FPS: {telemetry['fps']}", (20, 40), font, 0.6, hud_color, 2)
    cv2.putText(frame, f"ALT: {telemetry['altitude']:.1f}m", (20, 70), font, 0.6, hud_color, 2)
    cv2.putText(frame, f"SPD: {telemetry['speed']:.1f}m/s", (20, 100), font, 0.6, hud_color, 2)
    
    return frame
import subprocess
import cv2
import numpy as np
import time
import threading


def main():
    MAVLINK_UDP = 'udpin:127.0.0.1:14551'
    LISTEN_PORT = '9000'
    
    mav_thread = threading.Thread(target=mavlink_receiver_thread, args=(MAVLINK_UDP,), daemon=True)
    mav_thread.start()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
         print("Error: Could not open camera device.")
         return

    # Construct standard system pipeline command
    gst_command = [
        'gst-launch-1.0', 
        'fdsrc', '!', 'video/x-raw,format=BGR,width=640,height=480,framerate=30/1', '!',
        'videoconvert', '!', 'video/x-raw,format=I420', '!',
        'x264enc', 'speed-preset=ultrafast', 'tune=zerolatency', 'bitrate=1500', 'key-int-max=30', '!',
        'mpegtsmux', '!',
        f'srtsink', f'uri=srt://:{LISTEN_PORT}?mode=listener', 'wait-for-connection=false'
    ]

    print(f"gst pipeline: {gst_command}")

    # Open a fast pipeline pipe straight to the system terminal environment
    pipe = subprocess.Popen(gst_command, stdin=subprocess.PIPE, bufsize=0)
    print(f"SRT Server Live via Subprocess! Listening on port {LISTEN_PORT}...")

    fps_start = time.time()
    frames_processed = 0
    current_fps = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frames_processed += 1
            if (time.time() - fps_start) >= 1.0:
                current_fps = frames_processed
                frames_processed = 0
                fps_start = time.time()
                
            with data_lock:
                local_telemetry = telemetry_data.copy()
            
            local_telemetry['fps'] = current_fps
            final_output = draw_hud(frame, local_telemetry)
            
            # Write raw array bytes directly down the system pipe execution line
            try:
                pipe.stdin.write(final_output.tobytes())
            except IOError:
                # Catch pipe breaks gracefully if GStreamer exits early
                print("GStreamer pipeline disconnected.")
                break
                
    finally:
        cap.release()
        pipe.stdin.close()
        pipe.wait()
        print("Stream ended.")

if __name__ == '__main__':
    main()

