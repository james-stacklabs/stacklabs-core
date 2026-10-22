#!/usr/bin/env python3
import sqlite3
import json
import asyncio
import websockets
import os

async def trigger_panel():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_name, team FROM persona WHERE team IS NOT NULL")
    rows = c.fetchall()
    conn.close()

    personas = [r[0] for r in rows]
    if not personas:
        # Default fallback yappers
        personas = ["señora_caos", "standard_deviant_0", "silas_truegrit", "iron_gaze", "water_barrel_wayne"]
    
    context_text = (
        "DEBATE MODERATOR OVERRIDE: Gather immediately at Scruffy's roundtable for a live panel debate. "
        "Discuss the rumors of WeedStack's firesale and allegations that their experimental gummies are tested "
        "on local wildlife i.e. Catnip Wars. Stay 100% in character and fiercely defend or attack these factions! "
        "CRITICAL: Be extremely sarcastic, witty, and unhinged! Do not agree with each other!"
    )
    
    payload = {
        "type": "update_context",
        "text": context_text,
        "target_nodes": personas + ["ALL_ACTIVE_YAPPERS"],
        "target_game_pk": "GLOBAL",
        "engine_override": "local_llama3"
    }
    
    print(f"Triggering cross-faction Skew panel debate targeting: {personas}")
    try:
        async with websockets.connect("ws://localhost:8009", ping_interval=None) as ws:
            await ws.send(json.dumps(payload))
            print("Successfully transmitted Skew panel debate trigger!")
    except Exception as e:
        print(f"Failed to connect to Skew relay on Port 8009: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_panel())
