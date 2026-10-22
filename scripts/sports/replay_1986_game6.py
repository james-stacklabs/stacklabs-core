#!/usr/bin/env python3
"""
Sovereign OS — 1986 World Series Game 6 Classic Replay Engine
Ticket: WO0010063-1986-WORLD-SERIES-GAME6-REPLAY
Path: /home/james/stacklabs/scripts/sports/replay_1986_game6.py

Synchronizes 1986 World Series Game 6 (Oct 25, 1986: Boston Red Sox @ New York Mets at Shea Stadium)
10th-inning play events, base runner advancements, retro scoreboard HUD state, authentic persona lore,
and living room Govee UDP Port 4003 victory lighting cues.
"""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

sys.path.insert(0, "/home/james/stacklabs")
from scripts.core import api_client

EVENTS_FILE = "/home/james/stacklabs/scripts/1986_game6_events.json"
GAME_PK = "19861025"

PERSONAS_1986 = [
    "keith_fanboy",
    "7_train_terry",
    "barf",
    "metsfan_86",
    "SoxNationProphet"
]

LORE_DISCOURSE = {
    1: [
        {"user_name": "7_train_terry", "text": "Bottom of the 10th. Schiraldi is throwing gas. Backman flies out to Rice in left. 1 out.", "mood": "tense"},
        {"user_name": "SoxNationProphet", "text": "Two outs away from the first Red Sox championship since 1918! You can feel destiny!", "mood": "smug"}
    ],
    2: [
        {"user_name": "keith_fanboy", "text": "Keith flies out to Lynn in center! That's 2 outs! Keith is storming into the clubhouse right now...", "mood": "devastated"},
        {"user_name": "7_train_terry", "text": "I can't watch this. Keith just walked off into Davey's office with a cold beer and a cigarette. He thinks it's over.", "mood": "cardiac_collapse"},
        {"user_name": "barf", "text": "NO! We won 108 games! This cannot end like this! One out away from the curse dying on our turf!", "mood": "panic"}
    ],
    3: [
        {"user_name": "7_train_terry", "text": "HOLD ON! Gary Carter lines a single into left! The Kid refuses to make the final out!", "mood": "hopeful"},
        {"user_name": "keith_fanboy", "text": "Carter is on first. Keith is still in Davey's office with his cleats unlaced, hearing the crowd through the radio.", "mood": "cautious"},
        {"user_name": "SoxNationProphet", "text": "Meaningless single with 2 outs. Schiraldi just needs one more strike.", "mood": "confident"}
    ],
    4: [
        {"user_name": "barf", "text": "KEVIN MITCHELL! Pinch-hitting in his underwear practically, lines one into center field! Carter to second!", "mood": "screaming"},
        {"user_name": "7_train_terry", "text": "Tying run is on first base! Shea Stadium is shaking! My heart rate is 190 BPM!", "mood": "frenzy"}
    ],
    5: [
        {"user_name": "7_train_terry", "text": "RAY KNIGHT SINGLE TO CENTER! Carter scores! 5-4 Red Sox! Mitchell to third!", "mood": "unhinged"},
        {"user_name": "keith_fanboy", "text": "5 to 4! McNamara is pulling Schiraldi! Here comes Bob Stanley! Shea is rocking to its concrete pillars!", "mood": "electric"},
        {"user_name": "SoxNationProphet", "text": "Stanley, throw strikes. Just one out. Don't let the ghosts in.", "mood": "sweating"}
    ],
    6: [
        {"user_name": "barf", "text": "WILD PITCH! IT GETS AWAY FROM GEDMAN! MITCHELL DIVES IN HEAD FIRST! WE ARE TIED 5-5!", "mood": "delirium"},
        {"user_name": "7_train_terry", "text": "TIE GAME! 5-5! Ray Knight moves to second! The winning run is in scoring position!", "mood": "hysteria"},
        {"user_name": "keith_fanboy", "text": "Davey's office television is vibrating! Keith is staring at the screen through a cloud of smoke, completely stunned!", "mood": "incredulous"}
    ],
    7: [
        {"user_name": "barf", "text": "A little roller up along first... BEHIND THE BAG! IT GETS THROUGH BUCKNER! HERE COMES KNIGHT AND THE METS WIN IT!", "mood": "vin_scully_immortal"},
        {"user_name": "7_train_terry", "text": "THE METS WIN IT! THE METS WIN IT! 6 TO 5! UNBELIEVABLE! SHEA STADIUM IS ON THE FIELD!", "mood": "championship_joy"},
        {"user_name": "keith_fanboy", "text": "HE DID IT! MOOKIE WILSON! KNIGHT SCORES! THE GREATEST COMEBACK IN BASEBALL HISTORY! Keith runs out of the tunnel!", "mood": "legendary"},
        {"user_name": "SoxNationProphet", "text": "Through Buckner's legs... God has forsaken New England.", "mood": "ruined"}
    ]
}

class Classic1986ReplayEngine:
    def __init__(self, game_pk: str = GAME_PK, speed: float = 1.0, fast_mode: bool = False):
        self.game_pk = str(game_pk)
        self.speed = speed
        self.fast_mode = fast_mode
        self.events = self._load_events()

    def _load_events(self) -> List[Dict[str, Any]]:
        if os.path.exists(EVENTS_FILE):
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def seed_environment(self) -> Dict[str, Any]:
        """Seeds the 1986 World Series Game 6 into sport_schedule and seats personas."""
        print(f"[*] Seeding sport_schedule for GamePk {self.game_pk} (BOS @ NYM - Shea Stadium)...")
        schedule_res = api_client.seed_sport_schedule(
            game_pk=self.game_pk,
            sport="MLB",
            home_team="NYM",
            away_team="BOS",
            home_team_name="New York Mets",
            away_team_name="Boston Red Sox",
            game_date="1986-10-25",
            game_time="8:30 PM",
            venue="Shea Stadium, Queens, NY",
            status="Replay (Bot 10th)",
            room_state="active",
            boggs_level=5,
            home_score=6,
            away_score=5
        )

        print(f"[*] Seating 1986 advocates into room {self.game_pk}...")
        seat_res = api_client.seat_room_personas(
            game_pk=self.game_pk,
            personas=PERSONAS_1986,
            prompt_overlay="1986 World Series Game 6 Classic Replay: 10th inning Shea Stadium miracle."
        )

        return {"schedule": schedule_res, "personas": seat_res}

    def get_play_state(self, play_idx: int) -> Dict[str, Any]:
        """Calculates precise diamond, scoreboard, and video-sync state for a given play (1-7)."""
        idx = max(1, min(len(self.events), play_idx))
        event = self.events[idx - 1]

        # Inning base running state transitions
        states = {
            1: {
                "outs": 1, "balls": 1, "strikes": 1, "away_score": 5, "home_score": 3,
                "runners": {"first": None, "second": None, "third": None},
                "batter": "Wally Backman", "pitcher": "Calvin Schiraldi",
                "last_play": "Backman flied out to left field. (1 Out)",
                "status_msg": "Bot 10th • 1 Out • Bases Empty • BOS 5, NYM 3",
                "video_timestamp": 0, "video_time_str": "00:00"
            },
            2: {
                "outs": 2, "balls": 0, "strikes": 2, "away_score": 5, "home_score": 3,
                "runners": {"first": None, "second": None, "third": None},
                "batter": "Keith Hernandez", "pitcher": "Calvin Schiraldi",
                "last_play": "Hernandez flied out to center field. (2 Outs)",
                "status_msg": "Bot 10th • 2 Outs • Keith to Clubhouse • BOS 5, NYM 3",
                "video_timestamp": 35, "video_time_str": "00:35"
            },
            3: {
                "outs": 2, "balls": 2, "strikes": 1, "away_score": 5, "home_score": 3,
                "runners": {"first": "Gary Carter", "second": None, "third": None},
                "batter": "Gary Carter", "pitcher": "Calvin Schiraldi",
                "last_play": "Carter lined a single to left field. (Carter to 1st)",
                "status_msg": "Bot 10th • 2 Outs • Runner on 1st • BOS 5, NYM 3",
                "video_timestamp": 70, "video_time_str": "01:10"
            },
            4: {
                "outs": 2, "balls": 1, "strikes": 2, "away_score": 5, "home_score": 3,
                "runners": {"first": "Kevin Mitchell", "second": "Gary Carter", "third": None},
                "batter": "Kevin Mitchell", "pitcher": "Calvin Schiraldi",
                "last_play": "Mitchell pinch-hit single to center. Carter to 2nd.",
                "status_msg": "Bot 10th • 2 Outs • Runners on 1st & 2nd • BOS 5, NYM 3",
                "video_timestamp": 105, "video_time_str": "01:45"
            },
            5: {
                "outs": 2, "balls": 0, "strikes": 2, "away_score": 5, "home_score": 4,
                "runners": {"first": "Ray Knight", "second": None, "third": "Kevin Mitchell"},
                "batter": "Ray Knight", "pitcher": "Calvin Schiraldi",
                "last_play": "Knight singled to center. Carter scored! (5-4 Red Sox)",
                "status_msg": "Bot 10th • 2 Outs • Runners on 1st & 3rd • BOS 5, NYM 4",
                "video_timestamp": 140, "video_time_str": "02:20"
            },
            6: {
                "outs": 2, "balls": 3, "strikes": 2, "away_score": 5, "home_score": 5,
                "runners": {"first": None, "second": "Ray Knight", "third": None},
                "batter": "Mookie Wilson", "pitcher": "Bob Stanley",
                "last_play": "Stanley wild pitch! Mitchell scores! Knight to 2nd! (5-5 Tie)",
                "status_msg": "Bot 10th • 2 Outs • TIE GAME • Runner on 2nd • BOS 5, NYM 5",
                "video_timestamp": 180, "video_time_str": "03:00"
            },
            7: {
                "outs": 2, "balls": 3, "strikes": 2, "away_score": 5, "home_score": 6,
                "runners": {"first": None, "second": None, "third": None},
                "batter": "Mookie Wilson", "pitcher": "Bob Stanley",
                "last_play": "Wilson reached on error by Buckner! Knight scores from 2nd! METS WIN 6-5!",
                "status_msg": "FINAL • METS WIN 6-5 • 1986 WORLD CHAMPIONSHIP GAME 6 WALK-OFF",
                "video_timestamp": 225, "video_time_str": "03:45"
            }
        }

        st = states.get(idx, states[1])
        st.update({
            "game_pk": self.game_pk,
            "play_index": idx,
            "total_plays": len(self.events),
            "event_id": event.get("id"),
            "inning": "Bot 10th",
            "home_team": "NYM",
            "away_team": "BOS",
            "home_team_name": "New York Mets",
            "away_team_name": "Boston Red Sox",
            "venue": "Shea Stadium, Queens, NY",
            "game_date": "1986-10-25",
            "lore_discourse": LORE_DISCOURSE.get(idx, []),
            "all_plays": [
                {"idx": 1, "title": "1. Backman Flyout", "desc": "1 out, bases empty", "score": "5-3"},
                {"idx": 2, "title": "2. Hernandez Flyout", "desc": "2 outs (Keith to clubhouse)", "score": "5-3"},
                {"idx": 3, "title": "3. Carter Single", "desc": "Carter to 1st base", "score": "5-3"},
                {"idx": 4, "title": "4. Mitchell Single", "desc": "Carter to 2nd, Mitchell to 1st", "score": "5-3"},
                {"idx": 5, "title": "5. Knight RBI Single", "desc": "Carter scores (5-4), Mitchell to 3rd", "score": "5-4"},
                {"idx": 6, "title": "6. Stanley Wild Pitch", "desc": "Mitchell scores (5-5 tie), Knight to 2nd", "score": "5-5"},
                {"idx": 7, "title": "7. Buckner Error Walk-Off", "desc": "Knight scores from 2nd! Mets Win 6-5!", "score": "6-5"}
            ]
        })
        return st

    def run_full_sequence(self) -> Dict[str, Any]:
        """Executes the complete 7-play sequence with optional Govee hardware strobe."""
        self.seed_environment()
        history = []
        print("\n⚡ Beginning 1986 10th-Inning Replay Sweep...")
        for play_num in range(1, len(self.events) + 1):
            st = self.get_play_state(play_num)
            history.append(st)
            print(f"   [Play {play_num}/7] {st['status_msg']}")
            print(f"      ▶ {st['last_play']}")
            for d in st.get("lore_discourse", []):
                print(f"      💬 @{d['user_name']}: \"{d['text']}\"")

            if play_num == 7:
                print("\n🎆 WALK-OFF CLIMAX REACHED! Dispatching Govee Port 4003 VICTORY_SWEEP...")
                try:
                    govee_res = api_client.trigger_govee_strobe("VICTORY_SWEEP")
                    print(f"   ✔ Govee UDP Status: {govee_res}")
                except Exception as e:
                    print(f"   ⚠️ Govee Trigger Notice: {e}")

            if not self.fast_mode:
                time.sleep(2.0 / self.speed)

        print("\n✔ 1986 Classic Replay Sweep Complete!")
        return {
            "status": "SUCCESS",
            "game_pk": self.game_pk,
            "total_plays": len(self.events),
            "final_score": "BOS 5, NYM 6",
            "walkoff_reached": True
        }

def main():
    parser = argparse.ArgumentParser(description="1986 World Series Game 6 Classic Replay Engine")
    parser.add_argument("--fast", action="store_true", help="Run in fast mode without delays")
    parser.add_argument("--seed-only", action="store_true", help="Seed schedule and personas only")
    parser.add_argument("--play", type=int, default=None, help="Inspect specific play (1-7)")
    args = parser.parse_args()

    engine = Classic1986ReplayEngine(fast_mode=args.fast)

    if args.seed_only:
        res = engine.seed_environment()
        print("Seed result:", res)
    elif args.play is not None:
        st = engine.get_play_state(args.play)
        print(json.dumps(st, indent=2))
    else:
        engine.run_full_sequence()

if __name__ == "__main__":
    main()
