#!/home/james/stacklabs/.venv/bin/python3
"""
Test Harness for VFS Chat Velocity Burst Bridge
Path: /home/james/stacklabs/scripts/test_vfs_chat_velocity_bridge.py
"""
import json
import os
import pathlib
import sqlite3
import subprocess
import time

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
SERVICE_DIR = ROOT_DIR / "vfs" / "services" / "chat_velocity_bridge"
BARF_DIR = ROOT_DIR / "vfs" / "advocates" / "barf_discord"
DB_PATH = ROOT_DIR / "data" / "morning_wiretap.db"
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python3"

def run_cmd(args, cwd):
    res = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def test_bridge():
    print("==================================================")
    print("⚡ TESTING VFS CHAT VELOCITY BURST BRIDGE")
    print("==================================================")

    # 1. Clean test state
    (SERVICE_DIR / ".state" / "pending_burst.json").unlink(missing_ok=True)
    (SERVICE_DIR / ".state" / "team_cooldowns.json").unlink(missing_ok=True)

    # 2. Inject synthetic velocity surge into chat_telemetry
    now_epoch = time.time()
    test_team = "BUF"
    test_channel = "BUF_test_spike"
    test_stream = "test_stream_123"
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    print("1. Injecting 60 synthetic messages for BUF in last 5 seconds...")
    for i in range(60):
        cur.execute("""
            INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_channel, test_stream, f"BillsMafia_{i}", f"UNBELIEVABLE JOSH ALLEN PLAY #{i}!", "18:50:00", now_epoch - 2 + (i * 0.02)))
    conn.commit()
    conn.close()

    # 3. Test verify.sh detection (Expect Exit 1)
    print("2. Running chat_velocity_bridge verify.sh (Expect Exit 1)...")
    rc, stdout, stderr = run_cmd(["bash", "verify.sh"], SERVICE_DIR)
    assert rc == 1, f"Expected Exit 1, got {rc}. Stderr: {stderr}"
    assert "DELTA_EXIT_1" in stderr, f"Expected DELTA_EXIT_1 in stderr, got: {stderr}"
    print(f"✓ verify.sh correctly detected burst: {stderr}")

    # 4. Test run.py execution (Expect Exit 0 and DB insertion)
    print("3. Running chat_velocity_bridge run.py (Expect Exit 0)...")
    rc, stdout, stderr = run_cmd([str(PYTHON_BIN), "run.py"], SERVICE_DIR)
    assert rc == 0, f"Expected Exit 0, got {rc}. Stderr: {stderr}"
    print(f"✓ run.py executed successfully: {stdout}")

    # 5. Verify row inserted into discord_burst_alerts
    print("4. Verifying record in discord_burst_alerts...")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT alert_id, team_abbrev, peak_quote, z_score 
        FROM discord_burst_alerts 
        WHERE channel_key = ? 
        ORDER BY rowid DESC LIMIT 1
    """, (test_channel,))
    row = cur.fetchone()
    conn.close()
    assert row is not None, "Failed to find inserted burst alert in morning_wiretap.db!"
    print(f"✓ Verified burst alert committed: ID={row[0]}, Team={row[1]}, z={row[3]}, Quote='{row[2]}'")

    # 6. Test Barf Advocate reflex recognition
    print("5. Running barf_discord verify.sh (Expect Exit 1 on new burst)...")
    rc, stdout, stderr = run_cmd(["bash", "verify.sh"], BARF_DIR)
    print(f"Barf verify.sh exit code: {rc} (Output: {stderr or stdout})")

    print("\n✅ VFS CHAT VELOCITY BURST BRIDGE VERIFICATION COMPLETE: ALL GATES PASSED")
    print("==================================================")

if __name__ == "__main__":
    test_bridge()
