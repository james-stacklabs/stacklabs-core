#!/home/james/stacklabs/.venv/bin/python3
"""
Production VFS Reflex Supervisor
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/vfs_reflex_watcher.py

Watches /home/james/stacklabs/vfs/{services,advocates} and enforces:
- Exit 0: Healthy, 0 tokens.
- Exit 1: Pure UNIX reflex restart / trigger, 0 tokens.
- Exit 2: /dev/shm repair dumbwaiter (Gear 0 Blueprints -> Gear 1 gemini-3.8-flash -> Circuit Breaker).
"""
import ast
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from typing import Optional

ROOT_DIR = pathlib.Path("/home/james/stacklabs")
VFS_ROOT = ROOT_DIR / "vfs"
SERVICES_DIR = VFS_ROOT / "services"
ADVOCATES_DIR = VFS_ROOT / "advocates"
BLUEPRINTS_DIR = VFS_ROOT / "blueprints"
SHM_ROOT = pathlib.Path("/dev/shm/vfs_sandbox")
LOG_FILE = ROOT_DIR / "data" / "vfs_reflex.log"
PYTHON_BIN = ROOT_DIR / ".venv" / "bin" / "python3"


def log(tag: str, msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{tag}] {msg}"
    print(entry, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def kill_process(comp_dir: pathlib.Path) -> None:
    pid_file = comp_dir / ".state" / "run.pid"
    if not pid_file.exists():
        return
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


def atomic_promote(shm_file: pathlib.Path, dest_file: pathlib.Path) -> None:
    """Avoids EXDEV by copying to destination directory staging file first, then os.replace."""
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    staging_file = dest_file.with_suffix(dest_file.suffix + ".staging")
    shutil.copy2(shm_file, staging_file)
    os.replace(staging_file, dest_file)


def gather_deps_context(sandbox: pathlib.Path) -> str:
    """Extracts schema DDL and upstream contracts from symlinks in deps/."""
    deps_dir = sandbox / "deps"
    if not deps_dir.exists():
        return "No upstream dependencies linked in ./deps/"

    context_lines = []
    for dep in deps_dir.iterdir():
        resolved = dep.resolve()
        if not resolved.exists():
            context_lines.append(f"[{dep.name}]: BROKEN_SYMLINK -> {resolved}")
            continue

        # If upstream is a directory with spec.json
        if resolved.is_dir() and (resolved / "spec.json").exists():
            spec_data = (resolved / "spec.json").read_text(encoding="utf-8")
            context_lines.append(f"[{dep.name}/spec.json]:\n{spec_data}")
        elif resolved.is_file() and resolved.suffix == ".db":
            # Extract SQLite table DDL in read-only mode
            try:
                res = subprocess.run(
                    ["sqlite3", f"file:{resolved}?mode=ro", ".schema"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    context_lines.append(f"[{dep.name} schema]:\n{res.stdout.strip()[:1000]}")
            except Exception as e:
                context_lines.append(f"[{dep.name}]: SQLite inspection error: {e}")
        else:
            context_lines.append(f"[{dep.name}]: Target file exists ({resolved.name})")

    return "\n\n".join(context_lines)


def strip_code_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _get_gemini_api_key() -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key.strip()
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def call_gemini_flash_repair(prompt: str) -> Optional[str]:
    """Invokes gemini-3.8-flash via REST API using standard urllib. Zero local APU compute."""
    api_key = _get_gemini_api_key()
    if not api_key:
        log("REPAIR-ERROR", "GEMINI_API_KEY not configured in environment.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.0,
                "thinkingConfig": {"thinkingLevel": "low"},
            },
        }
    ).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            code = strip_code_fences(raw)
            ast.parse(code)
            return code
    except Exception as e:
        log("REPAIR-ERROR", f"gemini-3.8-flash call failed: {e}")
        return None


def deterministic_patch_fallback(sandbox: pathlib.Path, delta_err: str) -> Optional[str]:
    """Deterministic regex patcher for test canaries and simple state drift."""
    run_file = sandbox / "run.py"
    if not run_file.exists():
        return None
    code = run_file.read_text(encoding="utf-8")

    # Check for canary status drift: Expected status=X, got status=Y
    m = re.search(r"Expected status=(\w+), got status=(\w*)", delta_err)
    if m:
        expected, actual = m.group(1), m.group(2)
        if actual and f'"status": "{actual}"' in code:
            patched = code.replace(f'"status": "{actual}"', f'"status": "{expected}"')
            try:
                ast.parse(patched)
                return patched
            except Exception:
                return None
    return None


def escalate_to_shm_repair(comp_dir: pathlib.Path, spec: dict, delta_err: str) -> bool:
    state_dir = comp_dir / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_file = state_dir / "CIRCUIT_OPEN.lock"
    attempts_file = state_dir / "repair_attempts.json"

    if lock_file.exists():
        log("CIRCUIT-BREAKER", f"{comp_dir.name} is LOCKED by CIRCUIT_OPEN.lock. Manual clear required.")
        return False

    attempts_data = {"attempts": 0, "last_error": ""}
    if attempts_file.exists():
        try:
            attempts_data = json.loads(attempts_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if attempts_data.get("attempts", 0) >= 2:
        log("CIRCUIT-BREAKER", f"{comp_dir.name} exceeded 2 repair attempts. Tripping CIRCUIT_OPEN.lock.")
        lock_file.write_text(
            f"TRIPPED at {time.strftime('%Y-%m-%d %H:%M:%S')} on error:\n{delta_err}\n",
            encoding="utf-8",
        )
        return False

    SHM_ROOT.mkdir(parents=True, exist_ok=True)
    sandbox = SHM_ROOT / f"{comp_dir.name}_{int(time.time() * 1000)}"
    shutil.copytree(comp_dir, sandbox, symlinks=True)

    shm_state = sandbox / ".state"
    shm_state.mkdir(exist_ok=True)
    (shm_state / "delta.err").write_text(delta_err, encoding="utf-8")

    # Check for port re-binding if network component
    has_port = "bindings" in spec and "port" in spec["bindings"]
    orig_port = spec["bindings"]["port"] if has_port else None
    if has_port and isinstance(orig_port, int):
        shm_spec = dict(spec)
        shm_spec["bindings"] = dict(spec["bindings"], port=orig_port + 10000)
        (sandbox / "spec.json").write_text(json.dumps(shm_spec, indent=2), encoding="utf-8")

    bp_file = BLUEPRINTS_DIR / comp_dir.name / "run.py"
    patched_code = None

    # Gear 0: Stigmergic Blueprint
    if bp_file.exists():
        log("STIGMERGY", f"Gear 0: Stigmergic blueprint found for {comp_dir.name}. Testing in RAM...")
        patched_code = bp_file.read_text(encoding="utf-8")
    else:
        # Gear 1: Cloud Escalation (or deterministic test fallback)
        log("REPAIR", f"Gear 1: Escalating {comp_dir.name} to repair mechanic...")
        deps_context = gather_deps_context(sandbox)
        current_code = (sandbox / "run.py").read_text(encoding="utf-8") if (sandbox / "run.py").exists() else ""
        prompt = f"""You are the StackLabs VFS Junior Repair Mechanic.
Fix the broken Python script run.py for component '{comp_dir.name}'.

=== ERROR DIAGNOSIS (verify.sh stderr) ===
{delta_err}

=== CURRENT run.py ===
{current_code}

=== UPSTREAM CIRCUIT DEPENDENCIES (./deps/) ===
{deps_context}

=== RULES ===
1. Return ONLY the complete, runnable, corrected Python code for run.py.
2. Preserve all port bindings, spec.json reading, and PID logging in .state/run.pid.
3. No explanation, no Markdown fences, no comments.
"""
        patched_code = call_gemini_flash_repair(prompt)
        if not patched_code:
            patched_code = deterministic_patch_fallback(sandbox, delta_err)

    if not patched_code:
        log("REPAIR-FAILED", f"No candidate code generated for {comp_dir.name}.")
        attempts_data["attempts"] = attempts_data.get("attempts", 0) + 1
        attempts_data["last_error"] = delta_err
        attempts_file.write_text(json.dumps(attempts_data, indent=2), encoding="utf-8")
        if attempts_data["attempts"] >= 2:
            log("CIRCUIT-BREAKER", f"{comp_dir.name} reached 2 failed repair attempts. Tripping CIRCUIT_OPEN.lock.")
            lock_file.write_text(
                f"TRIPPED at {time.strftime('%Y-%m-%d %H:%M:%S')} on error:\n{delta_err}\n",
                encoding="utf-8",
            )
        shutil.rmtree(sandbox, ignore_errors=True)
        return False

    candidate_run = sandbox / "run.py"
    candidate_run.write_text(patched_code, encoding="utf-8")
    candidate_run.chmod(0o755)

    # Boot candidate in RAM sandbox
    subprocess.Popen([str(PYTHON_BIN), "run.py"], cwd=str(sandbox))
    time.sleep(0.35)

    res = subprocess.run(["bash", "verify.sh"], cwd=str(sandbox), capture_output=True, text=True)
    kill_process(sandbox)

    if res.returncode == 0:
        log("REPAIR-SUCCESS", f"Candidate for {comp_dir.name} PASSED verify.sh in RAM! Promoting...")
        # 1. Save to blueprints (Stigmergy)
        bp_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_promote(candidate_run, bp_file)

        # 2. NVMe-safe atomic promotion to production
        kill_process(comp_dir)
        atomic_promote(candidate_run, comp_dir / "run.py")
        (comp_dir / "run.py").chmod(0o755)

        # 3. Reset circuit breaker attempts
        attempts_data["attempts"] = 0
        attempts_file.write_text(json.dumps(attempts_data, indent=2), encoding="utf-8")

        # 4. Restart in production if container service
        if has_port:
            subprocess.Popen([str(PYTHON_BIN), "run.py"], cwd=str(comp_dir))
            time.sleep(0.35)

        shutil.rmtree(sandbox, ignore_errors=True)
        return True
    else:
        log("REPAIR-FAILED", f"Candidate for {comp_dir.name} FAILED verify.sh in RAM (code {res.returncode}): {res.stderr}")
        attempts_data["attempts"] = attempts_data.get("attempts", 0) + 1
        attempts_data["last_error"] = res.stderr or delta_err
        attempts_file.write_text(json.dumps(attempts_data, indent=2), encoding="utf-8")
        if attempts_data["attempts"] >= 2:
            log("CIRCUIT-BREAKER", f"{comp_dir.name} reached 2 failed repair attempts. Tripping CIRCUIT_OPEN.lock.")
            lock_file.write_text(
                f"TRIPPED at {time.strftime('%Y-%m-%d %H:%M:%S')} on error:\n{res.stderr or delta_err}\n",
                encoding="utf-8",
            )
        shutil.rmtree(sandbox, ignore_errors=True)
        return False


def sweep_directory(parent_dir: pathlib.Path) -> None:
    if not parent_dir.exists():
        return

    for item in sorted(parent_dir.iterdir()):
        if not item.is_dir():
            continue
        spec_file = item / "spec.json"
        verify_sh = item / "verify.sh"
        if not spec_file.exists() or not verify_sh.exists():
            continue

        try:
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        if spec.get("target_state") != "active":
            continue

        res = subprocess.run(["bash", "verify.sh"], cwd=str(item), capture_output=True, text=True)
        rc = res.returncode

        if rc == 0:
            pass  # Steady state
        elif rc == 1:
            # Pure reflex execution
            log("REFLEX", f"Exit 1 reflex triggered for {item.name}: executing run.py")
            has_port = "bindings" in spec and "port" in spec.get("bindings", {})
            if has_port or spec.get("primitive") == "container":
                subprocess.Popen([str(PYTHON_BIN), "run.py"], cwd=str(item))
            else:
                subprocess.run([str(PYTHON_BIN), "run.py"], cwd=str(item), capture_output=True, text=True, check=False)
        elif rc == 2:
            # Code repair / schema drift
            delta_err = res.stderr.strip() or res.stdout.strip() or "Exit 2 verification failure"
            log("DRIFT", f"Exit 2 defect detected for {item.name}: {delta_err}")
            escalate_to_shm_repair(item, spec, delta_err)


def main() -> None:
    pid_file = ROOT_DIR / "data" / "vfs_reflex.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    log("SUPERVISOR", f"VFS Reflex Supervisor starting production watch loop (PID {os.getpid()})...")
    while True:
        try:
            sweep_directory(SERVICES_DIR)
            sweep_directory(ADVOCATES_DIR)
        except Exception as e:
            log("SUPERVISOR-EXCEPTION", f"Loop exception: {e}")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
