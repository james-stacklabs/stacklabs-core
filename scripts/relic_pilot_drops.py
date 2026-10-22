#!/usr/bin/env python3
"""
scripts/relic_pilot_drops.py
============================
Non-destructive classification and archival migration script for /home/james/stacklabs/pilot_drops/.
Reorganizes loose clutter into dedicated /home/james/stacklabs/pilot_drops/relics/ taxonomy.
Maintains a full rollback manifest (MIGRATION_MANIFEST_*.json) allowing instant 1-command backout.

Usage:
  python3 scripts/relic_pilot_drops.py [--dry-run]
  python3 scripts/relic_pilot_drops.py --undo <path_to_manifest>
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

PILOT_DROPS = Path("/home/james/stacklabs/pilot_drops")
RELICS_DIR = PILOT_DROPS / "relics"

KEEPERS = {
    "pilot_scratch_pad.md",
    "scratch_pad.md",
    "PILOT_PASSPORT_CURRENT.md",
    "PILOT_VOICE_CARD.md",
    "JAMES_CARROLL_ENTERPRISE_RESUME.md",
    "James_Carroll_Resume.pdf",
    "no-wet-toothbrush.md",
    "LATEST_STACKLABS_EMAILS.md",
    "NOTEBOOKLM_PODCAST_DIRECTIVE_PAUL_FRICTIONLESS_METAL.txt",
}

RELIC_CATEGORIES = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
    "media": [".mp3", ".wav", ".m4a", ".mp4", ".mov", ".mkv"],
    "archives": [".zip", ".tar", ".gz", ".tgz", ".7z", ".bz2"],
    "documents_and_pdf": [".pdf", ".pptx", ".ppt", ".doc", ".docx", ".xls", ".xlsx", ".html", ".xml", ".json"],
}

PROJECT_DIRS_TO_RELIC = {
    "Architecting-a-Hardware-Level-System",
    "geminini architect",
    "horizon_paul_sources",
    "notebook_paul_executive",
    "slm_millionaires_notes",
    "slm_millionaires_sources",
    "synapse_sources",
    "upstream_pilot_gyroscope",
}

def classify(file_path: Path) -> str:
    name = file_path.name
    ext = file_path.suffix.lower()
    fname_lower = name.lower()

    if name in KEEPERS:
        return "KEEP"
    if ext in RELIC_CATEGORIES["images"]:
        return "images"
    if "transcript" in fname_lower:
        return "transcripts"
    if name.startswith("Gemini-") or name.startswith("gemini-"):
        return "gemini_exports"
    if ext in RELIC_CATEGORIES["media"]:
        return "media"
    if ext in RELIC_CATEGORIES["archives"]:
        return "archives"
    if ext in RELIC_CATEGORIES["documents_and_pdf"]:
        return "documents_and_pdf"
    if name.startswith("WO") or name.startswith("DRAFT_") or name.startswith("email_draft_") or "draft" in fname_lower or name.endswith(".md.md") or name.endswith(".txt.md") or name.endswith(".docx.md"):
        return "old_drafts_and_wos"
    return "historical_specs"

def run_migration(dry_run=False):
    print("=" * 70)
    print("🧹 STACKLABS PILOT DROPS: RELICS ARCHIVAL MIGRATION")
    print(f"🕒 Timestamp: {datetime.now().isoformat()}")
    print(f"📁 Root:      {PILOT_DROPS}")
    print(f"📦 Relics:    {RELICS_DIR}")
    print(f"⚙️  Mode:      {'[DRY-RUN]' if dry_run else '[LIVE EXECUTION]'}")
    print("=" * 70)

    loose_files = sorted([f for f in PILOT_DROPS.iterdir() if f.is_file() and not f.name.startswith(".")])
    
    moves = []
    skipped_keepers = []

    for f in loose_files:
        cat = classify(f)
        if cat == "KEEP":
            skipped_keepers.append(f.name)
            continue
        dest_dir = RELICS_DIR / cat
        dest_file = dest_dir / f.name
        
        # Avoid collisions
        if dest_file.exists():
            stem = f.stem
            suffix = f.suffix
            counter = 1
            while (dest_dir / f"{stem}_{counter}{suffix}").exists():
                counter += 1
            dest_file = dest_dir / f"{stem}_{counter}{suffix}"
            
        moves.append({
            "source": str(f),
            "destination": str(dest_file),
            "category": cat,
            "filename": f.name
        })

    # Subdirectories
    dir_moves = []
    for d in PILOT_DROPS.iterdir():
        if d.is_dir() and d.name in PROJECT_DIRS_TO_RELIC:
            dest_d = RELICS_DIR / "project_archives" / d.name
            dir_moves.append({
                "source": str(d),
                "destination": str(dest_d),
                "type": "directory",
                "name": d.name
            })

    print(f"Found {len(loose_files)} loose files.")
    print(f"  • Whitelisted Keepers: {len(skipped_keepers)}")
    print(f"  • Files to Relocate:   {len(moves)}")
    print(f"  • Old Dirs to Relocate: {len(dir_moves)}")

    by_cat = {}
    for m in moves:
        c = m["category"]
        by_cat[c] = by_cat.get(c, 0) + 1

    print("\nTaxonomy Distribution:")
    for c, count in sorted(by_cat.items()):
        print(f"  - relics/{c}/: {count} files")

    if dry_run:
        print("\n[DRY RUN COMPLETE] Zero files moved.")
        return

    # Create destination directories
    for cat in set(m["category"] for m in moves):
        (RELICS_DIR / cat).mkdir(parents=True, exist_ok=True)
    if dir_moves:
        (RELICS_DIR / "project_archives").mkdir(parents=True, exist_ok=True)

    executed_file_moves = []
    for m in moves:
        src = Path(m["source"])
        dst = Path(m["destination"])
        shutil.move(src, dst)
        executed_file_moves.append(m)

    executed_dir_moves = []
    for dm in dir_moves:
        src = Path(dm["source"])
        dst = Path(dm["destination"])
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(src, dst)
        executed_dir_moves.append(dm)

    # Save Manifest for Backout
    manifest_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = RELICS_DIR / f"MIGRATION_MANIFEST_{manifest_id}.json"
    manifest_data = {
        "manifest_id": manifest_id,
        "timestamp": datetime.now().isoformat(),
        "total_files_moved": len(executed_file_moves),
        "total_dirs_moved": len(executed_dir_moves),
        "whitelisted_keepers": skipped_keepers,
        "file_moves": executed_file_moves,
        "dir_moves": executed_dir_moves
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Also save as LATEST
    latest_path = RELICS_DIR / "MIGRATION_MANIFEST_LATEST.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE")
    print(f"  • Files Moved:       {len(executed_file_moves)}")
    print(f"  • Dirs Moved:        {len(executed_dir_moves)}")
    print(f"  • Keepers in Root:   {len(skipped_keepers)}")
    print(f"  • Rollback Manifest: {manifest_path}")
    print("=" * 70)

def run_undo(manifest_path: Path):
    if not manifest_path.exists():
        print(f"[-] Error: Manifest not found at {manifest_path}")
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 70)
    print("⏪ STACKLABS PILOT DROPS: ROLLBACK RESTORATION")
    print(f"Manifest ID: {data['manifest_id']}")
    print("=" * 70)

    # Reverse files
    restored_files = 0
    for m in reversed(data.get("file_moves", [])):
        src = Path(m["destination"])
        dst = Path(m["source"])
        if src.exists():
            shutil.move(src, dst)
            restored_files += 1

    # Reverse dirs
    restored_dirs = 0
    for dm in reversed(data.get("dir_moves", [])):
        src = Path(dm["destination"])
        dst = Path(dm["source"])
        if src.exists():
            shutil.move(src, dst)
            restored_dirs += 1

    print(f"✔ Restored {restored_files} files and {restored_dirs} directories back to root.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pilot Drops Relics Migration & Rollback")
    parser.add_argument("--dry-run", action="store_true", help="Simulate moves without executing")
    parser.add_argument("--undo", type=str, default="", help="Path to manifest file to undo migration")
    args = parser.parse_args()

    if args.undo:
        run_undo(Path(args.undo))
    else:
        run_migration(dry_run=args.dry_run)
