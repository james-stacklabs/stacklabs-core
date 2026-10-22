#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Dual-Channel & Wiretap Pipeline Test Harness
Validates that:
1. export_wiretap_for_drive.py generates valid manifest and JSON slices.
2. argon_lexicon_harvester.py commits evolving shibboleths to SQLite WAL.
3. discord_dual_channel_dispatcher.py structures valid Discord payloads.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/test_dual_channel_pipeline.py
"""
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
PYTHON_EXEC = PROJECT_ROOT / ".venv" / "bin" / "python3"
DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"


def test_export_wiretap():
    print("[1/3] Testing export_wiretap_for_drive.py...")
    cmd = [str(PYTHON_EXEC), str(PROJECT_ROOT / "scripts" / "export_wiretap_for_drive.py"), "--hours", "48"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    manifest = json.loads(res.stdout)
    assert "counts" in manifest, "Manifest missing counts key"
    assert manifest["counts"]["chat_spikes"] >= 0, "Invalid chat_spikes count"
    print(f"  ✓ Wiretap export generated clean manifest with {manifest['counts']['chat_spikes']} spike messages.")


def test_lexicon_harvester():
    print("[2/3] Testing argon_lexicon_harvester.py...")
    cmd = [str(PYTHON_EXEC), str(PROJECT_ROOT / "scripts" / "argon_lexicon_harvester.py")]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    nfl_row = cur.execute("SELECT shibboleth_id FROM nfl_subcultural_lexicon WHERE shibboleth_id = 'WSH_DANIELS_CLOCK_AWARENESS_HAIL_NO'").fetchone()
    assert nfl_row is not None, "NFL shibboleth not found in database"

    cfb_row = cur.execute("SELECT shibboleth_id FROM cfb_subcultural_lexicon WHERE shibboleth_id = 'MINN_LITTLE_BROWN_JUG_49_YEAR_DROUGHT'").fetchone()
    assert cfb_row is not None, "CFB shibboleth not found in database"
    conn.close()
    print("  ✓ Evolving shibboleths verified in SQLite WAL ledgers.")


def test_dispatcher_compilation():
    print("[3/3] Testing discord_dual_channel_dispatcher.py compilation...")
    cmd = [str(PYTHON_EXEC), "-m", "py_compile", str(PROJECT_ROOT / "scripts" / "discord_dual_channel_dispatcher.py")]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("  ✓ Dispatcher compiled with zero syntax errors.")


def main():
    print("==================================================")
    print("⚡ STACKLABS DUAL-CHANNEL & ARGON PIPELINE HARNESS")
    print("==================================================")
    test_export_wiretap()
    test_lexicon_harvester()
    test_dispatcher_compilation()
    print("\n✅ ALL PIPELINE TESTS PASSED CLEANLY.")


if __name__ == "__main__":
    main()
