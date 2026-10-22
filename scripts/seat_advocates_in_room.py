#!/usr/bin/env python3
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_ID = "823293"
TARGET_PERSONAS = [
    'keith_fanboy', 'UncleStevieStan', '7_train_terry', 'barf',
    'Friar_Frank', 'Petco_Paul', 'Tacos_N_Tatis', 'Slam_Diego_Surfer',
    'Gwynn_Ghost', 'spin_rate_sylvia', 'compliance_karen', 'dr_terp',
    'ed_haskins', 'lupita_community', 'Altitude_Sickness', 'Rock_Pile_Randy'
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print(f"🧹 Clearing existing sparse mappings for room {ROOM_ID}...")
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (ROOM_ID,))
    deleted_count = cur.rowcount
    print(f"🗑️ Deleted {deleted_count} old mappings.")
    
    print("Seating 14 advocates in the game room...")
    inserted_count = 0
    for username in TARGET_PERSONAS:
        cur.execute("SELECT sys_id FROM sys_user WHERE LOWER(user_name) = LOWER(?)", (username,))
        row = cur.fetchone()
        if not row:
            print(f"❌ Error: Persona '{username}' not found in sys_user table! Seeding aborted.")
            conn.rollback()
            return
            
        persona_id = row[0]
        sys_id = uuid.uuid4().hex
        prompt_overlay = f"Current Matchup Context: Deployed to Game {ROOM_ID} (NYM @ SD)."
        
        cur.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
            VALUES (?, ?, ?, ?)
        """, (sys_id, persona_id, ROOM_ID, prompt_overlay))
        inserted_count += 1
        print(f"  🛋️ Seated {username} (ID: {persona_id})")
        
    conn.commit()
    conn.close()
    print(f"✅ Seating complete! Successfully seated {inserted_count} advocates in room {ROOM_ID}.")

if __name__ == "__main__":
    main()
