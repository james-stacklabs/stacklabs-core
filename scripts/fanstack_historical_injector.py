import sqlite3
import json
import time
import asyncio
import websockets
import argparse
import os

DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'
WS_URI = 'ws://localhost:8008/ws' 

async def stream_historical_game(game_pk: str, speed_multiplier: float):
    print(f"📡 [DVR INJECTOR] Booting Historical Stream for game_pk: {game_pk}")
    print(f"⏱️ Playback Speed: {speed_multiplier}x")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Query standard statcast columns. We assume order by at_bat_number asc, pitch_number asc
    try:
        c.execute("""
            SELECT * FROM statcast_pitches 
            WHERE game_pk = ? 
            ORDER BY at_bat_number ASC, pitch_number ASC
        """, (game_pk,))
    except sqlite3.OperationalError:
        # Fallback if at_bat_number or pitch_number is named differently
        c.execute("""
            SELECT * FROM statcast_pitches 
            WHERE game_pk = ? 
            ORDER BY rowid ASC
        """, (game_pk,))
        
    pitches = c.fetchall()
    conn.close()
    
    if not pitches:
        print(f"❌ [DVR INJECTOR] No pitches found for {game_pk} in sovereign_intelligence.db!")
        return

    print(f"📼 [DVR INJECTOR] Loaded {len(pitches)} pitches. Engaging WebSocket Relay...")
    
    async with websockets.connect(WS_URI) as ws:
        # Force the mesh into the correct room
        await ws.send(json.dumps({
            "type": "JOIN_ROOM",
            "target_game_pk": game_pk
        }))
        await asyncio.sleep(1)

        # Baseline parsing logic
        away_score = 0
        home_score = 0
        try:
            home_team = pitches[0]['home_team']
            away_team = pitches[0]['away_team']
        except KeyError:
            home_team = "HOME"
            away_team = "AWAY"
        
        last_ab = None
        
        for row in pitches:
            try:
                p = dict(row)
                # Top/Bot inning calculation
                inning_num = p['inning']
                inning_hlf = p.get('inning_topbot', 'Bot')
                inning = f"Top {inning_num}" if "Top" in str(inning_hlf) else f"Bot {inning_num}"
                
                # Basic mock scoring
                events = str(p.get('events', ''))
                if events == 'home_run':
                    if 'Top' in inning: away_score += 1
                    else: home_score += 1
                    
                status_msg = str(p.get('description', ''))
                if events and events != 'None':
                    status_msg += f". Play: {events.replace('_', ' ').upper()}"
                
                des = str(p.get('des', ''))
                if des and des != 'None':
                    status_msg += f". {des}"
                
                # Try to extract the batter's name from 'des'
                batter_name = "Unknown Batter"
                if des:
                    parts = des.split(' ')
                    if len(parts) >= 2:
                        batter_name = f"{parts[0]} {parts[1]}"
                
                pitcher_name = str(p.get('player_name', 'Unknown Pitcher'))
                pitch_type = str(p.get('pitch_name', 'Fastball'))
                pitch_spd = p.get('release_speed', 90.0)
                if not pitch_spd: pitch_spd = 90.0
                
                payload = {
                    "type": "CMD_SYNC_STATE",
                    "target_game_pk": game_pk,
                    "data": {
                        "game_pk": game_pk,
                        "away_score": away_score,
                        "home_score": home_score,
                        "away_team": away_team,
                        "home_team": home_team,
                        "inning": inning,
                        "outs": p.get('outs_when_up', 0) or 0,
                        "balls": p.get('balls', 0) or 0,
                        "strikes": p.get('strikes', 0) or 0,
                        "last_exit_velocity": p.get('launch_speed', '') or "",
                        "status_msg": status_msg,
                        "pitcher": pitcher_name,
                        "batter": batter_name,
                        "pitch_name": pitch_type,
                        "pitch_speed": round(float(pitch_spd), 1),
                        "onFirst": True if p.get('on_1b') else False,
                        "onSecond": True if p.get('on_2b') else False,
                        "onThird": True if p.get('on_3b') else False,
                        "pitchCount": p.get('pitch_number', 1) or 1
                    }
                }
                
                print(f"🎬 [DVR PLAY] {inning} | {status_msg}")
                await ws.send(json.dumps(payload))
                
                # Base real-world time between pitches is roughly 15 seconds.
                # We calculate delay based on multiplier.
                delay = 15.0 / speed_multiplier
                slept = 0
                while slept < delay:
                    if os.path.exists('/tmp/sovereign_flow_pause.flag'):
                        # Pause MLB telemetry during Flowmercial
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(1)
                        slept += 1
                        
            except Exception as e:
                print(f"⚠️ [DVR INJECTOR] Parsing drift on row: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FanStack DVR Historical Injector")
    parser.add_argument("--game_pk", required=True, help="MLB Game PK to simulate")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (e.g. 1.0, 5.0, 10.0)")
    args = parser.parse_args()
    
    asyncio.run(stream_historical_game(args.game_pk, args.speed))
