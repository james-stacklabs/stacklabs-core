#!/usr/bin/env python3
"""
Automated Unit Test Suite: Sovereign Legal Intelligence Ethical Wall ACL
Target CI: sovereign_knot_core / 26_MARD_Studio
Verification: 100% Boundary Isolation Across Practice Groups & Audit Logging
"""

import os
import sys
import json
import sqlite3

# Add repo root to path
sys.path.insert(0, "/home/james/stacklabs")
if os.name == 'nt':
    sys.path.insert(0, r"y:\ ")

from sovereign_knot_core.legal_enclave import (
    get_db_connection,
    check_matter_access,
    register_matter_document,
    query_matter_context
)

def run_ethical_wall_tests():
    print("=================================================================")
    print("⚖️  RUNNING SOVEREIGN LEGAL INTELLIGENCE ETHICAL WALL UNIT TESTS")
    print("=================================================================\n")

    conn = get_db_connection()
    try:
        # 1. Clean and Seed Test Matters
        print("[STEP 1] Seeding Test Practice Group Matters...")
        with conn:
            conn.execute("DELETE FROM sli_access_audit_log WHERE matter_id LIKE 'TEST-MTR-%'")
            conn.execute("DELETE FROM sli_matter_vector_chunk WHERE matter_id LIKE 'TEST-MTR-%'")
            conn.execute("DELETE FROM sli_matter_document WHERE matter_id LIKE 'TEST-MTR-%'")
            conn.execute("DELETE FROM sli_matter_acl WHERE matter_id LIKE 'TEST-MTR-%'")

            # Matter 1: Corporate M&A (Whitford & Carroll)
            conn.execute(
                """
                INSERT INTO sli_matter_acl (
                    matter_id, matter_name, practice_group, lead_attorney, authorized_timekeepers, is_confidential_restricted
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "TEST-MTR-CORP-001",
                    "Acme Corp Asset Purchase Agreement",
                    "Corporate M&A",
                    "james",
                    json.dumps(["james", "attorney_corp_01", "paralegal_corp_02"]),
                    0
                )
            )

            # Matter 2: Litigation Boutique (Miller Deposition)
            conn.execute(
                """
                INSERT INTO sli_matter_acl (
                    matter_id, matter_name, practice_group, lead_attorney, authorized_timekeepers, is_confidential_restricted
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "TEST-MTR-LIT-002",
                    "Miller v. Apex Logistics Discovery & Contradictions",
                    "Commercial Litigation",
                    "attorney_lit_05",
                    json.dumps(["attorney_lit_05", "associate_lit_03"]),
                    0
                )
            )

            # Matter 3: Confidential Executive Investigation
            conn.execute(
                """
                INSERT INTO sli_matter_acl (
                    matter_id, matter_name, practice_group, lead_attorney, authorized_timekeepers, is_confidential_restricted
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "TEST-MTR-CONF-003",
                    "Special Committee Independent Audit",
                    "Internal Governance",
                    "james",
                    json.dumps(["james"]),
                    1 # Confidential Restricted
                )
            )
        print("  ✓ Seeded 3 test matters across Corporate, Litigation, and Governance.\n")

        # 2. Ingest Test Documents
        print("[STEP 2] Ingesting & Chunking Privileged Case Documents...")
        sample_contract_text = """
SECTION 4.2 - INDEMNIFICATION AND SURVIVAL OF COVENANTS.
The Seller shall defend, indemnify, and hold harmless Buyer and its affiliates from and against any and all Losses arising out of, or resulting from, any breach of any representation or warranty made by Seller in Article III of this Agreement.
The survival period for fundamental representations shall be sixty (60) months following the Closing Date.
All claims under Section 4.2(b) must be brought in the Delaware Court of Chancery.
This document contains proprietary trade secret pricing mechanisms and is protected under attorney work-product privilege.
"""
        sample_depo_text = """
DEPOSITION OF WITNESS DAVID MILLER - VOLUME I (PAGES 1 - 250).
Q: Mr. Miller, on October 14th, did you personally inspect the warehouse shipment before departure?
A: No, I was in Chicago attending the logistics summit on October 14th. I did not return until the 18th.
Q: Were you aware of the temperature excursion logged by the sensor on October 15th?
A: I never saw any temperature telemetry logs until my deposition prep last week.
"""

        ok1, msg1, doc_id1 = register_matter_document(
            user_id="attorney_corp_01",
            matter_id="TEST-MTR-CORP-001",
            file_name="acme_asset_purchase_agreement_v4.pdf",
            file_path="/data/fixtures/acme_apa.pdf",
            text_content=sample_contract_text,
            is_privileged=1,
            privilege_basis="Attorney Work Product Doctrine"
        )
        assert ok1, f"Failed to ingest corp document: {msg1}"
        print(f"  ✓ Corp Document registered successfully: doc_id={doc_id1}")

        ok2, msg2, doc_id2 = register_matter_document(
            user_id="attorney_lit_05",
            matter_id="TEST-MTR-LIT-002",
            file_name="depo_witness_miller_vol1.txt",
            file_path="/data/fixtures/miller_vol1.txt",
            text_content=sample_depo_text,
            is_privileged=0
        )
        assert ok2, f"Failed to ingest litigation document: {msg2}"
        print(f"  ✓ Litigation Document registered successfully: doc_id={doc_id2}\n")

        # 3. Test Authorized Access
        print("[STEP 3] Testing Authorized Practice Group Timekeeper Access...")
        allowed_corp, reason_corp, meta_corp = check_matter_access(
            user_id="paralegal_corp_02",
            matter_id="TEST-MTR-CORP-001",
            action="UI_VIEW"
        )
        assert allowed_corp, f"Expected authorized access, got: {reason_corp}"
        assert reason_corp == "ALLOWED_AUTHORIZED_TIMEKEEPER"
        print(f"  ✓ [PASS] paralegal_corp_02 granted access to TEST-MTR-CORP-001 ({reason_corp})")

        # 4. Test Ethical Wall Boundary Rejection
        print("\n[STEP 4] Testing Cross-Practice Group Ethical Wall Violation...")
        blocked_cross, reason_cross, meta_cross = check_matter_access(
            user_id="attorney_lit_05", # Litigator trying to peek at Corporate M&A matter
            matter_id="TEST-MTR-CORP-001",
            action="UI_VIEW"
        )
        assert not blocked_cross, "Security Failure: Cross-practice attorney accessed restricted matter!"
        assert reason_cross == "ACCESS_DENIED_ETHICAL_WALL"
        print(f"  ✓ [PASS] attorney_lit_05 STRICTLY BLOCKED from TEST-MTR-CORP-001 ({reason_cross})")

        # 5. Test Confidential Matter Rejection
        print("\n[STEP 5] Testing Confidential Partner Restriction Enforcement...")
        blocked_conf, reason_conf, meta_conf = check_matter_access(
            user_id="attorney_corp_01", # Corporate attorney trying to access confidential investigation
            matter_id="TEST-MTR-CONF-003",
            action="UI_VIEW"
        )
        assert not blocked_conf, "Security Failure: Unauthorized user accessed confidential matter!"
        assert reason_conf == "BLOCKED_CONFIDENTIAL_RESTRICTED"
        print(f"  ✓ [PASS] attorney_corp_01 BLOCKED from Confidential Matter TEST-MTR-CONF-003 ({reason_conf})")

        # 6. Test Zero-Bleed Context Querying
        print("\n[STEP 6] Testing Zero-Bleed Grounded Vector Context Retrieval...")
        q_ok, q_msg, q_chunks = query_matter_context(
            user_id="attorney_corp_01",
            matter_id="TEST-MTR-CORP-001",
            search_keyword="INDEMNIFICATION"
        )
        assert q_ok, f"Query failed: {q_msg}"
        assert len(q_chunks) > 0, "No chunks returned for keyword query"
        for chunk in q_chunks:
            assert chunk["matter_id"] == "TEST-MTR-CORP-001", "Cross-matter data bleed detected!"
            assert len(chunk["chunk_hash_sha256"]) == 64, "Missing verified SHA-256 chunk hash!"
        print(f"  ✓ [PASS] Grounded query returned {len(q_chunks)} chunks with 100% matter isolation and SHA-256 hashes.")

        # Unauthorized query attempt
        unauth_q_ok, unauth_q_msg, unauth_chunks = query_matter_context(
            user_id="attorney_lit_05", # Unauthorized user
            matter_id="TEST-MTR-CORP-001",
            search_keyword="INDEMNIFICATION"
        )
        assert not unauth_q_ok, "Security Failure: Unauthorized user retrieved context chunks!"
        assert len(unauth_chunks) == 0
        print(f"  ✓ [PASS] Unauthorized context query blocked: '{unauth_q_msg}' (0 chunks leaked)")

        # 7. Verify Immutable Audit Ledger Integrity
        print("\n[STEP 7] Verifying Immutable Access Audit Trail (eDiscovery Ledger)...")
        cur = conn.cursor()
        cur.execute(
            "SELECT action, status, user_id, matter_id, details FROM sli_access_audit_log WHERE matter_id LIKE 'TEST-MTR-%' ORDER BY timestamp ASC"
        )
        audit_records = cur.fetchall()
        assert len(audit_records) >= 6, f"Expected at least 6 audit records, found {len(audit_records)}"
        
        allowed_count = sum(1 for r in audit_records if r["status"] == "ALLOWED")
        blocked_count = sum(1 for r in audit_records if "BLOCKED" in r["status"] or "RESTRICTED" in r["status"])
        
        print(f"  ✓ [PASS] Total audit records logged: {len(audit_records)}")
        print(f"    - Allowed Operations: {allowed_count}")
        print(f"    - Blocked Ethical Wall Interceptions: {blocked_count}")

        print("\n=================================================================")
        print("🎉 ALL ETHICAL WALL & DATA CONTAINMENT TESTS PASSED WITH 100% FIDELITY!")
        print("=================================================================\n")

    finally:
        conn.close()

if __name__ == "__main__":
    run_ethical_wall_tests()
