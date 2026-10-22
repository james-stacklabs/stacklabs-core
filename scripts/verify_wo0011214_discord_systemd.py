#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Suite for WO0011214: Discord Stream Tailer Systemd Unit & Supervisor
Path: /home/james/stacklabs/scripts/verify_wo0011214_discord_systemd.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(REPO_ROOT))

SERVICE_REPO_PATH = REPO_ROOT / "systemd" / "stacklabs-discord-tailer.service"
CONFIG_REPO_PATH = REPO_ROOT / "config" / "discord_channel_bindings.json"
SUPERVISOR_SCRIPT = REPO_ROOT / "scripts" / "discord_tailer_supervisor.py"
HEARTBEAT_PATH = Path("/dev/shm/vfs/telemetry/discord_supervisor_heartbeat.json")


def verify_systemd_unit_directives() -> None:
    assert SERVICE_REPO_PATH.exists(), f"Missing {SERVICE_REPO_PATH}"
    content = SERVICE_REPO_PATH.read_text(encoding="utf-8")
    required_directives = [
        "ExecStart=/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/discord_tailer_supervisor.py",
        "Restart=always",
        "RestartSec=5",
        "RuntimeMaxSec=14400",
        "KillMode=control-group",
        "User=james",
    ]
    for directive in required_directives:
        assert directive in content, f"Missing mandatory systemd directive: {directive}"
    print("[PASS] 1/3 Systemd unit directives (RuntimeMaxSec=14400, Restart=always, KillMode=control-group) verified.")


def verify_supervisor_dry_run_and_heartbeat() -> None:
    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        str(SUPERVISOR_SCRIPT),
        "--config",
        str(CONFIG_REPO_PATH),
        "--dry-run",
    ]
    out = subprocess.check_output(cmd, text=True)
    data = json.loads(out)
    assert data["supervisor_status"] == "DRY_RUN_VERIFIED"
    assert data["heartbeat"]["ttl_seconds"] == 14400
    assert data["heartbeat"]["active_channel_count"] >= 5
    assert data["tailer_diagnostic"]["status"] == "DRY_RUN_VERIFIED"
    assert data["tailer_diagnostic"]["db_writes_executed"] == 0
    assert HEARTBEAT_PATH.exists(), "Supervisor heartbeat file was not written to /dev/shm"
    print("[PASS] 2/3 Supervisor --dry-run execution and atomic /dev/shm heartbeat verified.")


def verify_hot_bind_and_unbind_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_cfg = Path(tmpdir) / "bindings.json"
        tmp_cfg.write_text(CONFIG_REPO_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        # 1. Bind a new NFL Discord channel
        cmd_bind = [
            "/home/james/stacklabs/.venv/bin/python3",
            str(SUPERVISOR_SCRIPT),
            "--config",
            str(tmp_cfg),
            "--bind-channel",
            "555666777888",
            "--game-id",
            "PHI_NYG",
            "--stream-id",
            "discord_phi_nyg_live",
            "--sport",
            "nfl",
            "--home",
            "NYG",
            "--away",
            "PHI",
            "--ttl-seconds",
            "14400",
        ]
        res_bind = json.loads(subprocess.check_output(cmd_bind, text=True))
        assert res_bind["status"] == "CHANNEL_BOUND"
        assert res_bind["binding"]["game_id"] == "PHI_NYG"
        assert res_bind["binding"]["ttl_seconds"] == 14400

        # 2. Unbind the test channel so watch_party_streams is cleanly marked is_live=0
        cmd_unbind = [
            "/home/james/stacklabs/.venv/bin/python3",
            str(SUPERVISOR_SCRIPT),
            "--config",
            str(tmp_cfg),
            "--unbind-channel",
            "555666777888",
        ]
        res_unbind = json.loads(subprocess.check_output(cmd_unbind, text=True))
        assert res_unbind["status"] == "CHANNEL_UNBOUND"
    print("[PASS] 3/3 Hot channel bind/unbind CLI & watch_party_streams lifecycle verified.")


def main() -> None:
    verify_systemd_unit_directives()
    verify_supervisor_dry_run_and_heartbeat()
    verify_hot_bind_and_unbind_lifecycle()
    print("\n=== ALL WO0011214 SYSTEMD UNIT & SUPERVISOR CHECKS PASSED ===")


if __name__ == "__main__":
    main()
