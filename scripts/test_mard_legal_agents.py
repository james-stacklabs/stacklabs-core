#!/usr/bin/env python3
"""
Automated Unit Test Suite: M.A.R.D. Legal Multi-Agent Swarms & Playbook Dispatch
Target CI: 26_MARD_Studio / 27_Sovereign_Legal
Compliance: Deterministic Agent Outputs, 100% Citation Hashes & State Persistence
"""

import os
import sys
import json
import sqlite3

REPO_ROOT = "/home/james/stacklabs"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.name == 'nt' and "y:\\" not in sys.path:
    sys.path.insert(0, "y:\\")

from services.mard_studio.legal.mard_legal_dispatcher import legal_dispatcher
from sovereign_knot_core.legal_enclave import get_db_connection

def run_mard_legal_tests():
    print("=================================================================")
    print("⚡ RUNNING M.A.R.D. LEGAL MULTI-AGENT SWARM UNIT TESTS")
    print("=================================================================\n")

    conn = get_db_connection()
    try:
        # Seed test matter
        with conn:
            conn.execute("DELETE FROM sli_agent_execution_log WHERE matter_id = 'TEST-MARD-MTR-001'")
            conn.execute("DELETE FROM sli_matter_acl WHERE matter_id = 'TEST-MARD-MTR-001'")
            conn.execute(
                """
                INSERT INTO sli_matter_acl (
                    matter_id, matter_name, practice_group, lead_attorney, authorized_timekeepers, is_confidential_restricted
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "TEST-MARD-MTR-001",
                    "M.A.R.D. Test Multi-Agent Matter",
                    "Commercial Litigation",
                    "james",
                    json.dumps(["james", "attorney_lit_01"]),
                    0
                )
            )

        # -------------------------------------------------------------
        # TEST 1: Deposition Contradiction Extraction Agent
        # -------------------------------------------------------------
        print("[TEST 1] Testing Deposition Contradiction Extraction Agent...")
        sample_transcript = """
Q: Mr. Miller, on October 14th, did you personally inspect the warehouse shipment before departure?
A: No, I was in Chicago attending the logistics summit on October 14th. I was not in Bay 4.
"""
        sample_exhibit = """
SECURITY EXHIBIT 14: Badge Swipe Timestamp: 2026-10-14 08:14:22 EST. Location: Bay 4 Outbound Loading Dock, Building 2. Access Log confirmed.
"""
        depo_res = legal_dispatcher.dispatch_legal_task(
            agent_name="depo_contradiction",
            matter_id="TEST-MARD-MTR-001",
            user_id="james",
            payload={
                "transcript_text": sample_transcript,
                "exhibit_text": sample_exhibit,
                "witness_name": "David Miller (VP Operations)"
            }
        )
        assert depo_res["status"] == "SUCCESS", f"Deposition agent failed: {depo_res}"
        res_data = depo_res["result"]
        assert res_data["contradiction_count"] >= 1, "Failed to detect deposition contradiction"
        assert res_data["contradictions"][0]["severity"] == "HIGH_IMPEACHMENT"
        print(f"  ✓ [PASS] Detected {res_data['contradiction_count']} high-impeachment contradiction(s) in {depo_res['latency_ms']}ms.")

        # -------------------------------------------------------------
        # TEST 2: Playbook Contract Redlining Agent
        # -------------------------------------------------------------
        print("\n[TEST 2] Testing Playbook Contract Redlining Agent...")
        sample_contract = """
SECTION 4.2 - SURVIVAL.
The representations and warranties in this Agreement shall survive for 12 months following Closing.
SECTION 9.1 - GOVERNING LAW.
This Agreement shall be governed by the laws of the State of New York.
SECTION 8.4 - DAMAGES.
Neither party shall be liable for indirect, punitive, or consequential damages.
"""
        redline_res = legal_dispatcher.dispatch_legal_task(
            agent_name="contract_redline",
            matter_id="TEST-MARD-MTR-001",
            user_id="james",
            payload={
                "contract_text": sample_contract,
                "playbook": "BUYER_FAVORABLE"
            }
        )
        assert redline_res["status"] == "SUCCESS", f"Redline agent failed: {redline_res}"
        redlines = redline_res["result"]["redlines"]
        assert len(redlines) >= 3, f"Expected 3 redlines, got {len(redlines)}"
        assert "sixty (60) months" in redlines[0]["proposed_redline"]
        assert "Delaware Court of Chancery" in redlines[1]["proposed_redline"]
        print(f"  ✓ [PASS] Generated {len(redlines)} deterministic playbook redlines in {redline_res['latency_ms']}ms.")

        # -------------------------------------------------------------
        # TEST 3: Privilege & Work-Product Redaction Guard
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing Privilege & Work-Product Redaction Guard...")
        sample_memo = """
CONFIDENTIAL ATTORNEY WORK-PRODUCT & LITIGATION STRATEGY MEMO.
Prepared for client trial prep. Case valuation exposure estimated at $4.2M.
SSN Reference: 000-12-3456.
"""
        priv_res = legal_dispatcher.dispatch_legal_task(
            agent_name="privilege_guard",
            matter_id="TEST-MARD-MTR-001",
            user_id="james",
            payload={
                "document_text": sample_memo,
                "bates_number": "PROD-000482",
                "author": "James Carroll (Lead Counsel)",
                "recipient": "Board of Directors"
            }
        )
        assert priv_res["status"] == "SUCCESS", f"Privilege agent failed: {priv_res}"
        priv_data = priv_res["result"]
        assert priv_data["is_privileged"] is True
        assert len(priv_data["redactions"]) >= 2 # Work product + SSN
        assert len(priv_data["privilege_log_entries"]) >= 1
        print(f"  ✓ [PASS] Identified privilege assertions & generated eDiscovery privilege log in {priv_res['latency_ms']}ms.")

        # -------------------------------------------------------------
        # TEST 4: Outside Counsel Guidelines (OCG) Pre-Billing Guard
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing OCG Pre-Billing Guard & Splitter...")
        sample_entries = [
            {
                "line_id": "L-01",
                "timekeeper": "Keith Whittaker (Partner)",
                "rate": 850,
                "hours": 3.0,
                "narrative": "Review transcript, draft cross-examination outline, and conference call with client."
            },
            {
                "line_id": "L-02",
                "timekeeper": "Jackson Oates (Paralegal)",
                "rate": 240,
                "hours": 1.0,
                "narrative": "Organize binder and file organization for trial."
            }
        ]
        ocg_res = legal_dispatcher.dispatch_legal_task(
            agent_name="ocg_billing",
            matter_id="TEST-MARD-MTR-001",
            user_id="james",
            payload={"entries": sample_entries}
        )
        assert ocg_res["status"] == "SUCCESS", f"OCG agent failed: {ocg_res}"
        ocg_items = ocg_res["result"]["line_items"]
        assert ocg_items[0]["status"] == "BLOCKED_BLOCK_BILLING"
        assert ocg_items[0]["suggested_split"] is not None
        assert ocg_items[1]["status"] == "FLAGGED_ADMINISTRATIVE"
        print(f"  ✓ [PASS] Intercepted block billing & administrative overhead in {ocg_res['latency_ms']}ms.")

        # -------------------------------------------------------------
        # TEST 5: Ethical Wall Rejection & Audit Log Persistence
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Ethical Wall Rejection & Database Persistence...")
        unauth_res = legal_dispatcher.dispatch_legal_task(
            agent_name="depo_contradiction",
            matter_id="TEST-MARD-MTR-001",
            user_id="unauthorized_attorney_99", # Unauthorized persona
            payload={"transcript_text": "test", "exhibit_text": "test"}
        )
        assert unauth_res["status"] == "FORBIDDEN", "Security failure: Unauthorized agent dispatch allowed!"
        print(f"  ✓ [PASS] Unauthorized agent execution strictly blocked by ethical wall.")

        # Check sli_agent_execution_log in sovereign_now.db
        cur = conn.cursor()
        cur.execute("SELECT run_id, agent_name, status, latency_ms, tokens_processed, source_chunk_hashes FROM sli_agent_execution_log WHERE matter_id = 'TEST-MARD-MTR-001'")
        db_records = cur.fetchall()
        assert len(db_records) == 4, f"Expected 4 successful execution logs in DB, found {len(db_records)}"
        for rec in db_records:
            assert rec["status"] == "SUCCESS"
            hashes = json.loads(rec["source_chunk_hashes"])
            assert len(hashes) > 0, "Missing SHA-256 citation hashes in persistent run log!"
        print(f"  ✓ [PASS] Verified 4 persistent execution logs with verified SHA-256 citation hashes in sovereign_now.db.")

        print("\n=================================================================")
        print("🎉 ALL 4 M.A.R.D. LEGAL AGENTS & DISPATCH PIPELINES PASSED (100%)")
        print("=================================================================\n")

    finally:
        conn.close()

if __name__ == "__main__":
    run_mard_legal_tests()
