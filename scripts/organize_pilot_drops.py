#!/usr/bin/env python3
"""
Sovereign OS — Pilot Drops Historical Tidy & Subfolder Migration
Path: /home/james/stacklabs/scripts/organize_pilot_drops.py
Work Order: WO0010216-PILOT-DROPS-DEDICATED-FOLDERS

Organizes flat drops in /home/james/stacklabs/pilot_drops/ into dedicated taxonomy subfolders:
- screenshots/
- photos/
- audio/
- video/
- documents/
- archives/

Strictly preserves whitelisted files in the root.
"""

import os
import sys
import re
import shutil
import argparse
from pathlib import Path

PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops")
THUMBNAILS_DIR = PILOT_DROPS_DIR / ".thumbnails"

SUBFOLDERS = ['screenshots', 'photos', 'audio', 'video', 'documents', 'archives']

WHITELIST_EXACT = {
    'scratch_pad.md',
    'pilot_scratch_pad.md',
    'pegasus_eyes_only.md',
    'artemis_eyes_only.md',
    'ACTIVE_PILOT_PULSE.md',
}

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}


def is_whitelisted(name: str) -> bool:
    """Determine if a file must remain in the root directory."""
    if name in WHITELIST_EXACT:
        return True
    if name.startswith('NOTEBOOKLM_') and name.endswith('.md'):
        return True
    if name.startswith('SOVEREIGN_EDGE_') and name.endswith('.md'):
        return True
    if name.startswith('SOVEREIGN_') and name.endswith('.md'):
        return True
    if name.startswith('SOVEREIGN'):
        return True
    if name.endswith('.py') or name.endswith('.sh') or name.endswith('.log'):
        return True
    if name.startswith('.'):
        return True
    return False


def classify_file(filename: str) -> str:
    """Classify loose file into dedicated taxonomy subfolder."""
    fname_lower = filename.lower()
    ext = os.path.splitext(filename)[1].lower()

    # 1. Screenshots: matches ^Screenshot_ or screencast or Screen_Shot
    if re.search(r'(^screenshot_|screencast|screen_shot)', fname_lower):
        return 'screenshots'

    # 2. Photos: matches ^PXL_ or camera
    if re.search(r'(^pxl_|camera)', fname_lower):
        return 'photos'

    # 3. Audio: {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}
    if ext in {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}:
        return 'audio'

    # 4. Video: {'.mp4', '.mov', '.webm', '.mkv', '.avi'}
    if ext in {'.mp4', '.mov', '.webm', '.mkv', '.avi'}:
        return 'video'

    # 5. Archives: {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'}
    if ext in {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'} or fname_lower.endswith('.tar.gz'):
        return 'archives'

    # 6. Documents: {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}
    if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}:
        return 'documents'

    # 7. Fallback image to photos
    if ext in IMAGE_EXTENSIONS:
        return 'photos'

    # Default fallback
    return 'documents'


def organize(dry_run: bool = False):
    print(f"⚡ Sovereign Pilot Drops Tidy Migration")
    print(f"Target Directory: {PILOT_DROPS_DIR}")
    print(f"Mode: {'[DRY RUN]' if dry_run else '[LIVE EXECUTION]'}")
    print("=" * 60)

    # Ensure all target taxonomy directories exist
    for sub in SUBFOLDERS:
        sub_path = PILOT_DROPS_DIR / sub
        sub_thumb = THUMBNAILS_DIR / sub
        if not dry_run:
            sub_path.mkdir(parents=True, exist_ok=True)
            sub_thumb.mkdir(parents=True, exist_ok=True)

    loose_files = sorted([f for f in PILOT_DROPS_DIR.iterdir() if f.is_file() and not f.name.startswith('.')])
    print(f"Found {len(loose_files)} loose files in root.\n")

    whitelisted_count = 0
    moved_counts = {sub: 0 for sub in SUBFOLDERS}

    for f in loose_files:
        name = f.name
        if is_whitelisted(name):
            whitelisted_count += 1
            print(f"🛡️  [WHITELIST KEEP] {name}")
            continue

        target_folder = classify_file(name)
        target_dir = PILOT_DROPS_DIR / target_folder
        target_path = target_dir / name

        # Avoid clobbering if a file already exists
        if target_path.exists():
            base, ext = os.path.splitext(name)
            counter = 1
            candidate = f"{base}_{counter}{ext}"
            while (target_dir / candidate).exists():
                counter += 1
                candidate = f"{base}_{counter}{ext}"
            target_path = target_dir / candidate

        print(f"📦 [MOVE -> {target_folder}/] {name} -> {target_path.name}")

        if not dry_run:
            shutil.move(str(f), str(target_path))

            # Mirror thumbnail if exists
            flat_thumb = THUMBNAILS_DIR / name
            if flat_thumb.exists() and flat_thumb.is_file():
                dest_thumb_dir = THUMBNAILS_DIR / target_folder
                dest_thumb_dir.mkdir(parents=True, exist_ok=True)
                dest_thumb_path = dest_thumb_dir / target_path.name
                shutil.move(str(flat_thumb), str(dest_thumb_path))

        moved_counts[target_folder] += 1

    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY:")
    print(f"  Total Root Files Scanned: {len(loose_files)}")
    print(f"  Whitelisted Files Kept in Root: {whitelisted_count}")
    for sub in SUBFOLDERS:
        print(f"  Moved to {sub}/: {moved_counts[sub]}")
    total_moved = sum(moved_counts.values())
    print(f"  Total Files Relocated: {total_moved}")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pilot Drops Historical Organizer")
    parser.add_argument("--dry-run", action="store_true", help="Perform simulation without moving files")
    args = parser.parse_args()
    organize(dry_run=args.dry_run)
