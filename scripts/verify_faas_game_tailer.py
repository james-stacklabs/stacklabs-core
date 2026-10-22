#!/usr/bin/env python3
"""
Verification Script for WO0010432:
FaaS Game Stream Omni-Tailer Daemon & Telemetry Verification
Path: /home/james/stacklabs/scripts/verify_faas_game_tailer.py
"""

import os
import sys
import json
import sqlite3
import subprocess
import urllib.request

def verify():
    print("=======================================================")
    print("⚡ VERIFYING WO0010432: FAAS GAME STREAM OMNI-TAILER")
    print("=======================================================")
    
    # 1. Check systemd service status
    try:
        status_out = subprocess.check_output(
            ["systemctl", "--user", "is-active", "faas_game_tailer.service"],
            text=True
        ).strip()
        print(f"✔ [SYSTEMD] faas_game_tailer.service status: {status_out}")
        assert status_out == "active", f"Expected active, got {status_out}"
    except Exception as e:
        print(f"❌ [SYSTEMD FAIL] {e}")
        sys.exit(1)

    # 2. Check stream_chat_tail.md
    tail_path = "/home/james/sovereign_inbox/today/stream_chat_tail.md"
    assert os.path.exists(tail_path), f"Missing {tail_path}"
    with open(tail_path, "r", encoding="utf-8", errors="ignore") as f:
        tail_content = f.read()
    print(f"✔ [TAIL FILE] {tail_path} exists ({len(tail_content):,} chars)")
    assert "Talkin Yanks" in tail_content or "Section 10 Pod" in tail_content, "Missing live stream chatter in tail file"
    print("✔ [TAIL CONTENT] Verified live stream chatter present from active games")

    # 3. Check SQLite database telemetry
    db_path = "/home/james/stacklabs/data/morning_wiretap.db"
    assert os.path.exists(db_path), f"Missing {db_path}"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM chat_telemetry")
    count = cur.fetchone()[0]
    cur.execute("SELECT channel_key, stream_id, author, message, timestamp_str FROM chat_telemetry ORDER BY id DESC LIMIT 3")
    recent = cur.fetchall()
    conn.close()
    print(f"✔ [DATABASE] morning_wiretap.db chat_telemetry rows: {count}")
    for r in recent:
        print(f"    - [{r[4]}] {r[0]} ({r[1]}): {r[2]}: {r[3]}")
    assert count > 0, "chat_telemetry table is empty"

    # 4. Check Port 3033 API endpoint
    api_url = "http://127.0.0.1:3033/api/stream/chat_tail"
    req = urllib.request.Request(api_url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    print(f"✔ [API] Port 3033 /api/stream/chat_tail returned {len(data)} items")
    assert len(data) > 0, "API returned empty list"
    sample = data[-1]
    print(f"    - Latest comment: {sample.get('author')}: \"{sample.get('message')}\" (sentiment: {sample.get('sentiment')})")

    # 5. Check visual twin capture
    uat_png = "/home/james/stacklabs/mockups/pegasus_uat_wo0010432_omni_tail.png"
    assert os.path.exists(uat_png), f"Missing {uat_png}"
    size = os.path.getsize(uat_png)
    print(f"✔ [PEGASUS UAT] Screenshot verified: {uat_png} ({size:,} bytes)")
    assert size > 50000, "Screenshot file is unexpectedly small"

    print("=======================================================")
    print("🎉 ALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    verify()
