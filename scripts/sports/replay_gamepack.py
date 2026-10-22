#!/usr/bin/env python3
"""
Sovereign OS — Statcast Replay GamePack Simulation Engine
Ticket: WO0010059-FANSTACK-SUBWAY-SERIES-SIM
Path: /home/james/stacklabs/scripts/sports/replay_gamepack.py

Simulates the May 17, 2026 Subway Series game (GamePk 823628, NYY @ NYM at Citi Field).
Streams 91 Statcast plays across 10 innings over FanStack WebSocket mesh (Port 8008),
drives commentator bot dialectics, delivers the 10th-inning walk-off sequence,
and captures Pegasus Playwright visual twins.
"""

import sys
import os
import json
import time
import asyncio
import argparse
from datetime import datetime
import websockets

sys.path.insert(0, "/home/james/stacklabs")
from scripts.core import api_client

DEFAULT_FEED_PATH = "/home/james/stacklabs/dna/cache/mlb_823628_feed.json"
DEFAULT_WS_URL = "ws://127.0.0.1:8008"

SUBWAY_PERSONAS = [
    # Mets Advocates
    "barf",
    "7_train_terry",
    "UncleStevieStan",
    "keith_fanboy",
    # Yankees Advocates
    "BronxBomberFury",
    "bleacher_creature_99",
    "bronx_bomber_bob",
    "PinstripeGrudge"
]

class StatcastReplayEngine:
    def __init__(self, game_pk: str = "823628", feed_path: str = DEFAULT_FEED_PATH,
                 ws_url: str = DEFAULT_WS_URL, speed: float = 4.0, fast_mode: bool = False,
                 skip_to_walkoff: bool = False, max_plays: int = None,
                 ticket_id: str = "WO0010059-FANSTACK-SUBWAY-SERIES-SIM"):
        self.game_pk = str(game_pk)
        self.feed_path = feed_path
        self.ws_url = ws_url
        self.speed = max(0.1, speed)
        self.fast_mode = fast_mode
        self.skip_to_walkoff = skip_to_walkoff
        self.max_plays = max_plays
        self.ticket_id = ticket_id
        
        self.bot_messages = []
        self.plays_streamed = 0
        self.walkoff_reached = False
        
    def prepare_environment(self):
        """Seed schedule and seat personas via FastAPI on Port 8095 (Invariants I.8 & I.9)."""
        print(f"[*] Seeding sport_schedule for GamePk {self.game_pk} (NYY @ NYM)...")
        seed_res = api_client.seed_sport_schedule(
            game_pk=self.game_pk,
            sport="MLB",
            home_team="NYM",
            away_team="NYY",
            home_team_name="New York Mets",
            away_team_name="New York Yankees",
            game_date=datetime.now().strftime("%Y-%m-%d"),
            game_time="1:40 PM",
            venue="Citi Field",
            status="In Progress",
            room_state="active",
            boggs_level=3,
            home_score=0,
            away_score=0
        )
        print(f"✔ Schedule seeded: {seed_res.get('matchup')} ({seed_res.get('room_state')})")
        
        print(f"[*] Seating NYM & NYY advocates into room {self.game_pk}...")
        seat_res = api_client.seat_room_personas(
            game_pk=self.game_pk,
            personas=SUBWAY_PERSONAS,
            prompt_overlay="2026 Subway Series Live Replay: Citi Field 10th-inning walk-off clash."
        )
        print(f"✔ Seated {seat_res.get('seated_count')} advocates: {', '.join(seat_res.get('personas', []))}")
        
    async def listen_for_bots(self, ws):
        """Asynchronously collect incoming chat messages from commentator bots."""
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    mtype = data.get("type")
                    if mtype in ("CHAT_MESSAGE", "ROOM_CHAT"):
                        room = str(data.get("target_game_pk") or data.get("room") or "")
                        user = data.get("user") or data.get("persona") or "Unknown"
                        text = data.get("text", "")
                        if room == self.game_pk or room in ("GLOBAL", ""):
                            self.bot_messages.append({"user": user, "text": text, "time": time.strftime("%H:%M:%S")})
                            print(f"   💬 [BOT DIALECTIC] @{user}: {text}")
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[!] Bot listener terminated: {e}")

    async def run(self):
        self.prepare_environment()
        
        print(f"\n[*] Loading Statcast feed from {self.feed_path}...")
        with open(self.feed_path, "r") as f:
            feed = json.load(f)
            
        all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
        total_plays = len(all_plays)
        print(f"✔ Ingested {total_plays} total plays from Statcast feed.")
        
        if self.skip_to_walkoff:
            start_index = max(0, total_plays - 10)
            print(f"⚡ Fast-forward: Starting at play index {start_index} (10th Inning Drama)...")
            plays_to_run = all_plays[start_index:]
        else:
            plays_to_run = all_plays
            
        if self.max_plays:
            plays_to_run = plays_to_run[:self.max_plays]
            
        print(f"[*] Connecting to FanStack WebSocket Relay: {self.ws_url}...")
        async with websockets.connect(self.ws_url) as ws:
            print(f"✔ Connected to WebSocket Relay! Joining room {self.game_pk}...")
            await ws.send(json.dumps({"type": "ROOM_JOIN", "room": self.game_pk}))
            
            listener_task = asyncio.create_task(self.listen_for_bots(ws))
            
            curr_away_score = 0
            curr_home_score = 0
            
            try:
                for idx, play in enumerate(plays_to_run):
                    about = play.get("about", {})
                    inning = about.get("inning", 1)
                    half = about.get("halfInning", "top")
                    inning_label = f"{'Top' if half.lower() == 'top' else 'Bot'} {inning}"
                    
                    matchup = play.get("matchup", {})
                    batter = matchup.get("batter", {}).get("fullName", "Batter")
                    pitcher = matchup.get("pitcher", {}).get("fullName", "Pitcher")
                    
                    result = play.get("result", {})
                    desc = result.get("description", "")
                    event_type = result.get("event", "play")
                    away_score = result.get("awayScore", curr_away_score)
                    home_score = result.get("homeScore", curr_home_score)
                    curr_away_score = away_score
                    curr_home_score = home_score
                    
                    play_events = play.get("playEvents", [])
                    
                    # Iterate pitch sub-events or synthesize main play
                    pitch_speed = "---"
                    pitch_name = "---"
                    hit_speed = None
                    launch_angle = None
                    hit_distance = None
                    
                    for pe in play_events:
                        if pe.get("isPitch"):
                            details = pe.get("pitchData", {})
                            pitch_speed = str(details.get("startSpeed", "---"))
                            pitch_name = pe.get("details", {}).get("type", {}).get("description", "Pitch")
                            hit_data = pe.get("hitData", {})
                            if hit_data:
                                hit_speed = hit_data.get("launchSpeed")
                                launch_angle = hit_data.get("launchAngle")
                                hit_distance = hit_data.get("totalDistance")
                                
                    is_last_play = (idx == len(plays_to_run) - 1) or ("Carson Benge" in desc and "Marcus Semien scores" in desc)
                    
                    telemetry_packet = {
                        "type": "CMD_SYNC_STATE",
                        "target_game_pk": self.game_pk,
                        "data": {
                            "game_pk": self.game_pk,
                            "home_team": "NYM",
                            "away_team": "NYY",
                            "home_score": home_score,
                            "away_score": away_score,
                            "inning": inning_label,
                            "outs": play.get("count", {}).get("outs", 0),
                            "balls": play.get("count", {}).get("balls", 0),
                            "strikes": play.get("count", {}).get("strikes", 0),
                            "pitcher": pitcher,
                            "batter": batter,
                            "pitch_name": pitch_name,
                            "pitch_speed": pitch_speed,
                            "hit_speed": hit_speed,
                            "launch_angle": launch_angle,
                            "hit_distance": hit_distance,
                            "status_msg": desc,
                            "is_telemetry": True,
                            "is_final": is_last_play
                        }
                    }
                    
                    await ws.send(json.dumps(telemetry_packet))
                    self.plays_streamed += 1
                    
                    print(f"[{inning_label}] {pitcher} vs {batter} | NYY {away_score} - NYM {home_score} | {desc[:60]}...")
                    
                    if "homers" in desc.lower() or "home run" in desc.lower():
                        await ws.send(json.dumps({
                            "type": "trigger_event",
                            "event": "home_run",
                            "target_game_pk": self.game_pk
                        }))
                        await ws.send(json.dumps({
                            "type": "update_context",
                            "text": f"HOME RUN ALERT: {desc}",
                            "target_game_pk": self.game_pk
                        }))

                    if is_last_play:
                        self.walkoff_reached = True
                        print("\n" + "="*80)
                        print("🎉 10th INNING WALK-OFF VICTORY FOR THE NEW YORK METS! (7 - 6 FINAL)")
                        print(f"Play: {desc}")
                        print("="*80 + "\n")
                        
                        # Trigger commentator bots on walk-off
                        await ws.send(json.dumps({
                            "type": "trigger_event",
                            "event": "walk_off",
                            "target_game_pk": self.game_pk
                        }))
                        await ws.send(json.dumps({
                            "type": "update_context",
                            "text": f"10TH INNING WALK-OFF VICTORY! {desc}",
                            "target_game_pk": self.game_pk
                        }))
                        await ws.send(json.dumps({
                            "type": "CHAT_MESSAGE",
                            "room": self.game_pk,
                            "target_game_pk": self.game_pk,
                            "user": "Pilot",
                            "text": f"METS WIN! CARSON BENGE WALKS IT OFF 7-6! @barf @7_train_terry @BronxBomberFury"
                        }))

                        # Finalize schedule in database
                        api_client.seed_sport_schedule(
                            game_pk=self.game_pk,
                            home_team="NYM",
                            away_team="NYY",
                            status="Final (10)",
                            home_score=7,
                            away_score=6,
                            room_state="active"
                        )
                        break
                        
                    # Delay pacing based on speed
                    if not self.fast_mode:
                        sleep_time = max(0.05, 1.0 / self.speed)
                        await asyncio.sleep(sleep_time)
                    else:
                        await asyncio.sleep(0.05)
                        
                # Allow 2 seconds for trailing bot responses
                print("[*] Gathering final commentator bot banter...")
                await asyncio.sleep(2.0)
                
            finally:
                listener_task.cancel()
                
        print(f"\n✔ Simulation completed! Plays Streamed: {self.plays_streamed}, Walk-off Reached: {self.walkoff_reached}")
        print(f"✔ Commentator bot messages recorded: {len(self.bot_messages)}")
        return {
            "game_pk": self.game_pk,
            "plays_streamed": self.plays_streamed,
            "walkoff_reached": self.walkoff_reached,
            "bot_messages_count": len(self.bot_messages),
            "bot_messages": self.bot_messages
        }

def main():
    parser = argparse.ArgumentParser(description="Statcast Replay GamePack Simulation Engine")
    parser.add_argument("--gamepk", default="823628", help="MLB GamePk")
    parser.add_argument("--feed", default=DEFAULT_FEED_PATH, help="Path to cached Statcast JSON feed")
    parser.add_argument("--ws", default=DEFAULT_WS_URL, help="FanStack WebSocket Relay URL")
    parser.add_argument("--speed", type=float, default=4.0, help="Replay speed multiplier (default 4.0x)")
    parser.add_argument("--fast", action="store_true", help="Execute rapid test sweep")
    parser.add_argument("--skip-to-walkoff", action="store_true", help="Jump directly to 10th inning walk-off")
    parser.add_argument("--plays", type=int, default=None, help="Max plays to execute")
    parser.add_argument("--verify-twin", action="store_true", help="Capture live Pegasus Playwright visual twin")
    parser.add_argument("--ticket-id", default="WO0010059-FANSTACK-SUBWAY-SERIES-SIM", help="SDLC Ticket ID")
    
    args = parser.parse_args()
    
    engine = StatcastReplayEngine(
        game_pk=args.gamepk,
        feed_path=args.feed,
        ws_url=args.ws,
        speed=args.speed,
        fast_mode=args.fast,
        skip_to_walkoff=args.skip_to_walkoff,
        max_plays=args.plays,
        ticket_id=args.ticket_id
    )
    
    report = asyncio.run(engine.run())
    
    if args.verify_twin:
        print("\n🦅 Dispatched to node Pegasus (100.96.77.20) for Rule IV.2.b Visual Twin capture...")
        twin_res = api_client.capture_and_upload_ticket_twin(
            ticket_id=args.ticket_id,
            url="https://clio.taila01894.ts.net:3010/playcall-desk",
            click="button:has-text('AUDIENCE PULSE')",
            filename="pegasus_visual_twin_subway_series_sim.png"
        )
        print(f"✔ Pegasus Visual Twin Captured: {twin_res.get('local_path')}")
        print(f"✔ KI-095 Compliance: {twin_res.get('ki095_compliant')}")
        report["visual_twin"] = twin_res
        
    print("\n🏁 Replay Execution Finished.")
    return report

if __name__ == "__main__":
    main()
