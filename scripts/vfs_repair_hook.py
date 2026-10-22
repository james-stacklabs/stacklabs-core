#!/home/james/stacklabs/.venv/bin/python3
"""
VFS Circuit Repair Hook (SLM / Pattern Mechanic)
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC

Operates inside /dev/shm sandboxes when verify.sh exits with code 2.
Applies surgical fixes and passes through an AST syntax gate before writing.
"""
import ast
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SLM_ENDPOINT = os.environ.get("VFS_SLM_URL", "http://127.0.0.1:11434/api/generate")
SLM_MODEL = os.environ.get("VFS_SLM_MODEL", "qwen2.5-coder:7b")

def strip_fences(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def apply_pattern_repair(code: str, delta_err: str) -> str | None:
    """Deterministic pattern repair for common schema/status drifts."""
    m = re.search(r"Expected status=(\w+), got status=(\w+)", delta_err)
    if m:
        expected, actual = m.group(1), m.group(2)
        return code.replace(f'"status": "{actual}"', f'"status": "{expected}"')
    return None

def apply_slm_repair(spec_text: str, run_text: str, delta_err: str) -> str | None:
    prompt = (
        "You are an autonomous POSIX VFS circuit mechanic.\n"
        "The component failed verify.sh with Exit 2 (Diagnosis = Instruction).\n"
        "Return ONLY the complete, corrected Python code for `run.py` resolving DELTA_ERROR.\n\n"
        f"--- spec.json ---\n{spec_text}\n\n"
        f"--- delta.err ---\n{delta_err}\n\n"
        f"--- broken run.py ---\n{run_text}\n"
    )
    payload = json.dumps({
        "model": SLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            SLM_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("response", "")
            return strip_fences(raw)
    except Exception:
        return None

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: vfs_repair_hook.py <sandbox_path> [delta_err]", file=sys.stderr)
        return 1

    sandbox = Path(sys.argv[1])
    spec_path = sandbox / "spec.json"
    run_path = sandbox / "run.py"
    delta_file = sandbox / ".state" / "delta.err"

    if not spec_path.exists() or not run_path.exists():
        print(f"Error: Missing spec.json or run.py in {sandbox}", file=sys.stderr)
        return 1

    spec_text = spec_path.read_text(encoding="utf-8")
    run_text = run_path.read_text(encoding="utf-8")
    delta_err = delta_file.read_text(encoding="utf-8") if delta_file.exists() else (
        sys.argv[2] if len(sys.argv) > 2 else "Unknown Exit 2"
    )

    # 1. Try deterministic pattern repair first
    candidate = apply_pattern_repair(run_text, delta_err)

    # 2. If pattern did not match and local SLM is enabled, attempt inference
    if not candidate and os.environ.get("VFS_ENABLE_SLM") == "1":
        candidate = apply_slm_repair(spec_text, run_text, delta_err)

    if not candidate:
        print(f"Repair hook failed: No matching pattern or SLM unavailable for '{delta_err}'", file=sys.stderr)
        return 2

    # 3. Zero-trust AST validation gate
    try:
        ast.parse(candidate)
    except SyntaxError as e:
        print(f"AST Gate Rejected candidate patch: line {e.lineno}: {e.msg}", file=sys.stderr)
        return 3

    if not candidate.startswith("#!"):
        candidate = "#!/home/james/stacklabs/.venv/bin/python3\n" + candidate

    run_path.write_text(candidate + "\n", encoding="utf-8")
    run_path.chmod(0o755)
    print(f"Successfully patched {run_path} in RAM sandbox.", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
