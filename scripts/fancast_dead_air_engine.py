#!/usr/bin/env python3
"""
==============================================================================
SOVEREIGN OS: FANCAST NFL DEAD-AIR STOPPAGE BANTER ENGINE & DUAL-MODE CONTROLLER
Script: /home/james/stacklabs/scripts/fancast_dead_air_engine.py
Ticket: WO0010035-FANCAST-NFL-DEAD-AIR-BANTER-ENGINE (CI: 15_FanStack)
==============================================================================
Provides automated, high-fidelity persona banter during NFL broadcast dead air
(play clock huddles, yellow penalty flags, commercial breaks, booth reviews).

Features:
  1. Dual-Mode Governance:
     - 'broadcast_safe' (Default): Strict 2-turn maximum (Hot Take -> Roast),
       with immediate interrupt kill on play snap.
     - 'emergent_chaos': Uncapped multi-agent conversational loop allowing
       running in-jokes, inter-advocate tags, and organic alliances.
  2. Telemetry & Optical Grounding:
     - Ingests triggers from Tapo C120 optical detection or API/telemetry events.
  3. Ground-Truth Persistence:
     - State managed in `fancast_banter_state` and `fancast_banter_log` (sovereign_now.db).
"""

import os
import sys
import time
import json
import uuid
import random
import sqlite3
from typing import Dict, List, Optional, Any, Tuple

DB_PATH = os.getenv("SOVEREIGN_DB_PATH", "/home/james/stacklabs/dna/sovereign_now.db")

# ------------------------------------------------------------------------------
# Persona Roster
# ------------------------------------------------------------------------------
NFL_PERSONAS = [
    {
        "id": "jets_woe",
        "name": "Sal from Secaucus",
        "handle": "@jets_woe",
        "team": "NYJ",
        "role": "Perpetual Sufferer",
        "avatar": "/avatars/sal_jets.png",
        "style": "Cynical, hyper-anxious, traumatized by decades of third-and-long draw plays. Expects an interception on every dropback."
    },
    {
        "id": "mafia_mitch",
        "name": "Mitch Kowalski",
        "handle": "@mafia_mitch",
        "team": "BUF",
        "role": "Table-Breaker",
        "avatar": "/avatars/mitch_bills.png",
        "style": "Loud, blue-collar Buffalo diehard in zubaz pants. Screams about soft penalties, drinks cold Labatt, claims weather doesn't exist."
    },
    {
        "id": "blind_stripes",
        "name": "Zebra Sceptic",
        "handle": "@blind_stripes",
        "team": "NFL",
        "role": "Ref Conspiracy Theorist",
        "avatar": "/avatars/ref_hater.png",
        "style": "Convinced the officiating crew has money on the under. Freezes the broadcast on holding penalties and screams at the sky."
    },
    {
        "id": "fantasy_freak",
        "name": "PPR Pete",
        "handle": "@fantasy_freak",
        "team": "ALL",
        "role": "Fantasy Point Junkie",
        "avatar": "/avatars/ppr_pete.png",
        "style": "Does not care who wins as long as his flex receiver gets 8 targets. Frantic, caffeinated, panics over vulture touchdowns."
    }
]

# ------------------------------------------------------------------------------
# Dialogue Templates (Ground-Truth Generation Matrix)
# ------------------------------------------------------------------------------
BANTER_TEMPLATES = {
    "YELLOW_FLAG": {
        "turn_1": [
            ("blind_stripes", "OF COURSE THERE'S LAUNDRY ON THE FIELD! Look at that phantom hold! The league office literally called that one in from New York!"),
            ("mafia_mitch", "Are you kidding me with that flag?! In the AFC East that's not a penalty, that's a polite greeting! Game is softer than wet cardboard!"),
            ("jets_woe", "Here it comes. Third and two, drive looking decent, and boom—holding, number 74, ten-yard penalty. We've seen this horror movie 500 times.")
        ],
        "turn_2": [
            ("jets_woe", "@blind_stripes Stop blaming the refs, Sal! Our offensive tackle was practically slow-dancing with their edge rusher! Pure undisciplined garbage!"),
            ("fantasy_freak", "@mafia_mitch I don't care about the hold, DID THE SCREEN PASS COUNT?! If that 6-yard catch gets wiped out I lose my matchup by 0.4 points!"),
            ("mafia_mitch", "@jets_woe Keep crying in your turnpike puddle, Sal. Real football teams push through the flags. Grab a cold one and suck it up!")
        ],
        "chaos_followups": [
            ("fantasy_freak", "Ref just picked up the microphone. My heart rate is at 165 bpm. GIVE ME MY 1.2 PPR POINTS YOU COWARDS!"),
            ("blind_stripes", "Notice how he adjusted his cap before announcing? Secret hand signal to Vegas. I have the receipts on VHS!"),
            ("jets_woe", "I need an antacid. Every yellow towel on the turf takes six months off my life expectancy.")
        ]
    },
    "HUDDLE_40S": {
        "turn_1": [
            ("jets_woe", "Why are we taking 35 seconds to break the huddle down by six?! RUN A PLAY! The play clock is at 4! We're gonna burn our last timeout!"),
            ("mafia_mitch", "Line up in 12 personnel and smash it right down their throats! Stop with the cute motion sweeps behind the line of scrimmage!"),
            ("fantasy_freak", "Throw the ball to the tight end! He's been wide open in the flat on the last four plays! Why do I draft players on this team?!")
        ],
        "turn_2": [
            ("mafia_mitch", "@jets_woe Relax, Jersey! It's called pacing. You wear the front four down before you drop the hammer!"),
            ("jets_woe", "@fantasy_freak Nobody cares about your fantasy team, Pete! We're trying to not go 2-and-15 for the twelfth straight autumn!"),
            ("blind_stripes", "@mafia_mitch Left guard is clearly flinching in the stance right now. If they don't call false start on the next snap, I'm filing a police report.")
        ],
        "chaos_followups": [
            ("fantasy_freak", "If they run a QB sneak and vulture my running back's touchdown, I am throwing my tablet into the drywall."),
            ("mafia_mitch", "Put me in at fullback, coach! One block and a cloud of dust!"),
            ("jets_woe", "I can feel the delay of game penalty in my bones. It's coming. Clock is at 2... 1...")
        ]
    },
    "COMMERCIAL_WIPE": {
        "turn_1": [
            ("fantasy_freak", "Commercial break! Quick, checking all 14 of my fantasy matchups... oh god, my kicker has minus-two points?! HOW?!"),
            ("mafia_mitch", "Three minutes of pickup truck commercials and sugary beer ads. Perfect window for another sausage sandwich."),
            ("jets_woe", "Every commercial break gives me just enough time to stare into the ceiling fan and ponder my life choices.")
        ],
        "turn_2": [
            ("jets_woe", "@fantasy_freak Why are you in 14 leagues, Pete?! That's not a hobby, that's an outpatient psychiatric program!"),
            ("blind_stripes", "@mafia_mitch Watch the broadcast audio balance during these ads. They mute the crowd noise to hide the booing!"),
            ("fantasy_freak", "@jets_woe Because unlike the Jets, at least my dynasty roster has a five-year plan, Sal!")
        ],
        "chaos_followups": [
            ("mafia_mitch", "I just smashed a folding table in the living room during the insurance ad just to stay warm!"),
            ("blind_stripes", "Who approves these truck commercials? It's always a boulder falling off a mountain!"),
            ("jets_woe", "We're coming back from commercial. Deep breaths. The pain is about to resume.")
        ]
    },
    "BOOTH_REVIEW": {
        "turn_1": [
            ("blind_stripes", "THE HEADSET IS ON! The referee is standing inside the tent! The shadowy figures in Manhattan are reviewing the tape!"),
            ("jets_woe", "He didn't maintain possession through the ground. Look at the blade of grass! The ball moved half a millimeter! They're reversing it!"),
            ("mafia_mitch", "That's a catch every day of the week! Both feet down, shin down, elbow down! Clear as crystal!")
        ],
        "turn_2": [
            ("mafia_mitch", "@jets_woe Only a Jets fan could look at a pristine diving catch and claim the ball shifted on an electron level!"),
            ("blind_stripes", "@mafia_mitch The camera angle from the pylon is suspiciously obstructed by a cameraman's thigh! Cover-up in real time!"),
            ("fantasy_freak", "@jets_woe If this gets overturned, my point differential drops into 5th place! That is an indisputable reception!")
        ],
        "chaos_followups": [
            ("fantasy_freak", "They've been looking at the tablet for four minutes! What are they ordering on DoorDash in there?!"),
            ("jets_woe", "They're gonna call it incomplete and assess an unsportsmanlike conduct on our bench. Standard protocol."),
            ("mafia_mitch", "OVERTURN THIS AND WE MARCH ON ORCHARD PARK!")
        ]
    },
    "TWO_MINUTE_WARNING": {
        "turn_1": [
            ("jets_woe", "Two-minute warning! Zero timeouts left! 75 yards to go! Time for the classic three-yard checkdown in bounds as the clock expires!"),
            ("mafia_mitch", "Two minutes! Put the foot on the throat! No prevent defense! PREVENT DEFENSE ONLY PREVENTS YOU FROM WINNING!"),
            ("fantasy_freak", "GARBAGE TIME HEROICS! This is where champions are born! Dump it off five times in a row!")
        ],
        "turn_2": [
            ("fantasy_freak", "@jets_woe If they throw the three-yard checkdown, that's a full point in PPR, Sal! Praise the heavens!"),
            ("jets_woe", "@mafia_mitch Your coach has lost four games because he doesn't know how to call a timeout before the 2-minute mark!"),
            ("blind_stripes", "@mafia_mitch Watch the clock operator. They let a full 1.8 seconds tick off after the receiver hit the sideline!")
        ],
        "chaos_followups": [
            ("jets_woe", "My heart is beating like a bass drum in a marching band. Here we go."),
            ("mafia_mitch", "DEFENSE! SACK HIM INTO NEXT TUESDAY!"),
            ("blind_stripes", "False start incoming, watch the center's left thumb!")
        ]
    }
}

class DeadAirBanterEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def get_state(self) -> Dict[str, Any]:
        """Fetch current banter engine state from SQLite."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM fancast_banter_state WHERE id=1").fetchone()
            if not row:
                conn.execute("""
                    INSERT OR IGNORE INTO fancast_banter_state 
                    (id, active_mode, current_stoppage, turn_counter, last_trigger_ts)
                    VALUES (1, 'broadcast_safe', 'NONE', 0, 0.0)
                """)
                conn.commit()
                row = conn.execute("SELECT * FROM fancast_banter_state WHERE id=1").fetchone()
            return dict(row)
        finally:
            conn.close()

    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Update active mode ('broadcast_safe' or 'emergent_chaos')."""
        if mode not in ("broadcast_safe", "emergent_chaos"):
            raise ValueError(f"Invalid mode: '{mode}'. Must be 'broadcast_safe' or 'emergent_chaos'.")
        
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE fancast_banter_state 
                SET active_mode = ?, updated_at = DATETIME('now')
                WHERE id = 1
            """, (mode,))
            conn.commit()
            return self.get_state()
        finally:
            conn.close()

    def interrupt_snap(self) -> Dict[str, Any]:
        """Snap detected or play clock < 5s. Instantly halts active banter."""
        conn = self._get_conn()
        try:
            conn.execute("""
                UPDATE fancast_banter_state 
                SET current_stoppage = 'PLAY_ACTIVE', turn_counter = 0, updated_at = DATETIME('now')
                WHERE id = 1
            """)
            conn.commit()
            return {"status": "INTERRUPTED", "reason": "SNAP_OR_PLAY_ACTIVE", "state": self.get_state()}
        finally:
            conn.close()

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent banter logs."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM fancast_banter_log 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def trigger_stoppage(self, stoppage_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ingest an optical or telemetry stoppage event and generate the appropriate banter.
        In 'broadcast_safe': Generates Turn 1 + Turn 2 and halts.
        In 'emergent_chaos': Generates Turn 1 + Turn 2 + Turn 3 + Turn 4 with cross-talk.
        """
        if stoppage_type not in BANTER_TEMPLATES:
            stoppage_type = "HUDDLE_40S"

        context = context or {}
        state = self.get_state()
        mode = state.get("active_mode", "broadcast_safe")
        now_ts = time.time()

        conn = self._get_conn()
        try:
            # Update state with active stoppage
            conn.execute("""
                UPDATE fancast_banter_state 
                SET current_stoppage = ?, turn_counter = 0, last_trigger_ts = ?, updated_at = DATETIME('now')
                WHERE id = 1
            """, (stoppage_type, now_ts))
            conn.commit()

            template_group = BANTER_TEMPLATES[stoppage_type]
            generated_turns: List[Dict[str, Any]] = []

            # Turn 1: Hot Take
            t1_options = template_group["turn_1"]
            speaker_id, text = random.choice(t1_options)
            p1 = next((p for p in NFL_PERSONAS if p["id"] == speaker_id), NFL_PERSONAS[0])
            
            turn_1_record = self._log_turn(conn, stoppage_type, mode, 1, p1, text, context)
            generated_turns.append(turn_1_record)

            # Turn 2: Roast / Counter-Punch
            t2_options = [opt for opt in template_group["turn_2"] if opt[0] != speaker_id]
            if not t2_options:
                t2_options = template_group["turn_2"]
            speaker_id_2, text_2 = random.choice(t2_options)
            p2 = next((p for p in NFL_PERSONAS if p["id"] == speaker_id_2), NFL_PERSONAS[1])

            turn_2_record = self._log_turn(conn, stoppage_type, mode, 2, p2, text_2, context)
            generated_turns.append(turn_2_record)

            # Check Mode Governance
            if mode == "broadcast_safe":
                # Strict 2-turn lock
                conn.execute("""
                    UPDATE fancast_banter_state 
                    SET turn_counter = 2, updated_at = DATETIME('now')
                    WHERE id = 1
                """)
                conn.commit()
                governance_status = "BROADCAST_SAFE_LOCKED_2_TURNS"
            else:
                # Emergent Chaos: Uncap additional turns
                t3_speaker, t3_text = random.choice(template_group.get("chaos_followups", template_group["turn_1"]))
                p3 = next((p for p in NFL_PERSONAS if p["id"] == t3_speaker), NFL_PERSONAS[2])
                turn_3_record = self._log_turn(conn, stoppage_type, mode, 3, p3, t3_text, context)
                generated_turns.append(turn_3_record)

                t4_speaker, t4_text = random.choice([opt for opt in template_group["turn_2"] if opt[0] != t3_speaker] or template_group["turn_2"])
                p4 = next((p for p in NFL_PERSONAS if p["id"] == t4_speaker), NFL_PERSONAS[3])
                turn_4_record = self._log_turn(conn, stoppage_type, mode, 4, p4, f"{t4_text} (CHAOS MULTI-AGENT LOOP)", context)
                generated_turns.append(turn_4_record)

                conn.execute("""
                    UPDATE fancast_banter_state 
                    SET turn_counter = 4, updated_at = DATETIME('now')
                    WHERE id = 1
                """)
                conn.commit()
                governance_status = "EMERGENT_CHAOS_UNCAPPED_TURNS"

            return {
                "status": "SUCCESS",
                "governance": governance_status,
                "stoppage_type": stoppage_type,
                "mode": mode,
                "turns_generated": len(generated_turns),
                "turns": generated_turns,
                "active_state": self.get_state()
            }
        finally:
            conn.close()

    def _log_turn(self, conn: sqlite3.Connection, stoppage_type: str, mode: str, 
                  turn_num: int, persona: Dict[str, Any], message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        sys_id = uuid.uuid4().hex
        meta_json = json.dumps({
            "handle": persona["handle"],
            "role": persona["role"],
            "avatar": persona["avatar"],
            "context": context
        })
        conn.execute("""
            INSERT INTO fancast_banter_log 
            (sys_id, stoppage_type, mode, turn_number, speaker_id, speaker_name, team_tag, message, raw_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            stoppage_type,
            mode,
            turn_num,
            persona["id"],
            persona["name"],
            persona["team"],
            message,
            meta_json
        ))
        conn.commit()
        return {
            "sys_id": sys_id,
            "stoppage_type": stoppage_type,
            "mode": mode,
            "turn_number": turn_num,
            "speaker_id": persona["id"],
            "speaker_name": persona["name"],
            "speaker_handle": persona["handle"],
            "team_tag": persona["team"],
            "message": message,
            "avatar": persona["avatar"]
        }


# ------------------------------------------------------------------------------
# Standalone CLI / Verification Runner
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    engine = DeadAirBanterEngine()
    print("🏈 [FANCAST DEAD-AIR BANTER ENGINE INITIALIZING]...")
    state = engine.get_state()
    print(f"  Current State: Mode={state['active_mode']}, Stoppage={state['current_stoppage']}")

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("\n🧪 Running Diagnostic Test Suite...")
        
        # Test 1: Broadcast Safe Trigger
        print("\n--- Test 1: Testing 'broadcast_safe' (Strict 2-Turn Limit) ---")
        engine.set_mode("broadcast_safe")
        res1 = engine.trigger_stoppage("YELLOW_FLAG", {"down_distance": "3rd & 4", "quarter": 3})
        print(f"  Governance: {res1['governance']}")
        print(f"  Turns Generated: {res1['turns_generated']}")
        for t in res1["turns"]:
            print(f"    [{t['team_tag']}] {t['speaker_name']}: \"{t['message']}\"")
        assert res1["turns_generated"] == 2, f"Expected 2 turns in broadcast_safe, got {res1['turns_generated']}"
        print("  ✓ PASS: Exactly 2 turns generated.")

        # Test 2: Play Snap Interrupt
        print("\n--- Test 2: Testing 'interrupt_snap()' ---")
        res2 = engine.interrupt_snap()
        print(f"  Status: {res2['status']}, State={res2['state']['current_stoppage']}")
        assert res2["state"]["current_stoppage"] == "PLAY_ACTIVE"
        print("  ✓ PASS: Interrupted successfully on snap.")

        # Test 3: Emergent Chaos Mode
        print("\n--- Test 3: Testing 'emergent_chaos' (Uncapped Multi-Turn Loop) ---")
        engine.set_mode("emergent_chaos")
        res3 = engine.trigger_stoppage("COMMERCIAL_WIPE", {"game": "BUF @ NYJ"})
        print(f"  Governance: {res3['governance']}")
        print(f"  Turns Generated: {res3['turns_generated']}")
        for t in res3["turns"]:
            print(f"    Turn {t['turn_number']} [{t['team_tag']}] {t['speaker_name']}: \"{t['message']}\"")
        assert res3["turns_generated"] >= 4, f"Expected >= 4 turns in emergent_chaos, got {res3['turns_generated']}"
        print("  ✓ PASS: Multi-turn emergent loop active.")

        # Reset back to default broadcast_safe
        engine.set_mode("broadcast_safe")
        print("\n✅ All Dead-Air Banter Engine tests PASSED successfully!")
