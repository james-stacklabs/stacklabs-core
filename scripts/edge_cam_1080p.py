import subprocess
import socketserver
import http.server
import threading
import glob
import time

global_frame = None
lock = threading.Lock()

def find_video_device():
    print("Scanning for active video devices...")
    for dev in sorted(glob.glob('/dev/video*')):
        try:
            proc = subprocess.run(['v4l2-ctl', '--device', dev, '--set-fmt-video=width=1920,height=1080,pixelformat=MJPG', '--stream-mmap', '--stream-to=-', '--stream-count=1'], capture_output=True, timeout=2)
            if proc.returncode == 0 and len(proc.stdout) > 100:
                print(f"Found active camera on {dev}")
                return dev
        except Exception:
            continue
    return None

def capture_thread(dev):
    global global_frame
    print(f"Starting continuous capture on {dev}...")
    while True:
        proc = subprocess.Popen(['v4l2-ctl', '--device', dev, '--set-fmt-video=width=1920,height=1080,pixelformat=MJPG', '--stream-mmap', '--stream-to=-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        buffer = b''
        while True:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break
            buffer += chunk
            start = buffer.find(b'\xff\xd8')
            if start != -1:
                end = buffer.find(b'\xff\xd9', start)
                if end != -1:
                    frame = buffer[start:end+2]
                    with lock:
                        global_frame = frame
                    buffer = buffer[end+2:]
                else:
                    buffer = buffer[start:]
            else:
                buffer = b''
        print("Capture process died, restarting...")
        time.sleep(1)

class CamHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/cam/0':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while True:
                with lock:
                    frame = global_frame
                if frame:
                    try:
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                        time.sleep(0.05) # ~20 FPS limit
                    except Exception:
                        break
                else:
                    time.sleep(0.1)
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Edge Cam Active</h1><a href='/cam/0'>View Stream</a></body></html>")

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    dev = find_video_device()
    if not dev:
        print("No active camera found. Exiting.")
    else:
        t = threading.Thread(target=capture_thread, args=(dev,), daemon=True)
        t.start()
        
        try:
            server = ThreadingHTTPServer(('0.0.0.0', 8081), CamHandler)
            print("Starting edge camera server on port 8081...")
            server.serve_forever()
        except Exception as e:
            print(f"Error: {e}")
