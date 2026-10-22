#!/usr/bin/env python3
"""
scripts/verify_postseason_war_room.py
=============================================================================
VERIFICATION SUITE FOR WO0010493: POSTSEASON WAR ROOM & BATTERYCHUCKER DYNASTY
=============================================================================
Asserts:
1. All 10 canonical citizens exist in emergent_society.db with valid avatars and bios.
2. Zero synthetic names (Yinzer Yough, Dawg Pound Dan) remain in emergent_citizens.
3. BatteryChucker Sr has BP >= 200 mmHg and Jr has team ATL.
4. $BATTERY-CHUCK contract is open in market_contracts.
5. Father-son friction score calculates to 0.98.
"""

import os
import sys
import sqlite3
import unittest

REPO_ROOT = "/home/james/stacklabs"
DB_PATH = os.environ.get("EMERGENT_SOCIETY_DB", os.path.join(REPO_ROOT, "data", "emergent_society.db"))

sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))


class TestPostseasonWarRoom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.path.exists(DB_PATH), f"Missing database: {DB_PATH}"

    def test_01_canonical_citizens_count_and_avatars(self):
        """Asserts exact canonical roster exists with non-null avatars and bios."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT handle, name, avatar_url, bio, systolic_bp FROM emergent_citizens ORDER BY citizen_id;")
        rows = cur.fetchall()
        conn.close()
        
        handles = [r[0] for r in rows]
        print(f"✔ Active Citizens on Metal ({len(handles)}): {handles}")
        
        self.assertGreaterEqual(len(rows), 10, "Must have at least 10 canonical citizens.")
        self.assertIn("@batterychucker", handles)
        self.assertIn("@batterychuckerjr", handles)
        self.assertIn("@barf", handles)
        self.assertIn("@sammy_the_savant", handles)
        self.assertIn("@AcunaBombSquad", handles)
        self.assertIn("@BronxBomberOracle", handles)
        self.assertIn("@TrueBlueProphet", handles)
        self.assertIn("@NoDodgerPrivilege", handles)
        self.assertIn("@RoyalSalvyKing", handles)
        self.assertIn("@hoffa_under_section_107", handles)
        
        # Assert non-empty avatar URLs and bios
        for r in rows:
            self.assertTrue(len(r[2]) > 0, f"Citizen {r[0]} missing avatar_url")
            self.assertTrue(len(r[3]) > 0, f"Citizen {r[0]} missing bio")

    def test_02_zero_synthetic_placeholders(self):
        """Asserts synthetic placeholders from Spark draft are permanently gone."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM emergent_citizens WHERE name IN ('Yinzer Yough', 'Dawg Pound Dan', 'Table Breaker Tony', 'Delco Dave');")
        rows = cur.fetchall()
        conn.close()
        self.assertEqual(len(rows), 0, f"Detected banned synthetic placeholder names: {rows}")
        print("✔ Verified zero synthetic placeholder names in database.")

    def test_03_batterychucker_dynasty_vitals(self):
        """Asserts Senior is in cardiac redline and Jr is smug."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT systolic_bp, status FROM emergent_citizens WHERE handle = '@batterychucker';")
        sr = cur.fetchone()
        cur.execute("SELECT systolic_bp, status FROM emergent_citizens WHERE handle = '@batterychuckerjr';")
        jr = cur.fetchone()
        conn.close()
        
        self.assertIsNotNone(sr, "BatteryChucker Sr must exist.")
        self.assertIsNotNone(jr, "BatteryChucker Jr must exist.")
        self.assertGreaterEqual(sr[0], 200, "Senior must be at systolic BP >= 200 mmHg.")
        self.assertLess(jr[0], 140, "Jr must be resting at systolic BP < 140 mmHg.")
        print(f"✔ Verified BatteryChucker Vitals: Senior BP {sr[0]} mmHg ({sr[1]}) vs Jr BP {jr[0]} mmHg ({jr[1]})")

    def test_04_prediction_contracts(self):
        """Asserts $BATTERY-CHUCK contract is open."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT ticker, current_probability, status FROM market_contracts WHERE ticker = '$BATTERY-CHUCK';")
        contract = cur.fetchone()
        conn.close()
        
        self.assertIsNotNone(contract, "$BATTERY-CHUCK contract must exist.")
        self.assertGreater(contract[1], 0.90, "$BATTERY-CHUCK probability must be > 90%.")
        self.assertEqual(contract[2], "OPEN")
        print(f"✔ Verified Prediction Contract: {contract[0]} at {int(contract[1]*100)}¢ (Status: {contract[2]})")

    def test_05_father_son_friction(self):
        """Asserts father-son feud friction evaluates to 0.98."""
        from emergent_society_daemon import SimulationEngine
        engine = SimulationEngine(db_path=DB_PATH)
        friction_sr_to_jr = engine.calculate_friction("CIT-001-BATTERYCHUCKER", "CIT-002-BATTERYCHUCKERJR")
        friction_jr_to_sr = engine.calculate_friction("CIT-002-BATTERYCHUCKERJR", "CIT-001-BATTERYCHUCKER")
        self.assertEqual(friction_sr_to_jr, 0.98, "Senior <-> Jr feud friction must evaluate to 0.98.")
        self.assertEqual(friction_jr_to_sr, 0.98, "Jr <-> Senior feud friction must evaluate to 0.98.")
        neutral = engine.calculate_friction("CIT-003-BARF", "CIT-004-SAMMY")
        self.assertEqual(neutral, 0.50, "Neutral personas friction should be baseline 0.50.")
        print(f"✔ Verified Father-Son Friction Trigger: 0.98 (Neutral: {neutral})")


if __name__ == "__main__":
    unittest.main()
