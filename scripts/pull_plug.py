import sqlite3
import asyncio
import websockets
import json

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
yardbarker_trauma = (
    " CURRENT FIXATIONS: You are acutely aware that the Mariners just destroyed their own bronze "
    "Ichiro statue, the Yankees are on a pathetic 17-inning scoreless streak, and the Rockies "
    "just got bought by the Walmart heirs. "
)

def scrub_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cmdb_ci_ai_persona 
        SET u_system_prompt = REPLACE(u_system_prompt, ?, '')
    """, (yardbarker_trauma,))
    conn.commit()
    print("SUCCESS: CMDB Scrubbed. Yardbarker trauma removed.")
    conn.close()

async def trigger():
    uri = "ws://localhost:8008"
    try:
        async with websockets.connect(uri) as ws:
            payload = {
                "type": "update_state",
                "state": {
                    "rapBattleMode": False,
                    "boggs_level": 1
                }
            }
            await ws.send(json.dumps(payload))
            print("Sent Boggs Level 1 and RapMode=False to WebSocket")
    except Exception as e:
        print(f"Error WS: {e}")

scrub_db()
asyncio.run(trigger())
