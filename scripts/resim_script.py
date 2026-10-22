import asyncio
import websockets
import json
import re

async def resim():
    ws_uri = "ws://127.0.0.1:8008/ws"
    
    # Read key moments
    with open("/home/james/stacklabs/dna/dropzone/daily_22042026/key_moments_823641.md", "r") as f:
        content = f.read()

    # Simple parsing logic
    blocks = content.split('\n\n')
    events = []
    current_inning = "Top 1st"
    
    for block in blocks:
        if "Top" in block or "Bottom" in block:
            lines = block.strip().split('\n')
            if len(lines) == 1:
                current_inning = lines[0].strip()
            else:
                current_inning = lines[0].strip()
                block = '\n'.join(lines[1:])
                
        if "MIN" in block and "NYM" in block:
            # It's an event block
            lines = block.strip().split('\n')
            desc = ""
            for line in lines:
                if len(line) > 15 and "NYM" not in line and "MIN" not in line and "win prob" not in line:
                    desc += line + " "
            if desc:
                events.append({"inning": current_inning, "desc": desc.strip()})
                
    # Add a few insights
    events.append({"inning": "Top 9th", "desc": "Luke Weaver threw a Four-seam FB (59%), Changeup (30%), Cutter (9%), and Slider (2%) in 2025."})
                
    async with websockets.connect(ws_uri) as ws:
        # Join room
        await ws.send(json.dumps({"type": "JOIN_ROOM", "target_game_pk": "823641"}))
        await asyncio.sleep(1)
        
        for i, ev in enumerate(events):
            print(f"Injecting: {ev['inning']} - {ev['desc']}")
            payload = {
                "type": "CMD_SYNC_STATE",
                "target_game_pk": "823641",
                "data": {
                    "game_pk": "823641",
                    "away_score": 2,
                    "home_score": 3,
                    "away_team": "MIN",
                    "home_team": "NYM",
                    "inning": ev["inning"],
                    "outs": 0,
                    "balls": 0,
                    "strikes": 0,
                    "status_msg": ev["desc"]
                }
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(8)  # Wait for chatbots to generate responses
            
if __name__ == "__main__":
    asyncio.run(resim())
