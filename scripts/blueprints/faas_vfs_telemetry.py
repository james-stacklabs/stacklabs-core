#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs FaaS Telemetry, VFS Fast-Path, Subcultural Shibboleth Bursts & Discord Gateway Inspector Blueprint
Path: /home/james/stacklabs/scripts/blueprints/faas_vfs_telemetry.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Governing Standards: Invariant 15, 24, 26 (Gandalf UI), 32 (Law of "I"), 35 (.venv), 38 (Telemetry Isolation), 50 (Drop-In Code), Argon Laws 1-9
"""

import collections
import json
import logging
import math
import os
import re
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Query
from scripts.cfb_slate_omni_resolver import get_wal_connection, sync_lexicon_to_sqlite
try:
    from scripts.nfl_slate_omni_resolver import sync_nfl_lexicon_to_sqlite
except ImportError:
    sync_nfl_lexicon_to_sqlite = None
from scripts.core.shm_counterparty_bus import (
    compute_sliding_10s_velocity,
    match_counterparty_echo,
    read_counterparty_shm,
)
from scripts.discord_stream_tailer import ensure_wiretap_discord_schemas

logger = logging.getLogger("faas_vfs_telemetry")

router = APIRouter(
    prefix="/api/vfs_telemetry",
    tags=["VFS Telemetry & Lexicon Inspector"],
)
faas_lexicon_router = APIRouter(
    prefix="/api/faas/lexicon",
    tags=["FaaS Lexicon Bursts, Drilldown & Discord Gateway"],
)

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = Path(
    os.getenv(
        "STACKLABS_WIRETAP_DB",
        str(REPO_ROOT / "data" / "morning_wiretap.db"),
    )
)
DISCORD_CONFIG_PATH = REPO_ROOT / "config" / "discord_channel_bindings.json"
VFS_DIR = Path("/dev/shm/vfs/telemetry")
SYN_DIR = Path("/dev/shm/vfs/synthetic")
DISCORD_HEARTBEAT_PATH = VFS_DIR / "discord_supervisor_heartbeat.json"
DISCORD_LATEST_BURST_PATH = VFS_DIR / "discord_burst_latest.json"

VFS_DIR.mkdir(parents=True, exist_ok=True)
SYN_DIR.mkdir(parents=True, exist_ok=True)
EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")

_TICKER_CACHE: List[Dict[str, Any]] = []
_LAST_TICKER_MTIME: float = 0.0
_LEXICON_SEEDED: bool = False

TICKER_FILE_CANDIDATES = [
    Path("/dev/shm/vfs/telemetry/mcafee_ticker_feed.jsonl"),
    Path("/home/james/stacklabs_inbox/today/mcafee_ticker_feed.jsonl"),
]


def atomic_write_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=str(target.parent), delete=False, encoding="utf-8"
    ) as tf:
        tf.write(content)
        tmp_name = tf.name
    os.replace(tmp_name, str(target))


def read_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def ensure_lexicon_seeded() -> None:
    global _LEXICON_SEEDED
    if _LEXICON_SEEDED and DB_PATH.exists():
        return
    try:
        con = get_wal_connection(DB_PATH)
        try:
            sync_lexicon_to_sqlite(con)
            if sync_nfl_lexicon_to_sqlite:
                try:
                    sync_nfl_lexicon_to_sqlite(con)
                except Exception:
                    pass
            ensure_wiretap_discord_schemas(con)
            _LEXICON_SEEDED = True
        finally:
            con.close()
    except sqlite3.Error as exc:
        print(f"[VFS Telemetry] Lexicon/Discord schema seed warning: {exc}")


def resolve_ticker_file() -> Path:
    for c in TICKER_FILE_CANDIDATES:
        if c.exists():
            return c
    return TICKER_FILE_CANDIDATES[1]


def classify_message_sentiment(msg: str) -> Tuple[str, str]:
    low = msg.lower()
    if any(
        k in low
        for k in [
            "fire",
            "trash",
            "fraud",
            "panic",
            "meltdown",
            "horrible",
            "bench",
            "choke",
            "cooked",
            "awful",
            "sell",
        ]
    ):
        return "MELTDOWN", "MLTD"
    if any(
        k in low
        for k in [
            "why",
            "bro",
            "wtf",
            "hate",
            "scared",
            "worried",
            "ump",
            "blind",
            "bad",
            "weak",
            "ugh",
            "damn",
        ]
    ):
        return "HEATED", "HEAT"
    if any(
        k in low
        for k in [
            "let's go",
            "lets go",
            "lfg",
            "huge",
            "clutch",
            "boom",
            "nasty",
            "filthy",
            "!!",
            "go brewers",
            "go dodgers",
        ]
    ):
        return "HYPED", "HYPD"
    return "NEUTRAL", "LIVE"


def _resolve_teams_from_slate(game_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolves away_team and home_team codes from the active VFS slate JSON or game_id slug."""
    # 1. Parse slug if already in AAA_BBB format
    clean = game_id.replace("cfb_", "").replace("nfl_", "").replace("mlb_", "")
    if "_" in clean and not clean.replace("_", "").isdigit():
        parts = clean.split("_")
        return parts[0].upper()[:6], parts[1].upper()[:6]

    # 2. Look up in active VFS unified slate
    try:
        vfs_path = Path("/dev/shm/vfs/schedule/unified_slate.json")
        if vfs_path.exists():
            games = json.loads(vfs_path.read_text(encoding="utf-8"))
            for g in games:
                if str(g.get("id")) == str(game_id) or str(g.get("id")).endswith(str(clean)):
                    away = g.get("away_team", {}).get("code") or g.get("awayTeam")
                    home = g.get("home_team", {}).get("code") or g.get("homeTeam")
                    if away and home:
                        return str(away).upper()[:6], str(home).upper()[:6]
    except Exception:
        pass
    return None, None


@router.api_route("/chat_tail", methods=["GET", "HEAD"])
def get_vfs_chat_tail(
    limit: int = 40, game_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Strict Entity-Scoped Telemetry Isolation (WO0011210 Lock 2 & Argon Law 5)
    with Dynamic Team-Aware Stream Aliasing (WO0011227):
    Queries morning_wiretap.db strictly for the requested game_id, resolved team codes, or channel_key.
    Returns [] when a specific game has no active stream (zero global fallback bleed).
    """
    if not DB_PATH.exists():
        return []
    if not game_id or game_id in ("ALL", "stream_chat"):
        return []
    try:
        con = get_wal_connection(DB_PATH)
        try:
            cur = con.cursor()
            raw_id = game_id.split("_", 1)[1] if "_" in game_id else game_id

            # 1. Direct query
            rows = cur.execute(
                "SELECT stream_id, away_team, home_team FROM watch_party_streams WHERE (game_pk=? OR stream_id=? OR game_pk=?) AND is_live=1",
                (game_id, game_id, raw_id),
            ).fetchall()
            stream_ids = [r["stream_id"] for r in rows if r["stream_id"]]

            # 2. Team-aware dynamic resolution
            away_code, home_code = _resolve_teams_from_slate(game_id)
            if away_code and home_code:
                team_rows = cur.execute(
                    """SELECT stream_id FROM watch_party_streams 
                       WHERE ((away_team=? AND home_team=?) OR (away_team=? AND home_team=?) 
                              OR game_pk LIKE ? OR game_pk LIKE ?) 
                       AND is_live=1""",
                    (
                        away_code,
                        home_code,
                        home_code,
                        away_code,
                        f"%{away_code}%{home_code}%",
                        f"%{home_code}%{away_code}%",
                    ),
                ).fetchall()
                for tr in team_rows:
                    if tr["stream_id"] and tr["stream_id"] not in stream_ids:
                        stream_ids.append(tr["stream_id"])

            max_row = cur.execute(
                "SELECT MAX(id) AS max_id FROM chat_telemetry"
            ).fetchone()
            id_floor = max(
                0, (int(max_row["max_id"] or 0) if max_row else 0) - 5000
            )

            channel_likes = []
            if away_code and home_code:
                channel_likes = [
                    f"%{away_code}%{home_code}%",
                    f"%{home_code}%{away_code}%",
                ]

            if stream_ids:
                ph = ",".join("?" for _ in stream_ids)
                if channel_likes:
                    query = f"SELECT id, timestamp_str, author, message, channel_key FROM chat_telemetry WHERE id > ? AND (stream_id IN ({ph}) OR channel_key = ? OR channel_key LIKE ? OR channel_key LIKE ?) ORDER BY id DESC LIMIT ?"
                    params = (
                        id_floor,
                        *stream_ids,
                        game_id,
                        channel_likes[0],
                        channel_likes[1],
                        limit * 2,
                    )
                else:
                    query = f"SELECT id, timestamp_str, author, message, channel_key FROM chat_telemetry WHERE id > ? AND (stream_id IN ({ph}) OR channel_key = ?) ORDER BY id DESC LIMIT ?"
                    params = (id_floor, *stream_ids, game_id, limit * 2)
            else:
                if channel_likes:
                    query = "SELECT id, timestamp_str, author, message, channel_key FROM chat_telemetry WHERE id > ? AND (channel_key = ? OR channel_key LIKE ? OR channel_key LIKE ?) ORDER BY id DESC LIMIT ?"
                    params = (
                        id_floor,
                        game_id,
                        channel_likes[0],
                        channel_likes[1],
                        limit * 2,
                    )
                else:
                    query = "SELECT id, timestamp_str, author, message, channel_key FROM chat_telemetry WHERE id > ? AND channel_key = ? ORDER BY id DESC LIMIT ?"
                    params = (id_floor, game_id, limit * 2)

            chat_rows = cur.execute(query, params).fetchall()
            if not chat_rows:
                return []
            items: List[Dict[str, Any]] = []
            seen: set[Tuple[str, str]] = set()
            for r in reversed(chat_rows):
                a = str(r["author"] or "Anonymous")
                m = str(r["message"] or "")
                k = (a.lower().strip(), m.lower().strip())
                if k in seen:
                    continue
                seen.add(k)
                sentiment, bytecode = classify_message_sentiment(m)
                items.append(
                    {
                        "id": f"wire-{r['id']}",
                        "db_id": int(r["id"]),
                        "timestamp": r["timestamp_str"] or "Live",
                        "author": a if a.startswith("@") else f"@{a}",
                        "message": m,
                        "sentiment": sentiment,
                        "bytecode": bytecode,
                        "provenance": {
                            "badge": r["channel_key"] or game_id,
                            "sicko_tier": "AUTHENTIC_BLEACHER",
                        },
                    }
                )
            return items[-limit:]
        finally:
            con.close()
    except sqlite3.Error as exc:
        print(f"[VFS Telemetry] Scoped chat lookup error for {game_id}: {exc}")
        return []


@router.api_route("/discord_bursts", methods=["GET", "HEAD"])
@router.api_route("/lexicon/discord_bursts", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/discord_bursts", methods=["GET", "HEAD"])
def get_discord_burst_alerts(
    channel_key: Optional[str] = Query(default=None),
    min_z_score: float = Query(default=4.5, ge=0.0, le=50.0),
    limit: int = Query(default=50, ge=1, le=250),
) -> Dict[str, Any]:
    """
    Exposes the real-time discord_burst_alerts table from data/morning_wiretap.db
    via indexed lookup (idx_discord_burst_channel_epoch), enriched with decoded
    subcultural ground truth from cfb_subcultural_lexicon.
    Enforces strict entity-scoped isolation when channel_key is specified (Argon Law 5).
    """
    ensure_lexicon_seeded()
    heartbeat = read_json_safe(DISCORD_HEARTBEAT_PATH) or {"state": "STANDBY"}
    latest_vfs_burst = read_json_safe(DISCORD_LATEST_BURST_PATH)

    if not DB_PATH.exists():
        return {
            "status": "NO_DATABASE",
            "channel_scope": channel_key or "ALL",
            "total_alerts": 0,
            "supervisor": heartbeat,
            "latest_burst": latest_vfs_burst,
            "alerts": [],
        }

    con = get_wal_connection(DB_PATH)
    try:
        cur = con.cursor()
        lex_map: Dict[str, Dict[str, Any]] = {}
        lex_table = "v_subcultural_lexicon" if cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name='v_subcultural_lexicon'").fetchone() else "cfb_subcultural_lexicon"
        for lrow in cur.execute(f"SELECT * FROM {lex_table}").fetchall():
            lex_map[str(lrow["shibboleth_id"])] = {
                "program_name": str(lrow["program_name"]),
                "primary_board": str(lrow["primary_board"]),
                "board_url": str(lrow["board_url"]),
                "static_nlp_false_positive": str(lrow["static_nlp_false_positive"]),
                "subcultural_ground_truth": str(lrow["subcultural_ground_truth"]),
                "barf_ammunition_angle": str(lrow["barf_ammunition_angle"]),
            }

        if channel_key and channel_key not in ("ALL", ""):
            rows = cur.execute(
                """
                SELECT
                    alert_id, channel_key, stream_id, channel_id,
                    shibboleth_id, team_abbrev, ngram_or_token,
                    hit_count, window_messages, window_seconds,
                    velocity_mps, z_score, z_score_threshold,
                    peak_author, peak_quote, timestamp_str,
                    epoch_time, content_sha256
                FROM discord_burst_alerts
                WHERE channel_key = ? AND z_score >= ?
                ORDER BY epoch_time DESC
                LIMIT ?
                """,
                (channel_key, float(min_z_score), int(limit)),
            ).fetchall()
        else:
            rows = cur.execute(
                """
                SELECT
                    alert_id, channel_key, stream_id, channel_id,
                    shibboleth_id, team_abbrev, ngram_or_token,
                    hit_count, window_messages, window_seconds,
                    velocity_mps, z_score, z_score_threshold,
                    peak_author, peak_quote, timestamp_str,
                    epoch_time, content_sha256
                FROM discord_burst_alerts
                WHERE z_score >= ?
                ORDER BY epoch_time DESC
                LIMIT ?
                """,
                (float(min_z_score), int(limit)),
            ).fetchall()

        alerts: List[Dict[str, Any]] = []
        for r in rows:
            shib_id = str(r["shibboleth_id"])
            meta = lex_map.get(
                shib_id,
                {
                    "program_name": f"{r['team_abbrev']} Emergent N-Gram Spike",
                    "primary_board": "Discord Live Game Channel",
                    "board_url": f"https://discord.com/channels/@me/{r['channel_id']}",
                    "static_nlp_false_positive": "Uncatalogued high-velocity chat token cluster",
                    "subcultural_ground_truth": f"Real-time Discord n-gram burst ('{r['ngram_or_token']}') crossing +{float(r['z_score']):.2f}σ in {r['channel_key']}.",
                    "barf_ammunition_angle": f"Live Discord bleachers in {r['channel_key']} are spamming '{r['ngram_or_token']}' at {float(r['velocity_mps']):.2f} msgs/sec.",
                },
            )
            alerts.append(
                {
                    "alert_id": str(r["alert_id"]),
                    "channel_key": str(r["channel_key"]),
                    "stream_id": str(r["stream_id"]),
                    "channel_id": str(r["channel_id"]),
                    "shibboleth_id": shib_id,
                    "team_abbrev": str(r["team_abbrev"]),
                    "program_name": meta["program_name"],
                    "primary_board": meta["primary_board"],
                    "board_url": meta["board_url"],
                    "ngram_or_token": str(r["ngram_or_token"]),
                    "hit_count": int(r["hit_count"]),
                    "window_messages": int(r["window_messages"]),
                    "window_seconds": float(r["window_seconds"]),
                    "velocity_mps": float(r["velocity_mps"]),
                    "z_score": float(r["z_score"]),
                    "z_score_threshold": float(r["z_score_threshold"]),
                    "peak_author": str(r["peak_author"]),
                    "peak_quote": str(r["peak_quote"]),
                    "timestamp_str": str(r["timestamp_str"]),
                    "epoch_time": float(r["epoch_time"]),
                    "content_sha256": str(r["content_sha256"]),
                    "static_nlp_false_positive": meta["static_nlp_false_positive"],
                    "subcultural_ground_truth": meta["subcultural_ground_truth"],
                    "barf_ammunition_angle": meta["barf_ammunition_angle"],
                }
            )

        scoped_latest = alerts[0] if alerts else (
            latest_vfs_burst
            if (
                latest_vfs_burst
                and (
                    not channel_key
                    or channel_key in ("ALL", "")
                    or latest_vfs_burst.get("channel_key") == channel_key
                )
            )
            else None
        )

        return {
            "status": "ONLINE",
            "channel_scope": channel_key or "ALL",
            "total_alerts": len(alerts),
            "supervisor": heartbeat,
            "latest_burst": scoped_latest,
            "alerts": alerts,
        }
    finally:
        con.close()


@router.api_route("/discord_status", methods=["GET", "HEAD"])
@router.api_route("/lexicon/discord_status", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/discord_status", methods=["GET", "HEAD"])
def get_discord_supervisor_status() -> Dict[str, Any]:
    """
    Returns unified health, TTL bounds, active channel-to-game bindings, and SQLite WAL
    ingestion counts for stacklabs-discord-tailer.service.
    """
    ensure_lexicon_seeded()
    heartbeat = read_json_safe(DISCORD_HEARTBEAT_PATH) or {
        "service": "stacklabs-discord-tailer.service",
        "state": "NO_HEARTBEAT_FILE",
        "auth_mode": "UNKNOWN",
        "ttl_seconds": 14400,
        "active_channel_count": 0,
        "active_channels": [],
    }
    config_data = read_json_safe(DISCORD_CONFIG_PATH) or {"bindings": []}
    latest_burst = read_json_safe(DISCORD_LATEST_BURST_PATH)

    discord_chat_rows = 0
    discord_burst_rows = 0
    live_streams: List[Dict[str, Any]] = []

    if DB_PATH.exists():
        con = get_wal_connection(DB_PATH)
        try:
            cur = con.cursor()
            c_row = cur.execute(
                "SELECT COUNT(*) AS cnt FROM chat_telemetry WHERE discord_channel_id IS NOT NULL AND discord_channel_id != ''"
            ).fetchone()
            discord_chat_rows = int(c_row["cnt"] or 0) if c_row else 0

            b_row = cur.execute(
                "SELECT COUNT(*) AS cnt FROM discord_burst_alerts"
            ).fetchone()
            discord_burst_rows = int(b_row["cnt"] or 0) if b_row else 0

            s_rows = cur.execute(
                """
                SELECT sport, game_pk, home_team, away_team, stream_id, stream_title, stream_url, is_live, resolved_at
                FROM watch_party_streams
                WHERE source = 'discord_gateway_v10'
                ORDER BY is_live DESC, game_pk ASC
                """
            ).fetchall()
            for sr in s_rows:
                live_streams.append(
                    {
                        "sport": str(sr["sport"]),
                        "game_id": str(sr["game_pk"]),
                        "home_team": str(sr["home_team"]),
                        "away_team": str(sr["away_team"]),
                        "stream_id": str(sr["stream_id"]),
                        "stream_title": str(sr["stream_title"]),
                        "stream_url": str(sr["stream_url"]),
                        "is_live": bool(sr["is_live"]),
                        "resolved_at": str(sr["resolved_at"]),
                    }
                )
        finally:
            con.close()

    return {
        "status": "ONLINE",
        "service_unit": "stacklabs-discord-tailer.service",
        "heartbeat": heartbeat,
        "configured_bindings_count": len(config_data.get("bindings", [])),
        "configured_bindings": config_data.get("bindings", []),
        "watch_party_discord_streams": live_streams,
        "metrics": {
            "discord_chat_telemetry_rows": discord_chat_rows,
            "discord_burst_alerts_rows": discord_burst_rows,
            "window_seconds": float(config_data.get("window_seconds", 60.0)),
            "sigma_threshold": float(config_data.get("sigma_threshold", 4.5)),
            "ttl_seconds": int(config_data.get("ttl_seconds", 14400)),
        },
        "latest_burst": latest_burst,
    }


@router.api_route("/lexicon/bursts", methods=["GET", "HEAD"])
@router.api_route("/lexicon/anomalies", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/bursts", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/anomalies", methods=["GET", "HEAD"])
@router.api_route("/lexicon/all", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/all", methods=["GET", "HEAD"])
def get_lexicon_bursts(
    channel_key: Optional[str] = Query(default=None),
    window_messages: int = Query(default=2500, ge=100, le=10000),
) -> Dict[str, Any]:
    """
    Evaluates the bounded sliding chat_telemetry window (WHERE id > max_id - window_messages)
    against the 16 canonical CFB subcultural shibboleths in cfb_subcultural_lexicon,
    and attaches real-time Discord Gateway burst alert telemetry.
    """
    ensure_lexicon_seeded()
    heartbeat = read_json_safe(DISCORD_HEARTBEAT_PATH) or {"state": "STANDBY"}
    latest_vfs_burst = read_json_safe(DISCORD_LATEST_BURST_PATH)
    if not DB_PATH.exists():
        return {
            "status": "NO_DATABASE",
            "evaluated_messages": 0,
            "active_burst_count": 0,
            "discord_burst_alerts_count": 0,
            "latest_discord_burst": latest_vfs_burst,
            "discord_supervisor": heartbeat,
            "discord_supervisor_state": heartbeat.get("state", "STANDBY"),
            "anomalies": [],
            "lexicon": [],
        }
    con = get_wal_connection(DB_PATH)
    try:
        cur = con.cursor()
        lex_rows = cur.execute(
            f"SELECT * FROM {'v_subcultural_lexicon' if cur.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\',\'view\') AND name=\'v_subcultural_lexicon\'').fetchone() else 'cfb_subcultural_lexicon'} ORDER BY team_abbrev ASC, shibboleth_id ASC"
        ).fetchall()
        has_chat = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_telemetry'"
        ).fetchone()
        chat_rows: List[sqlite3.Row] = []
        max_id = 0
        if has_chat:
            max_row = cur.execute(
                "SELECT MAX(id) AS max_id FROM chat_telemetry"
            ).fetchone()
            max_id = int(max_row["max_id"] or 0) if max_row else 0
            floor_id = max(0, max_id - int(window_messages))
            if channel_key and channel_key not in ("ALL", ""):
                chat_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str FROM chat_telemetry WHERE id > ? AND channel_key = ? ORDER BY id ASC",
                    (floor_id, channel_key),
                ).fetchall()
            else:
                chat_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str FROM chat_telemetry WHERE id > ? ORDER BY id ASC",
                    (floor_id,),
                ).fetchall()

        # Fetch recent Discord burst alerts per shibboleth_id (scoped if channel_key is provided)
        discord_burst_by_shib: Dict[str, Dict[str, Any]] = {}
        discord_burst_total = 0
        if channel_key and channel_key not in ("ALL", ""):
            d_rows = cur.execute(
                "SELECT shibboleth_id, z_score, hit_count, velocity_mps, peak_author, peak_quote, timestamp_str, channel_key FROM discord_burst_alerts WHERE channel_key = ? ORDER BY epoch_time DESC LIMIT 100",
                (channel_key,),
            ).fetchall()
        else:
            d_rows = cur.execute(
                "SELECT shibboleth_id, z_score, hit_count, velocity_mps, peak_author, peak_quote, timestamp_str, channel_key FROM discord_burst_alerts ORDER BY epoch_time DESC LIMIT 100"
            ).fetchall()
        discord_burst_total = len(d_rows)
        for dr in d_rows:
            sid = str(dr["shibboleth_id"])
            if sid not in discord_burst_by_shib:
                discord_burst_by_shib[sid] = {
                    "z_score": float(dr["z_score"]),
                    "hit_count": int(dr["hit_count"]),
                    "velocity_mps": float(dr["velocity_mps"]),
                    "peak_author": str(dr["peak_author"]),
                    "peak_quote": str(dr["peak_quote"]),
                    "timestamp_str": str(dr["timestamp_str"]),
                    "channel_key": str(dr["channel_key"]),
                }

        norm_msgs = [
            (
                int(r["id"]),
                str(r["channel_key"] or "radio_mcafee"),
                str(r["author"] or "Chatter"),
                str(r["message"] or ""),
                str(r["timestamp_str"] or "Live"),
                EMOJI_SHORTCODE_RE.sub(" ", str(r["message"] or "")).lower(),
            )
            for r in chat_rows
        ]
        total_msgs = len(norm_msgs)
        expected_mean = max(total_msgs * 0.005, 0.5)
        std_dev = math.sqrt(max(total_msgs * 0.005 * 0.995, 0.25))
        results, active_burst_count = [], 0
        for lrow in lex_rows:
            shib_id = str(lrow["shibboleth_id"])
            tokens = json.loads(lrow["trigger_tokens_json"])
            hit_count, matched_tokens = 0, set()
            peak_id, peak_ch, peak_author, peak_quote, peak_ts = (
                None,
                channel_key or "radio_mcafee",
                "",
                "",
                "Standby",
            )
            for mid, ch, auth, raw_m, ts_s, clean_low in norm_msgs:
                hits = [tok for tok in tokens if tok in clean_low]
                if hits:
                    hit_count += 1
                    matched_tokens.update(hits)
                    peak_id, peak_ch, peak_author, peak_quote, peak_ts = (
                        mid,
                        ch,
                        auth,
                        raw_m,
                        ts_s,
                    )
            z_score = (
                round((hit_count - expected_mean) / std_dev, 2)
                if hit_count > 0
                else 0.0
            )
            threshold = float(lrow["z_score_threshold"])
            d_burst = discord_burst_by_shib.get(shib_id)
            if d_burst and d_burst["z_score"] > z_score:
                z_score = d_burst["z_score"]
                hit_count = max(hit_count, d_burst["hit_count"])
                if not peak_quote:
                    peak_author = d_burst["peak_author"]
                    peak_quote = d_burst["peak_quote"]
                    peak_ts = d_burst["timestamp_str"]
                    peak_ch = d_burst["channel_key"]

            is_burst = bool(hit_count > 0 and z_score >= threshold)
            if is_burst:
                active_burst_count += 1
            results.append(
                {
                    "shibboleth_id": shib_id,
                    "team_abbrev": lrow["team_abbrev"],
                    "program_name": lrow["program_name"],
                    "primary_board": lrow["primary_board"],
                    "board_url": lrow["board_url"],
                    "trigger_tokens": tokens,
                    "matched_tokens": sorted(matched_tokens),
                    "hit_count": hit_count,
                    "z_score": z_score,
                    "z_score_threshold": threshold,
                    "is_active_burst": is_burst,
                    "peak_message_id": peak_id,
                    "peak_channel_key": peak_ch,
                    "peak_author": peak_author,
                    "peak_quote": peak_quote,
                    "peak_timestamp": peak_ts,
                    "discord_burst": d_burst,
                    "static_nlp_false_positive": lrow[
                        "static_nlp_false_positive"
                    ],
                    "subcultural_ground_truth": lrow[
                        "subcultural_ground_truth"
                    ],
                    "barf_ammunition_angle": lrow["barf_ammunition_angle"],
                }
            )
        # Check /dev/shm counterparty echoes
        shm_state = read_counterparty_shm()
        for anom in results:
            c_tokens = anom.get("trigger_tokens", []) or anom.get("matched_tokens", [])
            echo = match_counterparty_echo(c_tokens, shm_state=shm_state)
            if echo:
                anom["counterparty_echo"] = echo["badge"]
                anom["counterparty_echo_meta"] = echo

        results.sort(
            key=lambda x: (
                1 if x["is_active_burst"] else 0,
                x["hit_count"],
                x["z_score"],
                x["team_abbrev"],
            ),
            reverse=True,
        )
        scoped_latest_discord = (
            next(iter(discord_burst_by_shib.values()))
            if discord_burst_by_shib
            else (
                latest_vfs_burst
                if (
                    latest_vfs_burst
                    and (
                        not channel_key
                        or channel_key in ("ALL", "")
                        or latest_vfs_burst.get("channel_key") == channel_key
                    )
                )
                else None
            )
        )
        return {
            "status": "ONLINE",
            "snapshot_max_id": max_id,
            "evaluated_messages": total_msgs,
            "active_burst_count": active_burst_count,
            "discord_burst_alerts_count": discord_burst_total,
            "latest_discord_burst": scoped_latest_discord,
            "discord_supervisor": heartbeat,
            "discord_supervisor_state": heartbeat.get("state", "STANDBY"),
            "anomalies": results,
            "lexicon": results,
        }
    finally:
        con.close()


@router.api_route("/lexicon/drilldown", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/drilldown", methods=["GET", "HEAD"])
@router.api_route("/lexicon/detail", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/detail", methods=["GET", "HEAD"])
def get_lexicon_drilldown(
    shibboleth_id: str = Query(...),
    channel_key: Optional[str] = Query(default=None),
    center_id: Optional[int] = Query(default=None),
    context_radius: int = Query(default=40, ge=10, le=200),
) -> Dict[str, Any]:
    ensure_lexicon_seeded()
    con = get_wal_connection(DB_PATH)
    try:
        cur = con.cursor()
        lrow = cur.execute(
            f"SELECT * FROM {'v_subcultural_lexicon' if cur.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\',\'view\') AND name=\'v_subcultural_lexicon\'').fetchone() else 'cfb_subcultural_lexicon'} WHERE shibboleth_id = ?",
            (shibboleth_id,),
        ).fetchone()
        if not lrow:
            return {
                "status": "NOT_FOUND",
                "shibboleth_id": shibboleth_id,
                "shibboleth": None,
                "messages": [],
            }
        tokens = json.loads(lrow["trigger_tokens_json"])
        meta = {
            "shibboleth_id": lrow["shibboleth_id"],
            "team_abbrev": lrow["team_abbrev"],
            "program_name": lrow["program_name"],
            "primary_board": lrow["primary_board"],
            "board_url": lrow["board_url"],
            "trigger_tokens": tokens,
            "static_nlp_false_positive": lrow["static_nlp_false_positive"],
            "subcultural_ground_truth": lrow["subcultural_ground_truth"],
            "barf_ammunition_angle": lrow["barf_ammunition_angle"],
            "z_score_threshold": float(lrow["z_score_threshold"]),
        }
        if not cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_telemetry'"
        ).fetchone():
            return {
                "status": "NO_CHAT_TELEMETRY",
                "shibboleth_id": shibboleth_id,
                "shibboleth": meta,
                "anchor_message_id": None,
                "trigger_hit_count": 0,
                "total_window_messages": 0,
                "messages": [],
            }
        max_row = cur.execute(
            "SELECT MAX(id) AS max_id FROM chat_telemetry"
        ).fetchone()
        max_id = int(max_row["max_id"] or 0) if max_row else 0
        scan_floor = max(0, max_id - 5000)
        anchor_id = center_id
        if anchor_id is None:
            q_sql = (
                "SELECT id, message FROM chat_telemetry WHERE id > ? AND channel_key = ? ORDER BY id DESC LIMIT 2500"
                if (channel_key and channel_key not in ("ALL", ""))
                else "SELECT id, message FROM chat_telemetry WHERE id > ? ORDER BY id DESC LIMIT 2500"
            )
            q_args: Tuple[Any, ...] = (
                (scan_floor, channel_key)
                if (channel_key and channel_key not in ("ALL", ""))
                else (scan_floor,)
            )
            for r in cur.execute(q_sql, q_args).fetchall():
                low_m = EMOJI_SHORTCODE_RE.sub(
                    " ", str(r["message"] or "")
                ).lower()
                if any(tok in low_m for tok in tokens):
                    anchor_id = int(r["id"])
                    break
        if anchor_id is not None:
            low_id, high_id = (
                max(0, anchor_id - int(context_radius)),
                anchor_id + int(context_radius),
            )
            if channel_key and channel_key not in ("ALL", ""):
                w_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str, epoch_time FROM chat_telemetry WHERE id BETWEEN ? AND ? AND channel_key = ? ORDER BY id ASC",
                    (low_id, high_id, channel_key),
                ).fetchall()
            else:
                w_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str, epoch_time FROM chat_telemetry WHERE id BETWEEN ? AND ? ORDER BY id ASC",
                    (low_id, high_id),
                ).fetchall()
        else:
            low_id = max(0, max_id - int(context_radius * 2))
            if channel_key and channel_key not in ("ALL", ""):
                w_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str, epoch_time FROM chat_telemetry WHERE id > ? AND channel_key = ? ORDER BY id ASC LIMIT ?",
                    (low_id, channel_key, context_radius * 2),
                ).fetchall()
            else:
                w_rows = cur.execute(
                    "SELECT id, channel_key, author, message, timestamp_str, epoch_time FROM chat_telemetry WHERE id > ? ORDER BY id ASC LIMIT ?",
                    (low_id, context_radius * 2),
                ).fetchall()
        msgs, trigger_hits = [], 0
        for row in w_rows:
            raw_m = str(row["message"] or "")
            low_m = EMOJI_SHORTCODE_RE.sub(" ", raw_m).lower()
            matched = [tok for tok in tokens if tok in low_m]
            is_hit = len(matched) > 0
            if is_hit:
                trigger_hits += 1
            sentiment, bytecode = classify_message_sentiment(raw_m)
            auth = str(row["author"] or "Chatter")
            msgs.append(
                {
                    "id": int(row["id"]),
                    "channel_key": str(row["channel_key"] or "radio_mcafee"),
                    "author": auth if auth.startswith("@") else f"@{auth}",
                    "message": raw_m,
                    "timestamp": str(row["timestamp_str"] or "Live"),
                    "epoch_time": float(row["epoch_time"] or 0.0),
                    "is_trigger_hit": is_hit,
                    "matched_tokens": matched,
                    "sentiment": sentiment,
                    "bytecode": bytecode,
                }
            )
        return {
            "status": "ONLINE",
            "shibboleth_id": shibboleth_id,
            "shibboleth": meta,
            "anchor_message_id": anchor_id,
            "trigger_hit_count": trigger_hits,
            "total_window_messages": len(msgs),
            "messages": msgs,
        }
    finally:
        con.close()


@router.api_route("/ticker_feed", methods=["GET", "HEAD"])
def get_vfs_ticker_feed(limit: int = 20) -> List[Dict[str, Any]]:
    global _TICKER_CACHE, _LAST_TICKER_MTIME
    target = resolve_ticker_file()
    if not target.exists():
        return []
    try:
        stat = target.stat()
        if stat.st_mtime != _LAST_TICKER_MTIME:
            _LAST_TICKER_MTIME = stat.st_mtime
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            items = []
            for ln in lines[-max(100, limit) :]:
                try:
                    items.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
            _TICKER_CACHE = items[::-1]
    except OSError:
        pass
    return _TICKER_CACHE[:limit]


@router.api_route("/metrics", methods=["GET", "HEAD"])
def get_vfs_metrics() -> Dict[str, Any]:
    hb = read_json_safe(DISCORD_HEARTBEAT_PATH) or {"state": "STANDBY"}
    return {
        "status": "ONLINE",
        "cache_plane": "SQLite WAL + RAM (/dev/shm)",
        "cached_ticker_count": len(_TICKER_CACHE),
        "discord_supervisor_state": hb.get("state", "STANDBY"),
        "latency_target": "<100us",
    }


@router.api_route("/pipeline_heartbeat", methods=["GET", "HEAD"])
def get_pipeline_heartbeat() -> Dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S EDT")
    hb = read_json_safe(DISCORD_HEARTBEAT_PATH) or {"state": "STANDBY", "active_channel_count": 0}
    discord_state = str(hb.get("state") or "STANDBY")
    discord_channels = int(hb.get("active_channel_count") or 0)
    discord_desc = f"Supervised 60s ring buffer across {discord_channels} mapped channels (TTL 4h)"
    stages = [
        {
            "id": "01",
            "name": "STATCAST & ESPN INGRESS",
            "status": "ACTIVE",
            "latency_ms": 12,
            "desc": "Ingesting live scoreboard & play-by-play feeds",
            "summary": "Ingesting live scoreboard & play-by-play feeds",
        },
        {
            "id": "02",
            "name": "CHAT & WIRETAP INGRESS",
            "status": "ACTIVE",
            "latency_ms": 8,
            "desc": "Indexing live bleacher message stream",
            "summary": "Indexing live bleacher message stream",
        },
        {
            "id": "03",
            "name": "CFB SHIBBOLETH LEXICON",
            "status": "VERIFIED",
            "latency_ms": 2,
            "desc": "16-program subcultural burst detector active",
            "summary": "16-program subcultural burst detector active",
        },
        {
            "id": "04",
            "name": "PAYLOAD SYNTHESIS",
            "status": "ACTIVE",
            "latency_ms": 15,
            "desc": "Compiling multi-sport VFS event state",
            "summary": "Compiling multi-sport VFS event state",
        },
        {
            "id": "05",
            "name": "DRIVE VAULT SYNC",
            "status": "ACTIVE",
            "latency_ms": 120,
            "desc": "Vault sync to stacklabs_edge:",
            "summary": "Vault sync to stacklabs_edge:",
        },
        {
            "id": "06",
            "name": "EDGE HUD DISTRIBUTION",
            "status": "ACTIVE",
            "latency_ms": 6,
            "desc": "Serving FaaS microfrontends",
            "summary": "Serving FaaS microfrontends",
        },
        {
            "id": "07",
            "name": "ARTEMIS CUDA WHISPER",
            "status": "STANDBY",
            "latency_ms": 2,
            "desc": "Acoustic silicon gating pinned to Artemis",
            "summary": "Acoustic silicon gating pinned to Artemis",
        },
        {
            "id": "08",
            "name": "DISCORD GATEWAY V10 INGRESS",
            "status": discord_state,
            "latency_ms": 4,
            "desc": discord_desc,
            "summary": discord_desc,
        },
    ]
    return {
        "status": "ONLINE",
        "cadence": "15M NOMINAL",
        "last_pulse": now,
        "current_time": now,
        "stages": stages,
    }


@router.api_route("/companion_state", methods=["GET", "HEAD"])
@router.api_route("/game_telemetry", methods=["GET", "HEAD"])
def get_vfs_companion_telemetry() -> Dict[str, Any]:
    return {
        "status": "GROUNDED_VAULT",
        "headline": "SATURDAY CFB SLATE & MLB POSTSEASON TELEMETRY",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S-04:00"),
        "vfs_metrics": {
            "cache_layer": "RAM (/dev/shm) + SQLite WAL",
            "latency": "<50us",
        },
    }


@router.api_route("/advocate_banter", methods=["GET", "HEAD"])
@router.api_route("/events/latest", methods=["GET", "HEAD"])
@router.api_route("/banter_feed", methods=["GET", "HEAD"])
def get_latest_advocate_banter() -> Dict[str, Any]:
    latest_file = Path("/dev/shm/faas_vfs/events/latest_event.json")
    if latest_file.exists():
        try:
            return json.loads(latest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"status": "STANDBY", "banter": []}


@router.api_route("/events", methods=["GET", "HEAD"])
def get_vfs_events_list(limit: int = 10) -> List[Dict[str, Any]]:
    return []


@router.api_route("/predict/state", methods=["GET", "HEAD"])
def get_predict_exchange_state() -> Dict[str, Any]:
    return {"status": "STANDBY", "positions": []}


@router.api_route("/vfs/guide", methods=["GET", "HEAD"])
@router.api_route("/guide", methods=["GET", "HEAD"])
def get_vfs_live_guide() -> Dict[str, Any]:
    return {"channels": []}


@router.api_route("/tripwires", methods=["GET", "HEAD"])
@router.api_route("/lore_tripwires", methods=["GET", "HEAD"])
def get_lore_tripwires() -> Dict[str, Any]:
    vfs_file = Path("/dev/shm/faas_vfs/telemetry/lore_tripwires.json")
    if vfs_file.exists():
        try:
            return json.loads(vfs_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    data_file = Path("/home/james/stacklabs/data/lore_tripwire_receipts.json")
    if data_file.exists():
        try:
            return json.loads(data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"status": "ONLINE", "hypocrisy_cards": [], "recent_hits": []}


@router.api_route("/capital_crater", methods=["GET", "HEAD"])
@router.api_route("/dodgers_capital", methods=["GET", "HEAD"])
def get_dodgers_capital_crater() -> Dict[str, Any]:
    vfs_file = Path("/dev/shm/faas_vfs/telemetry/dodgers_capital_crater.json")
    if vfs_file.exists():
        try:
            return json.loads(vfs_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    data_file = Path("/home/james/stacklabs/data/telemetry/dodgers_capital_crater.json")
    if data_file.exists():
        try:
            return json.loads(data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"status": "ONLINE"}


@router.api_route("/gameroom_overlay/{game_key}", methods=["GET", "HEAD"])
@router.api_route("/gameroom/{game_key}/overlay", methods=["GET", "HEAD"])
def get_gameroom_overlay(game_key: str) -> Dict[str, Any]:
    clean_key = game_key.upper().replace("-", "_")
    vfs_file = Path(f"/dev/shm/faas_vfs/gameroom/{clean_key}_special_overlay.json")
    if vfs_file.exists():
        try:
            return json.loads(vfs_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"status": "STANDBY", "game_key": clean_key}


@router.api_route("/lexicon/dialects", methods=["GET", "HEAD"])
def get_lexicon_dialects() -> Dict[str, Any]:
    reg_file = Path("/home/james/stacklabs/ground_truth/regional_lexicon_registry.json")
    if reg_file.exists():
        try:
            return json.loads(reg_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"status": "empty"}

@router.api_route("/barf_tweet_storm", methods=["GET", "HEAD"])
@router.api_route("/lexicon/barf_tweet_storm", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/barf_tweet_storm", methods=["GET", "HEAD"])
def get_barf_tweet_storm() -> Dict[str, Any]:
    """Returns the latest @BarfFanStack synthesized tweet storm receipt from VFS or SQLite."""
    vfs_file = Path("/dev/shm/vfs/telemetry/barf_latest_tweet_storm.json")
    if vfs_file.exists():
        try:
            return {
                "status": "ONLINE",
                "source": "VFS_FAST_PATH",
                "storm": json.loads(vfs_file.read_text(encoding="utf-8")),
            }
        except (OSError, json.JSONDecodeError):
            pass

    try:
        conn = get_wal_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT storm_id, source_alert_id, channel_key, shibboleth_id, team_abbrev,
                   z_score, velocity_mps, blood_pressure, tums_chewed, discord_blast,
                   tweets_json, content_sha256, dispatched_to_discord, created_at
            FROM barf_tweet_storms
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        row = cur.fetchone()
        if row:
            res = dict(row)
            try:
                res["tweets"] = json.loads(res.pop("tweets_json", "[]"))
            except json.JSONDecodeError:
                res["tweets"] = []
            return {"status": "ONLINE", "source": "SQLITE_PERSISTENCE", "storm": res}
    except Exception as exc:
        return {"status": "ERROR", "detail": str(exc), "storm": None}

    return {"status": "STANDBY", "detail": "No synthesized tweet storm found", "storm": None}


@router.api_route("/barf_dispatch_burst", methods=["POST", "HEAD"])
@router.api_route("/lexicon/barf_dispatch_burst", methods=["POST", "HEAD"])
@faas_lexicon_router.api_route("/barf_dispatch_burst", methods=["POST", "HEAD"])
def post_barf_dispatch_burst(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Triggers on-demand dynamic synthesis and optional Discord dispatch for a burst alert."""
    try:
        from scripts.barf_discord_burst_tweet_synthesizer import (
            seed_canonical_burst_if_empty,
            synthesize_barf_storm,
            ensure_barf_tables,
        )

        conn = get_wal_connection(DB_PATH)
        ensure_barf_tables(conn)
        req = payload or {}
        alert_id = req.get("alert_id")
        dispatch_discord = bool(req.get("dispatch", False))
        channel_id = req.get("channel_id")

        if alert_id:
            cur = conn.cursor()
            cur.execute("SELECT * FROM discord_burst_alerts WHERE alert_id = ? LIMIT 1;", (str(alert_id),))
            row = cur.fetchone()
            alert_row = dict(row) if row else seed_canonical_burst_if_empty(conn)
        else:
            alert_row = seed_canonical_burst_if_empty(conn)

        receipt = synthesize_barf_storm(
            alert_row=alert_row,
            conn=conn,
            dispatch_discord=dispatch_discord,
            target_channel_id=channel_id,
        )
        return {"status": "SUCCESS", "receipt": receipt.to_dict()}
    except Exception as exc:
        return {"status": "ERROR", "detail": str(exc)}


@router.api_route("/lexicon/timeline", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/timeline", methods=["GET", "HEAD"])
@router.api_route("/lexicon/timeline/shibboleth_bursts", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/timeline/shibboleth_bursts", methods=["GET", "HEAD"])
def get_lexicon_timeline(
    shibboleth_id: str = Query(default="DAL_THIS_IS_OUR_YEAR_VHS_GLORY_HOLE"),
    channel_key: Optional[str] = Query(default=None),
    window_minutes: int = Query(default=60, ge=5, le=360),
) -> Dict[str, Any]:
    """
    Computes deterministic 60-second epoch velocity buckets for the requested shibboleth
    across the active sliding window in morning_wiretap.db.
    """
    ensure_lexicon_seeded()
    if not DB_PATH.exists():
        return {
            "status": "NO_DATABASE",
            "shibboleth_id": shibboleth_id,
            "window_minutes": window_minutes,
            "channel_key": channel_key or "ALL",
            "total_evaluated_messages": 0,
            "total_hits": 0,
            "peak_velocity_mps": 0.0,
            "peak_bucket_epoch": None,
            "buckets": [],
        }
    con = get_wal_connection(DB_PATH)
    try:
        cur = con.cursor()
        shib_row = cur.execute(
            f"SELECT trigger_tokens_json FROM {'v_subcultural_lexicon' if cur.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\',\'view\') AND name=\'v_subcultural_lexicon\'').fetchone() else 'cfb_subcultural_lexicon'} WHERE shibboleth_id = ?",
            (shibboleth_id,),
        ).fetchone()
        tokens = json.loads(shib_row["trigger_tokens_json"]) if shib_row else []

        max_row = cur.execute("SELECT MAX(epoch_time) AS max_epoch FROM chat_telemetry").fetchone()
        max_epoch = int(max_row["max_epoch"] or 0) if max_row else int(time.time())
        if max_epoch <= 0:
            max_epoch = int(time.time())
        start_epoch = max_epoch - (window_minutes * 60)

        if channel_key and channel_key not in ("ALL", ""):
            rows = cur.execute(
                """SELECT id, (CAST(epoch_time / 60 AS INTEGER) * 60) AS bucket_epoch,
                          author, message, epoch_time, timestamp_str, channel_key
                   FROM chat_telemetry
                   WHERE epoch_time >= ? AND channel_key = ?
                   ORDER BY epoch_time ASC""",
                (start_epoch, channel_key),
            ).fetchall()
        else:
            rows = cur.execute(
                """SELECT id, (CAST(epoch_time / 60 AS INTEGER) * 60) AS bucket_epoch,
                          author, message, epoch_time, timestamp_str, channel_key
                   FROM chat_telemetry
                   WHERE epoch_time >= ?
                   ORDER BY epoch_time ASC""",
                (start_epoch,),
            ).fetchall()

        buckets_map: Dict[int, Dict[str, Any]] = {}
        total_hits = 0
        matched_epochs: List[float] = []

        for r in rows:
            b_epoch = int(r["bucket_epoch"])
            if b_epoch not in buckets_map:
                t_struct = time.localtime(b_epoch)
                t_label = time.strftime("%H:%M", t_struct)
                buckets_map[b_epoch] = {
                    "epoch_bucket": b_epoch,
                    "time_label": t_label,
                    "hit_count": 0,
                    "total_messages": 0,
                    "velocity_mps": 0.0,
                    "tumbling_velocity_mps": 0.0,
                    "sliding_10s_peak_mps": 0.0,
                    "matched_tokens": set(),
                    "matched_authors": [],
                }
            b = buckets_map[b_epoch]
            b["total_messages"] += 1
            clean_m = EMOJI_SHORTCODE_RE.sub(" ", str(r["message"] or "")).lower()
            matched = [tok for tok in tokens if tok in clean_m]
            if matched:
                b["hit_count"] += 1
                total_hits += 1
                matched_epochs.append(float(r["epoch_time"]))
                b["matched_tokens"].update(matched)
                if len(b["matched_authors"]) < 5:
                    b["matched_authors"].append(str(r["author"] or "Chatter"))

        # Compute 10-second rolling sliding velocity
        sliding_metrics = compute_sliding_10s_velocity(
            matched_epochs, window_start_epoch=start_epoch, window_end_epoch=max_epoch
        )
        minute_peaks = sliding_metrics.get("minute_peak_mps", {})

        bucket_list: List[Dict[str, Any]] = []
        peak_velocity = float(sliding_metrics.get("peak_velocity_mps", 0.0))
        peak_bucket_epoch = sliding_metrics.get("peak_center_epoch")

        for b_epoch in sorted(buckets_map.keys()):
            b = buckets_map[b_epoch]
            tumbling_mps = round(b["hit_count"] / 60.0, 3)
            b["tumbling_velocity_mps"] = tumbling_mps
            # True peak incorporates 10s sliding window across the minute
            b["sliding_10s_peak_mps"] = minute_peaks.get(b_epoch, tumbling_mps)
            b["velocity_mps"] = max(tumbling_mps, b["sliding_10s_peak_mps"])
            b["matched_tokens"] = sorted(list(b["matched_tokens"]))
            bucket_list.append(b)

        # Counterparty echo check
        shm_state = read_counterparty_shm()
        echo_badge = match_counterparty_echo(tokens, shm_state=shm_state)

        return {
            "status": "OK",
            "shibboleth_id": shibboleth_id,
            "window_minutes": window_minutes,
            "channel_key": channel_key or "ALL",
            "total_evaluated_messages": len(rows),
            "total_hits": total_hits,
            "peak_velocity_mps": peak_velocity,
            "peak_bucket_epoch": peak_bucket_epoch,
            "sliding_10s_ring": {
                "bin_size_seconds": 10,
                "hop_count": 6,
                "window_seconds": 60,
                "peak_velocity_mps": peak_velocity,
                "z_score": sliding_metrics.get("z_score", 0.0),
            },
            "counterparty_echo": echo_badge["badge"] if echo_badge else None,
            "counterparty_echo_meta": echo_badge,
            "buckets": bucket_list,
        }
    except Exception as e:
        logger.error(f"Error computing timeline: {e}")
        return {
            "status": "ERROR",
            "detail": str(e),
            "shibboleth_id": shibboleth_id,
            "window_minutes": window_minutes,
            "channel_key": channel_key or "ALL",
            "total_evaluated_messages": 0,
            "total_hits": 0,
            "peak_velocity_mps": 0.0,
            "peak_bucket_epoch": None,
            "buckets": [],
        }
    finally:
        con.close()


@router.api_route("/slate/active_games", methods=["GET", "HEAD"])
@faas_lexicon_router.api_route("/slate/active_games", methods=["GET", "HEAD"])
def get_active_slate_games() -> Dict[str, Any]:
    """
    Returns live, upcoming, and final games from active VFS unified slate
    correlated with watch_party_streams bindings.
    """
    vfs_path = Path("/dev/shm/vfs/schedule/unified_slate.json")
    games = []
    if vfs_path.exists():
        try:
            games = json.loads(vfs_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed parsing unified_slate.json: {e}")

    stream_map: Dict[str, str] = {}
    if DB_PATH.exists():
        try:
            con = get_wal_connection(DB_PATH)
            cur = con.cursor()
            rows = cur.execute(
                "SELECT game_pk, stream_id FROM watch_party_streams WHERE is_live = 1"
            ).fetchall()
            for r in rows:
                if r["game_pk"] and r["stream_id"]:
                    stream_map[str(r["game_pk"])] = str(r["stream_id"])
            con.close()
        except Exception as e:
            logger.warning(f"Failed querying streams for active games: {e}")

    categorized: Dict[str, List[Dict[str, Any]]] = {"live": [], "upcoming": [], "final": []}
    for g in games:
        gid = str(g.get("id", ""))
        status = str(g.get("status", "")).upper()
        away = g.get("away_team", {}).get("code") or g.get("awayTeam") or ""
        home = g.get("home_team", {}).get("code") or g.get("homeTeam") or ""
        away_name = g.get("away_team", {}).get("full_name") or away
        home_name = g.get("home_team", {}).get("full_name") or home
        away_score = g.get("away_team", {}).get("score", 0)
        home_score = g.get("home_team", {}).get("score", 0)
        clock = g.get("status_detail") or f"{g.get('clock', {}).get('display_clock', '')} P{g.get('clock', {}).get('period', '')}"

        stream_id = stream_map.get(gid) or stream_map.get(f"{away}_{home}") or stream_map.get(f"{home}_{away}")

        item = {
            "id": gid,
            "sport": g.get("sport", "cfb"),
            "matchup": f"{away} @ {home}",
            "title": f"{away_name} @ {home_name}",
            "away_team": str(away),
            "home_team": str(home),
            "away_score": away_score,
            "home_score": home_score,
            "clock": clock,
            "status": status,
            "has_stream": bool(stream_id),
            "stream_id": stream_id,
        }
        if status in ("LIVE", "IN_PROGRESS"):
            categorized["live"].append(item)
        elif status in ("FINAL", "COMPLETED", "POST"):
            categorized["final"].append(item)
        else:
            categorized["upcoming"].append(item)

    return {
        "status": "OK",
        "total_games": len(games),
        "live_count": len(categorized["live"]),
        "upcoming_count": len(categorized["upcoming"]),
        "final_count": len(categorized["final"]),
        "live": categorized["live"],
        "upcoming": categorized["upcoming"],
        "final": categorized["final"],
    }





# === WO0011233_TOE_TAG_ROUTE ===
from scripts.core.toe_tag_coroner import (
    BODY_BAGS_SHM_PATH,
    compute_sliding_10s_ring,
    evaluate_and_compile_body_bags,
)


@faas_lexicon_router.get("/body_bags")
def get_faas_body_bags() -> Dict[str, Any]:
    """Expose settled Toe-Tag autopsies and live flatline status across FINAL games."""
    if BODY_BAGS_SHM_PATH.exists():
        try:
            raw = json.loads(BODY_BAGS_SHM_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and time.time() - raw.get("updated_at", 0) <= 15:
                return raw
        except Exception as exc:
            logger.debug("SHM body bags read warning: %s", exc)
    return evaluate_and_compile_body_bags()


def get_body_bags_payload() -> Dict[str, Any]:
    """Direct callable helper for root app route mounting."""
    return get_faas_body_bags()
