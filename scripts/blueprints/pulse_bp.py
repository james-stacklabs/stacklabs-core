"""pulse blueprint extracted from dead_drop_server.py (generated). Routes unchanged."""
from flask import Blueprint
from scripts.dead_drop_common import *  # noqa: F401,F403

bp = Blueprint("pulse", __name__)


PULSE_HTML_TEMPLATE = load_template("pulse.html")


@bp.route('/pulse', methods=['GET'])
def pulse_hud():
    """Serve the Sovereign Daemon Pulse & Live Heartbeat HUD (WO0010108)."""
    return render_template_string(PULSE_HTML_TEMPLATE)


@bp.route('/api/pulse', methods=['GET'])
def api_pulse():
    """Real-time pulse telemetry endpoint for both Web HUD and external monitors."""
    now = time.time()
    
    # 1. Read scratch_pad_poller_heartbeat.json
    sp_hb_file = Path("/home/james/SovereignOS/logs/scratch_pad_poller_heartbeat.json")
    sp_hb = {}
    if sp_hb_file.exists():
        try:
            with open(sp_hb_file, "r") as f:
                sp_hb = json.load(f)
                ts = sp_hb.get("timestamp", 0)
                sp_hb["delta_seconds"] = max(0.0, round(now - ts, 2))
                sp_hb["is_live"] = sp_hb["delta_seconds"] < 8.0
        except Exception as e:
            sp_hb["error"] = str(e)

    # 2. Read fanstack_poller_heartbeat.json
    fs_hb_file = Path("/home/james/SovereignOS/logs/fanstack_poller_heartbeat.json")
    fs_hb = {}
    if fs_hb_file.exists():
        try:
            with open(fs_hb_file, "r") as f:
                fs_hb = json.load(f)
                ts = fs_hb.get("timestamp", 0)
                fs_hb["delta_seconds"] = max(0.0, round(now - ts, 2))
                fs_hb["is_live"] = fs_hb["delta_seconds"] < 12.0
        except Exception as e:
            fs_hb["error"] = str(e)

    # 3. Read scratch_pad.md preview (lines and active work order)
    sp_md_file = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
    scratchpad_preview = ""
    active_work_order = "No active work orders detected"
    if sp_md_file.exists():
        try:
            with open(sp_md_file, "r") as f:
                lines = f.readlines()
                scratchpad_preview = "".join(lines[:30])
                for line in lines:
                    if line.strip().startswith("- [ ]") or line.strip().startswith("## 🎯"):
                        active_work_order = line.strip()
                        break
        except Exception as e:
            scratchpad_preview = f"Error reading scratch_pad.md: {e}"

    # 4. Tail last 15 lines of scratch_pad_poller.log
    log_file = Path("/home/james/SovereignOS/logs/scratch_pad_poller.log")
    log_tail = []
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                log_tail = [line.rstrip() for line in all_lines[-15:]]
        except Exception as e:
            log_tail = [f"Error reading log: {e}"]

    return jsonify({
        "timestamp": now,
        "iso_time": datetime.utcnow().isoformat() + "Z",
        "scratch_pad_poller": sp_hb,
        "fanstack_poller": fs_hb,
        "active_work_order": active_work_order,
        "scratch_pad_preview": scratchpad_preview,
        "log_tail": log_tail
    })


@bp.route('/api/wildseed_beacon', methods=['POST', 'OPTIONS'])
def api_wildseed_beacon():
    """Relay edge visitor telemetry beacon to SDLC Portal Server (Port 8095)."""
    if request.method == 'OPTIONS':
        return ('', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
    try:
        import urllib.request
        payload = request.get_data()
        client_ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for") or request.remote_addr or ""
        req = urllib.request.Request(
            "http://127.0.0.1:8095/api/wildseed_beacon",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Forwarded-For": client_ip,
                "User-Agent": request.headers.get("User-Agent", "")
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            return (data, resp.status, {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            })
    except Exception as e:
        logger.error(f"Error forwarding wildseed_beacon to 8095: {e}")
        return jsonify({"status": "relayed_with_error", "error": str(e)}), 200
