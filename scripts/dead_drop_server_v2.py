"""dead_drop_server_v2 -- ingress + auth gate + blueprint registration (generated).
STAGING: defaults to port 8089. Live dead_drop_server.py is untouched."""
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from scripts.dead_drop_common import *  # noqa: F401,F403

app = Flask(__name__)


try:
    if "/home/james/SovereignOS" not in sys.path:
        sys.path.insert(0, "/home/james/SovereignOS")
    from scripts.fanstack_predict_engine import register_flask_routes
    register_flask_routes(app)
    logger.info("⚡ Mounted Deranged Kalshi Prediction Market routes on Flask app (/api/predict)")
except Exception as e:
    logger.error(f"Failed to mount predict routes on dead drop server: {e}")


@app.before_request
def enforce_cockpit_tailscale_security():
    """
    Blocks all access to /cockpit, /api/cockpit, and /api/sync when accessed
    through public Cloudflare Tunnel or external hostnames.
    Access is strictly permitted over Tailscale (clio.taila01894.ts.net) or localhost.
    """
    path = request.path
    if path.startswith('/cockpit') or path.startswith('/api/cockpit') or path.startswith('/api/sync'):
        is_cloudflare = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
        is_public_domain = 'stacklabsllc.com' in request.host.lower()
        if is_cloudflare or is_public_domain:
            logger.warning(f"🚨 BLOCKED public external access to {path} from {request.remote_addr} (Host: {request.host})")
            abort(403, description="Access Forbidden: Cockpit is strictly restricted to Sovereign Tailscale mesh.")


app.config['UPLOAD_FOLDER'] = PILOT_DROPS_DIR


app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB payload limit


try:
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from sms_ingress import sms_ingress_bp
    app.register_blueprint(sms_ingress_bp)
    logger.info("Successfully mounted sms_ingress_bp on Port 8088 (/api/ingress/sms)")
except Exception as e:
    logger.error(f"Failed to register sms_ingress_bp: {e}")


try:
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from web_drop_ingress import web_drop_ingress_bp
    app.register_blueprint(web_drop_ingress_bp)
    logger.info("Successfully mounted web_drop_ingress_bp on Port 8088 (/drop)")
except Exception as e:
    logger.error(f"Failed to register web_drop_ingress_bp: {e}")


@app.route('/', methods=['GET', 'POST'])
def index():
    """Serve the StackLabs Restricted Enterprise Diligence Drop Portal with 30-Day Magic Key Gate."""
    from_arg = request.args.get('from', '').strip()
    # Handle POST passcode submission from Passcode Gate
    if request.method == 'POST':
        submitted_key = (request.form.get('passcode') or request.form.get('key') or '').strip()
        if submitted_key in get_valid_access_keys():
            auth_hash = get_auth_hash(submitted_key)
            target_url = f"/?from={urllib.parse.quote(from_arg)}" if from_arg else "/"
            resp = make_response(redirect(target_url))
            is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
            resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
            return resp
        else:
            return render_template_string(PASSCODE_GATE_TEMPLATE, error="Invalid access key. Please verify and try again.", from_arg=from_arg), 401

    # Handle GET request
    q_key = request.args.get('key', '').strip()
    cookie_val = request.cookies.get(AUTH_COOKIE_NAME, '').strip()
    valid_hashes = get_all_valid_hashes()

    # Determine sender prefill
    if from_arg:
        sender_prefill = from_arg
    else:
        sender_prefill = ""

    # If valid query key provided: set 30-day cookie and render Drop Interface
    if q_key and q_key in get_valid_access_keys():
        auth_hash = get_auth_hash(q_key)
        resp = make_response(render_template_string(DROP_PORTAL_TEMPLATE, sender_prefill=sender_prefill))
        is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
        return resp

    # If valid cookie present: render Drop Interface
    if cookie_val and (cookie_val in valid_hashes or cookie_val in get_valid_access_keys()):
        return render_template_string(DROP_PORTAL_TEMPLATE, sender_prefill=sender_prefill)

    # Unauthorized: Render Passcode Gate
    return render_template_string(PASSCODE_GATE_TEMPLATE, error=None, from_arg=from_arg)


@app.route('/api/auth', methods=['POST'])
def api_auth():
    """Authenticate via AJAX and set 30-day HttpOnly cookie."""
    data = request.get_json(silent=True) or request.form
    key = (data.get('key') or data.get('passcode') or '').strip()
    if key in get_valid_access_keys():
        auth_hash = get_auth_hash(key)
        resp = jsonify({"status": "authenticated", "message": "Access granted"})
        is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
        return resp
    return jsonify({"status": "error", "message": "Invalid access key. Please verify and try again."}), 401


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Ingress endpoint for Enterprise Diligence Documents and Drops."""
    # Check authorization if accessed externally
    is_cf = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public = 'stacklabsllc.com' in request.host.lower()
    if is_cf or is_public:
        if not is_authorized(request):
            form_key = (request.form.get('key') or request.form.get('passcode') or '').strip()
            if form_key not in get_valid_access_keys():
                return jsonify({"status": "error", "error": "Unauthorized. Access key required."}), 401

    if 'file' not in request.files:
        return jsonify({"status": "error", "error": "No file in request"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"status": "error", "error": "Empty filename"}), 400

    incoming_dir = os.path.join(PILOT_DROPS_DIR, 'incoming')
    os.makedirs(incoming_dir, exist_ok=True)

    orig_filename = secure_filename(file.filename)
    if not orig_filename:
        orig_filename = f"diligence_doc_{int(time.time())}.bin"

    requested_folder = request.form.get('folder', 'incoming').strip()
    if requested_folder and requested_folder not in ('auto', 'incoming', ''):
        folder = requested_folder
        dest_dir = os.path.join(PILOT_DROPS_DIR, folder)
        os.makedirs(dest_dir, exist_ok=True)
    else:
        folder = 'incoming'
        dest_dir = incoming_dir

    target_filename = get_unique_filename(dest_dir, orig_filename)
    target_path = os.path.join(dest_dir, target_filename)

    # Save file and calculate SHA-256 hash
    sha256_hasher = hashlib.sha256()
    size_bytes = 0
    with open(target_path, "wb") as f:
        while chunk := file.stream.read(65536):
            sha256_hasher.update(chunk)
            f.write(chunk)
            size_bytes += len(chunk)

    file_sha256 = sha256_hasher.hexdigest()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sender = request.form.get('sender', '').strip()
    if not sender:
        sender = "Direct Ingress"
    memo = request.form.get('memo', '').strip()

    # Detect audio format and trigger deterministic transcription pipeline
    file_ext = os.path.splitext(target_filename)[1].lower()
    mimetype = getattr(file, 'mimetype', '') or ''
    is_audio = file_ext in AUDIO_EXTENSIONS or mimetype.startswith('audio/')

    transcript = ""
    duration_seconds = None
    if is_audio:
        duration_seconds = get_audio_duration(target_path)
        transcript = transcribe_audio_file(target_path)
        # Write companion plain text transcript
        transcript_path = f"{target_path}.transcript.txt"
        try:
            with open(transcript_path, "w", encoding="utf-8") as tf:
                tf.write(transcript)
        except Exception as te:
            logger.error(f"Failed to write transcript companion file: {te}")

    # Generate companion metadata JSON (Quarter 2 & 3)
    meta_data = {
        "filename": target_filename,
        "sender": sender,
        "memo": memo,
        "sha256": file_sha256,
        "size_bytes": size_bytes,
        "timestamp": timestamp,
        "is_audio": is_audio
    }
    if is_audio:
        meta_data["transcript"] = transcript
        meta_data["duration_seconds"] = duration_seconds

    meta_path = f"{target_path}.meta.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write metadata JSON: {e}")

    # Trigger background sync to Google Drive (stacklabs_edge:)
    def sync_to_edge_drive():
        try:
            logger.info(f"Syncing incoming drop to stacklabs_edge:pilot_drops/incoming/: {target_filename}")
            cmd = [
                "/usr/bin/rclone", "copy",
                incoming_dir,
                "stacklabs_edge:pilot_drops/incoming",
                "--timeout", "60s",
                "--contimeout", "15s",
                "--quiet"
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except Exception as err:
            logger.error(f"Background drive sync failed: {err}")

    threading.Thread(target=sync_to_edge_drive, daemon=True).start()

    logger.info(f"Ingested enterprise diligence drop: {target_filename} ({format_bytes(size_bytes)}, sha256={file_sha256[:12]}..., is_audio={is_audio})")

    file_link = f"file://{target_path}"
    audio_url = f"/drops/{folder}/{target_filename}" if is_audio else None
    return jsonify({
        "status": "success",
        "filename": target_filename,
        "sender": sender,
        "memo": memo,
        "sha256": file_sha256,
        "size_bytes": size_bytes,
        "size_formatted": format_bytes(size_bytes),
        "timestamp": timestamp,
        "folder": folder,
        "rel_path": f"{folder}/{target_filename}",
        "local_path": target_path,
        "file_link": file_link,
        "markdown_img": f"![{target_filename}]({file_link})",
        "markdown_link": f"[{target_filename}]({file_link})",
        "orig_size": format_bytes(size_bytes),
        "final_size": format_bytes(size_bytes),
        "reduction_pct": 0.0,
        "is_audio": is_audio,
        "transcript": transcript,
        "duration_seconds": duration_seconds,
        "audio_url": audio_url,
        "relative_audio_link": audio_url
    })


@app.route('/api/drops', methods=['GET'])
def api_drops():
    """List recent files in pilot_drops directory and dedicated subfolders."""
    is_cloudflare = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public_domain = 'stacklabsllc.com' in request.host.lower()
    if is_cloudflare or is_public_domain:
        if not is_authorized(request):
            abort(403, description="Access Forbidden: Drop enumeration is restricted.")
    files = []
    try:
        def scan_dir(dir_path: str, folder_name: str):
            if not os.path.exists(dir_path):
                return
            entries = os.scandir(dir_path)
            for entry in entries:
                if entry.is_file() and not entry.name.startswith('.'):
                    st = entry.stat()
                    ext = os.path.splitext(entry.name)[1].lower()
                    is_image = ext in IMAGE_EXTENSIONS
                    
                    diff_sec = time.time() - st.st_mtime
                    if diff_sec < 60:
                        time_ago = f"{int(diff_sec)}s ago"
                    elif diff_sec < 3600:
                        time_ago = f"{int(diff_sec // 60)}m ago"
                    elif diff_sec < 86400:
                        time_ago = f"{int(diff_sec // 3600)}h ago"
                    else:
                        time_ago = f"{int(diff_sec // 86400)}d ago"

                    icon = "📄"
                    if is_image:
                        icon = "🖼️"
                    elif ext in {'.mp4', '.mov', '.webm', '.mkv', '.avi'}:
                        icon = "🎬"
                    elif ext in {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}:
                        icon = "🎵"
                    elif ext in {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'}:
                        icon = "📦"
                    elif ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}:
                        icon = "📑"

                    rel_path = f"{folder_name}/{entry.name}" if folder_name != "root" else entry.name
                    file_link = f"file://{entry.path}"
                    files.append({
                        "name": entry.name,
                        "folder": folder_name,
                        "rel_path": rel_path,
                        "size_bytes": st.st_size,
                        "size_formatted": format_bytes(st.st_size),
                        "mtime": st.st_mtime,
                        "time_ago": time_ago,
                        "is_image": is_image,
                        "icon": icon,
                        "file_link": file_link,
                        "markdown_img": f"![{entry.name}]({file_link})",
                        "markdown_link": f"[{entry.name}]({file_link})"
                    })

        # 1. Scan root
        scan_dir(PILOT_DROPS_DIR, "root")

        # 2. Scan designated subfolders
        for sub in SUBFOLDERS:
            scan_dir(os.path.join(PILOT_DROPS_DIR, sub), sub)

        # Sort newest first
        files.sort(key=lambda x: x['mtime'], reverse=True)
    except Exception as e:
        logger.error(f"Error listing drops: {e}")

    return jsonify({"files": files})


@app.route('/drops/<path:filename>')
def serve_drop(filename):
    """Serve asset from pilot_drops (supporting root or subdirectories)."""
    return send_from_directory(PILOT_DROPS_DIR, filename)


@app.route('/drops/thumb/<path:filename>')
def serve_thumb(filename):
    """Serve cached thumbnail or fallback to raw asset."""
    thumb_path = os.path.join(THUMBNAILS_DIR, filename)
    if os.path.exists(thumb_path) and os.path.isfile(thumb_path):
        return send_from_directory(THUMBNAILS_DIR, filename)
    flat_thumb_path = os.path.join(THUMBNAILS_DIR, os.path.basename(filename))
    if os.path.exists(flat_thumb_path) and os.path.isfile(flat_thumb_path):
        return send_from_directory(THUMBNAILS_DIR, os.path.basename(filename))
    return send_from_directory(PILOT_DROPS_DIR, filename)


def run_server(port: int = 8089):
    logger.info(f"⚡ Starting Sovereign Mobile Pilot Drop Gateway on port {port}...")
    logger.info(f"📁 Ingress Directory: {PILOT_DROPS_DIR}")
    host = '127.0.0.1'
    logger.info(f"Binding strictly to {host}:{port} for Tailscale HTTPS proxying")
    app.run(host=host, port=port, debug=False, threaded=True)


# --- BLUEPRINTS (extracted) ---
from scripts.blueprints.cockpit_bp import bp as cockpit_bp
app.register_blueprint(cockpit_bp)
from scripts.blueprints.sync_bp import bp as sync_bp
app.register_blueprint(sync_bp)
from scripts.blueprints.media_bp import bp as media_bp
app.register_blueprint(media_bp)
from scripts.blueprints.horizon_bp import bp as horizon_bp
app.register_blueprint(horizon_bp)
from scripts.blueprints.pulse_bp import bp as pulse_bp
app.register_blueprint(pulse_bp)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8089))
    run_server(port=port)
