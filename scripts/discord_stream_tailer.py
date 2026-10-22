#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs FaaS Discord Gateway v10 Real-Time Stream Tailer & Burst Ingress Daemon
Path: /home/james/stacklabs/scripts/discord_stream_tailer.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Target Host: Clio dedicated Linux host (100.96.77.20)
Governing Standards: Invariant 0, 1.9, 15, 32 (Law of "I"), 35 (.venv), 38 (Telemetry Isolation), 50 (Drop-In Code), Argon Laws 1-9
"""

import argparse
import asyncio
import collections
import dataclasses
import datetime
import hashlib
import json
import math
import os
import random
import re
import signal
import sqlite3
import sys
import tempfile
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Set, Tuple

import aiohttp
import requests
from requests.adapters import HTTPAdapter

REPO_ROOT = Path("/home/james/stacklabs")
ENV_PATH = REPO_ROOT / ".env"
DB_PATH = Path(
    os.getenv(
        "STACKLABS_WIRETAP_DB",
        str(REPO_ROOT / "data" / "morning_wiretap.db"),
    )
)
VFS_TELEMETRY_DIR = Path("/dev/shm/vfs/telemetry")
DISCORD_BURST_VFS_PATH = VFS_TELEMETRY_DIR / "discord_burst_latest.json"
DEFAULT_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
DISCORD_API_BASE = "https://discord.com/api/v10"

# Pre-compiled sanitization regexes (Argon Law 3: Zero-I/O Hot Path)
USER_MENTION_RE = re.compile(r"<@!?\d+>")
ROLE_MENTION_RE = re.compile(r"<@&\d+>")
CHANNEL_MENTION_RE = re.compile(r"<#\d+>")
CUSTOM_EMOJI_RE = re.compile(r"<a?:[a-zA-Z0-9_]+:\d+>")
EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")
URL_RE = re.compile(r"https?://\S+")
MARKDOWN_NOISE_RE = re.compile(r"[*_~`|>]")
UNICODE_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)
WHITESPACE_RE = re.compile(r"\s+")
WORD_TOKEN_RE = re.compile(r"[a-z0-9']+")

STOPWORDS: Set[str] = {
    "the", "and", "for", "that", "this", "with", "you", "are", "was", "but",
    "not", "have", "from", "they", "what", "all", "were", "when", "your",
    "can", "said", "there", "use", "each", "which", "she", "how", "their",
    "will", "other", "about", "out", "many", "then", "them", "these", "some",
    "her", "would", "make", "like", "him", "into", "time", "has", "look",
    "two", "more", "write", "see", "number", "way", "could", "people", "than",
    "first", "water", "been", "call", "who", "oil", "its", "now", "find",
    "just", "bro", "man", "lol", "lmao", "yeah", "yes", "nah", "got", "get",
}

def load_dotenv_file(env_path: Path) -> None:
    """Loads key=value pairs from /home/james/stacklabs/.env without overriding existing env vars."""
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip()
            val = v.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError as exc:
        print(f"[DISCORD-TAILER] Warning reading {env_path}: {exc}", file=sys.stderr)

def atomic_write_json(target: Path, payload: Dict[str, Any]) -> None:
    """Argon Law 6: Atomic write-to-temp-and-rename so readers never observe partial JSON."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=str(target.parent), delete=False, encoding="utf-8"
    ) as tf:
        json.dump(payload, tf, indent=2, sort_keys=True)
        tf.write("\n")
        tmp_name = tf.name
    os.replace(tmp_name, str(target))

def build_pooled_http_session() -> requests.Session:
    """Argon Law 2: Single shared requests.Session mounted with HTTPAdapter(pool_connections=8, pool_maxsize=8)."""
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": "StackLabs-Discord-Tailer/1.0 (+https://stacklabsllc.com)",
            "Accept": "application/json",
        }
    )
    return session

def get_wal_connection(db_path: Path) -> sqlite3.Connection:
    """Argon Law 3: SQLite connection configured with WAL mode, NORMAL sync, 5000ms busy timeout, and MEMORY temp_store."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=15.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    con.execute("PRAGMA temp_store=MEMORY;")
    return con

@dataclasses.dataclass(frozen=True)
class ChannelEntityBinding:
    """Strict Entity-Scoped Mapping (Invariant 38 & Argon Law 5)."""
    channel_id: str
    game_id: str
    stream_id: str
    sport: str = "cfb"
    home_team: str = "HOME"
    away_team: str = "AWAY"
    stream_title: str = "Discord Live Game Channel"

@dataclasses.dataclass(frozen=True)
class SanitizedDiscordMessage:
    """Normalized Discord MESSAGE_CREATE telemetry record ready for SQLite WAL persistence."""
    message_id: str
    channel_id: str
    channel_key: str
    stream_id: str
    author: str
    raw_content: str
    clean_message: str
    normalized_lower: str
    tokens: List[str]
    token_count: int
    timestamp_str: str
    epoch_time: float
    content_sha256: str

    def to_db_tuple(self) -> Tuple[str, str, str, str, str, float, int, str, str]:
        return (
            self.channel_key,
            self.stream_id,
            self.author,
            self.clean_message,
            self.timestamp_str,
            self.epoch_time,
            self.token_count,
            self.content_sha256,
            self.channel_id,
        )

@dataclasses.dataclass(frozen=True)
class BurstAlertEvent:
    """Statistical burst alert emitted when a sliding-window n-gram or shibboleth crosses +4.5 sigma."""
    alert_id: str
    channel_key: str
    stream_id: str
    channel_id: str
    shibboleth_id: str
    team_abbrev: str
    ngram_or_token: str
    hit_count: int
    window_messages: int
    window_seconds: float
    velocity_mps: float
    z_score: float
    z_score_threshold: float
    peak_author: str
    peak_quote: str
    timestamp_str: str
    epoch_time: float
    content_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

def sanitize_discord_text(raw_text: str) -> Tuple[str, str, List[str], int]:
    """
    Strips Discord mentions (<@...>, <#...>, <@&...>), custom emojis (<:name:id>),
    shortcode emojis (:name:), URLs, Unicode emojis, and markdown control characters.
    Returns (clean_display_text, normalized_lowercase_text, word_tokens, token_count).
    """
    if not raw_text:
        return "", "", [], 0
    txt = USER_MENTION_RE.sub(" ", raw_text)
    txt = ROLE_MENTION_RE.sub(" ", txt)
    txt = CHANNEL_MENTION_RE.sub(" ", txt)
    txt = CUSTOM_EMOJI_RE.sub(" ", txt)
    txt = EMOJI_SHORTCODE_RE.sub(" ", txt)
    txt = URL_RE.sub(" ", txt)
    txt = UNICODE_EMOJI_RE.sub(" ", txt)
    txt = MARKDOWN_NOISE_RE.sub(" ", txt)
    clean_display = WHITESPACE_RE.sub(" ", txt).strip()
    norm_lower = clean_display.lower()
    tokens = WORD_TOKEN_RE.findall(norm_lower)
    return clean_display, norm_lower, tokens, len(tokens)

def compute_merkle_sha256(payload: Dict[str, Any]) -> str:
    """Argon Law 1: Deterministic SHA-256 Merkle digest over canonical sorted-key JSON."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def ensure_wiretap_discord_schemas(con: sqlite3.Connection) -> None:
    """
    Ensures chat_telemetry, watch_party_streams, cfb_subcultural_lexicon, and discord_burst_alerts
    exist in morning_wiretap.db with full backward compatibility for faas_vfs_telemetry.py.
    """
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_key TEXT,
            stream_id TEXT,
            author TEXT,
            message TEXT,
            timestamp_str TEXT,
            epoch_time REAL,
            token_count INTEGER DEFAULT 0,
            content_sha256 TEXT,
            discord_channel_id TEXT
        )
        """
    )
    # Safely add optional columns if chat_telemetry was created by an older schema version
    existing_cols = {
        row["name"]
        for row in cur.execute("PRAGMA table_info(chat_telemetry)").fetchall()
    }
    if "token_count" not in existing_cols:
        cur.execute("ALTER TABLE chat_telemetry ADD COLUMN token_count INTEGER DEFAULT 0")
    if "content_sha256" not in existing_cols:
        cur.execute("ALTER TABLE chat_telemetry ADD COLUMN content_sha256 TEXT")
    if "discord_channel_id" not in existing_cols:
        cur.execute("ALTER TABLE chat_telemetry ADD COLUMN discord_channel_id TEXT")

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_stream_epoch ON chat_telemetry(stream_id, epoch_time)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_channel_id ON chat_telemetry(channel_key, id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_merkle_sha256 ON chat_telemetry(content_sha256)"
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watch_party_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT NOT NULL,
            game_pk TEXT NOT NULL,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            stream_id TEXT NOT NULL,
            stream_title TEXT,
            stream_url TEXT,
            source TEXT,
            resolved_at TEXT,
            is_live INTEGER DEFAULT 1,
            UNIQUE(game_pk, stream_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_watch_party_game ON watch_party_streams(game_pk, game_date)"
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_burst_alerts (
            alert_id TEXT PRIMARY KEY,
            channel_key TEXT NOT NULL,
            stream_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            shibboleth_id TEXT NOT NULL,
            team_abbrev TEXT NOT NULL,
            ngram_or_token TEXT NOT NULL,
            hit_count INTEGER NOT NULL,
            window_messages INTEGER NOT NULL,
            window_seconds REAL NOT NULL,
            velocity_mps REAL NOT NULL,
            z_score REAL NOT NULL,
            z_score_threshold REAL NOT NULL,
            peak_author TEXT NOT NULL,
            peak_quote TEXT NOT NULL,
            timestamp_str TEXT NOT NULL,
            epoch_time REAL NOT NULL,
            content_sha256 TEXT NOT NULL
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_discord_burst_channel_epoch ON discord_burst_alerts(channel_key, epoch_time DESC)"
    )
    con.commit()

    # Ensure the 16 canonical CFB subcultural shibboleths are seeded in cfb_subcultural_lexicon
    try:
        from scripts.cfb_slate_omni_resolver import sync_lexicon_to_sqlite
        sync_lexicon_to_sqlite(con)
        try:
            from scripts.nfl_slate_omni_resolver import sync_nfl_lexicon_to_sqlite
            sync_nfl_lexicon_to_sqlite(con)
        except Exception:
            pass
    except ImportError:
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from scripts.cfb_slate_omni_resolver import sync_lexicon_to_sqlite
            sync_lexicon_to_sqlite(con)
        except Exception as exc:
            print(f"[DISCORD-TAILER] Lexicon seed import warning: {exc}", file=sys.stderr)

def load_lexicon_From_sqlite(db_path: Path) -> List[Dict[str, Any]]:
    """Loads the 16 canonical CFB subcultural shibboleths from morning_wiretap.db."""
    if not db_path.exists():
        return []
    con = get_wal_connection(db_path)
    try:
        cur = con.cursor()
        has_table = cur.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name='v_subcultural_lexicon'"
        ).fetchone() or cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cfb_subcultural_lexicon'"
        ).fetchone()
        if not has_table:
            return []
        rows = cur.execute(
            "SELECT shibboleth_id, team_abbrev, program_name, trigger_tokens_json, z_score_threshold "
            "FROM " + ("v_subcultural_lexicon" if cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name='v_subcultural_lexicon'").fetchone() else "cfb_subcultural_lexicon") + " ORDER BY team_abbrev ASC"
        ).fetchall()
        catalog: List[Dict[str, Any]] = []
        for r in rows:
            tokens = json.loads(r["trigger_tokens_json"])
            catalog.append(
                {
                    "shibboleth_id": str(r["shibboleth_id"]),
                    "team_abbrev": str(r["team_abbrev"]),
                    "program_name": str(r["program_name"]),
                    "trigger_tokens": [str(t).lower().strip() for t in tokens if str(t).strip()],
                    "z_score_threshold": float(r["z_score_threshold"] or 4.5),
                }
            )
        return catalog
    finally:
        con.close()

def register_discord_stream_binding(
    db_path: Path, binding: ChannelEntityBinding, is_live: int = 1
) -> None:
    """
    Upserts the Discord channel binding into watch_party_streams so faas_vfs_telemetry.py
    immediately serves the scoped stream on /api/vfs_telemetry/chat_tail?game_id=<game_id>.
    """
    con = get_wal_connection(db_path)
    try:
        ensure_wiretap_discord_schemas(con)
        cur = con.cursor()
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        stream_url = f"https://discord.com/channels/@me/{binding.channel_id}"
        # Handle both schemas of watch_party_streams (stream_id PK or (game_pk, stream_id) UNIQUE)
        try:
            cur.execute(
                """
                INSERT INTO watch_party_streams (
                    sport, game_pk, game_date, home_team, away_team,
                    stream_id, stream_title, stream_url, source, resolved_at, is_live
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'discord_gateway_v10', datetime('now'), ?)
                ON CONFLICT(game_pk, stream_id) DO UPDATE SET
                    stream_title = excluded.stream_title,
                    stream_url = excluded.stream_url,
                    is_live = excluded.is_live,
                    resolved_at = datetime('now')
                """,
                (
                    binding.sport,
                    binding.game_id,
                    today_str,
                    binding.home_team,
                    binding.away_team,
                    binding.stream_id,
                    binding.stream_title,
                    stream_url,
                    int(is_live),
                ),
            )
        except sqlite3.OperationalError:
            cur.execute(
                """
                INSERT INTO watch_party_streams (
                    sport, game_pk, game_date, home_team, away_team,
                    stream_id, stream_title, stream_url, source, resolved_at, is_live
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'discord_gateway_v10', datetime('now'), ?)
                ON CONFLICT(stream_id) DO UPDATE SET
                    game_pk = excluded.game_pk,
                    stream_title = excluded.stream_title,
                    stream_url = excluded.stream_url,
                    is_live = excluded.is_live,
                    resolved_at = datetime('now')
                """,
                (
                    binding.sport,
                    binding.game_id,
                    today_str,
                    binding.home_team,
                    binding.away_team,
                    binding.stream_id,
                    binding.stream_title,
                    stream_url,
                    int(is_live),
                ),
            )
        con.commit()
    finally:
        con.close()

class SlidingWindowBurstGate:
    """
    Argon Law 3: Bounded In-Memory Sliding Ring Buffer & O(1) Deduplication Gate.
    Maintains a rolling time window (default 60s) per channel_key, calculates real-time
    messages-per-second (mps) velocity and binomial z-scores against cfb_subcultural_lexicon
    and emergent n-grams, and emits BurstAlertEvent records when z_score >= +4.5 sigma.
    """

    def __init__(
        self,
        lexicon: List[Dict[str, Any]],
        window_seconds: float = 60.0,
        sigma_threshold: float = 4.5,
        max_ring_size: int = 2000,
        cooldown_seconds: float = 15.0,
    ) -> None:
        self.lexicon = lexicon
        self.window_seconds = max(5.0, float(window_seconds))
        self.sigma_threshold = float(sigma_threshold)
        self.max_ring_size = int(max_ring_size)
        self.cooldown_seconds = float(cooldown_seconds)
        self._windows: Dict[str, Deque[SanitizedDiscordMessage]] = collections.defaultdict(
            lambda: deque(maxlen=self.max_ring_size)
        )
        self._dedup_ring: Deque[str] = deque(maxlen=4096)
        self._dedup_set: Set[str] = set()
        self._last_alert_ts: Dict[Tuple[str, str], float] = {}

    def is_duplicate(self, msg: SanitizedDiscordMessage) -> bool:
        """O(1) bounded deduplication ring keyed on (stream_id, author, clean_message, 5s_bucket)."""
        bucket = int(msg.epoch_time // 5)
        dedup_key = f"{msg.stream_id}|{msg.author.lower()}|{msg.normalized_lower}|{bucket}"
        if dedup_key in self._dedup_set:
            return True
        if len(self._dedup_ring) >= self._dedup_ring.maxlen:
            evicted = self._dedup_ring.popleft()
            self._dedup_set.discard(evicted)
        self._dedup_ring.append(dedup_key)
        self._dedup_set.add(dedup_key)
        return False

    @staticmethod
    def _extract_candidate_ngrams(tokens: List[str]) -> Set[str]:
        filtered = [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]
        grams: Set[str] = set(filtered)
        for i in range(len(filtered) - 1):
            grams.add(f"{filtered[i]} {filtered[i + 1]}")
        for i in range(len(filtered) - 2):
            grams.add(f"{filtered[i]} {filtered[i + 1]} {filtered[i + 2]}")
        return grams

    def ingest_and_evaluate(
        self, msg: SanitizedDiscordMessage
    ) -> Tuple[float, List[BurstAlertEvent]]:
        """
        Appends message to the channel's sliding window, evicts expired entries older than
        window_seconds, computes messages-per-second velocity, and evaluates +4.5 sigma bursts.
        """
        ring = self._windows[msg.channel_key]
        ring.append(msg)
        cutoff = msg.epoch_time - self.window_seconds
        while ring and ring[0].epoch_time < cutoff:
            ring.popleft()

        total_msgs = len(ring)
        elapsed = max(1.0, min(self.window_seconds, msg.epoch_time - ring[0].epoch_time + 1.0))
        velocity_mps = round(total_msgs / elapsed, 3)

        # Binomial baseline expectation matching faas_vfs_telemetry.py & cfb_slate_omni_resolver.py
        expected_mean = max(total_msgs * 0.005, 0.5)
        std_dev = math.sqrt(max(total_msgs * 0.005 * 0.995, 0.25))

        alerts: List[BurstAlertEvent] = []

        # 1. Evaluate against the 16 canonical CFB subcultural shibboleths
        for item in self.lexicon:
            shib_id = item["shibboleth_id"]
            team_abbrev = item["team_abbrev"]
            tokens = item["trigger_tokens"]
            threshold = max(self.sigma_threshold, float(item.get("z_score_threshold", 4.5)))

            matched_here = [tok for tok in tokens if tok in msg.normalized_lower]
            if not matched_here:
                continue

            hit_count = 0
            matched_set: Set[str] = set()
            for m in ring:
                hits = [tok for tok in tokens if tok in m.normalized_lower]
                if hits:
                    hit_count += 1
                    matched_set.update(hits)

            if hit_count <= 0:
                continue

            z_score = round((hit_count - expected_mean) / std_dev, 2)
            cooldown_key = (msg.channel_key, shib_id)
            last_emitted = self._last_alert_ts.get(cooldown_key, 0.0)

            if z_score >= threshold and (msg.epoch_time - last_emitted) >= self.cooldown_seconds:
                self._last_alert_ts[cooldown_key] = msg.epoch_time
                token_label = ", ".join(sorted(matched_set))
                alert_payload = {
                    "channel_key": msg.channel_key,
                    "stream_id": msg.stream_id,
                    "shibboleth_id": shib_id,
                    "hit_count": hit_count,
                    "z_score": z_score,
                    "epoch_bucket": int(msg.epoch_time // 10),
                }
                digest = compute_merkle_sha256(alert_payload)
                alerts.append(
                    BurstAlertEvent(
                        alert_id=f"burst-{shib_id.lower()}-{int(msg.epoch_time * 1000)}",
                        channel_key=msg.channel_key,
                        stream_id=msg.stream_id,
                        channel_id=msg.channel_id,
                        shibboleth_id=shib_id,
                        team_abbrev=team_abbrev,
                        ngram_or_token=token_label,
                        hit_count=hit_count,
                        window_messages=total_msgs,
                        window_seconds=self.window_seconds,
                        velocity_mps=velocity_mps,
                        z_score=z_score,
                        z_score_threshold=threshold,
                        peak_author=msg.author,
                        peak_quote=msg.clean_message,
                        timestamp_str=msg.timestamp_str,
                        epoch_time=msg.epoch_time,
                        content_sha256=digest,
                    )
                )

        # 2. Evaluate uncatalogued emergent n-gram spikes crossing +4.5 sigma when no canonical shibboleth matched
        if total_msgs >= 20 and not alerts and not any(
            any(tok in msg.normalized_lower for tok in item["trigger_tokens"])
            for item in self.lexicon
        ):
            current_grams = self._extract_candidate_ngrams(msg.tokens)
            if current_grams:
                gram_counts: Counter[str] = Counter()
                for m in ring:
                    for g in self._extract_candidate_ngrams(m.tokens):
                        if g in current_grams:
                            gram_counts[g] += 1
                for gram, count in gram_counts.items():
                    if count < 8 or count > int(total_msgs * 0.6):
                        continue
                    z_score = round((count - expected_mean) / std_dev, 2)
                    shib_key = f"NGRAM_{gram.upper().replace(' ', '_')[:32]}"
                    cooldown_key = (msg.channel_key, shib_key)
                    if (
                        z_score >= self.sigma_threshold
                        and (msg.epoch_time - self._last_alert_ts.get(cooldown_key, 0.0))
                        >= self.cooldown_seconds
                    ):
                        self._last_alert_ts[cooldown_key] = msg.epoch_time
                        alert_payload = {
                            "channel_key": msg.channel_key,
                            "stream_id": msg.stream_id,
                            "shibboleth_id": shib_key,
                            "hit_count": count,
                            "z_score": z_score,
                            "epoch_bucket": int(msg.epoch_time // 10),
                        }
                        digest = compute_merkle_sha256(alert_payload)
                        alerts.append(
                            BurstAlertEvent(
                                alert_id=f"burst-ngram-{int(msg.epoch_time * 1000)}-{abs(hash(gram)) % 10000}",
                                channel_key=msg.channel_key,
                                stream_id=msg.stream_id,
                                channel_id=msg.channel_id,
                                shibboleth_id=shib_key,
                                team_abbrev=msg.channel_key.split("_")[0][:6].upper(),
                                ngram_or_token=gram,
                                hit_count=count,
                                window_messages=total_msgs,
                                window_seconds=self.window_seconds,
                                velocity_mps=velocity_mps,
                                z_score=z_score,
                                z_score_threshold=self.sigma_threshold,
                                peak_author=msg.author,
                                peak_quote=msg.clean_message,
                                timestamp_str=msg.timestamp_str,
                                epoch_time=msg.epoch_time,
                                content_sha256=digest,
                            )
                        )

        return velocity_mps, alerts

class AsyncSQLiteWALWriter:
    """
    Non-blocking SQLite WAL batch writer consuming SanitizedDiscordMessage and BurstAlertEvent
    items from an asyncio.Queue and committing with Merkle SHA-256 deduplication.
    """

    def __init__(self, db_path: Path, dry_run: bool = False) -> None:
        self.db_path = db_path
        self.dry_run = dry_run
        self.msg_queue: asyncio.Queue[Optional[SanitizedDiscordMessage]] = asyncio.Queue(maxsize=10000)
        self.alert_queue: asyncio.Queue[Optional[BurstAlertEvent]] = asyncio.Queue(maxsize=1000)
        self.rows_written: int = 0
        self.alerts_written: int = 0

    def flush_sync(
        self,
        messages: List[SanitizedDiscordMessage],
        alerts: List[BurstAlertEvent],
    ) -> Tuple[int, int]:
        if self.dry_run or (not messages and not alerts):
            return 0, 0
        con = get_wal_connection(self.db_path)
        try:
            ensure_wiretap_discord_schemas(con)
            cur = con.cursor()
            msg_count = 0
            alert_count = 0
            if messages:
                cur.executemany(
                    """
                    INSERT INTO chat_telemetry (
                        channel_key, stream_id, author, message,
                        timestamp_str, epoch_time, token_count,
                        content_sha256, discord_channel_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [m.to_db_tuple() for m in messages],
                )
                msg_count = len(messages)
            if alerts:
                cur.executemany(
                    """
                    INSERT OR REPLACE INTO discord_burst_alerts (
                        alert_id, channel_key, stream_id, channel_id,
                        shibboleth_id, team_abbrev, ngram_or_token,
                        hit_count, window_messages, window_seconds,
                        velocity_mps, z_score, z_score_threshold,
                        peak_author, peak_quote, timestamp_str,
                        epoch_time, content_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            a.alert_id,
                            a.channel_key,
                            a.stream_id,
                            a.channel_id,
                            a.shibboleth_id,
                            a.team_abbrev,
                            a.ngram_or_token,
                            a.hit_count,
                            a.window_messages,
                            a.window_seconds,
                            a.velocity_mps,
                            a.z_score,
                            a.z_score_threshold,
                            a.peak_author,
                            a.peak_quote,
                            a.timestamp_str,
                            a.epoch_time,
                            a.content_sha256,
                        )
                        for a in alerts
                    ],
                )
                alert_count = len(alerts)
                latest = alerts[-1].to_dict()
                atomic_write_json(DISCORD_BURST_VFS_PATH, latest)
            con.commit()
            self.rows_written += msg_count
            self.alerts_written += alert_count
            return msg_count, alert_count
        finally:
            con.close()

    async def run_writer_loop(self) -> None:
        msg_batch: List[SanitizedDiscordMessage] = []
        alert_batch: List[BurstAlertEvent] = []
        last_flush = time.monotonic()
        running = True

        while running:
            try:
                item = await asyncio.wait_for(self.msg_queue.get(), timeout=0.5)
                if item is None:
                    running = False
                else:
                    msg_batch.append(item)
                self.msg_queue.task_done()
            except asyncio.TimeoutError:
                pass

            while not self.alert_queue.empty():
                alert_item = self.alert_queue.get_nowait()
                if alert_item is not None:
                    alert_batch.append(alert_item)
                self.alert_queue.task_done()

            now = time.monotonic()
            if (len(msg_batch) >= 20 or alert_batch or (now - last_flush >= 1.0)) and (
                msg_batch or alert_batch
            ):
                to_write_msgs = list(msg_batch)
                to_write_alerts = list(alert_batch)
                msg_batch.clear()
                alert_batch.clear()
                last_flush = now
                if not self.dry_run:
                    await asyncio.to_thread(self.flush_sync, to_write_msgs, to_write_alerts)

        if (msg_batch or alert_batch) and not self.dry_run:
            await asyncio.to_thread(self.flush_sync, msg_batch, alert_batch)

class DiscordGatewayStreamTailer:
    """
    Asynchronous Discord Gateway v10 WebSocket Tailer enforcing:
    - Dual Auth Mode (DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN)
    - Strict Channel-to-Game Entity Isolation (Invariant 38 & Argon Law 5)
    - 60s Sliding-Window Statistical Burst Gating (+4.5 sigma)
    - Hard 4-hour TTL (14400s) & Clean Shutdown (Argon Law 9)
    """

    def __init__(
        self,
        bindings: Dict[str, ChannelEntityBinding],
        db_path: Path = DB_PATH,
        bot_token: Optional[str] = None,
        user_token: Optional[str] = None,
        window_seconds: float = 60.0,
        sigma_threshold: float = 4.5,
        ttl_seconds: int = 14400,
        dry_run: bool = False,
        gateway_url: str = DEFAULT_GATEWAY_URL,
    ) -> None:
        if not bindings:
            raise ValueError("At least one explicit channel-to-game binding is required (Invariant 38).")
        self.bindings = dict(bindings)
        self.db_path = db_path
        self.bot_token = (bot_token or "").strip() or None
        self.user_token = (user_token or "").strip() or None
        self.auth_mode = "BOT" if self.bot_token else ("USER" if self.user_token else "UNAUTHENTICATED")
        self.window_seconds = float(window_seconds)
        self.sigma_threshold = float(sigma_threshold)
        self.ttl_seconds = min(int(ttl_seconds), 14400)
        self.dry_run = bool(dry_run)
        self.gateway_url = gateway_url

        if not self.dry_run:
            con = get_wal_connection(self.db_path)
            try:
                ensure_wiretap_discord_schemas(con)
            finally:
                con.close()
        lexicon = load_lexicon_From_sqlite(self.db_path)
        self.burst_gate = SlidingWindowBurstGate(
            lexicon=lexicon,
            window_seconds=self.window_seconds,
            sigma_threshold=self.sigma_threshold,
        )
        self.writer = AsyncSQLiteWALWriter(db_path=self.db_path, dry_run=self.dry_run)

        self._seq: Optional[int] = None
        self._session_id: Optional[str] = None
        self._resume_gateway_url: Optional[str] = None
        self._last_heartbeat_ack: bool = True
        self._stop_event = asyncio.Event()
        self.ingested_count: int = 0
        self.ignored_unmapped_count: int = 0
        self.emitted_bursts: List[BurstAlertEvent] = []

    def build_identify_payload(self) -> Dict[str, Any]:
        """Constructs Discord Gateway v10 Opcode 2 IDENTIFY payload for Bot or User token mode."""
        if self.bot_token:
            token_str = (
                self.bot_token
                if self.bot_token.startswith("Bot ")
                else self.bot_token
            )
            # Intents: GUILDS (1<<0) | GUILD_MESSAGES (1<<9) | DIRECT_MESSAGES (1<<12) | MESSAGE_CONTENT (1<<15) = 37377
            return {
                "op": 2,
                "d": {
                    "token": token_str,
                    "intents": 37377,
                    "properties": {
                        "os": "linux",
                        "browser": "stacklabs_faas_tailer",
                        "device": "stacklabs_faas_tailer",
                    },
                },
            }
        if self.user_token:
            return {
                "op": 2,
                "d": {
                    "token": self.user_token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Linux",
                        "browser": "Chrome",
                        "device": "",
                        "system_locale": "en-US",
                        "browser_user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                        "browser_version": "130.0.0.0",
                        "os_version": "",
                        "referrer": "",
                        "referring_domain": "",
                        "referrer_current": "",
                        "referring_domain_current": "",
                        "release_channel": "stable",
                        "client_build_number": 342000,
                    },
                    "presence": {"status": "invisible", "since": 0, "activities": [], "afk": True},
                    "compress": False,
                },
            }
        raise RuntimeError(
            "No Discord token configured. Provide DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN."
        )

    def process_message_create_event(
        self, event_data: Dict[str, Any], now_epoch: Optional[float] = None
    ) -> Optional[Tuple[SanitizedDiscordMessage, float, List[BurstAlertEvent]]]:
        """
        Validates channel isolation (Invariant 38), strips mentions/emojis, computes token length
        and Merkle hash, evaluates sliding-window z-score bursts, and returns the record.
        """
        channel_id = str(event_data.get("channel_id") or "").strip()
        binding = self.bindings.get(channel_id)
        if binding is None:
            # Strict Invariant 38 Enforcement: Unmapped channels never enter game telemetry
            self.ignored_unmapped_count += 1
            return None

        raw_content = str(event_data.get("content") or "").strip()
        clean_msg, norm_lower, tokens, token_count = sanitize_discord_text(raw_content)
        if not clean_msg or token_count < 1:
            return None

        author_obj = event_data.get("author") or {}
        author_name = str(
            author_obj.get("global_name")
            or author_obj.get("username")
            or "DiscordFan"
        ).strip()
        message_id = str(event_data.get("id") or f"msg-{int(time.time() * 1000)}")
        epoch = float(now_epoch if now_epoch is not None else time.time())

        raw_ts = str(event_data.get("timestamp") or "")
        if "T" in raw_ts:
            t_part = raw_ts.split("T", 1)[1][:8]
            timestamp_str = t_part if len(t_part) == 8 else time.strftime("%H:%M:%S", time.localtime(epoch))
        else:
            timestamp_str = time.strftime("%H:%M:%S", time.localtime(epoch))

        merkle_digest = compute_merkle_sha256(
            {
                "channel_id": channel_id,
                "channel_key": binding.game_id,
                "stream_id": binding.stream_id,
                "message_id": message_id,
                "author": author_name,
                "clean_message": clean_msg,
            }
        )

        record = SanitizedDiscordMessage(
            message_id=message_id,
            channel_id=channel_id,
            channel_key=binding.game_id,
            stream_id=binding.stream_id,
            author=author_name,
            raw_content=raw_content,
            clean_message=clean_msg,
            normalized_lower=norm_lower,
            tokens=tokens,
            token_count=token_count,
            timestamp_str=timestamp_str,
            epoch_time=epoch,
            content_sha256=merkle_digest,
        )

        if self.burst_gate.is_duplicate(record):
            return None

        velocity_mps, alerts = self.burst_gate.ingest_and_evaluate(record)
        self.ingested_count += 1
        if alerts:
            self.emitted_bursts.extend(alerts)
            for alert in alerts:
                print(
                    f"[BURST ALERT +{alert.z_score:.2f}σ] game={alert.channel_key} "
                    f"shibboleth={alert.shibboleth_id} token='{alert.ngram_or_token}' "
                    f"hits={alert.hit_count}/{alert.window_messages} mps={alert.velocity_mps:.2f} "
                    f"quote=\"{alert.peak_quote[:80]}\"",
                    file=sys.stderr if self.dry_run else sys.stdout,
                    flush=True,
                )
        return record, velocity_mps, alerts

    async def _heartbeat_loop(self, ws: aiohttp.ClientWebSocketResponse, interval_ms: float) -> None:
        interval_s = max(5.0, float(interval_ms) / 1000.0)
        # Initial jitter per Discord Gateway v10 specification
        await asyncio.sleep(interval_s * random.uniform(0.1, 0.5))
        while not ws.closed and not self._stop_event.is_set():
            if not self._last_heartbeat_ack:
                print("[DISCORD-TAILER] Zombied connection detected (missing HEARTBEAT_ACK). Reconnecting...", flush=True)
                await ws.close(code=4000)
                return
            self._last_heartbeat_ack = False
            await ws.send_json({"op": 1, "d": self._seq})
            await asyncio.sleep(interval_s)

    def run_dry_run_diagnostic(self) -> Dict[str, Any]:
        """
        Executes --dry-run diagnostic verification: validates Gateway endpoint discovery,
        channel-to-game bindings, lexicon triggers, and synthetic message pipeline without writing to SQLite.
        """
        session = build_pooled_http_session()
        gateway_probe_status = "SKIPPED_OFFLINE"
        discovered_url = self.gateway_url
        try:
            resp = session.get(f"{DISCORD_API_BASE}/gateway", timeout=5)
            if resp.status_code == 200:
                body = resp.json()
                discovered_url = f"{body.get('url', 'wss://gateway.discord.gg')}/?v=10&encoding=json"
                gateway_probe_status = "REACHABLE_HTTP_200"
            else:
                gateway_probe_status = f"HTTP_{resp.status_code}"
        except requests.RequestException as exc:
            gateway_probe_status = f"LOCAL_DIAGNOSTIC_ONLY ({exc.__class__.__name__})"

        first_binding = next(iter(self.bindings.values()))
        base_epoch = time.time()
        # Feed 20 neutral filler messages + 6 shibboleth trigger messages in the mapped channel
        # plus 3 unmapped channel messages to prove Invariant 38 isolation and +4.5 sigma detection
        for idx in range(20):
            self.process_message_create_event(
                {
                    "id": f"dry-filler-{idx}",
                    "channel_id": first_binding.channel_id,
                    "author": {"username": f"BleacherScout{idx}"},
                    "content": f"Watching {first_binding.game_id} live play by play snap {idx} on 2nd down",
                    "timestamp": "2026-10-17T18:20:00Z",
                },
                now_epoch=base_epoch + idx * 0.5,
            )
        for idx in range(6):
            self.process_message_create_event(
                {
                    "id": f"dry-burst-{idx}",
                    "channel_id": first_binding.channel_id,
                    "author": {"username": f"CougarBoardSicko{idx}"},
                    "content": f"<@123456789> <:cougar:987654> Provo dorm soaking and quaking alert #{idx}!",
                    "timestamp": "2026-10-17T18:20:15Z",
                },
                now_epoch=base_epoch + 12.0 + idx * 0.4,
            )
        for idx in range(3):
            self.process_message_create_event(
                {
                    "id": f"dry-unmapped-{idx}",
                    "channel_id": "999999999999999999",
                    "author": {"username": "RogueUnmappedUser"},
                    "content": "This unmapped channel message must never bleed into active games!",
                },
                now_epoch=base_epoch + 15.0 + idx,
            )

        summary = {
            "status": "DRY_RUN_VERIFIED",
            "auth_mode": self.auth_mode,
            "gateway_probe": gateway_probe_status,
            "gateway_url": discovered_url,
            "db_writes_executed": self.writer.rows_written,
            "mapped_channels": [dataclasses.asdict(b) for b in self.bindings.values()],
            "lexicon_shibboleths_loaded": len(self.burst_gate.lexicon),
            "synthetic_messages_ingested": self.ingested_count,
            "unmapped_messages_rejected": self.ignored_unmapped_count,
            "burst_alerts_emitted": [b.to_dict() for b in self.emitted_bursts],
        }
        return summary

    async def run_gateway_forever(self) -> None:
        """Connects to Discord Gateway v10 with exponential jittered backoff and hard 4-hour TTL."""
        if self.dry_run:
            report = self.run_dry_run_diagnostic()
            print(json.dumps(report, indent=2), flush=True)
            return

        if not self.bot_token and not self.user_token:
            raise RuntimeError(
                "Live Gateway mode requires DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN (or --dry-run)."
            )

        for binding in self.bindings.values():
            register_discord_stream_binding(self.db_path, binding, is_live=1)
            print(
                f"[DISCORD-TAILER] Bound channel_id={binding.channel_id} -> "
                f"game_id={binding.game_id} (stream_id={binding.stream_id})",
                flush=True,
            )

        writer_task = asyncio.create_task(self.writer.run_writer_loop())
        start_monotonic = time.monotonic()
        attempt = 0

        try:
            timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=90)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                while not self._stop_event.is_set():
                    elapsed = time.monotonic() - start_monotonic
                    if elapsed >= self.ttl_seconds:
                        print(
                            f"[DISCORD-TAILER] Reached hard TTL ({self.ttl_seconds}s). Terminating cleanly.",
                            flush=True,
                        )
                        break

                    ws_url = self._resume_gateway_url or self.gateway_url
                    try:
                        async with session.ws_connect(ws_url, heartbeat=None, max_msg_size=4 * 1024 * 1024) as ws:
                            attempt = 0
                            self._last_heartbeat_ack = True
                            heartbeat_task: Optional[asyncio.Task[None]] = None

                            async for msg in ws:
                                if self._stop_event.is_set() or (
                                    time.monotonic() - start_monotonic >= self.ttl_seconds
                                ):
                                    break
                                if msg.type != aiohttp.WSMsgType.TEXT:
                                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                        break
                                    continue

                                packet = json.loads(msg.data)
                                op = packet.get("op")
                                data = packet.get("d")
                                seq = packet.get("s")
                                event_name = packet.get("t")

                                if seq is not None:
                                    self._seq = int(seq)

                                if op == 10:  # HELLO
                                    interval_ms = float((data or {}).get("heartbeat_interval", 41250))
                                    heartbeat_task = asyncio.create_task(
                                        self._heartbeat_loop(ws, interval_ms)
                                    )
                                    if self._session_id and self._seq is not None:
                                        token_val = self.bot_token or self.user_token or ""
                                        await ws.send_json(
                                            {
                                                "op": 6,
                                                "d": {
                                                    "token": token_val,
                                                    "session_id": self._session_id,
                                                    "seq": self._seq,
                                                },
                                            }
                                        )
                                    else:
                                        await ws.send_json(self.build_identify_payload())

                                elif op == 11:  # HEARTBEAT_ACK
                                    self._last_heartbeat_ack = True

                                elif op == 1:  # Server requested immediate HEARTBEAT
                                    await ws.send_json({"op": 1, "d": self._seq})

                                elif op == 7:  # RECONNECT
                                    print("[DISCORD-TAILER] Gateway requested Op 7 RECONNECT.", flush=True)
                                    await ws.close()
                                    break

                                elif op == 9:  # INVALID_SESSION
                                    resumable = bool(data)
                                    if not resumable:
                                        self._session_id = None
                                        self._seq = None
                                    await asyncio.sleep(random.uniform(1.5, 4.0))
                                    await ws.close()
                                    break

                                elif op == 0:  # DISPATCH
                                    if event_name == "READY" and isinstance(data, dict):
                                        self._session_id = str(data.get("session_id") or "")
                                        resume_url = data.get("resume_gateway_url")
                                        if resume_url:
                                            self._resume_gateway_url = (
                                                f"{resume_url.rstrip('/')}/?v=10&encoding=json"
                                            )
                                        user_info = data.get("user") or {}
                                        print(
                                            f"[DISCORD-TAILER] Gateway READY as "
                                            f"{user_info.get('username', 'observer')} "
                                            f"(mode={self.auth_mode}, session={self._session_id[:10]}...)",
                                            flush=True,
                                        )
                                    elif event_name == "MESSAGE_CREATE" and isinstance(data, dict):
                                        outcome = self.process_message_create_event(data)
                                        if outcome is not None:
                                            record, _, alerts = outcome
                                            await self.writer.msg_queue.put(record)
                                            for alert in alerts:
                                                await self.writer.alert_queue.put(alert)

                            if heartbeat_task and not heartbeat_task.done():
                                heartbeat_task.cancel()

                    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                        attempt += 1
                        cap = min(30.0, 1.0 * (2 ** min(attempt, 5)))
                        sleep_s = random.uniform(cap * 0.5, cap)
                        print(
                            f"[DISCORD-TAILER] Gateway socket error ({exc}). Backing off {sleep_s:.2f}s...",
                            flush=True,
                        )
                        await asyncio.sleep(sleep_s)
        finally:
            await self.writer.msg_queue.put(None)
            await writer_task
            if not self.dry_run:
                for binding in self.bindings.values():
                    register_discord_stream_binding(self.db_path, binding, is_live=0)

def parse_bindings_from_args(args: argparse.Namespace) -> Dict[str, ChannelEntityBinding]:
    bindings: Dict[str, ChannelEntityBinding] = {}
    if args.channel_id and args.attach_game:
        stream_id = args.stream_id or f"discord_{args.channel_id}"
        bindings[str(args.channel_id)] = ChannelEntityBinding(
            channel_id=str(args.channel_id),
            game_id=str(args.attach_game),
            stream_id=str(stream_id),
            sport=str(args.sport or "cfb"),
            home_team=str(args.home or "HOME"),
            away_team=str(args.away or "AWAY"),
            stream_title=str(args.title or f"Discord #{args.channel_id} ({args.attach_game})"),
        )
    for spec in args.map or []:
        parts = [p.strip() for p in spec.split(":") if p.strip()]
        if len(parts) < 2:
            raise ValueError(f"Invalid --map '{spec}'. Expected <channel_id>:<game_id>[:<stream_id>].")
        ch_id = parts[0]
        g_id = parts[1]
        st_id = parts[2] if len(parts) >= 3 else f"discord_{ch_id}"
        bindings[ch_id] = ChannelEntityBinding(
            channel_id=ch_id,
            game_id=g_id,
            stream_id=st_id,
            sport=str(args.sport or "cfb"),
            home_team=str(args.home or "HOME"),
            away_team=str(args.away or "AWAY"),
            stream_title=f"Discord #{ch_id} ({g_id})",
        )
    return bindings

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StackLabs FaaS Discord Gateway v10 Stream Tailer & Statistical Burst Ingress"
    )
    parser.add_argument("--channel-id", dest="channel_id", help="Discord channel ID to subscribe")
    parser.add_argument(
        "--attach-game",
        dest="attach_game",
        help="Canonical game_id / channel_key to tag all messages from this channel",
    )
    parser.add_argument(
        "--stream-id",
        dest="stream_id",
        help="Explicit stream_id tag (defaults to discord_<channel_id>)",
    )
    parser.add_argument(
        "--map",
        action="append",
        help="Additional channel mapping in format <channel_id>:<game_id>[:<stream_id>]",
    )
    parser.add_argument("--sport", default="cfb", help="Sport code (cfb, nfl, mlb)")
    parser.add_argument("--home", default="HOME", help="Home team abbreviation")
    parser.add_argument("--away", default="AWAY", help="Away team abbreviation")
    parser.add_argument("--title", default=None, help="Human-readable stream title")
    parser.add_argument(
        "--bot-token",
        dest="bot_token",
        default=None,
        help="Discord Bot Token (defaults to DISCORD_BOT_TOKEN env var)",
    )
    parser.add_argument(
        "--user-token",
        dest="user_token",
        default=None,
        help="Discord User Observer Token (defaults to DISCORD_USER_TOKEN env var)",
    )
    parser.add_argument(
        "--window-seconds",
        dest="window_seconds",
        type=float,
        default=60.0,
        help="Sliding ring-buffer window in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--sigma-threshold",
        dest="sigma_threshold",
        type=float,
        default=4.5,
        help="Z-score burst alert threshold (default: 4.5)",
    )
    parser.add_argument(
        "--ttl-seconds",
        dest="ttl_seconds",
        type=int,
        default=14400,
        help="Hard worker TTL in seconds (capped at 14400s / 4 hours per Argon Law 9)",
    )
    parser.add_argument(
        "--db-path",
        dest="db_path",
        default=str(DB_PATH),
        help="Path to SQLite WAL database (default: data/morning_wiretap.db)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Validate Gateway discovery, entity isolation, and +4.5 sigma burst logic without DB writes",
    )
    return parser

def main() -> None:
    load_dotenv_file(ENV_PATH)
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.dry_run and not args.channel_id and not args.map:
        args.channel_id = "1296543210987654321"
        args.attach_game = "ND_BYU"
        args.stream_id = "discord_cougarboard_live"

    bindings = parse_bindings_from_args(args)
    if not bindings:
        parser.error("Provide --channel-id <id> --attach-game <game_id> (or --map <ch>:<game>:<stream>).")

    bot_token = args.bot_token or os.getenv("DISCORD_BOT_TOKEN")
    user_token = args.user_token or os.getenv("DISCORD_USER_TOKEN")

    tailer = DiscordGatewayStreamTailer(
        bindings=bindings,
        db_path=Path(args.db_path),
        bot_token=bot_token,
        user_token=user_token,
        window_seconds=args.window_seconds,
        sigma_threshold=args.sigma_threshold,
        ttl_seconds=args.ttl_seconds,
        dry_run=args.dry_run,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, tailer._stop_event.set)
        except NotImplementedError:
            pass
    try:
        loop.run_until_complete(tailer.run_gateway_forever())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
