#!/usr/bin/env python3
"""
SICKO Burst Trading State Machine - 30-Day Metal Soak Engine (Hardened v2)
Path: /home/james/stacklabs/scripts/sicko_engine.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)
Audited by: Qwen 2.5 Systems Crucible
"""

import sqlite3
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal, ROUND_HALF_UP

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
DATA_DIR = SOVEREIGN_ROOT / "data"
DB_PATH = DATA_DIR / "sicko_burst.db"
AUDIT_LOG_DIR = Path("/home/james/sovereign_inbox/today/sicko_audit")

# Strict thresholds using Decimal to prevent floating-point boundary drift
TP_THRESHOLD = Decimal('0.050')   # +5.0%
SL_THRESHOLD = Decimal('-0.025')  # -2.5%
MAX_HOLD_DAYS = 10
SLOT_CAPITAL = Decimal('1000.00')
TOTAL_SLOTS = 10

@dataclass
class PositionCheckResult:
    slot_id: int
    symbol: str
    action: str  # 'HOLD', 'TAKE_PROFIT', 'STOP_LOSS', 'TIME_EXPIRE'
    pnl_percent: str
    pnl_usd: str
    current_price: str
    slippage_delta_usd: str

class SickoStateMachine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_slots (
                slot_id INTEGER PRIMARY KEY CHECK(slot_id BETWEEN 1 AND 10),
                status TEXT NOT NULL CHECK(status IN ('VACANT', 'ACTIVE')),
                current_symbol TEXT,
                entry_timestamp TEXT,
                entry_price TEXT,
                shares TEXT,
                allocated_capital TEXT DEFAULT '1000.00',
                peak_price TEXT,
                holding_days INTEGER DEFAULT 0,
                target_tp TEXT,
                target_sl TEXT
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS burst_trade_ledger (
                trade_id TEXT PRIMARY KEY,
                slot_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                entry_timestamp TEXT NOT NULL,
                entry_price TEXT NOT NULL,
                exit_timestamp TEXT,
                exit_price TEXT,
                shares TEXT NOT NULL,
                pnl_usd TEXT,
                pnl_percent TEXT,
                exit_reason TEXT CHECK(exit_reason IN ('TAKE_PROFIT_5PCT', 'STOP_LOSS_2.5PCT', 'TIME_HORIZON_10D', 'MANUAL_ABORT')),
                holding_days INTEGER,
                slippage_delta_usd TEXT DEFAULT '0.00',
                catalyst_drop_id TEXT,
                swarm_sentiment_score TEXT
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

            # Migration: Ensure slippage_delta_usd exists if upgrading older db
            try:
                conn.execute("ALTER TABLE burst_trade_ledger ADD COLUMN slippage_delta_usd TEXT DEFAULT '0.00';")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Initialize 10 vacant slots if empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM portfolio_slots;")
            if cur.fetchone()[0] == 0:
                for i in range(1, TOTAL_SLOTS + 1):
                    conn.execute("INSERT INTO portfolio_slots (slot_id, status) VALUES (?, 'VACANT')", (i,))
        finally:
            conn.close()

    def evaluate_active_slots(self, current_market_prices: Dict[str, Union[float, Decimal, str]], timestamp: Optional[str] = None) -> List[PositionCheckResult]:
        """
        Cold execution loop: evaluates all active positions against +5.0% / -2.5% / Day 10.
        Uses BEGIN IMMEDIATE transaction to prevent slot hijacking and race conditions.
        Uses Decimal precision for exact penny and percentage accuracy.
        """
        results = []
        now_str = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.row_factory = sqlite3.Row
            slots = cur.execute("SELECT * FROM portfolio_slots WHERE status = 'ACTIVE'").fetchall()

            for slot in slots:
                sym = slot["current_symbol"]
                if sym not in current_market_prices:
                    continue

                curr_price = Decimal(str(current_market_prices[sym]))
                entry_price = Decimal(str(slot["entry_price"]))
                shares = Decimal(str(slot["shares"]))
                holding_days = int(slot["holding_days"])

                pnl_pct = (curr_price - entry_price) / entry_price
                pnl_usd = (curr_price - entry_price) * shares

                action = "HOLD"
                exit_reason = None
                slippage_delta = Decimal('0.00')
                final_exit_price = curr_price

                if pnl_pct >= TP_THRESHOLD:
                    action = "TAKE_PROFIT"
                    exit_reason = "TAKE_PROFIT_5PCT"
                elif pnl_pct <= SL_THRESHOLD:
                    action = "STOP_LOSS"
                    exit_reason = "STOP_LOSS_2.5PCT"
                    theoretical_stop_price = entry_price * (Decimal('1') + SL_THRESHOLD)
                    slippage_delta = (final_exit_price - theoretical_stop_price) * shares
                elif holding_days >= MAX_HOLD_DAYS:
                    action = "TIME_EXPIRE"
                    exit_reason = "TIME_HORIZON_10D"

                if action != "HOLD":
                    trade_id = f"TRD_{slot['slot_id']}_{sym}_{now_str[:10]}_{int(datetime.datetime.now().timestamp())}"
                    cur.execute("""
                        INSERT INTO burst_trade_ledger (
                            trade_id, slot_id, symbol, entry_timestamp, entry_price,
                            exit_timestamp, exit_price, shares, pnl_usd, pnl_percent,
                            exit_reason, holding_days, slippage_delta_usd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_id,
                        slot["slot_id"],
                        sym,
                        str(slot["entry_timestamp"]),
                        str(entry_price),
                        now_str,
                        str(final_exit_price),
                        str(shares),
                        str(pnl_usd.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                        str(pnl_pct.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
                        exit_reason,
                        holding_days,
                        str(slippage_delta.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                    ))

                    cur.execute("""
                        UPDATE portfolio_slots 
                        SET status = 'VACANT', current_symbol = NULL, entry_timestamp = NULL,
                            entry_price = NULL, shares = NULL, peak_price = NULL, holding_days = 0,
                            target_tp = NULL, target_sl = NULL
                        WHERE slot_id = ? AND status = 'ACTIVE'
                    """, (slot["slot_id"],))

                results.append(PositionCheckResult(
                    slot_id=slot["slot_id"],
                    symbol=sym,
                    action=action,
                    pnl_percent=str(pnl_pct.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
                    pnl_usd=str(pnl_usd.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                    current_price=str(curr_price),
                    slippage_delta_usd=str(slippage_delta.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                ))

            cur.execute("COMMIT")
        except Exception as e:
            cur.execute("ROLLBACK")
            conn.close()
            raise e
        finally:
            conn.close()

        return results

    def fill_vacant_slots(self, candidate_queue: List[Dict[str, Any]], timestamp: Optional[str] = None) -> int:
        """
        Executes 'Swap 15' rotation: allocates top ranked candidates to vacant slots.
        Uses BEGIN IMMEDIATE transaction to prevent slot allocation collisions.
        """
        now_str = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        filled_count = 0
        conn = self._get_conn()
        cur = conn.cursor()

        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.row_factory = sqlite3.Row
            vacant_slots = cur.execute("SELECT slot_id FROM portfolio_slots WHERE status = 'VACANT' ORDER BY slot_id ASC").fetchall()

            cand_idx = 0
            for slot in vacant_slots:
                if cand_idx >= len(candidate_queue):
                    break
                candidate = candidate_queue[cand_idx]
                sym = candidate["symbol"]
                entry_ts = candidate.get("entry_timestamp", now_str)
                price = Decimal(str(candidate["entry_price"]))
                shares = (SLOT_CAPITAL / price).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                tp = (price * (Decimal('1') + TP_THRESHOLD)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                sl = (price * (Decimal('1') + SL_THRESHOLD)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                cur.execute("""
                    UPDATE portfolio_slots 
                    SET status = 'ACTIVE', current_symbol = ?, entry_timestamp = ?,
                        entry_price = ?, shares = ?, peak_price = ?, holding_days = 0,
                        target_tp = ?, target_sl = ?
                    WHERE slot_id = ? AND status = 'VACANT'
                """, (sym, entry_ts, str(price), str(shares), str(price), str(tp), str(sl), slot["slot_id"]))

                cand_idx += 1
                filled_count += 1

            cur.execute("COMMIT")
        except Exception as e:
            cur.execute("ROLLBACK")
            conn.close()
            raise e
        finally:
            conn.close()

        return filled_count

    def increment_holding_days(self):
        """Called once per market day close to advance hold day counters."""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE portfolio_slots SET holding_days = holding_days + 1 WHERE status = 'ACTIVE'")
        finally:
            conn.close()

    def get_portfolio_summary(self, current_market_prices: Optional[Dict[str, Union[float, Decimal, str]]] = None) -> Dict[str, Any]:
        """Computes current balance, realized/unrealized P&L, and win/loss statistics using Decimal math."""
        current_market_prices = current_market_prices or {}
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row

            slots = conn.execute("SELECT * FROM portfolio_slots ORDER BY slot_id ASC").fetchall()
            trades = conn.execute("SELECT * FROM burst_trade_ledger").fetchall()

            realized_pnl = sum((Decimal(str(t["pnl_usd"])) for t in trades), Decimal('0.00'))
            total_wins = sum(1 for t in trades if Decimal(str(t["pnl_usd"])) > Decimal('0.00'))
            total_losses = sum(1 for t in trades if Decimal(str(t["pnl_usd"])) <= Decimal('0.00'))
            win_rate = (Decimal(str(total_wins)) / Decimal(str(len(trades))) * Decimal('100.0')) if trades else Decimal('0.0')

            unrealized_pnl = Decimal('0.00')
            active_count = 0
            for s in slots:
                if s["status"] == "ACTIVE":
                    active_count += 1
                    sym = s["current_symbol"]
                    if sym in current_market_prices:
                        curr = Decimal(str(current_market_prices[sym]))
                        entry = Decimal(str(s["entry_price"]))
                        sh = Decimal(str(s["shares"]))
                        unrealized_pnl += (curr - entry) * sh

            total_portfolio_value = Decimal('10000.00') + realized_pnl + unrealized_pnl

            return {
                "initial_bankroll": 10000.00,
                "realized_pnl_usd": float(realized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                "unrealized_pnl_usd": float(unrealized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                "total_portfolio_value": float(total_portfolio_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                "total_trades": len(trades),
                "wins": total_wins,
                "losses": total_losses,
                "win_rate_pct": float(win_rate.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)),
                "active_positions": active_count,
                "vacant_positions": TOTAL_SLOTS - active_count,
                "slots": [dict(s) for s in slots]
            }
        finally:
            conn.close()
