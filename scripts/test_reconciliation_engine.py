#!/home/james/stacklabs/.venv/bin/python3
"""
Test Suite: Bare-Metal CMDB Reconciliation Engine
Path: /home/james/stacklabs/scripts/test_reconciliation_engine.py
Author: James Carroll (Lead Systems Architect, StackLabs LLC)
Governed by: Invariant 15 (Two-Call Verification), Invariant 35 (Canonical .venv)

Verifies:
1. Identification Rule Enforced (Null PK rejected)
2. Precedence Rules (Level 1 Authority overwrites Level 3 Chatter; Level 3 rejected against Level 1)
3. Two-Call Verification (Write then Read-Back SHA256 integrity match)
4. Memory Block NVMe Projection
"""

import sys
import json
import tempfile
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from services.reconciliation_engine import ReconciliationEngine, PRECEDENCE_LEVELS


def run_tests():
    print("=" * 70)
    print("🧪 RUNNING BARE-METAL CMDB RECONCILIATION ENGINE TEST SUITE")
    print("=" * 70)

    # Use isolated test database
    temp_dir = tempfile.TemporaryDirectory()
    test_db = Path(temp_dir.name) / "test_golden.db"
    test_proj = Path(temp_dir.name) / "test_projection.json"
    engine = ReconciliationEngine(db_path=test_db)

    # TEST 1: Identification Rule Enforced
    print("\n[TEST 1] Identification Rule (Reject Empty Event PK)...")
    try:
        engine.stage_discovery(
            event_pk="",
            domain="TEST",
            source_name="Malformed_Ingress",
            source_tier="BLEACHER_NOISE",
            payload={"data": "invalid"}
        )
        print("❌ FAIL: Empty event_pk was accepted!")
        sys.exit(1)
    except ValueError as e:
        print(f"✅ PASS: Blocked unverified entropy: {e}")

    # TEST 2: Precedence Conflict Resolution
    print("\n[TEST 2] Precedence Rules (Level 1 Authority vs Level 3 Chatter)...")
    event_pk = "TEST_SEC_EDGAR_00010914"

    # Stage Level 3 Chatter (Weight 20)
    engine.stage_discovery(
        event_pk=event_pk,
        domain="FINANCE_SEC",
        source_name="Social_Sentiment",
        source_tier="BLEACHER_NOISE",
        payload={"net_income": "$100M", "status": "RUMOR"}
    )
    r1 = engine.reconcile_event(event_pk)
    assert r1["winning_weight"] == 20, f"Expected weight 20, got {r1['winning_weight']}"
    assert r1["verification"]["verified"] is True, "Verification failed for step 1"

    # Stage Level 1 Metal Authority (Weight 100)
    engine.stage_discovery(
        event_pk=event_pk,
        domain="FINANCE_SEC",
        source_name="SEC_EDGAR_10Q_WIRE",
        source_tier="AUTHORITATIVE_METAL",
        payload={"net_income": "$42.5M", "status": "FILED_AND_CONFIRMED", "cik": "000184920"}
    )
    r2 = engine.reconcile_event(event_pk)
    assert r2["winning_weight"] == 100, f"Expected weight 100, got {r2['winning_weight']}"
    assert r2["winning_source"] == "SEC_EDGAR_10Q_WIRE"

    # Verify attributes were updated correctly
    verify_r2 = engine.two_call_verify(event_pk)
    with engine._get_connection() as conn:
        row = conn.execute("SELECT attributes_json FROM golden_record WHERE event_pk = ?;", (event_pk,)).fetchone()
        attrs = json.loads(row["attributes_json"])
        assert attrs["net_income"] == "$42.5M", f"Expected $42.5M, got {attrs['net_income']}"
        assert attrs["status"] == "FILED_AND_CONFIRMED"
    print("✅ PASS: Level 1 Metal Authority successfully overrode Level 3 Chatter.")

    # Stage Contradictory Level 3 Chatter (Weight 20) post-Level 1
    engine.stage_discovery(
        event_pk=event_pk,
        domain="FINANCE_SEC",
        source_name="Discord_Whisper_Network",
        source_tier="BLEACHER_NOISE",
        payload={"net_income": "$999B_FAKE"}
    )
    r3 = engine.reconcile_event(event_pk)
    assert r3["winning_weight"] == 100, "Corrupt chatter erroneously overwrote Level 1 Golden Record!"
    verify_r3 = engine.two_call_verify(event_pk)
    with engine._get_connection() as conn:
        row = conn.execute("SELECT attributes_json FROM golden_record WHERE event_pk = ?;", (event_pk,)).fetchone()
        attrs = json.loads(row["attributes_json"])
        assert attrs["net_income"] == "$42.5M", "Golden record attributes corrupted by inferior source!"
    print("✅ PASS: Contradictory low-precedence chatter cleanly rejected by Reality Gate.")

    # TEST 3: Two-Call Verification Protocol Integrity
    print("\n[TEST 3] Two-Call Verification Protocol...")
    v_receipt = engine.two_call_verify(event_pk)
    assert v_receipt["verified"] is True
    assert len(v_receipt["sha256_hash"]) == 64
    assert v_receipt["sha256_hash"] == v_receipt["recomputed_hash"]
    print(f"✅ PASS: Cryptographic receipt verified: {v_receipt['sha256_hash'][:16]}...")

    # TEST 4: NVMe Memory Block Projection
    print("\n[TEST 4] Dynamic Memory Block Projection...")
    proj = engine.project_memory_block(destination=test_proj)
    assert test_proj.exists(), "Projection file does not exist on disk!"
    with open(test_proj, "r", encoding="utf-8") as f:
        proj_data = json.load(f)
    assert event_pk in proj_data["records"], "Event PK missing from projected memory block!"
    assert proj_data["records"][event_pk]["attributes"]["net_income"] == "$42.5M"
    print(f"✅ PASS: Memory block projected cleanly ({proj['bytes_written']} bytes).")

    temp_dir.cleanup()
    print("\n" + "=" * 70)
    print("🏆 ALL 4 CMDB RECONCILIATION ENGINE TEST GATES PASSED (4/4 PASS)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
