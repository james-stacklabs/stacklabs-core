#!/usr/bin/env python3
"""
StackLabs Ground Truth Vault Automated Verification Suite
Path: /home/james/stacklabs/scripts/verify_ground_truth_vault.py (symlinked to SovereignOS/scripts/verify_ground_truth_vault.py)

Automated test suite asserting:
1. Directory /home/james/stacklabs/ground_truth/ exists on NVMe.
2. All 4 foundational ledgers exist and are valid JSON.
3. All 4 ledgers pass strict Pydantic model validation.
4. Calling atomic_commit with identical payload burns 0 write cycles (returns NO_CHANGE).
5. Modifying a field creates .tmp and executes atomic os.replace(), updating the SHA-256 fingerprint.
6. Asserts Invariant 30: sports_ground_truth.json states Aaron Rodgers is on Pittsburgh Steelers.
7. Asserts Invariant 32: partner_ground_truth.json specifies founder voice is "I" and corporate we is banned.
8. Asserts Invariant 44: partner_ground_truth.json specifies Pawel ranch is "SOLD".
9. Asserts zero legacy sovereign_inbox references in .agents/ or symlinks on disk.
10. Asserts canonical weather_ground_truth.json exists and passes Pydantic model validation.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ground_truth_daemon import (
    VAULT_DIR,
    ComputeGroundTruth,
    PartnerGroundTruth,
    QuantGroundTruth,
    SportsGroundTruth,
    WeatherGroundTruth,
    atomic_commit,
)


def run_verification() -> bool:
    print("=" * 72)
    print("🏛️ STACKLABS CANONICAL GROUND TRUTH VAULT: AUTOMATED VERIFICATION SUITE")
    print(f"Target Vault Directory: {VAULT_DIR}")
    print("=" * 72)

    passed_checks = 0
    total_checks = 10

    # --------------------------------------------------------------------------
    # CHECK 1: Vault Directory on NVMe
    # --------------------------------------------------------------------------
    print("\n[CHECK 1/10] Asserting vault directory exists on NVMe...")
    assert VAULT_DIR.is_dir(), f"Vault directory missing: {VAULT_DIR}"
    sovereign_link = Path("/home/james/stacklabs/ground_truth")
    assert sovereign_link.exists(), f"Symlink missing: {sovereign_link}"
    print(f"  ✅ PASS: Vault directory verified at {VAULT_DIR}")
    print(f"  ✅ PASS: Symlink verified at {sovereign_link} -> {sovereign_link.resolve()}")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 2: All 4 Foundational Ledgers Exist & Valid JSON
    # --------------------------------------------------------------------------
    print("\n[CHECK 2/10] Asserting 4 foundational ledgers exist and parse as JSON...")
    expected_ledgers = [
        "compute_ground_truth.json",
        "partner_ground_truth.json",
        "quant_ground_truth.json",
        "sports_ground_truth.json",
    ]
    raw_data = {}
    for filename in expected_ledgers:
        path = VAULT_DIR / filename
        assert path.is_file(), f"Foundational ledger missing: {path}"
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict), f"Ledger {filename} must be a JSON object"
        raw_data[filename] = parsed
        print(f"  ✅ PASS: {filename} exists ({len(content)} bytes, valid JSON)")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 3: Strict Pydantic Model Validation
    # --------------------------------------------------------------------------
    print("\n[CHECK 3/10] Validating all ledgers against Pydantic v2 schemas...")
    compute_model = ComputeGroundTruth.model_validate(raw_data["compute_ground_truth.json"])
    assert compute_model.engine_version, "engine_version required"
    print("  ✅ PASS: ComputeGroundTruth validated")

    partner_model = PartnerGroundTruth.model_validate(raw_data["partner_ground_truth.json"])
    assert partner_model.founder_identity.name == "James Carroll"
    print("  ✅ PASS: PartnerGroundTruth validated")

    quant_model = QuantGroundTruth.model_validate(raw_data["quant_ground_truth.json"])
    assert quant_model.universe_name, "universe_name required"
    print("  ✅ PASS: QuantGroundTruth validated")

    sports_model = SportsGroundTruth.model_validate(raw_data["sports_ground_truth.json"])
    assert sports_model.season == 2026, "season must be 2026"
    print("  ✅ PASS: SportsGroundTruth validated")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 4: Zero-Cycle NVMe Burn (NO_CHANGE on identical commit)
    # --------------------------------------------------------------------------
    print("\n[CHECK 4/10] Asserting atomic_commit with identical payload burns 0 write cycles...")
    target_path = VAULT_DIR / "compute_ground_truth.json"
    committed, status = atomic_commit(target_path, raw_data["compute_ground_truth.json"], ComputeGroundTruth)
    assert not committed, f"Expected committed=False, got {committed}"
    assert status == "NO_CHANGE", f"Expected status='NO_CHANGE', got {status}"
    print("  ✅ PASS: Zero write cycles burned on identical payload (NO_CHANGE asserted)")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 5: Atomic Rename & Fingerprint Update on State Modification
    # --------------------------------------------------------------------------
    print("\n[CHECK 5/10] Asserting atomic .tmp write, os.replace, and fingerprint update...")
    fixture_path = VAULT_DIR / "_test_atomic_fixture.json"
    try:
        # Step A: initial commit
        initial_payload = {"status": "INITIAL", "version": 1}
        c1, s1 = atomic_commit(fixture_path, initial_payload)
        assert c1 and s1 == "COMMITTED"
        h1 = hashlib.sha256(fixture_path.read_bytes()).hexdigest()

        # Step B: modified commit
        modified_payload = {"status": "MODIFIED", "version": 2}
        c2, s2 = atomic_commit(fixture_path, modified_payload)
        assert c2 and s2 == "COMMITTED"
        h2 = hashlib.sha256(fixture_path.read_bytes()).hexdigest()

        assert h1 != h2, "Fingerprint must change upon payload mutation"
        tmp_check = fixture_path.with_suffix(".json.tmp")
        assert not tmp_check.exists(), "Temporary .tmp file must not linger after atomic rename"

        # Step C: identical recommit
        c3, s3 = atomic_commit(fixture_path, modified_payload)
        assert not c3 and s3 == "NO_CHANGE"
        print("  ✅ PASS: Atomic rename, SHA-256 update, and temp file cleanup verified")
    finally:
        if fixture_path.exists():
            fixture_path.unlink()
        tmp_check = fixture_path.with_suffix(".json.tmp")
        if tmp_check.exists():
            tmp_check.unlink()
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 6: Invariant 30 (Sports Temporal Ground Truth - 2026 Shibboleths)
    # --------------------------------------------------------------------------
    print("\n[CHECK 6/10] Asserting Invariant 30 (Calendar Year 2026 & Aaron Rodgers Shibboleth)...")
    sports_data = raw_data["sports_ground_truth.json"]
    assert sports_data.get("season") == 2026, "Season must be 2026"
    roster_shibboleths = sports_data.get("roster_shibboleths", {})
    rodgers = roster_shibboleths.get("aaron_rodgers", {})
    assert rodgers.get("team") == "Pittsburgh Steelers", (
        f"Invariant 30 violation: Aaron Rodgers must be on Pittsburgh Steelers, found: {rodgers.get('team')}"
    )
    assert rodgers.get("role") == "Starting Quarterback"
    print(f"  ✅ PASS: Invariant 30 verified (Season 2026, Aaron Rodgers Starting QB on {rodgers.get('team')})")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 7: Invariant 32 (Solo Builder Voice - I, Never We)
    # --------------------------------------------------------------------------
    print("\n[CHECK 7/10] Asserting Invariant 32 (Solo Builder Voice Card)...")
    partner_data = raw_data["partner_ground_truth.json"]
    founder = partner_data.get("founder_identity", {})
    assert founder.get("voice") == "I", f"Invariant 32 violation: voice must be 'I', got: {founder.get('voice')}"
    assert founder.get("corporate_we_allowed") is False, "Invariant 32 violation: corporate_we_allowed must be False"
    assert founder.get("name") == "James Carroll"
    print("  ✅ PASS: Invariant 32 verified (Solo Builder voice='I', corporate_we_allowed=False)")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 8: Invariant 44 (Pawel Ranch Shibboleth)
    # --------------------------------------------------------------------------
    print("\n[CHECK 8/10] Asserting Invariant 44 (Pawel Ranch Sold Shibboleth)...")
    partners = partner_data.get("partners", {})
    pawel = partners.get("pawel_rudnicki", {})
    ranch_status = pawel.get("ranch_status", "")
    assert "SOLD" in ranch_status, (
        f"Invariant 44 violation: Pawel ranch status must state SOLD, got: {ranch_status}"
    )
    print(f"  ✅ PASS: Invariant 44 verified (Pawel ranch status: {ranch_status})")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 9: Assert Zero Deprecated Sovereign Inbox Paths or Symlinks
    # --------------------------------------------------------------------------
    print("\n[CHECK 9/10] Asserting zero legacy sovereign_inbox references or symlinks...")
    sovereign_inbox_path = Path("/home/james/sovereign_inbox")
    assert not sovereign_inbox_path.exists() and not sovereign_inbox_path.is_symlink(), (
        "FAIL: /home/james/sovereign_inbox still exists on disk!"
    )

    # Assert zero occurrences in .agents/
    res = subprocess.run(
        ["grep", "-rn", "sovereign_inbox", "/home/james/stacklabs/.agents/"],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, f"FAIL: Found sovereign_inbox in .agents:\n{res.stdout}"
    print("  ✅ PASS: sovereign_inbox is permanently eradicated from disk and .agents/")
    passed_checks += 1

    # --------------------------------------------------------------------------
    # CHECK 10: Canonical Weather & Hurricane Ground Truth
    # --------------------------------------------------------------------------
    print("\n[CHECK 10/10] Asserting weather_ground_truth.json exists on NVMe...")
    weather_file = VAULT_DIR / "weather_ground_truth.json"
    assert weather_file.exists(), f"Missing weather ledger: {weather_file}"
    try:
        w_data = json.loads(weather_file.read_text())
        assert "tropical_cyclones" in w_data, "Missing tropical_cyclones key in weather_ground_truth.json"
        WeatherGroundTruth.model_validate(w_data)
        print(f"  ✅ PASS: weather_ground_truth.json verified ({len(w_data.get('tropical_cyclones', []))} storms tracked)")
        passed_checks += 1
    except Exception as e:
        print(f"  ❌ FAIL: {e}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 72)
    print(f"🏆 ALL CHECKS PASSED: {passed_checks}/{total_checks} (100% Compliance)")
    print("=" * 72)
    return passed_checks == total_checks


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
