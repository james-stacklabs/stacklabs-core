import os
import subprocess
import requests
import shutil
from flask import Flask, request, render_template_string, send_from_directory, abort, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
DROPZONE_DIR = "/home/james/SovereignOS/staging/dead_drop"
HAILO_DROPZONE = "/home/james/SovereignOS/dna/media/hailo_dropzone"
QUARANTINE_DIR = "/home/james/SovereignOS/staging/quarantine"
os.makedirs(DROPZONE_DIR, exist_ok=True)
os.makedirs(HAILO_DROPZONE, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = DROPZONE_DIR
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
VIDEO_AUDIO_EXTS = {'.mp4', '.mp3', '.m4a', '.wav', '.webm', '.mov'}
ARCHIVE_EXTS = {'.zip', '.7z', '.rar', '.tar', '.gz'}

def create_ticket(title, description):
    try:
        requests.post('http://localhost:8082/api/tickets', json={
            'title': title,
            'priority': 'High',
            'ci_id': 'CI-DEAD-DROP',
            'description': description
        }, timeout=5)
    except Exception as e:
        print(f"[ERROR] Ticket Generation Failed: {e}")

def process_archive(filepath):
    result = subprocess.run(['7z', 'l', '-ba', '-slt', filepath], capture_output=True, text=True)
    unauthorized_files = []
    extracted = 0
    files = []
    current_file = {}
    
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            if current_file:
                files.append(current_file)
                current_file = {}
            continue
        if line.startswith('Path = '):
            current_file['path'] = line.split(' = ', 1)[1]
        elif line.startswith('Folder = '):
            current_file['folder'] = (line.split(' = ', 1)[1] == '+')
            
    if current_file:
        files.append(current_file)

    for item in files:
        if item.get('folder'):
            continue
        fpath = item.get('path', '')
        ext = os.path.splitext(fpath)[1].lower()
        
        if ext in IMAGE_EXTS:
            out_dir = HAILO_DROPZONE
        elif ext in VIDEO_AUDIO_EXTS:
            out_dir = app.config['UPLOAD_FOLDER']
        else:
            unauthorized_files.append(fpath)
            continue
            
        subprocess.run(['7z', 'e', filepath, fpath, f'-o{out_dir}', '-y'], capture_output=True)
        extracted += 1

    if unauthorized_files:
        create_ticket(f"Unauthorized Payload in Archive: {os.path.basename(filepath)}", 
                      f"Found {len(unauthorized_files)} unauthorized items. Example: {unauthorized_files[0]}")
    
    shutil.move(filepath, os.path.join(QUARANTINE_DIR, os.path.basename(filepath)))
    return extracted, len(unauthorized_files)

def route_payload(filepath, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ARCHIVE_EXTS:
        exts, unauth = process_archive(filepath)
        return f"[SUCCESS] Archive Unpacked. {exts} media items sent to pipeline. Unauthorized: {unauth}"
    elif ext in IMAGE_EXTS:
        shutil.move(filepath, os.path.join(HAILO_DROPZONE, filename))
        return f"[SUCCESS] Image routed directly to Hailo NPU queue."
    elif ext in VIDEO_AUDIO_EXTS:
        return f"[SUCCESS] Media successfully staged in Dead Drop."
    else:
        shutil.move(filepath, os.path.join(QUARANTINE_DIR, filename))
        create_ticket(f"Unauthorized File Drop: {filename}", "Non-media file intercepted at Dead Drop gateway.")
        return f"[WARNING] Invalid file quarantined. Ticket created."


# --- SECURITY ---
USERNAME = 'admin'
PASSWORD = 'sovereign_drop' # Hardcoded dead-drop password

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
    'Verification required. Proceed to the Omega Gate.\n', 401,
    {'WWW-Authenticate': 'Basic realm="Sovereign Dead Drop"'})

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sovereign Dead Drop</title>
    <style>
        body { font-family: 'Courier New', Courier, monospace; background-color: #0b1120; color: #4ade80; text-align: center; margin-top: 50px; }
        .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border: 1px solid #4ade80; box-shadow: 0 0 15px #4ade8055; }
        h1 { color: #f8fafc; font-weight: normal; letter-spacing: 2px;}
        h2 { color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 10px; }
        .file-list { text-align: left; margin-bottom: 30px; }
        .file-item { padding: 10px 0; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; color: #7dd3fc; }
        .upload-section { margin-top: 30px; border-top: 1px solid #334155; padding-top: 20px;}
        input[type="file"] { padding: 10px; background: #0f172a; color: #94a3b8; border: 1px solid #4ade80; }
        input[type="submit"] { padding: 10px 20px; background: #4ade80; color: #0b1120; border: none; font-weight: bold; cursor: pointer; }
        input[type="submit"]:hover { background: #22c55e; }
        .alert { padding: 10px; margin-bottom: 20px; text-align: center; background: #166534; color: #fff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>[ SOVEREIGN DEAD DROP ]</h1>
        <p>Air-Gapped Gateway | Node .73</p>
        
        {% if message %}
        <div class="alert">{{ message }}</div>
        {% endif %}

        <h2>Available Assets</h2>
        <div class="file-list">
            {% for f in files %}
            <div class="file-item">
                <a href="{{ url_for('download_file', filename=f.name) }}">DOWNLOAD_ASSET_::_{{ f.name }}</a>
                <span style="color:#64748b;">{{ f.size }} MB</span>
            </div>
            {% else %}
            <div class="file-item"><span style="color:#64748b;">[ NO ASSETS IN BAY ]</span></div>
            {% endfor %}
        </div>

        <div class="upload-section">
            <h2>Secure Upload</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <input type="submit" value="MIGRATE TO NODE .73">
            </form>
            <p style="color:#64748b; font-size:0.8em; margin-top:20px;">Max file size: 1GB</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
@requires_auth
def index():
    message = None
    if request.method == 'POST':
        if 'file' not in request.files:
            message = "[ERROR] NO_FILE_PAYLOAD"
        else:
            file = request.files['file']
            if file.filename == '':
                message = "[ERROR] EMPTY_FILE_NAME"
            else:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                message = route_payload(filepath, filename)

    files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        path = os.path.join(app.config['UPLOAD_FOLDER'], f)
        if os.path.isfile(path):
            size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
            files.append({'name': f, 'size': size_mb})
    
    # Sort files by name
    files.sort(key=lambda x: x['name'])

    return render_template_string(HTML_TEMPLATE, files=files, message=message)

@app.route('/download/<filename>')
@requires_auth
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    print("[SYSTEM] Starting Sovereign Dead Drop on port 8088...")
    print("[WARNING] Strict security policy enforced: Binding tightly to localhost (127.0.0.1).")
    print("[WARNING] This gateway is only accessible locally or routed through secure private Tailscale mesh (100.73.155.70). Public funnels are prohibited.")
    app.run(host='127.0.0.1', port=8088, debug=False)
