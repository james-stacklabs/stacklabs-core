import os
import cv2
import time
import json
import base64
import asyncio
import websockets
from dotenv import load_dotenv

# Load credentials
load_dotenv('/home/james/stacklabs/.env')

tapo_user = os.getenv('TAPO_C120_USER')
tapo_pass = os.getenv('TAPO_C120_PASS')
tapo_ip = os.getenv('TAPO_C120_IP', '192.168.1.191')

if not tapo_user or not tapo_pass:
    print("Error: Tapo credentials not found in .env")
    exit(1)

# Tapo RTSP stream
rtsp_url = f"rtsp://{tapo_user}:{tapo_pass}@{tapo_ip}:554/stream1"
SAM_TRACKER_WS = "ws://127.0.0.1:3004/sam/ws"

async def ingest_stream():
    print(f"[{time.strftime('%H:%M:%S')}] Connecting to Tapo C120 at {tapo_ip}...")
    cap = cv2.VideoCapture(rtsp_url)
    
    # We want to pull frames, but we don't want to process 30FPS for motion detection if it's too heavy.
    # Setting buffer size helps prevent lag buildup on RTSP streams.
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    
    if not cap.isOpened():
        print("[ERROR] Could not open RTSP stream.")
        return

    print(f"[{time.strftime('%H:%M:%S')}] Stream connected. Connecting to SamTracker Backend...")
    
    try:
        async with websockets.connect(SAM_TRACKER_WS) as websocket:
            print(f"[{time.strftime('%H:%M:%S')}] Connected to SamTracker! Starting visual pipeline...")
            
            last_alert_time = 0
            alert_cooldown = 30 # Seconds between alerts
            
            # Baseline for motion detection (fallback until Hailo AI Hat YOLO is fully trained)
            ret, prev_frame = cap.read()
            if not ret:
                return
            prev_gray = cv2.cvtColor(cv2.resize(prev_frame, (640, 360)), cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[WARNING] Frame dropped. Reconnecting...")
                    cap.release()
                    await asyncio.sleep(2)
                    cap = cv2.VideoCapture(rtsp_url)
                    continue
                
                # --- [HAILO AI HAT INTEGRATION POINT] ---
                # This is where we will eventually pipe the `frame` into the Hailo YOLO model.
                # Example: detections = hailo_infer(frame)
                # if "cat" in detections: ...
                # ----------------------------------------
                
                # For now, we use a simple OpenCV motion threshold to trigger the pipeline
                gray = cv2.cvtColor(cv2.resize(frame, (640, 360)), cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                
                diff = cv2.absdiff(prev_gray, gray)
                thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                
                # Count non-zero pixels as a motion score
                motion_score = cv2.countNonZero(thresh)
                
                if motion_score > 5000: # Significant motion threshold
                    current_time = time.time()
                    if current_time - last_alert_time > alert_cooldown:
                        print(f"[{time.strftime('%H:%M:%S')}] Movement detected! (Score: {motion_score})")
                        
                        # Compress image for WebSocket payload
                        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                        b64_img = base64.b64encode(buffer).decode('utf-8')
                        
                        # Send telemetry to SamTracker
                        payload = {
                            "type": "CMD_LOG",
                            "message": "Argo Node detected movement on the Tapo C120.",
                            "image_base64": f"data:image/jpeg;base64,{b64_img}"
                        }
                        
                        await websocket.send(json.dumps(payload))
                        print("  -> Telemetry payload fired to SamTracker!")
                        
                        last_alert_time = current_time
                        
                prev_gray = gray
                
                # Yield to the event loop so we don't block
                await asyncio.sleep(0.01)

    except Exception as e:
        print(f"[ERROR] Ingestion pipeline crashed: {e}")
    finally:
        cap.release()

if __name__ == "__main__":
    asyncio.run(ingest_stream())
