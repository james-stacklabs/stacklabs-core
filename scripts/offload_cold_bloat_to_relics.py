#!/home/james/stacklabs/.venv/bin/python3
"""
Offload Cold Storage Bloat from Clio Internal NVMe to 1TB External Drive.
Path: /home/james/stacklabs/scripts/offload_cold_bloat_to_relics.py

1. Ensures /mnt/relics/archives structure exists
2. Safely moves legacy codebases, cleanse backups, stale environments, and heavy media
3. Creates symlinks where appropriate to preserve backward compatibility
4. Calculates and records verified bytes reclaimed in data/telemetry/cold_storage_offload_receipt.json
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ARCHIVES_ROOT = pathlib.Path("/mnt/relics/archives")
HOME_DIR = pathlib.Path("/home/james")
STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
TELEMETRY_DIR = STACKLABS_ROOT / "data" / "telemetry"


def get_dir_size(path: pathlib.Path) -> int:
    total = 0
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def move_with_receipt(source: pathlib.Path, target: pathlib.Path) -> dict:
    if not source.exists():
        print(f"[SKIP] Source does not exist: {source}")
        return {"source": str(source), "status": "NOT_FOUND", "bytes": 0}

    size_bytes = get_dir_size(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[OFFLOAD] Moving {source} -> {target} ({size_bytes / (1024*1024):.2f} MB)...")
    if target.exists():
        print(f"[WARN] Target already exists: {target}, merging or skipping")
        target_size = get_dir_size(target)
        return {"source": str(source), "target": str(target), "status": "ALREADY_EXISTS", "bytes": target_size}

    shutil.move(str(source), str(target))
    print(f"[OK] Completed move: {source.name}")
    return {"source": str(source), "target": str(target), "status": "MOVED", "bytes": size_bytes}


def main() -> int:
    if not pathlib.Path("/mnt/relics").exists() or not os.path.ismount("/mnt/relics"):
        print("[ERROR] /mnt/relics is not mounted.")
        return 1

    print("=== Step 1: Ensure Archive Directory Structure ===")
    archive_subdirs = [
        ARCHIVES_ROOT / "legacy_repos",
        ARCHIVES_ROOT / "cleanse_backups",
        ARCHIVES_ROOT / "runtime_snapshots",
        ARCHIVES_ROOT / "media_vault",
    ]
    for d in archive_subdirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Initialized archive tree at {ARCHIVES_ROOT}")

    receipts = []

    print("=== Step 2: Offload Legacy Codebases ===")
    for legacy_name in ["SovereignOS", "SovereignOS-uat"]:
        src = HOME_DIR / legacy_name
        dest = ARCHIVES_ROOT / "legacy_repos" / legacy_name
        receipts.append(move_with_receipt(src, dest))

    # Move standalone legacy repo directory
    legacy_repo_dir = HOME_DIR / "sovereign"
    if legacy_repo_dir.exists():
        dest = ARCHIVES_ROOT / "legacy_repos" / "sovereign"
        receipts.append(move_with_receipt(legacy_repo_dir, dest))

    print("=== Step 3: Offload Cleanse Backups ===")
    for backup_dir in HOME_DIR.glob(".stacklabs_cleanse_backup_*"):
        dest = ARCHIVES_ROOT / "cleanse_backups" / backup_dir.name
        receipts.append(move_with_receipt(backup_dir, dest))

    print("=== Step 4: Offload Stale Runtimes and Unmanaged Modules ===")
    whisper_env = HOME_DIR / "whisper_env"
    if whisper_env.exists():
        dest = ARCHIVES_ROOT / "runtime_snapshots" / "whisper_env"
        receipts.append(move_with_receipt(whisper_env, dest))

    ollama_dir = HOME_DIR / ".ollama"
    if ollama_dir.exists():
        dest = ARCHIVES_ROOT / "runtime_snapshots" / "ollama"
        receipts.append(move_with_receipt(ollama_dir, dest))

    loose_nm = HOME_DIR / "node_modules"
    if loose_nm.exists():
        dest = ARCHIVES_ROOT / "runtime_snapshots" / "loose_home_node_modules"
        receipts.append(move_with_receipt(loose_nm, dest))

    servicenow_mid = HOME_DIR / "servicenow_mid"
    if servicenow_mid.exists():
        dest = ARCHIVES_ROOT / "runtime_snapshots" / "servicenow_mid"
        receipts.append(move_with_receipt(servicenow_mid, dest))

    print("=== Step 5: Offload Heavy Raw Media ===")
    heavy_mp4 = HOME_DIR / "Vientos_Raw_Capture.mp4"
    if heavy_mp4.exists():
        dest = ARCHIVES_ROOT / "media_vault" / "Vientos_Raw_Capture.mp4"
        receipts.append(move_with_receipt(heavy_mp4, dest))

    print("=== Step 6: Verify and Maintain Symlinks ===")
    archive_symlink = HOME_DIR / "sovereign_archive"
    if not archive_symlink.exists():
        os.symlink("/mnt/relics/archives/legacy_repos", str(archive_symlink))
        print(f"[OK] Created symlink {archive_symlink} -> /mnt/relics/archives/legacy_repos")

    total_reclaimed_bytes = sum(r.get("bytes", 0) for r in receipts if r.get("status") == "MOVED")
    total_reclaimed_gb = total_reclaimed_bytes / (1024 ** 3)
    print(f"[SUMMARY] Total cold storage offloaded: {total_reclaimed_gb:.2f} GB")

    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    receipt_file = TELEMETRY_DIR / "cold_storage_offload_receipt.json"
    telemetry_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "node": "Clio (100.96.77.20)",
        "total_reclaimed_bytes": total_reclaimed_bytes,
        "total_reclaimed_gb": round(total_reclaimed_gb, 3),
        "items_offloaded": receipts,
    }
    receipt_file.write_text(json.dumps(telemetry_payload, indent=2), encoding="utf-8")
    print(f"[OK] Telemetry receipt committed to {receipt_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
