import subprocess
import time
import socketserver
import http.server

class CamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/cam/0', '/'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while True:
                try:
                    proc = subprocess.run(['v4l2-ctl', '--device', '/dev/video0', '--stream-mmap', '--stream-to=-', '--stream-count=1'], capture_output=True)
                    if proc.stdout:
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + proc.stdout + b'\r\n')
                    else:
                        break
                except Exception:
                    break
        else:
            self.send_error(404)

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

if __name__ == '__main__':
    try:
        server = ThreadingHTTPServer(('0.0.0.0', 8081), CamHandler)
        print("Starting camera server on port 8081...")
        server.serve_forever()
    except Exception as e:
        print(f"Error: {e}")
