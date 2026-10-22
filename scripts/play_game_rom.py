import asyncio
import websockets
import json
import argparse
import os

async def play_rom(game_pk, interval):
    rom_path = f"/home/james/stacklabs/data/roms/game_{game_pk}.json"
    if not os.path.exists(rom_path):
        print(f"Error: ROM file not found at {rom_path}. Run download_game_rom.py first.")
        return
        
    with open(rom_path, 'r') as f:
        rom_data = json.load(f)
        
    ws_uri = "ws://127.0.0.1:8008"
    plays = rom_data.get("plays", [])
    
    print(f"[*] Loading ROM for Game {game_pk} ({rom_data.get('away_team')} @ {rom_data.get('home_team')})")
    print(f"[*] Found {len(plays)} plays. Booting DVR Player at {interval}s tempo...")
    
    async with websockets.connect(ws_uri, ping_interval=None, ping_timeout=None) as ws:
        await ws.send(json.dumps({"type": "JOIN_ROOM", "target_game_pk": game_pk}))
        await asyncio.sleep(1)
        
        for play in plays:
            payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": game_pk,
                "data": {
                    "game_pk": game_pk,
                    "away_score": play.get("away_score"),
                    "home_score": play.get("home_score"),
                    "away_team": rom_data.get("away_team"),
                    "home_team": rom_data.get("home_team"),
                    "inning": play.get("inning"),
                    "outs": play.get("outs"),
                    "balls": play.get("balls"),
                    "strikes": play.get("strikes"),
                    "status_msg": play.get("desc"),
                    "pitcher": play.get("pitcher"),
                    "batter": play.get("batter"),
                    "mard_engine": True
                }
            }
            
            print(f"[{play.get('inning')}] {play.get('desc')}")
            await ws.send(json.dumps(payload))
            await asyncio.sleep(interval)
            
    print(f"[*] DVR Playback Complete for Game {game_pk}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FanStack DVR ROM Player")
    parser.add_argument("--game_pk", required=True, help="MLB Game PK of the ROM to play")
    parser.add_argument("--interval", type=int, default=20, help="Tempo interval in seconds (default: 20s for pitch clock)")
    args = parser.parse_args()
    
    asyncio.run(play_rom(args.game_pk, args.interval))
