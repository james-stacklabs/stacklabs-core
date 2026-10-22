#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011237: FastAPI Blueprint for CFB Week 7 Carnage & Entity-Scoped Stream Tails.
Enforces Argon Law 3 (Cursor Pagination), Law 5 (Zero Cross-Game Bleed), and Law 7 (Dynamic Ceiling Lock).
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/faas/cfb", tags=["faas_cfb_carnage"])

BASE_DIR = Path("/home/james/stacklabs")
DB_PATH = Path(os.getenv("WIRETAP_DB_PATH", str(BASE_DIR / "data" / "morning_wiretap.db")))


def _get_wal_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


@router.get("/week7_carnage")
def get_cfb_week7_carnage() -> Dict[str, Any]:
    """
    Argon Law 7: Dynamically queries cfb_carnage_autopsy with locked snapshot ceiling.
    """
    if not DB_PATH.exists():
        return {"status": "EMPTY_LEDGER", "total_games": 0, "items": []}

    conn = _get_wal_conn()
    try:
        has_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cfb_carnage_autopsy'").fetchone()
        if not has_table:
            return {"status": "NO_SCHEMA", "total_games": 0, "items": []}

        rows = conn.execute(
            """
            SELECT
                game_id, season_week, kickoff_utc,
                away_team, away_rank, away_score,
                home_team, home_rank, home_score,
                spread_favorite, closing_spread, upset_margin_vs_spread,
                portal_flattening_index, sampled_messages, unique_authors,
                peak_cpm, mean_shannon_entropy, caps_ratio,
                flatline_drop_ratio, shibboleth_hits_json,
                decisive_catalyst, content_sha256, last_synced_at
            FROM cfb_carnage_autopsy
            WHERE season_week = 7
            ORDER BY portal_flattening_index DESC, upset_margin_vs_spread DESC, game_id ASC;
            """
        ).fetchall()

        items: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            raw_shib = item.pop("shibboleth_hits_json", "{}")
            try:
                item["shibboleth_hits"] = json.loads(raw_shib)
            except Exception:
                item["shibboleth_hits"] = {}
            items.append(item)

        mean_prfi = (
            round(sum(x["portal_flattening_index"] for x in items) / len(items), 4)
            if items
            else 0.0
        )
        return {
            "status": "OK",
            "total_games": len(items),
            "mean_portal_flattening_index": mean_prfi,
            "items": items,
        }
    finally:
        conn.close()


@router.get("/stream_tail/{game_id}")
def get_entity_scoped_stream_tail(
    game_id: str,
    after_id: int = Query(0, ge=0, description="Indexed primary-key cursor"),
    window_hours: int = Query(24, ge=1, le=72, description="Rolling lookback floor in hours"),
    limit: int = Query(200, ge=1, le=500, description="Max rows per cursor page"),
) -> Dict[str, Any]:
    """
    Argon Law 3 & Law 5: Strict entity-scoped cursor pagination with zero global fallback bleed.
    Dynamically maps game IDs, game PKs, or team dynamic channel keys.
    Returns honest empty items[] + NO_ACTIVE_STREAM when no matching rows exist.
    """
    clean_id = game_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="game_id is required")

    if not DB_PATH.exists():
        return {
            "game_id": clean_id,
            "stream_status": "NO_ACTIVE_STREAM",
            "snapshot_max_id": 0,
            "next_cursor_id": after_id,
            "velocity_buckets_cpm": [],
            "items": [],
        }

    conn = _get_wal_conn()
    try:
        # Resolve candidate channels dynamically
        candidates = [clean_id]
        if "CFB_2026_W7_" in clean_id:
            tokens = clean_id.replace("CFB_2026_W7_", "").split("_")
            if len(tokens) == 2:
                away_t, home_t = tokens[0], tokens[1]
                candidates.extend([f"{home_t}_dynamic", f"{away_t}_dynamic", f"{away_t}@{home_t} LIVE"])
        elif clean_id.endswith("_dynamic"):
            candidates.append(clean_id)
        else:
            candidates.extend([f"{clean_id}_dynamic", f"CFB_{clean_id}"])

        placeholders = ",".join(["?"] * len(candidates))
        window_floor = time.time() - (window_hours * 3600.0)

        # Argon Law 7: Lock snapshot ceiling once for consistent denominator and pagination
        ceiling_query = f"""
            SELECT COALESCE(MAX(id), 0) AS max_id, COUNT(*) AS total_rows, COUNT(DISTINCT author) AS unique_authors
            FROM chat_telemetry
            WHERE channel_key IN ({placeholders}) AND epoch_time >= ?;
        """
        ceiling_row = conn.execute(ceiling_query, candidates + [window_floor]).fetchone()

        max_id = int(ceiling_row["max_id"]) if ceiling_row else 0
        if max_id == 0:
            return {
                "game_id": clean_id,
                "stream_status": "NO_ACTIVE_STREAM",
                "snapshot_max_id": 0,
                "next_cursor_id": after_id,
                "velocity_buckets_cpm": [],
                "items": [],
            }

        rows_query = f"""
            SELECT id, channel_key, stream_id, author, message, epoch_time
            FROM chat_telemetry
            WHERE channel_key IN ({placeholders})
              AND id > ?
              AND id <= ?
              AND epoch_time >= ?
            ORDER BY id ASC
            LIMIT ?;
        """
        rows = conn.execute(rows_query, candidates + [after_id, max_id, window_floor, limit]).fetchall()

        bucket_query = f"""
            SELECT
                CAST(epoch_time / 60 AS INTEGER) * 60 AS minute_epoch,
                COUNT(*) AS cpm
            FROM chat_telemetry
            WHERE channel_key IN ({placeholders})
              AND id <= ?
              AND epoch_time >= ?
            GROUP BY minute_epoch
            ORDER BY minute_epoch DESC
            LIMIT 30;
        """
        bucket_rows = conn.execute(bucket_query, candidates + [max_id, window_floor]).fetchall()

        items = [dict(r) for r in rows]
        next_cursor = int(items[-1]["id"]) if items else after_id

        return {
            "game_id": clean_id,
            "stream_status": "ACTIVE_OR_ARCHIVED_TAIL",
            "snapshot_max_id": max_id,
            "total_window_messages": int(ceiling_row["total_rows"]),
            "unique_window_authors": int(ceiling_row["unique_authors"]),
            "next_cursor_id": next_cursor,
            "velocity_buckets_cpm": [dict(b) for b in bucket_rows],
            "items": items,
        }
    finally:
        conn.close()
