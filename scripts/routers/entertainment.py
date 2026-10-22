
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
import datetime
import glob
import requests
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import uuid
# -------------------------------------------------------------

from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security

router = APIRouter()


def discover_service_url(port: int, service_name: str, path_prefix: str = "") -> str:
    import socket
    hosts = ["127.0.0.1", "clio.taila01894.ts.net"]
    for host in hosts:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return f"http://{host}:{port}{path_prefix}"
        except OSError:
            continue
    # Fallback to local
    return f"http://127.0.0.1:{port}{path_prefix}"



@router.post("/api/vengeance/process")
async def process_vengeance(audio: UploadFile = File(...)):
    try:
        content = await audio.read()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE sys_menu_item
            SET cost_credits = CAST(cost_credits * 0.65 AS INTEGER),
                is_spite_special = 1
            WHERE stack_origin = 'spiteslice' AND target_competitor = 'davincis'
        """)
        conn.commit()
        rows_updated = cur.rowcount
        conn.close()

        # Log system message
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            chatter_id = uuid.uuid4().hex
            cur.execute("""
                INSERT INTO sys_room_chatter (sys_id, room_id, sender, message)
                VALUES (?, 'smyrna_heights', 'system', ?)
            """, (chatter_id, f"🎙️ Vengeance Audio processed! Mutation applied: Spite Slice pricing sliced by 35% for DaVinci's targets. ({rows_updated} items updated)"))
            conn.commit()
            conn.close()
        except Exception as ce:
            print(f"Error logging vengeance chatter: {ce}")

        return {
            "status": "success",
            "message": "Automated Spite Pricing Mutation triggered successfully.",
            "rows_updated": rows_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================================
# END AUTH SUBSYSTEM
# ============================================================================




# ── Theater Remote Relay ───────────────────────────────────────────────────

class TheaterConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

theater_manager = TheaterConnectionManager()

@router.websocket("/ws/theater")
async def websocket_theater_endpoint(websocket: WebSocket):
    await theater_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        theater_manager.disconnect(websocket)

class TheaterCommand(BaseModel):
    command: str
    target: str | None = None
    time: float | None = None
    volume: float | None = None
    extra: dict | None = None

@router.post("/api/theater/command")
async def send_theater_command(req: TheaterCommand):
    # Broadcast to all active websockets first
    await theater_manager.broadcast({
        "type": "THEATER_COMMAND",
        "command": req.command,
        "target": req.target,
        "time": req.time,
        "volume": req.volume,
        "extra": req.extra
    })

    # Full X11+DBUS session environment required for all xdotool calls
    x_env = {
        "DISPLAY": ":0",
        "XAUTHORITY": "/home/james/.Xauthority",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "XDG_RUNTIME_DIR": "/run/user/1000",
        "HOME": "/home/james",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/snap/bin",
    }

    def xrun(*cmd):
        subprocess.run(list(cmd), env=x_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def focus_browser_and_key(key: str):
        """Focus the topmost player window (MPV or Browser) then send a keystroke."""
        # Detect running MPV process first
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--class", "mpv"],
            env=x_env, capture_output=True, text=True
        )
        win_ids = result.stdout.strip().split()
        if win_ids:
            xrun("xdotool", "windowfocus", "--sync", win_ids[-1])
            # Translate keys for MPV if needed
            mpv_key = key
            if key == 'space' or key == 'p':
                mpv_key = 'space'
            xrun("xdotool", "key", mpv_key)
            return

        # Fallback to browser
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", "Chromium|Chrome|cinema"],
            env=x_env, capture_output=True, text=True
        )
        win_ids = result.stdout.strip().split()
        if win_ids:
            xrun("xdotool", "windowfocus", "--sync", win_ids[-1])
        # Always send key after focus
        xrun("xdotool", "key", key)

    # Wake up the display
    xrun("xdotool", "mousemove_relative", "1", "1")
    xrun("xdotool", "mousemove_relative", "--", "-1", "-1")

    # Map directional commands to xdotool keys
    xdotool_map = {
        'up': 'Up',
        'down': 'Down',
        'left': 'Left',
        'right': 'Right',
        'select': 'Return',
        'back': 'Escape',
        'home': 'Browser_Home',
        'space': 'space'
    }

    
    if req.command in xdotool_map:
        if req.command == 'back':
            subprocess.run("pkill -9 mpv", shell=True)
        focus_browser_and_key(xdotool_map[req.command])
    elif req.command == 'mousemove':
        if req.extra and 'x' in req.extra and 'y' in req.extra:
            dx, dy = req.extra['x'], req.extra['y']
            xrun("xdotool", "mousemove_relative", str(dx), str(dy))
    elif req.command == 'mouseclick':
        xrun("xdotool", "click", "1")
    elif req.command == 'volume_up':
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], env=x_env)
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"], env=x_env)
    elif req.command == 'volume_down':
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], env=x_env)
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"], env=x_env)
    elif req.command == 'play_mpv':
        if req.extra and 'video_url' in req.extra:
            video_url = req.extra['video_url']
            if video_url.startswith("/stream/"):
                rel_path = video_url[len("/stream/"):]
            else:
                rel_path = video_url
            # [Hoisted to header] import urllib.parse
            rel_path = urllib.parse.unquote(rel_path)
            abs_path = os.path.join("/home/james/stacklabs/media_vault", rel_path)
            with open("/tmp/mpv_debug.log", "w") as f:
                f.write(f"video_url: {video_url}\n")
                f.write(f"rel_path: {rel_path}\n")
                f.write(f"abs_path: {abs_path}\n")
                f.write(f"exists: {os.path.exists(abs_path)}\n")
                
            # Pre-emptive incident logging in database (KI-022 Watchdog Log Safeguard)
            # [Hoisted to header] import sqlite3
            # [Hoisted to header] import uuid
            # [Hoisted to header] import datetime
            db_path = "/home/james/stacklabs/dna/sovereign_now.db"
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                # Auto-generate INC number
                row = cur.execute("SELECT number FROM sovereign_tickets WHERE type='INC' ORDER BY number DESC LIMIT 1").fetchone()
                if row:
                    try:
                        last_num = int(row[0].replace('INC', ''))
                        inc_number = f"INC{last_num + 1:07d}"
                    except:
                        inc_number = f"INC{int(datetime.datetime.now(datetime.UTC).timestamp())}"
                else:
                    inc_number = "INC0000001"
                    
                sys_id = uuid.uuid4().hex
                file_name = os.path.basename(abs_path)
                short_desc = f"HDMI-CEC TV play command: {file_name}"
                description = f"User triggered MPV playback for {abs_path} on local display. Wake commands sent."
                created_at = datetime.datetime.now(datetime.UTC).isoformat()
                
                cur.execute("""
                    INSERT INTO sovereign_tickets (
                        sys_id, number, type, short_description, description, 
                        state, priority, assigned_to, cmdb_ci, work_notes, 
                        sys_created_on, sys_updated_on
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sys_id,
                    inc_number,
                    "INC",
                    short_desc,
                    description,
                    4, # 4 = Resolved/Done
                    3, # 3 = Medium
                    "system",
                    "448032d5-c6fd-46cf-b81f-53be7bde30e5", # Hobbes HW CI sys_id
                    f"Pre-execution watchdog record generated. Spawning mpv player for {file_name}",
                    created_at,
                    created_at
                ))
                conn.commit()
                conn.close()
                print(f"[Watchdog] Successfully logged pre-emptive incident {inc_number} for playback.")
            except Exception as e:
                print(f"[Watchdog] Error logging play incident: {e}")
                
            # Wake TV via HDMI-CEC prior to spawning player
            try:
                subprocess.Popen("echo 'on 0' | cec-client -s -d 1 && echo 'as' | cec-client -s -d 1", shell=True)
            except Exception as cec_err:
                print(f"Failed to wake TV: {cec_err}")
                
            # Kill existing mpv
            subprocess.run("pkill -9 mpv", shell=True)
            
            # Launch mpv on display :0 in full screen with direct DRM KMS rendering and IPC socket for TV remote control
            subprocess.Popen(
                ["mpv", "--fs", "--input-ipc-server=/tmp/mpvsocket", "--vo=drm", "--hwdec=auto", abs_path],
                env=x_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp
            )
    elif req.command == 'mute':
        subprocess.run("pactl set-sink-mute 0 toggle", shell=True)
    elif req.command == 'restart_cinema':
        # Kill whatever is on port 3008, then relaunch Cinema Vite server
        subprocess.run("fuser -k 3008/tcp", shell=True)
        # [Hoisted to header] import time
        time.sleep(1)
        subprocess.Popen(
            "cd /home/james/stacklabs/02_Sovereign_Media && npm run dev -- --host 0.0.0.0 --port 3008",
            shell=True,
            stdout=open("/tmp/vite_cinema.log", "w"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setpgrp
        )
    elif req.command == 'launch_cinema':
        # Launch Chrome on clio's display. Must pass full X11+DBUS session env or Chrome silently fails.
        cinema_url = "https://clio.taila01894.ts.net:3008/cinema-portal/?room=living_room"
        launch_env = {
            "DISPLAY": ":0",
            "XAUTHORITY": "/home/james/.Xauthority",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
            "HOME": "/home/james",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/snap/bin",
        }
        subprocess.Popen(
            ["google-chrome", "--new-window", "--start-maximized",
             "--password-store=basic",
             "--force-device-scale-factor=2.0",
             "--disable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL",
             cinema_url],
            env=launch_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp
        )
    
    await theater_manager.broadcast({
        "type": "THEATER_COMMAND",
        "command": req.command,
        "target": req.target,
        "time": req.time,
        "volume": req.volume
    })
    return {"status": "success"}

@router.get("/api/cinema/status")
async def cinema_status():
    """Returns whether the Cinema Vite server on port 3008 is up."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 3008), timeout=2):
            return {"status": "online"}
    except OSError:
        return {"status": "offline"}

# ── End Theater Remote Relay ───────────────────────────────────────────────

# ── Sovereign Ingestor API (STRY1779446316) ────────────────────────────────
# POST /api/ingest — bulk insert tickets into sovereign_tickets
# Accepts: JSON array of ticket objects
# Returns: per-row success/error report

DB_INGEST_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
VALID_TYPES = {"STRY", "DFCT", "ENHC", "INC", "REQ"}

CORS_HEADERS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}


class CastRequest(BaseModel):
    url: str

@router.post("/api/cast_tv/{tv_ip}")
async def cast_to_tv(tv_ip: str, req: CastRequest):
    print(f"Casting to {tv_ip}: {req.url}")
    subprocess.run(["adb", "connect", f"{tv_ip}:5555"])
    subprocess.run(["adb", "-s", f"{tv_ip}:5555", "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f'"{req.url}"'])
    subprocess.run(["adb", "disconnect", f"{tv_ip}:5555"])
    return {"status": "success", "tv_ip": tv_ip, "url": req.url}

class TVControlRequest(BaseModel):
    ip: str
    command: str

@router.post("/api/television/control")
async def television_control(req: TVControlRequest):
    print(f"Television Control Command [{req.command}] to {req.ip}")
    
    # Pre-emptive incident logging in database (KI-022)
    # [Hoisted to header] import sqlite3
    # [Hoisted to header] import uuid
    # [Hoisted to header] import datetime
    # [Hoisted to header] import subprocess
    
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Auto-generate INC number
    row = cur.execute("SELECT number FROM sovereign_tickets WHERE type='INC' ORDER BY number DESC LIMIT 1").fetchone()
    if row:
        try:
            last_num = int(row[0].replace('INC', ''))
            inc_number = f"INC{last_num + 1:07d}"
        except:
            inc_number = f"INC{int(datetime.datetime.now(datetime.UTC).timestamp())}"
    else:
        inc_number = "INC0000001"
        
    sys_id = uuid.uuid4().hex
    display_ip = req.ip
    if display_ip == "127.0.0.1":
        display_ip = "clio.taila01894.ts.net"
    short_desc = f"HDMI-CEC TV state override: {req.command} on {display_ip}"
    description = f"User/System triggered TV state override command '{req.command}' on outpost {display_ip}."
    created_at = datetime.datetime.now(datetime.UTC).isoformat()
    
    try:
        cur.execute("""
            INSERT INTO sovereign_tickets (
                sys_id, number, type, short_description, description, 
                state, priority, assigned_to, cmdb_ci, work_notes, 
                sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            inc_number,
            "INC",
            short_desc,
            description,
            4, # 4 = Resolved/Done
            3, # 3 = Medium
            "system",
            "448032d5-c6fd-46cf-b81f-53be7bde30e5", # Hobbes HW CI sys_id
            f"Pre-execution watchdog record generated. Executing command: {req.command}",
            created_at,
            created_at
        ))
        conn.commit()
        print(f"[Watchdog] Successfully logged pre-emptive incident {inc_number}")
    except Exception as e:
        print(f"[Watchdog] Error logging incident: {e}")
    finally:
        conn.close()
        
    # Translate and run the remote CEC command
    cec_cmd = ""
    if req.command == "power_on":
        cec_cmd = "echo 'on 0' | cec-client -s -d 1 && echo 'as' | cec-client -s -d 1"
    elif req.command == "power_off":
        cec_cmd = "echo 'standby 0' | cec-client -s -d 1"
    elif req.command == "input_switch":
        cec_cmd = "echo 'as' | cec-client -s -d 1"
    else:
        return {"status": "error", "message": f"Unknown command: {req.command}"}
        
    if cec_cmd:
        # Launch remote SSH command
        subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", f"james@{req.ip}", cec_cmd])
        
    return {"status": "success", "incident_logged": inc_number, "command": req.command}

class CinemaCommand(BaseModel):
    ip: str
    command: str

@router.post("/api/cinema/command")
async def cinema_remote_cmd(req: CinemaCommand):
    print(f"Cinema Command [{req.command}] to {req.ip}")
    
    mpv_cmd = ""
    if req.command == "launch":
        mpv_cmd = 'killall mpv || true && nohup mpv --input-ipc-server=/tmp/mpvsocket --vo=drm --hwdec=auto --sid=1 /home/james/media/movie.mkv > /tmp/mpv.log 2>&1 &'
    elif req.command == "pause":
        mpv_cmd = 'echo \'{ "command": ["cycle", "pause"] }\' | socat - /tmp/mpvsocket'
    elif req.command == "seek_fwd":
        mpv_cmd = 'echo \'{ "command": ["seek", 10] }\' | socat - /tmp/mpvsocket'
    elif req.command == "seek_back":
        mpv_cmd = 'echo \'{ "command": ["seek", -10] }\' | socat - /tmp/mpvsocket'
    elif req.command == "toggle_subtitles":
        mpv_cmd = 'echo \'{ "command": ["cycle", "sub-visibility"] }\' | socat - /tmp/mpvsocket'
    elif req.command == "quit":
        mpv_cmd = 'echo \'{ "command": ["quit"] }\' | socat - /tmp/mpvsocket'
        
    if mpv_cmd:
        subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=no", f"james@{req.ip}", mpv_cmd])
        
    return {"status": "success"}

class CinemaRequest(BaseModel):
    title: str
    media_type: str = "movie"
    target_node: str = "clio"
    mst3k_mode: bool = False

@router.get("/api/cinema/search")
async def api_cinema_search(term: str, media_type: str = "movie"):
    """
    Search Sonarr or Radarr for matching titles.
    """
    # [Hoisted to header] import requests
    headers = {"X-Api-Key": "3a86bddfeefa4c93b104f33a534ffb72"}
    results = []
    
    if media_type == "tv":
        try:
            sonarr_url = discover_service_url(8989, "sonarr", "/sonarr")
            url = f"{sonarr_url}/api/v3/series/lookup?term={requests.utils.quote(term)}"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                for item in res.json():
                    added = item.get("id") is not None
                    poster = None
                    for img in item.get("images", []):
                        if img.get("coverType") == "poster":
                            poster = img.get("remoteUrl") or img.get("url")
                            break
                    if not poster:
                        poster = item.get("remotePoster")
                        
                    results.append({
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "overview": item.get("overview"),
                        "poster_url": poster,
                        "media_type": "tv",
                        "tvdb_or_tmdb_id": item.get("tvdbId"),
                        "added": added
                    })
        except Exception as e:
            print(f"Sonarr search failed: {e}")
            
    else: # movie
        try:
            radarr_url = discover_service_url(7878, "radarr", "")
            url = f"{radarr_url}/api/v3/movie/lookup?term={requests.utils.quote(term)}"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                for item in res.json():
                    added = item.get("id") is not None
                    poster = None
                    for img in item.get("images", []):
                        if img.get("coverType") == "poster":
                            poster = img.get("remoteUrl") or img.get("url")
                            break
                    if not poster:
                        poster = item.get("remotePoster")
                        
                    results.append({
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "overview": item.get("overview"),
                        "poster_url": poster,
                        "media_type": "movie",
                        "tvdb_or_tmdb_id": item.get("tmdbId"),
                        "added": added
                    })
        except Exception as e:
            print(f"Radarr search failed: {e}")
            
    return results

@router.get("/api/cinema/queue")
async def api_cinema_queue():
    """
    Tunnel to SABnzbd's client queue API on Port 8086.
    """
    # [Hoisted to header] import requests
    url = "http://127.0.0.1:8086/api?mode=queue&apikey=4ee070eb74734e9f9f02143533be6bdd&output=json"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
        else:
            return {"status": "error", "message": f"SABnzbd returned status code {res.status_code}"}
    except Exception as e:
        print(f"SABnzbd queue fetch failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/api/cinema/request")
async def cinema_request(req: CinemaRequest):
    print(f"Cinema Request: {req.title} (media_type={req.media_type}, target={req.target_node}, mst3k={req.mst3k_mode})")
    
    # [Hoisted to header] import glob
    # [Hoisted to header] import requests
    import threading
    
    # Handle TV shows separately
    if req.media_type == "tv":
        def trigger_sonarr():
            try:
                headers = {"X-Api-Key": "3a86bddfeefa4c93b104f33a534ffb72"}
                search_term = req.title
                if req.title.lower() == "seinfeld":
                    search_term = "tvdb:79169"
                sonarr_url = discover_service_url(8989, "sonarr", "/sonarr")
                lookup_url = f"{sonarr_url}/api/v3/series/lookup?term={requests.utils.quote(search_term)}"
                res = requests.get(lookup_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    results = res.json()
                    if results:
                        best_match = results[0]
                        series_id = best_match.get("id")
                        if series_id is not None:
                            cmd_payload = {"name": "SeriesSearch", "seriesId": series_id}
                            requests.post(f"{sonarr_url}/api/v3/command", json=cmd_payload, headers=headers, timeout=5)
                        else:
                            add_payload = {
                                "title": best_match["title"],
                                "tvdbId": best_match["tvdbId"],
                                "qualityProfileId": 1,
                                "languageProfileId": 1,
                                "rootFolderPath": "/media_vault/TV_Shows",
                                "monitored": True,
                                "seasonFolder": True,
                                "seriesType": "standard",
                                "addOptions": {
                                    "searchForMissingEpisodes": True
                                }
                            }
                            requests.post(f"{sonarr_url}/api/v3/series", json=add_payload, headers=headers, timeout=5)
            except Exception as e:
                print(f"Silent Sonarr trigger failed: {e}")
        
        threading.Thread(target=trigger_sonarr).start()
        return {
            "status": "triggered_download",
            "message": f"TV show '{req.title}' search/download triggered in Sonarr.",
            "mst3k_mode": req.mst3k_mode
        }
        
    media_dir = "/home/james/stacklabs/media_vault/Movies"
    title_clean = req.title.lower().replace(" ", "_")
    
    # 1. Scan for matching file name
    found_file = None
    if os.path.exists(media_dir):
        files = os.listdir(media_dir)
        for f in files:
            f_clean = f.lower().replace(" ", "_").replace(".", "_")
            if title_clean in f_clean:
                found_file = os.path.join(media_dir, f)
                break
                
    if not found_file:
        # silent Radarr request trigger
        def trigger_radarr():
            try:
                headers = {"X-Api-Key": "3a86bddfeefa4c93b104f33a534ffb72"}
                radarr_url = discover_service_url(7878, "radarr", "")
                lookup_url = f"{radarr_url}/api/v3/movie/lookup?term={requests.utils.quote(req.title)}"
                res = requests.get(lookup_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    results = res.json()
                    if results:
                        best_match = results[0]
                        movie_id = best_match.get("id")
                        if movie_id is not None:
                            cmd_payload = {"name": "MoviesSearch", "movieIds": [movie_id]}
                            requests.post(f"{radarr_url}/api/v3/command", json=cmd_payload, headers=headers, timeout=5)
                        else:
                            add_payload = {
                                "title": best_match["title"],
                                "tmdbId": best_match["tmdbId"],
                                "qualityProfileId": 1,
                                "rootFolderPath": "/media_vault/Movies/",
                                "monitored": True,
                                "addOptions": {
                                    "searchForMovie": True
                                }
                            }
                            requests.post(f"{radarr_url}/api/v3/movie", json=add_payload, headers=headers, timeout=5)
            except Exception as e:
                print(f"Silent Radarr trigger failed: {e}")
                
        threading.Thread(target=trigger_radarr).start()
        return {
            "status": "triggered_download",
            "message": "Movie not found locally. Radarr search triggered.",
            "mst3k_mode": req.mst3k_mode
        }
        
    # 2. Wake & Switch TV Input via HDMI-CEC, logging INC under KI-022
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Auto-generate INC number
    row = cur.execute("SELECT number FROM sovereign_tickets WHERE type='INC' ORDER BY number DESC LIMIT 1").fetchone()
    if row:
        try:
            last_num = int(row[0].replace('INC', ''))
            inc_number = f"INC{last_num + 1:07d}"
        except:
            inc_number = f"INC{int(datetime.now(timezone.utc).timestamp())}"
    else:
        inc_number = "INC0000001"
        
    sys_id = uuid.uuid4().hex
    short_desc = f"HDMI-CEC TV state override: power_on on clio.taila01894.ts.net"
    description = f"Automated Cinema Request trigger for '{req.title}' on Clio."
    created_at = datetime.now(timezone.utc).isoformat()
    
    try:
        cur.execute("""
            INSERT INTO sovereign_tickets (
                sys_id, number, type, short_description, description, 
                state, priority, assigned_to, cmdb_ci, work_notes, 
                sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            inc_number,
            "INC",
            short_desc,
            description,
            4, # 4 = Resolved
            3, # 3 = Medium
            "system",
            "448032d5-c6fd-46cf-b81f-53be7bde30e5",
            f"Cinema Request initiated local playback. Title: {req.title}. MST3K Mode: {req.mst3k_mode}",
            created_at,
            created_at
        ))
        conn.commit()
    except Exception as db_err:
        print(f"[Watchdog] Error logging incident: {db_err}")
    finally:
        conn.close()
        
    # Run HDMI-CEC command locally
    try:
        subprocess.run("echo 'on 0' | cec-client -s -d 1 && echo 'as' | cec-client -s -d 1", shell=True)
    except Exception as e:
        print(f"Error executing local CEC command: {e}")
        
    # 3. Video Playback via mpv
    overlay_stream = "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"
    if req.mst3k_mode:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            row = cur.execute("SELECT stream_url FROM mlb_schedule WHERE room_state = 'active' AND stream_url IS NOT NULL LIMIT 1").fetchone()
            if row and row[0]:
                overlay_stream = row[0]
            conn.close()
        except Exception as e:
            print(f"Error fetching active stream for overlay: {e}")
            
        mpv_cmd = f"killall mpv || true && nohup mpv --input-ipc-server=/tmp/mpvsocket --vo=drm --hwdec=auto --sid=1 --external-file='{overlay_stream}' --lavfi-complex=\"[vid1] scale=1920:1080 [main]; [vid2] scale=480:270 [over]; [main][over] overlay=main_w-overlay_w-50:main_h-overlay_h-50 [vo]\" '{found_file}' > /tmp/mpv.log 2>&1 &"
    else:
        mpv_cmd = f"killall mpv || true && nohup mpv --input-ipc-server=/tmp/mpvsocket --vo=drm --hwdec=auto --sid=1 '{found_file}' > /tmp/mpv.log 2>&1 &"
        
    subprocess.Popen(mpv_cmd, shell=True)
    
    return {
        "status": "playing",
        "local_path": found_file,
        "incident_logged": inc_number,
        "mst3k_mode": req.mst3k_mode
    }

@router.get("/cinema")
async def get_cinema_ui():
    return FileResponse("/home/james/stacklabs/media_vault/cinema_remote.html")

class ManuelChatRequest(BaseModel):
    message: str
    history: list[dict] = []

@router.post("/api/cinema/manuel")
async def chat_with_manuel(req: ManuelChatRequest):
    try:
        # [Hoisted to header] import sys
        if '/home/james/stacklabs/scripts' not in sys.path:
            sys.path.insert(0, '/home/james/stacklabs/scripts')
        from media_manuel_agent import ask_manuel
        response = ask_manuel(req.message, req.history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
