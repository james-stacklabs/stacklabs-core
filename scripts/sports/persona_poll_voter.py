#!/usr/bin/env python3
"""
Sovereign OS — Automated Persona In-Game Poll Voter Engine
Ticket: WO0010061-FANSTACK-SIM-PHASE2-3-POLLS-AND-MED
SOW: SOW_2026_09_11_FANSTACK_SIMULATION_PHASE_2_3.md
Path: /home/james/stacklabs/scripts/sports/persona_poll_voter.py

Evaluates active room polls in real time and automates bias-driven voting
across seated fan personas based on their distinct psychological profiles:
- barf: 100% Mets Homerism (always favors Mets/Benge/LFGM/heroics) -> react_jump_celebrate
- keith_fanboy: Fundamentals & Sabermetrics (fundies, pitching, defense) -> react_thinking
- 7_train_terry: Cardiac Doomer (bullpen disaster, blown saves, gloom) -> react_facepalm
- BronxBomberFury: Pinstripe Supremacy (Yankees, Judge, blame umps) -> react_raised_eyebrow
- UncleStevieStan: Cohen Balance Sheet & Capital Optimism -> react_smug
- bleacher_creature_99: 27 Rings, Bronx Bleacher Roll Call -> react_flex
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Any, Optional

sys.path.insert(0, "/home/james/stacklabs")
from scripts.core import api_client

PERSONA_BIAS_RULES = {
    "barf": {
        "team": "NYM",
        "homer_weight": 1.0,
        "keywords": ["mets", "benge", "semien", "senga", "vientos", "nimmo", "lindor", "walk-off", "lfgm", "yes"],
        "negative_keywords": ["yankees", "judge", "soto", "stanton", "cole", "no"],
        "pose": "react_jump_celebrate"
    },
    "keith_fanboy": {
        "team": "NYM",
        "homer_weight": 0.6,
        "keywords": ["fundies", "fundamentals", "pitch", "strikeout", "defense", "under", "mendoza", "starter"],
        "negative_keywords": ["chaos", "wild", "walk", "error", "balk"],
        "pose": "react_thinking"
    },
    "7_train_terry": {
        "team": "NYM",
        "homer_weight": 0.2, # Doomerism overrides homerism on high stress
        "keywords": ["bullpen", "implosion", "disaster", "pull", "extra inning", "walk", "blown save", "yankees", "no"],
        "negative_keywords": ["easy", "lock", "guarantee"],
        "pose": "react_facepalm"
    },
    "BronxBomberFury": {
        "team": "NYY",
        "homer_weight": 1.0,
        "keywords": ["yankees", "judge", "soto", "stanton", "cole", "bronx", "pinstripes", "championship"],
        "negative_keywords": ["mets", "citi field", "benge", "grimace"],
        "pose": "react_raised_eyebrow"
    },
    "UncleStevieStan": {
        "team": "NYM",
        "homer_weight": 0.9,
        "keywords": ["mets", "steve", "cohen", "invest", "payroll", "future", "talent", "benge"],
        "negative_keywords": ["cheap", "luxury tax", "rebuild"],
        "pose": "react_point_rally"
    },
    "bleacher_creature_99": {
        "team": "NYY",
        "homer_weight": 0.95,
        "keywords": ["yankees", "roll call", "judge", "27 rings", "bombers", "bronx"],
        "negative_keywords": ["mets", "queens", "little brother"],
        "pose": "react_point_rally"
    },
    "bronx_bomber_bob": {
        "team": "NYY",
        "homer_weight": 0.9,
        "keywords": ["yankees", "judge", "volpe", "bednar", "wells"],
        "negative_keywords": ["mets", "queens"],
        "pose": "react_raised_eyebrow"
    },
    "PinstripeGrudge": {
        "team": "NYY",
        "homer_weight": 0.85,
        "keywords": ["umpire", "bad call", "strike zone", "yankees", "rigged"],
        "negative_keywords": ["mets", "fair"],
        "pose": "react_facepalm"
    }
}

class PersonaPollVoterEngine:
    def __init__(self, room_id: str = "823628"):
        self.room_id = str(room_id)

    def evaluate_persona_choice(self, persona: str, question: str, options: List[str]) -> int:
        """Determines the 0-indexed choice for a persona based on profile heuristics."""
        rule = PERSONA_BIAS_RULES.get(persona)
        if not rule:
            # Fallback based on name hints
            if any(k in persona.lower() for k in ["yankee", "bronx", "pinstripe"]):
                rule = PERSONA_BIAS_RULES["BronxBomberFury"]
            else:
                rule = PERSONA_BIAS_RULES["barf"]

        scores = [0.0] * len(options)
        q_lower = question.lower()

        for idx, opt in enumerate(options):
            opt_lower = opt.lower()
            # Positive keywords
            for kw in rule["keywords"]:
                if kw in opt_lower:
                    scores[idx] += 3.0
                elif kw in q_lower and ("yes" in opt_lower or "over" in opt_lower):
                    scores[idx] += 1.5

            # Negative keywords
            for nkw in rule["negative_keywords"]:
                if nkw in opt_lower:
                    scores[idx] -= 3.0

        # Select option with maximum score; if tied, default to team preference
        max_score = max(scores)
        best_indices = [i for i, s in enumerate(scores) if s == max_score]
        
        # If tie, use first matching or default index
        choice = best_indices[0]
        return choice

    def cast_persona_votes(self, poll_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches active poll and executes votes for all seated personas."""
        print(f"[*] Fetching active poll for Room {self.room_id}...")
        poll = None
        if poll_id:
            polls_list = api_client.list_polls(room_id=self.room_id)
            for p in polls_list:
                if p.get("poll_id") == poll_id:
                    poll = p
                    break
        
        if not poll:
            active_data = api_client.get_active_poll(self.room_id)
            poll = active_data.get("active_poll") or active_data.get("poll")

        if not poll:
            print(f"⚠️ No active poll found for Room {self.room_id}.")
            return {"status": "no_active_poll", "room_id": self.room_id, "votes": []}

        target_poll_id = poll.get("poll_id")
        question = poll.get("question", "")
        options = poll.get("options", [])
        print(f"✔ Target Poll Identified: [{target_poll_id}] '{question}'")
        print(f"   Options: {options}")

        # Retrieve seated personas in room
        try:
            room_data = api_client.get_room_personas(self.room_id)
            seated_raw = room_data.get("personas", [])
            seated_personas = []
            for p in seated_raw:
                if isinstance(p, dict):
                    name = p.get("user_name") or p.get("name") or p.get("id")
                    if name:
                        seated_personas.append(name)
                elif isinstance(p, str):
                    seated_personas.append(p)
        except Exception:
            seated_personas = []

        if not seated_personas:
            seated_personas = list(PERSONA_BIAS_RULES.keys())

        results = []
        print(f"\n[*] Processing automated votes across {len(seated_personas)} personas...")
        for persona in seated_personas:
            opt_idx = self.evaluate_persona_choice(persona, question, options)
            chosen_label = options[opt_idx] if opt_idx < len(options) else f"Option {opt_idx}"
            
            # Submit vote via API
            try:
                vote_res = api_client.vote_in_poll(
                    poll_id=target_poll_id,
                    option_id=opt_idx,
                    user_name=persona,
                    room_id=self.room_id
                )
            except Exception as e:
                vote_res = {"error": str(e)}

            # Update persona reaction pose
            rule = PERSONA_BIAS_RULES.get(persona, {})
            pose = rule.get("pose", "react_thinking")
            try:
                api_client.set_persona_active_pose(persona, pose, room=self.room_id)
            except Exception:
                pass

            record = {
                "persona": persona,
                "team": rule.get("team", "UNKNOWN"),
                "selected_option": opt_idx,
                "selected_label": chosen_label,
                "pose": pose,
                "api_response": vote_res
            }
            results.append(record)
            print(f"   🗳️  @{persona:20} [{rule.get('team', '???')}] voted -> [{opt_idx}] {chosen_label} (Pose: {pose})")

        # Fetch updated tallies
        updated_data = api_client.get_active_poll(self.room_id)
        active_p = updated_data.get("active_poll") or updated_data
        tallies = active_p.get("tallies", {})
        total_votes = tallies.get("total_votes", 0)
        option_counts = tallies.get("option_counts", [])
        option_pcts = tallies.get("option_pcts", [])

        print(f"\n✔ Voting Complete! Total Tallies for Poll [{target_poll_id}]: {total_votes} votes")
        for idx, opt in enumerate(options):
            cnt = option_counts[idx] if idx < len(option_counts) else 0
            pct = option_pcts[idx] if idx < len(option_pcts) else 0.0
            print(f"   Option {idx} ({opt}): {cnt} votes ({pct:.1f}%)")

        return {
            "status": "success",
            "poll_id": target_poll_id,
            "question": question,
            "options": options,
            "total_votes": total_votes,
            "tallies": tallies,
            "votes": results
        }

def main():
    parser = argparse.ArgumentParser(description="Persona Poll Voter Engine")
    parser.add_argument("--room", default="823628", help="Target room / game_pk")
    parser.add_argument("--poll-id", default=None, help="Target poll ID (optional)")
    args = parser.parse_args()

    engine = PersonaPollVoterEngine(room_id=args.room)
    res = engine.cast_persona_votes(poll_id=args.poll_id)
    print("\n🏁 Persona Poll Voter Finished.")
    return res

if __name__ == "__main__":
    main()
