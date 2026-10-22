from flask import Flask, render_template_string, request, jsonify
import os
import uuid
import threading
import subprocess
import json
import time
import glob

app = Flask(__name__)

MEDIA_DIR = "/home/james/stacklabs/media_vault/01_Ingest/postgames"
os.makedirs(MEDIA_DIR, exist_ok=True)

JOBS = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign Stream Sniper</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #E0E0E0;
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #00E676; /* Hacker Green / Intel Vibe */
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .container {
            width: 100%;
            max-width: 900px;
            background-color: #1E1E1E;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: bold;
            color: #A0A0A0;
        }
        input[type="text"] {
            width: 100%;
            padding: 1rem;
            background-color: #2D2D2D;
            border: 1px solid #404040;
            color: #FFF;
            border-radius: 4px;
            font-size: 1.1rem;
            box-sizing: border-box;
        }
        button {
            background-color: #00E676;
            color: #000;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.2rem;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
            width: 100%;
        }
        button:hover {
            background-color: #00C853;
        }
        button:disabled {
            background-color: #444;
            color: #888;
            cursor: not-allowed;
        }
        .status-box {
            margin-top: 1.5rem;
            padding: 1rem;
            background-color: #252525;
            border-left: 4px solid #00E676;
            display: none;
            font-family: monospace;
            font-size: 1.1rem;
        }
        #result-container {
            margin-top: 2rem;
            display: none;
        }
        #result-text {
            background-color: #2D2D2D;
            border: 1px solid #404040;
            padding: 1.5rem;
            font-size: 1.1rem;
            border-radius: 4px;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .loader {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #00E676;
            animation: spin 1s ease-in-out infinite;
            vertical-align: middle;
            margin-right: 10px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <h1>Sovereign Stream Sniper Dashboard</h1>
    <div class="container">
        <div class="form-group">
            <label for="url-input">Target Stream URL (YouTube):</label>
            <input type="text" id="url-input" placeholder="https://www.youtube.com/watch?v=...">
        </div>

        <button id="analyze-btn" onclick="startAnalysis()">Extract Juicy Bits</button>

        <div id="status-box" class="status-box">
            <span class="loader" id="spinner"></span>
            <span id="status-text">Initializing...</span>
        </div>

        <div id="result-container">
            <h2 style="color: #00E676; margin-top: 0;">Extraction Complete</h2>
            <div id="result-text"></div>
        </div>
    </div>

    <script>
        let pollInterval;

        async function startAnalysis() {
            const url = document.getElementById('url-input').value;
            if (!url.trim()) {
                alert('Please enter a YouTube URL!');
                return;
            }

            document.getElementById('analyze-btn').disabled = true;
            document.getElementById('result-container').style.display = 'none';
            document.getElementById('status-box').style.display = 'block';
            document.getElementById('spinner').style.display = 'inline-block';
            document.getElementById('status-text').textContent = 'Submitting job...';

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);

                const jobId = data.job_id;
                pollInterval = setInterval(() => checkStatus(jobId), 3000);
            } catch (err) {
                alert('Error starting analysis: ' + err.message);
                resetUI();
            }
        }

        async function checkStatus(jobId) {
            try {
                const res = await fetch('/api/status/' + jobId);
                const data = await res.json();
                
                document.getElementById('status-text').textContent = data.status;

                if (data.status === 'DONE') {
                    clearInterval(pollInterval);
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('status-text').textContent = 'Analysis Finished! See results below.';
                    
                    document.getElementById('result-text').innerHTML = marked.parse(data.result);
                    document.getElementById('result-container').style.display = 'block';
                    document.getElementById('analyze-btn').disabled = false;
                } else if (data.status.startsWith('ERROR:')) {
                    clearInterval(pollInterval);
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('analyze-btn').disabled = false;
                }
            } catch (err) {
                console.error(err);
            }
        }

        function resetUI() {
            document.getElementById('analyze-btn').disabled = false;
            document.getElementById('status-box').style.display = 'none';
        }
    </script>
</body>
</html>
"""

def extract_comments_to_md(info_json_path, output_md_path):
    try:
        with open(info_json_path, 'r') as f:
            data = json.load(f)
        
        comments = data.get('comments', [])
        if not comments:
            return False

        with open(output_md_path, 'w') as f:
            f.write("# Live Chat & Comments Extraction\n\n")
            for c in comments:
                author = c.get('author', 'Unknown')
                text = c.get('text', '')
                f.write(f"**{author}**: {text}\n\n")
        return True
    except Exception as e:
        print(f"Failed to extract comments: {e}")
        return False

def worker(job_id, url):
    try:
        # 1. Download Video and Comments
        JOBS[job_id]['status'] = "Downloading Video and Live Chat (this takes a few minutes)..."
        
        # Get the filename prefix from yt-dlp first
        cmd_name = ["yt-dlp", "--print", "filename", "-o", "%(title)s", url]
        try:
            base_title = subprocess.check_output(cmd_name).decode().strip().split('\n')[0]
        except:
            base_title = f"stream_{job_id}"

        # Clean title for filesystem
        safe_title = "".join([c for c in base_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        file_prefix = os.path.join(MEDIA_DIR, safe_title)

        cmd = [
            "yt-dlp", 
            "--write-comments", 
            "--write-info-json", 
            "-o", f"{file_prefix}.%(ext)s", 
            url
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Find the downloaded video file
        possible_vids = glob.glob(f"{file_prefix}.*")
        video_path = None
        info_json_path = None
        
        for p in possible_vids:
            if p.endswith('.mp4') or p.endswith('.webm') or p.endswith('.mkv'):
                video_path = p
            if p.endswith('.info.json'):
                info_json_path = p

        if not video_path:
            JOBS[job_id]['status'] = "ERROR: Failed to download video."
            return

        # 2. Extract Comments
        comments_md_path = f"{file_prefix}_comments.md"
        has_comments = False
        if info_json_path:
            JOBS[job_id]['status'] = "Parsing live chat comments..."
            has_comments = extract_comments_to_md(info_json_path, comments_md_path)

        # 3. Run Pipeline
        JOBS[job_id]['status'] = "Transcribing & Extracting Juicy Bits with AI (this takes a few minutes)..."
        
        pipeline_cmd = ["python3", "/home/james/stacklabs/scripts/postgame_pipeline.py", video_path]
        if has_comments:
            pipeline_cmd.append(comments_md_path)
            
        subprocess.run(pipeline_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 4. Read Results
        juicy_bits_path = f"{file_prefix}_juicy_bits.md"
        if os.path.exists(juicy_bits_path):
            with open(juicy_bits_path, 'r') as f:
                result_text = f.read()
        else:
            result_text = "Analysis completed, but could not find the Juicy Bits report."

        # 5. Cleanup (Delete massive video and raw json)
        JOBS[job_id]['status'] = "Cleaning up massive video files..."
        try:
            os.remove(video_path)
            if info_json_path:
                os.remove(info_json_path)
        except Exception as e:
            print(f"Cleanup error: {e}")

        JOBS[job_id]['result'] = result_text
        JOBS[job_id]['status'] = "DONE"

    except Exception as e:
        JOBS[job_id]['status'] = f"ERROR: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "Starting up...",
        "result": None
    }

    t = threading.Thread(target=worker, args=(job_id, url))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(JOBS[job_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=False)
