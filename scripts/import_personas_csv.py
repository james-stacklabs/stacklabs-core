import sqlite3
import csv
import json
import asyncio
import websockets

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
CSV_PATH = '/home/james/stacklabs/dna/personas_spreadsheet_full.csv'

def ingest_edits():
    print("=== [PHASE 3] GRUDGE ROTATION (UPSERT) ===")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    upsert_count = 0
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row.get("name")
                prompt = row.get("u_system_prompt")
                boggs = row.get("u_boggs_reactivity", "3")
                cadence = row.get("u_cadence", "Lurker")
                
                if not name or not prompt:
                    continue
                    
                # We update the cmdb_ci_ai_persona table based on joining via cmdb_ci name
                # find sys_id first
                c.execute("SELECT sys_id FROM cmdb_ci WHERE name=?", (name,))
                res = c.fetchone()
                if res:
                    sys_id = res[0]
                    c.execute("""
                        UPDATE cmdb_ci_ai_persona 
                        SET u_system_prompt=?, u_boggs_reactivity=?, u_cadence=?
                        WHERE sys_id=?
                    """, (prompt, boggs, cadence, sys_id))
                    upsert_count += 1
        
        conn.commit()
        print(f"> Upserted {upsert_count} persona records successfully.")
    except Exception as e:
        print(f"> [ERROR] Failed to read CSV or update DB: {e}")
    finally:
        conn.close()

async def trigger_mesh():
    print("> Triggering FanStack Mesh Hot-Reload...")
    try:
        async with websockets.connect('ws://127.0.0.1:8008') as ws:
            payload = {"action": "SYNC_DB_PERSONAS"}
            await ws.send(json.dumps(payload))
            print("> Payload dispatched successfully.")
    except Exception as e:
        print(f"> [MESH ERROR]: {e}")

if __name__ == '__main__':
    ingest_edits()
    asyncio.run(trigger_mesh())
