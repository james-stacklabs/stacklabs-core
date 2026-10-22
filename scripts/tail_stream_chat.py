import pytchat
import json
import time
import asyncio
import websockets
import sys
import os
import sqlite3
import subprocess

# Usage: python3 tail_stream_chat.py <video_id> <output_file>

DB_PATH = "/home/james/stacklabs/data/morning_wiretap.db"
INSERT_SQL = """
    INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time)
    VALUES (?, ?, ?, ?, ?, ?)
"""

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Initialize SQLite schema once and maintain persistent WAL connection."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_key TEXT NOT NULL,
            stream_id TEXT NOT NULL,
            author TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp_str TEXT NOT NULL,
            epoch_time REAL NOT NULL,
            is_spike INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn

def resolve_channel_badge(db_conn, video_id: str, cli_badge: str = "") -> str:
    if cli_badge and cli_badge != "mcafee":
        return cli_badge
    if db_conn:
        try:
            cur = db_conn.cursor()
            row = cur.execute(
                "SELECT away_team, home_team, stream_title FROM watch_party_streams WHERE stream_id = ? ORDER BY resolved_at DESC LIMIT 1",
                (video_id,)
            ).fetchone()
            if row:
                away, home, title = row[0] or "", row[1] or "", row[2] or ""
                if away and home and away != "VS":
                    return f"{away}@{home} LIVE"
                if title:
                    return title[:22].strip()
        except Exception:
            pass
    return f"LIVE:{video_id[:6]}"

async def tail_chat(video_id, output_file, cli_badge=""):
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    db_conn = None
    try:
        try:
            db_conn = init_db()
        except Exception as dbe:
            print(f"[StreamChatTail] DB initialization warning: {dbe}", flush=True)

        chat = pytchat.create(video_id=video_id)
        ws_url = "ws://127.0.0.1:8008"

        # Brief settle to let pytchat initialize
        await asyncio.sleep(2)
        if not chat.is_alive():
            print(f"[StreamChatTail] No live chat feed detected for video {video_id}. VOD or highlights clip?", flush=True)
            try:
                async with websockets.connect(ws_url) as ws:
                    await ws.send(json.dumps({
                        "type": "YOUTUBE_CHAT",
                        "user": "Sniper Bot",
                        "text": f"⚠️ No live chat feed found for video ID: {video_id}. This may be a highlights clip or a VOD without chat replay enabled. Paste a live stream or live-replay URL.",
                        "target_game_pk": "live_chat_sniper"
                    }))
                    print("[StreamChatTail] Diagnostic sent to relay.", flush=True)
            except Exception as e:
                print(f"[StreamChatTail] Could not send diagnostic: {e}", flush=True)
            return

        while chat.is_alive():
            try:
                async with websockets.connect(ws_url) as ws:
                    print(f"[StreamChatTail] Connected to {ws_url}. Tailing video {video_id}...", flush=True)
                    
                    while chat.is_alive():
                        try:
                            items = chat.get().sync_items()
                            new_rows = 0
                            for c in items:
                                author = c.author.name
                                message = c.message
                                raw_dt = getattr(c, 'datetime', '') or ''
                                t_str = raw_dt.split()[-1] if ' ' in raw_dt else (raw_dt if raw_dt else time.strftime('%H:%M:%S'))
                                
                                # 1. Append to Markdown file
                                try:
                                    with open(output_file, "a", encoding="utf-8") as f:
                                        f.write(f"\n\n[{t_str}] @@{author}\n{message}")
                                    
                                    # Periodic non-blocking ring-buffer maintenance
                                    append_counter = getattr(tail_chat, "append_counter", 0) + 1
                                    setattr(tail_chat, "append_counter", append_counter)
                                    if append_counter % 1000 == 0:
                                        if os.path.exists(output_file) and os.path.getsize(output_file) > 2 * 1024 * 1024:
                                            subprocess.Popen([
                                                "/home/james/stacklabs/.venv/bin/python3",
                                                "/home/james/stacklabs/scripts/stream_tail_rotator.py",
                                                "--tail-path", output_file,
                                                "--max-size-mb", "2.0",
                                                "--keep-lines", "5000"
                                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                except Exception as file_err:
                                    print(f"File write error: {file_err}", flush=True)
                                    
                                # 2. Send to Sovereign OS WebSocket
                                payload = {
                                    "type": "YOUTUBE_CHAT",
                                    "user": author,
                                    "text": message,
                                    "timestamp": t_str,
                                    "target_game_pk": "live_chat_sniper"
                                }
                                await ws.send(json.dumps(payload))
                                print(f"[{t_str}] Relayed: {author}: {message}", flush=True)
                                
                                # 2b. SuperChat & Moderator Ingress into Ticker Wire
                                try:
                                    is_sc = getattr(c, 'amountValue', 0) > 0 or getattr(c, 'type', '') == 'superChat'
                                    is_mod = getattr(c.author, 'isChatModerator', False) or getattr(c.author, 'isChatOwner', False)
                                    if is_sc or is_mod:
                                        c_id = getattr(c, 'id', str(int(time.time())))
                                        sc_entry = {
                                            "id": f"sc-{int(time.time())}-{c_id}",
                                            "timestamp": t_str,
                                            "type": "MCAFEE_TICKER",
                                            "subtype": "SUPERCHAT" if is_sc else "PRODUCER_PIN",
                                            "user": author,
                                            "amount": getattr(c, 'amountString', '') if is_sc else '',
                                            "text": message
                                        }
                                        ticker_file = "/home/james/stacklabs_inbox/today/mcafee_ticker_feed.jsonl"
                                        os.makedirs(os.path.dirname(ticker_file), exist_ok=True)
                                        with open(ticker_file, "a", encoding="utf-8") as tf:
                                            tf.write(json.dumps(sc_entry) + "\n")
                                        await ws.send(json.dumps(sc_entry))
                                        print(f"[{t_str}] [TICKER {sc_entry['subtype']}] {author}: {message}", flush=True)
                                except Exception as sc_err:
                                    print(f"Superchat/mod ingress err: {sc_err}", flush=True)
                                
                                # 3. Store into SQLite morning_wiretap.db (Persistent Connection & Batching)
                                if db_conn is None:
                                    try:
                                        db_conn = init_db()
                                    except Exception as dbe:
                                        print(f"DB reconnect error: {dbe}", flush=True)
                                if db_conn:
                                    try:
                                        badge = resolve_channel_badge(db_conn, video_id, cli_badge)
                                        db_conn.execute(INSERT_SQL, (badge, video_id, author, message, t_str, time.time()))
                                        new_rows += 1
                                    except Exception as dbe:
                                        print(f"DB insert error: {dbe}", flush=True)

                            if db_conn and new_rows > 0:
                                try:
                                    db_conn.commit()
                                except Exception as dbe:
                                    print(f"DB commit error: {dbe}", flush=True)
                                
                        except websockets.exceptions.ConnectionClosed:
                            print("WebSocket connection closed. Retrying in 2s...", flush=True)
                            break
                        except Exception as e:
                            print(f"Error processing chat: {e}", flush=True)
                        finally:
                            if db_conn and getattr(db_conn, "in_transaction", False):
                                try:
                                    db_conn.commit()
                                except Exception:
                                    pass
                            
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"Connection error, reconnecting in 5s: {e}", flush=True)
                await asyncio.sleep(5)
    finally:
        if db_conn:
            try:
                db_conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 tail_stream_chat.py <video_id> <output_file> [channel_key]")
        sys.exit(1)
        
    vid = sys.argv[1]
    out_file = sys.argv[2]
    cli_badge = sys.argv[3] if len(sys.argv) > 3 else ""
    
    try:
        asyncio.run(tail_chat(vid, out_file, cli_badge))
    except KeyboardInterrupt:
        print("Stopping...")
    except Exception as e:
        print(f"Exiting due to error: {e}")
