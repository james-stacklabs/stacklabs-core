import asyncio
import websockets
import json
import subprocess
import os
import io
import time
import zipfile
import sqlite3
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pybaseball import statcast_single_game
from sqlalchemy import create_engine


from schema_enforcer import validate_payload
from protocol_shifter import shift_protocol
from live_context_writer import append_live_context

app = Flask(__name__)
CORS(app)

DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'
engine = create_engine(f'sqlite:///{DB_PATH}')
table_name = 'statcast_pitches'

async def notify_mesh(ws_action="SYNC_DB_PERSONAS", custom_payload=None):
    """
    Pings the central Mesh relay (Port 8008) to trigger hot-reloads and context injections 
    in the chatbots without requiring a system restart.
    """
    try:
        async with websockets.connect('ws://127.0.0.1:8008') as ws:
            # 1. Sync DB if we touched protocol shifter
            if ws_action == "SYNC_DB_PERSONAS":
                await ws.send(json.dumps({'action': 'SYNC_DB_PERSONAS'}))
                await asyncio.sleep(0.5)
            
            # 2. Push context/actions to the chat engine directly
            if custom_payload:
                await ws.send(json.dumps(custom_payload))
                
    except Exception as e:
        print(f"[MESH ERROR] Unable to ping Port 8008: {e}")

@app.route('/api/admin/override', methods=['POST'])
def handle_override():
    """
    Primary endpoint for ingesting Admin Overrides.
    Expects a JSON payload detailing the required simulation shifts.
    """
    try:
        payload = request.get_json()
        
        # 1. Enforce Schema strictness
        validate_payload(payload)
        
        # 2. Extract Data
        source = payload.get("source", "UNKNOWN")
        target_nodes = payload.get("target_nodes", "ALL")
        constraints = payload.get("constraints_toggle", {})
        global_ctx = payload.get("global_context", "")
        
        # 3. DB Modification
        action = constraints.get("action", "none")
        protocol_str = constraints.get("protocol_string", "")
        
        new_state = payload.get("new_state", "")
        if new_state == "RESTORE_BASELINE":
            action = "restore_baseline"
            protocol_str = ""
            
        shift_protocol(action, protocol_str, target_nodes)

        # 4. Context Log Serialization
        append_live_context(global_ctx, source)
        
        # 5. Push to Live Simulation Mesh
        mesh_payload = None
        if global_ctx:
            mesh_payload = {'type': 'update_context', 'text': f"[{source} OVERRIDE]: {global_ctx}", 'target_nodes': target_nodes}
            
        asyncio.run(notify_mesh(ws_action="SYNC_DB_PERSONAS" if action != "none" else None, custom_payload=mesh_payload))
        
        return jsonify({
            "status": "success", 
            "message": "Admin Override executed and propagated down to the mesh layer."
        }), 200

    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal System Failure: {e}"}), 500

@app.route('/api/admin/download_rom', methods=['POST'])
def handle_download_rom():
    try:
        payload = request.get_json()
        game_pk = payload.get("game_pk")
        if not game_pk:
            return jsonify({"status": "error", "message": "game_pk is required"}), 400

        print(f"[API] Downloading ROM for game_pk: {game_pk}")
        df = statcast_single_game(game_pk)
        
        if df is not None and not df.empty:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            return jsonify({
                "status": "success",
                "message": f"Successfully pulled and stored {len(df)} pitches for Game PK {game_pk}"
            }), 200
        else:
            return jsonify({"status": "error", "message": f"No data returned for Game PK {game_pk}"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": f"Download Failed: {e}"}), 500

@app.route('/api/admin/ignite_sim', methods=['POST'])
def handle_ignite_sim():
    try:
        payload = request.get_json()
        game_pk = payload.get("game_pk")
        speed = payload.get("speed", 1.0)
        
        if not game_pk:
            return jsonify({"status": "error", "message": "game_pk is required"}), 400

        print(f"[API] Igniting Simulation for {game_pk} at {speed}x speed")
        
        cmd = [
            "/home/james/stacklabs/.venv/bin/python3",
            "/home/james/stacklabs/scripts/fanstack_historical_injector.py",
            "--game_pk", str(game_pk),
            "--speed", str(speed)
        ]
        
        # Launching subprocess and decoupling so the API doesn't block
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return jsonify({
            "status": "success",
            "message": f"Ignited historical injector for game {game_pk} at speed {speed}x"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to ignite simulation: {e}"}), 500

@app.route('/api/admin/burn_leaderboard', methods=['GET'])
def get_burn_leaderboard():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT persona, SUM(burn_score) as score, SUM(is_tko) as tkos
            FROM burn_events
            WHERE burn_date = date('now')
            GROUP BY persona
            ORDER BY score DESC
        """)
        rows = cursor.fetchall()
        
        ranked = []
        total_burns = 0
        for r in rows:
            ranked.append({
                "persona": r["persona"],
                "score": r["score"],
                "tkos": r["tkos"]
            })
            total_burns += r["score"]
            
        conn.close()
        return jsonify({
            "status": "success",
            "leaderboard": ranked,
            "total_burns": total_burns
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Leaderboard failure: {e}"}), 500

@app.route('/api/burn-book/daily', methods=['GET'])
def get_burn_book_daily():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT persona, SUM(burn_score) as score, SUM(is_tko) as tkos
            FROM burn_events
            WHERE burn_date = date('now')
            GROUP BY persona
            ORDER BY score DESC
        """)
        rows = cursor.fetchall()
        
        ranked = []
        total_burns = 0
        for r in rows:
            ranked.append({
                "persona": r["persona"],
                "score": r["score"],
                "tkos": r["tkos"]
            })
            total_burns += r["score"]
            
        conn.close()
        return jsonify({
            "status": "success",
            "leaderboard": ranked,
            "total_burns": total_burns
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/burn-book/persona/<username>', methods=['GET'])
def get_burn_book_persona(username):
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT persona, SUM(burn_score) as total_score, SUM(is_tko) as tkos, MAX(heat_index) as heat
            FROM burn_events
            WHERE burn_date = date('now')
            GROUP BY persona
            ORDER BY total_score DESC
        """)
        standings = cursor.fetchall()
        
        today_stats = {
            "total_burn": 0,
            "heat_index": 0,
            "tko_count": 0,
            "rank": 0
        }
        
        for idx, row in enumerate(standings):
            if row["persona"] == username:
                today_stats = {
                    "total_burn": row["total_score"],
                    "heat_index": row["heat"] or 0,
                    "tko_count": row["tkos"],
                    "rank": idx + 1
                }
                break
                
        cursor.execute("""
            SELECT sys_id, message, target_persona as target, burn_score as score, heat_index, is_tko, game_pk, created_at
            FROM burn_events
            WHERE persona = ? AND burn_date = date('now')
            ORDER BY created_at DESC
        """, (username,))
        burn_rows = cursor.fetchall()
        
        burns = []
        for b in burn_rows:
            burns.append({
                "sys_id": b["sys_id"],
                "message": b["message"],
                "target": b["target"],
                "score": b["score"],
                "heat_index": b["heat_index"],
                "is_tko": bool(b["is_tko"]),
                "game_pk": b["game_pk"],
                "created_at": b["created_at"]
            })
            
        conn.close()
        return jsonify({
            "persona": username,
            "today": today_stats,
            "burns": burns
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/burn-book/history', methods=['GET'])
def get_burn_book_history():
    try:
        days = request.args.get('days', default=30, type=int)
        persona = request.args.get('persona', default=None, type=str)
        
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if persona:
            cursor.execute("""
                SELECT archive_date, total_burn as score, heat_index, tko_count as tkos, top_burn
                FROM burn_daily_archive
                WHERE persona = ? AND archive_date >= date('now', ?)
                ORDER BY archive_date DESC
            """, (persona, f"-{days} days"))
            rows = cursor.fetchall()
            history = []
            for r in rows:
                history.append({
                    "date": r["archive_date"],
                    "score": r["score"],
                    "heat_index": r["heat_index"],
                    "tkos": r["tkos"],
                    "top_burn": r["top_burn"]
                })
            conn.close()
            return jsonify({
                "persona": persona,
                "days": days,
                "history": history
            }), 200
        else:
            cursor.execute("""
                SELECT persona, SUM(total_burn) as score, MAX(heat_index) as heat, SUM(tko_count) as tkos, MAX(top_burn) as top_burn
                FROM burn_daily_archive
                WHERE archive_date >= date('now', ?)
                GROUP BY persona
                ORDER BY score DESC
            """, (f"-{days} days",))
            rows = cursor.fetchall()
            leaders = []
            for r in rows:
                leaders.append({
                    "persona": r["persona"],
                    "score": r["score"],
                    "heat_index": r["heat"],
                    "tkos": r["tkos"],
                    "top_burn": r["top_burn"]
                })
            conn.close()
            return jsonify({
                "days": days,
                "leaders": leaders
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/burn-book/reset', methods=['POST'])
def reset_burn_book():
    try:
        import uuid
        from datetime import date
        
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute("""
            SELECT persona, SUM(burn_score) as total, 
                   MAX(heat_index) as heat,
                   SUM(is_tko) as tkos,
                   MAX(message) as top_burn
            FROM burn_events 
            WHERE burn_date = ?
            GROUP BY persona
            ORDER BY total DESC
        """, (today,))
        rows = cursor.fetchall()
        
        inserted = 0
        for row in rows:
            cursor.execute("""
                INSERT OR REPLACE INTO burn_daily_archive
                (sys_id, archive_date, persona, total_burn, heat_index, tko_count, top_burn)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (uuid.uuid4().hex, today, row["persona"], row["total"], row["heat"], row["tkos"], row["top_burn"]))
            inserted += 1
        
        conn.commit()
        conn.close()
        return jsonify({"status": "archived", "date": today, "personas": inserted}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/admin/flowmercial', methods=['POST'])
def handle_flowmercial():
    try:
        payload = request.get_json()
        action = payload.get("action", "start")
        ad_name = payload.get("ad_name", "Unknown Commercial")
        
        flag_file = '/tmp/sovereign_flow_pause.flag'
        
        if action == "start":
            with open(flag_file, 'w') as f:
                f.write("active")
            mesh_payload = {'type': 'update_context', 'text': f"[COMMERCIAL BREAK]: {ad_name} is playing aggressively on the screen. The broadcast is paused! All users MUST REACT!"}
            asyncio.run(notify_mesh(custom_payload=mesh_payload))
            return jsonify({"status": "success", "message": f"Flowmercial {ad_name} started. Telemetry paused."}), 200
        else:
            if os.path.exists(flag_file):
                os.remove(flag_file)
            mesh_payload = {'type': 'update_context', 'text': "[COMMERCIAL OVER]: MLB Broadcast is resuming..."}
            asyncio.run(notify_mesh(custom_payload=mesh_payload))
            return jsonify({"status": "success", "message": "Flowmercial stopped. Telemetry resumed."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Flowmercial execution failed: {e}"}), 500

@app.route('/api/admin/documents', methods=['GET'])
def list_documents():
    root_dir = '/home/james/stacklabs'
    documents = []
    
    exclude_dirs = {'.venv', 'node_modules', '__pycache__', '.git', '.next'}
    allowed_exts = {'.md', '.txt', '.json', '.pdf'}
    
    try:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            
            for file in filenames:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    full_path = os.path.join(dirpath, file)
                    stat = os.stat(full_path)
                    documents.append({
                        "path": full_path,
                        "name": file,
                        "last_modified": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
                        "timestamp": stat.st_mtime
                    })
                    
        documents.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify({"status": "success", "documents": documents}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/package', methods=['POST'])
def package_documents():
    try:
        payload = request.get_json()
        file_paths = payload.get("files", [])
        
        if not file_paths:
            return jsonify({"status": "error", "message": "No files selected"}), 400
            
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in file_paths:
                if os.path.exists(path):
                    arcname = os.path.relpath(path, '/home/james/stacklabs')
                    zf.write(path, arcname)
                    
        memory_file.seek(0)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'sovereign_payload_{timestamp}.zip'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/daily_prep', methods=['POST'])
def handle_daily_prep():
    try:
        print("[API] Initiating Daily Prep Sequence in background...")
        # Launch detached so the API can return 200 OK before it gets killed by restart_stack.sh
        subprocess.Popen(
            ["nohup", "bash", "/home/james/stacklabs/scripts/daily_prep.sh"],
            stdout=open('/tmp/daily_prep.log', 'w'),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setpgrp # Create a new process group so it survives when the parent dies
        )
        return jsonify({
            "status": "success",
            "message": "Daily prep initiated. The system will now cold-boot."
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to initiate daily prep: {e}"}), 500

@app.route('/', methods=['GET'])
def admin_ui():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sovereign FanStack Control Port</title>
        <style>
            body { background: #0A0A0A; color: #E0E0E0; font-family: system-ui, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #EAB308; }
            textarea { width: 100%; height: 400px; background: #1A1A1A; color: #00FF00; font-family: monospace; border: 1px solid #333; padding: 10px; box-sizing: border-box; }
            button { background: #EAB308; color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; margin-top: 10px; font-size: 16px; transition: 0.2s;}
            button:hover { background: #FDE047; }
            #status { margin-top: 20px; padding: 10px; display: none; }
            .success { border-left: 4px solid #22C55E; background: rgba(34, 197, 94, 0.1); }
            .error { border-left: 4px solid #EF4444; background: rgba(239, 68, 68, 0.1); }
        </style>
    </head>
    <body>
        <h1>⚾ FanStack God-Mode Control Port</h1>
        <p>Drop a reality-collapse JSON override payload below to execute surgically.</p>
        <textarea id="payloadText">{
    "source": "Gonzo 2.o / Pilot",
    "target_nodes": ["823319", "GLOBAL"],
    "new_state": "REALITY_COLLAPSE",
    "instructions": "Enter new instructions here.",
    "global_context": "Enter a global event here.",
    "constraints_toggle": {
        "action": "none",
        "protocol_string": ""
    }
}</textarea>
        <br>
        <button onclick="injectPayload()">INJECT OVERRIDE</button>
        <div id="status"></div>

        <script>
            async function injectPayload() {
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.className = '';
                statusDiv.innerText = 'Injecting...';
                
                try {
                    const payloadText = document.getElementById('payloadText').value;
                    const parsed = JSON.parse(payloadText);
                    
                    const res = await fetch('/api/admin/override', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(parsed)
                    });
                    
                    const data = await res.json();
                    if (res.ok) {
                        statusDiv.className = 'success';
                        statusDiv.innerText = `✅ [SUCCESS] ` + data.message;
                    } else {
                        statusDiv.className = 'error';
                        statusDiv.innerText = `❌ [REJECTED] ` + data.message;
                    }
                } catch(e) {
                    statusDiv.className = 'error';
                    statusDiv.innerText = `❌ [ERROR] Invalid JSON payload. Please fix syntax and try again.`;
                }
            }
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    # Bind to robust admin interface port (e.g. 5055)
    print("🚀 SOVEREIGN FANSTACK ADMIN API: INITIALIZED")
    app.run(host='0.0.0.0', port=5055, debug=False)
