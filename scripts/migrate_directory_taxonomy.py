#!/usr/bin/env python3
"""
Sovereign OS: Automated Directory Taxonomy Refactor & Symlink Bridge
Work Order: WO0010469-SOVEREIGN-DIRECTORY-TAXONOMY-REFACTOR
Governed by: Invariant 12 (Directory Taxonomy) & Campsite Protocol

Categorizes flat architecture specs in /home/james/stacklabs/dna/docs/ into
5 clean domain directories under /home/james/stacklabs/:
  1. 01_Governance_and_ITSM/
  2. 02_Edge_Hardware_and_Mesh/
  3. 03_Market_Intelligence/
  4. 04_Advocate_Swarms/
  5. 99_Legacy_Archive/

For every file moved, creates an exact relative symlink in dna/docs/ pointing
to the new destination (e.g. dna/docs/SPEC_XYZ.md -> ../../02_Edge_Hardware_and_Mesh/SPEC_XYZ.md),
ensuring zero broken paths for existing scripts, sync daemons, and systemd units.
"""

import os
import sys
import fnmatch
import shutil
import json
from datetime import datetime

BASE_DIR = "/home/james/stacklabs"
DOCS_DIR = os.path.join(BASE_DIR, "dna", "docs")
MANIFEST_PATH = os.path.join(BASE_DIR, "scripts", "taxonomy_migration_manifest.json")

DOMAINS = {
    "01_Governance_and_ITSM": os.path.join(BASE_DIR, "01_Governance_and_ITSM"),
    "02_Edge_Hardware_and_Mesh": os.path.join(BASE_DIR, "02_Edge_Hardware_and_Mesh"),
    "03_Market_Intelligence": os.path.join(BASE_DIR, "03_Market_Intelligence"),
    "04_Advocate_Swarms": os.path.join(BASE_DIR, "04_Advocate_Swarms"),
    "99_Legacy_Archive": os.path.join(BASE_DIR, "99_Legacy_Archive"),
}

# Domain 01: Governance, Communications & ITSM
PATTERNS_D1 = [
    "*CONSTITUTION*", "*AGENTS*", "*GEMINI*", "*ITSM*", "*GOVERNANCE*", "*SHUTDOWN*", "*BOOT*",
    "13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.MD",
    "PILOT_BIOGRAPHY*.MD", "*PILOT_BIO*", "*SOW*", "*PROSPECTUS*", "*SERVICE_CATALOG*",
    "SOVEREIGN_POWER_TOOLS_AND_MICROSERVICES_CATALOG.MD",
    "*COMMUNICATIONS*", "*PASSPORT*", "*INCIDENT*", "*STANDARDS*", "*INVARIANT*",
    "*COVENANT*", "*TENANT*", "*PILOT*", "*POWER_TOOLS*", "*RUNBOOK*", "*LEXICON*",
    "*CAMPSITE*", "*SECURITY*", "*LEGAL*", "*SDLC*", "*KANBAN*", "*JIT*"
]

# Domain 02: Edge Hardware, Nodes & Mesh
PATTERNS_D2 = [
    "SPEC_MODEL_S*", "SPEC_HAILO*", "SPEC_SHEPHERD*", "SPEC_FLEET*", "SPEC_CMDB*",
    "*MODEL_S*", "*HAILO*", "*SHEPHERD*", "*FLEET*", "*CMDB*",
    "*HARDWARE*", "*WIREGUARD*", "*MESH*", "*NODE*", "*PROVISIONING*", "*APPLIANCE*",
    "*BEELINK*", "*JETSON*", "*PI_ZERO*", "*TOPOLOGY*"
]

# Domain 03: Market Intelligence & Horizon
PATTERNS_D3 = [
    "*HORIZON*", "*ALPHA*", "*5_PERCENT*", "*CAPITOL*", "*OHLCV*", "*COLLISION*",
    "*PREDICTION_MARKET*", "*QUANT*", "*SCREENER*", "*ARBITRAGE*", "*EQUITY*"
]

# Domain 04: Advocate Swarms & Creator Verticals
PATTERNS_D4 = [
    "SPEC_FAAS*", "*WARDY*", "*BARF*", "*SAMMY*", "*METSY*", "*WILDSEED*", "*ARKLE*", "*STEARNS*",
    "*FAAS*", "*FANSTACK*", "*ADVOCATE*", "*SWARM*", "*PERSONA*", "*SPORTS*", "*MARD*",
    "*BLUNDERDOME*", "*STATCAST*", "*SKEW*", "*CROSSTALK*", "*FANCAST*", "*FOOTYSTACK*", "*FLORADEX*"
]


def classify_file(fname: str) -> str:
    up = fname.upper()

    for p in PATTERNS_D1:
        if fnmatch.fnmatch(up, p):
            return "01_Governance_and_ITSM"

    for p in PATTERNS_D2:
        if fnmatch.fnmatch(up, p):
            return "02_Edge_Hardware_and_Mesh"

    for p in PATTERNS_D3:
        if fnmatch.fnmatch(up, p):
            return "03_Market_Intelligence"

    for p in PATTERNS_D4:
        if fnmatch.fnmatch(up, p):
            return "04_Advocate_Swarms"

    return "99_Legacy_Archive"


def run_migration():
    print("=" * 80)
    print("🏛️ SOVEREIGN OS: TAXONOMY MIGRATION & SYMLINK BRIDGE ENGINE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # 1. Ensure domain directories exist
    for domain_name, domain_dir in DOMAINS.items():
        os.makedirs(domain_dir, exist_ok=True)
        print(f"✔ Verified domain directory: {domain_dir}")

    # 2. Collect regular files from dna/docs/
    if not os.path.isdir(DOCS_DIR):
        print(f"❌ Error: Docs directory does not exist: {DOCS_DIR}")
        sys.exit(1)

    items = sorted(os.listdir(DOCS_DIR))
    files_to_migrate = []
    skipped_symlinks = []
    skipped_dirs = []

    for item in items:
        item_path = os.path.join(DOCS_DIR, item)
        if os.path.islink(item_path):
            skipped_symlinks.append(item)
        elif os.path.isdir(item_path):
            skipped_dirs.append(item)
        elif os.path.isfile(item_path):
            files_to_migrate.append(item)

    print(f"\nDiscovered: {len(files_to_migrate)} flat files to migrate.")
    print(f"Subdirectories preserved in dna/docs/: {skipped_dirs}")
    if skipped_symlinks:
        print(f"Existing symlinks in dna/docs/ (skipped): {skipped_symlinks}")

    # Load existing manifest if present
    existing_moves = {}
    if os.path.isfile(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for m in data.get("moves", []):
                    existing_moves[m["filename"]] = m
        except Exception as e:
            print(f"⚠️ Warning loading existing manifest: {e}")

    # 3. Classify and execute moves + symlinks
    for fname in files_to_migrate:
        domain = classify_file(fname)
        old_path = os.path.join(DOCS_DIR, fname)
        target_dir = DOMAINS[domain]
        new_path = os.path.join(target_dir, fname)

        # Move file to domain directory if not already there
        if os.path.exists(new_path):
            if os.path.isfile(old_path) and not os.path.islink(old_path):
                os.remove(old_path)
        else:
            shutil.move(old_path, new_path)

        # Generate relative symlink from dna/docs to new location
        rel_target = os.path.relpath(new_path, start=DOCS_DIR)
        if not os.path.islink(old_path):
            os.symlink(rel_target, old_path)

        existing_moves[fname] = {
            "filename": fname,
            "domain": domain,
            "old_path": old_path,
            "new_path": new_path,
            "symlink_target": rel_target
        }

    # Recalculate domain counts from all moves
    domain_counts = {d: 0 for d in DOMAINS}
    all_moves = list(existing_moves.values())
    for m in all_moves:
        d = m.get("domain")
        if d in domain_counts:
            domain_counts[d] += 1

    # 4. Save manifest for verification and rollback
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "total_migrated": len(all_moves),
        "domain_counts": domain_counts,
        "moves": all_moves
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✔ Migration manifest saved to {MANIFEST_PATH}")
    print("\n--- Domain Summary ---")
    for d, c in domain_counts.items():
        print(f"  {d}: {c} files")
    print(f"Total tracked in manifest: {len(all_moves)} files")

    # 5. Sanity check: assert all symlinks resolve
    broken = []
    for m in all_moves:
        p = m["old_path"]
        if not os.path.exists(p):
            broken.append(p)

    if broken:
        print(f"\n❌ ERROR: {len(broken)} broken symlinks detected:")
        for b in broken[:5]:
            print(f"  {b}")
        sys.exit(1)
    else:
        print(f"\n🟢 SUCCESS: All {len(all_moves)} symlinks in {DOCS_DIR} resolve perfectly!")


if __name__ == "__main__":
    run_migration()
