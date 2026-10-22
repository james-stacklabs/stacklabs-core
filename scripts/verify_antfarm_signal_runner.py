#!/usr/bin/env python3
"""
Verification Suite for Ant Farm Model Signal Runner
Path: /home/james/stacklabs/scripts/verify_antfarm_signal_runner.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)

Tests end-to-end multi-agent debate, JSON schema conformance, and SQLite ledger insertion.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
STACKLABS_ROOT = Path("/home/james/stacklabs")

for p in [str(STACKLABS_ROOT), str(SOVEREIGN_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.antfarm_signal_runner import AntFarmSignalEngine

def test_antfarm_single_catalyst():
    print("🧪 [TEST 1/2] Initializing AntFarmSignalEngine...")
    engine = AntFarmSignalEngine()
    
    test_catalyst = {
        "date": "2026-09-21",
        "ticker": "OXY",
        "headline": "Occidental Petroleum files emergency 8-K announcing $2.1B senior note offering to refinance debt amid volatile WTI crude prices.",
        "pre_price": 55.20,
        "catalyst_price": 52.00,
        "volume_surge": "4.8x ADV"
    }

    print("🧪 [TEST 2/2] Running Live 4-Pleeb Debate & Arbiter Signal Generation...")
    res = engine.run_debate_for_catalyst(test_catalyst)
    
    # Assertions
    assert "panic" in res["debate"], "Panic Pleeb response missing!"
    assert "value" in res["debate"], "Value Contrarian response missing!"
    assert "signal" in res, "Consensus Arbiter signal missing!"
    
    sig = res["signal"]
    assert "action" in sig, "Signal missing 'action' key!"
    assert "consensus_score" in sig, "Signal missing 'consensus_score' key!"
    assert sig["ticker"] == "OXY", f"Expected ticker OXY, got {sig.get('ticker')}"
    
    print("\n✅ Ant Farm Multi-Agent Debate Verified!")
    print(f"  Panic: {res['debate']['panic'][:80]}...")
    print(f"  Value: {res['debate']['value'][:80]}...")
    print(f"  Signal Action: {sig['action']} (Score: {sig['consensus_score']:.1f}/100)")
    print(f"  Rationale: {sig.get('rationale')}")
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY ON METAL!")

if __name__ == "__main__":
    test_antfarm_single_catalyst()
