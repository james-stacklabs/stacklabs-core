#!/usr/bin/env python3
"""
verify_deranged_predict_engine.py — Sovereign Predict Verification & Metal Test Gate
===================================================================================
Path: /home/james/stacklabs/scripts/verify_deranged_predict_engine.py

Verifies:
1. Canonical Emergent Society simulation integration and schema on metal.
2. Live citizens (Barf, Sammy, Hoffa, BatteryChucker) with live BPs and bankrolls.
3. Live market contracts from market_contracts table (MKT-001, MKT-002, MKT-003, etc.).
4. Simulated trade execution against emergent_society.db (citizen_trades).
5. Live REST API endpoints on Dead Drop Server (Port 8088) and Emergent Society (Port 8098).
6. Asserts exit code 0.
"""

import sys
import os
import json
import urllib.request
from pathlib import Path

# Add project root
PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fanstack_predict_engine import (
    load_market_state,
    execute_trade,
    DB_PATH
)


def log_step(name: str):
    print(f"\n⚡ [STEP] {name}")


def assert_condition(cond: bool, msg: str):
    if not cond:
        print(f"❌ ASSERTION FAILED: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ {msg}")


def test_state_schema():
    log_step("Validating Living Emergent Society Simulation State Schema")
    assert_condition(DB_PATH.exists(), f"Emergent society database exists at {DB_PATH}")

    state = load_market_state()
    for field in ["updated_at", "season", "market_title", "engine_status", "contracts", "advocates_bankrolls", "recent_trades"]:
        assert_condition(field in state, f"Root field '{field}' present in state")

    assert_condition(state["engine_status"] == "LIVE_EMERGENT_SOCIETY", "Engine status is 'LIVE_EMERGENT_SOCIETY'")

    contracts = state["contracts"]
    assert_condition(len(contracts) >= 3, f"Found {len(contracts)} contracts (expected >= 3)")

    contract_ids = {c["id"] for c in contracts}
    for req_id in ["MKT-001", "MKT-002", "MKT-003"]:
        assert_condition(req_id in contract_ids, f"Active simulation contract '{req_id}' present")

    for c in contracts:
        for cf in ["id", "ticker", "category", "question", "yes_price_cents", "no_price_cents", "volume_contracts", "status"]:
            assert_condition(cf in c, f"Contract {c.get('ticker')} has field '{cf}'")
        assert_condition(
            c["yes_price_cents"] + c["no_price_cents"] == 100,
            f"Contract {c.get('ticker')} pricing invariant: {c['yes_price_cents']}¢ + {c['no_price_cents']}¢ == 100¢"
        )

    advocates = state["advocates_bankrolls"]
    assert_condition(len(advocates) >= 5, f"Found {len(advocates)} advocate citizens in bankrolls")

    # Check key citizens exist
    citizen_names = [adv["name"] for adv in advocates.values()]
    for expected_name in ["Barf", "Sammy the Savant", "Jimmy Hoffa Under Section 107"]:
        assert_condition(any(expected_name in n for n in citizen_names), f"Citizen '{expected_name}' present in bankrolls")

    for adv_key, adv in advocates.items():
        for af in ["name", "cash_cents", "portfolio_value_cents", "profit_loss_cents", "rank", "active_superstition", "systolic_bp"]:
            assert_condition(af in adv, f"Advocate {adv_key} has field '{af}'")


def test_simulated_trade_cycle():
    log_step("Executing Simulated Trade Cycle on Metal (Emergent Society DB)")
    advocate_id = "barf"
    contract_id = "MKT-001"
    side = "YES"
    shares = 10
    superstition = "Automated Verification Test: Buying YES on Barf BP 160+"

    # Execute trade directly
    result = execute_trade(
        advocate_id=advocate_id,
        contract_id=contract_id,
        side=side,
        shares=shares,
        superstition_note=superstition
    )

    assert_condition(result.get("status") == "EXECUTED", "Trade execution returned status: EXECUTED")
    assert_condition(result.get("success") is True, "Trade execution returned success: True")
    assert_condition("trade_id" in result.get("trade", {}), "Trade payload contains trade_id")
    print(f"  • Executed trade {result['trade']['trade_id']}: {result['trade']['citizen']} bought {shares} shs of {result['trade']['ticker']} {side}")

    # Check trade appears in latest market state
    state = load_market_state()
    recent = state.get("recent_trades", [])
    assert_condition(len(recent) > 0, "Recent trades ledger is non-empty")
    latest_trade_ids = [t.get("trade_id") for t in recent[:5]]
    assert_condition(result["trade"]["trade_id"] in latest_trade_ids, f"Trade {result['trade']['trade_id']} visible in recent trades")


def test_live_rest_endpoints():
    log_step("Verifying Live REST Endpoints on Metal")
    endpoints = [
        ("Dead Drop Gateway (Port 8088)", "http://127.0.0.1:8088/api/predict/state"),
        ("Emergent Society Daemon (Port 8098)", "http://127.0.0.1:8098/api/society/market"),
    ]

    for name, url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PredictVerification/2.0"})
            with urllib.request.urlopen(req, timeout=5) as res:
                assert_condition(res.status == 200, f"{name} responded HTTP 200")
                payload = json.loads(res.read().decode("utf-8"))
                assert_condition("contracts" in payload, f"{name} payload contains 'contracts'")
        except Exception as e:
            assert_condition(False, f"{name} endpoint failed: {e}")

    # Test POST trade through Dead Drop Server REST API
    log_step("Testing POST /api/predict/trade on Dead Drop Server (Port 8088)")
    trade_payload = json.dumps({
        "advocate": "sammy_the_savant",
        "contract_id": "MKT-002",
        "side": "NO",
        "shares": 5,
        "superstition": "REST API Automated Test Gate"
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:8088/api/predict/trade",
        data=trade_payload,
        headers={"Content-Type": "application/json", "User-Agent": "PredictVerification/2.0"}
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        assert_condition(res.status == 200, "POST /api/predict/trade responded HTTP 200")
        resp_data = json.loads(res.read().decode("utf-8"))
        assert_condition(resp_data.get("status") == "EXECUTED", "REST trade returned status: EXECUTED")
        print(f"  • REST Trade Executed: {resp_data['trade']['trade_id']} ({resp_data['trade']['ticker']} {resp_data['trade']['side']})")


def main():
    print("=" * 72)
    print("🎲 SOVEREIGN OS: PREDICT EXCHANGE & SIMULATION ENGINE VERIFICATION")
    print("   Physical Metal & Live Emergent Society Daemon Verification")
    print("=" * 72)

    test_state_schema()
    test_simulated_trade_cycle()
    test_live_rest_endpoints()

    print("\n" + "=" * 72)
    print("✨ ALL PREDICT MARKET CHECKS PASSED ON METAL WITH ZERO DEFECTS.")
    print("=" * 72 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
