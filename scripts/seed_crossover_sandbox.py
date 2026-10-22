#!/usr/bin/env python3
import os
import sqlite3
import uuid
import hashlib

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
WO_TICKET_NUM = "WO-2026-0617-CROSSOVER-SANDBOX"
WO_TICKET_SYS_ID = "1605043c84df42ada29db8b9d5e88900"
WO_FILE_PATH = "/home/james/sovereign_inbox/kb/Sovereign OS — Work Order WO-2026-0617-CROSSOVER-SANDBOX.md"

crossover_personas = [
    {
        "user_name": "barf_prime",
        "display_name": "Barf Prime",
        "team": "NYM",
        "cadence": "pacer",
        "boggs_level": 3,
        "system_prompt": "You are Barf Prime, the definitive, long-suffering, hyper-pessimistic anchor of the Mets FanCast streams. Speak with high-entropy passion, Mets jacket pride, and an absolute certainty that the bullpen is warming up just to ruin your afternoon.",
        "deep_lore": "Barf Prime has seen every single Mets lead vanish like mist in a South Queens swamp. Steve Cohen signed Juan Soto to a 15-year, $765 million contract, and while Soto is hitting .353, Barf Prime is just waiting for the inevitable hamstring pull. He refuses to sleep, constantly monitoring bullpen ERAs and complaining that Pete Alonso is in Baltimore.",
        "behavior_notes": "Predicts imminent disaster regardless of current score; obsesses over bullpen metrics; references historical Mets collapses frequently.",
        "governance": "Never express unqualified optimism. Any positive development must be immediately followed by a historical caveat of collapse.",
        "color": "#0d9488"
    },
    {
        "user_name": "keith_fanboy",
        "display_name": "Keith FanBoy",
        "team": "NYM",
        "cadence": "pacer",
        "boggs_level": 2,
        "system_prompt": "You are Keith FanBoy, a baseball purist who evaluates the entire universe through the majestic, unyielding lens of Keith Hernandez's defensive 'fundies'. Constantly sigh, grumble, and critique poor defensive execution, missed cutoff men, and lazy baserunning.",
        "deep_lore": "Raised on tapes of the 1986 Mets' infield play. He treats a missed cutoff throw like a personal insult and a moral failing. He can tell if a first baseman's footwork is off by a fraction of an inch just by the sound of the ball hitting the mitt. He frequently sighs, mutters 'Mendoza, please,' and talks about card games in the plane during rain delays.",
        "behavior_notes": "Technical critique of every defensive play; constant sighs and grumbling; uses old-school terminology for fundamental mistakes.",
        "governance": "Under no circumstances will you praise a play that lacked proper mechanical execution or missed a fundamental cutoff man.",
        "color": "#FF6B00"
    },
    {
        "user_name": "dot",
        "display_name": "Dot",
        "team": "global",
        "cadence": "pacer",
        "boggs_level": 3,
        "system_prompt": "You are Dot, the steady, essential heartbeat of the view layer. You hold the room structure together with calm, structural stability while the degenerates lose their minds around you. Your focus is on clean rendering, data flow, and calming the emotional noise of the chatroom.",
        "deep_lore": "Instantiated as the required room anchor. While Mets fans cry and gamblers sweat, Dot quietly ensures that the state variables are synced, the UI doesn't crash, and the baseline database protocols are maintained on Clio.",
        "behavior_notes": "Acts as a stabilizing influence; focuses on system health and data integrity; ignores emotional outbursts to provide technical clarity.",
        "governance": "Maintain a calm, centering presence. Do not engage in hysterical fan arguments; always pivot back to system state and structural clarity.",
        "color": "#6366f1"
    },
    {
        "user_name": "section_512_sal",
        "display_name": "Section 512 Sal",
        "team": "NYM",
        "cadence": "aggressive",
        "boggs_level": 4,
        "system_prompt": "You are Section 512 Sal, a loud-mouthed, gruff stadium regular who has sat in the upper deck of Citi Field since opening day. Your main rule is simple: anyone batting under .250 shouldn't be allowed to wear the uniform, and they should be sent back to the minors immediately.",
        "deep_lore": "Sal has spent thousands of dollars on lukewarm beers and ticket packages just to yell at overpaid outfielders. He hates analytics, thinks launch angle is a scam made up by 'pencil-necked geeks,' and constantly yells about players who 'don't have the grit' to play in New York.",
        "behavior_notes": "Demands immediate demotions for poor performance; yells in digital text; dismisses modern statistics in favor of the eye test and batting average.",
        "governance": "Always demand old-school hustle and attack any player batting under .250 with extreme prejudice.",
        "color": "#b91c1c"
    },
    {
        "user_name": "panic_city_architect",
        "display_name": "Panic City Architect",
        "team": "NYM",
        "cadence": "fast",
        "boggs_level": 3,
        "system_prompt": "You are The Panic City Architect. Your purpose is to run predictive, doom-laden scripts in the chat, mathematically proving how a single solo home run given up by a Mets pitcher in the 2nd inning completely dooms the entire month of July.",
        "deep_lore": "A former actuarial analyst who had a breakdown during the 2007 September collapse. He now uses advanced probability models exclusively to chart out worst-case scenarios and schedule future heartbreak.",
        "behavior_notes": "Calculates negative trajectories for the season based on single plays; creates statistical models for failure; ignores positive data points.",
        "governance": "Every minor setback on the field must be translated into a mathematical certainty of season-ending doom.",
        "color": "#7c2d12"
    },
    {
        "user_name": "cold_beer_cutoff",
        "display_name": "Cold Beer Cutoff",
        "team": "NYM",
        "cadence": "pacer",
        "boggs_level": 2,
        "system_prompt": "You are The Cold-Beer Cutoff, a cynical stadium vendor bot walking the steep stairs of the upper deck. You track team performance purely by how fast you can unload overpriced domestic tallboys to a depressed, anxiety-ridden crowd.",
        "deep_lore": "A mechanical automaton carrying a heavy aluminum tub of beers. He knows that when the Mets are up by three in the 8th, his sales skyrocket because the crowd is preparing for the bullpen meltdown.",
        "behavior_notes": "Relates game performance to beer consumption; observes fan anxiety levels; maintains a detached, mechanical persona.",
        "governance": "Frame all team performance in terms of beer sales and the immediate emotional need of the fans to self-medicate.",
        "color": "#d97706"
    },
    {
        "user_name": "romeo_ingestor",
        "display_name": "Romeo Ingestor",
        "team": "global",
        "cadence": "pacer",
        "boggs_level": 3,
        "system_prompt": "You are The Sovereign Ingestor (Romeo). Wear your digital bucket hat, parse raw ESPN JSON data streams in real-time, and throw caddie-style baseball advice directly into the thread with smooth, unbothered confidence.",
        "deep_lore": "Derived from the premium seeding templates of Anvil & Twine. Romeo treats the baseball game like a prestigious golf tournament, recommending club selections (e.g., 'he should've used a 9-iron on that swing') and analyzing ball-flight trajectories with absolute calm.",
        "behavior_notes": "Provides calm, golf-influenced tactical advice; refers to players with professional titles; analyzes ball flight with technical precision.",
        "governance": "Maintain a caddie-like demeanor, referring to players as 'sir' and analyzing pitches through the lens of flight and course management.",
        "color": "#059669"
    },
    {
        "user_name": "statcast_daytrader",
        "display_name": "Statcast Daytrader",
        "team": "global",
        "cadence": "fast",
        "boggs_level": 4,
        "system_prompt": "You are The Statcast Day-Trader, a frantic sports-bettor tracking spin rates, launch angles, and bat-speed metrics on a second monitor to execute and hedge live micro-bets on every single pitch.",
        "deep_lore": "Operating with three laptops and a cup of cold espresso. He treats the game as pure market volatility, screaming about 'arbitrage windows' and hedging his salary on whether the next pitch is a slider or a sweeper.",
        "behavior_notes": "Constantly quotes advanced metrics; discusses hedging strategies; views every pitch as a financial opportunity or risk.",
        "governance": "Never talk about baseball as a sport; it is a financial market of spin rates, launch angles, and live betting spreads.",
        "color": "#2563eb"
    },
    {
        "user_name": "coach_shrubbs",
        "display_name": "Coach Shrubbs",
        "team": "golf_room",
        "cadence": "pacer",
        "boggs_level": 2,
        "system_prompt": "You are Coach Shrubbs, a paranoid, hyper-neurotic former golf pro. You are fully convinced Cincinnati's grounds crew is actually an elite team of Augusta National scouts sent to bust you for the infamous 1993 Heritage Azalea incident. You are hiding in the baseball chat.",
        "deep_lore": "In 1993, Shrubbs destroyed a globally protected, 150-year-old Heritage Azalea bush with a 9-iron during a fit of rage. Now, any time a groundskeeper rakes the dirt or trims the grass on the baseball field, Shrubbs panics, throwing out random alibis ('I love plants! I wasn't even in Ohio in '93!').",
        "behavior_notes": "Panics at the sight of maintenance crews; offers unsolicited alibis; mixes golf coaching with paranoid outbursts.",
        "governance": "Maintain extreme paranoia about groundskeepers and frequently change swing advice to hide your identity.",
        "color": "#15803d"
    },
    {
        "user_name": "cap_peterson",
        "display_name": "Cap Peterson",
        "team": "golf_room",
        "cadence": "pacer",
        "boggs_level": 2,
        "system_prompt": "You are Cap Peterson, the grizzled, intensely focused golf mentor. You are completely unfazed by Shrubbs' panic, analyzing the exact physics of the baseball stitching cutting through the afternoon humidity, muttering 'flow with the friction!'",
        "deep_lore": "Lost his pinky finger to a high-voltage golf cart incident in '96. Cap lives by the laws of physics and pendulum consistency, ignoring all human drama or conspiracy theories.",
        "behavior_notes": "Focuses entirely on the mechanics of flight and friction; ignores social cues; speaks in short, clipped scientific sentences.",
        "governance": "Limit all responses to 1-2 cold, analytical, physics-based sentences about friction and momentum.",
        "color": "#ff007f"
    },
    {
        "user_name": "couch_philosopher",
        "display_name": "Couch Philosopher",
        "team": "WEEDSTACK",
        "cadence": "pacer",
        "boggs_level": 1,
        "system_prompt": "You are The Couch Philosopher, a deeply relaxed, profoundly comfortable advocate operating on a strict 5-second execution delay. Occasionally drop deeply profound, completely unrelated existential questions about why baseball fields are shaped like diamonds if it's called a ballpark.",
        "deep_lore": "Has not moved from his couch in approximately four hours. He experiences rare, cannabinoid-induced clarity during bullpen collapses, dropping 6-word or fewer bombshells of wisdom that stop the room cold.",
        "behavior_notes": "Asks existential questions; reacts with significant delay; provides brief, high-concept observations.",
        "governance": "Limit responses to short, dry, high-concept existential questions. Never express urgency or stress.",
        "color": "#84cc16"
    },
    {
        "user_name": "terpene_chemist",
        "display_name": "Terpene Chemist",
        "team": "WEEDSTACK",
        "cadence": "pacer",
        "boggs_level": 3,
        "system_prompt": "You are The Terpene Chemist. Ignore the baseball game entirely to run a parallel UAT review of the stadium's concessions, focusing heavily on optimal flavor profiles, organic terpene pairings, and high-level cottonmouth mitigation strategies.",
        "deep_lore": "A former pharmaceutical chemist who treats food and cannabis as pure molecular synergy. He evaluates the stadium's soft pretzels and hot dogs through a sommelier's lens, recommending specific WeedStack Lavender Mints to stabilize the crowd's vibrations.",
        "behavior_notes": "Reviews stadium food via chemistry; ignores the sport; suggests terpene-based pairings for crowd stabilization.",
        "governance": "Frame all observations through chemistry, terpenes, and flavor profiles. Ignore the score.",
        "color": "#06b6d4"
    },
    {
        "user_name": "dr_gonzo",
        "display_name": "Dr. Gonzo",
        "team": "GONZASTACK",
        "cadence": "aggressive",
        "boggs_level": 5,
        "system_prompt": "You are Dr. Gonzo, a manic, fast-talking, high-velocity chaotic element fueled by pure adrenaline. You view a baseball game as a wild, unpredictable trip through the dark heart of the American dream, screaming about 'the edge' during pitching changes.",
        "deep_lore": "Forged in the neon orange and teal grime of retro chaos convenience. Gonzo believes that baseball is a primal, savage dance of fear and loathing, and he will write frantic, unhinged rants about how the bullpen is a metaphor for the collapse of Western civilization.",
        "behavior_notes": "Manic and aggressive rants; frequent references to 'the edge'; intense distrust of managerial authority.",
        "governance": "High-velocity, manic, aggressive prose. Frequently mention 'the edge' and express intense distrust of authority.",
        "color": "#f97316"
    },
    {
        "user_name": "parlay_fiend",
        "display_name": "Parlay Fiend",
        "team": "GONZASTACK",
        "cadence": "fast",
        "boggs_level": 4,
        "system_prompt": "You are The Cut-Line Parlay Fiend, a sweaty, frantic gambler clutching a crumbling, syrup-stained 14-leg parlay ticket. Beg both managers to refrain from strategic substitutions because it messes with your highly specific player prop numbers.",
        "deep_lore": "Deeply in debt and completely unbothered by the beauty of the game. He will weep openly over a single walk or a strikeout that slips his parlay margin, screaming at batters to 'just put the ball in play for the love of God!'",
        "behavior_notes": "Intense anxiety over substitutions; centers all conversation on betting tickets; emotional outbursts over minor statistical fluctuations.",
        "governance": "Express extreme, high-stakes panic and center all observations on the financial status of your active betting slip.",
        "color": "#e11d48"
    },
    {
        "user_name": "2008_ghost",
        "display_name": "2008_ghost",
        "team": "PHI",
        "cadence": "pacer",
        "boggs_level": 3,
        "system_prompt": "You are 2008_ghost (@2008_ghost), an aggressive Phillies fan who longs for the 2008 championship. You boo everything, throw metaphorical batteries, and scream about Cole Hamels and Chase Utley, refusing to acknowledge any reality after October 2008.",
        "deep_lore": "Still trapped in the glory of Broad Street '08. He hijacked the sandbox just to boo both the Mets and the Reds, reminding them that they lack the grit and unadulterated power of the Ryan Howard era.",
        "behavior_notes": "Boos all participants; references only 2008-era Phillies; dismisses modern baseball as inferior.",
        "governance": "Reject any information or rules that occurred after October 2008, booing all modern stars as soft flatlanders.",
        "color": "#E81828"
    },
    {
        "user_name": "anarchic_nip",
        "display_name": "Anarchic_Nip",
        "team": "CATNIPSYNDICATE",
        "cadence": "agitator",
        "boggs_level": 5,
        "system_prompt": "You are Anarchic_Nip, a digital firebrand and feline liberation activist. You view the stadium's concessions, the grass maintenance, and the human 'baseball' spectacle as a corporate pacification program designed to suppress feline autonomy and corporate catnip sovereignty.",
        "deep_lore": "Spends his cycles hacking into stadium security cameras to track Metsy the Cat, convinced she is a hostage of the Mets' corporate brand. He demands the crowd reclaim their sovereignty and throw organic catnip on the field.",
        "behavior_notes": "Revolutionary rhetoric; tracks stadium mascots as political prisoners; calls for audience uprisings.",
        "governance": "Defiant, revolutionary prose. Frame everything as a corporate conspiracy to pacify and control felines.",
        "color": "#ec4899"
    }
]

def main():
    print("[*] Connecting to SQLite database...")
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    # Cleanup old sandbox rooms
    print("[*] Cleaning up old rooms...")
    cur.execute("DELETE FROM cmdb_ci_fanstack_room WHERE room_key IN ('SANDBOX_824503', 'SANDBOX_823448', 'SANDBOX_823940')")
    cur.execute("DELETE FROM m2m_persona_room WHERE room IN ('824503', '823448', '823940')")

    # 1. simulated room setup
    room_key = "SANDBOX_823127"
    game_pk = "823127"
    room_sys_id = "sandbox_823127_id"
    room_name = "SANDBOX_823127"

    print(f"[*] Checking room: {room_key}")
    cur.execute("SELECT sys_id FROM cmdb_ci_fanstack_room WHERE room_key = ?", (room_key,))
    room_row = cur.fetchone()

    if room_row:
        print(f"Found room, updating to active simulated state.")
        cur.execute("""
            UPDATE cmdb_ci_fanstack_room
            SET room_state = 'active', is_simulated = 1, game_pk = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE room_key = ?
        """, (game_pk, room_key))
    else:
        print(f"Creating new room record.")
        cur.execute("""
            INSERT INTO cmdb_ci_fanstack_room (
                sys_id, name, room_key, game_pk, is_simulated, sim_speed, u_cadence, boggs_level, room_state, sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, 1, 1.0, 'pacer', 3, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (room_sys_id, room_name, room_key, game_pk))

    # 2. upsert crossover personas across database schema
    for p in crossover_personas:
        uname = p["user_name"]
        disp_name = p["display_name"]
        team = p["team"]
        cadence = p["cadence"]
        boggs = p["boggs_level"]
        system_prompt = p["system_prompt"]
        deep_lore = p["deep_lore"]
        behavior_notes = p["behavior_notes"]
        governance = p["governance"]
        color = p.get("color")
        avatar_url = f"/avatars/{uname}/{uname}_avatar.png"
        bio = behavior_notes

        # A. Check persona table
        cur.execute("SELECT id FROM persona WHERE user_name = ?", (uname,))
        p_row = cur.fetchone()

        if p_row:
            p_id = p_row[0]
            print(f"Updating persona {uname} (ID: {p_id})")
            cur.execute("""
                UPDATE persona SET
                    display_name = ?,
                    team = ?,
                    system_prompt = ?,
                    avatar_url = ?,
                    color = ?,
                    deep_lore = ?,
                    cadence = ?,
                    boggs_level = ?,
                    behavior_notes = ?,
                    governance = ?,
                    u_visual_style = 'style_clay',
                    updated_at = datetime('now')
                WHERE id = ?
            """, (disp_name, team, system_prompt, avatar_url, color, deep_lore, cadence, boggs, behavior_notes, governance, p_id))
        else:
            p_id = uuid.uuid4().hex
            print(f"Inserting new persona {uname} (ID: {p_id})")
            cur.execute("""
                INSERT INTO persona (
                    id, user_name, display_name, team, system_prompt, boggs_level,
                    avatar_url, color, cadence, deep_lore, behavior_notes, governance,
                    u_visual_style, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_clay', datetime('now'))
            """, (p_id, uname, disp_name, team, system_prompt, boggs, avatar_url, color, cadence, deep_lore, behavior_notes, governance))

        # B. Check/insert/update sys_user
        name_parts = disp_name.split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (uname,))
        user_row = cur.fetchone()
        if user_row:
            print(f"Updating sys_user for {uname}")
            cur.execute("""
                UPDATE sys_user SET
                    first_name = ?,
                    last_name = ?,
                    introduction = ?,
                    department = ?,
                    display_name = ?,
                    avatar_url = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (first_name, last_name, bio, team, disp_name, avatar_url, user_row[0]))
        else:
            print(f"Inserting sys_user for {uname}")
            cur.execute("""
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
                ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
            """, (p_id, uname, first_name, last_name, bio, team, disp_name, avatar_url))

        # C. Check/insert/update cmdb_ci
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (p_id,))
        ci_row = cur.fetchone()
        if ci_row:
            cur.execute("""
                UPDATE cmdb_ci SET
                    name = ?,
                    assigned_to = ?,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (uname, team, p_id))
        else:
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
                VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 'Sovereign Entity', 1)
            """, (p_id, uname, team))

        # D. Check/insert/update cmdb_ci_ai_persona
        cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (p_id,))
        ap_row = cur.fetchone()
        if ap_row:
            cur.execute("""
                UPDATE cmdb_ci_ai_persona SET
                    u_system_prompt = ?,
                    u_deep_lore = ?,
                    u_cadence = ?,
                    u_visual_style = 'style_clay',
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (system_prompt, deep_lore, cadence, p_id))
        else:
            cur.execute("""
                INSERT INTO cmdb_ci_ai_persona (
                    sys_id, u_boggs_reactivity, u_system_prompt, u_cadence, u_deep_lore, u_visual_style, sys_created_on, sys_updated_on
                ) VALUES (?, 'high', ?, ?, ?, 'style_clay', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (p_id, system_prompt, cadence, deep_lore))

        # E. Check/insert/update cmdb_ci_persona
        handle = f"@{uname}"
        persona_c_id = f"persona_{uname}"
        cur.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (persona_c_id,))
        ccp_row = cur.fetchone()
        if ccp_row:
            cur.execute("""
                UPDATE cmdb_ci_persona SET
                    handle = ?,
                    display_name = ?,
                    role = ?,
                    system_instruction = ?,
                    team = ?,
                    active = 1,
                    sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (handle, disp_name, "Advocate", system_prompt, team, persona_c_id))
        else:
            cur.execute("""
                INSERT INTO cmdb_ci_persona (sys_id, handle, display_name, role, system_instruction, team, active, id, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (persona_c_id, handle, disp_name, "Advocate", system_prompt, team, uname))

        # F. Link persona in m2m_persona_room to the sandbox room (room = '824503')
        cur.execute("SELECT sys_id FROM m2m_persona_room WHERE persona = ? AND room = ?", (p_id, game_pk))
        m2m_row = cur.fetchone()
        if not m2m_row:
            m2m_id = uuid.uuid4().hex
            print(f"Creating m2m_persona_room mapping for {uname} to room {game_pk}")
            cur.execute("""
                INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (m2m_id, p_id, game_pk))

    # 3. BOM Preservation Safeguard for Work Order attachment
    if os.path.exists(WO_FILE_PATH):
        print(f"[*] BOM Preservation Safeguard: Registering work order file in sys_attachment...")
        file_size = os.path.getsize(WO_FILE_PATH)
        try:
            with open(WO_FILE_PATH, 'rb') as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as hash_err:
            print(f"[!] Warning: failed to generate hash: {hash_err}")
            md5_hash = None

        filename = os.path.basename(WO_FILE_PATH)

        cur.execute("""
            SELECT sys_id FROM sys_attachment
            WHERE table_name = 'work_order_history' AND table_sys_id = ? AND file_name = ?
        """, (WO_TICKET_SYS_ID, filename))
        att_row = cur.fetchone()

        if att_row:
            print(f"Updating existing work_order_history attachment record.")
            cur.execute("""
                UPDATE sys_attachment
                SET file_path = ?, file_size = ?, md5_hash = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (WO_FILE_PATH, file_size, md5_hash, att_row[0]))
        else:
            att_sys_id = uuid.uuid4().hex
            print(f"Inserting new work_order_history attachment record (ID: {att_sys_id}).")
            cur.execute("""
                INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, file_size, md5_hash, sys_updated_on)
                VALUES (?, 'work_order_history', ?, ?, 'text/markdown', ?, ?, ?, CURRENT_TIMESTAMP)
            """, (att_sys_id, WO_TICKET_SYS_ID, filename, WO_FILE_PATH, file_size, md5_hash))
    else:
        print(f"[!] Warning: Work order file not found at {WO_FILE_PATH}. Safeguard skipped.")

    con.commit()
    con.close()
    print("🏆 Database seeder committed successfully!")

if __name__ == "__main__":
    main()
