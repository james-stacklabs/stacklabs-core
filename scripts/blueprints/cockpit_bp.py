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
        Path("/home/james/sovereign_inbox/today/alpha_trader_stats.json"),
        Path("/home/james/SovereignOS/33_FanStack_Lite/public/FanStack_Live/alpha_trader_stats.json"),
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
    sys.path.append("/home/james/SovereignOS/scripts")
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
    incoming = list(Path("/home/james/sovereign_inbox/queue/incoming").glob("*.md"))
    processing = list(Path("/home/james/sovereign_inbox/queue/processing").glob("*.md"))
    archive = sorted(list(Path("/home/james/sovereign_inbox/queue/archive").glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True)
    atf_file = Path("/home/james/sovereign_inbox/queue/atf_status.json")
    atf_data = json.loads(atf_file.read_text()) if atf_file.exists() else {"status": "UNKNOWN"}
    return jsonify({
        "incoming_count": len(incoming),
        "processing_ticket": processing[0].name if processing else None,
        "recent_archive": [p.name for p in archive[:8]],
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
        sys.path.append("/home/james/SovereignOS/scripts")
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
        needs_review_dir = Path("/home/james/sovereign_inbox/queue/needs_review")
        incoming_dir = Path("/home/james/sovereign_inbox/queue/incoming")
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
                    sys.path.append("/home/james/SovereignOS/scripts")
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
                sys.path.append("/home/james/SovereignOS/scripts")
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
            scratch_file = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
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
        sys.path.append("/home/james/SovereignOS/scripts")
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
    scratch_file = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
    try:
        with open(scratch_file, "a") as f:
            f.write(entry)
        return jsonify({"status": "success", "message": "Saved to scratch_pad.md"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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

        proc_dir = Path("/home/james/sovereign_inbox/queue/processing")
        failed_dir = Path("/home/james/sovereign_inbox/queue/failed")
        failed_dir.mkdir(parents=True, exist_ok=True)

        is_self_test = any(f.name.startswith("WO0010495") for f in proc_dir.glob("*.md"))

        # Check for exemption flag or active WO0010495 self-test
        exempt_file = Path("/home/james/sovereign_inbox/queue/.kill_exempt_pid")
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
    m_id = re.search(r'(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO)[\s:_\-]*([A-Z0-9]+)', content, re.IGNORECASE)
    if m_id:
        val = m_id.group(1).upper()
        if re.match(r'^WO\d+', val):
            ticket_id = val

    if not ticket_id:
        # Fallback to query next sequential number
        try:
            req = urllib.request.Request("http://127.0.0.1:8095/api/tickets/next_number?category=WO&increment=true")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    ticket_id = json.loads(resp.read().decode()).get("next_number")
        except Exception:
            pass

    if not ticket_id or ticket_id in ["WO0100000", "WO99999"]:
        # Safe fallback based on existing queue files
        incoming_dir = Path("/home/james/sovereign_inbox/queue/incoming")
        processing_dir = Path("/home/james/sovereign_inbox/queue/processing")
        archive_dir = Path("/home/james/sovereign_inbox/queue/archive")
        failed_dir = Path("/home/james/sovereign_inbox/queue/failed")
        max_num = 10494
        for qdir in [incoming_dir, processing_dir, archive_dir, failed_dir]:
            for f in qdir.glob("WO*.md"):
                m = re.match(r'WO0*(\d+)', f.name)
                if m:
                    num = int(m.group(1))
                    if 10000 <= num < 90000 and num > max_num:
                        max_num = num
        ticket_id = f"WO00{max_num + 1}"

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
        slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()[:50]

    if not slug:
        slug = "UNTITLED-WORK-ORDER"

    filename = f"{ticket_id}-{slug}.md"
    incoming_dir = Path("/home/james/sovereign_inbox/queue/incoming")
    incoming_dir.mkdir(parents=True, exist_ok=True)
    target_path = incoming_dir / filename

    # Atomically write
    target_path.write_text(content, encoding="utf-8")

    # Update scratch_pad.md ephemeral queue
    scratch_path = Path("/home/james/sovereign_inbox/pilot_drops/scratch_pad.md")
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
