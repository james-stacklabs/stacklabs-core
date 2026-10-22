import subprocess
from flask import Flask, Response

# principal architect: the sovereign ffmpeg-based MJPEG relay
# bypasses opencv-python dependencies for Pi Zero 2W mesh nodes
app = Flask(__name__)

def generate_frames():
    # -f v4l2 (input device) -> /dev/video0
    # -c:v mjpeg (codec) -> convert to mjpeg
    # -f mjpeg (format) -> stream of jpegs
    # -r 5 (frame rate) -> throttle to preserve pi zero 2w thermals
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-f', 'v4l2', '-i', '/dev/video0', 
        '-c:v', 'mjpeg', '-f', 'mjpeg', '-r', '5', '-'
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1024 * 10)
    
    try:
        buffer = b""
        while True:
            chunk = process.stdout.read(1024 * 4)
            if not chunk:
                break
            buffer += chunk
            
            # Locate JPEG frame boundaries (SOI=0xFFD8, EOI=0xFFD9)
            start = buffer.find(b'\xff\xd8')
            end = buffer.find(b'\xff\xd9', start)
            
            if start != -1 and end != -1:
                # Extract frame and clear buffer
                frame = buffer[start:end+2]
                buffer = buffer[end+2:]
                
                # Yield multipart HTTP payload
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
            elif len(buffer) > 1024 * 500: # Safety flush
                buffer = b""
    except Exception as e:
        print(f"[!] STREAM ERROR: {e}")
    finally:
        process.terminate()

@app.route('/')
def video_feed():
    # Push the unadulterated byte stream directly into the Sovereign OS
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("[+] ARGUS NODE MANDO ONLINE: Streaming /dev/video0 via FFmpeg on Port 8081...")
    # Threaded=True allows multiple local/remote viewers to grab the feed
    app.run(host='0.0.0.0', port=8081, threaded=True, debug=False)
