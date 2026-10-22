import asyncio
import websockets
import json
import random

async def loop():
    prompts = [
        "Provide a hardcore statistical breakdown of the Cubs home offensive production vs Mets pitching. Include expected wOBA against sinker-heavy staffs.",
        "Dismantle the Mets 0-8 streak using Pythagorean Expectation and BaseRuns. Explain mathematically why their run differential guarantees failure.",
        "Perform a probabilistic analysis of Francisco Alvarez's early season exit velocity distributions compared to the rest of the Mets lineup.",
        "Analyze the shifting run environment at Wrigley Field today factoring in wind speed, temperature density altitude, and the drag coefficient of the 2026 rawling baseballs.",
        "Issue a statistical anomaly warning: Cite the catastrophic discrepancies between the Mets' expected batting average (xBA) and their actual weighted outcomes."
    ]
    
    while True:
        try:
            p = random.choice(prompts)
            update_payload = {
                "type": "update_context",
                "text": f"SYSTEM OVERRIDE DIRECTIVE: {p} Deliver purely in mathematical/analytical tone with strict jargon. Reject emotional reasoning.",
                "target_game_pk": "824693",
                "target_nodes": ["dot"]
            }
            async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
                await ws.send(json.dumps(update_payload))
                print(f"Injected Stats Context: {p}")
        except Exception as e:
            print(f"Error during injection: {e}")
            
        # Wait 5 minutes
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(loop())
