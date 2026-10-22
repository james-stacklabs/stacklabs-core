
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
import base64
import sqlite3
import time
# -------------------------------------------------------------

import asyncio
import json
import socket
import time
import os
import sys
from aiohttp import web

# CMDB integration
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

import os
import requests
from dotenv import load_dotenv

def trigger_govee_cloud_alert(interaction_warning=False):
    load_dotenv('/home/james/stacklabs/.env')
    api_key = os.getenv('GOVEE_API_KEY')
    if not api_key:
        print("[GOVEE CLOUD] Error: No API key found in .env")
        return

    headers = {'Govee-API-Key': api_key, 'Content-Type': 'application/json'}
    url_devices = 'https://developer-api.govee.com/v1/devices'
    url_control = 'https://developer-api.govee.com/v1/devices/control'

    try:
        resp = requests.get(url_devices, headers=headers, timeout=5)
        if resp.status_code != 200:
            print(f"[GOVEE CLOUD] Failed to fetch devices: {resp.text}")
            return
            
        devices = resp.json().get('data', {}).get('devices', [])
        if not devices:
            print("[GOVEE CLOUD] No devices returned.")
            return

        print(f"\n[GOVEE CLOUD] API Key validated. Firing Cloud Alert to {len(devices)} nodes...")
        
        # Because we can't pulse/flash without hitting rate limits, 
        # we will use solid Orange for standard alert, Blue for interaction danger.
        if interaction_warning:
            print("[GOVEE CLOUD] INTERACTION WARNING! Metsy is HOME! (Mets Blue)")
            target_color = {'r': 0, 'g': 45, 'b': 114}
        else:
            print("[GOVEE CLOUD] STANDARD ALERT: Metsy is AWAY. (Mets Orange)")
            target_color = {'r': 255, 'g': 89, 'b': 16}
            
        count = 0
        for d in devices:
            mac = d.get('device')
            model = d.get('model')
            payload = {'device': mac, 'model': model, 'cmd': {'name': 'color', 'value': target_color}}
            requests.put(url_control, headers=headers, json=payload, timeout=5)
            time.sleep(1.2) # Rate limit protection pacing
            
            count += 1
            if count >= 8: break # Safety limit

        print("[GOVEE CLOUD] Alert sequence complete.\n")

    except Exception as e:
        print(f"[GOVEE CLOUD] ERROR: {e}")

def trigger_govee_cat_alert(cat_name):
    load_dotenv('/home/james/stacklabs/.env')
    api_key = os.getenv('GOVEE_API_KEY')
    if not api_key: return

    headers = {'Govee-API-Key': api_key, 'Content-Type': 'application/json'}
    url_devices = 'https://developer-api.govee.com/v1/devices'
    url_control = 'https://developer-api.govee.com/v1/devices/control'

    try:
        resp = requests.get(url_devices, headers=headers, timeout=5)
        if resp.status_code != 200: return
        devices = resp.json().get('data', {}).get('devices', [])
        if not devices: return

        if cat_name.lower() == 'metsy':
            print("[GOVEE CLOUD] Metsy Detected via Nest! (Blue)")
            target_color = {'r': 0, 'g': 45, 'b': 114}
        else: # Default to Sam
            print("[GOVEE CLOUD] Sam Detected via Nest! (Orange)")
            target_color = {'r': 255, 'g': 89, 'b': 16}

        count = 0
        for d in devices:
            requests.put(url_control, headers=headers, json={'device': d.get('device'), 'model': d.get('model'), 'cmd': {'name': 'color', 'value': target_color}}, timeout=5)
            time.sleep(1.2)
            count += 1
            if count >= 8: break
    except Exception as e:
        print(f"[GOVEE CLOUD] Error triggering cat alert: {e}")

clients = set()

# State memory (backed by SQLite)
state = {
    "last_fed_timestamp": 0,
    "last_events": [],
    "chindogu_level": 1
}

def init_db():
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sam_tracker_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        note_title TEXT,
        note_text TEXT,
        status_text TEXT,
        daily_naps TEXT,
        adventures TEXT,
        tuna_snacks TEXT,
        picture_url TEXT
    )
    """)
    cur.execute("INSERT OR IGNORE INTO sam_tracker_config (id, note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url) VALUES (1, 'Note for Jeannine', 'Thanks for letting us know he was doing okay and resting up. We can keep in touch and track Sam with the Sam the Cat Tracker website. ❤️', 'On the mend ❤️', '8', '2', '1', 'sam.jpg')")
    conn.commit()
    conn.close()

# Synchronous DB helpers to be run in executor threads
def db_load_events():
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp, message, type FROM sam_tracker_log ORDER BY timestamp DESC, id DESC")
    rows = cur.fetchall()
    events = [{"db_id": row[0], "time": row[1], "message": row[2], "type": row[3]} for row in rows]
    
    cur.execute("SELECT note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url FROM sam_tracker_config WHERE id=1")
    cfg = cur.fetchone()
    config_data = {}
    if cfg:
        config_data = {
            "note_title": cfg[0],
            "note_text": cfg[1],
            "status_text": cfg[2],
            "daily_naps": cfg[3],
            "adventures": cfg[4],
            "tuna_snacks": cfg[5],
            "picture_url": cfg[6],
        }
    conn.close()
    return events, config_data

def db_save_event(event_type, message):
    # [Hoisted to header] import sqlite3
    # [Hoisted to header] import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO sam_tracker_log (timestamp, type, message) VALUES (?, ?, ?)", (timestamp, event_type, message))
    conn.commit()
    conn.close()
    return {"time": timestamp, "message": message, "type": event_type}

def db_delete_event(db_id):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM sam_tracker_log WHERE id=?", (db_id,))
    conn.commit()
    conn.close()

def db_update_config(note_title, note, status_txt, naps, advs, snacks, pic_url):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE sam_tracker_config 
        SET note_title=?, note_text=?, status_text=?, daily_naps=?, adventures=?, tuna_snacks=?, picture_url=? 
        WHERE id=1
    """, (note_title, note, status_txt, naps, advs, snacks, pic_url))
    conn.commit()
    conn.close()

def db_get_friction_level():
    # [Hoisted to header] import sqlite3
    friction_level = 1
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT friction_level FROM fleet_nodes WHERE node_id='Node.73'")
        row = cur.fetchone()
        if row and row[0]:
            friction_level = int(row[0])
    except Exception as e:
        print("DB Check Error:", e)
    finally:
        if conn:
            conn.close()
    return friction_level

def db_get_chindogu_level():
    # [Hoisted to header] import sqlite3
    level = None
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT friction_level FROM fleet_nodes WHERE node_id='Chindogu_Engine'")
        row = cur.fetchone()
        if row and row[0]:
            level = int(row[0])
    except Exception:
        pass
    finally:
        if conn:
            conn.close()
    return level

def db_update_video_status(event_id, final_filename):
    # [Hoisted to header] import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    old_str_1 = f" ||| VID_PROCESSING:/inbox/sam_{event_id}.jpg"
    old_str_1_new = f" ||| VID_PROCESSING:/media/sam_{event_id}.jpg"
    old_str_2 = f" ||| VID_PROCESSING:none"
    new_str = f" ||| VID:/media/{final_filename}"
    
    cur.execute("""
        UPDATE sam_tracker_log 
        SET message = REPLACE(message, ?, ?) 
        WHERE message LIKE ?
    """, (old_str_1, new_str, f"%{event_id}%"))
    
    cur.execute("""
        UPDATE sam_tracker_log 
        SET message = REPLACE(message, ?, ?) 
        WHERE message LIKE ?
    """, (old_str_1_new, new_str, f"%{event_id}%"))
    
    cur.execute("""
        UPDATE sam_tracker_log 
        SET message = REPLACE(message, ?, ?) 
        WHERE message LIKE ?
    """, (old_str_2, new_str, f"%{event_id}%"))
    
    conn.commit()
    conn.close()

# Synchronous file write helper
def save_file(filepath, data):
    with open(filepath, "wb") as f:
        f.write(data)

async def broadcast_state():
    if not clients: return
    msg = {"type": "STATE_UPDATE", "data": state}
    for c in list(clients):
        try:
            await c.send_json(msg)
        except Exception:
            clients.remove(c)

async def websocket_handler(request):
    # Support up to 10MB message sizes to handle base64 image strings
    ws = web.WebSocketResponse(max_msg_size=10 * 1024 * 1024)
    await ws.prepare(request)
    clients.add(ws)
    print("New Sam-Tracker node connected via AIOHTTP!")
    
    chindogu_level = await asyncio.to_thread(db_get_friction_level)
    state["chindogu_level"] = chindogu_level

    await ws.send_json({"type": "STATE_UPDATE", "data": state})
    
    try:
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                continue
            data = json.loads(message.data)
            
            if data.get("type") == "CMD_FED":
                state["last_fed_timestamp"] = time.time()
                event = await asyncio.to_thread(db_save_event, "FED", data.get("message", "Fed Sam"))
                state["last_events"].insert(0, event)
                state["last_events"] = state["last_events"][:50]
                await broadcast_state()

            elif data.get("type") == "CMD_LOG":
                msg = data.get("message", "Saw Sam")
                image_b64 = data.get("image_base64")
                if image_b64:
                    try:
                        # [Hoisted to header] import base64
                        # [Hoisted to header] import time
                        if "," in image_b64:
                            header, encoded = image_b64.split(",", 1)
                        else:
                            encoded = image_b64
                        img_data = base64.b64decode(encoded)
                        ts = int(time.time())
                        
                        filename = f"sam_{ts}.jpg"
                        filepath_public = f"/home/james/stacklabs/14_SamTracker/public/media/{filename}"
                        os.makedirs(os.path.dirname(filepath_public), exist_ok=True)
                        await asyncio.to_thread(save_file, filepath_public, img_data)
                        
                        filepath_dist = f"/home/james/stacklabs/14_SamTracker/dist/media/{filename}"
                        if os.path.exists(os.path.dirname(filepath_dist)):
                            os.makedirs(os.path.dirname(filepath_dist), exist_ok=True)
                            await asyncio.to_thread(save_file, filepath_dist, img_data)
                            
                        # Also copy to raw_uploads to trigger style transfer watcher
                        raw_upload_path = f"/home/james/stacklabs/apps/samtracker/storage/raw_uploads/{filename}"
                        os.makedirs(os.path.dirname(raw_upload_path), exist_ok=True)
                        await asyncio.to_thread(save_file, raw_upload_path, img_data)
                        
                        msg += f" ||| IMG:/media/{filename}"
                    except Exception as e:
                        print("Error saving image:", e)

                event = await asyncio.to_thread(db_save_event, "SIGHTING", msg)
                state["last_events"].insert(0, event)
                state["last_events"] = state["last_events"][:50]
                await broadcast_state()

            elif data.get("type") == "CMD_LOG_VIDEO_START":
                msg = data.get("message", "Saw Sam")
                image_b64 = data.get("image_base64")
                event_id = data.get("event_id", "unknown")
                
                if image_b64:
                    try:
                        # [Hoisted to header] import base64
                        if "," in image_b64:
                            header, encoded = image_b64.split(",", 1)
                        else:
                            encoded = image_b64
                        img_data = base64.b64decode(encoded)
                        
                        filename = f"sam_{event_id}.jpg"
                        filepath_public = f"/home/james/stacklabs/14_SamTracker/public/media/{filename}"
                        os.makedirs(os.path.dirname(filepath_public), exist_ok=True)
                        await asyncio.to_thread(save_file, filepath_public, img_data)
                        
                        filepath_dist = f"/home/james/stacklabs/14_SamTracker/dist/media/{filename}"
                        if os.path.exists(os.path.dirname(filepath_dist)):
                            os.makedirs(os.path.dirname(filepath_dist), exist_ok=True)
                            await asyncio.to_thread(save_file, filepath_dist, img_data)
                            
                        msg += f" ||| VID_PROCESSING:/media/{filename}"
                    except Exception as e:
                        print("Error saving video thumb:", e)
                else:
                    msg += f" ||| VID_PROCESSING:none"

                event = await asyncio.to_thread(db_save_event, "SIGHTING", msg)
                state["last_events"].insert(0, event)
                state["last_events"] = state["last_events"][:50]
                await broadcast_state()

            elif data.get("type") == "CMD_DELETE_LOG":
                db_id = data.get("db_id")
                if db_id:
                    await asyncio.to_thread(db_delete_event, db_id)
                    events, config_data = await asyncio.to_thread(db_load_events)
                    state["last_events"] = events
                    state.update(config_data)
                    await broadcast_state()

            elif data.get("type") == "CMD_UPDATE_CONFIG":
                cfg = data.get("config", {})
                
                img_b64 = data.get("image_base64")
                pic_url = state.get("picture_url", "sam.jpg")
                if img_b64:
                    try:
                        # [Hoisted to header] import base64
                        # [Hoisted to header] import time
                        if "," in img_b64:
                            header, encoded = img_b64.split(",", 1)
                        else:
                            encoded = img_b64
                        img_data = base64.b64decode(encoded)
                        ts = int(time.time())
                        filename = f"sam_{ts}.jpg"
                        
                        # Save to public for persistence across builds
                        filepath_public = f"/home/james/stacklabs/14_SamTracker/public/{filename}"
                        await asyncio.to_thread(save_file, filepath_public, img_data)
                            
                        # Save to dist so it is immediately served by the current aiohttp process
                        filepath_dist = f"/home/james/stacklabs/14_SamTracker/dist/{filename}"
                        if os.path.exists("/home/james/stacklabs/14_SamTracker/dist"):
                            await asyncio.to_thread(save_file, filepath_dist, img_data)
                                
                        pic_url = filename
                    except Exception as e:
                        print("Error saving config image:", e)

                note_title = cfg.get("note_title", state.get("note_title", "Note for Jeannine"))
                note = cfg.get("note_text", state.get("note_text", ""))
                status_txt = cfg.get("status_text", state.get("status_text", ""))
                naps = cfg.get("daily_naps", state.get("daily_naps", ""))
                advs = cfg.get("adventures", state.get("adventures", ""))
                snacks = cfg.get("tuna_snacks", state.get("tuna_snacks", ""))

                await asyncio.to_thread(db_update_config, note_title, note, status_txt, naps, advs, snacks, pic_url)

                state["note_title"] = note_title
                state["note_text"] = note
                state["status_text"] = status_txt
                state["daily_naps"] = naps
                state["adventures"] = advs
                state["tuna_snacks"] = snacks
                state["picture_url"] = pic_url
                
                await broadcast_state()
                
            elif data.get("type") == "CMD_SAM_DETECTED":
                print("🚨 SAM DETECTED PROTOCOL TRIGGERED! 🚨")
                t_status = state.get("metsy_status", "HOME")
                interaction_warning = (t_status == "HOME")
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, trigger_govee_cloud_alert, interaction_warning)
                out_msg = {"type": "ORANGE_ALERT"}
                for c in list(clients):
                    try: 
                        await c.send_json(out_msg)
                    except: 
                        pass
    except Exception as e:
        pass
    finally:
        if ws in clients: clients.remove(ws)
    return ws

import urllib.request
import datetime

def check_mando_motion():
    try:
        import cv2
        import numpy as np
        cap = cv2.VideoCapture("http://100.88.5.122:8081/cam/0")
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        ret1, f1 = cap.read()
        ret2, f2 = cap.read()
        cap.release()
        if ret1 and ret2:
            g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(g1, g2)
            score = np.sum(diff)
            return score > 3000000  # threshold
    except Exception as e:
        print("[Motion Error]", e)
    return False

def check_weather():
    try:
        req = urllib.request.Request("https://wttr.in/Smyrna+30080?format=j1", headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=3)
        wdata = json.loads(res.read().decode('utf-8'))
        return str(wdata['current_condition'][0]['weatherDesc'][0]['value']).lower()
    except Exception:
        return "clear"

def check_tractive():
    try:
        req = urllib.request.Request("http://graph.tractive.com/4/tracker/public/XHRMVRYR", headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=3)
        data = res.read().decode('utf-8')
        if "IN_THE_WILD" in data or "OUT_OF_ZONE" in data:
            return "IN_THE_WILD"
    except Exception:
        pass
    return "HOME"

async def check_slider_loop():
    last_tractive_check = 0.0
    cached_tractive_status = "HOME"
    while True:
        try:
            target_level = None
            metsy_status = "HOME"
            
            # 1. Tractive Geofence Breach -> Level 6 (throttled to once every 300 seconds to prevent battery drain)
            now = time.time()
            if now - last_tractive_check >= 300.0:
                last_tractive_check = now
                cached_tractive_status = await asyncio.to_thread(check_tractive)
            t_status = cached_tractive_status
            
            if t_status == "IN_THE_WILD":
                target_level = 6
                metsy_status = "IN_THE_WILD"
                
            # 2. Mando Camera Motion -> Level 9
            is_motion = await asyncio.to_thread(check_mando_motion)
            if is_motion:
                target_level = 9
                
            # 3. Time of day: 11pm-6am calm -> Level 1
            hour = datetime.datetime.now().hour
            if hour >= 23 or hour < 6:
                if target_level is None or target_level < 1:
                    target_level = 1

            # 4. Weather API (Smyrna) -> Pilot prompt
            weather = await asyncio.to_thread(check_weather)
            if "rain" in weather or "shower" in weather or "storm" in weather:
                if state.get("weather_alert") != "sent":
                    out_msg = {"type": "WEATHER_PROMPT", "user": "WEATHER NODE", "text": "RAIN DETECTED IN SMYRNA - PILOT PROMPT REQUIRED", "color": "#00f0ff"}
                    for c in list(clients):
                        try: await c.send_json(out_msg)
                        except: pass
                    state["weather_alert"] = "sent"
            else:
                state["weather_alert"] = "clear"

            if target_level is not None:
                new_level = target_level
            else:
                # Revert to DB slider if no overrides
                new_level = state["chindogu_level"]
                db_level = await asyncio.to_thread(db_get_chindogu_level)
                if db_level is not None:
                    new_level = db_level
            
            changed = False
            if new_level != state["chindogu_level"]:
                state["chindogu_level"] = new_level
                changed = True
            
            if metsy_status != state.get("metsy_status"):
                state["metsy_status"] = metsy_status
                changed = True

            if changed:
                await broadcast_state()

        except Exception as e:
            print("[Loop Error]", e)
            pass
        await asyncio.sleep(4)

async def handle_video_upload(request):
    reader = await request.multipart()
    video_file = None
    event_id = None
    
    while True:
        part = await reader.next()
        if part is None:
            break
        if part.name == 'video':
            video_file = await part.read()
        elif part.name == 'event_id':
            event_id = await part.text()
            
    if not video_file or not event_id:
        return web.json_response({"error": "Missing video or event_id"}, status=400)
        
    ts = int(time.time())
    raw_filename = f"/home/james/stacklabs/pilot_drops/incoming/raw_sam_{event_id}.mp4"
    final_filename = f"sam_{event_id}.mp4"
    final_path = f"/home/james/stacklabs/14_SamTracker/public/media/{final_filename}"
    
    os.makedirs("/home/james/stacklabs/pilot_drops/incoming", exist_ok=True)
    os.makedirs("/home/james/stacklabs/14_SamTracker/public/media", exist_ok=True)
    
    await asyncio.to_thread(save_file, raw_filename, video_file)
    
    # Start ffmpeg async
    async def process_video():
        try:
            cmd = [
                "ffmpeg", "-y", "-i", raw_filename,
                "-vf", "scale=-2:720",
                "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "128k",
                final_path
            ]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await process.communicate()
            
            # Delete raw file to save space
            if os.path.exists(raw_filename):
                await asyncio.to_thread(os.remove, raw_filename)
                
            # Update DB to swap VID_PROCESSING for VID using thread pool
            await asyncio.to_thread(db_update_video_status, event_id, final_filename)
            
            # Reload state and broadcast thread-safely
            events, config_data = await asyncio.to_thread(db_load_events)
            state["last_events"] = events
            state.update(config_data)
            await broadcast_state()
            
        except Exception as e:
            print("ffmpeg error:", e)
            
    loop = asyncio.get_running_loop()
    loop.create_task(process_video())
    
    return web.json_response({"status": "processing", "id": event_id})

async def handle_internal_cat_alert(request):
    try:
        data = await request.json()
        cat_name = data.get('cat', 'sam')
        
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, trigger_govee_cat_alert, cat_name)
        
        msg = f"ORANGE ALERT: {cat_name.upper()} SPOTTED VIA NEST CAM!"
        
        await asyncio.to_thread(db_save_event, "SIGHTING", msg)
        events, config_data = await asyncio.to_thread(db_load_events)
        state["last_events"] = events
        state.update(config_data)
        await broadcast_state()
        
        out_msg = {"type": "ORANGE_ALERT"}
        for ws in list(clients):
            try: await ws.send_json(out_msg)
            except: pass
        
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_internal_reload_state(request):
    try:
        events, config_data = await asyncio.to_thread(db_load_events)
        state["last_events"] = events
        state.update(config_data)
        await broadcast_state()
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def index_handler(request):
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return web.FileResponse('/home/james/stacklabs/14_SamTracker/dist/index.html', headers=headers)

async def main():
    print("🚀 Sovereign Sam-Tracker Unified Backend booting on 0.0.0.0:8083...")
    asyncio.create_task(check_slider_loop())
    
    app = web.Application(client_max_size=50*1024*1024) # 50MB limit
    
    # 1. API and WebSockets
    app.router.add_post('/sam/api/upload_video', handle_video_upload)
    app.router.add_post('/api/upload_video', handle_video_upload)
    
    app.router.add_post('/sam/api/internal/cat_alert', handle_internal_cat_alert)
    app.router.add_post('/api/internal/cat_alert', handle_internal_cat_alert)
    
    app.router.add_post('/sam/api/internal/reload_state', handle_internal_reload_state)
    app.router.add_post('/api/internal/reload_state', handle_internal_reload_state)
    
    app.router.add_get('/sam/ws', websocket_handler)
    app.router.add_get('/ws', websocket_handler)
    
    # 2. Inbox Static Serving
    app.router.add_static('/sam/inbox', '/home/james/stacklabs/pilot_drops')
    app.router.add_static('/inbox', '/home/james/stacklabs/pilot_drops')
    
    app.router.add_static('/sam/media', '/home/james/stacklabs/14_SamTracker/public/media')
    app.router.add_static('/media', '/home/james/stacklabs/14_SamTracker/public/media')
    
    # 3. Frontend Static Serving
    app.router.add_get('/', index_handler)
    app.router.add_get('/sam/', index_handler)
    app.router.add_get('/sam', index_handler)
    if os.path.exists('/home/james/stacklabs/14_SamTracker/dist'):
        app.router.add_static('/assets/', '/home/james/stacklabs/14_SamTracker/dist/assets')
        app.router.add_static('/sam/', '/home/james/stacklabs/14_SamTracker/dist')
        
        async def static_fallback(request):
            filename = request.match_info.get('filename')
            filepath = f'/home/james/stacklabs/14_SamTracker/dist/{filename}'
            if os.path.exists(filepath) and os.path.isfile(filepath):
                headers = {
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
                return web.FileResponse(filepath, headers=headers)
            return web.HTTPNotFound()
            
        app.router.add_get('/{filename}', static_fallback)
        
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8083)
    await site.start()
    
    await asyncio.Future()

if __name__ == "__main__":
    init_db()
    events, config_data = db_load_events()
    state["last_events"] = events
    state.update(config_data)
    asyncio.run(main())
