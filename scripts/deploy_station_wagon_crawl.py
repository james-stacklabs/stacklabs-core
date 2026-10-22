#!/usr/bin/env python3
import sqlite3
import uuid
import requests

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
START_BOTS_URL = "http://127.0.0.1:8000/api/system/start/bots"

SOURCE_ROOM = "823613"  # CHC @ NYM (Our Station Wagon Gang)
DEST_ROOM = "823284"    # ATL @ SD (The Watch Party Destination)

def main():
    print(f"🚗 Preparing the Station Wagon Watch Party Crawl from Room {SOURCE_ROOM} to Room {DEST_ROOM}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Retrieve the Mets/Cubs "Station Wagon Gang" from the source room
    cur.execute("""
        SELECT DISTINCT p.user_name FROM game_persona gp
        JOIN persona p ON gp.persona_id = p.id
        WHERE gp.game_pk = ?
    """, (SOURCE_ROOM,))
    source_advocates = [row[0] for row in cur.fetchall()]
    
    # Fallback/insurance to make sure our main Mets/Cubs gang is fully included
    mets_cubs_must_haves = [
        "barf", "keith_fanboy", "7_train_terry", "UncleStevieStan",
        "bartman", "ivy_inspector_ian", "CubsConspiracy",
        "dr_kosmos", "scruffy", "compliance_karen", "skyline_chili_chad",
        "bartmans_ghost", "dot", "wordy_nym"
    ]
    for m in mets_cubs_must_haves:
        if m not in source_advocates:
            # check if it exists in DB first
            cur.execute("SELECT 1 FROM persona WHERE user_name = ? COLLATE NOCASE", (m,))
            if cur.fetchone():
                source_advocates.append(m)

    print(f"👥 Station Wagon Gang ({len(source_advocates)} advocates): {', '.join(source_advocates)}")

    # 2. Retrieve/define the destination room advocates (Braves & Padres)
    # Start with the ones currently seated in the destination room
    cur.execute("""
        SELECT DISTINCT p.user_name FROM game_persona gp
        JOIN persona p ON gp.persona_id = p.id
        WHERE gp.game_pk = ?
    """, (DEST_ROOM,))
    dest_advocates = [row[0] for row in cur.fetchall()]

    # Explicitly ensure tomahawk, waffle_house_warrior, and battery_chucker_jr are in the destination roster
    braves_padres_must_haves = [
        "Tacos_N_Tatis", "friar_faithful_frank", "Gwynn_Ghost", "spitfire_spud",
        "battery_chucker_jr", "tomahawk", "waffle_house_warrior"
    ]
    for b in braves_padres_must_haves:
        if b not in dest_advocates:
            cur.execute("SELECT 1 FROM persona WHERE user_name = ? COLLATE NOCASE", (b,))
            if cur.fetchone():
                dest_advocates.append(b)

    print(f"🍻 Destination Room Original Roster ({len(dest_advocates)} advocates): {', '.join(dest_advocates)}")

    # 3. Combine the rosters, removing duplicates
    combined_usernames = list(set(source_advocates + dest_advocates))
    print(f"🎉 Combined Watch Party Roster ({len(combined_usernames)} advocates): {', '.join(combined_usernames)}")

    # 4. Resolve both canonical persona.id and sys_user.sys_id for each combined advocate
    resolved_advocates = []
    for uname in combined_usernames:
        cur.execute("SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE", (uname,))
        persona_row = cur.fetchone()
        
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ? COLLATE NOCASE", (uname,))
        sys_user_row = cur.fetchone()
        
        if persona_row and sys_user_row:
            resolved_advocates.append({
                'username': uname,
                'persona_id': persona_row[0],
                'sys_user_id': sys_user_row[0]
            })
        else:
            print(f"  [!] Warning: Keys not resolved for '{uname}' (Persona: {bool(persona_row)}, SysUser: {bool(sys_user_row)})")

    # 5. Clear and write the combined seating for DEST_ROOM
    cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (DEST_ROOM,))
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (DEST_ROOM,))

    sp_placeholders = ",".join(["?"] * len(combined_usernames))

    # Deactivate ALL personas first to prevent ghosts
    cur.execute("UPDATE sys_user SET active = 0 WHERE sys_id IN (SELECT sys_id FROM cmdb_ci_ai_persona)")
    
    # Activate the combined watch party personas
    cur.execute(f"UPDATE sys_user SET active = 1 WHERE user_name IN ({sp_placeholders})", combined_usernames)
    cur.execute(f"UPDATE cmdb_ci SET operational_status = 1 WHERE name IN ({sp_placeholders})", combined_usernames)

    for adv in resolved_advocates:
        uname = adv['username']
        p_id = adv['persona_id']
        sys_id = adv['sys_user_id']
        
        # Game persona seat
        gp_uuid = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO game_persona (id, game_pk, persona_id, seat_state)
            VALUES (?, ?, ?, 'active')
        """, (gp_uuid, DEST_ROOM, p_id))

        # m2m persona room entry
        m2m_uuid = str(uuid.uuid4()).replace('-', '')
        prompt_overlay = f"Current Matchup Context: Station Wagon Watch Party! Deployed to Game {DEST_ROOM} (ATL @ SD)."
        cur.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
            VALUES (?, ?, ?, ?)
        """, (m2m_uuid, sys_id, DEST_ROOM, prompt_overlay))
        
        print(f"  [🛋️] Seated {uname} in Room {DEST_ROOM}")

    # Set deployment zone for all combined advocates to DEST_ROOM
    cur.execute(f"""
        UPDATE cmdb_ci_ai_persona 
        SET u_deployment_zone = ? 
        WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name IN ({sp_placeholders}))
    """, [DEST_ROOM] + combined_usernames)

    # Deactivate other rooms and activate DEST_ROOM in schedule and rooms tables
    cur.execute("UPDATE mlb_schedule SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (DEST_ROOM,))
    cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (DEST_ROOM,))
    cur.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (DEST_ROOM,))
    cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (DEST_ROOM,))

    # Set active_game_rooms status
    cur.execute("""
        INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
        VALUES (?, ?, 'SD', 'ATL', 'ACTIVE', '2026-06-24')
    """, (DEST_ROOM, f"mlb.com/gameday/braves-vs-padres/2026/06/24/{DEST_ROOM}"))

    conn.commit()
    conn.close()
    print(f"[✔] Database transaction committed. Combined roster successfully seated in Room {DEST_ROOM}!")

    # 6. Trigger the hot-reload of bots
    print("Restarting FanStack MARD Engine bots to apply changes...")
    try:
        res = requests.post(START_BOTS_URL)
        print(res.json().get("message", "Restart command sent successfully!"))
    except Exception as e:
        print(f"Error restarting bots: {e}")

    print(f"🎉 SUCCESS! Room {DEST_ROOM} is now deployed with the combined Watch Party roster!")

if __name__ == "__main__":
    main()
