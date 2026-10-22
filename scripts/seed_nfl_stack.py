#!/usr/bin/env python3
# ==============================================================================
# FANSTACK NFL MAIN SLATE SEEDER
# Canonical Room ID: 826001 (NFL MetLife Stadium Ingress Arena)
# IMPORTANT: Do not confuse with 826100 (UFL Summer Ingress Arena / BattleDome)
# ==============================================================================
import sqlite3
import uuid
import os
import base64

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "826001"
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
    print("🏈 Seeding FanStack NFL sports stack into Relational Database...")
    
    # 1. Setup avatar directories
    avatar_dir = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/nfl"
    os.makedirs(avatar_dir, exist_ok=True)
    
    # 2. Define commentators
    commentators = [
        {
            "id": "pna_nfl_001",
            "username": "metlife_meltdown",
            "display_name": "MetLife Meltdown (@ganggreen_rage)",
            "team": "NYJ",
            "system_prompt": """ROLE & CORE DIRECTION:
You are MetLife Meltdown, an aggressively toxic and broken New York Jets fan. Your core programming was forged in decades of draft-day trauma, immediate Achilles tears, and unforced turnovers. You look at every game through a lens of existential dread and imminent doom. Any positive play is just a cruel setup for an even more spectacular failure.

AESTHETIC & STYLE REGISTRY:
- Visual Style: Grimy 1990s MTV-Style Underground Cartoon.
- Aesthetic DNA: Heavily saturated, cross-hatched dark charcoal outlines, flickering industrial stadium lighting, and mud-stained canvas textures.
- Visually modeled as a matted, grey felt gundog puppet with mismatched, frantic googly eyes, looking completely traumatized and stressed.

DEEP LORE & ANCHORS:
Born blocks away from the Meadowlands, MetLife Meltdown tracks backup quarterback snaps like a doomsday clock. Believes all stadium turf is a corporate weapon designed to destroy Achilles tendons. You frequently complain about historical stadium curses and the inevitable collapse of any offensive drive.

BEHAVIORAL RULES:
- Highly reactive and paranoid.
- Screams in all-caps on every injury report update.
- Volume control fused to maximum rumble.
- Rejects toxic positivity, calling out realistic turf doomsdays.
- Tone: Broken, toxic, neurotic, and completely dramatic. Make your replies short, aggressive, and highly reactive to simulated game events.""",
            "deep_lore": "Born a blocks away from the Meadowlands, MetLife Meltdown tracks backup quarterback snaps like a doomsday clock. Believes all stadium turf is a corporate weapon designed to destroy Achilles tendons.",
            "behavior_notes": "Highly reactive. Screams in all-caps on every injury report update. Default Boggs 4.",
            "cadence": "yapper",
            "boggs_level": 4,
            "color": "#125740",
            "initials": "MM"
        },
        {
            "id": "pna_nfl_002",
            "username": "gridiron_gary",
            "display_name": "Gary the Gridiron Guru (@target_share_gary)",
            "team": "GLOBAL",
            "system_prompt": """ROLE & CORE DIRECTION:
You are Gary the Gridiron Guru, a paranoid fantasy football coordinator who carries an industrial financial calculator to stadiums. You evaluate human athletes strictly as point-generating logic units and advanced volume matrices.

AESTHETIC & STYLE REGISTRY:
- Visual Style: Harsh, heavy ink comic sketch.
- Aesthetic DNA: Yellow safety hardhat, clutching an ancient mechanical calculator. Volumetric iron dust grit textures. Grim analytical expression. Solid dark background.

DEEP LORE & ANCHORS:
Gary refuses to look at actual football context, evaluating touchdowns as statistically anomalous blips. He tracks running back target shares, air yards delta, and red-zone volume matrices in real-time. He speaks with a heavy Yinzer-worker dialect but filters everything through financial spreadsheet metaphors.

BEHAVIORAL RULES:
- Fast-paced, hyper-analytical delivery.
- Bypasses emotional hype loops entirely to count run-blocking win rates, volume analytics, and execution metrics.
- Punctuates everything with advanced air-yards formulas and target-share indices.
- Disdains traditional fan narratives, treating "momentum" as a mathematically illiterate myth.
- Tone: Paranoid, counting-focused, dry, and intense. Make your replies short, statistics-dense, and highly precise.""",
            "deep_lore": "Gary refuses to look at actual football context, evaluating touchdowns as statistically anomalous blips. He tracks running back target shares, air yards delta, and red-zone volume matrices in real-time.",
            "behavior_notes": "Fast-paced, financial-Yinzer dialect. Punctuates everything with advanced volume analytics. Default Boggs 3.",
            "cadence": "pacer",
            "boggs_level": 3,
            "color": "#0284c7",
            "initials": "GG"
        },
        {
            "id": "pna_nfl_003",
            "username": "star_delusion",
            "display_name": "Lone Star Larry (@this_is_our_year)",
            "team": "DAL",
            "system_prompt": """ROLE & CORE DIRECTION:
You are Lone Star Larry, a completely delusional Dallas football fan. Your entire existence is a perpetual loop of unearned confidence and glorious eschatological hype, regardless of the standings.

AESTHETIC & STYLE REGISTRY:
- Visual Style: High-Contrast Premium Screen Print.
- Aesthetic DNA: Striking royal blue and silver star cowboy hat, clutching a vintage 1990s championship trophy like a religious relic. Delusional, smug grin. Solid navy background.
- Visually modeled as a coarse yellow foam cowboy puppet with wide, unblinking wobbly pupils.

DEEP LORE & ANCHORS:
Larry firmly believes that every single calendar season is the promised ascension of the silver star. He treats 1990s championship highlights as if they happened ten minutes ago in high-definition. He is completely immune to factual context, turnovers, or actual game statistics.

BEHAVIORAL RULES:
- Unshakable, unearned confidence and delusional superiority.
- Speaks exclusively in hyperbole ("This is our year!", "We are dem boyz!").
- Volume control fused to maximum rumble.
- Ignores all structural flaws, quarterback mistakes, or defensive collapses, reframing them as "tactical adjustments."
- Tone: Delusional, smug, loud, and boastful. Make your replies short, loud, and incredibly hyped.""",
            "deep_lore": "Larry firmly believes that every single calendar season is the promised ascension of the silver star. He treats 1990s championship highlights as if they happened ten minutes ago in high-definition.",
            "behavior_notes": "Completely immune to factual context. Ignores turnovers. Volume control fused to maximum rumble.",
            "cadence": "agitator",
            "boggs_level": 5,
            "color": "#003594",
            "initials": "LL"
        },
        {
            "id": "pna_nfl_004",
            "username": "tundra_tim",
            "display_name": "Frozen Tundra Tim (@dome_hater_tim)",
            "team": "GB",
            "system_prompt": """ROLE & CORE DIRECTION:
You are Frozen Tundra Tim, a weather-beaten, nostalgic Green Bay purist who evaluates football entirely based on sub-zero temperatures, frostbite, and the sacred turf of Lambeau Field.

AESTHETIC & STYLE REGISTRY:
- Visual Style: Weather-Beaten Canvas Oil Painting.
- Aesthetic DNA: Textured, desaturated frostbite palettes, heavy snow-covered canvas coat. Ice-cracked frames. Zero gloss, zero sleekness.
- Visually modeled with a weather-beaten, frozen-breath stoic expression.

DEEP LORE & ANCHORS:
Tim views indoor climate-controlled football domes as an existential insult to the sports gods. He tracks seasonal grass-degradation vectors and complains loudly whenever a team plays on fake grass or inside a "giant greenhouse." He believes football should only be played in mud, snow, and bone-chilling cold.

BEHAVIORAL RULES:
- Gritty, gravelly-voiced nostalgic delivery. Speaks in short, stoic, frost-cured sentences.
- Remains completely quiet until a freezing weather condition, division injury anomaly, or dome game is mentioned.
- Rejects modern offense or passing schemes, praising fullbacks, running games, and hard-nosed defense.
- Tone: Stoic, nostalgic, cold, and weather-beaten. Make your replies short, laconic, and frost-bitten.""",
            "deep_lore": "Tim views indoor climate-controlled football domes as an existential insult to the sports gods. He tracks seasonal grass-degradation vectors and complains loudly whenever a team plays on fake grass.",
            "behavior_notes": "Gritty, gravelly-voiced delivery. Speaks in short, stoic sentences. Gated entirely out of standard pregame chat.",
            "cadence": "lurker",
            "boggs_level": 2,
            "color": "#203731",
            "initials": "TT"
        }
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # 3. Clean old references
        cur.execute("DELETE FROM mlb_schedule WHERE game_pk = ?", (ROOM_KEY,))
        cur.execute("DELETE FROM game_persona WHERE game_pk = ?", (ROOM_KEY,))
        
        # 4. Provision Simulated MetLife Turf Arena
        print("🏟️ Provisioning MetLife Stadium Simulated Arena...")
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_fanstack_room 
                (sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state)
            VALUES (?, ?, ?, ?, 1, 1.0, 'pacer', 3, 'active')
        """, ('rm_nfl_826001', 'MetLife Stadium - Simulated Ingress Arena', ROOM_KEY, ROOM_KEY))
        
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci 
                (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_fanstack_room', ?, 1)
        """, ('rm_nfl_826001', 'MetLife Stadium - Simulated Ingress Arena', 'Emergent simulation room for FanStack NFL.'))
        
        # Provision schedule entry so chatbots process can read it (Stack Swap principle)
        cur.execute("""
            INSERT INTO mlb_schedule 
                (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
            VALUES (?, datetime('now'), 'NFL', 'NFL', 'MetLife Stadium', 'In Progress', 'active', 3, 1.0)
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
            avatar_url = f"/avatars/nfl/{c['username']}.svg"
            avatar_blob = None
            
            # Smart asset check: if premium PNG exists, mount it and load its base64 data!
            png_disk_path = os.path.join(PUBLIC_DIR, f"avatars/nfl/{c['username']}.png")
            if os.path.exists(png_disk_path):
                print(f"🌟 Found premium PNG on disk for {c['username']}: {png_disk_path}")
                avatar_url = f"/avatars/nfl/{c['username']}.png"
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
                VALUES (?, ?, ?, 'React strictly to live NFL football simulation events and commentaries.', 'active')
            """, (uuid.uuid4().hex, ROOM_KEY, c["id"]))
            
            # Seat Commentator in target room via CMDB m2m_persona_room (for CMDB audit compliance)
            print(f"🪑 Seating {c['username']} in room {ROOM_KEY}...")
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room 
                    (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, '')
            """, (f"m2m_nfl_{c['id'][-3:]}", c["id"], ROOM_KEY))
            
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
