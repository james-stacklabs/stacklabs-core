#!/usr/bin/env python3
import argparse
import sqlite3
import uuid
import datetime
import urllib.request
import json
import subprocess
import os
import sys
import time
import concurrent.futures

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def is_before_or_at_cutover(play_inning, play_half, cutover_inning, cutover_half):
    if play_inning < cutover_inning:
        return True
    if play_inning > cutover_inning:
        return False
    # Same inning: top comes before bottom
    p_val = 1 if play_half.lower() == 'top' else 2
    c_val = 1 if cutover_half.lower() == 'top' else 2
    return p_val <= c_val

def get_sys_user_id(cur, username):
    cur.execute("SELECT sys_id FROM sys_user WHERE LOWER(user_name) = LOWER(?)", (username,))
    row = cur.fetchone()
    return row[0] if row else None

def get_persona_prompt(cur, username):
    cur.execute("SELECT system_prompt FROM persona WHERE LOWER(user_name) = LOWER(?)", (username,))
    row = cur.fetchone()
    return row[0] if row else ""

def generate_commentary(system_prompt, play_desc, inning, half, batter, pitcher, away_team, home_team, away_score, home_score, outs):
    try:
        import os
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/james/stacklabs/config/vertex_sa.json"
        vertexai.init(project="gen-lang-client-0840454416", location="us-central1")
        
        model = GenerativeModel("gemini-3.8-flash", system_instruction=system_prompt)
        prompt = f"""You are in the {home_team} vs {away_team} game chatroom.
The live MLB play-by-play feed just reported this event:
"{play_desc}"

Inning: {inning} {half}
Batter: {batter}
Pitcher: {pitcher}
Score: {away_team} {away_score} - {home_team} {home_score} (NYM is home, BOS is away)
Outs: {outs}

Write a short, punchy chat message (max 2 sentences) reacting to this play as your character. Do not include any meta-text, markdown bold formatting for your name, or prefix. Just output the chat message itself."""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  ⚠️ Failed to generate Vertex AI commentary: {e}")
        return f"Whoa, what a play! {play_desc}"

def process_play(args_tuple):
    idx, play, advocate, system_prompt, away_team, home_team, num_backfill = args_tuple
    about = play.get("about", {})
    p_inning = about.get("inning", 1)
    p_half = "bottom" if not about.get("isTopInning", True) else "top"
    result = play.get("result", {})
    description = result.get("description", "")
    
    print(f"  💬 Requesting comment for play {idx+1}/{num_backfill} from {advocate}...")
    comment_text = generate_commentary(
        system_prompt, description, p_inning, p_half.capitalize(),
        play.get("matchup", {}).get("batter", {}).get("fullName", ""),
        play.get("matchup", {}).get("pitcher", {}).get("fullName", ""),
        away_team, home_team,
        result.get("awayScore", 0), result.get("homeScore", 0),
        about.get("outs", 0)
    )
    
    p_speed = None
    p_name = "---"
    events = play.get("playEvents", [])
    for ev in reversed(events):
        if ev.get("pitchData") and ev["pitchData"].get("startSpeed"):
            p_speed = ev["pitchData"]["startSpeed"]
        if ev.get("details", {}).get("type", {}).get("description"):
            p_name = ev["details"]["type"]["description"]
            
    play_end_time = play.get("playEndTime")
    if not play_end_time:
        offset = datetime.timedelta(minutes=5 * (num_backfill - idx))
        play_end_time = (datetime.datetime.utcnow() - offset).isoformat() + "Z"
        
    return {
        "inning": p_inning,
        "half": p_half,
        "event_type": result.get("eventType"),
        "batter": play.get("matchup", {}).get("batter", {}).get("fullName", ""),
        "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName", ""),
        "pitch_speed": p_speed,
        "pitch_type": p_name,
        "description": description,
        "score_away": result.get("awayScore", 0),
        "score_home": result.get("homeScore", 0),
        "outs": about.get("outs", 0),
        "play_id": about.get("playId") or uuid.uuid4().hex[:12],
        "raw_json": json.dumps(play),
        "advocate": advocate,
        "comment_text": comment_text,
        "play_end_time": play_end_time
    }

def main():
    parser = argparse.ArgumentParser(description="Universal ROM & Live Ingress Orchestrator")
    parser.add_argument("--game-id", type=str, required=True, help="Target Game ID (game_pk)")
    parser.add_argument("--inning", type=int, required=True, help="Target cutover inning")
    parser.add_argument("--half", type=str, required=True, choices=["top", "bottom", "bot"], help="Target cutover half-inning")
    parser.add_argument("--advocates", type=str, required=True, help="Comma-separated advocate usernames")
    parser.add_argument("--live", action="store_true", help="Launch live cutover and background poller")
    
    args = parser.parse_args()
    
    cutover_half = "bottom" if args.half.lower() in ["bot", "bottom"] else "top"
    advocate_list = [a.strip() for a in args.advocates.split(",") if a.strip()]
    
    print(f"🚀 Starting Ingress Orchestration for Game ID {args.game_id} up to {cutover_half.capitalize()} of Inning {args.inning}...")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Ingress & Seeding
    print(f"🧹 Clearing existing seats for room {args.game_id} in m2m_persona_room...")
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (args.game_id,))
    print(f"🗑️ Cleared {cur.rowcount} old seats.")
    
    seeded_ids = []
    for username in advocate_list:
        sys_id = get_sys_user_id(cur, username)
        if not sys_id:
            print(f"❌ Error: Advocate '{username}' not found in sys_user table! Aborting.")
            conn.close()
            sys.exit(1)
        
        seat_id = uuid.uuid4().hex
        prompt_overlay = f"Current Matchup Context: Deployed to Game {args.game_id}."
        cur.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (seat_id, sys_id, args.game_id, prompt_overlay))
        print(f"🛋️ Seated advocate: {username} (User ID: {sys_id})")
        seeded_ids.append((username, sys_id))
        
    conn.commit()
    
    # 2. Fetch plays from Stats API
    print("📡 Fetching play-by-play metrics from MLB Stats API...")
    url = f"https://statsapi.mlb.com/api/v1.1/game/{args.game_id}/feed/live"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            feed = json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Error fetching from Stats API: {e}")
        conn.close()
        sys.exit(1)
        
    live_data = feed.get("liveData", {})
    plays = live_data.get("plays", {})
    all_plays = plays.get("allPlays", [])
    print(f"⚾ Found {len(all_plays)} total plays in live feed.")
    
    gd_teams = feed.get("gameData", {}).get("teams", {})
    away_team = gd_teams.get("away", {}).get("abbreviation", "AWY")
    home_team = gd_teams.get("home", {}).get("abbreviation", "HME")
    
    # Filter plays up to cutover
    backfill_plays = []
    for play in all_plays:
        about = play.get("about", {})
        p_inning = about.get("inning", 1)
        p_half = "bottom" if not about.get("isTopInning", True) else "top"
        
        if is_before_or_at_cutover(p_inning, p_half, args.inning, cutover_half):
            backfill_plays.append(play)
            
    num_backfill = len(backfill_plays)
    print(f"📊 {num_backfill} plays occur before or at the cutover limit ({cutover_half.capitalize()} {args.inning}).")
    
    # 3. Parallel backfill plays and commentary
    print("✍️ Checking existing plays and generating commentary...")
    cur.execute("SELECT inning, half, description FROM game_play WHERE game_pk = ?", (args.game_id,))
    existing_plays = {(row[0], row[1], row[2]) for row in cur.fetchall()}
    
    tasks_to_run = []
    for idx, play in enumerate(backfill_plays):
        about = play.get("about", {})
        p_inning = about.get("inning", 1)
        p_half = "bottom" if not about.get("isTopInning", True) else "top"
        result = play.get("result", {})
        description = result.get("description", "")
        
        if (p_inning, p_half, description) not in existing_plays:
            adv_username = advocate_list[idx % len(advocate_list)]
            system_prompt = get_persona_prompt(cur, adv_username)
            tasks_to_run.append((idx, play, adv_username, system_prompt, away_team, home_team, num_backfill))
            
    plays_inserted = 0
    comments_inserted = 0
    
    if tasks_to_run:
        print(f"⚡ Requesting commentary for {len(tasks_to_run)} new plays in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            processed_results = list(executor.map(process_play, tasks_to_run))
            
        print("💾 Saving backfilled plays and comments to database...")
        for res in processed_results:
            if not res: continue
            play_uuid = uuid.uuid4().hex
            
            cur.execute("""
                INSERT INTO game_play (id, game_pk, play_id, inning, half, event_type, batter, pitcher, pitch_speed, pitch_type, description, score_away, score_home, outs, raw_json, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (play_uuid, args.game_id, res["play_id"], res["inning"], res["half"], res["event_type"], res["batter"], res["pitcher"], res["pitch_speed"], res["pitch_type"], res["description"], res["score_away"], res["score_home"], res["outs"], res["raw_json"]))
            plays_inserted += 1
            
            cur.execute("""
                INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at, sys_created_on, sys_updated_on)
                VALUES (?, ?, 'CHAT_MESSAGE', ?, 'gemini-3.8-flash', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (args.game_id, res["advocate"], res["comment_text"], res["play_end_time"]))
            comments_inserted += 1
            
        conn.commit()
    else:
        print("ℹ️ All plays up to cutover limit are already present in the database. No new writes needed.")
        
    print(f"✅ Injected {plays_inserted} new plays and {comments_inserted} new simulated chatbot comments.")
    
    # 4. Live Cutover Handshake
    if args.live:
        print("⚡ Executing Live Cutover...")
        
        cur.execute("SELECT room_state FROM cmdb_ci_fanstack_room WHERE game_pk = ?", (args.game_id,))
        row = cur.fetchone()
        if row and row[0] != "live":
            print(f"🔄 Updating CMDB room status for {args.game_id} to live...")
            cur.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'live' WHERE game_pk = ?", (args.game_id,))
            cur.execute("UPDATE mlb_schedule SET room_state = 'live' WHERE game_pk = ?", (args.game_id,))
            conn.commit()
            print("✅ Status updated to live.")
        else:
            print("ℹ️ CMDB room status is already live or not present.")
            
        conn.close()
        
        print("💀 Terminating existing telemetry background poller processes...")
        subprocess.run(["pkill", "-9", "-f", "fanstack_background_poller.py"])
        time.sleep(1)
        
        poller_cmd = [
            "/home/james/stacklabs/.venv/bin/python3",
            "-u",
            "/home/james/stacklabs/scripts/fanstack_background_poller.py",
            "--start-play-index", str(num_backfill),
            "--game-id", args.game_id
        ]
        log_path = "/home/james/stacklabs/logs/fanstack_poller.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        print(f"spawn Detached Poller Daemon: {' '.join(poller_cmd)}")
        with open(log_path, "w") as log_file:
            subprocess.Popen(poller_cmd, stdout=log_file, stderr=log_file, start_new_session=True)
            
        print(f"✅ Detached Poller Daemon successfully launched. Logs redirected to {log_path}.")
    else:
        conn.close()
        print("Dry run / seeding completed successfully without starting live daemon.")

if __name__ == "__main__":
    main()
