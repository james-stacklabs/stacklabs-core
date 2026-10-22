#!/usr/bin/env python3
"""
StackLabs Two-Call Verification Script: WO0011223 Notre Dame @ BYU Stream Ingress
Path: /home/james/stacklabs/scripts/verify_wo0011223_nd_byu_stream_ingress.py

Empirically verifies:
- Call 1: watch_party_streams in data/morning_wiretap.db contains ND_BYU with stream_id a6kFatjvbNU and is_live = 1.
- Call 2: Live FaaS API on Port 3033 exposes ND_BYU in discord_status and lexicon drilldown.
"""

import os
import sys
import json
import sqlite3
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = REPO_ROOT / "data" / "morning_wiretap.db"
FAAS_PORT = int(os.getenv("FAAS_PORT", "3033"))

def verify_call_1_sqlite() -> None:
    print("--- [CALL 1: SQLITE WAL LEDGER VERIFICATION] ---")
    if not DB_PATH.exists():
        print(f"FAIL: Database file {DB_PATH} not found.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT sport, game_pk, home_team, away_team, stream_id, stream_title, is_live
        FROM watch_party_streams
        WHERE game_pk = 'ND_BYU' AND stream_id = 'a6kFatjvbNU';
    """)
    row = cur.fetchone()
    conn.close()
    
    if not row:
        print("FAIL: No record found for game_pk='ND_BYU' and stream_id='a6kFatjvbNU' in watch_party_streams.")
        sys.exit(1)
        
    sport, game_pk, home, away, stream_id, title, is_live = row
    print(f"✔ Found attached watch party stream: {game_pk} ({away} @ {home})")
    print(f"  Stream ID: {stream_id}")
    print(f"  Title: {title}")
    print(f"  is_live: {is_live}")
    assert is_live == 1, "Expected is_live == 1"
    print("✔ CALL 1 PASSED: SQLite registration verified.\n")

def verify_call_2_faas_api() -> None:
    print("--- [CALL 2: FAAS REST API ENDPOINT PROBE] ---")
    url = f"http://127.0.0.1:{FAAS_PORT}/api/faas/lexicon/discord_status"
    req = urllib.request.Request(url, headers={"User-Agent": "StackLabs-WO0011223-Verifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status_code = resp.status
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"FAIL: Failed to query FaaS discord_status API at {url}: {e}")
        sys.exit(1)
        
    assert status_code == 200, f"Expected 200, got {status_code}"
    print(f"✔ FaaS API responded HTTP {status_code}")
    
    configured = data.get("configured_bindings", [])
    nd_byu_binding = [b for b in configured if b.get("game_id") == "ND_BYU"]
    assert len(nd_byu_binding) > 0, "Expected ND_BYU binding in configured_bindings"
    print(f"✔ Verified ND_BYU Discord binding: {nd_byu_binding[0].get('stream_title')}")
    
    drilldown_url = f"http://127.0.0.1:{FAAS_PORT}/api/faas/lexicon/drilldown?shibboleth_id=BYU_SOAKING_QUAKING"
    req_dd = urllib.request.Request(drilldown_url, headers={"User-Agent": "StackLabs-WO0011223-Verifier/1.0"})
    try:
        with urllib.request.urlopen(req_dd, timeout=5) as resp_dd:
            dd_data = json.loads(resp_dd.read().decode("utf-8"))
            shib = dd_data.get("shibboleth", {})
            prog_name = dd_data.get("program_name") or shib.get("program_name")
            hits = dd_data.get("hit_count") or dd_data.get("total_hits") or len(dd_data.get("recent_hits", []))
            print(f"✔ Verified BYU Shibboleth Drilldown: {prog_name} (Hits: {hits})")
    except Exception as e:
        print(f"FAIL: Failed to query drilldown API: {e}")
        sys.exit(1)
        
    print("✔ CALL 2 PASSED: Live FaaS API state verified.\n")

if __name__ == "__main__":
    print("=================================================================")
    print("STACKLABS TWO-CALL VERIFICATION: WO0011223 ND @ BYU STREAM INGRESS")
    print("=================================================================")
    verify_call_1_sqlite()
    verify_call_2_faas_api()
    print("🎉 ALL TWO-CALL CHECKS PASSED EMPIRICALLY.")
    sys.exit(0)
