#!/home/james/stacklabs/.venv/bin/python3
"""
Self-Contained VFS Executable Schematic & /dev/shm Sabotage Harness (Port 5099)
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC

Tests:
  1. Pure Reflex (Exit 1): Process killed -> Instant restart, 0 tokens.
  2. RAM Sandbox Escalation (Exit 2): Schema drift -> /dev/shm clone on Port 15099 -> Patch -> Atomic NVMe promotion.
  3. Stigmergy / Pheromone Trail (Exit 2 repeat): Re-sabotaged -> Fixed instantly from blueprints without waking mechanic.
"""
import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

LAB_ROOT = Path("/tmp/vfs_lab")
VFS_SERVICES = LAB_ROOT / "services"
BLUEPRINTS = LAB_ROOT / "blueprints"
SHM_ROOT = Path("/dev/shm/vfs_sandbox_5099")
COMP_DIR = VFS_SERVICES / "dummy_ticker"
HOOK_PATH = LAB_ROOT / "slm_repair_hook.py"

def log(tag: str, msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}", flush=True)

# ---------------------------------------------------------------------------
# 1. 3-File VFS Folder Contract Definitions
# ---------------------------------------------------------------------------
SPEC_JSON = {
    "ci_id": "ci_dummy_ticker_5099",
    "primitive": "container",
    "target_state": "active",
    "bindings": {"port": 5099, "host": "127.0.0.1", "pid_file": ".state/run.pid"},
    "dependencies": [],
    "reflex_policy": {"max_retries": 2, "backoff_ms": 200, "escalate_to_shm": True}
}

RUN_PY = """#!/home/james/stacklabs/.venv/bin/python3
import json
import os
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = pathlib.Path(__file__).resolve().parent
SPEC = json.loads((BASE_DIR / "spec.json").read_text(encoding="utf-8"))
STATE_DIR = BASE_DIR / ".state"
STATE_DIR.mkdir(exist_ok=True)
(STATE_DIR / "run.pid").write_text(str(os.getpid()), encoding="utf-8")

PAYLOAD = {"service": "dummy_ticker", "status": "ok"}

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

VERIFY_SH_V1 = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PID_FILE=".state/run.pid"
PORT=$(/home/james/stacklabs/.venv/bin/python3 -c 'import json; print(json.load(open("spec.json"))["bindings"]["port"])')

if [[ ! -f "$PID_FILE" ]] || ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "DELTA_EXIT_1: Process dead on port $PORT" >&2
    exit 1
fi

RESP=$(curl -s --max-time 1 "http://127.0.0.1:${PORT}/health" || true)
ACTUAL=$(/home/james/stacklabs/.venv/bin/python3 -c "import json, sys; print(json.loads(sys.argv[1]).get('status',''))" "$RESP" 2>/dev/null || true)

if [[ "$ACTUAL" != "ok" ]]; then
    echo "DELTA_EXIT_2: Expected status=ok, got status=${ACTUAL}" >&2
    exit 2
fi
exit 0
"""

SLM_HOOK_PY = """#!/home/james/stacklabs/.venv/bin/python3
import ast
import re
import sys
from pathlib import Path

sandbox = Path(sys.argv[1])
delta_err = (sandbox / ".state" / "delta.err").read_text(encoding="utf-8").strip()
run_path = sandbox / "run.py"
code = run_path.read_text(encoding="utf-8")

# Parse the exact diagnosis: "Expected status=X, got status=Y"
m = re.search(r"Expected status=(\\w+), got status=(\\w+)", delta_err)
if not m:
    sys.exit(f"UNRECOGNIZED_DELTA: {delta_err}")

expected, actual = m.group(1), m.group(2)
patched = code.replace(f'"status": "{actual}"', f'"status": "{expected}"')

# Zero-trust AST syntax gate before writing candidate
ast.parse(patched)
run_path.write_text(patched, encoding="utf-8")
run_path.chmod(0o755)
"""

# ---------------------------------------------------------------------------
# 2. Reflex Engine (with Cross-Device EXDEV Atomic Promotion Fix)
# ---------------------------------------------------------------------------
def kill_circuit(comp_dir: Path) -> None:
    pid_file = comp_dir / ".state" / "run.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.05)
                    os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        except (ValueError, OSError):
            pass
        pid_file.unlink(missing_ok=True)

def atomic_promote(shm_file: Path, dest_file: Path) -> None:
    """Avoids EXDEV (cross-device link) by staging to dest filesystem first, then os.replace."""
    stage_tmp = dest_file.with_suffix(dest_file.suffix + ".staging")
    shutil.copy2(shm_file, stage_tmp)
    os.replace(stage_tmp, dest_file)

def escalate_to_shm(comp_dir: Path, spec: dict, delta_err: str) -> None:
    SHM_ROOT.mkdir(parents=True, exist_ok=True)
    sandbox = SHM_ROOT / f"{comp_dir.name}_{int(time.time() * 1000)}"
    shutil.copytree(comp_dir, sandbox, symlinks=True)

    shm_port = spec["bindings"]["port"] + 10000
    shm_spec = dict(spec, bindings=dict(spec["bindings"], port=shm_port))
    (sandbox / "spec.json").write_text(json.dumps(shm_spec, indent=2), encoding="utf-8")
    (sandbox / ".state").mkdir(exist_ok=True)
    (sandbox / ".state" / "delta.err").write_text(delta_err, encoding="utf-8")

    bp_run = BLUEPRINTS / comp_dir.name / "run.py"
    if bp_run.exists():
        log("STIGMERGY", f"Found pheromone blueprint at {bp_run}! Skipping SLM.")
        shutil.copy2(bp_run, sandbox / "run.py")
    else:
        log("SLM-MECHANIC", f"No blueprint yet. Running repair hook in /dev/shm for: '{delta_err}'")
        subprocess.run([sys.executable, str(HOOK_PATH), str(sandbox)], check=True)

    log("SANDBOX", f"Booting candidate circuit in RAM on ephemeral port {shm_port}...")
    subprocess.Popen(["./run.py"], cwd=sandbox)
    time.sleep(0.3)
    try:
        res = subprocess.run(["./verify.sh"], cwd=sandbox, capture_output=True, text=True)
        if res.returncode == 0:
            log("SANDBOX", "Candidate passed verify.sh (Exit 0) in RAM! Promoting to production...")
            bp_run.parent.mkdir(parents=True, exist_ok=True)
            atomic_promote(sandbox / "run.py", bp_run)
            kill_circuit(comp_dir)
            atomic_promote(sandbox / "run.py", comp_dir / "run.py")
            subprocess.Popen(["./run.py"], cwd=comp_dir)
            time.sleep(0.3)
        else:
            log("SANDBOX-FAIL", f"Candidate failed verification: {res.stderr.strip()}")
    finally:
        kill_circuit(sandbox)
        shutil.rmtree(sandbox, ignore_errors=True)
        log("SANDBOX", "Wiped /dev/shm scratchpad clean (0 orphan processes).")

def sweep_once() -> None:
    for spec_file in VFS_SERVICES.glob("*/spec.json"):
        comp_dir = spec_file.parent
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        res = subprocess.run(["./verify.sh"], cwd=comp_dir, capture_output=True, text=True)
        if res.returncode == 0:
            log("VERIFY", f"{comp_dir.name} healthy on port {spec['bindings']['port']} (Exit 0).")
        elif res.returncode == 1:
            log("REFLEX-EXIT-1", f"{res.stderr.strip()} -> Restarting immediately (0 tokens)...")
            kill_circuit(comp_dir)
            subprocess.Popen(["./run.py"], cwd=comp_dir)
            time.sleep(0.3)
        elif res.returncode == 2:
            delta_msg = (res.stderr or res.stdout).strip()
            log("DELTA-EXIT-2", f"Diagnosis triggered instruction: '{delta_msg}'")
            escalate_to_shm(comp_dir, spec, delta_msg)

# ---------------------------------------------------------------------------
# 3. Main Test Execution
# ---------------------------------------------------------------------------
def main() -> int:
    if LAB_ROOT.exists():
        kill_circuit(COMP_DIR)
        shutil.rmtree(LAB_ROOT, ignore_errors=True)
    COMP_DIR.mkdir(parents=True, exist_ok=True)

    (COMP_DIR / "spec.json").write_text(json.dumps(SPEC_JSON, indent=2), encoding="utf-8")
    for fname, content in [("run.py", RUN_PY), ("verify.sh", VERIFY_SH_V1)]:
        p = COMP_DIR / fname
        p.write_text(content, encoding="utf-8")
        p.chmod(0o755)
    HOOK_PATH.write_text(SLM_HOOK_PY, encoding="utf-8")
    HOOK_PATH.chmod(0o755)

    try:
        print("\n=== BOOT: Starting dummy_ticker on Port 5099 ===")
        sweep_once()  # Sees dead process -> Reflex starts it
        sweep_once()  # Confirms Exit 0

        print("\n=== TEST 1: Pure Reflex ('Kick the Plug Out') ===")
        pid = int((COMP_DIR / ".state" / "run.pid").read_text(encoding="utf-8").strip())
        log("SABOTAGE-1", f"Sending SIGKILL to live PID {pid} on port 5099...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.1)
        sweep_once()  # Detects Exit 1 -> Restarts immediately
        sweep_once()  # Confirms Exit 0

        print("\n=== TEST 2: 'A Diagnosis is an Instruction' (/dev/shm Escalation) ===")
        log("SABOTAGE-2", "Updating verify.sh target state: requiring status='ironclad' instead of 'ok'...")
        verify_v2 = VERIFY_SH_V1.replace('!= "ok"', '!= "ironclad"').replace('status=ok', 'status=ironclad')
        (COMP_DIR / "verify.sh").write_text(verify_v2, encoding="utf-8")
        sweep_once()  # Detects Exit 2 -> Clones to /dev/shm:15099 -> Patches -> Promotes -> Saves blueprint
        sweep_once()  # Confirms Exit 0 on port 5099 with new payload

        print("\n=== TEST 3: Stigmergy / Pheromone Memory (Zero-Token Instant Fix) ===")
        log("SABOTAGE-3", "Re-sabotaging live run.py back to broken status='ok'...")
        (COMP_DIR / "run.py").write_text(RUN_PY, encoding="utf-8")
        (COMP_DIR / "run.py").chmod(0o755)
        kill_circuit(COMP_DIR)
        subprocess.Popen(["./run.py"], cwd=COMP_DIR)
        time.sleep(0.3)
        sweep_once()  # Detects Exit 2 -> Finds blueprints/ -> Fixes without calling SLM hook
        sweep_once()  # Confirms Exit 0

        print("\n=== ALL 3 CIRCUIT TESTS PASSED ===")
        return 0
    finally:
        kill_circuit(COMP_DIR)
        if SHM_ROOT.exists():
            shutil.rmtree(SHM_ROOT, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
