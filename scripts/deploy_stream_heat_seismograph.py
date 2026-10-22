#!/home/james/stacklabs/.venv/bin/python3
"""
Deployment script for WO0011177: Cultural Heat Seismograph & Stream Tail CMDB Engine.
Installs validated drop-in daemon from pilot_drops/downloads/scratch/ into scripts/.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

SCRATCH_SOURCE = pathlib.Path(
    "/home/james/stacklabs/pilot_drops/downloads/scratch/stream_heat_seismograph_daemon.py"
)
TARGET_SCRIPT = pathlib.Path(
    "/home/james/stacklabs/scripts/stream_heat_seismograph_daemon.py"
)
SAMPLE_FIXTURE_SRC = pathlib.Path(
    "/home/james/stacklabs_inbox/notebook_sync/00_Spark_Code_Scratch/stream_tail_meltdown_engine/sample_chat_telemetry.json"
)
SAMPLE_FIXTURE_DST = pathlib.Path(
    "/home/james/stacklabs/data/sample_chat_telemetry.json"
)
VENV_PYTHON = "/home/james/stacklabs/.venv/bin/python3"


def deploy() -> None:
    print("[WO0011177] Starting Cultural Heat Seismograph deployment...")

    if not SCRATCH_SOURCE.exists():
        print(f"❌ Error: Source file not found: {SCRATCH_SOURCE}")
        sys.exit(1)

    # 1. Install to canonical scripts directory
    shutil.copy2(SCRATCH_SOURCE, TARGET_SCRIPT)
    TARGET_SCRIPT.chmod(0o755)
    print(f"  ✔ Deployed {TARGET_SCRIPT} (755)")

    # 2. Stage permanent sample telemetry fixture
    if SAMPLE_FIXTURE_SRC.exists() and not SAMPLE_FIXTURE_DST.exists():
        shutil.copy2(SAMPLE_FIXTURE_SRC, SAMPLE_FIXTURE_DST)
        print(f"  ✔ Staged sample telemetry fixture to {SAMPLE_FIXTURE_DST}")

    # 3. Syntax check
    res = subprocess.run(
        [VENV_PYTHON, "-m", "py_compile", str(TARGET_SCRIPT)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Syntax error in {TARGET_SCRIPT}:\n{res.stderr}")
        sys.exit(1)
    print("  ✔ PyCompile syntax validation passed cleanly.")

    # 4. Anti-metaphor linter gate
    linter_path = "/home/james/stacklabs/scripts/anti_metaphor_linter.py"
    if os.path.exists(linter_path):
        res = subprocess.run(
            [VENV_PYTHON, linter_path, "--artifacts", str(TARGET_SCRIPT)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print(f"❌ Anti-metaphor lint failed:\n{res.stdout}\n{res.stderr}")
            sys.exit(1)
        print("  ✔ Anti-metaphor linter gate passed cleanly.")

    # 5. CLI Replay Verification
    if SAMPLE_FIXTURE_DST.exists():
        res = subprocess.run(
            [
                VENV_PYTHON,
                str(TARGET_SCRIPT),
                "--replay-json",
                str(SAMPLE_FIXTURE_DST),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print(f"❌ Replay test execution failed:\n{res.stderr}")
            sys.exit(1)
        
        # Verify JSON output structure
        try:
            report = json.loads(res.stdout)
            processed = (
                report.get("telemetry_metrics", {}).get("raw_records_scanned")
                or report.get("replay_metrics", {}).get("total_messages_processed", 0)
            )
            tails = len(report.get("synthesized_cmdb_stream_tails", []))
            provocateurs = len(report.get("provocateur_clusters", {}).get("top_provocateurs", []))
            print(f"  ✔ Replay test passed: {processed} messages processed, {provocateurs} provocateurs extracted, {tails} CMDB stream tails synthesized.")
        except Exception as e:
            print(f"❌ Failed to parse replay JSON output: {e}")
            sys.exit(1)

    print("\n[WO0011177] Deployment completed successfully.")


if __name__ == "__main__":
    deploy()
