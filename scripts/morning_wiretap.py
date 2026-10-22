#!/usr/bin/env python3
"""
THE MORNING WIRETAP: Autonomous Multi-Stream Cultural Seismograph & Chat Ingress Engine
Path: /home/james/stacklabs/scripts/morning_wiretap.py
Tool #49 // Sovereign OS FaaS Data Plane

Usage:
    python3 scripts/morning_wiretap.py --list-channels
    python3 scripts/morning_wiretap.py --channels mcafee,firsttake,squawkbox
    python3 scripts/morning_wiretap.py --all-morning --duration 120
    python3 scripts/morning_wiretap.py --video-id fa_CN7JKMCY
    python3 scripts/morning_wiretap.py --stream-url https://www.youtube.com/watch?v=fa_CN7JKMCY
    python3 scripts/morning_wiretap.py --dry-run
"""

import os
import sys
import re
import json
import time
import sqlite3
import argparse
import asyncio
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Auto-reexec with SovereignOS virtualenv if pytchat is missing in system python
try:
    import pytchat
except ImportError:
    venv_py = "/home/james/stacklabs/.venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        print("[-] Error: pytchat is not installed.", file=sys.stderr)
        sys.exit(1)

CANONICAL_CHANNELS = {
    "mcafee": {
        "name": "The Pat McAfee Show",
        "category": "sports",
        "handle": "ThePatMcAfeeShow",
        "url": "https://www.youtube.com/@ThePatMcAfeeShow/live"
    },
    "firsttake": {
        "name": "ESPN First Take",
        "category": "sports",
        "handle": "ESPN",
        "url": "https://www.youtube.com/@ESPN/live"
    },
    "squawkbox": {
        "name": "CNBC Squawk Box",
        "category": "markets",
        "handle": "CNBC",
        "url": "https://www.youtube.com/@CNBC/live"
    },
    "bloomberg": {
        "name": "Bloomberg Surveillance",
        "category": "markets",
        "handle": "BloombergPodcasts",
        "url": "https://www.youtube.com/@BloombergPodcasts/live"
    },
    "breakingpoints": {
        "name": "Breaking Points",
        "category": "politics",
        "handle": "BreakingPoints",
        "url": "https://www.youtube.com/@BreakingPoints/live"
    },
    "today": {
        "name": "NBC Today Show",
        "category": "news",
        "handle": "TODAY",
        "url": "https://www.youtube.com/@TODAY/live"
    },
    "gma": {
        "name": "Good Morning America",
        "category": "news",
        "handle": "ABCNews",
        "url": "https://www.youtube.com/@ABCNews/live"
    },
    "foxfriends": {
        "name": "Fox & Friends",
        "category": "news",
        "handle": "FoxNews",
        "url": "https://www.youtube.com/@FoxNews/live"
    },
    "morningjoe": {
        "name": "MSNBC Morning Joe",
        "category": "politics",
        "handle": "MSNBC",
        "url": "https://www.youtube.com/@MSNBC/live"
    },
    "pbd": {
        "name": "PBD Podcast",
        "category": "indie",
        "handle": "PBDPodcast",
        "url": "https://www.youtube.com/@PBDPodcast/live"
    },
    "megynkelly": {
        "name": "The Megyn Kelly Show",
        "category": "indie",
        "handle": "MegynKelly",
        "url": "https://www.youtube.com/@MegynKelly/live"
    },
    "lebatard": {
        "name": "Dan Le Batard Show",
        "category": "sports",
        "handle": "DanLeBatardShow",
        "url": "https://www.youtube.com/@DanLeBatardShow/live"
    },
    "wfan": {
        "name": "WFAN Sports Radio 660 AM / 101.9 FM",
        "category": "sports",
        "handle": "WFAN660",
        "url": "https://www.youtube.com/@WFAN660/live"
    },
    "94wip": {
        "name": "SportsRadio 94WIP Philadelphia",
        "category": "sports",
        "handle": "94WIP",
        "url": "https://www.youtube.com/@94WIP/live"
    },
    "weei": {
        "name": "WEEI 93.7 FM Boston",
        "category": "sports",
        "handle": "WEEI937",
        "url": "https://www.youtube.com/@WEEI937/live"
    },
    "670thescore": {
        "name": "670 The Score Chicago",
        "category": "sports",
        "handle": "670TheScore",
        "url": "https://www.youtube.com/@670TheScore/live"
    },
    "phly": {
        "name": "PHLY Sports",
        "category": "sports",
        "handle": "PHLY_Sports",
        "url": "https://www.youtube.com/@PHLY_Sports/live"
    },
    "chgo": {
        "name": "CHGO Sports",
        "category": "sports",
        "handle": "CHGO_Sports",
        "url": "https://www.youtube.com/@CHGO_Sports/live"
    }
}

DB_PATH = "/home/james/stacklabs/data/morning_wiretap.db"

def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()
    cursor.execute("""
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_epoch ON chat_telemetry(channel_key, epoch_time)")
    conn.commit()
    conn.close()

async def db_writer_worker(queue: asyncio.Queue, db_path: str = DB_PATH):
    """
    Dedicated single-worker SQLite writer coroutine.
    Connects to SQLite once: sqlite3.connect(db_path, timeout=60.0).
    Executes PRAGMA journal_mode=WAL; PRAGMA busy_timeout=30000;.
    Batches writes every 1.0 second or 50 items.
    """
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()

    batch: List[Tuple[str, str, str, str, str, float]] = []
    last_flush = time.time()

    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
                if item is None:  # Shutdown sentinel
                    break
                batch.append(item)
                queue.task_done()
            except asyncio.TimeoutError:
                pass

            now = time.time()
            if batch and (len(batch) >= 50 or (now - last_flush) >= 1.0):
                cursor.executemany(
                    "INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time) VALUES (?, ?, ?, ?, ?, ?)",
                    batch
                )
                conn.commit()
                batch.clear()
                last_flush = now

        # Flush any remaining items before exiting
        if batch:
            cursor.executemany(
                "INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time) VALUES (?, ?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            batch.clear()
    except asyncio.CancelledError:
        if batch:
            try:
                cursor.executemany(
                    "INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time) VALUES (?, ?, ?, ?, ?, ?)",
                    batch
                )
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        print(f"[-] DB Writer Worker encountered an error: {e}", file=sys.stderr)
    finally:
        try:
            conn.commit()
            conn.close()
        except Exception:
            pass

def resolve_live_id(channel_url: str) -> Optional[str]:
    """Resolve active YouTube live video ID using yt-dlp or url regex."""
    # Check if URL itself has an 11-char video ID
    v_match = re.search(r"(?:v=|\/live\/|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", channel_url)
    if v_match:
        return v_match.group(1)

    yt_dlp_bin = "/home/james/stacklabs/.venv/bin/yt-dlp"
    if not os.path.exists(yt_dlp_bin):
        yt_dlp_bin = shutil.which("yt-dlp") or "yt-dlp"
    try:
        proc = subprocess.run(
            [yt_dlp_bin, "--get-id", channel_url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=8
        )
        if proc.returncode == 0 and proc.stdout.strip():
            vid = proc.stdout.strip().split("\n")[0]
            if len(vid) == 11:
                return vid
    except Exception:
        pass
    return None

class StreamListener:
    def __init__(self, key: str, meta: Dict[str, Any], video_id: str, queue: asyncio.Queue):
        self.key = key
        self.meta = meta
        self.video_id = video_id
        self.queue = queue
        self.msg_count = 0
        self.active = True
        self.chat_alive = True

    async def listen(self):
        print(f"[*] Starting wiretap: {self.meta['name']} (ID: {self.video_id})")
        try:
            chat = pytchat.create(video_id=self.video_id)
        except Exception as e:
            print(f"[-] Failed to bind pytchat to {self.key} ({self.video_id}): {e}")
            self.chat_alive = False
            return

        try:
            self.chat_alive = True
            while chat.is_alive() and self.active:
                for c in chat.get().sync_items():
                    msg = c.message.strip()
                    # Filter out short noise (< 3 words) and emote-only lines
                    words = msg.split()
                    if len(words) < 3:
                        continue
                    now = time.time()
                    await self.queue.put((self.key, self.video_id, c.author.name, msg, c.datetime, now))
                    self.msg_count += 1
                    if self.msg_count % 20 == 0:
                        print(f"[{self.key.upper()}] Ingested {self.msg_count} msgs | Sample: {c.author.name}: {msg[:45]}...")
                await asyncio.sleep(0.5)
            self.chat_alive = False
            print(f"[*] Stream chat for {self.key} marked inactive (is_alive=False).")
        except Exception as e:
            self.chat_alive = False
            print(f"[-] Wiretap error on {self.key}: {e}")

def generate_morning_pulse(minutes: int = 15) -> str:
    """Generate Markdown pulse report of high-frequency topics and quotes."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    cursor = conn.cursor()
    cutoff = time.time() - (minutes * 60)
    cursor.execute("""
        SELECT channel_key, author, message, timestamp_str 
        FROM chat_telemetry 
        WHERE epoch_time >= ? 
        ORDER BY epoch_time DESC
    """, (cutoff,))
    rows = cursor.fetchall()
    conn.close()

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_dir = "/home/james/stacklabs_inbox/today"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"MORNING_WIRETAP_PULSE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

    md = [
        f"# 🎙️ THE MORNING WIRETAP // 15-MINUTE PULSE",
        f"**Generated:** {today_str} EDT | **Sample Window:** Last {minutes} minutes | **Total Messages Ingested:** {len(rows)}\n",
        f"## ⚡ Live Channel Samples\n"
    ]
    by_channel: Dict[str, List[Any]] = {}
    for r in rows:
        by_channel.setdefault(r[0], []).append(r)

    for ch_key, ch_rows in by_channel.items():
        ch_name = CANONICAL_CHANNELS.get(ch_key, {}).get("name", ch_key.upper())
        md.append(f"### {ch_name} ({len(ch_rows)} msgs)")
        for row in ch_rows[:5]:
            md.append(f"- **{row[1]}** ({row[3]}): \"{row[2]}\"")
        md.append("")

    content = "\n".join(md)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Morning pulse written to: {out_file}")
    return out_file

async def main():
    parser = argparse.ArgumentParser(description="The Morning Wiretap: Autonomous Live Stream Chat Telemetry")
    parser.add_argument("--list-channels", action="store_true", help="List pre-configured canonical channels")
    parser.add_argument("--channels", type=str, help="Comma-separated list of channel keys to tail")
    parser.add_argument("--all-morning", action="store_true", help="Tail all morning channels")
    parser.add_argument("--video-id", type=str, help="Explicit YouTube video ID to wiretap directly (e.g. fa_CN7JKMCY)")
    parser.add_argument("--stream-url", type=str, help="Explicit YouTube stream or live URL to wiretap directly")
    parser.add_argument("--dry-run", action="store_true", help="Check live status of channels without recording")
    parser.add_argument("--duration", type=int, default=60, help="Run duration in seconds (0 = run indefinitely)")
    parser.add_argument("--pulse", action="store_true", help="Generate a markdown pulse report from database")
    parser.add_argument("--auto-hard-out", action="store_true", help="Automatically trigger hourly_soft_out.py --hour 3 --hard-out when stream ends")
    args = parser.parse_args()

    if args.list_channels:
        print("\nCanonical Morning Wiretap Channels:")
        for k, v in CANONICAL_CHANNELS.items():
            print(f"  • {k.ljust(15)} : {v['name'].ljust(26)} [{v['category'].upper()}] ({v['handle']})")
        return

    init_db()

    if args.pulse:
        generate_morning_pulse()
        return

    db_queue: asyncio.Queue = asyncio.Queue()
    writer_task = None
    if not args.dry_run:
        writer_task = asyncio.create_task(db_writer_worker(db_queue, DB_PATH))

    tasks = []
    listeners = []

    if args.video_id:
        vid = args.video_id.strip()
        meta = {
            "name": f"Direct Video Stream ({vid})",
            "category": "custom",
            "handle": vid,
            "url": f"https://www.youtube.com/watch?v={vid}"
        }
        print(f"[+] Direct Video ID target: https://www.youtube.com/watch?v={vid}")
        if not args.dry_run:
            l = StreamListener("custom", meta, vid, db_queue)
            listeners.append(l)
            tasks.append(asyncio.create_task(l.listen()))
    elif args.stream_url:
        target_url = args.stream_url.strip()
        print(f"[*] Resolving direct stream URL: {target_url}...")
        vid = resolve_live_id(target_url)
        if vid:
            meta = {
                "name": f"Direct URL Stream ({vid})",
                "category": "custom",
                "handle": vid,
                "url": target_url
            }
            print(f"[+] Resolved live stream ID {vid} from {target_url}")
            if not args.dry_run:
                l = StreamListener("custom", meta, vid, db_queue)
                listeners.append(l)
                tasks.append(asyncio.create_task(l.listen()))
        else:
            print(f"[-] Failed to resolve live video ID from URL: {target_url}")
            if writer_task:
                await db_queue.put(None)
                await writer_task
            return
    else:
        target_keys = []
        if args.all_morning:
            target_keys = list(CANONICAL_CHANNELS.keys())
        elif args.channels:
            target_keys = [k.strip().lower() for k in args.channels.split(",") if k.strip().lower() in CANONICAL_CHANNELS]
        else:
            # Morning wiretap active stream defaults: mcafee, squawkbox, bloomberg, gma, foxfriends
            target_keys = ["mcafee", "squawkbox", "bloomberg", "gma", "foxfriends"]

        print(f"[*] Resolving live streams for targets: {', '.join(target_keys)}...")
        for k in target_keys:
            meta = CANONICAL_CHANNELS[k]
            vid = resolve_live_id(meta["url"])
            if vid:
                print(f"[+] Found LIVE stream for {meta['name']}: https://www.youtube.com/watch?v={vid}")
                if not args.dry_run:
                    l = StreamListener(k, meta, vid, db_queue)
                    listeners.append(l)
                    tasks.append(asyncio.create_task(l.listen()))
            else:
                print(f"[-] {meta['name']} is currently OFFLINE / no live broadcast found.")

    if args.dry_run:
        print("[*] Dry run complete.")
        return

    if not tasks:
        print("[-] No active live streams found right now.")
        if writer_task:
            await db_queue.put(None)
            await writer_task
        return

    try:
        if args.duration > 0:
            print(f"[*] Running multi-wiretap for up to {args.duration}s with async stream-end monitoring...")
            elapsed = 0
            while elapsed < args.duration:
                await asyncio.sleep(5.0)
                elapsed += 5
                # If listeners were spawned and ALL have terminated (chat not alive), exit early
                if listeners and all(not l.active or not getattr(l, 'chat_alive', True) for l in listeners):
                    now_hour = datetime.now().hour
                    now_minute = datetime.now().minute
                    # If past 1:15 PM EDT, this is a legitimate broadcast conclusion
                    if now_hour > 13 or (now_hour == 13 and now_minute >= 15):
                        print(f"[!] All live stream listeners terminated after {now_hour:02d}:{now_minute:02d} EDT. Ending wiretap early.")
                        break
        else:
            print("[*] Running multi-wiretap indefinitely (press Ctrl+C to stop)...")
            while True:
                await asyncio.sleep(1.0)
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[*] Stopping wiretap listeners...")
    finally:
        for l in listeners:
            l.active = False
        await asyncio.gather(*tasks, return_exceptions=True)
        if writer_task:
            await db_queue.put(None)
            await writer_task
        generate_morning_pulse()

        if getattr(args, 'auto_hard_out', False) or (args.channels and 'mcafee' in args.channels.lower()):
            now_hour = datetime.now().hour
            # Trigger hard-out if after 1:30 PM EDT
            if now_hour >= 13:
                print("[*] Dispatching Tool #50 hourly_soft_out.py --hour 3 --hard-out in background...")
                subprocess.Popen(
                    ["/home/james/stacklabs/.venv/bin/python3", "/home/james/stacklabs/scripts/hourly_soft_out.py", "--hour", "3", "--hard-out"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
