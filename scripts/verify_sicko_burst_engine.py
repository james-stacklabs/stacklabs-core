#!/usr/bin/env python3
"""
Verification Test Suite: SICKO Burst Engine Hardened State Machine
Path: /home/james/stacklabs/scripts/verify_sicko_burst_engine.py
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from decimal import Decimal

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

from scripts.sicko_engine import SickoStateMachine, TP_THRESHOLD, SL_THRESHOLD, MAX_HOLD_DAYS
from scripts.oracle_swarm import simulate_swarm_debate
from scripts.sicko_daily_audit import generate_daily_audit

def test_engine_lifecycle():
    print("[TEST] Initializing SICKO State Machine in isolated sandbox DB...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db = Path(tmp.name)

    try:
        sm = SickoStateMachine(db_path=test_db)
        summary = sm.get_portfolio_summary()
        assert summary["initial_bankroll"] == 10000.00
        assert summary["active_positions"] == 0
        assert summary["vacant_positions"] == 10
        print("[PASS] 10 vacant slots initialized successfully.")

        # Test Allocation
        candidates = [
            {"symbol": "EQT", "entry_price": "40.00"},
            {"symbol": "KMI", "entry_price": "20.00"},
            {"symbol": "LNG", "entry_price": "50.00"}
        ]
        filled = sm.fill_vacant_slots(candidates)
        assert filled == 3
        summary2 = sm.get_portfolio_summary()
        assert summary2["active_positions"] == 3
        assert summary2["vacant_positions"] == 7
        print("[PASS] Slot allocation verified (3 filled, 7 vacant).")

        # Test Take Profit Trigger (+5.0%)
        # EQT entry 40.00 -> 42.10 (+5.25%) -> Take Profit
        # KMI entry 20.00 -> 19.80 (-1.00%) -> Hold
        res1 = sm.evaluate_active_slots({"EQT": "42.10", "KMI": "19.80", "LNG": "50.00"})
        eqt_res = next(r for r in res1 if r.symbol == "EQT")
        kmi_res = next(r for r in res1 if r.symbol == "KMI")
        assert eqt_res.action == "TAKE_PROFIT"
        assert Decimal(eqt_res.pnl_percent) >= TP_THRESHOLD
        assert kmi_res.action == "HOLD"
        print("[PASS] Take Profit (+5.0%) trigger executed correctly with Decimal precision.")

        # Test Stop Loss Trigger with Gap Slippage Recording (-2.5% theoretical vs -4.0% market tick)
        # KMI entry 20.00 -> 19.20 (-4.0%) -> Stop Loss with slippage delta
        # Theoretical stop was 19.50 (-2.5%). Actual exit is 19.20. Gap slippage delta = (19.20 - 19.50) * 50 shares = -$15.00
        res2 = sm.evaluate_active_slots({"KMI": "19.20", "LNG": "50.00"})
        kmi_res2 = next(r for r in res2 if r.symbol == "KMI")
        assert kmi_res2.action == "STOP_LOSS"
        assert Decimal(kmi_res2.pnl_percent) <= SL_THRESHOLD
        assert Decimal(kmi_res2.slippage_delta_usd) < Decimal('0.00')
        print(f"[PASS] Stop Loss triggered with recorded gap slippage: ${kmi_res2.slippage_delta_usd}.")

        # Test Day-10 Time Stop Expiration
        # Advance LNG holding days to 10
        with sm._get_conn() as conn:
            conn.execute("UPDATE portfolio_slots SET holding_days = 10 WHERE current_symbol = 'LNG'")

        res3 = sm.evaluate_active_slots({"LNG": "50.50"})
        lng_res = next(r for r in res3 if r.symbol == "LNG")
        assert lng_res.action == "TIME_EXPIRE"
        print("[PASS] Day-10 Time Horizon Stop triggered and vacated cleanly.")

        # Verify Ledger Inspection
        with sm._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            ledger_rows = conn.execute("SELECT * FROM burst_trade_ledger").fetchall()
            assert len(ledger_rows) == 3
            for row in ledger_rows:
                assert row["slippage_delta_usd"] is not None
                print(f"  [LEDGER] {row['symbol']} | Exit: {row['exit_reason']} | PnL: ${row['pnl_usd']} | Slip: ${row['slippage_delta_usd']}")

        summary3 = sm.get_portfolio_summary()
        assert summary3["active_positions"] == 0
        assert summary3["vacant_positions"] == 10
        assert summary3["total_trades"] == 3
        print(f"[PASS] P&L calculated: Realized ${summary3['realized_pnl_usd']:+.2f}, Win Rate: {summary3['win_rate_pct']}%.")

        # Test Swarm Debate
        print("[TEST] Running Mount Olympus Oracle Swarm Debate simulation...")
        debate = simulate_swarm_debate("LNG export terminals hit by Gulf storm delays.", "LNG")
        assert "synthesis" in debate
        print(f"[PASS] Swarm Debate synthesized. Action: {debate['synthesis']['recommended_action']}.")

        # Test Audit Logger
        report_path = generate_daily_audit(day_number=1, db_path=test_db)
        assert report_path.exists()
        print(f"[PASS] Daily audit report generated at {report_path}.")

        print("==================================================")
        print("🎉 ALL SICKO HARDENED STATE MACHINE TESTS PASSED!")
        print("==================================================")

    finally:
        if test_db.exists():
            test_db.unlink()

if __name__ == "__main__":
    test_engine_lifecycle()
