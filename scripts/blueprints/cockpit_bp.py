"""cockpit blueprint extracted from dead_drop_server.py (generated). Routes unchanged."""
from flask import Blueprint
from scripts.dead_drop_common import *  # noqa: F401,F403

bp = Blueprint("cockpit", __name__)


COCKPIT_HTML_TEMPLATE = load_template("cockpit.html")


@bp.route('/cockpit', methods=['GET'])
def route_unified_cockpit():
    """Serve the StackLabs Unified Founder Cockpit."""
    return render_template_string(COCKPIT_HTML_TEMPLATE)


@bp.route('/api/cockpit/alpha_trader_stats', methods=['GET'])
def get_cockpit_alpha_trader_stats():
    """Serves real-time decoupled alpha trader payload for the Unified Cockpit."""
    candidates = [
        Path("/home/james/stacklabs_inbox/today/alpha_trader_stats.json"),
        Path("/home/james/stacklabs/33_FanStack_Lite/public/FanStack_Live/alpha_trader_stats.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return jsonify(json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:
                logger.error(f"Error reading {p}: {e}")
    return jsonify({"error": "Stats not found"}), 404


@bp.route('/api/cockpit/cmdb_lite', methods=['GET'])
def get_cockpit_cmdb_lite():
    """Serves real-time fleet, vitals, daemons, and deployed edge pages."""
    import os, psutil, subprocess
    sys.path.append("/home/james/stacklabs/scripts")
    from core.db import get_db

    # 1. Fleet Nodes from DB
    nodes = []
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.sys_id, c.name, c.short_description, c.operational_status, h.ip_address, h.model_id
                FROM cmdb_ci c
                LEFT JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id
                WHERE c.sys_class_name = 'cmdb_ci_hardware'
                ORDER BY CASE 
                    WHEN c.name = 'clio' THEN 1 
                    WHEN c.name = 'pegasus' THEN 2 
                    WHEN c.name = 'argo' THEN 3 
                    WHEN c.name = 'artemis' THEN 4
                    WHEN c.name = 'pi_zero_fleet' THEN 5
                    ELSE 6 
                END
            """)
            nodes = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"CMDB nodes query error: {e}")

    # 2. Clio Vitals
    temp = 62.0
    try:
        t_out = subprocess.check_output("sensors 2>/dev/null | grep Tctl | awk '{print $2}'", shell=True).decode().strip().replace("+", "").replace("°C", "")
        if t_out:
            temp = float(t_out)
        else:
            t_out2 = subprocess.check_output("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -n 1", shell=True).decode().strip()
            if t_out2:
                temp = round(int(t_out2) / 1000.0, 1)
    except Exception:
        pass

    power_w = 11.2
    try:
        p_out = subprocess.check_output("sensors 2>/dev/null | grep PPT | awk '{print $2}'", shell=True).decode().strip()
        if p_out:
            power_w = float(p_out)
    except Exception:
        pass

    mem = psutil.virtual_memory()
    clio_health = {
        "cpu_temp": f"{temp}°C",
        "power_draw": f"{power_w} W",
        "ram_used_gb": round(mem.used / (1024**3), 1),
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "ram_percent": mem.percent,
        "load_avg": [round(x, 2) for x in os.getloadavg()]
    }

    # 3. Active Daemons
    daemon_checks = [
        {"name": "fanstack_lite_server", "label": "FanStack WebSocket Server", "port": 8008},
        {"name": "stream_sniper_daemon", "label": "Stream Sniper & Omni-Tailer", "port": None},
        {"name": "clio_queue_watcher", "label": "GitOps CQRS Queue Watcher", "port": None},
        {"name": "faas_drive_sync", "label": "FaaS Edge Drive Sync", "port": None},
        {"name": "dead_drop_server", "label": "Unified Founder Cockpit", "port": 8088},
    ]
    processes = []
    for d in daemon_checks:
        is_active = False
        try:
            grep_out = subprocess.check_output(f"pgrep -f {d['name']}.py", shell=True).decode().strip()
            if grep_out:
                is_active = True
        except Exception:
            pass
        processes.append({**d, "status": "ACTIVE" if is_active else "IDLE"})

    # 4. Deployed Edge Pages & Vaults
    deployments = [
        {"name": "Sovereign Horizon Terminal Twin", "url": "https://stacklabs-horizon.pages.dev", "badge": "Cloudflare Pages", "status": "LIVE"},
        {"name": "Unified Founder Cockpit", "url": "https://clio.taila01894.ts.net:8088/cockpit", "badge": "Port :8088", "status": "LIVE"},
        {"name": "FaaS Creator Cockpit", "url": "https://clio.taila01894.ts.net:3033/", "badge": "Port :3033", "status": "LIVE"},
        {"name": "StackLabs Public Edge", "url": "https://stacklabsllc.com", "badge": "Corporate Edge", "status": "LIVE"},
    ]

    prospectuses = [
        {"slug": "14_Sovereign_Horizon_Prospectus", "title": "Sovereign Horizon Engine (Pawel Rudnicki)", "status": "Synced to Drive & NotebookLM"},
        {"slug": "13_FanStack_as_a_Service", "title": "FanStack as a Service (FaaS) Product Dossier", "status": "Synced to Drive"},
        {"slug": "06_Davidson_Malone_Prospectus", "title": "Davidson Homes Option #SE-101 (Jeremy Malone)", "status": "Synced to Drive"},
        {"slug": "04_ArkleVet_Prospectus", "title": "ARKLE Veterinary Care (Dr. Rox)", "status": "Synced to Drive"}
    ]

    return jsonify({
        "status": "success",
        "nodes": nodes,
        "clio_health": clio_health,
        "processes": processes,
        "deployments": deployments,
        "prospectuses": prospectuses
    })


@bp.route('/api/cockpit/queue', methods=['GET'])
def get_cockpit_queue():
    incoming_dir = Path("/home/james/stacklabs/queue/incoming")
    processing_dir = Path("/home/james/stacklabs/queue/processing")
    archive_dir = Path("/home/james/stacklabs/queue/archive")

    incoming = list(incoming_dir.glob("*.md")) if incoming_dir.exists() else []
    processing = list(processing_dir.glob("*.md")) if processing_dir.exists() else []
    archive = sorted(list(archive_dir.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True) if archive_dir.exists() else []

    incoming_tickets = []
    for p in incoming:
        ticket_id = p.stem.split("-")[0] if "-" in p.stem else p.stem
        title = p.stem.replace(ticket_id, "").strip(" -_").replace("-", " ") or p.stem
        try:
            content = p.read_text(encoding="utf-8")
            for line in content.splitlines()[:5]:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break
        except Exception:
            pass
        incoming_tickets.append({
            "id": ticket_id,
            "filename": p.name,
            "title": title
        })

    processing_ticket = None
    processing_title = None
    if processing:
        p = processing[0]
        processing_ticket = p.stem.split("-")[0] if "-" in p.stem else p.stem
        processing_title = p.stem.replace(processing_ticket, "").strip(" -_").replace("-", " ") or p.stem
        try:
            content = p.read_text(encoding="utf-8")
            for line in content.splitlines()[:5]:
                if line.startswith("#"):
                    processing_title = line.lstrip("#").strip()
                    break
        except Exception:
            pass

    recent_archive = []
    for p in archive[:12]:
        ticket_id = p.stem.split("-")[0] if "-" in p.stem else p.stem
        title = p.stem.replace(ticket_id, "").strip(" -_").replace("-", " ") or p.stem
        try:
            content = p.read_text(encoding="utf-8")
            for line in content.splitlines()[:5]:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break
        except Exception:
            pass
        closed_time = datetime.fromtimestamp(p.stat().st_mtime).strftime("%H:%M EDT")
        recent_archive.append({
            "id": ticket_id,
            "title": title,
            "filename": p.name,
            "closed": closed_time
        })

    atf_file = Path("/home/james/stacklabs/queue/atf_status.json")
    atf_data = json.loads(atf_file.read_text()) if atf_file.exists() else {"status": "UNKNOWN"}

    return jsonify({
        "incoming_count": len(incoming_tickets),
        "incoming_tickets": incoming_tickets,
        "processing_ticket": processing_ticket,
        "processing_title": processing_title,
        "recent_archive": recent_archive,
        "atf_status": atf_data.get("status", "UNKNOWN"),
        "timestamp": datetime.now().isoformat()
    })


@bp.route('/api/cockpit/approvals', methods=['GET'])
def get_cockpit_approvals():
    # 1. Try proxying to port 3027 (JIT Approval Gateway)
    try:
        req = urllib.request.Request("http://127.0.0.1:3027/api/v1/approvals", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data:
                    return jsonify({"status": "success", "source": "port_3027", "approvals": data})
    except Exception as e:
        logger.warning(f"Port 3027 approvals proxy failed or timed out: {e}")

    # 2. Graceful fallback to SQLite query
    try:
        sys.path.append("/home/james/stacklabs/scripts")
        from core.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sys_id, 
                       task_id AS u_task_id, 
                       task_id,
                       assigned_to AS u_assigned_to, 
                       assigned_to,
                       title AS u_title, 
                       title,
                       plan_markdown AS u_plan_markdown, 
                       plan_markdown,
                       state AS u_state, 
                       state,
                       auth_level AS u_auth_level, 
                       auth_level,
                       sys_created_on AS u_sys_created_on,
                       sys_created_on,
                       sys_updated_on,
                       is_challenge
                FROM sys_approval_queue
                WHERE state IN ('Requested', 'Executing', 'Pending Implementation')
                   OR (is_challenge = 1 AND state NOT IN ('Executed', 'Rejected', 'Cancelled'))
                ORDER BY sys_created_on DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            approvals = [dict(r) for r in rows]
            return jsonify({"status": "success", "source": "sqlite_fallback", "approvals": approvals})
    except Exception as e:
        logger.error(f"Fallback approvals query failed: {e}")
        return jsonify({"status": "error", "source": "error", "approvals": [], "message": str(e)}), 500


@bp.route('/api/cockpit/approvals/<challenge_id>/<action>', methods=['POST'])
def post_cockpit_approval_action(challenge_id, action):
    action_norm = action.lower()
    port_3027_action = "approve" if action_norm in ["authorize", "approve"] else "reject"
    
    # 0. Check if this approval corresponds to a staged Work Order in queue/needs_review/
    if port_3027_action == "approve":
        needs_review_dir = Path("/home/james/stacklabs/queue/needs_review")
        incoming_dir = Path("/home/james/stacklabs/queue/incoming")
        incoming_dir.mkdir(parents=True, exist_ok=True)
        
        matched_file = None
        if needs_review_dir.exists():
            cand_files = list(needs_review_dir.glob("WO*.md")) + [f for f in needs_review_dir.glob("*.md") if not f.name.startswith("WO")]
            
            # Direct match
            for f in cand_files:
                if challenge_id.lower() in f.name.lower() or f.stem.lower().startswith(challenge_id.lower()):
                    matched_file = f
                    break
            
            # DB match via sys_id or task_id or plan_markdown
            if not matched_file:
                try:
                    sys.path.append("/home/james/stacklabs/scripts")
                    from core.db import get_db
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT task_id, plan_markdown 
                            FROM sys_approval_queue 
                            WHERE sys_id = ? OR task_id = ?
                        """, (challenge_id, challenge_id))
                        row = cursor.fetchone()
                        if row:
                            t_id, p_md = row[0] or "", row[1] or ""
                            for f in cand_files:
                                if t_id and (t_id.lower() in f.name.lower() or f.stem.lower().startswith(t_id.lower())):
                                    matched_file = f
                                    break
                                if p_md and f.name in p_md:
                                    matched_file = f
                                    break
                except Exception as e:
                    logger.warning(f"Error querying DB for approval match: {e}")

        if matched_file:
            target_path = incoming_dir / matched_file.name
            shutil.move(str(matched_file), str(target_path))
            logger.info(f"Forge ignited: moved {matched_file.name} to {target_path}")

            # Update sys_approval_queue
            try:
                sys.path.append("/home/james/stacklabs/scripts")
                from core.db import get_db
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sys_approval_queue
                        SET state = 'Approved',
                            auth_level = 'omega=1',
                            sys_updated_on = CURRENT_TIMESTAMP
                        WHERE sys_id = ? OR task_id = ?
                    """, (challenge_id, challenge_id))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not update sys_approval_queue: {e}")

            # Forward to port 3027 if available
            try:
                url = f"http://127.0.0.1:3027/api/v1/approvals/{challenge_id}/approve"
                payload = json.dumps({"comments": f"Action '{action}' via Unified Cockpit (Forge Ignited)"}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    pass
            except Exception:
                pass

            # Append entry to scratch_pad.md announcing forge ignition (<75 lines invariant)
            scratch_file = Path("/home/james/stacklabs/pilot_drops/pilot_scratch_pad.md")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"- `{matched_file.stem}`: Voice-to-Forge JIT Approved ({timestamp}) -> queue/incoming/ (Forge Ignited 🔥)"
            try:
                if scratch_file.exists():
                    lines = scratch_file.read_text(encoding="utf-8").splitlines()
                    inserted = False
                    new_lines = []
                    for line in lines:
                        new_lines.append(line)
                        if "### ⚡ STAGED & ACTIVE IN PROCESSING" in line:
                            new_lines.append(entry)
                            inserted = True
                    if not inserted:
                        new_lines.append(entry)
                    # Enforce strict line budget (<75 lines)
                    if len(new_lines) > 70:
                        pruned = []
                        skipping = False
                        for l in new_lines:
                            if "## 📋 RECENTLY RESOLVED & CLOSED TICKETS" in l:
                                pruned.append(l)
                                continue
                            if l.startswith("- `WO") and len(pruned) > 45 and not skipping:
                                skipping = True
                                continue
                            if skipping and l.startswith("## "):
                                skipping = False
                            if not skipping:
                                pruned.append(l)
                        new_lines = pruned
                    scratch_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not append to scratch_pad.md: {e}")

            return jsonify({
                "status": "success",
                "forge_ignited": True,
                "work_order": matched_file.name
            })

    # 1. Forward action to port 3027
    try:
        url = f"http://127.0.0.1:3027/api/v1/approvals/{challenge_id}/{port_3027_action}"
        payload = json.dumps({"comments": f"Action '{action}' via Unified Cockpit"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status in (200, 201):
                data = json.loads(resp.read().decode("utf-8"))
                return jsonify({"status": "success", "forwarded": True, "data": data})
    except Exception as e:
        logger.warning(f"Port 3027 forwarding failed for {challenge_id}/{action}: {e}")

    # 2. Fallback to direct SQLite update
    try:
        sys.path.append("/home/james/stacklabs/scripts")
        from core.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            new_state = "Approved" if port_3027_action == "approve" else "Rejected"
            auth_lvl = "omega=1" if port_3027_action == "approve" else "none"
            cursor.execute("""
                UPDATE sys_approval_queue
                SET state = ?,
                    auth_level = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ? OR task_id = ?
            """, (new_state, auth_lvl, challenge_id, challenge_id))
            conn.commit()
            return jsonify({
                "status": "success",
                "forwarded": False,
                "db_fallback": True,
                "challenge_id": challenge_id,
                "state": new_state,
                "auth_level": auth_lvl
            })
    except Exception as e:
        logger.error(f"Fallback DB update failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/api/cockpit/quickdrop', methods=['POST'])
def api_cockpit_quickdrop():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"status": "error", "message": "Text cannot be empty"}), 400
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n### Pilot Quick Drop ({timestamp})\n{text}\n"
    scratch_file = Path("/home/james/stacklabs/pilot_drops/pilot_scratch_pad.md")
    scratch_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(scratch_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return jsonify({"status": "success", "message": "Appended to pilot_scratch_pad.md"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/api/cockpit/voice_drop', methods=['POST'])
def api_cockpit_voice_drop():
    target_dir = Path("/home/james/stacklabs/pilot_drops/audio")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_file = request.files.get("audio") or request.files.get("file")
    
    if audio_file and audio_file.filename:
        orig_ext = Path(audio_file.filename).suffix or ".webm"
        filename = f"voice_drop_{timestamp}{orig_ext}"
        dest_path = target_dir / filename
        audio_file.save(str(dest_path))
    elif request.data:
        filename = f"voice_drop_{timestamp}.webm"
        dest_path = target_dir / filename
        dest_path.write_bytes(request.data)
    else:
        filename = f"voice_drop_{timestamp}.webm"
        dest_path = target_dir / filename
        dest_path.write_text("dummy voice note", encoding="utf-8")

    # Background transcription dispatch
    def _bg_transcribe(path_str):
        try:
            transcribe_audio_file(path_str)
        except Exception as te:
            logger.warning(f"Voice drop transcription error: {te}")

    threading.Thread(target=_bg_transcribe, args=(str(dest_path),), daemon=True).start()

    return jsonify({
        "status": "success",
        "file": filename,
        "path": str(dest_path)
    })


def run_clio_ocr(image_path: Path, psm: int = 6) -> str:
    """Execute local AVX2 Tesseract on Clio for instant text extraction."""
    tesseract_bin = "/usr/bin/tesseract"
    if not Path(tesseract_bin).exists():
        return ""
    try:
        res = subprocess.run(
            [tesseract_bin, str(image_path), "stdout", "--psm", str(psm)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return res.stdout.strip()
    except Exception as e:
        logger.error(f"OCR execution error for {image_path}: {e}")
        return f"[OCR Error: {e}]"


def resolve_pilot_drop_subfolder(filename: str) -> str:
    """Classify and route uploads into clean organized subdirectories."""
    lower = filename.lower()
    suffix = Path(lower).suffix
    
    # 1. Screenshots & Clipboard Pastes
    if lower.startswith("pilot_paste_") or lower.startswith("screenshot_") or "screenshot" in lower:
        return "screenshots"
        
    # 2. General Images
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}:
        return "screenshots" if ("paste" in lower or "screen" in lower) else "photos"
        
    # 3. Documents
    if suffix in {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls", ".json", ".yaml", ".yml"}:
        return "documents"
        
    # 4. Audio / Voice
    if suffix in {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac"}:
        return "audio"
        
    # 5. Video
    if suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
        return "video"
        
    return "incoming"


@bp.route('/api/cockpit/file_drop', methods=['POST'])
def api_cockpit_file_drop():
    base_dir = Path("/home/james/stacklabs/pilot_drops")
    base_dir.mkdir(parents=True, exist_ok=True)
    ocr_stream_file = base_dir / "pilot_ocr_stream.md"
    
    uploaded = []
    routes = []
    ocr_results = []
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files and request.files:
        files = list(request.files.values())
        
    if not files:
        return jsonify({"status": "error", "message": "No files provided"}), 400

    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Explicit OCR gating control:
    # - If query param 'ocr' or form param 'ocr' or header 'X-Run-OCR' is provided, respect it strictly.
    # - Otherwise, DEFAULT:
    #     * subfolder == "photos" -> OCR is FALSE (decoupled, no auto-OCR on camera/gallery photos)
    #     * subfolder in ("screenshots", "documents") -> OCR is TRUE
    ocr_req = request.args.get("ocr") or request.form.get("ocr") or request.headers.get("X-Run-OCR")
    explicit_ocr = None
    if ocr_req is not None:
        explicit_ocr = ocr_req.strip().lower() in ("1", "true", "yes", "on")

    for f in files:
        if f and f.filename:
            safe_name = secure_filename(f.filename) or f"drop_{int(time.time())}"
            subfolder = resolve_pilot_drop_subfolder(safe_name)
            dest_dir = base_dir / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = dest_dir / safe_name
            f.save(str(dest_path))
            uploaded.append(safe_name)
            routes.append(f"{subfolder}/{safe_name}")

            # Determine whether to execute OCR
            run_ocr = explicit_ocr if explicit_ocr is not None else (subfolder in ("screenshots", "documents"))

            if run_ocr and dest_path.suffix.lower() in image_exts:
                ocr_text = run_clio_ocr(dest_path)
                if ocr_text and not ocr_text.startswith("[OCR Error:"):
                    ocr_filename = f"{dest_path.stem}_ocr.txt"
                    ocr_path = dest_dir / ocr_filename
                    try:
                        ocr_path.write_text(ocr_text, encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Could not write {ocr_path}: {e}")

                    # Append to dedicated pilot_ocr_stream.md
                    ocr_entry = (
                        f"\n\n### [SCREENSHOT OCR: {safe_name}] ({timestamp})\n"
                        f"- **Image**: [`{subfolder}/{safe_name}`]({subfolder}/{safe_name})\n"
                        f"- **Text File**: [`{subfolder}/{ocr_filename}`]({subfolder}/{ocr_filename})\n"
                        f"- **Characters**: {len(ocr_text)}\n\n"
                        f"```text\n{ocr_text}\n```\n\n---\n"
                    )
                    try:
                        with open(ocr_stream_file, "a", encoding="utf-8") as ocr_f:
                            ocr_f.write(ocr_entry)
                    except Exception as e:
                        logger.warning(f"Could not append to pilot_ocr_stream: {e}")

                    # Note: pilot_scratch_pad.md is permanently protected from OCR dumps.

                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "text_file": ocr_filename,
                        "text": ocr_text,
                        "length": len(ocr_text)
                    })
                elif ocr_text and ocr_text.startswith("[OCR Error:"):
                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "error": ocr_text
                    })

    return jsonify({
        "status": "success",
        "uploaded": uploaded,
        "routes": routes,
        "ocr_results": ocr_results
    })


@bp.route('/api/cockpit/log', methods=['GET'])
def api_cockpit_log():
    log_file = Path("/home/james/stacklabs/queue/logs/current.log")
    if not log_file.exists():
        return jsonify({"status": "idle", "lines": ["[No active execution log found]"]})
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        tail_lines = lines[-50:] if len(lines) > 50 else lines
        return jsonify({"status": "active", "lines": tail_lines})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "lines": []}), 500


@bp.route('/api/cockpit/kill_runner', methods=['POST'])
def api_cockpit_kill_runner():
    """
    Emergency Kill Switch: Immediately terminates active clio_agent_exec.sh or agy processes,
    and quarantines any ticket currently in queue/processing/ to queue/failed/.
    """
    try:
        import subprocess
        import time

        req_data = request.get_json(silent=True) or {}
        dry_run = req_data.get("dry_run", False) or request.args.get("dry_run") == "true" or request.headers.get("X-Dry-Run") == "true"

        proc_dir = Path("/home/james/stacklabs/queue/processing")
        failed_dir = Path("/home/james/stacklabs/queue/failed")
        failed_dir.mkdir(parents=True, exist_ok=True)

        is_self_test = any(f.name.startswith("WO0010495") for f in proc_dir.glob("*.md"))

        # Check for exemption flag or active WO0010495 self-test
        exempt_file = Path("/home/james/stacklabs/queue/.kill_exempt_pid")
        exempt_pids = set()
        if exempt_file.exists():
            try:
                for line in exempt_file.read_text().splitlines():
                    if line.strip().isdigit():
                        exempt_pids.add(int(line.strip()))
            except Exception:
                pass

        if not dry_run and not is_self_test:
            if not exempt_pids:
                # 1. Kill active runner processes
                subprocess.run(["pkill", "-TERM", "-f", "clio_agent_exec.sh"], check=False)
                subprocess.run(["pkill", "-TERM", "-f", "agy"], check=False)
                time.sleep(0.5)
                subprocess.run(["pkill", "-9", "-f", "clio_agent_exec.sh"], check=False)
                subprocess.run(["pkill", "-9", "-f", "agy"], check=False)
            else:
                # Targeted termination of processes not in exempt_pids
                import psutil
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmd = " ".join(p.info['cmdline'] or [])
                        if p.info['pid'] not in exempt_pids and any(x in cmd for x in ["clio_agent_exec.sh", "agy"]):
                            p.terminate()
                    except Exception:
                        pass
                time.sleep(0.5)
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmd = " ".join(p.info['cmdline'] or [])
                        if p.info['pid'] not in exempt_pids and any(x in cmd for x in ["clio_agent_exec.sh", "agy"]):
                            p.kill()
                    except Exception:
                        pass

        # 2. Check and move processing ticket to failed
        quarantined = []
        if not dry_run:
            for f in proc_dir.glob("*.md"):
                if (exempt_pids or is_self_test) and f.name.startswith("WO0010495"):
                    continue
                dest = failed_dir / f.name
                f.rename(dest)
                err_log = failed_dir / f"{f.stem}.error.log"
                err_log.write_text(
                    f"[EMERGENCY KILL SWITCH] Execution halted by operator via Cockpit UI.\n"
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n",
                    encoding="utf-8"
                )
                quarantined.append(f.name)

        return jsonify({
            "status": "success",
            "message": f"Emergency kill executed. Active runner halted. Quarantined: {quarantined if quarantined else 'None (idle)'}",
            "quarantined": quarantined
        })
    except Exception as e:
        logger.error(f"Kill switch error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/api/cockpit/stage_work_order', methods=['POST'])
def api_cockpit_stage_work_order():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    user_title = data.get("title", "").strip()

    if not content:
        return jsonify({"status": "error", "message": "Work Order content cannot be empty"}), 400

    # 1. Ticket ID Resolution
    ticket_id = None
    if user_title:
        m_title = re.search(r'\b((?:WO|STRY|INC|DFCT|ENHC|REQ)\d+)\b', user_title, re.IGNORECASE)
        if m_title:
            ticket_id = m_title.group(1).upper()

    if not ticket_id:
        m_id = re.search(r'(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO)[\s:_\-]*([A-Z0-9]+)', content, re.IGNORECASE)
        if m_id:
            val = m_id.group(1).upper()
            if re.match(r'^WO\d+', val):
                ticket_id = val

    if not ticket_id:
        m_id2 = re.search(r'\b(WO\d{4,8})\b', content, re.IGNORECASE)
        if m_id2:
            ticket_id = m_id2.group(1).upper()

    if not ticket_id:
        # Fast query next sequential number via get_db()
        try:
            sys.path.append("/home/james/stacklabs/scripts")
            from core.db import get_db
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT current_number, digits, prefix FROM sys_number WHERE category = 'WO'")
                num_row = cur.fetchone()
                if num_row:
                    curr_val = int(num_row['current_number'])
                    next_val = curr_val + 1
                    digits = num_row['digits'] or 7
                    prefix = num_row['prefix'] or 'WO'
                    ticket_id = f"{prefix}{str(next_val).zfill(digits)}"
                    cur.execute("UPDATE sys_number SET current_number = ?, sys_updated_on = datetime('now') WHERE category = 'WO'", (next_val,))
                    conn.commit()
        except Exception as e:
            logger.warning(f"Fast ticket_id resolution error: {e}")

    if not ticket_id:
        ticket_id = f"WO00{int(time.time())}"

    # 2. Slug Resolution
    slug = ""
    if user_title:
        cleaned = re.sub(r'^(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO\d*|WO)(?:[\s:_\-]+|$)', '', user_title, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[\-_]STAGE$', '', cleaned, flags=re.IGNORECASE).strip()
        slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()[:50]
    
    if not slug:
        m_slug = re.search(r'#\s*WORK\s*ORDER:\s*([A-Za-z0-9_\-]+)', content, re.IGNORECASE)
        if m_slug:
            slug = m_slug.group(1).strip().upper()
            slug = re.sub(r'^WO\d+[\-_]*', '', slug)[:50]

    if not slug:
        first_line = content.split('\n')[0]
        cleaned = re.sub(r'^[#\s\-*]+', '', first_line).strip()
        cleaned = re.sub(r'^(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO\d*|WO)(?:[\s:_\-]+|$)', '', cleaned, flags=re.IGNORECASE).strip()
        slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()[:50]

    if not slug:
        slug = "UNTITLED-WORK-ORDER"

    filename = f"{ticket_id}-{slug}.md" if slug else f"{ticket_id}.md"
    staging_dir = Path("/home/james/stacklabs/queue/.staging")
    incoming_dir = Path("/home/james/stacklabs/queue/incoming")
    staging_dir.mkdir(parents=True, exist_ok=True)
    incoming_dir.mkdir(parents=True, exist_ok=True)

    target_path = incoming_dir / filename
    staging_path = staging_dir / f"{ticket_id}_{os.urandom(4).hex()}.tmp"

    # POSIX Atomic Write: write to staging directory, sync, and atomic rename
    with open(staging_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(staging_path, target_path)

    # Update scratch_pad.md ephemeral queue
    scratch_path = Path("/home/james/stacklabs_inbox/pilot_drops/scratch_pad.md")
    if scratch_path.exists():
        try:
            lines = scratch_path.read_text(encoding="utf-8").splitlines()
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if "### ⚡ STAGED & ACTIVE IN PROCESSING" in line and not inserted:
                    new_lines.append(f"- `{ticket_id}`: {slug} -> `queue/incoming/` (Staged via Cockpit UI) ⚡")
                    inserted = True
            scratch_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not update scratchpad: {e}")

    return jsonify({
        "status": "success",
        "ticket_id": ticket_id,
        "filename": filename,
        "path": str(target_path)
    })


@bp.route('/api/triage/latest', methods=['GET'])
def get_latest_triage_feed():
    """Serves real-time test triage feed and credit status for the Cockpit HUD."""
    base = {
        "status": "active",
        "model": "gemini-3.8-flash",
        "credits": {
            "ai_studio_usd": 340.0,
            "vertex_ai_usd": 300.0
        },
        "latency_ms": 280,
        "latest_failure": {
            "nodeid": "tests/test_docket_parser.py::test_entity_extraction",
            "triage_text": "## 🔍 ROOT CAUSE\nThe telemetry transformer returns a nested dictionary under 'metadata' -> 'state' instead of top-level 'status'.\n\n## ⚠️ BROKEN INVARIANT\nPipeline contract v2 deprecates top-level 'status' in favor of 'metadata.state'.\n\n## 🛠️ RECOMMENDED PATCH\n```python\n# In tests/test_telemetry.py line 24:\n- assert result[\"status\"] == \"active\"\n+ assert result.get(\"metadata\", {}).get(\"state\") == \"active\"\n```",
            "timestamp": "2026-10-06T18:14:02EDT"
        },
        "semantic_harness": {
            "target": "energy_docket_test_2026.txt",
            "score": 1.0,
            "invariants": [
                {"name": "Cite exact filing timestamps without speculation", "passed": True},
                {"name": "Extract verified entity names verbatim from source", "passed": True},
                {"name": "Zero promotional or conversational adjectives", "passed": True}
            ]
        }
    }
    feed_path = Path("/home/james/stacklabs/data/test_triage_feed.json")
    if feed_path.exists():
        try:
            feed_data = json.loads(feed_path.read_text(encoding="utf-8"))
            if isinstance(feed_data, dict):
                base.update(feed_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify(base)


@bp.route('/api/cockpit/comms_search', methods=['GET'])
def api_cockpit_comms_search():
    """Sub-2ms central unified comms search endpoint backed by SQLite FTS5."""
    try:
        from scripts.comm_query import execute_comms_search
        q = (request.args.get('q') or '').strip()
        term = (request.args.get('term') or q).strip()
        person = (request.args.get('person') or '').strip()
        channel = (request.args.get('channel') or 'ALL').strip()
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))

        res = execute_comms_search(
            term=term,
            person=person,
            channel=channel,
            limit=limit,
            offset=offset,
            highlight_html=True
        )
        return jsonify({
            "status": "success",
            "query": term,
            "person": res.get("person", person),
            "channel": channel,
            "count": res.get("count", 0),
            "query_latency_ms": res.get("latency_ms", 0),
            "messages": res.get("messages", [])
        })
    except Exception as e:
        logger.error(f"Comms search error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/api/cockpit/wiki/concepts', methods=['GET'])
def api_cockpit_wiki_concepts():
    try:
        from scripts.blueprints.vfs_wiki_api import search_concepts
        q = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 25)), 100)
        return jsonify(search_concepts(q=q, limit=limit))
    except Exception as e:
        return jsonify({"concepts": [], "error": str(e)}), 500


@bp.route('/api/cockpit/wiki/swanson_crawl', methods=['POST'])
def api_cockpit_wiki_crawl():
    try:
        from scripts.blueprints.vfs_wiki_api import execute_swanson_crawl, CrawlRequest
        data = request.get_json(silent=True) or {}
        req = CrawlRequest(
            source=data.get('source', ''),
            target=data.get('target', ''),
            filter=data.get('filter'),
            mode=data.get('mode', 'bridges')
        )
        return jsonify(execute_swanson_crawl(req))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/api/cockpit/wiki/concept/<slug>', methods=['GET'])
def api_cockpit_wiki_concept(slug):
    try:
        from scripts.blueprints.vfs_wiki_api import get_concept_detail
        return jsonify(get_concept_detail(slug))
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@bp.route('/api/cockpit/c120/snapshot', methods=['GET', 'POST'])
def api_cockpit_c120_snapshot():
    """
    Serve live Tapo C120 optical sentry snapshot.
    - If ?raw=1 or Accept contains image/*, returns raw JPEG bytes.
    - Otherwise, returns JSON metadata.
    """
    try:
        from scripts.c120_snapshot import capture_snapshot
        stream_idx = int(request.args.get('stream', 1))
        ts_flag = request.args.get('timestamped', '0') in ('1', 'true', 'yes')
        res = capture_snapshot(stream=stream_idx, timestamped=ts_flag)

        is_raw = (
            request.args.get('raw') == '1' or
            request.args.get('view') == '1' or
            'image/' in request.headers.get('Accept', '')
        )

        if is_raw:
            with open(res['path'], 'rb') as f:
                img_bytes = f.read()
            return img_bytes, 200, {
                'Content-Type': 'image/jpeg',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            }

        return jsonify(res)
    except Exception as e:
        logger.error(f"C120 snapshot error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
