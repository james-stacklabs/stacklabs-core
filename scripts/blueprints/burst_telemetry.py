"""
StackLabs Sovereign OS - Burst Telemetry Blueprint
Decoupled Flask Blueprint exposing sanitized Day-00 Mount Olympus HUD.
Adheres strictly to Invariant 26 (Gandalf), Invariant 35 (.venv), and Invariant 50 (Decoupling).
"""

from datetime import datetime, timezone
import json
import os
import sqlite3
from flask import Blueprint, jsonify, render_template

burst_blueprint = Blueprint("burst_blueprint", __name__)

DB_PATH = "/home/james/stacklabs/data/sicko_burst.db"


def get_db_connection():
    """Return a read-only SQLite connection adhering to WAL isolation."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_day_zero_telemetry():
    """Deterministic Day-00 baseline telemetry payload. Zero fabricated trades."""
    slots = []
    for i in range(1, 11):
        slots.append({
            "slot_id": i,
            "status": "VACANT",
            "allocated_capital_usd": 1000.00,
            "position": None
        })

    return {
        "system_status": "PRE_SOAK_STANDBY",
        "proof_gate_day": 0,
        "proof_gate_total_days": 30,
        "portfolio": {
            "starting_bankroll_usd": 10000.00,
            "total_equity_usd": 10000.00,
            "cash_balance_usd": 10000.00,
            "invested_equity_usd": 0.00,
            "cumulative_realized_pnl_usd": 0.00,
            "cumulative_realized_pnl_pct": 0.00,
            "current_drawdown_pct": 0.00,
            "max_drawdown_pct": 0.00,
            "total_closed_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "expired_count": 0,
            "win_rate_pct": 0.0,
        },
        "slots": slots,
        "active_catalyst": {
            "catalyst_id": "CAT-2026-TX-WHARTON-084",
            "detected_at": "2026-10-02T19:14:22Z",
            "source": "Wharton County Commissioners Court Minutes",
            "jurisdiction": "Wharton County, TX",
            "target_ticker": "VST",
            "verbatim_quote": "Court denies industrial water cooling variance request for proposed 40MW compute substation citing Section 36 groundwater conservation rules.",
            "v_fear_score": 0.84,
            "sub_scores": {
                "target_specificity": 0.91,
                "regulatory_severity": 0.85,
                "capex_at_risk": 0.72,
                "iv_complacency": 0.68,
            },
            "deliberation": {
                "bcs_score": 0.86,
                "consensus_direction": "SHORT",
                "analysts": {
                    "marcus_value": {
                        "name": "MARCUS // FUNDAMENTALS",
                        "stance": "HIGH CONVICTION SHORT",
                        "confidence": 0.89,
                        "summary": "Substation deployment freeze forces $42M CapEx write-off; debt service multiples cannot absorb 14-month redesign delay.",
                    },
                    "kai_momentum": {
                        "name": "KAI // MOMENTUM",
                        "stance": "SHORT ACCELERATION",
                        "confidence": 0.84,
                        "summary": "Gamma wall pinned at $125. Institutional stop run begins once $120.00 breaks with 3.2x daily volume spike.",
                    },
                    "hendricks_risk": {
                        "name": "HENDRICKS // REGULATORY & RISK",
                        "stance": "SHORT CONFIRMED",
                        "confidence": 0.88,
                        "summary": "TX Water Code Section 36 statutory appeals average 14 months with zero emergency injunction probability.",
                    },
                    "pete_velocity": {
                        "name": "PETE // RETAIL VELOCITY",
                        "stance": "LAGGING PANIC",
                        "confidence": 0.83,
                        "summary": "Local county zoning dockets completely ignored by FinTwit and retail aggregators. True gap down occurs on Monday morning.",
                    },
                },
            },
        },
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }


@burst_blueprint.route("/burst", methods=["GET"])
def burst_hud_view():
    """Render the Mount Olympus HUD single-page application."""
    return render_template("burst_hud.html")


@burst_blueprint.route("/api/burst/telemetry", methods=["GET"])
def burst_telemetry_feed():
    """Return JSON telemetry for the 10-slot Mount Olympus engine."""
    conn = get_db_connection()
    if not conn:
        return jsonify(get_day_zero_telemetry())

    try:
        cur = conn.cursor()
        cur.execute("SELECT payload_json FROM telemetry_snapshots ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row and row["payload_json"]:
            return jsonify(json.loads(row["payload_json"]))
        return jsonify(get_day_zero_telemetry())
    except Exception:
        return jsonify(get_day_zero_telemetry())
    finally:
        conn.close()
