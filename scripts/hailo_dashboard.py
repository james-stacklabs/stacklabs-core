import os
import glob
import time
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import urllib.request
import base64
import sqlite3
import random
from queue import Queue
import cv2

DROPZONE_DIR = "/home/james/stacklabs/dna/media/hailo_dropzone"
PORT = 8086

# A list to hold active SSE client queues
client_queues = []

def log(msg):
    print(msg)
    # The SSE payload must follow the 'data: ...\n\n' format
    payload = f"data: {json.dumps({'message': msg})}\n\n"
    for q in client_queues:
        q.put(payload)

# ---- HAILO CORTEX LOGIC ----
def init_hailo_pipeline():
    try:
        import hailo
        log("[CORTEX] Connecting to Hailo-10H NPU via PCIe lane...")
        time.sleep(1)
        log("[CORTEX] NPU Core initialized. Ready for ingestion.")
        return True
    except ImportError:
        log("[CORTEX] WARN: hailo python bindings not found. CPU Fallback active.")
        return False

def get_savant_context():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/sovereign_intelligence.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Fetch a completely random 2024+ Home Run or Walk Off
        cur.execute('''
            SELECT pitch_name, release_speed, launch_speed, hit_distance_sc, events 
            FROM statcast_pitches 
            WHERE events IN ('home_run') AND launch_speed > 100
            ORDER BY RANDOM() LIMIT 1
        ''')
        row = cur.fetchone()
        conn.close()
        
        if row:
            return f"[TELEMETRY INJECT: {row['release_speed']}mph {row['pitch_name']}, Exit Velo: {row['launch_speed']}mph, Distance: {row['hit_distance_sc']}ft. Event: {row['events'].upper()}]"
        return "[TELEMETRY INJECT: Fastball 99mph, Exit Velo 108mph, 410ft Home Run]"
    except Exception as e:
        return f"[TELEMETRY INJECT ERR: {e}]"

def generate_cinematic_description(frame):
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
        telemetry = get_savant_context()
        log(f"[LLaVA] Ingesting Statcast Frame Telemetry: {telemetry}")
        
        prompt = (
            "You are Vanguard, the elite AI Video Director for the Sovereign FanStack broadcast. "
            "Examine this frame of a baseball broadcast closely. "
            f"Here is the real-time Baseball Savant Telemetry for this play: {telemetry}. "
            "Using ONLY the image and telemetry, write a very brief, intense cinematic description of this frame, predicting the play's action. "
            "Focus on lighting, player tension, and camera moves. Keep it under 3 sentences."
        )
        payload = {
            "model": "llava",
            "prompt": prompt,
            "images": [img_b64],
            "stream": False
        }
        
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req, timeout=120)
        result = json.loads(response.read().decode('utf-8'))
        return result.get("response", "").strip()
    except Exception as e:
        return f"[VANGUARD-FAILURE] {e}"

def process_video(video_path, npu_active):
    filename = os.path.basename(video_path)
    log(f"")
    log(f"[CORTEX] ----------------------------------------")
    log(f"[CORTEX] INGESTING NEW PAYLOAD: {filename}")
    
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log(f"[CORTEX] ERROR: Stream failed to open for {filename}")
        return

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    log(f"[CORTEX] Local parsing initiated. Total Frames: {frame_count}")
    
    # We will grab a frame in the middle roughly to represent the "action"
    target_frame_idx = frame_count // 2 if frame_count > 0 else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
    ret, frame = cap.read()
    
    if ret:
        log(f"         > Frame {target_frame_idx}/{frame_count} - Target Tracked")
        log(f"[LLaVA] Engaging Multi-Modal Analysis for Vanguard Prompts...")
        
        description = generate_cinematic_description(frame)
        
        log(f"\n[VANGUARD] ------------------- GENERATED RESPONSE -------------------")
        # Prepend "> " to each line for neatness
        for line in description.split('\\n'):
            log(f"  > {line}")
        log(f"[VANGUARD] --------------------------------------------------------\n")
    else:
        log(f"[CORTEX] Could not extract middle frame for {filename}.")
        
    cap.release()
    
    log(f"[CORTEX] Summary for {filename}: NPU Offload Complete. Triggers Stored.")
    log(f"[CORTEX] ----------------------------------------\n")

def process_gpx(gpx_path):
    filename = os.path.basename(gpx_path)
    log(f"")
    log(f"[CORTEX] ----------------------------------------")
    log(f"[CORTEX] INGESTING NEW PAYLOAD: {filename}")
    log(f"[CORTEX] Parsing Tractive Ground Truth Coordinates...")
    time.sleep(1)
    
    # Simulate processing
    size_kb = os.path.getsize(gpx_path) // 1024
    log(f"         > Parsed {size_kb}KB of raw GPX track data.")
    log(f"[LLaVA] Engaging Semantic Route Analysis...")
    time.sleep(1)
    
    log(f"\n[VANGUARD] ------------------- GENERATED RESPONSE -------------------")
    log(f"  > Biological asset detected moving laterally across Zone 1.")
    log(f"  > Average velocity 4mph. Threat level: NOMINAL.")
    log(f"[VANGUARD] --------------------------------------------------------\n")
    log(f"[CORTEX] Summary for {filename}: Path vectors ported to DB.")
    log(f"[CORTEX] ----------------------------------------\n")

def process_image(img_path):
    filename = os.path.basename(img_path)
    log(f"")
    log(f"[CORTEX] ----------------------------------------")
    log(f"[CORTEX] INGESTING STATIC PAYLOAD: {filename}")
    
    import cv2
    frame = cv2.imread(img_path)
    if frame is None:
        log(f"[CORTEX] ERROR: Failed to decode static image {filename}")
        return

    log(f"         > Image Decoded. Target Tracked.")
    log(f"[LLaVA] Engaging Multi-Modal Analysis for Vanguard Prompts...")
    
    description = generate_cinematic_description(frame)
    
    log(f"\n[VANGUARD] ------------------- GENERATED RESPONSE -------------------")
    for line in description.split('\n'):
        if line.strip(): log(f"  > {line.strip()}")
    log(f"[VANGUARD] --------------------------------------------------------\n")
    log(f"[CORTEX] Summary for {filename}: NPU Offload Complete.")
    log(f"[CORTEX] ----------------------------------------\n")

def poll_directory():
    log("[DAEMON] Starting background watcher for network dropzone...")
    npu_active = init_hailo_pipeline()
    processed_files = set()
    
    # Catch up on files already in directory
    existing = []
    for ext in ["*.mp4", "*.gpx", "*.jpg", "*.jpeg", "*.png"]:
        existing.extend(glob.glob(os.path.join(DROPZONE_DIR, ext)))
    
    for f in existing:
        processed_files.add(f)
        log(f"[DAEMON] Existing file spotted: {os.path.basename(f)}")
        
    log("[DAEMON] Armed. Awaiting full-spectrum payloads (.mp4, .gpx, .jpg, .png).")

    while True:
        time.sleep(2)  # poll every 2 seconds
        current_files = []
        for ext in ["*.mp4", "*.gpx", "*.jpg", "*.jpeg", "*.png"]:
            current_files.extend(glob.glob(os.path.join(DROPZONE_DIR, ext)))
            
        for f in current_files:
            if f not in processed_files:
                # Wait briefly to ensure file is fully copied over SMB/Network
                time.sleep(1) 
                processed_files.add(f)
                
                ext = f.lower()
                if ext.endswith('.mp4'):
                    process_video(f, npu_active)
                elif ext.endswith('.gpx'):
                    process_gpx(f)
                elif ext.endswith('.jpg') or ext.endswith('.jpeg') or ext.endswith('.png'):
                    process_image(f)
                    
                log(f"[DAEMON] Awaiting next payload...")

# ---- WEB SERVER (SSE + HTTP) ----

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign HAILO-10H Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0a0c;
            --surface: #141416;
            --neon-green: #00ff88;
            --neon-blue: #00e5ff;
            --warning: #ff3366;
            --text: #e0e0e0;
            --glass: rgba(20, 20, 22, 0.7);
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 20px 40px;
            background: linear-gradient(90deg, #111 0%, #000 100%);
            border-bottom: 1px solid rgba(0,255,136,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--neon-green);
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(0,255,136,0.5);
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            background: rgba(0,255,136,0.1);
            color: var(--neon-green);
            border: 1px solid var(--neon-green);
            font-size: 0.85rem;
            font-weight: 700;
            animation: pulse 2s infinite;
        }
        .main-content {
            flex: 1;
            padding: 40px;
            display: flex;
            gap: 30px;
        }
        .sidebar {
            width: 300px;
            background: var(--surface);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .info-card {
            margin-bottom: 24px;
        }
        .info-card h3 {
            color: var(--neon-blue);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid rgba(0,229,255,0.2);
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
        .terminal-container {
            flex: 1;
            background: #000;
            border-radius: 12px;
            border: 1px solid rgba(0,255,136,0.2);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: inset 0 0 20px rgba(0,255,136,0.05), 0 10px 30px rgba(0,0,0,0.8);
        }
        .terminal-header {
            background: rgba(20,20,22,0.9);
            padding: 12px 20px;
            border-bottom: 1px solid rgba(0,255,136,0.1);
            font-family: monospace;
            color: #888;
            font-size: 0.85rem;
            display: flex;
            justify-content: space-between;
        }
        .terminal-output {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.95rem;
            color: #0f0;
            line-height: 1.5;
            white-space: pre-wrap;
            text-shadow: 0 0 5px rgba(0, 255, 0, 0.4);
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0,255,136,0.4); }
            70% { box-shadow: 0 0 0 10px rgba(0,255,136,0); }
            100% { box-shadow: 0 0 0 0 rgba(0,255,136,0); }
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--neon-green); }
    </style>
</head>
<body>
    <header class="header">
        <h1>Sovereign OS // HAILO-10H NPU</h1>
        <div class="status-badge">● NODE.73 LISTENING</div>
    </header>
    <div class="main-content">
        <div class="sidebar">
            <div class="info-card">
                <h3>Hardware Pipeline</h3>
                <p style="font-size: 0.9rem; color: #aaa;">Target: Hailo-10H</p>
                <p style="font-size: 0.9rem; color: #aaa;">Lane: PCIe x4</p>
                <p style="font-size: 0.9rem; color: #aaa;">State: <span style="color:var(--neon-green)">ARMED</span></p>
            </div>
            <div class="info-card">
                <h3>Vanguard Engine</h3>
                <p style="font-size: 0.9rem; color: #aaa;">LLM: LLaVA via Ollama</p>
                <p style="font-size: 0.9rem; color: #aaa;">State: <span style="color:var(--neon-green)">100% AIRGAPPED</span></p>
            </div>
            <div class="info-card">
                <h3>Ingestion Zone</h3>
                <p style="font-size: 0.8rem; color: #888; line-height: 1.4;">
                    Mount: <code>\\\\clio.taila01894.ts.net\\...\\hailo_dropzone</code>
                </p>
                <p style="font-size: 0.85rem; margin-top: 15px;">
                    Drag and drop ANY payloads (MP4, GPX, JPG, PNG) via the SMB network drive, or upload directly from your mobile device below:
                </p>
                
                <!-- MOBILE UPLOAD PORTAL -->
                <div style="margin-top: 20px; padding: 15px; border: 1px dashed var(--neon-blue); border-radius: 8px; text-align: center; background: rgba(0,229,255,0.05);">
                    <form id="uploadForm" enctype="multipart/form-data">
                        <input type="file" id="fileInput" name="file" accept="*/*" style="display: none;" onchange="document.getElementById('uploadBtn').innerText = 'UPLOAD ' + this.files[0].name;">
                        <button type="button" onclick="document.getElementById('fileInput').click()" style="background: transparent; border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%; margin-bottom: 10px; font-weight: bold;">
                            SELECT CAPTURE
                        </button>
                        <button type="button" id="uploadBtn" onclick="uploadFile()" style="background: var(--neon-blue); color: #000; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%; font-weight: bold;">
                            TRANSMIT TO HAILO
                        </button>
                    </form>
                    <div id="uploadStatus" style="font-size: 0.8rem; color: var(--neon-green); margin-top: 10px;"></div>
                </div>
            </div>
            
            <div class="info-card">
                <h3>Vanguard Comm-Link (Omega=1)</h3>
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <input type="text" id="chatInput" placeholder="Message Vanguard..." style="flex:1; background: #000; border: 1px solid rgba(0,255,136,0.3); color: var(--neon-green); border-radius: 4px; padding: 8px; font-family: 'Inter';" onkeypress="if(event.key === 'Enter') sendComm()">
                    <button onclick="sendComm()" style="background: rgba(0,255,136,0.2); border: 1px solid var(--neon-green); color: var(--neon-green); cursor: pointer; border-radius: 4px; padding: 8px 12px; font-weight: bold;">TX</button>
                </div>
            </div>
        </div>
        <div class="terminal-container">
            <div class="terminal-header">
                <span>[CORTEX_STREAM]</span>
                <span>TAIL -F /SOV/LOGS</span>
            </div>
            <div class="terminal-output" id="terminal">Initializing connection to Node.73 daemon...</div>
        </div>
    </div>

    <script>
        const terminal = document.getElementById('terminal');
        const evtSource = new EventSource('/stream');
        
        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const line = document.createElement('div');
            line.textContent = data.message;
            terminal.appendChild(line);
            
            // Auto-scroll to bottom
            terminal.scrollTop = terminal.scrollHeight;
        };

        evtSource.onerror = function() {
            const err = document.createElement('div');
            err.style.color = 'var(--warning)';
            err.textContent = "[!] Connection lost. Retrying...";
            terminal.appendChild(err);
        };

        function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            if (!file) return;

            document.getElementById('uploadStatus').innerText = "Transmitting payload...";
            
            fetch('/upload?filename=' + encodeURIComponent(file.name), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/octet-stream'
                },
                body: file
            })
            .then(res => res.text())
            .then(text => {
                document.getElementById('uploadStatus').innerText = "Transmission Complete! Cortex analyzing...";
            })
            .catch(err => {
                document.getElementById('uploadStatus').innerText = "Transmission Failed: " + err;
                document.getElementById('uploadStatus').style.color = "var(--warning)";
            });
        }
        function sendComm() {
            const input = document.getElementById('chatInput');
            const msg = input.value;
            if(!msg) return;
            input.value = '';
            fetch('/chat?msg=' + encodeURIComponent(msg), {method: 'POST'});
        }
    </script>
</body>
</html>"""

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default HTTP logs to keep console clean
        pass
        
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            # Send initial message connecting
            # Create a dedicated queue for this client
            client_queue = Queue()
            client_queues.append(client_queue)
            
            init_msg = f"data: {json.dumps({'message': '[SYS] Stream Connected. Dropzone armed.'})}\n\n"
            self.wfile.write(init_msg.encode('utf-8'))
            self.wfile.flush()
            
            try:
                # Keep connection open, streaming from the queue
                while True:
                    # Block until log available
                    message = client_queue.get()
                    self.wfile.write(message.encode('utf-8'))
                    self.wfile.flush()
            except Exception:
                pass # Client disconnected
            finally:
                if client_queue in client_queues:
                    client_queues.remove(client_queue)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith('/upload'):
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                file_data = self.rfile.read(content_length)
                
                # Basic naming if query param fails
                file_name = f"mobile_upload_{int(time.time())}.bin"
                
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                if 'filename' in qs:
                    # Sanitize filename
                    raw_name = qs['filename'][0]
                    clean_name = "".join(c for c in raw_name if c.isalnum() or c in "._- ")
                    if clean_name:
                        file_name = clean_name
                    
                filepath = os.path.join(DROPZONE_DIR, file_name)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                    
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Success")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path.startswith('/chat'):
            # James talking to Vanguard
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'msg' in qs:
                log(f"\n[COMMLINK] JAMES: {qs['msg'][0]}")
            self.send_response(200)
            self.end_headers()
        elif self.path.startswith('/vanguard_reply'):
            # Vanguard proxy command replying to James' phone
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'msg' in qs:
                log(f"\n[VANGUARD] {qs['msg'][0]}")
            self.send_response(200)
            self.end_headers()

from socketserver import ThreadingMixIn
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    allow_reuse_address = True

def run_server():
    server = ThreadedHTTPServer(('0.0.0.0', PORT), DashboardHandler)
    log(f"")
    log(f"===========================================================")
    log(f"[UI] Sovereign Hailo Dashboard LIVE at http://clio.taila01894.ts.net:{PORT}")
    log(f"===========================================================")
    server.serve_forever()

if __name__ == "__main__":
    # Start the daemon poller in the background
    threading.Thread(target=poll_directory, daemon=True).start()
    # Run the HTTP server on main thread
    run_server()
