#!/usr/bin/env python3
"""
SOVEREIGN OS — NEXT GEN STATS RFID TELEMETRY INGESTION DAEMON
File: /home/james/stacklabs/scripts/nfl_event_stream.py
Description: Ingests & simulates real-time NFL Next Gen Stats RFID chip data
             (Player coordinates, velocities, ball trajectory, play events)
             and streams telemetry to the FanStack Crosstalk Lounge.
"""

import sys
import time
import json
import random
import math
import asyncio
from typing import Dict, List, Any

class NFLEventStreamer:
    def __init__(self):
        self.viewport_width = 100  # 100 yards field coordinate system
        self.viewport_height = 53.3  # NFL field width in yards
        self.active_play = False
        self.play_type = "PASS_PLAY"
        self.down = 3
        self.distance = 7
        self.yardline = 35  # Ball on 35 yardline
        
        # Initialize 22 player RFID positions (11 Offense, 11 Defense) + Ball
        self.players = self._init_roster()
        self.ball = {"x": 35.0, "y": 26.65, "z": 1.2, "vx": 0.0, "vy": 0.0, "vz": 0.0, "airborne": False}

    def _init_roster() -> List[Dict[str, Any]]:
        roster = []
        # Offense (Chiefs red / home)
        offense_positions = [
            ("QB", 30.0, 26.65, "15", "Patrick Mahomes"),
            ("RB", 27.0, 26.65, "10", "Isiah Pacheco"),
            ("WR1", 35.0, 5.0, "10", "Rashee Rice"),
            ("WR2", 35.0, 48.0, "4", "Marquise Brown"),
            ("TE", 34.0, 32.0, "87", "Travis Kelce"),
            ("LT", 34.5, 20.0, "79", "Wanya Morris"),
            ("LG", 34.5, 23.0, "62", "Joe Thuney"),
            ("C",  34.5, 26.65, "52", "Creed Humphrey"),
            ("RG", 34.5, 30.0, "65", "Trey Smith"),
            ("RT", 34.5, 33.0, "74", "Jawaan Taylor"),
            ("FB", 32.0, 26.65, "42", "Carson Steele"),
        ]
        for pos, x, y, num, name in offense_positions:
            roster.append({
                "rfid_id": f"RFID_OFF_{num}",
                "team": "KC",
                "side": "OFFENSE",
                "jersey": num,
                "name": name,
                "position": pos,
                "x": x,
                "y": y,
                "vx": 0.0,
                "vy": 0.0,
                "speed_mph": 0.0,
                "accel": 0.0
            })

        # Defense (49ers gold/white / away)
        defense_positions = [
            ("DE1", 35.5, 19.5, "97", "Nick Bosa"),
            ("DT1", 35.5, 23.5, "90", "Kevin Givens"),
            ("DT2", 35.5, 29.5, "98", "Javon Hargrave"),
            ("DE2", 35.5, 33.5, "56", "Leonard Floyd"),
            ("MLB", 38.0, 26.65, "54", "Fred Warner"),
            ("WLB", 38.0, 21.0, "57", "Dre Greenlaw"),
            ("CB1", 37.0, 5.0, "7", "Charvarius Ward"),
            ("CB2", 37.0, 48.0, "2", "Deommodore Lenoir"),
            ("FS",  45.0, 15.0, "31", "Tashaun Gipson"),
            ("SS",  43.0, 38.0, "29", "Talanoa Hufanga"),
            ("NB",  37.0, 33.0, "26", "Isaiah Oliver")
        ]
        for pos, x, y, num, name in defense_positions:
            roster.append({
                "rfid_id": f"RFID_DEF_{num}",
                "team": "SF",
                "side": "DEFENSE",
                "jersey": num,
                "name": name,
                "position": pos,
                "x": x,
                "y": y,
                "vx": 0.0,
                "vy": 0.0,
                "speed_mph": 0.0,
                "accel": 0.0
            })
        return roster

    def step_telemetry() -> Dict[str, Any]:
        """Simulate Next Gen Stats high-frequency (10Hz) RFID coordinate frame update."""
        event_trigger = None
        
        # Random chance to initiate snap / play sequence
        if not self.active_play and random.random() < 0.15:
            self.active_play = True
            self.play_type = random.choice(["PASS_PLAY", "DEEP_BOMB", "BLITZ_SACK", "RUN_PLAY"])

        if self.active_play:
            # Move offensive skill players downfield
            for p in self.players:
                if p["side"] == "OFFENSE":
                    if p["position"] in ["WR1", "WR2", "TE"]:
                        p["vx"] = random.uniform(3.5, 7.5)
                        p["vy"] = random.uniform(-1.5, 1.5)
                    elif p["position"] == "QB":
                        p["vx"] = random.uniform(-1.0, 0.5)
                        p["vy"] = random.uniform(-0.5, 0.5)
                    else:
                        p["vx"] = random.uniform(0.5, 2.0)
                else:  # DEFENSE
                    if p["position"] in ["CB1", "CB2", "FS", "SS"]:
                        p["vx"] = random.uniform(3.0, 7.0)
                        p["vy"] = random.uniform(-1.5, 1.5)
                    elif p["position"] in ["DE1", "DE2"]:
                        p["vx"] = random.uniform(-2.0, -4.5) if p["x"] > self.yardline else random.uniform(2.0, 4.0)

                # Update coordinates & clamp to field limits
                p["x"] = max(0.0, min(100.0, p["x"] + p["vx"] * 0.1))
                p["y"] = max(0.0, min(53.3, p["y"] + p["vy"] * 0.1))
                p["speed_mph"] = round(math.sqrt(p["vx"]**2 + p["vy"]**2) * 2.23694, 1)

            # Ball trajectory logic
            if self.play_type == "DEEP_BOMB" and random.random() < 0.2:
                self.ball["airborne"] = True
                self.ball["x"] += 4.5
                self.ball["z"] = round(math.sin(time.time() * 2) * 15.0 + 2.0, 1)
                if self.ball["x"] > 65.0:
                    self.active_play = False
                    event_trigger = "TOUCHDOWN"
            elif self.play_type == "BLITZ_SACK" and random.random() < 0.25:
                self.active_play = False
                event_trigger = "SACK"
            elif random.random() < 0.08:
                self.active_play = False
                event_trigger = "THIRD_DOWN_CONVERSION"

        return {
            "timestamp": time.time(),
            "down": self.down,
            "distance": self.distance,
            "yardline": self.yardline,
            "active_play": self.active_play,
            "play_type": self.play_type,
            "ball": self.ball,
            "players": self.players,
            "event_trigger": event_trigger
        }

if __name__ == "__main__":
    streamer = NFLEventStreamer()
    print("[NFL Event Streamer] Initialized. Streaming 10Hz Next Gen Stats RFID Telemetry...")
    for _ in range(5):
        frame = streamer.step_telemetry()
        print(f"  Frame timestamp={frame['timestamp']:.2f} | Active Play={frame['active_play']} | Event={frame['event_trigger']}")
        time.sleep(0.1)
