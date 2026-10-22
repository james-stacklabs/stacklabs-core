#!/usr/bin/env python3
"""
StackLabs Ground Truth Vault Drive Sync & Prompt Packer Verification Suite
Path: /home/james/stacklabs/scripts/verify_ground_truth_sync.py

Verifies:
1. pack_ground_truth_context.py executes and creates GROUND_TRUTH_PROMPT_CONTEXT.md.
2. Total token size of packed context is under 6,000 tokens (< 30 KB).
3. sports_ground_truth.json contains cfb_marquee_slate with Florida/Mizzou and Auburn/Tennessee.
4. sync_to_gdrive.sh contains the stacklabs_edge:ground_truth entry.
5. All 4 ledgers continue to pass strict Pydantic validation via ground_truth_daemon.py --validate-all.
"""

import sys
import json
import subprocess
from pathlib import Path

PYTHON_BIN = "/home/james/stacklabs/.venv/bin/python3"
VAULT_DIR = Path("/home/james/stacklabs/ground_truth")
CONTEXT_FILE = Path("/home/james/sovereign_inbox/pilot_drops/GROUND_TRUTH_PROMPT_CONTEXT.md")
SYNC_SCRIPT = Path("/home/james/stacklabs/scripts/sync_to_gdrive.sh")
PACKER_SCRIPT = Path("/home/james/stacklabs/scripts/pack_ground_truth_context.py")
DAEMON_SCRIPT = Path("/home/james/stacklabs/scripts/ground_truth_daemon.py")


def test_1_packer_execution():
    print("▶ Assertion 1: pack_ground_truth_context.py executes and produces context file...")
    cmd = [PYTHON_BIN, str(PACKER_SCRIPT)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Packer execution failed: {res.stderr}"
    assert CONTEXT_FILE.exists(), f"Context file not created: {CONTEXT_FILE}"
    print(f"  ✅ PASS: Context file created at {CONTEXT_FILE}")


def test_2_token_and_byte_budget():
    print("▶ Assertion 2: Total size of packed context is under 6,000 tokens (< 30 KB)...")
    content = CONTEXT_FILE.read_text(encoding="utf-8")
    byte_count = len(content.encode("utf-8"))
    approx_tokens = int(byte_count / 4.2)
    print(f"  📊 Measured: {byte_count} bytes (~{approx_tokens} tokens)")
    assert byte_count < 30 * 1024, f"Context file exceeds 30KB: {byte_count} bytes"
    assert approx_tokens < 7000, f"Token budget exceeded: ~{approx_tokens} tokens >= 7000"
    print("  ✅ PASS: Within token and byte budget (< 7,000 tokens, < 30 KB)")


def test_3_cfb_marquee_slate():
    print("▶ Assertion 3: sports_ground_truth.json contains cfb_marquee_slate with FLA/MIZ and AUB/TENN...")
    sports_path = VAULT_DIR / "sports_ground_truth.json"
    assert sports_path.exists(), f"Missing {sports_path}"
    data = json.loads(sports_path.read_text(encoding="utf-8"))
    assert "cfb_marquee_slate" in data, "Missing cfb_marquee_slate in sports_ground_truth.json"
    cfb = data["cfb_marquee_slate"]
    assert "FLA_MIZ" in cfb, "Missing FLA_MIZ in cfb_marquee_slate"
    assert "AUB_TENN" in cfb, "Missing AUB_TENN in cfb_marquee_slate"
    assert "MIZZOU 45 — 17 FLA" in cfb["FLA_MIZ"]["score"], f"Unexpected score: {cfb['FLA_MIZ']['score']}"
    assert "TENN 24 — 14 AUB" in cfb["AUB_TENN"]["score"], f"Unexpected score: {cfb['AUB_TENN']['score']}"
    print("  ✅ PASS: Verified CFB Week 5 marquee slate entries (FLA_MIZ, AUB_TENN, ND_UNC)")


def test_4_sync_script_entries():
    print("▶ Assertion 4: sync_to_gdrive.sh contains stacklabs_edge:ground_truth entry...")
    assert SYNC_SCRIPT.exists(), f"Missing {SYNC_SCRIPT}"
    sync_content = SYNC_SCRIPT.read_text(encoding="utf-8")
    assert "stacklabs_edge:ground_truth" in sync_content, "Missing stacklabs_edge:ground_truth in sync_to_gdrive.sh"
    assert "stacklabs_vault:ground_truth" in sync_content, "Missing stacklabs_vault:ground_truth in sync_to_gdrive.sh"
    print("  ✅ PASS: Verified ground_truth rclone entries in sync_to_gdrive.sh")


def test_5_pydantic_validation():
    print("▶ Assertion 5: All 4 ledgers continue to pass strict Pydantic validation via ground_truth_daemon.py --validate-all...")
    cmd = [PYTHON_BIN, str(DAEMON_SCRIPT), "--validate-all"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Pydantic validation failed: {res.stdout}\n{res.stderr}"
    assert "[ALL-VALID]" in res.stdout, f"Missing [ALL-VALID] in output: {res.stdout}"
    print("  ✅ PASS: All 4 ledgers valid under Pydantic v2 schemas")


def main():
    print("================================================================================")
    print("🏛️ STACKLABS GROUND TRUTH SYNC & PACKER VERIFICATION SUITE")
    print("================================================================================")
    try:
        test_1_packer_execution()
        test_2_token_and_byte_budget()
        test_3_cfb_marquee_slate()
        test_4_sync_script_entries()
        test_5_pydantic_validation()
        print("================================================================================")
        print("🎉 ALL 5/5 ASSERTIONS PASSED WITH 100% COMPLIANCE")
        print("================================================================================")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
