import cv2
import time
import os
from datetime import datetime

# Local Argus/Nest RTSP stream (internal LAN IP)
RTSP_URL = "rtsp://192.168.1.55/live"  # Local Arlo/Nest stream bypass

# Setup output evidence
OUTPUT_DIR = "/home/james/stacklabs/dna/media/forensics/SDLC-0040"
os.makedirs(OUTPUT_DIR, exist_ok=True)
output_path = os.path.join(OUTPUT_DIR, f"Exhibit_D_STL_DET_{int(time.time())}.mp4")

def capture_bridge():
    print(f"Initializing Local Cam Bridge to {RTSP_URL}...")
    cap = cv2.VideoCapture(RTSP_URL)
    
    if not cap.isOpened():
        print("ERROR: Could not bind to local RTSP stream. Verify Arlo Base Station routing.")
        # Fallback to local webcam for demo/testing if RTSP fails
        cap = cv2.VideoCapture(0)

    # 30 fps
    fps = 30.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Recording Cockpit Evidence to: {output_path} at 30 FPS.")
    print("Burning in Node .73 system clock. Press Ctrl+C to stop.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Stream dropped. Attempting to reconnect...")
                time.sleep(1)
                continue

            # Burn Node .73 epoch/timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(frame, f"[NODE .73 MESH TRUTH] {current_time}", 
                        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0, 0, 255), 2, cv2.LINE_AA)

            out.write(frame)
            
            # Optional preview if running in X11
            # cv2.imshow('Node .73 Zero-Trust Cockpit', frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

    except KeyboardInterrupt:
        print("\nShutdown signal received.")
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print(f"Exhibit D saved to {output_path}")

if __name__ == "__main__":
    capture_bridge()
