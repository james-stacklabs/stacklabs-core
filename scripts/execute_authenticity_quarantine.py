#!/usr/bin/env python3
"""
Sovereign OS Final Documentation Quarantine & Purge Execution
Moves confirmed fiction out of active documentation into quarantine,
purges notebook_sync copies, and syncs clean state with Google Drive.
"""

import os
import shutil
import json
import subprocess

HIT_LIST_JSON = "/home/james/sovereign_inbox/reports/DOCS_AUTHENTICITY_HIT_LIST.json"
QUARANTINE_DIR = "/home/james/sovereign_inbox/quarantine_ai_fiction"
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# Whitelist doctrine and rules files that define the forbidden terms
WHITELIST = [
    "THE_ANTI_SCRIPT_KIDDIE_DOCTRINE.md",
    "THE_ANTI_SCRIPT_KIDDIE_DOCTRINE.txt",
    "THE_ANTI_SCRIPT_KIDDIE_DOCTRINE.md.txt",
    "walkthrough_ENHC0010014-CODE-HYGIENE-SENTINEL-UI.md",
    "walkthrough_ENHC0010014-CODE-HYGIENE-SENTINEL-UI.md.txt",
    "DOCS_AUTHENTICITY_HIT_LIST.json",
    "README.md"
]

with open(HIT_LIST_JSON, "r", encoding="utf-8") as f:
    items = json.load(f)

quarantined = []
deleted_sync = []

for item in items:
    fpath = item["file"]
    basename = os.path.basename(fpath)
    
    if basename in WHITELIST:
        print(f"Skipping whitelisted doctrine/definition: {basename}")
        continue
        
    if not os.path.exists(fpath):
        continue
        
    # If in notebook_sync, delete it so it is permanently gone from NotebookLM
    if "/notebook_sync/" in fpath:
        os.remove(fpath)
        deleted_sync.append(fpath)
        print(f"🗑️ Purged from notebook_sync: {fpath}")
    else:
        # Move to quarantine
        dest = os.path.join(QUARANTINE_DIR, basename)
        shutil.move(fpath, dest)
        quarantined.append(dest)
        print(f"📦 Quarantined: {fpath} -> {dest}")

print(f"\n✅ Quarantined {len(quarantined)} fiction files.")
print(f"✅ Purged {len(deleted_sync)} NotebookLM sync files.")

# Re-sync with Google Drive to remove deleted sync files
print("\n🔄 Syncing clean notebook_sync with Google Drive...")
res = subprocess.run([
    "rclone", "sync",
    "/home/james/sovereign_inbox/notebook_sync/",
    "sovereign_os:Notebook_Sync/",
    "-v"
], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)
print("✅ Google Drive Notebook_Sync updated.")
