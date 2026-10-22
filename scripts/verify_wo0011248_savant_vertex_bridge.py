#!/home/james/stacklabs/.venv/bin/python3
"""
Verification Script for WO0011248: Savant Query Bridge Vertex AI Gateway & Forensic Entity Evidence
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/verify_wo0011248_savant_vertex_bridge.py
"""
import json
import os
import pathlib
import subprocess
import sys
import time

REPO_ROOT = pathlib.Path("/home/james/stacklabs")
SERVICE_DIR = REPO_ROOT / "vfs" / "services" / "savant_query_bridge"
RUNNER_SCRIPT = SERVICE_DIR / "run.py"
VERIFY_SCRIPT = SERVICE_DIR / "verify.sh"
RECEIPT_FILE = SERVICE_DIR / ".state" / "last_query_receipt.json"
PENDING_FILE = SERVICE_DIR / ".state" / "pending_query.json"
DIVEBAR_CTL = REPO_ROOT / "scripts" / "vfs_divebar.py"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python3"


def test_syntax_and_compilation():
    print("🔍 [TEST 1/4] Checking python compilation for savant_query_bridge/run.py...")
    res = subprocess.run([str(PYTHON_BIN), "-m", "py_compile", str(RUNNER_SCRIPT)], capture_output=True, text=True)
    assert res.returncode == 0, f"Compilation failed: {res.stderr}"
    print("  ✔ Compilation clean.")


def test_entity_evidence_retrieval():
    print("🔍 [TEST 2/4] Testing high-entropy entity evidence retrieval...")
    sys.path.insert(0, str(SERVICE_DIR))
    from run import retrieve_wiretap_evidence
    evidence = retrieve_wiretap_evidence(["Harbaugh", "Skattebo", "Saints"])
    assert len(evidence) > 0, "Failed to retrieve evidence for Skattebo inquiry"
    has_skat = any("skat" in e["message"].lower() for e in evidence)
    assert has_skat, f"Retrieved evidence did not prioritize Skattebo: {evidence}"
    print(f"  ✔ Retrieved {len(evidence)} evidence rows prioritizing Skattebo correctly.")


def test_staged_dispatch_via_divebar():
    print("🔍 [TEST 3/4] Staging forensic question via vfs_divebar.py...")
    question = "Why did Harbaugh give Skattebo zero carries against the Saints?"
    cmd = [str(PYTHON_BIN), str(DIVEBAR_CTL), "query", question, "--advocate", "barf"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Dive bar query dispatch failed: {res.stderr}"
    assert PENDING_FILE.exists(), "pending_query.json was not staged"
    print("  ✔ Query staged in .state/pending_query.json.")

    print("🔍 [TEST 4/4] Executing savant_query_bridge/run.py and asserting 3-tier gateway...")
    res = subprocess.run([str(PYTHON_BIN), str(RUNNER_SCRIPT)], capture_output=True, text=True)
    assert res.returncode == 0, f"Execution failed: {res.stderr}\nStdout: {res.stdout}"
    assert not PENDING_FILE.exists(), "pending_query.json was not cleared"
    assert RECEIPT_FILE.exists(), "Receipt file was not generated"

    receipt = json.loads(RECEIPT_FILE.read_text(encoding="utf-8"))
    assert receipt.get("advocate") == "barf", f"Unexpected advocate: {receipt}"
    assert receipt.get("evidence_rows", 0) > 0, f"No evidence rows recorded in receipt: {receipt}"
    provider = receipt.get("provider", "")
    assert provider in ["vertex_ai_stacklabs_foundry", "colab_sovereign_slm", "offline_matrix_local"], f"Invalid provider: {provider}"
    assert len(receipt.get("response", "")) > 10, "Response is too short"
    print(f"  ✔ Dispatch successful via provider: {provider}")
    print(f"  🎙️ Barf Verdict: \"{receipt.get('response')}\"")


def main():
    print("========================================================================")
    print("🧪 RUNNING WO0011248 SAVANT QUERY BRIDGE VERTEX AI VERIFICATION HARNESS")
    print("========================================================================")
    test_syntax_and_compilation()
    test_entity_evidence_retrieval()
    test_staged_dispatch_via_divebar()
    print("========================================================================")
    print("🟢 SUCCESS: WO0011248 Verified clean on Clio local host.")
    print("========================================================================")


if __name__ == "__main__":
    main()
