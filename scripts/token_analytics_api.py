#!/usr/bin/env python3
"""
token_analytics_api.py
======================
STRY1779338715 — FanStack Token Usage Analytics

FastAPI router mounted by sovereign_core_api.py.
Surfaces token burn data from mlb_schedule + game_persona tables.

Routes:
  GET /api/token-analytics/games          — games with token data
  GET /api/token-analytics/game/{game_pk} — full report for one game
  GET /api/token-analytics/trends         — daily rollup
  GET /api/token-analytics/leaderboard    — all-time persona burn
  GET /api/token-analytics/summary        — fleet-wide totals
"""

import sqlite3
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

router = APIRouter(prefix="/api/token-analytics", tags=["token-analytics"])

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Gemini 2.5 Flash blended rate (input+output averaged)
# Input: $0.15/1M | Output: $0.60/1M → blended ~$0.30/1M
# Until we have input/output split tracking, use blended
BLENDED_COST_PER_M = 0.30
# sys_tokens = Mean Gene Bouncer (same model)
SYS_COST_PER_M = 0.30


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _est_cost(tokens: int) -> float:
    return round(tokens * BLENDED_COST_PER_M / 1_000_000, 4)


@router.get("/games")
def get_games_with_tokens():
    """All games that have token data, sorted by date DESC."""
    conn = _db()
    rows = conn.execute("""
        SELECT 
            ms.game_pk,
            ms.game_date,
            ms.away_team,
            ms.home_team,
            ms.venue,
            ms.status,
            ms.total_tokens,
            ms.gemini_tokens,
            ms.sys_tokens,
            ROUND(ms.total_tokens / 1000000.0, 3) AS total_M,
            ROUND(ms.gemini_tokens * ? / 1000000.0, 4) AS est_cost_usd,
            COUNT(gp.id) AS active_personas
        FROM mlb_schedule ms
        LEFT JOIN game_persona gp ON gp.game_pk = CAST(ms.game_pk AS TEXT) AND gp.total_tokens > 0
        WHERE ms.total_tokens > 0
        GROUP BY ms.game_pk
        ORDER BY ms.game_date DESC, ms.total_tokens DESC
    """, (BLENDED_COST_PER_M,)).fetchall()
    conn.close()
    return {"games": [dict(r) for r in rows], "count": len(rows)}


@router.get("/game/{game_pk}")
def get_game_report(game_pk: str):
    """Full token report for a single game."""
    conn = _db()

    # Game summary
    game = conn.execute("""
        SELECT 
            ms.game_pk, ms.game_date, ms.away_team, ms.home_team,
            ms.venue, ms.status,
            ms.total_tokens, ms.gemini_tokens, ms.sys_tokens,
            ms.gemini_input_tokens, ms.gemini_output_tokens,
            ROUND(ms.total_tokens / 1000000.0, 3) AS total_M,
            ROUND(ms.gemini_tokens / 1000000.0, 3) AS gemini_M,
            ROUND(ms.sys_tokens / 1000000.0, 3) AS sys_M,
            ROUND(ms.gemini_tokens * ? / 1000000.0, 4) AS gemini_cost_usd,
            ROUND(ms.sys_tokens * ? / 1000000.0, 4) AS sys_cost_usd,
            ROUND(ms.total_tokens * ? / 1000000.0, 4) AS total_cost_usd,
            CASE WHEN ms.total_tokens > 0 
                 THEN ROUND(ms.gemini_tokens * 100.0 / ms.total_tokens, 1) 
                 ELSE 0 END AS gemini_pct,
            CASE WHEN ms.total_tokens > 0 
                 THEN ROUND(ms.sys_tokens * 100.0 / ms.total_tokens, 1) 
                 ELSE 0 END AS sys_pct
        FROM mlb_schedule ms
        WHERE ms.game_pk = ?
    """, (BLENDED_COST_PER_M, SYS_COST_PER_M, BLENDED_COST_PER_M, game_pk)).fetchone()

    if not game:
        return JSONResponse({"error": "game not found"}, status_code=404)

    # Per-persona breakdown
    personas = conn.execute("""
        SELECT 
            p.user_name,
            p.display_name,
            p.team,
            p.color AS hex,
            p.avatar_url,
            gp.total_tokens,
            gp.gemini_tokens,
            gp.input_tokens,
            gp.output_tokens,
            ROUND(gp.total_tokens / 1000000.0, 3) AS total_M,
            ROUND(gp.gemini_tokens * ? / 1000000.0, 4) AS est_cost_usd,
            CASE WHEN ? > 0 
                 THEN ROUND(gp.total_tokens * 100.0 / ?, 1) 
                 ELSE 0 END AS pct_of_game
        FROM game_persona gp
        JOIN persona p ON p.id = gp.persona_id
        WHERE gp.game_pk = ? AND gp.total_tokens > 0
        ORDER BY gp.total_tokens DESC
    """, (BLENDED_COST_PER_M, game["total_tokens"], game["total_tokens"], game_pk)).fetchall()

    conn.close()
    return {
        "game": dict(game),
        "personas": [dict(p) for p in personas],
        "persona_count": len(personas),
    }


@router.get("/trends")
def get_trends(days: int = 30):
    """Daily token burn rollup for the last N days."""
    conn = _db()
    rows = conn.execute("""
        SELECT 
            ms.game_date,
            COUNT(*) AS games,
            SUM(ms.total_tokens) AS total_tokens,
            SUM(ms.gemini_tokens) AS gemini_tokens,
            SUM(ms.sys_tokens) AS sys_tokens,
            ROUND(SUM(ms.total_tokens) / 1000000.0, 3) AS total_M,
            ROUND(SUM(ms.gemini_tokens) * ? / 1000000.0, 4) AS est_cost_usd
        FROM mlb_schedule ms
        WHERE ms.total_tokens > 0
          AND ms.game_date >= date('now', ? || ' days')
        GROUP BY ms.game_date
        ORDER BY ms.game_date ASC
    """, (BLENDED_COST_PER_M, f"-{days}")).fetchall()
    conn.close()

    rows_list = [dict(r) for r in rows]
    total_tokens = sum(r["total_tokens"] for r in rows_list)
    total_cost = sum(r["est_cost_usd"] for r in rows_list)

    return {
        "days": days,
        "trend": rows_list,
        "totals": {
            "total_tokens": total_tokens,
            "total_M": round(total_tokens / 1_000_000, 2),
            "est_cost_usd": round(total_cost, 4),
            "game_nights": len(rows_list),
        }
    }


@router.get("/leaderboard")
def get_leaderboard():
    """All-time per-persona cumulative token burn across all games."""
    conn = _db()
    rows = conn.execute("""
        SELECT 
            p.user_name,
            p.display_name,
            p.team,
            p.color AS hex,
            p.avatar_url,
            SUM(gp.total_tokens) AS lifetime_tokens,
            SUM(gp.gemini_tokens) AS lifetime_gemini,
            COUNT(DISTINCT gp.game_pk) AS games_played,
            ROUND(SUM(gp.total_tokens) / 1000000.0, 2) AS lifetime_M,
            ROUND(SUM(gp.gemini_tokens) * ? / 1000000.0, 4) AS est_cost_usd,
            ROUND(AVG(gp.total_tokens) / 1000000.0, 2) AS avg_M_per_game,
            MAX(gp.total_tokens) AS peak_game_tokens
        FROM game_persona gp
        JOIN persona p ON p.id = gp.persona_id
        WHERE gp.total_tokens > 0
        GROUP BY p.user_name
        ORDER BY lifetime_tokens DESC
        LIMIT 25
    """, (BLENDED_COST_PER_M,)).fetchall()
    conn.close()
    return {"leaderboard": [dict(r) for r in rows], "count": len(rows)}


@router.get("/summary")
def get_fleet_summary():
    """Fleet-wide totals for the dashboard headline cards."""
    conn = _db()

    totals = conn.execute("""
        SELECT 
            COUNT(*) AS total_games,
            SUM(total_tokens) AS all_time_tokens,
            SUM(gemini_tokens) AS all_time_gemini,
            SUM(sys_tokens) AS all_time_sys,
            MAX(total_tokens) AS peak_game_tokens,
            ROUND(SUM(total_tokens) / 1000000.0, 2) AS all_time_M,
            ROUND(SUM(gemini_tokens) * ? / 1000000.0, 4) AS all_time_cost_usd,
            AVG(total_tokens) AS avg_tokens_per_game
        FROM mlb_schedule WHERE total_tokens > 0
    """, (BLENDED_COST_PER_M,)).fetchone()

    peak_game = conn.execute("""
        SELECT game_pk, game_date, away_team || ' @ ' || home_team AS matchup, total_tokens
        FROM mlb_schedule WHERE total_tokens > 0
        ORDER BY total_tokens DESC LIMIT 1
    """).fetchone()

    top_persona = conn.execute("""
        SELECT p.user_name, p.display_name, p.color AS hex, SUM(gp.total_tokens) AS t
        FROM game_persona gp JOIN persona p ON p.id = gp.persona_id
        WHERE gp.total_tokens > 0
        GROUP BY p.user_name ORDER BY t DESC LIMIT 1
    """).fetchone()

    # Credit runway (remaining GCP free credit)
    remaining_credit_usd = 291.80
    cost_per_game_avg = (dict(totals)["all_time_cost_usd"] / max(1, dict(totals)["total_games"]))
    games_remaining = int(remaining_credit_usd / max(0.01, cost_per_game_avg))

    conn.close()
    return {
        "totals": dict(totals),
        "peak_game": dict(peak_game) if peak_game else None,
        "top_persona": dict(top_persona) if top_persona else None,
        "credit_runway": {
            "remaining_usd": remaining_credit_usd,
            "avg_cost_per_game": round(cost_per_game_avg, 4),
            "est_games_remaining": games_remaining,
        }
    }


@router.get("/export/{game_pk}")
def export_game_csv(game_pk: str):
    """CSV export of per-persona token data for a game."""
    conn = _db()
    game = conn.execute(
        "SELECT game_date, away_team, home_team FROM mlb_schedule WHERE game_pk=?",
        (game_pk,)
    ).fetchone()

    rows = conn.execute("""
        SELECT p.user_name, p.team, gp.total_tokens, gp.gemini_tokens, gp.sys_tokens,
               gp.input_tokens, gp.output_tokens,
               ROUND(gp.gemini_tokens * 0.30 / 1000000.0, 6) AS est_cost_usd
        FROM game_persona gp JOIN persona p ON p.id = gp.persona_id
        WHERE gp.game_pk = ? ORDER BY gp.total_tokens DESC
    """, (game_pk,)).fetchall()
    conn.close()

    lines = ["persona,team,total_tokens,gemini_tokens,sys_tokens,input_tokens,output_tokens,est_cost_usd"]
    for r in rows:
        lines.append(",".join(str(v) for v in dict(r).values()))

    filename = f"token_report_{game_pk}_{game['game_date'] if game else 'unknown'}.csv"
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
