"""
game_cache_reader.py — Sovereign FanStack Hot Cache Reader
Node: clio (192.168.1.183)

Provides lightweight, read-only access to the local game state cache
written atomically by fanstack_background_poller.py on every state-hash delta.

INVARIANTS:
  - This module NEVER writes to disk.
  - This module NEVER touches sovereign_now.db or sovereign_intelligence.db.
  - This module NEVER raises exceptions — all failures return safe empty strings.
    Callers live in hot async paths; a crashed reader kills chatbot throughput.
  - All reads are single open-read-close operations. No file handles are held open.
  - Cache files are written with atomic rename by the poller, so partial reads
    are structurally impossible on Linux (rename is atomic on same filesystem).
"""
import json
import os
from typing import Optional

GAME_STATE_DIR = "/home/james/stacklabs/game_states"


def load_game_state(game_pk: str) -> Optional[dict]:
    """
    Load the current cached game state document for a given game_pk.

    Returns the parsed JSON dict on success.
    Returns None if the file does not exist, is 0 bytes, or is malformed JSON.

    Args:
        game_pk: The MLB game primary key as a string (e.g. "748532").
    """
    path = os.path.join(GAME_STATE_DIR, f"{game_pk}.json")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        # File exists but was caught mid-write — this should not happen given
        # the atomic rename pattern in the poller, but we guard it anyway.
        print(f"[CACHE READER] Malformed JSON for game {game_pk}: {e}")
        return None
    except Exception as e:
        print(f"[CACHE READER] Unexpected read error for game {game_pk}: {e}")
        return None


def get_inning_context(game_pk: str, max_scoring_innings: int = 3, live_state: dict = None) -> str:
    """
    Returns a compact, human-readable scoring summary string for the given game.

    This is the PRIMARY injection point for MASSIVE EVENTS (home runs, runs scored,
    ejections). It must NOT be called on routine pitches (balls, strikes, fouls).

    Returns empty string if the cache file does not exist or has no data.
    The caller is responsible for gating on is_massive_event before calling this.

    Args:
        game_pk:              The MLB game PK as a string.
        max_scoring_innings:  Maximum number of scoring innings to include in
                              the summary. Capped to prevent token creep.
                              Default: 3 (the last 3 innings where runs scored).
        live_state:           Optional dictionary containing live telemetry variables to hot-override.

    Returns:
        A pre-formatted string like:
        "Score: NYM 3 — PHI 1 | Bot 5th. Recent scoring: Inning 3 (Bot): NYM
         scored 2 run(s). Inning 5 (Top): PHI scored 1 run(s)."
        Or empty string "" on any failure.

    Example usage in fanstack_chatbots.py STATE_UPDATE handler:
        if is_massive_event:
            inning_ctx = get_inning_context(str(game_pk), live_state=state)
        else:
            inning_ctx = ""
    """
    doc = load_game_state(game_pk)
    if not doc:
        if live_state:
            doc = {}
        else:
            return ""

    try:
        # Override doc fields with live_state fields if present
        if live_state:
            for key in ["away_team", "home_team", "away_score", "home_score", "inning", "innings_detail"]:
                if key in live_state and live_state[key] is not None:
                    doc[key] = live_state[key]
                if key == "inning" and "inning" not in live_state and "current_inning" in live_state:
                    doc["inning"] = live_state["current_inning"]

        away      = doc.get("away_team", "AWY")
        home      = doc.get("home_team", "HME")
        away_score = doc.get("away_score", 0)
        home_score = doc.get("home_score", 0)
        inning_now = doc.get("inning", "")

        # Build inning-by-inning scoring narrative from innings_detail array.
        # innings_detail is populated from linescore.innings in the full feed.
        scoring_innings = []
        for inn in doc.get("innings_detail", []):
            inn_num   = inn.get("num", "?")
            away_runs = inn.get("away", {}).get("runs") or 0
            home_runs = inn.get("home", {}).get("runs") or 0
            if away_runs > 0:
                scoring_innings.append(
                    f"Inning {inn_num} (Top): {away} scored {away_runs} run(s)"
                )
            if home_runs > 0:
                scoring_innings.append(
                    f"Inning {inn_num} (Bot): {home} scored {home_runs} run(s)"
                )

        # Cap to last N scoring innings for token efficiency.
        recent_scoring = scoring_innings[-max_scoring_innings:] if scoring_innings else []

        score_line = f"Score: {away} {away_score} — {home} {home_score} | {inning_now}"
        if recent_scoring:
            return score_line + ". Recent scoring: " + ". ".join(recent_scoring) + "."
        return score_line + ". No runs scored yet."

    except Exception as e:
        print(f"[CACHE READER] get_inning_context error for game {game_pk}: {e}")
        return ""


def get_recent_plays(game_pk: str, n: int = 3, live_state: dict = None) -> str:
    """
    Returns the last N play descriptions from the cached game document as a
    compact pipe-delimited string.

    CALL GATE — This function must ONLY be invoked for MASSIVE EVENTS:
        - Home runs
        - Runs scored
        - Ejections / brawls / reviews
    It must NEVER be called for routine pitch events (balls, strikes, fouls, outs).
    The caller is responsible for enforcing this gate via is_massive_event.

    Args:
        game_pk: The MLB game PK as a string.
        n:       Number of recent plays to return. Default: 3.
                 Hard ceiling of 5 is enforced internally to prevent token creep
                 even if a caller passes a higher value.
        live_state: Optional dictionary containing live telemetry variables to hot-override.

    Returns:
        A pre-formatted string like:
        "Recent plays: [Top 4] Ball. | [Top 4] Called Strike. | [Top 4] Juan Soto
         homers (24) on a fly ball to left field."
        Or empty string "" on any failure or empty play list.
    """
    doc = load_game_state(game_pk)
    if not doc:
        if live_state:
            doc = {}
        else:
            return ""

    try:
        # Override doc fields with live_state fields if present
        if live_state:
            if "recent_plays" in live_state and live_state["recent_plays"] is not None:
                doc["recent_plays"] = live_state["recent_plays"]
            elif "status_msg" in live_state and live_state["status_msg"]:
                plays = list(doc.get("recent_plays", []))
                current_desc = live_state["status_msg"]
                current_inn = live_state.get("inning", "")
                if not plays or plays[-1].get("description") != current_desc:
                    plays.append({
                        "inning": current_inn,
                        "description": current_desc
                    })
                doc["recent_plays"] = plays

        plays = doc.get("recent_plays", [])
        if not plays:
            return ""

        # Hard ceiling: never return more than 5 plays regardless of caller arg.
        n = min(n, 5)
        recent = plays[-n:]
        parts = [
            f"[{p['inning']}] {p['description']}"
            for p in recent
            if p.get("description")
        ]
        if parts:
            return "Recent plays: " + " | ".join(parts)
        return ""

    except Exception as e:
        print(f"[CACHE READER] get_recent_plays error for game {game_pk}: {e}")
        return ""


def cache_exists(game_pk: str) -> bool:
    """
    Fast existence check for a game cache file.
    Use before calling get_inning_context() if you want to avoid a redundant
    double-read, though load_game_state() handles the missing-file case safely.

    Args:
        game_pk: The MLB game PK as a string.

    Returns:
        True if the cache file exists and has non-zero size.
        False otherwise.
    """
    path = os.path.join(GAME_STATE_DIR, f"{game_pk}.json")
    return os.path.isfile(path) and os.path.getsize(path) > 0


if __name__ == "__main__":
    # Smoke test — run directly to validate the module loads and directory is sane.
    import sys
    print(f"[CACHE READER] GAME_STATE_DIR: {GAME_STATE_DIR}")
    if not os.path.isdir(GAME_STATE_DIR):
        print(f"[CACHE READER] WARNING: Cache directory does not yet exist.")
        print(f"               It will be created automatically by fanstack_background_poller.py")
        print(f"               on the first state-hash delta for any live game.")
    else:
        cache_files = [f for f in os.listdir(GAME_STATE_DIR) if f.endswith(".json")]
        print(f"[CACHE READER] Found {len(cache_files)} cached game(s): {cache_files}")
        for cf in cache_files:
            pk = cf.replace(".json", "")
            doc = load_game_state(pk)
            if doc:
                print(f"  [{pk}] {doc.get('away_team')} {doc.get('away_score')} — "
                      f"{doc.get('home_team')} {doc.get('home_score')} | {doc.get('inning')}")
                print(f"         inning_ctx : {get_inning_context(pk)}")
                print(f"         recent_plays: {get_recent_plays(pk)}")
    print("[CACHE READER] Module OK.")
    sys.exit(0)
