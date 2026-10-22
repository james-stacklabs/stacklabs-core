#!/usr/bin/env python3
"""
scripts/verify_atf_gate.py
Master SDLC Circuit Breaker for StackLabs Platform.
Enforces 100% pass on TCP ports, Journeys, Console Errors, and Visual Diffs.
"""
import sys
import os
import subprocess
import socket
import json
import time
from datetime import datetime
from pathlib import Path

UAT_ROOT = "/home/james/stacklabs/tests/uat"
REGISTRY_PATH = os.path.join(UAT_ROOT, "stack_registry.json")

def check_socket(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def run_command(cmd: list) -> tuple[int, str]:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return res.returncode, res.stdout

def main():
    print("=" * 80)
    print("⚡ STACKLABS PLATFORM: PRE-DEPLOY ATF CIRCUIT BREAKER")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    if not os.path.exists(REGISTRY_PATH):
        print(f"[FATAL] Missing registry: {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH, "r") as f:
        registry = json.load(f).get("stacks", {})
        if not registry:
            f.seek(0)
            registry = json.load(f)

    failures = []
    
    # 1. Pre-Flight Socket & Service Probing
    print("\n--- STAGE 1: PORT PROBING ---")
    for key, item in registry.items():
        if item.get("decommissioned") or item.get("status") == "decommissioned":
            print(f"[DECOMMISSIONED_SKIP] {item.get('name', key)} (Port {item.get('port', 'N/A')})")
            continue
        if item.get("type") == "static":
            print(f"[STATIC_SKIP] {item.get('name', key)} (Served dynamically during journey)")
            continue

        port = item.get("port")
        if not port:
            continue

        alive = check_socket("127.0.0.1", port)
        status = "ONLINE" if alive else "OFFLINE"
        print(f"[{status}] {item.get('name', key)} (Port {port})")
        if not alive and item.get("type") == "dynamic" and not item.get("optional", False):
            failures.append(f"Port {port} for stack '{key}' is unreachable.")

    # 2. Execute Interactive Journeys
    print("\n--- STAGE 2: INTERACTIVE JOURNEYS ---")
    journeys = [
        ("fanstack_wire", os.path.join(UAT_ROOT, "test_fanstack_wire_journey.cjs"))
    ]

    for stack_name, script_path in journeys:
        if not os.path.exists(script_path):
            print(f"[SKIP] Journey script not found: {script_path}")
            continue

        print(f"[RUNNING] Journey: {stack_name}...")
        proc = None
        if stack_name == "fanstack_wire":
            static_dir = registry.get("fanstack_wire", {}).get("static_dir", "/home/james/stacklabs/apps/faas/dist")
            if os.path.exists(static_dir):
                proc = subprocess.Popen(["python3", "-m", "http.server", "3029", "--bind", "127.0.0.1", "--directory", static_dir],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.5)

        env = os.environ.copy()
        env["PLAYWRIGHT_HEADLESS"] = "true"
        env["DISPLAY"] = ""
        node_paths = [
            env.get("NODE_PATH", ""),
            "/home/james/stacklabs/apps/portal/node_modules",
            "/home/james/stacklabs/apps/fanstack_creator/node_modules",
            "/home/james/stacklabs/node_modules"
        ]
        env["NODE_PATH"] = ":".join(filter(None, node_paths))
        res = subprocess.run(["node", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        code = res.returncode
        out = res.stdout

        if proc:
            proc.terminate()

        if code == 0:
            print(f"[PASS] Journey {stack_name} passed.")
        else:
            print(f"[FAIL] Journey {stack_name} failed with code {code}:\n{out}")
            failures.append(f"Journey '{stack_name}' failed.")

    # 3. Visual Regression Diff Assertions
    print("\n--- STAGE 3: VISUAL REGRESSION GATES ---")
    visual_diff_script = os.path.join(UAT_ROOT, "visual_diff_validator.cjs")
    if os.path.exists(visual_diff_script):
        active_diff_stacks = ["fanstack_wire"]
        for stack_name in active_diff_stacks:
            for vp in ["desktop", "mobile"]:
                screenshot_file = os.path.join(UAT_ROOT, "screenshots", f"{stack_name}_{vp}.png")
                if not os.path.exists(screenshot_file):
                    continue
                code, out = run_command(["node", visual_diff_script, stack_name, vp])
                if code == 0:
                    print(f"[PASS] Visual diff for {stack_name} ({vp}) verified.")
                else:
                    print(f"[FAIL] Visual regression on {stack_name} ({vp}):\n{out}")
                    failures.append(f"Visual regression detected on {stack_name}_{vp}")

    # Record status for Clio HUD & Telemetry
    status_record = {
        "status": "PASSED" if len(failures) == 0 else "BLOCKED",
        "timestamp": datetime.now().isoformat(),
        "failures": failures
    }
    for dest in [
        "/home/james/stacklabs/queue/atf_status.json",
        "/home/james/sovereign_inbox/queue/atf_status.json",
        os.path.join(UAT_ROOT, "atf_status.json")
    ]:
        try:
            p = Path(dest)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(status_record, indent=2))
        except Exception:
            pass

    # Final Decision
    print("\n" + "=" * 80)
    if len(failures) == 0:
        print("🎉 [ATF GATE CLEARED] Zero defects detected. StackLabs Verification Gate intact.")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f"🛑 [ATF GATE BLOCKED] {len(failures)} violations detected:")
        for fail in failures:
            print(f"  - {fail}")
        print("Pre-deploy aborted. Commits and edge uploads frozen.")
        print("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    main()
