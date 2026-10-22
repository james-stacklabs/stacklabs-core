#!/usr/bin/env python3
"""
scripts/core/society_oracle.py
=============================================================================
DIVINE ORACLE INTERFACE FOR THE AUTONOMOUS EMERGENT SOCIETY SIMULATION
=============================================================================
Provides natural-language query capabilities and divine environmental shock
injection into data/emergent_society.db. Adheres strictly to Invariant 23
(Cloud inference via google.genai, zero local heavy LLM execution on Clio).
"""

import os
import sys
import json
import sqlite3
import argparse
from typing import Dict, Any, Optional

if not os.environ.get("GEMINI_API_KEY") and os.path.exists("/home/james/stacklabs/.env"):
    try:
        from dotenv import load_dotenv
        load_dotenv("/home/james/stacklabs/.env")
    except ImportError:
        pass

try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

DB_PATH = os.environ.get("EMERGENT_SOCIETY_DB", "/home/james/stacklabs/data/emergent_society.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class SocietyOracle:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        if HAS_GENAI_SDK and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.client = None

    def _ensure_schema(self):
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "dna/migrations/20261002_emergent_society_schema.sql"
        )
        if os.path.exists(schema_path):
            with get_db_connection(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emergent_citizens'")
                if not cur.fetchone():
                    with open(schema_path, "r", encoding="utf-8") as f:
                        conn.executescript(f.read())
                    conn.commit()


    def get_society_snapshot(self) -> Dict[str, Any]:
        """Reads current real-time state across all tables for prompt grounding."""
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT citizen_id, name, archetype, fandom, cash_balance, 
                       systolic_bp, diastolic_bp, resting_hr, tums_inventory, 
                       tums_consumed_today, status, superstition_level 
                FROM emergent_citizens
                ORDER BY systolic_bp DESC
            """)
            citizens = [dict(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT d.dialogue_id, c.name as speaker, d.message_text, 
                       d.emotional_tone, d.bp_delta, d.created_at
                FROM society_dialogue d
                JOIN emergent_citizens c ON d.speaker_id = c.citizen_id
                ORDER BY d.created_at DESC LIMIT 10
            """)
            recent_dialogue = [dict(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT contract_id, ticker, name, current_price_cents, 
                       total_volume, open_interest, status 
                FROM market_contracts 
                WHERE status = 'OPEN'
            """)
            contracts = [dict(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT event_id, source, category, headline, volatility_score, created_at
                FROM event_stream
                ORDER BY created_at DESC LIMIT 5
            """)
            recent_events = [dict(row) for row in cur.fetchall()]

        return {
            "citizens": citizens,
            "recent_dialogue": recent_dialogue,
            "contracts": contracts,
            "recent_events": recent_events
        }

    def query(self, question: str) -> Dict[str, Any]:
        """Executes a divine query against the simulation state using Gemini 2.5."""
        snapshot = self.get_society_snapshot()
        state_context = json.dumps(snapshot, indent=2)

        prompt = f"""You are the Divine Oracle for an autonomous emergent society simulation: 'Catnip Wars II: The Degenerate Bleacher Simulacra'.
The simulation runs on real-world sports trauma, hemodynamic blood pressure spikes, and degenerate betting contracts in a dive bar.

CURRENT SIMULATION STATE LEDGER:
{state_context}

PILOT ORACLE QUERY:
"{question}"

Analyze the simulation state with razor-sharp insight, zero academic fluff, and zero corporate PR boilerplate.
Synthesize the citizens' emotional trajectories, hemodynamic risks, betting market exposure, and friction points.
Deliver a direct, grounded assessment suitable for the Pilot."""

        tokens_consumed = 0
        system_response = ""
        reasoning = "State synthesized from SQLite WAL snapshot."

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt
                )
                system_response = response.text
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    tokens_consumed = getattr(response.usage_metadata, 'total_token_count', 0)
            except Exception as e:
                system_response = f"[Oracle API Degraded: {str(e)}]\nFallback Synthesis: {self._heuristic_oracle(question, snapshot)}"
        else:
            system_response = f"[Local Heuristic Mode (Set GEMINI_API_KEY for Cloud Synthesis)]\n{self._heuristic_oracle(question, snapshot)}"

        query_id = f"QRY-{os.urandom(4).hex().upper()}"
        with get_db_connection(self.db_path) as conn:
            conn.execute("""
                INSERT INTO oracle_audit_log (
                    query_id, query_type, input_text, llm_reasoning,
                    system_response, state_deltas, tokens_consumed, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (query_id, 'NATURAL_LANGUAGE_QUERY', question, reasoning, system_response, None, tokens_consumed))
            conn.commit()

        return {
            "query_id": query_id,
            "question": question,
            "response": system_response,
            "tokens_consumed": tokens_consumed,
            "citizens_audited": len(snapshot["citizens"])
        }

    def inject_event(self, headline: str, category: str = "DIVINE_SHOCK",
                     volatility_score: float = 0.85, raw_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Injects a divine event or environmental shock into the simulation stream."""
        event_id = f"EVT-{os.urandom(4).hex().upper()}"
        payload_str = json.dumps(raw_payload or {"origin": "pilot_divine_oracle"})

        with get_db_connection(self.db_path) as conn:
            conn.execute("""
                INSERT INTO event_stream (
                    event_id, source, category, headline, raw_payload,
                    volatility_score, processed, created_at
                ) VALUES (?, 'ORACLE_INJECT', ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            """, (event_id, category, headline, payload_str, volatility_score))

            query_id = f"INJ-{os.urandom(4).hex().upper()}"
            conn.execute("""
                INSERT INTO oracle_audit_log (
                    query_id, query_type, input_text, llm_reasoning,
                    system_response, state_deltas, tokens_consumed, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            """, (query_id, 'EVENT_INJECTION', headline, f"Injected into event_stream as {event_id}",
                  f"Event {event_id} queued with volatility {volatility_score}", payload_str))
            conn.commit()

        return {
            "event_id": event_id,
            "headline": headline,
            "category": category,
            "volatility_score": volatility_score,
            "status": "QUEUED_FOR_HIGH_ENTROPY_TICK"
        }

    def _heuristic_oracle(self, question: str, snapshot: Dict[str, Any]) -> str:
        """Deterministic grounding engine when running offline without Cloud API."""
        citizens = snapshot.get("citizens", [])
        highest_bp = max(citizens, key=lambda c: c["systolic_bp"]) if citizens else None
        lowest_cash = min(citizens, key=lambda c: c["cash_balance"]) if citizens else None
        active_contracts = len(snapshot.get("contracts", []))

        lines = [
            f"Barroom Census: {len(citizens)} active citizens on metal.",
            f"Acute Hemodynamic Alert: {highest_bp['name']} ({highest_bp['fandom']}) leads in cardiovascular strain at {highest_bp['systolic_bp']}/{highest_bp['diastolic_bp']} mmHg (Tums today: {highest_bp['tums_consumed_today']})." if highest_bp else "No citizen telemetry.",
            f"Liquidation Watch: {lowest_cash['name']} is closest to insolvency with ${lowest_cash['cash_balance']:.2f} remaining bankroll." if lowest_cash else "No cash balances.",
            f"Market Depth: {active_contracts} open binary event contracts.",
            f"Ground Truth Status: The bleacher collective is currently reacting to recent sports entropy with zero synthetic lore."
        ]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Divine Oracle CLI for Emergent Society Simulation")
    parser.add_argument("--query", "-q", type=str, help="Natural language query to pose to the society")
    parser.add_argument("--inject", "-i", type=str, help="Headline of divine event to inject")
    parser.add_argument("--category", "-c", type=str, default="DIVINE_SHOCK", help="Event category")
    parser.add_argument("--volatility", "-v", type=float, default=0.85, help="Event volatility score (0.0 to 1.0)")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to SQLite database")
    args = parser.parse_args()

    oracle = SocietyOracle(db_path=args.db)

    if args.inject:
        res = oracle.inject_event(headline=args.inject, category=args.category, volatility_score=args.volatility)
        print(json.dumps(res, indent=2))
    elif args.query:
        res = oracle.query(question=args.query)
        print(f"\n[ORACLE AUDIT: {res['query_id']} | TOKENS: {res['tokens_consumed']}]")
        print("=" * 60)
        print(res["response"])
        print("=" * 60)
    else:
        snapshot = oracle.get_society_snapshot()
        print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
