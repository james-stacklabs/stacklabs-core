import cv2
import glob
import threading
from flask import Flask, Response

app = Flask(__name__)
active_cameras = {}
latest_frames = {}
locks = {}

def camera_reader(cam_id, cap):
    """Background thread to read frames continuously and avoid Flask blocking."""
    while True:
        success, frame = cap.read()
        if success:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            with locks[cam_id]:
                latest_frames[cam_id] = buffer.tobytes()

def init_cameras():
    print("[*] Initiating Sovereign OS Plug and Play Enumeration...")
    device_paths = glob.glob('/dev/video*')
    
    for dev in sorted(device_paths):
        try:
            cam_id = int(dev.replace('/dev/video', ''))
            # Linux assigns odd numbers (video1) to metadata, sticking to checking all and verifying frames
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    active_cameras[cam_id] = cap
                    locks[cam_id] = threading.Lock()
                    
                    # Start background reader thread
                    t = threading.Thread(target=camera_reader, args=(cam_id, cap), daemon=True)
                    t.start()
                    
                    print(f"[+] Plug and Play Engine detected physical hardware on: {dev}")
                    print(f"    -> Streaming Route active at: /cam/{cam_id}")
                else:
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            pass

def generate_frames(cam_id):
    """Yield the most recent frame aggressively to any connected client."""
    while True:
        with locks.get(cam_id, threading.Lock()):
            frame = latest_frames.get(cam_id, None)
            
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/cam/<int:cam_id>')
def video_feed(cam_id):
    if cam_id in active_cameras:
        return Response(generate_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera Offline or Unplugged", 404

@app.route('/')
def index():
    html = "<h3>Sovereign Argus Node : Active Optic Arrays</h3><ul>"
    for cid in active_cameras.keys():
        html += f'<li><a href="/cam/{cid}">/dev/video{cid} : STREAMING</a></li>'
    html += "</ul>"
    return html

if __name__ == '__main__':
    init_cameras()
    if not active_cameras:
        print("[!] ARGUS FATAL: No visual hardware detected.")
    app.run(host='0.0.0.0', port=8081, threaded=True)
