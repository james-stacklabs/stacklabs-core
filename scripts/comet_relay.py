import asyncio
import json
import sqlite3
import os
import aiohttp
import socket
from aiohttp import web
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PORT = 8015
SDLC_PORTAL_URL = "http://localhost:8095/api/tickets"

# Govee UDP Signaling Configuration
GOVEE_PORT = int(os.getenv("GOVEE_PORT", 4003))
GOVEE_DEVICE_IPS = [
    ip.strip() for ip in os.getenv("GOVEE_DEVICE_IP", "192.168.1.173,192.168.1.174,192.168.1.176,192.168.1.188").split(",")
    if ip.strip()
]

# Track active govee alert background task
govee_alert_state = {
    "task": None
}


def send_govee_command(payload):
    """Send JSON payload to Govee device IPs over UDP Port 4003."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data_bytes = json.dumps(payload).encode('utf-8')
    for ip in GOVEE_DEVICE_IPS:
        try:
            sock.sendto(data_bytes, (ip, GOVEE_PORT))
            print(f"[GOVEE UDP] Sent payload to {ip}:{GOVEE_PORT}: {payload}")
        except Exception as e:
            print(f"[GOVEE UDP ERROR] Failed to send to {ip}: {e}")
    sock.close()

async def govee_alert_loop():
    print("[GOVEE ALERT] Spawning indefinite care alert loop...")
    
    crimson_payload = {
        "msg": {
            "cmd": "colorWC",
            "data": {
                "color": { "r": 239, "g": 68, "b": 68 },
                "colorTem": 0
            }
        }
    }
    
    amber_payload = {
        "msg": {
            "cmd": "colorWC",
            "data": {
                "color": { "r": 245, "g": 158, "b": 11 },
                "colorTem": 0
            }
        }
    }
    
    state = False
    try:
        while True:
            # Alternate colors
            payload = amber_payload if state else crimson_payload
            state = not state
            
            # Send command
            send_govee_command(payload)
            
            # Sleep 500ms
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        print("[GOVEE ALERT] Alert loop cancelled.")
        raise
    except Exception as e:
        print(f"[GOVEE ALERT LOOP ERROR] {e}")



clients = set()

def query_db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(query, args)
        if commit:
            conn.commit()
            lastrowid = cur.lastrowid
            return lastrowid
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

async def get_initial_state():
    # Fetch recent messages (last 50)
    msg_rows = query_db("""
        SELECT id, sender_id, message_text, channel_name, created_at 
        FROM comet_messages 
        ORDER BY created_at ASC 
        LIMIT 50
    """)
    messages = []
    for r in msg_rows:
        messages.append({
            "id": r["id"],
            "sender_id": r["sender_id"],
            "message_text": r["message_text"],
            "channel_name": r["channel_name"],
            "created_at": r["created_at"]
        })

    # Fetch active grocery items
    groc_rows = query_db("""
        SELECT id, item_name, quantity, status, compiled_at 
        FROM comet_grocery_lists 
        WHERE status != 'DELETED'
        ORDER BY compiled_at ASC
    """)
    groceries = []
    for r in groc_rows:
        groceries.append({
            "id": r["id"],
            "item_name": r["item_name"],
            "quantity": r["quantity"],
            "status": r["status"],
            "compiled_at": r["compiled_at"]
        })

    # Fetch active priority alerts, including avatar_url
    alert_rows = query_db("""
        SELECT id, alert_type, status, sys_ticket_id, avatar_url 
        FROM comet_priority_alerts 
        WHERE status = 'ACTIVE'
    """)
    alerts = []
    for r in alert_rows:
        alerts.append({
            "id": r["id"],
            "alert_type": r["alert_type"],
            "status": r["status"],
            "sys_ticket_id": r["sys_ticket_id"],
            "avatar_url": r["avatar_url"]
        })

    return {
        "type": "state",
        "messages": messages,
        "groceries": groceries,
        "alerts": alerts
    }

async def broadcast(message):
    if not clients:
        return
    payload = json.dumps(message)
    for ws in list(clients):
        try:
            await ws.send_str(payload)
        except Exception:
            clients.discard(ws)

async def create_clio_ticket(alert_type):
    payload = {
        "ticket_type": "Incident",
        "title": f"Comet Priority Alert: {alert_type}",
        "description": f"Priority assistance alert for '{alert_type}' raised from mid-century Toon Town Sputnik messenger console.",
        "status": "OPEN",
        "priority": "P1",
        "assigned_to": "Pilot",
        "affected_ci": "comet_messenger"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SDLC_PORTAL_URL, json=payload, timeout=5) as resp:
                if resp.status in (200, 201):
                    res_data = await resp.json()
                    ticket_id = res_data.get("id")
                    print(f"[CLIO TICKET CREATED] Ticket ID: {ticket_id}")
                    return ticket_id
                else:
                    print(f"[CLIO TICKET ERROR] Failed with status {resp.status}")
    except Exception as e:
        print(f"[CLIO TICKET EXCEPTION] Failed to connect to SDLC Portal: {e}")
    return None

async def resolve_clio_ticket(ticket_id):
    if not ticket_id:
        return
    payload = {
        "status": "RESOLVED",
        "work_notes": "Resolved automatically from Comet Messenger."
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{SDLC_PORTAL_URL}/{ticket_id}", json=payload, timeout=5) as resp:
                if resp.status in (200, 201):
                    print(f"[CLIO TICKET RESOLVED] Ticket ID: {ticket_id}")
                else:
                    print(f"[CLIO TICKET RESOLVE ERROR] Failed with status {resp.status}")
    except Exception as e:
        print(f"[CLIO TICKET RESOLVE EXCEPTION] Failed to resolve: {e}")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    clients.add(ws)
    print(f"[WS CLIENT CONNECTED] Total clients: {len(clients)}")
    
    try:
        # Send initial state
        state = await get_initial_state()
        await ws.send_str(json.dumps(state))

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception as e:
                    print(f"[WS JSON ERROR] {e}")
                    continue

                msg_type = data.get("type")

                if msg_type == "chat":
                    sender_id = data.get("sender_id", "Anonymous")
                    message_text = data.get("message_text", "")
                    channel_name = data.get("channel_name", "general")
                    created_at = datetime.now().isoformat()
                    
                    new_id = query_db("""
                        INSERT INTO comet_messages (sender_id, message_text, channel_name, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (sender_id, message_text, channel_name, created_at), commit=True)
                    
                    await broadcast({
                        "type": "chat",
                        "id": new_id,
                        "sender_id": sender_id,
                        "message_text": message_text,
                        "channel_name": channel_name,
                        "created_at": created_at
                    })

                    if sender_id.strip().lower() == "eileen":
                        query_db("""
                            INSERT INTO govee_active_alerts (source_sender, alert_type, status)
                            VALUES (?, 'COMET_MESSAGE', 'ACTIVE')
                        """, (sender_id,), commit=True)
                        
                        task = govee_alert_state.get("task")
                        if task is None or task.done():
                            govee_alert_state["task"] = asyncio.create_task(govee_alert_loop())

                elif msg_type == "grocery_add":
                    item_name = data.get("item_name", "")
                    quantity = data.get("quantity", "1")
                    compiled_at = datetime.now().isoformat()
                    
                    new_id = query_db("""
                        INSERT INTO comet_grocery_lists (item_name, quantity, status, compiled_at)
                        VALUES (?, ?, 'PENDING', ?)
                    """, (item_name, quantity, compiled_at), commit=True)
                    
                    await broadcast({
                        "type": "grocery_add",
                        "id": new_id,
                        "item_name": item_name,
                        "quantity": quantity,
                        "status": "PENDING",
                        "compiled_at": compiled_at
                    })

                elif msg_type == "grocery_toggle":
                    item_id = data.get("id")
                    new_status = data.get("status", "COMPLETED")
                    
                    query_db("""
                        UPDATE comet_grocery_lists
                        SET status = ?
                        WHERE id = ?
                    """, (new_status, item_id), commit=True)
                    
                    await broadcast({
                        "type": "grocery_toggle",
                        "id": item_id,
                        "status": new_status
                    })

                elif msg_type == "ACK_ALERT":
                    user_name = data.get("user_name", "Unknown")
                    print(f"[GOVEE ALERT] Alert acknowledged by {user_name}. Restoring baseline lights.")
                    
                    # Update active Govee alerts to ACKNOWLEDGED
                    query_db("""
                        UPDATE govee_active_alerts
                        SET status = 'ACKNOWLEDGED', acknowledged_at = ?
                        WHERE status = 'ACTIVE'
                    """, (datetime.now().isoformat(),), commit=True)
                    
                    # Cancel active background strobe task
                    task = govee_alert_state.get("task")
                    if task and not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    
                    # Broadcast warm-white restore command
                    restore_payload = {
                        "msg": {
                            "cmd": "colorWC",
                            "data": {
                                "color": { "r": 255, "g": 255, "b": 255 },
                                "colorTem": 3500
                            }
                        }
                    }
                    send_govee_command(restore_payload)
                    
                    # Broadcast status to other clients
                    await broadcast({
                        "type": "govee_alert_ack",
                        "status": "ACKNOWLEDGED",
                        "user_name": user_name
                    })


                elif msg_type in ("priority_alert", "TRIGGER_ALERT"):
                    alert_type = data.get("alert_type", "General")
                    avatar_url = data.get("avatar_url", "/avatars/mando/mando_warning.png")
                    
                    # Auto-generate a formal system incident index identifier (e.g. INC-COMET-0001)
                    row_count = query_db("SELECT COUNT(*) as cnt FROM comet_priority_alerts", one=True)
                    count = row_count["cnt"] if row_count else 0
                    comet_incident_id = f"INC-COMET-{count + 1:04d}"

                    # Submit incident ticket to Clio
                    ticket_id = await create_clio_ticket(alert_type)
                    combined_ticket_id = f"{comet_incident_id}|{ticket_id}" if ticket_id else comet_incident_id
                    
                    new_id = query_db("""
                        INSERT INTO comet_priority_alerts (alert_type, status, sys_ticket_id, avatar_url)
                        VALUES (?, 'ACTIVE', ?, ?)
                    """, (alert_type, combined_ticket_id, avatar_url), commit=True)
                    
                    await broadcast({
                        "type": "priority_alert",
                        "id": new_id,
                        "alert_type": alert_type,
                        "status": "ACTIVE",
                        "sys_ticket_id": combined_ticket_id,
                        "avatar_url": avatar_url
                    })

                elif msg_type in ("priority_resolve", "RESOLVE_ALERT"):
                    alert_id = data.get("id")
                    
                    # Fetch ticket ID to close it
                    row = query_db("SELECT sys_ticket_id FROM comet_priority_alerts WHERE id = ?", (alert_id,), one=True)
                    ticket_id = row["sys_ticket_id"] if row else None
                    
                    if ticket_id:
                        # Extract raw Clio ticket ID if present in combined format
                        real_ticket_id = ticket_id.split("|")[-1] if "|" in ticket_id else ticket_id
                        await resolve_clio_ticket(real_ticket_id)
                    
                    query_db("""
                        UPDATE comet_priority_alerts
                        SET status = 'RESOLVED'
                        WHERE id = ?
                    """, (alert_id,), commit=True)
                    
                    await broadcast({
                        "type": "priority_resolve",
                        "id": alert_id,
                        "status": "RESOLVED"
                    })
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[WS CLIENT DISCONNECTED WITH ERROR] {ws.exception()}")
    finally:
        clients.discard(ws)
        print(f"[WS CLIENT DISCONNECTED] Total clients: {len(clients)}")
    return ws

async def webhook_alert_handler(request):
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": f"Invalid JSON: {e}"}, status=400)
        
    alert_type = data.get("alert_type", "General")
    sys_ticket_id = data.get("sys_ticket_id")
    avatar_url = data.get("avatar_url", "/avatars/mando/mando_warning.png")
    
    # Store in DB
    new_id = query_db("""
        INSERT INTO comet_priority_alerts (alert_type, status, sys_ticket_id, avatar_url)
        VALUES (?, 'ACTIVE', ?, ?)
    """, (alert_type, sys_ticket_id, avatar_url), commit=True)
    
    # Broadcast to websocket clients
    await broadcast({
        "type": "priority_alert",
        "id": new_id,
        "alert_type": alert_type,
        "status": "ACTIVE",
        "sys_ticket_id": sys_ticket_id,
        "avatar_url": avatar_url
    })
    
    return web.json_response({"status": "dispatched", "id": new_id})

async def webhook_resolve_handler(request):
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": f"Invalid JSON: {e}"}, status=400)
        
    sys_ticket_id = data.get("sys_ticket_id")
    if not sys_ticket_id:
        return web.json_response({"error": "Missing sys_ticket_id"}, status=400)
        
    # Find matching active alerts (supports exact match or combined format suffix)
    rows = query_db("SELECT id FROM comet_priority_alerts WHERE (sys_ticket_id = ? OR sys_ticket_id LIKE '%|' || ?) AND status = 'ACTIVE'", (sys_ticket_id, sys_ticket_id))
    for row in rows:
        alert_id = row["id"]
        query_db("UPDATE comet_priority_alerts SET status = 'RESOLVED' WHERE id = ?", (alert_id,), commit=True)
        await broadcast({
            "type": "priority_resolve",
            "id": alert_id,
            "status": "RESOLVED"
        })
        
    return web.json_response({"status": "resolved"})

async def get_medical_vault_handler(request):
    try:
        rows = query_db("""
            SELECT record_id, category, document_title, provider_name, date_of_service, file_path, uploaded_by, created_at
            FROM sovereign_medical_vault
            ORDER BY date_of_service DESC
        """)
        records = []
        for r in rows:
            records.append({
                "record_id": r["record_id"],
                "category": r["category"],
                "document_title": r["document_title"],
                "provider_name": r["provider_name"],
                "date_of_service": r["date_of_service"],
                "file_path": r["file_path"],
                "uploaded_by": r["uploaded_by"],
                "created_at": r["created_at"]
            })
        return web.json_response(records)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def main():
    app = web.Application()
    app.router.add_get('/', websocket_handler)
    app.router.add_post('/webhook/alert', webhook_alert_handler)
    app.router.add_post('/webhook/resolve', webhook_resolve_handler)
    app.router.add_get('/api/medical_vault', get_medical_vault_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    print(f"📡 Starting Comet Relay Server (HTTP + WS) on Port {PORT}...")
    await site.start()
    
    # Keep running forever
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
