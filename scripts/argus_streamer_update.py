import cv2
from flask import Flask, Response
import time
import sys

# ultra-lean MJPEG streamer for Argus Node (Pi Zero 2W)
app = Flask(__name__)

# Try multiple indices and forcefully bypass GStreamer by using raw V4L2 backend
camera = None
active_index = -1
for idx in [0, 2, 1, 4]:
    print(f"[*] Scanning /dev/video{idx} via V4L2...")
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if cap.isOpened():
        success, _ = cap.read()
        if success:
            camera = cap
            active_index = idx
            print(f"[+] HARDWARE LOCK: Successfully engaged /dev/video{idx}")
            break
        else:
            cap.release()

if camera is None or not camera.isOpened():
    print(f"[!] ENGINES DEAD: Could not establish a pure V4L2 video stream.")
    sys.exit(1)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue
        
        # JPEG compression (80% quality balances bandwidth and YOLOv8 accuracy)
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        
        # Yield the multipart frame payload to the HTTP stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
@app.route('/cam/0')
def video_feed():
    # Push the unadulterated byte stream directly into the Sovereign OS
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("[+] ARGUS NODE ONLINE: Streaming /dev/video0 on Port 8081...")
    # Threaded=True is critical so multiple viewers (you + YOLO model) can grab frames simultaneously
    app.run(host='0.0.0.0', port=8081, threaded=True)
