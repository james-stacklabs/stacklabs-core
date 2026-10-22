#!/usr/bin/env python3
"""
scripts/verify_emergent_society_engine.py
=============================================================================
AUTOMATED VERIFICATION SUITE & SMOKE TESTS FOR EMERGENT SOCIETY ENGINE
=============================================================================
Asserts database creation in WAL mode, citizen seeding, hemodynamic formulas,
Tums burn rate triggers, high-entropy event activation, market order matching,
and Divine Oracle query/injection functionality.
"""

import os
import sys
import json
import sqlite3
import unittest
import time
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from emergent_society_daemon import init_database, SimulationEngine, get_db_connection
from core.society_oracle import SocietyOracle

TEST_DB_PATH = os.environ.get("EMERGENT_SOCIETY_DB", "/tmp/test_emergent_society.db")
TEST_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dna/migrations/20261002_emergent_society_schema.sql"
)


class TestEmergentSocietyEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["EMERGENT_SOCIETY_DB"] = TEST_DB_PATH
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(TEST_DB_PATH + ext):
                os.remove(TEST_DB_PATH + ext)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass
        for ext in ["-wal", "-shm"]:
            if os.path.exists(TEST_DB_PATH + ext):
                try:
                    os.remove(TEST_DB_PATH + ext)
                except OSError:
                    pass

    def test_01_schema_initialization_and_wal_mode(self):
        """Asserts database initializes with WAL mode and foreign keys enabled."""
        init_database(TEST_DB_PATH, TEST_SCHEMA_PATH)
        self.assertTrue(os.path.exists(TEST_DB_PATH), "Database file must exist.")
        with get_db_connection(TEST_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            journal_mode = cur.fetchone()[0].upper()
            self.assertEqual(journal_mode, "WAL", "Database must be in WAL mode.")
            cur.execute("PRAGMA foreign_keys;")
            fk = cur.fetchone()[0]
            self.assertEqual(fk, 1, "Foreign keys must be enabled.")

    def test_02_citizen_seed_data(self):
        """Asserts the 6 canonical bleacher archetypes are seeded correctly."""
        with get_db_connection(TEST_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT citizen_id, name, archetype, systolic_bp, tums_inventory FROM emergent_citizens")
            rows = cur.fetchall()
            citizens = {r["citizen_id"]: dict(r) for r in rows}
            self.assertIn("CIT-001-BARF", citizens)
            self.assertIn("CIT-002-SAMMY", citizens)
            self.assertIn("CIT-003-MIKE", citizens)
            self.assertIn("CIT-004-SOUTHSIDE", citizens)
            self.assertIn("CIT-005-IVAN", citizens)
            self.assertIn("CIT-006-DAN", citizens)
            barf = citizens["CIT-001-BARF"]
            self.assertEqual(barf["name"], "Barf")
            self.assertGreaterEqual(barf["systolic_bp"], 120)
            self.assertEqual(barf["tums_inventory"], 48)

    def test_03_hemodynamic_formula_and_tums_burn(self):
        """Asserts hemodynamic shifts and the Tums consumption dampening trigger."""
        engine = SimulationEngine(db_path=TEST_DB_PATH)
        barf = {
            "citizen_id": "CIT-001-BARF",
            "name": "Barf",
            "resting_hr": 88,
            "cardiac_output": 1.45,
            "scar_tissue_index": 0.98,
            "systolic_bp": 150,
            "diastolic_bp": 95,
            "tums_inventory": 10,
            "tums_consumed_today": 0,
            "status": "WATCHING",
            "cash_balance": 1000.0
        }
        hemo = engine.evaluate_hemodynamics(barf, event_volatility=0.95, is_negative_impact=True)
        self.assertGreater(hemo["bp_delta"], 0, "Negative high-volatility event must spike BP.")
        self.assertEqual(hemo["tums_consumed"], 2, "Acute systolic spike >= 155 must burn 2 Tums.")
        self.assertEqual(hemo["tums_inventory"], 8, "Tums inventory must decrement by 2.")
        self.assertEqual(hemo["tums_consumed_today"], 2, "Daily Tums counter must increment by 2.")
        self.assertIn(hemo["new_status"], ("PANICKED", "RANTING"), "High BP must transition state to PANICKED or RANTING.")

    def test_04_high_entropy_event_ingestion_and_tick(self):
        """Asserts unprocessed events trigger dialogue, state updates, and trades."""
        oracle = SocietyOracle(db_path=TEST_DB_PATH)
        inj_res = oracle.inject_event(
            headline="Aaron Rodgers throws pick-six in overtime; Steelers win 27-24",
            category="TURNOVER",
            volatility_score=0.92,
            raw_payload={"game": "PIT vs CLE", "down": "3rd and 12"}
        )
        self.assertIn("EVT-", inj_res["event_id"])
        engine = SimulationEngine(db_path=TEST_DB_PATH)
        engine.run_tick()
        with get_db_connection(TEST_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT processed FROM event_stream WHERE event_id = ?", (inj_res["event_id"],))
            self.assertEqual(cur.fetchone()[0], 1, "Event must be marked processed.")
            cur.execute("SELECT COUNT(*) FROM society_dialogue")
            dialogue_count = cur.fetchone()[0]
            self.assertGreaterEqual(dialogue_count, 6, "All 6 citizens must have generated dialogue.")
            cur.execute("SELECT COUNT(*) FROM citizen_memories WHERE event_id = ?", (inj_res["event_id"],))
            mem_count = cur.fetchone()[0]
            self.assertGreater(mem_count, 0, "High salience event must record memories.")
            cur.execute("SELECT COUNT(*) FROM citizen_trades")
            trade_count = cur.fetchone()[0]
            self.assertGreater(trade_count, 0, "High volatility must trigger market trades.")

    def test_05_divine_oracle_query(self):
        """Asserts the Divine Oracle can query society state and audit the interaction."""
        oracle = SocietyOracle(db_path=TEST_DB_PATH)
        res = oracle.query("Who in the dive bar has the most critical blood pressure right now?")
        self.assertIn("query_id", res)
        self.assertIn("response", res)
        self.assertGreater(len(res["response"]), 20)
        self.assertEqual(res["citizens_audited"], 6)
        with get_db_connection(TEST_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM oracle_audit_log WHERE query_id = ?", (res["query_id"],))
            self.assertEqual(cur.fetchone()[0], 1, "Oracle query must be logged in oracle_audit_log.")


def run_verification():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEmergentSocietyEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n[+] ALL SMOKE TESTS PASSED (100% GROUNDED STATE CONFIRMED).")


if __name__ == "__main__":
    run_verification()
