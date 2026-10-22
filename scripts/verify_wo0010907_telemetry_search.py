#!/usr/bin/env python3
"""
Verification Suite for WO0010907: Broadcast & Horizon Telemetry Search Engine
Path: /home/james/stacklabs/scripts/verify_wo0010907_telemetry_search.py
"""

import os
import sys
import httpx
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.broadcast_intelligence_engine import BroadcastIntelligenceEngine


def test_search_engine():
    print("==================================================")
    print("🔬 WO0010907: TELEMETRY SEARCH ENGINE HARNESS")
    print("==================================================")

    # 1. Direct Engine Query Test (Giants)
    print("[1/3] Testing BroadcastIntelligenceEngine query on 'giants'...")
    engine = BroadcastIntelligenceEngine()
    res = engine.search("giants", "10052026")
    assert "Giants" in res["summary_title"], "Failed to extract Giants title"
    assert res["primary_timecode"] == "[12:48:10]", "Incorrect timecode mapping"
    assert len(res["chiron_hits"]) > 0, "No Chiron OCR hits found"
    print(f"      ✓ Engine returned: \"{res['summary_title']}\" at {res['primary_timecode']}")
    print(f"      ✓ Velocity: {res['chat_velocity']} | Meltdown: {res['meltdown_index']}")

    # 2. Direct Engine Query Test (Sirianni)
    print("[2/3] Testing BroadcastIntelligenceEngine query on 'sirianni'...")
    res_sirianni = engine.search("sirianni", "10052026")
    assert "Sirianni" in res_sirianni["summary_title"], "Failed to extract Sirianni title"
    assert res_sirianni["meltdown_index"] == "88% TOXIC", "Failed to match meltdown index"
    print(f"      ✓ Engine returned Sirianni dogpile reading: {res_sirianni['meltdown_index']}")

    # 3. HTTP API Endpoint Verification
    print("[3/3] Testing FaaS Server /api/broadcast/query on Port 3033...")
    r = httpx.get("http://127.0.0.1:3033/api/broadcast/query", params={"q": "giants", "date": "10052026"}, timeout=5.0)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    payload = r.json()
    assert payload["query"] == "giants", "Payload query mismatch"
    assert payload["primary_timecode"] == "[12:48:10]", "Payload timecode mismatch"
    print("      ✓ HTTP API responded 200 OK with valid JSON payload.")

    print("\n✅ TELEMETRY SEARCH VERIFICATION COMPLETED CLEANLY.")


if __name__ == "__main__":
    test_search_engine()
