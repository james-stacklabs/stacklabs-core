import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GAME_ID = "823615" # ATL @ NYM

CROSS_TALK_USERNAMES = [
    "wavy",
    "senora",
    "420_linda",
    "pizzabot_74",
    "warden_barb",
    "cary_sterling",
    "vesper_vance",
    "mando_enforcer",
    "gaslamp_goon",
    "pancho_scholar",
    "isolated_silo",
    "barf",
    "7_train_terry",
    "battery_chucker_jr",
    "the_chop_shop",
    "waffle_house_warrior",
    "dot"
]

def seed_crosstalk_today():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()
    
    print(f"[*] Seeding crosstalk advocates for Game ID {GAME_ID}...")
    
    # 1. Update schedule and fanstack room states
    cur.execute("""
        UPDATE cmdb_ci_fanstack_room 
        SET room_state = 'active', boggs_level = 3 
        WHERE game_pk = ?
    """, (GAME_ID,))

    cur.execute("""
        UPDATE mlb_schedule
        SET room_state = 'active', boggs_level = 3
        WHERE game_pk = ?
    """, (GAME_ID,))
    
    # 2. Clear out any current assignments for today to avoid duplicate constraint failures
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (GAME_ID,))
    cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (GAME_ID,))
    
    # 3. Seat each advocate inside both m2m_persona_room and game_persona
    for username in CROSS_TALK_USERNAMES:
        cur.execute("SELECT id, display_name FROM persona WHERE user_name = ?", (username,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ Warning: Advocate '{username}' is missing from database. Skipping.")
            continue
        adv_id, display_name = row
        
        # Seat inside m2m_persona_room
        m2m_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
            VALUES (?, ?, ?, ?)
        """, (m2m_id, adv_id, GAME_ID, f"Multi-Tenant Cross-Talk: Seated inside Game ID {GAME_ID}."))
        
        # Seat inside game_persona
        gp_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_id, GAME_ID, adv_id))
        
        print(f"✅ Seated Advocate: @{username} in Faction Room {GAME_ID}")
        
    con.commit()
    con.close()
    print("🏆 Successfully completed crosstalk seeder run for today's game.")

if __name__ == "__main__":
    seed_crosstalk_today()
