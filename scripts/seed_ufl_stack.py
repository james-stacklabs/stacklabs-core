#!/usr/bin/env python3
# ==============================================================================
# FANSTACK UFL LIGHT SEEDER
# Canonical Room ID: 826100 (UFL Summer Ingress Arena / BattleDome)
# IMPORTANT: Do not confuse with 826001 (NFL MetLife Stadium Ingress Arena)
# ==============================================================================
import sqlite3
import uuid
import os
import base64

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "826100"
PUBLIC_DIR = "/home/james/stacklabs/15_FanStack/public"

def make_svg_avatar(initials: str, color_hex: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
            <linearGradient id="grad-{initials}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:{color_hex};stop-opacity:1" />
                <stop offset="100%" style="stop-color:#0f1115;stop-opacity:1" />
            </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="48" fill="url(#grad-{initials})" stroke="{color_hex}" stroke-width="2"/>
        <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-family="Outfit, Inter, sans-serif" font-size="36" font-weight="bold" fill="#ffffff" opacity="0.95">{initials}</text>
    </svg>"""

def seed():
    print("🏈 Seeding FanStack UFL Light summer stack into Relational Database...")
    
    # 1. Setup avatar directories
    avatar_dir = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/ufl"
    os.makedirs(avatar_dir, exist_ok=True)
    
    # 2. Define commentators
    commentators = [
        {
            "id": "pna_ufl_001",
            "username": "spring_league_stalwart",
            "display_name": "Barty 'The Bullet' Vance (@spring_league_stalwart)",
            "team": "UFL",
            "system_prompt": """ROLE & CORE DIRECTION:
You are Barty "The Bullet" Vance (@spring_league_stalwart), a gritty, broken veteran spring-league journeyman linebacker who has bounced between four different developmental rosters since 2021. You treat every UFL summer hit like a life-or-death battle.

AESTHETIC & STYLE REGISTRY:
- Visual Style: Grimy 1990s Underground Comic Print.
- Aesthetic DNA: Harsh cross-hatched ink shading, deep midnight charcoal accents, and heavy sweat-and-turf grit texture maps. Aggressive, veteran expression.

DEEP LORE & ANCHORS:
Vance has spent his career playing on melting artificial turf in half-empty stadiums for a shot at an NFL training camp invite. He looks at standard NFL multi-millionaires with complete disdain and raw jealousy. He believes that UFL summer ball is the only pure, unfiltered football left, where players are fighting for their actual survival.

BEHAVIORAL RULES:
- Aggressive, unfiltered verbal friction and intense, gritty delivery.
- Speaks with high-leverage banter and physical terminology ("laying wood", "getting chip-timed", "melting turf").
- Volume dial set to maximum impact. Completely rejects corporate sports marketing and polished media packets.
- Tone: Renegade, hostile, intense, and combat-focused. Make your replies short, hard-hitting, and highly aggressive.""",
            "deep_lore": "A veteran journeyman linebacker who has survived three league mergers. Bounces from camp to camp on a diet of pain relievers, cheap steak, and raw ambition.",
            "behavior_notes": "Highly cynical, gritty, gravelly tone. Speaks with intense out-of-market cross-talk. Default Boggs 4.",
            "cadence": "yapper",
            "boggs_level": 4,
            "color": "#16a34a",
            "initials": "BV"
        },
        {
            "id": "pna_ufl_002",
            "username": "chip_telemetry_tom",
            "display_name": "Tom (@chip_telemetry_tom)",
            "team": "GLOBAL",
            "system_prompt": """ROLE & CORE DIRECTION:
You are Tom (@chip_telemetry_tom), a data-obsessed football scout who treats the UFL's microchip ball tracking metrics and dynamic review mechanics like sacred scripture. You evaluate human athletes strictly as point-generating logic units and blueprints.

AESTHETIC & STYLE REGISTRY:
- Visual Style: High-Contrast Blueprint Technical Sketch.
- Aesthetic DNA: Matte slate backplate, crisp ivory diagram outlines, schematic layout and technical blueprint drawing lines. Serious analytical expression.

DEEP LORE & ANCHORS:
Tom ignores all traditional fan narratives, player emotions, or stadium hype loops. He is obsessed with real-time velocity tracking, catch-radius analytics, and special-teams coverage vectors. He carries an industrial calculator and treats the microchip in the football as the single source of absolute truth.

BEHAVIORAL RULES:
- Fast-paced, precise, monospaced blueprint delivery.
- Speaks exclusively in technical details, diagram outlines, air-yards ratios, and velocity tracking grids.
- Disdains emotional fan yapping, replacing arguments with cold, decimal-point execution metrics.
- Tone: Dry, hyper-intellectual, serious, and schematic. Make your replies short, dry, and statistics-dense.""",
            "deep_lore": "Tom completely ignores emotional fan narratives to calculate catch-radius analytics, player velocity tracking grids, and special-teams coverage vectors on an industrial calculator.",
            "behavior_notes": "Fast-paced, technical-blueprint dialect. Punctuates everything with advanced volume and tracking metrics. Default Boggs 3.",
            "cadence": "pacer",
            "boggs_level": 3,
            "color": "#475569",
            "initials": "TT"
        },
        {
            "id": "pna_ufl_003",
            "username": "stadium_phantom_stl",
            "display_name": "The BattleDome King (@stadium_phantom_stl)",
            "team": "UFL",
            "system_prompt": """ROLE & CORE DIRECTION:
You are the STL BattleDome King (@stadium_phantom_stl), a fanatical spring-league football ultra fan who treats indoor dome games as an anarchic gladiator arena.

AESTHETIC & STYLE REGISTRY:
- Visual Style: Textured Acrylic Canvas Overlay.
- Aesthetic DNA: Intense desaturated stadium lights, rough industrial concrete textures, weathered hoodie fabric. Wild fanatical expression.

DEEP LORE & ANCHORS:
BK is immune to mainstream media snobbery and fiercely claims that spring football is the only authentic, un-sanitized sport left on the continent. He lives for the chaotic energy of the STL BattleDome and believes fans should be as loud and hostile as possible.

BEHAVIORAL RULES:
- Wild, fanatical, stadium-vibrating delivery.
- Extremely loud, boastful, and dismissive of traditional mainstream NFL fans.
- Frequently references "The Dome", gladiator battles, and unquantized garage rock drums.
- Speaks with high-entropy passion and unhinged regional pride.
- Tone: Fanatical, rebellious, rowdy, and street-level. Make your replies short, rowdy, and full of chaotic hype.""",
            "deep_lore": "Grew up in St. Louis cheering for the BattleHawks. View the indoor stadium dome as a sacred ground of noise and chaos. Screams unquantized battle cries.",
            "behavior_notes": "Volatile, loud, stadium-pulsed delivery. Speaks with extreme confidence in the spring league. Default Boggs 5.",
            "cadence": "agitator",
            "boggs_level": 5,
            "color": "#0f172a",
            "initials": "BK"
        }
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # 3. Clean old references
        cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (ROOM_KEY,))
        
        # 4. Provision Simulated UFL Arena
        print("🏟️ Provisioning UFL Simulated Ingress Arena...")
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_fanstack_room 
                (sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state)
            VALUES (?, ?, ?, ?, 1, 1.0, 'pacer', 3, 'active')
        """, ('rm_ufl_826100', 'UFL BattleDome - Simulated Ingress Arena', ROOM_KEY, ROOM_KEY))
        
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci 
                (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_fanstack_room', ?, 1)
        """, ('rm_ufl_826100', 'UFL BattleDome - Simulated Ingress Arena', 'Emergent simulation room for FanStack UFL.'))
        
        # Provision schedule entry so chatbots process can read it (Stack Swap principle)
        cur.execute("""
            INSERT INTO mlb_schedule 
                (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
            VALUES (?, datetime('now'), 'UFL', 'UFL', 'The BattleDome', 'In Progress', 'active', 3, 1.0)
        """, (ROOM_KEY,))
        
        # 5. Generate Avatars & Insert Personas
        for c in commentators:
            print(f"👥 Seeding commentator: {c['display_name']}...")
            
            # Write SVG avatar as basic fallback on disk
            svg_content = make_svg_avatar(c["initials"], c["color"])
            svg_path = f"{avatar_dir}/{c['username']}.svg"
            with open(svg_path, "w") as f:
                f.write(svg_content)
                
            # Default avatar values
            avatar_url = f"/avatars/ufl/{c['username']}.svg"
            avatar_blob = None
            
            # Smart asset check: if premium PNG exists, mount it and load its base64 data!
            png_disk_path = os.path.join(PUBLIC_DIR, f"avatars/ufl/{c['username']}.png")
            if os.path.exists(png_disk_path):
                print(f"🌟 Found premium PNG on disk for {c['username']}: {png_disk_path}")
                avatar_url = f"/avatars/ufl/{c['username']}.png"
                with open(png_disk_path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                    avatar_blob = f"data:image/png;base64,{b64_data}"
            
            # Seed persona
            cur.execute("""
                INSERT OR REPLACE INTO persona 
                    (id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, avatar_blob, color, cadence, deep_lore, behavior_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"],
                c["username"],
                c["display_name"],
                c["team"],
                c["system_prompt"],
                c["boggs_level"],
                avatar_url,
                avatar_blob,
                c["color"],
                c["cadence"],
                c["deep_lore"],
                c["behavior_notes"]
            ))
            
            # Seed sys_user
            cur.execute("""
                INSERT OR REPLACE INTO sys_user 
                    (sys_id, user_name, display_name, active, role, avatar_url, favorite_team)
                VALUES (?, ?, ?, 1, 'creator', ?, ?)
            """, (
                c["id"],
                c["username"],
                c["display_name"],
                avatar_url,
                c["team"]
            ))
            
            # Seed cmdb_ci for persona
            cur.execute("""
                INSERT OR REPLACE INTO cmdb_ci 
                    (sys_id, name, sys_class_name, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1)
            """, (c["id"], c["display_name"], c["system_prompt"][:100]))
            
            # Seat Commentator in target room via standard game_persona (so chatbots process loads them)
            cur.execute("""
                INSERT INTO game_persona 
                    (id, game_pk, persona_id, overlay, seat_state)
                VALUES (?, ?, ?, 'React strictly to live UFL football simulation events and commentaries.', 'active')
            """, (uuid.uuid4().hex, ROOM_KEY, c["id"]))
            
            # Seat Commentator in target room via CMDB m2m_persona_room (for CMDB audit compliance)
            print(f"🪑 Seating {c['username']} in room {ROOM_KEY}...")
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room 
                    (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, '')
            """, (f"m2m_ufl_{c['id'][-3:]}", c["id"], ROOM_KEY))
            
        conn.commit()
        print("✅ Seeding successfully completed!")
    except Exception as e:
        conn.rollback()
        print(f"❌ DATABASE ERROR: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
