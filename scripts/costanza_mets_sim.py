import asyncio
import websockets
import json

# =========================================================================
# SOVEREIGN OS: THE COSTANZA PROTOCOL (VERLANDER INVERSE)
# =========================================================================

async def run_simulation():
    uri = "ws://localhost:8000/ws"
    
    script = [
        {
            "author": "Dot", 
            "text": "PROTOCOL ENGAGED: The Costanza Inverse Strategy. Analyzing the December 2022 signing of Justin Verlander at $43.33M AAV.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "Dot", 
            "text": "Empirical data review: Verlander generated 1.1 fWAR at ~$39.3 Million per win. The Costanza Inverse dictates paying the league minimum for unheralded, soft-tossing arms.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "Dot", 
            "text": "Applying inverse metrics. Deploying the 'Churve/Changeup Scrap-Heap Syndicate'. Joey Lucchesi and José Buttó. 0.7 fWAR at $2.6 Million per win. Costanza Strategy saves $41.4 million with near-identical run prevention.", 
            "reaction_image": "/avatars/dot.png"
        },
        {
            "author": "WardyIcon", 
            "text": "This is absolute Stearns-level genius before David Stearns even got here! Everyone laughed when we didn't sign Verlander, but look at the metrics! Who needs a 40-year-old with a dead arm when you have the Lucchesi Churve?!",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "UncleStevieStan", 
            "text": "Exactly Wardy! Uncle Steve is just keeping our powder dry so we have the ultimate financial flexibility to give Juan Soto a billion dollars next year! The Cohen-naissance is real!", 
            "reaction_image": "/avatars/unclesteviestan.png"
        },
        {
            "author": "Terry", 
            "text": "ARE YOU LISTENING TO YOURSELVES?! I'm on the train right now reading a spreadsheet about scrap-heap soft-tossers! WHAT HAPPENED TO ACES?!", 
            "reaction_image": "/avatars/terry.png" 
        },
        {
            "author": "Barf", 
            "text": "Are you physically out of your mind?! We let Jacob deGrom—a generational, earth-shattering talent—walk away, and we replaced him with a guy throwing 89 mph meatballs and a rookie whose changeup is basically a cry for help?!", 
            "reaction_image": "/avatars/barf.png"
        },
        {
            "author": "WardyIcon", 
            "text": "Joey Fuego is the truth! Let the kids pitch! Ya Gotta Believe! LFGM!",
            "reaction_image": "/avatars/wardyicon.png"
        },
        {
            "author": "Barf", 
            "text": "I AM PAYING $18 FOR A PASTRAMI SANDWICH TO WATCH THE SYRACUSE METS ROTATION GET SHELLED BY THE BRAVES! THE WILPONS NEVER LEFT! THEY JUST PUT ON A STEVE COHEN SKIN SUIT!", 
            "reaction_image": "/avatars/barf.png"
        },
        {
            "author": "Dot", 
            "text": "System Note: Emotional volatility detected. Total collapse is imminent. We are cursed. Chaos is all we have.", 
            "reaction_image": "/avatars/dot.png"
        }
    ]
    
    print("Sovereign Engine Initializing: INCIDENT COSTANZA-VERLANDER...")
    print("Locked Personas: DOT, WARDY, STEVIE_STAN, TERRY, BARF")
    
    try:
        async with websockets.connect(uri) as websocket:
            for line in script:
                # Text chunking logic to prevent massive bubble overflow on TV
                # We split Dot and Barf's long paragraphs into rapid-fire sequential bubbles
                payload = {
                    "type": "CHAT_MSG",
                    "author": line["author"],
                    "text": line["text"]
                }
                if line["reaction_image"]:
                    payload["reaction_image"] = line["reaction_image"]
                    
                await websocket.send(json.dumps(payload))
                
                # Dynamic pacing logic based on word count
                pacing = max(3.5, len(line["text"]) / 20.0) 
                await asyncio.sleep(pacing) 
                
    except Exception as e:
        print(f"[!] Simulation Error: {e}")
        
    print("Broadcast Extracted. Ready for video rendering.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
