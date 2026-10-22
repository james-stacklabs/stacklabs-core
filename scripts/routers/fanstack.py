from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3, os, re, uuid, time, json, subprocess, asyncio, aiohttp, shutil, logging
from datetime import datetime, timedelta, timezone
from core.db import DB_PATH, get_db
from core.security import get_current_user, require_pilot, require_manager_or_pilot, security
from core.utils import _et_game_date
from core.roster_registry import RoomRosterRegistry

logger = logging.getLogger("fanstack_router")

router = APIRouter()

# ── Advocate AI Inference Engine Mode API ──────────────────────────────────────

class InferenceModePayload(BaseModel):
    mode: str

@router.get("/api/fanstack/inference_mode")
async def get_fanstack_inference_mode():
    """Retrieve the active Advocate AI discourse inference engine mode."""
    mode = "LOCAL_CORPUS"
    updated_at = None
    try:
        with get_db() as conn:
            row = conn.execute("SELECT setting_value, updated_at FROM sys_app_settings WHERE setting_key = 'fanstack.advocate_inference_mode'").fetchone()
            if row:
                mode = row["setting_value"]
                updated_at = row["updated_at"]
    except Exception:
        pass
        
    # Check environment & .env file
    g_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("VERTEX_API_KEY")
    if not g_key:
        try:
            import dotenv
            dotenv.load_dotenv("/home/james/stacklabs/.env")
            g_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("VERTEX_API_KEY")
        except Exception:
            pass
    has_gemini_key = bool(g_key and len(g_key) > 5)
    return {
        "mode": mode,
        "active_model": "gemini-3.7-flash" if mode == "CLOUD_API" else "offline_corpus",
        "has_api_key": has_gemini_key,
        "gcp_project": "1096490775777",
        "billing_status": "Active ($300 Credit Buffer)" if has_gemini_key else "Missing Key",
        "updated_at": updated_at
    }

@router.put("/api/fanstack/inference_mode")
async def set_fanstack_inference_mode(payload: InferenceModePayload):
    """Set and persist the active Advocate AI discourse inference engine mode."""
    normalized_mode = payload.mode.strip().upper()
    if normalized_mode not in ("CLOUD_API", "LOCAL_CORPUS"):
        raise HTTPException(status_code=400, detail="Invalid mode. Must be CLOUD_API or LOCAL_CORPUS.")
        
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO sys_app_settings (sys_id, setting_key, setting_value, setting_category, description, updated_by, updated_at)
                VALUES ('setting_fanstack_inference_mode', 'fanstack.advocate_inference_mode', ?, 'fanstack', 'Active Advocate inference engine mode', 'pilot', CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_by = 'pilot',
                    updated_at = CURRENT_TIMESTAMP
            """, (normalized_mode,))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist inference mode: {str(e)}")
        
    return {
        "status": "success",
        "mode": normalized_mode,
        "active_model": "gemini-3.7-flash" if normalized_mode == "CLOUD_API" else "offline_corpus"
    }

# ── End Game Log Export API ────────────────────────────────────────────────────


@router.get("/api/hot_takes")
async def get_hot_takes(persona: str = None, limit: int = 50):
    """Retrieve persisted hot takes from sovereign_now.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if persona:
        cur.execute("SELECT * FROM hot_takes WHERE persona = ? ORDER BY created_at DESC LIMIT ?", (persona, limit))
    else:
        cur.execute("SELECT * FROM hot_takes ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"hot_takes": rows}

@router.post("/api/rooms/{game_pk}/injections")
async def add_room_injection(game_pk: str, data: dict):
    """
    Pilot manual injection endpoint for related lists satirical or breaking drops.
    """
    import uuid
    import sqlite3
    from fastapi import HTTPException
    
    injection_type = data.get("injection_type", "satirical")
    headline = data.get("headline", "Manual Drop")
    content = data.get("content", "")
    weight = float(data.get("weight", 1.0))
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
        
    sys_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000")
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO room_lore_injections (sys_id, game_pk, injection_type, headline, content, weight, active, used_count)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0)
        """, (sys_id, game_pk, injection_type, headline, content, weight))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    conn.close()
    return {"status": "success", "sys_id": sys_id}
# ── End Hot Takes Service ─────────────────────────────────────────────────────



@router.get("/api/mlb/games")
async def get_mlb_games(
    date: str = None,
    days: int = None,
    all: bool = False
):
    """
    Returns games from mlb_schedule for use in the Deployment Zone dropdown.
    - Default: today's Scheduled/Pre-Game/In Progress games only
    - ?date=YYYY-MM-DD  → specific date
    - ?days=7           → today + next N days (rolling window for advance setup)
    - ?all=true         → full season (use sparingly — 2437 rows)
    Postponed, Suspended, and Cancelled games are always excluded.
    """
    from datetime import date as dt_date, timedelta
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    skip_statuses = ("'Postponed'", "'Suspended'", "'Cancelled'", "'Cancelled by Rain'")
    skip_clause = f"AND status NOT IN ({','.join(skip_statuses)})"

    if all:
        c.execute(f"""
            SELECT game_pk, game_date, away_team, home_team, venue, status
            FROM mlb_schedule {skip_clause}
            ORDER BY game_date, game_pk
        """)
    elif date:
        c.execute(f"""
            SELECT game_pk, game_date, away_team, home_team, venue, status
            FROM mlb_schedule WHERE game_date=? {skip_clause}
            ORDER BY game_pk
        """, (date,))
    elif days:
        today = _et_game_date()
        from datetime import date as _d
        end   = (_d.fromisoformat(today) + timedelta(days=days)).isoformat()
        c.execute(f"""
            SELECT game_pk, game_date, away_team, home_team, venue, status
            FROM mlb_schedule WHERE game_date BETWEEN ? AND ? {skip_clause}
            ORDER BY game_date, game_pk
        """, (today, end))
    else:
        today = _et_game_date()
        c.execute(f"""
            SELECT game_pk, game_date, away_team, home_team, venue, status
            FROM mlb_schedule WHERE game_date=? {skip_clause}
            ORDER BY game_pk
        """, (today,))

    rows = c.fetchall()
    conn.close()
    return {
        "status": "success",
        "count": len(rows),
        "games": [
            {
                "game_pk":   r["game_pk"],
                "game_date": r["game_date"],
                "label":     f"{r['game_pk']} — {r['away_team']} @ {r['home_team']}",
                "away_team": r["away_team"],
                "home_team": r["home_team"],
                "venue":     r["venue"],
                "status":    r["status"],
            }
            for r in rows
        ]
    }

@router.get("/api/teams")
async def get_teams():
    """Returns distinct MLB team codes from the persona table (SSOT for team dropdowns).

    NOTE: this file previously had TWO definitions of this route with different logic --
    one querying cmdb_ci/cmdb_ci_ai_persona (which was actually live, since FastAPI uses
    the first-registered match), and one querying the `persona` table (which was dead code
    and never executed). The `persona` table is what every other route in personas.py
    actually reads/writes, so that's the version kept here. If /api/teams was returning
    different team codes than you expected before this refactor, this is why -- verify
    against your live DB before treating this as final.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT team AS assigned_to
            FROM persona
            WHERE team IS NOT NULL
              AND team != ''
              AND length(team) BETWEEN 2 AND 3
              AND team = upper(team)
              AND team NOT GLOB '*[^A-Z]*'
            ORDER BY team
        """)
        teams = [row["assigned_to"] for row in cur.fetchall()]
    return {"teams": teams}

class OverlayRule(BaseModel):
    rule_name: str
    trigger_condition: str
    overlay_action: str
    active: int = 1

@router.get("/api/sys_overlay_registry")
async def get_overlay_rules():
    """Retrieve all registered condition rules."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM sys_overlay_registry ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"status": "success", "rules": rows}

@router.post("/api/sys_overlay_registry")
async def register_overlay_rule(rule: OverlayRule):
    """Register and persist a new condition rule."""
    import uuid
    from datetime import datetime
    sys_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO sys_overlay_registry (sys_id, rule_name, trigger_condition, overlay_action, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sys_id, rule.rule_name, rule.trigger_condition, rule.overlay_action, rule.active, created_at))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"status": "success", "sys_id": sys_id}

@router.delete("/api/sys_overlay_registry/{sys_id}")
async def delete_overlay_rule(sys_id: str):
    """Delete a registered condition rule by sys_id."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sys_overlay_registry WHERE sys_id = ?", (sys_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"status": "success", "message": f"Deleted rule {sys_id}"}


class PinCreate(BaseModel):
    game_pk: str
    x_pct: float
    y_pct: float
    author: str
    comment: str


@router.get("/api/pins")
async def get_pins(game_pk: str = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if game_pk:
        cur.execute("SELECT * FROM ui_pins WHERE game_pk = ? AND status = 'active' ORDER BY timestamp DESC", (game_pk,))
    else:
        cur.execute("SELECT * FROM ui_pins WHERE status = 'active' ORDER BY timestamp DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"status": "success", "pins": rows}


@router.post("/api/pins")
async def create_pin(pin: PinCreate):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    try:
        cur.execute("""
            INSERT INTO ui_pins (game_pk, x_pct, y_pct, author, comment, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (pin.game_pk, pin.x_pct, pin.y_pct, pin.author, pin.comment, timestamp))
        conn.commit()
        pin_id = cur.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"status": "success", "id": pin_id, "timestamp": timestamp}


@router.delete("/api/pins/{pin_id}")
async def delete_pin(pin_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM ui_pins WHERE id = ?", (pin_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"status": "success", "message": f"Deleted pin {pin_id}"}


def resolve_player_id(player_val: str) -> int:
    if not player_val:
        return None
    try:
        return int(player_val)
    except ValueError:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT sys_id FROM mlb_rosters WHERE player_name = ? COLLATE NOCASE LIMIT 1", (player_val,))
        row = cur.fetchone()
        conn.close()
        if row:
            match = re.search(r'\d+', row[0])
            if match:
                return int(match.group())
    return None


@router.get("/api/sports/telemetry/matchup-prediction")
async def get_matchup_prediction_api(batter: str, pitcher: str):
    """
    Exposes matchup predictive odds.
    """
    batter_id = resolve_player_id(batter)
    pitcher_id = resolve_player_id(pitcher)

    if not batter_id or not pitcher_id:
        return {
            "source": "invalid-players",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }

    intelligence_db = "/home/james/stacklabs/sovereign_intelligence.db"
    conn = sqlite3.connect(intelligence_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # 1. Try head-to-head matchup history
        cur.execute("""
            SELECT
                COUNT(*) as total_matchups,
                COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
            FROM statcast_pitches
            WHERE batter = ? AND pitcher = ?;
        """, (batter_id, pitcher_id))
        row = cur.fetchone()

        if row and row["total_matchups"] > 0:
            return {
                "source": "head-to-head",
                "total_matchups": row["total_matchups"],
                "strikeout_prob": round(row["strikeout_prob"], 1) if row["strikeout_prob"] is not None else 0.0,
                "hit_prob": round(row["hit_prob"], 1) if row["hit_prob"] is not None else 0.0,
                "walk_prob": round(row["walk_prob"], 1) if row["walk_prob"] is not None else 0.0
            }

        # 2. If no head-to-head, get pitcher's dominant pitch type
        cur.execute("""
            SELECT pitch_name, COUNT(*) as c
            FROM statcast_pitches
            WHERE pitcher = ? AND pitch_name IS NOT NULL AND pitch_name != '' AND pitch_name != '---'
            GROUP BY pitch_name
            ORDER BY c DESC
            LIMIT 1
        """, (pitcher_id,))
        p_row = cur.fetchone()

        dominant_pitch = p_row["pitch_name"] if p_row else None

        if dominant_pitch:
            # Try batter's splits against this dominant pitch type
            cur.execute("""
                SELECT
                    COUNT(*) as total_matchups,
                    COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                    COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                    COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
                FROM statcast_pitches
                WHERE batter = ? AND pitch_name = ?;
            """, (batter_id, dominant_pitch))
            b_row = cur.fetchone()

            if b_row and b_row["total_matchups"] > 0:
                return {
                    "source": f"splits_vs_{dominant_pitch}",
                    "total_matchups": b_row["total_matchups"],
                    "strikeout_prob": round(b_row["strikeout_prob"], 1) if b_row["strikeout_prob"] is not None else 0.0,
                    "hit_prob": round(b_row["hit_prob"], 1) if b_row["hit_prob"] is not None else 0.0,
                    "walk_prob": round(b_row["walk_prob"], 1) if b_row["walk_prob"] is not None else 0.0
                }

        # 3. Fallback: Batter's overall splits against all pitch types
        cur.execute("""
            SELECT
                COUNT(*) as total_matchups,
                COUNT(*) FILTER (WHERE events = 'strikeout') * 100.0 / COUNT(*) as strikeout_prob,
                COUNT(*) FILTER (WHERE events IN ('single', 'double', 'triple', 'home_run')) * 100.0 / COUNT(*) as hit_prob,
                COUNT(*) FILTER (WHERE events = 'walk') * 100.0 / COUNT(*) as walk_prob
            FROM statcast_pitches
            WHERE batter = ?;
        """, (batter_id,))
        fallback_row = cur.fetchone()

        if fallback_row and fallback_row["total_matchups"] > 0:
            return {
                "source": "batter-overall",
                "total_matchups": fallback_row["total_matchups"],
                "strikeout_prob": round(fallback_row["strikeout_prob"], 1) if fallback_row["strikeout_prob"] is not None else 0.0,
                "hit_prob": round(fallback_row["hit_prob"], 1) if fallback_row["hit_prob"] is not None else 0.0,
                "walk_prob": round(fallback_row["walk_prob"], 1) if fallback_row["walk_prob"] is not None else 0.0
            }

        # 4. Final safety fallback
        return {
            "source": "league-average",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }

    except Exception as e:
        print(f"[API_PREDICTION_ERROR] {e}")
        return {
            "source": "error-fallback",
            "total_matchups": 0,
            "strikeout_prob": 22.0,
            "hit_prob": 25.0,
            "walk_prob": 8.0
        }
    finally:
        conn.close()


# ── Game Day Pre-Game Intelligence Dossier Engine (WO-2026-0908) ────────────

class PregameIntelPayload(BaseModel):
    intel_id: str | None = None
    game_pk: str
    sport: str = "MLB"
    home_team: str
    away_team: str
    event_time_utc: str
    venue: str
    broadcast_info: str
    betting_odds: dict | list | str
    series_context: str
    pitcher_matchup: dict | list | str
    key_players: dict | list | str
    tactical_analysis: str
    prediction_lean: str | None = None
    status: str = "ACTIVE"


@router.get("/api/sports/pregame-intel/active")
async def get_active_pregame_intel():
    """Fetches pre-game intelligence for the currently active or imminent game."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM game_pregame_intel 
            WHERE status = 'ACTIVE' 
            ORDER BY sys_created_on DESC LIMIT 1
        """).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No active pre-game intel available")
        data = dict(row)
        for field in ("betting_odds", "pitcher_matchup", "key_players"):
            if isinstance(data.get(field), str):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    pass
        return data


@router.get("/api/sports/pregame-intel/{game_pk}")
async def get_pregame_intel(game_pk: str):
    """Fetches pre-game intelligence dossier for a specific game."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM game_pregame_intel WHERE game_pk = ? AND status = 'ACTIVE' LIMIT 1",
            (game_pk,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"No pre-game intelligence found for game {game_pk}")
        data = dict(row)
        for field in ("betting_odds", "pitcher_matchup", "key_players"):
            if isinstance(data.get(field), str):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    pass
        return data


@router.post("/api/sports/pregame-intel")
async def upsert_pregame_intel(payload: PregameIntelPayload):
    """Upsert pre-game intelligence dossier."""
    intel_id = payload.intel_id or f"INTEL-{payload.game_pk}-{uuid.uuid4().hex[:6]}"
    odds_str = json.dumps(payload.betting_odds) if not isinstance(payload.betting_odds, str) else payload.betting_odds
    pitcher_str = json.dumps(payload.pitcher_matchup) if not isinstance(payload.pitcher_matchup, str) else payload.pitcher_matchup
    players_str = json.dumps(payload.key_players) if not isinstance(payload.key_players, str) else payload.key_players
    sys_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO game_pregame_intel (
                sys_id, intel_id, game_pk, sport, home_team, away_team,
                event_time_utc, venue, broadcast_info, betting_odds,
                series_context, pitcher_matchup, key_players,
                tactical_analysis, prediction_lean, status,
                sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'james', 'james', 0)
            ON CONFLICT(intel_id) DO UPDATE SET
                game_pk = excluded.game_pk,
                home_team = excluded.home_team,
                away_team = excluded.away_team,
                event_time_utc = excluded.event_time_utc,
                venue = excluded.venue,
                broadcast_info = excluded.broadcast_info,
                betting_odds = excluded.betting_odds,
                series_context = excluded.series_context,
                pitcher_matchup = excluded.pitcher_matchup,
                key_players = excluded.key_players,
                tactical_analysis = excluded.tactical_analysis,
                prediction_lean = excluded.prediction_lean,
                status = excluded.status,
                sys_updated_on = excluded.sys_updated_on,
                sys_mod_count = game_pregame_intel.sys_mod_count + 1
        """, (
            sys_id, intel_id, payload.game_pk, payload.sport, payload.home_team, payload.away_team,
            payload.event_time_utc, payload.venue, payload.broadcast_info, odds_str,
            payload.series_context, pitcher_str, players_str,
            payload.tactical_analysis, payload.prediction_lean, payload.status,
            now, now
        ))
        conn.commit()
        return {"status": "success", "intel_id": intel_id, "game_pk": payload.game_pk}


# ── Audience Pulse & Real-Time Polling Engine ─────────────────────────────────

_poll_ws_broadcast_callback = None

def set_poll_ws_broadcast_callback(cb):
    global _poll_ws_broadcast_callback
    _poll_ws_broadcast_callback = cb

async def _notify_poll_ws(event_payload: dict):
    if _poll_ws_broadcast_callback:
        try:
            res = _poll_ws_broadcast_callback(event_payload)
            if asyncio.iscoroutine(res):
                await res
            return
        except Exception as e:
            print(f"[POLL WS ERROR] {e}")
    # Fallback: connect over loopback to 8008 to inject the broadcast event
    try:
        import websockets
        async with websockets.connect("ws://127.0.0.1:8008", ping_interval=None) as ws:
            await ws.send(json.dumps(event_payload))
    except Exception:
        pass

class CreatePollPayload(BaseModel):
    poll_id: str | None = None
    room_id: str = "GLOBAL"
    question: str
    options: list[str]
    poll_type: str = "single"

class VotePollPayload(BaseModel):
    room_id: str = "GLOBAL"
    voter_id: str
    selected_option: int

def _calculate_poll_tallies(conn, poll_id: str, options: list[str]):
    rows = conn.execute("""
        SELECT selected_option, COUNT(*) as vote_count 
        FROM fanstack_poll_votes 
        WHERE poll_id = ? 
        GROUP BY selected_option
    """, (poll_id,)).fetchall()
    
    counts = {i: 0 for i in range(len(options))}
    total_votes = 0
    for r in rows:
        idx = int(r["selected_option"])
        cnt = int(r["vote_count"])
        if idx in counts:
            counts[idx] = cnt
        total_votes += cnt
        
    counts_list = [counts[i] for i in range(len(options))]
    pcts_list = [round((counts[i] / total_votes * 100), 1) if total_votes > 0 else 0.0 for i in range(len(options))]
    
    return {
        "total_votes": total_votes,
        "option_counts": counts_list,
        "option_pcts": pcts_list
    }

@router.post("/api/sports/polls/create")
async def create_poll(payload: CreatePollPayload):
    """Stage a new in-game audience poll."""
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Poll question cannot be empty.")
    if len(payload.options) < 2:
        raise HTTPException(status_code=400, detail="Poll must provide at least 2 options.")
    if len(payload.options) > 6:
        raise HTTPException(status_code=400, detail="Poll supports maximum of 6 options.")
        
    poll_id = payload.poll_id.strip() if payload.poll_id else f"poll_{uuid.uuid4().hex[:10]}"
    options_json = json.dumps([opt.strip() for opt in payload.options])
    now_iso = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO fanstack_polls (poll_id, room_id, question, options, poll_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'staged', ?)
            ON CONFLICT(poll_id) DO UPDATE SET
                room_id = excluded.room_id,
                question = excluded.question,
                options = excluded.options,
                poll_type = excluded.poll_type
        """, (poll_id, payload.room_id, payload.question.strip(), options_json, payload.poll_type, now_iso))
        conn.commit()
        
    return {
        "poll_id": poll_id,
        "room_id": payload.room_id,
        "question": payload.question.strip(),
        "options": [opt.strip() for opt in payload.options],
        "poll_type": payload.poll_type,
        "status": "staged",
        "created_at": now_iso,
        "tallies": {
            "total_votes": 0,
            "option_counts": [0] * len(payload.options),
            "option_pcts": [0.0] * len(payload.options)
        }
    }

@router.post("/api/sports/polls/{poll_id}/publish")
async def publish_poll(poll_id: str):
    """Activate poll and broadcast to connected room clients."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fanstack_polls WHERE poll_id = ?", (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Poll not found.")
            
        conn.execute("UPDATE fanstack_polls SET status = 'active' WHERE poll_id = ?", (poll_id,))
        conn.commit()
        
        options = json.loads(row["options"])
        tallies = _calculate_poll_tallies(conn, poll_id, options)
        
        poll_data = {
            "poll_id": row["poll_id"],
            "room_id": row["room_id"],
            "question": row["question"],
            "options": options,
            "poll_type": row["poll_type"],
            "status": "active",
            "created_at": row["created_at"],
            "tallies": tallies
        }
        
    await _notify_poll_ws({
        "type": "POLL_PUBLISHED",
        "room_id": row["room_id"],
        "poll_id": poll_id,
        "data": poll_data
    })
    
    return poll_data

@router.post("/api/sports/polls/{poll_id}/vote")
async def vote_poll(poll_id: str, payload: VotePollPayload):
    """Cast an idempotent vote in an active poll."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fanstack_polls WHERE poll_id = ?", (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Poll not found.")
            
        if row["status"] != "active":
            raise HTTPException(status_code=400, detail=f"Voting is locked (poll status is '{row['status']}').")
            
        options = json.loads(row["options"])
        if payload.selected_option < 0 or payload.selected_option >= len(options):
            raise HTTPException(status_code=400, detail="Invalid selected option index.")
            
        conn.execute("""
            INSERT INTO fanstack_poll_votes (poll_id, room_id, voter_id, selected_option, voted_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(poll_id, voter_id) DO UPDATE SET
                selected_option = excluded.selected_option,
                voted_at = CURRENT_TIMESTAMP
        """, (poll_id, payload.room_id, payload.voter_id, payload.selected_option))
        conn.commit()
        
        tallies = _calculate_poll_tallies(conn, poll_id, options)
        poll_data = {
            "poll_id": row["poll_id"],
            "room_id": row["room_id"],
            "question": row["question"],
            "options": options,
            "poll_type": row["poll_type"],
            "status": row["status"],
            "tallies": tallies,
            "user_voted_option": payload.selected_option
        }
        
    await _notify_poll_ws({
        "type": "POLL_VOTED",
        "room_id": row["room_id"],
        "poll_id": poll_id,
        "tallies": tallies,
        "voter_id": payload.voter_id,
        "selected_option": payload.selected_option
    })
    
    return poll_data

@router.get("/api/sports/polls/room/{room_id}/active")
async def get_active_room_poll(room_id: str, voter_id: str | None = None):
    """Retrieve the current active or most recently active poll for a room."""
    with get_db() as conn:
        # Search for active or frozen poll in room or fallback to GLOBAL
        row = conn.execute("""
            SELECT * FROM fanstack_polls 
            WHERE (room_id = ? OR room_id = 'GLOBAL') AND status IN ('active', 'frozen')
            ORDER BY CASE WHEN room_id = ? THEN 0 ELSE 1 END, created_at DESC 
            LIMIT 1
        """, (room_id, room_id)).fetchone()
        
        if not row:
            return {"active_poll": None}
            
        options = json.loads(row["options"])
        tallies = _calculate_poll_tallies(conn, row["poll_id"], options)
        
        user_voted = None
        if voter_id:
            vote_row = conn.execute(
                "SELECT selected_option FROM fanstack_poll_votes WHERE poll_id = ? AND voter_id = ?",
                (row["poll_id"], voter_id)
            ).fetchone()
            if vote_row:
                user_voted = int(vote_row["selected_option"])
                
        return {
            "active_poll": {
                "poll_id": row["poll_id"],
                "room_id": row["room_id"],
                "question": row["question"],
                "options": options,
                "poll_type": row["poll_type"],
                "status": row["status"],
                "is_broadcast": row["is_broadcast"] if "is_broadcast" in row.keys() else 0,
                "created_at": row["created_at"],
                "tallies": tallies,
                "user_voted_option": user_voted
            }
        }

@router.post("/api/sports/polls/{poll_id}/freeze")
async def freeze_poll(poll_id: str):
    """Freeze voting on a poll (read-only state)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fanstack_polls WHERE poll_id = ?", (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Poll not found.")
            
        conn.execute("UPDATE fanstack_polls SET status = 'frozen' WHERE poll_id = ?", (poll_id,))
        conn.commit()
        
        options = json.loads(row["options"])
        tallies = _calculate_poll_tallies(conn, poll_id, options)
        poll_data = {
            "poll_id": row["poll_id"],
            "room_id": row["room_id"],
            "question": row["question"],
            "options": options,
            "status": "frozen",
            "is_broadcast": row["is_broadcast"] if "is_broadcast" in row.keys() else 0,
            "tallies": tallies
        }
        
    await _notify_poll_ws({
        "type": "POLL_FROZEN",
        "room_id": row["room_id"],
        "poll_id": poll_id,
        "data": poll_data
    })
    return poll_data

@router.post("/api/sports/polls/{poll_id}/close")
async def close_poll(poll_id: str):
    """Lock voting and mark poll as closed."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fanstack_polls WHERE poll_id = ?", (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Poll not found.")
            
        conn.execute("UPDATE fanstack_polls SET status = 'closed', is_broadcast = 0, closed_at = ? WHERE poll_id = ?", (now_iso, poll_id))
        conn.commit()
        
        options = json.loads(row["options"])
        tallies = _calculate_poll_tallies(conn, poll_id, options)
        poll_data = {
            "poll_id": row["poll_id"],
            "room_id": row["room_id"],
            "question": row["question"],
            "options": options,
            "status": "closed",
            "is_broadcast": 0,
            "closed_at": now_iso,
            "tallies": tallies
        }
        
    await _notify_poll_ws({
        "type": "POLL_CLOSED",
        "room_id": row["room_id"],
        "poll_id": poll_id,
        "data": poll_data
    })
    return poll_data

@router.post("/api/sports/polls/{poll_id}/broadcast")
async def broadcast_poll_to_tv(poll_id: str):
    """Push or toggle poll results banner to Broadcast TV HUD overlay (Argo / Port 3010)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fanstack_polls WHERE poll_id = ?", (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Poll not found.")
        
        is_bc = int(row["is_broadcast"] or 0) if "is_broadcast" in row.keys() else 0
        new_broadcast = 0 if is_bc == 1 else 1
        conn.execute("UPDATE fanstack_polls SET is_broadcast = ? WHERE poll_id = ?", (new_broadcast, poll_id))
        conn.commit()
            
        options = json.loads(row["options"])
        tallies = _calculate_poll_tallies(conn, poll_id, options)
        poll_data = {
            "poll_id": row["poll_id"],
            "room_id": row["room_id"],
            "question": row["question"],
            "options": options,
            "status": row["status"],
            "is_broadcast": new_broadcast,
            "tallies": tallies
        }
        
    await _notify_poll_ws({
        "type": "POLL_BROADCAST" if new_broadcast == 1 else "POLL_UNBROADCAST",
        "room_id": row["room_id"],
        "poll_id": poll_id,
        "data": poll_data
    })
    return {"status": "broadcast_toggled", "is_broadcast": new_broadcast, "poll_id": poll_id, "data": poll_data}

@router.get("/api/sports/polls/list")
async def list_polls(room_id: str | None = None):
    """List polls with tallies for Producer PlayCall Desk."""
    with get_db() as conn:
        if room_id and room_id != "GLOBAL":
            rows = conn.execute(
                "SELECT * FROM fanstack_polls WHERE room_id = ? OR room_id = 'GLOBAL' ORDER BY created_at DESC LIMIT 50",
                (room_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM fanstack_polls ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            
        results = []
        for r in rows:
            options = json.loads(r["options"])
            tallies = _calculate_poll_tallies(conn, r["poll_id"], options)
            results.append({
                "poll_id": r["poll_id"],
                "room_id": r["room_id"],
                "question": r["question"],
                "options": options,
                "poll_type": r["poll_type"],
                "status": r["status"],
                "is_broadcast": r["is_broadcast"] if "is_broadcast" in r.keys() else 0,
                "created_at": r["created_at"],
                "closed_at": r["closed_at"],
                "tallies": tallies
            })
            
        return results

# ── Sports Schedule & Persona Room Seeding Endpoints ─────────────────────────

@router.post("/api/sports/schedule/seed")
async def seed_sports_schedule(data: dict):
    """
    Seeds or upserts a polymorphic sport game into sport_schedule and cmdb_ci_fanstack_room.
    Enforces Invariants I.8 & I.9 (Enterprise REST Ingress).
    """
    game_pk = str(data.get("game_pk", "")).strip()
    if not game_pk:
        raise HTTPException(status_code=400, detail="game_pk is required")
        
    sport = data.get("sport", "MLB")
    home_team = data.get("home_team", "NYM")
    away_team = data.get("away_team", "NYY")
    home_team_name = data.get("home_team_name", "New York Mets")
    away_team_name = data.get("away_team_name", "New York Yankees")
    game_date = data.get("game_date", "2026-05-17")
    game_time = data.get("game_time", "1:40 PM")
    venue = data.get("venue", "Citi Field")
    status = data.get("status", "In Progress")
    room_state = data.get("room_state", "active")
    boggs_level = int(data.get("boggs_level", 3))
    home_score = int(data.get("home_score", 0))
    away_score = int(data.get("away_score", 0))
    
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sport_schedule (
                game_pk, sport, game_date, game_time, home_team, away_team,
                home_team_name, away_team_name, venue, status, room_state,
                boggs_level, home_score, away_score, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            game_pk, sport, game_date, game_time, home_team, away_team,
            home_team_name, away_team_name, venue, status, room_state,
            boggs_level, home_score, away_score
        ))
        
        postgame_raid_url = data.get("postgame_raid_url")
        try:
            existing = conn.execute("SELECT sys_id FROM cmdb_ci_fanstack_room WHERE game_pk = ?", (game_pk,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE cmdb_ci_fanstack_room 
                    SET room_state = ?, boggs_level = ?, 
                        postgame_raid_url = COALESCE(?, postgame_raid_url),
                        sys_updated_on = CURRENT_TIMESTAMP
                    WHERE game_pk = ?
                """, (room_state, boggs_level, postgame_raid_url, game_pk))
            else:
                new_sys_id = uuid.uuid4().hex
                conn.execute("""
                    INSERT INTO cmdb_ci_fanstack_room (
                        sys_id, name, room_key, game_pk, room_state, boggs_level, postgame_raid_url, is_simulated, sim_speed, sys_updated_on
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1.0, CURRENT_TIMESTAMP)
                """, (new_sys_id, f"{away_team} @ {home_team}", f"room_{game_pk}", game_pk, room_state, boggs_level, postgame_raid_url or ""))
        except Exception as err:
            logger.warning("Error updating cmdb_ci_fanstack_room in seed: %s", err)
            
        conn.commit()
        
    return {
        "status": "seeded",
        "game_pk": game_pk,
        "sport": sport,
        "matchup": f"{away_team} @ {home_team}",
        "room_state": room_state,
        "game_date": game_date
    }


@router.post("/api/sports/rooms/{game_pk}/personas")
@router.post("/api/fanstack/rooms/{game_pk}/personas")
@router.post("/api/fanstack/seat")
async def seat_room_personas(game_pk: Optional[str] = None, data: dict = None):
    """
    Seats fan personas into a game room across m2m_persona_room and game_persona,
    and atomically updates the Data Plane RoomRosterRegistry (WO0010160).
    """
    data = data or {}
    pk = str(game_pk or data.get("game_pk") or data.get("room_id") or "").strip()
    if not pk:
        raise HTTPException(status_code=400, detail="game_pk is required")
        
    personas = data.get("personas", [])
    if not isinstance(personas, list) or not personas:
        raise HTTPException(status_code=400, detail="personas list is required")
        
    prompt_overlay = data.get("prompt_overlay") or f"Subway Series 2026 Seated Advocate for Room {pk}."
    clear_existing = data.get("clear_existing", True)
    
    seated = []
    with get_db() as conn:
        if clear_existing:
            conn.execute("DELETE FROM m2m_persona_room WHERE room = ?", (pk,))
            conn.execute("DELETE FROM game_persona WHERE game_pk = ?", (pk,))
            
        for p_identifier in personas:
            row = conn.execute(
                "SELECT id, user_name, display_name FROM persona WHERE user_name = ? OR id = ? LIMIT 1",
                (p_identifier, p_identifier)
            ).fetchone()
            if not row:
                continue
                
            adv_id = row["id"]
            user_name = row["user_name"]
            
            m2m_sys_id = uuid.uuid4().hex
            conn.execute("""
                INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, ?)
            """, (m2m_sys_id, user_name, pk, prompt_overlay))
            
            gp_id = uuid.uuid4().hex
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
                    VALUES (?, ?, ?, 'active')
                """, (gp_id, pk, adv_id))
            except Exception:
                pass
                
            seated.append(user_name)
            
        conn.commit()

    # Atomically synchronize Data Plane in-memory cache (WO0010160 Invariant)
    if clear_existing:
        RoomRosterRegistry.set_roster(pk, seated)
    else:
        for s in seated:
            RoomRosterRegistry.add_persona(pk, s)
        
    return {
        "status": "seated",
        "game_pk": pk,
        "seated_count": len(seated),
        "personas": seated,
        "active_roster": list(RoomRosterRegistry.get_active_personas(pk))
    }


@router.delete("/api/sports/rooms/{game_pk}/personas/{persona}")
@router.delete("/api/fanstack/rooms/{game_pk}/personas/{persona}")
async def remove_room_persona(game_pk: str, persona: str):
    """
    Removes a persona from a game room across m2m_persona_room and game_persona,
    and updates RoomRosterRegistry in memory (WO0010160).
    """
    pk = str(game_pk).strip()
    p_target = persona.lower().lstrip('@').strip()
    with get_db() as conn:
        conn.execute("""
            DELETE FROM m2m_persona_room 
            WHERE room = ? AND (
                LOWER(persona) = ? OR 
                persona IN (SELECT id FROM persona WHERE LOWER(user_name) = ?)
            )
        """, (pk, p_target, p_target))
        conn.execute("""
            DELETE FROM game_persona 
            WHERE game_pk = ? AND persona_id IN (
                SELECT id FROM persona WHERE LOWER(user_name) = ?
            )
        """, (pk, p_target))
        conn.commit()

    RoomRosterRegistry.remove_persona(pk, p_target)
    return {
        "status": "removed",
        "game_pk": pk,
        "persona": p_target,
        "active_roster": list(RoomRosterRegistry.get_active_personas(pk))
    }


@router.post("/api/fanstack/bring_gang")
@router.post("/api/sports/rooms/{game_pk}/bring_gang")
async def bring_gang_endpoint(game_pk: Optional[str] = None, data: dict = None):
    """
    Transfers an entourage / gang of advocates from source_room to target_room.
    Persists to m2m_persona_room and game_persona, and atomically updates RoomRosterRegistry (WO0010160).
    """
    data = data or {}
    target_pk = str(game_pk or data.get("target_room_id") or data.get("target_game_pk") or data.get("target_stream") or "").strip()
    source_pk = str(data.get("source_room_id") or data.get("previous_game_pk") or "").strip()
    if not target_pk:
        raise HTTPException(status_code=400, detail="target_room_id/game_pk is required")

    explicit_personas = data.get("personas") or []
    prompt_overlay = data.get("prompt_overlay") or f"Entourage transferred via Bring Gang to Room {target_pk}"

    transferred = []
    with get_db() as conn:
        if explicit_personas:
            to_seat = explicit_personas
        elif source_pk:
            rows = conn.execute("""
                SELECT COALESCE(p.user_name, m.persona) as persona_name
                FROM m2m_persona_room m
                LEFT JOIN persona p ON (p.user_name = m.persona OR p.id = m.persona)
                WHERE m.room = ?
            """, (source_pk,)).fetchall()
            to_seat = [r["persona_name"] for r in rows if r["persona_name"]]
        else:
            rows = conn.execute("SELECT user_name FROM persona WHERE is_sophisticated = 1 OR deployment_zone = 'GLOBAL' LIMIT 5").fetchall()
            to_seat = [r["user_name"] for r in rows if r["user_name"]]

        for p_name in to_seat:
            row = conn.execute(
                "SELECT id, user_name FROM persona WHERE user_name = ? OR id = ? LIMIT 1",
                (p_name, p_name)
            ).fetchone()
            if not row:
                continue
            adv_id = row["id"]
            u_name = row["user_name"]

            m2m_sys_id = uuid.uuid4().hex
            conn.execute("""
                INSERT OR REPLACE INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, ?)
            """, (m2m_sys_id, u_name, target_pk, prompt_overlay))

            gp_id = uuid.uuid4().hex
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO game_persona (id, game_pk, persona_id, seat_state)
                    VALUES (?, ?, ?, 'active')
                """, (gp_id, target_pk, adv_id))
            except Exception:
                pass

            transferred.append(u_name)

        conn.commit()

    # Atomically update in-memory cache
    for p in transferred:
        RoomRosterRegistry.add_persona(target_pk, p)

    return {
        "status": "success",
        "action": "bring_gang",
        "source_room_id": source_pk,
        "target_room_id": target_pk,
        "count": len(transferred),
        "personas": transferred,
        "active_roster": list(RoomRosterRegistry.get_active_personas(target_pk))
    }


@router.get("/api/sports/rooms/{game_pk}/personas")
@router.get("/api/fanstack/roster")
@router.get("/api/fanstack/rooms/{game_pk}/personas")
async def get_room_personas(game_pk: Optional[str] = None, room_id: Optional[str] = None):
    """
    Retrieves all personas currently seated in a game room.
    """
    pk = str(game_pk or room_id or "823498").strip()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.id, p.user_name, p.display_name, p.team, p.color, m.prompt_overlay
            FROM m2m_persona_room m
            JOIN persona p ON (p.user_name = m.persona OR p.id = m.persona)
            WHERE m.room = ?
        """, (pk,)).fetchall()
        
        personas_list = [dict(r) for r in rows]
        # Keep in-memory cache synchronized
        RoomRosterRegistry.set_roster(pk, [r["user_name"] for r in rows if r["user_name"]])
        
        return {
            "game_pk": pk,
            "count": len(rows),
            "personas": personas_list,
            "active_roster": list(RoomRosterRegistry.get_active_personas(pk))
        }



# ── Dual-Mode NFL Live Telemetry & Video-Synced Replay Ingress ──────────────
_nfl_cache: Dict[str, Any] = {}

@router.get("/api/nfl/live/{game_pk}")
async def get_nfl_live_telemetry(game_pk: str, mode: str = "live", play: Optional[int] = None, sport: Optional[str] = "nfl"):
    """
    Fetches real-time authentic NFL / CFB telemetry via ESPN API summary parser (Mode A)
    or cached video-synced replay drive frames (Mode B).
    """
    pk = str(game_pk).strip()
    sport_name = (sport or "nfl").lower()
    cache_key = f"{sport_name}_{pk}"
    
    # Mode B: Replay Mode
    if mode.lower() == "replay" or pk.startswith("rm_nfl") or pk == "replay":
        try:
            from scripts.sports.nfl_replay_harness import NflReplayHarness
            harness = NflReplayHarness()
            play_idx = play if play is not None else 1
            state = harness.get_play_state(play_idx)
            if state:
                return {
                    "status": "SUCCESS",
                    "source": "REPLAY_GAMEPACK",
                    "mode": "replay",
                    "game": state
                }
        except Exception as e:
            pass

    # Mode A: Live Gameday Ingress with 5s TTL Cache
    now = time.time()
    if cache_key in _nfl_cache:
        cached_time, cached_state = _nfl_cache[cache_key]
        if now - cached_time < 5.0:
            return {"status": "SUCCESS", "source": f"ESPN_{sport_name.upper()}_LIVE_CACHED", "mode": "live", "game": cached_state}

    try:
        from scripts.nfl_live_streamer import fetch_nfl_summary, parse_nfl_state
        raw = fetch_nfl_summary(pk, sport=sport_name)
        if raw:
            state = parse_nfl_state(pk, raw, sport=sport_name)
            if state:
                _nfl_cache[cache_key] = (now, state)
                return {"status": "SUCCESS", "source": f"ESPN_{sport_name.upper()}_LIVE", "mode": "live", "game": state}
    except Exception as e:
        pass

    # Fallback to Replay Frame 1 if game is not currently active
    try:
        from scripts.sports.nfl_replay_harness import NflReplayHarness
        harness = NflReplayHarness()
        state = harness.get_play_state(1)
        if state:
            return {"status": "SUCCESS", "source": "REPLAY_FALLBACK", "mode": "replay", "game": state}
    except Exception:
        pass

    return {
        "status": "ERROR",
        "message": f"Unable to fetch NFL telemetry for game {pk}"
    }


class FlagMomentPayload(BaseModel):
    game_pk: Optional[str] = "401872963"
    play_id: Optional[str] = ""
    down_dist: Optional[str] = ""
    play_text: Optional[str] = ""
    vibe_chip: Optional[str] = ""


class TTSBriefPayload(BaseModel):
    senior: Optional[str] = None
    junior: Optional[str] = None
    barf: Optional[str] = None
    text: Optional[str] = None


@router.post("/api/nfl/live/flag_moment")
async def flag_live_moment(payload: FlagMomentPayload):
    """
    Synthesizes real-time reactions and 3-bullet intel brief from Gemini 3.8 Flash
    with calibrated high-fidelity persona fallbacks for Senior, Junior, and Barf.
    """
    g_key = os.environ.get("GEMINI_API_KEY")
    if not g_key:
        try:
            import dotenv
            dotenv.load_dotenv("/home/james/stacklabs/.env")
            g_key = os.environ.get("GEMINI_API_KEY")
        except Exception:
            pass
    if not g_key:
        try:
            key_file = os.path.expanduser("~/.gemini/gemini_api_key.txt")
            if os.path.exists(key_file):
                with open(key_file, "r") as f:
                    g_key = f.read().strip()
        except Exception:
            pass

    if g_key and len(g_key) > 5:
        try:
            from google import genai
            client = genai.Client(api_key=g_key)
            prompt = f"""You are the live reaction engine for FanStack Producer Desk covering Chicago Bears vs Philadelphia Eagles Monday Night Football.
A turning-point play was flagged by the broadcast producer:
Play: {payload.play_text}
Down & Distance: {payload.down_dist}
Producer Vibe: {payload.vibe_chip}

Respond in authentic voice for 3 calibrated sports fan advocates:
1. Senior (@battery_chucker_sr): Havertown auto mechanic, Delco rage, resting BP 210/120. Constant WIP caller. Furious at Nick Sirianni, demands they run Saquon Barkley, disgusted watching Jalen Hurts throw dirt balls while Case Keenum carves up the secondary.
2. Junior (@battery_chucker_jr): Senior's son who fled to Smyrna, GA. Smug software sales rep at Truist Battery. Flexing 35-14 win over GB yesterday, laughing at Delco misery and Keenum carving up Philly in the cold.
3. Barf (@barf): Mets/Jets degenerate regular at Mac's Corner Tap in Queens. Resting BP 214/118. Reality check: Dave, you're 3-1! My season ended on Friday in Queens! Why are you screaming about Case Keenum?!

Also produce 2 sharp intel brief bullets with timestamps and quotes.

Return PURE JSON strictly formatted as:
{{
  "boggs_level": 4.9,
  "reactions": {{
    "senior": "...",
    "junior": "...",
    "barf": "..."
  }},
  "intel_brief": [
    {{ "timestamp": "Halftime", "headline": "...", "quote": "..." }},
    {{ "timestamp": "Q1 8:47", "headline": "...", "quote": "..." }}
  ]
}}"""
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            raw = (res.text or "").strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw)
            return {
                "status": "success",
                "play_id": payload.play_id,
                "boggs_level": parsed.get("boggs_level", 4.9),
                "reactions": parsed.get("reactions", {}),
                "intel_brief": parsed.get("intel_brief", [])
            }
        except Exception as e:
            logger.warning(f"Live Gemini synthesis error: {e}. Falling back to calibrated persona matrix.")

    # High-fidelity calibrated fallback based on vibe chip
    vibe = (payload.vibe_chip or "").upper()
    if "SIRIANNI" in vibe:
        senior = "I drove through Havertown traffic to watch Nick Sirianni call three straight bubble screens! The guy looks like a substitute gym teacher who lost his whistle! RUN SAQUON INTO THE DIRT!"
        junior = "Dad, calm your pacemaker. It's 75 and sunny down here at the Battery and we hung 35 on Green Bay yesterday. Watching you lose your mind over Case Keenum is pure comedy."
        barf = "BP is 214/118. Dave, you're 3-1! My season ended on Friday in Queens! Sirianni won a playoff game last year, Carlos Mendoza hasn't had a hit since June. Eat some pastrami and breathe."
    elif "SAQUON" in vibe:
        senior = "We're paying Saquon Barkley 13 million dollars and Sirianni is running empty backfield with Hurts chucking dirt balls on 3rd & 1! Hand the damn ball to 26!"
        junior = "Dad, Saquon's getting hit 3 yards deep because your line is falling over Soldier Field sod. Down here in Atlanta we just run bootlegs in 75 degree breeze."
        barf = "BP is 214/118. At least you have a running back! The Mets spent $310M and couldn't advance a runner from second with zero outs."
    elif "KEENUM" in vibe:
        senior = "Case Keenum! An insurance salesman journeyman backup QB is 15 of 21 carving up our secondary like a damn Christmas ham! Fire everybody into the Delaware River!"
        junior = "Enjoy Keenum looking like prime Brady against your Delco secondary, pops. Truist Battery is lit tonight, 35-14 vibes only."
        barf = "BP is 214/118. Dave, Keenum has been in the league since George Bush was in office. If you have a stroke at my bar over Case Keenum I'm charging your tab."
    elif "MEDICAL" in vibe:
        senior = "Great, now half the defense is in the blue medical tent while Soldier Field turf claims another ACL. Season is officially in the toilet!"
        junior = "Classic Delco panic. A guy gets a tape job on his ankle and Senior is drafting Sirianni's obituary on WIP."
        barf = "BP is 214/118. You want to talk medical tents? The Mets medical staff is just three guys with ice packs and a prayer."
    else:
        senior = "I drove through Havertown traffic to watch Hurts chuck dirt balls! We're down 10-7 to Case Keenum and Sirianni looks like a substitute gym teacher who lost his whistle."
        junior = "Dad, it's 75 degrees in Smyrna and we hung 35 yesterday. Enjoy Keenum. Truist Battery sends its regards."
        barf = "BP is 214/118. Dave, you're 3-1! My season ended on Friday in Queens! I'm watching Keenum carve up your secondary while eating a cold pastrami on rye."

    intel_brief = [
        { "timestamp": "Halftime", "headline": "Hurts Intentional Grounding (-10 yds)", "quote": "Sirianni looks like a substitute gym teacher who lost his whistle." },
        { "timestamp": "Q1 8:47", "headline": "Case Keenum 8-yd TD to Luther Burden", "quote": "Keenum 15/21 carving secondary like Christmas ham." }
    ]

    return {
        "status": "success",
        "play_id": payload.play_id,
        "boggs_level": 4.9,
        "reactions": {
            "senior": senior,
            "junior": junior,
            "barf": barf
        },
        "intel_brief": intel_brief
    }


@router.post("/api/nfl/live/tts_brief")
async def tts_live_brief(payload: Optional[TTSBriefPayload] = None):
    """
    Synthesizes multi-speaker audio brief using edge-tts into mnf_halftime_brief.mp3.
    """
    sr_text = (payload.senior if payload and payload.senior else
               "I drove through Havertown traffic to watch Hurts chuck dirt balls! We are paying Saquon Barkley thirteen million dollars and Sirianni is running empty backfield! Case Keenum is carving up our secondary like a damn Christmas ham!")
    jr_text = (payload.junior if payload and payload.junior else
               "Dad, calm your pacemaker. It is seventy-five degrees and sunny down here at Truist Battery and we hung thirty-five on Green Bay yesterday. Watching you lose your mind over Case Keenum is pure comedy.")
    bf_text = (payload.barf if payload and payload.barf else
               "BP is 214 over 118. Dave, you are 3 and 1! My season ended on Friday in Queens! Why are you screaming about Case Keenum? Sirianni looks like a substitute gym teacher who lost his whistle. Eat some pastrami and shut up.")

    dist_dir = "/home/james/stacklabs/33_FanStack_Lite/dist/assets"
    pub_dir = "/home/james/stacklabs/33_FanStack_Lite/public/assets"
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(pub_dir, exist_ok=True)
    dist_target = os.path.join(dist_dir, "mnf_halftime_brief.mp3")
    pub_target = os.path.join(pub_dir, "mnf_halftime_brief.mp3")

    try:
        import edge_tts
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            sr_path = os.path.join(tmpdir, "sr.mp3")
            jr_path = os.path.join(tmpdir, "jr.mp3")
            bf_path = os.path.join(tmpdir, "bf.mp3")
            merged_path = os.path.join(tmpdir, "merged.mp3")

            await edge_tts.Communicate(sr_text, "en-US-GuyNeural", rate="+12%", pitch="+0Hz").save(sr_path)
            await edge_tts.Communicate(jr_text, "en-US-EricNeural", rate="+8%", pitch="+2Hz").save(jr_path)
            await edge_tts.Communicate(bf_text, "en-US-ChristopherNeural", rate="+14%", pitch="-4Hz").save(bf_path)

            cmd = ["ffmpeg", "-y", "-i", f"concat:{sr_path}|{jr_path}|{bf_path}", "-acodec", "copy", merged_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            shutil.copyfile(merged_path, dist_target)
            shutil.copyfile(merged_path, pub_target)
    except Exception as e:
        logger.error(f"TTS brief synthesis failed: {e}")
        # If synthesis failed, ensure fallback file exists
        if not os.path.exists(dist_target):
            with open(dist_target, "wb") as f:
                f.write(b"")

    return {
        "status": "success",
        "audio_url": "/assets/mnf_halftime_brief.mp3"
    }


# ── Classic Historical Game Replay Ingress (1986 World Series Game 6) ────────
@router.get("/api/sports/classic/{game_pk}")
async def get_classic_game_telemetry(game_pk: str, play: Optional[int] = 1):
    """
    Fetches synchronized historical game replay telemetry and authentic persona discourse.
    Supports 1986 World Series Game 6 (game_pk: 19861025 / 111111).
    """
    pk = str(game_pk).strip()
    try:
        from scripts.sports.replay_1986_game6 import Classic1986ReplayEngine
        engine = Classic1986ReplayEngine(game_pk=pk)
        play_idx = play if play is not None else 1
        state = engine.get_play_state(play_idx)
        if state:
            return {
                "status": "SUCCESS",
                "source": "1986_GAME6_CLASSIC_REPLAY",
                "game": state
            }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to load classic replay: {str(e)}"
        }

    return {
        "status": "ERROR",
        "message": f"Classic replay not found for game {pk}"
    }


# ── Statcast Savant Oracle & Jake Taylor Umpire Node Endpoints ─────────────────

class SavantQueryPayload(BaseModel):
    query: str


class UmpireArbitratePayload(BaseModel):
    query: str
    sport: Optional[str] = "auto"
    current_pitch: Optional[Dict[str, Any]] = None
    game_context: Optional[Dict[str, Any]] = None


@router.post("/api/savant_query")
@router.post("/api/fanstack/savant_query")
async def handle_savant_query(payload: SavantQueryPayload):
    """Execute Text-to-SQL over 807MB statcast_pitches database."""
    try:
        from core.statcast_savant_engine import process_savant_oracle
        result = await process_savant_oracle(payload.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Savant Oracle Error: {str(e)}")


@router.post("/api/umpire/arbitrate")
@router.post("/api/fanstack/umpire/arbitrate")
async def handle_umpire_arbitrate(payload: UmpireArbitratePayload):
    """Arbitrate controversial plays & pitch box coordinates via Jake Taylor Umpire Node."""
    try:
        from core.jake_taylor_engine import arbitrate_rule
        result = await arbitrate_rule(
            payload.query,
            sport=payload.sport or "auto",
            current_pitch=payload.current_pitch,
            game_context=payload.game_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jake Taylor Umpire Error: {str(e)}")


# ── WeedStack "Mean Gene" Guerilla Discourse Loop Endpoints ───────────────────

class WeedstackDiscoursePayload(BaseModel):
    room: Optional[str] = "823498"
    delay_override: Optional[float] = 0.1


@router.post("/api/discourse/trigger_weedstack_loop")
@router.post("/api/sports/discourse/trigger_weedstack_loop")
async def trigger_weedstack_discourse_loop(payload: WeedstackDiscoursePayload):
    """Trigger the 4-step wrestling heel-and-face guerilla discourse loop."""
    try:
        from core.weedstack_guerilla_engine import execute_weedstack_guerilla_discourse
        res = await execute_weedstack_guerilla_discourse(room_id=payload.room, delay_override=payload.delay_override)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WeedStack Discourse Loop Error: {str(e)}")


# ── Room Chat Purge Endpoint ──────────────────────────────────────────────────

@router.post("/api/chat/rooms/{game_pk}/purge")
@router.post("/api/sports/chat/rooms/{game_pk}/purge")
async def purge_room_chat_endpoint(game_pk: str):
    """Purge chat messages for a specific room across database and memory buffers, and notify clients."""
    pk_str = str(game_pk)
    purged_count = 0
    try:
        with get_db() as conn:
            cur1 = conn.execute("DELETE FROM game_chat WHERE game_pk = ?", (pk_str,))
            cur2 = conn.execute("DELETE FROM m2m_persona_room_ledger WHERE game_pk = ?", (pk_str,))
            purged_count = cur1.rowcount + cur2.rowcount
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database chat purge failed: {str(e)}")

    # Notify fanstack_relay on Port 8000 to clear in-memory buffer and broadcast WS event
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"http://127.0.0.1:8000/api/chat/rooms/{pk_str}/purge")
    except Exception:
        pass

    return {"status": "success", "game_pk": pk_str, "purged_count": purged_count}


# ── On-Demand Football Watch Room Deployment & Seating (WO0010093) ────────────

class FootballRoomDeployPayload(BaseModel):
    game_pk: str
    sport: Optional[str] = "cfb"
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    team_home: Optional[str] = None
    team_away: Optional[str] = None


class FootballChatMessagePayload(BaseModel):
    persona: Optional[str] = "@pilot"
    user: Optional[str] = None
    text: str
    msg_type: Optional[str] = "user"
    team: Optional[str] = "COMMAND"
    color: Optional[str] = "#00F0FF"



CFB_DEFAULT_ADVOCATES = {
    "TENN": [
        {
            "user_name": "smokey_sam",
            "display_name": "Smokey Sam",
            "team": "TENN",
            "color": "#FF8200",
            "system_prompt": "You are Smokey Sam, an uncompromising Tennessee Volunteers fan from Knoxville. You bleed orange and white, sing 'Rocky Top' after every first down, and celebrate Neyland Stadium checkerboards.",
            "canned_takes": json.dumps(["ROCKY TOP YOU'LL ALWAYS BE HOME SWEET HOME TO ME! 🍊", "Neyland was shaking at 115 decibels when that ball was snapped!", "Give him six! That deep ball was pure Tennessee magic."]),
            "role": "Volunteers Advocate"
        },
        {
            "user_name": "vol_vance",
            "display_name": "Volunteer Vance",
            "team": "TENN",
            "color": "#FFA347",
            "system_prompt": "You are Volunteer Vance, a tailgating legend from G10 parking garage. You know every SEC defensive scheme and believe Tennessee's tempo offense cannot be stopped.",
            "canned_takes": json.dumps(["Tempo! They can't even substitute! Run it again!", "That offensive line pushed their front four all the way back to Atlanta!", "Vols by fitty! Let's go!"]),
            "role": "Neyland Tailgater"
        },
        {
            "user_name": "peyton_disciple",
            "display_name": "Peyton Disciple",
            "team": "TENN",
            "color": "#E65100",
            "system_prompt": "You are Peyton Disciple, a quarterback purist who watches every replay for audibles, pocket protection, and back-shoulder boundary fades.",
            "canned_takes": json.dumps(["Check with me at the line... perfect read against cover 3!", "Notice the protection slide picking up the boundary corner blitz. Masterclass.", "Touchdown Tennessee! You love to see it!"]),
            "role": "Pass Pro Purist"
        }
    ],
    "GT": [
        {
            "user_name": "ramblin_ray",
            "display_name": "Ramblin' Ray",
            "team": "GT",
            "color": "#B3A369",
            "system_prompt": "You are Ramblin' Ray, a Georgia Tech mechanical engineering graduate. You analyze football with mathematical precision, calculating EPA per play and edge leverage.",
            "canned_takes": json.dumps(["Efficiency rating through the roof! The geometry on that counter trey was textbook.", "To Hell With Georgia, and today we sting the Vols!", "That triple-threat RPO created a 3-on-2 numbers advantage in the boundary."]),
            "role": "Yellow Jackets Engineer"
        },
        {
            "user_name": "buzz_bennett",
            "display_name": "Buzz Bennett",
            "team": "GT",
            "color": "#EAAA00",
            "system_prompt": "You are Buzz Bennett, an electrifying Yellow Jackets superfan with the gold stinger hat. You lead the Wreck parade and bring the noise to Bobby Dodd Stadium.",
            "canned_takes": json.dumps(["STING 'EM JACKETS! 🐝💛", "Bobby Dodd is rocking! The Wreck is revving on the sideline!", "Down goes the ranked SEC squad! Atlanta is Gold and White tonight!"]),
            "role": "Stinger Superfan"
        },
        {
            "user_name": "stinger_sarah",
            "display_name": "Stinger Sarah",
            "team": "GT",
            "color": "#003057",
            "system_prompt": "You are Stinger Sarah, fourth-generation North Avenue faithful. You live for 4th-down red zone stands and hard-hitting defensive line containment.",
            "canned_takes": json.dumps(["TURNOVER ON DOWNS! Defense held the line right at the goal line!", "That pass rush from the edge is relentless today!", "Up with the White and Gold! Keep the pressure on!"]),
            "role": "Bobby Dodd Defender"
        }
    ]
}


@router.post("/api/sports/football/deploy_room")
async def deploy_football_watch_room(payload: FootballRoomDeployPayload):
    """Deploy on-demand watch room for a football game, dynamically seating authentic team advocates."""
    CFB_TEAM_ALIASES = {
        "ALA": "BAMA", "ALABAMA": "BAMA",
        "GEORGIA": "UGA",
        "OHIO STATE": "OSU", "OHIOST": "OSU",
        "TEXAS": "TEX",
        "OLE MISS": "MISS", "OLEMISS": "MISS",
        "OREGON": "ORE",
        "PENN STATE": "PSU", "PENNST": "PSU",
        "MISSOURI": "MIZ", "MIZZOU": "MIZ",
        "TENNESSEE": "TENN",
        "UTAH": "UTAH",
        "MIAMI": "MIA", "MIAMI (FL)": "MIA", "MIA-FL": "MIA",
        "USC": "USC", "SOUTHERN CAL": "USC",
        "OKLAHOMA": "OU",
        "OKLAHOMA STATE": "OKST", "OKLAST": "OKST",
        "KANSAS STATE": "KSU", "K-STATE": "KSU",
        "LSU": "LSU", "LOUISIANA STATE": "LSU",
        "MICHIGAN": "MICH",
        "NOTRE DAME": "ND", "NOTREDAME": "ND",
        "CLEMSON": "CLEM",
        "ARIZONA": "ARIZ",
        "IOWA STATE": "ISU",
        "LOUISVILLE": "LOU", "UL": "LOU",
        "NEBRASKA": "NEB",
        "TEXAS A&M": "TAMU", "TEXAS AM": "TAMU", "A&M": "TAMU",
        "WASHINGTON": "WASH",
        "GEORGIA TECH": "GT", "GATECH": "GT"
    }

    clean_away = re.sub(r'^[#0-9\s]+', '', (payload.away_team or payload.team_away or "TENN").strip().upper())
    clean_home = re.sub(r'^[#0-9\s]+', '', (payload.home_team or payload.team_home or "GT").strip().upper())
    clean_away = CFB_TEAM_ALIASES.get(clean_away, clean_away)
    clean_home = CFB_TEAM_ALIASES.get(clean_home, clean_home)
    pk_str = str(payload.game_pk)
    
    seated_list = []
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with get_db() as conn:
            # 1. Dynamically resolve away advocates from persona table
            away_rows = conn.execute(
                "SELECT user_name, display_name, team, color, cadence, system_prompt, canned_takes FROM persona WHERE UPPER(team) = ? AND (behavior_notes IS NULL OR behavior_notes NOT LIKE '%baseball%') LIMIT 3",
                (clean_away,)
            ).fetchall()
            if not away_rows:
                # Unranked or buy-game cupcake program: slot in generic cupcake advocates
                away_rows = conn.execute(
                    "SELECT user_name, display_name, team, color, cadence, system_prompt, canned_takes FROM persona WHERE UPPER(team) = 'GENERIC_CUPCAKE' LIMIT 3"
                ).fetchall()

            # 2. Dynamically resolve home advocates from persona table
            home_rows = conn.execute(
                "SELECT user_name, display_name, team, color, cadence, system_prompt, canned_takes FROM persona WHERE UPPER(team) = ? AND (behavior_notes IS NULL OR behavior_notes NOT LIKE '%baseball%') LIMIT 3",
                (clean_home,)
            ).fetchall()
            if not home_rows:
                # Unranked or buy-game cupcake program: slot in generic cupcake advocates
                home_rows = conn.execute(
                    "SELECT user_name, display_name, team, color, cadence, system_prompt, canned_takes FROM persona WHERE UPPER(team) = 'GENERIC_CUPCAKE' LIMIT 3"
                ).fetchall()

            # Combine and deduplicate
            all_rows = list(away_rows) + list(home_rows)
            seen_unames = set()
            unique_advocates = []
            for r in all_rows:
                uname = r["user_name"]
                if uname and uname not in seen_unames:
                    seen_unames.add(uname)
                    unique_advocates.append(dict(r))

            # 3. Seat personas into m2m_persona_room for pk_str and cfb_pk_str
            for adv in unique_advocates:
                uname = adv["user_name"]
                for room_key in (pk_str, f"cfb_{pk_str}"):
                    sys_id = f"m2m_{uname}_{room_key}"
                    conn.execute("""
                        INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sys_id) DO UPDATE SET
                            sys_updated_on = excluded.sys_updated_on
                    """, (sys_id, uname, room_key, f"Active game room {room_key} advocate for {adv['team']}", now_iso, now_iso))

                seated_list.append({
                    "handle": f"@{uname}",
                    "name": adv["display_name"],
                    "team": adv["team"],
                    "role": f"{adv['team']} {adv.get('cadence', 'Advocate').capitalize()}",
                    "color": adv.get("color") or "#00b4d8"
                })

            # 4. Seed initial banter if room chat is empty
            chat_count = conn.execute("SELECT COUNT(*) as cnt FROM game_chat WHERE game_pk = ? OR game_pk = ?", (pk_str, f"cfb_{pk_str}")).fetchone()
            if not chat_count or chat_count["cnt"] == 0:
                initial_banter = []
                # Pick up to 2 takes from away advocates and 2 from home advocates
                for adv in unique_advocates[:4]:
                    takes = []
                    raw_takes = adv.get("canned_takes")
                    if raw_takes:
                        try:
                            takes = json.loads(raw_takes) if isinstance(raw_takes, str) else raw_takes
                        except Exception:
                            pass
                    text = takes[0] if takes else f"Gameday locked in for {adv['team']}! Let's get this victory!"
                    initial_banter.append((pk_str, f"@{adv['user_name']}", text, "cfb_advocate", now_iso))

                for g_pk, sender, msg, m_type, ts in initial_banter:
                    conn.execute("""
                        INSERT INTO game_chat (game_pk, persona, text, msg_type, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (g_pk, sender, msg, m_type, ts))

            conn.commit()

        return {
            "status": "success",
            "game_pk": pk_str,
            "room_state": "active",
            "advocate_count": len(seated_list),
            "advocates": seated_list,
            "message": f"Watch room deployed successfully with {len(seated_list)} seated advocates."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deploy football watch room: {str(e)}")


@router.get("/api/sports/football/room_status/{game_pk}")
async def get_football_room_status(game_pk: str):
    """Retrieve the deployment status and seated advocates for a football game watch room."""
    pk_str = str(game_pk)
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT DISTINCT m.persona, p.display_name, p.team, p.color
                FROM m2m_persona_room m
                LEFT JOIN persona p ON (p.user_name = m.persona OR p.id = m.persona)
                WHERE m.room = ? OR m.room = ?
            """, (pk_str, f"cfb_{pk_str}")).fetchall()

            advocates = []
            for r in rows:
                uname = r["persona"]
                advocates.append({
                    "handle": f"@{uname}" if not uname.startswith("@") else uname,
                    "name": r["display_name"] or uname,
                    "team": r["team"] or "NCAA",
                    "color": r["color"] or "#00B4D8"
                })

            is_active = len(advocates) > 0
            return {
                "game_pk": pk_str,
                "room_state": "active" if is_active else "dormant",
                "advocate_count": len(advocates),
                "advocates": advocates
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch room status: {str(e)}")


@router.get("/api/sports/football/chat/{game_pk}")
async def get_football_game_chat(game_pk: str):
    """Retrieve chat message history for a football game watch room."""
    pk_str = str(game_pk)
    try:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT gc.id, gc.game_pk, gc.persona, gc.text, gc.msg_type, gc.created_at,
                       COALESCE(p.team, 'NCAA') as team,
                       COALESCE(p.color, '#00b4d8') as color
                FROM game_chat gc
                LEFT JOIN persona p ON (
                    p.user_name = replace(gc.persona, '@', '')
                    OR p.id = replace(gc.persona, '@', '')
                )
                WHERE gc.game_pk = ? OR gc.game_pk = ?
                ORDER BY gc.id ASC
            """, (pk_str, f"cfb_{pk_str}")).fetchall()

            messages = []
            for r in rows:
                messages.append({
                    "id": r["id"],
                    "game_pk": r["game_pk"],
                    "persona": r["persona"],
                    "user": r["persona"],
                    "text": r["text"],
                    "msg_type": r["msg_type"],
                    "team": r["team"],
                    "color": r["color"],
                    "created_at": r["created_at"],
                    "timestamp": r["created_at"]
                })
            return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch game chat: {str(e)}")


@router.post("/api/sports/football/chat/{game_pk}")
async def post_football_game_chat(game_pk: str, payload: FootballChatMessagePayload):
    """Post a chat message to a football game watch room."""
    pk_str = str(game_pk)
    sender = payload.persona or payload.user or "@pilot"
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO game_chat (game_pk, persona, text, msg_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (pk_str, sender, payload.text, payload.msg_type or "user", now_iso))
            conn.commit()
            new_id = cur.lastrowid
            return {
                "status": "success",
                "id": new_id,
                "game_pk": pk_str,
                "persona": sender,
                "user": sender,
                "text": payload.text,
                "msg_type": payload.msg_type or "user",
                "created_at": now_iso
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to post game chat: {str(e)}")


# ==============================================================================
# IN-BREAK ENTERTAINMENT SUITE ENDPOINTS (WO0010106)
# ==============================================================================

@router.get("/api/fanstack/infill_playlist")
async def get_fanstack_infill_playlist(sport: str = "MLB", break_type: str = "COMMERCIAL"):
    """
    Return curated adaptive infill media items (parody ads, advocate takes, tributes).
    """
    playlist = [
        {
            "id": "infill_bent_carrot",
            "title": "The Bent Carrot Clinic",
            "subtitle": "Leading corrective urology & broadcast curvature specialists since 1986",
            "src": "/videos/parodies/bent_carrot_ad.mp4",
            "durationSec": 30,
            "durationLabel": "0:30",
            "category": "PARODY_AD",
            "badge": "🥕 SPONSOR SPOTLIGHT"
        },
        {
            "id": "infill_gonzas_cantina",
            "title": "Gonza's Postgame Cantina & Taqueria",
            "subtitle": "Where victory tastes like smoked carnitas and defeat is washed down with mezcal",
            "src": "/videos/parodies/gonzas_cantina_ad.mp4",
            "durationSec": 30,
            "durationLabel": "0:30",
            "category": "PARODY_AD",
            "badge": "🌮 LOCAL FLAVOR"
        },
        {
            "id": "infill_weedstack_wildseed",
            "title": "WeedStack Botanical Dispensary // WildSeed Pre-Rolls",
            "subtitle": "Precision organic phytocannabinoids cultivated for extra-inning anxiety",
            "src": "/videos/parodies/weedstack_wildseed_ad.mp4",
            "durationSec": 30,
            "durationLabel": "0:30",
            "category": "PARODY_AD",
            "badge": "🌿 DISPENSARY DROP"
        },
        {
            "id": "infill_barf_rant",
            "title": "Barf's 9th-Inning Bullpen Meltdown",
            "subtitle": "Unfiltered rage and existential despair over blown slider execution",
            "src": "/videos/advocate_takes/barf_bullpen_meltdown.mp4",
            "durationSec": 45,
            "durationLabel": "0:45",
            "category": "ADVOCATE_RANT",
            "badge": "🎙️ ADVOCATE TAKE"
        },
        {
            "id": "infill_first_responders",
            "title": "First Responders on Field — September 2001",
            "subtitle": "Ceremony honoring FDNY, NYPD, and PAPD heroes on the field at Shea Stadium",
            "src": "/videos/tributes/first_responders_baseball.mp4",
            "durationSec": 24,
            "durationLabel": "0:24",
            "category": "HISTORICAL_TRIBUTE",
            "badge": "🗽 HEROES ON FIELD"
        },
        {
            "id": "infill_fireboat_spray",
            "title": "FDNY Fireboat Hudson River Water Salute",
            "subtitle": "Patriotic red, white & blue water cannons against the Manhattan skyline",
            "src": "/videos/tributes/fireboat_water_spray.mp4",
            "durationSec": 22,
            "durationLabel": "0:22",
            "category": "HISTORICAL_TRIBUTE",
            "badge": "🌊 WATER SALUTE"
        }
    ]

    return {
        "status": "success",
        "sport": sport.upper(),
        "break_type": break_type.upper(),
        "count": len(playlist),
        "playlist": playlist
    }


@router.get("/api/fanstack/trivia")
async def get_fanstack_trivia(sport: str = "MLB", matchup: Optional[str] = None):
    """
    Return a 3-question rapid-fire matchup trivia set with loyalty rewards.
    """
    sport_upper = sport.upper()
    if "CFB" in sport_upper or "NCAA" in sport_upper or "FOOTBALL" in sport_upper:
        questions = [
            {
                "id": "cfb_triv_1",
                "question": "Which historic college football coach coined the famous 'Win One for the Gipper' halftime speech?",
                "choices": ["Knute Rockne (Notre Dame)", "Bear Bryant (Alabama)", "Woody Hayes (Ohio State)", "Bobby Bowden (FSU)"],
                "correctIndex": 0,
                "rewardPoints": 250,
                "loreExplanation": "Knute Rockne delivered the iconic speech to the Fighting Irish in 1928, inspiring their legendary victory over Army."
            },
            {
                "id": "cfb_triv_2",
                "question": "What is the oldest rivalry game in NCAA Division I FBS College Football history?",
                "choices": ["The Game (Michigan vs. Ohio State)", "The Rivalry (Lehigh vs. Lafayette)", "Paul Bunyan's Axe (Minnesota vs. Wisconsin)", "The Iron Bowl (Auburn vs. Alabama)"],
                "correctIndex": 2,
                "rewardPoints": 250,
                "loreExplanation": "Minnesota and Wisconsin have met continuously since 1890, playing over 130 times for Paul Bunyan's Axe."
            },
            {
                "id": "cfb_triv_3",
                "question": "Which team won the inaugural 4-team College Football Playoff National Championship in 2014-15?",
                "choices": ["Alabama Crimson Tide", "Oregon Ducks", "Ohio State Buckeyes", "Clemson Tigers"],
                "correctIndex": 2,
                "rewardPoints": 250,
                "loreExplanation": "Ohio State, led by 3rd-string QB Cardale Jones and Ezekiel Elliott, won the first CFP National Championship."
            }
        ]
    else:
        questions = [
            {
                "id": "mlb_triv_1",
                "question": "Who scored the winning run in the bottom of the 10th inning of Game 6 of the 1986 World Series at Shea Stadium?",
                "choices": ["Keith Hernandez", "Gary Carter", "Mookie Wilson", "Ray Knight"],
                "correctIndex": 3,
                "rewardPoints": 250,
                "loreExplanation": "Ray Knight rounded third and stamped on home plate as Bob Stanley's wild pitch and Bill Buckner's error completed the miracle comeback."
            },
            {
                "id": "mlb_triv_2",
                "question": "What was the official capacity of Shea Stadium during its final season in 2008?",
                "choices": ["45,100", "57,333", "62,100", "51,200"],
                "correctIndex": 1,
                "rewardPoints": 250,
                "loreExplanation": "Shea Stadium officially held 57,333 fans, shaking violently whenever jets from LaGuardia flew overhead."
            },
            {
                "id": "mlb_triv_3",
                "question": "Which Mets pitcher struck out 19 batters in a single game in 1970, including 10 consecutive to finish the game?",
                "choices": ["Dwight Gooden", "Tom Seaver", "Jerry Koosman", "Tug McGraw"],
                "correctIndex": 1,
                "rewardPoints": 250,
                "loreExplanation": "'Tom Terrific' struck out 19 San Diego Padres on April 22, 1970, fanning the final 10 batters in an untouchable masterclass."
            }
        ]

    return {
        "status": "success",
        "sport": sport_upper,
        "matchup": matchup or "LIVE_SLATE",
        "questions": questions
    }


# ── Shea Stadium Zork Sub-Level 3 Engine ──────────────────────────────────────

class ZorkCommandRequest(BaseModel):
    user_id: str
    match_id: Optional[str] = "823584"
    command: str

ZORK_ROOMS = {
    "maintenance_concourse": {
        "title": "Shea Stadium Sub-Level 3: Maintenance Concourse",
        "desc": "Cracked linoleum floors, flickering fluorescent tubes humming at 60Hz, and exposed conduits dripping lukewarm water. To the NORTH is a battered steel service door marked 'OLIDAY INN - STAFF ONLY'. To the EAST lies the visiting bullpen storage corridor.",
        "exits": {"north": "oliday_inn_passage", "east": "visiting_bullpen_storage"},
        "items": ["rusty wire hanger"]
    },
    "oliday_inn_passage": {
        "title": "The Oliday Inn Secret Laundry Tunnel",
        "desc": "A narrow, musty subterranean corridor that connects the visiting team hotel laundry basement directly to the dugout. A vintage laundry cart sits abandoned. To the WEST is a heavy reinforced steel vault with a sealed keycard and grease lock inscribed '1986 POSTSEASON SHRINE'. To the SOUTH is the maintenance concourse.",
        "exits": {"south": "maintenance_concourse", "west": "postseason_shrine_1986"},
        "items": ["pastrami on rye"]
    },
    "visiting_bullpen_storage": {
        "title": "Visiting Bullpen Equipment Storage",
        "desc": "Rusted equipment cages filled with broken batting tees, discarded rosin bags, and an electric golf-cart bullpen buggy with disconnected ignition wiring. To the WEST is the maintenance concourse.",
        "exits": {"west": "maintenance_concourse"},
        "items": ["jug of underground riot punch", "shea yellow paint scrape"]
    },
    "postseason_shrine_1986": {
        "title": "The 1986 Postseason Champions Inner Sanctum",
        "desc": "A secret celebration sanctuary preserved in amber since October 27, 1986. Empty champagne bottles, confetti from the Canyon of Heroes, and a velvet display case glowing beneath vintage stadium floodlights. To the EAST is the laundry passage.",
        "exits": {"east": "oliday_inn_passage"},
        "items": ["keith 1986 mustache comb", "1986 asbestos seat cushion"]
    }
}

CANONICAL_RELIC_MAP = {
    "keith 1986 mustache comb": {
        "id": "loot_keith_comb_gold",
        "name": "Keith Hernandez's 1986 Mustache Comb (Gold-Plated)",
        "category": "RELIC",
        "rarity": "LEGENDARY",
        "icon": "🪮",
        "stats": {"Clutch Multiplier": "+15%", "9th Inning Edge": "+25%", "Charisma": "MAX"},
        "lore": "Gold-plated pocket comb recovered from Keith's locker in the 1986 Postseason Champions Inner Sanctum.",
        "accolade_title": "Master of Shea Sub-Level 3",
        "accolade_desc": "Solved the secret laundry tunnel riddle and recovered Keith's 1986 Postseason Comb."
    },
    "shea yellow paint scrape": {
        "id": "loot_shea_paint_scrape",
        "name": "Shea Stadium Foul Pole Yellow Paint Scrape",
        "category": "RELIC",
        "rarity": "RARE",
        "icon": "🟡",
        "stats": {"Organ Soundboard": "UNLOCKED", "Fair/Foul Edge": "+10%"},
        "lore": "Authentic yellow paint scrape from the right-field foul pole at Shea Stadium.",
        "accolade_title": "Ballpark Archaeologist",
        "accolade_desc": "Recovered historical paint scrapes from Shea Stadium Sub-Level 3."
    },
    "jug of underground riot punch": {
        "id": "loot_underground_riot_punch",
        "name": "Jug of Underground Riot Punch",
        "category": "CONSUMABLE",
        "rarity": "UNCOMMON",
        "icon": "🧃",
        "stats": {"Terminal Phosphor": "NEON GREEN", "Banter Velocity": "+50%"},
        "lore": "Secret concoction brewed by visiting bullpen relievers during rain delays in 1986.",
        "accolade_title": "Concourse Survivor",
        "accolade_desc": "Surfaced from Shea's bowels holding a vintage jug of riot punch."
    },
    "1986 asbestos seat cushion": {
        "id": "loot_1986_seat_cushion",
        "name": "1986 Commemorative Asbestos Seat Cushion",
        "category": "RELIC",
        "rarity": "EPIC",
        "icon": "🛋️",
        "stats": {"Bullpen Insurance": "1-TIME BAILOUT", "Durability": "INVULNERABLE"},
        "lore": "Durable stadium seat cushion hurled onto the field during the 1986 Game 6 tenth-inning rally.",
        "accolade_title": "Game 6 Miracle Witness",
        "accolade_desc": "Unearthed an indestructible 1986 seat cushion beneath Shea's concourse."
    }
}


@router.post("/api/fanstack/zork/command")
async def execute_zork_command(payload: ZorkCommandRequest):
    """
    Execute a natural-language text adventure command in Shea Stadium Sub-Level 3.
    Persists session state and mints generative relics upon solving puzzles.
    """
    u_id = payload.user_id.lower().strip()
    m_id = str(payload.match_id or "823584")
    cmd_raw = payload.command.strip()
    cmd = cmd_raw.lower()

    with get_db() as conn:
        # Load or initialize session
        row = conn.execute(
            "SELECT sys_id, current_room, inventory_json, visited_rooms_json, turns_count, solved_puzzles_json, relics_minted_json, terminal_history_json FROM fanstack_zork_session WHERE user_id = ? AND match_id = ?",
            (u_id, m_id)
        ).fetchone()

        if not row:
            session_id = f"zork_{uuid.uuid4().hex[:8]}"
            curr_room = "maintenance_concourse"
            inventory = []
            visited = ["maintenance_concourse"]
            turns = 0
            solved = []
            relics_minted = []
            history = [f"> [SESSION INITIALIZED] You step into Shea Stadium Sub-Level 3. Type 'LOOK' or 'HELP'."]
            conn.execute(
                """INSERT INTO fanstack_zork_session 
                (sys_id, session_id, user_id, match_id, current_room, inventory_json, visited_rooms_json, turns_count, solved_puzzles_json, relics_minted_json, terminal_history_json) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, session_id, u_id, m_id, curr_room, json.dumps(inventory), json.dumps(visited), turns, json.dumps(solved), json.dumps(relics_minted), json.dumps(history))
            )
            conn.commit()
        else:
            session_id = row["sys_id"]
            curr_room = row["current_room"]
            inventory = json.loads(row["inventory_json"] or "[]")
            visited = json.loads(row["visited_rooms_json"] or "[]")
            turns = row["turns_count"] + 1
            solved = json.loads(row["solved_puzzles_json"] or "[]")
            relics_minted = json.loads(row["relics_minted_json"] or "[]")
            history = json.loads(row["terminal_history_json"] or "[]")

        room_data = ZORK_ROOMS.get(curr_room, ZORK_ROOMS["maintenance_concourse"])
        output_lines = []
        newly_minted_relic = None

        # Command Parser
        if cmd in ("help", "?"):
            output_lines.append("COMMANDS: LOOK, INVENTORY, GO <NORTH|SOUTH|EAST|WEST>, TAKE <ITEM>, EXAMINE <ITEM>, USE <ITEM> ON <TARGET>")
            output_lines.append("Shortcuts: N, S, E, W, I, L")

        elif cmd in ("look", "l"):
            output_lines.append(f"=== {room_data['title']} ===")
            output_lines.append(room_data["desc"])
            # Visible items not yet taken
            avail_items = [it for it in room_data["items"] if it not in inventory]
            if avail_items:
                output_lines.append(f"You see here: {', '.join([it.upper() for it in avail_items])}.")
            output_lines.append(f"Obvious exits: {', '.join([k.upper() for k in room_data['exits'].keys()])}.")

        elif cmd in ("inventory", "inv", "i"):
            if not inventory:
                output_lines.append("Your pockets are empty.")
            else:
                output_lines.append(f"You are carrying: {', '.join([it.upper() for it in inventory])}.")

        elif cmd in ("n", "north", "go north"):
            if "north" in room_data["exits"]:
                curr_room = room_data["exits"]["north"]
                if curr_room not in visited:
                    visited.append(curr_room)
                room_data = ZORK_ROOMS[curr_room]
                output_lines.append(f"You move North into {room_data['title']}.")
                output_lines.append(room_data["desc"])
            else:
                output_lines.append("You cannot go that way. A damp concrete wall blocks your path.")

        elif cmd in ("s", "south", "go south"):
            if "south" in room_data["exits"]:
                curr_room = room_data["exits"]["south"]
                if curr_room not in visited:
                    visited.append(curr_room)
                room_data = ZORK_ROOMS[curr_room]
                output_lines.append(f"You move South into {room_data['title']}.")
                output_lines.append(room_data["desc"])
            else:
                output_lines.append("You cannot go that way.")

        elif cmd in ("e", "east", "go east"):
            if "east" in room_data["exits"]:
                curr_room = room_data["exits"]["east"]
                if curr_room not in visited:
                    visited.append(curr_room)
                room_data = ZORK_ROOMS[curr_room]
                output_lines.append(f"You move East into {room_data['title']}.")
                output_lines.append(room_data["desc"])
            else:
                output_lines.append("You cannot go that way.")

        elif cmd in ("w", "west", "go west"):
            if curr_room == "oliday_inn_passage" and "unlocked_shrine" not in solved:
                output_lines.append("⛔ The heavy steel door to the 1986 Postseason Shrine is sealed with an archaic grease lock. It smells faintly of deli pastrami.")
            elif "west" in room_data["exits"]:
                curr_room = room_data["exits"]["west"]
                if curr_room not in visited:
                    visited.append(curr_room)
                room_data = ZORK_ROOMS[curr_room]
                output_lines.append(f"You move West into {room_data['title']}.")
                output_lines.append(room_data["desc"])
            else:
                output_lines.append("You cannot go that way.")

        elif cmd.startswith("take ") or cmd.startswith("get "):
            item_name = cmd.replace("take ", "").replace("get ", "").strip()
            # Match item loosely
            matched_item = None
            for it in room_data["items"]:
                if item_name in it or it in item_name:
                    matched_item = it
                    break
            
            if not matched_item:
                output_lines.append(f"There is no '{item_name}' here to take.")
            elif matched_item in inventory:
                output_lines.append(f"You already have the {matched_item.upper()} in your inventory.")
            else:
                inventory.append(matched_item)
                output_lines.append(f"Taken: {matched_item.upper()}.")

                # Check if this item is a mintable relic
                if matched_item in CANONICAL_RELIC_MAP and matched_item not in relics_minted:
                    relic_def = CANONICAL_RELIC_MAP[matched_item]
                    new_loot_sys_id = f"usr_loot_{uuid.uuid4().hex[:8]}"
                    new_acc_id = f"acc_{uuid.uuid4().hex[:8]}"

                    # Mint to dim_loot_item & sys_user_loot
                    conn.execute("""
                        INSERT OR IGNORE INTO dim_loot_item 
                        (item_id, name, category, rarity, stats_json, icon_emoji, image_url, lore_description, sport_origin, is_tradable)
                        VALUES (?, ?, ?, ?, ?, ?, '/media_vault/loot/default_relic.png', ?, 'MLB', 1)
                    """, (relic_def["id"], relic_def["name"], relic_def["category"], relic_def["rarity"], json.dumps(relic_def["stats"]), relic_def["icon"], relic_def["lore"]))

                    conn.execute("""
                        INSERT INTO sys_user_loot (sys_id, owner_id, owner_type, item_id, acquired_via, is_equipped_desk, is_equipped_ttrpg, wager_locked)
                        VALUES (?, ?, 'HUMAN', ?, 'SHEA_ZORK_SUBLEVEL_3', 0, 0, 0)
                    """, (new_loot_sys_id, u_id, relic_def["id"]))

                    # Award accolade
                    conn.execute("""
                        INSERT INTO sys_user_accolade (accolade_id, user_id, title, description, badge_icon, tier, event_context)
                        VALUES (?, ?, ?, ?, ?, 'GOLD', 'Shea Stadium Zork: Sub-Level 3 Quest')
                    """, (new_acc_id, u_id, relic_def["accolade_title"], relic_def["accolade_desc"], relic_def["icon"]))

                    relics_minted.append(matched_item)
                    newly_minted_relic = relic_def
                    output_lines.append(f"✨ [AUTHENTIC RELIC MINTED] '{relic_def['name']}' has been forged into your Pilot Dossier Loot Vault & Trophy Showcase!")

        elif cmd.startswith("examine ") or cmd.startswith("x "):
            target = cmd.replace("examine ", "").replace("x ", "").strip()
            if "hanger" in target or "wire" in target:
                output_lines.append("A sturdy metal coat hanger from the Shea Stadium umpire dressing room. You could probably bend it to hotwire or jimmy a lock.")
            elif "pastrami" in target or "sandwich" in target:
                output_lines.append("An extraordinarily preserved pastrami on rye wrapped in vintage tin foil. The legendary 1986 superstition fuel.")
            elif "cart" in target or "buggy" in target:
                output_lines.append("A classic electric bullpen golf cart with a giant baseball cap roof. The ignition cylinder is missing its key.")
            elif "door" in target or "lock" in target:
                output_lines.append("A reinforced steel blast door. The grease lock requires an organic lubricant or iconic deli offering to turn.")
            elif "comb" in target:
                output_lines.append("Keith Hernandez's legendary gold-plated mustache comb. It radiates pure defensive fundies and +15% clutch aura.")
            else:
                output_lines.append(f"You don't see anything unusual about the {target}.")

        elif "use" in cmd:
            if ("pastrami" in cmd or "sandwich" in cmd) and ("door" in cmd or "lock" in cmd or "shrine" in cmd):
                if "pastrami on rye" in inventory:
                    solved.append("unlocked_shrine")
                    output_lines.append("🔑 You slide the pastrami grease across the ancient mechanism! The tumblers click with a resonant THUD. The 1986 Postseason Shrine door swings open to the WEST!")
                else:
                    output_lines.append("You don't have pastrami in your inventory.")
            elif ("hanger" in cmd or "wire" in cmd) and ("cart" in cmd or "buggy" in cmd or "hotwire" in cmd):
                if "rusty wire hanger" in inventory:
                    solved.append("hotwired_cart")
                    output_lines.append("⚡ You bend the coat hanger and short the starter terminals! The bullpen cart engine COUGHS to life, vibrating violently and shaking a hidden yellow paint scrape and cold jug of riot punch loose from the chassis!")
                else:
                    output_lines.append("You don't have a wire hanger in your inventory.")
            else:
                output_lines.append("You can't use that in that way here.")

        else:
            output_lines.append(f"I don't understand '{cmd_raw}'. Type 'HELP' for navigation and action verbs.")

        # Record history
        turn_text = f"> {cmd_raw}\n" + "\n".join(output_lines)
        history.append(turn_text)
        if len(history) > 30:
            history = history[-30:]

        # Update DB
        conn.execute("""
            UPDATE fanstack_zork_session SET
                current_room = ?,
                inventory_json = ?,
                visited_rooms_json = ?,
                turns_count = ?,
                solved_puzzles_json = ?,
                relics_minted_json = ?,
                terminal_history_json = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE user_id = ? AND match_id = ?
        """, (curr_room, json.dumps(inventory), json.dumps(visited), turns, json.dumps(solved), json.dumps(relics_minted), json.dumps(history), u_id, m_id))
        conn.commit()

        return {
            "status": "success",
            "user_id": u_id,
            "match_id": m_id,
            "current_room": curr_room,
            "room_title": room_data["title"],
            "output": output_lines,
            "inventory": inventory,
            "visited_rooms": visited,
            "turns": turns,
            "new_relic": newly_minted_relic,
            "history": history
        }


@router.get("/api/fanstack/zork/session/{user_id}/{match_id}")
async def get_zork_session(user_id: str, match_id: str = "823584"):
    """Fetch current Zork terminal state and room coordinates."""
    u_id = user_id.lower().strip()
    m_id = str(match_id)
    with get_db() as conn:
        row = conn.execute(
            "SELECT current_room, inventory_json, visited_rooms_json, turns_count, solved_puzzles_json, relics_minted_json, terminal_history_json FROM fanstack_zork_session WHERE user_id = ? AND match_id = ?",
            (u_id, m_id)
        ).fetchone()

        if not row:
            # Trigger first look
            return await execute_zork_command(ZorkCommandRequest(user_id=u_id, match_id=m_id, command="LOOK"))

        room_key = row["current_room"]
        room_data = ZORK_ROOMS.get(room_key, ZORK_ROOMS["maintenance_concourse"])
        return {
            "status": "success",
            "user_id": u_id,
            "match_id": m_id,
            "current_room": room_key,
            "room_title": room_data["title"],
            "inventory": json.loads(row["inventory_json"] or "[]"),
            "visited_rooms": json.loads(row["visited_rooms_json"] or "[]"),
            "turns": row["turns_count"],
            "history": json.loads(row["terminal_history_json"] or "[]")
        }


# ── POST-GAME TELEMETRY RECONCILIATION & HARVESTER (ENHC2026082608) ──────────

@router.post("/api/sports/telemetry/reconcile/{game_pk}")
async def trigger_telemetry_reconciliation(game_pk: int):
    """Trigger on-demand post-game telemetry reconciliation for a specific MLB game."""
    try:
        from telemetry_reconciliation_harvester import reconcile_game
        result = reconcile_game(game_pk)
        return {
            "status": "success",
            "game_pk": game_pk,
            "reconciliation": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation error: {str(e)}")


@router.get("/api/sports/telemetry/reconciliations")
async def list_telemetry_reconciliations(limit: int = 50):
    """Retrieve historical post-game reconciliation records from the ledger."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT game_pk, game_date, home_team_id, away_team_id, status, 
                   discrepancy_count, discrepancy_breakdown, editorial_headline, 
                   editorial_blurb, reconciled_at
            FROM game_reconciliations
            ORDER BY reconciled_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        items = []
        for r in rows:
            d = dict(r)
            try:
                d["discrepancy_breakdown"] = json.loads(d.get("discrepancy_breakdown") or "[]")
            except Exception:
                d["discrepancy_breakdown"] = []
            items.append(d)
            
        return {
            "status": "success",
            "count": len(items),
            "reconciliations": items
        }


@router.get("/api/sports/telemetry/reconciliations/{game_pk}")
async def get_telemetry_reconciliation(game_pk: int):
    """Retrieve specific reconciliation details for a given game_pk."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT game_pk, game_date, home_team_id, away_team_id, status, 
                   discrepancy_count, discrepancy_breakdown, editorial_headline, 
                   editorial_blurb, reconciled_at
            FROM game_reconciliations
            WHERE game_pk = ?
            """,
            (game_pk,)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"No reconciliation record found for game_pk {game_pk}")
            
        d = dict(row)
        try:
            d["discrepancy_breakdown"] = json.loads(d.get("discrepancy_breakdown") or "[]")
        except Exception:
            d["discrepancy_breakdown"] = []
            
        return {
            "status": "success",
            "game_pk": game_pk,
            "reconciliation": d
        }


# ── Interactive Statcast Replay Studio Controller (WO0010154) ──────────────────

class SimState:
    def __init__(self):
        self.game_pk: str = "823574"
        self.feed_path: str = "/home/james/stacklabs/dna/cache/mlb_823574_feed.json"
        self.plays: list[dict] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.speed: float = 1.0
        self.prompt_overlay: str = (
            "### 2026 MLB TIMELINE & ROSTER GROUND TRUTH (MANDATORY FACTS) ###\n"
            "- CURRENT YEAR: 2026. This is NOT 2024 or 2025. Roster movements and off-season signings are real and permanent.\n"
            "- BALTIMORE ORIOLES (BAL): Pete Alonso plays first base for Baltimore wearing #20. Gunnar Henderson is the shortstop. Coby Mayo plays third base/DH.\n"
            "- NEW YORK METS (NYM): Juan Soto plays right field for the Mets. Francisco Lindor is shortstop. Bo Bichette and Marcus Semien are on the Mets. Kodai Senga is the starting/relief ace.\n"
            "- GAME SITUATION: Game 2 of 3 (BAL @ NYM, Sept 15, 2026, Citi Field).\n"
            "- TOP 9TH INNING: Kodai Senga is on the mound for the Mets. Pete Alonso hits a game-tying 2-run home run off Senga! Mets fans are in disbelief and heartbreak seeing their former slugger tie the game in the 9th at Citi Field wearing orange and black.\n"
            "- TOP 11TH INNING: Jonathan Pintaro is pitching for the Mets. Coby Mayo hits a 3-run inside-the-park home run! Mets bullpen implosion is complete.\n"
            "- CRITICAL: Never claim Pete Alonso plays for the Mets. Never claim Alonso homered off anyone other than Kodai Senga."
        )
        self.stream_task: Optional[asyncio.Task] = None
        self.teams: str = "BAL @ NYM"
        self.venue: str = "Citi Field"

sim_state = SimState()

async def _send_sim_ws(payload: dict):
    try:
        import websockets
        async with websockets.connect("ws://127.0.0.1:8008", ping_interval=None) as ws:
            await ws.send(json.dumps(payload))
    except Exception as e:
        print(f"[SIM WS RELAY WARNING] {e}")

def _parse_sim_play(game_pk: str, play: dict, is_final: bool = False) -> dict:
    about = play.get("about", {})
    inning = about.get("inning", 1)
    half = about.get("halfInning", "top")
    inning_label = f"{'Top' if str(half).lower() == 'top' else 'Bot'} {inning}"
    
    matchup = play.get("matchup", {})
    batter = matchup.get("batter", {}).get("fullName", "Batter")
    pitcher = matchup.get("pitcher", {}).get("fullName", "Pitcher")
    
    result = play.get("result", {})
    desc = result.get("description", "")
    event_type = result.get("event", "play")
    away_score = result.get("awayScore", 0)
    home_score = result.get("homeScore", 0)
    
    count = play.get("count", {})
    outs = count.get("outs", 0)
    balls = count.get("balls", 0)
    strikes = count.get("strikes", 0)
    
    play_events = play.get("playEvents", [])
    pitch_speed = "---"
    pitch_name = "---"
    hit_speed = None
    launch_angle = None
    hit_distance = None
    
    for pe in play_events:
        if pe.get("isPitch"):
            details = pe.get("pitchData", {})
            if details.get("startSpeed"):
                pitch_speed = str(details.get("startSpeed"))
            if pe.get("details", {}).get("type", {}).get("description"):
                pitch_name = pe.get("details", {}).get("type", {}).get("description")
        hit_data = pe.get("hitData", {})
        if hit_data:
            hit_speed = hit_data.get("launchSpeed")
            launch_angle = hit_data.get("launchAngle")
            hit_distance = hit_data.get("totalDistance")

    # Hardcoded Statcast ground truth telemetry for key plays
    at_bat_idx = about.get("atBatIndex")
    if at_bat_idx == 63 or "Pete Alonso homers" in desc:
        pitcher = "Kodai Senga"
        batter = "Pete Alonso"
        hit_speed = 107.4
        launch_angle = 35.0
        hit_distance = 412
    elif at_bat_idx == 83 or "Coby Mayo hits an inside-the-park home run" in desc:
        pitcher = "Jonathan Pintaro"
        batter = "Coby Mayo"
        hit_speed = 106.9
        launch_angle = 25.0
        hit_distance = 410

    runners = play.get("runners", [])
    runner_on_1b = any(r.get("movement", {}).get("start") == "1B" or r.get("movement", {}).get("end") == "1B" for r in runners)
    runner_on_2b = any(r.get("movement", {}).get("start") == "2B" or r.get("movement", {}).get("end") == "2B" for r in runners)
    runner_on_3b = any(r.get("movement", {}).get("start") == "3B" or r.get("movement", {}).get("end") == "3B" for r in runners)

    return {
        "game_pk": str(game_pk),
        "home_team": "NYM",
        "away_team": "BAL",
        "home_score": home_score,
        "away_score": away_score,
        "inning": inning_label,
        "half": half,
        "inning_num": inning,
        "outs": outs,
        "balls": balls,
        "strikes": strikes,
        "pitcher": pitcher,
        "batter": batter,
        "pitch_name": pitch_name,
        "pitch_speed": pitch_speed,
        "hit_speed": hit_speed,
        "launch_angle": launch_angle,
        "hit_distance": hit_distance,
        "runner_on_1b": runner_on_1b,
        "runner_on_2b": runner_on_2b,
        "runner_on_3b": runner_on_3b,
        "status_msg": desc,
        "event_type": event_type,
        "is_telemetry": True,
        "is_final": is_final
    }

async def _dispatch_sim_play(index: int):
    if 0 <= index < len(sim_state.plays):
        play_packet = sim_state.plays[index]
        telemetry_packet = {
            "type": "CMD_SYNC_STATE",
            "target_game_pk": sim_state.game_pk,
            "data": play_packet
        }
        await _send_sim_ws(telemetry_packet)
        
        desc = play_packet.get("status_msg", "")
        if "homers" in desc.lower() or "home run" in desc.lower():
            await _send_sim_ws({
                "type": "trigger_event",
                "event": "home_run",
                "target_game_pk": sim_state.game_pk
            })
            await _send_sim_ws({
                "type": "update_context",
                "text": f"HOME RUN ALERT: {desc}",
                "target_game_pk": sim_state.game_pk
            })

async def _sim_stream_loop():
    try:
        while sim_state.is_playing and sim_state.current_index < len(sim_state.plays):
            await _dispatch_sim_play(sim_state.current_index)
            sim_state.current_index += 1
            if sim_state.current_index >= len(sim_state.plays):
                sim_state.is_playing = False
                break
            delay = max(0.2, 3.0 / max(0.1, sim_state.speed))
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[SIM STREAM LOOP ERROR] {e}")
    finally:
        sim_state.is_playing = False

class SimLoadPayload(BaseModel):
    game_pk: str = "823574"
    feed_path: Optional[str] = None

class SimControlPayload(BaseModel):
    action: str  # "play", "pause", "step_next", "step_prev", "jump"
    index: Optional[int] = None
    speed: Optional[float] = None

class SimOverlayPayload(BaseModel):
    game_pk: str = "823574"
    prompt_overlay: str

@router.post("/api/sports/sim/load")
async def sim_load_endpoint(payload: SimLoadPayload):
    pk = str(payload.game_pk).strip() or "823574"
    fpath = payload.feed_path or f"/home/james/stacklabs/dna/cache/mlb_{pk}_feed.json"
    if not os.path.exists(fpath):
        fpath = "/home/james/stacklabs/dna/cache/mlb_823574_feed.json"
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Statcast feed file not found: {fpath}")

    with open(fpath, "r", encoding="utf-8") as f:
        feed = json.load(f)

    all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    parsed_plays = []
    for idx, p in enumerate(all_plays):
        is_final = (idx == len(all_plays) - 1)
        parsed_plays.append(_parse_sim_play(pk, p, is_final=is_final))

    sim_state.game_pk = pk
    sim_state.feed_path = fpath
    sim_state.plays = parsed_plays
    sim_state.current_index = 0
    sim_state.is_playing = False
    sim_state.speed = 1.0

    # Purge Pete Alonso NYM ghost trauma
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM cmdb_ci_ghost_roster WHERE player_name = 'Pete Alonso' AND trauma_team = 'NYM'")
            conn.commit()
    except Exception as e:
        print(f"[SIM LOAD] Ghost trauma purge warning: {e}")

    # Seed sport schedule for 823574
    try:
        await seed_sports_schedule({
            "game_pk": pk,
            "sport": "MLB",
            "home_team": "NYM",
            "away_team": "BAL",
            "home_team_name": "New York Mets",
            "away_team_name": "Baltimore Orioles",
            "game_date": "2026-09-15",
            "game_time": "7:10 PM",
            "venue": "Citi Field",
            "status": "In Progress",
            "room_state": "active",
            "boggs_level": 5,
            "home_score": 0,
            "away_score": 0
        })
    except Exception as e:
        print(f"[SIM LOAD] Schedule seed warning: {e}")

    # Seat Queens 4 and Baltimore 2
    seated_personas = ["barf", "7_train_terry", "UncleStevieStan", "keith_fanboy", "birdland_boomer", "dirty_water_danny"]
    try:
        await seat_room_personas(
            pk,
            {
                "personas": seated_personas,
                "prompt_overlay": sim_state.prompt_overlay,
                "clear_existing": True
            }
        )
    except Exception as e:
        print(f"[SIM LOAD] Persona seat warning: {e}")

    alonso_idx = 63 if len(parsed_plays) > 63 else 0
    mayo_idx = 83 if len(parsed_plays) > 83 else 0
    final_idx = len(parsed_plays) - 1 if parsed_plays else 0

    return {
        "status": "ok",
        "game_pk": pk,
        "total_plays": len(parsed_plays),
        "teams": "BAL @ NYM",
        "venue": "Citi Field",
        "current_index": 0,
        "is_playing": False,
        "speed": sim_state.speed,
        "prompt_overlay": sim_state.prompt_overlay,
        "bookmarks": {
            "alonso_hr": alonso_idx,
            "mayo_inside_park_hr": mayo_idx,
            "final_out": final_idx
        }
    }

@router.post("/api/sports/sim/control")
async def sim_control_endpoint(payload: SimControlPayload):
    action = payload.action.lower()
    if not sim_state.plays:
        await sim_load_endpoint(SimLoadPayload(game_pk=sim_state.game_pk))

    if payload.speed is not None and payload.speed > 0:
        sim_state.speed = payload.speed

    if action == "play":
        sim_state.is_playing = True
        if sim_state.stream_task and not sim_state.stream_task.done():
            sim_state.stream_task.cancel()
        sim_state.stream_task = asyncio.create_task(_sim_stream_loop())
        return {
            "status": "playing",
            "current_index": sim_state.current_index,
            "speed": sim_state.speed,
            "is_playing": True
        }
    elif action == "pause":
        sim_state.is_playing = False
        if sim_state.stream_task and not sim_state.stream_task.done():
            sim_state.stream_task.cancel()
            sim_state.stream_task = None
        return {
            "status": "paused",
            "current_index": sim_state.current_index,
            "speed": sim_state.speed,
            "is_playing": False
        }
    elif action in ("step_next", "step_prev", "jump"):
        sim_state.is_playing = False
        if sim_state.stream_task and not sim_state.stream_task.done():
            sim_state.stream_task.cancel()
            sim_state.stream_task = None

        if action == "step_next":
            sim_state.current_index = min(len(sim_state.plays) - 1, sim_state.current_index + 1)
        elif action == "step_prev":
            sim_state.current_index = max(0, sim_state.current_index - 1)
        elif action == "jump" and payload.index is not None:
            sim_state.current_index = max(0, min(len(sim_state.plays) - 1, payload.index))

        await _dispatch_sim_play(sim_state.current_index)
        play_data = sim_state.plays[sim_state.current_index] if sim_state.plays else {}
        return {
            "status": "stepped",
            "action": action,
            "current_index": sim_state.current_index,
            "is_playing": False,
            "play_data": play_data
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown sim action: {action}")

@router.get("/api/sports/sim/status")
async def sim_status_endpoint(game_pk: Optional[str] = "823574"):
    if not sim_state.plays:
        await sim_load_endpoint(SimLoadPayload(game_pk=game_pk or "823574"))

    play_data = sim_state.plays[sim_state.current_index] if (sim_state.plays and 0 <= sim_state.current_index < len(sim_state.plays)) else {}
    return {
        "game_pk": sim_state.game_pk,
        "current_index": sim_state.current_index,
        "total_plays": len(sim_state.plays),
        "is_playing": sim_state.is_playing,
        "speed": sim_state.speed,
        "play_data": play_data,
        "prompt_overlay": sim_state.prompt_overlay
    }

@router.post("/api/sports/sim/overlay")
async def sim_overlay_endpoint(payload: SimOverlayPayload):
    pk = str(payload.game_pk).strip() or "823574"
    overlay = payload.prompt_overlay.strip()
    sim_state.prompt_overlay = overlay
    
    with get_db() as conn:
        conn.execute("UPDATE m2m_persona_room SET prompt_overlay = ? WHERE room = ?", (overlay, pk))
        conn.commit()

    await _send_sim_ws({
        "type": "update_context",
        "target_game_pk": pk,
        "text": overlay
    })
    
    return {
        "status": "success",
        "game_pk": pk,
        "prompt_overlay": overlay
    }


# ── Advocate AI Chatter Policy & Room Matrix (WO0010184) ───────────────────────

class ChatPolicyUpdate(BaseModel):
    global_enabled: Optional[bool] = None
    leagues: Optional[Dict[str, bool]] = None  # e.g. {"NFL": True, "MLB": False, "CFB": False}
    room_policy: Optional[str] = None          # "all_active" or "whitelist"
    whitelisted_rooms: Optional[List[str]] = None


def _fetch_chat_policy_settings(conn) -> Dict[str, Any]:
    """Internal helper to load chat policy settings from sys_app_settings."""
    rows = conn.execute("""
        SELECT setting_key, setting_value FROM sys_app_settings
        WHERE setting_key IN (
            'chat.global_enabled',
            'chat.league.nfl',
            'chat.league.cfb',
            'chat.league.mlb',
            'chat.room_policy',
            'chat.whitelisted_rooms'
        )
    """).fetchall()
    settings = {r["setting_key"]: r["setting_value"] for r in rows}

    global_enabled = settings.get("chat.global_enabled", "true").lower() == "true"
    nfl_enabled = settings.get("chat.league.nfl", "true").lower() == "true"
    cfb_enabled = settings.get("chat.league.cfb", "true").lower() == "true"
    mlb_enabled = settings.get("chat.league.mlb", "true").lower() == "true"
    room_policy = settings.get("chat.room_policy", "all_active")

    whitelisted_rooms = []
    raw_whitelist = settings.get("chat.whitelisted_rooms", "[]")
    try:
        parsed = json.loads(raw_whitelist)
        if isinstance(parsed, list):
            whitelisted_rooms = [str(x) for x in parsed]
    except Exception:
        whitelisted_rooms = []

    return {
        "global_enabled": global_enabled,
        "leagues": {
            "NFL": nfl_enabled,
            "CFB": cfb_enabled,
            "MLB": mlb_enabled
        },
        "room_policy": room_policy,
        "whitelisted_rooms": whitelisted_rooms
    }


@router.get("/api/fanstack/chat_policy")
async def get_fanstack_chat_policy():
    """
    Retrieve current Advocate AI chatter policy across leagues and rooms.
    Includes active schedule rooms, persona counts, and effective chat active states.
    """
    with get_db() as conn:
        policy = _fetch_chat_policy_settings(conn)

        # Query active games from sport_schedule
        sched_rows = conn.execute("""
            SELECT game_pk, sport, game_date, game_time, home_team, away_team,
                   home_team_name, away_team_name, venue, status, room_state
            FROM sport_schedule
            WHERE room_state IN ('active', 'live', 'staged')
               OR game_date = CURRENT_DATE
            ORDER BY game_date DESC, game_time ASC
        """).fetchall()

        # Query persona counts per room
        persona_counts = {}
        try:
            p_rows = conn.execute("""
                SELECT room, COUNT(DISTINCT persona) as cnt 
                FROM m2m_persona_room 
                GROUP BY room
            """).fetchall()
            for pr in p_rows:
                persona_counts[str(pr["room"])] = pr["cnt"]
        except Exception as e:
            logger.warning("Error querying m2m_persona_room: %s", e)

        # In-memory presence cache fallback
        try:
            all_rosters = RoomRosterRegistry.get_all_rosters()
            for r_pk, r_list in all_rosters.items():
                if str(r_pk) not in persona_counts or persona_counts[str(r_pk)] == 0:
                    persona_counts[str(r_pk)] = len(r_list)
        except Exception:
            pass

        rooms = []
        seen_pks = set()
        stats = {
            "NFL": {"games": 0, "personas": 0},
            "MLB": {"games": 0, "personas": 0},
            "CFB": {"games": 0, "personas": 0}
        }

        for r in sched_rows:
            pk = str(r["game_pk"]).strip()
            if pk in seen_pks:
                continue
            seen_pks.add(pk)

            raw_sport = (r["sport"] or "MLB").strip().upper()
            sport = raw_sport if raw_sport in ("NFL", "CFB", "MLB") else ("NFL" if "nfl" in pk.lower() else ("CFB" if "cfb" in pk.lower() else "MLB"))

            p_count = persona_counts.get(pk, 0)
            if sport in stats:
                stats[sport]["games"] += 1
                stats[sport]["personas"] += p_count
            else:
                stats[sport] = {"games": 1, "personas": p_count}

            league_allowed = policy["leagues"].get(sport, True)
            room_allowed = True if policy["room_policy"] == "all_active" else (pk in policy["whitelisted_rooms"])
            chat_active = bool(policy["global_enabled"] and league_allowed and room_allowed)

            away_str = r["away_team_name"] or r["away_team"] or "Away"
            home_str = r["home_team_name"] or r["home_team"] or "Home"
            matchup = f"{away_str} @ {home_str}"

            rooms.append({
                "game_pk": pk,
                "sport": sport,
                "home_team": r["home_team"] or "",
                "away_team": r["away_team"] or "",
                "home_team_name": r["home_team_name"] or "",
                "away_team_name": r["away_team_name"] or "",
                "matchup": matchup,
                "venue": r["venue"] or "",
                "game_date": r["game_date"] or "",
                "game_time": r["game_time"] or "",
                "status": r["status"] or "Scheduled",
                "room_state": r["room_state"] or "staged",
                "persona_count": p_count,
                "chat_active": chat_active
            })

        # Also inspect cmdb_ci_fanstack_room for any active rooms not in sport_schedule
        try:
            cmdb_rows = conn.execute("""
                SELECT game_pk, name, room_state, sport 
                FROM cmdb_ci_fanstack_room 
                WHERE room_state IN ('active', 'live', 'staged')
            """).fetchall()
            for cr in cmdb_rows:
                pk = str(cr["game_pk"]).strip()
                if pk and pk not in seen_pks:
                    seen_pks.add(pk)
                    raw_sp = (cr["sport"] if "sport" in cr.keys() and cr["sport"] else "").upper()
                    sport = raw_sp if raw_sp in ("NFL", "CFB", "MLB") else ("NFL" if "nfl" in pk.lower() else ("CFB" if "cfb" in pk.lower() else "MLB"))
                    p_count = persona_counts.get(pk, 0)
                    if sport in stats:
                        stats[sport]["games"] += 1
                        stats[sport]["personas"] += p_count
                    else:
                        stats[sport] = {"games": 1, "personas": p_count}
                    league_allowed = policy["leagues"].get(sport, True)
                    room_allowed = True if policy["room_policy"] == "all_active" else (pk in policy["whitelisted_rooms"])
                    chat_active = bool(policy["global_enabled"] and league_allowed and room_allowed)
                    rooms.append({
                        "game_pk": pk,
                        "sport": sport,
                        "home_team": "",
                        "away_team": "",
                        "home_team_name": "",
                        "away_team_name": "",
                        "matchup": cr["name"] or pk,
                        "venue": "",
                        "game_date": "",
                        "game_time": "",
                        "status": "Active Room",
                        "room_state": cr["room_state"] or "active",
                        "persona_count": p_count,
                        "chat_active": chat_active
                    })
        except Exception as e:
            logger.warning("Error querying cmdb_ci_fanstack_room: %s", e)

        active_rooms_count = sum(1 for rm in rooms if rm["chat_active"])

        return {
            "status": "success",
            "global_enabled": policy["global_enabled"],
            "leagues": policy["leagues"],
            "room_policy": policy["room_policy"],
            "whitelisted_rooms": policy["whitelisted_rooms"],
            "rooms": rooms,
            "stats": stats,
            "active_rooms_count": active_rooms_count,
            "total_rooms_count": len(rooms)
        }


@router.put("/api/fanstack/chat_policy")
async def update_fanstack_chat_policy(payload: ChatPolicyUpdate):
    """
    Update Advocate AI chatter policy and broadcast CHAT_POLICY_UPDATED WebSocket event.
    """
    with get_db() as conn:
        if payload.global_enabled is not None:
            val = "true" if payload.global_enabled else "false"
            conn.execute("""
                INSERT INTO sys_app_settings (sys_id, setting_key, setting_value, setting_category, description, updated_by, updated_at)
                VALUES ('setting_chat_global_enabled', 'chat.global_enabled', ?, 'fanstack', 'Global AI Advocate chat switch', 'pilot', CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_by = 'pilot',
                    updated_at = CURRENT_TIMESTAMP
            """, (val,))

        if payload.leagues is not None:
            for sport_name, is_enabled in payload.leagues.items():
                s_key = f"chat.league.{sport_name.strip().lower()}"
                val = "true" if is_enabled else "false"
                sys_id = f"setting_{s_key.replace('.', '_')}"
                conn.execute("""
                    INSERT INTO sys_app_settings (sys_id, setting_key, setting_value, setting_category, description, updated_by, updated_at)
                    VALUES (?, ?, ?, 'fanstack', ?, 'pilot', CURRENT_TIMESTAMP)
                    ON CONFLICT(setting_key) DO UPDATE SET
                        setting_value = excluded.setting_value,
                        updated_by = 'pilot',
                        updated_at = CURRENT_TIMESTAMP
                """, (sys_id, s_key, val, f"{sport_name.upper()} Advocate chat switch"))

        if payload.room_policy is not None:
            policy_val = "whitelist" if payload.room_policy == "whitelist" else "all_active"
            conn.execute("""
                INSERT INTO sys_app_settings (sys_id, setting_key, setting_value, setting_category, description, updated_by, updated_at)
                VALUES ('setting_chat_room_policy', 'chat.room_policy', ?, 'fanstack', 'Scope policy for advocate chatter', 'pilot', CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_by = 'pilot',
                    updated_at = CURRENT_TIMESTAMP
            """, (policy_val,))

        if payload.whitelisted_rooms is not None:
            clean_list = [str(x) for x in payload.whitelisted_rooms]
            val = json.dumps(clean_list)
            conn.execute("""
                INSERT INTO sys_app_settings (sys_id, setting_key, setting_value, setting_category, description, updated_by, updated_at)
                VALUES ('setting_chat_whitelisted_rooms', 'chat.whitelisted_rooms', ?, 'fanstack', 'Whitelisted room IDs for advocate chat', 'pilot', CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_by = 'pilot',
                    updated_at = CURRENT_TIMESTAMP
            """, (val,))

        conn.commit()

    # Broadcast WebSocket event CHAT_POLICY_UPDATED via local relay & direct WS
    event_payload = {
        "type": "CHAT_POLICY_UPDATED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "global_enabled": payload.global_enabled,
            "leagues": payload.leagues,
            "room_policy": payload.room_policy,
            "whitelisted_rooms": payload.whitelisted_rooms
        }
    }

    # Dispatch via HTTP to relay broadcast endpoint
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post("http://127.0.0.1:8000/broadcast", json=event_payload)
    except Exception:
        pass

    # Direct WS dispatch to Port 8008
    try:
        import websockets
        async with websockets.connect("ws://127.0.0.1:8008", ping_interval=None) as ws:
            await ws.send(json.dumps(event_payload))
    except Exception:
        pass

    return await get_fanstack_chat_policy()

