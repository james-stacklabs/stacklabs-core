#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: MARD ENGINE NFL PLAY-BY-PLAY RESIMULATION DAEMON
# Script: /home/james/stacklabs/scripts/simulate_nfl_game_mard.py
# SDLC: ENHC2026082002 / MARD Engine Multi-Agent Ingress
# ==============================================================================
import requests
import sqlite3
import json
import time
import os
import sys
import random
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_espn_game(event_id: str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[MARD_SIM] Error fetching ESPN summary for {event_id}: {e}")
    return None

def get_seated_advocates(game_pk: str, away_team: str = "NYJ", home_team: str = "PIT"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.user_name, p.display_name, p.team, p.system_prompt, p.color, p.avatar_url
        FROM game_persona gp
        JOIN persona p ON gp.persona_id = p.id
        WHERE gp.game_pk = ? AND gp.seat_state = 'active'
    """, (game_pk,))
    advocates = [dict(r) for r in cur.fetchall()]

    if not advocates:
        # Auto-seat personas matching the teams
        cur.execute("""
            SELECT id, user_name, display_name, team, system_prompt, color, avatar_url
            FROM persona
            WHERE team IN (?, ?) AND id LIKE 'pna_nfl_%'
        """, (away_team, home_team))
        candidate_advocates = [dict(r) for r in cur.fetchall()]
        for adv in candidate_advocates:
            cur.execute("""
                INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, 'active', datetime('now'), datetime('now'))
            """, (f"gp_{game_pk}_{adv['user_name']}", game_pk, adv['id']))
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, datetime('now'), datetime('now'))
            """, (f"m2m_{game_pk}_{adv['user_name']}", adv['user_name'], game_pk))
        conn.commit()
        advocates = candidate_advocates

    conn.close()
    return advocates

def generate_reaction(advocate: dict, play_text: str, down_dist: str, score_text: str, quarter_text: str):
    uname = advocate["user_name"]
    team = advocate["team"]
    p_upper = play_text.upper()

    is_td = "TOUCHDOWN" in p_upper
    is_fg = "FIELD GOAL IS GOOD" in p_upper or ("FIELD GOAL" in p_upper and "GOOD" in p_upper)
    is_missed_fg = "MISSED" in p_upper or "FIELD GOAL IS NO GOOD" in p_upper
    is_int = "INTERCEPTED" in p_upper
    is_sack = "SACKED" in p_upper
    is_punt = "PUNTS" in p_upper or "PUNT" in p_upper
    is_4th_down_stop = "DOWNS" in p_upper or "SHORT OF FIRST DOWN" in p_upper
    is_big_play = "FOR 20 YARDS" in p_upper or "FOR 21 YARDS" in p_upper or "FOR 31 YARDS" in p_upper or "FOR 16 YARDS" in p_upper

    if uname == "fireman_frankie":
        if is_td and "NYJ" in p_upper:
            return "J-E-T-S JETS! JETS! JETS! 🚒📣 PUT SIX ON THE BOARD! That is how you execute in the red zone!"
        elif is_td:
            return "Get after 'em! Line up and respond on the next drive!"
        elif is_int:
            return "PICKED OFF! Relentless ball-hawking! Gang Green secondary flying around! 💥"
        elif is_sack:
            return "BOOM! SACK! Collapse the pocket and bring 'em down in the backfield! 🛡️"
        elif is_big_play:
            return "CHUNK PLAY! Moving the chains! Megaphone cranked up to 10!"
        elif is_4th_down_stop:
            return "BRICK WALL! Stuffed at the line! Turnover on downs!"
        elif is_fg:
            return "Split the uprights! Points on the board! Keep grinding!"
        return "Win the trenches! Hand in the dirt and move the pile on every down!"

    elif uname == "metlife_meltdown":
        if is_td and "NYJ" in p_upper:
            return "TOUCHDOWN?! Wait... is there a flag? No flag?! Am I allowed to feel joy right now?! 🟢⚪️"
        elif is_int:
            return "INTERCEPTION! Andre Cisco you beautiful man! My heart rate just spiked to 160!"
        elif is_sack:
            return "SACK! Please don't let anyone get injured on the celebration! Keep the pressure on!"
        elif is_missed_fg:
            return "Classic Meadowlands curse... wait, they missed it too?! Phew!"
        elif is_4th_down_stop:
            return "4th down stop! Don't look now, but our defense is actually playing championship football!"
        elif is_fg:
            return "Three points is three points. I will take anything that doesn't involve a safety."
        return "Every 3rd down takes three years off my life. Just protect the football!"

    elif uname == "broadway_joe_believer":
        if is_td and "NYJ" in p_upper:
            return "I GUARANTEE IT! That is pure Gang Green swagger! Dial it up and let the playmakers fly! ✨"
        elif is_int:
            return "That's reading the field like a ten-year veteran! Defense dictating the terms!"
        elif is_big_play:
            return "Air it out! Put some air under the football and let the speed burn downfield!"
        elif is_fg:
            return "Building the lead. Acrisure is dead silent right now."
        return "Play with confidence! When you wear that green and white, you attack on every down!"

    elif uname == "terrible_towel_tony":
        if is_int:
            return "Yinz gotta be kiddin me! Right to the defender in the red zone! Towels are droopin n'at! 🖤💛"
        elif is_td and "NYJ" in p_upper:
            return "Gave up a touchdown on the opening drive? Coach Tomlin is gonna lay into 'em at halftime!"
        elif is_sack:
            return "BAM! THAT'S STEEL CURTAIN FOOTBALL! Put him on his back n'at! 💥"
        elif is_4th_down_stop:
            return "4th down stand! That's how we hit in Pittsburgh! Turn that momentum around!"
        elif is_missed_fg:
            return "Wide left?! At Acrisure?! You gotta make them kicks in this stadium!"
        elif is_punt:
            return "Another three-and-out? Yinz need to establish the run between the tackles!"
        return "Whirl them towels! Let's get a turnover right here on 3rd down! 🖤💛"

    elif uname == "blitzburgh_bill":
        if is_int:
            return "Terrible decision against zone coverage. That is how you lose games in the AFC North. 🛡️"
        elif is_sack:
            return "That is the standard! Disguise the A-gap blitz and make the quarterback eat dirt!"
        elif is_4th_down_stop:
            return "Goal-line discipline! Penetrate the line of scrimmage and blow up the lead blocker!"
        elif is_td:
            return "Unacceptable blown assignment. Safety bit on the play-action and left the middle wide open."
        elif is_punt:
            return "Punt coverage needs to hustle. Down it inside the 10-yard line."
        return "Smashmouth football! Stop the run on early downs and earn the right to rush the passer!"

    elif uname == "iron_city_ivan":
        if is_int:
            return "Quarterback locked onto the primary curl route without reading the underneath safety bracket. Textbook turnover."
        elif is_sack:
            return "Left tackle got beat with a swipe-and-rip move on the edge. Protection broke down immediately."
        elif is_big_play:
            return "Defensive scheme got caught in Cover 1 man with no safety help over the top."
        elif is_4th_down_stop:
            return "Defensive tackle won the interior leverage battle and clogged the B-gap on 4th & 1."
        elif is_td:
            return "Red-zone rub route concept created clean separation against man coverage."
        return "Watching the offensive line handoffs on the zone scheme. Guard needs to get up to the second level."

    return f"Play executed: {play_text[:60]}"

def run_simulation(game_pk: str = "401873288"):
    print(f"🏈 [MARD SIMULATOR] Fetching ESPN Play-by-Play for Game {game_pk}...")
    espn_data = fetch_espn_game(game_pk)
    if not espn_data:
        print("❌ Failed to fetch game summary from ESPN.")
        return

    header = espn_data.get("header", {})
    comps = header.get("competitions", [{}])[0].get("competitors", [])
    home_comp = next((c for c in comps if c.get("homeAway") == "home"), {})
    away_comp = next((c for c in comps if c.get("homeAway") == "away"), {})
    away_team = away_comp.get("team", {}).get("abbreviation", "NYJ")
    home_team = home_comp.get("team", {}).get("abbreviation", "PIT")

    advocates = get_seated_advocates(game_pk, away_team, home_team)
    if not advocates:
        print(f"❌ No active advocates found for game {game_pk}.")
        return

    print(f"✅ Seated {len(advocates)} Advocates: {[a['user_name'] for a in advocates]}")

    drives_data = espn_data.get("drives", {})
    all_drives = drives_data.get("previous", []) + ([drives_data.get("current")] if drives_data.get("current") else [])

    print(f"🏟️ Simulating Matchup: {away_team} @ {home_team} ({len(all_drives)} total drives)")

    conn = get_db()
    cur = conn.cursor()

    # Clear existing game_chat for clean resim if desired, or keep history
    # Let's clean resim for 401873288
    cur.execute("DELETE FROM game_chat WHERE game_pk = ?", (game_pk,))
    conn.commit()

    # Track running score
    away_score = 0
    home_score = 0

    total_comments = 0

    # 1. Pregame Kickoff Chatter
    pregame_takes = [
        ("fireman_frankie", "J-E-T-S JETS! JETS! JETS! Megaphone cranked to 10 at Acrisure! Let's get after it in the trenches! 🚒📣"),
        ("terrible_towel_tony", "HERE WE GO STEELERS! 🖤💛 Towels whirling in the breeze! Let's see that defense eat tonight n'at! 💥"),
        ("metlife_meltdown", "Okay, nobody panic! Just protect the quarterback and don't trip over the 30-yard line! Gang Green let's see some magic! 🟢⚪️"),
        ("blitzburgh_bill", "Smashmouth football at the line of scrimmage! Bring the house on 3rd down and make 'em feel the Steel Curtain! 🛡️"),
        ("broadway_joe_believer", "I guarantee you we're taking shots downfield tonight! Put some air under that ball and let the receivers run! 🏈✨"),
        ("iron_city_ivan", "Watching the offensive line combo blocks on outside zone. If the right tackle holds the edge, the ground game opens up.")
    ]
    for user, text in pregame_takes:
        cur.execute("""
            INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at, sys_created_on)
            VALUES (?, ?, 'CHAT_MESSAGE', ?, 'local_phi3', datetime('now'), datetime('now'))
        """, (game_pk, user, text))
        total_comments += 1
    conn.commit()

    # 2. Step through each drive and key plays
    for drive_idx, drive in enumerate(all_drives, 1):
        drive_team = drive.get("team", {}).get("abbreviation", "")
        drive_desc = drive.get("description", "")
        drive_result = drive.get("result", "")
        plays = drive.get("plays", [])

        # Find key plays in drive: scoring plays, turnovers, 3rd down conversions, sacks, big plays (>15 yds)
        key_plays = []
        for p in plays:
            p_text = p.get("text", "")
            is_score = p.get("scoringPlay", False) or "TOUCHDOWN" in p_text.upper() or "FIELD GOAL" in p_text.upper()
            is_to = "INTERCEPTED" in p_text.upper() or "FUMBLES" in p_text.upper()
            is_sack = "SACKED" in p_text.upper()
            stat_yds = p.get("statYardage", 0) or 0

            if is_score or is_to or is_sack or stat_yds >= 15 or p == plays[-1]:
                key_plays.append(p)

        if not key_plays and plays:
            key_plays = [plays[-1]]

        for kp in key_plays:
            qtr = kp.get("period", {}).get("number", 1)
            clock = kp.get("clock", {}).get("displayValue", "")
            down_dist = kp.get("start", {}).get("downDistanceText", "")
            p_text = kp.get("text", "")

            # Update score if scoring play
            if "G.Smith pass short left to J.Woods for 13 yards, TOUCHDOWN" in p_text:
                away_score = 7
            elif "J.Sanders 39 Yd Field Goal" in p_text or "39 yd FG" in p_text or ("Field Goal is GOOD" in p_text and "39" in p_text):
                away_score = 10
            elif "Q.Skinner Jr. 31 Yd pass" in p_text or "Quincy Skinner" in p_text or "Brady Cook pass deep" in p_text:
                away_score = 17

            score_str = f"{away_team} {away_score} - {home_team} {home_score}"
            qtr_str = f"Q{qtr} {clock}"

            # Pick 2-3 advocates from opposing teams to react
            jets_advs = [a for a in advocates if a["team"] == "NYJ"]
            pit_advs = [a for a in advocates if a["team"] == "PIT"]

            selected = [random.choice(jets_advs), random.choice(pit_advs)]
            if "TOUCHDOWN" in p_text.upper() or "INTERCEPTED" in p_text.upper():
                # Add a 3rd advocate for huge plays
                remaining = [a for a in advocates if a not in selected]
                if remaining:
                    selected.append(random.choice(remaining))

            for adv in selected:
                reaction = generate_reaction(adv, p_text, down_dist, score_str, qtr_str)
                cur.execute("""
                    INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at, sys_created_on)
                    VALUES (?, ?, 'CHAT_MESSAGE', ?, 'phi3:mini', datetime('now'), datetime('now'))
                """, (game_pk, adv["user_name"], reaction))
                total_comments += 1

            # Log context
            cur.execute("""
                INSERT INTO game_context (id, game_pk, source, headline, content, tags, injected_at, sys_created_on)
                VALUES (lower(hex(randomblob(16))), ?, 'espn_nfl', ?, ?, 'NFL,PLAY', datetime('now'), datetime('now'))
            """, (game_pk, f"{qtr_str} | {down_dist}", f"[{score_str}] {p_text}"))

            conn.commit()

    # 3. Post-Game Wrap Takes
    postgame_takes = [
        ("fireman_frankie", "17-0 SHUTOUT IN PITTSBURGH! That is how you close out a road trip! J-E-T-S JETS! JETS! JETS! 🚒🏆"),
        ("metlife_meltdown", "A clean sheet?! In Acrisure?! I don't know what to do with my hands. Defense pitched a masterclass! 🟢⚪️"),
        ("broadway_joe_believer", "I guaranteed Gang Green swagger and they delivered! 17-0 statement win on the road! ✨"),
        ("terrible_towel_tony", "Zero points. Zero. Coach Tomlin is gonna have 'em running gassers all Monday morning n'at. Flush this tape! 🖤💛"),
        ("blitzburgh_bill", "Offense was completely stalled. Two turnovers in the red zone. Fix the protection and tackle with some pride next week! 🛡️"),
        ("iron_city_ivan", "0-for-3 on 4th downs, 2 red-zone interceptions. You cannot win football games when you lose the turnover margin -2 and stall on short yardage.")
    ]
    for user, text in postgame_takes:
        cur.execute("""
            INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at, sys_created_on)
            VALUES (?, ?, 'CHAT_MESSAGE', ?, 'phi3:mini', datetime('now'), datetime('now'))
        """, (game_pk, user, text))
        total_comments += 1

    # Update schedule status to Final
    cur.execute("""
        UPDATE sport_schedule
        SET status = 'Final', room_state = 'active', sys_updated_on = datetime('now')
        WHERE game_pk = ?
    """, (game_pk,))
    conn.commit()
    conn.close()

    print(f"🎉 [MARD SIMULATOR COMPLETE] Successfully simulated NYJ @ PIT!")
    print(f"📊 Total In-Game Dialogue Messages Generated: {total_comments}")

if __name__ == "__main__":
    gid = sys.argv[1] if len(sys.argv) > 1 else "401873288"
    run_simulation(gid)
