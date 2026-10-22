#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: NFL LIVE TELEMETRY & DISCOURSE STREAMER (REAL-TIME MARD INGRESS)
# File: /home/james/stacklabs/scripts/nfl_live_streamer.py
# ==============================================================================
import asyncio
import json
import sqlite3
import time
import uuid
import os
import requests
import websockets
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
WS_URL = "ws://127.0.0.1:8008"
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

ACTIVE_NFL_GAMES = ["401872980", "401872930", "401873284", "401873279"]

# Track previous play hashes to detect new plays
last_play_hashes = {}
last_state_hashes = {}

def update_game_recap_json(game_pk: str, state: dict):
    paths = [
        "/home/james/stacklabs/apps/faas/public/FanStack_Live/game_recap_live.json",
        "/home/james/stacklabs/apps/faas/dist/FanStack_Live/game_recap_live.json"
    ]
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            games = data.get("games", {})
            target_keys = []
            if game_pk in games:
                target_keys.append(game_pk)
            
            away = state.get("away_team", "")
            home = state.get("home_team", "")
            for k in list(games.keys()):
                if f"{away}_{home}" in k or (away in k and home in k):
                    if k not in target_keys:
                        target_keys.append(k)
            
            venue_str = f" ({state['venue']})" if state.get("venue") else ""
            score_line = f"{away} {state.get('away_score', 0)} \u2014 {state.get('home_score', 0)} {home}{venue_str}"
            badge = state.get("clock") or state.get("status") or "LIVE"
            
            for k in target_keys:
                games[k]["score_line"] = score_line
                games[k]["inning_badge"] = badge
            
            data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S EDT")
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[RECAP_UPDATE_ERROR] Failed to update {path}: {e}")

update_recap_file = update_game_recap_json

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_nfl_summary(event_id: str, sport: str = "nfl"):
    is_cfb = str(sport).lower() in ("cfb", "college-football")
    primary_url = f"https://site.api.espn.com/apis/site/v2/sports/football/{'college-football' if is_cfb else 'nfl'}/summary?event={event_id}"
    fallback_url = f"https://site.api.espn.com/apis/site/v2/sports/football/{'nfl' if is_cfb else 'college-football'}/summary?event={event_id}"
    try:
        r = requests.get(primary_url, timeout=5)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            r_fb = requests.get(fallback_url, timeout=5)
            if r_fb.status_code == 200:
                return r_fb.json()
        return None
    except Exception as e:
        print(f"[NFL_STREAMER] Error fetching {event_id}: {e}")
        print(f"[NFL_STREAMER] Error fetching {event_id} ({sport}): {e}")
        return None

def parse_nfl_state(event_id: str, data: dict, sport: str = "nfl"):
    sport_lower = (sport or "nfl").lower().strip()
    is_cfb = sport_lower in ("cfb", "college-football", "ncaa")
    
    header = data.get("header", {})
    competitions = header.get("competitions", [{}])
    if not competitions:
        return None
    competition = competitions[0]
    competitors = competition.get("competitors", [])
    
    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})
    
    home_team = home_comp.get("team", {}).get("abbreviation", "HME")
    away_team = away_comp.get("team", {}).get("abbreviation", "AWY")
    home_name = home_comp.get("team", {}).get("displayName", home_team)
    away_name = away_comp.get("team", {}).get("displayName", away_team)
    
    home_score = int(home_comp.get("score", 0))
    away_score = int(away_comp.get("score", 0))
    
    status_type = competition.get("status", {}).get("type", {})
    status_detail = status_type.get("detail", "Scheduled")
    short_detail = status_type.get("shortDetail", status_detail)
    
    # Venue / Stadium
    game_info = data.get("gameInfo", {})
    venue = game_info.get("venue", {}).get("fullName") or competition.get("venue", {}).get("fullName") or ""
    
    # Drives & Plays
    drives = data.get("drives", {})
    curr_drive = drives.get("current") or (drives.get("previous", [{}])[-1] if drives.get("previous") else {})
    plays = curr_drive.get("plays", [])
    last_play = plays[-1] if plays else {}
    
    play_text = last_play.get("text", "")
    start_info = last_play.get("start", {})
    end_info = last_play.get("end", {})
    
    down_dist = end_info.get("downDistanceText") or start_info.get("downDistanceText") or ""
    yard_line = end_info.get("yardLine", start_info.get("yardLine", 50))
    
    # Derive line of scrimmage (0-100 yards)
    possession_team_id = curr_drive.get("team", {}).get("id") or start_info.get("team", {}).get("id")
    possession_abbr = home_team if str(possession_team_id) == str(home_comp.get("id")) else away_team
    
    # Full Game Drives & Plays Extraction (reverse-chronological order)
    seen_drive_ids = set()
    all_drives = []
    for d in drives.get("previous", []):
        d_id = str(d.get("id", ""))
        if d_id and d_id not in seen_drive_ids:
            seen_drive_ids.add(d_id)
            all_drives.append(d)

    curr_drive_obj = drives.get("current")
    if curr_drive_obj:
        c_id = str(curr_drive_obj.get("id", ""))
        if c_id not in seen_drive_ids:
            seen_drive_ids.add(c_id)
            all_drives.append(curr_drive_obj)
        else:
            for idx, d in enumerate(all_drives):
                if str(d.get("id", "")) == c_id:
                    all_drives[idx] = curr_drive_obj
                    break

    all_plays_chronological = []
    seen_play_ids = set()

    for drive_idx, drive in enumerate(all_drives, start=1):
        d_team = drive.get("team", {}).get("abbreviation", "")
        if not d_team:
            d_t_id = str(drive.get("team", {}).get("id", ""))
            d_team = home_team if d_t_id == str(home_comp.get("id")) else (away_team if d_t_id == str(away_comp.get("id")) else "")
        d_desc = drive.get("description", "")
        d_res = drive.get("displayResult") or drive.get("result") or drive.get("shortDisplayResult") or ""

        for p in drive.get("plays", []):
            p_id = str(p.get("id", ""))
            p_text = p.get("text", "").strip()
            if not p_text:
                continue
            if p_id and p_id in seen_play_ids:
                continue
            if p_id:
                seen_play_ids.add(p_id)

            p_down = p.get("start", {}).get("downDistanceText", "")
            p_clock = p.get("clock", {}).get("displayValue", "")
            p_period = p.get("period", {}).get("number", 1) if isinstance(p.get("period"), dict) else p.get("period", 1)
            p_scoring = bool(p.get("scoringPlay", False))
            p_score_val = p.get("scoreValue", 0)
            p_stat_yds = p.get("statYardage", 0)
            p_home_score = p.get("homeScore")
            p_away_score = p.get("awayScore")

            all_plays_chronological.append({
                "id": p_id or f"{drive_idx}-{len(all_plays_chronological)}",
                "drive_idx": drive_idx,
                "team": d_team or possession_abbr,
                "drive_desc": d_desc,
                "drive_result": d_res,
                "clock": p_clock,
                "period": p_period,
                "down": p_down,
                "text": p_text,
                "scoring": p_scoring,
                "scoreValue": p_score_val,
                "statYardage": p_stat_yds,
                "homeScore": p_home_score,
                "awayScore": p_away_score
            })

    # Reverse-chronological order: newest live play first, descending to opening kickoff
    recent_plays_list = list(reversed(all_plays_chronological))
    if recent_plays_list:
        recent_plays_list[0]["isLive"] = True
            
    # Box score stats
    boxscore = data.get("boxscore", {})
    teams_stats = boxscore.get("teams", [])
    away_stats = next((t for t in teams_stats if str(t.get("team", {}).get("id")) == str(away_comp.get("id"))), {})
    home_stats = next((t for t in teams_stats if str(t.get("team", {}).get("id")) == str(home_comp.get("id"))), {})
    
    def get_stat(stat_dict, name):
        for s in stat_dict.get("statistics", []):
            if s.get("name") == name or s.get("label") == name:
                return s.get("displayValue")
        return "0"

    # Dynamic Starting QB & Passing Stats parsing from boxscore.players
    players_data = boxscore.get("players", [])
    away_qb = None
    away_qb_number = None
    away_qb_stat = None
    away_qb_rating = None
    away_qb_comp_pct = None

    home_qb = None
    home_qb_number = None
    home_qb_stat = None
    home_qb_rating = None
    home_qb_comp_pct = None

    for p_team in players_data:
        t_info = p_team.get("team", {})
        t_id = str(t_info.get("id"))
        t_abbr = t_info.get("abbreviation", "")
        
        is_home = (t_id == str(home_comp.get("id"))) or (t_abbr == home_team)
        is_away = (t_id == str(away_comp.get("id"))) or (t_abbr == away_team)
        
        for stat_grp in p_team.get("statistics", []):
            if stat_grp.get("name") == "passing":
                athletes = stat_grp.get("athletes", [])
                labels = stat_grp.get("labels", [])
                if athletes:
                    primary_qb = athletes[0]
                    ath = primary_qb.get("athlete", {})
                    stats_vals = primary_qb.get("stats", [])
                    stat_dict = dict(zip(labels, stats_vals))
                    
                    qb_name = ath.get("displayName")
                    qb_num = f"#{ath.get('jersey')}" if ath.get("jersey") else ""
                    c_att = stat_dict.get("C/ATT") or stat_dict.get("CP/AT") or ""
                    yds = stat_dict.get("YDS") or ""
                    td = stat_dict.get("TD") or "0"
                    interceptions = stat_dict.get("INT") or "0"
                    rating = stat_dict.get("RTG") or stat_dict.get("QBR") or ""
                    
                    comp_pct = ""
                    if c_att and "/" in c_att:
                        try:
                            c, a = map(int, c_att.split("/"))
                            if a > 0:
                                comp_pct = f"{(c / a) * 100:.1f}%"
                        except Exception:
                            pass
                    
                    stat_line = f"{c_att}, {yds} yds, {td} TD" + (f", {interceptions} INT" if interceptions != "0" else "")
                    
                    if is_home and not home_qb:
                        home_qb = qb_name
                        home_qb_number = qb_num
                        home_qb_stat = stat_line
                        home_qb_rating = rating
                        home_qb_comp_pct = comp_pct
                    elif is_away and not away_qb:
                        away_qb = qb_name
                        away_qb_number = qb_num
                        away_qb_stat = stat_line
                        away_qb_rating = rating
                        away_qb_comp_pct = comp_pct

    # Fallback to leaders if boxscore did not resolve QBs
    if not away_qb:
        try:
            away_qb = away_comp.get("leaders", [{}])[0].get("leaders", [{}])[0].get("athlete", {}).get("displayName")
        except Exception:
            pass
    if not home_qb:
        try:
            home_qb = home_comp.get("leaders", [{}])[0].get("leaders", [{}])[0].get("athlete", {}).get("displayName")
        except Exception:
            pass

    is_cfb_flag = str(sport).lower() in ("cfb", "college-football")

    return {
        "game_pk": event_id,
        "away_team": away_team,
        "home_team": home_team,
        "away_team_name": away_name,
        "home_team_name": home_name,
        "away_score": away_score,
        "home_score": home_score,
        "status": status_detail,
        "inning": status_detail,
        "clock": short_detail,
        "down_dist": down_dist,
        "yardline": yard_line,
        "possession": possession_abbr,
        "status_msg": f"[{down_dist}] {play_text}" if down_dist else play_text,
        "last_play": play_text,
        "recent_plays": recent_plays_list,
        "venue": venue,
        "away_qb": away_qb,
        "away_qb_number": away_qb_number,
        "away_qb_stat": away_qb_stat,
        "away_qb_stats": away_qb_stat,
        "away_qb_rating": away_qb_rating,
        "away_qb_comp_pct": away_qb_comp_pct,
        "home_qb": home_qb,
        "home_qb_number": home_qb_number,
        "home_qb_stat": home_qb_stat,
        "home_qb_stats": home_qb_stat,
        "home_qb_rating": home_qb_rating,
        "home_qb_comp_pct": home_qb_comp_pct,
        "away_total_yards": get_stat(away_stats, "totalYards"),
        "home_total_yards": get_stat(home_stats, "totalYards"),
        "away_pass_yards": get_stat(away_stats, "netPassingYards"),
        "home_pass_yards": get_stat(home_stats, "netPassingYards"),
        "away_rush_yards": get_stat(away_stats, "rushingYards"),
        "home_rush_yards": get_stat(home_stats, "rushingYards"),
        "away_top": get_stat(away_stats, "possessionTime"),
        "home_top": get_stat(home_stats, "possessionTime"),
        "sport": "CFB" if is_cfb_flag else "NFL",
        "league": "NCAA" if is_cfb_flag else "NFL"
    }

def get_room_advocates(game_pk: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT p.user_name, p.display_name, p.team, p.color, p.avatar_url, p.system_prompt
        FROM game_persona gp
        JOIN persona p ON gp.persona_id = p.id
        WHERE gp.game_pk = ? AND gp.seat_state = 'active'
    """, (game_pk,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

async def generate_advocate_reaction(advocate: dict, play_text: str, down_dist: str, game_state: dict):
    user_name = advocate["user_name"]
    team = advocate["team"]
    prompt = f"""You are {advocate['display_name']} ({team} fan advocate).
{advocate['system_prompt']}

LIVE NFL PLAY EVENT:
Down & Distance: {down_dist}
Score: {game_state['away_team']} {game_state['away_score']} - {game_state['home_score']} {game_state['home_team']}
Play: {play_text}

Output ONE short, punchy, in-character live reaction to this play (maximum 1-2 sentences). Do not use hashtags or meta text. Speak directly in your distinct persona voice!"""

    try:
        # Fast local LLM call or Gemini
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": "phi3:mini",
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 45, "temperature": 0.7}
        }, timeout=3)
        if r.status_code == 200:
            res = r.json().get("response", "").strip().strip('"')
            if res:
                return res
    except Exception:
        pass
        
    # Vertex / Gemini Fallback
    if GEMINI_KEY:
        try:
            import google.genai as genai
            client = genai.Client(api_key=GEMINI_KEY)
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            return resp.text.strip().strip('"')
        except Exception as e:
            print(f"[REACTION_GEN_ERROR] {e}")

    # Sane fallback canned reaction based on team
    if team == "PHI":
        return f"Let's go Eagles! Keep grinding on the line! 🦅"
    elif team == "BAL":
        return f"Ravens Flock defense locking it down! Big Truss! 😈"
    elif team == "DAL":
        return f"Cowboys making the play happen! This is our year! ⭐️"
    else:
        return f"12th Man making noise! Let's get that stop! 🌊"

async def stream_loop():
    print(f"🏈 [NFL STREAMER] Initializing Live Telemetry & Discourse Streamer...")
    
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print(f"📡 [NFL STREAMER] Connected to MARD Relay WebSocket on port 8008!")
                await ws.send(json.dumps({"type": "JOIN_ROOM", "room": "POLLER"}))
                
                while True:
                    for game_pk in ACTIVE_NFL_GAMES:
                        raw_data = fetch_nfl_summary(game_pk)
                        if not raw_data:
                            continue
                            
                        state = parse_nfl_state(game_pk, raw_data)
                        if not state:
                            continue
                            
                        # Check state hash for changes
                        state_hash = f"{state['away_score']}-{state['home_score']}|{state['status']}|{state['down_dist']}|{state['last_play']}"
                        
                        if game_pk not in last_state_hashes or last_state_hashes[game_pk] != state_hash:
                            last_state_hashes[game_pk] = state_hash
                            print(f"\n🏈 [NFL LIVE] Game {game_pk} ({state['away_team']}@{state['home_team']}): {state['clock']} | {state['status_msg']}")
                            
                            # 1. Send CMD_SYNC_STATE to update UI
                            sync_packet = {
                                "type": "CMD_SYNC_STATE",
                                "source": "ESPN_NFL_TELEMETRY",
                                "target_game_pk": game_pk,
                                "data": state
                            }
                            await ws.send(json.dumps(sync_packet))
                            
                            # 2. Update game_recap_live.json directly
                            try:
                                update_game_recap_json(game_pk, state)
                            except Exception as e:
                                print(f"[RECAP_UPDATE_ERROR] {e}")

                            # 3. Update database schedule records
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                cur = conn.cursor()
                                cur.execute("""
                                    UPDATE mlb_schedule
                                    SET status = ?, sys_updated_on = datetime('now')
                                    WHERE game_pk = ?
                                """, (state["status"], game_pk))
                                cur.execute("""
                                    UPDATE nfl_schedule
                                    SET status = ?, sys_updated_on = datetime('now')
                                    WHERE game_pk = ?
                                """, (state["status"], game_pk))
                                conn.commit()
                                conn.close()
                            except Exception as e:
                                print(f"[DB_UPDATE_ERROR] {e}")

                        # 3. Detect new play for advocate reactions
                        play_hash = f"{state['down_dist']}:{state['last_play']}"
                        if state['last_play'] and (game_pk not in last_play_hashes or last_play_hashes[game_pk] != play_hash):
                            last_play_hashes[game_pk] = play_hash
                            
                            # Write play to game_context
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                cur = conn.cursor()
                                cur.execute("""
                                    INSERT INTO game_context 
                                        (id, game_pk, source, headline, content, tags, injected_at, sys_created_on)
                                    VALUES (lower(hex(randomblob(16))), ?, 'espn_nfl', ?, ?, 'NFL,PLAY', datetime('now'), datetime('now'))
                                """, (game_pk, state["down_dist"], state["last_play"]))
                                conn.commit()
                                conn.close()
                            except Exception:
                                pass
                                
                            # Pick 1-2 advocates to react
                            advocates = get_room_advocates(game_pk)
                            if advocates:
                                # Pick 1 PHI advocate and 1 BAL advocate or random
                                chosen_advocates = []
                                away_advs = [a for a in advocates if a["team"] == state["away_team"]]
                                home_advs = [a for a in advocates if a["team"] == state["home_team"]]
                                
                                import random
                                if away_advs: chosen_advocates.append(random.choice(away_advs))
                                if home_advs: chosen_advocates.append(random.choice(home_advs))
                                
                                for adv in chosen_advocates:
                                    reaction = await generate_advocate_reaction(adv, state["last_play"], state["down_dist"], state)
                                    if reaction:
                                        print(f"  💬 [{adv['team']}] @{adv['user_name']}: {reaction}")
                                        
                                        chat_msg = {
                                            "type": "CHAT_MESSAGE",
                                            "user": adv["user_name"],
                                            "persona": adv["user_name"],
                                            "display_name": adv["display_name"],
                                            "team": adv["team"],
                                            "color": adv["color"],
                                            "avatar_url": adv["avatar_url"],
                                            "text": reaction,
                                            "target_game_pk": game_pk,
                                            "timestamp": time.strftime("%H:%M:%S")
                                        }
                                        await ws.send(json.dumps(chat_msg))
                                        
                                        # Save to game_chat
                                        try:
                                            conn = sqlite3.connect(DB_PATH)
                                            cur = conn.cursor()
                                            cur.execute("""
                                                INSERT INTO game_chat
                                                    (game_pk, persona, text, msg_type, sys_created_on)
                                                VALUES (?, ?, ?, 'chat', datetime('now'))
                                            """, (game_pk, adv["user_name"], reaction))
                                            conn.commit()
                                            conn.close()
                                        except Exception as e:
                                            print(f"[CHAT_SAVE_ERROR] {e}")
                                            
                                        await asyncio.sleep(1.2) # Stagger chatter
                                        
                    await asyncio.sleep(4)
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"[NFL_STREAMER] WebSocket reconnecting in 3s... ({e})")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[NFL_STREAMER] Unexpected error: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(stream_loop())
