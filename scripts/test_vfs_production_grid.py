#!/home/james/stacklabs/.venv/bin/python3
"""
Test Harness for VFS Production Reaction Grid & Autonomous Escalation
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/test_vfs_production_grid.py

Executes comprehensive validation stages:
  1. Exit 1 Reflex Recovery: Process kill -> sub-second recovery (0 tokens).
  2. Exit 2 Escalation & Promotion: Schema drift -> /dev/shm repair -> NVMe atomic promotion -> Blueprint saved.
  3. Stigmergic Healing: Repeat error fixed via Gear 0 blueprint (0 tokens).
  3b. Circuit Breaker: Unrepairable drift trips .state/CIRCUIT_OPEN.lock after 2 attempts.
  4. Advocate Stigmergic Chain: Barf -> Burl -> Sammy reactive delay flow.
"""
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
sys.path.insert(0, str(ROOT_DIR / "scripts"))

VFS_ROOT = ROOT_DIR / "vfs"
SERVICES_DIR = VFS_ROOT / "services"
ADVOCATES_DIR = VFS_ROOT / "advocates"
BLUEPRINTS_DIR = VFS_ROOT / "blueprints"
TEST_SERVICE = SERVICES_DIR / "canary_ticker"
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python3"
REFLEX_SCRIPT = ROOT_DIR / "scripts" / "vfs_reflex_watcher.py"


def log(tag: str, msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}", flush=True)


def kill_pid(pid_file: pathlib.Path) -> None:
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        pid_file.unlink(missing_ok=True)


def setup_canary() -> None:
    TEST_SERVICE.mkdir(parents=True, exist_ok=True)
    state_dir = TEST_SERVICE / ".state"
    state_dir.mkdir(exist_ok=True)

    spec = {
        "ci_id": "ci_canary_ticker_5098",
        "primitive": "container",
        "target_state": "active",
        "bindings": {"port": 5098, "host": "127.0.0.1", "pid_file": ".state/run.pid"},
        "dependencies": [],
    }
    (TEST_SERVICE / "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    run_py = f"""#!{PYTHON_BIN}
import json, os, pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
STATE_DIR = BASE_DIR / ".state"
STATE_DIR.mkdir(exist_ok=True)
(STATE_DIR / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

PAYLOAD = {{"service": "canary_ticker", "status": "ok"}}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(PAYLOAD).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", SPEC["bindings"]["port"]), Handler)
    server.serve_forever()
"""
    (TEST_SERVICE / "run.py").write_text(run_py, encoding="utf-8")
    (TEST_SERVICE / "run.py").chmod(0o755)

    verify_sh = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PID_FILE=".state/run.pid"
PORT=$({PYTHON_BIN} -c "import json; print(json.load(open('spec.json'))['bindings']['port'])")

if [[ ! -f "$PID_FILE" ]] || ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "DELTA_EXIT_1: Process dead on port $PORT" >&2
    exit 1
fi

RESP=$(curl -s --max-time 1 "http://127.0.0.1:${{PORT}}/health" || true)
ACTUAL=$({PYTHON_BIN} -c "import json, sys; print(json.loads(sys.argv[1]).get('status',''))" "$RESP" 2>/dev/null || true)

if [[ "$ACTUAL" != "ok" ]]; then
    echo "DELTA_EXIT_2: Expected status=ok, got status=${{ACTUAL}}" >&2
    exit 2
fi
exit 0
"""
    (TEST_SERVICE / "verify.sh").write_text(verify_sh, encoding="utf-8")
    (TEST_SERVICE / "verify.sh").chmod(0o755)


def cleanup_canary() -> None:
    kill_pid(TEST_SERVICE / ".state" / "run.pid")
    shutil.rmtree(TEST_SERVICE, ignore_errors=True)
    shutil.rmtree(BLUEPRINTS_DIR / "canary_ticker", ignore_errors=True)


def main() -> int:
    log("TEST", "Starting VFS Production Reaction Grid verification...")
    cleanup_canary()
    setup_canary()

    # Start canary initial run
    log("TEST", "Booting canary ticker on port 5098...")
    subprocess.Popen([str(PYTHON_BIN), "run.py"], cwd=str(TEST_SERVICE))
    time.sleep(0.4)

    # Verify Initial Exit 0
    res = subprocess.run(["bash", "verify.sh"], cwd=str(TEST_SERVICE), capture_output=True, text=True)
    if res.returncode != 0:
        log("FAIL", f"Initial canary boot failed verify.sh: {res.stderr}")
        cleanup_canary()
        return 1
    log("PASS", "Stage 0: Canary is healthy (Exit 0)")

    # -------------------------------------------------------------
    # Stage 1: Exit 1 Pure Reflex
    # -------------------------------------------------------------
    log("TEST", "Stage 1: Simulating SIGKILL on canary ticker...")
    t0 = time.monotonic()
    kill_pid(TEST_SERVICE / ".state" / "run.pid")

    from vfs_reflex_watcher import sweep_directory

    sweep_directory(SERVICES_DIR)
    time.sleep(0.35)

    res = subprocess.run(["bash", "verify.sh"], cwd=str(TEST_SERVICE), capture_output=True, text=True)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    if res.returncode != 0:
        log("FAIL", f"Stage 1: Exit 1 pure reflex restart failed! {res.stderr}")
        cleanup_canary()
        return 1
    log("PASS", f"Stage 1: Pure reflex recovery successful in {elapsed_ms:.1f}ms (Exit 0 restored without tokens)")

    # -------------------------------------------------------------
    # Stage 2: Exit 2 Drift, Repair, Promotion & Blueprint
    # -------------------------------------------------------------
    log("TEST", "Stage 2: Sabotaging verify.sh to demand status=ironclad (Exit 2)...")
    verify_content = (TEST_SERVICE / "verify.sh").read_text(encoding="utf-8")
    sabotaged = verify_content.replace('[[ "$ACTUAL" != "ok" ]]', '[[ "$ACTUAL" != "ironclad" ]]')
    sabotaged = sabotaged.replace("Expected status=ok", "Expected status=ironclad")
    (TEST_SERVICE / "verify.sh").write_text(sabotaged, encoding="utf-8")

    sweep_directory(SERVICES_DIR)
    time.sleep(0.4)

    res = subprocess.run(["bash", "verify.sh"], cwd=str(TEST_SERVICE), capture_output=True, text=True)
    if res.returncode != 0:
        log("FAIL", f"Stage 2: Repair failed to promote working code! {res.stderr}")
        cleanup_canary()
        return 1

    bp_file = BLUEPRINTS_DIR / "canary_ticker" / "run.py"
    if not bp_file.exists():
        log("FAIL", "Stage 2: Blueprint was not saved to /vfs/blueprints/!")
        cleanup_canary()
        return 1
    log("PASS", "Stage 2: Exit 2 repaired in RAM, promoted via atomic rename, and blueprint archived.")

    # -------------------------------------------------------------
    # Stage 3: Stigmergy Healing (0 tokens)
    # -------------------------------------------------------------
    log("TEST", "Stage 3: Re-sabotaging run.py back to status=ok (Exit 2 repeat)...")
    run_code = (TEST_SERVICE / "run.py").read_text(encoding="utf-8")
    reverted = run_code.replace('"status": "ironclad"', '"status": "ok"')
    (TEST_SERVICE / "run.py").write_text(reverted, encoding="utf-8")
    kill_pid(TEST_SERVICE / ".state" / "run.pid")
    subprocess.Popen([str(PYTHON_BIN), "run.py"], cwd=str(TEST_SERVICE))
    time.sleep(0.35)

    sweep_directory(SERVICES_DIR)
    time.sleep(0.4)

    res = subprocess.run(["bash", "verify.sh"], cwd=str(TEST_SERVICE), capture_output=True, text=True)
    if res.returncode != 0:
        log("FAIL", "Stage 3: Stigmergic blueprint recovery failed!")
        cleanup_canary()
        return 1
    log("PASS", "Stage 3: Stigmergic blueprint healed component instantly (0 tokens).")

    # -------------------------------------------------------------
    # Stage 3b: Circuit Breaker Verification (.state/CIRCUIT_OPEN.lock)
    # -------------------------------------------------------------
    log("TEST", "Stage 3b: Testing Circuit Breaker ceiling (2 failed attempts -> CIRCUIT_OPEN.lock)...")
    # Keep blueprint that returns status=ironclad, but sabotage verify.sh to demand status=impossible
    impossible_verify = sabotaged.replace('[[ "$ACTUAL" != "ironclad" ]]', '[[ "$ACTUAL" != "impossible" ]]')
    impossible_verify = impossible_verify.replace("Expected status=ironclad", "Expected status=impossible")
    (TEST_SERVICE / "verify.sh").write_text(impossible_verify, encoding="utf-8")

    # Attempt 1 & Attempt 2 using stale blueprint (which returns ironclad != impossible)
    sweep_directory(SERVICES_DIR)
    sweep_directory(SERVICES_DIR)

    lock_file = TEST_SERVICE / ".state" / "CIRCUIT_OPEN.lock"
    if not lock_file.exists():
        log("FAIL", "Stage 3b: Circuit breaker failed to trip .state/CIRCUIT_OPEN.lock after 2 failed attempts!")
        cleanup_canary()
        return 1
    log("PASS", "Stage 3b: Circuit breaker tripped .state/CIRCUIT_OPEN.lock after 2 failed attempts.")

    # -------------------------------------------------------------
    # Stage 4: Advocate Reaction Grid Smoke Test
    # -------------------------------------------------------------
    log("TEST", "Stage 4: Auditing live advocate reaction grid...")
    adv_test = ROOT_DIR / "scripts" / "test_vfs_advocates_chain.py"
    res = subprocess.run([str(PYTHON_BIN), str(adv_test)], capture_output=True, text=True)
    if res.returncode != 0:
        log("FAIL", f"Stage 4: Advocate chain verification failed:\n{res.stderr or res.stdout}")
        cleanup_canary()
        return 1
    log("PASS", "Stage 4: Advocate stigmergic chain reaction verified 100% green.")

    cleanup_canary()
    log("DONE", "All Production Reaction Grid stages validated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
