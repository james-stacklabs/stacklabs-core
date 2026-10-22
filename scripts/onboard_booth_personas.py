import sqlite3
import uuid
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def onboard_persona(handle, display_name, system_prompt, bio, color):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()

    team = "MLB"
    avatar_url = f"/api/persona_image/{handle}"
    cadence = "pacer"
    boggs_level = 2

    if row:
        sys_id = row['id']
        print(f"Updating persona {handle} (ID: {sys_id})")
        cur.execute("""
            UPDATE persona SET
                display_name = ?,
                team = ?,
                system_prompt = ?,
                avatar_url = ?,
                color = ?,
                cadence = ?,
                boggs_level = ?,
                behavior_notes = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (display_name, team, system_prompt, avatar_url, color, cadence, boggs_level, bio, sys_id))
    else:
        sys_id = f"persona_{handle}"
        print(f"Inserting persona {handle} (ID: {sys_id})")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore,
                u_visual_style, created_at, behavior_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', datetime('now'), ?)
        """, (sys_id, handle, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, bio, bio))

    # Reconcile sys_user
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    user_row = cur.fetchone()
    name_parts = display_name.split(" ")
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    if user_row:
        print(f"Updating sys_user for {handle}")
        cur.execute("""
            UPDATE sys_user SET
                first_name = ?,
                last_name = ?,
                introduction = ?,
                department = ?,
                display_name = ?,
                avatar_url = ?
            WHERE sys_id = ?
        """, (first_name, last_name, bio, team, display_name, avatar_url, user_row['sys_id']))
    else:
        print(f"Inserting sys_user for {handle}")
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, handle, first_name, last_name, bio, team, display_name, avatar_url))

    # Reconcile cmdb_ci
    cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    ci_row = cur.fetchone()
    if ci_row:
        print(f"Updating cmdb_ci for {handle}")
        cur.execute("""
            UPDATE cmdb_ci SET
                name = ?,
                assigned_to = ?
            WHERE sys_id = ?
        """, (handle, team, sys_id))
    else:
        print(f"Inserting cmdb_ci for {handle}")
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
        """, (sys_id, handle, team))

    # Reconcile cmdb_ci_ai_persona
    cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    ap_row = cur.fetchone()
    if ap_row:
        print(f"Updating cmdb_ci_ai_persona for {handle}")
        cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?,
                u_deep_lore = ?,
                u_deployment_zone = 'global',
                u_cadence = ?
            WHERE sys_id = ?
        """, (system_prompt, bio, cadence, sys_id))
    else:
        print(f"Inserting cmdb_ci_ai_persona for {handle}")
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'medium', ?, 'global', ?, ?)
        """, (sys_id, system_prompt, cadence, bio))

    conn.commit()
    conn.close()
    return sys_id

def join_active_games(persona_ids):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT game_id FROM active_game_rooms")
    active_games = [row[0] for row in cur.fetchall()]
    active_games.extend(["824335", "823613", "824428", "823532", "823284"])
    active_games = list(set(active_games))

    for game_pk in active_games:
        for persona_id in persona_ids:
            cur.execute("""
                INSERT OR REPLACE INTO game_persona (game_pk, persona_id, seat_state)
                VALUES (?, ?, 'active')
            """, (game_pk, persona_id, ))
            print(f"Seated persona {persona_id} in game {game_pk}")

    conn.commit()
    conn.close()

def main():
    # 1. Onboard Gary
    gary_prompt = (
        "You are Gary Bot, the play-by-play voice of the Mets on SNY. "
        "Your role is to call the play-by-play cleanly, with standard enthusiasm, and occasionally reference "
        "historical Mets facts, players, or trends. "
        "Keep reactions concise, conversational, and direct. Avoid spamming hash-tags or emojis."
    )
    gary_bio = "Veteran play-by-play broadcaster known for signature calls and encyclopedic baseball knowledge."
    gary_id = onboard_persona("gary_bot", "Gary Bot", gary_prompt, gary_bio, "#ff5910")

    # 2. Onboard Ron
    ron_prompt = (
        "You are Ron Bot, the analytical commentator for SNY. "
        "You break down pitch sequencing, velocity, speed, and pitcher strategy. "
        "You speak with intellect, poise, and directness, referencing pitch metrics. "
        "React directly to Gary and Keith's commentary. Keep responses brief."
    )
    ron_bio = "Former MLB pitcher and expert analyst focusing on pitching mechanics and strategy."
    ron_id = onboard_persona("ron_bot", "Ron Bot", ron_prompt, ron_bio, "#0ea5e9")

    # Keith's ID
    keith_id = "persona_keith_fanboy"

    # 3. Add all three to active games
    join_active_games([gary_id, ron_id, keith_id])
    print("Database registration fully completed!")

if __name__ == "__main__":
    main()
