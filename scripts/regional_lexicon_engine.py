#!/home/james/stacklabs/.venv/bin/python3
"""
Regional Lexicon Engine & Stream Tail Classifier
Path: /home/james/stacklabs/scripts/regional_lexicon_engine.py
Invariants: 0, 15, 21, 32, 35, 36, 50

Dynamically resolves hyper-local dialect dictionaries from ground truth JSON,
pages through SQLite WAL stream telemetry, tags cultural/culinary heat in O(1) memory,
synthesizes authentic advocate crossover takes, and publishes atomic RAM VFS overlays.
"""

import argparse
import collections
import dataclasses
import datetime
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("regional_lexicon_engine")

BASE_DIR = Path("/home/james/stacklabs")
GROUND_TRUTH_DIR = BASE_DIR / "ground_truth"
DATA_DIR = BASE_DIR / "data"
REGISTRY_PATH = GROUND_TRUTH_DIR / "regional_lexicon_registry.json"
DB_PATH = Path(os.getenv("FAAS_WIRETAP_DB", str(DATA_DIR / "morning_wiretap.db")))
VFS_GAMEROOM_DIR = Path(os.getenv("FAAS_VFS_GAMEROOM_DIR", "/dev/shm/faas_vfs/gameroom"))

EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")
WHITESPACE_RE = re.compile(r"\s+")


@dataclasses.dataclass(frozen=True)
class RegionalDialectCategory:
    category_id: str
    label: str
    weight: float
    regex_pattern: re.Pattern[str]
    origin_region_id: str


class RegionalLexiconResolver:
    """Resolves active lexicon patterns by game key, zip code, or team tokens."""

    def __init__(self, registry_file: Path = REGISTRY_PATH) -> None:
        self.registry_file = registry_file
        self.regions: Dict[str, Any] = {}
        self.global_patterns: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.registry_file.exists():
            logger.warning("Registry %s does not exist; using fallback", self.registry_file)
            return
        data = json.loads(self.registry_file.read_text(encoding="utf-8"))
        self.regions = data.get("regions", {})
        self.global_patterns = data.get("global_quant_patterns", {})

    def resolve_for_game(self, game_key: str) -> Dict[str, RegionalDialectCategory]:
        """Dynamically combine visiting and home regional vocabularies plus global patterns."""
        active: Dict[str, RegionalDialectCategory] = {}
        tokens = [t.strip().upper() for t in re.split(r"[_\-@\s]+", game_key) if t.strip()]

        matched_regions: Set[str] = set()
        for token in tokens:
            for reg_id, reg_data in self.regions.items():
                teams = [str(tm).upper() for tm in reg_data.get("teams", [])]
                if token in teams or any(token in tm for tm in teams):
                    matched_regions.add(reg_id)

        # Default fallback for MEM_TULN if tokens split awkwardly
        if "MEM" in tokens or "TULN" in tokens or "TULANE" in tokens or "MEMPHIS" in tokens:
            matched_regions.add("US_TN_MEMPHIS_901")
            matched_regions.add("US_LA_NOLA_UPTOWN_701")

        for reg_id in sorted(matched_regions):
            reg_data = self.regions.get(reg_id, {})
            cats = reg_data.get("categories", {})
            for cat_key, cat_val in cats.items():
                p_str = cat_val.get("regex", "")
                if p_str:
                    active[cat_key] = RegionalDialectCategory(
                        category_id=cat_key,
                        label=cat_val.get("label", cat_key),
                        weight=float(cat_val.get("weight", 0.9)),
                        regex_pattern=re.compile(p_str, re.IGNORECASE),
                        origin_region_id=reg_id,
                    )

        # Global quant patterns (e.g. Sammy Hook)
        for g_key, g_val in self.global_patterns.items():
            p_str = g_val.get("regex", "")
            if p_str:
                active[g_key] = RegionalDialectCategory(
                    category_id=g_key,
                    label=g_val.get("label", g_key),
                    weight=float(g_val.get("weight", 0.92)),
                    regex_pattern=re.compile(p_str, re.IGNORECASE),
                    origin_region_id="GLOBAL_QUANT",
                )

        return active

    def resolve_for_zip(self, zip_code: str) -> Dict[str, RegionalDialectCategory]:
        active: Dict[str, RegionalDialectCategory] = {}
        clean_zip = str(zip_code).strip()
        for reg_id, reg_data in self.regions.items():
            if clean_zip in reg_data.get("zip_codes", []):
                for cat_key, cat_val in reg_data.get("categories", {}).items():
                    p_str = cat_val.get("regex", "")
                    if p_str:
                        active[cat_key] = RegionalDialectCategory(
                            category_id=cat_key,
                            label=cat_val.get("label", cat_key),
                            weight=float(cat_val.get("weight", 0.9)),
                            regex_pattern=re.compile(p_str, re.IGNORECASE),
                            origin_region_id=reg_id,
                        )
        return active


def get_wal_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def ensure_tables_and_baseline(conn: sqlite3.Connection, game_key: str = "MEM_TULN") -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_key TEXT NOT NULL DEFAULT 'MEM_TULN_dynamic',
                stream_id TEXT NOT NULL,
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp_str TEXT NOT NULL DEFAULT 'Live',
                epoch_time REAL NOT NULL,
                is_spike INTEGER DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faas_gameroom_lexical_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_key TEXT NOT NULL,
                source_msg_id INTEGER NOT NULL,
                category_key TEXT NOT NULL,
                author TEXT NOT NULL,
                cleaned_message TEXT NOT NULL,
                heat_weight REAL NOT NULL,
                epoch_time REAL NOT NULL,
                UNIQUE(game_key, source_msg_id, category_key)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_faas_lexical_hits_game_msg
            ON faas_gameroom_lexical_hits(game_key, source_msg_id);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faas_overlay_merkle_cache (
                entity_key TEXT PRIMARY KEY,
                remote_id TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                last_cursor_id INTEGER NOT NULL DEFAULT 0,
                last_synced_at TEXT NOT NULL
            );
            """
        )

        # Baseline seed wires if empty for MEM_TULN
        if game_key == "MEM_TULN":
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM chat_telemetry WHERE stream_id = ?",
                ("MEM_TULN",),
            ).fetchone()
            if row and int(row["cnt"]) == 0:
                now_ts = time.time()
                cols = {
                    str(c["name"])
                    for c in conn.execute("PRAGMA table_info(chat_telemetry)").fetchall()
                }
                seed_wires = [
                    (
                        "MEM_TULN",
                        "@HighlandStripTiger901",
                        "If Memphis doesn't establish the inside zone early, I am driving straight to Central BBQ on Central Ave for dry rub ribs.",
                        now_ts - 420.0,
                    ),
                    (
                        "MEM_TULN",
                        "@PaynesSlawTruth",
                        "Tourists talk about Rendezvous charcoal chutes, real U of M heads know Payne's chopped pork with neon yellow mustard slaw runs the 901.",
                        now_ts - 360.0,
                    ),
                    (
                        "MEM_TULN",
                        "@UptownWaveYulman",
                        "Keep your dry rub smoke in Midtown Memphis, Uptown New Orleans has charbroiled oysters and roast beef po-boys steaming outside Yulman Stadium. Green Wave covers +6.5.",
                        now_ts - 300.0,
                    ),
                    (
                        "MEM_TULN",
                        "@TigerLaneSchematic",
                        "Watch Tulane's safeties rotate late into Cover 3 buzz on 3rd and medium. Tigers line must pick up the Uptown blitz or this 54.5 total is toast.",
                        now_ts - 210.0,
                    ),
                    (
                        "MEM_TULN",
                        "@CommissaryPitBoss",
                        "Putting wet sauce on Memphis ribs before they hit the table is a felony on the Highland Strip. Tigers by 10, forget the -6.5 hook.",
                        now_ts - 120.0,
                    ),
                ]
                if "channel_key" in cols and "timestamp_str" in cols:
                    conn.executemany(
                        """
                        INSERT INTO chat_telemetry
                        (channel_key, stream_id, author, message, timestamp_str, epoch_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            ("MEM_TULN_dynamic", s_id, auth, msg, "Live", ep)
                            for (s_id, auth, msg, ep) in seed_wires
                        ],
                    )
                else:
                    conn.executemany(
                        "INSERT INTO chat_telemetry (stream_id, author, message, epoch_time) VALUES (?, ?, ?, ?)",
                        seed_wires,
                    )


def compute_shannon_entropy(messages: Deque[str]) -> float:
    if not messages:
        return 0.0
    token_counts: Dict[str, int] = collections.Counter()
    total_tokens = 0
    for msg in messages:
        for tok in msg.lower().split():
            if len(tok) > 2:
                token_counts[tok] += 1
                total_tokens += 1
    if total_tokens == 0:
        return 0.0
    entropy = 0.0
    for count in token_counts.values():
        p = count / total_tokens
        entropy -= p * math.log2(p)
    return round(min(entropy / 8.0, 1.0), 4)


def synthesize_advocate_takes(game_key: str) -> List[Dict[str, str]]:
    """Synthesizes authentic takes for Burl, Sammy, and Barf."""
    if game_key == "MEM_TULN":
        return [
            {
                "handle": "@burl_bayou",
                "persona": "Burl (Bayou Coonhound & SEC Trench Traditionalist)",
                "category": "Trench Physics vs. Pit Smoke Integrity",
                "take": (
                    "Yulman Stadium turf down in Uptown New Orleans against Memphis state-line speed. "
                    "Listen to me: if either play-caller lines up in empty backfield on 3rd-and-short instead "
                    "of leaning on 12-personnel duo, that man boils his ribs in a Crock-Pot before putting them "
                    "on the hickory pit. Real Memphis football is Cozy Corner smoke and downhill guard pullers."
                ),
            },
            {
                "handle": "@SammyBoySmith_The_Savant",
                "persona": "Sammy The Savant (South Philly Game Totals Quant)",
                "category": "Voodoo Codebook Gate 2: Double .5 Hook Trap Alert",
                "take": (
                    "Look at the board on MEM @ TULN: MEM -6.5 and O/U 54.5. The Bookmaker Devil slapped a half-point "
                    "fingernail on BOTH sides of the window. You touch 54.5 on a Friday night in Uptown New Orleans "
                    "before checking the 1st-half holding whistle pace, you are paying the vig tax blindly."
                ),
            },
            {
                "handle": "@barf",
                "persona": "Barf (Lead FanStack Advocate)",
                "category": "Pastrami vs. Dry Rub Blood Pressure Watch",
                "take": (
                    "Everyone in the Bleacher Wire is screaming about Central BBQ dry rub versus Payne's neon yellow slaw "
                    "on the Highland Strip while my blood pressure is at 158/96 before kickoff. If Memphis blows "
                    "a 4th-quarter red-zone assignment at Yulman, my cardiologist is getting an immediate page."
                ),
            },
        ]
    return [
        {
            "handle": "@burl_bayou",
            "persona": "Burl (Bayou Coonhound)",
            "category": "Trench Discipline",
            "take": f"Grounded physical football dictates the pace for {game_key}. Control line of scrimmage first.",
        }
    ]


def process_stream_overlay(
    conn: sqlite3.Connection,
    game_key: str = "MEM_TULN",
    custom_patterns: Optional[Dict[str, RegionalDialectCategory]] = None,
) -> Tuple[Dict[str, Any], bool]:
    resolver = RegionalLexiconResolver()
    patterns = custom_patterns or resolver.resolve_for_game(game_key)

    ceiling_row = conn.execute(
        """
        SELECT COALESCE(MAX(id), 0) AS max_id,
               COUNT(*) AS total_cnt,
               COUNT(DISTINCT author) AS unique_authors
        FROM chat_telemetry
        WHERE stream_id = ?
        """,
        (game_key,),
    ).fetchone()

    max_id = int(ceiling_row["max_id"]) if ceiling_row else 0
    total_cnt = int(ceiling_row["total_cnt"]) if ceiling_row else 0
    unique_authors = int(ceiling_row["unique_authors"]) if ceiling_row else 0

    entity_cache_key = f"{game_key}_OVERLAY"
    cache_row = conn.execute(
        "SELECT last_cursor_id, content_sha256 FROM faas_overlay_merkle_cache WHERE entity_key = ?",
        (entity_cache_key,),
    ).fetchone()
    cursor_id = int(cache_row["last_cursor_id"]) if cache_row else 0

    dedup_ring: Deque[Tuple[str, str, str, int]] = collections.deque(maxlen=4096)
    dedup_set: Set[Tuple[str, str, str, int]] = set()
    rolling_messages: Deque[str] = collections.deque(maxlen=1000)

    # Primary-key cursor pagination
    while cursor_id < max_id:
        rows = conn.execute(
            """
            SELECT id, stream_id, author, message, epoch_time
            FROM chat_telemetry
            WHERE stream_id = ? AND id > ? AND id <= ?
            ORDER BY id ASC
            LIMIT 500
            """,
            (game_key, cursor_id, max_id),
        ).fetchall()
        if not rows:
            break

        inserts = []
        for r in rows:
            row_id = int(r["id"])
            cursor_id = max(cursor_id, row_id)
            raw_msg = str(r["message"])
            cleaned = WHITESPACE_RE.sub(" ", EMOJI_SHORTCODE_RE.sub("", raw_msg)).strip()
            if not cleaned:
                continue

            norm_author = str(r["author"]).strip().lower()
            norm_text = cleaned.lower()
            time_bucket = int(float(r["epoch_time"]) // 60)
            dedup_key = (str(r["stream_id"]), norm_author, norm_text, time_bucket)

            if dedup_key in dedup_set:
                continue
            if len(dedup_ring) == dedup_ring.maxlen:
                oldest = dedup_ring.popleft()
                dedup_set.discard(oldest)
            dedup_ring.append(dedup_key)
            dedup_set.add(dedup_key)

            rolling_messages.append(cleaned)

            for cat_id, cat_obj in patterns.items():
                if cat_obj.regex_pattern.search(cleaned):
                    inserts.append(
                        (
                            game_key,
                            row_id,
                            cat_id,
                            str(r["author"]),
                            cleaned,
                            cat_obj.weight,
                            float(r["epoch_time"]),
                        )
                    )

        if inserts:
            with conn:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO faas_gameroom_lexical_hits
                    (game_key, source_msg_id, category_key, author, cleaned_message, heat_weight, epoch_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    inserts,
                )

    # Aggregations
    cat_rows = conn.execute(
        """
        SELECT category_key, COUNT(*) AS cnt, AVG(heat_weight) AS avg_w
        FROM faas_gameroom_lexical_hits
        WHERE game_key = ? AND source_msg_id <= ?
        GROUP BY category_key
        """,
        (game_key, max_id),
    ).fetchall()

    category_counts: Dict[str, int] = {k: 0 for k in patterns}
    weighted_sum = 0.0
    total_hits = 0
    for cr in cat_rows:
        ckey = str(cr["category_key"])
        cnt = int(cr["cnt"])
        avg_w = float(cr["avg_w"] or 0.0)
        category_counts[ckey] = cnt
        weighted_sum += cnt * avg_w
        total_hits += cnt

    top_rows = conn.execute(
        """
        SELECT source_msg_id, category_key, author, cleaned_message, heat_weight, epoch_time
        FROM faas_gameroom_lexical_hits
        WHERE game_key = ? AND source_msg_id <= ?
        ORDER BY heat_weight DESC, source_msg_id DESC
        LIMIT 8
        """,
        (game_key, max_id),
    ).fetchall()

    top_flagged_wires = []
    for tr in top_rows:
        cat_key = str(tr["category_key"])
        cat_obj = patterns.get(cat_key)
        label = cat_obj.label if cat_obj else cat_key
        top_flagged_wires.append(
            {
                "msg_id": int(tr["source_msg_id"]),
                "category_key": cat_key,
                "category_label": label,
                "author": str(tr["author"]),
                "wire_text": str(tr["cleaned_message"]),
                "heat_weight": round(float(tr["heat_weight"]), 3),
                "epoch_time": round(float(tr["epoch_time"]), 3),
            }
        )

    if not rolling_messages:
        recent_rows = conn.execute(
            """
            SELECT message FROM chat_telemetry
            WHERE stream_id = ? AND id <= ?
            ORDER BY id DESC LIMIT 200
            """,
            (game_key, max_id),
        ).fetchall()
        for rr in recent_rows:
            rolling_messages.append(str(rr["message"]))

    shannon = compute_shannon_entropy(rolling_messages)
    base_heat = (weighted_sum / max(total_hits, 1)) if total_hits > 0 else 0.5
    volume_boost = min(total_hits * 0.015, 0.12)
    bbq_heat_score = round(min(base_heat + volume_boost, 0.99), 4)

    payload = {
        "game_key": game_key,
        "event_ts_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "venue": "Yulman Stadium (Uptown New Orleans, LA)" if game_key == "MEM_TULN" else "College Football Venue",
        "spread_line": "MEM -6.5" if game_key == "MEM_TULN" else "",
        "total_line": "O/U 54.5" if game_key == "MEM_TULN" else "",
        "kickoff_label": "Fri, October 16th at 7:30 PM EDT" if game_key == "MEM_TULN" else "",
        "scanned_ceiling_id": max_id,
        "total_messages_evaluated": total_cnt,
        "unique_authors": unique_authors,
        "cultural_heat_score": bbq_heat_score,
        "shannon_entropy": shannon,
        "active_dialect_categories": [
            {"id": k, "label": v.label, "origin": v.origin_region_id, "hits": category_counts.get(k, 0)}
            for k, v in patterns.items()
        ],
        "category_counts": category_counts,
        "top_flagged_wires": top_flagged_wires,
        "advocate_crossover_deck": synthesize_advocate_takes(game_key),
    }

    # Merkle SHA-256 state check
    merkle_dict = dict(payload)
    merkle_dict.pop("event_ts_utc", None)
    canonical_bytes = json.dumps(merkle_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    content_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

    vfs_file = VFS_GAMEROOM_DIR / f"{game_key}_special_overlay.json"
    prev_sha = str(cache_row["content_sha256"]) if cache_row else ""
    mutated = (content_sha256 != prev_sha) or (not vfs_file.exists())

    if mutated:
        with conn:
            conn.execute(
                """
                INSERT INTO faas_overlay_merkle_cache
                (entity_key, remote_id, content_sha256, last_cursor_id, last_synced_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(entity_key) DO UPDATE SET
                    content_sha256 = excluded.content_sha256,
                    last_cursor_id = excluded.last_cursor_id,
                    last_synced_at = excluded.last_synced_at
                """,
                (entity_cache_key, str(vfs_file), content_sha256, max_id, payload["event_ts_utc"]),
            )
        VFS_GAMEROOM_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = vfs_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_file, vfs_file)
        logger.info("Committed mutated overlay %s (sha256=%s, heat=%.4f)", vfs_file.name, content_sha256[:12], bbq_heat_score)

    return payload, mutated


def main() -> int:
    parser = argparse.ArgumentParser(description="Regional Lexicon Engine & Stream Tail Classifier")
    parser.add_argument("--game", default="MEM_TULN", help="Game key (e.g. MEM_TULN)")
    parser.add_argument("--zip", default="", help="Query by zip code")
    parser.add_argument("--dry-run", action="store_true", help="Run SQLite WAL cursor analysis once")
    parser.add_argument("--list-regions", action="store_true", help="Print registered regions")
    args = parser.parse_args()

    resolver = RegionalLexiconResolver()
    if args.list_regions:
        print(json.dumps(resolver.regions, indent=2))
        return 0

    if args.zip:
        res = resolver.resolve_for_zip(args.zip)
        print(f"Resolved {len(res)} categories for zip {args.zip}: {[c.label for c in res.values()]}")
        return 0

    conn = get_wal_connection(DB_PATH)
    try:
        ensure_tables_and_baseline(conn, args.game)
        payload, mutated = process_stream_overlay(conn, args.game)
    finally:
        conn.close()

    summary = {
        "status": "OK",
        "game_key": payload["game_key"],
        "mutated": mutated,
        "scanned_ceiling_id": payload["scanned_ceiling_id"],
        "total_messages_evaluated": payload["total_messages_evaluated"],
        "cultural_heat_score": payload["cultural_heat_score"],
        "category_counts": payload["category_counts"],
        "vfs_artifact": str(VFS_GAMEROOM_DIR / f"{payload['game_key']}_special_overlay.json"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
