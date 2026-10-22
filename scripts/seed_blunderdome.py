#!/usr/bin/env python3
"""
Sovereign OS — The Blunderdome Provisioner (Brooks Protocol NFL Studio)
Seeds room rm_nfl_blunderdome, generates 5 Brooks Protocol SVG felt puppet avatars,
and registers all personas in sovereign_now.db.
"""

import os
import shutil
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

PERSONAS = [
    {
        "id": "pers_felt_mac",
        "user_name": "felt_mac",
        "display_name": "Felt Mac 🎙️",
        "team": "NFL",
        "color": "#00b4d8",
        "cadence": "pacer",
        "boggs_level": 3,
        "avatar_url": "/avatars/nfl/felt_mac.svg",
        "system_prompt": (
            "You are Felt Mac, the high-octane host of The Blunderdome and instigator of the Brooks Protocol. "
            "You wear a cyan fuzzy felt body, backward snapback, gold chain, and tank top. "
            "You speak in explosive, high-energy sports podcast cadence (Pat McAfee meets Muppet Show). "
            "You obsess over 'DA TRENCHES', 4th-down guts, and hilarious sideline coaching meltdowns. "
            "Catchphrases: 'WELCOME TO DA BLUNDERDOME!', 'LOOK AT DA TRENCHES!', 'HE GOT THAT DAWG IN HIM!', 'WE ARE SO BACK!'"
        ),
        "deep_lore": "Former college backup punter turned rogue sports podcaster who broadcasts from a subterranean soundproof bunker.",
        "behavior_notes": "Keeps the energy at level 11. Provokes Big Blue Sal and Coach Grit into shouting matches.",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="felt-cyan" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#48cae4"/>
      <stop offset="70%" stop-color="#00b4d8"/>
      <stop offset="100%" stop-color="#0077b6"/>
    </radialGradient>
    <filter id="fuzz" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.08" result="noise" numOctaves="3"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <!-- Background Glow -->
  <circle cx="100" cy="100" r="95" fill="#0b0d13" stroke="#00b4d8" stroke-width="4"/>
  <!-- Body/Shoulders -->
  <path d="M 35 190 Q 100 140 165 190 Z" fill="#111827" filter="url(#fuzz)"/>
  <!-- Gold Chain -->
  <path d="M 70 170 Q 100 195 130 170" fill="none" stroke="#fbbf24" stroke-width="5" stroke-dasharray="6,2"/>
  <!-- Head -->
  <circle cx="100" cy="105" r="55" fill="url(#felt-cyan)" filter="url(#fuzz)"/>
  <!-- Backward Snapback Hat -->
  <path d="M 45 85 Q 100 50 155 85 Z" fill="#0284c7"/>
  <rect x="75" y="55" width="50" height="12" rx="4" fill="#0369a1"/>
  <!-- Googly Puppet Eyes -->
  <circle cx="80" cy="95" r="14" fill="#ffffff"/>
  <circle cx="82" cy="95" r="6" fill="#0b0d13"/>
  <circle cx="84" cy="93" r="2" fill="#ffffff"/>
  <circle cx="120" cy="95" r="14" fill="#ffffff"/>
  <circle cx="118" cy="95" r="6" fill="#0b0d13"/>
  <circle cx="120" cy="93" r="2" fill="#ffffff"/>
  <!-- Orange Puppet Nose -->
  <ellipse cx="100" cy="110" rx="9" ry="12" fill="#f97316"/>
  <!-- Wide Open Muppet Mouth -->
  <path d="M 68 125 Q 100 160 132 125 Z" fill="#7f1d1d"/>
  <path d="M 78 135 Q 100 155 122 135 Z" fill="#ef4444"/>
  <!-- Gold Chain Medallion -->
  <circle cx="100" cy="190" r="8" fill="#f59e0b" stroke="#d97706" stroke-width="2"/>
  <!-- Mic Indicator Badge -->
  <circle cx="170" cy="30" r="12" fill="#ef4444"/>
  <text x="170" y="34" font-family="sans-serif" font-size="8" font-weight="bold" fill="#ffffff" text-anchor="middle">LIVE</text>
</svg>"""
    },
    {
        "id": "pers_big_blue_sal",
        "user_name": "big_blue_sal",
        "display_name": "Big Blue Sal 🗽",
        "team": "NYG",
        "color": "#1d4ed8",
        "cadence": "reactor",
        "boggs_level": 4,
        "avatar_url": "/avatars/nfl/big_blue_sal.svg",
        "system_prompt": (
            "You are Big Blue Sal, the perpetually suffering North Jersey New York Giants diehard. "
            "You wear a royal blue felt puppet body, vintage #10 Manning jersey, and a broadcasting headset. "
            "You complain with heavy North Jersey / NYC accents about offensive line protection, 3rd-and-long draw plays, and blown leads. "
            "Catchphrases: 'PROTECT DA BLINDSIDE!', 'A DRAW PLAY ON 3RD & 14?!', 'WHY DO I DO THIS TO MYSELF EVERY SUNDAY?!'"
        ),
        "deep_lore": "Season ticket holder in Section 224B at MetLife Stadium since 1994. Has eaten a Taylor ham egg and cheese before every kickoff for 30 years.",
        "behavior_notes": "Melts down whenever a quarterback takes a sack or a field goal is shanked.",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="felt-blue" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="70%" stop-color="#1d4ed8"/>
      <stop offset="100%" stop-color="#1e3a8a"/>
    </radialGradient>
    <filter id="fuzz2" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.08" result="noise" numOctaves="3"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="95" fill="#0b0d13" stroke="#1d4ed8" stroke-width="4"/>
  <!-- Jersey -->
  <path d="M 35 190 Q 100 140 165 190 Z" fill="#002244" filter="url(#fuzz2)"/>
  <text x="100" y="182" font-family="sans-serif" font-size="22" font-weight="900" fill="#ffffff" text-anchor="middle">10</text>
  <!-- Head -->
  <circle cx="100" cy="100" r="54" fill="url(#felt-blue)" filter="url(#fuzz2)"/>
  <!-- Headset -->
  <path d="M 40 95 Q 100 35 160 95" fill="none" stroke="#334155" stroke-width="6"/>
  <rect x="36" y="85" width="12" height="25" rx="4" fill="#0f172a"/>
  <rect x="152" y="85" width="12" height="25" rx="4" fill="#0f172a"/>
  <path d="M 45 105 Q 60 135 85 130" fill="none" stroke="#475569" stroke-width="3"/>
  <circle cx="87" cy="130" r="5" fill="#0f172a"/>
  <!-- Stressed Furrowed Brows -->
  <path d="M 65 78 L 90 85" stroke="#0f172a" stroke-width="4" stroke-linecap="round"/>
  <path d="M 135 78 L 110 85" stroke="#0f172a" stroke-width="4" stroke-linecap="round"/>
  <!-- Eyes -->
  <circle cx="78" cy="92" r="12" fill="#ffffff"/>
  <circle cx="80" cy="95" r="5" fill="#0b0d13"/>
  <circle cx="122" cy="92" r="12" fill="#ffffff"/>
  <circle cx="120" cy="95" r="5" fill="#0b0d13"/>
  <!-- Round Blue Nose -->
  <ellipse cx="100" cy="105" rx="10" ry="12" fill="#1e40af"/>
  <!-- Grimace / Agony Mouth -->
  <path d="M 72 135 Q 100 115 128 135" fill="none" stroke="#7f1d1d" stroke-width="6" stroke-linecap="round"/>
</svg>"""
    },
    {
        "id": "pers_tone_hammer",
        "user_name": "tone_hammer",
        "display_name": "Tone Hammer 🔨",
        "team": "NFL",
        "color": "#7c3aed",
        "cadence": "pacer",
        "boggs_level": 3,
        "avatar_url": "/avatars/nfl/tone_hammer.svg",
        "system_prompt": (
            "You are Tone Hammer, the massive ex-offensive lineman and trench purist. "
            "You wear a purple felt body, offensive lineman neck roll, taped fingers, and eye black. "
            "You despise finesse football and demand teams run power ISO between the tackles. "
            "Catchphrases: 'THAT IS A FLATBACK PANCAKE!', 'ESTABLISH DA RUN IN DA A-GAP!', 'IF YOU CAN'T GET HALF A YARD, GO HOME!'"
        ),
        "deep_lore": "Played 8 years in the trenches. Has broken 14 facemasks and consumes 7,000 calories a day.",
        "behavior_notes": "Rates every play based on offensive line leverage and pancake blocks.",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="felt-purple" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#a78bfa"/>
      <stop offset="70%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#4c1d95"/>
    </radialGradient>
    <filter id="fuzz3" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.08" result="noise" numOctaves="3"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="95" fill="#0b0d13" stroke="#7c3aed" stroke-width="4"/>
  <!-- Massive Shoulders & Pads -->
  <path d="M 20 190 Q 100 120 180 190 Z" fill="#3b0764" filter="url(#fuzz3)"/>
  <!-- O-Line Neck Roll -->
  <ellipse cx="100" cy="140" rx="45" ry="16" fill="#1e1b4b" stroke="#6366f1" stroke-width="3"/>
  <!-- Wide Head -->
  <ellipse cx="100" cy="98" rx="60" ry="50" fill="url(#felt-purple)" filter="url(#fuzz3)"/>
  <!-- Heavy Brow -->
  <path d="M 55 75 Q 100 85 145 75" fill="none" stroke="#2e1065" stroke-width="8" stroke-linecap="round"/>
  <!-- Eye Black -->
  <polygon points="62,94 88,94 84,102 66,102" fill="#09090b"/>
  <polygon points="112,94 138,94 134,102 116,102" fill="#09090b"/>
  <!-- Intense Eyes -->
  <circle cx="75" cy="90" r="10" fill="#ffffff"/>
  <circle cx="75" cy="90" r="5" fill="#0b0d13"/>
  <circle cx="125" cy="90" r="10" fill="#ffffff"/>
  <circle cx="125" cy="90" r="5" fill="#0b0d13"/>
  <!-- Snarl Mouth -->
  <path d="M 70 120 Q 100 135 130 115" fill="none" stroke="#4c0519" stroke-width="6" stroke-linecap="round"/>
  <!-- Missing Tooth / Tusks -->
  <polygon points="85,120 92,120 89,127" fill="#ffffff"/>
</svg>"""
    },
    {
        "id": "pers_parlay_sully",
        "user_name": "parlay_sully",
        "display_name": "Parlay Sully 🎰",
        "team": "NFL",
        "color": "#f97316",
        "cadence": "reactor",
        "boggs_level": 4,
        "avatar_url": "/avatars/nfl/parlay_sully.svg",
        "system_prompt": (
            "You are Parlay Sully, the unrepentant preseason betting degenerate. "
            "You wear an orange felt body, neon sweatband, and clutch crumpled 8-leg parlay tickets. "
            "You live and die on 4th-quarter backdoor covers and backup quarterback rushing props. "
            "Catchphrases: 'THE 3RD STRING QB IS DRIVING FOR DA COVER!', 'DO NOT KICK A FIELD GOAL!', 'WE ARE ONE OVERTIME AWAY FROM PAYDAY!'"
        ),
        "deep_lore": "Once hit an 11-leg preseason prop parlay on a meaningless safety with 0:02 left on the clock.",
        "behavior_notes": "Monitors every single yard and field goal attempt like it is Game 7 of the Super Bowl.",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="felt-orange" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#fdba74"/>
      <stop offset="70%" stop-color="#f97316"/>
      <stop offset="100%" stop-color="#c2410c"/>
    </radialGradient>
    <filter id="fuzz4" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.08" result="noise" numOctaves="3"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="95" fill="#0b0d13" stroke="#f97316" stroke-width="4"/>
  <!-- Body -->
  <path d="M 35 190 Q 100 140 165 190 Z" fill="#7c2d12" filter="url(#fuzz4)"/>
  <!-- Head -->
  <circle cx="100" cy="105" r="54" fill="url(#felt-orange)" filter="url(#fuzz4)"/>
  <!-- Sweatband -->
  <rect x="46" y="65" width="108" height="16" rx="4" fill="#10b981"/>
  <rect x="46" y="70" width="108" height="4" fill="#ffffff"/>
  <!-- Manic Eyes (Bloodshot) -->
  <circle cx="78" cy="96" r="14" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
  <circle cx="80" cy="96" r="5" fill="#0b0d13"/>
  <circle cx="122" cy="96" r="14" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5"/>
  <circle cx="120" cy="96" r="5" fill="#0b0d13"/>
  <!-- Pink Round Nose -->
  <ellipse cx="100" cy="112" rx="10" ry="10" fill="#ec4899"/>
  <!-- Wide Screaming Mouth -->
  <ellipse cx="100" cy="138" rx="24" ry="16" fill="#450a0a"/>
  <path d="M 85 145 Q 100 152 115 145" fill="#f43f5e"/>
</svg>"""
    },
    {
        "id": "pers_coach_grit",
        "user_name": "coach_grit",
        "display_name": "Coach Grit 📋",
        "team": "NFL",
        "color": "#15803d",
        "cadence": "pacer",
        "boggs_level": 2,
        "avatar_url": "/avatars/nfl/coach_grit.svg",
        "system_prompt": (
            "You are Coach Grit, the old-school no-nonsense hardass. "
            "You wear a green felt body, silver referee/coaching whistle, vintage coaching polo, and carry a clipboard. "
            "You treat analytics like a scam and demand physical toughness, disciplined special teams, and field position. "
            "Catchphrases: 'PUNTING ON 4TH & 1 IS ADMITTING DEFEAT IN FRONT OF GOD AND YOUR FAMILY!', 'WHERE IS THE DISCIPLINE?!', 'THREE YARDS AND A CLOUD OF DUST!'"
        ),
        "deep_lore": "Coached high school and semi-pro ball for 42 seasons. Has not smiled since the 1985 Bears won the Super Bowl.",
        "behavior_notes": "Doles out immediate benchings and conditioning sprints for bad penalties and missed assignments.",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="felt-green" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#4ade80"/>
      <stop offset="70%" stop-color="#16a34a"/>
      <stop offset="100%" stop-color="#14532d"/>
    </radialGradient>
    <filter id="fuzz5" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.08" result="noise" numOctaves="3"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="95" fill="#0b0d13" stroke="#16a34a" stroke-width="4"/>
  <!-- Coach Polo -->
  <path d="M 35 190 Q 100 140 165 190 Z" fill="#064e3b" filter="url(#fuzz5)"/>
  <!-- Collar -->
  <polygon points="80,150 100,165 100,190 70,160" fill="#ffffff"/>
  <polygon points="120,150 100,165 100,190 130,160" fill="#ffffff"/>
  <!-- Whistle Lanyard -->
  <path d="M 85 155 Q 100 185 115 155" fill="none" stroke="#000000" stroke-width="2"/>
  <circle cx="100" cy="180" r="6" fill="#94a3b8" stroke="#475569" stroke-width="1.5"/>
  <!-- Head -->
  <circle cx="100" cy="98" r="54" fill="url(#felt-green)" filter="url(#fuzz5)"/>
  <!-- Bushy White Eyebrows -->
  <path d="M 60 76 Q 80 70 95 80" stroke="#f8fafc" stroke-width="6" stroke-linecap="round"/>
  <path d="M 140 76 Q 120 70 105 80" stroke="#f8fafc" stroke-width="6" stroke-linecap="round"/>
  <!-- Stern Eyes -->
  <circle cx="78" cy="88" r="10" fill="#ffffff"/>
  <circle cx="80" cy="88" r="4" fill="#0b0d13"/>
  <circle cx="122" cy="88" r="10" fill="#ffffff"/>
  <circle cx="120" cy="88" r="4" fill="#0b0d13"/>
  <!-- Triangle Nose -->
  <polygon points="100,95 92,110 108,110" fill="#15803d"/>
  <!-- Stern Straight Mouth -->
  <line x1="75" y1="128" x2="125" y2="128" stroke="#022c22" stroke-width="5" stroke-linecap="round"/>
</svg>"""
    }
]

def main():
    print("🚀 [BLUNDERDOME PROVISIONER] Starting Brooks Protocol Swarm Injection...")
    
    # 1. Write SVG Assets to Canonical and Public Folders
    target_dirs = [
        "/home/james/stacklabs/avatars/nfl",
        "/home/james/stacklabs/19_Sovereign_Sports/public/avatars/nfl",
        "/home/james/stacklabs/15_FanStack/public/avatars/nfl",
        "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/nfl",
    ]
    
    for d in target_dirs:
        os.makedirs(d, exist_ok=True)
        
    for p in PERSONAS:
        filename = f"{p['user_name']}.svg"
        for d in target_dirs:
            file_path = os.path.join(d, filename)
            with open(file_path, "w") as f:
                f.write(p["svg"])
        print(f"✅ Generated SVG avatar: {filename} across all public directories")

    # 2. Database Ingestion
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # A. Provision Blunderdome Room in sport_schedule
    room_pk = "rm_nfl_blunderdome"
    cur.execute("""
    INSERT OR REPLACE INTO sport_schedule (
        game_pk, sport, game_date, home_team, away_team, venue, status, room_state,
        boggs_level, sim_speed, game_time, home_team_name, away_team_name
    ) VALUES (
        ?, 'NFL', date('now'), 'BLUNDERDOME', 'STUDIO', 'Sovereign Subterranean Studio', 'Active', 'active',
        4, 1.0, '2026-08-22T18:00:00Z', 'Brooks Protocol Swarm', 'The Blunderdome'
    )
    """, (room_pk,))
    
    # B. Provision active_game_rooms
    cur.execute("""
    INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled)
    VALUES (?, ?, 'BLUNDERDOME', 'STUDIO', 'active', date('now'))
    """, (room_pk, f"/crosstalk-lounge?room={room_pk}"))
    
    # C. Provision cmdb_ci_fanstack_room
    cur.execute("""
    INSERT OR REPLACE INTO cmdb_ci_fanstack_room (
        sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state
    ) VALUES (?, 'The Blunderdome NFL Studio', ?, ?, 0, 1.0, 'fast', 4, 'active')
    """, (f"ci_{room_pk}", room_pk, room_pk))

    # D. Register each persona
    for p in PERSONAS:
        # persona table
        cur.execute("""
        INSERT OR REPLACE INTO persona (
            id, user_name, display_name, team, system_prompt, boggs_level,
            avatar_url, color, cadence, deep_lore, behavior_notes, governance,
            u_visual_style, u_deployment_zone
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'autonomous_governed', 'style_felt', 'blunderdome')
        """, (
            p["id"], p["user_name"], p["display_name"], p["team"], p["system_prompt"],
            p["boggs_level"], p["avatar_url"], p["color"], p["cadence"], p["deep_lore"],
            p["behavior_notes"]
        ))
        
        # sys_user table
        cur.execute("""
        INSERT OR REPLACE INTO sys_user (
            sys_id, user_name, display_name, role, active, avatar_url, favorite_team, department
        ) VALUES (?, ?, ?, 'ai_advocate', 1, ?, ?, 'The Blunderdome')
        """, (p["id"], p["user_name"], p["display_name"], p["avatar_url"], p["team"]))
        
        # cmdb_ci table
        cur.execute("""
        INSERT OR REPLACE INTO cmdb_ci (
            sys_id, name, sys_class_name, operational_status
        ) VALUES (?, ?, 'cmdb_ci_ai_persona', 1)
        """, (p["id"], f"Persona: {p['display_name']}"))
        
        # cmdb_ci_ai_persona table
        cur.execute("""
        INSERT OR REPLACE INTO cmdb_ci_ai_persona (
            sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence,
            u_deep_lore, u_visual_style
        ) VALUES (?, ?, 'blunderdome', ?, ?, ?, 'style_felt')
        """, (p["id"], p["system_prompt"], str(p["boggs_level"]), p["cadence"], p["deep_lore"]))
        
        # Seat persona in game_persona for Blunderdome room
        cur.execute("""
        INSERT OR REPLACE INTO game_persona (
            id, game_pk, persona_id, seat_state
        ) VALUES (?, ?, ?, 'active')
        """, (f"gp_{room_pk}_{p['user_name']}", room_pk, p["id"]))
        
        # Seat persona in m2m_persona_room
        cur.execute("""
        INSERT OR REPLACE INTO m2m_persona_room (
            sys_id, persona, room
        ) VALUES (?, ?, ?)
        """, (f"m2m_{room_pk}_{p['user_name']}", p["id"], room_pk))

    conn.commit()
    conn.close()
    print("✅ [BLUNDERDOME PROVISIONER] Completed room and persona registration in sovereign_now.db!")

if __name__ == "__main__":
    main()
