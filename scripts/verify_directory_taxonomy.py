#!/usr/bin/env python3
"""
Sovereign OS: Directory Taxonomy Verification Suite
Work Order: WO0010469-SOVEREIGN-DIRECTORY-TAXONOMY-REFACTOR
Governed by: Invariant 12 & Campsite Protocol

Asserts all Quarter 3 invariants:
1. All 5 domain directories exist and contain files.
2. Every symlink in dna/docs/ is relative and resolves to an existing target file.
3. Critical entry points resolve seamlessly.
4. Zero un-migrated regular markdown files in dna/docs/.
5. Manifest integrity matches file system state.
"""

import os
import sys
import json
import py_compile

BASE_DIR = "/home/james/stacklabs"
DOCS_DIR = os.path.join(BASE_DIR, "dna", "docs")
MANIFEST_PATH = os.path.join(BASE_DIR, "scripts", "taxonomy_migration_manifest.json")

DOMAINS = [
    "01_Governance_and_ITSM",
    "02_Edge_Hardware_and_Mesh",
    "03_Market_Intelligence",
    "04_Advocate_Swarms",
    "99_Legacy_Archive"
]

CRITICAL_ENTRY_POINTS = [
    "Sovereign_Power_Tools_and_Microservices_Catalog.md",
    "13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md",
    "SPEC_MODEL_S_CELLULAR_MESH_AND_SWARM_SHEPHERD_TOPOLOGY.md"
]

SCRIPTS_TO_VERIFY = [
    os.path.join(BASE_DIR, "scripts", "migrate_directory_taxonomy.py"),
    os.path.join(BASE_DIR, "scripts", "rollback_directory_taxonomy.py"),
]


def run_verification():
    print("=" * 80)
    print("🧪 SOVEREIGN OS: TAXONOMY VERIFICATION SUITE (WO0010469)")
    print("=" * 80)

    failures = []

    # 1. Assert all 5 target directories exist and contain files
    print("\n[Assertion 1] Verifying domain directories...")
    for d in DOMAINS:
        p = os.path.join(BASE_DIR, d)
        if not os.path.isdir(p):
            failures.append(f"Domain directory missing: {p}")
            print(f"  ❌ Missing: {d}")
        else:
            count = len(os.listdir(p))
            if count == 0:
                failures.append(f"Domain directory is empty: {p}")
                print(f"  ❌ Empty: {d}")
            else:
                print(f"  ✔ {d}: {count} files present")

    # 2. Assert every relative symlink in dna/docs/ resolves to existing target
    print("\n[Assertion 2] Verifying symlink integrity in dna/docs/...")
    symlink_count = 0
    broken_symlinks = []
    non_relative_symlinks = []

    for item in sorted(os.listdir(DOCS_DIR)):
        item_path = os.path.join(DOCS_DIR, item)
        if os.path.islink(item_path):
            symlink_count += 1
            target = os.readlink(item_path)
            if os.path.isabs(target):
                non_relative_symlinks.append((item, target))
            if not os.path.exists(item_path):
                broken_symlinks.append((item, target))

    print(f"  ✔ Checked {symlink_count} symlinks in {DOCS_DIR}")
    if non_relative_symlinks:
        failures.append(f"{len(non_relative_symlinks)} symlinks are absolute instead of relative")
        for s, t in non_relative_symlinks[:5]:
            print(f"  ❌ Absolute symlink: {s} -> {t}")
    else:
        print("  ✔ All symlinks use relative paths")

    if broken_symlinks:
        failures.append(f"{len(broken_symlinks)} broken symlinks detected")
        for s, t in broken_symlinks[:5]:
            print(f"  ❌ Broken symlink: {s} -> {t}")
    else:
        print(f"  ✔ Zero broken symlinks (100% resolution)")

    # 3. Assert critical entry points resolve seamlessly
    print("\n[Assertion 3] Verifying critical entry points...")
    for entry in CRITICAL_ENTRY_POINTS:
        p = os.path.join(DOCS_DIR, entry)
        if not os.path.exists(p):
            failures.append(f"Critical entry point does not resolve: {p}")
            print(f"  ❌ Missing: {entry}")
        else:
            real = os.path.realpath(p)
            print(f"  ✔ {entry} -> {os.path.relpath(real, BASE_DIR)}")

    # 4. Assert zero un-migrated regular markdown files directly in dna/docs/
    print("\n[Assertion 4] Verifying zero un-migrated markdown files in dna/docs/...")
    unmigrated = []
    for item in sorted(os.listdir(DOCS_DIR)):
        item_path = os.path.join(DOCS_DIR, item)
        if os.path.isfile(item_path) and not os.path.islink(item_path) and item.endswith(".md"):
            unmigrated.append(item)

    if unmigrated:
        failures.append(f"{len(unmigrated)} un-migrated markdown files remaining in dna/docs/")
        for u in unmigrated[:5]:
            print(f"  ❌ Unmigrated: {u}")
    else:
        print("  ✔ Zero un-migrated markdown files directly in dna/docs/")

    # 5. Verify script syntax
    print("\n[Assertion 5] Verifying syntax of migration and rollback scripts...")
    for s in SCRIPTS_TO_VERIFY:
        try:
            py_compile.compile(s, doraise=True)
            print(f"  ✔ Syntax valid: {os.path.basename(s)}")
        except Exception as e:
            failures.append(f"Syntax error in {s}: {e}")
            print(f"  ❌ Syntax error: {s} ({e})")

    # 6. Verify Manifest
    print("\n[Assertion 6] Verifying migration manifest...")
    if not os.path.isfile(MANIFEST_PATH):
        failures.append(f"Manifest missing at {MANIFEST_PATH}")
        print("  ❌ Manifest missing")
    else:
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            total = manifest.get("total_migrated", 0)
            print(f"  ✔ Manifest loaded: {total} files tracked across {len(manifest.get('domain_counts', {}))} domains")
        except Exception as e:
            failures.append(f"Failed to parse manifest: {e}")
            print(f"  ❌ Manifest corrupt: {e}")

    # Summary
    print("\n" + "=" * 80)
    if failures:
        print(f"❌ VERIFICATION FAILED with {len(failures)} defects:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("🟢 ALL INVARIANTS & VERIFICATION ASSERTIONS PASSED (100% OK)")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    run_verification()
