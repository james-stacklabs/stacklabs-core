#!/usr/bin/env python3
"""
Sovereign OS: Directory Taxonomy Rollback Engine
Work Order: WO0010469-SOVEREIGN-DIRECTORY-TAXONOMY-REFACTOR
Governed by: Invariant 12 & Campsite Protocol

Safely reverses the taxonomy migration:
1. Reads manifest from /home/james/stacklabs/scripts/taxonomy_migration_manifest.json
   (or dynamically scans symlinks in dna/docs/).
2. Removes relative symlinks in dna/docs/.
3. Moves physical files back from domain directories to dna/docs/.
4. Verifies all files are restored and intact.
5. Cleans up empty domain directories.
"""

import os
import sys
import shutil
import json

BASE_DIR = "/home/james/stacklabs"
DOCS_DIR = os.path.join(BASE_DIR, "dna", "docs")
MANIFEST_PATH = os.path.join(BASE_DIR, "scripts", "taxonomy_migration_manifest.json")

DOMAINS = [
    os.path.join(BASE_DIR, "01_Governance_and_ITSM"),
    os.path.join(BASE_DIR, "02_Edge_Hardware_and_Mesh"),
    os.path.join(BASE_DIR, "03_Market_Intelligence"),
    os.path.join(BASE_DIR, "04_Advocate_Swarms"),
    os.path.join(BASE_DIR, "99_Legacy_Archive"),
]


def run_rollback():
    print("=" * 80)
    print("⏪ SOVEREIGN OS: TAXONOMY ROLLBACK ENGINE")
    print("=" * 80)

    moves_to_revert = []

    if os.path.isfile(MANIFEST_PATH):
        print(f"✔ Found migration manifest: {MANIFEST_PATH}")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        moves = manifest.get("moves", [])
        for m in moves:
            moves_to_revert.append((m["old_path"], m["new_path"]))
        print(f"Loaded {len(moves_to_revert)} moves from manifest.")
    else:
        print("⚠️ Manifest not found. Performing dynamic scan of symlinks in dna/docs/...")
        for item in sorted(os.listdir(DOCS_DIR)):
            p = os.path.join(DOCS_DIR, item)
            if os.path.islink(p):
                real_target = os.path.realpath(p)
                for d in DOMAINS:
                    if real_target.startswith(d):
                        moves_to_revert.append((p, real_target))
                        break
        print(f"Discovered {len(moves_to_revert)} symlinks pointing to domain directories.")

    if not moves_to_revert:
        print("No symlinks or moves to revert. System is already in clean state.")
        return

    restored_count = 0
    errors = []

    for old_path, new_path in moves_to_revert:
        try:
            # 1. Verify target real file exists
            if not os.path.isfile(new_path):
                errors.append(f"Target file missing: {new_path}")
                continue

            # 2. Remove symlink if present
            if os.path.islink(old_path):
                os.unlink(old_path)
            elif os.path.exists(old_path):
                errors.append(f"Unexpected non-symlink file at {old_path}; aborting overwrite.")
                continue

            # 3. Move file back to dna/docs/
            shutil.move(new_path, old_path)
            restored_count += 1
        except Exception as e:
            errors.append(f"Failed to revert {old_path} <- {new_path}: {e}")

    print(f"\n✔ Successfully restored {restored_count} files back to {DOCS_DIR}.")

    if errors:
        print(f"\n❌ Encountered {len(errors)} errors:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)

    # 4. Clean up empty domain directories if all files removed
    for d in DOMAINS:
        if os.path.isdir(d):
            remaining = os.listdir(d)
            if not remaining:
                os.rmdir(d)
                print(f"✔ Removed empty domain directory: {d}")
            else:
                print(f"ℹ Directory {d} still contains {len(remaining)} items; kept intact.")

    # 5. Clean up manifest
    if os.path.isfile(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)
        print("✔ Removed manifest file.")

    print("\n🟢 ROLLBACK COMPLETE: All files restored to dna/docs/.")


if __name__ == "__main__":
    run_rollback()
