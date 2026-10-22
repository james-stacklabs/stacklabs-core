#!/usr/bin/env python3
"""Deterministic remediation for WO0011147."""
import os
import re
import signal
import sqlite3
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/james/stacklabs")
DB_PATH = ROOT / "data/morning_wiretap.db"

my_pids = {str(os.getpid()), str(os.getppid())}

def kill_matching(pattern: str):
    res = subprocess.run(["pgrep", "-f", pattern], stdout=subprocess.PIPE, text=True)
    for line in res.stdout.strip().splitlines():
        pid = line.strip()
        if pid and pid not in my_pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

# 1. Kill stale stream_sniper_daemon.py and xyYgJ0vTd2g tail_stream_chat.py
kill_matching("scripts/stream_sniper_daemon.py")
kill_matching("scripts/tail_stream_chat.py")
time.sleep(0.4)

# 2. Clean morning_wiretap.db badges & remove Knicks/Spurs noise
if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000;")
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_telemetry WHERE lower(message) LIKE '%knicks%' OR lower(message) LIKE '%spurs%'")
    cur.execute("UPDATE chat_telemetry SET channel_key = 'MIL@LAD • Play-by-Play' WHERE stream_id = 'P1QZve1reP8'")
    cur.execute("UPDATE chat_telemetry SET channel_key = 'MIL@LAD • NW Sports' WHERE stream_id = 'Gh363QK6kOQ'")
    cur.execute("UPDATE chat_telemetry SET channel_key = 'MIL@LAD • MaxCoverage' WHERE stream_id = 'Lf36gSxvH4U'")
    cur.execute("UPDATE chat_telemetry SET channel_key = 'MIL@LAD • C-LO Live' WHERE stream_id = 'l3yTD4YykUk'")
    cur.execute("""
        UPDATE chat_telemetry
        SET channel_key = 'MIL@LAD LIVE'
        WHERE channel_key = 'mcafee'
          AND stream_id IN (SELECT stream_id FROM watch_party_streams WHERE game_pk = '849811')
    """)
    conn.commit()
    conn.close()

# 3. Restart stream_sniper_daemon.py and tail_stream_chat.py cleanly
log_dir = ROOT / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
with open(log_dir / "stream_sniper_daemon.log", "a") as lf:
    subprocess.Popen(
        ["/home/james/stacklabs/.venv/bin/python3", str(ROOT / "scripts/stream_sniper_daemon.py")],
        stdout=lf,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )

subprocess.Popen(
    [
        "/home/james/stacklabs/.venv/bin/python3",
        str(ROOT / "scripts/tail_stream_chat.py"),
        "P1QZve1reP8",
        str(ROOT / "data/stream_chat_tail.md"),
        "MIL@LAD • Play-by-Play",
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
    close_fds=True,
)

# 4. Scrub dna/notebook_lm_exports/ for Section 3.1 trade-secret terms
export_dir = ROOT / "dna/notebook_lm_exports"
if export_dir.exists():
    replacements = [
        (re.compile(r"/dev/shm", re.I), "in-memory state plane"),
        (re.compile(r"\btmpfs\b", re.I), "in-memory state plane"),
        (re.compile(r"\bsymlink(s|ed|ing)?\b", re.I), "directed pointer"),
        (re.compile(r"\binode(s)?\b", re.I), "state register"),
        (re.compile(r"\bst_ino\b", re.I), "state_register_id"),
        (re.compile(r"\breadlink\b", re.I), "pointer resolution"),
    ]
    for fpath in export_dir.glob("SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE*"):
        if fpath.is_file():
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            for pat, rep in replacements:
                content = pat.sub(rep, content)
            fpath.write_text(content, encoding="utf-8")

print("WO0011147_PATCH_COMPLETE")
