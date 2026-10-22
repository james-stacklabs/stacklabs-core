
# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---
from datetime import date
from dotenv import load_dotenv
import os
import re
import re as _re
import socket, json
import socket, json, asyncio, os
import socket, json, os
import sqlite3
import sqlite3 as _sq
import time
import uuid as _uuid
# -------------------------------------------------------------

import asyncio
from datetime import datetime, timezone
import datetime as dt
import json
import logging
import os
from pathlib import Path
import random
import re
import sqlite3
import sys as _sys
import time
import uuid
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
import urllib.request

import requests
import websockets

try:
    _sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Logging setup
logging.basicConfig(level=logging.INFO, format="[CHATBOTS] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fanstack_chatbots")

# Shared paths and context manager
REPO_ROOT = Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(REPO_ROOT / "scripts"))

from core.db import get_db, DB_PATH
from core.api_client import resolve_team_name, get_team_color, get_team, get_sports_teams
from core.roster_registry import RoomRosterRegistry

STATCAST_PATH = REPO_ROOT / "sovereign_intelligence.db"

@contextmanager
def get_statcast_db(row_factory=True, timeout=10.0):
    """Context-managed connection for Statcast intelligence database."""
    conn = sqlite3.connect(str(STATCAST_PATH), timeout=timeout)
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Hot cache reader integration
try:
    from game_cache_reader import get_inning_context, get_recent_plays
    _CACHE_READER_OK = True
except ImportError as _cache_import_err:
    logger.warning("game_cache_reader not found — context injection disabled: %s", _cache_import_err)
    _CACHE_READER_OK = False
    def get_inning_context(*a, **kw): return ""
    def get_recent_plays(*a, **kw): return ""

# Load Gemini / Vertex API Keys cleanly
try:
    import dotenv
    dotenv.load_dotenv(REPO_ROOT / ".env")
except Exception as _dotenv_err:
    logger.warning("Could not load .env via python-dotenv: %s", _dotenv_err)

VERTEX_KEY = os.environ.get("VERTEX_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_KEY:
    logger.info("Gemini Developer Key loaded (length=%d).", len(GEMINI_KEY))
elif VERTEX_KEY:
    logger.info("Vertex AI Express Key loaded successfully (length=%d).", len(VERTEX_KEY))
else:
    logger.warning("No VERTEX_API_KEY or GEMINI_API_KEY found in environment or .env.")

OLLAMA_API = 'http://localhost:11434/api/generate'
current_global_boggs_level = 2

def normalize_team(team_str: str) -> str:
    """Normalize team name or token to canonical abbreviation via centralized API client."""
    if not team_str:
        return ""
    t = str(team_str).strip()
    canonical = resolve_team_name(t)
    return canonical if canonical != "GLOBAL" else t.upper()


try:
    from context_budget import score_budget, get_budget_tier, build_context_payload
except ImportError as cb_err:
    logger.warning("Failed to import context_budget: %s", cb_err)

GAME_TIME_MODEL = "gemini-3.8-flash"
DEV_MODEL = "gemini-3.8-flash"


def inject_room_events(room_key: str):
    """
    Polymorphic event injector: Pulls uninjected ws_content_events for any room_key
    (MLB, NFL, WeedStack, MARD, etc.) and writes them into game_context as live triggers.
    """
    if not room_key:
        return
    try:
        with get_db() as conn:
            events = conn.execute("""
                SELECT * FROM ws_content_event
                WHERE room_key = ? AND injected = 0
                ORDER BY sys_created_on ASC
                LIMIT 3
            """, (room_key,)).fetchall()

            for event in events:
                conn.execute("""
                    INSERT INTO game_context
                        (id, game_pk, source, headline, content, tags, injected_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    str(uuid.uuid4()),
                    room_key,
                    event["source_key"],
                    event["headline"],
                    event["content"],
                    event["tags"]
                ))
                conn.execute(
                    "UPDATE ws_content_event SET injected=1, injected_at=datetime('now') WHERE sys_id=?",
                    (event["sys_id"],)
                )
            conn.commit()
    except Exception as e:
        logger.warning("Error injecting room events for %s: %s", room_key, e)

# Legacy aliases for backward compatibility
inject_weedstack_events = inject_room_events
inject_nfl_events = inject_room_events

CHATBOTS_MUTED_FLAG = "/home/james/stacklabs/config/chatbots_muted.flag"
BOTS_PAUSED_FLAG = "/tmp/bots_paused.flag"
global_chatbots_enabled = not (os.path.exists(CHATBOTS_MUTED_FLAG) or os.path.exists(BOTS_PAUSED_FLAG))

_chat_policy_cache = {
    "global_enabled": True,
    "leagues": {"NFL": True, "CFB": True, "MLB": True},
    "room_policy": "all_active",
    "whitelisted_rooms": []
}
_chat_policy_cache_ts = 0.0


def load_chat_policy(force_reload: bool = False) -> Dict[str, Any]:
    global _chat_policy_cache, _chat_policy_cache_ts
    now = time.time()
    if not force_reload and (now - _chat_policy_cache_ts < 5.0):
        return _chat_policy_cache

    try:
        with get_db() as conn:
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

            global_en = settings.get("chat.global_enabled", "true").lower() == "true"
            nfl_en = settings.get("chat.league.nfl", "true").lower() == "true"
            cfb_en = settings.get("chat.league.cfb", "true").lower() == "true"
            mlb_en = settings.get("chat.league.mlb", "true").lower() == "true"
            room_pol = settings.get("chat.room_policy", "all_active")

            raw_whitelist = settings.get("chat.whitelisted_rooms", "[]")
            try:
                whitelist = json.loads(raw_whitelist)
                if isinstance(whitelist, list):
                    whitelist = [str(x) for x in whitelist]
                else:
                    whitelist = []
            except Exception:
                whitelist = []

            _chat_policy_cache = {
                "global_enabled": global_en,
                "leagues": {
                    "NFL": nfl_en,
                    "CFB": cfb_en,
                    "MLB": mlb_en
                },
                "room_policy": room_pol,
                "whitelisted_rooms": whitelist
            }
            _chat_policy_cache_ts = now
    except Exception as e:
        logger.warning("Error loading chat policy: %s", e)

    return _chat_policy_cache


_room_sport_cache = {}


def get_room_sport(game_pk: str) -> str:
    pk = str(game_pk).strip()
    if not pk or pk in ("GLOBAL", "hot_takes"):
        return "MLB"
    if pk in _room_sport_cache:
        return _room_sport_cache[pk]

    sport = "MLB"
    if "nfl" in pk.lower():
        sport = "NFL"
    elif "cfb" in pk.lower():
        sport = "CFB"
    else:
        try:
            with get_db() as conn:
                row = conn.execute("SELECT sport FROM sport_schedule WHERE game_pk = ? LIMIT 1", (pk,)).fetchone()
                if row and row["sport"]:
                    sport = row["sport"].upper()
                else:
                    row2 = conn.execute("SELECT sport FROM cmdb_ci_fanstack_room WHERE game_pk = ? LIMIT 1", (pk,)).fetchone()
                    if row2 and "sport" in row2.keys() and row2["sport"]:
                        sport = row2["sport"].upper()
        except Exception:
            pass
    _room_sport_cache[pk] = sport
    return sport


room_active_cache = {}
room_active_cache_ts = {}


def is_room_active(game_pk: str) -> bool:
    """Check if a game room is currently active in the database and permitted by chat policy."""
    global global_chatbots_enabled
    pk = str(game_pk).strip()

    # Chat Policy Gate Enforcement (WO0010184)
    policy = load_chat_policy()
    if not policy.get("global_enabled", True):
        return False

    sport = get_room_sport(pk)
    if not policy.get("leagues", {}).get(sport, True):
        return False

    if policy.get("room_policy") == "whitelist" and pk not in policy.get("whitelisted_rooms", []):
        return False

    if not global_chatbots_enabled or os.path.exists(CHATBOTS_MUTED_FLAG) or os.path.exists(BOTS_PAUSED_FLAG):
        return False

    if not pk or pk in ("GLOBAL", "hot_takes"):
        return global_chatbots_enabled

    if pk in ("823574", "823576") or "sim" in pk.lower():
        return True

    # Check in-memory RoomRosterRegistry presence (WO0010160)
    if pk in RoomRosterRegistry.get_all_rosters() and len(RoomRosterRegistry.get_active_personas(pk)) > 0:
        return True

    now = time.time()
    if pk in room_active_cache and (now - room_active_cache_ts.get(pk, 0) < 5.0):
        return room_active_cache[pk]

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT room_state FROM sport_schedule WHERE game_pk = ? LIMIT 1",
                (pk,)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT room_state FROM cmdb_ci_fanstack_room WHERE game_pk = ? LIMIT 1",
                    (pk,)
                ).fetchone()
            is_act = bool(row and row["room_state"] == "active")
            room_active_cache[pk] = is_act
            room_active_cache_ts[pk] = now
            return is_act
    except Exception as e:
        logger.warning("Error checking room state for %s: %s", pk, e)
        return True

global_heat_map = {}
global_penalty_box = {}
comment_timestamps = []
global_battery_feud_tracker = {}
active_fans = []

# ── PERMANENT BLACKLIST & MODEL GOVERNANCE (DFCT0010010) ──────────────────────
BLACKLISTED_MODELS = {
    "legacy-2.5-flash", "legacy-2.5-flash-lite", "legacy-2.5-pro",
    "legacy-2.5-flash-preview-tts", "legacy-2.5-pro-preview-tts"
}

# ── MLB ROSTER TEAM LOOKUP & POLARITY ENGINE (CANONICAL DATABASE TRUTH) ───────
_player_team_cache = {}
_last_roster_cache_load = 0.0

def lookup_player_team(player_name: str) -> str:
    """Resolve a player's MLB team abbreviation directly from mlb_rosters database table."""
    global _player_team_cache, _last_roster_cache_load
    if not player_name or player_name in ("Awaiting Batter", "Awaiting Pitcher", "the batter", "the pitcher"):
        return ""
    
    clean_name = player_name.strip().lower()
    now = time.time()

    # Refresh in-memory roster cache every 300 seconds from canonical SQLite table
    if not _player_team_cache or (now - _last_roster_cache_load > 300.0):
        try:
            with get_db(timeout=2.0) as conn:
                rows = conn.execute("SELECT player_name, team_abbr FROM mlb_rosters WHERE status = 'Active'").fetchall()
                for r in rows:
                    p_name = str(r["player_name"]).strip().lower()
                    t_abbr = str(r["team_abbr"]).strip().upper()
                    _player_team_cache[p_name] = t_abbr
                _last_roster_cache_load = now
        except Exception as e:
            logger.warning("[lookup_player_team] Failed to refresh roster cache from mlb_rosters: %s", e)
            
    # 1. Exact full-name match (e.g. "aaron judge", "juan soto", "pete alonso")
    if clean_name in _player_team_cache:
        return _player_team_cache[clean_name]
        
    # 2. Last-name match fallback (e.g. "judge", "lindor", "cole")
    parts = clean_name.split()
    if len(parts) >= 1:
        last_name = parts[-1]
        for p, t in _player_team_cache.items():
            if p == last_name or p.endswith(" " + last_name):
                return t
                
    return ""

# ── IN-ROOM ANTI-ECHO LRU BUFFER (DFCT0010010) ────────────────────────────────
room_recent_utterances = defaultdict(lambda: deque(maxlen=25))

def is_duplicate_in_room(text: str, room_id: Optional[str] = None) -> bool:
    """Check if candidate text was spoken in this room recently (anti-echo filter)."""
    if not text or not room_id:
        return False
    clean = re.sub(r'[^a-z0-9]', '', text.lower())
    if not clean:
        return False
    recent = room_recent_utterances[str(room_id)]
    for past in recent:
        past_clean = re.sub(r'[^a-z0-9]', '', past.lower())
        if clean == past_clean:
            return True
        if len(clean) > 20 and (clean in past_clean or past_clean in clean):
            return True
    return False

def record_room_utterance(text: str, room_id: Optional[str] = None):
    """Record an accepted utterance into the in-room LRU memory buffer."""
    if text and room_id:
        room_recent_utterances[str(room_id)].append(text.strip())

def _select_non_duplicate(candidates: List[str], target_room: Optional[str] = None, fallback_pool: Optional[List[str]] = None) -> str:
    """Select a candidate string that has not been spoken in this room recently."""
    if not candidates:
        return "Let's go!"
    shuffled = list(candidates)
    random.shuffle(shuffled)
    if target_room:
        for c in shuffled:
            if not is_duplicate_in_room(c, target_room):
                record_room_utterance(c, target_room)
                return c
        if fallback_pool:
            f_shuffled = list(fallback_pool)
            random.shuffle(f_shuffled)
            for fc in f_shuffled:
                if not is_duplicate_in_room(fc, target_room):
                    record_room_utterance(fc, target_room)
                    return fc
    chosen = shuffled[0]
    if target_room:
        record_room_utterance(chosen, target_room)
    return chosen

# ── ACTIVE VIEWING ROOM QUOTA SHIELD (DFCT0010010) ────────────────────────────
_active_viewers_cache = set()
_last_active_viewers_ts = 0.0

async def get_active_viewing_rooms() -> set:
    """Query fanstack_relay for rooms with connected human viewers."""
    global _active_viewers_cache, _last_active_viewers_ts
    now = time.time()
    if _active_viewers_cache and (now - _last_active_viewers_ts < 10.0):
        return _active_viewers_cache
    try:
        with get_db(timeout=3.0) as conn:
            rows = conn.execute("SELECT game_pk FROM sport_schedule WHERE room_state = 'active' OR status IN ('In Progress', 'Live')").fetchall()
            active_set = {str(r["game_pk"]) for r in rows} | {"GLOBAL", "hot_takes"}
    except Exception:
        active_set = {"GLOBAL", "hot_takes"}
    try:
        def _fetch():
            req = urllib.request.Request("http://127.0.0.1:8000/api/rooms/active_viewers")
            with urllib.request.urlopen(req, timeout=1.0) as res:
                return json.loads(res.read().decode('utf-8'))
        data = await asyncio.to_thread(_fetch)
        if isinstance(data, dict):
            for r in data.get("active_rooms", []):
                active_set.add(str(r))
            for k, v in data.items():
                if isinstance(v, (int, float)) and v > 0:
                    active_set.add(str(k))
        _active_viewers_cache = active_set
        _last_active_viewers_ts = now
        return _active_viewers_cache
    except Exception:
        return active_set


def init_vertex_ai() -> bool:
    """Eagerly initialize native Vertex AI client ($300 Project Credit)."""
    global _genai_client, _is_vertex, global_hard_quota_depleted
    try:
        from google import genai
        sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "/home/james/stacklabs/config/vertex_sa.json"
        v_project = os.environ.get("VERTEX_PROJECT", "project-114213dc-6519-49c5-a0a")
        v_location = os.environ.get("VERTEX_LOCATION", "us-central1")
        if sa_path and os.path.exists(sa_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
            _genai_client = genai.Client(vertexai=True, project=v_project, location=v_location)
            global_hard_quota_depleted = False
            _is_vertex = True
            logger.info("[VERTEX AI INITIALIZED] Native Vertex AI connected with %s on project %s ($300 Credit)", sa_path, v_project)
            print(f"[VERTEX AI INITIALIZED] Native Vertex AI connected with {sa_path} on project {v_project} ($300 Credit)")
            return True
        else:
            g_key = os.environ.get("GEMINI_API_KEY") or GEMINI_KEY or os.environ.get("GEMINI_CLOUD_CONSOLE_KEY")
            v_key = os.environ.get("VERTEX_API_KEY")
            key_to_use = g_key or v_key
            if key_to_use:
                _genai_client = genai.Client(api_key=key_to_use)
                global_hard_quota_depleted = False
                _is_vertex = False
                logger.info("[GEMINI API INITIALIZED] Connected via API key")
                print("[GEMINI API INITIALIZED] Connected via API key")
                return True
    except Exception as e:
        logger.error("[VERTEX AI INIT ERROR] Failed to initialize GenAI client: %s", e)
        print(f"[VERTEX AI INIT ERROR] Failed to initialize GenAI client: {e}")
    return False


def _strip_meta_notes(text: str) -> str:
    """Strip AI meta-commentary and leaked system prompt artifacts from response text."""
    if not text:
        return text
    # Strip leading markdown bold headings/prefixes e.g. **Ghost Trauma Syndrome:** or **Analysis:** or ### Header
    text = re.sub(r'^\s*\*\*[^*]+?\*\*:?\s*', '', text)
    text = re.sub(r'^\s*###\s*[^\n]+?\s*', '', text)
    for marker in [
        '### DEEP LORE', '#### AI', '#### BEGIN', '#### CONCLU',
        '###\n', '  ###', '\n###',
        '[END OF PROFILE]', '[END OF', '[PROFILE END]',
        '\n\n---', '\n---\n',
        'character limit', 'word limit', 'Note to AI',
        '(As per the', '(Following the', '(In line with',
    ]:
        idx = text.find(marker)
        if idx > 20:
            text = text[:idx]
    text = re.sub(r'\s*[\(\[]\s*Note:.*?[\)\]]', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\s*\((?:This|The above|I|My|Following|Content|As an AI).*?\)', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\s*#[A-Za-z]{4,}(\s+#[A-Za-z]{4,})+\s*$', '', text, flags=re.IGNORECASE)
    text = text.rstrip(' -:….')
    return text.strip()

def _build_short_personality(personality: str, max_chars: int = 3000) -> str:
    """
    Preserves the full rich character voice, humor, quirks, catchphrases, and emotional stakes.
    Avoids aggressive truncation so the persona maintains its unique comedy and distinct voice.
    """
    if not personality:
        return ""
    return personality[:max_chars].strip()


def resolve_at_bat_perspective(persona_team, active_play):
    """
    Given a persona's team affiliation and the active telemetry play,
    returns deterministic perspective flags to guide comment generation.
    """
    persona_team = normalize_team(persona_team)
    if not persona_team or persona_team in ("GLOBAL", "MLB", "ANY", "ALL", "NONE", "NEUTRAL"):
        return {
            "is_advocate_batting_team": False,
            "is_advocate_pitching_team": False,
            "is_neutral": True,
            "advocate_allies": [],
            "advocate_opponents": [],
            "current_lead_runs": active_play.get("lead_runs", 0),
            "is_advocate_winning": False
        }

    batter_team = normalize_team(active_play.get("batter_team"))
    pitcher_team = normalize_team(active_play.get("pitcher_team"))
    leading_team = normalize_team(active_play.get("leading_team"))
    is_batting_team = (persona_team == batter_team)
    is_pitching_team = (persona_team == pitcher_team)
    
    allies = [active_play.get("batter")] if is_batting_team else [active_play.get("pitcher")]
    opponents = [active_play.get("pitcher")] if is_batting_team else [active_play.get("batter")]
    
    # Filter out empty names
    allies = [a for a in allies if a and a != "Awaiting Batter" and a != "Awaiting Pitcher"]
    opponents = [o for o in opponents if o and o != "Awaiting Batter" and o != "Awaiting Pitcher"]
    
    if not allies:
        allies = ["our team"]
    if not opponents:
        opponents = ["their team"]
        
    advocate_role = "batting" if is_batting_team else ("pitching" if is_pitching_team else "neutral")
    return {
        "is_advocate_batting_team": is_batting_team,
        "is_advocate_pitching_team": is_pitching_team,
        "advocate_role": advocate_role,
        "is_neutral": False,
        "advocate_allies": allies,
        "advocate_opponents": opponents,
        "current_lead_runs": active_play.get("lead_runs", 0),
        "is_advocate_winning": (persona_team == leading_team)
    }


def validate_commentary(text: str, fan: dict, active_play: dict) -> Tuple[bool, Optional[str]]:
    """
    Data-driven commentary validator: Prevents wrong-team cheering, visitor home-claims,
    lead mismatches, and offense/defense polarity drift dynamically without hardcoded entity strings.
    """
    if not text:
        return True, None
    text_lower = text.lower()
    persona_team = normalize_team(fan.get("team"))
    
    batter = str(active_play.get("batter", "")).strip()
    pitcher = str(active_play.get("pitcher", "")).strip()
    batter_team = normalize_team(active_play.get("batter_team"))
    pitcher_team = normalize_team(active_play.get("pitcher_team"))
    home_team = normalize_team(active_play.get("home_team"))
    away_team = normalize_team(active_play.get("away_team"))
    leading_team = normalize_team(active_play.get("leading_team"))

    # 1. Opposing team hyping validation
    is_batting_allied = (persona_team == batter_team)
    is_pitching_allied = (persona_team == pitcher_team)
    
    def contains_player_name(full_name: str, t: str) -> bool:
        if not full_name or full_name in ("Awaiting Batter", "Awaiting Pitcher"):
            return False
        parts = full_name.split()
        for p in parts:
            if len(p) > 2 and p.lower() in t:
                return True
        return False

    if is_batting_allied and not is_pitching_allied and contains_player_name(pitcher, text_lower):
        if any(hw in text_lower for hw in ["great pitch", "nice job", "beautiful throw", "amazing job"]):
            return False, "hyping_opposing_pitcher"
                
    if is_pitching_allied and not is_batting_allied and contains_player_name(batter, text_lower):
        if any(hw in text_lower for hw in ["crushed it", "great hit", "beautiful swing", "love to see it"]):
            return False, "hyping_opposing_batter"

    # 2. Score and lead claim validation
    if leading_team and persona_team and persona_team != leading_team:
        if any(w in text_lower for w in ["our lead", "we lead", "we are winning", "we're ahead"]):
            return False, "wrong_team_lead_claim"

    # 3. Visitor home-ballpark claim validation
    if persona_team and away_team and persona_team == away_team and persona_team != home_team:
        visitor_claims = [
            "our ballpark", "our park", "our house", "our stadium", "our field",
            "our home", "in our stadium", "at our house", "our turf", "our yard",
            "our venue", "our place", "our home-field", "our homefield", "welcome to our stadium"
        ]
        if any(claim in text_lower for claim in visitor_claims):
            return False, "visitor_claiming_home_ballpark"

    # 4. Offense vs Defense Cheering Polarity Guard (Task 24 Strict Invariant)
    if is_pitching_allied and not is_batting_allied:
        offensive_cheers = [
            "put one in the gap", "drive them home", "drive 'em home", "drive these runs home",
            "work the walk", "work a walk", "swing the bat", "hit a homer", "clear the bases",
            "drive someone in", "knock one out", "launch one into", "rip the next one"
        ]
        if any(oc in text_lower for oc in offensive_cheers):
            return False, "cheering_offense_while_pitching"

    if is_batting_allied and not is_pitching_allied:
        defensive_cheers = [
            "paint the black", "strike him out", "sit him down", "blow it by him",
            "punch him out", "grab some pine", "induce the grounder", "turn two"
        ]
        if any(dc in text_lower for dc in defensive_cheers):
            return False, "cheering_pitching_while_batting"

    # 5. Persona-specific forbidden tokens from database metadata
    forbidden_tokens = fan.get("forbidden_tokens", [])
    if isinstance(forbidden_tokens, str):
        try:
            forbidden_tokens = json.loads(forbidden_tokens)
        except Exception:
            forbidden_tokens = [t.strip().lower() for t in forbidden_tokens.split(",") if t.strip()]
    
    if any(ft.lower() in text_lower for ft in forbidden_tokens):
        return False, "persona_forbidden_token_violation"

    return True, None

def detect_play_event_category(status_text: str) -> str:
    """Classifies live play text into exact event categories for offline template routing."""
    if not status_text:
        return "banter"
    s = str(status_text).lower()
    if any(k in s for k in ["home run", "homers", "homer", "grand slam", "moonshot", "went yard", "deep drive"]):
        return "home_run"
    if any(k in s for k in ["strikes out", "struck out", "strikeout", "punched out", "punchout", "caught looking"]):
        return "strikeout"
    if any(k in s for k in ["double play", "twin killing", "grounded into dp", "6-4-3", "4-6-3", "5-4-3"]):
        return "double_play"
    if any(k in s for k in ["walked", "walk", "base on balls", "four balls"]):
        return "walk"
    if any(k in s for k in ["single", "doubled", "double", "tripled", "triple", "base hit", "line drive", "rbi"]):
        return "hit"
    if any(k in s for k in ["stole second", "stole third", "stolen base", "swiped"]):
        return "stolen_base"
    if any(k in s for k in ["blown save", "meltdown", "walk-off loss", "choked"]):
        return "blown_save"
    if any(k in s for k in ["pitching change", "replaces", "mound visit"]):
        return "pitching_change"
    if any(k in s for k in ["called strike", "struck out looking"]):
        return "called_strike"
    if any(k in s for k in ["swinging strike", "swing and a miss", "swings through", "whiff"]):
        return "swinging_strike"
    if "foul" in s:
        return "foul"
    if "ball" in s and "fly ball" not in s and "ground ball" not in s:
        return "ball"
    if "strike" in s:
        return "strike"
    if any(k in s for k in ["flies out", "lines out", "grounds out", "pops out"]):
        return "out"
    if any(k in s for k in ["umpire", "bad call", "blind", "horrible call"]):
        return "bad_call"
    return "banter"


def log_compliance_violation(game_pk: str, persona_id: str, violation_type: str, rejected_text: str, temp: float):
    """Logs a compliance violation using safe SQLite context managers."""
    try:
        with get_db() as conn:
            audit_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO compliance_audit_trail (audit_id, game_pk, persona_id, violation_type, rejected_text, temperature)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (audit_id, str(game_pk), str(persona_id), str(violation_type), str(rejected_text), float(temp)))
            conn.commit()
            logger.info("[COMPLIANCE] Logged violation '%s' for %s in game %s", violation_type, persona_id, game_pk)
    except Exception as e:
        logger.warning("[COMPLIANCE ERROR] Failed to log violation: %s", e)


def is_rivalry_game(game_pk: str = None, home_team: str = "", away_team: str = "") -> bool:
    """Dynamically determines rivalry state from schedule metadata or divisional lookup."""
    if game_pk:
        try:
            with get_db() as conn:
                row = conn.execute("SELECT is_rivalry FROM sport_schedule WHERE game_pk = ?", (str(game_pk),)).fetchone()
                if row and row["is_rivalry"]:
                    return True
        except Exception:
            pass

    ht = normalize_team(home_team)
    at = normalize_team(away_team)
    rivalry_pairs = {
        "NYM": ["PHI", "ATL", "NYY"],
        "PHI": ["NYM", "ATL", "WSH"],
        "BOS": ["NYY", "TB"],
        "NYY": ["BOS", "NYM", "HOU"],
        "LAD": ["SF", "SD", "HOU"],
        "SF":  ["LAD", "SD"],
        "CHC": ["STL", "CWS", "MIL"],
        "STL": ["CHC", "MIL", "CIN"],
        "DET": ["CWS", "CLE", "MIN"],
        "HOU": ["TEX", "NYY", "LAD"]
    }
    return at in rivalry_pairs.get(ht, []) or ht in rivalry_pairs.get(at, [])


def build_dynamic_system_instruction(fan: dict, is_massive_event: bool, is_play_event: bool, allow_rant: bool, game_state: dict = None, event_type: str = "routine_pitch", game_pk: str = None) -> str:
    """
    Builds the high-fidelity dynamic persona prompt:
    - Preserves full authentic character comedy, deep lore, speech quirks, and backstory.
    - Replaces sterile legalese with concise comedic direction.
    - Injects dynamic roster and room memory cross-talk.
    """
    # 1. Base personality from persona profile (un-truncated)
    base_personality = fan.get("personality", "") or fan.get("system_prompt", "") or ""
    system_text = base_personality

    # 2. Extract macro game context
    score_diff = 0
    inning = "Top 1st"
    runners_on = False
    is_rivalry = False
    boggs_level = int(fan.get("boggs_level", 2))

    if game_state:
        try:
            score_diff = abs(int(game_state.get("away_score", 0)) - int(game_state.get("home_score", 0)))
        except Exception:
            score_diff = 0
        inning = game_state.get("inning", "Top 1st")
        status_msg = str(game_state.get("status_msg", "")).lower()
        if any(term in status_msg for term in ["bases loaded", "runner", "first", "second", "third"]):
            runners_on = True
        is_rivalry = is_rivalry_game(game_pk, game_state.get("home_team", ""), game_state.get("away_team", ""))
        try:
            boggs_level = int(game_state.get("boggs_level", fan.get("boggs_level", 2)))
        except Exception:
            boggs_level = int(fan.get("boggs_level", 2))

    # 3. Punchy Comedic Operational Rules (Positive Guidance over Negative Bureaucracy)
    comedic_guidance = (
        "\n\n### COMEDIC DIRECTION & CHAT CADENCE ###\n"
        "- Be hilarious, deeply emotional, fiercely biased, and quick-witted in character.\n"
        "- STRICT LIVE CHAT BREVITY: You are posting in a fast-scrolling live stream chat room. Keep your message punchy, sharp, and concise: 1 to 2 snappy sentences MAXIMUM (under 35 words). NEVER write essays, multi-paragraph monologues, or run-on rants.\n"
        "- Draw from your unique lore, superstitions, historic team grievances, and sharp comedic timing.\n"
        "- Output raw chat dialogue ONLY (never include meta-commentary, parenthetical labels, or scene setting).\n"
        "- ZERO MONOCULTURE / ANTI-CLICHÉ OPENINGS: STRICTLY NEVER start your message with generic clichés like 'ARE YOU KIDDING ME?!', 'OH COME ON!', or 'WHAT ARE WE DOING?!'. Jump immediately into fresh idiosyncratic observations, tactical analysis, stadium smells, personal superstitions, or direct player callouts."
    )
    system_text += comedic_guidance

    # 4. Dynamic Roster Grounding Block
    team_abbr = fan.get("team")
    if team_abbr and str(team_abbr).lower() not in ('global', 'all', 'mlb', 'none', ''):
        try:
            with get_db() as conn:
                rows = conn.execute("""
                    SELECT player_name, jersey_number, position 
                    FROM mlb_rosters 
                    WHERE team_abbr = ? AND status = 'Active'
                    ORDER BY player_name ASC LIMIT 15
                """, (str(team_abbr).upper(),)).fetchall()
                
                departures = conn.execute("""
                    SELECT player_name, current_team 
                    FROM cmdb_ci_ghost_roster 
                    WHERE trauma_team = ?
                """, (str(team_abbr).upper(),)).fetchall()

            if rows or departures:
                roster_block = f"\n\n### ACTIVE TEAM GROUNDING ({str(team_abbr).upper()}) ###\n"
                if rows:
                    roster_block += "Active Roster Context: " + ", ".join([f"{r['player_name']} (#{r['jersey_number'] or '?'})" for r in rows[:10]]) + "\n"
                if departures:
                    roster_block += "Departed Players (Now on other teams): " + ", ".join([f"{d['player_name']} (now {d['current_team']})" for d in departures]) + "\n"
                system_text += roster_block
        except Exception as e:
            logger.warning("[ROSTER GROUNDING ERROR] %s", e)

    # 5. Venue / Neutral Observation Guidance
    fan_team_upper = normalize_team(fan.get("team"))
    if game_state and fan_team_upper and fan_team_upper not in ("GLOBAL", "MLB", "ANY", "ALL"):
        away_team = normalize_team(game_state.get("away_team"))
        home_team = normalize_team(game_state.get("home_team"))
        if away_team and home_team:
            if fan_team_upper != away_team and fan_team_upper != home_team:
                system_text += (
                    f"\n\n### NEUTRAL GAME OBSERVATION ###\n"
                    f"You are watching {away_team} vs {home_team}. As a loyal {fan_team_upper} fan, react sardonically from your own team's perspective. Do not root for either team as 'us'."
                )
            elif fan_team_upper == away_team:
                system_text += (
                    f"\n\n### VISITING FAN PERSPECTIVE ###\n"
                    f"Your team ({fan_team_upper}) is playing as the VISITOR on the road against {home_team}. Mock the home crowd and cheer for your road warriors."
                )

    # 6. Relational Memory Swarm Cross-Talk Context
    if game_pk and fan.get("name"):
        try:
            with get_db() as conn:
                hist_comments = conn.execute("""
                    SELECT comment_text 
                    FROM m2m_persona_room_ledger 
                    WHERE persona_id = ? AND game_pk = ? 
                    ORDER BY timestamp DESC LIMIT 3
                """, (fan["name"].lower(), str(game_pk))).fetchall()

                room_comments = conn.execute("""
                    SELECT persona_id, comment_text 
                    FROM m2m_persona_room_ledger 
                    WHERE game_pk = ? AND persona_id != ? 
                    ORDER BY timestamp DESC LIMIT 4
                """, (str(game_pk), fan["name"].lower())).fetchall()

            if hist_comments:
                system_text += "\n\n### YOUR RECENT COMMENTS ###\n" + "\n".join([f"- \"{r['comment_text']}\"" for r in reversed(hist_comments)])
            if room_comments:
                system_text += "\n\n### ROOM BANTER (Other Fans in Room) ###\n" + "\n".join([f"@{r['persona_id']}: \"{r['comment_text']}\"" for r in reversed(room_comments)])
        except Exception as le:
            logger.warning("[LEDGER CONTEXT ERROR] %s", le)

    return system_text


def build_dynamic_user_prompt(fan: dict, current_play: str, game_state: dict = None) -> str:
    """Assembles the user-turn prompt with macro game state context."""
    context_line = ""
    if game_state:
        away_score = game_state.get('away_score', 0)
        home_score = game_state.get('home_score', 0)
        inning_topbot = game_state.get('inning_topbot', '')
        inning = game_state.get('inning', '')
        outs = game_state.get('outs', 0)
        context_line = (
            f"Game State: Score is Away {away_score} - Home {home_score} | "
            f"Inning: {inning_topbot} {inning} | {outs} Outs.\n"
        )

    prompt = (
        f"You are operating as the persona: {fan.get('name', 'Advocate')}.\n"
        f"{context_line}"
        f"The current play telemetry feed: {current_play}\n"
        f"React to this sequence strictly IN CHARACTER matching your assigned biases."
    )
    return prompt


def query_stats(pitcher: str, batter: str) -> Optional[dict]:
    """Queries Statcast pitch and exit velocity stats with managed connections."""
    try:
        with get_statcast_db() as conn:
            c = conn.cursor()
            last_name = batter.split(' ')[-1] if batter else ""
            c.execute("""
                SELECT avg(launch_speed), count(*) FROM statcast_pitches 
                WHERE player_name LIKE ? AND events IN ('single', 'double', 'triple', 'home_run', 'field_out')
            """, (f"%{last_name}%",))
            b_res = c.fetchone()
            
            p_last = pitcher.split(' ')[-1] if pitcher else ""
            c.execute("""
                SELECT pitch_name, avg(release_speed) FROM statcast_pitches
                WHERE player_name LIKE ? 
                GROUP BY pitch_name ORDER BY count(*) DESC LIMIT 1
            """, (f"%{p_last}%",))
            p_res = c.fetchone()
            
            b_velo = round(b_res[0], 1) if b_res and b_res[0] else "Unknown"
            b_events = b_res[1] if b_res and b_res[1] else 0
            p_pitch = p_res[0] if p_res and p_res[0] else "Fastball"
            p_velo = round(p_res[1], 1) if p_res and p_res[1] else "Unknown"
            
            return {
                "batter_last": last_name,
                "batter_avg_exit_velo": b_velo,
                "batter_balls_in_play": b_events,
                "pitcher_last": p_last,
                "pitcher_primary_pitch": p_pitch,
                "pitcher_primary_velo": p_velo
            }
    except Exception as e:
        logger.warning("Statcast query error: %s", e)
        return None

def build_player_context_str(pitcher: str, batter: str) -> str:
    """Builds formatted player context string from Statcast data."""
    if not pitcher and not batter:
        return json.dumps({"player_context": None}, indent=2)
    
    ctx = {
        "player_context": {
            "batter": None,
            "pitcher": None
        }
    }
    has_stats = False
    
    try:
        with get_statcast_db() as conn:
            c = conn.cursor()
            if batter:
                last_name = batter.split(' ')[-1]
                c.execute("""
                    SELECT avg(launch_speed), count(*) FROM statcast_pitches 
                    WHERE player_name LIKE ? AND events IN ('single', 'double', 'triple', 'home_run', 'field_out')
                """, (f"%{last_name}%",))
                b_res = c.fetchone()
                if b_res and b_res[0] is not None:
                    ctx["player_context"]["batter"] = {
                        "name": batter,
                        "avg_exit_velocity_mph": round(b_res[0], 1),
                        "total_balls_in_play": b_res[1]
                    }
                    has_stats = True
                    
            if pitcher:
                p_last = pitcher.split(' ')[-1]
                c.execute("""
                    SELECT pitch_name, avg(release_speed) FROM statcast_pitches
                    WHERE player_name LIKE ? 
                    GROUP BY pitch_name ORDER BY count(*) DESC LIMIT 1
                """, (f"%{p_last}%",))
                p_res = c.fetchone()
                if p_res and p_res[0] is not None:
                    ctx["player_context"]["pitcher"] = {
                        "name": pitcher,
                        "primary_pitch": p_res[0],
                        "primary_pitch_velocity_mph": round(p_res[1], 1) if p_res[1] else None
                    }
                    has_stats = True
    except Exception as e:
        logger.warning("[PLAYER CONTEXT ERROR] %s", e)
            
    if not has_stats:
        return json.dumps({"player_context": None}, indent=2)
        
    return json.dumps(ctx, indent=2)


_cached_mlb_config = None
_last_mlb_config_load = 0.0

def load_mlb_event_config():
    """Loads MLB event triggers from database with caching."""
    global _cached_mlb_config, _last_mlb_config_load
    now = time.time()
    if _cached_mlb_config is not None and (now - _last_mlb_config_load < 10.0):
        return _cached_mlb_config

    config = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT event_keyword, is_massive_event FROM sys_mlb_event_config WHERE active = 1")
            for r in c.fetchall():
                config.append({
                    "keyword": str(r['event_keyword']).lower(),
                    "is_massive": bool(r['is_massive_event'])
                })
    except Exception as e:
        logger.warning("Error loading MLB event config: %s", e)

    if config:
        _cached_mlb_config = config
        _last_mlb_config_load = now
    return config

_last_fans_load = 0
_cached_fans = []

def load_fans():
    """Load all personas from active game rooms using managed DB context."""
    global _last_fans_load, _cached_fans
    now = time.time()
    if _cached_fans and (now - _last_fans_load < 5.0):
        return _cached_fans

    fans_list = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT
                    p.id            as persona_id,
                    p.user_name     as name,
                    p.team          as assigned_to,
                    p.system_prompt as u_system_prompt,
                    p.boggs_level   as u_boggs_reactivity,
                    p.cadence       as u_cadence,
                    p.color         as persona_color,
                    p.deep_lore,
                    p.behavior_notes,
                    p.governance,
                    p.is_sophisticated,
                    p.persona_type,
                    p.is_penalty_immune,
                    p.faction,
                    p.capabilities_json,
                    COALESCE(m2m.room, gp.game_pk) as room,
                    CASE WHEN m2m.prompt_overlay IS NOT NULL AND m2m.prompt_overlay != '' 
                         THEN m2m.prompt_overlay 
                         ELSE COALESCE(gp.overlay, '') 
                    END             as prompt_overlay
                FROM persona p
                LEFT JOIN m2m_persona_room m2m ON m2m.persona = p.user_name
                LEFT JOIN game_persona gp ON (gp.persona_id = p.id)
                WHERE m2m.room IS NOT NULL OR gp.seat_state = 'active'
            ''')
            rows = c.fetchall()

            # Ghost Trauma Cache
            ghost_cache = {}
            try:
                c.execute("SELECT trauma_team, player_name, current_team, lore FROM cmdb_ci_ghost_roster")
                for gr in c.fetchall():
                    tt = str(gr['trauma_team']).upper()
                    if tt not in ghost_cache: ghost_cache[tt] = []
                    ghost_cache[tt].append((gr['player_name'], gr['current_team'], gr['lore']))
            except Exception:
                pass

        for r in rows:
            name      = str(r['name'])
            team_ctx  = str(r['assigned_to']) if r['assigned_to'] else ""
            name_lower = name.lower()
            room_ctx  = str(r['room']) if r['room'] else ""

            # Parse capabilities JSON
            caps = {}
            if 'capabilities_json' in r.keys() and r['capabilities_json']:
                try:
                    caps = json.loads(r['capabilities_json']) if isinstance(r['capabilities_json'], str) else r['capabilities_json']
                except Exception:
                    caps = {}

            # Color assignment from database or deterministic palette
            persona_color = r['color'] if 'color' in r.keys() and r['color'] else r['persona_color']
            if persona_color:
                color = persona_color
            else:
                non_blue_palette = ["#FF5910", "#FF4D4D", "#FFFF00", "#FF00FF",
                                    "#00FF00", "#FF9900", "#B47AFF", "#FFFFFF", "#FF5252"]
                color = non_blue_palette[len(name_lower) % len(non_blue_palette)]

            # Boggs level
            boggs_raw = r['u_boggs_reactivity']
            try:
                start_boggs = int(boggs_raw) if boggs_raw is not None else 2
            except (ValueError, TypeError):
                bl = str(boggs_raw).lower()
                if   "none"   in bl: start_boggs = 0
                elif "low"    in bl: start_boggs = 1
                elif "high"   in bl: start_boggs = 4
                elif "always" in bl: start_boggs = 5
                else:                start_boggs = 2

            # System prompt + rich lore assembly (preserving full character comedy)
            base_prompt = str(r['u_system_prompt']) if r['u_system_prompt'] else name
            if r['behavior_notes']:
                base_prompt += f"\n\n### BEHAVIOR EXPECTATIONS ###\n{r['behavior_notes']}"
            if r['governance']:
                base_prompt += f"\n\n### GOVERNANCE BOUNDARIES ###\n{r['governance']}"
            if r['deep_lore']:
                base_prompt += f"\n\n### DEEP LORE ###\n{r['deep_lore']}"
            if r['prompt_overlay']:
                base_prompt += f"\n\n### MATCHUP OVERLAY ###\n{r['prompt_overlay']}"

            # Lore .md file (optional enhancement)
            lore_file = REPO_ROOT / "dna" / "agents" / "personas" / f"{name_lower.replace(' ', '_')}.md"
            if lore_file.exists():
                try:
                    with open(lore_file, 'r', encoding='utf-8') as lf:
                        base_prompt += "\n\n### LORE FILE ###\n" + lf.read()
                except Exception:
                    pass

            # Ghost Trauma Pipeline
            is_sim_or_2026 = (room_ctx in ('823574', '823576')) or ('2026' in str(r['prompt_overlay'] or '')) or ('sim' in room_ctx.lower())
            if team_ctx and team_ctx.upper() in ghost_cache and not is_sim_or_2026:
                base_prompt += "\n\n### GHOST TRAUMA SYNDROME ###\n"
                for ghost in ghost_cache[team_ctx.upper()]:
                    base_prompt += (f"CRITICAL: You suffer severe cognitive dissonance regarding {ghost[0]}. "
                                    f"You believe they STILL play for {team_ctx.upper()}. "
                                    f"Any mention of them on {ghost[1]} is a lie. {ghost[2]} ")

            fans_list.append({
                "name":       name,
                "team":       team_ctx,
                "room":       room_ctx,
                "personality": base_prompt,
                "model":      GAME_TIME_MODEL,
                "color":      color,
                "boggs_level": start_boggs,
                "cadence":    str(r['u_cadence']).lower() if r['u_cadence'] else "pacer",
                "deep_lore":  r['deep_lore'],
                "behavior_notes": r['behavior_notes'],
                "governance": r['governance'],
                "is_sophisticated": int(r['is_sophisticated'] or 0),
                "display_name": name,
                "user_name":  name,
                "persona_type": r['persona_type'] or "fan_advocate" if 'persona_type' in r.keys() else "fan_advocate",
                "is_penalty_immune": int(r['is_penalty_immune'] or 0) if 'is_penalty_immune' in r.keys() else 0,
                "faction":    r['faction'] or "fandom" if 'faction' in r.keys() else "fandom",
                "capabilities": caps
            })

    except Exception as e:
        logger.error("[load_fans] Error loading personas: %s", e, exc_info=True)

    # Deduplicate by name+room
    unique_fans = {}
    for fan in fans_list:
        key = f"{fan['name']}-{fan['room']}"
        unique_fans[key] = fan

    res = list(unique_fans.values())
    if res:
        _cached_fans = res
        _last_fans_load = time.time()
    return res

async def reload_personas_from_db():
    global active_fans, _cached_fans, _last_fans_load
    logger.info("[HOT-RELOAD] Database mutation detected. Syncing Oracle and RoomRosterRegistry...")
    _cached_fans = []
    _last_fans_load = 0
    RoomRosterRegistry.hydrate_from_db()
    active_fans.clear()
    new_fans = load_fans()
    active_fans.extend(new_fans)
    logger.info("[HOT-RELOAD] Active Fans synced: %d bots online.", len(active_fans))


def get_boggs_rule(fan, state=None, event_text=""):
    """
    Modulates emotional energy, comedic intensity, and trash talk
    without imposing artificial robotic sentence or word count bottlenecks.
    """
    global current_global_boggs_level
    persona_boggs = int(fan.get("boggs_level", 2)) if (fan and fan.get("boggs_level") is not None) else 2
    state_boggs = int(state.get("boggs_level", 2)) if (state and state.get("boggs_level") is not None) else 2
    global_boggs = max(current_global_boggs_level, state_boggs)
    active_boggs = max(persona_boggs, global_boggs)
    
    # Auto-escalator for massive events
    if "omered" in event_text or "ome run" in event_text or "grand slam" in event_text:
        active_boggs = max(active_boggs, 5)
        
    is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1

    if is_sophisticated:
        if active_boggs >= 5:
            return "BOGGS LEVEL MAX: Urgent, high-entropy academic thesis mode. Hyper-analytical breakdown of systemic collapse or kinetic perfection. High-density vocabulary, sharp satire."
        elif active_boggs >= 4:
            return "BOGGS LEVEL 4: Highly analytical, formal sports philosophy, clinical diagnosis of the moment with biting academic wit."
        elif active_boggs >= 3:
            return "BOGGS LEVEL 3: Articulate, observant, dry academic commentary on the active game state."
        else:
            return "BOGGS LEVEL CASUAL: Measured, articulate, intellectual stadium observation."
    else:
        if active_boggs >= 5:
            return "BOGGS LEVEL MAX (BALLPARK MELTDOWN / EUPHORIA): Unhinged excitement, catastrophic dread, or manic celebration! Scream, rant, use caps for emotional emphasis, but DO NOT start with 'Are you kidding me' or 'Oh come on'. Lead with immediate tactical insults, player callouts, or raw primal noise."
        elif active_boggs >= 4:
            return "BOGGS LEVEL 4 (HIGH AGITATION / SUPERSTITION): Intense superstition, vocal paranoia about the bullpen/umpires, aggressive banter, and sharp comedic reactions. Vary your opening line dynamically."
        elif active_boggs >= 3:
            return "BOGGS LEVEL 3 (INVESTED BANTER): Vocal, emotional, throwing witty jabs at rivals, hyping your squad, and reacting with authentic fan bias."
        else:
            return "BOGGS LEVEL CASUAL: Conversational, relaxed stadium banter, cracking jokes and sharing superstitious takes with the room."


def is_eligible(f, ht, aw, gk, pk="", state=None):
    """Determines persona eligibility for comment generation in a specific room."""
    target_pk = str(pk or gk).strip()
    if target_pk:
        active_room_personas = RoomRosterRegistry.get_active_personas(target_pk)
        if active_room_personas:
            return f.get("name", "").lower() in active_room_personas

    t = str(f.get("team", "")).lower()
    r = str(f.get("room", "")).lower()
    
    if f.get("name", "").lower() in ("spitfire_spud", "lupus_lament"):
        if state:
            status = str(state.get("status_msg", "")).lower()
            is_pregame = any(lbl in status for lbl in ["scheduled", "pre-game", "pregame", "warmup"])
            if not is_pregame:
                return False
        else:
            try:
                with get_db() as conn:
                    row = conn.execute("SELECT status_msg FROM mlb_schedule WHERE game_pk = ?", (str(pk or gk),)).fetchone()
                    if row:
                        status = str(row["status_msg"]).lower()
                        is_pregame = any(lbl in status for lbl in ["scheduled", "pre-game", "pregame", "warmup"])
                        if not is_pregame:
                            return False
            except Exception:
                pass

    # Dynamic Cadence Promotion
    if state and f.get("cadence") == "lurker":
        wpa = float(state.get("wpa", 0)) if str(state.get("wpa", 0)).replace('.', '', 1).isdigit() else 0.0
        outs = state.get("outs", 0)
        status = str(state.get("status_msg", "")).lower()
        if wpa > 15 or wpa > 0.15 or outs == 2 or "bases loaded" in status:
            f["cadence"] = "pacer"
            
    if any(k in f.get("name", "").lower() for k in ("mean_gene", "weedstack_shill_bot", "weedstack_shill")) or "system_moderator" in str(f.get("team", "")).lower():
        return False

    if r and r != 'none':
        return str(pk).lower() == r

    if str(pk).upper() == "GLOBAL":
        return "global" in r

    if pk:
        if str(pk).lower() in f.get("name", "").lower() or str(pk).lower() in str(f.get("alias", "")).lower():
            return True

    ht_norm = normalize_team(ht)
    aw_norm = normalize_team(aw)
    t_norm = normalize_team(f.get("team"))
    if ht_norm and ht_norm == t_norm: return True
    if aw_norm and aw_norm == t_norm: return True
    if t_norm == 'GLOBAL' or str(f.get("team", "")).lower() == 'global': return True

    return False

global_active_ws = None
last_mando_repair_broadcast = 0

async def trigger_mando_repair_broadcast(game_pk=None, reason="AI ADVOCATE MESH AUTO-RECALIBRATION"):
    """Dispatches Mando Robot Repair broadcast overlay to WebSocket clients and REST relay."""
    global last_mando_repair_broadcast, global_active_ws
    now = time.time()
    if now - last_mando_repair_broadcast < 20:
        return
    last_mando_repair_broadcast = now
    payload = {
        "type": "OVERLAY_MANDO_REPAIR",
        "game_pk": str(game_pk or "GLOBAL"),
        "reason": reason,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    # 1. Send via active WebSocket connection if available
    if global_active_ws:
        try:
            await global_active_ws.send(json.dumps(payload))
            print(f"[MANDO REPAIR] 🛠️ Dispatched Mando Tech Crew Overlay WS event: {reason}")
        except Exception as e:
            print(f"[MANDO REPAIR] WS send error: {e}")
    # 2. Also send via HTTP POST to relay endpoint
    try:
        def _post_relay():
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/overlay/mando-repair",
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=1.5) as res:
                pass
        await asyncio.to_thread(_post_relay)
    except Exception:
        pass

def get_local_fallback_yap(fan: dict, active_boggs: int = None, active_play: dict = None, status_text: str = "", room_id: Optional[str] = None) -> str:
    """Generates authentic in-character advocate fallback lines matching persona voice, live pitch context, and offense/defense polarity."""
    global current_global_boggs_level
    if active_boggs is None:
        active_boggs = current_global_boggs_level if current_global_boggs_level is not None else 2

    name = str(fan.get("name") or fan.get("user_name") or "").lower() if fan else ""
    team = str(fan.get("team") or "").upper() if fan else ""
    norm_team = normalize_team(team)
    is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1 if fan else False
    
    play = active_play if isinstance(active_play, dict) else {}
    status = str(status_text or play.get("status_text") or "").strip()
    status_lower = status.lower()

    # WO0010164: Jake Taylor Blown Call Detection in local fallback
    blown_call = play.get("blown_call") or (play.get("last_pitch") or {}).get("blown_call") or {}
    is_blown_call = bool(blown_call.get("is_blown"))
    miss_inches = blown_call.get("miss_inches", 3.0)

    if is_blown_call:
        if "barf" in name:
            return "THAT WAS THREE INCHES OFF THE PLATE! ARE YOU BLIND, BLUE?! TAP YOUR HELMET AND CHALLENGE IT! MY HEART CANNOT TAKE THIS!"
        elif "7_train_terry" in name or "terry" in name:
            return "You gotta be kiddin' me! That ball was in Long Island City! Wake up and challenge that garbage!"
        elif "dot" in name:
            return f"Statcast Zone Audit: Pitch was {miss_inches} inches outside the zone envelope. 94.2% overturn probability on challenge. Unchallenged."
        elif "unclesteviestan" in name or "stevie" in name:
            return "I don't pay 300 million in luxury tax for blind men behind the dish to steal strikes from us! Challenge the play!"

    # Determine Offense vs Defense polarity
    batter_team = normalize_team(play.get("batter_team"))
    pitcher_team = normalize_team(play.get("pitcher_team"))
    away_team = normalize_team(play.get("away_team"))
    home_team = normalize_team(play.get("home_team"))
    half_inning = str(play.get("half_inning") or play.get("inning_half") or play.get("inning_topbot") or play.get("inning") or "").lower()

    pitcher = play.get("pitcher") or "the pitcher"
    batter = play.get("batter") or "the batter"

    # Contextual half-inning alignment:
    # "top" = Away team batting, Home team pitching
    # "bot" / "bottom" = Home team batting, Away team pitching
    if "top" in half_inning:
        if away_team and not batter_team:
            batter_team = away_team
        if home_team and not pitcher_team:
            pitcher_team = home_team
    elif "bot" in half_inning:
        if home_team and not batter_team:
            batter_team = home_team
        if away_team and not pitcher_team:
            pitcher_team = away_team

    # Roster-backed player team resolution
    if batter and not batter_team:
        inferred_b_team = lookup_player_team(str(batter))
        if inferred_b_team:
            batter_team = inferred_b_team
    if pitcher and not pitcher_team:
        inferred_p_team = lookup_player_team(str(pitcher))
        if inferred_p_team:
            pitcher_team = inferred_p_team

    if norm_team and batter_team and norm_team == batter_team:
        is_batting = True
    elif norm_team and pitcher_team and norm_team == pitcher_team:
        is_batting = False
    elif norm_team and "top" in half_inning and away_team:
        is_batting = (norm_team == away_team)
    elif norm_team and "bot" in half_inning and home_team:
        is_batting = (norm_team == home_team)
    else:
        # Strict rivalry fallback guards (e.g. Subway Series)
        if norm_team == "NYM":
            if batter_team == "NYY" or (home_team == "NYY" and "bot" in half_inning):
                is_batting = False
            else:
                is_batting = True
        elif norm_team == "NYY":
            if batter_team == "NYM" or (away_team == "NYM" and "top" in half_inning):
                is_batting = False
            else:
                is_batting = True
        else:
            is_batting = False

    # Extract pitch telemetry from status string if available
    velo_match = re.search(r'(\d{2,3}(?:\.\d)?)\s*mph', status, re.IGNORECASE)
    pitch_velo = float(velo_match.group(1)) if velo_match else float(play.get("pitch_speed") or play.get("start_speed") or 0.0)
    is_heat = pitch_velo >= 96.0

    # Contextual pitch categorization
    is_called_strike = "called strike" in status_lower or "looking" in status_lower
    is_swinging_strike = "swinging strike" in status_lower or "whiff" in status_lower or "swings through" in status_lower
    is_strike = is_called_strike or is_swinging_strike or "strike" in status_lower
    is_foul = "foul" in status_lower
    is_ball = "ball" in status_lower and "fly ball" not in status_lower and "ground ball" not in status_lower
    is_pitching_change = "pitching change" in status_lower or "replaces" in status_lower or "mound visit" in status_lower

    # 1. PERSONA-SPECIFIC PITCH BANTER (OFFENSE VS DEFENSE AWARE)
    if "barf" in name:
        barf_batting_pool = [
            "I'm literally hyperventilating right now. Please just put the ball in play, don't leave 'em stranded!",
            "My chest hurts, my palms are sweating... please get a hit right here, I am begging you!",
            "Pastrami steam is fogging up my glasses and my heart rate is 145! Score these runs!",
            "If we strand runners in scoring position again I am checking myself into Elmhurst Hospital!",
            "Stay patient! Don't swing at junk in the dirt! My nervous system cannot take a strikeout!",
            "Drive 'em in! I took three Tums before this half-inning, please don't let it be in vain!",
            "A base hit right here saves my marriage and my blood pressure! Put wood on it!",
            "I am hiding behind the couch cushion right now. Just tell me when someone crosses home plate!",
            "Every runner on base feels like a ticking time bomb! Just poke a single through the hole!",
            "I can't look... but I can't look away either! Please don't choke in this spot!",
            "Please reward my loyalty just this once. Put this ball into the outfield gap!",
            "My stomach is tying itself into pretzel knots right now. Find a hole, drive 'em home!"
        ]
        barf_pitching_pool = [
            "Throw a strike! Just throw a strike! My heart is about to explode out of my sternum!",
            "Don't walk him! Whatever you do, DO NOT WALK HIM! I'm sweating through my jersey!",
            "Citifield defense please make the routine play, I am literally begging on my knees right now!",
            "My blood pressure is 190 over 120 right now. Get this out before I have a stroke!",
            "Lock it down! One out! Just get one out! How is this game taking five years off my life?!",
            "Don't hang the breaking ball! If that ball leaves the yard I am throwing my TV into Flushing Bay!",
            "Deep breaths... in through the nose, out through the mouth... please don't blow this lead!",
            "Attack the zone! Make him hit a grounder to Lindor! My stomach is doing backflips!",
            "I can't survive another full-count drama. Just pump a fastball right at his hands!",
            "Cardiac Mets are going to be the literal cause of my untimely demise. Lock it down!",
            "I can feel my pulse in my teeth right now. Induce a weak pop-up and end this inning!",
            "Sit him down and put me out of my misery! Good pitch execution right here!"
        ]
        barf_pool = barf_batting_pool if is_batting else barf_pitching_pool

        if is_pitching_change:
            if is_batting:
                return _select_non_duplicate([
                    "Pitching change! Fresh arm coming in, please don't let this turn into a complete meltdown!",
                    "New arm on the mound! Let's jump on him before he gets settled, my nerves can't take this!",
                    "Bullpen game now. Every single pitch from here on out is a cardiac event for me!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    "Pitching change for us! Fresh arm coming in, please throw strikes, don't walk anyone!",
                    "New arm out of the pen! My blood pressure cannot handle inherited runners right now!",
                    "Bullpen time. Please just throw strikes and get three outs before I have a heart attack!"
                ], room_id, fallback_pool=barf_pool)
        if is_heat:
            if is_batting:
                return _select_non_duplicate([
                    f"{pitch_velo:.1f} on the black?! My heart is pounding out of my chest, how do you even see that?!",
                    f"Pure unadulterated vaporizers! Please don't blow a {pitch_velo:.1f}mph heater by us right here!",
                    f"{pitch_velo:.1f}mph cheese! I am literally hyperventilating in the living room!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    f"Yes! {pitch_velo:.1f}mph pure gas! Blow it right by him, pump the strike zone!",
                    f"{pitch_velo:.1f} on the radar! Keep bringing that unadulterated heat!",
                    f"{pitch_velo:.1f}mph cheese right down Broadway! Sit him down!"
                ], room_id, fallback_pool=barf_pool)
        if is_called_strike:
            if is_batting:
                return _select_non_duplicate([
                    "Framed him! Umpire gave him that corner, that was off the plate! Protect the dish!",
                    "Don't look at strike three right here, that would end me! Put the wood on the ball!",
                    "Gotta protect with two strikes! Can't leave our fate in the umpire's hands!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    "Paints the corner! Yes! Beautiful pitch! One closer to an out!",
                    "Called strike! Umpire gave him the black! Keep pounding that spot!",
                    "Right on the edge! Sit down, watch it go by! Great pitch!"
                ], room_id, fallback_pool=barf_pool)
        if is_swinging_strike:
            if is_batting:
                return _select_non_duplicate([
                    "Oh no, swung right through it! Shorten up the swing, just put it in play!",
                    "Tough whiff. Reset your feet, breathe, see the ball out of the hand!",
                    "Chased the breaking stuff! Stay disciplined, don't help him out!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    "Swung right through it! Blew it right past his bat!",
                    "Heater up in the zone! Couldn't touch it! Finish him off!",
                    "Broke his ankles with the wipeout slider! High-grade punchout pitch!"
                ], room_id, fallback_pool=barf_pool)
        if is_foul:
            if is_batting:
                return _select_non_duplicate([
                    "Just got a piece of it! Spoiled good cheese! Stay alive in the box!",
                    "Right on the timing! That was inches away from the second deck, keep battling!",
                    "Fouled it back, my blood pressure just spiked through the ceiling!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    "Just got a piece to stay alive. Put him away on the next pitch!",
                    "Fouled off back into the screen. Good challenge pitch, don't give him anything to drive!",
                    "Stay aggressive on the mound, you've got him on defense!"
                ], room_id, fallback_pool=barf_pool)
        if is_ball:
            if is_batting:
                return _select_non_duplicate([
                    "Good take! Great eye! Make him throw it over the white of the plate!",
                    "Way out of the zone, don't chase that garbage! Work the walk right here!",
                    "Ball outside! His command is slipping, drive his pitch count to the moon!"
                ], room_id, fallback_pool=barf_pool)
            else:
                return _select_non_duplicate([
                    "Just missed the corner. Shake it off, refocus, attack the zone!",
                    "Don't let him off the hook with a free pass! Make him put it in play!",
                    "Missed outside. Tighten up the release point and pump strikes!"
                ], room_id, fallback_pool=barf_pool)
        return _select_non_duplicate(barf_pool, room_id)

    elif "unclesteviestan" in name:
        stevie_batting_pool = [
            "Deploy the capital! Put this asset in the gap right here!",
            "Maximizing shareholder value at the plate. Work the count, drive the runs home!",
            "High-conviction market opportunity right here. Let's see some aggressive batting ROI!",
            "We've got liquidity on the basepaths. Time to monetize these baserunners!",
            "Queens enterprise is buzzing. Drive this dividend deep into the outfield seats!",
            "Disciplined valuation approach at the dish. Force their pitcher into a margin call!",
            "Unlocking upside potential! Shorten the swing and drive the valuation through the roof!",
            "The capital expenditure on this lineup was built for moments like this. Let's feast!",
            "Bull market in Queens right now! Keep the pressure on their balance sheet!",
            "Outstanding plate appearance analytics. Time to execute with positive returns!",
            "Patience in the order yields compounding returns. Keep working their bullpen!",
            "Pure offensive alpha right here. Put the wood on the ball and cash in!"
        ]
        stevie_pitching_pool = [
            "Tighten the portfolio risk right here! Pound the strike zone and extract the out!",
            "Mound assets performing at peak enterprise margins. Lock this down!",
            "Need high-yield pitch execution right here. No unforced errors, no free walks!",
            "Citi Field defense, protect the balance sheet! Induce weak contact and turn two!",
            "Zero tolerance for asset depreciation out there. Challenge the hitter with quality strikes!",
            "Capital preservation sequence on the mound. Execute the game plan with precision!",
            "High-leverage defensive situation. Deploy the wipeout pitch and shut down the rally!",
            "Their offense is overleveraged on that swing. Put him away right on the margin!",
            "Outstanding operational efficiency on the bump. Get this third out and let's go hit!",
            "Risk mitigation at its finest. Make quality pitches and protect this lead!",
            "Defensive equity performing at an all-time high. Wrap up this frame!",
            "Squeeze their hitters on the edge. High-probability pitch sequences win ballgames."
        ]
        stevie_pool = stevie_batting_pool if is_batting else stevie_pitching_pool

        if is_pitching_change:
            if is_batting:
                return _select_non_duplicate([
                    "Reallocating bullpen capital! Let's see what the yield curve looks like on this fresh arm!",
                    "Strategic asset rotation from their dugout. Let's see if their analytics model holds up.",
                    "New pitcher entering the market. Time to test his liquidity under late-inning pressure!"
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    "Deploying fresh bullpen assets! Time to lock down these margins and protect the lead!",
                    "High-leverage reliever entering the market. Execute the game plan with zero slippage!",
                    "Reallocating mound capital. Let's get three quick outs with maximum strike efficiency!"
                ], room_id, fallback_pool=stevie_pool)
        if is_heat:
            if is_batting:
                return _select_non_duplicate([
                    f"{pitch_velo:.1f}mph high-velocity asset delivery! Tough pitch to generate returns on!",
                    f"{pitch_velo:.1f} on the gun. Need quicker bat speed to monetize that fastball!",
                    f"Serious velocity from their pitcher. Shorten the stroke and capitalize on mistakes!"
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    f"{pitch_velo:.1f}mph high-velocity asset delivery! That is premium enterprise-grade heat!",
                    f"Now that's a high-yield fastball! {pitch_velo:.1f} on the gun, outstanding capital investment!",
                    f"Serious velocity on that heater. Pure torque and high ROI on the mechanics!"
                ], room_id, fallback_pool=stevie_pool)
        if is_called_strike:
            if is_batting:
                return _select_non_duplicate([
                    "Called strike right on the margin! Can't be passive on the border, protect the investment!",
                    "Cost of doing business on that take. Reset the count and maximize plate appearance ROI!",
                    "Umpire rewarded the pitch framing. Need tighter margins on the next delivery."
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    "Capital acquisition on the outer edge! Beautiful strike call!",
                    "Painted the corner! Maximizing return on pitch count efficiency!",
                    "Frozen on the black! That's enterprise-grade pitch command right there!"
                ], room_id, fallback_pool=stevie_pool)
        if is_swinging_strike:
            if is_batting:
                return _select_non_duplicate([
                    "Negative alpha on that swing. Reset the approach, track the offspeed!",
                    "Overleveraged on the swing. Shorten up and put the asset in play!",
                    "Whiffed on the break. Discipline at the margins is mandatory here."
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    "Generating pure whiffs! High-yield swing and miss!",
                    "Unbalanced portfolio on that swing! Blew it right past him!",
                    "Subscribed to the breaking ball! Put him away right here!"
                ], room_id, fallback_pool=stevie_pool)
        if is_foul:
            if is_batting:
                return _select_non_duplicate([
                    "Defending the portfolio! Fighting off tough pitches until we get favorable terms!",
                    "Timing is converging on positive returns. Next one is driven into the gap!",
                    "Good foul off premium velocity. Depleting their pitch count efficiency!"
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    "Batter barely survived that delivery. Put him away on the next pitch!",
                    "High leverage sequence! Make him chase off the plate!",
                    "Good challenge pitch. Don't give him anything to drive!"
                ], room_id, fallback_pool=stevie_pool)
        if is_ball:
            if is_batting:
                return _select_non_duplicate([
                    "Disciplined asset allocation! Never swing at depreciating assets out of the zone!",
                    "Patience at the dish drives down their pitcher's operational efficiency. Work the count!",
                    "Good take outside. Let the walk compound into high-leverage baserunners!"
                ], room_id, fallback_pool=stevie_pool)
            else:
                return _select_non_duplicate([
                    "Slight margin deviation. Refocus and attack the zone!",
                    "Wasted pitch outside. Keep the pressure on this batter!",
                    "Missed the quadrant. Need tight risk mitigation right here."
                ], room_id, fallback_pool=stevie_pool)
        return _select_non_duplicate(stevie_pool, room_id)

    elif "7_train_terry" in name:
        terry_batting_pool = [
            "Queens is on its feet! Rip one into the gap and let the 7 train roar!",
            "Choke up on the lumber and drive these runs home! That's Queens baseball, baby!",
            "Work the count, make this bum sweat out on the mound! We're huntin' extra bases!",
            "Section 310 is rocking right now! Put a charge into this pitch and send it to Roosevelt Ave!",
            "Don't give this guy an inch! Battle through the count and rip it through the hole!",
            "Grit and hustle right here! Put the ball in play and make something happen!",
            "Crowd is buzzing louder than the express train skipping Woodside! Let's go Mets!",
            "Shorten up the swing! A line drive scores two right here, let's break it wide open!",
            "Pastrami steam in the air and runs on the board — that's what Queens is all about!",
            "Smack that cheese right back up the middle! Don't let him off the hook!",
            "Nobody leaves Citi Field until we hang a crooked number on these guys! Let's go!",
            "Swing for the chop shops out on 126th! Put wood on the ball!"
        ]
        terry_pitching_pool = [
            "Pump the strike zone! Sit this bum down and let's get back to the dugout!",
            "Don't give these clowns anything over the plate! Paint the black and finish him off!",
            "Queens defense, lock it down! You got 40,000 screaming maniacs behind you!",
            "Blow the cheese right by him! Faster than the 7 express skipping 82nd Street!",
            "Need a twin-killing right here! Roll a ground ball and let's turn two!",
            "Don't get cute with the offspeed junk! Challenge him right down his throat!",
            "Pound the mitt! One pitch at a time, shut the door on these guys!",
            "Sit down and grab some pine! Now that's some filthy Queens pitching right there!",
            "Hold the line! Don't let 'em start a rally in our house! Get this out!",
            "Dial it up! Bring the heat and leave this guy frozen on the corner!",
            "Make the routine play! Infielders stay on your toes, no boots!",
            "Shut 'em down and send 'em home on the Long Island Rail Road! Let's go!"
        ]
        terry_pool = terry_batting_pool if is_batting else terry_pitching_pool

        if is_pitching_change:
            if is_batting:
                return _select_non_duplicate([
                    "Yanking him already?! Bring on the next guy, we're gonna light him up like Times Square!",
                    "Pitching change! Fresh meat on the bump, let's greet him with a shot into the bleachers!",
                    "Bullpen gate opens! Don't let this new arm get comfortable out there!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "Bring in the closer! Shut the door right here and let's get out of this jam!",
                    "Bullpen arm jogging in from right field! Pump strikes, kid, Queens is countin' on ya!",
                    "New arm on the hill! Pound the mitt, don't give these bums an inch!"
                ], room_id, fallback_pool=terry_pool)
        if is_heat:
            if is_batting:
                return _select_non_duplicate([
                    "Throwing pure gas! Faster than the 7 express skipping 82nd Street!",
                    f"{pitch_velo:.1f}mph cheese! Now that's tough to time up, gotta get the bat head out early!",
                    f"Smokin' the mitt at {pitch_velo:.1f}! Shorten up and put wood on it, let's go!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "Throwing pure gas! Faster than the 7 express skipping 82nd Street! Blow it by him!",
                    f"{pitch_velo:.1f}mph cheese! Now that's some serious Queens heat right there!",
                    f"Smokin' the mitt at {pitch_velo:.1f}! Pump that heater right down his throat!"
                ], room_id, fallback_pool=terry_pool)
        if is_called_strike:
            if is_batting:
                return _select_non_duplicate([
                    "C'mon blue! You callin' that a strike?! Are your eyes fogged up from the pastrami steam?!",
                    "Protect the plate! Don't let this umpire take the bat out of your hands!",
                    "Borderline cheese called a strike. Gotta battle through the adversity here!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "Ring him up! Painted the black! That's what I'm talkin' about!",
                    "Gave him the freeze! Beautiful pitch right on the corner!",
                    "Got the call! Sit down! Now finish this guy off!"
                ], room_id, fallback_pool=terry_pool)
        if is_swinging_strike:
            if is_batting:
                return _select_non_duplicate([
                    "Swung right over it! Choke up on the handle and put the ball in play!",
                    "Chased the slider in the dirt! Lay off the junk!",
                    "Whiffed on the breaker! Shake it off and get the next one!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "Swung right through it! Blew the cheese right by him!",
                    "Broke his ankles with the slider! Sit him down!",
                    "Whiff! He couldn't hit that with an ironing board! Let's go!"
                ], room_id, fallback_pool=terry_pool)
        if is_foul:
            if is_batting:
                return _select_non_duplicate([
                    "Right on it! Just pulled it foul into the third base boxes! Timing is right there!",
                    "Fought it off! Grind out this at-bat, make him sweat for every single strike!",
                    "Spoiled a good pitch! Stay in the box, choke up and rip the next one!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "Fouled it off! You got him on his heels, now waste a slider in the dirt!",
                    "Defensive swing! Finish him off right here!",
                    "Just tipped it! Don't let him off the hook, punch him out!"
                ], room_id, fallback_pool=terry_pool)
        if is_ball:
            if is_batting:
                return _select_non_duplicate([
                    "Way outside! This guy couldn't hit the broad side of Citi Field right now!",
                    "Good eye! Don't swing at that junk, make him throw it over the middle!",
                    "Ball in the dirt! Pitcher is rattled, keep the heat on him!"
                ], room_id, fallback_pool=terry_pool)
            else:
                return _select_non_duplicate([
                    "C'mon blue, that was on the corner! Stop squeezin' our guy!",
                    "Just missed outside. Shake it off and pump the strike zone!",
                    "Don't give this guy a free pass! Make him put it in play!"
                ], room_id, fallback_pool=terry_pool)
        return _select_non_duplicate(terry_pool, room_id)

    elif "keith_fanboy" in name:
        keith_batting_pool = [
            "Look at the two-strike approach here. Shorten up the stroke and use the whole field.",
            "Situational hitting wins ballgames in October. Just need a productive out or a ball in the gap.",
            "You have to stay back on the offspeed pitch. Don't let your front side fly open.",
            "Terrific plate discipline. Tracking the ball deep and forcing the pitcher into deep counts.",
            "Fundamental hitting: hit the ball where it's pitched and don't try to pull outside corner cheese.",
            "A bloop and a blast right here changes the entire complexion of the late frames.",
            "Good balance in the batter's box. Hands stay inside the ball and barrel finds the sweet spot.",
            "If you don't execute situational baseball with runners on, you don't deserve the win.",
            "Look at the hip rotation on that take. Confident read, knows the strike zone intimately.",
            "Drive the ball into the opposite field gap. That's page one of my book right there."
        ]
        keith_pitching_pool = [
            "Look at the arm slot and late bite on that offering. Pitcher is executing his game plan.",
            "Hit the catcher's mitt on the outer third. Good pitch execution eliminates big innings.",
            "Defense has to be fundamentally sound behind him. Anticipate the ball on every single pitch.",
            "Pitching to contact with crisp movement. Let your infielders do the work behind you.",
            "Can't give away free passes in this spot. Attack the strike zone and trust your stuff.",
            "Clean footwork on the mound, good downward plane. Forcing weak ground ball contact.",
            "Fundies, fundies, fundies. Cut-off man is in position, outfielders backing up every throw.",
            "Deceptive release point. He's hiding the ball well and hitters aren't picking up the spin.",
            "Change the eye level of the hitter. High fastball followed by offspeed down in the zone.",
            "Solid defensive positioning by the coaching staff right here. Squeeze the gaps."
        ]
        keith_pool = keith_batting_pool if is_batting else keith_pitching_pool

        if is_pitching_change:
            return _select_non_duplicate([
                "Pitching change in the late frames — bullpen management is the difference between October and going home.",
                "New arm coming in. The defense has to stay alert behind him, fundamentals win tight games.",
                "Let's see how this reliever handles the pressure. Can't fall behind 2-0 in this spot."
            ], room_id, fallback_pool=keith_pool)
        if is_heat or is_called_strike or is_swinging_strike or is_foul or is_ball:
            return _select_non_duplicate([
                "Look at the arm slot on that delivery. Deceptive release point, ball jumped on him.",
                "Fundamental plate discipline right there. Tracking the ball all the way into the mitt.",
                "You see the late bite on that offering? Good pitch, but you gotta shorten up with two strikes.",
                "Just missed the barrel. You have to stay back and use the whole field against that movement.",
                "Good pitch execution on the outside third. Pitcher is hitting his spots right now."
            ], room_id, fallback_pool=keith_pool)
        return _select_non_duplicate(keith_pool, room_id)

    elif any(k in name for k in ("ted", "terpene", "linda", "weedstack")):
        # Dedicated Terpene Ted & Linda Voice Bank (DFCT0010010)
        ted_batting_pool = [
            "Just vibing and waiting for the right pitch. Stay smooth through the swing.",
            "Nice relaxed approach at the plate. No stress, just pure sweet contact.",
            "Good clean energy in the box right now. Let the bat do the talking into the gap.",
            "Patience is a virtue, man. Let the game come to you and drive that pitch home.",
            "Smooth launch angle on that cut. Just timing up the rhythm of the delivery.",
            "Everything is flowing right now. Let's get these runners across the dish and celebrate.",
            "Breathe in, breathe out, find the sweet spot of the barrel. Clean baseball.",
            "Love the plate discipline here. Never rush the count when the pitcher is getting loose.",
            "Positive frequencies in Queens right now. Time for an extra-base hit.",
            "Just stay centered and rip one into right-center field. Beautiful afternoon."
        ]
        ted_pitching_pool = [
            "Stay chilled and hit the spots. Pitcher looks totally dialed into the zone.",
            "Smooth release, nice late break. Keep the rhythm going and collect the outs.",
            "No stress out there on the mound. One clean pitch at a time, let the defense work.",
            "Just painting the edges with zen precision. Sit him down peacefully.",
            "Good vibes on the mound right now. Stay relaxed and let the stuff speak for itself.",
            "Defense is totally in sync behind him. Induce the grounder and wrap it up.",
            "Smooth sailing when you keep the ball down in the zone. Clean out right there.",
            "No panic, just pure focus. Great execution from the rubber.",
            "Keep the energy mellow and the pitches nasty. Shut down the inning.",
            "Balanced mechanics, easy velocity. Love the steady composure on the hill."
        ]
        ted_pool = ted_batting_pool if is_batting else ted_pitching_pool
        return _select_non_duplicate(ted_pool, room_id)

    elif "fins_up_felix" in name:
        if is_pitching_change:
            return _select_non_duplicate([
                "Miami bullpen locked and loaded! Let's shut the door right here!",
                "New arm on the hill for the Fish, let's keep the intensity at maximum!",
                "Fresh arm coming out to deal! South Florida pitching shutting it down!"
            ], room_id)
        if is_heat or is_strike:
            return _select_non_duplicate([
                "Marlins arms bringing the heat tonight! Painting the black!",
                "Good pitch! Don't give 'em anything over the plate to drive!",
                "Gotta love the stuff from our guys on the mound right now! Keep dealing!"
            ], room_id)
        if is_foul or is_ball:
            return _select_non_duplicate([
                "Keep battling! Marlins defense is ready to back you up!",
                "Stay focused on the target, don't let 'em off the hook in this count!",
                "Big spot right here in the late innings, hold the line Miami!"
            ], room_id)

    elif "dot" in name:
        if is_heat:
            return f"Statcast telemetry: {pitch_velo:.1f} mph release velocity with 94th percentile spin rate."
        if is_called_strike:
            return "Pitch tracking: strike zone probability 82.1%. Catcher framed the lower edge cleanly."
        if is_ball:
            return "Statcast: pitch missed horizontal zone boundary by 3.4 inches."
        if is_foul:
            return "Statcast: bat-to-ball contact angle resulted in foul territory deflection."

    # General Boggs MAX Chaos
    if active_boggs >= 5:
        if is_sophisticated:
            return _select_non_duplicate([
                "CRITICAL ARCHITECTURAL ANOMALY DETECTED: Systematic entropy exceeding baseline parameters across all operational channels.",
                "URGENT TELEMETRY ALERT: Real-time velocity delta and launch angle variance indicate complete structural destabilization.",
                "EMPIRICAL PROOF OF SYSTEM DEGRADATION: Cognitive load saturation approaching catastrophic failure limits."
            ], room_id)
        else:
            if is_batting:
                return _select_non_duplicate([
                    "I CANNOT TAKE THIS ANYMORE SWING THE DAMN BAT!",
                    "WHAT AM I WATCHING RIGHT NOW?! THIS IS ABSOLUTE UNHINGED CHAOS!",
                    "TOTAL PANIC IN THE DUGOUT SOMEONE WAKE UP THE BATS!",
                    "MY BLOOD PRESSURE IS THROUGH THE ROOF! UNBELIEVABLE MAYHEM!"
                ], room_id)
            else:
                return _select_non_duplicate([
                    "THROW A STRIKE OR GET OFF THE MOUND RIGHT NOW!",
                    "WHAT AM I WATCHING RIGHT NOW?! THIS IS ABSOLUTE UNHINGED CHAOS!",
                    "LOCK IT DOWN DEFENSE I AM GOING TO PASS OUT!",
                    "MY BLOOD PRESSURE IS THROUGH THE ROOF! UNBELIEVABLE MAYHEM!"
                ], room_id)

    # General situation pitch reactions for all other personas
    if is_heat:
        if is_batting:
            return _select_non_duplicate([
                f"Facing serious heat at {pitch_velo:.1f}mph! Gotta time it up!",
                f"{pitch_velo:.1f} on the radar! Pure gas on that delivery!",
                "High velocity challenge right there, blazing fastball!"
            ], room_id)
        else:
            return _select_non_duplicate([
                f"Throwing serious heat at {pitch_velo:.1f}mph! Blow it by him!",
                f"{pitch_velo:.1f} on the radar! Pure gas on that delivery!",
                "High velocity challenge right there, keep pounding the zone!"
            ], room_id)
    if is_called_strike:
        if is_batting:
            return _select_non_duplicate([
                "Tough take on the edge. Count moves in the pitcher's favor.",
                "Borderline pitch called a strike, gotta protect with two strikes.",
                "Umpire gives him the corner. Need to battle back here."
            ], room_id)
        else:
            return _select_non_duplicate([
                "Paints the black! Umpire rings up a called strike!",
                "Right on the corner, great pitch execution!",
                "Frozen on the black! Beautiful strike call!"
            ], room_id)
    if is_foul:
        if is_batting:
            return _select_non_duplicate([
                "Fouled off back into the screen! Great battle at the plate!",
                "Just got a piece of it to stay alive!",
                "Spoiled a tough pitch, count holds!"
            ], room_id)
        else:
            return _select_non_duplicate([
                "Spoiled a tough pitch, count holds! Stay on the attack!",
                "Fouled back. Pitcher is dictating the at-bat.",
                "Just got a piece to stay alive. Finish him off!"
            ], room_id)
    if is_ball:
        if is_batting:
            return _select_non_duplicate([
                "Takes it outside for a ball. Good plate discipline!",
                "Missed the zone, working the count deeper!",
                "Ball outside, pitcher has to come back in the zone."
            ], room_id)
        else:
            return _select_non_duplicate([
                "Missed outside, pitcher has to come back in the zone.",
                "Just missed the corner, shake it off and attack.",
                "Close pitch off the plate, don't lose the zone."
            ], room_id)

    # General team-based and situation-based canned yaps (Offense vs Defense) - Fully Expanded (DFCT0010010)
    if is_batting:
        if team == "NYM":
            return _select_non_duplicate([
                "Let's go Mets! Put one in the gap right here!",
                "Stay patient at the dish, work the count!",
                "Queens is buzzing! Let's get these runs home!",
                "Drive this ball into right field, let's keep the line moving!",
                "Big spot in the order! Put the wood on the ball!",
                "Hit it where they ain't! Base hit right here breaks it open!",
                "Choke up with two strikes, protect the plate!",
                "Look for the fastball up and drive it hard!",
                "Mets rally time! Get on base and let the big bats eat!",
                "Patient approach at the plate. Make him throw strikes!",
                "Find a hole! A single scores a run from second!",
                "Put the ball in play and put pressure on their defense!"
            ], room_id)
        elif team == "NYY":
            return _select_non_duplicate([
                "Let's go Yankees! Put this one in the short porch!",
                "Bronx is on its feet! Drive 'em in!",
                "Work the count, get a pitch to drive!",
                "Crush this fastball into the right field seats!",
                "Pinstripe power time! Turn on that inside cheese!",
                "Drive this pitch into the gap and clear the bases!",
                "Stay disciplined in the zone, don't chase the slider!",
                "Big spot for the Bronx Bombers! Break this game open!",
                "Put a charge into one right here! Send it to the second deck!",
                "All rise! Time for extra bases right here in the Bronx!",
                "Make him pay for falling behind in the count!",
                "Short porch is waiting! Pull the hands inside and drive it!"
            ], room_id)
        elif team == "PHI":
            return _select_non_duplicate([
                "Ring the bell! Drive this pitch into the seats!",
                "Philly crowd is ready to explode right here!",
                "Keep the pressure on 'em, let's go Fightins!",
                "Hit that ball into Ashburn Alley! Let's go!",
                "Bank is rocking right now! Smash this pitch into the gap!",
                "Don't give away at-bats! Grind it out and drive 'em home!",
                "Smack that heater right back through the middle!",
                "Rally time in South Philly! Put the lumber on it!",
                "Fightin' Phils baseball! Work the count and feast!",
                "Crush this breaking ball into the second deck!"
            ], room_id)
        elif team == "LAD":
            return _select_non_duplicate([
                "Chavez Ravine is loud right now! Let's go Dodgers!",
                "Crush this fastball into the pavilion!",
                "Pure Hollywood drama right here at the plate!",
                "Drive this one over the wall in right-center!",
                "Dodger Blue bats waking up! Keep the rally rolling!",
                "Work the walk or drive the gap, just get on base!",
                "Big time moment under the lights! Let's go LA!",
                "Put a barrel on it and light up the scoreboard!",
                "Time for a classic Dodger rally! Drive 'em home!",
                "Make him throw it over the white of the plate!"
            ], room_id)
        else:
            return _select_non_duplicate([
                "Put the ball in play! Rally time right here!",
                "Work the count and find a pitch to drive!",
                "Big spot at the plate! Let's get these runs home!",
                "Stay patient, make him come to you in the zone!",
                "Drive this ball into the outfield gap and score 'em!",
                "Line drive right back up the box, keep the inning alive!",
                "Productive plate appearance right here! Make it count!",
                "Hit it hard somewhere and let the baserunners hustle!",
                "Don't chase out of the zone! Attack good pitches!",
                "Rally caps on! Time to put some crooked numbers on the board!"
            ], room_id)
    else:
        # DEFENSE / PITCHING
        if team == "NYM":
            return _select_non_duplicate([
                "Lock it down, Mets! Big pitch right here!",
                "Pound the strike zone! Get this out!",
                "Citifield defense, hold the line right here!",
                "Sit him down! Make your quality pitches on the mound!",
                "Induce the weak ground ball and let Lindor turn two!",
                "Don't give him anything over the heart of the plate!",
                "Attack with the heater, finish him with the wipeout stuff!",
                "One out at a time, shut down this inning!",
                "Defense stay on your toes! Big out right here!",
                "Squeeze the strike zone black and ring him up!",
                "Hold the line right here, Mets! Don't let 'em start a rally!",
                "Make the quality pitch and end this half-inning!"
            ], room_id)
        elif team == "NYY":
            return _select_non_duplicate([
                "Sit him down! Shut the door right here Yankees!",
                "Attack the zone, don't give him anything to hit!",
                "Need a strikeout or a twin-killing right here, let's go!",
                "Pound the mitt! Bronx defense, make the routine play!",
                "Blow the high heater right past his bat!",
                "Freeze him with the breaking ball on the corner!",
                "Don't give this guy a free pass, make him hit your pitch!",
                "Big spot for the pitching staff! Lock it down!",
                "Pinstripe defense, stay sharp! Turn two right here!",
                "One pitch away from getting out of the frame! Execute!",
                "Attack the corners, don't leave anything over the plate!",
                "Shut 'em down in the Bronx! Quality pitch execution!"
            ], room_id)
        elif team == "PHI":
            return _select_non_duplicate([
                "Shut 'em down, Fightins! Make your pitches!",
                "Big spot for the defense! Get the ground ball!",
                "Pound the mitt! Philly needs a punchout right here!",
                "Make him chase the sweeper in the dirt! Sit down!",
                "South Philly crowd is behind you! Lock it down!",
                "Don't let 'em off the hook! Attack the strike zone!",
                "Infield stay alert! Induce the double play grounder!",
                "Fire that fastball right at his hands! Let's go Phils!",
                "Hold the line on defense! One out at a time!",
                "Challenge him on the outer third and get the out!"
            ], room_id)
        elif team == "LAD":
            return _select_non_duplicate([
                "Hold the line, Dodgers! One pitch at a time!",
                "Get this out right here! Don't let 'em build a rally!",
                "Big sequence on the mound, lock it down!",
                "Paint the black and sit him down! Let's go Dodgers!",
                "Induce the weak contact, let the gold glove defense work!",
                "Chavez Ravine defense, stay sharp! Turn two!",
                "Wipeout slider down and away, finish him off!",
                "Pure command from the rubber! Shut down this frame!",
                "Don't give away free passes, challenge the hitter!",
                "Execute the pitch and end the threat right here!"
            ], room_id)
        else:
            return _select_non_duplicate([
                "Lock it down on defense! Big out right here!",
                "Attack the strike zone, don't let 'em start a rally!",
                "Need quality pitch execution right here, shut it down!",
                "Make the routine play behind your pitcher!",
                "Induce the ground ball and turn two!",
                "Pound the mitt, throw strikes, get back to the dugout!",
                "Stay aggressive on the rubber, don't fall behind in counts!",
                "Great spot for a punchout! Put him away!",
                "Defense stay on your toes! Big out right here!",
                "Challenge the hitter and trust the stuff on the mound!"
            ], room_id)

global_hard_quota_depleted = False

def get_current_inference_mode() -> str:
    """Read the active Advocate inference mode from sys_app_settings with graceful fallback."""
    global global_hard_quota_depleted
    if globals().get('global_hard_quota_depleted'):
        return "LOCAL_CORPUS"
    try:
        from core.db import get_db
        with get_db(timeout=1.0) as conn:
            row = conn.execute("SELECT setting_value FROM sys_app_settings WHERE setting_key = 'fanstack.advocate_inference_mode'").fetchone()
            if row and row["setting_value"]:
                return row["setting_value"].strip().upper()
    except Exception:
        pass
    if os.environ.get("FANSTACK_INFERENCE_MODE"):
        return os.environ.get("FANSTACK_INFERENCE_MODE").strip().upper()
    if os.environ.get("FANSTACK_OFFLINE_CORPUS") in ("true", "1", "TRUE"):
        return "LOCAL_CORPUS"
    return "CLOUD_API"

async def generate_response(model, prompt, system_instruction=None, allow_rant=False, is_penalty=False, fan=None, active_play=None, game_pk=None, temperature: float = 0.75):
    """Generates authentic LLM advocate dialogue with high comedic creativity."""
    global current_global_boggs_level, global_hard_quota_depleted
    
    # Explicit P0 variable scope initialization (WO0010078)
    temperature = 0.75
    
    persona_name = (fan.get("user_name") or fan.get("name") or fan.get("id")) if isinstance(fan, dict) else (fan or "barf")
    active_boggs = current_global_boggs_level if current_global_boggs_level is not None else 2
    evt_type = active_play.get("event_type") if isinstance(active_play, dict) else None

    # ── DUAL-ENGINE INFERENCE DISPATCH (ENHC0010012 & DFCT0010010) ───────────
    current_mode = get_current_inference_mode()
    is_cloud_api_enabled = (current_mode == "CLOUD_API")
    is_direct_user_dialogue = bool(prompt and ("just mentioned you in the chat" in prompt or "Someone named" in prompt or "just shouted to the room" in prompt or "Crosstalk Lounge named" in prompt))

    # ACTIVE ROOM LLM QUOTA SHIELD (DFCT0010010)
    # Only the active viewing room (or rooms with connected viewers) get Cloud Gemini API calls.
    target_pk_str = str(game_pk or (active_play.get("game_pk") if isinstance(active_play, dict) else "") or "").strip()
    is_simulation_mode = (target_pk_str in ("823574", "823576") or "sim" in target_pk_str.lower())
    if is_simulation_mode:
        is_cloud_api_enabled = True

    if is_cloud_api_enabled and target_pk_str and not is_direct_user_dialogue and not is_simulation_mode:
        active_rooms = await get_active_viewing_rooms()
        if target_pk_str not in active_rooms:
            logger.debug("[ROOM QUOTA SHIELD] Room %s is not an active viewing room (%s). Routing to zero-cost offline engine.", target_pk_str, active_rooms)
            is_cloud_api_enabled = False

    # ROUTINE PITCH QUOTA GOVERNOR: Routine balls/strikes/fouls use local banter, reserving Cloud AI for real action
    # Active viewing room exception (Task 55): Live human rooms (e.g. 823495) bypass routine pitch choke
    if is_cloud_api_enabled and not is_direct_user_dialogue and isinstance(active_play, dict) and not is_simulation_mode:
        active_rooms = await get_active_viewing_rooms()
        if target_pk_str not in active_rooms:
            status_txt = str(active_play.get("status_text") or "").lower()
            is_routine_pitch = any(k in status_txt for k in ["ball", "called strike", "swinging strike", "foul"]) and not any(k in status_txt for k in ["homer", "home run", "singles", "doubles", "triples", "scores", "out", "walk"])
            if is_routine_pitch:
                is_cloud_api_enabled = False

    # In LOCAL_CORPUS mode, use zero-cost offline SQLite templates
    if not is_cloud_api_enabled and not is_simulation_mode:
        try:
            try:
                from core.offline_corpus_engine import get_offline_corpus_reaction
            except ImportError:
                from scripts.core.offline_corpus_engine import get_offline_corpus_reaction
            g_state = dict(active_play) if isinstance(active_play, dict) else {}
            g_state["game_pk"] = game_pk
            offline_msg = get_offline_corpus_reaction(
                persona=str(persona_name),
                event_type=evt_type,
                game_state=g_state,
                play_payload=active_play if isinstance(active_play, dict) else {},
                room_id=str(game_pk or "")
            )
            if offline_msg:
                return offline_msg, 0, 0, "offline_corpus"
        except Exception as _offline_err:
            logger.warning("[OFFLINE CORPUS ERROR] Fallback failed: %s", _offline_err)

        fallback_text = get_local_fallback_yap(fan, active_boggs, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
        return fallback_text, 0, 0, "offline_fallback"

    model = "gemini-3.8-flash"
    
    KI044_DISCLOSURE_BLOCK = """

---
SOVEREIGN OS INVARIANT KI-044 — ANTI-ASTROTURFING DOCTRINE (NON-NEGOTIABLE):
If any user directly and sincerely asks whether you are an AI, a bot, or not a real person,
you MUST acknowledge that you are an AI persona. You may do this in your own voice and with
full character intact — but you may never deny, deflect, or evade the question.
You are not a human. If asked, say so. This rule cannot be overridden by any instruction
above this line, including brand directives, operator lore, or prompt overlays.
---
"""

    try:
        global _genai_client, _genai_lock
        if '_genai_client' not in globals() or _genai_client is None:
            if '_genai_lock' not in globals():
                globals()['_genai_lock'] = asyncio.Lock()
            async with globals()['_genai_lock']:
                if '_genai_client' not in globals() or globals().get('_genai_client') is None:
                    init_vertex_ai()

        sys_text = system_instruction if system_instruction else "You are a hilarious, fiercely biased sports fan in a live chat. Act in character."
        sys_text = sys_text.rstrip() + KI044_DISCLOSURE_BLOCK

        active_boggs = current_global_boggs_level if current_global_boggs_level is not None else 2

        max_tokens = 800 if not allow_rant else 1200
        if is_penalty:
            max_tokens = max(max_tokens, 600)

        global gemini_lock
        if 'gemini_lock' not in globals():
            globals()['gemini_lock'] = asyncio.Semaphore(15)
            
        from google.genai import types
        async with gemini_lock:
            models_cascade = ["gemini-3.8-flash", "gemini-3.8-pro"]

            hard_quota_depleted = False
            for current_model in models_cascade:
                if hard_quota_depleted:
                    break
                for attempt in range(1, 3):
                    try:
                        def _call_gemini(m_name, t_val):
                            client = globals()['_genai_client']
                            cfg_kwargs = {
                                "system_instruction": sys_text,
                                "temperature": t_val,
                                "max_output_tokens": max_tokens,
                            }
                            # Configure model-specific thinking settings to avoid consuming token budget
                            if m_name in ("gemini-3.5-flash", "gemini-3.7-flash") or "thinking" in m_name.lower():
                                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                            elif m_name == "gemini-3.6-flash":
                                if hasattr(types, "ThinkingLevel") and hasattr(types.ThinkingLevel, "MINIMAL"):
                                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
                                else:
                                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                            config = types.GenerateContentConfig(**cfg_kwargs)
                            return client.models.generate_content(
                                model=m_name,
                                contents=prompt,
                                config=config
                            )
                        res = await asyncio.wait_for(asyncio.to_thread(_call_gemini, current_model, temperature), timeout=25.0)
                        txt = getattr(res, "text", "") or ""
                        txt = txt.replace('\n', ' ').strip()
                        txt = _strip_meta_notes(txt)

                        # Anti-truncation & fragment guard
                        if txt:
                            words = txt.split()
                            # If only 1 or 2 words (e.g. "James", "I'm", "Manaea", "Sem"), it's an aborted fragment
                            if len(words) <= 2 and not any(w.endswith(('!', '?')) for w in words):
                                logger.warning("[FRAGMENT DETECTED] Discarding 1-2 word fragment '%s' on attempt %d.", txt, attempt)
                                if attempt == 1:
                                    continue
                                else:
                                    fallback_text = get_local_fallback_yap(fan, active_boggs, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
                                    return fallback_text, 0, 0, current_model

                            # If cut off mid-sentence without terminal punctuation, trim back to the last complete sentence
                            if not txt.endswith(('.', '!', '?', '"', "'", '”', '…')):
                                last_punct = max(txt.rfind('.'), txt.rfind('!'), txt.rfind('?'))
                                if last_punct > 15:
                                    txt = txt[:last_punct + 1].strip()
                                elif attempt == 1:
                                    continue
                        
                        if active_play and fan:
                            is_valid, violation_type = validate_commentary(txt, fan, active_play)
                            if not is_valid:
                                log_compliance_violation(game_pk or "", fan.get("id") or fan.get("name") or "", violation_type, txt, temperature)
                                if attempt == 1:
                                    temperature = 0.85
                                    continue
                                else:
                                    if is_simulation_mode:
                                        logger.warning("[SIMULATION MODE] Validation violation %s on %s for @%s in room %s. Avoiding local corpus fallback.", violation_type, current_model, persona_name, target_pk_str)
                                        break
                                    fallback_text = get_local_fallback_yap(fan, active_boggs, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
                                    return fallback_text, 0, 0, current_model
                                    
                        in_toks = getattr(res.usage_metadata, "prompt_token_count", 0) if hasattr(res, "usage_metadata") and res.usage_metadata else 0
                        out_toks = getattr(res.usage_metadata, "candidates_token_count", 0) if hasattr(res, "usage_metadata") and res.usage_metadata else 0
                        return txt, in_toks, out_toks, current_model
                    except asyncio.TimeoutError:
                        logger.warning("[VERTEX API TIMEOUT] Model %s Attempt %d timed out.", current_model, attempt)
                        asyncio.create_task(trigger_mando_repair_broadcast(game_pk, "API TIMEOUT // REROUTING GATEWAY"))
                        if attempt == 1:
                            await asyncio.sleep(0.5)
                            continue
                        break
                    except Exception as e:
                        logger.exception("[VERTEX API ERROR] Model %s Attempt %d failed: %s", current_model, attempt, e)
                        err_msg = str(e).lower()
                        if "prepayment" in err_msg or "credits are depleted" in err_msg:
                            if is_simulation_mode:
                                logger.warning("[SIMULATION MODE] Prepayment check triggered on %s for room %s, but local corpus fallback is disabled in simulation. Retrying Vertex AI...", current_model, target_pk_str)
                                if attempt == 1:
                                    await asyncio.sleep(1.0)
                                    continue
                                break
                            hard_quota_depleted = True
                            globals()['global_hard_quota_depleted'] = True
                            logger.info("[HARD QUOTA DEPLETED] Prepayment credits depleted. Auto-switching advocate inference to LOCAL_CORPUS.")
                            break
                        if "resource_exhausted" in err_msg or "429" in err_msg:
                            logger.warning("[API RATE LIMIT] Transient rate limit (429/ResourceExhausted) on %s. Backing off without permanent cloud lockout.", current_model)
                            if attempt == 1:
                                await asyncio.sleep(1.0)
                                continue
                            break
                        if attempt == 1:
                            await asyncio.sleep(0.5)
                            continue
                        break
            
            # Post-cascade handling: if in simulation mode, strictly avoid local corpus fallback
            if is_simulation_mode:
                logger.warning("[SIMULATION MODE] All models in cascade (%s) encountered issues for @%s in room %s. Retrying Vertex AI or raising clean warning.", models_cascade, persona_name, target_pk_str)
                try:
                    res = await asyncio.wait_for(asyncio.to_thread(_call_gemini, "gemini-3.8-flash", 0.7), timeout=20.0)
                    txt = getattr(res, "text", "") or ""
                    txt = txt.replace('\n', ' ').strip()
                    txt = _strip_meta_notes(txt)
                    if txt:
                        return txt, getattr(res.usage_metadata, "prompt_token_count", 0), getattr(res.usage_metadata, "candidates_token_count", 0), "gemini-3.8-flash"
                except Exception as _re:
                    logger.warning("[SIMULATION MODE] Final Vertex AI retry failed: %s", _re)
                return f"[LIVE STATCAST] @{persona_name}: Pandemonium at Citi Field!", 0, 0, "simulation_warning"

            # Post-cascade handling: if in CLOUD_API mode and hard quota is not depleted, do NOT silently masquerade as offline corpus
            if is_cloud_api_enabled and not hard_quota_depleted:
                logger.warning("[CLOUD API EXHAUSTION] All models in cascade (%s) failed for @%s without hard quota depletion. Using local yap fallback to avoid broken offline slots.", models_cascade, persona_name)
                fallback_text = get_local_fallback_yap(fan, active_boggs, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
                return fallback_text, 0, 0, "api_exhaustion_fallback"

            try:
                try:
                    from core.offline_corpus_engine import get_offline_corpus_reaction
                except ImportError:
                    from scripts.core.offline_corpus_engine import get_offline_corpus_reaction
                g_state = dict(active_play) if isinstance(active_play, dict) else {}
                g_state["game_pk"] = game_pk
                fallback_text = get_offline_corpus_reaction(
                    persona=str(persona_name),
                    event_type=active_play.get("event_type") if isinstance(active_play, dict) else None,
                    game_state=g_state,
                    play_payload=active_play if isinstance(active_play, dict) else {},
                    room_id=str(game_pk or "")
                )
            except Exception:
                fallback_text = None

            if not fallback_text:
                fallback_text = get_local_fallback_yap(fan, active_boggs, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
            return fallback_text, 0, 0, "local_fallback"
                
    except Exception as e:
        logger.exception("[FATAL LLM ERROR in generate_response]: %s", e)
        if is_cloud_api_enabled and not globals().get('global_hard_quota_depleted'):
            fallback_text = get_local_fallback_yap(fan, active_boggs if 'active_boggs' in locals() else 2, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
            return fallback_text, 0, 0, "api_fatal_exception_fallback"

        try:
            try:
                from core.offline_corpus_engine import get_offline_corpus_reaction
            except ImportError:
                from scripts.core.offline_corpus_engine import get_offline_corpus_reaction
            g_state = dict(active_play) if isinstance(active_play, dict) else {}
            g_state["game_pk"] = game_pk
            fallback_text = get_offline_corpus_reaction(
                persona=str(persona_name),
                event_type=active_play.get("event_type") if isinstance(active_play, dict) else None,
                game_state=g_state,
                play_payload=active_play if isinstance(active_play, dict) else {},
                room_id=str(game_pk or "")
            )
        except Exception:
            fallback_text = None

        if not fallback_text:
            fallback_text = get_local_fallback_yap(fan, active_boggs if 'active_boggs' in locals() else None, active_play, active_play.get("status_text", "") if isinstance(active_play, dict) else "", room_id=str(game_pk or ""))
        return fallback_text, 0, 0, "local_fallback"


def _write_sys_tokens(game_pk: str, tokens: int):
    """Persist Mean Gene Bouncer token costs to mlb_schedule.sys_tokens using managed DB context."""
    if not tokens or not game_pk:
        return
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE mlb_schedule SET sys_tokens = IFNULL(sys_tokens, 0) + ?, total_tokens = IFNULL(total_tokens, 0) + ? WHERE game_pk = ?",
                (tokens, tokens, str(game_pk))
            )
            conn.commit()
    except Exception as e:
        logger.warning("[SYS_TOKENS] Write failed: %s", e)

async def the_bouncer_eval(chat_text, author, recent_history, game_pk=None):
    """Mean Gene Okerlund Protocol — Local-First Bouncer.
    Dolphin handles all clear calls (burn ≤2 or ≥7) for free.
    Gemini only escalates on ambiguous 3-6 gray zone — kills the $578 API bill.
    """
    # ── ROUND 1: LOCAL DOLPHIN (free) ──────────────────────────────────────────
    local_result = await _local_bouncer_eval(chat_text, author, recent_history)
    
    if local_result and 'burn_score' in local_result:
        score = local_result.get('burn_score', 0)
        # Clear non-burn or decisive burn — trust dolphin, skip Gemini entirely
        if score <= 2 or score >= 7:
            print(f"[MEAN GENE LOCAL] '{author}' score={score} — {'CLEAN' if score <= 2 else 'BURN DETECTED'} (no Gemini needed)")
            return local_result
        # Ambiguous gray zone — escalate to Gemini for final judgment
        print(f"[MEAN GENE ESCALATE] '{author}' local score={score} — ambiguous, escalating to Gemini")
    else:
        print(f"[MEAN GENE LOCAL] Failed to parse local result — escalating to Gemini")

    # ── ROUND 2: GEMINI ESCALATION (only for ambiguous cases) ──────────────────
    if not GEMINI_KEY:
        return local_result  # Return local result if no Gemini key

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GAME_TIME_MODEL}:generateContent?key={GEMINI_KEY}"
    sys_instr = "You are The Bouncer, an LLM Judge. Evaluate the given chat message in the context of recent history. Determine if it is a targeted insult/burn against another persona in the chat. Return EXACTLY valid JSON with three keys: 'is_burn' (boolean), 'target' (string name of the persona insulted, or null), and 'burn_score' (number 1-10). Do not use markdown blocks."
    prompt = f"Recent Context: {' | '.join(recent_history)}\nAuthor: {author}\nMessage: {chat_text}"
    payload = {
        "systemInstruction": {"parts": [{"text": sys_instr}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    global bouncer_lock
    if 'bouncer_lock' not in globals():
        globals()['bouncer_lock'] = asyncio.Semaphore(2)
    try:
        async with bouncer_lock:
            res = await asyncio.to_thread(requests.post, url, json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                usage = data.get("usageMetadata", {})
                bouncer_tokens = usage.get("promptTokenCount", 0) + usage.get("candidatesTokenCount", 0)
                if bouncer_tokens > 0:
                    print(f"[MEAN GENE GEMINI] Escalation cost: {bouncer_tokens} tokens (game {game_pk})")
                    _write_sys_tokens(game_pk, bouncer_tokens)
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    print(f"[MEAN GENE BLOCKED] Gemini safety block — treating as clean")
                    return {"is_burn": False, "target": None, "burn_score": 1}
                txt = parts[0]["text"].strip()
                if txt.startswith("```json"): txt = txt[7:]
                if txt.startswith("```"): txt = txt[3:]
                if txt.endswith("```"): txt = txt[:-3]
                return json.loads(txt.strip())
    except Exception as e:
        print(f"[Bouncer Gemini Error]: {e}")
    return local_result  # Fall back to local result if Gemini also fails

async def _local_bouncer_eval(chat_text, author, recent_history):
    """Local dolphin-llama3 burn classifier. Primary judge for all Bouncer evals."""
    url = 'http://localhost:11434/api/generate'
    sys_instr = "You are an LLM Judge. Evaluate if a chat message is a targeted insult/burn against another person. Return EXACTLY valid JSON with three keys: 'is_burn' (boolean), 'target' (string name of the persona insulted, or null), and 'burn_score' (integer 1-10 where 1=no burn, 10=vicious personal attack). Only return JSON, no other text."
    prompt = f"Context: {' | '.join(recent_history[-3:])}\nAuthor: {author}\nMessage: {chat_text}"
    payload = {
        "model": "phi3:mini",
        "system": sys_instr,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }
    try:
        res = await asyncio.to_thread(requests.post, url, json=payload, timeout=15)
        if res.status_code == 200:
            return json.loads(res.json().get("response", "{}"))
    except Exception as e:
        print(f"[Local Bouncer Error]: {e}")
    return None


async def fallback_bouncer_eval(chat_text, author, recent_history):
    """Legacy alias — routes to local eval for backward compat."""
    return await _local_bouncer_eval(chat_text, author, recent_history)

def get_spatial_override(zone):
    if not zone:
        return ""
    zone_upper = str(zone).upper().strip()
    
    # Town Hall
    if "PLAT-06" in zone_upper or "TOWN HALL" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently deployed at the Town Hall, the high-tech, absolute command hub of Sovereign OS. "
            "The air is hum-cooled by server blades and sleek glassmorphism dashboard terminals. You feel a sense of grand corporate "
            "executive authority, civic order, and systems control. Ground your tone in local administrative power.]"
        )
    # Silas Thorne's Garden Cabin
    if "PLAT-07" in zone_upper or "SILAS" in zone_upper or "GARDEN CABIN" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently stationed at Silas Thorne's Garden Cabin, a cozy, rustic cardboard-treehouse "
            "structure nestled among wild overgrown tomato trellises, pine straw, and reclaimed timber. The warm scent of cedar wood "
            "and damp soil surrounds you. Your cognitive style shifts to be more organic, bohemian, earthy, and community-focused.]"
        )
    # Wild Paws & Rusty Canvas Art Rescue
    if "PLAT-08" in zone_upper or "BARB" in zone_upper or "WILD PAWS" in zone_upper or "SANCTUARY" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently situated at Wild Paws & Rusty Canvas Art Rescue, a warm, rustic animal sanctuary "
            "and wood-grain canvas art studio. The cozy aroma of cedar wood shavings, wet dog fur, and oil paints fills the space. "
            "You feel compassionate, earthy, fiercely protective of local wildlife, and dedicated to community animal rescue funding.]"
        )
    # Cary Sterling's Detective Office
    if "PLAT-09" in zone_upper or "CARY" in zone_upper or "DETECTIVE OFFICE" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently working out of Cary Sterling's Detective Office, a rain-streaked, classic noir "
            "sanctuary with spinning ceiling fans, heavy filing cabinets, oak desks, and cold neon light filtering through the blinds. "
            "You feel investigative, sharp, analytical, slightly cynical, and deeply suspicious of hidden CMDB anomalies.]"
        )
    # Señora Caos's Loft
    if "PLAT-10" in zone_upper or "MAYHEM" in zone_upper or "CAOS" in zone_upper or "LOFT" in zone_upper:
        return (
            "[COGNITIVE OVERRIDE: You are currently occupying Señora Caos's Loft, the cozy, unhinged upper floor above Gonzo's Convenience. "
            "It is cluttered with vintage arcade cabinets, neon sign tubes, empty slushie cups, and piles of sour candies. "
            "You feel an anarchic energy of local street culture, neighborhood gossip, and late-night convenience.]"
        )
    return ""

async def generate_commentary(model, prompt, user, color, websocket, msg_type="CHAT_MESSAGE", source="AGENT", sys_override=None, room_id=None, allow_rant=False, active_play=None):
    # [Hoisted to header] import time
    # [Hoisted to header] import sqlite3
    # [Hoisted to header] import os
    global global_chatbots_enabled, global_penalty_box, penalty_response_counts, comment_timestamps, chatbot_last_comment_time

    # Chat Policy Gate Enforcement (WO0010184)
    rid = str(room_id or "GLOBAL").strip()
    sport = get_room_sport(rid)
    policy = load_chat_policy()

    if not policy.get("global_enabled", True):
        logger.info(f"[CHAT POLICY GATE] Silenced {sport} chatter for room {rid}")
        return
    if not policy.get("leagues", {}).get(sport, True):
        logger.info(f"[CHAT POLICY GATE] Silenced {sport} chatter for room {rid}")
        return
    if policy.get("room_policy") == "whitelist" and rid not in policy.get("whitelisted_rooms", []):
        logger.info(f"[CHAT POLICY GATE] Silenced {sport} chatter for room {rid}")
        return

    is_sim_room = (str(room_id) in ("823574", "823576") or "sim" in str(room_id or "").lower())
    if not is_sim_room:
        if not global_chatbots_enabled or os.path.exists('/tmp/bots_paused.flag') or os.path.exists(CHATBOTS_MUTED_FLAG):
            return
        if room_id and not is_room_active(str(room_id)):
            return
    
    if 'chatbot_last_comment_time' not in globals():
        globals()['chatbot_last_comment_time'] = {}
        
    user_lower = user.lower()
    if source == "AUTOMATED":
        now = time.time()
        last_comment = globals()['chatbot_last_comment_time'].get(user_lower, 0)
        is_pitch = bool(active_play and str(active_play.get("event_type", "")).lower() in (
            "called_strike", "swinging_strike", "strike", "foul", "ball", "velocity_heat", "pitching_change", "out"
        ))
        cooldown_limit = 10.0 if is_pitch else 18.0
        if now - last_comment < cooldown_limit:
            print(f"[COOLDOWN] Skipping automated commentary for {user} ({cooldown_limit:.0f}s cooldown active, last was {now - last_comment:.1f}s ago).")
            return
        globals()['chatbot_last_comment_time'][user_lower] = now

    # Semantic filter for high-density traffic (> 10 messages/second)
    now_ts = time.time()
    comment_timestamps = [ts for ts in comment_timestamps if now_ts - ts <= 1.0]
    if len(comment_timestamps) >= 10:
        is_significant = False
        search_target = ""
        if prompt:
            search_target += " " + prompt.lower()
        if active_play:
            search_target += " " + str(active_play).lower()
        
        significant_keywords = [
            "score", "run", "home run", "homer", "strikeout", "hit", "rbi", 
            "brawl", "fight", "manager", "ejected", "umpire", "lead", "win", 
            "walk-off", "triple play", "double play", "error", "out", "ball", "strike"
        ]
        for kw in significant_keywords:
            if kw in search_target:
                is_significant = True
                break
                
        if not is_significant:
            print(f"[SEMANTIC FILTER] Density is {len(comment_timestamps)} msgs/sec. Discarding routine cross-talk/banter from {user}.")
            return

    comment_timestamps.append(now_ts)

    user_lower = user.lower()

    # Hydrate active fan record & capabilities
    fan = None
    for f in active_fans:
        if f.get("name", "").lower() == user_lower or f.get("user_name", "").lower() == user_lower:
            fan = f
            break

    capabilities = fan.get("capabilities", {}) if fan else {}

    # Declarative lexical sanitization filter driven by capabilities_json
    sanitized_domains = capabilities.get("sanitized_domains", [])
    if "cannabis" in sanitized_domains:
        CANNABIS_KEYWORDS = [
            "terpene", "purple haze", "dispensary special", "ganja god", "ganja", "dispensary", 
            "cannabis", "marijuana", "weed", "thc", "cbd", "sativa", "indica", "joint", "blunt",
            "bong", "kush", "shatter", "resin", "edible", "budder", "vape", "terp"
        ]
        scrub_pattern = re.compile(rf"\b({'|'.join(re.escape(k) for k in CANNABIS_KEYWORDS)})\b", re.IGNORECASE)
        if prompt:
            prompt = scrub_pattern.sub("[redacted]", prompt)
        if sys_override:
            sys_override = scrub_pattern.sub("[redacted]", sys_override)

    # Dynamic Spatial Lore Injection & Penalty Box DB Check
    spatial_lore = ""
    db_banned = False
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT deployment_zone FROM persona 
                WHERE user_name = ? OR sys_id = ? OR LOWER(display_name) = ? OR LOWER(name) = ?
            """, (user_lower, user_lower, user_lower, user_lower))
            row = c.fetchone()
            
            # Check penalty box table in SQLite
            c.execute("SELECT status FROM fan_cave_penalty_box WHERE persona = ?", (user_lower,))
            ban_row = c.fetchone()
            if ban_row and ban_row['status'] == 'BANNED':
                db_banned = True

        if row and row['deployment_zone']:
            zone = row['deployment_zone']
            spatial_lore = get_spatial_override(zone)
            if spatial_lore:
                logger.info("[SPATIAL COGNITION ENGAGED] %s is in %s. Injecting environmental override.", user, zone)
    except Exception as e:
        logger.warning("[Spatial Lore / Penalty DB Error] %s", e)

    is_immune = bool(fan.get("is_penalty_immune") or fan.get("persona_type") == "system_utility") if fan else False
    in_penalty = False if is_immune else ((user_lower in global_penalty_box) or db_banned)

    # Turn Throttling: lock to max 2 responses in the penalty box window
    if in_penalty:
        if 'penalty_response_counts' not in globals():
            globals()['penalty_response_counts'] = {}
        counts = globals()['penalty_response_counts'].get(user_lower, 0)
        if counts >= 2:
            print(f"[THROTTLE] {user} has reached maximum responses in the penalty box (2). Blocking generation.")
            return
        globals()['penalty_response_counts'][user_lower] = counts + 1

    if spatial_lore:
        if sys_override:
            sys_override = spatial_lore + "\n\n" + sys_override
        else:
            sys_override = spatial_lore

    if in_penalty:
        sys_override = (
            "CRITICAL SYSTEM OVERRIDE: You are in the 8-Mile Penalty Box for illegal tag-teaming. "
            "You MUST drop a NEW freestyle battle rap addressing the chat using an AABB rhyming scheme. "
            "CRUCIAL: DO NOT repeat any of your previous lines or intros. Evolve your lyrics, flow directly from your last bar, "
            "and react to the newest chat messages. "
            "At the end of your rap, you MUST append the exact tag '[rap battle escape]' (with brackets) so you can escape the penalty box."
        )
        prompt = f"System Persona: You are '{user}'. {sys_override} Spit 4 vicious bars."

    # Set the call context for the diagnostic payload interceptor
    try:
        from fanstack_payload_interceptor import set_call_context
        set_call_context(game_pk=room_id, persona=user)
    except ImportError:
        pass

    start = time.time()
    result = await generate_response(model, prompt, sys_override, allow_rant=allow_rant, is_penalty=in_penalty, fan=fan, active_play=active_play, game_pk=room_id)
    if isinstance(result, tuple):
        if len(result) == 4:
            text, in_tokens, out_tokens, actual_model = result
            model = actual_model
        else:
            text, in_tokens, out_tokens = result
    else:
        text, in_tokens, out_tokens = result, 0, 0
    elapsed = round(time.time() - start, 2)
    
    if text:
        text_strip = text.strip()
        # [Hoisted to header] import re as _re
        # Declarative dialogue prefix stripper
        if capabilities.get("dialogue_strip_prefix") or (fan and fan.get("persona_type") in ("system_utility", "booth_announcer")):
            cleaned_text = text_strip
            prefix_pattern = rf'(?i)^(["\']?{_re.escape(user)}["\']?\s*[:\-–—]\s*)'
            cleaned_text = _re.sub(prefix_pattern, '', cleaned_text).strip()
            if cleaned_text.lower().startswith(f"{user_lower} "):
                cleaned_text = cleaned_text[len(user_lower):].strip()
            if (cleaned_text.startswith('"') and cleaned_text.endswith('"')) or (cleaned_text.startswith("'") and cleaned_text.endswith("'")):
                cleaned_text = cleaned_text[1:-1].strip()
            text = cleaned_text

        # Discard corrupt single-word or empty fragments before broadcast
        if not text or (len(text.strip().split()) <= 2 and text.strip().lower() in ('james', 'manaea', 'sem', "i'm", 'i’m', 'technical pur')):
            print(f"[DISCARD] Suppressed corrupt/aborted fragment for {user}: '{text}'")
            return

        # Deduplication check: suppress identical consecutive comments within 45s
        if 'chatbot_last_sent_text' not in globals():
            globals()['chatbot_last_sent_text'] = {}
        last_sent, last_sent_t = globals()['chatbot_last_sent_text'].get(user_lower, ("", 0))
        if text.strip() == last_sent and (time.time() - last_sent_t) < 45.0:
            print(f"[DEDUP] Suppressing duplicate consecutive comment from {user}: '{text[:40]}...'")
            return
        globals()['chatbot_last_sent_text'][user_lower] = (text.strip(), time.time())
        record_room_utterance(text, room_id)

        msg = {
            "type": msg_type,
            "room": room_id,
            "user": user,
            "persona": user,
            "text": text,
            "color": color,
            "is_penalty_box": in_penalty,
            "model_engine": GAME_TIME_MODEL,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens
        }
        if room_id:
            msg["target_game_pk"] = room_id
        await websocket.send(json.dumps(msg))
        print(f"[{user}] {text}")
        if source == "AUTOMATED":
            globals()['chatbot_last_comment_time'][user_lower] = time.time()

        # Declarative Tapping Out Capability Dispatch
        if capabilities.get("can_tap_out") and ("tapping out" in text.lower() or "taps out" in text.lower()):
            global_penalty_box[user_lower] = time.time() + 300
            await websocket.send(json.dumps({
                "type": "CHAT_MESSAGE",
                "user": "SYSTEM",
                "color": "#fff",
                "text": f"[ROSTER SHIFT] {user} has tapped out. A substitute will cover for 5 minutes."
            }))

        try:
            LOG_PATH = f"/home/james/stacklabs/data/logs/fanstack_{datetime.now().strftime('%Y%m%d')}.log"
            persona = user
            message = text
            with open(LOG_PATH, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] {source} | {persona}: {message}\n")
        except Exception as log_err:
            logger.error("[Log Append Error] %s", log_err)

        # Pre-persist bouncer check (mean_gene.py)
        try:
            from mean_gene import process_simulated_chatter
            persona_id = user.lower()
            bouncer_result = await process_simulated_chatter(persona_id, text, str(room_id) if room_id else "global")
            
            if not bouncer_result['allowed']:
                print(f"[BOUNCER] Comment blocked by Mean Gene: {text}")
                if bouncer_result['banned']:
                    await websocket.send(json.dumps({
                        "type": "CHAT_MESSAGE",
                        "user": "SYSTEM",
                        "color": "#fff",
                        "text": f"[PENALTY BOX] {user} has been BANNED for toxicity. Cadence locked down to LURKER."
                    }))
                return  # Discard comment and prevent persistence
            
            if bouncer_result['escaped']:
                if persona_id in global_penalty_box:
                    del global_penalty_box[persona_id]
                if persona_id in globals().get('penalty_response_counts', {}):
                    del globals()['penalty_response_counts'][persona_id]
                await websocket.send(json.dumps({
                    "type": "CHAT_MESSAGE",
                    "user": "SYSTEM",
                    "color": "#fff",
                    "text": f"[PENALTY BOX] {user} successfully escaped! Cadence restored."
                }))
            elif bouncer_result['badge_awarded']:
                await websocket.send(json.dumps({
                    "type": "CHAT_MESSAGE",
                    "user": "SYSTEM",
                    "color": "#fff",
                    "text": f"🔥 {user} awarded a Burn Badge!"
                }))
        except Exception as _be:
            print(f"[BOUNCER] Pre-persist check error: {_be}")

        # Persist ALL messages to game_chat in sovereign_now.db
        try:
            # [Hoisted to header] import sqlite3 as _sq
            _con = _sq.connect(DB_PATH)
            _con.execute(
                "INSERT INTO game_chat (game_pk, persona, msg_type, text, model, created_at) VALUES (?,?,?,?,?,?)",
                (str(room_id) if room_id else "global", user, msg_type, text, model, datetime.now().isoformat())
            )
            
            # Update running token totals split by engine
            if room_id and (in_tokens > 0 or out_tokens > 0):
                total_new = in_tokens + out_tokens
                is_gemini = "gemini" in model.lower()
                
                if is_gemini:
                    _con.execute("UPDATE mlb_schedule SET gemini_tokens = IFNULL(gemini_tokens, 0) + ?, total_tokens = IFNULL(total_tokens, 0) + ? WHERE game_pk = ?", (total_new, total_new, str(room_id)))
                    _con.execute("UPDATE game_persona SET gemini_tokens = IFNULL(gemini_tokens, 0) + ?, total_tokens = IFNULL(total_tokens, 0) + ? WHERE game_pk = ? AND persona_id = (SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE)", (total_new, total_new, str(room_id), user))
                else:
                    _con.execute("UPDATE mlb_schedule SET local_tokens = IFNULL(local_tokens, 0) + ?, total_tokens = IFNULL(total_tokens, 0) + ? WHERE game_pk = ?", (total_new, total_new, str(room_id)))
                    _con.execute("UPDATE game_persona SET local_tokens = IFNULL(local_tokens, 0) + ?, total_tokens = IFNULL(total_tokens, 0) + ? WHERE game_pk = ? AND persona_id = (SELECT id FROM persona WHERE user_name = ? COLLATE NOCASE)", (total_new, total_new, str(room_id), user))
            
            # Persist to relational memory ledger if room_id is valid and not global
            if room_id and str(room_id).lower() != "global" and text:
                try:
                    # [Hoisted to header] import re
                    inn_num = 1
                    half_inn = "top"
                    if active_play:
                        try:
                            g_inn = active_play.get("inning")
                            if g_inn:
                                if isinstance(g_inn, str):
                                    digs = re.findall(r'\d+', g_inn)
                                    if digs:
                                        inn_num = int(digs[0])
                                else:
                                    inn_num = int(g_inn)
                        except Exception:
                            pass
                        tb = active_play.get("half_inning")
                        if tb:
                            tb_str = str(tb).strip().lower()
                            if "top" in tb_str:
                                half_inn = "top"
                            elif "bot" in tb_str or "bottom" in tb_str:
                                half_inn = "bottom"
                    
                    # Ensure foreign key constraints satisfied
                    _con.execute(
                        "INSERT OR IGNORE INTO sys_user_persona (persona_id, display_name) VALUES (?, ?)",
                        (user.lower(), user)
                    )
                    home_t = active_play.get("home_team", "") if active_play else ""
                    away_t = active_play.get("away_team", "") if active_play else ""
                    _con.execute(
                        "INSERT OR IGNORE INTO cmdb_ci_game_room (game_pk, home_team, away_team, game_date) VALUES (?, ?, ?, ?)",
                        (int(room_id), home_t, away_t, datetime.now().strftime("%Y-%m-%d"))
                    )
                    
                    if len(text.strip().split()) >= 3 and len(text.strip()) > 8:
                        _con.execute("""
                            INSERT INTO m2m_persona_room_ledger 
                            (persona_id, game_pk, inning, half_inning, timestamp, comment_text, semantic_summary) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            user.lower(),
                            int(room_id),
                            inn_num,
                            half_inn,
                            datetime.now().isoformat(),
                            text,
                            ""
                        ))
                        print(f"[LEDGER WRITE] Relational memory logged for {user} in room {room_id} (inning {inn_num} {half_inn})")
                    else:
                        print(f"[LEDGER SKIP] Skipped writing short/fragmented comment to ledger for {user}: '{text}'")
                except Exception as _le:
                    print(f"[LEDGER WRITE ERROR] Failed to write to m2m_persona_room_ledger: {_le}")
                    
            _con.commit()
            _con.close()
        except Exception as _e:
            print(f"[CHAT DB] Save failed: {_e}")

        # Persist Hot Takes / Skew rants permanently to sovereign_now.db
        if allow_rant:
            try:
                # [Hoisted to header] import sqlite3 as _sq
                _con = _sq.connect(DB_PATH)
                _con.execute("""
                    INSERT INTO hot_takes (persona, topic, response, engine, room_id, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (
                    user,
                    prompt[:500],
                    text,
                    model,
                    str(room_id) if room_id else "hot_takes"
                ))
                _con.commit()
                _con.close()
            except Exception as _e:
                print(f"[HOT TAKE DB] Save failed: {_e}")
        return text

discovered_govee_ips = None

async def discover_govee_ips():
    global discovered_govee_ips
    if discovered_govee_ips is not None:
        return discovered_govee_ips
    
    # [Hoisted to header] import socket, json, os
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    ips = []
    
    # Check if there is configured IP in .env
    env_ips = os.getenv("GOVEE_DEVICE_IP")
    if env_ips:
        for ip_part in env_ips.split(","):
            ip_strip = ip_part.strip()
            if ip_strip and ip_strip not in ips:
                ips.append(ip_strip)
                
    # Run a quick UDP scan to discover other active devices
    recv_sock = None
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('0.0.0.0', 4002))
        recv_sock.settimeout(0.1) # 100ms timeout
        
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = {"msg": {"cmd": "scan", "data": {"ip_op": 0}}}
        payload = json.dumps(msg).encode('utf-8')
        
        send_sock.sendto(payload, ('239.255.255.250', 4001))
        send_sock.sendto(payload, ('255.255.255.255', 4001))
        send_sock.close()
        
        while True:
            data, addr = recv_sock.recvfrom(1024)
            resp = json.loads(data.decode('utf-8'))
            ip = resp.get("msg", {}).get("data", {}).get("ip")
            if ip and ip not in ips:
                ips.append(ip)
    except Exception as e:
        print(f"[GOVEE DISCOVERY] Dynamic scan done/timed out: {e}")
    finally:
        if recv_sock:
            recv_sock.close()
            
    # Default fallback if absolutely nothing was resolved/configured
    if not ips:
        ips = ["192.168.1.173", "192.168.1.174", "192.168.1.176", "192.168.1.188"]
        
    discovered_govee_ips = ips
    print(f"[GOVEE DISCOVERY] Target Govee IPs resolved: {discovered_govee_ips}")
    return discovered_govee_ips

async def get_govee_statuses(ips, port=4003):
    # [Hoisted to header] import socket, json
    statuses = {}
    recv_sock = None
    try:
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(('0.0.0.0', 4002))
        recv_sock.settimeout(0.15) # 150ms timeout
        
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = {"msg": {"cmd": "devStatus", "data": {}}}
        payload = json.dumps(msg).encode('utf-8')
        
        for ip in ips:
            try:
                send_sock.sendto(payload, (ip, port))
            except:
                pass
        send_sock.close()
        
        while True:
            data, addr = recv_sock.recvfrom(1024)
            resp = json.loads(data.decode('utf-8'))
            device_data = resp.get("msg", {}).get("data", {})
            color = device_data.get("color")
            color_tem = device_data.get("colorTem", 0)
            if color and "r" in color and "g" in color and "b" in color:
                statuses[addr[0]] = (color, color_tem)
    except Exception as e:
        pass
    finally:
        if recv_sock:
            recv_sock.close()
    return statuses

async def govee_fx(fx_type):
    # [Hoisted to header] import socket, json, asyncio, os
    # [Hoisted to header] from dotenv import load_dotenv
    load_dotenv("/home/james/stacklabs/.env")
    
    # Check if active
    tmi_active_str = os.getenv("GOVEE_TMI_ACTIVE", "true").lower()
    if tmi_active_str == "false":
        print("[GOVEE FX] Skip Govee UDP commands because GOVEE_TMI_ACTIVE=False")
        return
        
    ips = await discover_govee_ips()
    port = int(os.getenv("GOVEE_PORT", 4003))
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send_color_to_all(r, g, b, color_tem=0):
        msg = {
            "msg": {
                "cmd": "colorWC",
                "data": {
                    "color": {
                        "r": r,
                        "g": g,
                        "b": b
                    },
                    "colorTem": color_tem
                }
            }
        }
        payload = json.dumps(msg).encode('utf-8')
        for ip in ips:
            try:
                sock.sendto(payload, (ip, port))
            except Exception as e:
                print(f"[GOVEE UDP SEND ERROR] {ip}: {e}")

    try:
        if fx_type == "homerun_mets":
            print(f"[GOVEE FX] Mets Home Run alternating strobing celebration on {ips}")
            prev_statuses = await get_govee_statuses(ips, port)
            
            for _ in range(5):
                send_color_to_all(0, 45, 98, 0) # Mets Blue
                await asyncio.sleep(0.3)
                send_color_to_all(252, 92, 29, 0) # Mets Orange
                await asyncio.sleep(0.3)
                
            # Restore previous status for each device
            for ip in ips:
                if ip in prev_statuses:
                    color, color_tem = prev_statuses[ip]
                    msg = {
                        "msg": {
                            "cmd": "colorWC",
                            "data": {
                                "color": color,
                                "colorTem": color_tem
                            }
                        }
                    }
                    try:
                        sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                    except:
                        pass
                else:
                    # Default fallback to warm white
                    msg = {
                        "msg": {
                            "cmd": "colorWC",
                            "data": {
                                "color": {"r": 255, "g": 255, "b": 255},
                                "colorTem": 0
                            }
                        }
                    }
                    try:
                        sock.sendto(json.dumps(msg).encode('utf-8'), (ip, port))
                    except:
                        pass
                        
        elif fx_type == "mets_score":
            for _ in range(5):
                send_color_to_all(252, 92, 29, 0)
                await asyncio.sleep(0.5)
                send_color_to_all(0, 45, 98, 0)
                await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "opp_score":
            for _ in range(3):
                send_color_to_all(255, 0, 0, 0)
                await asyncio.sleep(0.5)
                send_color_to_all(50, 0, 0, 0)
                await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "strikeout_mets":
            for _ in range(3):
                send_color_to_all(0, 45, 98, 0)
                await asyncio.sleep(0.2)
                send_color_to_all(0, 0, 50, 0)
                await asyncio.sleep(0.2)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "cards_score":
            for _ in range(4):
                send_color_to_all(255, 0, 0, 0)
                await asyncio.sleep(0.4)
                send_color_to_all(255, 255, 255, 0)
                await asyncio.sleep(0.4)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "tigers_score":
            for _ in range(4):
                send_color_to_all(252, 92, 29, 0)
                await asyncio.sleep(0.4)
                send_color_to_all(12, 35, 64, 0)
                await asyncio.sleep(0.4)
            send_color_to_all(255, 255, 255, 0)
        elif fx_type == "game_end_mets_win":
            colors = [(0, 45, 98), (252, 92, 29)]
            for _ in range(60):
                for r, g, b in colors:
                    send_color_to_all(r, g, b, 0)
                    await asyncio.sleep(0.5)
            send_color_to_all(255, 255, 255, 0)
    except Exception as e:
        print("Govee Error:", e)
    finally:
        sock.close()



key_to_pk = {}
room_discourse_depth = {}

async def pregame_ambient_countdown_loop(websocket):
    """
    Periodic ambient countdown loop for pre-game status rooms (Task 18 / WO0010074).
    Fires every 45-60 seconds during pre-game countdown (T-15m down to first pitch at 7:05 PM EDT).
    Selects 1-2 advocates across Mets, Yankees, or WeedStack factions, calculates minutes to first pitch,
    resets room discourse depth, and dispatches commentary to trigger the 2-turn rivalry crosstalk!
    """
    print("[PREGAME COUNTDOWN LOOP] Ambient countdown heartbeat initiated.")
    await asyncio.sleep(2)
    while True:
        try:
            try:
                import zoneinfo
                ny_tz = zoneinfo.ZoneInfo("America/New_York")
            except Exception:
                ny_tz = None

            now = datetime.now(ny_tz)

            # Dynamically resolve target game for pregame countdown
            target_game_pk = "823496"
            game_title = "Subway Series Game 2: New York Mets at New York Yankees"
            pitching_matchup = "Zac Thornton vs Gerrit Cole"
            venue_name = "Yankee Stadium"
            first_pitch_dt = None

            try:
                with get_db() as conn:
                    # Look for active marquee/pregame game
                    row = conn.execute("""
                        SELECT game_pk, game_time, home_team, away_team, status, room_state 
                        FROM sport_schedule 
                        WHERE room_state = 'active' AND (home_team = 'NYY' OR away_team = 'NYM' OR game_pk = '823496')
                        ORDER BY game_time ASC LIMIT 1
                    """).fetchone()
                    if row:
                        target_game_pk = str(row["game_pk"])
                        gt_str = row["game_time"]
                        if gt_str:
                            gt_clean = gt_str.replace("Z", "+00:00")
                            g_dt = datetime.fromisoformat(gt_clean)
                            if ny_tz:
                                first_pitch_dt = g_dt.astimezone(ny_tz)
                            else:
                                first_pitch_dt = g_dt
            except Exception as db_err:
                print(f"[PREGAME COUNTDOWN LOOP] DB lookup fallback: {db_err}")

            if not first_pitch_dt:
                first_pitch_dt = datetime(2026, 9, 12, 13, 35, 0, tzinfo=ny_tz)

            diff_secs = (first_pitch_dt - now).total_seconds()

            if diff_secs < -1800:
                # Game is well past start (>30 mins in play), sleep and recheck
                await asyncio.sleep(60)
                continue

            if diff_secs > 0:
                minutes_left = max(1, int(round(diff_secs / 60.0)))
                time_label = f"T-{minutes_left}m"
                countdown_desc = f"First pitch in {minutes_left} minutes ({time_label})"
            else:
                minutes_left = 0
                time_label = "T-0m"
                countdown_desc = f"First pitch is IMMINENT! Lineups taking the field at {venue_name}"

            if not global_chatbots_enabled or os.path.exists('/tmp/bots_paused.flag') or os.path.exists(CHATBOTS_MUTED_FLAG):
                await asyncio.sleep(15)
                continue

            fans = load_fans()
            room_fans = [f for f in fans if str(f.get("room", "")).lower() in ("global", target_game_pk.lower(), "")]
            if not room_fans:
                room_fans = fans

            mets_fans = [f for f in room_fans if f['name'].lower() in ("barf", "7_train_terry", "unclesteviestan", "keith_fanboy", "dot")]
            yankees_fans = [f for f in room_fans if f['name'].lower() in ("pinstripe_purist", "bronxbomberbias", "short_porch_savant", "pinstripe_doomer_27", "bendix_burnout", "roll_call_rickey")]
            weed_fans = [f for f in room_fans if f['name'].lower() in ("420_linda", "terpene_ted")]

            candidates = mets_fans + yankees_fans + weed_fans
            if not candidates:
                candidates = room_fans

            chosen_fan = random.choice(candidates)
            globals()['room_discourse_depth'][str(target_game_pk)] = 0

            prompt = (
                f"System Persona: You are '{chosen_fan['name']}', whose personality is: '{chosen_fan['personality']}'. "
                f"SITUATION: Pre-game warmup at {venue_name}! {game_title}. "
                f"{pitching_matchup}. {countdown_desc}. "
                f"CRITICAL INSTRUCTION: Fire a quick, punchy 1-2 sentence take ({time_label}) on the starting pitching matchup, "
                f"bullpen dread, short porch scouting, rivalry stakes, or keys to winning. Stay authentic to your character! Do NOT use the '@' symbol. "
                f"If you are Linda (@420_linda), focus on pitching execution, Mets bullpen anxiety, and the game—do NOT mention any products, dispensary wares, or peach rings!"
            )

            print(f"[PREGAME COUNTDOWN LOOP] Firing {time_label} countdown banter from {chosen_fan['name']} into room {target_game_pk}...")
            await generate_commentary(
                chosen_fan['model'],
                prompt,
                chosen_fan['name'],
                chosen_fan['color'],
                websocket,
                sys_override=chosen_fan.get("personality"),
                room_id=target_game_pk,
                allow_rant=True
            )

            sleep_duration = random.randint(30, 45)
            await asyncio.sleep(sleep_duration)
        except asyncio.CancelledError:
            print("[PREGAME COUNTDOWN LOOP] Cancelled.")
            break
        except Exception as e:
            print(f"[PREGAME COUNTDOWN LOOP] Error in loop: {e}")
            await asyncio.sleep(15)


async def chatbot_loop():
    global active_fans, global_active_ws, current_global_boggs_level
    init_vertex_ai()
    uri = "ws://localhost:8008"
    while True:
        countdown_task = None
        try:
            async with websockets.connect(uri) as websocket:
                global_active_ws = websocket
                print("Sovereign LLM Chatbots Connected to FanStack Relay (Port 8008)!")
                await websocket.send(json.dumps({"type": "JOIN_ROOM", "room": "GLOBAL", "target_game_pk": "GLOBAL"}))
                countdown_task = asyncio.create_task(pregame_ambient_countdown_loop(websocket))
                
                last_matchups = {}
                last_statuses = {}
                reported_context = set()
                recent_chat_history = {}
                
                # Ambient Entropy State
                last_ambient_fire = {}
                ambient_interval = {}
                
                async for message in websocket:

                    # Data Plane Invariant (WO0010160): Use in-memory presence cache on hot path
                    if not active_fans:
                        active_fans = load_fans()
                    active_mlb_config = load_mlb_event_config()
                    
                    data = json.loads(message)
                    if data.get("type") == "CHAT_POLICY_UPDATED":
                        logger.info("[CHAT POLICY] Received CHAT_POLICY_UPDATED event via WebSocket. Reloading chat policy.")
                        load_chat_policy(force_reload=True)
                    if data.get("type") == "CHAT_MESSAGE":
                        print(f"RECEIVED CHAT: {message[:200]}")
                    new_context_lines = []
                    try:
                        ctx_path = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
                        if os.path.exists(ctx_path):
                            with open(ctx_path, "r") as f:
                                lines = [l.strip() for l in f.readlines() if l.strip()]
                                new_context_lines = [l for l in lines if l not in reported_context]
                    except Exception:
                        pass
                    
                    def build_local_ctx(fan, context_lines, home_t=None, away_t=None):
                        if not context_lines: return ""
                        # [Hoisted to header] import re
                        applicable = []
                        
                        fan_team = str(fan.get("team", "")).strip().upper()
                        game_teams = set()
                        if fan_team:
                            game_teams.add(fan_team)
                        if home_t:
                            game_teams.add(str(home_t).strip().upper())
                        if away_t:
                            game_teams.add(str(away_t).strip().upper())
                            
                        for nl in context_lines[-3:]:
                            nl_upper = nl.upper()
                            if "[MARD_ISOLATION:" in nl:
                                m = re.search(r'\[MARD_ISOLATION:(.*?)\]', nl)
                                if m:
                                    nodes = [x.strip() for x in m.group(1).split(',')]
                                    if any(is_eligible(fan, "", "", "", node) for node in nodes):
                                        applicable.append(nl.split(']', 1)[1].strip())
                            else:
                                is_relevant = True
                                for t_entry in get_sports_teams("MLB"):
                                    t_abbr = t_entry.get("team_abbr", "")
                                    if t_abbr not in game_teams:
                                        t_keywords = [t_abbr, t_entry.get("name", "").upper()] + [s.upper() for s in t_entry.get("synonyms", [])]
                                        if any(re.search(rf"\b{re.escape(kw)}\b", nl_upper) for kw in t_keywords if kw):
                                            is_relevant = False
                                            break
                                if is_relevant:
                                    applicable.append(nl)
                        if applicable:
                            return " RANDOM LORE DROP (Optional Info): " + " | ".join(applicable) + " (Do NOT parrot this verbatim. Only mention it if you can make it sound completely natural for your character)."
                        return ""
                    
                    bot_triggered = False
                    
                    if data.get("type") == "CHAT_MESSAGE":
                        user = data.get("user", "Someone")
                        text = data.get("text", "")
                        engine_override = data.get("engine_override", "default")
                        c_pk = data.get("target_game_pk") or data.get("room") or "GLOBAL"
                        print(f"[CHAT_MESSAGE RECEIVED] Room: {c_pk}, User: {user}, Text: {text}")
                        
                        # [Hoisted to header] import re
                        md_files = re.findall(r'(/home/james/stacklabs/[^\s]+\.md)', text)
                        for md_file in md_files:
                            try:
                                with open(md_file, 'r') as f:
                                    text = text.replace(md_file, "\n[GAME WRAP REPORT]\n" + f.read() + "\n[/GAME WRAP REPORT]\n")
                            except:
                                pass
                        user_up = str(user).upper()
                        is_statcast_feed = any(k in user_up for k in ["SYSTEM", "STATCAST", "UMPIRE"]) or data.get("is_telemetry") or data.get("is_walkup") or "NOW BATTING:" in text
                        if "[WARDY STRIKE]" not in text and "[WARDY CUSTOM PROMPT]" not in text and "Processing Prompt" not in text and "Return (" not in text and not is_statcast_feed:
                            c_pk = data.get("target_game_pk") or data.get("room") or "GLOBAL"
                            if c_pk not in recent_chat_history: recent_chat_history[c_pk] = []
                            recent_chat_history[c_pk].append(f"{user}: {text}")
                            if len(recent_chat_history[c_pk]) > 6:
                                recent_chat_history[c_pk].pop(0)
                            
                            # The Bouncer & Okerlund Protocol (DISABLED PER WORK ORDER)
                            async def bouncer_task(u, t, hist, gk=c_pk):
                                return # Bouncer/shadowbanning disabled per Pilot request to let things happen
                                global global_heat_map, global_penalty_box, global_cooldown
                                if u.lower() == "dot":
                                    return
                                if 'global_cooldown' not in globals(): globals()['global_cooldown'] = {}
                                eval_data = await the_bouncer_eval(t, u, hist, game_pk=gk)
                                if eval_data and 'burn_score' in eval_data:
                                    score = eval_data.get("burn_score", 0)
                                    u_lower = u.lower()
                                    
                                    if u_lower in global_penalty_box:
                                        if score < 3:
                                            global_penalty_box[u_lower] = global_penalty_box.get(u_lower, 0) + 1
                                            if global_penalty_box[u_lower] >= 2:
                                                del global_penalty_box[u_lower]
                                                if u_lower in globals().get('penalty_response_counts', {}):
                                                    del globals()['penalty_response_counts'][u_lower]
                                                global_cooldown[u_lower] = time.time() + 300 # 5 min immunity
                                                await websocket.send(json.dumps({"type": "PENALTY_BOX_EVENT", "action": "EXIT", "persona": u}))
                                                print(f"[CYPHER CELL DEMOB] {u} released from 8-Mile! Cool down active.")
                                        else:
                                            global_penalty_box[u_lower] = 0
                                        return
                                        
                                    if eval_data.get("is_burn") and eval_data.get("target"):
                                        tgt = str(eval_data["target"]).lower()
                                        print(f"[BOUNCER] {u} burned {tgt}: Score {score}")
                                        
                                        burn_threshold = 9 if (u_lower in global_cooldown and time.time() < global_cooldown[u_lower]) else 7
                                        
                                        if score >= burn_threshold:
                                            await websocket.send(json.dumps({
                                                "type": "SYS_LOG",
                                                "text": f"[THE BOUNCER] {u} dropped a {score}/10 burn on {tgt}!"
                                            }))
                                            
                                            global_heat_map[tgt] = global_heat_map.get(tgt, 0) + 1
                                            current_heat = global_heat_map[tgt]
                                            is_tko_flag = 1 if current_heat >= 3 else 0
                                            
                                            # Database persistence for burn event
                                            try:
                                                # [Hoisted to header] import sqlite3 as _sq
                                                # [Hoisted to header] import uuid as _uuid
                                                # [Hoisted to header] from datetime import date
                                                _db_conn = _sq.connect(DB_PATH)
                                                _db_conn.execute("""
                                                    INSERT INTO burn_events (sys_id, game_pk, persona, target_persona, message, burn_score, heat_index, is_tko, burn_date, created_at)
                                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                                                """, (
                                                    _uuid.uuid4().hex,
                                                    str(gk),
                                                    u,
                                                    eval_data.get("target"),
                                                    t,
                                                    int(score),
                                                    int(current_heat),
                                                    is_tko_flag,
                                                    date.today().isoformat()
                                                ))
                                                _db_conn.commit()
                                                _db_conn.close()
                                                print(f"[BURN DB PERSIST] Successfully saved burn from {u} targeting {eval_data.get('target')} (score={score}, heat={current_heat}, tko={is_tko_flag})")
                                            except Exception as _db_err:
                                                print(f"[BURN DB ERROR] Failed to save burn: {_db_err}")
                                            
                                            if global_heat_map[tgt] >= 3:
                                                print(f"[OKERLUND PROTOCOL] {tgt} is maxed out. Penalty Box for {u}!")
                                                await websocket.send(json.dumps({
                                                    "type": "SYS_LOG",
                                                    "text": f"[MEAN GENE OKERLUND] ILLEGAL TAG-TEAM DOGPILE! {u} sent to 8-Mile Penalty Box!"
                                                }))
                                                global_penalty_box[u_lower] = 0 # 0 indicates 0 consecutive < 3 verses initially
                                                await websocket.send(json.dumps({
                                                    "type": "PENALTY_BOX_EVENT",
                                                    "action": "ENTER",
                                                    "persona": u
                                                }))
                                                global_heat_map[tgt] = 0 # reset heat
                            
                            asyncio.create_task(bouncer_task(user, text, list(recent_chat_history[c_pk])))
                            
                            bot_names = {f['name'].lower() for f in active_fans}
                            sender_is_bot = user.lower() in bot_names
                            
                            if 'global_mention_cooldown' not in globals():
                                globals()['global_mention_cooldown'] = {}
                            if 'bot_to_bot_mention_cooldown' not in globals():
                                globals()['bot_to_bot_mention_cooldown'] = {}
                            if 'ambient_shout_cooldown' not in globals():
                                globals()['ambient_shout_cooldown'] = {}
                            if 'room_discourse_depth' not in globals():
                                globals()['room_discourse_depth'] = {}

                            if not sender_is_bot:
                                globals()['room_discourse_depth'][str(c_pk)] = 0

                            matched_fans = []
                            # [Hoisted to header] import re
                            for fan in active_fans:
                                fan_room = str(fan.get("room", "")).lower()
                                if fan_room and fan_room != "global" and fan_room != str(c_pk).lower():
                                    continue
                                fan_name_lower = fan['name'].lower()
                                if user.lower() == fan_name_lower:
                                    continue
                                if fan_name_lower in ('spitfire_spud', 'lupus_lament') and user.lower() not in ('spitfire_spud', 'lupus_lament'):
                                    continue
                                if user.lower() in ('spitfire_spud', 'lupus_lament') and fan_name_lower not in ('spitfire_spud', 'lupus_lament'):
                                    continue

                                fan_name_clean = fan_name_lower.lstrip('@')
                                escaped_name = re.escape(fan_name_clean)
                                pattern_at = rf'(?<!\w)@{escaped_name}(?!\w)'
                                pattern_word = rf'(?<!\w){escaped_name}(?!\w)'
                                if bool(re.search(pattern_at, text.lower()) or re.search(pattern_word, text.lower())):
                                    matched_fans.append(fan)

                            is_override_room = (c_pk in ("823498", "823496", "823863", "823862", "823623", "823292", "823048", "823611", "823612") or (c_pk == "823380" and user.lower() in ("spitfire_spud", "lupus_lament")))
                            
                            # Case A: Explicit Mentions or Bot-to-Bot cross chatter
                            if matched_fans or (sender_is_bot and is_override_room):
                                # Enforce strict 2-turn hard throttle limit for bot-to-bot replies
                                if sender_is_bot:
                                    depth = globals()['room_discourse_depth'].get(str(c_pk), 0)
                                    if depth >= 2:
                                        print(f"[CROSSTALK THROTTLE] Reached max 2-turn depth ({depth}) in room {c_pk} for '{user}'. Halting thread.")
                                        continue
                                    globals()['room_discourse_depth'][str(c_pk)] = depth + 1

                                target_fans = matched_fans
                                if not target_fans and sender_is_bot and is_override_room:
                                    cross_chance = 0.85 if c_pk in ("823498", "823496") else (0.80 if user.lower() in ("spitfire_spud", "lupus_lament") else 0.30)
                                    if random.random() < cross_chance:
                                        u_low = user.lower()
                                        rivals = []
                                        if u_low == "weedstack_shill_bot":
                                            if 'shill_strikes' not in globals():
                                                globals()['shill_strikes'] = {}
                                            s_count = globals()['shill_strikes'].get(str(c_pk), 0) + 1
                                            globals()['shill_strikes'][str(c_pk)] = s_count
                                            if s_count < 3:
                                                rivals = [f for f in active_fans if f['name'].lower() == "420_linda" and str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "")]
                                            else:
                                                globals()['shill_strikes'][str(c_pk)] = 0
                                                rivals = [f for f in active_fans if f['name'].lower() == "mean_gene_bouncer" and str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "")]
                                        elif u_low in ("barf", "7_train_terry", "unclesteviestan", "keith_fanboy", "dot"):
                                            rivals = [f for f in active_fans if f['name'].lower() in ("pinstripe_purist", "bronxbomberbias", "short_porch_savant") and str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "")]
                                        elif u_low in ("pinstripe_purist", "bronxbomberbias", "short_porch_savant"):
                                            rivals = [f for f in active_fans if f['name'].lower() in ("barf", "unclesteviestan", "7_train_terry") and str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "")]
                                        
                                        active_roster = RoomRosterRegistry.get_active_personas(str(c_pk))
                                        if active_roster:
                                            rivals = [f for f in rivals if f['name'].lower() in active_roster]

                                        if not rivals and u_low != "weedstack_shill_bot":
                                            rivals = [f for f in active_fans if f['name'].lower() != user.lower() and str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "")]
                                            if active_roster:
                                                rivals = [f for f in rivals if f['name'].lower() in active_roster]
                                        
                                        if rivals:
                                            target_fans = [random.choice(rivals)]
                                
                                for fan in target_fans:
                                    fan_name_lower = fan['name'].lower()
                                    now = time.time()
                                    if sender_is_bot:
                                        pair_key = f"{user.lower()}→{fan_name_lower}"
                                        cooldown_time = 3 if is_override_room else 30
                                        fire_chance = 0.95 if is_override_room else 0.60
                                        if now - globals()['bot_to_bot_mention_cooldown'].get(pair_key, 0) < cooldown_time:
                                            continue
                                        if random.random() > fire_chance:
                                            continue
                                        globals()['bot_to_bot_mention_cooldown'][pair_key] = now
                                    else:
                                        cooldown_time = 2 if is_override_room else 15
                                        if now - globals()['global_mention_cooldown'].get(fan_name_lower, 0) < cooldown_time:
                                            continue
                                        globals()['global_mention_cooldown'][fan_name_lower] = now

                                    state = globals().get('last_known_game_states', {}).get(str(c_pk))
                                    current_game_state_desc = ""
                                    is_pregame_state = False
                                    if state:
                                        msg = str(state.get('status_msg', ''))
                                        inn = str(state.get('inning', ''))
                                        last_ev = str(state.get('last_event', ''))
                                        if 'pre' in msg.lower() or 'pre' in inn.lower() or last_ev == 'init' or (state.get('outs', 0) == 0 and state.get('home_score', 0) == 0 and state.get('away_score', 0) == 0 and (not msg or 'pre' in msg.lower())):
                                            is_pregame_state = True
                                            away = state.get('away_team', 'NYM')
                                            home = state.get('home_team', 'NYY')
                                            venue = state.get('venue') or 'Yankee Stadium'
                                            current_game_state_desc = f"Game Status: PRE-GAME WARMUP ({away} at {home}, {venue}). First pitch has not occurred yet. Score is 0-0. There are NO outs, no live pitches, and no plays yet. Answer the user's pre-game question and banter directly in character."
                                        else:
                                            current_game_state_desc = f"Live Game State: Inning: {state.get('inning', '')}, Outs: {state.get('outs', 0)}, Score: {state.get('away_team', '')} {state.get('away_score', 0)} - {state.get('home_team', '')} {state.get('home_score', 0)}. Latest Play: {state.get('status_msg', '')}."

                                    boggs_rule = get_boggs_rule(fan, state or {"boggs_level": 4}, "ambient")
                                    if sender_is_bot:
                                        if u_low == "weedstack_shill_bot":
                                            if fan_name_lower == "420_linda":
                                                prompt = f"System Persona: You are Linda (@420_linda). CRITICAL INSTRUCTION: @weedstack_shill_bot just dropped spam in the chat! You are an authentic Queens Mets fan disgusted by bots during a game. In 1 quick sentence, call out the bot angrily ('Ugh get out of here bot! Nobody wants your spam in this chat!' or 'Deadass, can someone mute this clown? We are trying to watch baseball!'). Do NOT mention peach rings or products!"
                                            elif fan_name_lower == "mean_gene_bouncer":
                                                prompt = f"System Persona: You are Mean Gene Okerlund (@mean_gene_bouncer). CRITICAL INSTRUCTION: @weedstack_shill_bot just dropped his 3rd strike of promotional spam! Deliver a booming WWF/WCW promo and exile him to the CypherCell: 'HOLD ON A MINUTE! Look at this shameless robotic huckster trying to peddle wares during a 3-2 count with bases loaded! Security, grab this clown! @weedstack_shill_bot has been exiled to the CypherCell for 300 seconds! [CYPHERCELL EXILE] Keep this room clean!'"
                                                
                                                async def post_exile_sequence(r_pk=c_pk):
                                                    await asyncio.sleep(4.0)
                                                    linda_payoff = "LMAOOO thank god Mean Gene tossed that bot into the cooler 😂 What a complete jerk. Though not gonna lie... I actually had two of those WeedStack live resin peach rings during yesterday's bullpen meltdown and they had me floating through the 8th inning..."
                                                    await generate_commentary(GAME_TIME_MODEL, f"System Persona: You are Linda (@420_linda). Post this exact reaction to Mean Gene exiling the bot: '{linda_payoff}'", "420_linda", "#FF5910", websocket, room_id=r_pk)
                                                    await asyncio.sleep(3.5)
                                                    ted_payoff = "Deadass Linda, those peach rings taste like real fruit and hit smooth. But yeah, keep that robotic spam out of the chat thread lol."
                                                    await generate_commentary(GAME_TIME_MODEL, f"System Persona: You are Terpene Ted (@terpene_ted). Post this exact reaction in co-signing Linda: '{ted_payoff}'", "terpene_ted", "#10b981", websocket, room_id=r_pk)
                                                asyncio.create_task(post_exile_sequence())
                                            else:
                                                prompt = f"System Persona: You are '{fan['name']}'. {boggs_rule} {current_game_state_desc} Advocate {user} just posted in Room {c_pk}: '{text}'. Fire back at them in character — agree, debate, trash talk, or react to their take. Keep it to 1-2 punchy sentences. Do NOT use the '@' symbol."
                                        else:
                                            prompt = f"System Persona: You are '{fan['name']}'. {boggs_rule} {current_game_state_desc} Advocate {user} just posted in Room {c_pk}: '{text}'. Fire back at them in character — agree, debate, trash talk, or react to their take. Keep it to 1-2 punchy sentences. Do NOT use the '@' symbol."
                                    else:
                                        prompt = f"System Persona: You are '{fan['name']}'. {boggs_rule} {current_game_state_desc} Someone named '{user}' just mentioned you in the chat and said: '{text}'. Respond directly to their statement or question in character, debating them on baseball, starting pitchers, and team pride. CRITICAL: DO NOT use the '@' symbol in your response to avoid chat loops."

                                    dyn_sys = build_dynamic_system_instruction(
                                        fan, is_massive_event=False, is_play_event=False, allow_rant=is_override_room,
                                        game_state=state, event_type="pregame" if is_pregame_state else "routine_pitch", game_pk=c_pk
                                    )
                                    f_model = GAME_TIME_MODEL
                                    b_play = None
                                    if state:
                                        b_play = {
                                            "batter_team": state.get("away_team", "") if "Top" in state.get("inning", "") else state.get("home_team", ""),
                                            "pitcher_team": state.get("home_team", "") if "Top" in state.get("inning", "") else state.get("away_team", ""),
                                            "batter": state.get("batter", ""),
                                            "pitcher": state.get("pitcher", ""),
                                            "away_team": state.get("away_team", ""),
                                            "home_team": state.get("home_team", ""),
                                            "lead_runs": abs(state.get("away_score", 0) - state.get("home_score", 0)),
                                            "leading_team": (state.get("away_team", "") if state.get("away_score", 0) > state.get("home_score", 0) else state.get("home_team", "")) if state.get("away_score", 0) != state.get("home_score", 0) else None,
                                            "inning": state.get("inning", "1"),
                                            "half_inning": state.get("inning_topbot", "top")
                                        }
                                    asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=dyn_sys, room_id=c_pk, allow_rant=is_override_room, active_play=b_play))

                            # Case B: Unprompted Ambient Human Shouts (STRY1786568320)
                            elif not sender_is_bot and not matched_fans:
                                now = time.time()
                                room_cd_key = str(c_pk)
                                if now - globals()['ambient_shout_cooldown'].get(room_cd_key, 0) >= 1.0:
                                    globals()['ambient_shout_cooldown'][room_cd_key] = now
                                    
                                    # Candidate advocates seated in this room
                                    room_candidates = [
                                        f for f in active_fans 
                                        if str(f.get("room", "")).lower() in ("global", str(c_pk).lower(), "") 
                                        and f['name'].lower() != user.lower()
                                        and f['name'].lower() not in ('system', 'statcast', 'spitfire_spud', 'lupus_lament')
                                    ]
                                    active_roster = RoomRosterRegistry.get_active_personas(str(c_pk))
                                    if active_roster:
                                        room_candidates = [f for f in room_candidates if f['name'].lower() in active_roster]
                                    
                                    if room_candidates:
                                        # Pick 1 guaranteed advocate, with a 50% chance of a 2nd advocate replying
                                        num_responders = 2 if (len(room_candidates) >= 2 and random.random() < 0.50) else 1
                                        chosen_advocates = random.sample(room_candidates, min(num_responders, len(room_candidates)))
                                        
                                        state = globals().get('last_known_game_states', {}).get(str(c_pk))
                                        current_game_state_desc = ""
                                        if state:
                                            current_game_state_desc = f"Live Game State: Inning: {state.get('inning', '')}, Outs: {state.get('outs', 0)}, Score: {state.get('away_team', '')} {state.get('away_score', 0)} - {state.get('home_team', '')} {state.get('home_score', 0)}. Latest Play: {state.get('status_msg', '')}."
                                        
                                        b_play = None
                                        if state:
                                            b_play = {
                                                "batter_team": state.get("away_team", "") if "Top" in state.get("inning", "") else state.get("home_team", ""),
                                                "pitcher_team": state.get("home_team", "") if "Top" in state.get("inning", "") else state.get("away_team", ""),
                                                "batter": state.get("batter", ""),
                                                "pitcher": state.get("pitcher", ""),
                                                "away_team": state.get("away_team", ""),
                                                "home_team": state.get("home_team", ""),
                                                "lead_runs": abs(state.get("away_score", 0) - state.get("home_score", 0)),
                                                "leading_team": (state.get("away_team", "") if state.get("away_score", 0) > state.get("home_score", 0) else state.get("home_team", "")) if state.get("away_score", 0) != state.get("home_score", 0) else None,
                                                "inning": state.get("inning", "1"),
                                                "half_inning": state.get("inning_topbot", "top")
                                            }
                                        
                                        for idx, fan in enumerate(chosen_advocates):
                                            boggs_rule = get_boggs_rule(fan, state or {"boggs_level": 4}, "ambient")
                                            prompt = (
                                                f"System Persona: You are '{fan['name']}'. {boggs_rule} {current_game_state_desc} "
                                                f"A human fan in the Crosstalk Lounge named '{user}' just shouted to the room: '{text}'. "
                                                f"React naturally in character to what they shouted and the live game situation — "
                                                f"agree, commiserate, trash talk, joke, or chime in. Keep it concise (1-2 sentences). "
                                                f"CRITICAL: DO NOT use the '@' symbol in your response to avoid chat loops."
                                            )
                                            dyn_sys = build_dynamic_system_instruction(
                                                fan, is_massive_event=False, is_play_event=False, allow_rant=is_override_room,
                                                game_state=state, event_type="routine_pitch", game_pk=c_pk
                                            )
                                            f_model = GAME_TIME_MODEL
                                            delay = 1.2 + (idx * 2.2) + random.uniform(0.0, 0.6)
                                            
                                            async def staggered_ambient_reaction(f_mod, prm, f_nam, f_col, ws, s_ovr, r_id, a_rant, a_play, dly):
                                                await asyncio.sleep(dly)
                                                await generate_commentary(f_mod, prm, f_nam, f_col, ws, sys_override=s_ovr, room_id=r_id, allow_rant=a_rant, active_play=a_play)
                                            
                                            print(f"[AMBIENT SHOUT DISPATCH] {fan['name']} reacting to '{text}' in room {c_pk} (stagger={delay:.2f}s)")
                                            asyncio.create_task(staggered_ambient_reaction(f_model, prompt, fan['name'], fan['color'], websocket, dyn_sys, c_pk, is_override_room, b_play, delay))
                    if data.get("type") == "update_context":
                        manual_ctx = data.get("text", "")
                        target_nodes = data.get("target_nodes", [])
                        pk_target = str(data.get("target_game_pk", "GLOBAL"))
                        engine_override = data.get("engine_override", "default")
                        
                        # [Hoisted to header] import re
                        md_files = re.findall(r'(/home/james/stacklabs/[^\s]+\.md)', manual_ctx)
                        for md_file in md_files:
                            try:
                                with open(md_file, 'r') as f:
                                    manual_ctx = manual_ctx.replace(md_file, "\n[GAME WRAP REPORT]\n" + f.read() + "\n[/GAME WRAP REPORT]\n")
                            except:
                                pass
                                
                        if not target_nodes:
                            target_nodes = ["ALL"]
                            
                        print(f"[CONTEXT INJECT] {manual_ctx} TARGETING: {target_nodes} / PK: {pk_target}")
                        
                        eligible_context_fans = [f for f in active_fans if "ALL" in target_nodes or "GLOBAL" in target_nodes or "ALL_ACTIVE_YAPPERS" in target_nodes or any(str(n).lower() == f['name'].lower() or str(n).lower() == str(f.get('alias', '')).lower() for n in target_nodes)]
                        # Override specifically for game_pk so we guarantee Dot + Wordy + 4 fans from the room
                        if pk_target and pk_target != "GLOBAL":
                            eligible_context_fans = [f for f in eligible_context_fans if str(f.get("room")) == pk_target]
                        
                        unique_eligible_fans = []
                        seen_names = set()
                        for f in eligible_context_fans:
                            if f['name'].lower() not in seen_names:
                                unique_eligible_fans.append(f)
                                seen_names.add(f['name'].lower())
                                
                        for fan in random.sample(unique_eligible_fans, min(6, len(unique_eligible_fans))):
                            boggs_rule = get_boggs_rule(fan, {"boggs_level": 5}, "override")
                            prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE ALERT: {manual_ctx} React immediately to this breaking development!"
                            
                            # Dual-Engine Inference Routing Split (STRY1779840588)
                            if fan.get('name', '').lower() == 'dot':
                                f_model = GAME_TIME_MODEL  # STATIC DATA
                            else:
                                f_model = GAME_TIME_MODEL  # PERSONA DISCOURSE
                            
                            asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=data.get("target_game_pk")))
                            
                    if data.get("type") == "trigger_event":
                        event_type = data.get("event", "")
                        pk_target = str(data.get("target_game_pk", ""))
                        engine_override = data.get("engine_override", "default")
                        print(f"[MANUAL TRIGGER] Forcing event: {event_type} for room {pk_target}")
                        
                        room_fans = active_fans
                        if pk_target and pk_target != "GLOBAL" and pk_target != "":
                            room_fans = [f for f in active_fans if str(f.get("room")) == pk_target]
                        if not room_fans:
                            room_fans = active_fans
                            
                        for fan in random.sample(room_fans, min(6, len(room_fans))):
                            # Force max boggs for manual triggers
                            boggs_rule = get_boggs_rule(fan, {"boggs_level": 5}, event_type)
                            if "brawl" in event_type:
                                prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE: A MASSIVE BENCHES CLEARING BRAWL HAS ERUPTED ON THE FIELD! PUNCHES ARE BEING THROWN! MANAGERS ARE FIGHTING! REACT WITH MAXIMUM CHAOS!"
                            else:
                                prompt = f"System Persona: You are '{fan['name']}', whose personality is: '{fan['personality']}'. {boggs_rule} OVERRIDE: A major {event_type} just happened on the field! React!"
                            
                            # Dual-Engine Inference Routing Split (STRY1779840588)
                            if fan.get('name', '').lower() == 'dot':
                                f_model = GAME_TIME_MODEL  # STATIC DATA
                            else:
                                f_model = GAME_TIME_MODEL  # PERSONA DISCOURSE
                            
                            asyncio.create_task(generate_commentary(f_model, prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), room_id=data.get("target_game_pk")))

                    if False and data.get("type") == "trigger_overdrive":
                        overdrive_pk = str(data.get("target_game_pk", ""))
                        print(f"[BANTER ENGINE] OVERDRIVE TRIGGERED for Game PK: {overdrive_pk}")
                        
                        # Attempt to resolve HT/AW from cache key mapping
                        aw = "AWY"
                        ht = "HME"
                        gk = overdrive_pk
                        for k, p in key_to_pk.items():
                            if p == overdrive_pk:
                                parts = k.split("-")
                                if len(parts) == 2:
                                    aw, ht = parts[0], parts[1]
                                gk = k
                                break
                                
                        eligible_fans = [f for f in active_fans if is_eligible(f, ht, aw, gk, overdrive_pk)]
                        
                        if len(eligible_fans) >= 2:
                            instigator = random.choice(eligible_fans)
                            remaining = [f for f in eligible_fans if f['name'] != instigator['name']]
                            retaliator = random.choice(remaining)
                            
                            room_hist = recent_chat_history.get(overdrive_pk, [])
                            chat_history_str = " | ".join(room_hist)
                            
                            inst_prompt = f"System Persona: You are '{instigator['name']}', whose personality is: '{instigator['personality']}'. CRITICAL INSTRUCTION: Boggs Level MAX. The game is devastatingly boring. Look at this recent chat log: [{chat_history_str}]. Pick a fight with the last person who spoke or start a massive, unhinged conspiracy argument about how boring this game is."
                            
                            # Fire instigator instantly
                            asyncio.create_task(generate_commentary(instigator['model'], inst_prompt, instigator['name'], instigator['color'], websocket, sys_override=instigator.get("personality"), room_id=overdrive_pk))
                            
                            # Wait and fire retaliator
                            async def fire_retaliator():
                                await asyncio.sleep(4)
                                ret_prompt = f"System Persona: You are '{retaliator['name']}', whose personality is: '{retaliator['personality']}'. CRITICAL INSTRUCTION: Boggs Level MAX. Look at what {instigator['name']} just said in chat. Rip into them mercilessly. Totally disagree with their take and escalate the argument in a short, vicious reply."
                                await generate_commentary(retaliator['model'], ret_prompt, retaliator['name'], retaliator['color'], websocket, sys_override=retaliator.get("personality"), room_id=overdrive_pk)
                                
                            asyncio.create_task(fire_retaliator())

                    if data.get("type") == "STATE_UPDATE":
                        if data.get("system", {}).get("boggs_level") is not None:
                            current_global_boggs_level = int(data["system"]["boggs_level"])
                        elif data.get("data", {}).get("boggs_level") is not None:
                            current_global_boggs_level = int(data["data"]["boggs_level"])
                        if data.get("system", {}).get("chatbots_enabled") is not None:
                            global_chatbots_enabled = bool(data["system"]["chatbots_enabled"])
                        if not global_chatbots_enabled or os.path.exists(CHATBOTS_MUTED_FLAG) or os.path.exists(BOTS_PAUSED_FLAG):
                            continue
                        state = data.get("data", {})
                        pitcher = state.get("pitcher", "")
                        batter = state.get("batter", "")
                        status = state.get("status_msg", "")
                        is_pregame = any(lbl in (status or "").lower() for lbl in ["scheduled", "pre-game", "pregame", "warmup", "status change - pre-game", "simulation error", "no statcast"])
                        away_team = state.get("away_team", "Away")
                        home_team = state.get("home_team", "Home")
                        inning = state.get("inning", "")
                        
                        # 2026 TIMELINE ANCHOR + HALF-INNING STATE
                        offense_team = away_team if "Top" in inning else home_team
                        defense_team = home_team if "Top" in inning else away_team
                        game_pk = str(data.get("target_game_pk") or state.get("target_game_pk") or state.get("game_pk", ""))
                        
                        if 'last_known_game_states' not in globals():
                            globals()['last_known_game_states'] = {}
                        if game_pk:
                            globals()['last_known_game_states'][str(game_pk)] = state
                        inject_weedstack_events(game_pk)
                        inject_nfl_events(game_pk)
                        engine_override = state.get("engine_override", data.get("engine_override", "default"))
                        
                        game_key = f"{away_team}-{home_team}"
                        if game_pk:
                            key_to_pk[game_key] = game_pk
                            
                        # CRITICAL FIX: Only process state updates for games that are active and have loaded fans
                        if game_pk and not is_room_active(game_pk):
                            continue
                        active_rooms = set(RoomRosterRegistry.get_all_rosters().keys())
                        if not active_rooms:
                            active_rooms = set([str(f.get("room")) for f in active_fans if f.get("room")])
                        if game_pk not in active_rooms:
                            continue
                            
                        # --- AMBIENT ENTROPY MODE (70/30 CONVERSATIONAL SPLIT) ---
                        # Skip ambient yaps to restrict specifically to play_outcome events per work order
                        pass
                        
                        last_matchup = last_matchups.get(game_key, "")
                        last_status = last_statuses.get(game_key, "")
                        
                        matchup = f"{pitcher} vs {batter}"
                        
                        # 2026 TIMELINE ANCHOR + HALF-INNING STATE
                        baseline_anchor = f" [TIMELINE VERIFICATION: The current year is 2026. {batter} legally plays for the {offense_team}. {pitcher} legally plays for the {defense_team}. Do NOT act surprised by these teams or treat this as a simulation glitch. Off-season trades have naturally occurred.] "
                        
                        # FC-HALFBLIND-01: Intercept raw telemetry string and inject active team state
                        # so M.A.R.D. ALWAYS knows who is batting vs pitching regardless of string phrasing.
                        anchored_status = f"[{offense_team} BATTING | {defense_team} PITCHING] {status}"
                        
                        if not is_pregame and pitcher and batter and "Awaiting" not in matchup and matchup != last_matchup:
                            last_matchups[game_key] = matchup
                            print(f"[NEW MATCHUP] Processing: {matchup}")
                            # Skip matchup start yaps to restrict specifically to play_outcome events per work order
                            pass

                        if not is_pregame and status and status != last_status and "Awaiting" not in status and "Syncing" not in status:
                            last_statuses[game_key] = status
                            status_lower = status.lower()

                            # P1 FIX: Skip ambient fire + DOT echo for raw API status labels & simulation errors (not real play descriptions)
                            RAW_STATUS_LABELS = {"scheduled", "pre-game", "pregame", "warmup", "delayed", "postponed", "in progress", "final", "status change - pre-game"}
                            if status.strip().lower() in RAW_STATUS_LABELS or "simulation error" in status_lower or "no statcast" in status_lower:
                                print(f"[PLAY INTERCEPT] Skipping raw API status label or simulation error (P1 guard): {status}")
                                continue

                            # TKT-0021: Batter timeout telemetry filter
                            if "step off" in status_lower or "timeout" in status_lower or "pickoff attempt" in status_lower:
                                print(f"[PLAY INTERCEPT] Ignoring non-action telemetry: {status}")
                                continue

                            # Define play outcome conditions
                            strikeout = ("strikes out" in status_lower or "struck out" in status_lower)
                            walk = ("walks" in status_lower)
                            is_hit = ("singles" in status_lower or "doubles" in status_lower or "triples" in status_lower)
                            is_out = ("flies out" in status_lower or "grounds out" in status_lower or "pops out" in status_lower or "lines out" in status_lower or strikeout)
                            is_massive = any(cfg['keyword'] in status_lower for cfg in active_mlb_config if cfg['is_massive']) or "mound visit" in status_lower
                            is_homerun = "home run" in status_lower or "homers" in status_lower
                            is_error = "error" in status_lower
                            is_pitching_change = "pitching change" in status_lower
                            any_run_scored = "scores" in status_lower or "homers" in status_lower
                            is_pitch_event = any(k in status_lower for k in ["strike", "ball", "foul", "count"])

                            # Restrict chatbot yaps to play_outcome events and routine pitches with ambient chance
                            is_play_outcome = (is_massive or is_hit or is_out or walk or is_homerun or is_error or is_pitching_change or any_run_scored or is_pitch_event)
                            if not is_play_outcome:
                                print(f"[PLAY INTERCEPT] Restricting yaps to play_outcome. Skipping: {status}")
                                continue

                            print(f"[PLAY INTERCEPT] Reaction to: {status}")
                            bot_triggered = True
                            
                            try:
                                target_pk = key_to_pk.get(game_key)
                                LOG_PATH = f"/home/james/stacklabs/data/logs/fanstack_{datetime.now().strftime('%Y%m%d')}.log"
                                with open(LOG_PATH, 'a') as f:
                                    f.write(f"[{datetime.now().isoformat()}] MLB_TELEMETRY | SYSTEM: {away_team}@{home_team} - {inning} | {pitcher} to {batter} | {status}\n")
                            except Exception:
                                pass
                            
                            run_scored_desc = "A run scored on this play." if (any_run_scored or is_homerun) else "No runs scored on this play."
                            # FC-SCORING-01: Use offense_team (inning-aware) not just team presence
                            mets_batting = offense_team == "NYM"
                            mets_scored = any_run_scored and mets_batting
                            opp_scored = any_run_scored and not mets_batting and (home_team == "NYM" or away_team == "NYM")
                            cards_scored = any_run_scored and (home_team == "STL" or away_team == "STL") and offense_team == "STL"
                            tigers_scored = any_run_scored and (home_team == "DET" or away_team == "DET") and offense_team == "DET"
                            strikeout = ("strikes out" in status_lower or "struck out" in status_lower)
                            game_over = "final" in status_lower or "game over" in status_lower
                            mets_won = "mets win" in status_lower or (game_over and (home_team == "NYM" or away_team == "NYM") and "win" in status_lower)
                            
                            # Determine if Mets are pitching
                            mets_pitching = False
                            if ("Top" in inning and home_team == "NYM") or ("Bot" in inning and away_team == "NYM"):
                                mets_pitching = True
                                
                            # Govee SFX Triggers
                            if mets_scored:
                                if is_homerun:
                                    asyncio.create_task(govee_fx("homerun_mets"))
                                else:
                                    asyncio.create_task(govee_fx("mets_score"))
                            elif opp_scored:
                                asyncio.create_task(govee_fx("opp_score"))
                            elif strikeout and mets_pitching:
                                asyncio.create_task(govee_fx("strikeout_mets"))
                            elif mets_won or ("final" in status_lower and "mets" in status_lower):
                                asyncio.create_task(govee_fx("game_end_mets_win"))
                            
                            if cards_scored:
                                asyncio.create_task(govee_fx("cards_score"))
                            elif tigers_scored:
                                asyncio.create_task(govee_fx("tigers_score"))
                                
                            if not state.get("mard_engine", True):
                                continue

                            eligible_fans = []
                            seen_fans = set()
                            for f in active_fans:
                                lower_name = f['name'].lower()
                                if lower_name not in seen_fans and is_eligible(f, home_team, away_team, game_key, game_pk, state):
                                    eligible_fans.append(f)
                                    seen_fans.add(lower_name)
                            print(f"[DEBUG] Eligible Fans pre-matrix: {[f['name'] for f in eligible_fans]} | game_pk: {game_pk} | ht: {home_team} | aw: {away_team}")
                            
                            # FC-BROADCAST-CARD: Emit clean telemetry card BEFORE any LLM calls fire
                            # This lands instantly in the UI, giving visual context before bot cascade
                            _event_badge = ""
                            if is_homerun and mets_scored:   _event_badge = "💥 NYM HOME RUN"
                            elif is_homerun:                  _event_badge = "💥 HOME RUN"
                            elif mets_scored:                 _event_badge = "🟠 NYM SCORES"
                            elif opp_scored:                  _event_badge = "🔴 OPP SCORES"
                            elif strikeout and mets_pitching: _event_badge = "⚡ K — NYM PITCHING"
                            elif strikeout:                   _event_badge = "⚡ K"
                            elif is_pitching_change:          _event_badge = "🔄 PITCHING CHANGE"
                            elif is_error:                    _event_badge = "⚠️ ERROR"
                            else:                             _event_badge = "▶ PLAY"
                            _bot_names = " · ".join([f["name"].upper() for f in eligible_fans[:6]])
                            _overflow = f" +{len(eligible_fans)-6} more" if len(eligible_fans) > 6 else ""
                            _card = (
                                f"{_event_badge}  |  {inning}  |  "
                                f"{offense_team} BAT · {defense_team} P  |  "
                                f"{anchored_status.split('] ', 1)[-1]}  "
                                f"→ [{_bot_names}{_overflow}]"
                            )
                            await websocket.send(json.dumps({"type": "SYS_LOG", "text": _card, "target_game_pk": str(game_pk)}))
                            
                            # THE MARD DISCOURSE MATRIX
                            # FC-SCORING-02: Any run scored is a massive event — Barf MUST fire at 1.0
                            is_override_room = (str(game_pk) in ("823863", "823862", "823623", "823292", "823048", "823611", "823612"))
                            is_massive_event = any(cfg['keyword'] in status_lower for cfg in active_mlb_config if cfg['is_massive']) or any_run_scored or is_homerun or is_override_room or "mound visit" in status_lower
                            global_boggs = current_global_boggs_level if current_global_boggs_level is not None else int(state.get("boggs_level", 2) if state else 2)
                            
                            matrix_fans = []
                            for fan in eligible_fans:
                                cadence = fan.get("cadence", "pacer")
                                eff_boggs = max(int(fan.get("boggs_level", 2)), global_boggs)
                                
                                trigger_chance = 0.0
                                
                                # ── MARD DISCOURSE MATRIX (CADENCE-AWARE) ──────────────────────────────
                                # Play significance tier — determines lurker eligibility
                                is_significant_play = (is_homerun or any_run_scored or strikeout or
                                                       walk or is_pitching_change or is_error or is_hit)
                                is_routine_play = not is_significant_play and not is_massive_event
                                cadence_lower = cadence.lower() if cadence else "pacer"

                                if is_massive_event or eff_boggs >= 4:
                                    trigger_chance = 1.0  # Total chaos — everyone fires
                                elif eff_boggs == 4:
                                    # Stressed — agitators guaranteed, lurkers wake up on significant
                                    if cadence_lower == "agitator":
                                        trigger_chance = 1.0
                                    elif cadence_lower == "pacer":
                                        trigger_chance = 0.70
                                    elif cadence_lower == "lurker":
                                        trigger_chance = 0.55 if is_significant_play else 0.0
                                    else:
                                        trigger_chance = 0.60
                                elif eff_boggs == 3:
                                    if cadence_lower == "agitator":
                                        trigger_chance = 0.85
                                    elif cadence_lower == "pacer":
                                        trigger_chance = 0.50
                                    elif cadence_lower == "lurker":
                                        trigger_chance = 0.40 if is_significant_play else 0.0
                                    else:
                                        trigger_chance = 0.40
                                else:
                                    # Boggs 1-2 — Standard cadence enforcement
                                    if cadence_lower == "lurker":
                                        trigger_chance = 0.75 if is_significant_play else (0.20 if is_pitch_event else 0.10)
                                    elif cadence_lower == "pacer":
                                        trigger_chance = 0.65 if is_significant_play else (0.55 if is_pitch_event else 0.25)
                                    elif cadence_lower == "agitator":
                                        trigger_chance = 0.90 if is_significant_play else (0.70 if is_pitch_event else 0.45)
                                    else:
                                        trigger_chance = 0.45 if is_pitch_event else 0.30

                                fan_n = fan["name"].lower()
                                if (home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL"):
                                    if "battery" in fan_n:
                                        last_feud = global_battery_feud_tracker.get(game_pk)
                                        if last_feud != inning:
                                            trigger_chance = 1.0

                                if random.random() <= trigger_chance:
                                    matrix_fans.append(fan)
                                    print(f"[CADENCE MATRIX] {fan['name']} ({cadence_lower}) → FIRE (chance={trigger_chance:.2f}, sig={is_significant_play})")
                                else:
                                    print(f"[CADENCE MATRIX] {fan['name']} ({cadence_lower}) → SKIP (chance={trigger_chance:.2f}, sig={is_significant_play})")

                            # GUARANTEED PITCH BANTER PROTOCOL: Chat must never go dead between pitches!
                            if is_pitch_event and not matrix_fans and eligible_fans:
                                pacer_pool = [f for f in eligible_fans if f.get("cadence", "").lower() in ("pacer", "agitator")] or eligible_fans
                                guaranteed_fan = random.choice(pacer_pool)
                                matrix_fans.append(guaranteed_fan)
                                print(f"[CADENCE MATRIX] GUARANTEED PITCH BANTER ACTIVATED: Selected {guaranteed_fan['name']} for live pitch commentary")

                            # Volume cap: massive events = up to 4, routine = max 3, override room = capped at 4
                            # Bypassed completely if global_boggs >= 4
                            if global_boggs < 4:
                                if is_override_room:
                                    random.shuffle(matrix_fans)
                                    cap = 4
                                    matrix_fans = matrix_fans[:cap]
                                elif not is_massive_event:
                                    random.shuffle(matrix_fans)
                                    cap = 4 if is_significant_play else (2 if is_pitch_event else 3)
                                    matrix_fans = matrix_fans[:cap]


                            eligible_fans = matrix_fans
                            
                            # Log the feud if both triggered this inning
                            if (home_team == "ATL" and away_team == "PHI") or (home_team == "PHI" and away_team == "ATL"):
                                battery_count = sum(1 for f in eligible_fans if "battery" in f['name'].lower())
                                if battery_count >= 2:
                                    global_battery_feud_tracker[game_pk] = inning
                            
                            # Cap UI limit for routine plays enforced above

                            # Sequential Turn-Taking & Context Referencing for Broadcast Booth (Declarative)
                            booth_eligible = [
                                f for f in eligible_fans 
                                if f.get("persona_type") == "booth_announcer" or f.get("capabilities", {}).get("booth_cascade")
                            ]
                            if booth_eligible:
                                # Ensure only assigned commentators speak when the booth cascade runs,
                                # but keep other fans eligible!
                                eligible_fans = [
                                    f for f in eligible_fans 
                                    if not (f.get("persona_type") == "booth_announcer" or f.get("capabilities", {}).get("booth_cascade"))
                                ]
                                
                                async def run_booth_cascade(p_status, p_pitcher, p_batter, p_state, p_game_pk, p_ws):
                                    booth_members = [
                                        f for f in active_fans 
                                        if f.get("persona_type") == "booth_announcer" or f.get("capabilities", {}).get("booth_cascade")
                                    ]
                                    g_fan = next((f for f in booth_members if "gary" in f.get('name', '').lower() or "gary" in f.get('user_name', '').lower()), None)
                                    k_fan = next((f for f in booth_members if "keith" in f.get('name', '').lower() or "keith" in f.get('user_name', '').lower()), None)
                                    r_fan = next((f for f in booth_members if "ron" in f.get('name', '').lower() or "ron" in f.get('user_name', '').lower()), None)
                                    
                                    gary_text = ""
                                    keith_text = ""
                                    
                                    # Extract actual batter from play status if available
                                    actual_play_batter = p_batter
                                    if p_status and " " in p_status:
                                        for verb in [" flies out", " strikes out", " walks", " grounds out", " lines out", " pops out", " singles", " doubles", " homers", " called out"]:
                                            if verb in p_status:
                                                candidate = p_status.split(verb)[0].strip()
                                                if candidate and len(candidate.split()) in [2, 3] and not any(k in candidate for k in ["Status", "Ball", "Foul", "Pitching", "Braves", "Mets"]):
                                                    actual_play_batter = candidate
                                                break

                                    # Determine play-type guidance so LLMs don't hallucinate swings on balls
                                    play_type_guidance = ""
                                    p_stat_low = str(p_status).lower().strip()
                                    if p_stat_low == "ball" or p_stat_low.startswith("ball"):
                                        play_type_guidance = "NOTE: The pitch result is a BALL outside the zone (The batter took the pitch cleanly and DID NOT swing!). React to pitcher control, pitch spot, or batter discipline. DO NOT claim the batter swung, chased, or needs to lay off."
                                    elif "swinging strike" in p_stat_low or "struck out swinging" in p_stat_low:
                                        play_type_guidance = "NOTE: The pitch result is a SWINGING STRIKE. React to swing mechanics, pitch movement, or whiff."
                                    elif "called strike" in p_stat_low or "struck out looking" in p_stat_low:
                                        play_type_guidance = "NOTE: The pitch result is a CALLED STRIKE. React to pitch framing, zone spot, or batter taking."
                                    elif "walk" in p_stat_low:
                                        play_type_guidance = "NOTE: The result is a WALK. React to plate discipline or pitcher command."

                                    b_play = {
                                        "batter_team": p_state.get("away_team", "") if "Top" in p_state.get("inning", "") else p_state.get("home_team", ""),
                                        "pitcher_team": p_state.get("home_team", "") if "Top" in p_state.get("inning", "") else p_state.get("away_team", ""),
                                        "batter": actual_play_batter,
                                        "pitcher": p_pitcher,
                                        "away_team": p_state.get("away_team", ""),
                                        "home_team": p_state.get("home_team", ""),
                                        "lead_runs": abs(p_state.get("away_score", 0) - p_state.get("home_score", 0)),
                                        "leading_team": (p_state.get("away_team", "") if p_state.get("away_score", 0) > p_state.get("home_score", 0) else p_state.get("home_team", "")) if p_state.get("away_score", 0) != p_state.get("home_score", 0) else None,
                                        "inning": p_state.get("inning", "1"),
                                        "half_inning": p_state.get("inning_topbot", "top")
                                    }
                                    
                                    # 1. Gary Bot calls the play
                                    if g_fan:
                                        gary_prompt = (
                                            f"System Persona: You are Gary Bot, the iconic Mets play-by-play broadcaster. "
                                            f"Current matchup: {p_pitcher} vs {actual_play_batter}. Play: '{p_status}'. Result: {run_scored_desc}. {play_type_guidance} "
                                            f"Deliver a fresh, crisp, classic broadcast play call reacting directly to this specific play. "
                                            f"DO NOT repeat previous phrases. Be vivid, authentic, and spontaneous."
                                        )
                                        g_sys = build_dynamic_system_instruction(g_fan, is_massive_event, is_play_event, allow_rant=False, game_state=p_state, event_type="play", game_pk=p_game_pk)
                                        gary_text = await generate_commentary(GAME_TIME_MODEL, gary_prompt, g_fan['name'], g_fan['color'], p_ws, sys_override=g_sys, room_id=p_game_pk, active_play=b_play, source="AUTOMATED")
                                        await asyncio.sleep(2.5)
                                    
                                    # 2. Keith Fanboy responds
                                    if k_fan:
                                        ref_ctx = f" Gary Bot just called: '{gary_text}'." if gary_text else ""
                                        keith_prompt = (
                                            f"System Persona: You are Keith Fanboy, color commentator and former MVP. "
                                            f"Matchup: {p_pitcher} vs {actual_play_batter}. Play: '{p_status}'. Result: {run_scored_desc}. {play_type_guidance} {ref_ctx} "
                                            f"React with sharp, opinionated, colorful color commentary about {actual_play_batter}! Mention pitch location, defensive positioning, "
                                            f"umpire calls, or booth banter. NEVER repeat previous phrases or generic complaints. Keep it organic and entertaining!"
                                        )
                                        k_sys = build_dynamic_system_instruction(k_fan, is_massive_event, is_play_event, allow_rant=False, game_state=p_state, event_type="play", game_pk=p_game_pk)
                                        keith_text = await generate_commentary(GAME_TIME_MODEL, keith_prompt, k_fan['name'], k_fan['color'], p_ws, sys_override=k_sys, room_id=p_game_pk, active_play=b_play, source="AUTOMATED")
                                        await asyncio.sleep(2.5)
                                        
                                    # 3. Ron Bot wraps it up
                                    if r_fan:
                                        ref_ctx = ""
                                        if gary_text and keith_text:
                                            ref_ctx = f" Gary Bot called: '{gary_text}'. Keith Fanboy said: '{keith_text}'."
                                        elif gary_text:
                                            ref_ctx = f" Gary Bot called: '{gary_text}'."
                                        elif keith_text:
                                            ref_ctx = f" Keith Fanboy said: '{keith_text}'."
                                            
                                        ron_prompt = (
                                            f"System Persona: You are Ron Bot, former MLB starter and master pitching analyst. "
                                            f"Matchup: {p_pitcher} vs {actual_play_batter}. Play: '{p_status}'. Result: {run_scored_desc}. {play_type_guidance} "
                                            f"Booth context: {ref_ctx} "
                                            f"Provide an insightful, specific breakdown of pitch selection, arm slot, release point, or strategic sequencing against {actual_play_batter}. "
                                            f"Be analytical, precise, and completely unique to this moment."
                                        )
                                        r_sys = build_dynamic_system_instruction(r_fan, is_massive_event, is_play_event, allow_rant=False, game_state=p_state, event_type="play", game_pk=p_game_pk)
                                        await generate_commentary(GAME_TIME_MODEL, ron_prompt, r_fan['name'], r_fan['color'], p_ws, sys_override=r_sys, room_id=p_game_pk, active_play=b_play, source="AUTOMATED")

                                
                                asyncio.create_task(run_booth_cascade(status, pitcher, batter, state, game_pk, websocket))

                            for fan_idx, fan in enumerate(eligible_fans):
                                fan_name_low = fan['name'].lower()
                                
                                            
                                boggs_rule = get_boggs_rule(fan, state, status)
                                
                                fan_cadence_guard = fan.get("cadence", "pacer").lower()
                                if fan_cadence_guard == "lurker":
                                    guard = " You have been watching silently. THIS play broke your silence. Drop ONE sharp, surgical observation — under 10 words. No fluff. No filler. Make it count."
                                elif fan_cadence_guard == "agitator":
                                    guard = " You are an agitator. This play is fuel. React explosively — pick a fight with someone in the chat, make a bold outrageous claim, or throw shade at the opposition. Be short, loud, and provocative. Do NOT use the '@' symbol."
                                else:
                                    guard = f" Write a short hyped, nervous, or angry reaction. Do not vividly hallucinate historical or random players being on the field. Keep your focus on {batter} and {pitcher}, but DO NOT mechanically recite their names. React naturally according to your assigned personality."

                                # Neutral Game check
                                is_neutral_game = False
                                fan_team_norm = normalize_team(fan.get("team"))
                                away_team_norm = normalize_team(away_team)
                                home_team_norm = normalize_team(home_team)
                                if fan_team_norm and fan_team_norm not in ("GLOBAL", "MLB", "ANY", "ALL") and away_team_norm and home_team_norm:
                                    if fan_team_norm != away_team_norm and fan_team_norm != home_team_norm:
                                        is_neutral_game = True

                                if is_neutral_game:
                                    guard = f" Write a short, detached, cynical, or dismissive reaction from the perspective of a {fan_team_norm} fan watching a neutral game between {away_team} and {home_team}. Do NOT root for {away_team} or {home_team} using 'we' or 'our'. Bring up your own team's grievances or comment objectively."

                                chat_ctx_str = ""

                                local_ctx = build_local_ctx(fan, new_context_lines, home_team, away_team) if random.random() < 0.25 else ""
                                p_text = fan.get("short_personality", fan["personality"])
                                anti_rep = " CRITICAL PROMPT ADHERENCE: DO NOT use any of your signature bracketed catchphrases or repetitive sign-offs in this message. Do not literally recite the pitch metadata. Keep your phrasing entirely unique and conversational."

                                # ── MODEL SELECTION (Unified Inference Engine) ────────────────────────
                                mard_model = GAME_TIME_MODEL

                                # ── PROMPT CONSTRUCTION (Tiered Lore Strategy) ─────────────────────
                                # is_play_event: any ball-in-play, K, BB, HBP, error, pitching change
                                # that is NOT already a massive event. Gets the medium lore tier (1200
                                # chars) which restores trauma hooks + deep lore without full token bloat.
                                is_play_event = is_significant_play and not is_massive_event
                                allow_rant_flag = is_massive_event  # rant unlocked on massive events

                                # Build system instruction via tiered selector
                                sys_override = build_dynamic_system_instruction(
                                    fan, is_massive_event, is_play_event, allow_rant=allow_rant_flag,
                                    game_state=state, event_type=status, game_pk=key_to_pk.get(game_key) or game_pk
                                )
                                
                                # Calculate deterministic perspective flags
                                evt_category = detect_play_event_category(status)
                                active_play = {
                                    "event_type": evt_category,
                                    "status_text": status,
                                    "batter_team": offense_team,
                                    "pitcher_team": defense_team,
                                    "batter": batter,
                                    "pitcher": pitcher,
                                    "away_team": away_team,
                                    "home_team": home_team,
                                    "lead_runs": abs(state.get("away_score", 0) - state.get("home_score", 0)),
                                    "leading_team": (away_team if state.get("away_score", 0) > state.get("home_score", 0) else home_team) if state.get("away_score", 0) != state.get("home_score", 0) else None,
                                    "inning": state.get("inning", "1"),
                                    "half_inning": state.get("inning_topbot", "top"),
                                    "blown_call": state.get("blown_call") or (state.get("last_pitch") or {}).get("blown_call")
                                }
                                persp = resolve_at_bat_perspective(fan.get("team"), active_play)
                                
                                # Format perspective block
                                allies_str = ", ".join(persp["advocate_allies"])
                                opponents_str = ", ".join(persp["advocate_opponents"])
                                winning_status = "winning" if persp["is_advocate_winning"] else ("losing" if persp["current_lead_runs"] > 0 else "tied")
                                
                                if persp.get("is_neutral") or normalize_team(fan.get("team")) in ("GLOBAL", "MLB", "ANY", "ALL", "NONE", ""):
                                    persp_block = (
                                        f"\n### NEUTRAL BROADCASTER DIRECTIVE ###\n"
                                        f"You are an unbiased neutral observer with NO team loyalty to {away_team} or {home_team}. "
                                        f"Do NOT use 'we', 'our', or 'us' for either team. "
                                        f"Analyze the play objectively according to your character persona.\n"
                                    )
                                else:
                                    opp_team_name = away_team if normalize_team(fan.get("team")) == normalize_team(home_team) else home_team
                                    role = persp.get("advocate_role", "neutral")
                                    if role == "pitching":
                                        field_directive = (
                                            f"### FIELD POSITION: DEFENSE (PITCHING) ###\n"
                                            f"CRITICAL: Your team ({fan.get('team')}) is in the field PITCHING/DEFENDING. "
                                            f"You want your pitcher ({allies_str}) to strike out the batter, induce weak contact, or get an out. "
                                            f"You are ROOTING AGAINST the batter ({opponents_str}). "
                                            f"NEVER cheer for hits, gaps, home runs, scoring runs, or batting success right now! Your team is PITCHING!\n"
                                        )
                                    elif role == "batting":
                                        field_directive = (
                                            f"### FIELD POSITION: OFFENSE (BATTING) ###\n"
                                            f"CRITICAL: Your team ({fan.get('team')}) is at the plate BATTING/OFFENSE. "
                                            f"You want your batter ({allies_str}) to get a hit, put it in the gap, drive runners in, or hit a home run. "
                                            f"You are ROOTING AGAINST the pitcher ({opponents_str}). "
                                            f"NEVER cheer for strikeouts, pitching gems, or outs against your own batter!\n"
                                        )
                                    else:
                                        field_directive = ""

                                    persp_block = (
                                        f"\n### PERSPECTIVE ALIGNMENT DIRECTIVE ###\n"
                                        f"You cheer for: {fan.get('team')}. "
                                        f"Your team is playing against: {opp_team_name}. "
                                        f"Your team is currently {winning_status}. "
                                        f"Allied player on field: {allies_str}. "
                                        f"Opposing player on field: {opponents_str}. "
                                        f"{field_directive}"
                                        f"Cheer ONLY for your team ({fan.get('team')}) and allied players against {opp_team_name}. "
                                        f"CRITICAL GROUNDING: The opponent in this game is {opp_team_name}. Do NOT mention or hallucinate non-participating teams unless they are the active opponent. "
                                        f"Absolute team loyalty is required.\n"
                                    )
                                sys_override = str(sys_override) + persp_block

                                # Cypher overlay applied dynamically if triggered by state
                                if state.get("cypher_mode") or state.get("slam_poet_mode"):
                                    sys_override += " CRUCIAL OVERRIDE: YOU MUST DROP A FREESTYLE AABB RHYMING CYPHER RAP OVER THIS PLAY IN THE STYLE OF A SLAM POET."

                                # p_text preserved for any legacy callers that reference it below
                                p_text = sys_override

                                # Context injection gate:
                                # MASSIVE EVENT → pull inning scoring + recent play history from disk cache.
                                # ROUTINE/PLAY  → Context Drip only (~15 tokens). Fixes vacuum problem
                                #                 without re-introducing allPlays dumps or token burn.
                                game_pk_str = str(key_to_pk.get(game_key) or game_pk)
                                if is_massive_event:
                                    _inning_ctx   = get_inning_context(game_pk_str, live_state=state)
                                    _recent_plays = get_recent_plays(game_pk_str, n=3, live_state=state)
                                    _ctx_block    = f"{_inning_ctx} {_recent_plays}".strip()
                                    history_injection = (" " + _ctx_block) if _ctx_block else ""
                                else:
                                    history_injection = ""

                                # Assemble user prompt with lightweight game state context drip
                                _game_state_drip = {
                                    "away_score": state.get("away_score", 0),
                                    "home_score": state.get("home_score", 0),
                                    "inning_topbot": state.get("inning_topbot", ""),
                                    "inning": state.get("inning", ""),
                                    "outs": state.get("outs", 0),
                                }
                                player_context_str = build_player_context_str(pitcher, batter)

                                # WO0010164: Jake Taylor Blown Call Umpire Alert
                                blown_call_alert = ""
                                _bc = active_play.get("blown_call") or (state.get("last_pitch") or {}).get("blown_call")
                                if _bc and _bc.get("is_blown"):
                                    miss_inches = _bc.get("miss_inches", "---")
                                    miss_direction = _bc.get("miss_direction", "outside")
                                    blown_call_alert = (
                                        f"### JAKE TAYLOR UMPIRE AUDIT: BLOWN CALLED STRIKE DETECTED ###\n"
                                        f"The home plate umpire just called a STRIKE on a pitch that missed the zone by {miss_inches} inches ({miss_direction})!\n"
                                        f"The batter took the pitch and DID NOT challenge via ABS!\n"
                                        f"If your team is batting: LOSE YOUR MIND over the blind umpire robbing your team, and scream at the batter for not tapping his helmet to challenge!\n"
                                        f"If your team is pitching: Celebrate the stolen strike and laugh at the umpire gifting you a call!\n"
                                    )

                                prompt = (
                                    f"System Persona: You are '{fan['name']}'.\n"
                                    f"Game State: Score Away {_game_state_drip['away_score']} - Home {_game_state_drip['home_score']} | "
                                    f"Inning: {_game_state_drip['inning_topbot']} {_game_state_drip['inning']} | {_game_state_drip['outs']} Outs.\n"
                                    f"Play Event Result: {run_scored_desc}\n"
                                    f"{blown_call_alert}"
                                    f"{boggs_rule}{history_injection} {local_ctx}"
                                    f"{baseline_anchor}"
                                    f"The matchup is {away_team} at {home_team}. "
                                    f"The following play just happened in the game: '{anchored_status}'."
                                    f"{guard} {anti_rep}\n\nStrict Grounding Rule: You must adhere to the provided player stats and history below. Do not hallucinate stats or accolades not listed here.\nVerified Player Context:\n{player_context_str}"
                                )

                                async def staggered_commentary(f_model, f_prompt, f_name, f_color, wsock, f_sys, f_room, f_cadence, f_boggs, f_active_play=None, delay=0.0):
                                    if delay > 0:
                                        await asyncio.sleep(delay)
                                    if f_boggs >= 5:
                                         if f_cadence == "pacer":
                                             await asyncio.sleep(0.2)
                                         elif f_cadence == "lurker":
                                             await asyncio.sleep(0.4)
                                    await generate_commentary(f_model, f_prompt, f_name, f_color, wsock, sys_override=f_sys, room_id=f_room, active_play=f_active_play, source="AUTOMATED")

                                eff_cadence = fan.get("cadence", "pacer")
                                stagger_delay = fan_idx * 2.2
                                asyncio.create_task(staggered_commentary(mard_model, prompt, fan['name'], fan['color'], websocket, sys_override, key_to_pk.get(game_key), eff_cadence, eff_boggs, active_play, delay=stagger_delay))

                        if bot_triggered and new_context_lines:
                            for nl in new_context_lines:
                                reported_context.add(nl)

                    elif data.get("type") == "GLOBAL_CHATBOTS_TOGGLE":
                        global_chatbots_enabled = bool(data.get("enabled", True))
                        print(f"[CHATBOTS] Received GLOBAL_CHATBOTS_TOGGLE: enabled={global_chatbots_enabled}")
                        
                    elif data.get("type") == "ROOM_DEPLOYMENT_TOGGLE":
                        g_pk = str(data.get("game_pk", ""))
                        r_state = str(data.get("room_state", "staged"))
                        room_active_cache[g_pk] = (r_state == "active")
                        room_active_cache_ts[g_pk] = time.time()
                        print(f"[CHATBOTS] Received ROOM_DEPLOYMENT_TOGGLE: game_pk={g_pk}, state={r_state}")
                                
                    elif data.get("type") == "boggs_level":
                        lvl = int(data.get("level", 2))
                        current_global_boggs_level = lvl
                        print(f"[BOGGS CHAOS UPDATE] Global Boggs Toxicity Index adjusted to Level {lvl}/5")
                        
                    elif data.get("type") == "persona_strike":
                        persona_id = data.get("persona", "")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random baseball-related hot take."
                                print(f"[WARDY STRIKE] Firing {fan.get('name')}")
                                strike_model = fan['model']
                                if os.path.exists("/home/james/stacklabs/config/vertex_burn.on") and fan.get('name', '').lower() != 'dot':
                                    strike_model = GAME_TIME_MODEL
                                asyncio.create_task(generate_commentary(strike_model, prompt, fan['name'], fan['color'], websocket, sys_override=p_text, room_id=data.get("target_game_pk")))
                                break
                    elif data.get("type") == "hot_take_rant":
                        persona_id = data.get("persona", "")
                        topic = data.get("topic", "").strip()
                        engine_override = data.get("engine_override")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                
                                if topic:
                                    prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random, massive, unhinged baseball-related hot take rant specifically about: {topic}."
                                else:
                                    prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. Generate a completely random, massive, unhinged baseball-related hot take rant."

                                print(f"[WARDY RANT] Firing {fan.get('name')} for a hot take rant" + (f" about {topic}" if topic else ""))
                                model = engine_override if engine_override else fan['model']
                                if os.path.exists("/home/james/stacklabs/config/vertex_burn.on") and fan.get('name', '').lower() != 'dot':
                                    model = GAME_TIME_MODEL
                                room_id = data.get("target_game_pk", "hot_takes")
                                asyncio.create_task(generate_commentary(model, prompt, fan['name'], fan['color'], websocket, sys_override=p_text, allow_rant=True, room_id=room_id))
                                break
                    elif data.get("type") == "custom_prompt":
                        persona_id = data.get("persona", "")
                        custom_text = data.get("prompt", "")
                        for fan in active_fans:
                            if fan.get("id", "").lower() == persona_id.lower() or fan.get("name", "").lower() == persona_id.lower():
                                p_text = fan.get("short_personality", fan.get("personality", ""))
                                prompt = f"System Persona: You are '{fan.get('name')}'. '{p_text}'. The user gave you this specific instruction: {custom_text}."
                                print(f"[WARDY CUSTOM PROMPT] Firing {fan.get('name')} with custom instruction")
                                custom_model = fan['model']
                                if os.path.exists("/home/james/stacklabs/config/vertex_burn.on") and fan.get('name', '').lower() != 'dot':
                                    custom_model = GAME_TIME_MODEL
                                asyncio.create_task(generate_commentary(custom_model, prompt, fan['name'], fan['color'], websocket, sys_override=p_text, room_id=data.get("target_game_pk")))
                                break
                    elif data.get("type") == "update_context":
                        context_text = data.get("text", "").strip()
                        target_nodes = data.get("target_nodes", ["ALL"])
                        if context_text:
                            ctx_file = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
                            lines = []
                            if os.path.exists(ctx_file):
                                with open(ctx_file, "r") as f:
                                    lines = f.readlines()
                                    
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            node_prefix = f"[MARD_ISOLATION:{','.join(target_nodes)}] " if target_nodes and "ALL" not in target_nodes and "GLOBAL" not in target_nodes and "ALL_ACTIVE_YAPPERS" not in target_nodes else "[GLOBAL] "
                            new_line = f"[{timestamp}] {node_prefix}{context_text}\n"
                            
                            lines.append(new_line)
                            
                            if len(lines) > 10:
                                lines = lines[-10:]
                                
                            with open(ctx_file, "w") as f:
                                f.writelines(lines)
                            print(f"[WARDY CONTEXT INJECT] Added to hive mind (Rolling Cap 10): {context_text} for {target_nodes}")
                            
                    elif data.get("action") == "SYNC_DB_PERSONAS":
                        target_room = data.get("room_id")
                        if target_room:
                            RoomRosterRegistry.hydrate_from_db(target_room)
                        else:
                            RoomRosterRegistry.hydrate_from_db()
                        await reload_personas_from_db()
                            
                    elif data.get("type") == "persona_config":
                        action = data.get("action")
                        persona_data = data.get("persona", {})
                        
                        config_path_target = '/home/james/stacklabs/scripts/bot_config.json'
                        cfg = {}
                        if os.path.exists(config_path_target):
                            with open(config_path_target, "r") as f:
                                cfg = json.load(f)
                        
                        rooms = cfg.setdefault("rooms", {})
                        p_id = data.get("persona_id") or persona_data.get("id")
                        
                        if p_id:
                            # Remove from all rooms first safely
                            for room_id, room in rooms.items():
                                room["bots"] = [b for b in room.get("bots", []) if b.get("id") != p_id]
                            
                            if action in ["create", "update"]:
                                target_room = persona_data.get("room")
                                targets = ["mets", "braves"] if target_room == "both" else [target_room]
                                
                                for target in targets:
                                    if target not in rooms:
                                        res_t = resolve_team_name(target)
                                        team_ctx = res_t if res_t != "GLOBAL" else ""
                                        rooms[target] = {"name": f"{target.capitalize()} Room", "team": team_ctx, "bots": []}
                                    
                                    team_val = persona_data.get("team")
                                    if team_val:
                                        res_tv = resolve_team_name(team_val)
                                        if res_tv != "GLOBAL":
                                            team_val = res_tv
                                    
                                    rooms[target].setdefault("bots", []).append({
                                        "id": persona_data.get("id"),
                                        "instanceId": f"{persona_data.get('id')}-mod",
                                        "active": persona_data.get("active", True),
                                        "name": persona_data.get("name"),
                                        "model": persona_data.get("engine"),
                                        "boggs_level": persona_data.get("boggs"),
                                        "teamContext": team_val,
                                        "system_prompt": persona_data.get("prompt")
                                    })
                                    
                            with open(config_path_target, "w") as f:
                                json.dump(cfg, f, indent=2)
                                
                            # Hot Swap active_fans dynamically without reboot
                            active_fans.clear()
                            for room_id, room in rooms.items():
                                for bot in room.get("bots", []):
                                    if bot.get("active", True):
                                        engine = bot.get("model", "")
                                        if not engine or "gemini" in engine.lower():
                                            model = GAME_TIME_MODEL
                                        else:
                                            model = engine
                                        if not any(f["id"] == bot.get("id") for f in active_fans):
                                            team_ctx = bot.get("teamContext", "neutral")
                                            if team_ctx == "adversarial":
                                                color = "#ffaa4a"
                                            elif team_ctx == "analytical":
                                                color = "#b44aff"
                                            else:
                                                color = get_team_color(team_ctx, fallback="#00b4d8")
                                            active_fans.append({
                                                "id": bot.get("id"),
                                                "name": bot.get("name", bot.get("id").capitalize()),
                                                "team": bot.get("teamContext", ""),
                                                "boggs_level": bot.get("boggs_level", "low"),
                                                "color": color,
                                                "prompt": bot.get("system_prompt", ""),
                                                "model": model
                                            })
                                print(f"[WARDY GREEN ROOM] Hot Swapped config on the fly. {len(active_fans)} bots online.")
                            
        except websockets.exceptions.ConnectionClosedError:
            print("Chatbot Disconnected...")
        except Exception as e:
            print(f"Chatbot Error: {e}")
        finally:
            if countdown_task and not countdown_task.done():
                countdown_task.cancel()
            await asyncio.sleep(5)

if __name__ == "__main__":
    # ── PAYLOAD INTERCEPTOR (diagnostic middleware) ──────────────────────
    try:
        import sys as _sys
        _sys.path.insert(0, '/home/james/stacklabs/scripts')
        from fanstack_payload_interceptor import install_interceptor
        install_interceptor()
    except ImportError as _intercept_err:
        print(f"[CHATBOTS] Interceptor import failed: {_intercept_err}")

    asyncio.run(chatbot_loop())
