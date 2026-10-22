#!/home/james/stacklabs/.venv/bin/python3
"""
Verification Script for WO0011278: React Sniper Radar Morning AM & Engine Telemetry HUD.
Fulfills Invariant 15 (Two-Call Mandate).
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
PORT = int(os.getenv("PORT", 3033))
BASE_URL = f"http://127.0.0.1:{PORT}"

def test_endpoint(url: str):
    print(f"[*] Testing {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "StackLabs-Verification/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        status_code = resp.getcode()
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()
        print(f"    -> Status: {status_code}, Type: {content_type}, Bytes: {len(data)}")
        assert status_code == 200, f"Expected 200, got {status_code}"
        return data, content_type

def main():
    print("=================================================================")
    print("WO0011278 VERIFICATION: REACT SNIPER RADAR & ENGINE TELEMETRY HUD")
    print(f"Target: {BASE_URL}")
    print("=================================================================\n")

    # Call 1: Check stream_subscriptions.json has >= 18 channels including Morning AM
    print("[1/5] CALL 1: Validating stream_subscriptions.json...")
    subs_path = REPO_ROOT / "ground_truth" / "cmdb" / "stream_subscriptions.json"
    assert subs_path.exists(), "stream_subscriptions.json missing"
    subs = json.loads(subs_path.read_text(encoding="utf-8"))
    channel_ids = [s.get("channel_id") for s in subs]
    assert len(subs) >= 18, f"Expected >= 18 subscriptions, found {len(subs)}"
    assert "UCAIZ314ffmfM4PynCR8vElw" in channel_ids, "Dan Le Batard channel ID missing"
    assert "UCiWLfSweyRNmLpgEHekhoAg" in channel_ids, "ESPN First Take channel ID missing"
    assert "UCvJJ_dzjViJCoLf5uKUTwoA" in channel_ids, "CNBC Squawk Box channel ID missing"
    print(f"    -> Verified {len(subs)} channels including Morning AM wiretaps.")

    # Call 2: Test /api/snipe/radar
    print("\n[2/5] CALL 2: Checking /api/snipe/radar...")
    r_bytes, _ = test_endpoint(f"{BASE_URL}/api/snipe/radar")
    r_data = json.loads(r_bytes.decode("utf-8"))
    assert r_data.get("status") == "success", "Radar status must be success"
    drops = r_data.get("radar_drops", [])
    print(f"    -> Successfully polled {len(drops)} channels in parallel.")
    assert len(drops) >= 10, f"Expected >= 10 drops returned, got {len(drops)}"

    # Call 3: Test /api/snipe/engine_telemetry
    print("\n[3/5] CALL 3: Checking /api/snipe/engine_telemetry...")
    t_bytes, _ = test_endpoint(f"{BASE_URL}/api/snipe/engine_telemetry")
    t_data = json.loads(t_bytes.decode("utf-8"))
    assert t_data.get("status") == "online", "Telemetry status must be online"
    assert t_data.get("gemini_model") == "gemini-3.8-flash", "Model must be gemini-3.8-flash"
    assert "queue" in t_data, "Queue telemetry missing"
    assert "morning_wiretap" in t_data, "Morning wiretap telemetry missing"
    print(f"    -> Verified Engine Telemetry: Queue={t_data['queue']}, Wiretap={t_data['morning_wiretap']['chat_messages']} msgs.")

    # Call 4: Verify StreamRadarDeck.tsx exists and is non-empty
    print("\n[4/5] CALL 4: Checking StreamRadarDeck.tsx...")
    comp_path = REPO_ROOT / "apps" / "faas" / "src" / "components" / "StreamRadarDeck.tsx"
    assert comp_path.exists(), "StreamRadarDeck.tsx missing"
    assert "Behind the Scenes // Engine Telemetry" in comp_path.read_text(encoding="utf-8")
    print("    -> StreamRadarDeck.tsx verified on disk.")

    # Call 5: Verify compiled Vite bundle in apps/faas/dist/
    print("\n[5/5] CALL 5: Checking compiled bundle...")
    dist_html = REPO_ROOT / "apps" / "faas" / "dist" / "index.html"
    assert dist_html.exists(), "apps/faas/dist/index.html missing"
    print("    -> Production Vite bundle verified.")

    print("\n=================================================================")
    print("✔ ALL CHECKS PASSED: WO0011278 VERIFICATION COMPLETE (HTTP 200 OK)")
    print("=================================================================")

if __name__ == "__main__":
    main()
