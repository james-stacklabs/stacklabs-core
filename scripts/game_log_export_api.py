#!/usr/bin/env python3
"""
game_log_export_api.py
======================
STRY1779341054 — Game Room Log Export

FastAPI router mounted by sovereign_core_api.py.
Exports game_chat + game_play data as Markdown or JSON.

Routes:
  GET /api/game-log/games              — list games with chat log data
  GET /api/game-log/export/{game_pk}   — full export (format=md|json|csv)
  GET /api/game-log/chat/{game_pk}     — chat messages only
  GET /api/game-log/plays/{game_pk}    — play-by-play only
"""

import sqlite3
import json
import os
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

router = APIRouter(prefix="/api/game-log", tags=["game-log"])

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/games")
def list_games_with_logs():
    """Games that have chat log data, newest first."""
    conn = _db()
    rows = conn.execute("""
        SELECT 
            gc.game_pk,
            COALESCE(ms.game_date, 'Unknown Date') AS game_date,
            COALESCE(ms.away_team, '?') AS away_team,
            COALESCE(ms.home_team, '?') AS home_team,
            COALESCE(ms.venue, '') AS venue,
            COALESCE(ms.status, '') AS status,
            COUNT(gc.id) AS message_count,
            MIN(gc.created_at) AS log_start,
            MAX(gc.created_at) AS log_end,
            COUNT(DISTINCT gc.persona) AS persona_count,
            COUNT(DISTINCT gc.model) AS model_count
        FROM game_chat gc
        LEFT JOIN mlb_schedule ms ON CAST(ms.game_pk AS TEXT) = gc.game_pk
        GROUP BY gc.game_pk
        ORDER BY log_end DESC
    """).fetchall()
    conn.close()
    return {"games": [dict(r) for r in rows], "count": len(rows)}


@router.get("/chat/{game_pk}")
def get_chat_log(game_pk: str, persona: str = None, limit: int = 500):
    """Raw chat messages for a game, optionally filtered by persona."""
    conn = _db()
    q = "SELECT * FROM game_chat WHERE game_pk = ?"
    params = [game_pk]
    if persona:
        q += " AND persona = ?"
        params.append(persona)
    q += " ORDER BY created_at ASC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {"messages": [dict(r) for r in rows], "count": len(rows), "game_pk": game_pk}


@router.get("/plays/{game_pk}")
def get_play_log(game_pk: str, limit: int = 500):
    """Play-by-play Statcast events for a game."""
    conn = _db()
    rows = conn.execute("""
        SELECT id, game_pk, play_id, inning, half, event_type,
               batter, pitcher, pitch_speed, pitch_type, description,
               score_away, score_home, outs, recorded_at
        FROM game_play
        WHERE game_pk = ?
        ORDER BY recorded_at ASC
        LIMIT ?
    """, (game_pk, limit)).fetchall()
    conn.close()
    return {"plays": [dict(r) for r in rows], "count": len(rows), "game_pk": game_pk}


@router.get("/export/{game_pk}")
@router.get("/export/{game_pk}/{format}")
def export_game_log(game_pk: str, format: str = "md"):
    """
    Full game log export: chat + play-by-play merged chronologically.
    format: md (Markdown), json, csv
    """
    format = str(format or "md").lower()
    if format not in ("md", "json", "csv"):
        format = "md"
    conn = _db()

    game_row = conn.execute(
        "SELECT * FROM mlb_schedule WHERE game_pk = ?", (game_pk,)
    ).fetchone()
    if not game_row:
        # Also try string match in case game_pk not in mlb_schedule — still export chat
        pass
    game = dict(game_row) if game_row else {"game_pk": game_pk, "game_date": "Unknown", "away_team": "?", "home_team": "?", "venue": ""}

    # Unified SQL union query to fetch and sort chat and play logs chronologically database-side
    query = """
        SELECT 'chat' AS log_type, created_at AS ts, persona, text, model, msg_type,
               NULL AS inning, NULL AS half, NULL AS event_type,
               NULL AS batter, NULL AS pitcher, NULL AS pitch_speed, NULL AS description
        FROM game_chat WHERE game_pk = ?

        UNION ALL

        SELECT 'play' AS log_type, recorded_at AS ts, NULL AS persona, description AS text,
               NULL AS model, NULL AS msg_type,
               inning, half, event_type, batter, pitcher, pitch_speed, description
        FROM game_play WHERE game_pk = ?

        ORDER BY ts ASC
    """
    rows = conn.execute(query, (game_pk, game_pk)).fetchall()
    conn.close()

    all_events = [dict(r) for r in rows]
    chat_count = sum(1 for e in all_events if e["log_type"] == "chat")
    play_count = len(all_events) - chat_count

    matchup = f"{game['away_team']} @ {game['home_team']}"
    game_date = game['game_date']
    filename_base = f"game_log_{game_pk}_{game_date.replace('-', '')}"

    # ── Markdown export ───────────────────────────────────────────────────────
    if format == "md":
        lines = [
            f"# 📋 Game Room Log: {matchup}",
            f"**Date:** {game_date}  |  **Game PK:** {game_pk}  |  **Venue:** {game.get('venue', 'N/A')}",
            f"**Exported:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            f"## Summary",
            f"- **Total Events:** {len(all_events)}",
            f"- **Chat Messages:** {chat_count}",
            f"- **Plays Logged:** {play_count}",
            "",
            "---",
            "",
            "## Chronological Log",
            "",
        ]
        for e in all_events:
            ts = (e.get("ts") or "")[:19].replace("T", " ")
            if e["log_type"] == "chat":
                persona = e.get("persona") or "?"
                model = e.get("model") or ""
                text = e.get("text") or ""
                model_tag = f" `[{model}]`" if model else ""
                lines.append(f"**{ts}** 🗣️ **{persona}**{model_tag}")
                lines.append(f"> {text}")
                lines.append("")
            else:
                inning = e.get("inning") or "?"
                half = e.get("half") or ""
                batter = e.get("batter") or ""
                pitcher = e.get("pitcher") or ""
                desc = e.get("description") or ""
                speed = e.get("pitch_speed") or ""
                speed_tag = f" @ {speed} mph" if speed else ""
                lines.append(f"**{ts}** ⚾ **Inning {inning} {half}** — {batter} vs {pitcher}{speed_tag}")
                lines.append(f"*{desc}*")
                lines.append("")

        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.md"}
        )

    # ── JSON export ────────────────────────────────────────────────────────────
    elif format == "json":
        payload = {
            "game_pk": game_pk,
            "game_date": game_date,
            "matchup": matchup,
            "venue": game.get("venue"),
            "exported_at": datetime.utcnow().isoformat(),
            "summary": {"total": len(all_events), "chat": chat_count, "plays": play_count},
            "events": all_events,
        }
        return Response(
            content=json.dumps(payload, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.json"}
        )

    # ── CSV export ─────────────────────────────────────────────────────────────
    else:
        headers_row = "ts,log_type,persona,model,inning,half,event_type,batter,pitcher,pitch_speed,text"
        rows_csv = []
        for e in all_events:
            def esc(v):
                s = str(v or "").replace('"', '""')
                return f'"{s}"' if "," in s or "\n" in s or '"' in s else (s or "")
            rows_csv.append(",".join([
                esc(e.get("ts", "")[:19]),
                esc(e.get("log_type")),
                esc(e.get("persona")),
                esc(e.get("model")),
                esc(e.get("inning")),
                esc(e.get("half")),
                esc(e.get("event_type")),
                esc(e.get("batter")),
                esc(e.get("pitcher")),
                esc(e.get("pitch_speed")),
                esc(e.get("text")),
            ]))
        content = headers_row + "\n" + "\n".join(rows_csv)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
        )
