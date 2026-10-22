import sqlite3
import asyncio
import websockets
import json
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

async def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Update status to 'Warmup' in mlb_schedule
    print("Updating game 823604 status in mlb_schedule to 'Warmup'...")
    cursor.execute("UPDATE mlb_schedule SET status = 'Warmup' WHERE game_pk = '823604'")
    
    # 2. Insert/replace game_context for game 823604
    sys_id = uuid.uuid4().hex
    print(f"Inserting game context into game_context (id: {sys_id})...")
    cursor.execute("""
        INSERT OR REPLACE INTO game_context (id, game_pk, source, headline, content, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        sys_id,
        "823604",
        "manual",
        "Red Sox Travel Delay",
        "Boston Red Sox experienced a travel delay flying out of Chicago and only arrived at Citi Field two hours ago. Warmups are now underway.",
        "delay,warmup"
    ))
    
    conn.commit()
    conn.close()
    print("Database updated successfully.")
    
    # 3. Connect to the WebSocket relay and send the update_context payload
    relay_uri = "ws://127.0.0.1:8008/ws"
    print(f"Connecting to WebSocket relay at {relay_uri}...")
    try:
        async with websockets.connect(relay_uri) as ws:
            payload = {
                "type": "update_context",
                "text": "[OVERRIDE: Pre-Game Warmup Alert! Boston Red Sox had a flight delay flying out of Chicago and only got to Citi Field 2 hours ago. The game was delayed but warmups have finally started. Advocates, argue about the delay, how it affects the Red Sox, and the Mets chances now! Keep it unhinged and in character! Show high energy! Max 50 words.]",
                "target_game_pk": "823604",
                "target_nodes": ["ALL"]
            }
            await ws.send(json.dumps(payload))
            print("Successfully sent update_context payload to the relay.")
    except Exception as e:
        print(f"Failed to connect/send to relay: {e}")

if __name__ == "__main__":
    asyncio.run(main())
