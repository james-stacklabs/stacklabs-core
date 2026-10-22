#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs ServiceNow Cloud PDI — Content-Addressable Merkle Delta Sync Engine
Location: /home/james/stacklabs/scripts/servicenow_sync_engine.py

Replaces legacy brute-force seeders (`seed_servicenow_degenerate_cmdb.py`,
`seed_servicenow_grounded_cmdb.py`, `servicenow_bridge.py`, and
`clean_servicenow_pdi_bots.py`) with a unified, sub-second Content-Addressable
Merkle Delta Sync Engine backed by a local SQLite WAL state cache
(`data/servicenow_pdi_cache.db`).

Key Architectural Capabilities:
1. Local SQLite WAL Cache (`sn_ci_cache`, `sn_rel_cache`, `sn_sync_runs`):
   Eliminates cold remote paged GET scans across 2,000+ CIs on every invocation.
2. Content-Addressable SHA-256 Merkle Hashing:
   Normalizes CI and relationship payloads into canonical JSON, computes
   deterministic SHA-256 digests and an epoch Merkle root, and skips un-mutated
   records with 0 network calls and sub-millisecond local evaluation.
3. Adaptive Concurrency & Jittered Exponential Backoff:
   Replaces the 16-thread connection barrage with a persistent, connection-pooled
   4-6 worker pool (`AdaptiveServiceNowClient`) with AIMD rate-limiting and
   Retry-After-aware exponential backoff on HTTP 429, 502, 503, and 504.
4. Unified Harvesting & Hygiene:
   Reconciles Enterprise ITSM infrastructure CIs, physical/logical host topology,
   Broadcast Pantheon nodes, Emergent Society ledgers, Game Room episodes, and
   Morning Wiretap stream tails while pruning empty staged room shells and
   synthetic bot relics.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import glob
import hashlib
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import requests
from requests.adapters import HTTPAdapter

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


# =============================================================================
# 1. PATHS, ENVIRONMENT & CONSTANTS
# =============================================================================

ROOT_DIR = Path(os.environ.get("STACKLABS_ROOT", "/home/james/stacklabs"))
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
DNA_DIR = ROOT_DIR / "dna"
PUBLIC_DIR = ROOT_DIR / "apps" / "cmdb_studio" / "public"
DIST_DIR = ROOT_DIR / "apps" / "cmdb_studio" / "dist"
TELEMETRY_DIR = DATA_DIR / "telemetry"

DEFAULT_CACHE_DB = Path(
    os.environ.get("SN_CACHE_DB", str(DATA_DIR / "servicenow_pdi_cache.db"))
)
LOCAL_CMDB_DB = DNA_DIR / ("sovereign" + "_now.db")
EMERGENT_DB = DATA_DIR / "emergent_society.db"
WIRETAP_DB = DATA_DIR / "morning_wiretap.db"
LABELED_LOGS_DIR = DATA_DIR / "labeled_logs"
NEEDLE_GOLD_PATH = TELEMETRY_DIR / "authentic_sports_gold.json"
TOXIC_GRAPH_PATH = DATA_DIR / "toxic_comment_cmdb_graph.json"
BARF_WIRE_PATH = DATA_DIR / "barf_wire_payload.json"
SPORTS_CAUSAL_INDEX = DATA_DIR / "sports_causal_index.json"
BRAIN_GLOB = "/home/james/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl"
CRED_PATH = DNA_DIR / "vault" / "sn_credentials.json"

VFS_CMDB_PERSIST = ROOT_DIR / "vfs" / "cmdb"
VFS_CMDB_SHM = Path("/dev/shm/faas_vfs/cmdb")

CI_JSON_PATHS = [
    DATA_DIR / "fanstack_cmdb_ci.json",
    PUBLIC_DIR / "fanstack_cmdb_ci.json",
    DATA_DIR / "sports_cmdb_ci.json",
    PUBLIC_DIR / "sports_cmdb_ci.json",
]
REL_JSON_PATHS = [
    DATA_DIR / "fanstack_cmdb_rel_ci.json",
    PUBLIC_DIR / "fanstack_cmdb_rel_ci.json",
    DATA_DIR / "sports_cmdb_rel_ci.json",
    PUBLIC_DIR / "sports_cmdb_rel_ci.json",
]

REL_TYPE_SYS_ID = "015633570a0a0bc70029121512d46ede"  # Depends on::Used by
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

BANNED_NAME_TOKENS = (
    "mean_gene",
    "battery_chucker",
    "battery_chucker_jr",
    "unclesteviestan",
    "keith_fanboy",
    "the_chop_shop",
    "zork_rpg",
    "bleed_the_skew",
    "tva_001",
    "tva_002",
    "spreadsheets_on_fire",
    "conspiracy_tmi",
    "cypher_cell",
    "cypher_escape",
    "burn_823",
)

BANNED_CLASSES = {
    "cmdb_ci_tmi_scenario",
    "cmdb_ci_penalty_log",
    "cmdb_ci_burn_event",
}

PRESERVED_NAMES = {
    "sap_web01",
    "db_cluster01",
    "core_switch_alpha",
    "clio",
    "artemis",
    "pegasus",
    "argo",
    "c120",
    "faas_server",
    "stacklabs_retina",
    "stream_sniper",
    "clio_queue_watcher",
    "hero_pat_mcafee",
    "hero_aj_hawk",
    "hero_john_harbaugh_nyg",
    "villain_jerry_sun_glare_cap",
    "villain_daboll_titans_exile",
    "vitals_barf_bp_178_112",
    "villain_billy_napier_hot_seat",
    "villain_stearns_fleece_spreadsheet",
    "villain_animal_style_ump_cartel",
    "hero_nick_saban_alpha",
    "hero_ty_schmit_lou_holtz",
    "hero_jackson_chourio_walkoff",
    "hero_sammy_the_savant",
    "conspiracy_att_west_window_glare",
    "conspiracy_wisconsin_faustian_barter",
}

PRESERVED_CLASSES = {
    "cmdb_ci_appl",
    "cmdb_ci_db_instance",
    "cmdb_ci_ip_switch",
    "cmdb_ci_linux_server",
    "cmdb_ci_server",
    "cmdb_ci_hardware",
    "cmdb_ci_network_adapter",
}

logging.basicConfig(
    level=logging.INFO,
    format="[SN-DELTA-SYNC] %(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("servicenow_sync_engine")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_sys_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def make_reg_id(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def resolve_credentials() -> Tuple[str, str, str]:
    """Resolve ServiceNow instance URL, username, and password from env or vault."""
    instance = (
        os.environ.get("SN_INSTANCE")
        or os.environ.get("SERVICENOW_INSTANCE")
        or ""
    ).strip()
    user = (
        os.environ.get("SN_USER")
        or os.environ.get("SERVICENOW_USER")
        or ""
    ).strip()
    password = (
        os.environ.get("SN_PASS")
        or os.environ.get("SERVICENOW_PASSWORD")
        or ""
    ).strip()

    if (not instance or not user or not password) and CRED_PATH.exists():
        try:
            creds = json.loads(CRED_PATH.read_text(encoding="utf-8"))
            if not instance and creds.get("instance"):
                inst_val = str(creds["instance"]).strip()
                instance = (
                    inst_val
                    if inst_val.startswith("http")
                    else f"https://{inst_val}.service-now.com"
                )
            if not user and creds.get("username"):
                user = str(creds["username"]).strip()
            if (
                not password
                and creds.get("password")
                and creds.get("password") != "<PASTE_PASSWORD_HERE>"
            ):
                password = str(creds["password"]).strip()
        except Exception as exc:
            logger.warning("Failed reading credentials vault %s: %s", CRED_PATH, exc)

    instance = (instance or "https://dev186522.service-now.com").rstrip("/")
    user = user or "admin"
    password = password or "J-Slf7SPmg!2"
    return instance, user, password


# =============================================================================
# 2. CONTENT-ADDRESSABLE MERKLE HASHING & PAYLOAD NORMALIZATION
# =============================================================================


def build_canonical_ci_payload(ci: Dict[str, Any]) -> Dict[str, str]:
    """
    Construct the exact canonical ServiceNow REST payload for a CI record.
    Sorting keys and stripping trailing whitespace guarantees deterministic
    SHA-256 digests across runs.
    """
    ci_key = str(ci.get("ci_key") or ci.get("name") or "").strip()
    sys_class_name = str(ci.get("sys_class_name") or "cmdb_ci").strip()
    layer_label = str(
        ci.get("layer_label") or ci.get("layer") or ci.get("category") or "StackLabs"
    ).strip()
    reg_id = str(ci.get("state_register_id") or make_reg_id(ci_key)).strip()
    display_title = str(ci.get("display_title") or ci_key).strip()
    raw_short_desc = str(ci.get("short_description") or "").strip()

    if raw_short_desc.startswith(f"[{sys_class_name}"):
        formatted_desc = raw_short_desc[:395]
    else:
        formatted_desc = (
            f"[{sys_class_name} | {layer_label} | reg={reg_id}] "
            f"{display_title} — {raw_short_desc}"
        ).strip(" —")[:395]

    correlation_id = str(ci.get("sys_id") or make_sys_id(ci_key)).strip()
    install_status = str(ci.get("install_status") or "1").strip()
    op_raw = str(ci.get("operational_status") or "1").strip()
    operational_status = "1" if op_raw in ("1", "Operational", "ACTIVE", "ONLINE") else op_raw[:40]

    return {
        "install_status": install_status,
        "name": ci_key,
        "operational_status": operational_status,
        "short_description": formatted_desc,
        "sys_class_name": sys_class_name,
        "u_correlation_id": correlation_id,
    }


def compute_canonical_sha256(payload: Dict[str, Any]) -> str:
    """Compute SHA-256 over normalized, sorted-key compact JSON representation."""
    canonical_bytes = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_merkle_root(leaf_hashes: Sequence[str]) -> str:
    """
    Build a binary Merkle root over sorted leaf SHA-256 hashes.
    Allows O(1) epoch equality verification across the entire CMDB state plane.
    """
    if not leaf_hashes:
        return hashlib.sha256(b"EMPTY_MERKLE_TREE").hexdigest()

    layer = sorted(leaf_hashes)
    while len(layer) > 1:
        next_layer: List[str] = []
        for idx in range(0, len(layer), 2):
            left = layer[idx]
            right = layer[idx + 1] if idx + 1 < len(layer) else left
            combined = hashlib.sha256(f"{left}:{right}".encode("utf-8")).hexdigest()
            next_layer.append(combined)
        layer = next_layer
    return layer[0]


# =============================================================================
# 3. LOCAL SQLITE WAL CACHE ENGINE (`data/servicenow_pdi_cache.db`)
# =============================================================================


@dataclass
class CachedCIRecord:
    ci_key: str
    sys_id: str
    sys_class_name: str
    content_sha256: str
    last_synced_at: str


@dataclass
class CachedRelRecord:
    parent_key: str
    child_key: str
    type_sys_id: str
    sys_id: str
    content_sha256: str
    last_synced_at: str


@dataclass
class DeltaPlan:
    merkle_root: str
    previous_merkle_root: Optional[str]
    total_local_cis: int
    total_local_rels: int
    ci_creates: List[Tuple[Dict[str, Any], Dict[str, str], str]] = field(default_factory=list)
    ci_updates: List[Tuple[Dict[str, Any], Dict[str, str], str, str]] = field(default_factory=list)
    ci_skips: int = 0
    ci_prunes: List[Tuple[str, str, str]] = field(default_factory=list)
    rel_creates: List[Tuple[str, str, str, str]] = field(default_factory=list)
    rel_skips: int = 0
    rel_prunes: List[Tuple[str, str, str, str]] = field(default_factory=list)
    delta_compute_ms: float = 0.0


class LocalSQLiteWALCache:
    """
    High-concurrency local SQLite WAL cache storing known remote ServiceNow state.
    Eliminates cold remote paged GET scans on incremental sync invocations.
    """

    def __init__(self, db_path: Path = DEFAULT_CACHE_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sn_ci_cache (
                    ci_key TEXT PRIMARY KEY,
                    sys_id TEXT NOT NULL,
                    sys_class_name TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    payload_json TEXT,
                    last_synced_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sn_ci_cache_sys_id
                    ON sn_ci_cache(sys_id);

                CREATE TABLE IF NOT EXISTS sn_rel_cache (
                    parent_key TEXT NOT NULL,
                    child_key TEXT NOT NULL,
                    type_sys_id TEXT NOT NULL,
                    sys_id TEXT,
                    content_sha256 TEXT,
                    last_synced_at TEXT NOT NULL,
                    PRIMARY KEY (parent_key, child_key, type_sys_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sn_rel_cache_sys_id
                    ON sn_rel_cache(sys_id);

                CREATE TABLE IF NOT EXISTS sn_sync_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    merkle_root TEXT NOT NULL,
                    total_cis INTEGER NOT NULL,
                    ci_created INTEGER NOT NULL,
                    ci_updated INTEGER NOT NULL,
                    ci_skipped INTEGER NOT NULL,
                    ci_pruned INTEGER NOT NULL,
                    rel_created INTEGER NOT NULL,
                    rel_skipped INTEGER NOT NULL,
                    rel_pruned INTEGER NOT NULL,
                    http_requests INTEGER NOT NULL,
                    http_retries INTEGER NOT NULL,
                    elapsed_ms REAL NOT NULL
                );
                """
            )
            # Ensure forward-compatible columns if upgrading an older table
            ci_cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(sn_ci_cache)").fetchall()
            }
            if "payload_json" not in ci_cols:
                conn.execute("ALTER TABLE sn_ci_cache ADD COLUMN payload_json TEXT;")

            rel_cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(sn_rel_cache)").fetchall()
            }
            if "content_sha256" not in rel_cols:
                conn.execute("ALTER TABLE sn_rel_cache ADD COLUMN content_sha256 TEXT;")
            conn.commit()

    def load_ci_cache(self) -> Dict[str, CachedCIRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT ci_key, sys_id, sys_class_name, content_sha256, last_synced_at FROM sn_ci_cache"
            ).fetchall()
            return {
                r["ci_key"]: CachedCIRecord(
                    ci_key=r["ci_key"],
                    sys_id=r["sys_id"],
                    sys_class_name=r["sys_class_name"],
                    content_sha256=r["content_sha256"],
                    last_synced_at=r["last_synced_at"],
                )
                for r in rows
            }

    def load_rel_cache(self) -> Dict[Tuple[str, str, str], CachedRelRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT parent_key, child_key, type_sys_id, COALESCE(sys_id, '') AS sys_id,
                       COALESCE(content_sha256, '') AS content_sha256, last_synced_at
                FROM sn_rel_cache
                """
            ).fetchall()
            return {
                (r["parent_key"], r["child_key"], r["type_sys_id"]): CachedRelRecord(
                    parent_key=r["parent_key"],
                    child_key=r["child_key"],
                    type_sys_id=r["type_sys_id"],
                    sys_id=r["sys_id"],
                    content_sha256=r["content_sha256"],
                    last_synced_at=r["last_synced_at"],
                )
                for r in rows
            }

    def get_last_merkle_root(self) -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT merkle_root FROM sn_sync_runs ORDER BY run_id DESC LIMIT 1"
            ).fetchone()
            return str(row["merkle_root"]) if row else None

    def upsert_ci_batch(
        self, records: Sequence[Tuple[str, str, str, str, str, str]]
    ) -> None:
        """
        Atomically commit a batch of (ci_key, sys_id, sys_class_name, content_sha256, payload_json, last_synced_at).
        """
        if not records:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO sn_ci_cache (
                    ci_key, sys_id, sys_class_name, content_sha256, payload_json, last_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ci_key) DO UPDATE SET
                    sys_id = excluded.sys_id,
                    sys_class_name = excluded.sys_class_name,
                    content_sha256 = excluded.content_sha256,
                    payload_json = excluded.payload_json,
                    last_synced_at = excluded.last_synced_at
                """,
                records,
            )
            conn.commit()

    def delete_ci_keys(self, ci_keys: Sequence[str]) -> None:
        if not ci_keys:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                "DELETE FROM sn_ci_cache WHERE ci_key = ?",
                [(k,) for k in ci_keys],
            )
            conn.commit()

    def upsert_rel_batch(
        self, records: Sequence[Tuple[str, str, str, str, str, str]]
    ) -> None:
        """
        Atomically commit a batch of (parent_key, child_key, type_sys_id, sys_id, content_sha256, last_synced_at).
        """
        if not records:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO sn_rel_cache (
                    parent_key, child_key, type_sys_id, sys_id, content_sha256, last_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(parent_key, child_key, type_sys_id) DO UPDATE SET
                    sys_id = excluded.sys_id,
                    content_sha256 = excluded.content_sha256,
                    last_synced_at = excluded.last_synced_at
                """,
                records,
            )
            conn.commit()

    def delete_rel_keys(self, rel_keys: Sequence[Tuple[str, str, str]]) -> None:
        if not rel_keys:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                "DELETE FROM sn_rel_cache WHERE parent_key = ? AND child_key = ? AND type_sys_id = ?",
                rel_keys,
            )
            conn.commit()

    def record_sync_run(
        self,
        started_at: str,
        completed_at: str,
        mode: str,
        merkle_root: str,
        total_cis: int,
        ci_created: int,
        ci_updated: int,
        ci_skipped: int,
        ci_pruned: int,
        rel_created: int,
        rel_skipped: int,
        rel_pruned: int,
        http_requests: int,
        http_retries: int,
        elapsed_ms: float,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sn_sync_runs (
                    started_at, completed_at, mode, merkle_root, total_cis,
                    ci_created, ci_updated, ci_skipped, ci_pruned,
                    rel_created, rel_skipped, rel_pruned,
                    http_requests, http_retries, elapsed_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started_at,
                    completed_at,
                    mode,
                    merkle_root,
                    total_cis,
                    ci_created,
                    ci_updated,
                    ci_skipped,
                    ci_pruned,
                    rel_created,
                    rel_skipped,
                    rel_pruned,
                    http_requests,
                    http_retries,
                    elapsed_ms,
                ),
            )
            conn.commit()


# =============================================================================
# 4. ADAPTIVE CONCURRENCY, CONNECTION POOLING & EXPONENTIAL BACKOFF
# =============================================================================


class AdaptiveThrottleGate:
    """
    Thread-safe AIMD (Additive Increase / Multiplicative Decrease) rate controller.
    When ServiceNow PDI returns HTTP 429/503/504, all worker threads respect a
    shared cooldown window and inter-request pacing dynamically widens.
    Consecutive clean responses smoothly decay the pacing back to 0 ms.
    """

    def __init__(
        self,
        initial_delay_s: float = 0.0,
        max_delay_s: float = 2.5,
    ) -> None:
        self._lock = threading.Lock()
        self.current_delay_s = initial_delay_s
        self.max_delay_s = max_delay_s
        self.cooldown_until = 0.0
        self.throttle_events = 0
        self.clean_streak = 0

    def wait_before_request(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_s = max(0.0, self.cooldown_until - now) + self.current_delay_s
            if self.current_delay_s > 0:
                self.cooldown_until = max(self.cooldown_until, now + wait_s)
        if wait_s > 0:
            time.sleep(wait_s)

    def record_success(self) -> None:
        with self._lock:
            self.clean_streak += 1
            if self.clean_streak >= 12 and self.current_delay_s > 0:
                self.current_delay_s = max(0.0, self.current_delay_s * 0.75 - 0.005)
                self.clean_streak = 0

    def record_throttle(self, retry_after_s: Optional[float] = None) -> float:
        with self._lock:
            self.throttle_events += 1
            self.clean_streak = 0
            self.current_delay_s = min(
                self.max_delay_s,
                max(0.08, self.current_delay_s * 2.0 + 0.05),
            )
            penalty = retry_after_s if retry_after_s is not None else self.current_delay_s
            now = time.monotonic()
            self.cooldown_until = max(self.cooldown_until, now + penalty)
            return penalty


class AdaptiveServiceNowClient:
    """
    Connection-pooled ServiceNow REST client with adaptive worker concurrency (4-6 workers)
    and full-jitter exponential backoff on HTTP 429, 502, 503, and 504.
    """

    def __init__(
        self,
        instance_url: str,
        username: str,
        password: str,
        max_workers: int = 5,
        max_retries: int = 5,
        base_backoff_s: float = 0.4,
        max_backoff_s: float = 12.0,
        timeout_s: float = 15.0,
        transport_override: Optional[Callable[[str, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]], requests.Response]] = None,
    ) -> None:
        self.instance_url = instance_url.rstrip("/")
        self.max_workers = max(1, min(int(max_workers), 6))
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.timeout_s = timeout_s
        self.transport_override = transport_override

        self.throttle_gate = AdaptiveThrottleGate()
        self._metrics_lock = threading.Lock()
        self.http_requests = 0
        self.http_retries = 0
        self.status_429_count = 0
        self.status_5xx_count = 0

        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "StackLabs-Merkle-Delta-Sync/2.0",
            }
        )
        adapter = HTTPAdapter(
            pool_connections=self.max_workers + 2,
            pool_maxsize=self.max_workers + 4,
            max_retries=0,  # Managed explicitly by our jittered backoff loop
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _parse_retry_after(self, resp: requests.Response) -> Optional[float]:
        header_val = resp.headers.get("Retry-After")
        if not header_val:
            return None
        try:
            return max(0.1, min(float(header_val), self.max_backoff_s))
        except ValueError:
            return None

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        url = f"{self.instance_url}{path}" if path.startswith("/") else path
        attempt = 0

        while True:
            self.throttle_gate.wait_before_request()
            with self._metrics_lock:
                self.http_requests += 1

            try:
                if self.transport_override is not None:
                    resp = self.transport_override(method, url, params, json_payload)
                else:
                    resp = self.session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_payload,
                        timeout=self.timeout_s,
                    )
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise
                attempt += 1
                with self._metrics_lock:
                    self.http_retries += 1
                self.throttle_gate.record_throttle()
                cap = min(self.max_backoff_s, self.base_backoff_s * (2 ** (attempt - 1)))
                sleep_s = random.uniform(cap * 0.5, cap)
                logger.warning(
                    "Transient socket error on %s %s (%s). Retry %d/%d in %.2fs",
                    method,
                    path,
                    exc,
                    attempt,
                    self.max_retries,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue

            if resp.status_code in RETRYABLE_STATUS_CODES:
                with self._metrics_lock:
                    if resp.status_code == 429:
                        self.status_429_count += 1
                    else:
                        self.status_5xx_count += 1

                if attempt >= self.max_retries:
                    return resp

                attempt += 1
                with self._metrics_lock:
                    self.http_retries += 1

                retry_after = self._parse_retry_after(resp)
                self.throttle_gate.record_throttle(retry_after)
                cap = min(self.max_backoff_s, self.base_backoff_s * (2 ** (attempt - 1)))
                sleep_s = retry_after if retry_after is not None else random.uniform(cap * 0.5, cap)
                logger.warning(
                    "HTTP %d on %s %s. Adaptive backoff retry %d/%d in %.2fs",
                    resp.status_code,
                    method,
                    path,
                    attempt,
                    self.max_retries,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue

            self.throttle_gate.record_success()
            return resp

    def fetch_paged_table(
        self,
        table: str,
        fields: str,
        page_size: int = 500,
    ) -> List[Dict[str, Any]]:
        """Fetch all records from a ServiceNow table using adaptive pagination."""
        records: List[Dict[str, Any]] = []
        offset = 0
        while True:
            resp = self.request(
                "GET",
                f"/api/now/table/{table}",
                params={
                    "sysparm_fields": fields,
                    "sysparm_limit": str(page_size),
                    "sysparm_offset": str(offset),
                },
            )
            if resp.status_code != 200:
                logger.error(
                    "Paged GET failed on %s at offset %d: HTTP %d",
                    table,
                    offset,
                    resp.status_code,
                )
                break
            batch = resp.json().get("result", [])
            if not batch:
                break
            records.extend(batch)
            if len(batch) < page_size:
                break
            offset += len(batch)
        return records

    def fetch_table_count(self, table: str) -> Optional[int]:
        try:
            resp = self.request(
                "GET",
                f"/api/now/stats/{table}",
                params={"sysparm_count": "true"},
            )
            if resp.status_code == 200:
                return int(
                    resp.json().get("result", {}).get("stats", {}).get("count", 0)
                )
        except Exception as exc:
            logger.debug("Stats query failed on %s: %s", table, exc)
        return None


# =============================================================================
# 5. BOT & ORPHAN HYGIENE CLASSIFIER
# =============================================================================


def classify_prune_candidate(
    ci: Dict[str, Any],
    referenced_rooms: Optional[Set[str]] = None,
) -> Tuple[bool, str]:
    """
    Determine whether a CI should be pruned (synthetic bot persona, banned TMI/burn
    table relic, or unreferenced staged room shell).
    """
    name = str(ci.get("ci_key") or ci.get("name") or "").strip()
    name_low = name.lower()
    sys_id = str(ci.get("sys_id") or "").strip()
    s_class = str(ci.get("sys_class_name") or "").strip()
    title_low = str(ci.get("short_description") or ci.get("display_title") or "").lower()

    if name_low in PRESERVED_NAMES or sys_id in PRESERVED_NAMES:
        return False, "PRESERVED_NAME"
    if s_class in PRESERVED_CLASSES:
        return False, "PRESERVED_CLASS"

    if s_class in BANNED_CLASSES:
        return True, f"BANNED_CLASS_{s_class}"

    if re.match(r"^room_\d+$", name_low) or s_class == "cmdb_ci_fanstack_room":
        if referenced_rooms is not None:
            gpk_room = f"room_{ci.get('game_pk')}" if ci.get("game_pk") else name_low
            if name not in referenced_rooms and name_low not in referenced_rooms and gpk_room not in referenced_rooms:
                return True, "EMPTY_STAGED_ROOM"
        elif re.match(r"^room_\d+$", name_low):
            return True, "EMPTY_STAGED_ROOM"

    for token in BANNED_NAME_TOKENS:
        if token == name_low or f"_{token}" in name_low:
            return True, f"BANNED_TOKEN_{token}"

    if name_low == "dot" or name_low.startswith("dot_"):
        return True, "BANNED_DOT_PERSONA"

    if "cypher escape" in title_low or "total cypher" in title_low:
        return True, "CYPHER_LORE_IN_TITLE"

    return False, "OK"


# =============================================================================
# 6. UNIFIED MULTI-SOURCE CMDB HARVESTER
# =============================================================================


def harvest_ide_brain_barf_tweets(max_items: int = 35) -> List[Dict[str, str]]:
    """Scan local IDE brain transcripts for @BarfFanStack tweets and YouTube comments."""
    results: List[Dict[str, str]] = []
    seen_prefixes: Set[str] = set()
    files = sorted(glob.glob(BRAIN_GLOB), key=os.path.getmtime, reverse=True)
    for fpath in files:
        conv_id = Path(fpath).parent.parent.name[:8]
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if not any(
                        k in line
                        for k in ("@TheWardyNYM", "@BarfFanStack", "Barf", "Shapiro", "Daboll", "Soto")
                    ):
                        continue
                    for match in re.finditer(
                        r"([A-Z0-9][^\n\"\\]{40,260}(?:#LGM|@TheWardyNYM|#LFGM|#NYG|#Giants|Shapiro|pastrami|Daboll|Mendoza|Stearns)[^\n\"\\]{0,80})",
                        line,
                    ):
                        clean = re.sub(r"\s+", " ", match.group(1)).strip()
                        sig = clean[:45].lower()
                        if sig not in seen_prefixes and len(clean) >= 45:
                            seen_prefixes.add(sig)
                            results.append({"text": clean[:280], "source": f"IDE_Brain_{conv_id}"})
                            if len(results) >= max_items:
                                return results
        except Exception:
            continue
    return results


def build_enterprise_and_host_topology() -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    """
    Build grounded Enterprise ITSM CIs (`sap_web01`, `db_cluster01`, `core_switch_alpha`)
    and local host/service CIs (`clio`, `artemis`, `pegasus`, `argo`, `c120`, `faas_server`, etc.).
    """
    cis: List[Dict[str, Any]] = []
    edges: List[Tuple[str, str, str]] = []

    def _node(
        ci_key: str,
        sys_class_name: str,
        layer_label: str,
        display_title: str,
        short_desc: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            "sys_id": make_sys_id(ci_key),
            "ci_key": ci_key,
            "name": ci_key,
            "display_title": display_title[:160],
            "sys_class_name": sys_class_name,
            "layer_label": layer_label,
            "short_description": short_desc[:360],
            "state_register_id": make_reg_id(ci_key),
            "install_status": "1",
            "operational_status": "1",
        }
        if extra:
            record.update(extra)
        return record

    # Enterprise ITSM Anchor CIs
    cis.extend(
        [
            _node(
                "sap_web01",
                "cmdb_ci_appl",
                "Layer 0: Enterprise ITSM Core",
                "SAP Enterprise Services Web App Server 01 (sap_web01)",
                "Enterprise ServiceNow PDI primary web application CI backing sap_enterprise_services.",
                {"category": "Enterprise ITSM"},
            ),
            _node(
                "db_cluster01",
                "cmdb_ci_db_instance",
                "Layer 0: Enterprise ITSM Core",
                "Enterprise Primary Database Cluster 01 (db_cluster01)",
                "Enterprise ServiceNow PDI high-availability database cluster backing SAP Enterprise Services.",
                {"category": "Enterprise ITSM"},
            ),
            _node(
                "core_switch_alpha",
                "cmdb_ci_ip_switch",
                "Layer 0: Enterprise ITSM Core",
                "Core Distribution Switch Alpha (core_switch_alpha)",
                "Enterprise ServiceNow PDI top-of-rack core network switch serving SAP Enterprise Services.",
                {"category": "Enterprise ITSM"},
            ),
        ]
    )
    edges.extend(
        [
            ("sap_web01", "db_cluster01", "Depends on::Used by"),
            ("sap_web01", "core_switch_alpha", "Connected to::Connects"),
        ]
    )

    # Physical & Logical Fleet Topology (aligned with VFS and IRE)
    fleet_nodes = [
        (
            "clio",
            "cmdb_ci_linux_server",
            "Layer 0: Dedicated Linux Host Fleet",
            "Clio Primary Linux Host (100.73.155.70 • 32GB RAM • 1TB NVMe)",
            "Primary Linux workstation and service host running Ubuntu 24.04 LTS.",
            {"ip_address": "100.73.155.70", "lan_ip": "192.168.1.183", "ram_gb": 32},
        ),
        (
            "artemis",
            "cmdb_ci_server",
            "Layer 0: Dedicated Linux Host Fleet",
            "Artemis CUDA Transcode & Field Node (100.108.185.53 • GTX 1060 6GB)",
            "Dedicated CUDA transcode and standby compute host.",
            {"ip_address": "100.108.185.53", "lan_ip": "192.168.1.64", "vram_mb": 6144},
        ),
        (
            "pegasus",
            "cmdb_ci_server",
            "Layer 0: Dedicated Linux Host Fleet",
            "Pegasus Headless Visual Sentry & Terminal (100.96.77.20)",
            "Dedicated visual sentry and display terminal node.",
            {"ip_address": "100.96.77.20", "lan_ip": "192.168.1.200"},
        ),
        (
            "argo",
            "cmdb_ci_hardware",
            "Layer 0: Dedicated Linux Host Fleet",
            "Argo Vision & Audio Sensor Sentry (100.111.248.60 • Hailo-8L NPU)",
            "Real-time optical and acoustic sensor sentry node.",
            {"ip_address": "100.111.248.60"},
        ),
        (
            "c120",
            "cmdb_ci_hardware",
            "Layer 0: Dedicated Linux Host Fleet",
            "Tapo C120 Optical Stream Sentry (192.168.1.191 • 1080p RTSP)",
            "Local RTSP optical ingress camera feeding stacklabs_retina.",
            {"ip_address": "192.168.1.191"},
        ),
        (
            "faas_server",
            "cmdb_ci_appl",
            "Layer 0: Active Service Daemons",
            "FanStack as a Service Daemon (faas_server.service • Port 3033)",
            "Primary Starlette HTTP/1.1 + VFS service daemon on Port 3033.",
            {"port": "3033", "internal_port": "3032"},
        ),
        (
            "stacklabs_retina",
            "cmdb_ci_appl",
            "Layer 0: Active Service Daemons",
            "StackLabs Retina MJPEG Stream Service (Port 3028)",
            "HTTP/1.1 MJPEG multipart optical stream relay on Port 3028.",
            {"port": "3028"},
        ),
        (
            "stream_sniper",
            "cmdb_ci_appl",
            "Layer 0: Active Service Daemons",
            "Stream Sniper Daemon (stream_sniper_daemon.service • Port 5056)",
            "Real-time live stream chat ingestion and spike detection daemon on Port 5056.",
            {"port": "5056"},
        ),
        (
            "clio_queue_watcher",
            "cmdb_ci_appl",
            "Layer 0: Active Service Daemons",
            "Clio Work Order Queue Watcher Daemon (clio_queue_watcher.service)",
            "Autonomous work order queue runner monitoring /home/james/stacklabs/queue.",
            {"runner": "agy"},
        ),
    ]
    for ck, cls, lyr, title, desc, ext in fleet_nodes:
        cis.append(_node(ck, cls, lyr, title, desc, ext))

    edges.extend(
        [
            ("faas_server", "clio", "Runs on::Runs"),
            ("stacklabs_retina", "clio", "Runs on::Runs"),
            ("stacklabs_retina", "c120", "Ingests from::Feeds"),
            ("stream_sniper", "clio", "Runs on::Runs"),
            ("stream_sniper", "artemis", "Transcribes on::Processes"),
            ("clio_queue_watcher", "clio", "Runs on::Runs"),
        ]
    )
    return cis, edges


def build_pantheon_and_episodes(
    include_enterprise_topology: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]], List[Dict[str, Any]]]:
    """
    Build the unified CMDB graph combining Enterprise ITSM anchors, Pantheon Heroes/Villains,
    Conspiracies, Biometric Vitals, Emergent Society DB, Broadcast Episodes, Game Room Episodes,
    and Morning Wiretap Stream Tails.
    """
    pantheon_cis: List[Dict[str, Any]] = []
    pantheon_edges: List[Tuple[str, str, str]] = []
    seen_keys: Set[str] = set()

    def add_node(
        ci_key: str,
        sys_class_name: str,
        layer_label: str,
        display_title: str,
        short_desc: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not ci_key or ci_key in seen_keys:
            return
        seen_keys.add(ci_key)
        node: Dict[str, Any] = {
            "sys_id": make_sys_id(ci_key),
            "ci_key": ci_key,
            "name": ci_key,
            "display_title": display_title[:160],
            "sys_class_name": sys_class_name,
            "layer_label": layer_label,
            "short_description": short_desc[:360],
            "state_register_id": make_reg_id(ci_key),
            "install_status": "1",
            "operational_status": "1",
        }
        if extra:
            node.update(extra)
        pantheon_cis.append(node)

    if include_enterprise_topology:
        ent_cis, ent_edges = build_enterprise_and_host_topology()
        for ec in ent_cis:
            add_node(
                ec["ci_key"],
                ec["sys_class_name"],
                ec["layer_label"],
                ec["display_title"],
                ec["short_description"],
                ec,
            )
        pantheon_edges.extend(ent_edges)

    # 1. Villains
    villains = [
        (
            "villain_jerry_sun_glare_cap",
            "Jerry Jones' AT&T West Window Sun Glare & $60M Salary Cap Myth",
            "NFL Villain CI: Refuses to hang $4,000 stadium curtains over the west end-zone glass while paying $60M/yr to get blown out at home.",
            {"sport": "NFL", "team": "DAL", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_daboll_titans_exile",
            "Brian Daboll's 0-3 Tennessee Titans Exile & MetLife Red-Zone Trauma",
            "NFL Villain CI: Fired by NYG in Nov 2025, exiled to Tennessee where the Titans sit 0-3 after losing 12-7 to John Harbaugh's Giants.",
            {"sport": "NFL", "team": "TEN_NYG", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_billy_napier_hot_seat",
            "Billy Napier's 45-17 Mizzou Blowout & 2-4 Gainesville Hot Seat",
            "CFB Villain CI: No. 8 Florida crushed 45-17 at unranked Missouri as the Gators' rushing attack vanishes and buyout boosters revolt.",
            {"sport": "CFB", "team": "FLA", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_hugh_freeze_second_half",
            "Hugh Freeze's Auburn 2nd-Half Offensive Shutout Vortex",
            "CFB Villain CI: Back-to-back SEC second-half offensive collapses leaving Auburn's fanbase in a state of mutiny.",
            {"sport": "CFB", "team": "AUB", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_unc_secondary_sieve",
            "North Carolina Secondary Sieve (Clemson 4 First-Quarter TDs)",
            "CFB Villain CI: Surrendered 4 passing touchdowns in the 1st quarter alone, driving Bill Belichick's blood pressure into orbit.",
            {"sport": "CFB", "team": "UNC", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_gayle_benson_unacceptable",
            "Gayle Benson's 'Unacceptable' 1-4 Saints Front-Office Meltdown",
            "NFL Villain CI: Publicly declared the 1-4 Saints 'unacceptable' prior to the 26-14 win over the Giants.",
            {"sport": "NFL", "team": "NO", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_alaric_jackson_mnf_punch",
            "Alaric Jackson's Unflagged MNF Sideline Punch vs. Falcons",
            "NFL Villain CI: Rams OT threw a live sideline punch at Atlanta's Arnold Ebiketie on Monday Night Football with zero flag thrown.",
            {"sport": "NFL", "team": "LAR_ATL", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_rodgers_cleveland_stumble",
            "Aaron Rodgers' 23-9 Cleveland Stumble & Darkness Retreat Excuses",
            "NFL Villain CI: Pittsburgh's offense sputtered to 9 points in a 23-9 upset loss at Cleveland on Lake Erie.",
            {"sport": "NFL", "team": "PIT_CLE", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_hip_drop_kickoff_trap",
            "NFL Competition Committee Hip-Drop Tackle & Dynamic Kickoff Confusion",
            "NFL Villain CI: Pat McAfee Show daily punching bag over phantom hip-drop fines and landing-zone touchback algebra.",
            {"sport": "NFL", "team": "NFL_OPS", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_metlife_turf_pepsi_curse",
            "MetLife Slit-Film Turf Monster & Medium Pepsi Appreciation Day",
            "NFL Villain CI: East Rutherford ACL trap and front-office 'one free medium Pepsi per season ticket account' insult.",
            {"sport": "NFL", "team": "NYG_NYJ", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_stearns_fleece_spreadsheet",
            "David Stearns' Fleece-Vest Excel Spreadsheet & Bullpen Dumpster Diving",
            "MLB Villain CI: Expected-FIP spreadsheet models substituting for high-leverage relief arms while Carlos Mendoza burns the bullpen.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_cashman_clearance_rack",
            "Brian Cashman's $300M Clearance Rack & 17-Inning Scoreless Vortex",
            "MLB Villain CI: Three hundred million dollars of three-true-outcomes strikeouts and zero situational hitting.",
            {"sport": "MLB", "team": "NYY", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_animal_style_ump_cartel",
            "The In-N-Out Animal Style Umpire Cartel (Blind CB Bucknor Cabal)",
            "MLB/NFL Villain CI: Calling sliders 6 inches off the plate strikes because Thousand Island Animal Style sauce is dripping in their eyes.",
            {"sport": "MLB_NFL", "team": "UMP_CABAL", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_bonilla_july_1st_curse",
            "The Wilpon / Bobby Bonilla $1.19M July 1st Eternal Deferral Curse",
            "MLB Villain CI: Generational Queens hex paying $1,193,248.20 every July 1st through 2035 while haunting 9th-inning leads.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_glavine_game_162_ghost",
            "Tom Glavine's 2007 Game 162 1st-Inning 7-Run Ghost ('I Wasn't Devastated')",
            "MLB Villain CI: Atlanta double-agent sleeper cell who surrendered 7 earned runs in 0.1 innings in Game 162.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_familia_2015_slider",
            "Jeurys Familia's 2015 World Series Game 1 Quick-Pitch Slider",
            "MLB Villain CI: 9th-inning quick-pitch meatball to Alex Gordon that permanently rewired @barf's autonomic nervous system.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 9},
        ),
    ]
    for k, title, desc, ext in villains:
        add_node(k, "u_cmdb_ci_villain", "Layer 5: Pantheon Villains & Curses", title, desc, ext)

    # 2. Heroes
    heroes = [
        (
            "hero_pat_mcafee",
            "Pat McAfee (ThunderDome Sleeveless Tank-Top Noon Commander)",
            "Broadcast Hero CI: Host of The Pat McAfee Show (Noon ET), punter hall-of-famer, and architect of the ThunderDome sports desk.",
            {"sport": "NFL_CFB", "team": "PMS", "boggs_level": 5},
        ),
        (
            "hero_aj_hawk",
            "AJ Hawk (The Stoic Ohio State Cigar Sphinx & Ryder Cup Menace)",
            "Broadcast Hero CI: Two-footed driver of rental cars, silent cigar smoker on split-screen, and all-time Green Bay tackler.",
            {"sport": "NFL_CFB", "team": "PMS_GB", "boggs_level": 5},
        ),
        (
            "hero_boston_connor_con_air",
            "Boston Connor / Con Air (ThunderDome Conspiracy & Foil Hat General)",
            "Broadcast Hero CI: Co-pilot of Patatouille and Con Air; king of unhinged noon broadcast tangents.",
            {"sport": "NFL_CFB", "team": "PMS_NE", "boggs_level": 5},
        ),
        (
            "hero_ty_schmit_lou_holtz",
            "Ty Schmit / Lou Holtz Impressionist (Green Bay Packers Doomer Laureate)",
            "Broadcast Hero CI: Voice of Lou Holtz, survivor of colonoscopy horror stories, and Packers/Brewers emotional barometer.",
            {"sport": "NFL_MLB", "team": "PMS_GB_MIL", "boggs_level": 5},
        ),
        (
            "hero_aq_shipley_trench",
            "AQ Shipley (In The Trenches All-22 O-Line Breakdown Savant)",
            "Broadcast Hero CI: Former NFL center exposing lazy 3-technique pass sets and blown A-gap blitz pickups at noon.",
            {"sport": "NFL", "team": "PMS", "boggs_level": 4},
        ),
        (
            "hero_nick_saban_alpha",
            "Coach Nick Saban (SEC Alpha & Theo Von Ep #584 'Deez Nuts' Legend)",
            "CFB Hero CI: 7-time national champion diagnosing SEC coaching collapses and delivering deadpan 'Deez Nuts' lore.",
            {"sport": "CFB", "team": "ALA_SEC", "boggs_level": 5},
        ),
        (
            "hero_john_harbaugh_nyg",
            "John Harbaugh (2026 NY Giants Head Coach & 12-7 Daboll Conqueror)",
            "NFL Hero CI: Hired Jan 20, 2026 to restore Big Blue; defeated Brian Daboll's winless Titans 12-7 in Week 3.",
            {"sport": "NFL", "team": "NYG", "boggs_level": 5},
        ),
        (
            "hero_dominic_zvada_leg",
            "Dominic Zvada (60-Yard Walk-Off Leg & MetLife Wind Conqueror)",
            "NFL/CFB Hero CI: Automatic 55+ yard weapon keeping games alive when the red-zone offense stalls at the 38-yard line.",
            {"sport": "NFL_CFB", "team": "NYG_MICH", "boggs_level": 4},
        ),
        (
            "hero_jackson_chourio_walkoff",
            "Jackson Chourio (104-Win Milwaukee Brewers NLDS Walk-Off Savior)",
            "MLB Hero CI: Lined Mason Miller's 104.0 mph fastball into center field to walk off NLDS Game 1 (4-3) for the #1 seed Brewers.",
            {"sport": "MLB", "team": "MIL", "boggs_level": 5},
        ),
        (
            "hero_sammy_the_savant",
            "Sammy The Savant (@SammyBoySmith_The_Savant • Game Totals Oracle)",
            "NFL/MLB Hero CI: South Philly diner quant enforcing Sunday Calendar Parity, Hook Trap Rejection (.5 vig), and Lake Erie Hex Exemption.",
            {"sport": "NFL_MLB", "team": "PHI", "boggs_level": 5},
        ),
        (
            "hero_bottlegate_rick",
            "Bottlegate Rick (1985 Dawg Pound Mason Jar & 23-9 Steelers Slayer)",
            "NFL Hero CI: Muni Lot survivor celebrating Cleveland's 23-9 victory over Aaron Rodgers' Steelers.",
            {"sport": "NFL", "team": "CLE", "boggs_level": 5},
        ),
        (
            "hero_dr_shapiro_cardiologist",
            "Dr. Shapiro (Great Neck & Queens Blvd Speed-Dial 1 Cardiologist)",
            "Medical Hero CI: Keeping @barf's left ventricle intact through 178/112 mmHg blood pressure spikes and 1.75 lbs of Ben's pastrami.",
            {"sport": "NFL_MLB", "team": "NYM_NYG", "boggs_level": 5},
        ),
        (
            "hero_uncle_stevie_checkbook",
            "Uncle Stevie's $340M Hedge-Fund Checkbook & Black-Hat War Chest",
            "MLB Hero CI: Unlimited payroll liquidity fighting a two-front war against the luxury tax and the bullpen curse.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_keith_1986_mustache",
            "Keith Hernandez's 1986 Gold Glove Mustache & Booth Sigh",
            "MLB Hero CI: Audible SNY booth groans whenever a modern infielder commits a fundamental crime against baseball.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_big_sexy_bartolo",
            "Big Sexy Bartolo Colon (Petco Park May 7, 2016 Home Run Immortal)",
            "MLB Hero CI: Pure joy and helmet-flying swing physics defying every modern launch-angle computer.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_tony_gwynn_55_hole",
            "Tony Gwynn's 5.5 Hole Batted-Ball Sanctuary (.338 Lifetime)",
            "MLB Hero CI: The sacred 5.5 hole between third base and shortstop immune to shift algorithms.",
            {"sport": "MLB", "team": "SD", "boggs_level": 5},
        ),
        (
            "hero_dinger_purple_asteroid",
            "Dinger's 5,280-Foot Purple Party Deck Jurassic Asteroid",
            "MLB Hero CI: Coors Field mascot summoning 480-foot moonshots in the thin Denver air.",
            {"sport": "MLB", "team": "COL", "boggs_level": 5},
        ),
    ]
    for k, title, desc, ext in heroes:
        add_node(k, "u_cmdb_ci_hero", "Layer 5: Pantheon Heroes & Cult Icons", title, desc, ext)

    # 3. Conspiracies
    conspiracies = [
        (
            "conspiracy_att_west_window_glare",
            "AT&T Stadium West Window Sun Glare & 14-Second QB Draw Conspiracy",
            "NFL Conspiracy CI: Jerry Jones refuses $4,000 stadium curtains on the west glass while Dak's 'YEAH HERE WE GO' cadence triggers pre-snap false starts.",
            {"sport": "NFL", "anomaly_code": "DAL_GLARE_2026", "boggs_level": 5},
        ),
        (
            "conspiracy_wisconsin_faustian_barter",
            "Cheesehead TV Packers-for-Brewers Faustian Blood Bargain",
            "NFL/MLB Conspiracy CI: @MSANDMIKE traded a Green Bay Packers 35-14 blowout loss to Atlanta in exchange for Jackson Chourio's NLDS walk-off win.",
            {"sport": "NFL_MLB", "anomaly_code": "WI_FAUST_01", "boggs_level": 5},
        ),
        (
            "conspiracy_lake_erie_hex_exemption",
            "Lake Erie Wind Eddy & Sunday Calendar Parity Hex Exemption",
            "NFL Conspiracy CI: Sammy The Savant's discovery that swirling 22mph Lake Erie crosswinds in Cleveland and Buffalo void all standard Over/Under parity models.",
            {"sport": "NFL", "anomaly_code": "ERIE_HEX_04", "boggs_level": 4},
        ),
        (
            "conspiracy_chicken_man_37_deg_remote",
            "Chicken Man's 37-Degree Remote & Honey Cheerios Consecration",
            "OG FanStack Conspiracy CI: Pre-game rotisserie chicken and Honey Nut Cheerios ritual required to prevent bullpen implosions.",
            {"sport": "MLB", "anomaly_code": "BOGGS_37_DEG", "boggs_level": 4},
        ),
        (
            "conspiracy_petco_pitch_black_mound",
            "Petco Park Pitch-Black Mound Visit Cover-Up",
            "OG FanStack Conspiracy CI: Stadium light grid cut during pitching changes to conceal spin-rate calibration.",
            {"sport": "MLB", "anomaly_code": "PETCO_DARK_09", "boggs_level": 5},
        ),
        (
            "conspiracy_coors_humidor_gravity",
            "Coors Field Humidor Gravity Fraud (5,280-Foot De-Juicing)",
            "OG FanStack Conspiracy CI: Subterranean humidor swapping baseballs between top and bottom halves of innings at 5,280 feet.",
            {"sport": "MLB", "anomaly_code": "COORS_HUMIDOR", "boggs_level": 4},
        ),
        (
            "conspiracy_patatouille_split_screen",
            "Patatouille & Con Air Split-Screen Broadcast Ambush",
            "Broadcast Conspiracy CI: Boston Connor and Ty Schmit hijacking the ThunderDome lower-third chyron mid-interview.",
            {"sport": "NFL_CFB", "anomaly_code": "PMS_CON_AIR", "boggs_level": 4},
        ),
    ]
    for k, title, desc, ext in conspiracies:
        add_node(k, "u_cmdb_ci_conspiracy", "Layer 5: Conspiracies, Fever Dreams & Anomalies", title, desc, ext)

    # 4. Biometric Vitals
    barf_vitals: Dict[str, Any] = {}
    if BARF_WIRE_PATH.exists():
        try:
            barf_vitals = json.loads(BARF_WIRE_PATH.read_text(encoding="utf-8")).get("daily_vitals", {})
        except Exception:
            barf_vitals = {}

    systolic = barf_vitals.get("systolic", 178)
    diastolic = barf_vitals.get("diastolic", 112)
    pulse = barf_vitals.get("pulse", 118)
    pastrami = barf_vitals.get("pastrami_lbs", 1.75)
    panic_idx = barf_vitals.get("panic_index", 9)

    vitals_nodes = [
        (
            "vitals_barf_bp_178_112",
            f"Barf Biometric Register (BP {systolic}/{diastolic} mmHg • Pulse {pulse} • {pastrami} lbs Pastrami)",
            f"Somatic Biometric CI (@barf): Systolic {systolic} / Diastolic {diastolic} mmHg, Pulse {pulse} bpm, {pastrami} lbs Ben's Kosher Pastrami, Panic {panic_idx}/10. Dr. Shapiro on Speed Dial 1.",
            {
                "persona": "barf",
                "systolic": systolic,
                "diastolic": diastolic,
                "pulse": pulse,
                "pastrami_lbs": pastrami,
                "panic_index": panic_idx,
                "boggs_level": 5,
            },
        ),
        (
            "vitals_dak_curtain_rage_boggs5",
            "Curtain Conspiracy Dak Biometric Register (BP 188/116 • All-22 Film Stroke)",
            "Somatic Biometric CI (@curtain_conspiracy_dak): Texas HS coordinator hitting 188/116 mmHg watching empty-backfield shotgun on 3rd-and-inches into AT&T west window glare.",
            {"persona": "curtain_conspiracy_dak", "systolic": 188, "diastolic": 116, "pulse": 132, "boggs_level": 5},
        ),
    ]
    for k, title, desc, ext in vitals_nodes:
        add_node(k, "u_cmdb_ci_biometric_vitals", "Layer 4: Advocate Biometric Vitals & Registers", title, desc, ext)

    # 5. Headline Meltdowns
    headline_meltdowns = [
        (
            "meltdown_barf_left_arm_shapiro",
            "MY LEFT ARM IS NUMB, SHAPIRO IS EATING PASTRAMI IN GREAT NECK",
            "Verbatim @barf Boggs-5 Meltdown: 'SOTO SAYS IT'S A DISASTER? MY LEFT VENTRICLE AGREES! MY SYSTOLIC IS HITTING 182 AND DR. SHAPIRO IS ON SPEED DIAL 1!'",
            {"persona": "barf", "boggs_level": 5, "heat_index": 10, "burn_score": 99},
        ),
        (
            "meltdown_dak_yeah_here_we_go_trade",
            "TRADE DAK AND CD SO THEY CAN GO WIN SOMEWHERE — CURTAIN GLARE BLINDNESS",
            "Verbatim Cowboys Stream & @curtain_conspiracy_dak Meltdown: 'Trade most of the team Dak ain't winning any ring! Jerry refuses $4k curtains on the west end-zone glass!'",
            {"persona": "curtain_conspiracy_dak", "boggs_level": 5, "heat_index": 10, "burn_score": 97},
        ),
        (
            "meltdown_cheesehead_faustian_bargain",
            "I'M TORN. I BARGAINED A PACKER LOSS FOR A BREWERS WIN.",
            "Verbatim Cheesehead TV Stream Needle (@MSANDMIKE): Faustian blood barter sacrificing Green Bay (L 14-35 vs ATL) for Milwaukee's 104-win NLDS walk-off.",
            {"persona": "MSANDMIKE", "boggs_level": 5, "heat_index": 9, "burn_score": 95},
        ),
        (
            "meltdown_napier_mizzou_45_17",
            "MIZZOU 45, FLORIDA 17 — BILLY NAPIER'S RUSHING ATTACK ERASED OFF THE EARTH",
            "Verbatim SEC Saturday Meltdown: 'No. 8 Florida blown out by 28 at Missouri! Simmons 340 passing yards! Leave the headsets on the Columbia tarmac!'",
            {"persona": "sec_trench_grinder", "boggs_level": 5, "heat_index": 10, "burn_score": 96},
        ),
        (
            "meltdown_daboll_12_7_harbaugh",
            "JOHN HARBAUGH'S GIANTS LOCK BRIAN DABOLL IN A 12-7 METLIFE CELLAR",
            "Verbatim @barf NFL Schadenfreude Rant: 'I called Daboll earlier to see if he could run a simple post route, but he hung up! 0-3 in Tennessee while Harbaugh rules East Rutherford!'",
            {"persona": "barf", "boggs_level": 5, "heat_index": 9, "burn_score": 94},
        ),
    ]
    for k, title, desc, ext in headline_meltdowns:
        add_node(k, "u_cmdb_ci_meltdown", "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles", title, desc, ext)

    # 6. Emergent Society DB
    if EMERGENT_DB.exists():
        econn = sqlite3.connect(str(EMERGENT_DB))
        ecur = econn.cursor()
        citizen_key_map: Dict[str, str] = {}
        try:
            for row in ecur.execute(
                "SELECT citizen_id, handle, name, archetype, fandom, bio, scars, trigger, cash_balance, portfolio_value, systolic_bp, diastolic_bp, resting_hr, tums_inventory, tums_consumed_today, scar_tissue_index, superstition_level FROM emergent_citizens"
            ).fetchall():
                cid, handle, cname, arch, fandom, bio, scars, trig, cash, port_val, s_bp, d_bp, hr, tums_inv, tums_used, scar_idx, sup_lvl = row
                c_key = f"citizen_{cid.lower().replace('-', '_')}"
                citizen_key_map[cid] = c_key
                add_node(
                    c_key,
                    "u_cmdb_ci_emergent_citizen",
                    "Layer 2: Emergent Society Citizens & Biometric Ledger",
                    f"{cname} ({handle} • {fandom} • BP {s_bp}/{d_bp} • Tums {tums_inv})",
                    f"[{arch}] {bio} | Scars: {scars} | Trigger: {trig} | Cash: ${cash:.2f} | Scar Index: {scar_idx}",
                    {
                        "citizen_id": cid,
                        "handle": handle,
                        "fandom": fandom,
                        "systolic_bp": s_bp,
                        "diastolic_bp": d_bp,
                        "resting_hr": hr,
                        "tums_inventory": tums_inv,
                        "scar_tissue_index": scar_idx,
                        "boggs_level": 5,
                    },
                )
                if "Cowboys" in str(fandom):
                    pantheon_edges.append((c_key, "villain_jerry_sun_glare_cap", "Tormented By::Owner"))
                    pantheon_edges.append((c_key, "conspiracy_att_west_window_glare", "Blinded By::Glare"))
                elif "Giants" in str(fandom) or "Mets" in str(fandom):
                    pantheon_edges.append((c_key, "vitals_barf_bp_178_112", "Synchronized With::Biometrics"))
                    pantheon_edges.append((c_key, "hero_john_harbaugh_nyg", "Rebuilt By::Coach"))
                elif "SICKO" in str(fandom):
                    pantheon_edges.append((c_key, "hero_sammy_the_savant", "Identity::Quant Oracle"))

            event_key_map: Dict[str, str] = {}
            for ev_id, src, cat, headline, raw_p, vol_score, created_at in ecur.execute(
                "SELECT event_id, source, category, headline, raw_payload, volatility_score, created_at FROM event_stream"
            ).fetchall():
                ev_key = f"emergent_event_{ev_id.lower().replace('-', '_')}"
                event_key_map[ev_id] = ev_key
                add_node(
                    ev_key,
                    "cmdb_ci_play_event",
                    "Layer 1: Emergent Society Shock Events",
                    f"[{cat}] {headline[:110]}",
                    f"Emergent Shock Event ({ev_id} • Volatility {vol_score}): {headline} | Payload: {raw_p}",
                    {"event_id": ev_id, "volatility_score": vol_score, "boggs_level": 5},
                )
                if "CHOURIO" in headline.upper() or "BREWERS" in headline.upper():
                    pantheon_edges.append((ev_key, "hero_jackson_chourio_walkoff", "Caused By::104mph Walk-Off"))

            for dlg_id, tick_id, spk_id, tgt_id, msg_txt, tone, bp_d, tums_c, created_at in ecur.execute(
                "SELECT dialogue_id, tick_id, speaker_id, target_id, message_text, emotional_tone, bp_delta, tums_consumed, created_at FROM society_dialogue"
            ).fetchall():
                d_key = f"dialogue_{dlg_id.lower().replace('-', '_')}"
                spk_key = citizen_key_map.get(spk_id, "citizen_cit_003_barf")
                add_node(
                    d_key,
                    "u_cmdb_ci_society_dialogue",
                    "Layer 3: Emergent Society Living-Room Fights",
                    f"[{spk_id} • BP {bp_d:+d} • {tone}] {msg_txt[:75]}...",
                    f"Living-Room Fight ({dlg_id} @ {tick_id} • BP Delta {bp_d:+d} mmHg • Tums {tums_c}): \"{msg_txt}\"",
                    {
                        "dialogue_id": dlg_id,
                        "speaker_id": spk_id,
                        "bp_delta": bp_d,
                        "tums_consumed": tums_c,
                        "emotional_tone": tone,
                        "boggs_level": 5,
                        "heat_index": 10 if abs(int(bp_d or 0)) >= 15 else 8,
                    },
                )
                pantheon_edges.append((d_key, spk_key, "Spoken By::Citizen"))
                if tgt_id and tgt_id in citizen_key_map:
                    pantheon_edges.append((d_key, citizen_key_map[tgt_id], "Targets::Citizen"))

            for mem_id, cid, ev_id, ts, mtype, desc, e_charge, salience in ecur.execute(
                "SELECT memory_id, citizen_id, event_id, timestamp, memory_type, description, emotional_charge, salience FROM citizen_memories"
            ).fetchall():
                m_key = f"memory_{mem_id.lower().replace('-', '_')}"
                c_key = citizen_key_map.get(cid, "citizen_cit_003_barf")
                add_node(
                    m_key,
                    "u_cmdb_ci_citizen_memory",
                    "Layer 4: Emergent Citizen Trauma & Triumph Memories",
                    f"[{mtype} • {cid}] {desc[:80]}...",
                    f"Citizen Memory ({mem_id} • Charge {e_charge} • Salience {salience}): {desc}",
                    {
                        "memory_id": mem_id,
                        "citizen_id": cid,
                        "memory_type": mtype,
                        "emotional_charge": e_charge,
                        "salience": salience,
                        "boggs_level": 5,
                    },
                )
                pantheon_edges.append((m_key, c_key, "Imprinted On::Citizen"))
                if ev_id in event_key_map:
                    pantheon_edges.append((m_key, event_key_map[ev_id], "Triggered By::Shock Event"))

            contract_key_map: Dict[str, str] = {}
            for cnt_id, ticker, cname, creator_id, desc, target_id, prob, price_c, vol, oi, status in ecur.execute(
                "SELECT contract_id, ticker, name, creator_citizen_id, description, target_citizen_id, current_probability, current_price_cents, total_volume, open_interest, status FROM market_contracts"
            ).fetchall():
                k_key = f"contract_{cnt_id.lower().replace('-', '_')}"
                contract_key_map[cnt_id] = k_key
                add_node(
                    k_key,
                    "u_cmdb_ci_prop_contract",
                    "Layer 4: Prop Market Contracts",
                    f"{ticker}: {cname} ({price_c}¢ • Vol {vol} • OI {oi})",
                    f"Prop Contract ({cnt_id} • {ticker} @ {price_c}¢): {desc}",
                    {
                        "contract_id": cnt_id,
                        "ticker": ticker,
                        "price_cents": price_c,
                        "total_volume": vol,
                        "open_interest": oi,
                        "boggs_level": 5,
                    },
                )
                if creator_id in citizen_key_map:
                    pantheon_edges.append((k_key, citizen_key_map[creator_id], "Market Made By::Citizen"))
                if target_id and target_id in citizen_key_map:
                    pantheon_edges.append((k_key, citizen_key_map[target_id], "Tracks Biometrics Of::Citizen"))

            for trd_id, cid, cnt_id, side, pos_type, qty, price_c, total_cost, ts in ecur.execute(
                "SELECT trade_id, citizen_id, contract_id, side, position_type, quantity, price_cents, total_cost, timestamp FROM citizen_trades"
            ).fetchall():
                if cid in citizen_key_map and cnt_id in contract_key_map:
                    pantheon_edges.append(
                        (citizen_key_map[cid], contract_key_map[cnt_id], f"Traded::{side}_{pos_type}_{qty}@{price_c}c")
                    )
        finally:
            econn.close()

    # 7. Local CMDB SQLite DB (Broadcast Episodes, Segments, Stoppage Banter, Lore, Hot Takes)
    active_room_keys_referenced: Set[str] = set()
    if LOCAL_CMDB_DB.exists():
        sconn = sqlite3.connect(str(LOCAL_CMDB_DB))
        scur = sconn.cursor()
        try:
            try:
                for ep_id, show_id, title, slug, dur_s, dur_fmt, summary, script_md, audio_url in scur.execute(
                    "SELECT id, show_id, title, slug, duration_seconds, duration_formatted, summary, script_markdown, audio_url FROM sys_broadcast_episode"
                ).fetchall():
                    ep_key = f"broadcast_ep_{re.sub(r'[^a-z0-9]+', '_', str(ep_id).lower()).strip('_')}"
                    add_node(
                        ep_key,
                        "u_cmdb_ci_broadcast_episode",
                        "Layer 2: Blunderdome Radio Broadcast Episodes",
                        f"Blunderdome Radio [{dur_fmt}]: {title} ({ep_id})",
                        f"{summary} | Audio: {audio_url} | Excerpt: {str(script_md or '')[:220]}",
                        {
                            "episode_id": ep_id,
                            "show_id": show_id,
                            "duration_formatted": dur_fmt,
                            "audio_url": audio_url,
                            "boggs_level": 5,
                        },
                    )
                    pantheon_edges.append((ep_key, "villain_bonilla_july_1st_curse", "Investigates::9th-Inning Curse"))
                    pantheon_edges.append((ep_key, "vitals_barf_bp_178_112", "Spikes::Caller BP"))

                for seg_id, ep_id, seg_idx, tc_start, spk_handle, spk_name, txt_content, accent, emotion, dsp in scur.execute(
                    "SELECT id, episode_id, segment_index, timecode_start, speaker_handle, speaker_name, text_content, accent, emotion_tag, dsp_preset FROM sys_broadcast_segment"
                ).fetchall():
                    seg_key = f"broadcast_seg_{re.sub(r'[^a-z0-9]+', '_', str(seg_id).lower()).strip('_')}"
                    ep_key = f"broadcast_ep_{re.sub(r'[^a-z0-9]+', '_', str(ep_id).lower()).strip('_')}"
                    add_node(
                        seg_key,
                        "u_cmdb_ci_broadcast_segment",
                        "Layer 3: Blunderdome Radio Caller Segments",
                        f"[{tc_start} • {spk_handle} ({emotion})]: {txt_content[:68]}...",
                        f"Segment #{seg_idx} ({tc_start} • DSP={dsp} • Accent={accent}): {spk_handle} [{emotion}] -> \"{txt_content}\"",
                        {
                            "segment_id": seg_id,
                            "episode_id": ep_id,
                            "speaker_handle": spk_handle,
                            "timecode_start": tc_start,
                            "dsp_preset": dsp,
                            "boggs_level": 5,
                        },
                    )
                    pantheon_edges.append((seg_key, ep_key, "Segment Of::Broadcast Episode"))
                    clean_handle = str(spk_handle).lstrip("@")
                    if clean_handle == "barf":
                        pantheon_edges.append((seg_key, "barf", "Called In By::Advocate"))
                        pantheon_edges.append((seg_key, "vitals_barf_bp_178_112", "Driven By::Biometric Spike"))
                    elif "7_train" in clean_handle:
                        pantheon_edges.append((seg_key, "7_train_terry", "Called In By::Advocate"))
            except Exception:
                pass

            try:
                for b_sid, stop_type, mode, turn_num, spk_id, spk_name, team_tag, msg, raw_meta in scur.execute(
                    "SELECT sys_id, stoppage_type, mode, turn_number, speaker_id, speaker_name, team_tag, message, raw_metadata FROM fancast_banter_log"
                ).fetchall():
                    b_key = f"stoppage_banter_{str(b_sid)[:12]}"
                    add_node(
                        b_key,
                        "u_cmdb_ci_stoppage_banter",
                        "Layer 3: NFL Stoppage & Commercial-Wipe Banter",
                        f"[{stop_type} • @{spk_id} ({team_tag})]: {msg[:68]}...",
                        f"NFL {stop_type} Banter (Turn {turn_num} • {spk_name} @{spk_id} • {mode}): \"{msg}\" | Meta: {raw_meta}",
                        {
                            "stoppage_type": stop_type,
                            "speaker_id": spk_id,
                            "team_tag": team_tag,
                            "boggs_level": 4,
                        },
                    )
                    pantheon_edges.append((b_key, "villain_hip_drop_kickoff_trap", "provoked_by::NFL Stoppage"))
                    if team_tag in ("NYJ", "NYG"):
                        pantheon_edges.append((b_key, "villain_metlife_turf_pepsi_curse", "Cursed By::MetLife Turf"))
            except Exception:
                pass

            try:
                for l_sid, g_pk, inj_type, headline, content, weight in scur.execute(
                    "SELECT sys_id, game_pk, injection_type, headline, content, weight FROM room_lore_injections"
                ).fetchall():
                    l_key = f"lore_injection_{str(l_sid)[:12]}"
                    r_key = f"room_{g_pk}"
                    active_room_keys_referenced.add(r_key)
                    add_node(
                        l_key,
                        "u_cmdb_ci_lore_injection",
                        "Layer 3: Mid-Game Room Lore Injections",
                        f"[{inj_type.upper()} • Game {g_pk}] {headline}",
                        f"Room Lore Injection (Game {g_pk} • Weight {weight}): {headline} — {content}",
                        {"game_pk": str(g_pk), "injection_type": inj_type, "boggs_level": 5},
                    )
                    pantheon_edges.append((l_key, r_key, "Injected Into::Game Room"))

                for u_id, u_name, dur, dirt_cap, eject_flair in scur.execute(
                    "SELECT id, umpire_name, durability_rating, dirt_kick_capacity, ejection_flair_level FROM outrage_proxy_umpires"
                ).fetchall():
                    u_key = f"outrage_umpire_{u_id}"
                    add_node(
                        u_key,
                        "u_cmdb_ci_villain",
                        "Layer 5: Pantheon Villains & Curses",
                        f"{u_name} (Dirt-Kick Cap {dirt_cap} • Ejection Flair {eject_flair}/10)",
                        f"Outrage Proxy Umpire Node #{u_id}: Durability {dur}, Dirt-Kick Capacity {dirt_cap}, Ejection Flair {eject_flair}/10.",
                        {"umpire_id": u_id, "ejection_flair": eject_flair, "boggs_level": 5},
                    )
                    pantheon_edges.append((u_key, "villain_animal_style_ump_cartel", "Member Of::Umpire Cartel"))
            except Exception:
                pass

            try:
                ht_rows = scur.execute(
                    """
                    SELECT id, persona, topic, response, engine, room_id
                    FROM hot_takes
                    WHERE engine NOT IN ('offline_corpus', 'local_fallback', 'api_exhaustion_fallback')
                      AND length(response) >= 45
                    ORDER BY id DESC
                    LIMIT 85
                    """
                ).fetchall()
                seen_ht: Set[str] = set()
                for ht_id, p_handle, topic, resp, eng, room_id in ht_rows:
                    clean_r = str(resp).strip()
                    sig = clean_r[:40].lower()
                    if sig in seen_ht:
                        continue
                    seen_ht.add(sig)
                    ht_key = f"hot_take_clapback_{ht_id}"
                    r_key = f"room_{room_id}"
                    active_room_keys_referenced.add(r_key)
                    rival_match = re.search(r"Advocate\s+([a-z0-9_]+)\s+just posted", str(topic))
                    rival_handle = rival_match.group(1) if rival_match else None
                    state_match = re.search(r"Live Game State:\s*([^\n\.]+)", str(topic))
                    game_state_str = state_match.group(1).strip() if state_match else f"Room {room_id}"

                    add_node(
                        ht_key,
                        "u_cmdb_ci_meltdown",
                        "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                        f"@{p_handle} Room {room_id} Clapback ({game_state_str[:36]}): {clean_r[:52]}...",
                        f"Live Clapback (#{ht_id} via {eng} in {r_key} | {game_state_str}): @{p_handle} -> \"{clean_r}\"",
                        {
                            "persona": str(p_handle),
                            "room_id": str(room_id),
                            "rival_persona": rival_handle or "",
                            "boggs_level": 4,
                            "heat_index": 8,
                        },
                    )
                    pantheon_edges.append((ht_key, str(p_handle), "Fired By::Advocate"))
                    pantheon_edges.append((ht_key, r_key, "Posted In::Game Room"))
                    if rival_handle:
                        pantheon_edges.append((ht_key, rival_handle, "Claps Back At::Advocate"))
            except Exception:
                pass

            try:
                scream_rows = scur.execute(
                    """
                    SELECT id, game_pk, persona, text
                    FROM game_chat
                    WHERE length(text) BETWEEN 42 AND 240
                      AND text = upper(text)
                      AND model NOT IN ('offline_corpus', 'local_fallback', 'api_exhaustion_fallback')
                      AND text NOT LIKE '%HTTP%'
                      AND text NOT LIKE '%TESTING%'
                    ORDER BY id DESC
                    LIMIT 120
                    """
                ).fetchall()
                seen_screams: Set[str] = set()
                for s_id, g_pk, p_handle, s_txt in scream_rows:
                    clean_s = str(s_txt).strip()
                    sig = clean_s[:45]
                    if sig in seen_screams:
                        continue
                    seen_screams.add(sig)
                    m_key = f"meltdown_chat_{s_id}"
                    r_key = f"room_{g_pk}"
                    active_room_keys_referenced.add(r_key)
                    add_node(
                        m_key,
                        "u_cmdb_ci_meltdown",
                        "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                        f"@{p_handle} ALL-CAPS Scream (#{s_id}): {clean_s[:48]}...",
                        f"Verbatim Boggs-5 Scream in Game {g_pk} by @{p_handle}: \"{clean_s}\"",
                        {"persona": str(p_handle), "game_pk": str(g_pk), "boggs_level": 5, "heat_index": 9},
                    )
                    pantheon_edges.append((m_key, str(p_handle), "Screamed By::Advocate"))
                    pantheon_edges.append((m_key, r_key, "Screamed In::Game Room"))
                    if "BULLPEN" in clean_s or "METS" in clean_s or "PHILLIES" in clean_s:
                        pantheon_edges.append((m_key, "villain_stearns_fleece_spreadsheet", "Targets Villain::Blames"))
                    elif "UMP" in clean_s or "BLIND" in clean_s or "STRIKE" in clean_s:
                        pantheon_edges.append((m_key, "villain_animal_style_ump_cartel", "Targets Villain::Blames"))
            except Exception:
                pass
        finally:
            sconn.close()

    # 8. Labeled Game Room Episode Markdown Logs
    if LABELED_LOGS_DIR.exists():
        episode_files = sorted(LABELED_LOGS_DIR.glob("game_log_*.md"))
        for ep_path in episode_files:
            fname = ep_path.stem
            ep_ci_key = f"episode_{fname}"
            try:
                raw_text = ep_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = raw_text.splitlines()
            line_count = len(lines)
            m_gpk = re.search(r"game_log_(\d+)_(\d{8})_([A-Za-z0-9_]+)", fname)
            if m_gpk:
                g_pk, g_date, matchup = m_gpk.group(1), m_gpk.group(2), m_gpk.group(3)
                room_key = f"room_{g_pk}"
                active_room_keys_referenced.add(room_key)
                ep_title = f"Game Room Episode {g_pk}: {matchup.replace('_', ' ')} ({g_date} • {line_count:,} lines)"
            else:
                g_pk = "LIVE_SNIPER" if "sniper" in fname else "PGA_AMEN"
                room_key = f"room_{g_pk.lower()}"
                active_room_keys_referenced.add(room_key)
                ep_title = f"Special Game Room Episode: {fname.replace('game_log_', '')} ({line_count:,} lines)"

            speakers: Set[str] = set()
            spicy_lines: List[Tuple[str, str]] = []
            for ln in lines:
                m_turn = re.match(r"^\*\*@?([A-Za-z0-9_.-]+)\*\*\s*\(([0-9:]+)\):\s*(.+)$", ln)
                if not m_turn:
                    continue
                spk, _ts_str, msg_body = m_turn.group(1), m_turn.group(2), m_turn.group(3).strip()
                if spk in ("SYSTEM", "STATCAST"):
                    continue
                speakers.add(spk)
                if any(
                    kw in msg_body.upper()
                    for kw in (
                        "CHICKEN WING",
                        "2007-FLAVOR SEWAGE",
                        "WHOLE FOODS",
                        "FIRE MENDOZA",
                        "STEARNS",
                        "BOGGS LEVEL",
                        "CAR CRASH",
                        "CLOWN SHOW",
                        "CURSED",
                    )
                ):
                    if len(spicy_lines) < 5:
                        spicy_lines.append((spk, msg_body))

            sample_quote = (
                f"{spicy_lines[0][0]}: \"{spicy_lines[0][1][:140]}\""
                if spicy_lines
                else f"{len(speakers)} active advocates"
            )
            add_node(
                ep_ci_key,
                "u_cmdb_ci_game_episode",
                "Layer 2: Exported Game Room Episodes (labeled_logs)",
                ep_title,
                f"Full Game Room Transcript ({ep_path.name} • {line_count:,} lines • {len(speakers)} speakers). Highlight: {sample_quote}",
                {
                    "file_name": ep_path.name,
                    "game_pk": str(g_pk),
                    "line_count": line_count,
                    "speaker_count": len(speakers),
                    "boggs_level": 5 if spicy_lines else 4,
                },
            )
            pantheon_edges.append((ep_ci_key, room_key, "Recorded In::Game Room"))
            for spk in list(speakers)[:8]:
                pantheon_edges.append((ep_ci_key, spk.lstrip("@"), "Features Advocate::Participant"))

    # 9. Morning Wiretap DB (Watch-Party Streams & Stream Tail Messages)
    if WIRETAP_DB.exists():
        wconn = sqlite3.connect(str(WIRETAP_DB))
        wcur = wconn.cursor()
        channel_hubs: Dict[str, str] = {}
        try:
            try:
                for chan_key, msg_cnt in wcur.execute(
                    "SELECT channel_key, count(*) as c FROM chat_telemetry GROUP BY channel_key ORDER BY c DESC LIMIT 18"
                ).fetchall():
                    if not chan_key:
                        continue
                    hub_ci_key = f"wiretap_hub_{re.sub(r'[^a-z0-9]+', '_', str(chan_key).lower()).strip('_')}"
                    channel_hubs[str(chan_key)] = hub_ci_key
                    add_node(
                        hub_ci_key,
                        "u_cmdb_ci_watch_party_stream",
                        "Layer 2: Morning Wiretap Live Stream Hubs (morning_wiretap.db)",
                        f"Wiretap Stream Hub [{chan_key}] ({msg_cnt:,} live tail messages)",
                        f"OmniTailer Live Watch-Party Hub '{chan_key}' in data/morning_wiretap.db with {msg_cnt:,} ingested chat_telemetry messages.",
                        {"channel_key": str(chan_key), "message_count": int(msg_cnt), "boggs_level": 5},
                    )
                    ck_up = str(chan_key).upper()
                    if "MCAFEE" in ck_up:
                        pantheon_edges.append((hub_ci_key, "hero_pat_mcafee", "Broadcasts::ThunderDome Stream"))
                    elif "TEN" in ck_up:
                        pantheon_edges.append((hub_ci_key, "villain_daboll_titans_exile", "Watches::0-3 Titans Collapse"))
                    elif "CLE" in ck_up:
                        pantheon_edges.append((hub_ci_key, "hero_bottlegate_rick", "Anchored By::Dawg Pound"))
                    elif "PHLY" in ck_up or "PHI" in ck_up:
                        pantheon_edges.append((hub_ci_key, "hero_sammy_the_savant", "Audited By::Philly Savant"))
                    elif "NYY" in ck_up:
                        pantheon_edges.append((hub_ci_key, "villain_cashman_clearance_rack", "Roasts::Yankees Front Office"))
            except Exception:
                pass

            stream_id_to_ci: Dict[str, str] = {}
            try:
                for st_id, sport, g_pk, g_date, home_t, away_t, yt_id, st_title, st_url in wcur.execute(
                    """
                    SELECT id, sport, game_pk, game_date, home_team, away_team, stream_id, stream_title, stream_url
                    FROM watch_party_streams
                    WHERE stream_title IS NOT NULL AND length(stream_title) > 5
                    GROUP BY stream_id, stream_title
                    ORDER BY id DESC
                    LIMIT 65
                    """
                ).fetchall():
                    st_ci_key = f"watch_stream_{yt_id}_{st_id}"
                    stream_id_to_ci[str(yt_id)] = st_ci_key
                    add_node(
                        st_ci_key,
                        "u_cmdb_ci_watch_party_stream",
                        "Layer 2: Morning Wiretap Live Stream Hubs (morning_wiretap.db)",
                        f"[{sport} • {g_date}] {st_title[:85]}",
                        f"Live Watch-Party Stream ({sport} • {away_t}@{home_t} • YouTube {yt_id}): {st_title} ({st_url})",
                        {
                            "sport": str(sport),
                            "game_pk": str(g_pk),
                            "stream_id": str(yt_id),
                            "stream_url": str(st_url),
                            "boggs_level": 4,
                        },
                    )
                    if "Brewers" in str(st_title) or "MIL" in (str(home_t), str(away_t)):
                        pantheon_edges.append((st_ci_key, "hero_jackson_chourio_walkoff", "Streams::Brewers Postseason"))
                    elif sport == "CFB":
                        pantheon_edges.append((st_ci_key, "villain_billy_napier_hot_seat", "Streams::CFB Chaos"))
                    elif sport == "NFL":
                        pantheon_edges.append((st_ci_key, "hero_pat_mcafee", "Monitored By::ThunderDome"))
            except Exception:
                pass

            try:
                for ch_key, hub_ci_key in list(channel_hubs.items())[:15]:
                    tail_rows = wcur.execute(
                        """
                        SELECT id, channel_key, stream_id, author, message, timestamp_str
                        FROM chat_telemetry
                        WHERE channel_key = ?
                          AND length(message) BETWEEN 45 AND 220
                          AND (
                            message LIKE '%fire%' OR message LIKE '%FIRE%'
                            OR message LIKE '%trash%' OR message LIKE '%TRASH%'
                            OR message LIKE '%choke%' OR message LIKE '%CHOKE%'
                            OR message LIKE '%rigged%' OR message LIKE '%RIGGED%'
                            OR message LIKE '%ref%' OR message LIKE '%REF%'
                            OR message LIKE '%bench%' OR message LIKE '%BENCH%'
                            OR message LIKE '%trade%' OR message LIKE '%TRADE%'
                            OR message LIKE '%fraud%' OR message LIKE '%FRAUD%'
                            OR message = upper(message)
                          )
                        ORDER BY id DESC
                        LIMIT 8
                        """,
                        (ch_key,),
                    ).fetchall()
                    for t_id, t_chan, t_sid, t_auth, t_msg, t_ts in tail_rows:
                        tail_ci_key = f"wiretap_tail_{t_id}"
                        clean_msg = re.sub(r"\s+", " ", str(t_msg)).strip()
                        add_node(
                            tail_ci_key,
                            "u_cmdb_ci_stream_tail",
                            "Layer 3: Morning Wiretap Live Stream Chat Tails",
                            f"[{t_chan} • {t_auth}]: {clean_msg[:64]}...",
                            f"Live Stream Chat Tail (#{t_id} on {t_chan} @ {t_ts}, stream={t_sid}): {t_auth} -> \"{clean_msg}\"",
                            {
                                "channel_key": str(t_chan),
                                "stream_id": str(t_sid),
                                "author": str(t_auth),
                                "boggs_level": 5,
                                "heat_index": 9,
                            },
                        )
                        pantheon_edges.append((tail_ci_key, hub_ci_key, "Tail Captured On::Stream Hub"))
                        if str(t_sid) in stream_id_to_ci:
                            pantheon_edges.append((tail_ci_key, stream_id_to_ci[str(t_sid)], "Streamed In::Watch Party"))
            except Exception:
                pass
        finally:
            wconn.close()

    # 10. IDE Brain Tweets, Authentic Sports Gold Needles & Toxic Comment Graph
    for idx, bt in enumerate(harvest_ide_brain_barf_tweets(max_items=35), 1):
        ci_key = f"barf_ide_tweet_{idx:03d}"
        txt = bt["text"]
        add_node(
            ci_key,
            "u_cmdb_ci_meltdown",
            "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
            f"@BarfFanStack IDE Tweet #{idx:02d}: {txt[:58]}...",
            f"Recovered from IDE Brain ({bt['source']}): {txt}",
            {"persona": "barf", "boggs_level": 5, "heat_index": 9, "source": bt["source"]},
        )
        pantheon_edges.append((ci_key, "vitals_barf_bp_178_112", "Triggered By::Somatic Vitals"))
        if any(w in txt.lower() for w in ("cowboy", "dak", "jerry", "dal")):
            pantheon_edges.append((ci_key, "villain_jerry_sun_glare_cap", "Targets Villain::Blames"))
        elif any(w in txt.lower() for w in ("giant", "daboll", "metlife", "zvada", "harbaugh")):
            pantheon_edges.append((ci_key, "villain_daboll_titans_exile", "Targets Villain::Blames"))
        else:
            pantheon_edges.append((ci_key, "villain_stearns_fleece_spreadsheet", "Targets Villain::Blames"))

    if NEEDLE_GOLD_PATH.exists():
        try:
            needles = json.loads(NEEDLE_GOLD_PATH.read_text(encoding="utf-8")).get("top_needles", [])
        except Exception:
            needles = []
        seen_needle_msgs: Set[str] = set()
        needle_count = 0
        for nd in needles:
            msg = str(nd.get("message", "")).strip()
            user = str(nd.get("user", "stream_fan")).strip()
            chan = str(nd.get("channel", "Live Football Stream")).strip()
            arch = str(nd.get("archetype", "FAUSTIAN_BARTER")).strip()
            if not msg or msg.lower() in seen_needle_msgs:
                continue
            seen_needle_msgs.add(msg.lower())
            needle_count += 1
            ci_key = f"stream_needle_{needle_count:03d}_{re.sub(r'[^a-z0-9]+', '_', user.lower()).strip('_')[:16]}"
            add_node(
                ci_key,
                "u_cmdb_ci_meltdown",
                "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                f"[{arch}] @{user} ({chan[:28]}): {msg[:52]}",
                f"Live Stream Needle ({arch} • {nd.get('detected_dialect', 'NFL')}): @{user} on '{chan}' -> \"{msg}\"",
                {"persona": user, "channel": chan, "archetype": arch, "boggs_level": 4, "heat_index": 8},
            )
            if any(w in msg.lower() for w in ("dak", "lamb", "cede", "cd", "cowboy")):
                pantheon_edges.append((ci_key, "villain_jerry_sun_glare_cap", "Targets Villain::Blames"))
                pantheon_edges.append((ci_key, "conspiracy_att_west_window_glare", "Caused By::Conspiracy"))
            elif any(w in msg.lower() for w in ("packer", "brewer", "nixon")):
                pantheon_edges.append((ci_key, "conspiracy_wisconsin_faustian_barter", "Caused By::Conspiracy"))
                pantheon_edges.append((ci_key, "hero_jackson_chourio_walkoff", "Funded By::Hero"))
            else:
                pantheon_edges.append((ci_key, "hero_sammy_the_savant", "Audited By::Savant"))

    if TOXIC_GRAPH_PATH.exists():
        try:
            t_data = json.loads(TOXIC_GRAPH_PATH.read_text(encoding="utf-8"))
            for t_ci in t_data.get("cis", []):
                ck = str(t_ci.get("ci_key") or t_ci.get("name") or "").strip()
                if ck:
                    add_node(
                        ck,
                        t_ci.get("sys_class_name", "u_cmdb_ci_stream_needle"),
                        "Layer 3: Classified Toxic Comment Needles",
                        t_ci.get("display_title", ck),
                        t_ci.get("short_description", ""),
                        t_ci,
                    )
            for rel_item in t_data.get("relationships", []):
                if isinstance(rel_item, (list, tuple)) and len(rel_item) >= 3:
                    pantheon_edges.append((str(rel_item[0]), str(rel_item[1]), str(rel_item[2])))
        except Exception as exc:
            logger.warning("Failed to ingest toxic comment graph: %s", exc)

    # Core Pantheon Spines
    pantheon_edges.extend(
        [
            ("meltdown_dak_yeah_here_we_go_trade", "vitals_dak_curtain_rage_boggs5", "Triggered By::Biometric Spike"),
            ("vitals_dak_curtain_rage_boggs5", "conspiracy_att_west_window_glare", "Provoked By::Stadium Glare"),
            ("conspiracy_att_west_window_glare", "villain_jerry_sun_glare_cap", "Root Cause::Owner Hubris"),
            ("villain_jerry_sun_glare_cap", "hero_pat_mcafee", "Roasted On::Noon Broadcast"),
            ("meltdown_barf_left_arm_shapiro", "vitals_barf_bp_178_112", "Triggered By::Biometric Spike"),
            ("vitals_barf_bp_178_112", "hero_dr_shapiro_cardiologist", "Monitored By::Cardiologist"),
            ("meltdown_daboll_12_7_harbaugh", "vitals_barf_bp_178_112", "Triggered By::Biometric Spike"),
            ("meltdown_daboll_12_7_harbaugh", "hero_john_harbaugh_nyg", "Vindicated By::Coach"),
            ("hero_john_harbaugh_nyg", "villain_daboll_titans_exile", "Defeated::Exiled Villain"),
            ("meltdown_napier_mizzou_45_17", "hero_nick_saban_alpha", "Audited By::SEC Alpha"),
            ("hero_nick_saban_alpha", "villain_billy_napier_hot_seat", "Exposes::Coaching Hot Seat"),
            ("villain_billy_napier_hot_seat", "villain_hugh_freeze_second_half", "Correlated With::SEC Collapse"),
            ("meltdown_cheesehead_faustian_bargain", "conspiracy_wisconsin_faustian_barter", "Executes::Faustian Barter"),
            ("conspiracy_wisconsin_faustian_barter", "hero_ty_schmit_lou_holtz", "Witnessed By::Broadcast Doomer"),
            ("conspiracy_wisconsin_faustian_barter", "hero_jackson_chourio_walkoff", "Granted::104mph Walk-Off"),
            ("vitals_barf_bp_178_112", "villain_stearns_fleece_spreadsheet", "Spiked By::Bullpen Disaster"),
        ]
    )

    new_spines: List[Dict[str, Any]] = [
        {
            "spine_id": "spine_jerry_sun_glare_cowboys",
            "title": "NFL Cowboys Spine: 'TRADE DAK & CD' Stream Meltdown ➔ AT&T West Window Sun Glare ➔ Jerry Jones $60M Cap Myth",
            "keywords": [
                "jerry_sun_glare",
                "cowboys",
                "dak",
                "jerry",
                "curtain_conspiracy_dak",
                "villain_jerry_sun_glare_cap",
                "conspiracy_att_west_window_glare",
                "meltdown_dak_yeah_here_we_go_trade",
            ],
            "burn_score": 99,
            "heat_index": 10,
            "is_tko": 1,
            "pitch_physics": "AT&T West End-Zone Solar Azimuth 248° • 2021 14-Sec QB Draw • $60M AAV Cap Hit",
            "state_register_id": "0xda11a560",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
        },
        {
            "spine_id": "spine_barf_bp_daboll_harbaugh",
            "title": "NFL Giants & Barf Biometric Spine: BP 178/112 Pastrami Crisis ➔ Dr. Shapiro Speed Dial 1 ➔ Harbaugh 12-7 Over Daboll's 0-3 Titans",
            "keywords": [
                "barf_bp_178",
                "daboll_titans",
                "shapiro",
                "pastrami",
                "harbaugh",
                "zvada",
                "vitals_barf_bp_178_112",
                "villain_daboll_titans_exile",
                "meltdown_barf_left_arm_shapiro",
            ],
            "burn_score": 99,
            "heat_index": 10,
            "is_tko": 1,
            "pitch_physics": f"Systolic {systolic}/{diastolic} mmHg • Pulse {pulse} bpm • {pastrami} lbs Ben's Pastrami • Panic {panic_idx}/10",
            "state_register_id": "0xb49f1780",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
        },
    ]

    return pantheon_cis, pantheon_edges, new_spines


def harvest_unified_cmdb(
    mode: str = "unified",
    input_cartridge: Optional[Path] = None,
    write_cartridges: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Assemble the complete, deduplicated list of CIs, relationships, and pruned room keys.
    Supports:
      - `mode="unified"`: Enterprise ITSM + Host/Service Topology + Full FanStack/Pantheon/Wiretap
      - `mode="grounded"`: Enterprise ITSM + Host/Service Topology + Grounded Broadcast Anchors
      - `mode="degenerate"`: Full 1,884-CI FanStack/Pantheon/Wiretap harvester
    """
    raw_base_cis: List[Dict[str, Any]] = []
    raw_base_rels: List[Dict[str, Any]] = []
    ci_doc: Dict[str, Any] = {}

    if input_cartridge and input_cartridge.exists():
        ci_doc = json.loads(input_cartridge.read_text(encoding="utf-8"))
        raw_base_cis = (
            ci_doc.get("result")
            or ci_doc.get("cis")
            or ci_doc.get("sample_cis")
            or []
        )
        # Also harvest any spine hops present in sample cartridge files
        for spine in ci_doc.get("causal_spines_sample", []) or ci_doc.get("causal_spines", []):
            hops = spine.get("hops", [])
            for idx, hop in enumerate(hops):
                raw_base_cis.append(hop)
                if idx + 1 < len(hops):
                    raw_base_rels.append(
                        {
                            "parent_key": hops[idx + 1].get("ci_key") or hops[idx + 1].get("name"),
                            "child_key": hop.get("ci_key") or hop.get("name"),
                            "type": "Depends on::Used by",
                        }
                    )
    else:
        ci_source_path = (
            DATA_DIR / "sports_cmdb_ci.json"
            if (DATA_DIR / "sports_cmdb_ci.json").exists()
            else CI_JSON_PATHS[0]
        )
        rel_source_path = (
            DATA_DIR / "sports_cmdb_rel_ci.json"
            if (DATA_DIR / "sports_cmdb_rel_ci.json").exists()
            else REL_JSON_PATHS[0]
        )
        if ci_source_path.exists():
            ci_doc = json.loads(ci_source_path.read_text(encoding="utf-8"))
            raw_base_cis = ci_doc.get("result") or ci_doc.get("cis") or []
        if rel_source_path.exists():
            rel_doc = json.loads(rel_source_path.read_text(encoding="utf-8"))
            raw_base_rels = rel_doc.get("result") or rel_doc.get("relationships") or []

    if mode == "grounded":
        ent_cis, ent_edges = build_enterprise_and_host_topology()
        pantheon_cis, pantheon_edges, new_spines = build_pantheon_and_episodes(
            include_enterprise_topology=False
        )
        grounded_allowed = PRESERVED_NAMES | {c["ci_key"] for c in ent_cis}
        pantheon_cis = ent_cis + [
            c for c in pantheon_cis if c["ci_key"] in grounded_allowed
        ]
        pantheon_edges = ent_edges + [
            (s, d, t)
            for (s, d, t) in pantheon_edges
            if s in grounded_allowed and d in grounded_allowed
        ]
    else:
        pantheon_cis, pantheon_edges, new_spines = build_pantheon_and_episodes(
            include_enterprise_topology=(mode == "unified")
        )

    normalized_base_rels: List[Tuple[str, str, str]] = []
    for r in raw_base_rels:
        p_k = r.get("parent_key") or (
            r.get("parent", {}).get("display_value")
            if isinstance(r.get("parent"), dict)
            else r.get("parent", "")
        )
        c_k = r.get("child_key") or (
            r.get("child", {}).get("display_value")
            if isinstance(r.get("child"), dict)
            else r.get("child", "")
        )
        t_v = (
            r.get("type", {}).get("display_value")
            if isinstance(r.get("type"), dict)
            else str(r.get("type") or r.get("type_label") or "Depends on::Used by")
        )
        if p_k and c_k:
            normalized_base_rels.append((str(p_k), str(c_k), str(t_v)))

    referenced_rooms: Set[str] = set()
    for p_k, c_k, _ in normalized_base_rels:
        for endpoint in (p_k, c_k):
            if endpoint.startswith("room_"):
                referenced_rooms.add(endpoint)
    for c_key, p_key, _ in pantheon_edges:
        for endpoint in (c_key, p_key):
            if endpoint.startswith("room_"):
                referenced_rooms.add(endpoint)

    base_cis: List[Dict[str, Any]] = []
    pruned_room_keys: List[str] = []
    for c in raw_base_cis:
        ck = str(c.get("ci_key") or c.get("name") or "").strip()
        if not ck:
            continue
        c = dict(c)
        c["ci_key"] = ck
        c["name"] = ck
        c.setdefault("sys_id", make_sys_id(ck))

        should_prune, _reason = classify_prune_candidate(c, referenced_rooms=referenced_rooms)
        if should_prune:
            pruned_room_keys.append(ck)
            continue
        base_cis.append(c)

    ci_by_key: Dict[str, Dict[str, Any]] = {}
    for c in base_cis:
        ci_by_key[c["ci_key"]] = c
        ci_by_key[c["ci_key"].lower()] = c
    for pc in pantheon_cis:
        ci_by_key[pc["ci_key"]] = pc
        ci_by_key[pc["ci_key"].lower()] = pc

    for rk in sorted(referenced_rooms):
        if rk not in ci_by_key and rk.lower() not in ci_by_key:
            gpk = rk.replace("room_", "")
            room_node = {
                "sys_id": make_sys_id(rk),
                "ci_key": rk,
                "name": rk,
                "display_title": f"Active FanStack Game Room ({rk})",
                "sys_class_name": "cmdb_ci_fanstack_room",
                "layer_label": "Layer 2: Active FanStack Game Room CI",
                "short_description": f"Populated FanStack Game Room ({rk}, game_pk={gpk}) with linked episodes, meltdowns, and advocate banter.",
                "state_register_id": make_reg_id(rk),
                "install_status": "1",
                "operational_status": "1",
            }
            ci_by_key[rk] = room_node
            ci_by_key[rk.lower()] = room_node

    unique_cis_map: Dict[str, Dict[str, Any]] = {}
    for c in list(base_cis) + list(pantheon_cis):
        unique_cis_map[c["ci_key"]] = c
    for rk in sorted(referenced_rooms):
        resolved = ci_by_key.get(rk) or ci_by_key.get(rk.lower())
        if resolved and resolved["ci_key"] not in unique_cis_map:
            unique_cis_map[resolved["ci_key"]] = resolved

    all_cis = list(unique_cis_map.values())

    existing_rels: List[Dict[str, Any]] = []
    rel_seen: Set[Tuple[str, str]] = set()

    def add_merged_rel(src_key: str, dst_key: str, rel_label: str) -> None:
        src_ci = ci_by_key.get(src_key) or ci_by_key.get(src_key.lower())
        dst_ci = ci_by_key.get(dst_key) or ci_by_key.get(dst_key.lower())
        if not src_ci or not dst_ci:
            return
        sk = src_ci["ci_key"]
        dk = dst_ci["ci_key"]
        if sk == dk or (sk, dk) in rel_seen:
            return
        rel_seen.add((sk, dk))
        existing_rels.append(
            {
                "sys_id": make_sys_id(f"rel_{sk}_{dk}"),
                "parent": {"value": src_ci["sys_id"], "display_value": sk},
                "child": {"value": dst_ci["sys_id"], "display_value": dk},
                "type": {"value": rel_label, "display_value": rel_label},
                "parent_key": dst_ci["ci_key"],
                "parent_sys_id": dst_ci["sys_id"],
                "child_key": src_ci["ci_key"],
                "child_sys_id": src_ci["sys_id"],
                "type_sys_id": REL_TYPE_SYS_ID,
            }
        )

    for src_k, dst_k, rel_lbl in normalized_base_rels:
        add_merged_rel(src_k, dst_k, rel_lbl)
    for src_k, dst_k, rel_lbl in pantheon_edges:
        add_merged_rel(src_k, dst_k, rel_lbl)

    if write_cartridges and DATA_DIR.exists():
        try:
            class_counts: Dict[str, int] = {}
            for c in all_cis:
                cls = c.get("sys_class_name", "cmdb_ci")
                class_counts[cls] = class_counts.get(cls, 0) + 1

            ci_out = {
                "total_cis": len(all_cis),
                "total_relationships": len(existing_rels),
                "generated_at": utc_now_iso(),
                "class_counts": class_counts,
                "causal_spines": new_spines,
                "result": all_cis,
                "cis": all_cis,
            }
            rel_out = {
                "total_relationships": len(existing_rels),
                "generated_at": utc_now_iso(),
                "result": existing_rels,
                "relationships": existing_rels,
            }
            ci_payload = json.dumps(ci_out, indent=2)
            rel_payload = json.dumps(rel_out, indent=2)

            for p in CI_JSON_PATHS:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(ci_payload, encoding="utf-8")
            for p in REL_JSON_PATHS:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(rel_payload, encoding="utf-8")
            if DIST_DIR.exists():
                (DIST_DIR / "fanstack_cmdb_ci.json").write_text(ci_payload, encoding="utf-8")
                (DIST_DIR / "fanstack_cmdb_rel_ci.json").write_text(rel_payload, encoding="utf-8")
        except Exception as exc:
            logger.warning("Non-fatal error writing local JSON cartridges: %s", exc)

    return all_cis, existing_rels, pruned_room_keys


# =============================================================================
# 7. MERKLE DELTA SYNC ENGINE ORCHESTRATOR
# =============================================================================


class MerkleDeltaSyncEngine:
    """
    Core Content-Addressable Merkle Delta Sync Engine.
    Coordinates SQLite WAL cache comparison, optional full remote reconciliation,
    adaptive worker execution, and atomic state commits.
    """

    def __init__(
        self,
        cache: LocalSQLiteWALCache,
        client: AdaptiveServiceNowClient,
    ) -> None:
        self.cache = cache
        self.client = client

    def reconcile_cache_with_remote(
        self,
        local_cis_by_key: Dict[str, Dict[str, Any]],
        purge_orphans: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute `--full-reconcile`: fetch remote CIs and relationships from ServiceNow PDI,
        seed/repair `sn_ci_cache` and `sn_rel_cache` mappings, and optionally identify
        remote bot/orphan records for deletion.
        """
        logger.info("Executing full remote state reconciliation against %s ...", self.client.instance_url)
        remote_cis = self.client.fetch_paged_table(
            "cmdb_ci",
            fields="sys_id,name,sys_class_name,short_description,install_status,operational_status,u_correlation_id",
            page_size=500,
        )
        remote_rels = self.client.fetch_paged_table(
            "cmdb_rel_ci",
            fields="sys_id,parent,child,type",
            page_size=500,
        )

        existing_ci_cache = self.cache.load_ci_cache()
        now_ts = utc_now_iso()
        ci_upserts: List[Tuple[str, str, str, str, str, str]] = []
        remote_sys_id_to_key: Dict[str, str] = {}
        remote_prune_targets: List[Tuple[str, str, str]] = []

        for r_ci in remote_cis:
            nm = str(r_ci.get("name") or "").strip()
            sid = str(r_ci.get("sys_id") or "").strip()
            s_cls = str(r_ci.get("sys_class_name") or "cmdb_ci").strip()
            if not nm or not sid:
                continue
            remote_sys_id_to_key[sid] = nm

            if purge_orphans:
                flagged, reason = classify_prune_candidate(r_ci)
                if flagged and nm not in local_cis_by_key:
                    remote_prune_targets.append((nm, sid, reason))
                    continue

            cached = existing_ci_cache.get(nm)
            if cached and cached.sys_id == sid:
                # Preserve existing content_sha256 if already verified
                continue

            # Compute remote baseline hash if record matches local canonical format,
            # otherwise mark with a sentinel hash so delta engine will issue a surgical PATCH if needed.
            if nm in local_cis_by_key:
                local_payload = build_canonical_ci_payload(local_cis_by_key[nm])
                remote_short = str(r_ci.get("short_description") or "").strip()
                if remote_short == local_payload["short_description"]:
                    digest = compute_canonical_sha256(local_payload)
                    payload_str = json.dumps(local_payload, sort_keys=True, separators=(",", ":"))
                else:
                    digest = "REMOTE_DRIFT_" + make_sys_id(remote_short)
                    payload_str = json.dumps(r_ci, sort_keys=True, separators=(",", ":"))
            else:
                digest = "REMOTE_UNTRACKED_" + sid
                payload_str = json.dumps(r_ci, sort_keys=True, separators=(",", ":"))

            ci_upserts.append((nm, sid, s_cls, digest, payload_str, now_ts))

        if not dry_run and ci_upserts:
            self.cache.upsert_ci_batch(ci_upserts)

        rel_upserts: List[Tuple[str, str, str, str, str, str]] = []
        remote_orphan_rel_sids: List[str] = []
        pruned_sids = {sid for _, sid, _ in remote_prune_targets}

        for r_rel in remote_rels:
            rel_sid = str(r_rel.get("sys_id") or "").strip()
            p_obj = r_rel.get("parent")
            c_obj = r_rel.get("child")
            t_obj = r_rel.get("type")
            p_sid = str(p_obj.get("value") if isinstance(p_obj, dict) else p_obj or "").strip()
            c_sid = str(c_obj.get("value") if isinstance(c_obj, dict) else c_obj or "").strip()
            t_sid = str(t_obj.get("value") if isinstance(t_obj, dict) else t_obj or REL_TYPE_SYS_ID).strip()

            if not rel_sid or not p_sid or not c_sid:
                continue

            p_key = remote_sys_id_to_key.get(p_sid)
            c_key = remote_sys_id_to_key.get(c_sid)
            if not p_key or not c_key or p_sid in pruned_sids or c_sid in pruned_sids:
                if purge_orphans:
                    remote_orphan_rel_sids.append(rel_sid)
                continue

            rel_payload = {"parent_key": p_key, "child_key": c_key, "type": t_sid}
            rel_hash = compute_canonical_sha256(rel_payload)
            rel_upserts.append((p_key, c_key, t_sid, rel_sid, rel_hash, now_ts))

        if not dry_run and rel_upserts:
            self.cache.upsert_rel_batch(rel_upserts)

        return {
            "remote_cis_scanned": len(remote_cis),
            "remote_rels_scanned": len(remote_rels),
            "cache_ci_seeded": len(ci_upserts),
            "cache_rel_seeded": len(rel_upserts),
            "remote_prune_candidates": remote_prune_targets,
            "remote_orphan_rel_sys_ids": remote_orphan_rel_sids,
        }

    def compute_delta_plan(
        self,
        all_cis: Sequence[Dict[str, Any]],
        all_rels: Sequence[Dict[str, Any]],
        pruned_room_keys: Sequence[str],
        purge_orphans: bool = False,
        extra_remote_prunes: Optional[Sequence[Tuple[str, str, str]]] = None,
    ) -> DeltaPlan:
        """
        Compute the Content-Addressable Merkle Delta Plan in-memory against the
        SQLite WAL cache (`sn_ci_cache` and `sn_rel_cache`) with 0 network calls.
        """
        t0 = time.perf_counter()
        ci_cache = self.cache.load_ci_cache()
        rel_cache = self.cache.load_rel_cache()
        prev_merkle = self.cache.get_last_merkle_root()

        leaf_hashes: List[str] = []
        ci_creates: List[Tuple[Dict[str, Any], Dict[str, str], str]] = []
        ci_updates: List[Tuple[Dict[str, Any], Dict[str, str], str, str]] = []
        ci_skips = 0

        active_ci_keys: Set[str] = set()
        for ci in all_cis:
            ci_key = str(ci.get("ci_key") or ci.get("name") or "").strip()
            if not ci_key:
                continue
            active_ci_keys.add(ci_key)
            payload = build_canonical_ci_payload(ci)
            digest = compute_canonical_sha256(payload)
            leaf_hashes.append(f"ci:{ci_key}:{digest}")

            cached = ci_cache.get(ci_key)
            if cached is None or not cached.sys_id:
                ci_creates.append((ci, payload, digest))
            elif cached.content_sha256 == digest:
                ci_skips += 1
            else:
                ci_updates.append((ci, payload, digest, cached.sys_id))

        # Identify cached CIs that should be pruned
        ci_prunes: List[Tuple[str, str, str]] = []
        seen_prune_keys: Set[str] = set()
        for rk in pruned_room_keys:
            if rk in ci_cache and rk not in seen_prune_keys:
                seen_prune_keys.add(rk)
                ci_prunes.append((rk, ci_cache[rk].sys_id, "PRUNED_EMPTY_STAGED_ROOM"))

        if purge_orphans:
            for cached_key, cached_rec in ci_cache.items():
                if cached_key in seen_prune_keys or cached_key in active_ci_keys:
                    continue
                flagged, reason = classify_prune_candidate(
                    {"ci_key": cached_key, "name": cached_key, "sys_class_name": cached_rec.sys_class_name}
                )
                if flagged:
                    seen_prune_keys.add(cached_key)
                    ci_prunes.append((cached_key, cached_rec.sys_id, reason))

        if extra_remote_prunes:
            for rk, rsid, reason in extra_remote_prunes:
                if rk not in seen_prune_keys:
                    seen_prune_keys.add(rk)
                    ci_prunes.append((rk, rsid, reason))

        # Evaluate relationships against sn_rel_cache
        rel_creates: List[Tuple[str, str, str, str]] = []
        rel_skips = 0
        active_rel_keys: Set[Tuple[str, str, str]] = set()

        for rel in all_rels:
            p_key = str(rel.get("parent_key") or "").strip()
            c_key = str(rel.get("child_key") or "").strip()
            t_sid = str(rel.get("type_sys_id") or REL_TYPE_SYS_ID).strip()
            if not p_key or not c_key:
                continue
            rel_tuple = (p_key, c_key, t_sid)
            if rel_tuple in active_rel_keys:
                continue
            active_rel_keys.add(rel_tuple)

            rel_digest = compute_canonical_sha256(
                {"parent_key": p_key, "child_key": c_key, "type": t_sid}
            )
            leaf_hashes.append(f"rel:{p_key}->{c_key}:{t_sid}:{rel_digest}")

            cached_rel = rel_cache.get(rel_tuple)
            if (
                cached_rel is not None
                and cached_rel.sys_id
                and (not cached_rel.content_sha256 or cached_rel.content_sha256 == rel_digest)
                and p_key not in seen_prune_keys
                and c_key not in seen_prune_keys
            ):
                rel_skips += 1
            else:
                rel_creates.append((p_key, c_key, t_sid, rel_digest))

        rel_prunes: List[Tuple[str, str, str, str]] = []
        if purge_orphans or seen_prune_keys:
            for (p_key, c_key, t_sid), cached_rel in rel_cache.items():
                if p_key in seen_prune_keys or c_key in seen_prune_keys:
                    if cached_rel.sys_id:
                        rel_prunes.append((p_key, c_key, t_sid, cached_rel.sys_id))

        merkle_root = compute_merkle_root(leaf_hashes)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return DeltaPlan(
            merkle_root=merkle_root,
            previous_merkle_root=prev_merkle,
            total_local_cis=len(active_ci_keys),
            total_local_rels=len(active_rel_keys),
            ci_creates=ci_creates,
            ci_updates=ci_updates,
            ci_skips=ci_skips,
            ci_prunes=ci_prunes,
            rel_creates=rel_creates,
            rel_skips=rel_skips,
            rel_prunes=rel_prunes,
            delta_compute_ms=elapsed_ms,
        )

    def execute_delta_plan(
        self,
        plan: DeltaPlan,
        mode_label: str = "DELTA_ONLY",
        dry_run: bool = False,
        extra_orphan_rel_sys_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the computed DeltaPlan against ServiceNow using the adaptive worker pool
        and atomically commit all resulting state transitions to `sn_ci_cache` and `sn_rel_cache`.
        """
        started_at = utc_now_iso()
        t0 = time.perf_counter()

        if dry_run:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0 + plan.delta_compute_ms, 3)
            return {
                "status": "DRY_RUN_READY",
                "mode": f"{mode_label}_DRY_RUN",
                "merkle_root": plan.merkle_root,
                "previous_merkle_root": plan.previous_merkle_root,
                "merkle_epoch_unchanged": plan.merkle_root == plan.previous_merkle_root,
                "delta_compute_ms": plan.delta_compute_ms,
                "total_elapsed_ms": elapsed_ms,
                "ci_metrics": {
                    "total_evaluated": plan.total_local_cis,
                    "to_create_post": len(plan.ci_creates),
                    "to_update_patch": len(plan.ci_updates),
                    "skipped_zero_network": plan.ci_skips,
                    "to_prune_delete": len(plan.ci_prunes),
                    "cache_hit_ratio": round(
                        plan.ci_skips / max(1, plan.total_local_cis), 4
                    ),
                },
                "relationship_metrics": {
                    "total_evaluated": plan.total_local_rels,
                    "to_create_post": len(plan.rel_creates),
                    "skipped_zero_network": plan.rel_skips,
                    "to_prune_delete": len(plan.rel_prunes)
                    + len(extra_orphan_rel_sys_ids or []),
                    "cache_hit_ratio": round(
                        plan.rel_skips / max(1, plan.total_local_rels), 4
                    ),
                },
                "network_telemetry": {
                    "http_requests_transmitted": 0,
                    "http_retries": 0,
                    "worker_pool_size": self.client.max_workers,
                },
            }

        ci_cache = self.cache.load_ci_cache()
        ci_key_to_sys_id: Dict[str, str] = {
            k: rec.sys_id for k, rec in ci_cache.items() if rec.sys_id
        }

        # 1. Prune flagged CIs
        pruned_ci_keys: List[str] = []

        def _prune_ci_worker(item: Tuple[str, str, str]) -> Optional[str]:
            ck, sid, _reason = item
            resp = self.client.request("DELETE", f"/api/now/table/cmdb_ci/{sid}")
            if resp.status_code in (200, 204, 404):
                return ck
            return None

        if plan.ci_prunes:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                for deleted_key in pool.map(_prune_ci_worker, plan.ci_prunes):
                    if deleted_key:
                        pruned_ci_keys.append(deleted_key)
                        ci_key_to_sys_id.pop(deleted_key, None)
            self.cache.delete_ci_keys(pruned_ci_keys)

        # 2. Create new CIs (POST /api/now/table/cmdb_ci) and Update mutated CIs (PATCH /api/now/table/cmdb_ci/{sys_id})
        ci_created_count = 0
        ci_updated_count = 0
        ci_cache_upserts: List[Tuple[str, str, str, str, str, str]] = []

        def _create_ci_worker(
            item: Tuple[Dict[str, Any], Dict[str, str], str]
        ) -> Optional[Tuple[str, str, str, str, str, str]]:
            _ci, payload, digest = item
            ck = payload["name"]
            s_cls = payload["sys_class_name"]
            resp = self.client.request(
                "POST",
                "/api/now/table/cmdb_ci",
                json_payload=payload,
            )
            if resp.status_code in (200, 201):
                sid = str(resp.json().get("result", {}).get("sys_id") or "").strip()
                if sid:
                    return (
                        ck,
                        sid,
                        s_cls,
                        digest,
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        utc_now_iso(),
                    )
            return None

        def _update_ci_worker(
            item: Tuple[Dict[str, Any], Dict[str, str], str, str]
        ) -> Optional[Tuple[str, str, str, str, str, str]]:
            _ci, payload, digest, sid = item
            ck = payload["name"]
            s_cls = payload["sys_class_name"]
            resp = self.client.request(
                "PATCH",
                f"/api/now/table/cmdb_ci/{sid}",
                json_payload=payload,
            )
            if resp.status_code in (200, 201):
                return (
                    ck,
                    sid,
                    s_cls,
                    digest,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    utc_now_iso(),
                )
            if resp.status_code == 404:
                # Remote record was deleted outside cache; recreate via POST
                post_resp = self.client.request(
                    "POST",
                    "/api/now/table/cmdb_ci",
                    json_payload=payload,
                )
                if post_resp.status_code in (200, 201):
                    new_sid = str(
                        post_resp.json().get("result", {}).get("sys_id") or ""
                    ).strip()
                    if new_sid:
                        return (
                            ck,
                            new_sid,
                            s_cls,
                            digest,
                            json.dumps(payload, sort_keys=True, separators=(",", ":")),
                            utc_now_iso(),
                        )
            return None

        if plan.ci_creates:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                for res in pool.map(_create_ci_worker, plan.ci_creates):
                    if res:
                        ci_created_count += 1
                        ci_cache_upserts.append(res)
                        ci_key_to_sys_id[res[0]] = res[1]

        if plan.ci_updates:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                for res in pool.map(_update_ci_worker, plan.ci_updates):
                    if res:
                        ci_updated_count += 1
                        ci_cache_upserts.append(res)
                        ci_key_to_sys_id[res[0]] = res[1]

        if ci_cache_upserts:
            self.cache.upsert_ci_batch(ci_cache_upserts)

        # 3. Prune orphaned relationships
        pruned_rel_keys: List[Tuple[str, str, str]] = []
        pruned_rel_count = 0

        def _prune_rel_worker(item: Tuple[str, str, str, str]) -> Optional[Tuple[str, str, str]]:
            p_k, c_k, t_sid, r_sid = item
            resp = self.client.request("DELETE", f"/api/now/table/cmdb_rel_ci/{r_sid}")
            if resp.status_code in (200, 204, 404):
                return (p_k, c_k, t_sid)
            return None

        if plan.rel_prunes:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                for r_key in pool.map(_prune_rel_worker, plan.rel_prunes):
                    if r_key:
                        pruned_rel_keys.append(r_key)
                        pruned_rel_count += 1
            self.cache.delete_rel_keys(pruned_rel_keys)

        if extra_orphan_rel_sys_ids:
            def _prune_raw_rel_sid(r_sid: str) -> int:
                resp = self.client.request("DELETE", f"/api/now/table/cmdb_rel_ci/{r_sid}")
                return 1 if resp.status_code in (200, 204, 404) else 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                pruned_rel_count += sum(pool.map(_prune_raw_rel_sid, extra_orphan_rel_sys_ids))

        # 4. Create missing relationships
        rel_created_count = 0
        rel_cache_upserts: List[Tuple[str, str, str, str, str, str]] = []

        resolvable_rel_creates: List[Tuple[str, str, str, str, str, str]] = []
        for p_key, c_key, t_sid, rel_digest in plan.rel_creates:
            p_sys = ci_key_to_sys_id.get(p_key)
            c_sys = ci_key_to_sys_id.get(c_key)
            if p_sys and c_sys:
                resolvable_rel_creates.append((p_key, c_key, t_sid, p_sys, c_sys, rel_digest))

        def _create_rel_worker(
            item: Tuple[str, str, str, str, str, str]
        ) -> Optional[Tuple[str, str, str, str, str, str]]:
            p_key, c_key, t_sid, p_sys, c_sys, rel_digest = item
            resp = self.client.request(
                "POST",
                "/api/now/table/cmdb_rel_ci",
                json_payload={"parent": p_sys, "child": c_sys, "type": t_sid},
            )
            if resp.status_code in (200, 201):
                r_sid = str(
                    resp.json().get("result", {}).get("sys_id")
                    or make_sys_id(f"rel_{p_key}_{c_key}_{t_sid}")
                ).strip()
                return (p_key, c_key, t_sid, r_sid, rel_digest, utc_now_iso())
            return None

        if resolvable_rel_creates:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.client.max_workers) as pool:
                for res in pool.map(_create_rel_worker, resolvable_rel_creates):
                    if res:
                        rel_created_count += 1
                        rel_cache_upserts.append(res)

        if rel_cache_upserts:
            self.cache.upsert_rel_batch(rel_cache_upserts)

        completed_at = utc_now_iso()
        total_elapsed_ms = round((time.perf_counter() - t0) * 1000.0 + plan.delta_compute_ms, 3)

        self.cache.record_sync_run(
            started_at=started_at,
            completed_at=completed_at,
            mode=mode_label,
            merkle_root=plan.merkle_root,
            total_cis=plan.total_local_cis,
            ci_created=ci_created_count,
            ci_updated=ci_updated_count,
            ci_skipped=plan.ci_skips,
            ci_pruned=len(pruned_ci_keys),
            rel_created=rel_created_count,
            rel_skipped=plan.rel_skips,
            rel_pruned=pruned_rel_count,
            http_requests=self.client.http_requests,
            http_retries=self.client.http_retries,
            elapsed_ms=total_elapsed_ms,
        )

        return {
            "status": "SYNCHRONIZED",
            "mode": mode_label,
            "merkle_root": plan.merkle_root,
            "previous_merkle_root": plan.previous_merkle_root,
            "merkle_epoch_unchanged": plan.merkle_root == plan.previous_merkle_root,
            "delta_compute_ms": plan.delta_compute_ms,
            "total_elapsed_ms": total_elapsed_ms,
            "ci_metrics": {
                "total_evaluated": plan.total_local_cis,
                "created_post": ci_created_count,
                "updated_patch": ci_updated_count,
                "skipped_zero_network": plan.ci_skips,
                "pruned_delete": len(pruned_ci_keys),
                "cache_hit_ratio": round(
                    plan.ci_skips / max(1, plan.total_local_cis), 4
                ),
            },
            "relationship_metrics": {
                "total_evaluated": plan.total_local_rels,
                "created_post": rel_created_count,
                "skipped_zero_network": plan.rel_skips,
                "pruned_delete": pruned_rel_count,
                "cache_hit_ratio": round(
                    plan.rel_skips / max(1, plan.total_local_rels), 4
                ),
            },
            "network_telemetry": {
                "http_requests_transmitted": self.client.http_requests,
                "http_retries": self.client.http_retries,
                "status_429_throttles": self.client.status_429_count,
                "status_5xx_errors": self.client.status_5xx_count,
                "worker_pool_size": self.client.max_workers,
            },
        }


# =============================================================================
# 8. OPTIONAL POSIX VFS MATERIALIZER (`--sync-vfs`)
# =============================================================================


def materialize_posix_vfs(roots: Optional[Sequence[Path]] = None) -> List[str]:
    """Materialize physical and logical CIs into a sysfs-style POSIX directory tree."""
    target_roots = list(roots) if roots is not None else [VFS_CMDB_PERSIST, VFS_CMDB_SHM]
    synced: List[str] = []

    def _write_atomic(filepath: Path, content: str) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(str(content).strip() + "\n", encoding="utf-8")

    def _create_symlink(source: Path, link_name: Path) -> None:
        link_name.parent.mkdir(parents=True, exist_ok=True)
        if link_name.is_symlink() or link_name.is_file():
            link_name.unlink()
        elif link_name.is_dir():
            shutil.rmtree(link_name)
        rel_path = os.path.relpath(source, link_name.parent)
        link_name.symlink_to(rel_path)

    for root in target_roots:
        try:
            phys = root / "physical"
            clio = phys / "clio"
            _write_atomic(clio / "id.txt", "hw_clio")
            _write_atomic(clio / "role.txt", "primary_host")
            _write_atomic(clio / "silicon.txt", "AMD Ryzen 7 7735HS (8C/16T)")
            _write_atomic(clio / "ram_gb.txt", "32")
            _write_atomic(clio / "storage.txt", "1TB NVMe PCIe 4.0")
            _write_atomic(clio / "ip.txt", "100.73.155.70")
            _write_atomic(clio / "lan_ip.txt", "192.168.1.183")
            _write_atomic(clio / "os.txt", "Ubuntu 24.04 LTS")
            _write_atomic(clio / "status.txt", "ACTIVE")

            artemis = phys / "artemis"
            _write_atomic(artemis / "id.txt", "hw_artemis")
            _write_atomic(artemis / "role.txt", "cuda_transcode_node")
            _write_atomic(artemis / "gpu.txt", "NVIDIA GeForce GTX 1060 6GB GDDR5")
            _write_atomic(artemis / "ip.txt", "100.108.185.53")
            _write_atomic(artemis / "status.txt", "ACTIVE")

            pegasus = phys / "pegasus"
            _write_atomic(pegasus / "id.txt", "hw_pegasus")
            _write_atomic(pegasus / "role.txt", "visual_sentry_terminal")
            _write_atomic(pegasus / "ip.txt", "100.96.77.20")
            _write_atomic(pegasus / "status.txt", "ACTIVE")

            c120 = phys / "c120"
            _write_atomic(c120 / "id.txt", "hw_tapo_c120")
            _write_atomic(c120 / "role.txt", "smyrna_optical_sentry")
            _write_atomic(c120 / "lan_ip.txt", "192.168.1.191")
            _write_atomic(c120 / "status.txt", "ACTIVE")

            argo = phys / "argo"
            _write_atomic(argo / "id.txt", "hw_argo")
            _write_atomic(argo / "role.txt", "vision_sensor_sentry")
            _write_atomic(argo / "ip.txt", "100.111.248.60")
            _write_atomic(argo / "status.txt", "ACTIVE")

            log = root / "logical"
            faas = log / "faas_server"
            _write_atomic(faas / "id.txt", "svc_faas_server")
            _write_atomic(faas / "service.txt", "faas_server.service")
            _write_atomic(faas / "port.txt", "3033")
            _write_atomic(faas / "status.txt", "ACTIVE")
            _create_symlink(clio, faas / "runs_on")

            retina = log / "stacklabs_retina"
            _write_atomic(retina / "id.txt", "svc_stacklabs_retina")
            _write_atomic(retina / "service.txt", "stacklabs-retina.service")
            _write_atomic(retina / "port.txt", "3028")
            _write_atomic(retina / "status.txt", "ACTIVE")
            _create_symlink(clio, retina / "runs_on")
            _create_symlink(c120, retina / "ingests_from")

            sniper = log / "stream_sniper"
            _write_atomic(sniper / "id.txt", "svc_stream_sniper")
            _write_atomic(sniper / "service.txt", "stream_sniper_daemon.service")
            _write_atomic(sniper / "port.txt", "5056")
            _write_atomic(sniper / "status.txt", "ACTIVE")
            _create_symlink(clio, sniper / "runs_on")
            _create_symlink(artemis, sniper / "transcribes_on")

            synced.append(str(root))
        except Exception as exc:
            logger.warning("Failed VFS materialization at %s: %s", root, exc)

    return synced


# =============================================================================
# 9. CLI ENTRYPOINT
# =============================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StackLabs ServiceNow Cloud PDI — Content-Addressable Merkle Delta Sync Engine"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--delta-only",
        action="store_true",
        default=True,
        help="Default: sync only created/modified CIs and relationships via local SQLite WAL SHA-256 diff.",
    )
    mode_group.add_argument(
        "--full-reconcile",
        action="store_true",
        help="Page remote ServiceNow tables to warm/reconcile local SQLite WAL cache before applying deltas.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute Merkle root and delta statistics without transmitting mutating HTTP requests.",
    )
    parser.add_argument(
        "--purge-orphans",
        action="store_true",
        help="Prune synthetic bot CIs, banned relic classes, and unreferenced staged room shells.",
    )
    parser.add_argument(
        "--harvest-mode",
        choices=("unified", "grounded", "degenerate"),
        default="unified",
        help="Harvest scope: unified (default), grounded (ITSM + core broadcast), or degenerate (full FanStack).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Adaptive worker pool concurrency (clamped between 1 and 6; default: 5).",
    )
    parser.add_argument(
        "--cache-db",
        type=Path,
        default=DEFAULT_CACHE_DB,
        help="Path to local SQLite WAL cache database (default: data/servicenow_pdi_cache.db).",
    )
    parser.add_argument(
        "--input-cartridge",
        type=Path,
        default=None,
        help="Optional path to a specific CMDB CI JSON cartridge file to load.",
    )
    parser.add_argument(
        "--no-write-cartridges",
        action="store_true",
        help="Do not overwrite local JSON cartridge files during harvest.",
    )
    parser.add_argument(
        "--sync-vfs",
        action="store_true",
        help="Also materialize the POSIX VFS CMDB tree.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    instance_url, username, password = resolve_credentials()
    cache = LocalSQLiteWALCache(db_path=args.cache_db)
    client = AdaptiveServiceNowClient(
        instance_url=instance_url,
        username=username,
        password=password,
        max_workers=args.workers,
    )
    engine = MerkleDeltaSyncEngine(cache=cache, client=client)

    all_cis, all_rels, pruned_rooms = harvest_unified_cmdb(
        mode=args.harvest_mode,
        input_cartridge=args.input_cartridge,
        write_cartridges=not args.no_write_cartridges,
    )
    local_cis_by_key = {c["ci_key"]: c for c in all_cis}

    reconcile_summary: Optional[Dict[str, Any]] = None
    extra_remote_prunes: List[Tuple[str, str, str]] = []
    extra_orphan_rel_sids: List[str] = []

    if args.full_reconcile and not args.dry_run:
        reconcile_summary = engine.reconcile_cache_with_remote(
            local_cis_by_key=local_cis_by_key,
            purge_orphans=args.purge_orphans,
            dry_run=args.dry_run,
        )
        extra_remote_prunes = reconcile_summary.get("remote_prune_candidates", [])
        extra_orphan_rel_sids = reconcile_summary.get("remote_orphan_rel_sys_ids", [])

    plan = engine.compute_delta_plan(
        all_cis=all_cis,
        all_rels=all_rels,
        pruned_room_keys=pruned_rooms,
        purge_orphans=args.purge_orphans,
        extra_remote_prunes=extra_remote_prunes,
    )

    mode_label = "FULL_RECONCILE" if args.full_reconcile else "DELTA_ONLY"
    sync_result = engine.execute_delta_plan(
        plan=plan,
        mode_label=mode_label,
        dry_run=args.dry_run,
        extra_orphan_rel_sys_ids=extra_orphan_rel_sids,
    )

    if args.sync_vfs and not args.dry_run:
        sync_result["vfs_materialized_roots"] = materialize_posix_vfs()

    if reconcile_summary is not None:
        sync_result["remote_reconciliation"] = {
            "remote_cis_scanned": reconcile_summary["remote_cis_scanned"],
            "remote_rels_scanned": reconcile_summary["remote_rels_scanned"],
            "cache_ci_seeded": reconcile_summary["cache_ci_seeded"],
            "cache_rel_seeded": reconcile_summary["cache_rel_seeded"],
        }

    print(json.dumps(sync_result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())