#!/home/james/stacklabs/.venv/bin/python3
"""dead_drop_server_v2 -- Personal VFS Space routing, Artemis CUDA transcription gate, and URL Sniper portal."""
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from scripts.dead_drop_common import *  # noqa: F401,F403

app = Flask(__name__)
app.json.compact = False

try:
    if "/home/james/stacklabs" not in sys.path:
        sys.path.insert(0, "/home/james/stacklabs")
    from scripts.fanstack_predict_engine import register_flask_routes
    register_flask_routes(app)
    logger.info("⚡ Mounted Kalshi Prediction Market routes on Flask app (/api/predict)")
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
            abort(403, description="Access Forbidden: Cockpit is strictly restricted to internal Tailscale mesh.")


app.config['UPLOAD_FOLDER'] = PILOT_DROPS_DIR
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB payload limit

try:
    from scripts.blueprints.phone_bridge_bp import phone_bridge_bp
    app.register_blueprint(phone_bridge_bp)
    logger.info("Successfully mounted phone_bridge_bp on Port 8088 (/api/phone/inbound & /api/ingress/sms)")
except Exception as e:
    logger.error(f"Failed to register phone_bridge_bp: {e}")

try:
    from scripts.blueprints.voice_query_bp import voice_query_bp
    app.register_blueprint(voice_query_bp)
    logger.info("Successfully mounted voice_query_bp on Port 8088 (/api/voice/normalize & /api/voice/latest_query)")
except Exception as e:
    logger.error(f"Failed to register voice_query_bp: {e}")

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
    """Serve the StackLabs Restricted Enterprise Diligence Drop Portal with Personal VFS Space."""
    from_arg = request.args.get('from', '').strip()
    active_slug = normalize_user_slug(from_arg or "james")
    ensure_user_vfs_space(active_slug)

    if request.method == 'POST':
        submitted_key = (request.form.get('passcode') or request.form.get('key') or '').strip()
        if submitted_key in get_valid_access_keys():
            auth_hash = get_auth_hash(submitted_key)
            target_url = f"/?from={urllib.parse.quote(from_arg)}" if from_arg else "/"
            resp = make_response(redirect(target_url))
            is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
            resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
            return resp
        return render_template_string(PASSCODE_GATE_TEMPLATE, error="Invalid access key. Please verify and try again.", from_arg=from_arg), 401

    q_key = request.args.get('key', '').strip()
    cookie_val = request.cookies.get(AUTH_COOKIE_NAME, '').strip()
    valid_hashes = get_all_valid_hashes()
    sender_prefill = from_arg if from_arg else active_slug

    if is_tailscale_request(request):
        auth_hash = get_auth_hash("pilot")
        resp = make_response(render_template_string(DROP_PORTAL_TEMPLATE, sender_prefill=sender_prefill, active_slug=active_slug))
        is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
        return resp

    if q_key and q_key in get_valid_access_keys():
        auth_hash = get_auth_hash(q_key)
        resp = make_response(render_template_string(DROP_PORTAL_TEMPLATE, sender_prefill=sender_prefill, active_slug=active_slug))
        is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        resp.set_cookie(AUTH_COOKIE_NAME, auth_hash, max_age=30*86400, httponly=True, samesite='Lax', secure=is_secure, path='/')
        return resp

    if cookie_val and (cookie_val in valid_hashes or cookie_val in get_valid_access_keys()):
        return render_template_string(DROP_PORTAL_TEMPLATE, sender_prefill=sender_prefill, active_slug=active_slug)

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
    return jsonify({"status": "unauthorized", "message": "Invalid access key. Please verify and try again."}), 401


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Ingress endpoint routing files & audio into /vfs/spaces/<user_slug>/ + /pilot_drops/incoming/."""
    is_cf = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public = 'stacklabsllc.com' in request.host.lower()
    if (is_cf or is_public) and not is_authorized(request):
        form_key = (request.form.get('key') or request.form.get('passcode') or '').strip()
        if form_key not in get_valid_access_keys():
            return jsonify({"status": "error", "error": "Unauthorized. Access key required."}), 401

    if 'file' not in request.files:
        return jsonify({"status": "error", "error": "No file in request"}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"status": "error", "error": "Empty filename"}), 400

    sender = (request.form.get('sender') or request.args.get('from') or '').strip()
    user_slug = normalize_user_slug(sender)
    space = ensure_user_vfs_space(user_slug)
    if not sender:
        sender = user_slug

    incoming_dir = os.path.join(PILOT_DROPS_DIR, 'incoming')
    os.makedirs(incoming_dir, exist_ok=True)
    orig_filename = secure_filename(file.filename) or f"diligence_doc_{int(time.time())}.bin"

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

    sha256_hasher = hashlib.sha256()
    size_bytes = 0
    with open(target_path, "wb") as f:
        while chunk := file.stream.read(65536):
            sha256_hasher.update(chunk)
            f.write(chunk)
            size_bytes += len(chunk)

    file_sha256 = sha256_hasher.hexdigest()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    memo = request.form.get('memo', '').strip()

    # Mirror raw file into Personal VFS Space uploads/
    space_upload_path = os.path.join(space["uploads"], target_filename)
    link_or_copy_file(target_path, space_upload_path)

    file_ext = os.path.splitext(target_filename)[1].lower()
    mimetype = getattr(file, 'mimetype', '') or ''
    is_audio = file_ext in AUDIO_EXTENSIONS or mimetype.startswith('audio/')

    transcript = ""
    duration_seconds = None
    if is_audio:
        link_or_copy_file(target_path, os.path.join(space["audio"], target_filename))
        duration_seconds = get_audio_duration(target_path)
        transcript = transcribe_audio_file(target_path, user_slug=user_slug)
        transcript_path = f"{target_path}.transcript.txt"
        space_transcript_path = os.path.join(space["transcripts"], f"{target_filename}.transcript.txt")
        try:
            with open(transcript_path, "w", encoding="utf-8") as tf:
                tf.write(transcript)
            with open(space_transcript_path, "w", encoding="utf-8") as stf:
                stf.write(transcript)
        except Exception as te:
            logger.error(f"Failed to write transcript companion file: {te}")
    elif file_ext in {'.txt', '.md', '.csv', '.json', '.srt', '.vtt'}:
        link_or_copy_file(target_path, os.path.join(space["transcripts"], target_filename))

    meta_data = {
        "filename": target_filename,
        "sender": sender,
        "user_slug": user_slug,
        "workspace": f"/vfs/spaces/{user_slug}",
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
    space_meta_path = f"{space_upload_path}.meta.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
        link_or_copy_file(meta_path, space_meta_path)
    except Exception as e:
        logger.error(f"Failed to write metadata JSON: {e}")

    def sync_to_edge_drive():
        try:
            cmd = ["/usr/bin/rclone", "copy", incoming_dir, "stacklabs_edge:pilot_drops/incoming", "--timeout", "60s", "--contimeout", "15s", "--quiet"]
            subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except Exception as err:
            logger.error(f"Background drive sync failed: {err}")

    threading.Thread(target=sync_to_edge_drive, daemon=True).start()

    file_link = f"file://{space_upload_path}"
    audio_url = f"/drops/{folder}/{target_filename}" if is_audio else None
    return jsonify({
        "status": "success",
        "filename": target_filename,
        "sender": sender,
        "user_slug": user_slug,
        "workspace": f"/vfs/spaces/{user_slug}",
        "memo": memo,
        "sha256": file_sha256,
        "size_bytes": size_bytes,
        "size_formatted": format_bytes(size_bytes),
        "timestamp": timestamp,
        "folder": folder,
        "rel_path": f"{folder}/{target_filename}",
        "local_path": space_upload_path,
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


@app.route('/api/drop/snipe', methods=['POST'])
def api_drop_snipe():
    """Snipe a YouTube or media URL into the user's personal VFS space with 3-bullet brief + 40s audio reply."""
    is_cf = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public = 'stacklabsllc.com' in request.host.lower()
    if (is_cf or is_public) and not is_authorized(request):
        return jsonify({"status": "error", "error": "Unauthorized. Access key required."}), 401

    payload = request.get_json(silent=True) or request.form or {}
    url = (payload.get("url") or "").strip()
    sender = (payload.get("sender") or payload.get("user_slug") or request.args.get("from") or "james").strip()
    if not url:
        return jsonify({"status": "error", "error": "Please provide a valid media or YouTube URL."}), 400

    try:
        return jsonify(execute_user_space_snipe(url=url, raw_sender=sender))
    except Exception as exc:
        logger.error(f"Personal VFS snipe error for {url}: {exc}")
        return jsonify({"status": "error", "error": str(exc)}), 500


@app.route('/api/drop/space', methods=['GET'])
@app.route('/api/drop/space/<user_slug>', methods=['GET'])
def api_drop_space(user_slug: str = "james"):
    """Return all files, transcripts, snipes, and audio inside /home/james/stacklabs/vfs/spaces/<user_slug>/."""
    is_cf = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public = 'stacklabsllc.com' in request.host.lower()
    if (is_cf or is_public) and not is_authorized(request):
        return jsonify({"status": "error", "error": "Unauthorized. Access key required."}), 401
    return jsonify(inspect_user_vfs_space(user_slug or request.args.get("from") or "james"))


@app.route('/drops/spaces/<user_slug>/<path:subpath>')
def serve_user_space_asset(user_slug: str, subpath: str):
    """Serve audio, transcripts, or uploads from /home/james/stacklabs/vfs/spaces/<user_slug>/<subpath>."""
    is_cf = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public = 'stacklabsllc.com' in request.host.lower()
    if (is_cf or is_public) and not is_authorized(request):
        abort(403)
    return send_from_directory(os.path.join(VFS_SPACES_ROOT, normalize_user_slug(user_slug)), subpath)


@app.route('/api/drops', methods=['GET'])
def api_drops():
    """List recent files in pilot_drops directory and dedicated subfolders."""
    is_cloudflare = bool(request.headers.get('CF-Connecting-IP') or request.headers.get('cf-ray'))
    is_public_domain = 'stacklabsllc.com' in request.host.lower()
    if (is_cloudflare or is_public_domain) and not is_authorized(request):
        abort(403, description="Access Forbidden: Drop enumeration is restricted.")
    files = []
    try:
        def scan_dir(dir_path: str, folder_name: str):
            if not os.path.exists(dir_path):
                return
            for entry in os.scandir(dir_path):
                if entry.is_file() and not entry.name.startswith('.'):
                    st = entry.stat()
                    ext = os.path.splitext(entry.name)[1].lower()
                    diff_sec = time.time() - st.st_mtime
                    time_ago = f"{int(diff_sec)}s ago" if diff_sec < 60 else (
                        f"{int(diff_sec // 60)}m ago" if diff_sec < 3600 else (
                            f"{int(diff_sec // 3600)}h ago" if diff_sec < 86400 else f"{int(diff_sec // 86400)}d ago"
                        )
                    )
                    rel_path = f"{folder_name}/{entry.name}" if folder_name != "root" else entry.name
                    file_link = f"file://{entry.path}"
                    files.append({
                        "name": entry.name, "folder": folder_name, "rel_path": rel_path,
                        "size_bytes": st.st_size, "size_formatted": format_bytes(st.st_size),
                        "mtime": st.st_mtime, "time_ago": time_ago, "is_image": ext in IMAGE_EXTENSIONS,
                        "icon": "📄", "file_link": file_link,
                        "markdown_img": f"![{entry.name}]({file_link})", "markdown_link": f"[{entry.name}]({file_link})"
                    })

        scan_dir(PILOT_DROPS_DIR, "root")
        for sub in SUBFOLDERS:
            scan_dir(os.path.join(PILOT_DROPS_DIR, sub), sub)
        files.sort(key=lambda x: x['mtime'], reverse=True)
    except Exception as e:
        logger.error(f"Error listing drops: {e}")
    return jsonify({"files": files})


@app.route('/drops/<path:filename>')
def serve_drop(filename):
    """Serve asset from pilot_drops."""
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
    logger.info(f"⚡ Starting Mobile Pilot Drop Gateway on port {port}...")
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)


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
from scripts.blueprints.burst_telemetry import burst_blueprint
app.register_blueprint(burst_blueprint)
from scripts.blueprints.briefing_bp import bp as briefing_bp
app.register_blueprint(briefing_bp)

if __name__ == '__main__':
    run_server(port=int(os.environ.get("PORT", 8089)))
