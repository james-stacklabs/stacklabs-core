"""media blueprint extracted from dead_drop_server.py (generated). Routes unchanged."""
from flask import Blueprint
from scripts.dead_drop_common import *  # noqa: F401,F403

bp = Blueprint("media", __name__)


_WHISPER_MODEL = None


_WHISPER_LOCK = threading.Lock()


def get_whisper_model():
    """Lazy loader for local Whisper base.en model."""
    global _WHISPER_MODEL
    with _WHISPER_LOCK:
        if _WHISPER_MODEL is None:
            import whisper
            logger.info("⚡ Loading local Whisper base.en model onto CPU...")
            _WHISPER_MODEL = whisper.load_model('base.en')
            logger.info("✓ Local Whisper base.en model loaded")
        return _WHISPER_MODEL


@bp.route('/api/cockpit/snipe_youtube', methods=['POST'])
def cockpit_snipe_youtube():
    """
    Snipe audio track from YouTube URL using yt-dlp and transcribe via local Whisper.
    Returns: {success, video_id, title, duration_secs, transcript, audio_file}
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "No YouTube URL provided"}), 400

    snipes_dir = Path("/home/james/sovereign_inbox/today/snipes")
    snipes_dir.mkdir(parents=True, exist_ok=True)

    ytdlp_bin = "/home/james/SovereignOS/.venv/bin/yt-dlp"
    if not Path(ytdlp_bin).exists():
        ytdlp_bin = shutil.which("yt-dlp") or "yt-dlp"

    video_id = None
    title = "YouTube Snipe"
    duration_secs = 0

    try:
        cmd = [
            ytdlp_bin,
            "--no-simulate",
            "-x",
            "--audio-format", "m4a",
            "--print", "%(id)s\t%(title)s\t%(duration)s",
            "-o", str(snipes_dir / "%(id)s.%(ext)s"),
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip() and not l.startswith("WARNING:")]
        if lines:
            meta = lines[-1].split("\t")
            if len(meta) > 0 and meta[0].strip():
                video_id = meta[0].strip()
            if len(meta) > 1 and meta[1].strip():
                title = meta[1].strip()
            if len(meta) > 2:
                try:
                    duration_secs = int(float(meta[2].strip()))
                except Exception:
                    duration_secs = 0
    except Exception as e:
        logger.error(f"yt-dlp failed on {url}: {e}")
        return jsonify({"success": False, "error": f"Failed downloading audio: {e}"}), 500

    if not video_id:
        m = re.search(r"(?:v=|\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
        if m:
            video_id = m.group(1)
        else:
            return jsonify({"success": False, "error": "Could not determine YouTube video ID"}), 400

    audio_file = snipes_dir / f"{video_id}.m4a"
    if not audio_file.exists():
        candidates = list(snipes_dir.glob(f"{video_id}.*"))
        for c in candidates:
            if c.suffix.lower() in ['.m4a', '.mp3', '.opus', '.webm', '.wav']:
                audio_file = c
                break

    if not audio_file.exists():
        return jsonify({"success": False, "error": f"Audio file for {video_id} not found on metal"}), 500

    txt_path = snipes_dir / f"{video_id}_transcript.txt"
    json_path = snipes_dir / f"{video_id}.json"

    # Pre-seed if legacy Erlich file exists for this video ID
    if video_id == "OXqkkpnZDgU" and not txt_path.exists():
        legacy_txt = snipes_dir / "erlich_vision_quest_transcript.txt"
        if legacy_txt.exists():
            try:
                txt_path.write_text(legacy_txt.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

    transcript = ""
    if txt_path.exists():
        try:
            transcript = txt_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    if not transcript:
        try:
            model = get_whisper_model()
            trans_res = model.transcribe(str(audio_file), fp16=False)
            transcript = trans_res.get("text", "").strip()
            txt_path.write_text(transcript, encoding="utf-8")
        except Exception as e:
            logger.error(f"Whisper transcription failed for {audio_file}: {e}")
            return jsonify({"success": False, "error": f"Whisper failed: {e}"}), 500

    try:
        json_path.write_text(json.dumps({
            "video_id": video_id,
            "title": title,
            "duration_secs": duration_secs,
            "transcript": transcript,
            "audio_file": str(audio_file),
            "created_at": datetime.now().isoformat()
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

    return jsonify({
        "success": True,
        "video_id": video_id,
        "title": title,
        "duration_secs": duration_secs,
        "transcript": transcript,
        "audio_file": str(audio_file)
    }), 200


@bp.route('/api/transcribe', methods=['POST', 'OPTIONS'])
def api_transcribe():
    """Transcribes uploaded audio using Gemini 3.8 Flash via google.genai SDK."""
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    from google import genai
    import tempfile

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        load_dotenv("/home/james/SovereignOS/.env")
        key = os.getenv("GEMINI_API_KEY")
    if not key:
        return jsonify({"status": "error", "message": "GEMINI_API_KEY missing"}), 400

    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "No audio file in request"}), 400

    audio_file = request.files['audio']
    content = audio_file.read()

    file_ext = os.path.splitext(audio_file.filename)[1] if audio_file.filename and "." in audio_file.filename else ".webm"
    if not file_ext.startswith("."):
        file_ext = f".{file_ext}"

    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        client = genai.Client(api_key=key)
        uploaded = client.files.upload(file=tmp_path)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded, "Transcribe this audio recording verbatim. Provide only the plain text transcription without any commentary or quotation marks."]
        )
        transcript = response.text.strip()
        resp = jsonify({"status": "success", "transcript": transcript})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    except Exception as e:
        logger.error(f"Cloud transcription error: {e}")
        try:
            import whisper
            model = whisper.load_model("base.en")
            res = model.transcribe(tmp_path)
            resp = jsonify({"status": "success", "transcript": res["text"].strip()})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        except Exception as we:
            resp = jsonify({"status": "error", "message": str(e)})
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp, 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@bp.route('/api/tts', methods=['POST', 'OPTIONS'])
def api_tts():
    """Generates slick studio audio using Gemini 3.8 Flash TTS with Orbit voice."""
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    from google import genai
    from google.genai import types

    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    voice = payload.get("voice", "Orbit")

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        load_dotenv("/home/james/SovereignOS/.env")
        key = os.getenv("GEMINI_API_KEY")
    if not key:
        return jsonify({"status": "error", "message": "GEMINI_API_KEY missing"}), 400

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-3.8-flash-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )
        )
        audio_bytes = response.candidates[0].content.parts[0].inline_data.data
        return Response(audio_bytes, mimetype="audio/wav", headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        resp = jsonify({"status": "error", "message": str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500
