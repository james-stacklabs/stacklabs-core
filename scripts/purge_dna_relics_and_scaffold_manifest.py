#!/usr/bin/env python3
"""
=============================================================================
MODULE: purge_dna_relics_and_scaffold_manifest.py
ROLE: Evacuate dead SQLite backup dumps and legacy exports from dna/ to archive
RUNNER: Aggie (agy) on Clio Metal Forge via .venv/bin/python3
=============================================================================
TABLE OF CONTENTS & SYMBOL MAP:
  - L0025-L0045: Configuration & Target Paths
  - L0047-L0085: Backup Evacuation Handler (moves dead .bak files to sovereign_archive)
  - L0087-L0115: Ghost Directory & Legacy Export Evacuation
  - L0117-L0165: Scaffold Canonical dna/README.md Manifest
  - L0167-L0200: Main Execution Routine & Verification Receipt
=============================================================================
"""

import os
import shutil
import sys
from pathlib import Path

DNA_DIR = Path("/home/james/stacklabs/dna")
ARCHIVE_BASE = Path("/home/james/sovereign_archive")
BACKUP_ARCHIVE = ARCHIVE_BASE / "dna_dead_backups"
NOTEBOOK_ARCHIVE = ARCHIVE_BASE / "notebook_lm_legacy"

# Exact dead backup patterns to evacuate (leaving sovereign_now.db intact)
DEAD_DB_PATTERNS = [
    "sovereign_now.db.bak",
    "sovereign_now.db.p1_bak_20260829_063042",
    "sovereign_now.db.p1_bak_20260829_064952",
    "sovereign_now.db.p1_torn_final_bak",
    "sovereign_now.db.pre_repair_",
    "sovereign_now.db.pre_repair_20260828",
    "sovereign_now.db.pre_repair_20260828-shm",
    "sovereign_now.db.pre_repair_20260828-wal",
]

def evacuate_dead_databases() -> int:
    """Move dead SQLite repair backups to sovereign_archive."""
    BACKUP_ARCHIVE.mkdir(parents=True, exist_ok=True)
    moved_count = 0
    bytes_freed = 0

    for filename in DEAD_DB_PATTERNS:
        source_path = DNA_DIR / filename
        if source_path.exists():
            dest_path = BACKUP_ARCHIVE / filename
            size = source_path.stat().st_size
            print(f"[EVACUATE] Moving {filename} ({size / (1024*1024):.2f} MB) -> {dest_path}")
            shutil.move(str(source_path), str(dest_path))
            moved_count += 1
            bytes_freed += size

    print(f"[EVACUATE COMPLETE] Moved {moved_count} dead database files. Freed {bytes_freed / (1024*1024*1024):.2f} GB from dna/.")
    return moved_count

def evacuate_legacy_exports() -> None:
    """Move legacy notebook_lm_exports directory to sovereign_archive."""
    legacy_dir = DNA_DIR / "notebook_lm_exports"
    if legacy_dir.exists():
        NOTEBOOK_ARCHIVE.mkdir(parents=True, exist_ok=True)
        dest = NOTEBOOK_ARCHIVE / "notebook_lm_exports"
        if dest.exists():
            shutil.rmtree(str(dest))
        print(f"[EVACUATE] Moving notebook_lm_exports -> {dest}")
        shutil.move(str(legacy_dir), str(dest))

def purge_ghost_directories() -> None:
    """Remove empty ghost directories inside dna/."""
    ghost_targets = [
        DNA_DIR / "agents" / "FERRIS" / "payloads",
        DNA_DIR / "agents" / "FERRIS",
        DNA_DIR / "agents",
        DNA_DIR / "dropzone",
    ]
    for target in ghost_targets:
        if target.exists() and target.is_dir():
            try:
                # Only remove if empty
                if not any(target.iterdir()):
                    print(f"[PURGE GHOST] Removing empty directory: {target}")
                    target.rmdir()
                else:
                    print(f"[SKIP] Directory not empty: {target}")
            except Exception as e:
                print(f"[WARN] Could not remove {target}: {e}")

def scaffold_dna_manifest() -> Path:
    """Write canonical README.md manifest inside dna/."""
    manifest_path = DNA_DIR / "README.md"
    content = """---
status: ACTIVE
domain: STACKLABS_CORE_DATABASE
last_verified: 2026-10-04
canonical_source: file:///home/james/stacklabs/dna/README.md
summary: "Canonical SQLite operational database and schema migration ledger for StackLabs platform on Clio."
agent_routing: "If looking for active database state, connect to sovereign_now.db. If writing schema migrations, stage them to migrations/. Dead backup dumps have been quarantined to /home/james/sovereign_archive/dna_dead_backups/."
---

# 🧬 STACKLABS PLATFORM: CANONICAL DATA REPOSITORY (`dna/`)

> **Directory Classification**: Tier 1 Core Data Plane  
> **Host Node**: Clio Metal Forge (`clio` / Beelink SER Mini PC)  
> **Primary Database**: `sovereign_now.db` (SQLite 3.45+ with WAL mode enabled)  
> **Schema Migrations**: `migrations/` (Sequential numbered `.sql` migrations)

---

## 🛑 AGENT ROUTING & ACCESS RULES

1. **Active Database Invariant**:
   - `sovereign_now.db` is the live operational ledger on Clio bare metal.
   - Do NOT attempt to read `.bak` or `pre_repair` files—they have been archived to cold storage.
   - Read access should be handled via the FastAPI REST API (`http://127.0.0.1:8095/api/`) or targeted SQLite queries with short connection timeouts.
2. **Schema Alterations**:
   - Direct manual `ALTER TABLE` execution in live shell is strictly prohibited.
   - All schema changes must be codified as sequential migration files in `migrations/` and executed via the canonical migration runner.
3. **Dead Asset Prohibition**:
   - `dna/` contains strictly operational data assets. Do not store scratch scripts, markdown notes, or temporary exports here.
"""
    manifest_path.write_text(content, encoding="utf-8")
    print(f"[MANIFEST] Wrote canonical manifest: {manifest_path}")
    return manifest_path

def main() -> int:
    print("[INIT] Starting DNA relic purge on Clio metal...")
    if not DNA_DIR.exists():
        print(f"[ERROR] Target directory does not exist: {DNA_DIR}")
        return 1

    # Verify live DB exists before any mutations
    live_db = DNA_DIR / "sovereign_now.db"
    if not live_db.exists():
        print(f"[FATAL] Live database not found at {live_db}. Halting to prevent data loss.")
        return 1

    evacuate_dead_databases()
    evacuate_legacy_exports()
    purge_ghost_directories()
    scaffold_dna_manifest()

    print("[SUCCESS] DNA repository sanitized. Live database preserved.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
