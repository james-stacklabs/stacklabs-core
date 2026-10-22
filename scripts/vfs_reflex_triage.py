#!/usr/bin/env python3
"""
Sovereign OS: Autonomous Reflex Triage Loop
Path: /home/james/stacklabs/scripts/vfs_reflex_triage.py
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import time
from datetime import datetime, timezone
from pathlib import Path

VFS_ROOT = Path("/dev/shm/vfs")
INC_DIR = VFS_ROOT / "tickets" / "INC-9001"
DUMMY_LOG = Path("/tmp/vfs_dummy_log.txt")

def stage_p1_incident():
    """Stages simulated P1 incident on sea-db-01."""
    INC_DIR.mkdir(parents=True, exist_ok=True)
    (INC_DIR / "state.txt").write_text("NEW\n")
    (INC_DIR / "priority.txt").write_text("P1-CRITICAL\n")
    (INC_DIR / "short_desc.txt").write_text("Database transaction log disk volume 99% full\n")
    
    # Symlink to sea-db-01
    aff_ci = INC_DIR / "affected_ci"
    if aff_ci.is_symlink() or aff_ci.exists():
        aff_ci.unlink()
    aff_ci.symlink_to("../../cmdb/servers/sea-db-01")
    
    # Seed bloated dummy file
    DUMMY_LOG.write_text("FATAL: DISK FULL TRANSACTIONS BLOCKED\n" * 5000)
    
    # Telemetry leaf
    telem_dir = INC_DIR / "telemetry"
    telem_dir.mkdir(parents=True, exist_ok=True)
    (telem_dir / "disk_usage.txt").write_text("99%\n")
    (telem_dir / "target_log.txt").write_text(str(DUMMY_LOG) + "\n")
    
    (INC_DIR / "journal").mkdir(parents=True, exist_ok=True)

def execute_reflex_triage():
    """Executes the closed-loop autonomous remediation."""
    t_start = time.perf_counter_ns()
    
    # 1. Detect state
    state = (INC_DIR / "state.txt").read_text().strip()
    if state != "NEW":
        raise RuntimeError(f"Unexpected state: {state}")
        
    # 2. Dereference symlink to verify affected node
    resolved_ci = (INC_DIR / "affected_ci").resolve()
    ci_role = (resolved_ci / "operational" / "role.txt").read_text().strip() if (resolved_ci / "operational" / "role.txt").exists() else "SERVER"
    
    # 3. Read telemetry leaf
    usage = (INC_DIR / "telemetry" / "disk_usage.txt").read_text().strip()
    target_log_path = Path((INC_DIR / "telemetry" / "target_log.txt").read_text().strip())
    
    # 4. Execute atomic remediation
    if target_log_path.exists():
        target_log_path.write_text("")  # Truncate to 0 bytes
        
    (INC_DIR / "telemetry" / "disk_usage.txt").write_text("1%\n")
    
    # 5. Append immutable resolution receipt
    now_iso = datetime.now(timezone.utc).isoformat()
    receipt_file = INC_DIR / "journal" / f"{now_iso}_agent.txt"
    receipt_file.write_text(f"""Remediation Receipt: Autonomous Reflex Engine
Target CI: {resolved_ci.name} ({ci_role})
Remediation: Truncated transaction log {target_log_path}
Previous Telemetry: {usage} -> Post Remediation: 1%
State Changed: NEW -> RESOLVED
Timestamp: {now_iso}
""")

    # 6. Flip state
    (INC_DIR / "state.txt").write_text("RESOLVED\n")
    
    elapsed_ms = (time.perf_counter_ns() - t_start) / 1_000_000.0
    return {
        "status": "SUCCESS",
        "ticket": INC_DIR.name,
        "affected_ci": resolved_ci.name,
        "elapsed_ms": round(elapsed_ms, 3),
        "post_state": "RESOLVED"
    }

if __name__ == "__main__":
    stage_p1_incident()
    res = execute_reflex_triage()
    print(f"[PASS] Reflex Triage Loop Completed in {res['elapsed_ms']} ms!")
    print(f"       State: {res['post_state']} | Target CI: {res['affected_ci']}")
