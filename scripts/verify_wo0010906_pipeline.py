#!/usr/bin/env python3
"""
Verification Suite for WO0010906: Autonomous Voice Drop to Syndicate Pipeline
Path: /home/james/stacklabs/scripts/verify_wo0010906_pipeline.py
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.voice_drop_syndicate_builder import build_strategic_dossier, APPROVAL_DIR
from scripts.approve_syndicate_drop import list_pending, approve_dossier


def test_pipeline():
    print("==================================================")
    print("🔬 WO0010906: VOICE DROP TO SYNDICATE HARNESS")
    print("==================================================")

    # 1. Test Dossier Synthesis from Mock Audio Monologue
    mock_transcript = (
        "James, I was thinking about the sentinel swarms in The Matrix and how these market "
        "arbitrage nodes operate. If we have sub-millisecond execution on dedicated local hardware, can we "
        "structure an institutional liquidity pool that captures the retail spread without cloud hops? "
        "I need a complete presentation for our capital allocation committee."
    )
    print("[1/3] Testing strategic dossier synthesis...")
    dossier = build_strategic_dossier("pawel", "pawel", mock_transcript, "test_matrix_swarms.webm")
    assert dossier.get("dossier_id"), "Failed to generate dossier_id"
    json_path = APPROVAL_DIR / f"{dossier['dossier_id']}.json"
    md_path = APPROVAL_DIR / f"{dossier['dossier_id']}.md"
    assert json_path.exists(), f"Missing JSON dossier: {json_path}"
    assert md_path.exists(), f"Missing Markdown whitepaper: {md_path}"
    print(f"      ✓ Dossier generated and staged: {dossier['dossier_id']}")

    # 2. Test Pending Approval Listing
    print("[2/3] Testing pending approval catalog...")
    pending = list_pending()
    assert len(pending) > 0, "Pending list returned empty"
    print(f"      ✓ {len(pending)} pending item(s) found.")

    # 3. Test Pilot Approval Flow
    print("[3/3] Testing Pilot approval and portal mounting...")
    approve_dossier(json_path)
    updated_data = json_path.read_text(encoding="utf-8")
    assert "APPROVED_BY_PILOT" in updated_data, "Dossier status was not updated to APPROVED_BY_PILOT"
    print("      ✓ Dossier approved and state transition verified.")

    print("\n✅ ALL 3 PIPELINE TESTS PASSED CLEANLY ON METAL.")


if __name__ == "__main__":
    test_pipeline()
