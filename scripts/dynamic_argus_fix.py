import cv2
import glob
import threading
from flask import Flask, Response

app = Flask(__name__)
active_cameras = {}
latest_frames = {}
locks = {}

def camera_reader(cam_id, cap, rtsp_url=None):
    """Background thread to read frames continuously and avoid Flask blocking."""
    global active_cameras
    import time
    while True:
        try:
            success, frame = cap.read()
            if success:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                with locks[cam_id]:
                    latest_frames[cam_id] = buffer.tobytes()
                time.sleep(0.03)  # limit frame rate to ~30 fps to resolve memory and CPU watchdog inhibitors
            else:
                if rtsp_url:
                    print(f"[!] RTSP read failed for {rtsp_url}. Reconnecting in 5 seconds...")
                    cap.release()
                    time.sleep(5)
                    cap = cv2.VideoCapture(rtsp_url)
                    active_cameras[cam_id] = cap
                else:
                    time.sleep(1)
        except Exception as e:
            print(f"[ERROR] camera_reader encountered an error: {e}")
            import time
            time.sleep(2)

def init_cameras():
    print("[*] Initiating Sovereign OS Plug and Play Enumeration...")
    import os
    os.system("sudo chmod 666 /dev/video* 2>/dev/null")
    device_paths = glob.glob('/dev/video[0-9]')
    
    # Try physical cameras first
    for dev in sorted(device_paths):
        try:
            cam_id = int(dev.replace('/dev/video', ''))
            print(f"[*] Testing physical camera {dev}...")
            cap = cv2.VideoCapture(cam_id, cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    active_cameras[0] = cap
                    locks[0] = threading.Lock()
                    
                    t = threading.Thread(target=camera_reader, args=(0, cap), daemon=True)
                    t.start()
                    
                    print(f"[+] Plug and Play Engine detected physical hardware on: {dev}")
                    print(f"    -> Streaming Route active at: /cam/0")
                    return
                else:
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            print(f"[-] Physical camera test failed on {dev}: {e}")

    # Fallback to Tapo C120 RTSP stream
    print("[*] No physical USB cameras detected. Attempting Tapo C120 RTSP stream fallback...")
    try:
        from dotenv import load_dotenv
        load_dotenv('/home/james/stacklabs/.env')
        tapo_user = os.getenv('TAPO_C120_USER')
        tapo_pass = os.getenv('TAPO_C120_PASS')
        tapo_ip = os.getenv('TAPO_C120_IP', '192.168.1.191')
        if tapo_user and tapo_pass:
            rtsp_url = f"rtsp://{tapo_user}:{tapo_pass}@{tapo_ip}:554/stream1"
            print(f"[*] Connecting to Tapo RTSP: rtsp://{tapo_user}:***@{tapo_ip}:554/stream1")
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    active_cameras[0] = cap
                    locks[0] = threading.Lock()
                    
                    t = threading.Thread(target=camera_reader, args=(0, cap, rtsp_url), daemon=True)
                    t.start()
                    
                    print(f"[+] Tapo C120 RTSP stream fallback active on /cam/0!")
                    return
                else:
                    print("[-] Tapo stream opened but failed to read initial frame.")
                    cap.release()
            else:
                print("[-] Tapo stream failed to open.")
                cap.release()
    except Exception as e:
        print(f"[-] Tapo C120 fallback failed with exception: {e}")

def generate_frames(cam_id):
    """Yield the most recent frame aggressively to any connected client."""
    import time
    while True:
        with locks.get(cam_id, threading.Lock()):
            frame = latest_frames.get(cam_id, None)
            
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.033)  # limit yield rate to ~30 fps to reduce CPU and network buffer bloat

@app.route('/cam/<int:cam_id>')
def video_feed(cam_id):
    if cam_id in active_cameras:
        return Response(generate_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera Offline or Unplugged", 404

@app.route('/cam/tapo_couch')
def tapo_couch_feed():
    if 0 in active_cameras:
        return Response(generate_frames(0), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif active_cameras:
        first_cam = list(active_cameras.keys())[0]
        return Response(generate_frames(first_cam), mimetype='multipart/x-mixed-replace; boundary=frame')
    return "Camera Offline or Unplugged", 404

@app.route('/')
def index():
    html = "<h3>Sovereign Argus Node : Active Optic Arrays</h3><ul>"
    for cid in active_cameras.keys():
        html += f'<li><a href="/cam/{cid}">/dev/video{cid} : STREAMING</a></li>'
    html += '<li><a href="/cam/tapo_couch">Tapo C120 Couch Cam Feed</a></li>'
    html += "</ul>"
    return html

if __name__ == '__main__':
    init_cameras()
    if not active_cameras:
        print("[!] ARGUS FATAL: No visual hardware detected.")
    app.run(host='0.0.0.0', port=8081, threaded=True)
