#!/usr/bin/env python3
"""
Sovereign OS: 14-Day Inbox Archival Sweep
Path: /home/james/stacklabs/scripts/ops/inbox_14day_archival_sweep.py

Non-destructively archives directories older than 14 days from /home/james/sovereign_inbox
into structured archive vault subdirectories:
  - archive/daily/
  - archive/projects/
  - archive/backups/
  - archive/staging_cache/

Preserves all whitelisted dossiers, active sprint assets, recent daily dirs (09/11+), and core engines.
Heals the 'yesterday' symlink.
"""

import os
import shutil
from pathlib import Path

INBOX = Path("/home/james/sovereign_inbox")
ARCHIVE = INBOX / "archive"

# Ensure target archive structures exist
(ARCHIVE / "daily").mkdir(parents=True, exist_ok=True)
(ARCHIVE / "projects").mkdir(parents=True, exist_ok=True)
(ARCHIVE / "backups").mkdir(parents=True, exist_ok=True)
(ARCHIVE / "staging_cache").mkdir(parents=True, exist_ok=True)

# 1. Historical Daily Folders (>14 days, pre-2026-09-11)
DAILY_TARGETS = [
    "daily_05212026", "daily_05242026", "daily_05252026", "daily_05262026",
    "daily_05272026", "daily_05282026", "daily_05292026", "daily_05302026",
    "daily_05312026", "daily_06012026", "daily_06022026", "daily_06032026",
    "daily_06042026", "daily_06052026", "daily_06082026", "daily_06202026",
    "daily_06212026", "daily_06282026", "daily_06302026", "daily_07122026",
    "daily_08212026", "daily_08222026", "daily_08232026", "daily_08242026",
    "daily_08262026", "daily_08272026", "daily_08282026", "daily_08292026",
    "daily_08302026", "daily_09042026", "daily_09052026", "daily_09072026",
    "daily_09082026", "daily_09102026"
]

# 2. Historical Project Drops (>14 days)
PROJECT_TARGETS = [
    "FanStack_Creator_Portal_Lookbook", "Intake_Form_Templates", "Nostalgia",
    "PickleballStack", "sam_risky_business", "Sovereign OS Core System",
    "StackLabs_LLC", "verify_stackseeder", "dashboards", "outreach"
]

# 3. Cold Backups
BACKUP_TARGETS = [
    "takeout"
]

# 4. Staging Caches & Intermediate Drops
STAGING_TARGETS = [
    "dead_drop", "evaluations", "hailo_dropzone", "kb", "media_drop",
    "media_transcribe", "staged_docx", "staging", "uat_snapshots",
    "voice_tickets", "walkthrough_assets"
]

moved_count = 0

def move_group(targets, dest_dir):
    global moved_count
    for item in targets:
        src = INBOX / item
        dst = dest_dir / item
        if src.exists():
            print(f"Moving {src.name} -> {dest_dir.name}/{item}")
            shutil.move(str(src), str(dst))
            moved_count += 1
        else:
            print(f"Skipping {src.name} (not found at root)")

def main():
    print("Starting 14-day non-destructive inbox sweep...")
    move_group(DAILY_TARGETS, ARCHIVE / "daily")
    move_group(PROJECT_TARGETS, ARCHIVE / "projects")
    move_group(BACKUP_TARGETS, ARCHIVE / "backups")
    move_group(STAGING_TARGETS, ARCHIVE / "staging_cache")

    # 5. Fix yesterday symlink
    yesterday_link = INBOX / "yesterday"
    if yesterday_link.is_symlink() or yesterday_link.exists():
        yesterday_link.unlink()
    yesterday_link.symlink_to(INBOX / "daily_09242026")
    print("Healed yesterday symlink -> daily_09242026")

    print(f"Sweep complete! Successfully moved {moved_count} directories into archive.")

if __name__ == "__main__":
    main()
