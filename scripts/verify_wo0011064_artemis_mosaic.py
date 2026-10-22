#!/usr/bin/env python3
"""
VERIFICATION SUITE: WO0011064
Build Artemis Dynamic 4-Quad Mosaic Recalibrator & HTTPS Zero-Plaintext Stream Proxy
Host: Clio (Metal Forge) & Artemis (Tailscale 100.108.185.53)
"""

import sys
import os
import re
import json
import urllib.request
import subprocess
from pathlib import Path

FAAS_SERVER_BASE = "http://127.0.0.1:3033"
THEATER_DECK_FILE = Path("/home/james/stacklabs/apps/faas/src/components/TheaterDeck.tsx")
PEGASUS_DECK_FILE = Path("/home/james/stacklabs/apps/faas/src/components/PegasusTheaterDeck.tsx")
GUIDE_FILE = Path("/dev/shm/faas_vfs/guide.json")
CONFIG_FILE = Path("/dev/shm/faas_vfs/mosaic_config.json")
FAAS_DIR = Path("/home/james/stacklabs/apps/faas")

def log(msg, success=True):
    color = "\033[92m✔" if success else "\033[91m✖"
    print(f"{color} {msg}\033[0m")

def test_stream_proxy():
    print("\n--- TEST 1: HTTPS STREAM REVERSE PROXY ---")
    url = f"{FAAS_SERVER_BASE}/api/artemis/mosaic/master_grid.m3u8"
    req = urllib.request.Request(url, headers={"User-Agent": "FaaS-Verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8", errors="ignore")
            
            assert status == 200, f"Expected status 200, got {status}"
            assert "application/vnd.apple.mpegurl" in content_type or "mpegurl" in content_type, f"Invalid Content-Type: {content_type}"
            assert "#EXTM3U" in body, "Master playlist missing #EXTM3U tag"
            assert ".ts" in body, "Master playlist has no active .ts segments"
            
            log(f"Stream proxy 200 OK: Content-Type={content_type}")
            log(f"Master playlist valid with #EXTM3U: {len(body.splitlines())} lines")

            # Extract first segment and test TS chunk proxy
            for line in body.splitlines():
                if line.endswith(".ts"):
                    seg_url = f"{FAAS_SERVER_BASE}/api/artemis/mosaic/{line.strip()}"
                    seg_req = urllib.request.Request(seg_url, headers={"User-Agent": "FaaS-Verify/1.0"})
                    with urllib.request.urlopen(seg_req, timeout=5) as seg_resp:
                        assert seg_resp.status == 200, f"Segment proxy returned {seg_resp.status}"
                        seg_type = seg_resp.headers.get("Content-Type", "")
                        assert "video/mp2t" in seg_type, f"Invalid segment Content-Type: {seg_type}"
                        chunk = seg_resp.read(1024)
                        assert len(chunk) > 0, "Empty video chunk"
                        log(f"Video chunk proxy verified: {line.strip()} -> video/mp2t (HTTP 200)")
                    break
    except Exception as e:
        log(f"Stream proxy verification failed: {e}", success=False)
        return False
    return True

def test_mosaic_recalibrate():
    print("\n--- TEST 2: DYNAMIC RECALIBRATION ENDPOINT ---")
    url = f"{FAAS_SERVER_BASE}/api/mosaic/recalibrate"
    payload = {
        "q0": "rtsp://argo_pi5:!!Stella1977@192.168.1.191:554/stream1",
        "q1": "/dev/shm/vfs/synthetic/quad_agent_radar.txt",
        "q2": "/dev/shm/vfs/synthetic/quad_cmdb_topo.txt",
        "q3": "/dev/shm/vfs/synthetic/quad_faas_matrix.txt"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200, f"Expected status 200, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "recalibrated", f"Unexpected status: {data}"
            assert data.get("stream_url") == "/api/artemis/mosaic/master_grid.m3u8", f"Unexpected stream_url: {data}"
            assert "quadrants" in data, "Missing quadrants in response"
            log(f"Recalibrate endpoint 200 OK: status={data.get('status')}")
            log(f"Stream URL returned: {data.get('stream_url')}")

            # Verify mosaic_config.json written
            assert CONFIG_FILE.exists(), f"Configuration file {CONFIG_FILE} not found"
            cfg = json.loads(CONFIG_FILE.read_text())
            assert cfg.get("q0") == payload["q0"], "q0 in config mismatch"
            log(f"Verified /dev/shm/faas_vfs/mosaic_config.json written: timestamp={cfg.get('timestamp')}")
    except Exception as e:
        log(f"Recalibrate verification failed: {e}", success=False)
        return False
    return True

def test_zero_plaintext_in_frontend():
    print("\n--- TEST 3: ZERO-PLAINTEXT AUDIT (RULE 08) ---")
    src_dir = FAAS_DIR / "src"
    banned_patterns = ["192.168.1.189", "vfs_quad.html"]
    violations = []
    
    for f in src_dir.rglob("*.tsx"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for b in banned_patterns:
            if b in text:
                violations.append(f"{f.name}: Contains banned reference '{b}'")

    if violations:
        for v in violations:
            log(v, success=False)
        return False

    log("Zero occurrences of 192.168.1.189 in apps/faas/src")
    log("Zero occurrences of vfs_quad.html in apps/faas/src")

    # Verify TheaterDeck contains new 4-dropdown selectors
    deck_text = THEATER_DECK_FILE.read_text()
    assert "showQuadControl" in deck_text, "Missing showQuadControl in TheaterDeck.tsx"
    assert "handleRecalibrate" in deck_text, "Missing handleRecalibrate in TheaterDeck.tsx"
    assert "QUAD 0" in deck_text, "Missing QUAD 0 selector in TheaterDeck.tsx"
    assert "QUAD 3" in deck_text, "Missing QUAD 3 selector in TheaterDeck.tsx"
    assert "client_grid" in deck_text, "Missing Client 2x2 Grid mode in TheaterDeck.tsx"
    log("TheaterDeck.tsx contains 4-dropdown selector and dual mode controls")
    return True

def test_channel_zero_guide():
    print("\n--- TEST 4: GUIDE CHANNEL 0 INTEGRITY ---")
    if not GUIDE_FILE.exists():
        log(f"{GUIDE_FILE} does not exist", success=False)
        return False

    guide_data = json.loads(GUIDE_FILE.read_text())
    channels = guide_data.get("channels", [])
    assert len(channels) > 0, "Guide has zero channels"
    ch0 = channels[0]
    assert ch0.get("id") in ("artemis-mosaic", "artemis-quad"), f"Unexpected Channel 0 ID: {ch0.get('id')}"
    assert ch0.get("url") == "/api/artemis/mosaic/master_grid.m3u8", f"Channel 0 URL is not proxy URL: {ch0.get('url')}"
    log(f"Channel 0 Verified: {ch0.get('label')} -> {ch0.get('url')}")
    return True

def test_frontend_build():
    print("\n--- TEST 5: PRODUCTION BUILD VALIDATION ---")
    cmd = ["npm", "run", "build"]
    res = subprocess.run(cmd, cwd=str(FAAS_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        log(f"npm run build failed:\n{res.stderr}\n{res.stdout}", success=False)
        return False
    log("npm run build passed cleanly with code 0 (TypeScript + Anti-Metaphor Linter + Vite)")
    return True

def main():
    print("=" * 70)
    print("⚡ ARTEMIS DYNAMIC MOSAIC RECALIBRATOR VERIFICATION GATE (WO0011064)")
    print("=" * 70)

    tests = [
        ("Stream Proxy", test_stream_proxy),
        ("Mosaic Recalibrate", test_mosaic_recalibrate),
        ("Zero-Plaintext Frontend Audit", test_zero_plaintext_in_frontend),
        ("Guide Channel 0 Integrity", test_channel_zero_guide),
        ("Production Build Gate", test_frontend_build)
    ]

    all_passed = True
    for name, t_fn in tests:
        if not t_fn():
            all_passed = False
            break

    print("\n" + "=" * 70)
    if all_passed:
        print("\033[92m✔ ALL GATES PASSED: WO0011064 READY FOR PILOT SIGN-OFF\033[0m")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\033[91m✖ VERIFICATION FAILED: ONE OR MORE GATES REJECTED\033[0m")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
