#!/usr/bin/env python3
"""
scripts/feed_predict_market.py
Automated High-Entropy Event Feeder & Degen Trade Generator
Injects live CFB/Kalshi/Weather triggers into emergent_society.db to keep the syndicate trading.
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 15, 32, 35, 50
"""
import os
import time
import json
import random
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/james/stacklabs/data/emergent_society.db")
VFS_FAAS = Path("/dev/shm/faas_vfs")
KALSHI_ODDS_FILE = Path("/home/james/stacklabs/stacklabs_inbox/today/kalshi_live_odds.json")

DEGEN_PLAYS = [
    {
        "citizen_id": "CIT-004-SAMMY",
        "contract_id": "MKT-002",
        "ticker": "$SAV-UNDR",
        "side": "BUY",
        "pos_type": "SHORT",
        "qty": 25,
        "superstition": "Calendar parity violation on 2nd Sunday! Smash the Over!",
        "opcode": "SICK"
    },
    {
        "citizen_id": "CIT-001-BATTERYCHUCKER",
        "contract_id": "CNT-001-BATTERY-CHUCK",
        "ticker": "$BATTERY-CHUCK",
        "side": "BUY",
        "pos_type": "LONG",
        "qty": 35,
        "superstition": "Junior drank another Atlanta craft IPA. D-cell inbound!",
        "opcode": "MLTD"
    },
    {
        "citizen_id": "CIT-003-BARF",
        "contract_id": "CNT-003-BARF-BP-170",
        "ticker": "$BARF-BP-170",
        "side": "BUY",
        "pos_type": "LONG",
        "qty": 40,
        "superstition": "Heartburn spiking past 170. Bullpen is cursed!",
        "opcode": "TILT"
    },
    {
        "citizen_id": "CIT-002-BATTERYCHUCKERJR",
        "contract_id": "MKT-003",
        "ticker": "$MID-FIRE",
        "side": "BUY",
        "pos_type": "SHORT",
        "qty": 15,
        "superstition": "Havertown is living in the 90s. Truist Park owns you.",
        "opcode": "HYPD"
    }
]


def get_live_vfs_context():
    """Extracts live gameday triggers from /dev/shm/faas_vfs if available."""
    context = {}
    try:
        bp_trigger = VFS_FAAS / "blood_pressure" / "trigger_cause.txt"
        if bp_trigger.exists():
            context["bp_trigger"] = bp_trigger.read_text(encoding="utf-8").strip()

        reaction_file = VFS_FAAS / "chaos_center" / "last_degen_reaction.txt"
        if reaction_file.exists():
            context["last_reaction"] = reaction_file.read_text(encoding="utf-8").strip()

        if KALSHI_ODDS_FILE.exists():
            kalshi = json.loads(KALSHI_ODDS_FILE.read_text(encoding="utf-8"))
            context["kalshi_markets"] = len(kalshi.get("markets", {}))
    except Exception:
        pass
    return context


def feed_market_tick():
    if not DB_PATH.exists():
        print(f"[!] Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    cur = conn.cursor()

    # 1. Pick a random degen trade
    play = dict(random.choice(DEGEN_PLAYS))
    vfs_ctx = get_live_vfs_context()
    if vfs_ctx.get("bp_trigger"):
        play["vfs_trigger"] = vfs_ctx["bp_trigger"]
    
    # 2. Get contract details
    cur.execute("SELECT current_price_cents FROM market_contracts WHERE contract_id = ?", (play["contract_id"],))
    res = cur.fetchone()
    price = res[0] if res else 50
    total_cost = (play["qty"] * price) / 100.0

    trade_id = f"TRD-{os.urandom(4).hex().upper()}"
    
    # 3. Insert Trade
    cur.execute("""
        INSERT INTO citizen_trades (
            trade_id, citizen_id, contract_id, side, position_type,
            quantity, price_cents, total_cost, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (trade_id, play["citizen_id"], play["contract_id"], play["side"], play["pos_type"], play["qty"], price, total_cost))

    # 4. Update Citizen Bankroll & BP
    cur.execute("""
        UPDATE emergent_citizens
        SET cash_balance = cash_balance - ?,
            portfolio_value = portfolio_value + ?,
            systolic_bp = MIN(210, systolic_bp + ?),
            status = 'TILTED',
            last_active_ts = CURRENT_TIMESTAMP
        WHERE citizen_id = ?
    """, (total_cost, total_cost, random.randint(3, 8), play["citizen_id"]))

    # 5. Update Contract Volume
    cur.execute("""
        UPDATE market_contracts
        SET total_volume = total_volume + ?,
            open_interest = open_interest + ?
        WHERE contract_id = ?
    """, (play["qty"], play["qty"], play["contract_id"]))

    # 6. Inject High-Entropy Event so daemon continues cycling (source/category satisfy SQLite CHECK constraint)
    event_id = f"EVT-{os.urandom(4).hex().upper()}"
    headline = f"{play['citizen_id']} triggered: {play['superstition']}"
    cur.execute("""
        INSERT INTO event_stream (
            event_id, source, category, headline, raw_payload,
            volatility_score, processed, created_at
        ) VALUES (?, 'ORACLE_INJECT', 'DIVINE_SHOCK', ?, ?, 0.85, 0, CURRENT_TIMESTAMP)
    """, (event_id, headline, json.dumps(play)))

    conn.commit()
    conn.close()

    # 7. Sync 4-byte sentiment opcode and reaction to VFS fast-plane
    try:
        chaos_dir = VFS_FAAS / "chaos_center"
        chaos_dir.mkdir(parents=True, exist_ok=True)
        opcode = play.get("opcode", "SICK")
        (chaos_dir / "degen_sentiment_opcode.txt").write_text(f"{opcode}\n", encoding="utf-8")
        (chaos_dir / "last_degen_reaction.txt").write_text(f"{headline}\n", encoding="utf-8")
    except Exception:
        pass

    print(f"[TRADE EXECUTED] {play['citizen_id']} -> {play['ticker']} ({play['qty']} shares @ {price}¢) | {play['superstition']}")


if __name__ == "__main__":
    feed_market_tick()
