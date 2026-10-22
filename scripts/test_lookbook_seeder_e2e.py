#!/usr/bin/env python3
"""
E2E Verification Script for WO-2026-0910-FANSTACK-BARF-LOOKBOOK-SEEDER
Validates lookbook ingestion, active pose switching, sprite serving, and room telemetry.
"""
import sys
import os
import requests

BASE_CORE = "http://127.0.0.1:8090"
BASE_RELAY = "http://127.0.0.1:8000"

def test_e2e():
    print("=== [1] Verifying 22 Lookbook Shots for Barf ===")
    r = requests.get(f"{BASE_CORE}/api/persona/lookbook/barf")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    shots = data.get("shots", [])
    print(f"✅ Total shots returned: {len(shots)}")
    assert len(shots) == 22, f"Expected 22 shots, got {len(shots)}"
    
    categories = set(s["shot_category"] for s in shots)
    print(f"✅ Found categories: {categories}")
    expected_categories = {"orientation", "pitch_tilt", "reaction", "full_body"}
    assert expected_categories.issubset(categories), f"Missing categories: {expected_categories - categories}"

    print("\n=== [2] Testing Simulation: Scoring Play -> Trigger react_laugh ===")
    r = requests.post(f"{BASE_CORE}/api/persona/active_pose", json={"persona_id": "barf", "pose_key": "react_laugh"})
    assert r.status_code == 200, f"Failed setting react_laugh: {r.text}"
    resp_data = r.json()
    assert resp_data["active_pose_key"] == "react_laugh"
    print(f"✅ Active pose response: {resp_data}")

    # Check relay room_personas
    r = requests.get(f"{BASE_RELAY}/api/room_personas?gamePk=822929")
    assert r.status_code == 200
    roster = r.json().get("roster", [])
    barf_entry = next((a for a in roster if a["user_name"].lower() == "barf"), None)
    assert barf_entry is not None, "Barf not found in room roster"
    print(f"✅ Room roster entry for barf: {barf_entry}")
    assert barf_entry["active_pose_key"] == "react_laugh", f"Expected react_laugh, got {barf_entry['active_pose_key']}"

    print("\n=== [3] Testing Simulation: Strikeout Looking -> Trigger react_facepalm ===")
    r = requests.post(f"{BASE_CORE}/api/persona/active_pose", json={"persona_id": "barf", "pose_key": "react_facepalm"})
    assert r.status_code == 200
    assert r.json()["active_pose_key"] == "react_facepalm"
    print("✅ Active pose updated to react_facepalm")

    print("\n=== [4] Testing Binary Sprite Serving ===")
    r = requests.get(f"{BASE_CORE}/api/persona/lookbook/barf/react_facepalm")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/"), f"Unexpected content-type: {r.headers['content-type']}"
    assert len(r.content) > 10000, f"Expected image size > 10KB, got {len(r.content)} bytes"
    print(f"✅ Served react_facepalm sprite: {len(r.content)} bytes, {r.headers['content-type']}")

    print("\n=== [5] Resetting to front_neutral ===")
    r = requests.post(f"{BASE_CORE}/api/persona/active_pose", json={"persona_id": "barf", "pose_key": "front_neutral"})
    assert r.status_code == 200
    print("✅ Reset to front_neutral successfully")

    print("\n🎉 ALL E2E TESTS PASSED!")

if __name__ == "__main__":
    test_e2e()
