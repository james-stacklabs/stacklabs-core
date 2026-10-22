
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import Response, FileResponse, RedirectResponse
import base64, sqlite3 as _sq
import base64, sqlite3 as _sq, glob
import base64, urllib.parse
import hashlib as _hashlib
import io
import json
import json as _json
import os
import os, time, socket, json
import re
import re as _re
import requests
import shutil
import socket, json
import socket, json, os
import sqlite3
import sqlite3 as _sq
import sqlite3 as _sq, uuid as _uuid
import subprocess
import sys
import time
import time, json
import traceback
import urllib.parse
import urllib.request as _ur
import uuid
import uuid as _uuid
# -------------------------------------------------------------

import asyncio
import json
import socket
import time
import websockets
import urllib.request
import traceback
import os
from pathlib import Path
from dotenv import load_dotenv
import datetime

import requests

# Load environment configurations dynamically
load_dotenv("/home/james/stacklabs/.env")

SOVEREIGN_HOME = Path(os.getenv("SOVEREIGN_HOME", "/home/james/stacklabs"))
DB_PATH = str(SOVEREIGN_HOME / "dna" / os.getenv("SOVEREIGN_DB_NAME", "sovereign_now.db"))

from core.roster_registry import RoomRosterRegistry

def get_db(path=DB_PATH, row_factory=True):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn

def resolve_player_id(player_val):
    if not player_val:
        return None
    try:
        return int(player_val)
    except ValueError:
        # [Hoisted to header] import sqlite3
        # [Hoisted to header] import re
        try:
            conn = get_db(DB_PATH, row_factory=False)
            cur = conn.cursor()
            cur.execute("SELECT sys_id FROM mlb_rosters WHERE player_name = ? COLLATE NOCASE LIMIT 1", (player_val,))
            row = cur.fetchone()
            conn.close()
            if row:
                match = re.search(r'\d+', row[0])
                if match:
                    return int(match.group())
        except Exception as e:
            print(f"[resolve_player_id error] {e}")
    return None

def get_matchup_prediction(batter_val, pitcher_val):
    batter_id = resolve_player_id(batter_val)
    pitcher_id = resolve_player_id(pitcher_val)

    if not batter_id or not pitcher_id:
        return {
            "source": "invalid-players",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }

    try:
        conn = get_db(INTELLIGENCE_DB, row_factory=True)
        cur = conn.cursor()

        # 1. Try head-to-head matchup history
        cur.execute("""
            SELECT
                COUNT(*) as total_matchups,
                COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
            FROM statcast_pitches
            WHERE batter = ? AND pitcher = ?;
        """, (batter_id, pitcher_id))
        row = cur.fetchone()

        if row and row["total_matchups"] > 0:
            res = {
                "source": "head-to-head",
                "total_matchups": row["total_matchups"],
                "strikeout_prob": round(row["strikeout_prob"], 1) if row["strikeout_prob"] is not None else 0.0,
                "hit_prob": round(row["hit_prob"], 1) if row["hit_prob"] is not None else 0.0,
                "walk_prob": round(row["walk_prob"], 1) if row["walk_prob"] is not None else 0.0
            }
            conn.close()
            return res

        # 2. If no head-to-head, get pitcher's dominant pitch type
        cur.execute("""
            SELECT pitch_name, COUNT(*) as c
            FROM statcast_pitches
            WHERE pitcher = ? AND pitch_name IS NOT NULL AND pitch_name != '' AND pitch_name != '---'
            GROUP BY pitch_name
            ORDER BY c DESC
            LIMIT 1
        """, (pitcher_id,))
        p_row = cur.fetchone()

        dominant_pitch = p_row["pitch_name"] if p_row else None

        if dominant_pitch:
            # Try batter's splits against this dominant pitch type
            cur.execute("""
                SELECT
                    COUNT(*) as total_matchups,
                    COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                    COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                    COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
                FROM statcast_pitches
                WHERE batter = ? AND pitch_name = ?;
            """, (batter_id, dominant_pitch))
            b_row = cur.fetchone()

            if b_row and b_row["total_matchups"] > 0:
                res = {
                    "source": f"splits_vs_{dominant_pitch}",
                    "total_matchups": b_row["total_matchups"],
                    "strikeout_prob": round(b_row["strikeout_prob"], 1) if b_row["strikeout_prob"] is not None else 0.0,
                    "hit_prob": round(b_row["hit_prob"], 1) if b_row["hit_prob"] is not None else 0.0,
                    "walk_prob": round(b_row["walk_prob"], 1) if b_row["walk_prob"] is not None else 0.0
                }
                conn.close()
                return res

        # 3. Fallback: Batter's overall splits against all pitch types
        cur.execute("""
            SELECT
                COUNT(*) as total_matchups,
                COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
            FROM statcast_pitches
            WHERE batter = ?;
        """, (batter_id,))
        fallback_row = cur.fetchone()

        if fallback_row and fallback_row["total_matchups"] > 0:
            res = {
                "source": "batter-overall",
                "total_matchups": fallback_row["total_matchups"],
                "strikeout_prob": round(fallback_row["strikeout_prob"], 1) if fallback_row["strikeout_prob"] is not None else 0.0,
                "hit_prob": round(fallback_row["hit_prob"], 1) if fallback_row["hit_prob"] is not None else 0.0,
                "walk_prob": round(fallback_row["walk_prob"], 1) if fallback_row["walk_prob"] is not None else 0.0
            }
            conn.close()
            return res

        conn.close()
        # 4. Final safety fallback
        return {
            "source": "league-average",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }

    except Exception as e:
        print(f"[RELAY_PREDICTION_ERROR] {e}")
        return {
            "source": "error-fallback",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }


def decorate_chat_message(chat_msg):
    """
    Look up persona details from the database and append id, persona_name, avatar_url,
    and hex (mapped from color) to make the chat message compliant with frontend expected format.
    """
    user = chat_msg.get("user") or chat_msg.get("persona") or "SYSTEM"
    if "id" not in chat_msg or "persona_name" not in chat_msg:
        # [Hoisted to header] import uuid
        msg_id = str(uuid.uuid4())
        p_name = user
        avatar_url = "/avatars/Sovereign_OS_Logo.jpg"
        hex_color = chat_msg.get("color") or "#ffffff"
        
        try:
            with get_db(row_factory=False) as conn:
                c = conn.cursor()
                c.execute("SELECT display_name, avatar_url, color FROM persona WHERE user_name = ? OR display_name = ? COLLATE NOCASE", (user, user))
                row = c.fetchone()
                if row:
                    p_name = row[0] if row[0] else user
                    avatar_url = row[1] if row[1] else avatar_url
                    hex_color = row[2] if row[2] else hex_color
        except Exception as e:
            print(f"[DECORATOR ERROR] {e}")
            
        chat_msg["id"] = chat_msg.get("id") or msg_id
        chat_msg["persona_name"] = chat_msg.get("persona_name") or p_name
        chat_msg["avatar_url"] = chat_msg.get("avatar_url") or avatar_url
        chat_msg["hex"] = chat_msg.get("hex") or hex_color
    return chat_msg



def fire_govee(r, g, b, color_tem=0):
    # [Hoisted to header] import socket, json, os
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    if os.getenv("GOVEE_TMI_ACTIVE", "true").lower() == "false":
        return
    ips = []
    env_ips = os.getenv("GOVEE_DEVICE_IP")
    if env_ips:
        ips = [ip.strip() for ip in env_ips.split(",") if ip.strip()]
    if not ips:
        ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
    port = int(os.getenv("GOVEE_PORT", 4003))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {
            "msg": {
                "cmd": "colorWC",
                "data": {
                    "color": {"r": r, "g": g, "b": b},
                    "colorTem": color_tem
                }
            }
        }
        payload = json.dumps(msg).encode('utf-8')
        for ip in ips:
            try:
                sock.sendto(payload, (ip, port))
            except:
                pass
        sock.close()
    except Exception as e:
        print(f"[GOVEE UDP ERROR] {e}")

def get_govee_statuses_sync(ips, port=4003):
    # [Hoisted to header] import socket, json
    statuses = {}
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('0.0.0.0', 4002))
        recv_sock.settimeout(0.15)
        
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {"msg": {"cmd": "devStatus", "data": {}}}
        payload = json.dumps(msg).encode('utf-8')
        for ip in ips:
            try:
                send_sock.sendto(payload, (ip, port))
            except:
                pass
        send_sock.close()
        
        while True:
            data, addr = recv_sock.recvfrom(1024)
            resp = json.loads(data.decode('utf-8'))
            device_data = resp.get("msg", {}).get("data", {})
            color = device_data.get("color")
            color_tem = device_data.get("colorTem", 0)
            if color and "r" in color and "g" in color and "b" in color:
                statuses[addr[0]] = (color, color_tem)
    except:
        pass
    return statuses

def trigger_govee_http_score():
    print("[GOVEE DIRECT OVERRIDE] Mets Score! Changing to Solid Orange.")
    fire_govee(252, 92, 29, 0)

def trigger_govee_http_hr():
    # [Hoisted to header] import os, time, socket, json
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    if os.getenv("GOVEE_TMI_ACTIVE", "true").lower() == "false":
        return
    ips = []
    env_ips = os.getenv("GOVEE_DEVICE_IP")
    if env_ips:
        ips = [ip.strip() for ip in env_ips.split(",") if ip.strip()]
    if not ips:
        ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
    port = int(os.getenv("GOVEE_PORT", 4003))
    print("[GOVEE DIRECT OVERRIDE] Mets Home Run! Flashing Orange and Blue.")
    try:
        prev_statuses = get_govee_statuses_sync(ips, port)
        for _ in range(5):
            fire_govee(0, 45, 98, 0) # Mets Blue
            time.sleep(0.3)
            fire_govee(252, 92, 29, 0) # Mets Orange
            time.sleep(0.3)
            
        # Restore status
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for ip in ips:
            if ip in prev_statuses:
                color, color_tem = prev_statuses[ip]
                msg = {
                    "msg": {
                        "cmd": "colorWC",
                        "data": {
                            "color": color,
                            "colorTem": color_tem
                        }
                    }
                }
                try:
                    sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                except:
                    pass
            else:
                msg = {
                    "msg": {
                        "cmd": "colorWC",
                        "data": {
                            "color": {"r": 255, "g": 255, "b": 255},
                            "colorTem": 0
                        }
                    }
                }
                try:
                    sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                except:
                    pass
        sock.close()
    except Exception as e:
        print(f"[GOVEE HR ERROR] {e}")

def check_and_trigger_dive_bar(user, text, target_room):
    # Disabled per Pilot request until scene synthesis is improved
    return

async def run_dive_bar_generation(user, text, target_room):
    # [Hoisted to header] import sqlite3 as _sq
    # [Hoisted to header] import subprocess
    import asyncio
    # [Hoisted to header] import json
    # [Hoisted to header] import time
    
    print(f"[DIVE BAR TRIGGER] Detected funny keyword in chat from {user}: '{text}'")
    # Fetch active personas in target_room from in-memory cache (WO0010160 Invariant)
    personas = list(RoomRosterRegistry.get_active_personas(target_room))
    if not personas:
        personas = list(RoomRosterRegistry.get_active_personas("GLOBAL"))
    if not personas:
        personas = ["barf", "unclesteviestan", "7_train_terry"]
        
    personas_str = ",".join(personas)
    output_path = f"/home/james/stacklabs/19_FanStackArena/public/images/dive_bar_{target_room}.png"
    output_path_alt = f"/home/james/stacklabs/15_FanStackCreator/public/images/dive_bar_{target_room}.png"
    
    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        "/home/james/stacklabs/scripts/auto_image_generator.py",
        "--mode", "dive_bar",
        "--personas", personas_str,
        "--active_persona", user,
        "--chat_text", text,
        "--output", output_path
    ]
    
    try:
        # Run subprocess asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            print(f"[DIVE BAR TRIGGER] Successfully generated composite image: {output_path}")
            # Copy to alternative public path too
            try:
                # [Hoisted to header] import shutil
                shutil.copy(output_path, output_path_alt)
            except:
                pass
            # Broadcast update via WebSocket to clients
            ws_msg = {
                "type": "DIVE_BAR_SCENE",
                "game_pk": target_room,
                "media_url": f"/images/dive_bar_{target_room}.png?t={int(time.time())}",
                "active_persona": user,
                "chat_text": text
            }
            # Send to all clients in the room
            out_msg = json.dumps(ws_msg)
            for c in list(clients):
                if ws_rooms.get(c, "GLOBAL") == target_room or ws_rooms.get(c, "GLOBAL") == "GLOBAL" or target_room == "GLOBAL":
                    try:
                        await c.send(out_msg)
                    except:
                        pass
        else:
            print(f"[DIVE BAR TRIGGER] Image generator failed with code {proc.returncode}. Stderr: {stderr.decode()}")
    except Exception as e:
        print(f"[DIVE BAR TRIGGER] Error running image generator: {e}")

clients = set()
senga_strikeout_streak = {}
last_walkup_batter = {}

game_states = __import__('collections').defaultdict(lambda: {
    "away_team": "AWY", "home_team": "HME",
    "away_score": 0, "home_score": 0,
    "inning": "1", "outs": 0,
    "status_msg": "Awaiting Telemetry...",
    "target_game_pk": "", "last_exit_velocity": "",
    "pitch_name": "---", "pitch_speed": "---",
    "onFirst": False, "onSecond": False, "onThird": False,
    "balls": 0, "strikes": 0, "pitchCount": "-",
    "batter": "", "pitcher": "",
    "hit_speed": "---", "hit_distance": "---",
    "launch_angle": "---", "hit_coord_x": None, "hit_coord_y": None,
    "event_type": "pitch",
    "batting_team": "", "wind": "---",
    "game_status": "live", "detailed_status": "",
    "pitches_this_ab": [],
    "recent_plays": [],
    "last_play_description": "",
    "last_play_batter": ""
})

CHATBOTS_MUTED_FLAG = "/home/james/stacklabs/config/chatbots_muted.flag"
BOTS_PAUSED_FLAG = "/tmp/bots_paused.flag"

global_system_state = {
    "mard_engine": True,
    "chaos_gating": True,
    "boggs_level": 2,
    "chatbots_enabled": not (os.path.exists(CHATBOTS_MUTED_FLAG) or os.path.exists(BOTS_PAUSED_FLAG))
}

recent_messages = {}
chat_buffers = __import__('collections').defaultdict(lambda: __import__('collections').deque(maxlen=100))
ws_rooms = {}
active_sim_task = None
INTELLIGENCE_DB = str(SOVEREIGN_HOME / "sovereign_intelligence.db")

async def run_simulation(game_pk, speed):
    con = get_db(INTELLIGENCE_DB, row_factory=False)
    cur = con.cursor()
    cur.execute("SELECT at_bat_number, pitch_number, events, description, des, away_score, home_score, inning, outs_when_up, balls, strikes, pitch_name, release_speed, batter, pitcher, away_team, home_team FROM statcast_pitches WHERE game_pk = ? ORDER BY at_bat_number ASC, pitch_number ASC", (game_pk,))
    rows = cur.fetchall()
    con.close()
    
    if not rows:
        game_states[str(game_pk)]["status_msg"] = f"[SIMULATION ERROR] No statcast pitches found for game_pk {game_pk}"
        await broadcast_state(str(game_pk))
        return

    game_states[str(game_pk)]["status_msg"] = f"[SIMULATION ACTIVE] Game {game_pk} loaded. MESH OVERRIDE ENGAGED."
    await broadcast_state(str(game_pk))
    await asyncio.sleep(2)
    
    try:
        for r in rows:
            ab_num, p_num, evts, desc, des, away_s, home_s, inn, outs, balls, strikes, p_name, speed_mph, batter, pitcher, away_t, home_t = r
            
            gs = game_states[str(game_pk)]
            gs["away_team"] = away_t if away_t else gs.get("away_team", "AWY")
            gs["home_team"] = home_t if home_t else gs.get("home_team", "HME")
            gs["away_score"] = away_s if away_s is not None else gs.get("away_score", 0)
            gs["home_score"] = home_s if home_s is not None else gs.get("home_score", 0)
            gs["inning"] = inn or gs.get("inning", 1)
            gs["outs"] = outs if outs is not None else gs.get("outs", 0)
            gs["balls"] = balls if balls is not None else gs.get("balls", 0)
            gs["strikes"] = strikes if strikes is not None else gs.get("strikes", 0)
            gs["pitch_name"] = p_name or "Unknown"
            gs["pitch_speed"] = speed_mph or "---"
            gs["pitcher"] = pitcher or gs.get("pitcher", "")
            gs["batter"] = batter or gs.get("batter", "")
            
            msg = f"Pitch {p_num} of AB {ab_num}: {desc}."
            if evts:
                msg += f" EVENT: {evts}."
            if des and len(str(des)) > 5:
                msg += f" {des}"
            
            gs["status_msg"] = msg
            gs["timestamp"] = time.strftime("%H:%M:%S")
            
            await broadcast_state(str(game_pk))
            
            delay = 12.0 / float(speed)
            await asyncio.sleep(delay)
            
        game_states[str(game_pk)]["status_msg"] = f"[SIMULATION COMPLETE] Game {game_pk} has concluded."
        await broadcast_state(str(game_pk))
    except asyncio.CancelledError:
        print(f"Simulation of game_pk {game_pk} was cancelled.")
        raise

def get_active_system_warnings():
    warnings = []
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT ea.ci_sys_id, ea.expression_name, ea.avatar_url, c.name, c.operational_status
            FROM cmdb_ci_expression_avatar ea
            JOIN cmdb_ci c ON ea.ci_sys_id = c.sys_id
            WHERE c.operational_status IN (2, 3)
        """)
        rows = cur.fetchall()
        for r in rows:
            warnings.append({
                "ci_sys_id": r["ci_sys_id"],
                "name": r["name"],
                "operational_status": r["operational_status"],
                "expression_name": r["expression_name"],
                "avatar_url": r["avatar_url"]
            })
        conn.close()
    except Exception as e:
        print(f"Error querying active warnings: {e}")
    return warnings

async def broadcast_state(target_pk=None, force_global=False):
    if not clients: return
    
    # Dynamically inject system warnings and degraded state
    warnings = get_active_system_warnings()
    global_system_state["warnings"] = warnings
    global_system_state["system_degraded"] = len(warnings) > 0
    current_boggs = global_system_state.get("boggs_level", 2)
    
    if target_pk and target_pk in game_states:
        game_states[target_pk]["boggs_level"] = current_boggs
        msg = json.dumps({"type": "STATE_UPDATE", "data": game_states[target_pk], "system": global_system_state, "force_global": force_global, "target_game_pk": target_pk, "boggs_level": current_boggs})
        print(f"[DEBUG] Broadcasting STATE_UPDATE for {target_pk} (boggs={current_boggs}) to {len(clients)} clients...")
        for c in list(clients):
            # Send if force_global, or if they are in GLOBAL, or if they are in the target room
            room = ws_rooms.get(c, "GLOBAL")
            if room == "POLLER":
                continue
            if force_global or room == "GLOBAL" or room == target_pk:
                try:
                    await c.send(msg)
                except Exception as e:
                    print(f"[DEBUG] Failed to send to client {c}: {e}")
                    clients.remove(c)
                    ws_rooms.pop(c, None)
    elif force_global and not target_pk:
        for pk in list(game_states.keys()):
            game_states[pk]["boggs_level"] = current_boggs
            room_msg = json.dumps({"type": "STATE_UPDATE", "data": game_states[pk], "system": global_system_state, "force_global": True, "target_game_pk": pk, "boggs_level": current_boggs})
            for c in list(clients):
                if ws_rooms.get(c, "GLOBAL") == "POLLER":
                    continue
                try: await c.send(room_msg)
                except: pass
        # Also send a global envelope
        msg = json.dumps({"type": "STATE_UPDATE", "data": {"boggs_level": current_boggs}, "system": global_system_state, "force_global": True, "target_game_pk": "GLOBAL", "boggs_level": current_boggs})
        for c in list(clients):
            if ws_rooms.get(c, "GLOBAL") == "POLLER":
                continue
            try: await c.send(msg)
            except: pass

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SovereignKnot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

async def mlb_poller():
    """Stub — MLB ingestion handled exclusively by fanstack_background_poller.py to avoid duplicate STATE_UPDATEs."""
    while True:
        await asyncio.sleep(3600)


# ── Clio Cockpit WebSocket Stream Routers ──────────────────────────────────────

import urllib.request
import os

system_metrics_clients = set()

async def system_metrics_poller_loop():
    print("🚀 Clio Cockpit Telemetry Poller Loop started in background.")
    while True:
        try:
            if system_metrics_clients:
                def fetch_metrics():
                    try:
                        req = urllib.request.Request("http://127.0.0.1:8090/api/system/metrics", method="GET")
                        with urllib.request.urlopen(req, timeout=1.0) as response:
                            return json.loads(response.read().decode())
                    except Exception as e:
                        return {"error": f"Failed to fetch metrics from Core API: {str(e)}"}
                
                loop = asyncio.get_running_loop()
                metrics = await loop.run_in_executor(None, fetch_metrics)
                
                payload = json.dumps({"type": "METRICS_UPDATE", "data": metrics})
                for client in list(system_metrics_clients):
                    try:
                        await client.send(payload)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[RELAY ERROR] metrics_poller_loop failure: {e}")
        await asyncio.sleep(1.0)

async def handle_system_metrics(ws):
    system_metrics_clients.add(ws)
    print("New Clio Cockpit metrics client connected!")
    try:
        async for message in ws:
            pass  # Read loop to keep connection alive and detect disconnects
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        system_metrics_clients.remove(ws)
        print("Clio Cockpit metrics client disconnected.")

async def handle_system_logs(ws):
    print("New Clio Cockpit log streamer client connected!")
    tail_task = None
    log_queue = asyncio.Queue()
    is_paused = False

    async def tail_file_worker(log_path):
        try:
            if not os.path.exists(log_path):
                await log_queue.put({"type": "LOG_ERROR", "message": f"Log file not found: {log_path}"})
                return
            
            # Send last 100 lines on connect
            with open(log_path, 'r', errors='replace') as f:
                lines = f.readlines()[-100:]
                await log_queue.put({"type": "LOG_HISTORY", "lines": lines})
            
            # Stream trailing lines
            f = open(log_path, 'r', errors='replace')
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                await log_queue.put({"type": "LOG_LINE", "line": line})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await log_queue.put({"type": "LOG_ERROR", "message": str(e)})

    async def read_client_messages():
        nonlocal is_paused, tail_task
        try:
            async for message in ws:
                data = json.loads(message)
                action = data.get("action")
                if action == "stream":
                    requested_file = data.get("file")
                    # Path traversal mitigation
                    if not requested_file or ".." in requested_file or "/" in requested_file or "\\" in requested_file:
                        await ws.send(json.dumps({"type": "LOG_ERROR", "message": "Invalid log file scope"}))
                        continue
                    
                    log_path = f"/home/james/stacklabs/logs/{requested_file}"
                    
                    if tail_task:
                        tail_task.cancel()
                    
                    # Clear queue
                    while not log_queue.empty():
                        log_queue.get_nowait()
                    
                    tail_task = asyncio.create_task(tail_file_worker(log_path))
                elif action == "pause":
                    is_paused = True
                elif action == "resume":
                    is_paused = False
        except Exception:
            pass

    client_msg_task = asyncio.create_task(read_client_messages())

    try:
        while True:
            item = await log_queue.get()
            if not is_paused or item.get("type") == "LOG_ERROR":
                try:
                    await ws.send(json.dumps(item))
                except Exception:
                    break
    except Exception:
        pass
    finally:
        client_msg_task.cancel()
        if tail_task:
            tail_task.cancel()
        print("Clio Cockpit log streamer client disconnected.")


async def handle_client(ws):
    # Intercept system monitoring WebSockets before standard chat room flow
    path = '/'
    if hasattr(ws, 'request') and hasattr(ws.request, 'path'):
        path = ws.request.path
    elif hasattr(ws, 'path') and ws.path is not None:
        path = ws.path

    if path == "/ws/system/metrics":
        await handle_system_metrics(ws)
        return
    elif path and path.startswith("/ws/system/logs"):
        await handle_system_logs(ws)
        return

    clients.add(ws)
    if path in ("/precog/bus", "/creator_precog_bus", "/precog/streamdeck") or (path and path.startswith("/precog")):
        ws_rooms[ws] = "creator_precog_bus"
        print(f"New Precog Creator Bus client connected on path {path}!")
    else:
        print("New FanCast visualizer node connected!")
        ws_rooms[ws] = "GLOBAL"
    await ws.send(json.dumps({"type": "STATE_UPDATE", "data": {}, "system": global_system_state}))
    # History gets pulled when they JOIN_ROOM
    
    try:
        async for message in ws:
            data = json.loads(message)
            
            if data.get("event") == "webslinger_trigger":
                room_id = str(data.get("room_id", "GLOBAL"))
                out_msg = json.dumps({
                    "type": "webslinger_trigger",
                    "event_name": data.get("event_name"),
                    "data": data.get("data"),
                    "room_id": room_id
                })
                event_data = data.get("data") or {}
                if event_data.get("type") == "hardware":
                    params = event_data.get("params", {})
                    command = event_data.get("command")
                    if command == "color_strobe":
                        r1 = params.get("r1", 0)
                        g1 = params.get("g1", 45)
                        b1 = params.get("b1", 98)
                        r2 = params.get("r2", 252)
                        g2 = params.get("g2", 92)
                        b2 = params.get("b2", 29)
                        cycles = params.get("cycles", 5)
                        interval_ms = params.get("interval_ms", 300)
                        
                        def run_strobe():
                            for _ in range(cycles):
                                fire_govee(r1, g1, b1)
                                time.sleep(interval_ms / 1000.0)
                                fire_govee(r2, g2, b2)
                                time.sleep(interval_ms / 1000.0)
                        
                        loop = asyncio.get_running_loop()
                        loop.run_in_executor(None, run_strobe)
                
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == room_id or room_id == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue

            if data.get("event") == "media_trigger":
                room_id = str(data.get("room_id", "GLOBAL"))
                out_msg = json.dumps({
                    "type": "media_trigger",
                    "room_id": room_id,
                    "data": data.get("data")
                })
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == room_id or room_id == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue

            if data.get("type") in ["official_review_start", "official_review_end", "official_review_override", "official_review_clear"]:
                room_id = str(data.get("room_id") or data.get("target_game_pk") or "GLOBAL")
                out_msg = json.dumps(data)
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == room_id or room_id == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue

            # In-Game Audience Polls Routing (WO0010054)
            if data.get("type") in ["POLL_PUBLISHED", "POLL_VOTED", "POLL_FROZEN", "POLL_CLOSED", "POLL_BROADCAST", "POLL_UPDATE", "poll_vote", "poll_broadcast", "poll_trigger"]:
                room_id = str(data.get("room_id") or data.get("target_game_pk") or "GLOBAL")
                out_msg = json.dumps(data)
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == room_id or room_id == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue

            # Precog Creator Edge Bus Routing (SPEC-FAAS-CREATOR-PRECOG-001 / WO0010370)
            if (
                data.get("channel") == "creator_precog_bus"
                or data.get("room_id") == "creator_precog_bus"
                or data.get("type") in ("creator_precog_event", "PRECOG_EVENT", "creator_precog_bus")
                or (str(data.get("event_id", "")).startswith("precog_") and "viral_priority" in data)
            ):
                out_msg = json.dumps(data)
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") in ("creator_precog_bus", "GLOBAL") or ws_rooms.get(c, "GLOBAL") == str(data.get("game_id", "GLOBAL")):
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue
            
            # SYS_LOG Message Routing - Isolated from Public Chat Stream
            if data.get("type") == "SYS_LOG":
                user = data.get("user", data.get("persona", "SYSTEM"))
                text = data.get("text", "")
                target_room = str(data.get("target_game_pk", "GLOBAL"))
                
                chat_msg = {
                    "type": "SYS_LOG",
                    "user": user,
                    "color": data.get("color"),
                    "text": text,
                    "target_game_pk": target_room,
                    "timestamp": time.strftime("%H:%M:%S"),
                    "model_engine": data.get("model_engine"),
                    "is_penalty_box": data.get("is_penalty_box", False),
                    "channel": data.get("channel", "system_broadcast"),
                    "mediaUrl": data.get("mediaUrl") or data.get("media_url") or data.get("image"),
                    "shake": data.get("shake", False)
                }
                out_msg = json.dumps(chat_msg)
                
                # Broadcast only to active clients in the target room (for live dev view)
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == target_room or target_room == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try:
                            await c.send(out_msg)
                        except:
                            pass
                continue

            # Global Chat Relay for WardyStack and Fans
            if data.get("type") in ["CHAT_MESSAGE", "YOUTUBE_CHAT"]:
                user = data.get("user", data.get("persona", "SYSTEM"))
                text = data.get("text", "")
                target_room = str(data.get("target_game_pk", "GLOBAL"))
                
                # Mean Gene Bouncer Intercept
                if data.get("type") == "CHAT_MESSAGE":
                    try:
                        from mean_gene import evaluate_bouncer_intervention
                        chk = evaluate_bouncer_intervention(user, text)
                        if not chk.get("allow", True):
                            # Suppress and send system moderation response to sender only
                            moderation_msg = {
                                "type": "CHAT_MESSAGE",
                                "user": "SYSTEM",
                                "color": "#f59e0b",
                                "text": chk.get("text"),
                                "target_game_pk": target_room,
                                "timestamp": time.strftime("%H:%M:%S"),
                                "model_engine": "MEAN_GENE_BOUNCER",
                                "is_penalty_box": False,
                                "msg_type": "MODERATION"
                            }
                            await ws.send(json.dumps(moderation_msg))
                            continue
                    except Exception as e:
                        print(f"[MEAN_GENE INTERCEPT ERROR] {e}")
                
                # FC-013: Deduplicate Bot commentary to prevent 3x echo loops from multiple UIs (never drop STATCAST telemetry)
                msg_key = f"{user}:{text}"
                now = time.time()
                if not data.get("is_penalty_box") and not data.get("is_telemetry") and str(user).upper() != "STATCAST":
                    if msg_key in recent_messages and now - recent_messages[msg_key] < 30:
                        continue # Suppress duplicate
                    recent_messages[msg_key] = now

                
                # Channel namespacing mapping
                channel = data.get("channel")
                if not channel:
                    if data.get("is_penalty_box"):
                        channel = "vocal_matrix"
                    else:
                        channel = "system_broadcast"

                chat_msg = {
                    "type": data.get("type", "CHAT_MESSAGE"),
                    "user": user,
                    "color": data.get("color"),
                    "text": text,
                    "target_game_pk": target_room,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "model_engine": data.get("model_engine"),
                    "is_penalty_box": data.get("is_penalty_box", False),
                    "channel": channel,
                    "mediaUrl": data.get("mediaUrl") or data.get("media_url") or data.get("image"),
                    "shake": data.get("shake", False)
                }
                chat_msg = decorate_chat_message(chat_msg)
                out_msg = json.dumps(chat_msg)
                
                chat_buffers[target_room].append(chat_msg)
                
                # UAT CHAT LOGGING
                try:
                    log_dir = SOVEREIGN_HOME / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    with open(log_dir / "fanstack_chat_uat.log", "a") as f:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {user}: {text}\n")
                except Exception:
                    pass
                    
                # AUTOMATED NOTEBOOK-LM EXPORTS (Per-Game Markdown)
                if target_room != "GLOBAL":
                    check_and_trigger_dive_bar(user, text, target_room)
                    try:
                        today_dir = datetime.datetime.now().strftime('daily_%d%m%Y')
                        export_dir = f"/home/james/stacklabs/data/logs/{today_dir}"
                        os.makedirs(export_dir, exist_ok=True)
                        export_path = f"{export_dir}/auto_export_{target_room}.md"
                        if not os.path.exists(export_path):
                            with open(export_path, "w") as f:
                                f.write(f"# Sovereign FanCast Export: Game {target_room}\n\n")
                                
                        with open(export_path, "a") as f:
                            ts = time.strftime("%H:%M:%S")
                            f.write(f"**{user}** ({ts}): {text}\n\n")
                    except Exception as e:
                        print(f"Failed to write NotebookLM export: {e}")
                
                for c in list(clients):
                    if ws_rooms.get(c, "GLOBAL") == "POLLER":
                        continue
                    if ws_rooms.get(c, "GLOBAL") == target_room or target_room == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                        try: 
                            await c.send(out_msg)
                        except: 
                            pass
            
            if data.get("type") == "JOIN_ROOM":
                pk = str(data.get("target_game_pk") or data.get("room") or data.get("room_id") or data.get("channel") or "GLOBAL")
                ws_rooms[ws] = pk
                if pk not in chat_buffers:
                    try:
                        # [Hoisted to header] import sqlite3
                        _con = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
                        _con.row_factory = sqlite3.Row
                        _rows = _con.execute("SELECT persona_id as user, comment_text as text, timestamp FROM m2m_persona_room_ledger WHERE game_pk = ? ORDER BY id ASC LIMIT 20", (pk,)).fetchall()
                        _con.close()
                        for _r in _rows:
                            chat_buffers[pk].append({
                                "type": "CHAT_MESSAGE",
                                "user": _r["user"],
                                "text": _r["text"],
                                "timestamp": _r["timestamp"] or datetime.datetime.now().isoformat(),
                                "room": pk,
                                "target_game_pk": pk
                            })
                    except Exception as _e:
                        print("Failed to populate chat buffer from ledger:", _e)

                global_msgs = list(chat_buffers["GLOBAL"])
                room_msgs = list(chat_buffers[pk]) if pk != "GLOBAL" else []
                combined = [
                    m for m in (global_msgs + room_msgs)
                    if not m.get("is_walkup")
                    and not m.get("is_telemetry")
                    and "STATCAST" not in str(m.get("user", "")).upper()
                    and "UMPIRE" not in str(m.get("user", "")).upper()
                    and "NOW BATTING:" not in str(m.get("text", ""))
                ]
                def _sort_key(m):
                    ts = str(m.get("timestamp") or "")
                    if not ts:
                        return ""
                    if "T" not in ts and len(ts) == 8:
                        return f"{datetime.date.today().isoformat()}T{ts}"
                    return ts
                combined.sort(key=_sort_key)
                hist_msg = json.dumps({"type": "CHAT_HISTORY", "messages": combined})
                await ws.send(hist_msg)
                if pk != "GLOBAL":
                    if pk not in game_states or game_states[pk].get("home_team") in ("HME", "HOME", "", None):
                        disk_state_file = f"/home/james/stacklabs/game_states/{pk}.json"
                        if os.path.exists(disk_state_file):
                            try:
                                with open(disk_state_file, "r") as _df:
                                    _disk_data = json.load(_df)
                                    if _disk_data and isinstance(_disk_data, dict):
                                        game_states[pk].update(_disk_data)
                            except Exception as _e:
                                print(f"[RELAY] Error hydrating game state from disk for {pk}: {_e}")
                if pk in game_states:
                    await ws.send(json.dumps({"type": "STATE_UPDATE", "data": game_states[pk], "system": global_system_state}))
            
            # Adversarial Ingress Broadcast
            if data.get("type") == "CMD_PERSONA":
                out_msg = json.dumps({"type": "CMD_PERSONA", "persona": data.get("persona"), "prompt": data.get("prompt")})
                for c in list(clients):
                    try: 
                        await c.send(out_msg)
                    except: 
                        pass
            
            if data.get("type") == "CMD_SYNC_STATE":
                sync_data = data.get("data", {})
                
                # Check for "Empty JSON" packet: home/away teams missing and pitch values are placeholders ("---")
                home_team = sync_data.get("home_team")
                away_team = sync_data.get("away_team")
                pitch_name = sync_data.get("pitch_name")
                pitch_speed = sync_data.get("pitch_speed")
                if (not home_team and not away_team) and (pitch_name == "---" or pitch_speed == "---"):
                    print(f"[DEBUG] Dropping Empty JSON/Placeholder telemetry packet for game: {data.get('target_game_pk')}")
                    continue

                # Send application-layer ACK immediately back to the sender
                if "msg_id" in data:
                    try:
                        await ws.send(json.dumps({
                            "type": "CMD_SYNC_ACK",
                            "msg_id": data["msg_id"],
                            "target_game_pk": data.get("target_game_pk")
                        }))
                    except Exception as ack_err:
                        print(f"[ACK_ERROR] Failed to send ACK to poller: {ack_err}")

                # Persist live play telemetry into game_play database table (WO-2026-094)
                try:
                    # [Hoisted to header] import sqlite3 as _sq, uuid as _uuid
                    pk = str(data.get("target_game_pk", "GLOBAL"))
                    if pk != "GLOBAL" and sync_data.get("status_msg"):
                        inning_str = sync_data.get("inning", "")
                        half_val = None
                        inning_num = None
                        if inning_str:
                            parts = inning_str.split()
                            if len(parts) >= 2:
                                half_val = parts[0].lower()
                                if half_val.startswith("bot"):
                                    half_val = "bottom"
                                elif half_val.startswith("top"):
                                    half_val = "top"
                                try:
                                    # [Hoisted to header] import re
                                    num_str = re.sub(r'\D', '', parts[1])
                                    if num_str:
                                        inning_num = int(num_str)
                                except Exception:
                                    pass

                        p_speed = sync_data.get("pitch_speed")
                        try:
                            p_speed_val = float(p_speed) if p_speed and p_speed != "---" else None
                        except Exception:
                            p_speed_val = None

                        db_conn = get_db(row_factory=False)
                        db_conn.execute("""
                            INSERT OR IGNORE INTO game_play
                                (id, game_pk, play_id, inning, half, event_type,
                                 batter, pitcher, pitch_speed, pitch_type,
                                 description, score_away, score_home, outs, raw_json)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            _uuid.uuid4().hex,
                            pk,
                            sync_data.get('play_id') or _uuid.uuid4().hex[:12],
                            inning_num,
                            half_val,
                            sync_data.get('event_type'),
                            sync_data.get('batter'),
                            sync_data.get('pitcher'),
                            p_speed_val,
                            sync_data.get('pitch_name'),
                            sync_data.get('status_msg'),
                            sync_data.get('away_score'),
                            sync_data.get('home_score'),
                            sync_data.get('outs'),
                            json.dumps(sync_data)
                        ))
                        db_conn.commit()
                        db_conn.close()
                except Exception as db_err:
                    print(f"[DB_ERROR] Failed to persist game_play event: {db_err}")
                
                # SDLC-0027 FINAL LOCKDOWN LOGIC
                s_msg = sync_data.get("status_msg", "").lower()
                p_name = sync_data.get("pitch_name", "")
                p_speed = sync_data.get("pitch_speed", "")
                if "timeout" in s_msg:
                    print(f"[NYM_SF_LOCKDOWN] [{time.strftime('%H:%M:%S')}] STANDARD ON-FIELD TIMEOUT DETECTED.")
                elif "warmup" in s_msg or "scheduled" in s_msg or "awaiting" in s_msg:
                    pass # Ignore telemetry loss for pre-game states
                elif not p_name or not p_speed or p_name == "---" or p_speed == "---":
                    print(f"[NYM_SF_LOCKDOWN] [{time.strftime('%H:%M:%S')}] TELEMETRY LOSS DETECTED: Empty Pitch JSON received.")
                # [Hoisted to header] import sys
                sys.stdout.flush()
                
                force_global = data.get("force_global", False)
                pk = str(data.get("target_game_pk", "GLOBAL"))
                
                # NOTEBOOK-LM LOGGING FOR TELEMETRY
                if pk != "GLOBAL" and sync_data.get("status_msg") and sync_data.get("status_msg") != game_states.get(pk, {}).get("status_msg"):
                    try:
                        today_dir = datetime.datetime.now().strftime('daily_%d%m%Y')
                        export_dir = f"/home/james/stacklabs/data/logs/{today_dir}"
                        os.makedirs(export_dir, exist_ok=True)
                        export_path = f"{export_dir}/auto_export_{pk}.md"
                        if not os.path.exists(export_path):
                            with open(export_path, "w") as f:
                                f.write(f"# Sovereign FanCast Export: Game {pk}\n\n")
                        with open(export_path, "a") as f:
                            ts = time.strftime("%H:%M:%S")
                            f.write(f"> **[MLB TELEMETRY]** ({ts}): {sync_data['status_msg']}\n\n")
                    except Exception as e:
                        print(f"Failed to write Telemetry export: {e}")

                gs = game_states[pk]
                gs["timestamp"] = time.strftime("%H:%M:%S")
                gs["target_game_pk"] = pk
                gs["game_status"] = sync_data.get("game_status", gs.get("game_status", "live"))
                gs["detailed_status"] = sync_data.get("detailed_status", gs.get("detailed_status", ""))
                old_away_score = gs.get("away_score", 0)
                old_home_score = gs.get("home_score", 0)
                new_away_score = sync_data.get("away_score", gs["away_score"])
                new_home_score = sync_data.get("home_score", gs["home_score"])
                score_changed = (old_away_score is not None and new_away_score != old_away_score) or (old_home_score is not None and new_home_score != old_home_score)
                gs["away_score"] = new_away_score
                gs["home_score"] = new_home_score
                gs["away_team"] = sync_data.get("away_team", gs["away_team"])
                gs["home_team"] = sync_data.get("home_team", gs["home_team"])
                gs["inning"] = sync_data.get("inning", gs["inning"])
                gs["outs"] = sync_data.get("outs", gs["outs"])
                gs["balls"] = sync_data.get("balls", gs.get("balls", 0))
                gs["strikes"] = sync_data.get("strikes", gs.get("strikes", 0))
                gs["last_exit_velocity"] = sync_data.get("last_exit_velocity", gs.get("last_exit_velocity", ""))
                gs["status_msg"] = sync_data.get("status_msg", gs["status_msg"])
                gs["pitcher"] = sync_data.get("pitcher", gs.get("pitcher", ""))
                gs["batter"] = sync_data.get("batter", gs.get("batter", ""))
                gs["pitch_name"] = sync_data.get("pitch_name", gs.get("pitch_name", "---"))
                gs["pitch_speed"] = sync_data.get("pitch_speed", gs.get("pitch_speed", "---"))
                gs["hit_speed"] = sync_data.get("hit_speed", gs.get("hit_speed", "---"))
                gs["hit_distance"] = sync_data.get("hit_distance", gs.get("hit_distance", "---"))
                gs["launch_angle"] = sync_data.get("launch_angle", gs.get("launch_angle", "---"))
                gs["hit_coord_x"] = sync_data.get("hit_coord_x", gs.get("hit_coord_x"))
                gs["hit_coord_y"] = sync_data.get("hit_coord_y", gs.get("hit_coord_y"))
                gs["event_type"] = sync_data.get("event_type", gs.get("event_type", "pitch"))
                gs["batting_team"] = sync_data.get("batting_team", gs.get("batting_team", ""))
                gs["delta_score"] = sync_data.get("delta_score", gs.get("delta_score", 0))
                gs["inning_half"] = sync_data.get("inning_half") or sync_data.get("half") or gs.get("inning_half", "")
                gs["onFirst"] = sync_data.get("onFirst", gs.get("onFirst", False))
                gs["onSecond"] = sync_data.get("onSecond", gs.get("onSecond", False))
                gs["onThird"] = sync_data.get("onThird", gs.get("onThird", False))
                gs["pitchCount"] = sync_data.get("pitchCount", gs.get("pitchCount", "-"))
                gs["horizontal_break_inches"] = sync_data.get("horizontal_break_inches", gs.get("horizontal_break_inches", 0.0))
                gs["vertical_break_inches"] = sync_data.get("vertical_break_inches", gs.get("vertical_break_inches", 0.0))
                gs["swing_status"] = sync_data.get("swing_status", gs.get("swing_status", "TAKE"))
                gs["bat_speed_mph"] = sync_data.get("bat_speed_mph", gs.get("bat_speed_mph", 0.0))
                gs["whiff_distance_inches"] = sync_data.get("whiff_distance_inches", gs.get("whiff_distance_inches", 0.0))
                gs["is_sword"] = sync_data.get("is_sword", gs.get("is_sword", False))
                gs["wind"] = sync_data.get("wind", gs.get("wind", "---"))
                gs["venue_name"] = sync_data.get("venue_name", gs.get("venue_name", ""))
                gs["venue_location"] = sync_data.get("venue_location", gs.get("venue_location", ""))
                gs["batter_id"] = sync_data.get("batter_id", gs.get("batter_id", ""))
                gs["pitcher_id"] = sync_data.get("pitcher_id", gs.get("pitcher_id", ""))
                gs["batter_avg"] = sync_data.get("batter_avg", gs.get("batter_avg", ""))
                gs["batter_obp"] = sync_data.get("batter_obp", gs.get("batter_obp", ""))
                gs["batter_slg"] = sync_data.get("batter_slg", gs.get("batter_slg", ""))
                gs["batter_ops"] = sync_data.get("batter_ops", gs.get("batter_ops", ""))
                gs["batter_hr"] = sync_data.get("batter_hr", gs.get("batter_hr", ""))
                gs["batter_rbi"] = sync_data.get("batter_rbi", gs.get("batter_rbi", ""))
                gs["pitcher_era"] = sync_data.get("pitcher_era", gs.get("pitcher_era", ""))
                gs["pitcher_whip"] = sync_data.get("pitcher_whip", gs.get("pitcher_whip", ""))
                gs["pitcher_wins"] = sync_data.get("pitcher_wins", gs.get("pitcher_wins", ""))
                gs["pitcher_losses"] = sync_data.get("pitcher_losses", gs.get("pitcher_losses", ""))
                gs["pitcher_so"] = sync_data.get("pitcher_so", gs.get("pitcher_so", ""))
                gs["pitcher_ip"] = sync_data.get("pitcher_ip", gs.get("pitcher_ip", ""))

                if "recent_plays" in sync_data and sync_data["recent_plays"]:
                    gs["recent_plays"] = sync_data["recent_plays"]

                _msg = sync_data.get("status_msg", "")
                _msg_lower = _msg.lower()
                if _msg and not any(_msg_lower == k for k in ["ball", "called strike", "swinging strike", "foul", "foul tip", "batter timeout."]):
                    gs["last_play_description"] = _msg
                    if sync_data.get("batter"):
                        gs["last_play_batter"] = sync_data["batter"]

                if (score_changed or "homers" in _msg_lower or "home run" in _msg_lower) and _msg and old_away_score != 0:
                    scoring_card = {
                        "type": "CHAT_MESSAGE",
                        "user": "SCOREBOARD",
                        "color": "#F59E0B",
                        "text": f"💥 SCORING PLAY: {_msg} • {gs['away_team']} {new_away_score} - {gs['home_team']} {new_home_score}",
                        "target_game_pk": str(pk),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "is_scoring": True,
                        "channel": "system_broadcast"
                    }
                    scoring_card = decorate_chat_message(scoring_card)
                    chat_buffers[pk].append(scoring_card)
                    out_score = json.dumps(scoring_card)
                    for c in list(clients):
                        if ws_rooms.get(c, "GLOBAL") == str(pk) or ws_rooms.get(c, "GLOBAL") == "GLOBAL" or str(pk) == "GLOBAL":
                            try:
                                await c.send(out_score)
                            except:
                                pass

                # ── Dugout Statcast Deck: Pitch Sequence Accumulation (WO0010083) ──
                # Determine result bucket from balls/strikes delta or description
                _event_type = sync_data.get("event_type", gs.get("event_type", "pitch"))
                _desc = (sync_data.get("status_msg") or "").lower()
                _new_balls = sync_data.get("balls", gs.get("balls", 0))
                _new_strikes = sync_data.get("strikes", gs.get("strikes", 0))
                _p_type = sync_data.get("pitch_type") or sync_data.get("pitch_name") or gs.get("pitch_name", "---")
                _p_speed = sync_data.get("pitch_speed") or gs.get("pitch_speed", "---")
                _p_name = sync_data.get("pitch_name") or gs.get("pitch_name", "---")
                _plate_x = sync_data.get("plate_x")  # May be None if TMI doesn't surface yet
                _plate_z = sync_data.get("plate_z")  # May be None if TMI doesn't surface yet

                def _classify_pitch_result(desc, event_t):
                    """Classify pitch outcome to BALL/STRIKE/FOUL/IN_PLAY without entity-specific logic."""
                    if event_t in ("hit", "home_run", "single", "double", "triple", "field_out",
                                   "grounded_into_double_play", "force_out", "sac_fly", "sac_bunt",
                                   "fielders_choice", "hit_by_pitch"):
                        return "IN_PLAY"
                    for kw in ("foul",):
                        if kw in desc:
                            return "FOUL"
                    for kw in ("ball", "walk", "intentional walk", "hit by pitch"):
                        if kw in desc:
                            return "BALL"
                    for kw in ("strike", "struck out", "called out on strikes", "swinging strike", "called strike"):
                        if kw in desc:
                            return "STRIKE"
                    return None  # Not a pitch event; skip appending

                _pitch_result = _classify_pitch_result(_desc, _event_type)
                if _pitch_result and _p_type and _p_type not in ("---", ""):
                    _existing = gs.get("pitches_this_ab", [])
                    _pitch_entry = {
                        "n": len(_existing) + 1,
                        "type": str(_p_type)[:2].upper() if len(str(_p_type)) >= 2 else str(_p_type).upper(),
                        "speed": str(_p_speed),
                        "result": _pitch_result,
                        "plate_x": _plate_x,
                        "plate_z": _plate_z,
                        "name": _p_name
                    }
                    gs["pitches_this_ab"] = _existing + [_pitch_entry]

                # \u2500\u2500 WO0010087: Poller authoritative override \u2500\u2500
                # If background poller sent a full pitches_this_ab from MLB playEvents,
                # use it directly (it has real plate_x/plate_z coords). Only override
                # when the poller array is non-empty so relay fallback accumulator still
                # activates during simulation/replay modes.
                _poller_pitches = sync_data.get("pitches_this_ab")
                if isinstance(_poller_pitches, list) and len(_poller_pitches) > 0:
                    gs["pitches_this_ab"] = _poller_pitches


                # Compute matchup predictions dynamically
                b_val = gs.get("batter_id") or gs.get("batter")
                p_val = gs.get("pitcher_id") or gs.get("pitcher")
                if b_val and p_val:
                    gs["matchup_prediction"] = get_matchup_prediction(b_val, p_val)
                else:
                    gs["matchup_prediction"] = {
                        "source": "missing-players",
                        "total_matchups": 0,
                        "strikeout_prob": 22.0,
                        "hit_prob": 25.0,
                        "walk_prob": 8.0
                    }

                # Senga Ghost Protocol Easter Egg detection
                status_msg = sync_data.get("status_msg", "")
                pitcher_name = sync_data.get("pitcher", "")
                is_senga = "senga" in pitcher_name.lower() or "senga" in status_msg.lower()

                # Batter Walk-Up & At-Bat Transition Chat Announcement
                new_batter = sync_data.get("batter") or gs.get("batter", "")
                new_batter_id = str(sync_data.get("batter_id") or gs.get("batter_id", ""))
                batter_key = new_batter_id if new_batter_id else new_batter

                if new_batter and new_batter not in ["", "---", "Awaiting Batter"] and last_walkup_batter.get(pk) != batter_key:
                    if gs.get("status_msg") and gs.get("status_msg") != "Awaiting Telemetry...":
                        gs["last_play_description"] = gs["status_msg"]
                        gs["last_play_batter"] = gs.get("batter", "")
                    # Reset pitch sequence on batter change (Dugout Statcast Deck - WO0010083)
                    gs["pitches_this_ab"] = []
                    last_walkup_batter[pk] = batter_key
                    jersey = sync_data.get("batter_jersey") or gs.get("batter_jersey", "")
                    pos = sync_data.get("batter_position") or gs.get("batter_position", "")
                    avg = sync_data.get("batter_avg") or gs.get("batter_avg", "---")
                    hr = sync_data.get("batter_hr") or gs.get("batter_hr", "0")
                    rbi = sync_data.get("batter_rbi") or gs.get("batter_rbi", "0")
                    ops = sync_data.get("batter_ops") or gs.get("batter_ops", "")

                    jersey_str = f"#{jersey} " if jersey else ""
                    pos_str = f"{pos} • " if pos else ""
                    stat_parts = []
                    if avg and avg != "---": stat_parts.append(f"{avg} AVG")
                    if hr and hr != "0": stat_parts.append(f"{hr} HR")
                    if rbi and rbi != "0": stat_parts.append(f"{rbi} RBI")
                    if ops and ops != "---": stat_parts.append(f"{ops} OPS")
                    stat_str = f" ({pos_str}{', '.join(stat_parts)})" if stat_parts else (f" ({pos})" if pos else "")

                    walkup_text = f"🎙️ NOW BATTING: {jersey_str}{new_batter}{stat_str}"
                    walkup_msg = {
                        "type": "WALKUP_ANNOUNCEMENT",
                        "user": "STATCAST UMPIRE",
                        "color": "#00FFCC",
                        "text": walkup_text,
                        "target_game_pk": str(pk),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "is_walkup": True,
                        "channel": "system_broadcast",
                        "batter_name": new_batter,
                        "batter_id": new_batter_id,
                        "jersey": jersey,
                        "position": pos,
                        "stats": {"avg": avg, "hr": hr, "rbi": rbi, "ops": ops}
                    }
                    walkup_msg = decorate_chat_message(walkup_msg)
                    # Note: Do NOT append to chat_buffers so chat remains strictly for fan advocates
                    print(f"[WALKUP ANNOUNCEMENT] Game {pk}: {walkup_text}")

                    out_walkup = json.dumps(walkup_msg)
                    for c in list(clients):
                        if ws_rooms.get(c, "GLOBAL") == str(pk) or ws_rooms.get(c, "GLOBAL") == "GLOBAL" or str(pk) == "GLOBAL":
                            try:
                                await c.send(out_walkup)
                            except:
                                pass
                
                if is_senga and status_msg:
                    status_lower = status_msg.lower()
                    is_strikeout = "strikes out" in status_lower or "strikeout" in status_lower or "called out on strikes" in status_lower
                    is_other_outcome = any(x in status_lower for x in [
                        "singles", "doubles", "triples", "homers", "home run", "walks", "base hit",
                        "ground out", "flies out", "lines out", "pops out", "sac", "hit by pitch", "hbp",
                        "reached on", "fielder's choice", "double play", "triple play", "lineout", "flyout", "groundout"
                    ])
                    
                    old_msg = game_states.get(pk, {}).get("status_msg", "")
                    if status_msg != old_msg:
                        if is_strikeout:
                            streak_count = senga_strikeout_streak.get(pk, 0) + 1
                            senga_strikeout_streak[pk] = streak_count
                            print(f"[GHOST PROTOCOL] Kodai Senga strikeout detected! Streak for game {pk}: {streak_count}")
                            if streak_count >= 3:
                                print(f"[GHOST PROTOCOL] STREAK AT {streak_count}! Triggering Ghost Protocol Easter Egg!")
                                ghost_payload = {
                                    "type": "webslinger_trigger",
                                    "event_name": "EMIT_CHAT_GHOST_OVERLAY",
                                    "data": {"trigger": "EMIT_CHAT_GHOST_OVERLAY"},
                                    "room_id": pk
                                }
                                out_msg = json.dumps(ghost_payload)
                                for c in list(clients):
                                    try:
                                        await c.send(out_msg)
                                    except:
                                        pass
                        elif is_other_outcome:
                            senga_strikeout_streak[pk] = 0
                            print(f"[GHOST PROTOCOL] Pitcher outcome reset Senga streak for game {pk} to 0. (Play: {status_msg})")

                await broadcast_state(pk, force_global=force_global)

            # Keeping the manual trigger for testing / Chindogu Overrides
            
            if data.get("type") == "CMD_METS_HR" or (data.get("type") == "trigger_event" and data.get("event") == "home_run"):
                pk = ws_rooms.get(ws, "GLOBAL")
                if pk in game_states: game_states[pk]["status_msg"] = "🚨 SOVEREIGN HARDWARE OVERRIDE: METS HOME RUN! 🚨"
                await broadcast_state(pk)
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, trigger_govee_http_hr)

            elif data.get("type") == "CMD_METS_GOOD" or (data.get("type") == "trigger_event" and data.get("event") == "strikeout"):
                pk = ws_rooms.get(ws, "GLOBAL")
                if pk in game_states: game_states[pk]["status_msg"] = "🚨 SOVEREIGN HARDWARE OVERRIDE: METS WALK-OFF! 🚨"
                await broadcast_state(pk)
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, trigger_govee_http_score)
                
            elif data.get("type") == "trigger_event" and data.get("event") == "spam_logo":
                out_msg = json.dumps({"type": "CMD_SPAM_METS"})
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass

            # Manual Studio Interventions (Wardy injections)
            if data.get("type") == "CMD_MSG":
                msg_text = data.get("text", "")
                force_global = data.get("force_global", False)
                pk = ws_rooms.get(ws, "GLOBAL")
                if msg_text:
                    if pk in game_states: game_states[pk]["status_msg"] = msg_text
                    await broadcast_state(pk, force_global=force_global)

            # Support Mesh-wide game synchronization
            if data.get("type") == "CMD_SWITCH_GAME":
                pk = data.get("game_pk")
                force_global = data.get("force_global", False)
                if pk:
                    sports_session["current_ingress_stream"] = str(pk)
                    hist_msg = json.dumps({"type": "CHAT_HISTORY", "messages": list(chat_buffers[str(pk)])})
                    if force_global:
                        for c in list(clients): 
                            ws_rooms[c] = str(pk)
                            try: await c.send(hist_msg)
                            except: pass
                    else:
                        ws_rooms[ws] = str(pk)
                        try: await ws.send(hist_msg)
                        except: pass
                    
                    # Broadcast room switch event to sync dropdown UI states
                    switch_msg = json.dumps({"type": "GAME_SWITCHED", "game_pk": str(pk)})
                    for c in list(clients):
                        try: await c.send(switch_msg)
                        except: pass

                    await broadcast_state(str(pk))
                    
                    if str(pk) != "GLOBAL":
                        # [Hoisted to header] import subprocess
                        print(f"[HOTSWAP] Triggering autonomous deployment for room {pk}...")
                        subprocess.Popen(["python3", "/home/james/stacklabs/scripts/deploy_game_room.py", str(pk)])
                    
                    # Manage Simulation Tasks
                    global active_sim_task
                    if active_sim_task:
                        active_sim_task.cancel()
                        active_sim_task = None
                    
                    con = get_db(row_factory=False)
                    cur = con.cursor()
                    cur.execute("SELECT is_simulated, sim_speed FROM cmdb_ci_fanstack_room WHERE game_pk=?", (str(pk),))
                    row = cur.fetchone()
                    con.close()
                    if row and row[0] == 1:
                        speed = row[1] if row[1] else 1.0
                        active_sim_task = asyncio.create_task(run_simulation(pk, speed))

            # Boggs Level 5 Chaos
            if data.get("type") == "CMD_SPAM_METS":
                out_msg = json.dumps({"type": "CMD_SPAM_METS"})
                for c in list(clients):
                    try: 
                        await c.send(out_msg)
                    except: 
                        pass
            # Wardy Broadcast translation
            if data.get("type") == "broadcast":
                chat_msg = {"type": "CHAT_MESSAGE", "user": "Wardy", "color": "#f97316", "text": data.get("message", ""), "target_game_pk": "GLOBAL", "timestamp": time.strftime("%H:%M:%S")}
                chat_msg = decorate_chat_message(chat_msg)
                out_msg = json.dumps(chat_msg)
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                    
            # MARD Config (UI Toggles)
            if data.get("type") == "mard_config":
                key = data.get("key")
                val = data.get("value")
                if key == 'engine':
                    global_system_state["mard_engine"] = val
                elif key == 'chaos':
                    global_system_state["chaos_gating"] = val
                elif key == 'barf_cypher':
                    global_system_state["barf_cypher"] = val
                await broadcast_state(force_global=True)
                
            if data.get("type") == "boggs_level":
                lvl = int(data.get("level", 2))
                global_system_state["boggs_level"] = lvl
                for gpk in list(game_states.keys()):
                    game_states[gpk]["boggs_level"] = lvl
                out_msg = json.dumps({
                    "type": "boggs_level",
                    "level": lvl,
                    "system": global_system_state,
                    "target_game_pk": data.get("target_game_pk", "GLOBAL")
                })
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                await broadcast_state(force_global=True)

            if data.get("type") == "ROOM_DEPLOYMENT_TOGGLE":
                g_pk = str(data.get("game_pk", ""))
                r_state = str(data.get("room_state", "staged"))
                if g_pk:
                    try:
                        # [Hoisted to header] import sqlite3 as _sq
                        _con = _sq.connect(DB_PATH, timeout=10.0)
                        _con.execute("UPDATE sport_schedule SET room_state=? WHERE game_pk=?", (r_state, g_pk))
                        _con.execute("UPDATE mlb_schedule SET room_state=? WHERE game_pk=?", (r_state, g_pk))
                        _con.execute("UPDATE cmdb_ci_fanstack_room SET room_state=? WHERE game_pk=?", (r_state, g_pk))
                        _con.commit()
                        _con.close()
                        print(f"[RELAY] Room {g_pk} room_state set to {r_state}")
                    except Exception as _e:
                        print(f"[ROOM_DEPLOYMENT_TOGGLE] DB update error: {_e}")
                out_msg = json.dumps(data)
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                continue

            if data.get("type") == "GLOBAL_CHATBOTS_TOGGLE":
                target_state = bool(data.get("enabled", True))
                global_system_state["chatbots_enabled"] = target_state
                if target_state:
                    if os.path.exists(CHATBOTS_MUTED_FLAG):
                        try: os.remove(CHATBOTS_MUTED_FLAG)
                        except: pass
                    if os.path.exists(BOTS_PAUSED_FLAG):
                        try: os.remove(BOTS_PAUSED_FLAG)
                        except: pass
                else:
                    try:
                        os.makedirs(os.path.dirname(CHATBOTS_MUTED_FLAG), exist_ok=True)
                        with open(CHATBOTS_MUTED_FLAG, "w") as f: f.write(f"MUTED at {time.time()}\n")
                    except: pass
                    try:
                        with open(BOTS_PAUSED_FLAG, "w") as f: f.write(f"MUTED at {time.time()}\n")
                    except: pass
                out_msg = json.dumps({
                    "type": "GLOBAL_CHATBOTS_TOGGLE",
                    "enabled": target_state,
                    "system": global_system_state
                })
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                await broadcast_state(force_global=True)
                continue
                    
            if data.get("type") in ["MEDIA_OVERRIDE", "broadcast_media"]:
                out_msg = json.dumps(data)
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                continue

            if data.get("type") == "NARRATIVE_INJECTION":
                narrative_text = data.get("narrative") or data.get("context") or data.get("text") or ""
                target_room = data.get("target_game_pk", "GLOBAL")
                out_msg = json.dumps(data)
                for c in list(clients):
                    try: await c.send(out_msg)
                    except: pass
                ctx_msg = json.dumps({
                    "type": "update_context",
                    "context": narrative_text,
                    "target_game_pk": target_room
                })
                for c in list(clients):
                    try: await c.send(ctx_msg)
                    except: pass
                if narrative_text:
                    chat_msg = json.dumps({
                        "type": "CHAT_MESSAGE",
                        "user": "PRODUCER",
                        "color": "#F59E0B",
                        "text": f"🎙️ [NARRATIVE DIRECTIVE] {narrative_text}",
                        "room": target_room,
                        "target_game_pk": target_room,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                    for c in list(clients):
                        try: await c.send(chat_msg)
                        except: pass
                continue

            # Pass all new Claude Wardy v2 UI events and WebRTC signaling transparently to backend bots/clients
            if data.get("type") in ["persona_config", "persona_strike", "custom_prompt", "boggs_level", "sim_speed", "trigger_event", "switch_game", "update_context", "inject_context", "TMI_ANOMALY", "hot_take_rant", "HOLOLINK_REQUEST", "WEBRTC_OFFER", "WEBRTC_ANSWER", "WEBRTC_ICE_CANDIDATE", "HOLOLINK_END", "outrage_proxy_deployed", "MULTIVERSE_PREP", "MULTIVERSE_SETTLE", "CMD_SIT_DOWN", "TACTILE_TRIGGER", "MEDIA_OVERRIDE", "NARRATIVE_INJECTION", "broadcast_media", "KINETIC_TRIGGER", "media_trigger"]:
                out_msg = json.dumps(data)
                for c in list(clients):
                    try: 
                        await c.send(out_msg)
                    except: 
                        pass
    except Exception as e:
        print("Disconnection:", e)
    finally:
        if ws in clients: clients.remove(ws)

import uvicorn
from fastapi import FastAPI, WebSocket, Request, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import time

class ChatExportData(BaseModel):
    markdown_content: str

class HoloDexDecodeRequest(BaseModel):
    prompt: str
    vibe: str

import sqlite3
import uuid
import subprocess

# DB_PATH resolved dynamically in global scope at top of file

from fastapi.middleware.cors import CORSMiddleware

# --- FASTAPI PROXY SERVER (PORT 8000) ---
fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Hot Takes service router (POST /api/hot_take, POST /api/hot_take/dub, GET /api/hot_take/voices)
import sys as _sys
_sys.path.insert(0, os.path.dirname(__file__))
from hot_takes_service import router as hot_takes_router
fastapi_app.include_router(hot_takes_router)

# Register Game Log Export router (GET /api/game-log/export/{game_pk}, /games, /chat, /plays)
try:
    from game_log_export_api import router as _game_log_router
    fastapi_app.include_router(_game_log_router)
    print("✅ Game log export routes mounted on /api/game-log/*")
except Exception as _gl_err:
    print(f"⚠️  Game log export routes NOT mounted: {_gl_err}")

# Register CMDB, Personas, and Auth routers for ServiceNow table parity
try:
    from routers.cmdb import router as _cmdb_router
    fastapi_app.include_router(_cmdb_router)
    print("✅ CMDB routes mounted on /api/now/table/*")
except Exception as _cmdb_err:
    print(f"⚠️  CMDB routes NOT mounted: {_cmdb_err}")

try:
    from routers.personas import router as _personas_router
    fastapi_app.include_router(_personas_router)
    print("✅ Personas routes mounted on /api/personas/* and /api/persona_image/*")
except Exception as _pers_err:
    print(f"⚠️  Personas routes NOT mounted: {_pers_err}")

try:
    from routers.auth import router as _auth_router
    fastapi_app.include_router(_auth_router)
    print("✅ Auth routes mounted on /api/auth/*")
except Exception as _auth_err:
    print(f"⚠️  Auth routes NOT mounted: {_auth_err}")

try:
    from routers.fanstack import router as _fanstack_router, set_poll_ws_broadcast_callback
    fastapi_app.include_router(_fanstack_router)
    
    async def _relay_poll_ws_broadcast(event_data: dict):
        target_room = str(event_data.get("room_id") or "GLOBAL")
        msg = json.dumps(event_data)
        for c in list(clients):
            if ws_rooms.get(c, "GLOBAL") == "POLLER":
                continue
            c_room = ws_rooms.get(c, "GLOBAL")
            if target_room == "GLOBAL" or c_room == "GLOBAL" or c_room == target_room:
                try:
                    await c.send(msg)
                except Exception:
                    pass
                    
    set_poll_ws_broadcast_callback(_relay_poll_ws_broadcast)
    print("✅ FanStack routes mounted on /api/fanstack/* with Poll WS broadcast callback")
except Exception as _fs_err:
    print(f"⚠️  FanStack routes NOT mounted: {_fs_err}")

# Ensure hot_takes table exists
def _ensure_hot_takes_table():
    try:
        _c = get_db(row_factory=False)
        _c.execute("""
            CREATE TABLE IF NOT EXISTS hot_takes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                persona    TEXT NOT NULL,
                topic      TEXT,
                response   TEXT NOT NULL,
                engine     TEXT,
                room_id    TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        _c.commit()
        _c.close()
    except Exception as _e:
        print(f"[STARTUP] hot_takes table init failed: {_e}")
_ensure_hot_takes_table()

# Persistent Swarm State Registry for "Bring the Gang Along" protocol
sports_session = {
    "active_session_id": "session_clio_sports_active",
    "persistent_advocate_registry": [
        "persona_proper_pinter",
        "persona_expected_tears",
        "persona_ultra_nip",
        "persona_kit_collector_99"
    ],
    "historical_session_thread": [],
    "current_ingress_stream": ""
}

@fastapi_app.get("/api/session/active-stream")
async def api_get_active_stream():
    """
    Retrieve the current active session state and ingress stream PK.
    """
    return {
        "status": "success",
        "game_pk": sports_session["current_ingress_stream"] or None,
        "session": sports_session
    }

@fastapi_app.post("/api/session/swap-stream")
async def api_swap_stream(request: Request):
    """
    State-preservative route handler to hot-swap telemetry stream
    while preserving active advocate room roster in memory.
    """
    # [Hoisted to header] import json
    data = await request.json()
    target_game_pk = str(data.get("target_game_pk", data.get("target_stream", "")))
    if not target_game_pk:
        return {"status": "error", "message": "target_game_pk/target_stream is required"}
    
    bring_gang = bool(data.get("bring_gang", False))
    
    # 1. Update in-memory session current ingress stream
    sports_session["current_ingress_stream"] = target_game_pk
    
    # 2. Add to historical session thread
    if target_game_pk not in sports_session["historical_session_thread"]:
        sports_session["historical_session_thread"].append(target_game_pk)
        
    # 3. Carry over active advocate personas to the new target room in the database
    if bring_gang:
        try:
            # [Hoisted to header] import sqlite3 as _sq, uuid as _uuid
            con = _sq.connect(DB_PATH)
            c = con.cursor()
            
            # Get active personas from the previous current_ingress_stream (if exists and has any)
            prev_stream = data.get("previous_game_pk", "")
            if not prev_stream:
                # Fallback: get any active game room with personas
                c.execute("SELECT DISTINCT game_pk FROM game_persona WHERE seat_state = 'active' LIMIT 1")
                row = c.fetchone()
                if row:
                    prev_stream = row[0]
                    
            if prev_stream and prev_stream != target_game_pk:
                # Fetch active personas in the previous room, along with their assigned_to team from cmdb_ci
                c.execute("""
                    SELECT gp.persona_id, c.assigned_to 
                    FROM game_persona gp
                    LEFT JOIN cmdb_ci c ON gp.persona_id = c.sys_id
                    WHERE gp.game_pk = ? AND gp.seat_state = 'active'
                """, (prev_stream,))
                rows = c.fetchall()
                
                # Filter for global/gang advocates (assigned_to is 'GLOBAL' or empty, or in the persistent registry)
                # Standard MLB teams are 3-letter uppercase codes (NYM, PHI, PIT, CIN, etc.)
                global_active_ids = []
                for p_id, assigned_to in rows:
                    assigned_to_upper = str(assigned_to).upper().strip() if assigned_to else ""
                    is_persistent = p_id in sports_session["persistent_advocate_registry"]
                    is_global = assigned_to_upper in ('GLOBAL', '') or (len(assigned_to_upper) != 3 and assigned_to_upper != 'UFL')
                    if is_persistent or is_global:
                        global_active_ids.append(p_id)
                        
                if global_active_ids:
                    # Find all active personas in the target room
                    c.execute("""
                        SELECT gp.persona_id, c.assigned_to 
                        FROM game_persona gp
                        LEFT JOIN cmdb_ci c ON gp.persona_id = c.sys_id
                        WHERE gp.game_pk = ? AND gp.seat_state = 'active'
                    """, (target_game_pk,))
                    target_rows = c.fetchall()
                    
                    # Identify which ones in the target room are global/gang advocates
                    global_target_ids = []
                    for p_id, assigned_to in target_rows:
                        assigned_to_upper = str(assigned_to).upper().strip() if assigned_to else ""
                        is_persistent = p_id in sports_session["persistent_advocate_registry"]
                        is_global = assigned_to_upper in ('GLOBAL', '') or (len(assigned_to_upper) != 3 and assigned_to_upper != 'UFL')
                        if is_persistent or is_global:
                            global_target_ids.append(p_id)
                    
                    # Remove only the existing global personas in the target room first to avoid duplicates
                    # This explicitly PRESERVES the target room's native team-specific personas!
                    if global_target_ids:
                        placeholders = ', '.join(['?'] * len(global_target_ids))
                        c.execute(
                            f"DELETE FROM game_persona WHERE game_pk = ? AND persona_id IN ({placeholders})",
                            [target_game_pk] + global_target_ids
                        )
                    
                    # Insert the carried-over global personas into the target room!
                    for p_id in global_active_ids:
                        # Double-check to avoid duplicates
                        c.execute("SELECT 1 FROM game_persona WHERE game_pk = ? AND persona_id = ?", (target_game_pk, p_id))
                        if not c.fetchone():
                            c.execute(
                                "INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')",
                                (_uuid.uuid4().hex, target_game_pk, p_id)
                            )
                    
                    # Ensure all active game_persona seats for target game are active=1 in sys_user
                    c.execute("""
                        UPDATE sys_user 
                        SET active = 1 
                        WHERE sys_id IN (
                            SELECT persona_id 
                            FROM game_persona 
                            WHERE game_pk = ? AND seat_state = 'active'
                        )
                    """, (target_game_pk,))
                    con.commit()
                    print(f"[SWAP-STREAM] Carried over {len(global_active_ids)} global/gang personas from room {prev_stream} to {target_game_pk} (preserved native team advocates)")
            con.close()
        except Exception as db_err:
            print(f"[SWAP-STREAM] Database persona carryover warning: {db_err}")
    else:
        print(f"[SWAP-STREAM] Optional carryover skipped: bring_gang = False (preserved rosters)")
        try:
            # [Hoisted to header] import sqlite3 as _sq
            con = _sq.connect(DB_PATH)
            c = con.cursor()
            # Fetch active personas in the target room
            c.execute("""
                SELECT gp.persona_id, c.assigned_to 
                FROM game_persona gp
                LEFT JOIN cmdb_ci c ON gp.persona_id = c.sys_id
                WHERE gp.game_pk = ? AND gp.seat_state = 'active'
            """, (target_game_pk,))
            target_rows = c.fetchall()
            
            # Identify global/gang advocates
            global_target_ids = []
            for p_id, assigned_to in target_rows:
                assigned_to_upper = str(assigned_to).upper().strip() if assigned_to else ""
                is_persistent = p_id in sports_session["persistent_advocate_registry"]
                is_global = assigned_to_upper in ('GLOBAL', '') or (len(assigned_to_upper) != 3 and assigned_to_upper != 'UFL')
                if is_persistent or is_global:
                    global_target_ids.append(p_id)
            
            # Delete those global personas from the target room
            if global_target_ids:
                placeholders = ', '.join(['?'] * len(global_target_ids))
                c.execute(
                    f"DELETE FROM game_persona WHERE game_pk = ? AND persona_id IN ({placeholders})",
                    [target_game_pk] + global_target_ids
                )
            
            # Ensure all remaining active game_persona seats for target game are active=1 in sys_user
            c.execute("""
                UPDATE sys_user 
                SET active = 1 
                WHERE sys_id IN (
                    SELECT persona_id 
                    FROM game_persona 
                    WHERE game_pk = ? AND seat_state = 'active'
                )
            """, (target_game_pk,))
            con.commit()
            if global_target_ids:
                print(f"[SWAP-STREAM] Cleaned up {len(global_target_ids)} global advocates from target room {target_game_pk}")
            con.close()
        except Exception as db_err:
            print(f"[SWAP-STREAM] Database cleanup warning: {db_err}")
        
    # Synchronize in-memory presence cache (WO0010160)
    RoomRosterRegistry.hydrate_from_db(target_game_pk)
    if 'prev_stream' in locals() and prev_stream:
        RoomRosterRegistry.hydrate_from_db(prev_stream)

    # 4. Broadcast the hot-swap event (GAME_SWITCHED) to all connected websocket clients
    ws_msg = json.dumps({
        "type": "GAME_SWITCHED",
        "game_pk": target_game_pk,
        "is_hot_swap": True,
        "session_id": sports_session["active_session_id"]
    })
    
    success_count = 0
    for cl in list(clients):
        try:
            await cl.send(ws_msg)
            success_count += 1
        except:
            pass
            
    print(f"[SWAP-STREAM] Swapped active stream to {target_game_pk}. Broadcasted to {success_count} clients.")
    
    return {
        "status": "success",
        "message": f"Hot-swapped to stream {target_game_pk}",
        "session": sports_session
    }

# Also wire hot_takes DB persistence INTO hot_takes_service
@fastapi_app.get("/api/hot_takes")
async def get_hot_takes(persona: str = None, limit: int = 50):
    """Retrieve saved hot takes from the DB, optionally filtered by persona."""
    con = get_db()
    cur = con.cursor()
    if persona:
        cur.execute("SELECT * FROM hot_takes WHERE persona = ? ORDER BY created_at DESC LIMIT ?", (persona, limit))
    else:
        cur.execute("SELECT * FROM hot_takes ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return {"hot_takes": rows}

# Process Tracking
bot_process = None
telemetry_process = None

@fastapi_app.post("/api/holodex/decode")
async def decode_holodex_prompt(req: HoloDexDecodeRequest):
    # Sovereign Bro Decoder Logic Wrapper
    vibe_map = {
        "1990s Felt Puppet": "1990s physical felt puppet aesthetic, practical effects, Jim Henson style, slight VHS grain",
        "Cinematic Broadcast": "Cinematic 8k broadcast quality, telephoto lens, professional lighting, photorealistic",
        "Action Cam": "GoPro action cam POV, wide angle, dynamic motion, chaotic blur, high energy",
        "Gritty Noir": "High contrast black and white, gritty 1940s film noir, dramatic shadows, rain-slicked surfaces",
        "Hyper-Realistic": "Unreal Engine 5 render style, hyper-realistic, ray tracing, octane render, insanely detailed",
        "Retro 8-Bit": "Retro 8-bit pixel art style, flat colors, low resolution aesthetic, arcade vibe",
        "Surreal Anime": "Studio Ghibli inspired surreal anime style, vibrant pastel colors, ethereal lighting"
    }
    vibe_enhancement = vibe_map.get(req.vibe, req.vibe)
    decoded_prompt = f"[{req.vibe.upper()} OVERRIDE] {req.prompt}. Aesthetic injection: {vibe_enhancement}. Masterpiece, best quality, highly detailed."
    
    return {"decoded_prompt": decoded_prompt}


class HoloDexExpandRequest(BaseModel):
    prompt: str
    vibe: str = "Cinematic"

@fastapi_app.post("/api/holodex/expand_prompt")
async def expand_holodex_prompt(req: HoloDexExpandRequest):
    """
    Expands raw user prompt using Gemini API (if GEMINI_API_KEY is present) or smart template enhancement.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt_instruction = (
                f"You are the HoloDex Reality Synthesis Prompt Expansion Engine. "
                f"Expand the following scene prompt into a vivid, visually rich 2-sentence description "
                f"optimized for AI image generation in the '{req.vibe}' aesthetic style.\n\n"
                f"Original Prompt: {req.prompt}"
            )
            response = await asyncio.to_thread(model.generate_content, prompt_instruction)
            if response and response.text:
                return {"status": "success", "expanded_prompt": response.text.strip()}
        except Exception as e:
            print(f"[HOLODEX GEMINI EXPAND WARNING] {e}")

    # Fallback smart enhancement if Gemini Key is not configured
    vibe_map = {
        "1990s Felt Puppet": "1990s physical felt puppet aesthetic, practical effects, Jim Henson style, slight VHS grain",
        "Cinematic Broadcast": "Cinematic 8k broadcast quality, telephoto lens, professional lighting, photorealistic",
        "Action Cam": "GoPro action cam POV, wide angle, dynamic motion, chaotic blur, high energy",
        "Gritty Noir": "High contrast black and white, gritty 1940s film noir, dramatic shadows, rain-slicked surfaces",
        "Hyper-Realistic": "Unreal Engine 5 render style, hyper-realistic, ray tracing, octane render, insanely detailed",
        "Retro 8-Bit": "Retro 8-bit pixel art style, flat colors, low resolution aesthetic, arcade vibe",
        "Surreal Anime": "Studio Ghibli inspired surreal anime style, vibrant pastel colors, ethereal lighting"
    }
    vibe_enhancement = vibe_map.get(req.vibe, req.vibe)
    expanded = f"{req.prompt}. Rendered with cinematic atmospheric depth, dramatic rim lighting, dynamic composition, and {vibe_enhancement}. Masterpiece 8k render."
    return {"status": "success", "expanded_prompt": expanded}


@fastapi_app.get("/api/holodex/vault")
async def get_holodex_vault(campaign_id: str = None, limit: int = 50, search: str = None):
    """Retrieve synthesized campaign assets from sys_holodex_asset DB table."""
    try:
        con = get_db()
        cur = con.cursor()
        query = "SELECT * FROM sys_holodex_asset"
        params = []
        where_clauses = []
        if campaign_id and campaign_id != "ALL":
            where_clauses.append("campaign_id = ?")
            params.append(campaign_id)
        if search:
            where_clauses.append("(prompt LIKE ? OR title LIKE ? OR vibe LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term, term])
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        return {"status": "success", "assets": rows}
    except Exception as e:
        print(f"[HOLODEX VAULT GET ERROR] {e}")
        return {"status": "error", "message": str(e), "assets": []}


class HoloDexSynthesizeRequest(BaseModel):
    prompt: str
    vibe: str = "Cinematic"
    reference_image_a: str = None
    reference_image_b: str = None
    campaign_id: str = "GLOBAL"
    room_id: str = "GLOBAL"

@fastapi_app.post("/api/holodex/synthesize")
async def synthesize_holodex_image(req: HoloDexSynthesizeRequest):
    # [Hoisted to header] import urllib.parse
    # [Hoisted to header] import uuid
    # [Hoisted to header] import json
    
    vibe_map = {
        "1990s Felt Puppet": "1990s physical felt puppet aesthetic, practical effects, Jim Henson style, slight VHS grain",
        "Cinematic Broadcast": "Cinematic 8k broadcast quality, telephoto lens, professional lighting, photorealistic",
        "Action Cam": "GoPro action cam POV, wide angle, dynamic motion, chaotic blur, high energy",
        "Gritty Noir": "High contrast black and white, gritty 1940s film noir, dramatic shadows, rain-slicked surfaces",
        "Hyper-Realistic": "Unreal Engine 5 render style, hyper-realistic, ray tracing, octane render, insanely detailed",
        "Retro 8-Bit": "Retro 8-bit pixel art style, flat colors, low resolution aesthetic, arcade vibe",
        "Surreal Anime": "Studio Ghibli inspired surreal anime style, vibrant pastel colors, ethereal lighting"
    }
    
    vibe_enhancement = vibe_map.get(req.vibe, req.vibe)
    full_prompt = f"{req.prompt}. Aesthetic: {vibe_enhancement}. Masterpiece, highly detailed."
    
    # URL encode the prompt
    encoded_prompt = urllib.parse.quote(full_prompt)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    
    # Save synthesized image to both 15_FanStack and 26_MARD_Studio static public images directories
    dirs = [
        "/home/james/stacklabs/15_FanStackCreator/public/images",
        "/home/james/stacklabs/26_MARD_Studio/public/images"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    filename = f"holodex_{uuid.uuid4().hex[:8]}.png"
    file_path = os.path.join(dirs[0], filename)
    file_path_studio = os.path.join(dirs[1], filename)
    
    try:
        # Download the generated image using requests
        res = requests.get(pollinations_url, timeout=30)
        if res.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(res.content)
            with open(file_path_studio, "wb") as f:
                f.write(res.content)
            
            # Static URL served by Vite
            media_url = f"/images/{filename}"
            sys_id = uuid.uuid4().hex
            asset_tag = f"HDX-{uuid.uuid4().hex[:6].upper()}"
            title = f"HoloDex Anomaly: {req.prompt[:40]}"

            # 1. Register in sys_holodex_asset DB table!
            try:
                con = get_db(row_factory=False)
                c = con.cursor()
                c.execute("""
                    INSERT INTO sys_holodex_asset (
                        sys_id, asset_tag, title, prompt, expanded_prompt, vibe, media_type,
                        media_url, file_path, reference_image_a, reference_image_b, campaign_id, room_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sys_id, asset_tag, title, req.prompt, full_prompt, req.vibe, "image",
                    media_url, file_path, req.reference_image_a, req.reference_image_b,
                    req.campaign_id or "GLOBAL", req.room_id or "GLOBAL"
                ))
                con.commit()
                con.close()
                print(f"[HOLODEX DB SUCCESS] Persisted asset {asset_tag} into sys_holodex_asset")
            except Exception as dbe:
                print(f"[HOLODEX DB ERROR] {dbe}")

            # 2. Append entry to local holodex_history.json manifest for studio play area
            try:
                history_file = "/home/james/stacklabs/26_MARD_Studio/public/holodex_history.json"
                history_data = []
                if os.path.exists(history_file):
                    try:
                        with open(history_file, "r") as hf:
                            history_data = json.load(hf)
                    except:
                        history_data = []
                
                history_entry = {
                    "sys_id": sys_id,
                    "asset_tag": asset_tag,
                    "title": title,
                    "prompt": req.prompt,
                    "expanded_prompt": full_prompt,
                    "vibe": req.vibe,
                    "media_url": media_url,
                    "campaign_id": req.campaign_id or "GLOBAL",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                history_data.insert(0, history_entry)
                with open(history_file, "w") as hf:
                    json.dump(history_data[:100], hf, indent=2)
            except Exception as hfe:
                print(f"[HOLODEX HISTORY FILE ERROR] {hfe}")
                
            return {
                "status": "success",
                "sys_id": sys_id,
                "asset_tag": asset_tag,
                "mediaUrl": media_url,
                "decoded_prompt": full_prompt,
                "filename": filename
            }
        else:
            return {"status": "error", "message": f"Failed to download image: HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════════════
# STREAM SNIPER NATIVE INGRESS & PROXY
# ═══════════════════════════════════════════════════════════════

SNIPER_DAEMON_URL = "http://127.0.0.1:5056"

@fastapi_app.post("/api/snipe/tail")
async def start_stream_sniper_tail(request: Request):
    """Native Live Stream Chat Ingress — tails YouTube live chat into ws://127.0.0.1:8008 room live_chat_sniper"""
    try:
        data = await request.json()
    except Exception:
        data = {}
    video_id = str(data.get("video_id", "")).strip()
    if not video_id:
        raise HTTPException(status_code=400, detail="No video_id provided")

    # Regex to extract 11-char video ID if full URL was pasted
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', video_id)
    if match:
        video_id = match.group(1)

    output_dir = "/home/james/sovereign_inbox/today"
    os.makedirs(output_dir, exist_ok=True)
    output_md = os.path.join(output_dir, "stream_chat_tail.md")

    # Terminate any existing tail_stream_chat process
    subprocess.run(["pkill", "-f", "tail_stream_chat.py"], capture_output=True)

    # Fetch stream title via yt-dlp asynchronously
    title = "Live Sniper Feed"
    try:
        def _get_title():
            return subprocess.check_output(
                ["/home/james/stacklabs/.venv/bin/yt-dlp", "--get-title", f"https://www.youtube.com/watch?v={video_id}"],
                text=True, timeout=8
            ).strip()
        title = await asyncio.to_thread(_get_title)
    except Exception as e:
        print(f"[SNIPER TAIL] Failed to fetch video title: {e}")

    # Launch background tailing process
    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        "/home/james/stacklabs/scripts/tail_stream_chat.py",
        video_id,
        output_md
    ]
    try:
        proc = subprocess.Popen(cmd)
        print(f"[SNIPER TAIL] Launched tail_stream_chat.py (PID {proc.pid}) for video {video_id}")
        return {
            "status": "success",
            "message": f"Started tailing chat for {video_id}",
            "video_id": video_id,
            "title": title,
            "pid": proc.pid
        }
    except Exception as e:
        print(f"[SNIPER TAIL ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/api/snipe/tail/status")
async def get_stream_sniper_tail_status():
    res = subprocess.run(["pgrep", "-f", "tail_wardy_chat.py"], capture_output=True, text=True)
    pids = res.stdout.strip().split()
    return {"active": len(pids) > 0, "pids": pids}

@fastapi_app.post("/api/snipe/tail/stop")
async def stop_stream_sniper_tail():
    subprocess.run(["pkill", "-f", "tail_wardy_chat.py"], capture_output=True)
    return {"status": "success", "message": "Stopped stream sniper tailing"}

@fastapi_app.post("/api/snipe")
@fastapi_app.post("/api/snipe/{path:path}")
async def snipe_proxy_post(request: Request, path: str = ""):
    """Proxy POST /api/snipe and /api/snipe/* → stream_sniper_daemon:5056"""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length", "transfer-encoding")}
    dest_url = f"{SNIPER_DAEMON_URL}/api/snipe/{path}" if path else f"{SNIPER_DAEMON_URL}/api/snipe"
    try:
        resp = await asyncio.to_thread(
            lambda: requests.post(dest_url, data=body, headers=headers, timeout=15)
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("Content-Type", "application/json"))
    except Exception as e:
        print(f"[SNIPE PROXY ERROR] {type(e).__name__}: {e}")
        return Response(content=json.dumps({"error": str(e), "type": type(e).__name__}), status_code=502, media_type="application/json")

@fastapi_app.get("/api/snipe")
@fastapi_app.get("/api/snipe/{path:path}")
async def snipe_proxy_get(request: Request, path: str = ""):
    """Proxy GET /api/snipe and /api/snipe/* → stream_sniper_daemon:5056"""
    dest_url = f"{SNIPER_DAEMON_URL}/api/snipe/{path}" if path else f"{SNIPER_DAEMON_URL}/api/snipe"
    try:
        resp = await asyncio.to_thread(
            lambda: requests.get(dest_url, params=dict(request.query_params), timeout=15)
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("Content-Type", "application/json"))
    except Exception as e:
        return Response(content=json.dumps({"error": str(e), "type": type(e).__name__}), status_code=502, media_type="application/json")

@fastapi_app.delete("/api/snipe/{path:path}")
async def snipe_proxy_delete(path: str, request: Request):
    """Proxy DELETE /api/snipe/* → stream_sniper_daemon:5056"""
    dest_url = f"{SNIPER_DAEMON_URL}/api/snipe/{path}"
    try:
        resp = await asyncio.to_thread(
            lambda: requests.delete(dest_url, timeout=15)
        )
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("Content-Type", "application/json"))
    except Exception as e:
        return Response(content=json.dumps({"error": str(e), "type": type(e).__name__}), status_code=502, media_type="application/json")

@fastapi_app.get("/api/vertex_burn/status")
async def get_vertex_status():
    # [Hoisted to header] import os
    is_on = os.path.exists('/home/james/stacklabs/config/vertex_burn.on')
    return {"vertex_burn_enabled": is_on}

@fastapi_app.post("/api/vertex_burn/toggle")
async def toggle_vertex():
    # [Hoisted to header] import os
    file_path = '/home/james/stacklabs/config/vertex_burn.on'
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "success", "vertex_burn_enabled": False, "message": "Vertex Burn Mode Disabled"}
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write("ON")
        return {"status": "success", "vertex_burn_enabled": True, "message": "Vertex Burn Mode Enabled"}

@fastapi_app.get("/api/webslinger_events")
async def get_webslinger_events():
    """Retrieve all active webslinger templates from sys_webslinger_event."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        con.row_factory = _sq.Row
        c = con.cursor()
        c.execute("""
            SELECT id, event_name, payload_template, default_duration_ms, active_status
            FROM sys_webslinger_event
            WHERE active_status = 1
        """)
        rows = [dict(r) for r in c.fetchall()]
        con.close()
        return {"status": "success", "events": rows}
    except Exception as e:
        return {"status": "error", "message": str(e), "events": []}

class TelemetryRuleCreate(BaseModel):
    trigger_rule_name: str
    statcast_event_type: str
    telemetry_field: str
    operator_comparison: str
    comparison_value: str
    batting_team_filter: str = "NYM"
    target_webslinger_event_id: int
    is_automated_ingress: int = 1
    active_status: int = 1

class TelemetryRuleUpdate(BaseModel):
    trigger_rule_name: str = None
    statcast_event_type: str = None
    telemetry_field: str = None
    operator_comparison: str = None
    comparison_value: str = None
    batting_team_filter: str = None
    target_webslinger_event_id: int = None
    is_automated_ingress: int = None
    active_status: int = None

@fastapi_app.get("/api/tmi_telemetry_map")
async def get_tmi_telemetry_map():
    """Retrieve all telemetry rules from sys_tmi_telemetry_map."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        con.row_factory = _sq.Row
        c = con.cursor()
        c.execute("""
            SELECT id, trigger_rule_name, statcast_event_type, telemetry_field, 
                   operator_comparison, comparison_value, batting_team_filter, 
                   target_webslinger_event_id, is_automated_ingress, active_status
            FROM sys_tmi_telemetry_map
        """)
        rows = [dict(r) for r in c.fetchall()]
        con.close()
        return {"status": "success", "rules": rows}
    except Exception as e:
        return {"status": "error", "message": str(e), "rules": []}

@fastapi_app.post("/api/tmi_telemetry_map")
async def create_tmi_telemetry_rule(rule: TelemetryRuleCreate):
    """Create a new telemetry mapping rule."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        c = con.cursor()
        c.execute("""
            INSERT INTO sys_tmi_telemetry_map (
                trigger_rule_name, statcast_event_type, telemetry_field, 
                operator_comparison, comparison_value, batting_team_filter, 
                target_webslinger_event_id, is_automated_ingress, active_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.trigger_rule_name, rule.statcast_event_type, rule.telemetry_field,
            rule.operator_comparison, rule.comparison_value, rule.batting_team_filter,
            rule.target_webslinger_event_id, rule.is_automated_ingress, rule.active_status
        ))
        con.commit()
        new_id = c.lastrowid
        con.close()
        return {"status": "success", "id": new_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.put("/api/tmi_telemetry_map/{rule_id}")
async def update_tmi_telemetry_rule(rule_id: int, rule: TelemetryRuleUpdate):
    """Update an existing telemetry mapping rule."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        c = con.cursor()
        
        fields = []
        params = []
        for key, val in rule.dict(exclude_unset=True).items():
            fields.append(f"{key} = ?")
            params.append(val)
            
        if not fields:
            con.close()
            return {"status": "error", "message": "No fields to update"}
            
        params.append(rule_id)
        query = f"UPDATE sys_tmi_telemetry_map SET {', '.join(fields)} WHERE id = ?"
        c.execute(query, params)
        con.commit()
        con.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.delete("/api/tmi_telemetry_map/{rule_id}")
async def delete_tmi_telemetry_rule(rule_id: int):
    """Delete a telemetry mapping rule."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        c = con.cursor()
        c.execute("DELETE FROM sys_tmi_telemetry_map WHERE id = ?", (rule_id,))
        con.commit()
        con.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@fastapi_app.post("/api/tmi_telemetry_map/toggle_all")
async def toggle_all_tmi_telemetry_rules(enabled: bool):
    """Master toggle to enable/disable automated ingress database-wide."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        c = con.cursor()
        val = 1 if enabled else 0
        c.execute("UPDATE sys_tmi_telemetry_map SET is_automated_ingress = ?", (val,))
        con.commit()
        con.close()
        return {"status": "success", "is_automated_ingress": val}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class GoveeTriggerPayload(BaseModel):
    preset: str = "default"
    event_type: str = None

@fastapi_app.post("/api/govee/trigger")
async def trigger_govee_hardware(payload: GoveeTriggerPayload):
    """Dispatches UDP broadcast packets to all local Govee smart light hardware devices."""
    import socket
    import threading
    
    ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
    preset = payload.preset or payload.event_type or "default"
    
    # Preset RGB definitions
    color_map = {
        "ORANGE_BLUE_STROBE": {"r": 255, "g": 85, "b": 0},
        "CYAN_PULSE": {"r": 0, "g": 229, "b": 255},
        "RED_KLAXON": {"r": 255, "g": 0, "b": 30},
        "RED_ALERT": {"r": 255, "g": 0, "b": 30},
        "GOLD_BURST": {"r": 255, "g": 215, "b": 0},
        "VICTORY_SWEEP": {"r": 0, "g": 255, "b": 128},
        "AMBER_PULSE": {"r": 255, "g": 160, "b": 0},
        "strikeout": {"r": 255, "g": 215, "b": 0},
        "home_run": {"r": 255, "g": 85, "b": 0},
        "default": {"r": 0, "g": 255, "b": 204}
    }
    rgb = color_map.get(preset, {"r": 0, "g": 255, "b": 204})

    def _fire_udp():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)
            # Govee UDP API packet
            msg_turn_on = json.dumps({"msg": {"cmd": "turn", "data": {"value": 1}}}).encode('utf-8')
            msg_color = json.dumps({"msg": {"cmd": "colorwc", "data": {"color": rgb}}}).encode('utf-8')
            for ip in ips:
                try:
                    sock.sendto(msg_turn_on, (ip, 4003))
                    sock.sendto(msg_color, (ip, 4003))
                except Exception:
                    pass
            sock.close()
        except Exception as e:
            print(f"[GOVEE UDP ERROR] {e}")

    threading.Thread(target=_fire_udp, daemon=True).start()
    return {"status": "success", "preset": preset, "rgb": rgb, "nodes": len(ips)}

@fastapi_app.post("/api/media/inject")
async def inject_media(file: UploadFile = File(...), room_id: str = "GLOBAL"):
    """Accept drag-and-drop SVG file uploads, save to temporary folder, write manifest.json, run ingest_media_assets.py as a subprocess, and broadcast media_injection WS."""
    # [Hoisted to header] import uuid as _uuid
    # [Hoisted to header] import shutil
    # [Hoisted to header] import subprocess
    # [Hoisted to header] import json
    # [Hoisted to header] import os
    
    if not file.filename.endswith(".svg"):
        raise HTTPException(status_code=400, detail="Only SVG files are supported.")
        
    try:
        temp_dir = f"/tmp/media_inject_{_uuid.uuid4().hex}"
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        with open(file_path, "r", encoding="utf-8") as f:
            svg_data = f.read()
            
        manifest = {
            "scenarios": [
                {
                    "num": 1,
                    "name": file.filename,
                    "raw_file": file.filename,
                    "processed_file": file.filename,
                    "expression_key": "injected_svg",
                    "expression_reference": "injected_svg",
                    "vibe": "playcall_desk"
                }
            ]
        }
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)
            
        cmd = [
            "python3",
            "/home/james/stacklabs/scripts/ingest_media_assets.py",
            "--dir", temp_dir,
            "--ticket", "STRY-06152026-PLAYCALL-DESK",
            "--advocate", "playcall",
            "--category", "Playcall Injections"
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            stderr_str = stderr.decode('utf-8', errors='ignore')
            print(f"[MEDIA INJECT ERROR] Ingestion failed: {stderr_str}")
            raise HTTPException(status_code=500, detail=f"Asset ingestion failed: {stderr_str}")
            
        ws_msg = json.dumps({
            "type": "media_injection",
            "svg_data": svg_data,
            "filename": file.filename,
            "room_id": room_id
        })
        for c in list(clients):
            if ws_rooms.get(c, "GLOBAL") == room_id or room_id == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
                try:
                    await c.send(ws_msg)
                except:
                    pass
                    
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"[MEDIA INJECT WARNING] Failed to cleanup temp dir {temp_dir}: {e}")
            
        return {"status": "success", "message": "SVG Injected successfully"}
    except Exception as e:
        print(f"[MEDIA INJECT ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════
# FLOW LIVE INTEGRATION NODE (sys_media_asset tables)
# ═══════════════════════════════════════════════════════════════

class FlowAssetCreate(BaseModel):
    title: str
    category: str
    prompt: str

@fastapi_app.get("/api/flow/assets")
async def get_flow_assets():
    """Retrieve all assets registered in the sys_media_asset CMDB table."""
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH)
        con.row_factory = _sq.Row
        c = con.cursor()
        c.execute("""
            SELECT sys_id, asset_tag, name, file_name, file_path, file_size_bytes, category, status, created_at
            FROM sys_media_asset
            ORDER BY created_at DESC
        """)
        rows = [dict(r) for r in c.fetchall()]
        con.close()
        return {"status": "success", "assets": rows}
    except Exception as e:
        return {"status": "error", "message": str(e), "assets": []}

@fastapi_app.post("/api/flow/assets")
async def create_flow_asset(req: FlowAssetCreate):
    """Dynamically register a new synthesized Flow asset in the CMDB."""
    # [Hoisted to header] import sqlite3 as _sq
    # [Hoisted to header] import uuid as _uuid
    # [Hoisted to header] import hashlib as _hashlib
    try:
        con = _sq.connect(DB_PATH)
        c = con.cursor()
        
        sys_id = str(_uuid.uuid4()).replace('-', '')
        
        c.execute("SELECT asset_tag FROM sys_media_asset ORDER BY asset_tag DESC LIMIT 1")
        row = c.fetchone()
        tag = "FS-MED-00001"
        if row:
            last_tag = row[0]
            # [Hoisted to header] import re
            match = re.search(r'FS-MED-(\d+)', last_tag)
            if match:
                tag = f"FS-MED-{(int(match.group(1)) + 1):05d}"
                
        file_name = f"flow_{sys_id[:8]}.png"
        file_path = f"/home/james/stacklabs/media_vault/01_Assets/Catnip_Wars/{file_name}"
        md5_hash = _hashlib.md5(sys_id.encode('utf-8')).hexdigest()
        
        c.execute("""
            INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sys_id, tag, req.title, file_name, file_path, 1024, "image/png", req.category, f"Synced: {req.prompt[:100]}", md5_hash))
        con.commit()
        con.close()
        
        broadcast_msg = json.dumps({
            "type": "FLOW_ASSET_SYNC",
            "asset": {
                "sys_id": sys_id,
                "asset_tag": tag,
                "name": req.title,
                "file_name": file_name,
                "file_path": file_path,
                "category": req.category,
                "status": f"Synced: {req.prompt}",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
        for cl in list(clients):
            try: await cl.send(broadcast_msg)
            except: pass
            
        return {"status": "success", "asset": {
            "sys_id": sys_id,
            "asset_tag": tag,
            "name": req.title,
            "file_name": file_name,
            "file_path": file_path,
            "category": req.category,
            "status": f"Synced: {req.prompt}"
        }}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ═══════════════════════════════════════════════════════════════
# ROOM BUILDER API  (absorbed from scruffys_bar_server.py)
# ═══════════════════════════════════════════════════════════════

@fastapi_app.get("/api/all_personas")
async def api_all_personas():
    """All available personas for the Room Builder modal. Only returns valid AI personas with a team assignment."""
    con = _sq.connect(DB_PATH)
    c = con.cursor()
    c.execute("""
        SELECT p.id as sys_id, p.user_name, p.team, p.deep_lore, p.system_prompt, p.behavior_notes, p.governance, p.color, p.avatar_url, p.display_name, u.active, p.cadence, p.boggs_level
        FROM persona p
        LEFT JOIN sys_user u ON u.sys_id = p.id
        WHERE p.team IS NOT NULL AND p.team != '' AND p.team NOT IN ('golf_room')
        ORDER BY p.team, p.user_name
    """)
    rows = c.fetchall()
    con.close()
    
    clone_pattern = _re.compile(r'_\d{6}$')
    personas = [
        {
            "sys_id": r[0],
            "user_name": r[1],
            "team": r[2],
            "deep_lore": r[3],
            "system_prompt": r[4],
            "behavior_notes": r[5],
            "governance": r[6],
            "color": r[7],
            "avatar_url": r[8],
            "display_name": r[9],
            "active": r[10] if r[10] is not None else 1,
            "email_alias": "",
            "cadence": r[11],
            "boggs_level": r[12],
            "u_visual_style": "2D_ORGANIC_TOON_CARTOON",
            "avatar_prompt": "",
            "character_map_prompt": "",
            "u_deployment_zone": "GLOBAL"
        }
        for r in rows
        if not clone_pattern.search(r[1])
    ]
    return {"personas": personas}


@fastapi_app.get("/api/room_personas")
@fastapi_app.get("/api/fanstack/roster")
async def api_room_personas(gamePk: str = None, game_pk: str = None, room: str = None, room_id: str = None):
    """Current persona roster for a specific game room.
    Returns personas as @-prefixed strings plus a rich roster array.
    """
    target_pk = str(gamePk or game_pk or room or room_id or "823498")
    # [Hoisted to header] import sqlite3 as _sq
    try:
        con = _sq.connect(DB_PATH, timeout=10.0)
        c = con.cursor()
        c.execute("""
            SELECT p.user_name, p.team, p.color, COALESCE(gp.gemini_tokens, 0), COALESCE(gp.local_tokens, 0),
                   COALESCE(m2m.active_pose_key,
                       (SELECT m2.active_pose_key FROM m2m_persona_room m2 
                        WHERE (m2.persona = p.id OR m2.persona = p.user_name OR m2.persona = (SELECT sys_id FROM sys_user WHERE user_name = p.user_name COLLATE NOCASE)) 
                        AND m2.active_pose_key IS NOT NULL 
                        ORDER BY m2.sys_updated_on DESC LIMIT 1),
                       'front_neutral')
            FROM persona p
            JOIN sys_user u ON u.sys_id = p.id
            LEFT JOIN game_persona gp ON (gp.persona_id = p.id AND gp.game_pk = ?)
            LEFT JOIN m2m_persona_room m2m ON (m2m.room = ? AND (m2m.persona = p.id OR m2m.persona = p.user_name OR m2m.persona = (SELECT sys_id FROM sys_user WHERE user_name = p.user_name COLLATE NOCASE)))
            WHERE ((gp.game_pk = ? AND gp.seat_state = 'active') OR m2m.sys_id IS NOT NULL)
            GROUP BY p.user_name
            ORDER BY p.team, p.user_name
        """, (target_pk, target_pk, target_pk))
        rows = c.fetchall()
        
        # If room has no active seats assigned yet, load top active advocates
        if not rows:
            c.execute("""
                SELECT p.user_name, p.team, p.color, 0, 0,
                       COALESCE(
                           (SELECT m2.active_pose_key FROM m2m_persona_room m2 
                            WHERE (m2.persona = p.id OR m2.persona = p.user_name OR m2.persona = (SELECT sys_id FROM sys_user WHERE user_name = p.user_name COLLATE NOCASE)) 
                            AND m2.active_pose_key IS NOT NULL 
                            ORDER BY m2.sys_updated_on DESC LIMIT 1),
                           'front_neutral')
                FROM persona p
                WHERE p.user_name IS NOT NULL
                ORDER BY CASE WHEN LOWER(p.user_name) = 'barf' THEN 0 ELSE 1 END, p.user_name COLLATE NOCASE
                LIMIT 40
            """)
            rows = c.fetchall()

        c.execute("SELECT gemini_tokens, local_tokens, sys_tokens FROM sport_schedule WHERE game_pk = ?", (target_pk,))
        gt_row = c.fetchone()
        room_gemini = gt_row[0] if gt_row and gt_row[0] else 0
        room_local = gt_row[1] if gt_row and gt_row[1] else 0
        room_sys = gt_row[2] if gt_row and gt_row[2] else 0
        con.close()
        
        persona_strings = [f"@{r[0].lstrip('@')}" for r in rows]
        roster = [{
            "user_name": r[0],
            "team": r[1],
            "color": r[2],
            "gemini_tokens": r[3] or 0,
            "local_tokens": r[4] or 0,
            "active_pose_key": r[5] or "front_neutral",
            "active_sprite_url": f"/api/persona/lookbook/{r[0]}/{r[5] or 'front_neutral'}"
        } for r in rows]
        return {"personas": persona_strings, "roster": roster, "game_pk": target_pk, "room_gemini_tokens": room_gemini, "room_local_tokens": room_local, "room_sys_tokens": room_sys}
    except Exception as err:
        print(f"[api_room_personas] Error: {err}")
        default_advocates = [
            {"user_name": "barf", "team": "NYM", "color": "#FF6B00", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/barf/front_neutral"},
            {"user_name": "UncleStevieStan", "team": "NYM", "color": "#FF6B00", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/UncleStevieStan/front_neutral"},
            {"user_name": "7_train_terry", "team": "NYM", "color": "#FF6B00", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/7_train_terry/front_neutral"},
            {"user_name": "day_game_danny", "team": "TB", "color": "#0d9488", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/day_game_danny/front_neutral"},
            {"user_name": "cash_considerations", "team": "TB", "color": "#0d9488", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/cash_considerations/front_neutral"},
            {"user_name": "champa_bay_charlie", "team": "TB", "color": "#0A0A08", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/champa_bay_charlie/front_neutral"},
            {"user_name": "moxie", "team": "GLOBAL", "color": "#A855F7", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/moxie/front_neutral"},
            {"user_name": "keith", "team": "NYM", "color": "#FF9E0B", "active_pose_key": "front_neutral", "active_sprite_url": "/api/persona/lookbook/keith/front_neutral"}
        ]
        return {"personas": [f"@{a['user_name']}" for a in default_advocates], "roster": default_advocates, "game_pk": target_pk}


# Deprecated file-based upload route removed to resolve endpoint collision.
# All avatar uploads are handled securely by upload_persona_image_blob at line 1053.


@fastapi_app.post("/api/save_room_personas")
async def api_save_room_personas(request: Request):
    """Save persona roster for a game room (Room Builder save action)."""
    # [Hoisted to header] import sqlite3 as _sq, uuid as _uuid
    data = await request.json()
    
    con = _sq.connect(DB_PATH, timeout=30.0)
    c = con.cursor()
    
    # Handle RoomConfigurator incremental update format
    if 'action' in data:
        game_pk = str(data.get('game_pk', ''))
        persona_name = data.get('persona', '')
        action = data.get('action')
        
        if not game_pk or not persona_name:
            con.close()
            return {"status": "error", "message": "game_pk and persona required"}
            
        c.execute("SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE", (persona_name,))
        row = c.fetchone()
        if not row:
            con.close()
            return {"status": "error", "message": "persona not found"}
        persona_id = row[0]
            
        if action == 'add':
            c.execute("SELECT id FROM game_persona WHERE game_pk = ? AND persona_id = ?", (game_pk, persona_id))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?,?,?,'active')",
                    (_uuid.uuid4().hex, game_pk, persona_id)
                )
            c.execute("SELECT sys_id FROM m2m_persona_room WHERE room = ? AND (persona = ? OR persona = ?)", (game_pk, persona_id, persona_name))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?,?,?,?)",
                    (_uuid.uuid4().hex, persona_id, game_pk, f"Deployed to Game {game_pk} via Room Builder")
                )
            RoomRosterRegistry.add_persona(game_pk, persona_name)
        elif action == 'remove':
            c.execute("DELETE FROM game_persona WHERE game_pk = ? AND persona_id = ?", (game_pk, persona_id))
            c.execute("DELETE FROM m2m_persona_room WHERE room = ? AND (persona = ? OR persona = ?)", (game_pk, persona_id, persona_name))
            RoomRosterRegistry.remove_persona(game_pk, persona_name)
            
        con.commit()
        con.close()
        
        # Force chatbots to reload the roster
        sync_msg = json.dumps({"action": "SYNC_DB_PERSONAS", "room_id": game_pk})
        for c in list(clients):
            try: await c.send(sync_msg)
            except: pass
            
        return {"status": "success", "game_pk": game_pk, "action": action, "persona": persona_name}
        
    # Handle WatchPartyConsole bulk update format
    else:
        game_pk = str(data.get('gamePk', ''))
        persona_names = data.get('personas', [])
        
        if not game_pk:
            con.close()
            return {"status": "error", "message": "gamePk required"}
            
        c.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))
        c.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
        inserted = 0
        for name in persona_names:
            c.execute("SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE", (name,))
            row = c.fetchone()
            if row:
                p_id = row[0]
                c.execute(
                    "INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?,?,?,'active')",
                    (_uuid.uuid4().hex, game_pk, p_id)
                )
                c.execute(
                    "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?,?,?,?)",
                    (_uuid.uuid4().hex, p_id, game_pk, f"Deployed to Game {game_pk} via Room Builder")
                )
                inserted += 1
        con.commit()
        con.close()
        
        # Atomically update in-memory cache (WO0010160)
        RoomRosterRegistry.set_roster(game_pk, persona_names)

        # Force chatbots to reload the roster
        sync_msg = json.dumps({"action": "SYNC_DB_PERSONAS", "room_id": game_pk})
        for c in list(clients):
            try: await c.send(sync_msg)
            except: pass
            
        return {"status": "success", "game_pk": game_pk, "inserted": inserted}


@fastapi_app.get("/api/scoreboard")
async def api_scoreboard(gamePk: str):
    """Live scoreboard for a specific game_pk — hits the MLB Stats API."""
    # [Hoisted to header] import urllib.request as _ur
    # [Hoisted to header] import json as _json
    try:
        live_url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        req = _ur.Request(live_url, headers={"User-Agent": "SovereignKnot/1.0"})
        with _ur.urlopen(req, timeout=8) as resp:
            live_res = _json.loads(resp.read().decode("utf-8"))

        game_data = live_res["gameData"]
        live_data = live_res["liveData"]
        linescore = live_data["linescore"]

        away_abbr = game_data["teams"]["away"]["abbreviation"]
        home_abbr = game_data["teams"]["home"]["abbreviation"]
        away_name = game_data["teams"]["away"].get("teamName", away_abbr)
        home_name = game_data["teams"]["home"].get("teamName", home_abbr)

        return {
            "status": game_data["status"]["detailedState"],
            "away": {
                "name": away_abbr,
                "teamName": away_name,
                "runs": linescore["teams"]["away"].get("runs", 0),
                "hits": linescore["teams"]["away"].get("hits", 0),
                "errors": linescore["teams"]["away"].get("errors", 0),
            },
            "home": {
                "name": home_abbr,
                "teamName": home_name,
                "runs": linescore["teams"]["home"].get("runs", 0),
                "hits": linescore["teams"]["home"].get("hits", 0),
                "errors": linescore["teams"]["home"].get("errors", 0),
            },
            "inning": linescore.get("currentInningOrdinal", ""),
            "inningState": linescore.get("inningState", ""),
            "outs": linescore.get("outs", 0),
            "balls": linescore.get("balls", 0),
            "strikes": linescore.get("strikes", 0),
            "innings": linescore.get("innings", []),
            "offense": linescore.get("offense", {}),
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════
# ROLL CALL ROOM ACTIVATION TOGGLES
# ═══════════════════════════════════════════════════════════════

@fastapi_app.post("/api/room/activate")
async def api_activate_room(request: Request):
    """Flip a staged room to active — chatbots start firing."""
    # [Hoisted to header] import sqlite3 as _sq
    data = await request.json()
    game_pk = str(data.get('game_pk', ''))
    if not game_pk:
        return {"status": "error", "message": "game_pk required"}
    con = _sq.connect(DB_PATH, timeout=60.0)
    con.execute("UPDATE sport_schedule SET room_state='active' WHERE game_pk=?", (game_pk,))
    con.execute("UPDATE mlb_schedule SET room_state='active' WHERE game_pk=?", (game_pk,))
    con.execute("UPDATE cmdb_ci_fanstack_room SET room_state='active' WHERE game_pk=?", (game_pk,))
    con.commit()
    con.close()
    
    toggle_msg = json.dumps({"type": "ROOM_DEPLOYMENT_TOGGLE", "game_pk": game_pk, "room_state": "active"})
    for c in list(clients):
        try: await c.send(toggle_msg)
        except: pass
        
    return {"status": "success", "game_pk": game_pk, "room_state": "active"}


@fastapi_app.post("/api/room/deactivate")
async def api_deactivate_room(request: Request):
    """Flip an active room back to staged — chatbots go silent."""
    # [Hoisted to header] import sqlite3 as _sq
    data = await request.json()
    game_pk = str(data.get('game_pk', ''))
    if not game_pk:
        return {"status": "error", "message": "game_pk required"}
    con = _sq.connect(DB_PATH, timeout=60.0)
    con.execute("UPDATE sport_schedule SET room_state='staged' WHERE game_pk=?", (game_pk,))
    con.execute("UPDATE mlb_schedule SET room_state='staged' WHERE game_pk=?", (game_pk,))
    con.execute("UPDATE cmdb_ci_fanstack_room SET room_state='staged' WHERE game_pk=?", (game_pk,))
    con.commit()
    con.close()
    
    toggle_msg = json.dumps({"type": "ROOM_DEPLOYMENT_TOGGLE", "game_pk": game_pk, "room_state": "staged"})
    for c in list(clients):
        try: await c.send(toggle_msg)
        except: pass
        
    return {"status": "success", "game_pk": game_pk, "room_state": "staged"}


@fastapi_app.get("/api/chatbots/status")
async def api_get_chatbots_status():
    """Return global chatbot enable status and active room states."""
    enabled = global_system_state.get("chatbots_enabled", True)
    # [Hoisted to header] import sqlite3 as _sq
    con = _sq.connect(DB_PATH, timeout=10.0)
    con.row_factory = _sq.Row
    try:
        rows = con.execute("SELECT game_pk, room_state FROM sport_schedule WHERE room_state IN ('active', 'staged')").fetchall()
        room_states = {str(r["game_pk"]): r["room_state"] for r in rows}
    except Exception:
        room_states = {}
    finally:
        con.close()
    return {"global_enabled": enabled, "room_states": room_states}


@fastapi_app.post("/api/chatbots/global_toggle")
async def api_toggle_global_chatbots(request: Request = None):
    """
    Toggle or set global chatbot active status.
    When disabled, ALL bot commentary across all rooms is silenced,
    while live Statcast sports telemetry remains 100% active.
    """
    target_state = None
    if request:
        try:
            body = await request.json()
            if "enabled" in body:
                target_state = bool(body["enabled"])
        except Exception:
            pass
            
    if target_state is None:
        target_state = not global_system_state.get("chatbots_enabled", True)
        
    global_system_state["chatbots_enabled"] = target_state
    
    if target_state:
        if os.path.exists(CHATBOTS_MUTED_FLAG):
            try: os.remove(CHATBOTS_MUTED_FLAG)
            except: pass
        if os.path.exists(BOTS_PAUSED_FLAG):
            try: os.remove(BOTS_PAUSED_FLAG)
            except: pass
    else:
        try:
            os.makedirs(os.path.dirname(CHATBOTS_MUTED_FLAG), exist_ok=True)
            with open(CHATBOTS_MUTED_FLAG, "w") as f: f.write(f"MUTED at {time.time()}\n")
        except: pass
        try:
            with open(BOTS_PAUSED_FLAG, "w") as f: f.write(f"MUTED at {time.time()}\n")
        except: pass
        
    out_msg = json.dumps({
        "type": "GLOBAL_CHATBOTS_TOGGLE",
        "enabled": target_state,
        "system": global_system_state
    })
    for c in list(clients):
        try: await c.send(out_msg)
        except: pass
        
    await broadcast_state(force_global=True)
    return {"status": "success", "chatbots_enabled": target_state}

@fastapi_app.post("/api/system/broadcast")
async def api_system_broadcast():
    """Trigger an immediate websocket state broadcast for system/warning updates."""
    await broadcast_state(force_global=True)
    return {"status": "success", "message": "System broadcast triggered"}

@fastapi_app.post("/broadcast")
@fastapi_app.post("/api/broadcast")
async def api_broadcast_generic(request: Request):
    """Generic WebSocket broadcast endpoint for system, chatter policy, and client events."""
    try:
        data = await request.json()
    except Exception:
        data = {"type": "GENERIC_BROADCAST"}
    msg = json.dumps(data)
    for c in list(clients):
        try:
            await c.send(msg)
        except Exception:
            pass
    return {"status": "broadcast_dispatched", "recipients": len(clients), "data": data}

@fastapi_app.post("/api/sports/kinetic/trigger")
async def api_trigger_kinetic_fx(request: Request):
    """
    Triggers a live kinetic particle physics detonation across active game room dashboards.
    Accepts JSON: { "preset": "singularity_plunge", "room": "822932", "config": {...}, ... }
    """
    # [Hoisted to header] import json
    data = await request.json()
    preset = data.get("preset", "singularity_plunge")
    room = str(data.get("room", "822932"))
    
    msg_type = data.get("type", "KINETIC_TRIGGER")
    broadcast_payload = {
        "type": msg_type,
        "preset": preset,
        "room": room,
        "config": data.get("config"),
        "params": data,
        "title": data.get("title"),
        "desc": data.get("desc"),
        "clip_id": data.get("clip_id", preset),
        "tag": data.get("tag", "🗽 LIVE LASER SKY SHOW")
    }
    broadcast_msg = json.dumps(broadcast_payload)
    
    sent_count = 0
    for client in list(clients):
        try:
            await client.send(broadcast_msg)
            sent_count += 1
        except Exception:
            pass
            
    # If broadcast_media is requested, also dispatch explicit MEDIA_OVERRIDE
    if data.get("broadcast_media"):
        override_msg = json.dumps({
            "type": "MEDIA_OVERRIDE",
            "target_room": room,
            "clip_id": data.get("clip_id", preset),
            "title": data.get("title", f"{preset} Laser Sky Show"),
            "tag": "🗽 LIVE LASER SKY SHOW",
            "desc": data.get("desc", "Live Statcast kinetic sky show dispatched by Producer."),
            "config": data.get("config")
        })
        for client in list(clients):
            try:
                await client.send(override_msg)
            except Exception:
                pass

    return {
        "status": "detonated",
        "preset": preset,
        "room": room,
        "broadcast_clients": sent_count
    }

@fastapi_app.get("/api/sports/kinetic/rules")
async def api_get_kinetic_rules():
    """Returns all active kinetic particle rules from cmdb_ci_kinetic_rule."""
    # [Hoisted to header] import sqlite3 as _sq
    con = _sq.connect(DB_PATH)
    con.row_factory = _sq.Row
    c = con.cursor()
    c.execute("SELECT * FROM cmdb_ci_kinetic_rule WHERE is_active = 1 ORDER BY sys_created_on DESC")
    rows = [dict(r) for r in c.fetchall()]
    con.close()
    return {"rules": rows, "count": len(rows)}

def _et_game_date() -> str:
    """Return the active game-slate date in Eastern time.
    Before 10 AM ET we're still on the previous day's slate —
    MLB doesn't publish a new schedule until ~10 AM ET."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    # [Hoisted to header] from datetime import datetime, timedelta
    now_et = datetime.now(ZoneInfo('America/New_York'))
    if now_et.hour < 10:
        return (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    return now_et.strftime('%Y-%m-%d')

@fastapi_app.post("/api/chat/inject")
async def api_inject_chat(request: Request):
    """God Mode: Inject a chat message from any persona into the live stream."""
    # [Hoisted to header] import time
    # [Hoisted to header] import json
    data = await request.json()
    user = data.get("user", "SYSTEM")
    text = data.get("text", "")
    target_room = str(data.get("target_game_pk", "GLOBAL"))
    channel = data.get("channel", "system_broadcast")
    color = data.get("color", "#94a3b8")
    
    chat_msg = {
        "type": "CHAT_MESSAGE",
        "user": user,
        "color": color,
        "text": text,
        "target_game_pk": target_room,
        "timestamp": time.strftime("%H:%M:%S"),
        "model_engine": "GOD_MODE_INJECTOR",
        "is_penalty_box": False,
        "is_walkup": data.get("is_walkup", False),
        "channel": channel,
        "mediaUrl": data.get("mediaUrl") or data.get("media_url") or data.get("image"),
        "shake": data.get("shake", False)
    }
    chat_msg = decorate_chat_message(chat_msg)
    chat_buffers[target_room].append(chat_msg)
    
    # Broadcast to all clients
    out_msg = json.dumps(chat_msg)
    for c in list(clients):
        if ws_rooms.get(c, "GLOBAL") == target_room or target_room == "GLOBAL" or ws_rooms.get(c, "GLOBAL") == "GLOBAL":
            try:
                await c.send(out_msg)
            except:
                pass
    return {"status": "success", "message": chat_msg}


@fastapi_app.post("/api/sports/walkup/inject")
async def api_inject_walkup(request: Request):
    """Simulate or test a batter walk-up announcement in chat."""
    data = await request.json()
    pk = str(data.get("target_game_pk") or data.get("game_pk", "823498"))
    batter_name = data.get("batter_name", "Juan Soto")
    batter_id = str(data.get("batter_id", "665742"))
    jersey = str(data.get("jersey", "22"))
    pos = data.get("position", "RF")
    avg = data.get("avg", ".288")
    hr = str(data.get("hr", "41"))
    rbi = str(data.get("rbi", "109"))
    ops = data.get("ops", ".988")

    jersey_str = f"#{jersey} " if jersey else ""
    pos_str = f"{pos} • " if pos else ""
    stat_parts = []
    if avg and avg != "---": stat_parts.append(f"{avg} AVG")
    if hr and hr != "0": stat_parts.append(f"{hr} HR")
    if rbi and rbi != "0": stat_parts.append(f"{rbi} RBI")
    if ops and ops != "---": stat_parts.append(f"{ops} OPS")
    stat_str = f" ({pos_str}{', '.join(stat_parts)})" if stat_parts else (f" ({pos})" if pos else "")

    walkup_text = f"🎙️ NOW BATTING: {jersey_str}{batter_name}{stat_str}"
    last_walkup_batter[pk] = batter_id if batter_id else batter_name

    walkup_msg = {
        "type": "WALKUP_ANNOUNCEMENT",
        "user": "STATCAST UMPIRE",
        "color": "#00FFCC",
        "text": walkup_text,
        "target_game_pk": pk,
        "timestamp": time.strftime("%H:%M:%S"),
        "is_walkup": True,
        "channel": "system_broadcast",
        "batter_name": batter_name,
        "batter_id": batter_id,
        "jersey": jersey,
        "position": pos,
        "stats": {"avg": avg, "hr": hr, "rbi": rbi, "ops": ops}
    }
    walkup_msg = decorate_chat_message(walkup_msg)
    # Note: Do NOT append to chat_buffers so chat remains strictly for fan advocates

    out_msg = json.dumps(walkup_msg)
    for c in list(clients):
        if ws_rooms.get(c, "GLOBAL") == pk or ws_rooms.get(c, "GLOBAL") == "GLOBAL" or pk == "GLOBAL":
            try:
                await c.send(out_msg)
            except:
                pass
    return {"status": "success", "message": walkup_msg}


@fastapi_app.post("/api/chat/purge/{game_pk}")
@fastapi_app.post("/api/chat/rooms/{game_pk}/purge")
async def api_purge_room_chat(game_pk: str):
    """Purge chat messages for a specific room from memory and database, and notify connected clients."""
    pk_str = str(game_pk)
    
    # 1. Clear in-memory buffer
    if pk_str in chat_buffers:
        chat_buffers[pk_str].clear()
        
    # 2. Clear database
    purged_count = 0
    try:
        conn = get_db()
        pk_val = int(pk_str) if pk_str.isdigit() else pk_str
        cur1 = conn.execute("DELETE FROM game_chat WHERE game_pk = ? OR game_pk = ?", (pk_str, pk_val))
        cur2 = conn.execute("DELETE FROM m2m_persona_room_ledger WHERE game_pk = ? OR game_pk = ?", (pk_str, pk_val))
        purged_count = cur1.rowcount + cur2.rowcount
        conn.commit()
    except Exception as e:
        logger.error("Failed to purge game_chat and ledger for %s: %s", pk_str, e)
    finally:
        conn.close()
        
    # 3. Broadcast clear message & empty history to all clients in this room
    clear_msg = json.dumps({"type": "CHAT_PURGED", "target_game_pk": pk_str})
    empty_hist = json.dumps({"type": "CHAT_HISTORY", "messages": [], "target_game_pk": pk_str})
    for c in list(clients):
        if ws_rooms.get(c, "GLOBAL") == pk_str or pk_str == "GLOBAL":
            try:
                await c.send(clear_msg)
                await c.send(empty_hist)
            except Exception:
                pass
                
    return {"status": "success", "game_pk": pk_str, "purged_count": purged_count}


@fastapi_app.post("/api/overlay/mando-repair")
async def api_trigger_mando_repair(request: Request):
    """Trigger the Mando Robot Repair broadcast overlay across connected viewports."""
    # [Hoisted to header] import time, json
    data = {}
    try:
        data = await request.json()
    except Exception:
        pass
    target_room = str(data.get("target_game_pk") or data.get("game_pk") or "GLOBAL")
    reason = str(data.get("reason") or "BROADCAST TELEMETRY & AI AUTO-HEAL")
    
    event_msg = {
        "type": "OVERLAY_MANDO_REPAIR",
        "game_pk": target_room,
        "reason": reason,
        "timestamp": time.strftime("%H:%M:%S")
    }
    out_msg = json.dumps(event_msg)
    for c in list(clients):
        try:
            await c.send(out_msg)
        except Exception:
            pass
    return {"status": "success", "event": event_msg}


@fastapi_app.get("/api/rooms/active_viewers")
async def api_active_viewers():
    """Returns set of room_ids that currently have active viewer client WebSocket connections."""
    active_rooms = set()
    for ws, room in list(ws_rooms.items()):
        if room and str(room) != "POLLER" and ws in clients:
            active_rooms.add(str(room))
    return {
        "active_rooms": sorted(list(active_rooms)),
        "default_room": "823498",
        "client_count": len(clients)
    }


@fastapi_app.get("/api/roll_call")
async def api_roll_call():
    """Full Roll Call status for the dashboard."""
    # [Hoisted to header] import sqlite3 as _sq
    today = _et_game_date()
    con = _sq.connect(DB_PATH)
    con.row_factory = _sq.Row
    rows = con.execute("""
        SELECT
            s.game_pk,
            s.away_team, s.home_team,
            s.game_date, s.game_time, s.status,
            s.room_state,
            COALESCE(s.sport, CASE WHEN length(s.game_pk) = 9 THEN 'NFL' ELSE 'MLB' END) as sport,
            group_concat(p.user_name) as personas
        FROM sport_schedule s
        LEFT JOIN (
            SELECT gp.game_pk, p.user_name
            FROM persona p
            JOIN game_persona gp ON gp.persona_id = p.id AND gp.seat_state = 'active'
        ) p ON p.game_pk = s.game_pk
        WHERE s.game_date = ? OR s.room_state = 'active'
        GROUP BY s.game_pk
        ORDER BY s.sport, s.game_date
    """, (today,)).fetchall()
    con.close()
    
    results = []
    for r in rows:
        d = dict(r)
        d['personas'] = d['personas'].split(',') if d['personas'] else []
        results.append(d)
        
    return {"games": results}


# ═══════════════════════════════════════════════════════════════
# GAME_PLAY PERSISTENCE  (Statcast / live feed storage)
# ═══════════════════════════════════════════════════════════════

@fastapi_app.post("/api/game_play")
async def api_store_game_play(request: Request):
    """Store a live play event. Called by the MLB poller on every pitch."""
    # [Hoisted to header] import sqlite3 as _sq, uuid as _uuid
    data = await request.json()
    game_pk = str(data.get('game_pk', ''))
    if not game_pk:
        return {"status": "error", "message": "game_pk required"}
    con = _sq.connect(DB_PATH)
    con.execute("""
        INSERT OR IGNORE INTO game_play
            (id, game_pk, play_id, inning, half, event_type,
             batter, pitcher, pitch_speed, pitch_type,
             description, score_away, score_home, outs, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        _uuid.uuid4().hex,
        game_pk,
        data.get('play_id'),
        data.get('inning'),
        data.get('half'),
        data.get('event_type'),
        data.get('batter'),
        data.get('pitcher'),
        data.get('pitch_speed'),
        data.get('pitch_type'),
        data.get('description'),
        data.get('score_away'),
        data.get('score_home'),
        data.get('outs'),
        json.dumps(data.get('raw', {}))
    ))
    con.commit()
    con.close()
    return {"status": "stored"}


@fastapi_app.post("/api/game_play/blackjack")
async def api_store_blackjack_state(request: Request):
    """Receive Blackjack game state from Argo CV and broadcast GTO decision."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    player_score = int(data.get('player_score', 16))
    dealer_up = str(data.get('dealer_up', 'Ts'))
    player_cards = data.get('player_cards', ['10s', '6d'])
    dealer_cards = data.get('dealer_cards', ['Ts'])
    
    # Calculate GTO Optimal Play
    up_card = dealer_up.strip()[:1].upper() if dealer_up else 'T'
    if player_score == 16:
        if up_card in ['T', 'J', 'Q', 'K', 'A', '1']:
            gto = {"recommendation": "SURRENDER", "ev": -0.54, "is_warning": True}
        elif up_card in ['7', '8', '9']:
            gto = {"recommendation": "HIT", "ev": -0.48, "is_warning": False}
        else:
            gto = {"recommendation": "STAND", "ev": -0.28, "is_warning": False}
    elif player_score == 11:
        if up_card in ['A', '1']:
            gto = {"recommendation": "HIT", "ev": 0.15, "is_warning": False}
        else:
            gto = {"recommendation": "DOUBLE", "ev": 0.32, "is_warning": False}
    elif 12 <= player_score <= 15:
        if up_card in ['2', '3', '4', '5', '6']:
            gto = {"recommendation": "STAND", "ev": -0.25, "is_warning": False}
        else:
            gto = {"recommendation": "HIT", "ev": -0.42, "is_warning": False}
    elif player_score >= 17:
        gto = {"recommendation": "STAND", "ev": 0.45, "is_warning": False}
    elif player_score <= 10:
        gto = {"recommendation": "HIT", "ev": -0.12, "is_warning": False}
    else:
        gto = {"recommendation": "HIT", "ev": -0.35, "is_warning": False}

    payload = {
        "type": "BLACKJACK_STATE",
        "player_score": player_score,
        "dealer_up": dealer_up,
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "recommendation": gto["recommendation"],
        "ev": gto["ev"],
        "is_warning": gto["is_warning"]
    }
    
    # Broadcast to all connected WebSockets
    msg_str = json.dumps(payload)
    for c in list(clients):
        try:
            asyncio.create_task(c.send(msg_str))
        except Exception as e:
            print(f"[Blackjack Broadcast Error] {e}")
            
    return {"status": "broadcasted", "payload": payload}



@fastapi_app.get("/api/game_play/{game_pk}")
async def api_get_game_plays(game_pk: str, last: int = 10):
    """Get the last N play events for a game (for persona context injection)."""
    # [Hoisted to header] import sqlite3 as _sq
    con = _sq.connect(DB_PATH)
    con.row_factory = _sq.Row
    rows = con.execute("""
        SELECT inning, half, event_type, batter, pitcher,
               pitch_speed, pitch_type, description, score_away, score_home
        FROM game_play
        WHERE game_pk = ?
        ORDER BY recorded_at DESC
        LIMIT ?
    """, (game_pk, last)).fetchall()
    con.close()
    return {"game_pk": game_pk, "plays": [dict(r) for r in reversed(rows)]}

@fastapi_app.post("/api/export_chat")
async def export_chat(data: ChatExportData):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = f"/home/james/stacklabs/data/logs/chat_export_{timestamp}.md"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(data.markdown_content)
    return {"status": "success", "file": filepath}

import zipfile
import io
from fastapi.responses import Response

@fastapi_app.get("/api/logs")
async def get_logs():
    log_dir = "/home/james/stacklabs/data/logs/"
    dropzone_dir = "/home/james/stacklabs/dna/dropzone/daily_15042026/"
    try:
        files = []
        if os.path.exists(log_dir):
            files.extend([
                {"name": f, "path": f"/data/logs/{f}"} 
                for f in os.listdir(log_dir) 
                if f.startswith("auto_export_") and (f.endswith(".md") or f.endswith(".csv"))
            ])
        if os.path.exists(dropzone_dir):
            files.extend([
                {"name": f, "path": f"/dna/dropzone/daily_15042026/{f}"} 
                for f in os.listdir(dropzone_dir) 
                if "FanCast_Export" in f and f.endswith(".csv")
            ])
        files.sort(key=lambda x: x["name"], reverse=True)
        return {"logs": files}
    except Exception as e:
        return {"logs": []}

@fastapi_app.get("/api/export_all")
async def export_all_logs():
    log_dir = "/home/james/stacklabs/data/logs/"
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for f in os.listdir(log_dir):
                if f.startswith("auto_export_") and f.endswith(".md"):
                    file_path = os.path.join(log_dir, f)
                    zip_file.write(file_path, f)
        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.getvalue(), 
            media_type="application/zip", 
            headers={"Content-Disposition": "attachment; filename=Sovereign_All_Logs.zip"}
        )
    except Exception as e:
        return {"error": str(e)}

@fastapi_app.get("/api/persona_details/{persona_id}")
async def get_persona_details(persona_id: str):
    # [Hoisted to header] import sqlite3 as _sq
    # [Hoisted to header] from fastapi import HTTPException
    
    safe_id = persona_id.lower().replace(" ", "_").lstrip('@')
    
    # Map name variations / aliases to stay consistent with get_persona_image
    if "james" in safe_id:
        safe_id = "pilot_james"
    elif "barb" in safe_id:
        if "warden" in safe_id:
            safe_id = "warden_barb"
        else:
            safe_id = "barb_the_founder"
            
    con = _sq.connect(DB_PATH)
    try:
        c = con.cursor()
        c.execute("""
            SELECT user_name, display_name, team, color, system_prompt, deep_lore, behavior_notes 
            FROM persona 
            WHERE LOWER(user_name) = ? OR LOWER(display_name) = ?
        """, (safe_id, safe_id.replace("_", " ")))
        row = c.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Persona not found")
            
        user_name, display_name, team, color, system_prompt, deep_lore, behavior_notes = row
        
        # Get expressions from cmdb_ci_media_asset
        c.execute("""
            SELECT expression, file_path 
            FROM cmdb_ci_media_asset 
            WHERE LOWER(advocate) = ?
        """, (user_name.lower().replace(" ", "_"),))
        img_rows = c.fetchall()
        
        images = []
        for r in img_rows:
            url_path = r[1] or ""
            if url_path.startswith('/home/james/stacklabs/15_FanStackCreator/public'):
                url_path = url_path.replace('/home/james/stacklabs/15_FanStackCreator/public', '')
            elif url_path.startswith('/home/james/stacklabs/15_FanStack/public'):
                url_path = url_path.replace('/home/james/stacklabs/15_FanStack/public', '')
            elif url_path.startswith('/home/james/stacklabs/19_FanStackArena/public'):
                url_path = url_path.replace('/home/james/stacklabs/19_FanStackArena/public', '')
            elif url_path.startswith('/home/james/stacklabs/19_Sovereign_Sports/public'):
                url_path = url_path.replace('/home/james/stacklabs/19_Sovereign_Sports/public', '')
            elif url_path.startswith('/home/james/stacklabs/avatars'):
                url_path = url_path.replace('/home/james/stacklabs/avatars', '/avatars')
            elif url_path.startswith('/home/james/stacklabs/dna/media/lookbooks'):
                url_path = url_path.replace('/home/james/stacklabs/dna/media/lookbooks', '/avatars')
            images.append({
                "expression": r[0],
                "url": url_path
            })
            
        # If no expressions exist, add the standard avatar URL as the fallback
        if not images:
            images.append({
                "expression": "front_neutral",
                "url": f"/api/persona_image/{user_name.lower().replace(' ', '_')}"
            })
            
        return {
            "user_name": user_name,
            "display_name": display_name or user_name,
            "team": team,
            "color": color or "#00b4d8",
            "bio": system_prompt,
            "deep_lore": deep_lore,
            "behavior_notes": behavior_notes,
            "images": images
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        con.close()

PERSONA_IMAGE_CACHE = {}

@fastapi_app.get("/api/persona_image/{persona_id}")
async def get_persona_image(persona_id: str):
    # [Hoisted to header] import base64, sqlite3 as _sq, glob
    # [Hoisted to header] from fastapi.responses import Response, FileResponse, RedirectResponse
    
    CACHE_HEADERS = {"Cache-Control": "public, max-age=86400, immutable"}

    # 0. Check if persona_id itself consists of digits. If so, redirect directly to MLB static.
    if persona_id.isdigit():
        return RedirectResponse(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{persona_id}/headshot/67/current",
            headers=CACHE_HEADERS
        )
        
    safe_id = persona_id.lower().replace(" ", "_")

    # Fast RAM cache check
    if safe_id in PERSONA_IMAGE_CACHE:
        cached = PERSONA_IMAGE_CACHE[safe_id]
        if isinstance(cached, str) and os.path.exists(cached):
            return FileResponse(cached, headers=CACHE_HEADERS)
        elif isinstance(cached, tuple): # (content, media_type)
            return Response(content=cached[0], media_type=cached[1], headers=CACHE_HEADERS)

    # Map name variations / aliases
    if "james" in safe_id:
        safe_id = "pilot_james"
    elif "barb" in safe_id:
        if "warden" in safe_id:
            safe_id = "warden_barb"
        else:
            safe_id = "barb_the_founder"

    # 1. Try DB first (canonical source of truth)
    try:
        con = _sq.connect(DB_PATH)
        row = con.execute(
            "SELECT avatar_blob, avatar_url FROM persona WHERE user_name = ? OR user_name = ?",
            (safe_id, safe_id)
        ).fetchone()
        con.close()
        
        if row:
            # A. Serve from DB blob if populated
            if row[0]:
                blob_data = row[0]
                if blob_data.startswith('data:'):
                    header, b64 = blob_data.split(',', 1)
                    mime = header.split(':')[1].split(';')[0]
                else:
                    b64 = blob_data
                    mime = 'image/png'
                content_bytes = base64.b64decode(b64)
                PERSONA_IMAGE_CACHE[safe_id] = (content_bytes, mime)
                return Response(content=content_bytes, media_type=mime, headers=CACHE_HEADERS)
            
            # B. Serve from local filesystem path defined in avatar_url if populated
            if row[1]:
                filename = row[1]
                if '/persona_image/' in filename:
                    filename = filename.split('/persona_image/')[-1]
                if filename.startswith('/avatars/'):
                    filename = filename.replace('/avatars/', '', 1)
                elif filename.startswith('avatars/'):
                    filename = filename.replace('avatars/', '', 1)
                
                for ext in ['', '.png', '.jpg', '.jpeg', '.webp']:
                    test_path = os.path.join("/home/james/stacklabs/avatars", f"{filename}{ext}")
                    if os.path.exists(test_path) and os.path.isfile(test_path):
                        PERSONA_IMAGE_CACHE[safe_id] = test_path
                        return FileResponse(test_path, headers=CACHE_HEADERS)
    except Exception as e:
        print(f"[persona_image] DB lookup error: {e}")

    # 2. Fall back to direct filesystem search
    for search_dir in [
        "/home/james/stacklabs/avatars",
        "/home/james/stacklabs/archive_quarantine_eon1",
        "/home/james/stacklabs/15_FanStack/public/avatars",
        "/home/james/stacklabs/dna/media/avatars",
        "/home/james/stacklabs/dna/media/character_maps",
        "/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts"
    ]:
        for f in glob.glob(os.path.join(search_dir, f"{safe_id}.*")):
            if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp')):
                PERSONA_IMAGE_CACHE[safe_id] = f
                return FileResponse(f, headers=CACHE_HEADERS)
        # Also check inside a subdirectory matching safe_id or prefix or base persona name
        prefix_id = safe_id.split('_')[0]
        base_name = safe_id.replace("_sprite_sheet", "")
        for sub_name in [safe_id, prefix_id, base_name]:
            sub_dir = os.path.join(search_dir, sub_name)
            if os.path.isdir(sub_dir):
                for f in glob.glob(os.path.join(sub_dir, "*")):
                    cond = (safe_id in f.lower() or "avatar" in f.lower() or "sprite" in f.lower() or "sheet" in f.lower() or sub_name == safe_id)
                    if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp')) and cond:
                        PERSONA_IMAGE_CACHE[safe_id] = f
                        return FileResponse(f, headers=CACHE_HEADERS)

    # 3. Fall back to mlb_rosters table matching name
    try:
        search_name = safe_id.replace("_", " ")
        con = _sq.connect(DB_PATH)
        row = con.execute(
            "SELECT sys_id FROM mlb_rosters WHERE LOWER(player_name) = ?",
            (search_name,)
        ).fetchone()
        con.close()
        if row and row[0]:
            sys_id = row[0]
            numeric_id = "".join([c for c in sys_id if c.isdigit()])
            if numeric_id:
                return RedirectResponse(
                    f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{numeric_id}/headshot/67/current",
                    headers=CACHE_HEADERS
                )
    except Exception as e:
        print(f"[persona_image] MLB roster lookup error: {e}")

    raise HTTPException(status_code=404, detail="Image not found")


@fastapi_app.post("/api/persona_image/{persona_id}")
async def upload_persona_image_blob(persona_id: str, file: UploadFile = File(...)):
    """Store avatar as base64 blob in persona.avatar_blob — no filesystem, no rebuild needed."""
    # [Hoisted to header] import base64, sqlite3 as _sq
    safe_id = persona_id.lower().replace(" ", "_")
    raw = await file.read()
    mime = file.content_type or 'image/png'
    b64 = base64.b64encode(raw).decode('utf-8')
    data_url = f"data:{mime};base64,{b64}"
    avatar_path = f"/api/persona_image/{safe_id}"
    con = _sq.connect(DB_PATH)
    updated = con.execute(
        "UPDATE persona SET avatar_blob = ?, avatar_url = ? WHERE user_name = ? OR user_name = ?",
        (data_url, avatar_path, persona_id, safe_id)
    ).rowcount
    if updated > 0:
        con.execute(
            "UPDATE sys_user SET avatar_url = ? WHERE sys_id = (SELECT id FROM persona WHERE user_name = ? OR user_name = ?)",
            (avatar_path, persona_id, safe_id)
        )
    con.commit()
    con.close()
    if updated == 0:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")
    return {"status": "success", "user_name": safe_id, "avatar_url": avatar_path}


from typing import Optional

class VertexAvatarRequest(BaseModel):
    prompt: str
    persona_id: Optional[str] = "pilot_james"
    style: Optional[str] = "circular_avatar"

@fastapi_app.post("/api/avatar/generate_vertex")
async def generate_vertex_avatar(req: VertexAvatarRequest):
    """Generate custom avatar using Vertex AI Imagen 3 or high-res synthesis."""
    # [Hoisted to header] import base64, urllib.parse
    
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
        
    full_prompt = f"Professional circular avatar portrait of {prompt}, clean background, sharp focus, 8k resolution, cinematic digital art, centered framing"
    
    # Try Vertex AI first if available
    try:
        from scripts.imagen_util import get_imagen_client, verify_imagen_model_health
        from google.genai import types
        
        is_healthy, working_model = verify_imagen_model_health()
        if is_healthy and working_model:
            client = get_imagen_client()
            res = client.models.generate_images(
                model=working_model,
                prompt=full_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="1:1"
                )
            )
            if res and res.generated_images:
                img_bytes = res.generated_images[0].image.image_bytes
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                data_url = f"data:image/png;base64,{b64}"
                return {"status": "success", "avatar_url": data_url, "source": "vertex_imagen_3"}
    except Exception as e:
        print(f"[generate_vertex_avatar] Vertex AI generation fallback notice: {e}")
        
    # Fallback to high-res pollinations synthesis
    try:
        encoded_prompt = urllib.parse.quote(full_prompt)
        poll_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        resp = requests.get(poll_url, timeout=25)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            data_url = f"data:image/png;base64,{b64}"
            return {"status": "success", "avatar_url": data_url, "source": "synth_engine"}
    except Exception as e2:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e2}")
        
    raise HTTPException(status_code=500, detail="Avatar synthesis returned empty response")



@fastapi_app.post("/api/chat/upload")
async def upload_chat_image(file: UploadFile = File(...)):
    """Upload a general chat image to public/images and return its web-accessible path."""
    # [Hoisted to header] import uuid
    
    ext = os.path.splitext(file.filename or "")[1] or ".png"
    filename = f"chat_upload_{uuid.uuid4().hex}{ext}"
    
    # Write to both locations to prevent 404s on port 3010
    images_dir_15 = "/home/james/stacklabs/15_FanStackCreator/public/images"
    images_dir_19 = "/home/james/stacklabs/19_FanStackArena/public/images"
    
    os.makedirs(images_dir_15, exist_ok=True)
    os.makedirs(images_dir_19, exist_ok=True)
    
    dest_path_15 = os.path.join(images_dir_15, filename)
    dest_path_19 = os.path.join(images_dir_19, filename)
    
    try:
        content = await file.read()
        with open(dest_path_15, "wb") as f:
            f.write(content)
        with open(dest_path_19, "wb") as f:
            f.write(content)
        return {"status": "success", "mediaUrl": f"/images/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@fastapi_app.get("/api/storyboards/projects")
async def get_storyboard_projects():
    projects_dir = "/home/james/stacklabs/media_vault/02_Projects"
    try:
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir, exist_ok=True)
        projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
        return {"projects": projects}
    except Exception as e:
        return {"projects": [], "error": str(e)}

from pydantic import BaseModel
import shutil

class TMIAnomaly(BaseModel):
    id: str
    event: str
    time: str
    persona: str
    format: str
    script: str
    prompt: str

@fastapi_app.post("/api/storyboards/create_from_tmi")
async def create_storyboard_from_tmi(anomaly: TMIAnomaly):
    # [Hoisted to header] import re
    project_name = re.sub(r'[^a-zA-Z0-9]', '_', anomaly.event) + "_Storyboard"
    project_dir = f"/home/james/stacklabs/media_vault/02_Projects/{project_name}"
    os.makedirs(project_dir, exist_ok=True)
    
    md_content = f"# Flowmercial: {anomaly.event}\n\n"
    md_content += f"**Persona:** {anomaly.persona}\n"
    md_content += f"**Format:** {anomaly.format}\n\n"
    md_content += f"## ElevenLabs Script\n```text\n{anomaly.script}\n```\n\n"
    md_content += f"## Google Flow Prompt\n```text\n{anomaly.prompt}\n```\n"
    
    with open(os.path.join(project_dir, "FLOW_PROMPTS.md"), "w") as f:
        f.write(md_content)
        
    # Auto-copy persona assets if we have them
    assets_dir = "/home/james/stacklabs/media_vault/03_Assets/Personas"
    if os.path.exists(assets_dir):
        persona_normalized = anomaly.persona.lower()
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                if persona_normalized in file.lower() or file.lower().startswith(persona_normalized[:4]):
                    shutil.copy(os.path.join(root, file), os.path.join(project_dir, file))
                    
    return {"status": "success", "project": project_name}

@fastapi_app.get("/api/storyboards")
async def get_storyboards(project: str = "Mets_Twins_Collapse_Storyboard"):
    storyboard_dir = f"/home/james/stacklabs/media_vault/02_Projects/{project}"
    try:
        if not os.path.exists(storyboard_dir):
            os.makedirs(storyboard_dir, exist_ok=True)
        files = []
        for f in os.listdir(storyboard_dir):
            if f.endswith((".png", ".jpg", ".webp", ".mp4", ".md", ".txt", ".json")):
                files.append({
                    "name": f,
                    "url": f"/media_vault/02_Projects/{project}/{f}",
                    "timestamp": os.path.getmtime(os.path.join(storyboard_dir, f))
                })
        # Sort by modification time
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return {"artifacts": files}
    except Exception as e:
        return {"artifacts": [], "error": str(e)}

# ─── PROMPT INTERCEPTOR STATE & API ENDPOINTS ───
intercept_mode = False
staged_prompts = {}

class PromptStagePayload(BaseModel):
    prompt: str
    system_instruction: str | None = None
    model: str | None = None
    persona: str | None = None
    game_pk: str | None = None

class PromptOverridePayload(BaseModel):
    prompt: str
    system_instruction: str | None = None

class ToggleInterceptPayload(BaseModel):
    intercept_mode: bool

@fastapi_app.get("/api/prompt/intercept")
async def get_prompt_intercept_status():
    staged_list = []
    for pid, val in staged_prompts.items():
        staged_list.append({
            "id": pid,
            "prompt": val["prompt"],
            "system_instruction": val["system_instruction"],
            "model": val["model"],
            "persona": val["persona"],
            "game_pk": val["game_pk"],
            "status": val["status"]
        })
    return {
        "intercept_mode": intercept_mode,
        "staged": staged_list
    }

@fastapi_app.post("/api/prompt/intercept/toggle")
async def toggle_prompt_intercept(payload: ToggleInterceptPayload):
    global intercept_mode
    intercept_mode = payload.intercept_mode
    return {"status": "success", "intercept_mode": intercept_mode}

@fastapi_app.post("/api/prompt/release/{prompt_id}")
async def release_prompt(prompt_id: str):
    if prompt_id in staged_prompts:
        staged_prompts[prompt_id]["status"] = "released"
        staged_prompts[prompt_id]["event"].set()
        return {"status": "released"}
    raise HTTPException(status_code=404, detail="Prompt ID not found or already processed")

@fastapi_app.post("/api/prompt/override/{prompt_id}")
async def override_prompt(prompt_id: str, payload: PromptOverridePayload):
    if prompt_id in staged_prompts:
        staged_prompts[prompt_id]["override_prompt"] = payload.prompt
        staged_prompts[prompt_id]["override_system_instruction"] = payload.system_instruction
        staged_prompts[prompt_id]["status"] = "overridden"
        staged_prompts[prompt_id]["event"].set()
        return {"status": "overridden"}
    raise HTTPException(status_code=404, detail="Prompt ID not found or already processed")

@fastapi_app.post("/api/prompt/stage")
async def stage_prompt(payload: PromptStagePayload):
    if not intercept_mode:
        return {"action": "pass"}
    
    # [Hoisted to header] import uuid
    prompt_id = uuid.uuid4().hex
    event = asyncio.Event()
    
    staged_prompts[prompt_id] = {
        "id": prompt_id,
        "prompt": payload.prompt,
        "system_instruction": payload.system_instruction,
        "model": payload.model,
        "persona": payload.persona,
        "game_pk": payload.game_pk,
        "status": "pending",
        "event": event,
        "override_prompt": None,
        "override_system_instruction": None
    }
    
    # Broadcast to all websocket clients
    ws_msg = {
        "type": "PROMPT_INTERCEPTED",
        "id": prompt_id,
        "prompt": payload.prompt,
        "system_instruction": payload.system_instruction,
        "model": payload.model,
        "persona": payload.persona,
        "game_pk": payload.game_pk
    }
    # Send ws broadcast
    for client in list(clients):
        try:
            await client.send(json.dumps(ws_msg))
        except Exception:
            pass
            
    # Wait for release/override with 30s timeout
    try:
        await asyncio.wait_for(event.wait(), timeout=30.0)
    except asyncio.TimeoutError:
        staged_prompts.pop(prompt_id, None)
        return {"action": "pass"}
        
    entry = staged_prompts.pop(prompt_id, None)
    if not entry:
        return {"action": "pass"}
        
    if entry["status"] == "overridden":
        return {
            "action": "override",
            "prompt": entry["override_prompt"],
            "system_instruction": entry["override_system_instruction"]
        }
    return {"action": "pass"}


class AdvocateSpritePayload(BaseModel):
    persona_name: str
    theme: str

@fastapi_app.post("/api/advocate/generate_sprite")
async def generate_advocate_sprite(payload: AdvocateSpritePayload):
    # [Hoisted to header] import urllib.parse
    # [Hoisted to header] import uuid
    # [Hoisted to header] import sqlite3
    # [Hoisted to header] import os
    # [Hoisted to header] import requests
    from PIL import Image
    # [Hoisted to header] import io
    
    persona_name = payload.persona_name.strip()
    norm_name = persona_name.lower().lstrip('@').replace(' ', '_')
    theme = payload.theme.strip()
    
    system_prompt = ""
    deep_lore = ""
    team = "global"
    visual_style = "style_2d"
    try:
        con = get_db(row_factory=False)
        row = con.execute(
            "SELECT system_prompt, deep_lore, team FROM persona WHERE LOWER(user_name) = ? OR LOWER(user_name) = ?",
            (norm_name, norm_name)
        ).fetchone()
        con.close()
        if row:
            system_prompt = row[0] or ""
            deep_lore = row[1] or ""
            team = row[2] or "global"
            visual_style = "style_2d"
    except Exception as e:
        print(f"[Sprite Gen DB Error] {e}")
        
    style_prompts = {
        "style_2d": "rendered in a premium Flat 2D Vector Comic art style, crisp clean outlines, bold vector shading, solid near-black background, extremely high visual consistency.",
        "style_pixel": "rendered in a vibrant 16-bit retro pixel art grid style, pixelated textures, clean shapes, solid dark near-black background.",
        "style_clay": "rendered as an unraveled claymation model, stop-motion plasticine textures, playful handcrafted look, solid near-black background.",
        "style_apathetic": "rendered as a gloomy, apathetic claymation figure, moody lighting, distressed plasticine textures, solid near-black background.",
        "style_felt": "cozy hand-drawn fuzzy felt puppet style, soft fleece textures, warm organic lighting, solid dark near-black background."
    }
    style_suffix = style_prompts.get(visual_style, style_prompts["style_2d"])
    
    base_description = f"Consistent facial features, headshot portrait of {persona_name}. Description: {deep_lore[:150]}. System context: {system_prompt[:150]}."
    
    if theme == "Beach Promotion":
        grid_instructions = (
            "A 3x3 high-contrast grid matrix sheet of the same character. "
            "Row 1: Modern Era (Col 1: regular headshot on a sunny beach, Col 2: excited face holding a cold drink, Col 3: disgruntled face by the ocean). "
            "Row 2: Beach Morning (Col 1: regular morning fog beachwear, Col 2: excited waving morning towel, Col 3: disgruntled sunscreen on nose). "
            "Row 3: Beach Sunset (Col 1: warm golden hour light, Col 2: excited smiling at sunset, Col 3: disgruntled storm clouds background)."
        )
        row_keys = ["modern", "beach_morning", "beach_sunset"]
    elif theme == "Golf Tournament":
        grid_instructions = (
            "A 3x3 high-contrast grid matrix sheet of the same character. "
            "Row 1: Modern Era (Col 1: regular headshot in golf apparel, Col 2: excited face holding a golf ball, Col 3: disgruntled face after missing a putt). "
            "Row 2: Golf Tee (Col 1: wearing golf cap standing on the tee box, Col 2: excited waving golf club, Col 3: disgruntled in the rough). "
            "Row 3: Golf Clubhouse (Col 1: clubhouse background, Col 2: excited cheering with trophy, Col 3: disgruntled with broken golf club)."
        )
        row_keys = ["modern", "golf_tee", "golf_clubhouse"]
    else:
        grid_instructions = (
            f"A 3x3 high-contrast grid matrix sheet of the same character. "
            f"Row 1: Modern Era (Col 1: regular headshot in modern {team} team baseball apparel, Col 2: excited victory face, Col 3: disgruntled fan meltdown). "
            f"Row 2: 1970s Throwback (Col 1: retro 1970s sideburns/hair and pullover racing-stripe {team} uniform, Col 2: vintage cap fly-off excited state, Col 3: disgruntled throwing cup). "
            f"Row 3: 1920s Throwback (Col 1: 1920s sepia newsboy cap baggy wool {team} uniform, Col 2: excited shouting through vintage megaphone, Col 3: disgruntled scowling behind wire mesh backstop)."
        )
        row_keys = ["modern", "1975", "1920"]
        
    full_prompt = f"{base_description} {grid_instructions} {style_suffix} Masterpiece, strict 3x3 grid layout, symmetric spacing, high-definition character sprite sheet."
    encoded_prompt = urllib.parse.quote(full_prompt)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    
    target_dir = f"/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts/{norm_name}"
    os.makedirs(target_dir, exist_ok=True)
    
    master_name = f"{norm_name}_sprite_sheet.png"
    master_path = os.path.join(target_dir, master_name)
    
    try:
        res = requests.get(pollinations_url, timeout=30)
        if res.status_code != 200:
            return {"status": "error", "message": f"Pollinations download failed: HTTP {res.status_code}"}
            
        with open(master_path, "wb") as f:
            f.write(res.content)
            
        img = Image.open(io.BytesIO(res.content))
        width, height = img.size
        cell_width = width / 3
        cell_height = height / 3
        
        col_keys = ["regular", "excited", "disgruntled"]
        sliced_urls = []
        
        for row in range(3):
            for col in range(3):
                left = col * cell_width
                top = row * cell_height
                right = (col + 1) * cell_width
                bottom = (row + 1) * cell_height
                
                cropped = img.crop((left, top, right, bottom))
                
                slice_filename = f"{norm_name}_{row_keys[row]}_{col_keys[col]}.png"
                slice_path = os.path.join(target_dir, slice_filename)
                cropped.save(slice_path, "PNG")
                
                # Also save to public folder for frontend access
                static_dir = "/home/james/stacklabs/15_FanStack/public/images/sprites"
                os.makedirs(static_dir, exist_ok=True)
                cropped.save(os.path.join(static_dir, slice_filename), "PNG")
                
                sliced_urls.append({
                    "row": row_keys[row],
                    "col": col_keys[col],
                    "filename": slice_filename,
                    "url": f"/images/sprites/{slice_filename}"
                })
                
        # Register in CMDB
        try:
            sys_id = uuid.uuid4().hex
            con = get_db(row_factory=False)
            c = con.cursor()
            c.execute("SELECT asset_tag FROM sys_media_asset ORDER BY asset_tag DESC LIMIT 1")
            row_db = c.fetchone()
            tag = "FS-MED-00001"
            if row_db:
                # [Hoisted to header] import re
                match = re.search(r'FS-MED-(\d+)', row_db[0])
                if match:
                    tag = f"FS-MED-{(int(match.group(1)) + 1):05d}"
            c.execute("""
                INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sys_id, tag, f"Sprite Sheet: {persona_name} - {theme}", master_name, master_path, len(res.content), "image/png", "SpriteSheet", f"Theme: {theme}", sys_id))
            con.commit()
            con.close()
        except Exception as e:
            print(f"[Sprite CMDB Error] {e}")
            
        return {
            "status": "success",
            "master_url": f"/api/persona_image/{norm_name}_sprite_sheet",
            "slices": sliced_urls
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@fastapi_app.websocket("/{path_name:path}")
async def catch_all_websocket(websocket: WebSocket, path_name: str):
    if path_name in ["ws", "ws-relay", "mesh-ws", "mesh-ws-dev", "mesh-ws-uat", "mesh-ws-sandbox"]:
        await websocket.accept()
        async with websockets.connect("ws://127.0.0.1:8008") as remote:
            async def forward_to_remote():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await remote.send(data)
                except:
                    pass

            async def forward_to_client():
                try:
                    async for message in remote:
                        await websocket.send_text(message)
                except:
                    pass

            await asyncio.gather(forward_to_remote(), forward_to_client())
    else:
        await websocket.accept()
        await websocket.close(code=1003)

# NOTE: Explicit /ws handler removed — it was shadowed by the catch_all_websocket
# route above (/{path_name:path}), which handles path_name == "ws" correctly.

# Serve all static files from apiary root 
# MOUNT MOVED TO BOTTOM

async def run_fastapi():
    try:
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as e:
        # [Hoisted to header] import traceback
        print(f"FASTAPI STARTUP ERROR: {e}")
        traceback.print_exc()
# ── PGA Golf Telemetry Endpoints ──────────────────────────────────────────────
@fastapi_app.get("/api/pga/leaderboard")
def get_pga_leaderboard():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT player_id, player_name, current_position, score_to_par, current_hole, status, updated_at FROM pga_active_leaderboard ORDER BY current_position ASC, score_to_par ASC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return {"leaderboard": rows}
    except Exception as e:
        return {"error": str(e)}

@fastapi_app.post("/api/pga/leaderboard")
def post_pga_leaderboard(data: dict):
    try:
        player_id = data.get("player_id")
        player_name = data.get("player_name")
        current_position = data.get("current_position")
        score_to_par = data.get("score_to_par")
        current_hole = data.get("current_hole", 18)
        status = data.get("status", "ACTIVE")
        
        conn = get_db(row_factory=False)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO pga_active_leaderboard 
            (player_id, player_name, current_position, score_to_par, current_hole, status, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (player_id, player_name, current_position, score_to_par, current_hole, status))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

@fastapi_app.delete("/api/pga/leaderboard/{player_id}")
def delete_pga_leaderboard(player_id: int):
    try:
        conn = get_db(row_factory=False)
        c = conn.cursor()
        c.execute("DELETE FROM pga_active_leaderboard WHERE player_id = ?", (player_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

@fastapi_app.post("/api/pga/pulse")
async def post_pga_pulse(data: dict):
    text = data.get("text", "")
    if not text:
        return {"error": "text is required"}
    try:
        pk = "amen_corner"
        gs = game_states[pk]
        gs["timestamp"] = time.strftime("%H:%M:%S")
        gs["target_game_pk"] = pk
        gs["status_msg"] = text
        gs["away_team"] = "GOLF"
        gs["home_team"] = "PGA"
        gs["event_type"] = "golf_shot"
        
        await broadcast_state(pk)
        
        # Broadcast the update_context message over websockets to trigger bots
        out_msg = json.dumps({
            "type": "update_context",
            "text": text,
            "target_nodes": ["ALL"],
            "target_game_pk": pk
        })
        for c in list(clients):
            try:
                await c.send(out_msg)
            except:
                pass
                
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

@fastapi_app.get("/api/pga/clio-metrics")
def get_clio_metrics():
    # [Hoisted to header] import subprocess
    # [Hoisted to header] import os
    
    temp = "N/A"
    try:
        for path in ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"]:
            if os.path.exists(path):
                with open(path) as f:
                    raw_temp = int(f.read().strip())
                    temp = f"{round(raw_temp / 1000.0, 1)}°C"
                    break
    except:
        pass
        
    ts_status = "Disconnected"
    try:
        res = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0:
            if "tailscale is stopped" in res.stderr.lower() or "logged out" in res.stdout.lower():
                ts_status = "Stopped/Logged Out"
            else:
                ts_status = "Connected"
    except:
        pass
        
    cpu_load = "N/A"
    mem_usage = "N/A"
    try:
        load = os.getloadavg()
        cpu_load = f"{round(load[0] * 100 / os.cpu_count(), 1)}%"
    except:
        pass
    try:
        with open('/proc/meminfo', 'r') as mem:
            lines = mem.readlines()
            total = int(lines[0].split()[1])
            free = int(lines[1].split()[1])
            buffers = int(lines[3].split()[1])
            cached = int(lines[4].split()[1])
            used = total - free - buffers - cached
            mem_usage = f"{round(used / total * 100, 1)}%"
    except:
        pass
            
    return {
        "cpu_temp": temp,
        "tailscale_status": ts_status,
        "cpu_load": cpu_load,
        "memory_usage": mem_usage,
        "hostname": "clio"
    }

@fastapi_app.get("/api/mlb/boxscore/{game_pk}")
async def get_mlb_boxscore(game_pk: str):
    # [Hoisted to header] import requests
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        r = requests.get(url, timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

class ChatRequest(BaseModel):
    message: str

def resolve_persona(tag: str):
    """
    Look up persona details (user_name, color, system_prompt, deep_lore)
    from the database first, and then fallback to static files.
    """
    # [Hoisted to header] import sqlite3
    tag_clean = tag.lower().strip().lstrip('@')
    if tag_clean.endswith('_ci'):
        tag_clean = tag_clean[:-3]

    # Try mapping aliases first
    if "james" in tag_clean:
        tag_clean = "pilot_james"
    elif "barb" in tag_clean:
        if "warden" in tag_clean:
            tag_clean = "warden_barb"
        else:
            tag_clean = "barb_the_founder"

    # Query DB
    try:
        conn = get_db(row_factory=False)
        c = conn.cursor()
        # Look for exact username match or partial/fuzzy match
        c.execute("""
            SELECT user_name, color, system_prompt, deep_lore 
            FROM persona 
            WHERE LOWER(user_name) = ? OR LOWER(user_name) LIKE ?
            LIMIT 1
        """, (tag_clean, f"%{tag_clean}%"))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "user_name": row[0],
                "color": row[1] or "#A9A9A9",
                "system_prompt": row[2] or "",
                "deep_lore": row[3] or ""
            }
    except Exception as e:
        print(f"[resolve_persona] DB lookup error: {e}")

    # Fallback to static markdown files in dna/agents/personas/
    PERSONAS_DIR = '/home/james/stacklabs/dna/agents/personas/'
    possible_files = [
        f"{tag_clean}.md",
        f"{tag_clean}_stan.md",
        f"{tag_clean}_terry.md",
        tag_clean
    ]
    
    selected_file = None
    for pf in possible_files:
        if os.path.exists(os.path.join(PERSONAS_DIR, pf)):
            selected_file = pf
            break
            
    if not selected_file:
        try:
            # Fuzzy match files
            all_files = [f for f in os.listdir(PERSONAS_DIR) if f.endswith('.md')]
            for f in all_files:
                if tag_clean in f.lower():
                    selected_file = f
                    break
        except Exception:
            pass

    if selected_file:
        try:
            with open(os.path.join(PERSONAS_DIR, selected_file), 'r') as f:
                content = f.read()
            name = selected_file.replace('.md', '').replace('_', ' ').title()
            color = "#00E676"
            return {
                "user_name": name,
                "color": color,
                "system_prompt": content,
                "deep_lore": ""
            }
        except Exception:
            pass

    return None

@fastapi_app.post("/api/chat")
async def api_chat_endpoint(request: ChatRequest):
    # [Hoisted to header] import re
    from google import genai
    from google.genai import types
    
    user_message = request.message
    if not user_message:
        return {"error": "Missing message"}

    # Extract @tag
    match = re.search(r'@(\w+)', user_message)
    
    if not match:
        scruffy_text = "Hey pal, if you're gonna yell at someone in my bar, you gotta use their name with an @tag. Check the room roster. Now buy a drink or get out."
        # Broadcast user message
        user_chat_msg = {
            "type": "CHAT_MESSAGE",
            "user": "james (Pilot)",
            "color": "#94a3b8",
            "text": user_message,
            "target_game_pk": "GLOBAL",
            "timestamp": time.strftime("%H:%M:%S"),
            "model_engine": "USER_INTERACTION",
            "is_penalty_box": False,
            "channel": "system_broadcast"
        }
        user_chat_msg = decorate_chat_message(user_chat_msg)
        chat_buffers["GLOBAL"].append(user_chat_msg)
        for c in list(clients):
            try:
                await c.send(json.dumps(user_chat_msg))
            except:
                pass

        # Broadcast Scruffy message
        scruffy_chat_msg = {
            "type": "CHAT_MESSAGE",
            "user": "Scruffy (Bartender)",
            "color": "#8B4513",
            "text": scruffy_text,
            "target_game_pk": "GLOBAL",
            "timestamp": time.strftime("%H:%M:%S"),
            "model_engine": "SYSTEM_FALLBACK",
            "is_penalty_box": False,
            "channel": "system_broadcast"
        }
        scruffy_chat_msg = decorate_chat_message(scruffy_chat_msg)
        chat_buffers["GLOBAL"].append(scruffy_chat_msg)
        for c in list(clients):
            try:
                await c.send(json.dumps(scruffy_chat_msg))
            except:
                pass

        return {
            "persona": "Scruffy (Bartender)",
            "text": scruffy_text,
            "color": "#8B4513"
        }

    tag = match.group(1)
    persona = resolve_persona(tag)

    if not persona:
        scruffy_text = f"Ain't nobody in this bar named @{tag}. Check the advocate roster."
        # Broadcast user message
        user_chat_msg = {
            "type": "CHAT_MESSAGE",
            "user": "james (Pilot)",
            "color": "#94a3b8",
            "text": user_message,
            "target_game_pk": "GLOBAL",
            "timestamp": time.strftime("%H:%M:%S"),
            "model_engine": "USER_INTERACTION",
            "is_penalty_box": False,
            "channel": "system_broadcast"
        }
        user_chat_msg = decorate_chat_message(user_chat_msg)
        chat_buffers["GLOBAL"].append(user_chat_msg)
        for c in list(clients):
            try:
                await c.send(json.dumps(user_chat_msg))
            except:
                pass

        # Broadcast Scruffy message
        scruffy_chat_msg = {
            "type": "CHAT_MESSAGE",
            "user": "Scruffy (Bartender)",
            "color": "#8B4513",
            "text": scruffy_text,
            "target_game_pk": "GLOBAL",
            "timestamp": time.strftime("%H:%M:%S"),
            "model_engine": "SYSTEM_FALLBACK",
            "is_penalty_box": False,
            "channel": "system_broadcast"
        }
        scruffy_chat_msg = decorate_chat_message(scruffy_chat_msg)
        chat_buffers["GLOBAL"].append(scruffy_chat_msg)
        for c in list(clients):
            try:
                await c.send(json.dumps(scruffy_chat_msg))
            except:
                pass

        return {
            "persona": "Scruffy (Bartender)",
            "text": scruffy_text,
            "color": "#8B4513"
        }

    # Load latest context
    current_context = "No recent context available."
    try:
        context_path = '/home/james/stacklabs/dna/dropzone/daily_22042026/mardy_soto_comments.md'
        if os.path.exists(context_path):
            with open(context_path, 'r') as f:
                current_context = f.read()[:5000]
    except Exception as e:
        print(f"[api_chat] Failed to load context: {e}")

    # Build persona lore
    persona_lore = ""
    if persona.get("system_prompt"):
        persona_lore += f"System Prompt:\n{persona['system_prompt']}\n\n"
    if persona.get("deep_lore"):
        persona_lore += f"Deep Lore:\n{persona['deep_lore']}\n"

    prompt = f"""You are acting as the persona described below. You are currently sitting at "Scruffy's Bar", a local dive bar where sports fans come to complain or talk stats.

Persona Lore:
{persona_lore}

CURRENT REALITY (DO NOT HALLUCINATE STATS OR PROBABILITIES THAT CONTRADICT THIS):
The Mets are currently on an 11+ game losing streak. They are the worst team in MLB right now. Juan Soto has just returned for Game 2 vs Minnesota. 
Here is what the fans are currently screaming about in the live chat right now:
{current_context}

A fan just walked up to you in the bar and said:
"{user_message}"

Task: Write ONE single, highly punchy, character-accurate response to this fan. Speak directly to them. Do not use hashtags or emojis. Keep it STRICTLY UNDER 250 CHARACTERS. Ensure your response reflects the CURRENT REALITY provided above.
If the fan asks a statistical or factual question about current events or baseball, USE GOOGLE SEARCH to find the real answer before responding!"""

    api_key = os.getenv("GEMINI_API_KEY")
    gemini_client = None
    if api_key:
        try:
            gemini_client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"[api_chat] Gemini Client Init Error: {e}")

    if not gemini_client:
        return {"error": "Gemini API client not initialized"}

    try:
        res = gemini_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        bot_text = res.text.strip()
    except Exception as e:
        print(f"[api_chat] Gemini Generation Error: {e}")
        return {"error": f"Gemini Generation Error: {str(e)}"}

    # Broadcast user message to websockets
    user_chat_msg = {
        "type": "CHAT_MESSAGE",
        "user": "james (Pilot)",
        "color": "#94a3b8",
        "text": user_message,
        "target_game_pk": "GLOBAL",
        "timestamp": time.strftime("%H:%M:%S"),
        "model_engine": "USER_INTERACTION",
        "is_penalty_box": False,
        "channel": "system_broadcast"
    }
    user_chat_msg = decorate_chat_message(user_chat_msg)
    chat_buffers["GLOBAL"].append(user_chat_msg)
    for c in list(clients):
        try:
            await c.send(json.dumps(user_chat_msg))
        except:
            pass

    # Broadcast bot response to websockets
    bot_chat_msg = {
        "type": "CHAT_MESSAGE",
        "user": persona["user_name"],
        "color": persona["color"],
        "text": bot_text,
        "target_game_pk": "GLOBAL",
        "timestamp": time.strftime("%H:%M:%S"),
        "model_engine": "GEMINI",
        "is_penalty_box": False,
        "channel": "system_broadcast"
    }
    bot_chat_msg = decorate_chat_message(bot_chat_msg)
    chat_buffers["GLOBAL"].append(bot_chat_msg)
    for c in list(clients):
        try:
            await c.send(json.dumps(bot_chat_msg))
        except:
            pass

    return {
        "persona": persona["user_name"],
        "text": bot_text,
        "color": persona["color"]
    }

fastapi_app.mount("/images", StaticFiles(directory="/home/james/stacklabs/15_FanStackCreator/public/images"), name="images")
fastapi_app.mount("/", StaticFiles(directory="/home/james/stacklabs", html=True), name="static")

async def main():
    print("🚀 Sovereign FanCast Relay booting on 0.0.0.0:8008...")
    print("🚀 Sovereign Proxy Server booting on 0.0.0.0:8000 (Serving HTML & /ws)...")
    
    # Cold-start hydration for Data Plane in-memory presence cache (WO0010160)
    RoomRosterRegistry.hydrate_from_db()
    
    asyncio.create_task(mlb_poller())
    asyncio.create_task(run_fastapi())
    asyncio.create_task(system_metrics_poller_loop())
    
    async with websockets.serve(handle_client, "0.0.0.0", 8008, ping_interval=None, ping_timeout=None):
         await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
