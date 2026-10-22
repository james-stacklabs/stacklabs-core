import cv2
import threading
from flask import Flask, render_template_string, Response, jsonify, request
import os
import time

app = Flask(__name__)

# Initialize the webcam (Defaulting to the local Argus Streamer feed instead of /dev/video0)
camera_lock = threading.Lock()
camera = cv2.VideoCapture("http://127.0.0.1:8081/cam/0")
# Force 720p HD resolution for the capture
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

is_recording = False
out = None
output_dir = "/home/james/stacklabs/media_vault/01_Ingest/hailo_dropzone"
os.makedirs(output_dir, exist_ok=True)
current_output_file = ""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sovereign OS: Enterprise DVR Console</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0c10; color: #c5c6c7; text-align: center; margin-top: 20px; }
        h1 { color: #66fcf1; text-transform: uppercase; font-weight: 900; letter-spacing: 2px; }
        .subtitle { font-size: 14px; color: #45a29e; font-style: italic; margin-bottom: 20px; }
        .btn { padding: 15px 30px; font-size: 20px; font-weight: bold; cursor: pointer; border-radius: 6px; margin: 15px; border: none; transition: 0.3s; text-transform: uppercase; }
        .btn-record { background: #ff0033; color: white; box-shadow: 0 0 15px rgba(255, 0, 51, 0.4); }
        .btn-stop { background: #45a29e; color: #0b0c10; box-shadow: 0 0 15px rgba(69, 162, 158, 0.4); }
        .btn-record:hover { background: #cc0000; transform: scale(1.05); }
        .btn-stop:hover { background: #66fcf1; transform: scale(1.05); }
        #status { font-size: 20px; margin-top: 20px; font-weight: bold; }
        .feed-container { margin: 10px auto; border: 3px solid #1f2833; border-radius: 8px; width: 900px; max-width: 95%; overflow: hidden; box-shadow: 0 0 20px rgba(102, 252, 241, 0.1); background: #000; }
        img.feed { width: 100%; height: auto; display: block; }
    </style>
</head>
<body>
    <h1>Omega Gate: Live Edge DVR</h1>
    <div class="subtitle">ITSM Architecture Protocol // M.A.R.D. Engine Pre-Cog Feed</div>
    
    <div class="feed-container">
        <!-- Live feed from the webcam -->
        <img class="feed" src="/video_feed" alt="Live Camera Feed Loading... (If broken, camera is locked)">
    </div>

    <button class="btn btn-record" onclick="startRecording()">🔴 START CAPTURE</button>
    <button class="btn btn-stop" onclick="stopRecording()">⏹ STOP CAPTURE</button>
    
    <div id="status">State: IDLE (Monitoring Feed)</div>

    <script>
        function startRecording() {
            document.getElementById('status').innerText = "State: RECORDING (CMDB Sync Active)";
            document.getElementById('status').style.color = "#ff0033";
            fetch('/start');
        }
        function stopRecording() {
            document.getElementById('status').innerText = "State: FINALIZING ASSET...";
            document.getElementById('status').style.color = "#f2a900";
            fetch('/stop').then(r => r.json()).then(data => {
                document.getElementById('status').innerHTML = "State: ASSET SAVED to<br><span style='font-size: 14px; color: #fff;'>" + data.file + "</span>";
                document.getElementById('status').style.color = "#66fcf1";
            });
        }
    </script>
</body>
</html>
"""

def gen_frames():
    global is_recording, out, camera
    while True:
        with camera_lock:
            if camera is None or not camera.isOpened():
                success = False
            else:
                success, frame = camera.read()
                
        if not success:
            time.sleep(0.1)
            continue
        
        # If we are recording, write the exact frame to the MP4 file
        if is_recording and out is not None:
            out.write(frame)

        # Encode the frame to JPEG for the web stream
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    # Video streaming route
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start')
def start_recording():
    global is_recording, out, current_output_file
    if not is_recording:
        timestamp = int(time.time())
        current_output_file = f"{output_dir}/Sovereign_DVR_Capture_{timestamp}.mp4"
        # Use mp4v codec for MP4 files
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(current_output_file, fourcc, 30.0, (1280, 720))
        is_recording = True
    return jsonify({"status": "recording started"})

@app.route('/stop')
def stop_recording():
    global is_recording, out, current_output_file
    if is_recording:
        is_recording = False
        if out is not None:
            out.release()
            out = None
    return jsonify({"status": "recording stopped", "file": current_output_file})

@app.route('/set_node', methods=['POST'])
def set_node():
    global camera, is_recording
    if is_recording:
        return jsonify({"status": "error", "message": "Cannot switch node while recording"}), 400
    
    data = request.json
    ip = data.get('ip')
    
    with camera_lock:
        if camera is not None:
            camera.release()
            
        if ip == '0':
            camera = cv2.VideoCapture("http://127.0.0.1:8081/cam/0")
        else:
            camera = cv2.VideoCapture(f"http://{ip}:8081/cam/0")
            
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    return jsonify({"status": "success", "node": ip})

if __name__ == '__main__':
    # Kill any ffmpeg locks before starting
    os.system("pkill -f 'ffmpeg.*video0'")
    app.run(host='0.0.0.0', port=5051, threaded=True)
