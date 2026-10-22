import sqlite3
import requests
import re
import uuid
import os
import json
import google.genai as genai
from dotenv import load_dotenv
import sys
import asyncio
from datetime import datetime

# Enforce strict sequential execution to eliminate write deadlocks on sovereign_now.db
sem = asyncio.Semaphore(1)

async def setup_game_room(game, data, candidates, dot, wordy):
    async with sem:
        game_pk = str(game['gamePk'])
        home_team = game['teams']['home']['team']['name'].lower()
        away_team = game['teams']['away']['team']['name'].lower()
        
        room_name = f"Game {game_pk} ({away_team.title()}@{home_team.title()})"
        print(f"📡 SECURING TRANSACTION SEMAPHORE: Initializing {room_name}...")
        
        # Map to MLB standard abbreviations
        mlb_teams = {
            'arizona diamondbacks': 'AZ',
            'atlanta braves': 'ATL',
            'baltimore orioles': 'BAL',
            'boston red sox': 'BOS',
            'chicago cubs': 'CHC',
            'chicago white sox': 'CWS',
            'cincinnati reds': 'CIN',
            'cleveland guardians': 'CLE',
            'colorado rockies': 'COL',
            'detroit tigers': 'DET',
            'houston astros': 'HOU',
            'kansas city royals': 'KC',
            'los angeles angels': 'LAA',
            'los angeles dodgers': 'LAD',
            'miami marlins': 'MIA',
            'milwaukee brewers': 'MIL',
            'minnesota twins': 'MIN',
            'new york mets': 'NYM',
            'new york yankees': 'NYY',
            'oakland athletics': 'ATH',
            'athletics': 'ATH',
            'philadelphia phillies': 'PHI',
            'pittsburgh pirates': 'PIT',
            'san diego padres': 'SD',
            'san francisco giants': 'SF',
            'seattle mariners': 'SEA',
            'st. louis cardinals': 'STL',
            'tampa bay rays': 'TB',
            'texas rangers': 'TEX',
            'toronto blue jays': 'TOR',
            'washington nationals': 'WSH'
        }
        home_abbr = mlb_teams.get(home_team, 'UNK')
        away_abbr = mlb_teams.get(away_team, 'UNK')

        # Select exactly 3 personas whose assigned_to matches the team abbreviation
        import random
        def get_team_personas(team_abbr, candidate_pool):
            if team_abbr.upper() == 'NYM':
                target_names = ['barf', 'unclesteviestan', 'keith_fanboy', '7_train_terry']
                selected = []
                for name in target_names:
                    match = next((p for p in candidate_pool if p['user_name'].lower() == name), None)
                    if match:
                        selected.append(match)
                return selected

            matching = []
            for p in candidate_pool:
                if p['user_name'].lower() == 'barf_prime':
                    continue
                assigned = str(p.get('team') or '').strip().lower()
                if assigned in [k.lower() for k in mlb_teams.keys()]:
                    assigned = mlb_teams[assigned].lower()
                if team_abbr.lower() in assigned.split('-'):
                    matching.append(p)

            random.shuffle(matching)
            return matching[:3]

        if (home_abbr == 'NYM' and away_abbr == 'ATL') or (home_abbr == 'ATL' and away_abbr == 'NYM'):
            print(f"📡 SPECIAL METS-BRAVES BOOTH SEEDING ACTIVATED for game {game_pk}")
            # For NYM-ATL, we want exactly the 3 commentators, plus a limited subset of home/away fans (3 NYM, 3 ATL)
            nym_selected = get_team_personas('NYM', candidates)
            temp_candidates = [c for c in candidates if c not in nym_selected]
            atl_selected = get_team_personas('ATL', temp_candidates)
            gkr_selected = [p for p in candidates if p['user_name'].lower() in ['gary_bot', 'ron_bot', 'keith_fanboy']]
            members_set = {}
            for p in nym_selected + atl_selected + gkr_selected:
                members_set[p['id']] = p
            members = list(members_set.values())
        elif game_pk == '823604':
            print(f"📡 SPECIAL METS-RED SOX RIVALRY SEEDING ACTIVATED for game {game_pk}")
            # Ensure our newly onboarded rivalry advocates are seated
            nym_selected = get_team_personas('NYM', candidates)
            if not any(p['user_name'] == 'shea_vintage' for p in nym_selected):
                shea_persona = next((p for p in candidates if p['user_name'] == 'shea_vintage'), None)
                if shea_persona:
                    if len(nym_selected) >= 3:
                        nym_selected.pop()
                    nym_selected.append(shea_persona)
            
            temp_candidates = [c for c in candidates if c not in nym_selected]
            away_selected = get_team_personas('BOS', temp_candidates)
            if not any(p['user_name'] == 'bucky_dent_blues' for p in away_selected):
                bucky_persona = next((p for p in candidates if p['user_name'] == 'bucky_dent_blues'), None)
                if bucky_persona:
                    if len(away_selected) >= 3:
                        away_selected.pop()
                    away_selected.append(bucky_persona)
            
            members = nym_selected + away_selected
        elif game_pk == '823443':
            print(f"📡 SPECIAL ALL-STAR GAME SEEDING ACTIVATED for game {game_pk}")
            # Curate a league-wide roster
            gkr_selected = [p for p in candidates if p['user_name'].lower() in ['gary_bot', 'ron_bot', 'keith_fanboy']]
            
            # National League fans
            nl_teams = {'NYM', 'PHI', 'CHC', 'LAD', 'SD', 'SF', 'STL', 'MIA', 'ATL', 'PIT', 'COL', 'CIN', 'WSH', 'AZ'}
            nl_candidates = [p for p in candidates if p.get('team') in nl_teams and p['user_name'].lower() not in ['gary_bot', 'ron_bot', 'keith_fanboy']]
            
            # American League fans
            al_teams = {'NYY', 'BOS', 'CWS', 'CLE', 'TB', 'DET', 'HOU', 'ATH', 'KC', 'MIN', 'BAL', 'SEA', 'TEX', 'LAA', 'TOR'}
            al_candidates = [p for p in candidates if p.get('team') in al_teams]
            
            import random
            random.shuffle(nl_candidates)
            random.shuffle(al_candidates)
            
            nl_selected = nl_candidates[:4]
            al_selected = al_candidates[:4]
            
            members_set = {}
            for p in gkr_selected + nl_selected + al_selected:
                members_set[p['id']] = p
            members = list(members_set.values())
        else:
            home_selected = get_team_personas(home_abbr, candidates)
            temp_candidates = [c for c in candidates if c not in home_selected]
            away_selected = get_team_personas(away_abbr, temp_candidates)
            members = home_selected + away_selected

        room_key = f"room_{game_pk}"
        boggs_level = 2 # default mid
        
        db_path = '/home/james/stacklabs/dna/sovereign_now.db'
        conn = sqlite3.connect(db_path, timeout=60.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check and dynamically register in mlb_schedule if needed
        cursor.execute("SELECT game_pk FROM mlb_schedule WHERE game_pk = ?", (game_pk,))
        sched_game = cursor.fetchone()
        if not sched_game:
            print(f"Game {game_pk} not found in mlb_schedule. Registering it...")
            cursor.execute("""
                INSERT INTO mlb_schedule (game_pk, game_date, home_team, away_team, venue, status, room_state, boggs_level, sim_speed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_pk, game.get('officialDate', '2026-07-14'), 'NL', 'AL', game.get('venue', {}).get('name', 'Citizens Bank Park'), 'Preview', 'staged', boggs_level, 1.0))
        
        # Check room
        cursor.execute("SELECT sys_id FROM cmdb_ci_fanstack_room WHERE game_pk = ?", (game_pk,))
        room = cursor.fetchone()
        if not room:
            room_sys_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("""
                INSERT INTO cmdb_ci_fanstack_room (sys_id, name, room_key, game_pk, is_simulated, sim_speed, cadence, boggs_level, room_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (room_sys_id, room_name, room_key, game_pk, 1, 1.0, 'pacer', boggs_level, 'staged'))
        else:
            room_sys_id = room['sys_id']

        # Align room_state to active for today's provisioned rooms
        cursor.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (game_pk,))
        cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (game_pk,))
        
        # Ensure registered in active_game_rooms
        cursor.execute("""
            INSERT OR REPLACE INTO active_game_rooms (game_id, url, home_team, away_team, status, date_scheduled, sys_updated_on)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?, CURRENT_TIMESTAMP)
        """, (game_pk, f"/stream/{game_pk}", home_abbr.upper(), away_abbr.upper(), game.get('officialDate', '2026-08-19')))

        # Assign personas
        cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))
        cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
        if dot and dot['id'] not in [m['id'] for m in members]:
            members.append(dot)
        if wordy and wordy['id'] not in [m['id'] for m in members]:
            members.append(wordy)

        for p in members:
            gp_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, ?)",
                           (gp_id, game_pk, p['id'], 'active'))
            m2m_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("INSERT INTO m2m_persona_room (sys_id, persona, room) VALUES (?, ?, ?)",
                           (m2m_id, p['user_name'], game_pk))
            cursor.execute("UPDATE sys_user SET active = 1 WHERE sys_id = ?", (p['id'],))
            
        print(f"Room {room_name} configured with {len(members)} personas in game_persona and m2m_persona_room.")
        conn.commit()
        conn.close()

        # Seed initial game state cache file for instant frontend hydration
        try:
            game_state_dir = "/home/james/stacklabs/game_states"
            os.makedirs(game_state_dir, exist_ok=True)
            state_file = os.path.join(game_state_dir, f"{game_pk}.json")
            
            away_prob = game.get('teams', {}).get('away', {}).get('probablePitcher', {})
            home_prob = game.get('teams', {}).get('home', {}).get('probablePitcher', {})
            
            probable_away = {
                "id": away_prob.get("id"),
                "name": away_prob.get("fullName", "Probable Starter"),
                "era": "---",
                "record": "---"
            } if away_prob else None

            probable_home = {
                "id": home_prob.get("id"),
                "name": home_prob.get("fullName", "Probable Starter"),
                "era": "---",
                "record": "---"
            } if home_prob else None

            init_state = {
                "game_pk": str(game_pk),
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "status": game.get('status', {}).get('abstractGameState', 'Scheduled'),
                "game_status": game.get('status', {}).get('abstractGameState', 'scheduled').lower(),
                "detailed_status": game.get('status', {}).get('detailedState', 'Scheduled'),
                "away_team": away_abbr.upper(),
                "home_team": home_abbr.upper(),
                "away_score": 0,
                "home_score": 0,
                "inning": "Pre-Game",
                "outs": 0,
                "balls": 0,
                "strikes": 0,
                "pitcher": probable_home.get("name") if probable_home else "TBD",
                "batter": "TBD",
                "pitch_name": "NONE",
                "pitch_speed": 0,
                "venue_name": game.get('venue', {}).get('name', ''),
                "venue_location": "",
                "status_msg": f"Scheduled: {away_abbr.upper()} @ {home_abbr.upper()}",
                "probable_pitcher_away": probable_away,
                "probable_pitcher_home": probable_home,
                "lineups": game.get('lineups', {}),
                "recent_plays": []
            }
            tmp_path = state_file + ".tmp"
            with open(tmp_path, "w") as fh:
                json.dump(init_state, fh)
            os.replace(tmp_path, state_file)
            print(f"✅ Pre-seeded game state cache for Game {game_pk} ({away_abbr.upper()}@{home_abbr.upper()})")
        except Exception as seed_err:
            print(f"Warning: Failed to pre-seed game state for Game {game_pk}: {seed_err}")

        # TMI Scenario Generation Phase (blocking API calls, run via asyncio.to_thread)
        load_dotenv('/home/james/stacklabs/.env')
        api_key = os.environ.get("VERTEX_API_KEY") or os.environ.get("VITE_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        try:
            with open('/home/james/stacklabs/scripts/fanstack_live_context.txt', 'r') as f:
                news = f.read()
        except Exception:
            news = "No ambient news available."
            
        prompt = f"""You are Madam Moments, the cheerfully bureaucratic, highly sassy, and slightly terrifying Southern receptionist for the Timeline Moderation Initiative (TMI). You speak with an exaggerated, syrupy Southern accent (using terms like 'honey', sugar, bless his heart, y'all, etc) but your job is orchestrating chaotic timeline branches. A baseball game between {away_team} and {home_team} is experiencing a random on-field delay. 
        Use recent MLB news if relevant: '{news}'. Generate exactly 3 highly specific, chaotic scenarios detailing what caused the delay.
        Output as a JSON array of 3 objects with keys: 'name' (short title), 'description', 'payload' (the narrative text to inject into the live broadcast chat, written completely in your sassy Southern voice), and 'icon' (a single emoji)."""

        scenarios_text = None
        
        def run_api_call():
            text = None
            if api_key:
                try:
                    client = genai.Client(vertexai=True, api_key=api_key)
                    res = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    text = res.text
                except Exception as e:
                    try:
                        client = genai.Client(api_key=api_key)
                        res = client.models.generate_content(
                            model='gemini-3.8-flash',
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        )
                        text = res.text
                    except Exception as e2:
                        print(f"TMI generation failed: {e2}")
            return text

        scenarios_text = await asyncio.to_thread(run_api_call)

        if scenarios_text:
            try:
                clean_text = scenarios_text.strip()
                if clean_text.startswith("```"):
                    match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
                    if match:
                        clean_text = match.group(1).strip()
                
                import ast
                try:
                    scenarios = json.loads(clean_text)
                except:
                    scenarios = ast.literal_eval(clean_text)
                
                conn = sqlite3.connect(db_path, timeout=60.0)
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA busy_timeout = 30000;")
                cursor = conn.cursor()
                for s in scenarios[:3]:
                    s_id = str(uuid.uuid4()).replace('-', '')
                    cursor.execute("INSERT INTO cmdb_ci_tmi_scenario (sys_id, name, description, payload, icon, game_pk) VALUES (?, ?, ?, ?, ?, ?)", 
                                   (s_id, s.get('name',''), s.get('description',''), s.get('payload',''), s.get('icon','🚨'), game_pk))
                conn.commit()
                conn.close()
                print(f"Generated 3 distinct TMI Timeline Branches for Game {game_pk}")
            except Exception as e:
                print(f"Failed to parse or save TMI scenarios: {e}. Response was: {scenarios_text}")

async def main_async(games, data, candidates, dot, wordy):
    tasks = [setup_game_room(g, data, candidates, dot, wordy) for g in games]
    await asyncio.gather(*tasks)

def main():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Load personas directly from the canonical persona table
    cursor.execute("""
        SELECT id, user_name, team
        FROM persona
    """)
    data = [dict(row) for row in cursor.fetchall()]
    
    # Ensure no None types for text processing and filter out cloned game_pk and _ci personas
    valid_data = []
    for p in data:
        if not p.get('user_name'):
            continue
        is_clone = bool(re.search(r'_\d{6}$', p['user_name']) or p['user_name'].endswith('_ci'))
        if p['user_name'] == 'metsfan_86':
            is_clone = False
        if not is_clone:
            valid_data.append(p)
    data = valid_data

    # Parse arguments for date or game PKs
    target_date = None
    target_games = []
    for arg in sys.argv[1:]:
        if re.match(r'^\d{4}-\d{2}-\d{2}$', arg):
            target_date = arg
        else:
            target_games.append(arg)

    # Determine date using Eastern Time to align with fanstack_relay.py
    if not target_date:
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        from datetime import datetime, timedelta
        now_et = datetime.now(ZoneInfo('America/New_York'))
        if now_et.hour < 4:
            target_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            target_date = now_et.strftime('%Y-%m-%d')

    print(f"Aligning daily room setup with game slate date: {target_date}")

    # Deactivate past rooms to prevent stale entries from polluting the switcher dropdown
    try:
        cleanup_conn = sqlite3.connect(db_path, timeout=60.0)
        cleanup_conn.execute("PRAGMA journal_mode = WAL;")
        cleanup_conn.execute("PRAGMA synchronous = NORMAL;")
        cleanup_conn.execute("PRAGMA foreign_keys = ON;")
        cleanup_conn.execute("PRAGMA busy_timeout = 30000;")
        cleanup_cursor = cleanup_conn.cursor()
        cleanup_cursor.execute("UPDATE mlb_schedule SET room_state = 'staged' WHERE game_date < ?", (target_date,))
        cleanup_cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'staged' WHERE game_pk IN (SELECT game_pk FROM mlb_schedule WHERE game_date < ?)", (target_date,))
        cleanup_cursor.execute("UPDATE active_game_rooms SET status = 'CLOSED' WHERE date_scheduled < ?", (target_date,))
        cleanup_cursor.execute("DELETE FROM m2m_persona_room WHERE room IN (SELECT game_pk FROM mlb_schedule WHERE game_date < ?)", (target_date,))
        cleanup_cursor.execute("DELETE FROM game_persona WHERE game_pk IN (SELECT game_pk FROM mlb_schedule WHERE game_date < ?)", (target_date,))
        cleanup_conn.commit()
        cleanup_conn.close()
        print(f"🧹 Past game rooms (prior to {target_date}) deactivated.")
    except Exception as e:
        print("Error during past room cleanup:", e)

    # Get today's schedule explicitly passing the date to bypass MLB's 11 AM roll-over
    try:
        url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={target_date}&hydrate=probablePitcher,lineups,venue'
        schedule = requests.get(url, timeout=10).json()
        dates = schedule.get('dates', [])
        if not dates:
            print(f"No games found on the schedule for date: {target_date}")
            return
        games = dates[0].get('games', [])
        
        # Filter games if targets provided
        if target_games:
            games = [g for g in games if str(g['gamePk']) in target_games]
            if not games:
                print(f"Target games not found in today's schedule for {target_date}.")
                return
        
        # FC-008: Inject Ambient Live News Context automatically during room setup
        print("Scraping Yardbarker for live ambient context...")
        yb_res = requests.get('https://www.yardbarker.com/mlb', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}, timeout=5)
        if yb_res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(yb_res.text, 'html.parser')
            headlines = [a.text.strip() for a in soup.select('.article_title_link')[:6]]
            from datetime import datetime
            with open('/home/james/stacklabs/scripts/fanstack_live_context.txt', 'w') as f:
                for h in headlines:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AMBIENT YARDBARKER NEWS DROP: {h}\n")
            print("Successfully updated fanstack_live_context.txt with fresh MLB lore.")
        else:
            print(f"Failed to fetch Yardbarker news (Status: {yb_res.status_code}).")
    except Exception as e:
        print("Error fetching dynamic schedule or news context:", e)
        return
    finally:
        conn.close()

    dot = next((p for p in data if p['user_name'] == 'dot'), None)
    wordy = next((p for p in data if p['user_name'] == 'wordy'), None)
    candidates = [p for p in data if p['user_name'] not in ['dot', 'wordy']]

    asyncio.run(main_async(games, data, candidates, dot, wordy))
    print("All games today have been provisioned directly from the DB.")

if __name__ == "__main__":
    main()
