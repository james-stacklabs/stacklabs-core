import asyncio
import websockets
import json

async def run_simulation():
    uri = "ws://localhost:8000/ws"
    
    # 5 Persona Mets Fandom Pre-Game Script (Punchy / Short-form)
    script = [
        {
            "author": "WardyIcon", 
            "text": "Another bullpen collapse. I'm sick to my stomach.",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "UncleStevieStan", 
            "text": "Relax! The algorithms predict a 2029 wildcard!", 
            "reaction_image": "/avatars/unclesteviestan.png"
        },
        {
            "author": "Terry", 
            "text": "SCREW ALGORITHMS! WHERE IS THE HEALING GRIT?!", 
            "reaction_image": "/avatars/terry.png" 
        },
        {
            "author": "Dot", 
            "text": "99.8% probability of catastrophic failure tomorrow.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "Barf", 
            "text": "HAHAHA YOU'RE EXPERIENCING A SCHEDULED BRANCH!", 
            "reaction_image": "/avatars/barf.png"
        },
        {
            "author": "WardyIcon", 
            "text": "Even the AI knows we're cursed.",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "Terry", 
            "text": "THE GHOST OF THE WILPONS WILL NEVER LEAVE!", 
            "reaction_image": "/avatars/terry.png"
        }
    ]
    
    print("Sovereign Sandbox: PUNCHY METS SCENARIO")
    print("Broadcasting to The Skew...")
    
    try:
        async with websockets.connect(uri) as websocket:
            for i, line in enumerate(script):
                print(f"[{i+1}/{len(script)}] Submitting Chat Frame for: {line['author']}")
                
                payload = {
                    "type": "CHAT_MSG",
                    "author": line["author"],
                    "text": line["text"]
                }
                if line["reaction_image"]:
                    payload["reaction_image"] = line["reaction_image"]
                    
                await websocket.send(json.dumps(payload))
                await asyncio.sleep(4.0) 
                
    except Exception as e:
        print(f"[!] Simulation Error: {e}")
        
    print("Simulation Complete.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
