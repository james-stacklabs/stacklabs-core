import sys
import json
import sqlite3

sys.path.insert(0, '/home/james/stacklabs/scripts')

from fanstack_chatbots import build_dynamic_system_instruction, build_player_context_str, load_fans

def test_grounding():
    print("[*] Loading fans from database...")
    fans = load_fans()
    print(f"Loaded {len(fans)} fans.")
    
    redbird = None
    for f in fans:
        if "redbird" in f["name"].lower():
            redbird = f
            break
            
    if not redbird:
        print("Warning: Redbird persona not found. Using fallback dictionary.")
        redbird = {
            "name": "Redbird",
            "personality": "A passionate Cardinals fan.",
            "team": "STL",
            "boggs_level": 2
        }
        
    print("\n[*] Testing build_player_context_str for Jordan Walker and Cole Ragans...")
    ctx_str = build_player_context_str("Cole Ragans", "Jordan Walker")
    print(ctx_str)
    
    print("\n[*] Testing build_dynamic_system_instruction for Redbird...")
    system_instruction = build_dynamic_system_instruction(
        redbird, is_massive_event=False, is_play_event=True, allow_rant=False,
        game_state={"away_score": 0, "home_score": 0, "inning": "Top 1st", "outs": 0},
        event_type="matchup", game_pk="824095"
    )
    print("--- SYSTEM INSTRUCTION ---")
    print(system_instruction)
    print("--------------------------")
    
    # Verify strict grounding instruction is present in system_instruction
    assert "STRICT GROUNDING RULE" in system_instruction, "Strict grounding instruction missing!"
    print("[+] Verification Success: Grounding rules are injected into dynamic system instructions.")

if __name__ == "__main__":
    test_grounding()
