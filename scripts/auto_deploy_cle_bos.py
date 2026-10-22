#!/usr/bin/env python3
"""
AUTO-DEPLOY: CLE@STL and BOS@MIN pregame lobby watcher.
Runs once — polls the MLB schedule until both PKs are found,
then deploys persona configurations and exits.
"""
import sqlite3, uuid, requests, time, sys

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
SCHEDULE_URL = 'https://statsapi.mlb.com/api/v1/schedule?sportId=1'

TARGET_MATCHUPS = [
    ('CLE', 'STL'),
    ('BOS', 'MIN'),
]
OVERLAY_SUFFIX = " BREAKING: Kevin McGonigle & Tigers sign 8yr/$150M extension through 2034."

deployed = set()

def get_personas_for(away, home):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    aliases_a = [away.lower()]
    aliases_h = [home.lower()]
    aph = ",".join(["?"] * len(aliases_a))
    cur.execute(f"SELECT name FROM cmdb_ci WHERE assigned_to COLLATE NOCASE IN ({aph}) AND sys_class_name='cmdb_ci_ai_persona' LIMIT 3", aliases_a)
    away_fans = [r[0] for r in cur.fetchall()]
    hph = ",".join(["?"] * len(aliases_h))
    cur.execute(f"SELECT name FROM cmdb_ci WHERE assigned_to COLLATE NOCASE IN ({hph}) AND sys_class_name='cmdb_ci_ai_persona' LIMIT 3", aliases_h)
    home_fans = [r[0] for r in cur.fetchall()]
    con.close()
    return away_fans + home_fans + ['wardy', 'dot']

def deploy(game_pk, away, home, selected):
    game_pk = str(game_pk)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    overlay = f"Current Matchup Context: Deployed to Game {game_pk} ({away} @ {home}).{OVERLAY_SUFFIX}"
    
    # Activate selected personas
    sp_ph = ",".join(["?"] * len(selected))
    cur.execute(f"UPDATE sys_user SET active = 1 WHERE user_name IN ({sp_ph})", selected)
    cur.execute(f"UPDATE cmdb_ci SET operational_status = 1 WHERE name IN ({sp_ph})", selected)

    for persona in selected:
        cur.execute("SELECT COUNT(*) FROM m2m_persona_room WHERE persona=?", (persona,))
        if cur.fetchone()[0]:
            cur.execute("UPDATE m2m_persona_room SET room=?, prompt_overlay=? WHERE persona=?", (game_pk, overlay, persona))
        else:
            sys_id = uuid.uuid4().hex
            cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?,?,?,?)", (sys_id, persona, game_pk, overlay))
    
    cur.execute(f"UPDATE cmdb_ci_ai_persona SET u_deployment_zone=? WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name IN ({sp_ph}))", [game_pk]+selected)
    con.commit()
    con.close()
    print(f"[AUTO-DEPLOY] ✅ {away}@{home} (PK:{game_pk}) → {selected}")

for attempt in range(60):  # Poll up to 5 minutes
    try:
        r = requests.get(SCHEDULE_URL, timeout=15)
        games = r.json().get('dates', [{}])[0].get('games', [])
        for g in games:
            aw = g['teams']['away']['team']['abbreviation']
            ht = g['teams']['home']['team']['abbreviation']
            pk = g['gamePk']
            key = f"{aw}@{ht}"
            for (ta, th) in TARGET_MATCHUPS:
                if aw == ta and ht == th and key not in deployed:
                    selected = get_personas_for(ta, th)
                    deploy(pk, ta, th, selected)
                    deployed.add(key)
        if len(deployed) >= len(TARGET_MATCHUPS):
            print("[AUTO-DEPLOY] All targets deployed. Exiting.")
            sys.exit(0)
    except Exception as e:
        print(f"[AUTO-DEPLOY] Fetch error: {e}")
    time.sleep(5)

print(f"[AUTO-DEPLOY] Deployed: {deployed}. Timed out waiting for: {set(f'{a}@{h}' for a,h in TARGET_MATCHUPS) - deployed}")
