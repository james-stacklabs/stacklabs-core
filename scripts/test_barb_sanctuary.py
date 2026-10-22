#!/home/james/stacklabs/.venv/bin/python3
"""
Test Suite for Barb's Sanctuary & Dot's Sass Vault (WO0010916)
Path: /home/james/stacklabs/scripts/test_barb_sanctuary.py
Author: James Carroll (Lead Systems Architect, StackLabs LLC)
Governed by: Invariant 1 (Small Ball Metal), Invariant 15 (Two-Call Verification), Invariant 35 (Canonical .venv)
"""

import sys
import os
import io
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "services" / "barb_sanctuary"))

import dot_brain
import server

def main():
    print("=" * 70)
    print("🧪 RUNNING BARB SANCTUARY & SASSY BRIT VOICE TEST SUITE (WO0010916)")
    print("=" * 70)

    # Test 1: Dot Brain Text Vent
    print("\n[TEST 1] Dot Brain Voice Vent Processing...")
    test_vent = "Sarah bypassed seniority again and gave Jamande the catering run after I said no to her questions."
    res = dot_brain.process_vent_text(test_vent)
    assert "dot_sass" in res, "Missing dot_sass"
    assert "receipt_card" in res, "Missing receipt_card"
    print("✅ PASS: Dot Brain returned valid text & structured receipts.")

    # Test 2: Sassy Brit Audio Synthesis (en-GB-SoniaNeural)
    print("\n[TEST 2] Neural Audio Synthesis (en-GB-SoniaNeural via Edge-TTS)...")
    t0 = time.time()
    audio_url = dot_brain.synthesize_voice(res["dot_sass"][:120], 99999)
    dt = time.time() - t0
    assert audio_url is not None, "Audio URL is None"
    expected_file = REPO_ROOT / "services" / "barb_sanctuary" / "static" / "audio" / "dot_response_99999.mp3"
    assert expected_file.exists(), f"MP3 file not found: {expected_file}"
    print(f"✅ PASS: Generated {expected_file.name} in {dt:.2f}s ({expected_file.stat().st_size} bytes).")
    if expected_file.exists():
        expected_file.unlink()  # Clean up test artifact

    # Test 3: Whisper Model Liveness on Clio
    print("\n[TEST 3] Whisper tiny.en Model Verification on Clio Metal...")
    assert server.WHISPER_MODEL is not None, "Whisper model not initialized"
    print("✅ PASS: Local Whisper model loaded and ready on Clio.")

    # Test 4: SQLite Database WAL Persistence
    print("\n[TEST 4] Database Persistence in SQLite WAL...")
    with server.get_db_connection() as conn:
        conn.execute("""
            INSERT INTO barb_receipts (
                raw_vent, dot_sass, actors, infraction, estimated_loss, bulletproof_script, audio_url, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ("Test vent", "Test sass", "[]", "Test infraction", "$50", "Test script", "/static/audio/test.mp3", "2026-10-06T15:55:00Z"))
        conn.commit()
        cur = conn.execute("SELECT * FROM barb_receipts WHERE raw_vent = 'Test vent';")
        row = cur.fetchone()
        assert row is not None, "Failed to retrieve test record"
        assert row["audio_url"] == "/static/audio/test.mp3", "audio_url column missing or incorrect"
        conn.execute("DELETE FROM barb_receipts WHERE raw_vent = 'Test vent';")
        conn.commit()
    print("✅ PASS: SQLite WAL persistence with audio_url verified.")

    print("\n" + "=" * 70)
    print("🏆 ALL 4 TEST GATES PASSED (4/4 PASS) — READY FOR DEPLOYMENT")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
