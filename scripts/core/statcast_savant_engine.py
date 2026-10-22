"""
Sovereign OS: Statcast Savant Natural Language Text-to-SQL Engine
Governed by SOW-2026-09-11-JAKE-TAYLOR-SAVANT-ORACLE and Invariant I.8/I.9.

Transforms natural language baseball queries into safe, read-only SQL queries
over the 807 MB, 1.48M+ row statcast_pitches table in sovereign_intelligence.db.
"""

import os
import re
import json
import sqlite3
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
DATA_DB_PATH = REPO_ROOT / "data" / "sovereign_intelligence.db"
SYMLINK_DB_PATH = REPO_ROOT / "sovereign_intelligence.db"

STATCAST_DB = str(DATA_DB_PATH if DATA_DB_PATH.exists() else SYMLINK_DB_PATH)

FORBIDDEN_SQL_PATTERNS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bATTACH\b", r"\bDETACH\b",
    r"\bREPLACE\b", r"\bPRAGMA\b", r"\bEXEC\b", r"\bVACUUM\b",
    r";"
]

def sanitize_and_validate_sql(sql: str) -> str:
    """Ensure SQL is strictly a single, read-only SELECT statement."""
    clean_sql = sql.strip().strip("`").strip()
    if clean_sql.lower().startswith("sql"):
        clean_sql = clean_sql[3:].strip()

    # Strip a trailing semicolon if present so a single SQL statement is accepted
    clean_sql = clean_sql.rstrip(";").strip()
        
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, clean_sql, re.IGNORECASE):
            raise ValueError(f"Forbidden SQL operation detected: {pattern}")
            
    if not clean_sql.upper().startswith("SELECT"):
        raise ValueError("Only read-only SELECT queries are permitted.")
        
    return clean_sql


def get_deterministic_fallback(query_lower: str) -> Optional[Dict[str, Any]]:
    """Fast, accurate fallback templates for common baseball analytical prompts."""
    # 1. Pete Alonso splits (LHP vs RHP)
    if "alonso" in query_lower and any(w in query_lower for w in ["split", "left", "right", "lhp", "rhp", "hand"]):
        sql = """
        SELECT 
            CASE p_throws WHEN 'L' THEN 'vs Left-Handed Pitchers (LHP)' ELSE 'vs Right-Handed Pitchers (RHP)' END as matchup,
            COUNT(*) as total_pitches,
            COUNT(DISTINCT game_pk) as games,
            ROUND(AVG(launch_speed), 1) as avg_exit_velo_mph,
            ROUND(AVG(launch_angle), 1) as avg_launch_angle,
            ROUND(AVG(estimated_ba_using_speedangle), 3) as xBA,
            ROUND(AVG(estimated_woba_using_speedangle), 3) as xwOBA,
            SUM(CASE WHEN events = 'home_run' THEN 1 ELSE 0 END) as home_runs,
            SUM(CASE WHEN events = 'strikeout' THEN 1 ELSE 0 END) as strikeouts,
            SUM(CASE WHEN events = 'walk' THEN 1 ELSE 0 END) as walks
        FROM statcast_pitches
        WHERE (des LIKE '%Alonso%' OR player_name LIKE '%Alonso%')
          AND p_throws IN ('L', 'R')
        GROUP BY p_throws
        ORDER BY p_throws ASC;
        """.strip()
        return {
            "sql": sql,
            "chips": [
                {"label": "Batter", "value": "Pete Alonso"},
                {"label": "Split", "value": "p_throws (L vs R)"},
                {"label": "Metrics", "value": "Exit Velo, xBA, xwOBA, HRs"}
            ],
            "summary": "Pete Alonso statistical splits against left-handed vs. right-handed pitching, aggregating exit velocity, expected batting average (xBA), expected wOBA, and power outcomes across 1.48M Statcast records."
        }

    # 2. Francisco Lindor vs 95+ MPH heaters
    if "lindor" in query_lower and any(w in query_lower for w in ["heater", "fastball", "95", "velo", "velocity", "high heat"]):
        sql = """
        SELECT 
            pitch_name,
            COUNT(*) as pitches_seen,
            ROUND(AVG(release_speed), 1) as avg_pitch_velo,
            ROUND(AVG(launch_speed), 1) as avg_exit_velo,
            ROUND(AVG(estimated_ba_using_speedangle), 3) as xBA,
            ROUND(AVG(estimated_woba_using_speedangle), 3) as xwOBA,
            SUM(CASE WHEN events = 'home_run' THEN 1 ELSE 0 END) as home_runs,
            SUM(CASE WHEN events IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END) as total_hits
        FROM statcast_pitches
        WHERE (des LIKE '%Lindor%' OR player_name LIKE '%Lindor%')
          AND release_speed >= 95.0
          AND pitch_type IN ('FF', 'SI', 'FC')
        GROUP BY pitch_name
        ORDER BY pitches_seen DESC;
        """.strip()
        return {
            "sql": sql,
            "chips": [
                {"label": "Batter", "value": "Francisco Lindor"},
                {"label": "Filter", "value": "release_speed >= 95.0 MPH"},
                {"label": "Pitch Types", "value": "4-Seam (FF), Sinker (SI), Cutter (FC)"}
            ],
            "summary": "Francisco Lindor performance against elite velocity (95+ MPH heaters), measuring contact quality, exit velocity, and expected batting average by fastball variation."
        }

    # 3. Mark Vientos vs sliders / breaking balls
    if "vientos" in query_lower and any(w in query_lower for w in ["slider", "breaking", "spin", "whiff"]):
        sql = """
        SELECT 
            pitch_name,
            p_throws as pitcher_arm,
            COUNT(*) as pitches_faced,
            ROUND(AVG(launch_speed), 1) as avg_exit_velo,
            ROUND(AVG(estimated_ba_using_speedangle), 3) as xBA,
            SUM(CASE WHEN events = 'home_run' THEN 1 ELSE 0 END) as home_runs,
            SUM(CASE WHEN description IN ('swinging_strike', 'swinging_strike_blocked') THEN 1 ELSE 0 END) as whiffs,
            ROUND(SUM(CASE WHEN description IN ('swinging_strike', 'swinging_strike_blocked') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as whiff_pct
        FROM statcast_pitches
        WHERE (des LIKE '%Vientos%' OR player_name LIKE '%Vientos%')
          AND pitch_type IN ('SL', 'ST', 'CU')
        GROUP BY pitch_name, p_throws
        ORDER BY pitches_faced DESC;
        """.strip()
        return {
            "sql": sql,
            "chips": [
                {"label": "Batter", "value": "Mark Vientos"},
                {"label": "Arsenal", "value": "Slider (SL), Sweeper (ST), Curve (CU)"},
                {"label": "Key Metric", "value": "Whiff % & Exit Velo"}
            ],
            "summary": "Mark Vientos breakdown against breaking balls (sliders and sweepers), detailing whiff rate and contact authority broken down by pitcher arm."
        }

    # 4. Aaron Judge exit velocity / power
    if "judge" in query_lower:
        sql = """
        SELECT 
            pitch_type,
            COUNT(*) as pitches,
            ROUND(AVG(launch_speed), 1) as avg_exit_velo,
            ROUND(MAX(launch_speed), 1) as max_exit_velo,
            ROUND(AVG(estimated_ba_using_speedangle), 3) as xBA,
            ROUND(AVG(estimated_woba_using_speedangle), 3) as xwOBA,
            SUM(CASE WHEN events = 'home_run' THEN 1 ELSE 0 END) as home_runs
        FROM statcast_pitches
        WHERE (des LIKE '%Judge%' OR player_name LIKE '%Judge%')
          AND launch_speed IS NOT NULL
        GROUP BY pitch_type
        HAVING COUNT(*) >= 5
        ORDER BY home_runs DESC, avg_exit_velo DESC
        LIMIT 10;
        """.strip()
        return {
            "sql": sql,
            "chips": [
                {"label": "Batter", "value": "Aaron Judge"},
                {"label": "Metrics", "value": "Max Exit Velo, xBA, xwOBA"},
                {"label": "Filter", "value": "Batted Balls (launch_speed > 0)"}
            ],
            "summary": "Aaron Judge exit velocity and power distribution across pitch classifications, highlighting maximum exit velocity and expected weighted on-base average."
        }

    # 5. Default general Statcast query
    return None


async def generate_statcast_sql(query_text: str) -> Dict[str, Any]:
    """Generate SQL, parameter chips, and analytical summary using LLM or deterministic engine."""
    clean_query = query_text.strip()
    query_lower = clean_query.lower()
    
    # 1. Check deterministic fast path first
    fallback = get_deterministic_fallback(query_lower)
    if fallback:
        return fallback

    # 2. Schema Prompt for Gemini
    system_instruction = """You are the Sovereign OS Statcast Savant Engine. 
You translate natural language baseball analytical questions into a single valid, read-only SQLite query 
targeting the table `statcast_pitches` in `sovereign_intelligence.db`.

DATABASE SCHEMA:
Table: statcast_pitches (1,481,254 rows)
Columns:
- pitch_type (TEXT: FF, SL, SI, CH, CU, ST, FC, FS)
- game_date (TEXT: YYYY-MM-DD)
- release_speed (REAL: pitch velocity in MPH)
- player_name (TEXT: pitcher or batter name)
- des (TEXT: description of play outcome e.g. 'Pete Alonso homers (34)...')
- stand (TEXT: 'L' or 'R', batter handedness)
- p_throws (TEXT: 'L' or 'R', pitcher throwing arm)
- home_team, away_team (TEXT)
- events (TEXT: 'single', 'double', 'triple', 'home_run', 'strikeout', 'walk', 'field_out', etc.)
- description (TEXT: 'hit_into_play', 'ball', 'called_strike', 'swinging_strike', etc.)
- launch_speed (REAL: exit velocity in MPH)
- launch_angle (REAL: degrees)
- hit_distance_sc (REAL: projected distance in feet)
- estimated_ba_using_speedangle (REAL: expected batting average, xBA)
- estimated_woba_using_speedangle (REAL: expected wOBA, xwOBA)
- pitch_name (TEXT: '4-Seam Fastball', 'Slider', etc.)
- plate_x, plate_z, sz_top, sz_bot (REAL: pitch coordinates and strike zone bounds in feet)

CRITICAL BASEBALL RULES:
1. BATTER VS PITCHER HANDEDNESS:
   - When user asks about a batter facing lefties/righties, query `p_throws = 'L'` or `p_throws = 'R'`.
   - Match batter using `(des LIKE '%LastName%' OR player_name LIKE '%LastName%')`.
2. PITCHER VS BATTER STANCE:
   - When user asks about a pitcher facing left-handed/right-handed batters, query `stand = 'L'` or `stand = 'R'`.
3. METRICS & AGGREGATES:
   - Always calculate clean rounded aggregates:
     `COUNT(*) as pitches, ROUND(AVG(launch_speed), 1) as avg_exit_velo, ROUND(AVG(estimated_ba_using_speedangle), 3) as xBA, SUM(CASE WHEN events = 'home_run' THEN 1 ELSE 0 END) as home_runs`
4. SAFETY:
   - SELECT statements only.
   - Enforce `LIMIT 30` on non-aggregated row queries.

OUTPUT FORMAT:
Respond with STRICT JSON containing:
{
  "sql": "SELECT ... FROM statcast_pitches ...",
  "chips": [{"label": "Batter", "value": "Name"}, {"label": "Split", "value": "..."}],
  "summary": "Clinical 1-2 sentence analytical summary of what this query measures."
}
"""

    prompt = f"Translate this baseball question into a Statcast SQL query: '{clean_query}'"

    try:
        try:
            from core.utils import run_vertex_prompt, parse_json_garbage
        except ImportError:
            from scripts.core.utils import run_vertex_prompt, parse_json_garbage
        raw_response = await run_vertex_prompt(prompt, system_instruction=system_instruction)
        parsed = parse_json_garbage(raw_response)
        
        if isinstance(parsed, dict) and "sql" in parsed:
            parsed["sql"] = sanitize_and_validate_sql(parsed["sql"])
            if "chips" not in parsed or not isinstance(parsed["chips"], list):
                parsed["chips"] = [{"label": "Natural Query", "value": clean_query[:30]}]
            if "summary" not in parsed:
                parsed["summary"] = f"Executing Statcast analytical query for: {clean_query}"
            return parsed
    except Exception as e:
        print(f"⚠️ [SAVANT ENGINE] LLM SQL synthesis fallback engaged: {e}")

    # Fallback to general player search
    words = clean_query.split()
    target_player = words[0] if words else "Player"
    fallback_sql = f"""
    SELECT player_name, des, pitch_name, release_speed, launch_speed, launch_angle, estimated_ba_using_speedangle as xBA, events
    FROM statcast_pitches
    WHERE (des LIKE '%{target_player}%' OR player_name LIKE '%{target_player}%')
      AND events IS NOT NULL AND events != ''
    ORDER BY game_date DESC
    LIMIT 20;
    """.strip()
    return {
        "sql": fallback_sql,
        "chips": [{"label": "Search Target", "value": target_player}, {"label": "Engine", "value": "Standard Statcast"}],
        "summary": f"Retrieving recent Statcast batted ball events and pitch telemetry for {target_player}."
    }


def execute_savant_query(sql: str) -> Dict[str, Any]:
    """Execute validated read-only SQL against sovereign_intelligence.db."""
    validated_sql = sanitize_and_validate_sql(sql)
    
    if not os.path.exists(STATCAST_DB):
        raise FileNotFoundError(f"Statcast database not found at {STATCAST_DB}")

    conn = sqlite3.connect(STATCAST_DB, timeout=10.0)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Enforce read-only mode at database driver level
        cur.execute("PRAGMA query_only = ON;")
        cur.execute(validated_sql)
        rows = cur.fetchall()
        
        columns = [description[0] for description in cur.description] if cur.description else []
        results = [dict(row) for row in rows]
        
        return {
            "columns": columns,
            "results": results,
            "count": len(results)
        }
    finally:
        conn.close()


async def process_savant_oracle(query_text: str) -> Dict[str, Any]:
    """Full end-to-end pipeline: Question -> Text-to-SQL -> Execution -> Clinical Analysis."""
    # 1. Generate SQL and chips
    gen_result = await generate_statcast_sql(query_text)
    sql = gen_result["sql"]
    chips = gen_result.get("chips", [])
    summary = gen_result.get("summary", "")

    # 2. Execute SQL against the 807 MB database
    query_data = execute_savant_query(sql)

    # 3. Format clinical summary if rows were returned
    if query_data["count"] > 0 and len(query_data["results"]) == 2 and "vs" in str(query_data["results"][0]):
        # Handedness split comparative summary
        r1, r2 = query_data["results"][0], query_data["results"][1]
        summary += f" Split Breakdown: {r1.get('matchup', 'Group 1')}: {r1.get('avg_exit_velo_mph', r1.get('avg_exit_velo', '--'))} MPH exit velo, {r1.get('xBA', '--')} xBA, {r1.get('home_runs', 0)} HR. {r2.get('matchup', 'Group 2')}: {r2.get('avg_exit_velo_mph', r2.get('avg_exit_velo', '--'))} MPH exit velo, {r2.get('xBA', '--')} xBA, {r2.get('home_runs', 0)} HR."

    return {
        "sql": sql,
        "chips": chips,
        "summary": summary,
        "columns": query_data["columns"],
        "results": query_data["results"],
        "count": query_data["count"]
    }
