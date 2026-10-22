#!/usr/bin/env python3
"""
Test Suite: "Who's on First?" Spatial Diamond State Engine & Offline Corpus Disambiguation
Path: /home/james/stacklabs/scripts/test_diamond_state_engine.py
Initiative: STRY0010009
"""

import sys
import os
import time

sys.path.insert(0, '/home/james/stacklabs')
from scripts.core import api_client
from scripts.core.diamond_state_manager import diamond_engine
from scripts.core.offline_corpus_engine import OfflineCorpusEngine

def test_diamond_state_transitions():
    print("\n=======================================================")
    print("TEST 1: Spatial Diamond Base Runner State Transitions")
    print("=======================================================")
    
    game_pk = "test_nym_phi_823441"
    state = diamond_engine.get_or_create(game_pk, home_team="NYM", away_team="PHI", venue="Citi Field")
    
    # Inning 1 Top: Pitcher is Kodai Senga, Batter is Kyle Schwarber
    print("[STEP 1] Lead-off Walk to Kyle Schwarber")
    diamond_engine.process_statcast_event(game_pk, {
        "event": "walk",
        "batter_name": "Kyle Schwarber",
        "pitcher_name": "Kodai Senga",
        "balls": 4,
        "strikes": 1,
        "outs": 0
    })
    print(state.to_ascii_diamond())
    assert state.first_base is not None, "Runner should be on 1B"
    assert "Schwarber" in state.first_base.name, "1B runner should be Schwarber"
    assert state.double_play_in_order, "Double play should be in order with runner on 1B, 0 outs"
    print("✓ Passed: 1B runner tracked and double play depth recognized.")

    # Step 2: Single by Trea Turner -> Schwarber to 3B, Turner on 1B
    print("\n[STEP 2] Single by Trea Turner")
    diamond_engine.process_statcast_event(game_pk, {
        "event": "single",
        "batter_name": "Trea Turner",
        "pitcher_name": "Kodai Senga",
        "balls": 0,
        "strikes": 0
    })
    print(state.to_ascii_diamond())
    assert state.third_base is not None, "Lead runner should be on 3B"
    assert state.first_base is not None, "Batter should be on 1B"
    assert state.runners_in_scoring_position, "Runner in scoring position should be True"
    print("✓ Passed: Runners on corners tracked.")

    # Step 3: Walk to Bryce Harper -> Bases Loaded!
    print("\n[STEP 3] Walk to Bryce Harper -> Bases Loaded")
    diamond_engine.process_statcast_event(game_pk, {
        "event": "walk",
        "batter_name": "Bryce Harper",
        "pitcher_name": "Kodai Senga"
    })
    print(state.to_ascii_diamond())
    assert state.bases_loaded, "Bases should be loaded"
    assert state.runner_count == 3, "Runner count should be 3"
    print("✓ Passed: Bases loaded situation identified.")

    # Step 4: Grounded into Double Play -> 2 outs, run scores, runner on 3B
    print("\n[STEP 4] 6-4-3 Grounded into Double Play by Alec Bohm")
    diamond_engine.process_statcast_event(game_pk, {
        "event": "grounded_into_double_play",
        "batter_name": "Alec Bohm",
        "pitcher_name": "Kodai Senga"
    })
    print(state.to_ascii_diamond())
    assert state.outs == 2, "Outs should be 2"
    assert state.first_base is None, "1B runner forced out"
    print("✓ Passed: Double play correctly advanced outs and cleared force.")

def test_slot_disambiguation_and_corpus():
    print("\n=======================================================")
    print("TEST 2: Slot Disambiguation & 'Edible Freddie' Immunity")
    print("=======================================================")
    
    corpus = OfflineCorpusEngine()
    game_pk = "test_nym_phi_823441"
    state = diamond_engine.get_or_create(game_pk)
    
    # Mets fan perspective (Home Team) vs Phillies (Away Team batting)
    slots = state.get_slot_replacements(persona_team="NYM")
    print("Slot Mapping for Mets Fan (@barf):")
    print(f"  - {{ALLY_PITCHER}}: {slots.get('{ALLY_PITCHER}')}")
    print(f"  - {{OPPONENT_BATTER}}: {slots.get('{OPPONENT_BATTER}')}")
    print(f"  - {{RUNNER_3B}}: {slots.get('{RUNNER_3B}')}")
    print(f"  - {{VENUE}}: {slots.get('{VENUE}')}")
    
    # Test slot fill against template
    template = "Man, {PITCHER} is dealing at {VENUE}! {OUTS_VERBAL}, gotta watch out for {RUNNER_3B} over on third."
    filled = corpus.slot_fill(template, {}, state.to_dict(), persona_team="NYM")
    print(f"\nTemplate: {template}")
    print(f"Filled:   {filled}")
    assert "{PITCHER}" not in filled, "Token should be replaced"
    assert "Citi Field" in filled, "Venue should be populated"
    assert "the pitcher" in filled or "our starter" in filled, "Pitcher should use natural syntax fallback"

    # Test Task 4: Possessive replacements
    template_poss = "Can't touch {PITCHER}'s slider! {BATTER}'s swing was way behind."
    filled_poss = corpus.slot_fill(template_poss, {}, state.to_dict(), persona_team="NYM")
    print(f"\nTemplate (Possessive): {template_poss}")
    print(f"Filled (Possessive):   {filled_poss}")
    assert "{PITCHER}'s" not in filled_poss, "Possessive token {PITCHER}'s should be replaced"
    assert "{BATTER}'s" not in filled_poss, "Possessive token {BATTER}'s should be replaced"
    assert "the pitcher's" in filled_poss or "our starter's" in filled_poss, "Should produce natural possessive 'the pitcher's'"

    # Test Task 4: Broken Mad-Lib legacy remediation
    legacy_madlib_1 = "He's swinging at that their pitcher league velocity!"
    filled_madlib_1 = corpus.slot_fill(legacy_madlib_1, {}, state.to_dict(), persona_team="NYM")
    print(f"\nLegacy Mad-Lib 1: {legacy_madlib_1}")
    print(f"Remediated:       {filled_madlib_1}")
    assert "their pitcher league velocity" not in filled_madlib_1, "Broken mad-lib must be remediated"
    assert "the pitcher's velocity" in filled_madlib_1, "Should cleanly read 'the pitcher's velocity'"

    legacy_madlib_2 = "Man, their hitter needs to attack the zone instead of nibbling."
    filled_madlib_2 = corpus.slot_fill(legacy_madlib_2, {}, state.to_dict(), persona_team="NYM")
    print(f"\nLegacy Mad-Lib 2: {legacy_madlib_2}")
    print(f"Remediated:       {filled_madlib_2}")
    assert "their hitter needs to attack the zone" not in filled_madlib_2, "Illiterate mad-lib must be remediated"
    assert "the pitcher needs to attack the zone" in filled_madlib_2, "Should cleanly read 'the pitcher needs to attack the zone'"

    print("✓ Passed: Contextual, possessive, and legacy grammar slots filled cleanly without duplicates.")

def test_fastapi_diamond_endpoints():
    print("\n=======================================================")
    print("TEST 3: FastAPI REST API Diamond State Integration")
    print("=======================================================")
    
    game_id = "test_nym_phi_823441"
    data = api_client.get_diamond_state(game_id)
    print(f"Retrieved Diamond State via FastAPI (Port 8095):")
    print(f"  - Game PK: {data.get('game_pk')}")
    print(f"  - Inning: {data.get('inning_half')} {data.get('inning')}")
    print(f"  - Outs: {data.get('outs')}")
    print(f"  - Bases Loaded: {data.get('bases_loaded')}")
    assert data.get("game_pk") == game_id, "Game ID must match"
    print("✓ Passed: Live FastAPI endpoint /api/sports/diamond_state responded cleanly.")

if __name__ == "__main__":
    test_diamond_state_transitions()
    test_slot_disambiguation_and_corpus()
    test_fastapi_diamond_endpoints()
    print("\n=======================================================")
    print("🎉 ALL 'WHO'S ON FIRST?' SPATIAL ENGINE TESTS PASSED!")
    print("=======================================================\n")
