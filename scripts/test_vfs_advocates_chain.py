#!/home/james/stacklabs/.venv/bin/python3
"""
Test Harness for VFS Advocates Reactive Stigmergic Chain
Path: /home/james/stacklabs/scripts/test_vfs_advocates_chain.py

Tests the sequential reflex loop:
1. Simulates/verifies burst alert in morning_wiretap.db
2. Triggers Barf's verify.sh (Exit 1) and executes run.py
3. Verifies Burl's porch delay (Exit 0 when fresh, Exit 1 when aged >=45s) and executes run.py
4. Verifies Sammy's diner delay (Exit 0 when fresh, Exit 1 when aged >=30s) and executes run.py
5. Validates final steady state (all Exit 0)
"""

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import time

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
VFS_ADVOCATES = ROOT_DIR / "vfs" / "advocates"
BARF_DIR = VFS_ADVOCATES / "barf_discord"
BURL_DIR = VFS_ADVOCATES / "burl_discord"
SAMMY_DIR = VFS_ADVOCATES / "sammy_savant"
DB_PATH = ROOT_DIR / "data" / "morning_wiretap.db"

def run_cmd(cmd: list, cwd: pathlib.Path) -> tuple[int, str, str]:
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def main() -> int:
    print("🧪 [TEST HARNESS] Starting VFS Advocates Reactive Chain Test...")

    # 1. Verify directory layout and symlinks
    for adv_dir in (BARF_DIR, BURL_DIR, SAMMY_DIR):
        if not adv_dir.exists():
            print(f"❌ Missing advocate directory: {adv_dir}")
            return 1

    # 2. Seed test burst if none exist
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT rowid, team_abbrev, peak_quote FROM discord_burst_alerts ORDER BY rowid DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO discord_burst_alerts (
                alert_id, channel_key, stream_id, channel_id, shibboleth_id,
                team_abbrev, ngram_or_token, hit_count, window_messages, window_seconds,
                velocity_mps, z_score, z_score_threshold, peak_author, peak_quote,
                timestamp_str, epoch_time, content_sha256
            ) VALUES (
                'test_alert_99', 'BUF_LV', 'test_stream_id', '123456789', 'shibb_1',
                'LV', 'touchdown', 25, 50, 10.0,
                5.0, 5.2, 4.5, 'RaiderFan1', 'Raiders punch it in to tie the game at 10!',
                '17:40:00', strftime('%s','now'), 'hash99'
            )
        """)
        conn.commit()
        print("✓ Seeded test burst in discord_burst_alerts")
    conn.close()

    # Clear previous state files for clean test run
    for d in (BARF_DIR, BURL_DIR, SAMMY_DIR):
        state_dir = d / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        for f in state_dir.glob("*.json"):
            f.unlink()

    # Step A: Barf verify.sh (Expect Exit 1: Unbarked burst)
    code, out, err = run_cmd(["bash", "verify.sh"], BARF_DIR)
    print(f"Step A [Barf Verify]: exit_code={code} (err={err})")
    if code != 1:
        print("❌ Barf verify.sh failed to trigger on unbarked burst!")
        return 1

    # Step B: Barf run.py (Generate bark & drop last_bark.json)
    code, out, err = run_cmd(["/home/james/stacklabs/.venv/bin/python3", "run.py"], BARF_DIR)
    print(f"Step B [Barf Run]: exit_code={code} ({out})")
    last_bark = BARF_DIR / ".state" / "last_bark.json"
    if not last_bark.exists():
        print("❌ Barf failed to write last_bark.json!")
        return 1

    # Step C: Burl verify.sh immediately (Expect Exit 0: Porch delay active, < 45s)
    code, out, err = run_cmd(["bash", "verify.sh"], BURL_DIR)
    print(f"Step C [Burl Porch Delay Gate]: exit_code={code} (expected 0: porch delay active)")
    if code != 0:
        print("❌ Burl failed to observe porch delay gate!")
        return 1

    # Fast-forward last_bark.json timestamp by -50s to simulate 45s porch delay passing
    past_mtime = time.time() - 50
    os.utime(last_bark, (past_mtime, past_mtime))

    # Step D: Burl verify.sh after porch delay (Expect Exit 1: Time to counter Barf)
    code, out, err = run_cmd(["bash", "verify.sh"], BURL_DIR)
    print(f"Step D [Burl Porch Trip]: exit_code={code} (err={err})")
    if code != 1:
        print("❌ Burl verify.sh failed to trip after porch delay!")
        return 1

    # Step E: Burl run.py (Generate drawl & drop last_drawl.json)
    code, out, err = run_cmd(["/home/james/stacklabs/.venv/bin/python3", "run.py"], BURL_DIR)
    print(f"Step E [Burl Run]: exit_code={code} ({out})")
    last_drawl = BURL_DIR / ".state" / "last_drawl.json"
    if not last_drawl.exists():
        print("❌ Burl failed to write last_drawl.json!")
        return 1

    # Step F: Sammy verify.sh immediately (Expect Exit 0: Diner delay active, < 30s)
    code, out, err = run_cmd(["bash", "verify.sh"], SAMMY_DIR)
    print(f"Step F [Sammy Diner Delay Gate]: exit_code={code} (expected 0: diner delay active)")
    if code != 0:
        print("❌ Sammy failed to observe diner delay gate!")
        return 1

    # Fast-forward last_drawl.json timestamp by -35s to simulate 30s diner delay passing
    past_drawl_mtime = time.time() - 35
    os.utime(last_drawl, (past_drawl_mtime, past_drawl_mtime))

    # Step G: Sammy verify.sh after diner delay (Expect Exit 1: Time to grade total)
    code, out, err = run_cmd(["bash", "verify.sh"], SAMMY_DIR)
    print(f"Step G [Sammy Diner Trip]: exit_code={code} (err={err})")
    if code != 1:
        print("❌ Sammy verify.sh failed to trip after diner delay!")
        return 1

    # Step H: Sammy run.py (Grade total & drop last_ticket.json)
    code, out, err = run_cmd(["/home/james/stacklabs/.venv/bin/python3", "run.py"], SAMMY_DIR)
    print(f"Step H [Sammy Run]: exit_code={code} ({out})")
    last_ticket = SAMMY_DIR / ".state" / "last_ticket.json"
    if not last_ticket.exists():
        print("❌ Sammy failed to write last_ticket.json!")
        return 1

    # Step I: Steady state verification (All exit 0)
    for name, path in [("Barf", BARF_DIR), ("Burl", BURL_DIR), ("Sammy", SAMMY_DIR)]:
        c, _, _ = run_cmd(["bash", "verify.sh"], path)
        print(f"Step I [{name} Steady State]: exit_code={c} (expected 0)")
        if c != 0:
            print(f"❌ {name} verify.sh failed to return to steady state!")
            return 1

    print("✅ [TEST HARNESS] 100% SUCCESS: Entire Barf -> Burl -> Sammy VFS reaction chain verified!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
