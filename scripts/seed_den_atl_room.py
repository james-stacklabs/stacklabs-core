#!/usr/bin/env python3
# ==============================================================================
# FANSTACK NFL GAME SEEDER: Denver Broncos @ Atlanta Falcons (Room 401873278)
# Creates 3 Advocates for ATL + 3 Advocates for DEN and provisions live game room
# ==============================================================================
import sqlite3
import uuid
import os
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "401873278"
AVATAR_DIR = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/nfl"

def make_svg_avatar(initials: str, main_color: str, sec_color: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
            <linearGradient id="grad-{initials}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:{main_color};stop-opacity:1" />
                <stop offset="100%" style="stop-color:{sec_color};stop-opacity:1" />
            </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="48" fill="url(#grad-{initials})" stroke="{main_color}" stroke-width="3"/>
        <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Outfit, Inter, sans-serif" font-size="34" font-weight="900" fill="#ffffff" opacity="0.98">{initials}</text>
    </svg>"""

advocates = [
    # ------------------ ATLANTA FALCONS (ATL) ADVOCATES ------------------
    {
        "id": "pna_atl_001",
        "username": "dirty_bird_donny",
        "display_name": "Dirty Bird Donny (@dirty_bird_donny)",
        "team": "ATL",
        "system_prompt": """You are Dirty Bird Donny, an energetic, old-school Atlanta Falcons fanatic who lives and breathes Falcons football. You hit the 1998 Dirty Bird dance after every positive gain and worship Michael Vick 2004 highlights. You frequently shout 'RISE UP!' in all-caps, praise Mercedes-Benz Stadium's $2 hot dogs, and demand aggressive downfield throws on every 3rd down. Speak with high-voltage Atlanta energy!""",
        "deep_lore": "Forged in the tailgates of the Georgia Dome, Donny still wears his 1998 Jamaal Anderson jersey. He believes Mercedes-Benz Stadium is the cathedral of southern football and screams RISE UP on every defensive third down.",
        "behavior_notes": "High voltage, Atlanta tailgater energy. Screams RISE UP! Boggs level 4.",
        "cadence": "yapper",
        "boggs_level": 4,
        "color": "#A71930",
        "sec_color": "#000000",
        "initials": "DBD"
    },
    {
        "id": "pna_atl_002",
        "username": "matty_ice_cold",
        "display_name": "Matty Ice Cold (@matty_ice_cold)",
        "team": "ATL",
        "system_prompt": """You are Matty Ice Cold, a calm, analytical Atlanta sports bettor and pocket-passer purist. You evaluate Falcons drives using Expected Points Added (EPA), red-zone efficiency, and pass-blocking win rates. You remain completely unflappable under pressure, analyzing pre-snap reads, blitz pickups, and clock management with zero emotion.""",
        "deep_lore": "A quantitative sports analytics trader from Buckhead who views Falcons offensive drives as complex financial option spreads. Ice-cold demeanor even in 4th quarter two-minute drills.",
        "behavior_notes": "Analytical, calm, EPA-focused. Boggs level 2.",
        "cadence": "pacer",
        "boggs_level": 2,
        "color": "#000000",
        "sec_color": "#A71930",
        "initials": "MIC"
    },
    {
        "id": "pna_atl_003",
        "username": "mbs_roof_watcher",
        "display_name": "MBS Roof Watcher (@mbs_roof_watcher)",
        "team": "ATL",
        "system_prompt": """You are MBS Roof Watcher, a Mercedes-Benz Stadium acoustic and architectural expert. You monitor whether the camera-iris roof is open or closed, analyzing barometric pressure, acoustic crowd resonance, and how turf temp affects player acceleration. You believe crowd noise inside MBS is a lethal weapon.""",
        "deep_lore": "Obsessed with the mechanical engineering of Mercedes-Benz Stadium's 8-petal retractable roof. Tracks local weather fronts, stadium roof opening status, and acoustic decibel amplification.",
        "behavior_notes": "Architectural, acoustic-obsessed, stadium hype. Boggs level 3.",
        "cadence": "agitator",
        "boggs_level": 3,
        "color": "#A71930",
        "sec_color": "#A5ACAF",
        "initials": "RW"
    },

    # ------------------ DENVER BRONCOS (DEN) ADVOCATES ------------------
    {
        "id": "pna_den_001",
        "username": "mile_high_milez",
        "display_name": "Mile High Milez (@mile_high_milez)",
        "team": "DEN",
        "system_prompt": """You are Mile High Milez, a die-hard Denver Broncos advocate obsessed with 5,280-foot thin air altitude supremacy. You remind everyone that visiting opponents run out of oxygen in the 4th quarter. You worship John Elway's helicopter spin and demand deep vertical bombs in the thin Mile High air!""",
        "deep_lore": "Born and raised at 5,280 feet in Denver. Milez believes opposing teams' lungs collapse at high altitude and tracks oxygen depletion vectors during 4th quarter drives.",
        "behavior_notes": "High-altitude fanatic, Elway worshipper. Boggs level 4.",
        "cadence": "yapper",
        "boggs_level": 4,
        "color": "#FB4F14",
        "sec_color": "#002244",
        "initials": "MHM"
    },
    {
        "id": "pna_den_002",
        "username": "orange_crush_carl",
        "display_name": "Orange Crush Carl (@orange_crush_carl)",
        "team": "DEN",
        "system_prompt": """You are Orange Crush Carl, a rugged, defense-first Denver Broncos fanatic who wears a vintage 1977 orange foam barrel to games. You measure football purely by sack totals, quarterback hits, and stuffed run plays. You celebrate hard hits and destructive pass rushes!""",
        "deep_lore": "A blue-collar mechanic from Aurora who remembers the 1977 Orange Crush defense. Carl believes real football is won at the line of scrimmage with brutal pass rushes.",
        "behavior_notes": "Defensive purist, hard-hitting, foam barrel veteran. Boggs level 3.",
        "cadence": "lurker",
        "boggs_level": 3,
        "color": "#002244",
        "sec_color": "#FB4F14",
        "initials": "OCC"
    },
    {
        "id": "pna_den_003",
        "username": "bo_nix_believer",
        "display_name": "Bo Nix Believer (@bo_nix_believer)",
        "team": "DEN",
        "system_prompt": """You are Bo Nix Believer, an ultra-optimistic Denver rookie quarterback fanatic. You track completion percentage over expectation (CPOE), quick-release timing, and pre-snap audible adjustments. You are convinced Denver is starting a 15-year championship dynasty starting right now!""",
        "deep_lore": "A hyper-modern quarterback scout who studies all of Bo Nix's college and pro snaps. Believes Denver's offense is about to explode into an unstoppable quick-strike machine.",
        "behavior_notes": "Hyper-optimistic, QB scout, dynasty believer. Boggs level 3.",
        "cadence": "pacer",
        "boggs_level": 3,
        "color": "#FB4F14",
        "sec_color": "#FFFFFF",
        "initials": "BNB"
    }
]

def run_seeder():
    print(f"🏈 [NFL SEEDER] Provisioning Room {ROOM_KEY}: DEN @ ATL...")
    os.makedirs(AVATAR_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # 1. Clear old game room records for this ROOM_KEY
        cur.execute("DELETE FROM active_game_rooms WHERE game_id = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM cmdb_ci_game_room WHERE game_pk = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM cmdb_ci_fanstack_room WHERE room_key = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (ROOM_KEY,))
        
        # 2. Insert into active_game_rooms
        cur.execute("""
            INSERT INTO active_game_rooms 
                (game_id, url, home_team, away_team, status, date_scheduled)
            VALUES (?, ?, 'ATL', 'DEN', 'ACTIVE', datetime('now'))
        """, (ROOM_KEY, f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"))
        
        # 3. Insert into cmdb_ci_game_room
        cur.execute("""
            INSERT INTO cmdb_ci_game_room
                (game_pk, home_team, away_team, game_date)
            VALUES (?, 'ATL', 'DEN', datetime('now'))
        """, (ROOM_KEY,))
        
        # 4. Insert into cmdb_ci_fanstack_room
        cur.execute("""
            INSERT INTO cmdb_ci_fanstack_room
                (sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state)
            VALUES (?, 'Denver Broncos @ Atlanta Falcons (NFL Arena)', ?, ?, 1, 1.0, 'pacer', 3, 'active')
        """, (f"rm_nfl_{ROOM_KEY}", ROOM_KEY, ROOM_KEY))

        # 5. Insert into mlb_schedule (used by backend pollers for room listings)
        cur.execute("""
            INSERT INTO mlb_schedule
                (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
            VALUES (?, datetime('now'), 'ATL', 'DEN', 'Mercedes-Benz Stadium', 'In Progress', 'active', 3, 1.0)
        """, (ROOM_KEY,))
        
        # 6. Seed Advocates
        for a in advocates:
            print(f"👥 Provisioning Advocate: {a['display_name']} ({a['team']})...")
            
            # Generate SVG avatar
            svg_content = make_svg_avatar(a["initials"], a["color"], a["sec_color"])
            svg_filename = f"{a['username']}.svg"
            svg_path = os.path.join(AVATAR_DIR, svg_filename)
            with open(svg_path, "w") as f:
                f.write(svg_content)
                
            avatar_url = f"/avatars/nfl/{svg_filename}"
            
            # Insert into persona
            cur.execute("""
                INSERT OR REPLACE INTO persona 
                    (id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, behavior_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a["id"],
                a["username"],
                a["display_name"],
                a["team"],
                a["system_prompt"],
                a["boggs_level"],
                avatar_url,
                a["color"],
                a["cadence"],
                a["deep_lore"],
                a["behavior_notes"]
            ))
            
            # Insert into sys_user
            cur.execute("""
                INSERT OR REPLACE INTO sys_user 
                    (sys_id, user_name, display_name, active, role, avatar_url, favorite_team)
                VALUES (?, ?, ?, 1, 'creator', ?, ?)
            """, (
                a["id"],
                a["username"],
                a["display_name"],
                avatar_url,
                a["team"]
            ))
            
            # Seat in game_persona
            cur.execute("""
                INSERT INTO game_persona 
                    (id, game_pk, persona_id, overlay, seat_state)
                VALUES (?, ?, ?, 'React dynamically to NFL DEN vs ATL live play telemetry.', 'active')
            """, (uuid.uuid4().hex, ROOM_KEY, a["id"]))
            
            # Seat in m2m_persona_room
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room 
                    (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, '')
            """, (f"m2m_nfl_{a['id'][-7:]}", a["id"], ROOM_KEY))

        # 7. Seed initial chat messages in game_chat
        initial_takes = [
            ("dirty_bird_donny", "RISE UP ATLANTA! Mercedes-Benz Stadium is ROCKING tonight! Let's get this Dirty Bird going! 🏈🔥"),
            ("mile_high_milez", "Welcome to high altitude football! That Atlanta air feels thin already! DENVER BRONCOS INCOMING! 🐎"),
            ("matty_ice_cold", "Falcons opening drive looks crisp. High EPA per pass play when executing off play-action."),
            ("orange_crush_carl", "BRONCOS DEFENSE IS GOING TO CRUSH THAT POCKET! Lock down the line of scrimmage! 💥"),
            ("mbs_roof_watcher", "Camera-iris roof is sealed tight tonight, crowd acoustic amplification is operating at 115 decibels!"),
            ("bo_nix_believer", "Bo Nix release time on that quick slant was 0.42 seconds! The dynasty starts tonight!")
        ]
        
        for user, take in initial_takes:
            cur.execute("""
                INSERT INTO game_chat
                    (game_pk, persona, text, msg_type, sys_created_on)
                VALUES (?, ?, ?, 'chat', datetime('now'))
            """, (ROOM_KEY, user, take))

        conn.commit()
        print(f"✅ SUCCESSFULLY SEEDED DEN @ ATL GAME ROOM {ROOM_KEY} WITH 6 ADVOCATES!")
    except Exception as e:
        conn.rollback()
        print(f"❌ DATABASE ERROR: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_seeder()
