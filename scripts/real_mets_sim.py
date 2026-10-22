import asyncio
import websockets
import json

# =========================================================================
# SOVEREIGN OS: THE 2024 LINDOR OVATION PROTOCOL
# =========================================================================

async def run_simulation():
    uri = "ws://localhost:8000/ws"
    
    script = [
        {
            "author": "Dot", 
            "text": "Telemetry update: 11-game losing streak confirmed. We return to Citi Field tomorrow. Probability of crowd toxicity: 99.9%.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "Terry", 
            "text": "YOU'RE DAMN RIGHT IT'S 99.9%! IF THEY THINK THEY CAN COME BACK TO QUEENS AFTER DROPPING 11 STRAIGHT WITHOUT GETTING BOOED INTO OBLIVION, THEY'RE DELUSIONAL!",
            "reaction_image": "/avatars/terry.png"
        },
        {
            "author": "Barf", 
            "text": "BOO THEM! THROW THE PASTRAMI ON THE FIELD! BURN THE STADIUM DOWN! THIS IS A SCHEDULED TIMELINE COLLAPSE!", 
            "reaction_image": "/avatars/barf.png"
        },
        {
            "author": "WardyIcon", 
            "text": "Guys, wait. Think about it. Think about April 2024. Francisco Lindor was in the worst slump of his career. He came back to Citi Field... and instead of booing him... we gave him a Standing Ovation.",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "WardyIcon", 
            "text": "And what happened? He broke the slump. He put the entire franchise on his back and carried us to the NLCS! The Standing Ovation broke the curse!",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "UncleStevieStan", 
            "text": "Wardy is absolutely right! The Standing Ovation is an empirical market inefficiency! It reverses negative energy! Uncle Steve would applaud this! We have to cheer them tomorrow!", 
            "reaction_image": "/avatars/unclesteviestan.png"
        },
        {
            "author": "Dot", 
            "text": "Calculating 'Standing Ovation' anomaly... historical 2024 data confirms a 300% surge in offensive production post-ovation. Re-evaluating timeline.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "Terry", 
            "text": "SO YOU WANT ME TO STAND UP AND CHEER FOR A TEAM THAT JUST LOST 11 STRAIGHT GAMES?! I'M FROM LONG ISLAND! WE DON'T CHEER FOR LOSING!", 
            "reaction_image": "/avatars/terry.png" 
        },
        {
            "author": "Barf", 
            "text": "THIS IS TOXIC POSITIVITY! YA GOTTA BELIEVE IS A PSYOP CULT! I REFUSE TO STAND!", 
            "reaction_image": "/avatars/barf.png"
        },
        {
            "author": "WardyIcon", 
            "text": "You don't have a choice, Barf. Tomorrow night at Citi Field... we stand. We break the 11-game skid. LFGM.",
            "reaction_image": "/avatars/wardyicon.png"
        }
    ]
    
    print("Sovereign Engine Initializing: THE LINDOR OVATION PROTOCOL...")
    
    try:
        async with websockets.connect(uri) as websocket:
            for line in script:
                payload = {
                    "type": "CHAT_MSG",
                    "author": line["author"],
                    "text": line["text"]
                }
                if line["reaction_image"]:
                    payload["reaction_image"] = line["reaction_image"]
                    
                await websocket.send(json.dumps(payload))
                
                # Dynamic pacing
                pacing = max(3.0, len(line["text"]) / 22.0) 
                await asyncio.sleep(pacing) 
                
    except Exception as e:
        print(f"[!] Simulation Error: {e}")
        
    print("Broadcast Extracted. Ready for video rendering.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
