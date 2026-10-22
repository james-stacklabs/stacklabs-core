#!/usr/bin/env python3
"""
SICKO Daily Soak Audit Generator
Path: /home/james/stacklabs/scripts/sicko_daily_audit.py
Author: James Carroll (Lead Systems Architect)
"""

import sys
import datetime
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

from scripts.sicko_engine import SickoStateMachine, AUDIT_LOG_DIR

def generate_daily_audit(day_number: int = 1, current_prices: dict = None, db_path: Path = None) -> Path:
    sm = SickoStateMachine(db_path=db_path) if db_path else SickoStateMachine()
    summary = sm.get_portfolio_summary(current_prices)

    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.date.today().strftime("%Y%m%d")
    report_file = AUDIT_LOG_DIR / f"daily_soak_{today_str}.md"

    pnl_sign = "+" if summary["realized_pnl_usd"] >= 0 else ""
    unreal_sign = "+" if summary["unrealized_pnl_usd"] >= 0 else ""

    md = [
        f"# 📊 SICKO BURST LEDGER — DAILY SOAK AUDIT (DAY {day_number:02d} / 30)",
        f"**Date:** {datetime.date.today().isoformat()} | **Host:** Clio Bare Metal (Smyrna Lab) | **Engine:** SICKO v1.4.2",
        "",
        "### 1. High-Level Portfolio Metrics",
        f"- **Initial Bankroll:** ${summary['initial_bankroll']:,.2f}",
        f"- **Current Realized P&L:** {pnl_sign}${summary['realized_pnl_usd']:,.2f}",
        f"- **Unrealized Floating P&L:** {unreal_sign}${summary['unrealized_pnl_usd']:,.2f}",
        f"- **Total Portfolio Value:** ${summary['total_portfolio_value']:,.2f}",
        f"- **Win / Loss Record:** {summary['wins']} Wins / {summary['losses']} Losses ({summary['win_rate_pct']}% Win Rate)",
        f"- **Active Slots:** {summary['active_positions']} / 10 | **Vacant Slots:** {summary['vacant_positions']}",
        "",
        "### 2. Active 10-Slot Matrix",
        "| Slot | Symbol | Entry Date | Entry ($) | Shares | Holding Days | Target TP (+5%) | Target SL (-2.5%) | Status |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]

    for s in summary["slots"]:
        if s["status"] == "ACTIVE":
            entry_p = float(s['entry_price']) if s['entry_price'] is not None else 0.0
            sh = float(s['shares']) if s['shares'] is not None else 0.0
            tp = float(s['target_tp']) if s['target_tp'] is not None else 0.0
            sl = float(s['target_sl']) if s['target_sl'] is not None else 0.0
            md.append(f"| {s['slot_id']} | {s['current_symbol']} | {s['entry_timestamp'][:10]} | ${entry_p:.2f} | {sh:.2f} | Day {s['holding_days']} | ${tp:.2f} | ${sl:.2f} | ACTIVE |")
        else:
            md.append(f"| {s['slot_id']} | [VACANT] | — | — | — | — | — | — | VACANT |")

    md.append("")
    md.append("---")
    md.append("*Generated automatically by Sovereign OS SICKO Engine on Clio bare metal.*")

    content = "\n".join(md)
    report_file.write_text(content, encoding="utf-8")
    print(f"✅ Generated Daily Audit: {report_file}")
    return report_file

if __name__ == "__main__":
    generate_daily_audit()
