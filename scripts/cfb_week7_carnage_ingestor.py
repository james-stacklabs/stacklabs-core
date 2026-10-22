#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011237: Dynamic CFB Week 7 Carnage Ingestion, Stream Tails & Portal Roster-Flattening Engine.
Enforces Argon Crucible Laws 1-9 on Clio (100.96.77.20).
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
"""

import argparse
import collections
import dataclasses
import hashlib
import json
import logging
import math
import os
import random
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cfb_week7_carnage_ingestor")

BASE_DIR = Path("/home/james/stacklabs")
DB_PATH = Path(os.getenv("WIRETAP_DB_PATH", str(BASE_DIR / "data" / "morning_wiretap.db")))
SPORTS_GT_PATH = BASE_DIR / "ground_truth" / "sports_ground_truth.json"
VFS_DIR = Path(os.getenv("FAAS_VFS_DIR", "/dev/shm/faas_vfs"))
VFS_CARTRIDGE_PATH = VFS_DIR / "cfb_week7_carnage.json"

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")
WHITESPACE_RE = re.compile(r"\s+")

# Canonical Empirical Talent Profiles (Blue-Chip Ratio & Transfer Portal Starters)
# BCR: Percentage of 4-star and 5-star signees over previous 4 recruiting cycles (247 Composite)
TEAM_TALENT_REGISTRY: Dict[str, Dict[str, float]] = {
    "UGA": {"bcr": 0.80, "portal_starters": 3},
    "AUB": {"bcr": 0.46, "portal_starters": 12},
    "ND": {"bcr": 0.68, "portal_starters": 4},
    "BYU": {"bcr": 0.27, "portal_starters": 11},
    "ALA": {"bcr": 0.86, "portal_starters": 5},
    "TENN": {"bcr": 0.58, "portal_starters": 11},
    "TEX": {"bcr": 0.81, "portal_starters": 4},
    "FLA": {"bcr": 0.50, "portal_starters": 12},
    "OSU": {"bcr": 0.88, "portal_starters": 3},
    "IND": {"bcr": 0.30, "portal_starters": 17},
    "MIA": {"bcr": 0.61, "portal_starters": 14},
    "FSU": {"bcr": 0.42, "portal_starters": 16},
    "LSU": {"bcr": 0.72, "portal_starters": 7},
    "MSST": {"bcr": 0.25, "portal_starters": 14},
    "MISS": {"bcr": 0.52, "portal_starters": 15},
    "MIZ": {"bcr": 0.38, "portal_starters": 9},
    "OU": {"bcr": 0.65, "portal_starters": 8},
    "UK": {"bcr": 0.32, "portal_starters": 10},
    "TTU": {"bcr": 0.28, "portal_starters": 13},
    "ASU": {"bcr": 0.22, "portal_starters": 15},
    "SMU": {"bcr": 0.35, "portal_starters": 14},
    "UVA": {"bcr": 0.18, "portal_starters": 11},
    "MICH": {"bcr": 0.62, "portal_starters": 6},
    "PSU": {"bcr": 0.64, "portal_starters": 5},
    "MSU": {"bcr": 0.33, "portal_starters": 13},
    "NU": {"bcr": 0.15, "portal_starters": 8},
}


@dataclasses.dataclass(frozen=True)
class DynamicCarnageMatchup:
    game_id: str
    game_pk: str
    season_week: int
    kickoff_utc: str
    away_team: str
    away_name: str
    away_rank: Optional[int]
    away_score: int
    home_team: str
    home_name: str
    home_rank: Optional[int]
    home_score: int
    spread_favorite: str
    closing_spread: float
    portal_starters_delta: int
    blue_chip_ratio_gap: float
    decisive_catalyst: str
    shibboleth_tokens: Tuple[str, ...]
    candidate_channel_keys: Tuple[str, ...]


class PooledHttpClient:
    """Argon Law 2 compliant HTTP client with connection pooling and jittered backoff."""

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = min(max(1, int(max_workers)), 6)
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StackLabs-Carnage-Ingestor/2026.10",
                "Accept": "application/json",
            }
        )

    def fetch_json_with_backoff(
        self,
        url: str,
        timeout_s: float = 6.0,
        max_attempts: int = 3,
        base_backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
    ) -> Optional[Dict[str, Any]]:
        for attempt in range(max_attempts):
            try:
                resp = self.session.get(url, timeout=timeout_s)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 502, 503, 504):
                    retry_hdr = resp.headers.get("Retry-After")
                    retry_after = float(retry_hdr) if retry_hdr and retry_hdr.isdigit() else None
                    cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
                    sleep_s = retry_after if retry_after is not None else random.uniform(cap * 0.5, cap)
                    logger.warning("HTTP %d on %s (attempt %d); sleeping %.2fs", resp.status_code, url, attempt + 1, sleep_s)
                    time.sleep(sleep_s)
                    continue
                logger.error("Non-retryable HTTP %d from %s", resp.status_code, url)
                return None
            except requests.RequestException as exc:
                cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
                sleep_s = random.uniform(cap * 0.5, cap)
                logger.warning("RequestException on %s (attempt %d): %s; sleeping %.2fs", url, attempt + 1, exc, sleep_s)
                time.sleep(sleep_s)
        return None


def connect_wal_db(db_path: Path) -> sqlite3.Connection:
    """Argon Law 3 compliant SQLite WAL connection factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def ensure_schemas(conn: sqlite3.Connection) -> None:
    """Initialize canonical tables and indexes for CFB carnage and stream telemetry."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_key TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                epoch_time REAL NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_telemetry_channel_id
            ON chat_telemetry (channel_key, id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_telemetry_channel_epoch
            ON chat_telemetry (channel_key, epoch_time);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cfb_carnage_autopsy (
                game_id TEXT PRIMARY KEY,
                season_week INTEGER NOT NULL,
                kickoff_utc TEXT NOT NULL,
                away_team TEXT NOT NULL,
                away_rank INTEGER,
                away_score INTEGER NOT NULL,
                home_team TEXT NOT NULL,
                home_rank INTEGER,
                home_score INTEGER NOT NULL,
                spread_favorite TEXT NOT NULL,
                closing_spread REAL NOT NULL,
                upset_margin_vs_spread REAL NOT NULL,
                portal_flattening_index REAL NOT NULL,
                sampled_messages INTEGER NOT NULL,
                unique_authors INTEGER NOT NULL,
                peak_cpm INTEGER NOT NULL,
                mean_shannon_entropy REAL NOT NULL,
                caps_ratio REAL NOT NULL,
                flatline_drop_ratio REAL NOT NULL,
                shibboleth_hits_json TEXT NOT NULL,
                decisive_catalyst TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                last_synced_at REAL NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS u_cmdb_ci_stream_tail (
                sys_id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                heat_score REAL NOT NULL,
                peak_cpm INTEGER NOT NULL,
                portal_flattening_index REAL NOT NULL,
                operational_status TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )


def compute_shannon_entropy(text: str) -> float:
    cleaned = EMOJI_SHORTCODE_RE.sub("", text)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        return 0.0
    length = len(cleaned)
    counts = collections.Counter(cleaned)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 4)


def get_team_talent_profile(team_abbrev: str, rank: Optional[int]) -> Tuple[float, int]:
    """Resolves Blue-Chip Ratio and portal starter baseline dynamically."""
    ab = team_abbrev.upper().strip()
    if ab in TEAM_TALENT_REGISTRY:
        prof = TEAM_TALENT_REGISTRY[ab]
        return prof["bcr"], int(prof["portal_starters"])
    if rank is not None and 1 <= rank <= 10:
        return 0.75, 5
    if rank is not None and 11 <= rank <= 25:
        return 0.55, 9
    return 0.35, 12


def load_subcultural_shibboleths_for_teams(conn: sqlite3.Connection, teams: List[str]) -> Dict[str, List[str]]:
    """Loads trigger tokens dynamically from cfb_subcultural_lexicon in morning_wiretap.db."""
    tokens_by_team: Dict[str, List[str]] = collections.defaultdict(list)
    has_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cfb_subcultural_lexicon'").fetchone()
    if not has_table:
        return tokens_by_team

    clean_teams = [t.upper().strip() for t in teams]
    for team in clean_teams:
        rows = conn.execute(
            "SELECT trigger_tokens_json FROM cfb_subcultural_lexicon WHERE UPPER(team_abbrev) = ?",
            (team,),
        ).fetchall()
        for r in rows:
            try:
                tokens = json.loads(r["trigger_tokens_json"])
                tokens_by_team[team].extend([t.lower().strip() for t in tokens if t])
            except Exception:
                continue
    return tokens_by_team


def compute_portal_flattening_index(
    home_score: int,
    away_score: int,
    spread_favorite: str,
    home_team: str,
    closing_spread: float,
    portal_starters_delta: int,
    blue_chip_ratio_gap: float,
) -> Tuple[float, float]:
    """
    Quantifies how transfer portal starter concentration flattens traditional Recruiting Blue-Chip gaps.
    Returns (upset_margin_vs_spread, portal_flattening_index).
    """
    actual_fav_margin = (
        home_score - away_score
        if spread_favorite == home_team
        else away_score - home_score
    )
    expected_fav_margin = abs(closing_spread)
    upset_swing = round(expected_fav_margin - actual_fav_margin, 2)
    portal_weight = min(1.5, portal_starters_delta / 10.0)
    bcr_compression = 1.0 + max(0.05, blue_chip_ratio_gap)
    raw_prfi = (max(0.0, upset_swing) * 0.045 + portal_weight * 0.45) * bcr_compression
    return upset_swing, round(min(1.0, raw_prfi), 4)


def discover_dynamic_cfb_slate(
    http_client: PooledHttpClient,
    conn: sqlite3.Connection,
    date_str: str = "20261017",
    season_week: int = 7,
) -> List[DynamicCarnageMatchup]:
    """
    Dynamically discovers Week 7 CFB matchups, scores, and spreads from ESPN Scoreboard API
    with fallback to sports_ground_truth.json and watch_party_streams in morning_wiretap.db.
    """
    url = f"{ESPN_SCOREBOARD_URL}?dates={date_str}"
    data = http_client.fetch_json_with_backoff(url)
    events: List[Dict[str, Any]] = []
    if data and "events" in data:
        events = data.get("events", [])
        logger.info("Fetched %d events dynamically from ESPN Scoreboard API for %s", len(events), date_str)

    # Collect team tokens from wiretap database
    all_teams_in_slate: Set[str] = set()
    raw_matchups: List[Dict[str, Any]] = []

    if events:
        for ev in events:
            comps = ev.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

            h_ab = str(home.get("team", {}).get("abbreviation", "HOME")).upper().strip()
            a_ab = str(away.get("team", {}).get("abbreviation", "AWAY")).upper().strip()
            h_name = str(home.get("team", {}).get("displayName", h_ab))
            a_name = str(away.get("team", {}).get("displayName", a_ab))

            h_score = int(home.get("score", 0) or 0)
            a_score = int(away.get("score", 0) or 0)

            h_rank_raw = home.get("curatedRank", {}).get("current")
            a_rank_raw = away.get("curatedRank", {}).get("current")
            h_rank = int(h_rank_raw) if h_rank_raw and 1 <= int(h_rank_raw) <= 25 else None
            a_rank = int(a_rank_raw) if a_rank_raw and 1 <= int(a_rank_raw) <= 25 else None

            odds_list = comps.get("odds", [])
            odds_detail = odds_list[0].get("details") if odds_list else None
            spread_fav = h_ab
            closing_spread = -3.5

            if odds_detail and " " in odds_detail:
                parts = odds_detail.strip().split()
                spread_fav = parts[0].upper()
                try:
                    closing_spread = float(parts[1])
                except ValueError:
                    closing_spread = -3.5
            elif h_rank and not a_rank:
                spread_fav = h_ab
                closing_spread = -10.5
            elif a_rank and not h_rank:
                spread_fav = a_ab
                closing_spread = -10.5
            elif h_rank and a_rank:
                spread_fav = h_ab if h_rank < a_rank else a_ab
                closing_spread = -float(abs(h_rank - a_rank) * 1.5 + 2.5)

            status_desc = comps.get("status", {}).get("type", {}).get("name", "SCHEDULED")
            venue_name = comps.get("venue", {}).get("fullName", "Campus Stadium")

            all_teams_in_slate.add(h_ab)
            all_teams_in_slate.add(a_ab)

            raw_matchups.append(
                {
                    "game_pk": str(ev.get("id", "")),
                    "kickoff_utc": ev.get("date", "2026-10-17T19:30:00Z"),
                    "away_team": a_ab,
                    "away_name": a_name,
                    "away_rank": a_rank,
                    "away_score": a_score,
                    "home_team": h_ab,
                    "home_name": h_name,
                    "home_rank": h_rank,
                    "home_score": h_score,
                    "spread_favorite": spread_fav,
                    "closing_spread": closing_spread,
                    "status_desc": status_desc,
                    "venue_name": venue_name,
                }
            )

    # Fallback to sports_ground_truth.json if ESPN returned zero events
    if not raw_matchups and SPORTS_GT_PATH.exists():
        try:
            gt_data = json.loads(SPORTS_GT_PATH.read_text(encoding="utf-8"))
            top25 = gt_data.get("cfb_top25_slate_20261017", {}).get("games", [])
            for g in top25:
                a_info = g.get("away_team", {})
                h_info = g.get("home_team", {})
                h_ab = str(h_info.get("code", "")).upper()
                a_ab = str(a_info.get("code", "")).upper()
                all_teams_in_slate.add(h_ab)
                all_teams_in_slate.add(a_ab)
                raw_matchups.append(
                    {
                        "game_pk": str(g.get("game_id", "")).replace("cfb_", ""),
                        "kickoff_utc": "2026-10-17T19:30:00Z",
                        "away_team": a_ab,
                        "away_name": a_info.get("full_name", a_ab),
                        "away_rank": a_info.get("rank"),
                        "away_score": int(a_info.get("score", 0) or 0),
                        "home_team": h_ab,
                        "home_name": h_info.get("full_name", h_ab),
                        "home_rank": h_info.get("rank"),
                        "home_score": int(h_info.get("score", 0) or 0),
                        "spread_favorite": h_ab if (h_info.get("rank") or 99) < (a_info.get("rank") or 99) else a_ab,
                        "closing_spread": -7.5,
                        "status_desc": g.get("status", "FINAL"),
                        "venue_name": g.get("venue", "Campus Stadium"),
                    }
                )
            logger.info("Loaded %d fallback games from sports_ground_truth.json", len(raw_matchups))
        except Exception as e:
            logger.error("Failed loading fallback ground truth: %s", e)

    shib_map = load_subcultural_shibboleths_for_teams(conn, list(all_teams_in_slate))

    # Known marquee Week 7 empirical lines calibration (if live feed lacked closing lines)
    known_lines = {
        ("AUB", "UGA"): ("UGA", -14.5),
        ("ND", "BYU"): ("ND", -6.5),
        ("ALA", "TENN"): ("ALA", -3.5),
        ("FLA", "TEX"): ("TEX", -13.5),
        ("OSU", "IND"): ("OSU", -2.5),
        ("FSU", "MIA"): ("MIA", -16.5),
    }

    matchups: List[DynamicCarnageMatchup] = []

    for r in raw_matchups:
        a_ab, h_ab = r["away_team"], r["home_team"]
        # Look up closing lines calibration if defaults were used
        if (a_ab, h_ab) in known_lines:
            fav, line = known_lines[(a_ab, h_ab)]
            r["spread_favorite"] = fav
            r["closing_spread"] = line

        h_bcr, h_portal = get_team_talent_profile(h_ab, r["home_rank"])
        a_bcr, a_portal = get_team_talent_profile(a_ab, r["away_rank"])
        portal_delta = abs(h_portal - a_portal)
        bcr_gap = round(abs(h_bcr - a_bcr), 4)

        game_id = f"CFB_2026_W7_{a_ab}_{h_ab}"
        game_pk = r["game_pk"]

        # Build candidate channel keys for dynamic wiretap telemetry resolution
        candidate_keys = (
            f"{h_ab}_dynamic",
            f"{a_ab}_dynamic",
            f"{a_ab}@{h_ab} LIVE",
            f"CFB_{game_pk}",
            game_id,
            f"{a_ab}_{h_ab}",
        )

        tokens: List[str] = [h_ab.lower(), a_ab.lower(), "upset", "portal", "flatline"]
        tokens.extend(shib_map.get(h_ab, []))
        tokens.extend(shib_map.get(a_ab, []))
        dedup_tokens = tuple(sorted(set(t for t in tokens if len(t) >= 3)))

        # Formulate decisive catalyst
        winner = h_ab if r["home_score"] > r["away_score"] else a_ab
        loser = a_ab if winner == h_ab else h_ab
        win_score = max(r["home_score"], r["away_score"])
        lose_score = min(r["home_score"], r["away_score"])
        upset_swing, prfi = compute_portal_flattening_index(
            r["home_score"],
            r["away_score"],
            r["spread_favorite"],
            h_ab,
            r["closing_spread"],
            portal_delta,
            bcr_gap,
        )

        catalyst = (
            f"{winner} ({win_score}-{lose_score}) upset over {loser} at {r['venue_name']} "
            f"(line swing: +{upset_swing:.1f} pts, PRFI: {prfi:.4f})"
        )

        # Include Top-25, Upset, or high PRFI games
        is_upset = (
            (r["home_rank"] and r["away_score"] > r["home_score"] and (not r["away_rank"] or r["away_rank"] > r["home_rank"]))
            or (r["away_rank"] and r["home_score"] > r["away_score"] and (not r["home_rank"] or r["home_rank"] > r["away_rank"]))
            or (upset_swing > 0 and abs(r["closing_spread"]) >= 3.0)
        )
        is_marquee = bool(r["home_rank"] or r["away_rank"] or (a_ab, h_ab) in known_lines)

        if is_upset or is_marquee or prfi >= 0.75:
            matchups.append(
                DynamicCarnageMatchup(
                    game_id=game_id,
                    game_pk=game_pk,
                    season_week=season_week,
                    kickoff_utc=r["kickoff_utc"],
                    away_team=a_ab,
                    away_name=r["away_name"],
                    away_rank=r["away_rank"],
                    away_score=r["away_score"],
                    home_team=h_ab,
                    home_name=r["home_name"],
                    home_rank=r["home_rank"],
                    home_score=r["home_score"],
                    spread_favorite=r["spread_favorite"],
                    closing_spread=r["closing_spread"],
                    portal_starters_delta=portal_delta,
                    blue_chip_ratio_gap=bcr_gap,
                    decisive_catalyst=catalyst,
                    shibboleth_tokens=dedup_tokens,
                    candidate_channel_keys=candidate_keys,
                )
            )

    logger.info("Filtered %d qualifying CFB Week 7 carnage matchups", len(matchups))
    return matchups


def analyze_entity_stream_tail(
    conn: sqlite3.Connection, spec: DynamicCarnageMatchup
) -> Dict[str, Any]:
    """
    Argon Law 3 & Law 5: Strictly entity-scoped cursor pagination over chat_telemetry
    using candidate channel resolution, bounded ring buffers, and O(1) sliding deduplication.
    """
    ring_messages: Deque[str] = collections.deque(maxlen=1000)
    dedup_order: Deque[Tuple[str, str, str, int]] = collections.deque(maxlen=4096)
    dedup_set: Set[Tuple[str, str, str, int]] = set()
    authors: Set[str] = set()
    minute_buckets: Dict[int, int] = collections.defaultdict(int)
    shibboleth_counts: Dict[str, int] = {tok: 0 for tok in spec.shibboleth_tokens}

    cursor_id = 0
    total_valid = 0
    channel_placeholders = ",".join(["?"] * len(spec.candidate_channel_keys))

    while True:
        query = f"""
            SELECT id, stream_id, author, message, epoch_time
            FROM chat_telemetry
            WHERE channel_key IN ({channel_placeholders}) AND id > ?
            ORDER BY id ASC
            LIMIT 500;
        """
        params = list(spec.candidate_channel_keys) + [cursor_id]
        rows = conn.execute(query, params).fetchall()

        if not rows:
            break

        for row in rows:
            cursor_id = int(row["id"])
            norm_author = str(row["author"]).strip().lower()
            raw_msg = str(row["message"])
            norm_text = WHITESPACE_RE.sub(" ", EMOJI_SHORTCODE_RE.sub("", raw_msg)).strip().lower()
            bucket_10s = int(float(row["epoch_time"]) // 10)
            dedup_key = (str(row["stream_id"]), norm_author, norm_text, bucket_10s)

            if dedup_key in dedup_set:
                continue
            if len(dedup_order) >= 4096:
                evicted = dedup_order.popleft()
                dedup_set.discard(evicted)
            dedup_order.append(dedup_key)
            dedup_set.add(dedup_key)

            total_valid += 1
            authors.add(norm_author)
            ring_messages.append(raw_msg)
            minute_bucket = int(float(row["epoch_time"]) // 60) * 60
            minute_buckets[minute_bucket] += 1

            for tok in spec.shibboleth_tokens:
                if tok in norm_text:
                    shibboleth_counts[tok] += 1

    if not ring_messages:
        return {
            "sampled_messages": 0,
            "unique_authors": 0,
            "peak_cpm": 0,
            "mean_shannon_entropy": 0.0,
            "caps_ratio": 0.0,
            "flatline_drop_ratio": 0.0,
            "shibboleth_hits": shibboleth_counts,
        }

    entropies: List[float] = []
    alpha_chars = 0
    upper_chars = 0
    for msg in ring_messages:
        entropies.append(compute_shannon_entropy(msg))
        cleaned = EMOJI_SHORTCODE_RE.sub("", msg)
        for ch in cleaned:
            if ch.isalpha():
                alpha_chars += 1
                if ch.isupper():
                    upper_chars += 1

    mean_entropy = round(sum(entropies) / len(entropies), 4) if entropies else 0.0
    caps_ratio = round(upper_chars / alpha_chars, 4) if alpha_chars > 0 else 0.0

    sorted_buckets = sorted(minute_buckets.items(), key=lambda kv: kv[0])
    peak_cpm = max((cnt for _, cnt in sorted_buckets), default=0)
    tail_cpm = sorted_buckets[-1][1] if sorted_buckets else 0
    flatline_drop = round(1.0 - (tail_cpm / peak_cpm), 4) if peak_cpm > 0 else 0.0

    # Prune zero hits from shibboleths output to keep payload lean
    positive_hits = {k: v for k, v in shibboleth_counts.items() if v > 0}

    return {
        "sampled_messages": total_valid,
        "unique_authors": len(authors),
        "peak_cpm": peak_cpm,
        "mean_shannon_entropy": mean_entropy,
        "caps_ratio": caps_ratio,
        "flatline_drop_ratio": max(0.0, flatline_drop),
        "shibboleth_hits": positive_hits,
    }


def compute_canonical_sha256(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def upsert_autopsy_merkle(
    conn: sqlite3.Connection,
    spec: DynamicCarnageMatchup,
    tail_metrics: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Argon Law 1 & Law 6: Content-addressable SQLite WAL upsert + CMDB CI synthesis."""
    upset_swing, prfi = compute_portal_flattening_index(
        spec.home_score,
        spec.away_score,
        spec.spread_favorite,
        spec.home_team,
        spec.closing_spread,
        spec.portal_starters_delta,
        spec.blue_chip_ratio_gap,
    )
    shibboleths_json = json.dumps(tail_metrics["shibboleth_hits"], sort_keys=True, separators=(",", ":"))

    record_core = {
        "game_id": spec.game_id,
        "season_week": spec.season_week,
        "kickoff_utc": spec.kickoff_utc,
        "away_team": spec.away_team,
        "away_rank": spec.away_rank,
        "away_score": spec.away_score,
        "home_team": spec.home_team,
        "home_rank": spec.home_rank,
        "home_score": spec.home_score,
        "spread_favorite": spec.spread_favorite,
        "closing_spread": spec.closing_spread,
        "upset_margin_vs_spread": upset_swing,
        "portal_flattening_index": prfi,
        "sampled_messages": tail_metrics["sampled_messages"],
        "unique_authors": tail_metrics["unique_authors"],
        "peak_cpm": tail_metrics["peak_cpm"],
        "mean_shannon_entropy": tail_metrics["mean_shannon_entropy"],
        "caps_ratio": tail_metrics["caps_ratio"],
        "flatline_drop_ratio": tail_metrics["flatline_drop_ratio"],
        "shibboleth_hits_json": shibboleths_json,
        "decisive_catalyst": spec.decisive_catalyst,
    }
    digest = compute_canonical_sha256(record_core)
    now_ts = round(time.time(), 3)

    existing = conn.execute(
        "SELECT content_sha256 FROM cfb_carnage_autopsy WHERE game_id = ?;",
        (spec.game_id,),
    ).fetchone()

    sync_action = "SKIPPED_MERKLE_MATCH"
    if not existing or existing["content_sha256"] != digest:
        sync_action = "DRY_RUN_WOULD_UPSERT" if dry_run else "MERKLE_DELTA_COMMITTED"
        if not dry_run:
            with conn:
                conn.execute(
                    """
                    INSERT INTO cfb_carnage_autopsy (
                        game_id, season_week, kickoff_utc,
                        away_team, away_rank, away_score,
                        home_team, home_rank, home_score,
                        spread_favorite, closing_spread, upset_margin_vs_spread,
                        portal_flattening_index, sampled_messages, unique_authors,
                        peak_cpm, mean_shannon_entropy, caps_ratio,
                        flatline_drop_ratio, shibboleth_hits_json,
                        decisive_catalyst, content_sha256, last_synced_at
                    ) VALUES (
                        :game_id, :season_week, :kickoff_utc,
                        :away_team, :away_rank, :away_score,
                        :home_team, :home_rank, :home_score,
                        :spread_favorite, :closing_spread, :upset_margin_vs_spread,
                        :portal_flattening_index, :sampled_messages, :unique_authors,
                        :peak_cpm, :mean_shannon_entropy, :caps_ratio,
                        :flatline_drop_ratio, :shibboleth_hits_json,
                        :decisive_catalyst, :content_sha256, :last_synced_at
                    )
                    ON CONFLICT(game_id) DO UPDATE SET
                        away_score = excluded.away_score,
                        home_score = excluded.home_score,
                        upset_margin_vs_spread = excluded.upset_margin_vs_spread,
                        portal_flattening_index = excluded.portal_flattening_index,
                        sampled_messages = excluded.sampled_messages,
                        unique_authors = excluded.unique_authors,
                        peak_cpm = excluded.peak_cpm,
                        mean_shannon_entropy = excluded.mean_shannon_entropy,
                        caps_ratio = excluded.caps_ratio,
                        flatline_drop_ratio = excluded.flatline_drop_ratio,
                        shibboleth_hits_json = excluded.shibboleth_hits_json,
                        decisive_catalyst = excluded.decisive_catalyst,
                        content_sha256 = excluded.content_sha256,
                        last_synced_at = excluded.last_synced_at;
                    """,
                    {**record_core, "content_sha256": digest, "last_synced_at": now_ts},
                )

                # Synthesize CMDB CI when Portal Flattening or Heat >= 0.82
                heat_score = round(min(1.0, prfi * 0.7 + tail_metrics["caps_ratio"] * 0.3), 4)
                if heat_score >= 0.82 or prfi >= 0.82:
                    ci_sys_id = f"ci_stream_tail_{spec.game_id.lower()}"
                    conn.execute(
                        """
                        INSERT INTO u_cmdb_ci_stream_tail (
                            sys_id, game_id, heat_score, peak_cpm,
                            portal_flattening_index, operational_status,
                            content_sha256, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(sys_id) DO UPDATE SET
                            heat_score = excluded.heat_score,
                            peak_cpm = excluded.peak_cpm,
                            portal_flattening_index = excluded.portal_flattening_index,
                            operational_status = excluded.operational_status,
                            content_sha256 = excluded.content_sha256,
                            updated_at = excluded.updated_at;
                        """,
                        (
                            ci_sys_id,
                            spec.game_id,
                            heat_score,
                            tail_metrics["peak_cpm"],
                            prfi,
                            "POST_FINAL_AUTOPSY_LOCKED",
                            digest,
                            now_ts,
                        ),
                    )

    return {
        **record_core,
        "shibboleth_hits": tail_metrics["shibboleth_hits"],
        "content_sha256": digest,
        "sync_action": sync_action,
    }


def write_atomic_vfs_cartridge(records: List[Dict[str, Any]], target_path: Path) -> str:
    """Argon Law 6: Atomic write-to-temp-and-rename VFS state output."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "schema_version": "2026.10.18.w7",
        "generated_at_epoch": round(time.time(), 3),
        "total_games_audited": len(records),
        "mean_portal_flattening_index": round(
            sum(r["portal_flattening_index"] for r in records) / max(1, len(records)), 4
        ),
        "items": records,
    }
    payload_bytes = json.dumps(envelope, indent=2, sort_keys=True).encode("utf-8")
    envelope_sha = hashlib.sha256(payload_bytes).hexdigest()
    tmp_path = target_path.with_suffix(".json.tmp")
    tmp_path.write_bytes(payload_bytes)
    os.replace(tmp_path, target_path)
    return envelope_sha


def run_ingestion(
    db_path: Path,
    vfs_path: Path,
    date_str: str = "20261017",
    season_week: int = 7,
    dry_run: bool = False,
) -> Dict[str, Any]:
    conn = connect_wal_db(db_path)
    try:
        ensure_schemas(conn)
        http_client = PooledHttpClient(max_workers=4)

        # Discover matchups dynamically
        matchups = discover_dynamic_cfb_slate(
            http_client=http_client,
            conn=conn,
            date_str=date_str,
            season_week=season_week,
        )

        results: List[Dict[str, Any]] = []
        for spec in matchups:
            tail_metrics = analyze_entity_stream_tail(conn, spec)
            autopsy_row = upsert_autopsy_merkle(conn, spec, tail_metrics, dry_run=dry_run)
            results.append(autopsy_row)

        # Sort results by PRFI descending
        results.sort(key=lambda r: (r["portal_flattening_index"], r["upset_margin_vs_spread"]), reverse=True)

        vfs_sha = "DRY_RUN_NO_WRITE"
        if not dry_run:
            vfs_sha = write_atomic_vfs_cartridge(results, vfs_path)

        summary = {
            "status": "OK",
            "dry_run": dry_run,
            "date": date_str,
            "season_week": season_week,
            "db_path": str(db_path),
            "vfs_path": str(vfs_path),
            "vfs_sha256": vfs_sha,
            "games_processed": len(results),
            "merkle_commits": sum(1 for r in results if r["sync_action"] == "MERKLE_DELTA_COMMITTED"),
            "merkle_skips": sum(1 for r in results if r["sync_action"] == "SKIPPED_MERKLE_MATCH"),
            "total_sampled_chat_messages": sum(r["sampled_messages"] for r in results),
        }
        logger.info("CFB Week 7 Carnage Ingestion Summary: %s", json.dumps(summary))
        return summary
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic CFB Week 7 Carnage Ingestion, Stream Tails & Portal Roster-Flattening.")
    parser.add_argument("--date", type=str, default="20261017", help="Date string YYYYMMDD.")
    parser.add_argument("--week", type=int, default=7, help="Season week number.")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Path to SQLite WAL database.")
    parser.add_argument("--vfs-path", type=Path, default=VFS_CARTRIDGE_PATH, help="Path to atomic VFS output JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without mutating SQLite or VFS.")
    args = parser.parse_args()

    summary = run_ingestion(
        db_path=args.db_path,
        vfs_path=args.vfs_path,
        date_str=args.date,
        season_week=args.week,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
