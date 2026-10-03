#!/usr/bin/env python3
"""
SICKO Burst Trading State Machine - 30-Day Metal Soak Engine
Path: /home/james/SovereignOS/scripts/sicko_engine.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)
"""

import sqlite3
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

SOVEREIGN_ROOT = Path("/home/james/SovereignOS")
DATA_DIR = SOVEREIGN_ROOT / "data"
DB_PATH = DATA_DIR / "sicko_burst.db"
AUDIT_LOG_DIR = Path("/home/james/sovereign_inbox/today/sicko_audit")

TP_THRESHOLD = 0.050   # +5.0%
SL_THRESHOLD = -0.025  # -2.5%
MAX_HOLD_DAYS = 10
SLOT_CAPITAL = 1000.00
TOTAL_SLOTS = 10

@dataclass
class PositionCheckResult:
    slot_id: int
    symbol: str
    action: str  # 'HOLD', 'TAKE_PROFIT', 'STOP_LOSS', 'TIME_EXPIRE'
    pnl_percent: float
    pnl_usd: float
    current_price: float

class SickoStateMachine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_slots (
                slot_id INTEGER PRIMARY KEY CHECK(slot_id BETWEEN 1 AND 10),
                status TEXT NOT NULL CHECK(status IN ('VACANT', 'ACTIVE')),
                current_symbol TEXT,
                entry_timestamp TEXT,
                entry_price REAL,
                shares REAL,
                allocated_capital REAL DEFAULT 1000.00,
                peak_price REAL,
                holding_days INTEGER DEFAULT 0,
                target_tp REAL,
                target_sl REAL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS burst_trade_ledger (
                trade_id TEXT PRIMARY KEY,
                slot_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                entry_timestamp TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_timestamp TEXT,
                exit_price REAL,
                shares REAL NOT NULL,
                pnl_usd REAL,
                pnl_percent REAL,
                exit_reason TEXT CHECK(exit_reason IN ('TAKE_PROFIT_5PCT', 'STOP_LOSS_2.5PCT', 'TIME_HORIZON_10D', 'MANUAL_ABORT')),
                holding_days INTEGER,
                catalyst_drop_id TEXT,
                swarm_sentiment_score REAL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS candidate_queue (
                symbol TEXT PRIMARY KEY,
                rank_score REAL NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
                discovered_timestamp TEXT NOT NULL,
                catalyst_source TEXT,
                status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'DEPLOYED', 'EXPIRED'))
            );
            """)
            # Initialize 10 vacant slots if empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM portfolio_slots;")
            if cur.fetchone()[0] == 0:
                for i in range(1, TOTAL_SLOTS + 1):
                    conn.execute("INSERT INTO portfolio_slots (slot_id, status) VALUES (?, 'VACANT')", (i,))

    def evaluate_active_slots(self, current_market_prices: Dict[str, float]) -> List[PositionCheckResult]:
        """
        Cold execution loop: evaluates all active positions against +5.0% / -2.5% / Day 10.
        """
        results = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            slots = conn.execute("SELECT * FROM portfolio_slots WHERE status = 'ACTIVE'").fetchall()

            for slot in slots:
                sym = slot["current_symbol"]
                if sym not in current_market_prices:
                    continue

                curr_price = float(current_market_prices[sym])
                entry_price = float(slot["entry_price"])
                shares = float(slot["shares"])
                holding_days = int(slot["holding_days"])

                pnl_pct = (curr_price - entry_price) / entry_price
                pnl_usd = (curr_price - entry_price) * shares

                action = "HOLD"
                exit_reason = None

                if pnl_pct >= TP_THRESHOLD:
                    action = "TAKE_PROFIT"
                    exit_reason = "TAKE_PROFIT_5PCT"
                elif pnl_pct <= SL_THRESHOLD:
                    action = "STOP_LOSS"
                    exit_reason = "STOP_LOSS_2.5PCT"
                elif holding_days >= MAX_HOLD_DAYS:
                    action = "TIME_EXPIRE"
                    exit_reason = "TIME_HORIZON_10D"

                if action != "HOLD":
                    trade_id = f"TRD_{slot['slot_id']}_{sym}_{now_str[:10]}_{int(datetime.datetime.now().timestamp())}"
                    conn.execute("""
                        INSERT INTO burst_trade_ledger (
                            trade_id, slot_id, symbol, entry_timestamp, entry_price,
                            exit_timestamp, exit_price, shares, pnl_usd, pnl_percent,
                            exit_reason, holding_days
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_id, slot["slot_id"], sym, slot["entry_timestamp"],
                        entry_price, now_str, curr_price, shares, pnl_usd, pnl_pct,
                        exit_reason, holding_days
                    ))

                    conn.execute("""
                        UPDATE portfolio_slots 
                        SET status = 'VACANT', current_symbol = NULL, entry_timestamp = NULL,
                            entry_price = NULL, shares = NULL, peak_price = NULL, holding_days = 0,
                            target_tp = NULL, target_sl = NULL
                        WHERE slot_id = ?
                    """, (slot["slot_id"],))

                results.append(PositionCheckResult(
                    slot_id=slot["slot_id"],
                    symbol=sym,
                    action=action,
                    pnl_percent=pnl_pct,
                    pnl_usd=pnl_usd,
                    current_price=curr_price
                ))

        return results

    def fill_vacant_slots(self, candidate_queue: List[Dict[str, Any]]) -> int:
        """
        Executes 'Swap 15' rotation: allocates top ranked candidates to vacant slots.
        """
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        filled_count = 0

        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            vacant_slots = conn.execute("SELECT slot_id FROM portfolio_slots WHERE status = 'VACANT' ORDER BY slot_id ASC").fetchall()

            cand_idx = 0
            for slot in vacant_slots:
                if cand_idx >= len(candidate_queue):
                    break
                candidate = candidate_queue[cand_idx]
                sym = candidate["symbol"]
                price = float(candidate["entry_price"])
                shares = SLOT_CAPITAL / price
                tp = price * (1.0 + TP_THRESHOLD)
                sl = price * (1.0 + SL_THRESHOLD)

                conn.execute("""
                    UPDATE portfolio_slots 
                    SET status = 'ACTIVE', current_symbol = ?, entry_timestamp = ?,
                        entry_price = ?, shares = ?, peak_price = ?, holding_days = 0,
                        target_tp = ?, target_sl = ?
                    WHERE slot_id = ?
                """, (sym, now_str, price, shares, price, tp, sl, slot["slot_id"]))

                cand_idx += 1
                filled_count += 1

        return filled_count

    def increment_holding_days(self):
        """Called once per market day close to advance hold day counters."""
        with self._get_conn() as conn:
            conn.execute("UPDATE portfolio_slots SET holding_days = holding_days + 1 WHERE status = 'ACTIVE'")

    def get_portfolio_summary(self, current_market_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Computes current balance, realized/unrealized P&L, and win/loss statistics."""
        current_market_prices = current_market_prices or {}
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row

            slots = conn.execute("SELECT * FROM portfolio_slots ORDER BY slot_id ASC").fetchall()
            trades = conn.execute("SELECT * FROM burst_trade_ledger").fetchall()

            realized_pnl = sum(t["pnl_usd"] for t in trades)
            total_wins = sum(1 for t in trades if t["pnl_usd"] > 0)
            total_losses = sum(1 for t in trades if t["pnl_usd"] <= 0)
            win_rate = (total_wins / len(trades) * 100.0) if trades else 0.0

            unrealized_pnl = 0.0
            active_count = 0
            for s in slots:
                if s["status"] == "ACTIVE":
                    active_count += 1
                    sym = s["current_symbol"]
                    if sym in current_market_prices:
                        curr = current_market_prices[sym]
                        unrealized_pnl += (curr - s["entry_price"]) * s["shares"]

            total_portfolio_value = 10000.00 + realized_pnl + unrealized_pnl

            return {
                "initial_bankroll": 10000.00,
                "realized_pnl_usd": round(realized_pnl, 2),
                "unrealized_pnl_usd": round(unrealized_pnl, 2),
                "total_portfolio_value": round(total_portfolio_value, 2),
                "total_trades": len(trades),
                "wins": total_wins,
                "losses": total_losses,
                "win_rate_pct": round(win_rate, 1),
                "active_positions": active_count,
                "vacant_positions": TOTAL_SLOTS - active_count,
                "slots": [dict(s) for s in slots]
            }
