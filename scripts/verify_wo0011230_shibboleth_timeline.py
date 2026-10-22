#!/home/james/stacklabs/.venv/bin/python3
"""
Two-Call Verification Script for WO0011230:
Shibboleth Timeline 60s Velocity Buckets & Active Slate Resolution.
"""

import json
import subprocess
import sys
import urllib.request


def main() -> int:
    print("=" * 80)
    print("🔒 WO0011230 VERIFICATION: SHIBBOLETH TIMELINE & VELOCITY BUCKETS")
    print("=" * 80)

    # CALL 1: Direct endpoint probe for timeline and active slate
    print("\n[CALL 1] Probing active slate and lexicon timeline API endpoints...")

    # 1. Active slate
    try:
        req = urllib.request.Request("http://127.0.0.1:3033/api/faas/slate/active_games")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                print(f"[FAIL] /api/faas/slate/active_games returned status {resp.status}")
                return 1
            data = json.loads(resp.read().decode("utf-8"))
            if "live" not in data or "total_games" not in data:
                print("[FAIL] /api/faas/slate/active_games schema invalid")
                return 1
            print(f"[PASS] /api/faas/slate/active_games verified ({data['total_games']} games, {len(data['live'])} live).")
    except Exception as e:
        print(f"[FAIL] Error calling active_games endpoint: {e}")
        return 1

    # 2. Timeline endpoint
    try:
        url = "http://127.0.0.1:3033/api/faas/lexicon/timeline?shibboleth_id=BYU_SOAKING_QUAKING&window_minutes=60"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                print(f"[FAIL] /api/faas/lexicon/timeline returned status {resp.status}")
                return 1
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or "buckets" not in data:
                print(f"[FAIL] /api/faas/lexicon/timeline status not OK: {data}")
                return 1
            print(f"[PASS] /api/faas/lexicon/timeline verified (total_hits={data.get('total_hits')}, buckets={len(data.get('buckets', []))}).")
    except Exception as e:
        print(f"[FAIL] Error calling timeline endpoint: {e}")
        return 1

    # CALL 2: Read-back verification of production build and Port 3033 sidebyside view
    print("\n[CALL 2] Verifying Vite production build and sidebyside view...")
    build_res = subprocess.run(
        ["npm", "run", "build"],
        cwd="/home/james/stacklabs/apps/faas",
        capture_output=True,
        text=True,
    )
    if build_res.returncode != 0:
        print(f"[FAIL] Vite production build failed:\n{build_res.stderr}")
        return 1
    print("[PASS] apps/faas production build succeeded.")

    try:
        req = urllib.request.Request("http://127.0.0.1:3033/?view=sidebyside")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                print("[PASS] Port 3033 sidebyside view responded HTTP 200 OK.")
            else:
                print(f"[FAIL] Port 3033 returned HTTP {resp.status}")
                return 1
    except Exception as e:
        print(f"[FAIL] Port 3033 check failed: {e}")
        return 1

    print("\n" + "=" * 80)
    print("✅ WO0011230 VERIFICATION COMPLETE: ALL GATES PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
