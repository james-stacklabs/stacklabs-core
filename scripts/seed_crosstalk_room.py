# /home/james/stacklabs/scripts/seed_crosstalk_room.py
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GAME_ID = "823213" # CHC @ SF on June 13, 2026
TICKET_ID = "WO-2026-003-CHCSF-PORTAL-HEAL"

# Curated Multi-Tenant Cross-Talk Roster - Eclectic 17
CROSS_TALK_USERNAMES = [
    "wavy",
    "senora",
    "barf_prime",
    "7_train_terry_ci",
    "420_linda",
    "pizzabot_74",
    "warden_barb",
    "cary_sterling",
    "vesper_vance",
    "barb_the_founder",
    "mando_enforcer",
    "battery_chucker_ci",
    "battery_chucker_jr_ci",
    "gaslamp_goon",
    "pancho_scholar",
    "brand_boycott",
    "isolated_silo"
]

# Additional game personas for 3v3 matchup and bouncer dot
ADDITIONAL_GAME_PERSONAS = [
    "fog_sentinel",
    "fog_horn_frank",
    "cubfanragemachine",
    "CubbieConspiracy",
    "bleacher_bum_bill",
    "dot"
]

def seed_crosstalk():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()
    
    # Register / Sync SDLC Ticketing / CMDB records first
    print("[*] Syncing SDLC Task and CMDB CI registration...")
    cur.execute("""
        INSERT OR REPLACE INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
        VALUES (?, 'story', 'WIP', 'fanstack_core', '⚾ Cubs @ Giants Fan Portal Activation & Stream Resolution')
    """, (TICKET_ID,))
    
    cur.execute("""
        INSERT OR REPLACE INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to)
        VALUES ('ci_fan_portal_3010', 'Sovereign Fan Portal', 'cmdb_ci_portal', 'Standalone Sports Fan Portal and Scoreboard.', 1, 'antigravity')
    """)
    
    cur.execute("""
        INSERT OR REPLACE INTO sys_module (id, module_name, display_name, description, icon, active, category, port)
        VALUES (?, 'fan_portal', 'Sovereign Fan Portal', 'Standalone Sports Fan Portal & Scoreboard', '⚾', 1, 'portal', 3010)
    """, (uuid.uuid4().hex,))
    
    # 1. Promote CHC @ SF room state to active on the dashboard
    cur.execute("""
        UPDATE cmdb_ci_fanstack_room 
        SET room_state = 'active', boggs_level = 3 
        WHERE game_pk = ?
    """, (GAME_ID,))

    cur.execute("""
        UPDATE mlb_schedule
        SET room_state = 'active'
        WHERE game_pk = ?
    """, (GAME_ID,))
    
    # 2. Clear out any legacy staging assignments for this room
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (GAME_ID,))
    cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (GAME_ID,))
    cur.execute("DELETE FROM game_chat WHERE game_pk = ?", (GAME_ID,))
    
    # 3. Double-seat each Advocate inside both legacy and current relational tables
    for username in CROSS_TALK_USERNAMES:
        cur.execute("SELECT id, display_name FROM persona WHERE user_name = ?", (username,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ Warning: Advocate '{username}' is missing from database. Skipping.")
            continue
        adv_id, display_name = row
        
        # Seat inside current Faction Room junction table (m2m_persona_room)
        m2m_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
            VALUES (?, ?, ?, ?)
        """, (m2m_id, adv_id, GAME_ID, f"Multi-Tenant Cross-Talk Event: Seated inside Game ID {GAME_ID}."))
        
        # Also seat inside game_persona table to satisfy join condition in load_fans()
        gp_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_id, GAME_ID, adv_id))
        
        print(f"✅ Seated Advocate: @{username} in Faction Room {GAME_ID}")

    # 4. Seat the 3v3 matchup and bouncer dot in game_persona
    for username in ADDITIONAL_GAME_PERSONAS:
        cur.execute("SELECT id, display_name FROM persona WHERE user_name = ?", (username,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ Warning: Matchup Advocate '{username}' is missing from database. Skipping.")
            continue
        adv_id, display_name = row
        
        gp_id = uuid.uuid4().hex
        cur.execute("""
            INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_id, GAME_ID, adv_id))
        print(f"✅ Seated Matchup/Dot: @{username} in game_persona for {GAME_ID}")
        
    con.commit()
    con.close()
    print("🏆 Successfully completed multi-tenant cross-talk seeder run.")

if __name__ == "__main__":
    seed_crosstalk()
