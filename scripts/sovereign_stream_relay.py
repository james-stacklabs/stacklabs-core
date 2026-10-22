import sys
import os
import json
import asyncio
import logging
import sqlite3
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import re

# Use standard Sovereign OS logging format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - STREAM_RELAY - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Sovereign Stream Relay")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open CORS for the Vite proxies
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def cfb_score_sync_loop():
    """Periodically refreshes live college football scores from ESPN scoreboard API every 35s."""
    logger.info("🏈 [STREAM_RELAY] Starting CFB live score sync loop (35s cadence)...")
    while True:
        try:
            if "/home/james/stacklabs" not in sys.path:
                sys.path.insert(0, "/home/james/stacklabs")
            try:
                from scripts.sync_cfb_schedule import sync_cfb_date
            except ImportError:
                from sync_cfb_schedule import sync_cfb_date
            today_str = date.today().strftime("%Y%m%d")
            synced = await asyncio.to_thread(sync_cfb_date, today_str)
            logger.info(f"🏈 [STREAM_RELAY] Background sync refreshed {synced} CFB game scores.")
        except Exception as e:
            logger.error(f"Error in CFB live score sync loop: {e}")
        await asyncio.sleep(35)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(cfb_score_sync_loop())

@app.get("/api/health")
def health_check():
    return {"status": "Sovereign Stream Relay is Active", "port": 8097}

@app.get("/api/sports/telemetry_logs")
async def get_telemetry_logs(game_pk: str = None, limit: int = 50):
    """
    Returns the tail of the background poller's raw statcast telemetry log,
    optionally filtered by game_pk.
    """
    logger.info(f"get_telemetry_logs: game_pk={game_pk}, limit={limit}")
    log_path = "/home/james/sovereign_inbox/today/statcast_telemetry.log"
    if not os.path.exists(log_path):
        return []
    try:
        # Resolve game_pk to teams if provided
        filter_teams = None
        if game_pk:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT home_team, away_team FROM mlb_schedule WHERE game_pk = ?", (game_pk,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    # e.g., ("BAL", "SD")
                    filter_teams = (row["home_team"], row["away_team"])
            except Exception as db_err:
                logger.error(f"Error querying teams for game_pk {game_pk}: {db_err}")

        with open(log_path, "r") as f:
            content = f.read()
        
        # Split blocks by literal "\n\n" string
        raw_blocks = content.strip().split("\\n\\n")
            
        parsed_blocks = []
        for raw in raw_blocks:
            if not raw.strip():
                continue
            block_lines = raw.strip().split("\\n")
            block_data = {
                "timestamp": "",
                "state_summary": "",
                "statcast_info": None,
                "raw_payload": None
            }
            for l in block_lines:
                l = l.strip()
                if l.startswith("[") and "] [STATE]" in l:
                    parts = l.split("] [STATE] ")
                    block_data["timestamp"] = parts[0][1:]
                    block_data["state_summary"] = parts[1]
                elif l.startswith("[") and "STATCAST 📡" in l:
                    parts = l.split(" STATCAST 📡 ")
                    if not block_data["timestamp"]:
                        block_data["timestamp"] = parts[0][1:]
                    block_data["statcast_info"] = parts[1]
                elif l.startswith("RAW PAYLOAD: "):
                    payload_str = l[len("RAW PAYLOAD: "):]
                    try:
                        block_data["raw_payload"] = json.loads(payload_str)
                    except Exception:
                        block_data["raw_payload"] = payload_str
            
            # Filter by teams if game_pk was resolved
            if filter_teams:
                payload = block_data["raw_payload"]
                matches = False
                if isinstance(payload, dict):
                    home = payload.get("home_team")
                    away = payload.get("away_team")
                    # Check matching teams in either order
                    if (home == filter_teams[0] and away == filter_teams[1]) or \
                       (home == filter_teams[1] and away == filter_teams[0]):
                        matches = True
                else:
                    if filter_teams[0] in raw and filter_teams[1] in raw:
                        matches = True
                if not matches:
                    continue
                    
            parsed_blocks.append(block_data)
            
        return parsed_blocks[-limit:]
    except Exception as e:
        logger.error(f"Error parsing telemetry logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse telemetry logs")


@app.get("/api/sports/active_games")
async def get_active_games():
    """
    Returns a list of all active game rooms across mlb_schedule and active_game_rooms,
    augmented with live game state cache from disk when available.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        games_dict = {}
        # Fetch from sport_schedule (polymorphic MLB, NFL, PGA)
        cursor.execute(
            """
            SELECT game_pk, home_team, away_team, room_state, sport,
                   status, game_time, game_date, venue
            FROM sport_schedule 
            WHERE room_state IN ('active', 'live')
              AND (game_date >= date('now') OR sport != 'MLB' OR game_pk = 'rm_nfl_blunderdome')
            """
        )
        for r in cursor.fetchall():
            pk = str(r["game_pk"])
            sport = r["sport"] if "sport" in r.keys() and r["sport"] else ("NFL" if len(pk) == 9 else "MLB")
            games_dict[pk] = {
                "game_pk": pk,
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "room_state": r["room_state"],
                "sport": sport,
                "status": r["status"] or "Scheduled",
                "detailed_status": r["status"] or "Scheduled",
                "game_status": (r["status"] or "scheduled").lower(),
                "game_time": r["game_time"] or "",
                "game_date": r["game_date"] or "",
                "venue": r["venue"] or "",
                "away_score": 0,
                "home_score": 0,
                "inning": ""
            }
            
        # Fetch from active_game_rooms
        cursor.execute(
            "SELECT game_id as game_pk, home_team, away_team, status as room_state FROM active_game_rooms WHERE status IN ('ACTIVE', 'active', 'live', 'LIVE')"
        )
        for r in cursor.fetchall():
            pk = str(r["game_pk"])
            if pk not in games_dict:
                games_dict[pk] = {
                    "game_pk": pk,
                    "home_team": r["home_team"],
                    "away_team": r["away_team"],
                    "room_state": r["room_state"].lower(),
                    "sport": "NFL" if len(pk) == 9 else "MLB",
                    "status": "Scheduled",
                    "detailed_status": "Scheduled",
                    "game_status": "scheduled",
                    "game_time": "",
                    "game_date": "",
                    "venue": "",
                    "away_score": 0,
                    "home_score": 0,
                    "inning": ""
                }
                
        conn.close()

        # Overlay live game states from /home/james/stacklabs/game_states/{pk}.json
        for pk, game in games_dict.items():
            cache_file = f"/home/james/stacklabs/game_states/{pk}.json"
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        cached = json.load(f)
                        if cached:
                            game["status"] = cached.get("status") or game["status"]
                            game["game_status"] = cached.get("game_status") or game["game_status"]
                            game["detailed_status"] = cached.get("detailed_status") or cached.get("status") or game["detailed_status"]
                            game["status_msg"] = cached.get("status_msg") or ""
                            if "away_score" in cached and cached["away_score"] is not None:
                                game["away_score"] = cached["away_score"]
                            if "home_score" in cached and cached["home_score"] is not None:
                                game["home_score"] = cached["home_score"]
                            if "inning" in cached and cached["inning"]:
                                game["inning"] = cached["inning"]
                except Exception as cache_err:
                    logger.debug(f"Error reading game state cache {cache_file}: {cache_err}")

        return list(games_dict.values())
    except Exception as e:
        logger.error(f"Error fetching active games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sports/footy/incidents")
async def get_footy_incidents(match_id: int):
    """
    Returns live footy match incidents from the soccer_incident_ingress table for the given match_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT incident_id, match_minute, incident_type, leverage_delta, data_payload "
            "FROM soccer_incident_ingress WHERE match_id = ? ORDER BY CAST(match_minute AS INTEGER) DESC",
            (match_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "incident_id": r["incident_id"],
                "match_minute": r["match_minute"],
                "incident_type": r["incident_type"],
                "leverage_delta": float(r["leverage_delta"]),
                "data_payload": r["data_payload"]
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error fetching footy incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/sports/{sport_type}")
async def get_games(sport_type: str):
    """
    Returns filtered weekend and today games from the SQLite mlb_schedule database table,
    complete with mapped live statuses, sorted by status priority (LIVE first, then scheduled, then finished).
    """
    try:
        today_str = date.today().isoformat()
        start_date = (date.today() - timedelta(days=2)).isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if sport_type == "mlb":
            cursor.execute(
                "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue "
                "FROM mlb_schedule WHERE game_date BETWEEN ? AND ? "
                "AND away_team NOT IN ('PGA', 'GOLF', 'FOOTY', 'WORLD_CUP', 'NFL', 'UFL', 'CATNIPSYNDICATE', 'WEEDSTACK', 'USA', 'ENG', 'GER', 'ESP', 'MEX', 'ARG') "
                "AND home_team NOT IN ('PGA', 'GOLF', 'FOOTY', 'WORLD_CUP', 'NFL', 'UFL', 'CATNIPSYNDICATE', 'WEEDSTACK', 'USA', 'ENG', 'GER', 'ESP', 'MEX', 'ARG')",
                (start_date, today_str)
            )
        elif sport_type == "pga":
            cursor.execute(
                "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue "
                "FROM mlb_schedule WHERE game_date BETWEEN ? AND ? "
                "AND (away_team IN ('PGA', 'GOLF') OR home_team IN ('PGA', 'GOLF'))",
                (start_date, today_str)
            )
        elif sport_type == "nfl":
            end_date = (date.today() + timedelta(days=4)).isoformat()
            cursor.execute(
                "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue, home_score, away_score "
                "FROM sport_schedule WHERE (sport = 'NFL' AND (game_date BETWEEN ? AND ? OR room_state IN ('active', 'live'))) "
                "OR game_pk = 'rm_nfl_blunderdome' OR game_pk = '826001' "
                "ORDER BY CASE WHEN room_state IN ('live', 'active') THEN 0 ELSE 1 END, game_date ASC, game_time ASC",
                (start_date, end_date)
            )
            rows = cursor.fetchall()
            if not rows:
                cursor.execute(
                    "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue "
                    "FROM mlb_schedule WHERE game_pk = '826001' OR away_team = 'NFL' OR home_team = 'NFL'"
                )
                rows = cursor.fetchall()
            if not rows:
                rows = [
                    {"game_pk": "401873284", "home_team": "KC", "away_team": "BAL", "status": "Scheduled", "game_time": "8:20 PM ET", "stream_url": "", "stream_source": "ESPN Live Ingress", "venue": "Arrowhead Stadium"},
                    {"game_pk": "401873279", "home_team": "PHI", "away_team": "GB", "status": "Scheduled", "game_time": "8:15 PM ET", "stream_url": "", "stream_source": "ESPN Live Ingress", "venue": "Corinthians Arena"},
                    {"game_pk": "826001", "home_team": "NYJ", "away_team": "DAL", "status": "Warmup", "game_time": "1:00 PM ET", "stream_url": "", "stream_source": "MARD Ingress Arena", "venue": "MetLife Stadium"},
                    {"game_pk": "401873285", "home_team": "DET", "away_team": "LAR", "status": "Scheduled", "game_time": "8:20 PM ET", "stream_url": "", "stream_source": "ESPN Live Ingress", "venue": "Ford Field"},
                    {"game_pk": "401873286", "home_team": "SF", "away_team": "NYJ", "status": "Scheduled", "game_time": "8:15 PM ET", "stream_url": "", "stream_source": "ESPN Live Ingress", "venue": "Levi's Stadium"}
                ]
        elif sport_type == "cfb":
            end_date = (date.today() + timedelta(days=2)).isoformat()
            cursor.execute(
                "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue, home_score, away_score "
                "FROM sport_schedule WHERE sport = 'CFB' AND (game_date BETWEEN ? AND ? OR room_state IN ('active', 'live')) "
                "ORDER BY CASE WHEN room_state IN ('live', 'active') OR status LIKE '%Quarter%' OR status LIKE '%Half%' THEN 0 ELSE 1 END, game_date ASC, game_time ASC",
                (start_date, end_date)
            )
            rows = cursor.fetchall()
            if not rows:
                cursor.execute(
                    "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue, home_score, away_score "
                    "FROM sport_schedule WHERE sport = 'CFB' "
                    "ORDER BY CASE WHEN room_state IN ('live', 'active') OR status LIKE '%Quarter%' OR status LIKE '%Half%' THEN 0 ELSE 1 END, game_date DESC LIMIT 40"
                )
                rows = cursor.fetchall()
        elif sport_type == "footy":
            cursor.execute(
                "SELECT game_pk, home_team, away_team, status, game_time, stream_url, stream_source, venue "
                "FROM mlb_schedule WHERE game_date BETWEEN ? AND ? "
                "AND (away_team IN ('FOOTY', 'WORLD_CUP', 'USA', 'ENG', 'GER', 'ESP', 'MEX', 'ARG') "
                "OR home_team IN ('FOOTY', 'WORLD_CUP', 'USA', 'ENG', 'GER', 'ESP', 'MEX', 'ARG'))",
                (start_date, today_str)
            )
        else:
            conn.close()
            return []
            
        if sport_type in ("mlb", "pga", "footy"):
            rows = cursor.fetchall()
        conn.close()
        
        games = []
        for r in rows:
            game_pk = str(r["game_pk"])
            row_keys = r.keys()
            home_score = r["home_score"] if "home_score" in row_keys and r["home_score"] is not None else None
            away_score = r["away_score"] if "away_score" in row_keys and r["away_score"] is not None else None
            raw_status = r["status"] or "Scheduled"
            status_detail = raw_status
            
            state_path = f"/home/james/stacklabs/game_states/{game_pk}.json"
            if os.path.exists(state_path):
                try:
                    with open(state_path, "r") as f:
                        state_data = json.load(f)
                        if state_data.get("home_score") is not None:
                            home_score = state_data.get("home_score")
                        if state_data.get("away_score") is not None:
                            away_score = state_data.get("away_score")
                        if state_data.get("status_detail"):
                            status_detail = state_data.get("status_detail")
                        elif state_data.get("quarter") and state_data.get("clock"):
                            status_detail = f"{state_data.get('clock')} - {state_data.get('quarter')}"
                except Exception:
                    pass
            
            # Map active/in-progress game states to "LIVE" for frontend CSS trigger
            status = raw_status
            if "Final" in raw_status or raw_status.upper() == "COMPLETED":
                status = "FINAL"
            elif status in ("In Progress", "Warmup", "Active") or "Quarter" in status or "Half" in status or "Halftime" in status or ("OT" in status and "Final" not in status):
                status = "LIVE"
                if status_detail in ("Scheduled", "In Progress", "Active") and raw_status not in ("Scheduled", "In Progress", "Active"):
                    status_detail = raw_status
            
            title = f"{r['away_team']} @ {r['home_team']}"
            if sport_type == "pga" and r["venue"]:
                title = f"PGA: {r['venue']}"
            elif sport_type in ("nfl", "cfb"):
                title = f"{r['away_team']} @ {r['home_team']}"
                
            games.append({
                "id": game_pk,
                "title": title,
                "status": status,
                "status_detail": status_detail,
                "time": r["game_time"] or "7:10 PM ET",
                "stream_available": bool(r["stream_url"]),
                "scraper": r["stream_source"] or "Unknown",
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "home_score": home_score,
                "away_score": away_score
            })
            
        # Sort games: LIVE (0) first, Scheduled/Pre-Game (1) next, Final/Closed (2) last
        def get_sort_priority(g):
            s = g["status"].upper()
            if s in ("LIVE", "IN PROGRESS", "WARMUP", "ACTIVE"):
                return 0
            elif s in ("SCHEDULED", "PRE-GAME"):
                return 1
            else:
                return 2
                
        games.sort(key=lambda x: (get_sort_priority(x), x["time"], x["id"]))
        return games
    except Exception as e:
        logger.error(f"Error fetching from DB for {sport_type}: {e}")
        return []


@app.get("/api/stream/{game_id}")
async def get_stream_url(game_id: str):
    """
    Returns the resolved SQLite stream URL or falls back to the Red Bull TV stream.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT stream_url, stream_headers FROM mlb_schedule WHERE game_pk = ?", (game_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row["stream_url"]:
            headers_json = row["stream_headers"]
            headers = {}
            available_streams = []
            if headers_json:
                try:
                    data = json.loads(headers_json)
                    if isinstance(data, dict) and ("headers" in data or "available_streams" in data):
                        headers = data.get("headers", {})
                        available_streams = data.get("available_streams", [])
                    else:
                        headers = data
                except Exception:
                    pass
            
            if not available_streams:
                available_streams = [
                    {"name": "Default Feed", "url": row["stream_url"]}
                ]
            return {
                "m3u8_url": row["stream_url"], 
                "stream_headers": headers,
                "available_streams": available_streams
            }
    except Exception as e:
        logger.error(f"Error loading stream URL: {e}")
        
    # Active 24/7 Red Bull TV live HLS action sports stream (failsafe fallback)
    return {
        "m3u8_url": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
        "stream_headers": {},
        "available_streams": [
            {"name": "Failsafe Fallback", "url": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8"}
        ]
    }

class UpdateStreamRequest(BaseModel):
    stream_url: str
    stream_source: str = "Manual Override"
    stream_headers: dict = None

@app.post("/api/stream/{game_id}")
async def update_stream_url(game_id: str, req: UpdateStreamRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read existing headers to preserve available_streams
        cursor.execute("SELECT stream_headers FROM mlb_schedule WHERE game_pk = ?", (game_id,))
        row = cursor.fetchone()
        
        available_streams = []
        if row and row["stream_headers"]:
            try:
                data = json.loads(row["stream_headers"])
                if isinstance(data, dict):
                    available_streams = data.get("available_streams", [])
            except Exception:
                pass
                
        # Construct updated stream headers JSON
        updated_data = {
            "headers": req.stream_headers or {},
            "available_streams": available_streams
        }
        headers_json = json.dumps(updated_data)
        
        cursor.execute(
            "UPDATE mlb_schedule SET stream_url = ?, stream_source = ?, stream_headers = ?, stream_resolved_at = datetime('now') WHERE game_pk = ?",
            (req.stream_url, req.stream_source, headers_json, game_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated stream URL for game {game_id} to {req.stream_url}")
        return {"status": "success", "message": f"Updated stream URL for game {game_id}"}
    except Exception as e:
        logger.error(f"Error updating stream URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/sports/game_state/{game_id}")
async def get_game_state(game_id: str):
    """
    Returns the current cached game state for initial load in the sports portal.
    """
    from fastapi.responses import JSONResponse
    file_path = f"/home/james/stacklabs/game_states/{game_id}.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return JSONResponse(
                content=data,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            logger.error(f"Error reading game state file {file_path}: {e}")
    elif game_id.isdigit():
        if game_id.startswith("401"):
            # ESPN NFL game - bypass MLB statsapi
            away_abbr = "DAL" if game_id == "401872930" else "AWY"
            home_abbr = "NYG" if game_id == "401872930" else "HME"
            on_demand_state = {
                "game_pk": str(game_id),
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "status": "In Progress",
                "game_status": "live",
                "detailed_status": "Live Matchup",
                "away_team": away_abbr,
                "home_team": home_abbr,
                "away_score": 0,
                "home_score": 0,
                "inning": "1st Qtr",
                "outs": 0,
                "balls": 0,
                "strikes": 0,
                "pitcher": "TBD",
                "batter": "TBD",
                "pitch_name": "NONE",
                "pitch_speed": 0,
                "venue_name": "MetLife Stadium" if game_id == "401872930" else "",
                "venue_location": "East Rutherford, NJ",
                "status_msg": f"{away_abbr} @ {home_abbr}",
                "probable_pitcher_away": None,
                "probable_pitcher_home": None,
                "recent_plays": []
            }
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f_out:
                json.dump(on_demand_state, f_out, indent=2)
            return JSONResponse(
                content=on_demand_state,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    feed = json.loads(resp.read().decode("utf-8"))
                    gd = feed.get("gameData", {})
                    teams = gd.get("teams", {})
                    probables = gd.get("probablePitchers", {})
                    away_abbr = teams.get("away", {}).get("abbreviation", "AWY")
                    home_abbr = teams.get("home", {}).get("abbreviation", "HME")
                    away_p = probables.get("away")
                    home_p = probables.get("home")
                    status_desc = gd.get("status", {}).get("detailedState", "Scheduled")
                    
                    on_demand_state = {
                        "game_pk": str(game_id),
                        "last_updated": datetime.utcnow().isoformat() + "Z",
                        "status": gd.get("status", {}).get("abstractGameState", "Scheduled"),
                        "game_status": gd.get("status", {}).get("abstractGameState", "scheduled").lower(),
                        "detailed_status": status_desc,
                        "away_team": away_abbr,
                        "home_team": home_abbr,
                        "away_score": 0,
                        "home_score": 0,
                        "inning": "Pre-Game",
                        "outs": 0,
                        "balls": 0,
                        "strikes": 0,
                        "pitcher": home_p.get("fullName") if home_p else "TBD",
                        "batter": "TBD",
                        "pitch_name": "NONE",
                        "pitch_speed": 0,
                        "venue_name": gd.get("venue", {}).get("name", ""),
                        "venue_location": "",
                        "status_msg": f"Scheduled: {away_abbr} @ {home_abbr}",
                        "probable_pitcher_away": {
                            "id": away_p.get("id"),
                            "name": away_p.get("fullName"),
                            "era": "---",
                            "record": "---"
                        } if away_p else None,
                        "probable_pitcher_home": {
                            "id": home_p.get("id"),
                            "name": home_p.get("fullName"),
                            "era": "---",
                            "record": "---"
                        } if home_p else None,
                        "recent_plays": []
                    }
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    tmp_p = file_path + ".tmp"
                    with open(tmp_p, "w") as f_tmp:
                        json.dump(on_demand_state, f_tmp)
                    os.replace(tmp_p, file_path)
                    return JSONResponse(
                        content=on_demand_state,
                        headers={
                            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                            "Pragma": "no-cache",
                            "Expires": "0"
                        }
                    )
        except Exception as on_demand_err:
            logger.warning(f"On-demand feed fetch failed for {game_id}: {on_demand_err}")

    # Fallback: Query database if game_states file is missing
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT home_team, away_team, status, sport, venue, game_time, game_date FROM sport_schedule WHERE game_pk = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT home_team, away_team, status, venue, game_time, game_date FROM mlb_schedule WHERE game_pk = ?", (game_id,))
            row = cursor.fetchone()
            sport = "MLB" if row else "MLB"
        else:
            sport = row["sport"] if "sport" in row.keys() and row["sport"] else "MLB"
        conn.close()
        away = row["away_team"] if row else "AWAY"
        home = row["home_team"] if row else "HOME"
        status = row["status"] if row else "Scheduled"
        venue = row["venue"] if row and "venue" in row.keys() and row["venue"] else ""
        game_time = row["game_time"] if row and "game_time" in row.keys() and row["game_time"] else ""
    except Exception as db_err:
        logger.error(f"Database error in get_game_state fallback: {db_err}")
        away, home, status, sport, venue, game_time = "AWAY", "HOME", "Scheduled", "MLB", "", ""

    default_state = {
        "game_pk": str(game_id),
        "away_team": away,
        "home_team": home,
        "away_score": 0,
        "home_score": 0,
        "sport": sport,
        "inning": "Pre-Game",
        "outs": 0,
        "balls": 0,
        "strikes": 0,
        "pitcher": "TBD",
        "batter": "TBD",
        "pitch_name": "NONE",
        "pitch_speed": 0,
        "venue": venue,
        "game_time": game_time,
        "status_msg": f"Scheduled: {away} @ {home} {f'({game_time})' if game_time else ''}".strip(),
        "boggs_level": 3,
        "onFirst": False,
        "onSecond": False,
        "onThird": False,
        "status": status,
        "detailed_status": status,
        "game_status": status.lower(),
        "away_record": None,
        "home_record": None,
        "probable_pitcher_away": None,
        "probable_pitcher_home": None,
        "recent_plays": []
    }
    return JSONResponse(content=default_state)
@app.get("/api/properties")
def get_properties():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, value, description FROM sys_properties")
        props = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return props
    except Exception as e:
        logger.error(f"Error fetching properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/properties")
async def update_properties(request: Request):
    try:
        data = await request.json()
        conn = get_db_connection()
        cursor = conn.cursor()
        for name, value in data.items():
            cursor.execute("UPDATE sys_properties SET value = ?, sys_updated_on = datetime('now') WHERE name = ?", (str(value), name))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating properties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/studio/tables")
def get_studio_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/studio/tables/{table_name}")
def get_table_data(table_name: str, limit: int = 100, offset: int = 0):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get table info (columns)
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [{"name": row["name"], "type": row["type"], "pk": bool(row["pk"])} for row in cursor.fetchall()]
        
        # Fetch rows including rowid
        cursor.execute(f"SELECT rowid as _rowid, * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        cursor.execute(f"SELECT count(*) as total FROM {table_name}")
        total = cursor.fetchone()["total"]
        
        conn.close()
        return {"columns": columns, "rows": rows, "total": total}
    except Exception as e:
        logger.error(f"Error loading table data for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/studio/tables/{table_name}")
async def create_table_row(table_name: str, request: Request):
    try:
        data = await request.json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filter keys to columns that exist in the table
        cursor.execute(f"PRAGMA table_info({table_name})")
        col_names = [row[1] for row in cursor.fetchall()]
        
        insert_data = {k: v for k, v in data.items() if k in col_names and k != "_rowid"}
        
        if not insert_data:
            conn.close()
            # If no data columns are passed (e.g. empty or default row), let sqlite handle it
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {table_name} DEFAULT VALUES")
            new_rowid = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"status": "success", "_rowid": new_rowid}
            
        keys = list(insert_data.keys())
        placeholders = ", ".join(["?"] * len(keys))
        query = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
        
        cursor.execute(query, list(insert_data.values()))
        conn.commit()
        new_rowid = cursor.lastrowid
        conn.close()
        return {"status": "success", "_rowid": new_rowid}
    except Exception as e:
        logger.error(f"Error inserting row into {table_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/studio/tables/{table_name}/{row_id}")
async def update_table_row(table_name: str, row_id: int, request: Request):
    try:
        data = await request.json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filter keys to columns that exist in the table
        cursor.execute(f"PRAGMA table_info({table_name})")
        col_names = [row[1] for row in cursor.fetchall()]
        
        update_data = {k: v for k, v in data.items() if k in col_names and k != "_rowid"}
        
        if not update_data:
            conn.close()
            return {"status": "success"}
            
        sets = [f"{k} = ?" for k in update_data.keys()]
        query = f"UPDATE {table_name} SET {', '.join(sets)} WHERE rowid = ?"
        
        cursor.execute(query, list(update_data.values()) + [row_id])
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating row in {table_name} (rowid={row_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/studio/tables/{table_name}/{row_id}")
def delete_table_row(table_name: str, row_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE rowid = ?", (row_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting row in {table_name} (rowid={row_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info("Initializing Sovereign Stream Relay Engine...")
    uvicorn.run(app, host="0.0.0.0", port=8097)
