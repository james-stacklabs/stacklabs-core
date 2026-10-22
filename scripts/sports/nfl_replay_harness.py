#!/usr/bin/env python3
"""
Sovereign OS — NFL Video-Synced Replay Harness (Mode B)
Path: /home/james/stacklabs/scripts/sports/nfl_replay_harness.py

Streams sequential drive frames from dna/cache/nfl_drive_replay.json across the
WebSocket mesh (ws://127.0.0.1:8008), driving dynamic SVG line of scrimmage,
down & distance markers, box score metrics, and play-by-play chyron.
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime

DEFAULT_REPLAY_PATH = "/home/james/stacklabs/dna/cache/nfl_drive_replay.json"
WS_URL = "ws://127.0.0.1:8008"

class NflReplayHarness:
    def __init__(self, replay_path: str = DEFAULT_REPLAY_PATH, ws_url: str = WS_URL, speed: float = 1.0):
        self.replay_path = replay_path
        self.ws_url = ws_url
        self.speed = speed
        self.drive_data = self._load_drive_data()
        
    def _load_drive_data(self) -> dict:
        if not os.path.exists(self.replay_path):
            raise FileNotFoundError(f"NFL drive replay cache missing: {self.replay_path}")
        with open(self.replay_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_play_state(self, play_index: int = 1) -> dict:
        """Returns the full normalized state for a specific play in the drive."""
        plays = self.drive_data.get("plays", [])
        if not plays:
            return {}
        # 1-indexed clamp
        idx = max(1, min(play_index, len(plays)))
        play = plays[idx - 1]
        
        # Build recent_plays list up to current play in reverse chronological order
        recent = []
        for p in reversed(plays[:idx]):
            recent.append({
                "id": p.get("id", f"replay-{len(recent)}"),
                "drive_idx": 1,
                "team": p.get("possession", "PHI"),
                "drive_desc": "4th Quarter Final Drive",
                "drive_result": "In Progress",
                "clock": p.get("clock"),
                "down": p.get("down_dist"),
                "text": p.get("text"),
                "scoring": bool(p.get("scoring", False)),
                "scoreValue": p.get("scoreValue", 0),
                "statYardage": p.get("statYardage", 0),
                "isLive": len(recent) == 0
            })
            
        return {
            "game_pk": self.drive_data.get("game_pk", "401873284"),
            "away_team": self.drive_data.get("away_team", "PHI"),
            "home_team": self.drive_data.get("home_team", "BAL"),
            "away_team_name": self.drive_data.get("away_team_name", "Philadelphia Eagles"),
            "home_team_name": self.drive_data.get("home_team_name", "Baltimore Ravens"),
            "venue": self.drive_data.get("venue", "Lincoln Financial Field"),
            "away_score": play.get("away_score", 24),
            "home_score": play.get("home_score", 28),
            "status": self.drive_data.get("status", "4th Qtr"),
            "inning": self.drive_data.get("status", "4th Qtr"),
            "clock": f"4th • {play.get('clock')}",
            "down_dist": play.get("down_dist"),
            "down": play.get("down"),
            "distance": play.get("distance"),
            "yards_to_go": play.get("yards_to_go", 10),
            "yardline": play.get("yardline", 20),
            "possession": play.get("possession", "PHI"),
            "status_msg": f"[{play.get('down_dist')}] {play.get('text')}",
            "last_play": play.get("text"),
            "recent_plays": recent,
            "away_qb": self.drive_data.get("away_qb", "Jalen Hurts"),
            "home_qb": self.drive_data.get("home_qb", "Lamar Jackson"),
            "away_total_yards": str(play.get("away_total_yards", 325)),
            "home_total_yards": str(play.get("home_total_yards", 345)),
            "away_pass_yards": str(play.get("away_pass_yards", 220)),
            "home_pass_yards": str(play.get("home_pass_yards", 210)),
            "away_rush_yards": str(play.get("away_rush_yards", 105)),
            "home_rush_yards": str(play.get("home_rush_yards", 135)),
            "away_top": str(play.get("away_top", "28:00")),
            "home_top": str(play.get("home_top", "30:20")),
            "sport": "NFL",
            "league": "NFL",
            "mode": "REPLAY_GAMEPACK",
            "drive_play_current": idx,
            "drive_play_total": len(plays)
        }

    async def stream_drive(self, interval_sec: float = 3.0):
        """Streams all plays in the drive across the WebSocket mesh."""
        import websockets
        plays = self.drive_data.get("plays", [])
        print(f"🏈 [NFL REPLAY] Connecting to WebSocket relay: {self.ws_url}...")
        
        async with websockets.connect(self.ws_url) as ws:
            print(f"✔ Connected. Streaming {len(plays)} drive plays (Speed: {self.speed}x)...")
            
            for p in plays:
                idx = p["play_index"]
                state = self.get_play_state(idx)
                
                packet = {
                    "type": "CMD_SYNC_STATE",
                    "source": "NFL_REPLAY_HARNESS",
                    "target_game_pk": state["game_pk"],
                    "data": state
                }
                
                await ws.send(json.dumps(packet))
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏈 Play {idx}/{len(plays)}: {state['down_dist']} | {state['last_play']}")
                
                delay = max(0.2, interval_sec / self.speed)
                await asyncio.sleep(delay)
                
        print("🏁 [NFL REPLAY] Drive stream complete!")

def main():
    parser = argparse.ArgumentParser(description="NFL Video-Synced Replay Harness")
    parser.add_argument("--speed", type=float, default=2.0, help="Replay speed multiplier")
    parser.add_argument("--interval", type=float, default=2.0, help="Base interval in seconds per play")
    parser.add_argument("--play", type=int, default=None, help="Inspect single play (1-15)")
    args = parser.parse_args()

    harness = NflReplayHarness(speed=args.speed)
    
    if args.play is not None:
        state = harness.get_play_state(args.play)
        print(json.dumps(state, indent=2))
    else:
        asyncio.run(harness.stream_drive(interval_sec=args.interval))

if __name__ == "__main__":
    main()
