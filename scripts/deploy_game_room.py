import argparse
import requests
import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
START_BOTS_URL = 'http://127.0.0.1:8000/api/system/start/bots'

def get_teams(game_pk):
    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url, timeout=5).json()
        away_abbrev = data['gameData']['teams']['away']['abbreviation']
        home_abbrev = data['gameData']['teams']['home']['abbreviation']
        return away_abbrev.lower(), home_abbrev.lower()
    except Exception as e:
        print(f"Error fetching MLB game info: {e}")
        return None, None

def deploy_personas(game_pk, chaos_mode):
    away, home = get_teams(game_pk)
    if not away or not home:
        print("Failed to resolve teams. Cannot deploy personas.")
        return

    print(f"Game {game_pk} identified as {away.upper()} @ {home.upper()}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # --- RULE 30: m2m-FIRST SELECTION ---
    # If a curated m2m roster exists for this room, respect it exactly.
    # Only fall back to team-based query if m2m has zero entries.
    cur.execute("""
        SELECT u.user_name FROM sys_user u
        JOIN m2m_persona_room m ON u.sys_id = m.persona
        WHERE m.room = ?
    """, (game_pk,))
    m2m_personas = [row[0] for row in cur.fetchall()]

    if m2m_personas:
        selected_personas = m2m_personas
        print(f"[m2m-FIRST] Using curated m2m roster for room {game_pk} ({len(selected_personas)} personas).")
    else:
        print(f"[FALLBACK] No m2m roster found for room {game_pk}. Building from team assignment.")
        away_aliases = [away]
        if away in ['oak', 'ath']: away_aliases.extend(['oak', 'ath'])
        home_aliases = [home]
        if home in ['oak', 'ath']: home_aliases.extend(['oak', 'ath'])

        if 'nym' in [a.lower() for a in away_aliases]:
            away_fans = ['barf', 'UncleStevieStan', 'keith_fanboy', '7_train_terry']
        else:
            away_placeholders = ",".join(["?"] * len(away_aliases))
            cur.execute(f"SELECT name FROM cmdb_ci WHERE assigned_to COLLATE NOCASE IN ({away_placeholders}) AND sys_class_name='cmdb_ci_ai_persona' AND name NOT LIKE '%barf_prime%' AND name NOT LIKE '%barf prime%' LIMIT 3", away_aliases)
            away_fans = [row[0] for row in cur.fetchall()]

        if 'nym' in [h.lower() for h in home_aliases]:
            home_fans = ['barf', 'UncleStevieStan', 'keith_fanboy', '7_train_terry']
        else:
            home_placeholders = ",".join(["?"] * len(home_aliases))
            cur.execute(f"SELECT name FROM cmdb_ci WHERE assigned_to COLLATE NOCASE IN ({home_placeholders}) AND sys_class_name='cmdb_ci_ai_persona' AND name NOT LIKE '%barf_prime%' AND name NOT LIKE '%barf prime%' LIMIT 3", home_aliases)
            home_fans = [row[0] for row in cur.fetchall()]

        selected_personas = away_fans + home_fans

        if chaos_mode:
            print("Chaos Mode ENABLED. Appending Preordained Chaos personas.")
            selected_personas.extend(['battery_chucker', 'battery_chucker_jr', 'the_liquify_sadist', 'tell_it_terry'])

    print(f"Assigning {len(selected_personas)} personas to Game {game_pk}...")
    for p in selected_personas:
        print(f" - {p}")

    overlay_text = f"Current Matchup Context: Deployed to Game {game_pk} ({away.upper()} @ {home.upper()})."

    # Resolve sys_user.sys_id for each persona name — m2m stores sys_ids not user_names (RULE 30)
    sp_placeholders = ",".join(["?"] * len(selected_personas))
    cur.execute(f"SELECT sys_id, user_name FROM sys_user WHERE user_name IN ({sp_placeholders})", selected_personas)
    persona_id_map = {row[1]: row[0] for row in cur.fetchall()}

    # Query game_persona for active personas in this room (carried-over personas)
    cur.execute("""
        SELECT u.sys_id, u.user_name FROM sys_user u
        JOIN game_persona gp ON u.sys_id = gp.persona_id
        WHERE gp.game_pk = ? AND gp.seat_state = 'active'
    """, (game_pk,))
    gp_active = cur.fetchall()

    active_names = list(selected_personas)
    for sys_id, user_name in gp_active:
        if user_name not in active_names:
            active_names.append(user_name)
        persona_id_map[user_name] = sys_id

    # Deactivate ALL personas first, then activate ONLY this room's combined active/carried-over personas
    # (prevents ghosts from prior rooms bleeding in)
    cur.execute("UPDATE sys_user SET active = 0 WHERE sys_id IN (SELECT sys_id FROM cmdb_ci_ai_persona)")
    
    if active_names:
        active_placeholders = ",".join(["?"] * len(active_names))
        cur.execute(f"UPDATE sys_user SET active = 1 WHERE user_name IN ({active_placeholders})", active_names)
        cur.execute(f"UPDATE cmdb_ci SET operational_status = 1 WHERE name IN ({active_placeholders})", active_names)
        
        # Delete non-selected/non-active personas from m2m_persona_room for this room
        active_sys_ids = [persona_id_map[name] for name in active_names if name in persona_id_map]
        if active_sys_ids:
            id_placeholders = ",".join(["?"] * len(active_sys_ids))
            cur.execute(f"DELETE FROM m2m_persona_room WHERE room = ? AND persona NOT IN ({id_placeholders})", [game_pk] + active_sys_ids)
        else:
            cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
    else:
        cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))

    for persona_name in active_names:
        persona_sys_id = persona_id_map.get(persona_name)
        if not persona_sys_id:
            print(f"  [WARN] No sys_user found for '{persona_name}' — skipping m2m insert")
            continue
        cur.execute("SELECT COUNT(*) FROM m2m_persona_room WHERE persona=? AND room=?", (persona_sys_id, game_pk))
        exists = cur.fetchone()[0]
        if exists:
            cur.execute("UPDATE m2m_persona_room SET prompt_overlay = ? WHERE persona = ? AND room = ?", (overlay_text, persona_sys_id, game_pk))
        else:
            new_id = uuid.uuid4().hex
            cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)",
                        (new_id, persona_sys_id, game_pk, overlay_text))
            print(f"  [m2m] Inserted {persona_name} ({persona_sys_id}) into room {game_pk}")

    if active_names:
        active_placeholders = ",".join(["?"] * len(active_names))
        try:
            cur.execute(f"UPDATE cmdb_ci_ai_persona SET deployment_zone = ? WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name IN ({active_placeholders}))", [game_pk] + active_names)
        except Exception:
            try:
                cur.execute(f"UPDATE cmdb_ci_ai_persona SET u_deployment_zone = ? WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name IN ({active_placeholders}))", [game_pk] + active_names)
            except Exception:
                pass
    
    cur.execute("UPDATE mlb_schedule SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (game_pk,))
    cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk != ? AND room_state = 'active'", (game_pk,))
    cur.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (game_pk,))
    cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (game_pk,))

    con.commit()
    con.close()
    
    print("Restarting FanStack MARD Engine bots to apply changes...")
    try:
        res = requests.post(START_BOTS_URL)
        print(res.json().get("message", "Restart command sent!"))
    except Exception as e:
        print(f"Error restarting bots: {e}")
    
    print(f"Success! The game room {game_pk} is fully provisioned and bots are joining now.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Deploy Personas to a FanCast Game Room")
    parser.add_argument('game_pk', type=str, help="MLB statsapi Game PK (e.g., 823642)")
    parser.add_argument('--chaos', action='store_true', help="Append Preordained Chaos (battery_chucker & jr) to the room")
    args = parser.parse_args()
    deploy_personas(args.game_pk, args.chaos)
