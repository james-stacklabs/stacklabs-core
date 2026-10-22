#!/usr/bin/env python3
"""
verify_wo0011057_alarm_storm.py
Automated verification gate for WO0011057.
Asserts component compilation, endpoint readiness, and production build integrity.
"""
import sys
import subprocess
import requests
from pathlib import Path

WORKSPACE = Path("/home/james/stacklabs")
APP_DIR = WORKSPACE / "apps" / "cmdb_studio"

def main():
    print("==================================================")
    print("⚡ VERIFYING WO0011057 ON CLIO METAL")
    print("==================================================")

    # 1. Assert file presence
    comp = APP_DIR / "src" / "components" / "AlarmStormArenaView.tsx"
    if not comp.exists():
        print(f"❌ FAIL: {comp} missing")
        sys.exit(1)
    print("✔ AlarmStormArenaView.tsx exists")

    # 2. Test Backend API
    url = "http://127.0.0.1:3033/api/benchmark/alarm-storm"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code != 200 or "switch-core-01" not in r.text:
            print(f"❌ FAIL: API did not return expected alarm-storm payload: {r.status_code}")
            sys.exit(1)
        print("✔ /api/benchmark/alarm-storm returned verified payload")
    except Exception as e:
        print(f"❌ FAIL: API request failed: {e}")
        sys.exit(1)

    # 3. Linter check
    linter = WORKSPACE / "scripts" / "anti_metaphor_linter.py"
    if linter.exists():
        res = subprocess.run([str(WORKSPACE / ".venv" / "bin" / "python3"), str(linter), str(APP_DIR / "src")], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"❌ FAIL: Anti-metaphor linter failed:\n{res.stdout}")
            sys.exit(1)
        print("✔ Anti-metaphor linter passed with zero violations")

    # 4. Frontend production build
    res = subprocess.run(["npm", "run", "build"], cwd=str(APP_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ FAIL: npm run build failed:\n{res.stdout}\n{res.stderr}")
        sys.exit(1)
    print("✔ Frontend production bundle compiled successfully")

    print("==================================================")
    print("✅ WO0011057 VERIFIED: ALL GATES GREEN")
    print("==================================================")

if __name__ == "__main__":
    main()
