#!/usr/bin/env python3
"""
Sovereign Listen: Real-Time Wiretap Tailer
Path: /home/james/stacklabs/scripts/wiretap_listen_tail.py

Streams real-time listener events from /home/james/stacklabs/logs/listen_wiretap.log.
Highlights incoming hits, playback starts, chapter selections, and duration listened.
"""

import json
import os
import sys
import time
from datetime import datetime

LOG_FILE = "/home/james/stacklabs/logs/listen_wiretap.log"

def format_event(data: dict) -> str:
    ts = data.get("timestamp", datetime.utcnow().isoformat())
    event = data.get("event", "UNKNOWN")
    source = data.get("source", "UNKNOWN")
    ip = data.get("ip", "unknown")
    country = data.get("country", "")
    ua = data.get("userAgent", "")
    device = "Desktop/Other"
    if "iPhone" in ua:
        device = "iPhone"
    elif "Android" in ua:
        device = "Android"
    elif "Macintosh" in ua:
        device = "Mac"
    elif "Windows" in ua:
        device = "Windows"

    badge = "🎧"
    if "PLAY" in event:
        badge = "🔥 [PLAY]"
    elif "PAGE" in event or "MOUNT" in event:
        badge = "👀 [PAGE VIEW]"
    elif "COMPLETED" in event:
        badge = "🏁 [COMPLETED]"
    elif "PROGRESS" in event:
        badge = "⏱️  [LISTENING]"
    elif "STREAM" in event:
        badge = "⚡ [AUDIO STREAM]"

    payload = data.get("data", {})
    track = payload.get("trackTitle") or payload.get("trackId") or data.get("url") or ""
    current_time = payload.get("currentTime")
    time_str = f" @ {current_time:.0f}s" if current_time is not None else ""

    return f"{badge} [{ts}] | IP: {ip} ({country}) | Device: {device} | Event: {event} | Target: {track}{time_str}"

def main():
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        open(LOG_FILE, 'a').close()

    print("==================================================")
    print("📡 SOVEREIGN LISTEN // REAL-TIME WIRETAP STREAM")
    print(f"Target: {LOG_FILE}")
    print("Waiting for hits from listen.stacklabsllc.com...")
    print("==================================================")

    with open(LOG_FILE, "r") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            try:
                record = json.loads(line.strip())
                print(format_event(record), flush=True)
            except Exception:
                print(f"[RAW] {line.strip()}", flush=True)

if __name__ == "__main__":
    main()
