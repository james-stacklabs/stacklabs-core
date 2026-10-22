#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs 10-Second Sliding Velocity Ring & Post-FINAL Flatline Toe-Tag Coroner.
Computes 6-hop x 10s rolling velocity to eliminate fixed-minute boundary dilution.
Evaluates the Post-FINAL Flatline Gate: triggers when rolling velocity decays to <= 20%
of peak burst velocity for 30 consecutive seconds (3 x 10s ticks) after game status is FINAL.
Commits verified Toe-Tag receipts to SQLite WAL (morning_wiretap.db:toe_tag_receipts)
and atomic shared memory (/dev/shm/faas_vfs/body_bags.json).
"""

import argparse
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("stacklabs.toe_tag_coroner")

WIRETAP_DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
SHM_FAAS_DIR = Path("/dev/shm/faas_vfs")
BODY_BAGS_SHM_PATH = SHM_FAAS_DIR / "body_bags.json"
BARF_RECEIPTS_SHM_PATH = SHM_FAAS_DIR / "barf_receipts.json"

FLATLINE_RATIO_THRESHOLD = 0.20  # 20% of peak velocity
FLATLINE_HOLD_SECONDS = 30       # 30 consecutive seconds (3 x 10s steps)
SUB_BUCKET_SECONDS = 10
SLIDING_HOPS = 6                 # 6 x 10s = 60s rolling window


def get_wal_connection(db_path: Path = WIRETAP_DB_PATH) -> sqlite3.Connection:
    """Open SQLite connection with mandatory Argon Law 3 WAL pragmas."""
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def atomic_write_json(target_path: Path, payload: Any) -> None:
    """Write JSON atomically via process-scoped .tmp + os.replace()."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(f".tmp.{os.getpid()}")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, target_path)


def ensure_toe_tag_schema(conn: sqlite3.Connection) -> None:
    """Ensure toe_tag_receipts table exists in morning_wiretap.db."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS toe_tag_receipts (
            game_id TEXT PRIMARY KEY,
            channel_key TEXT NOT NULL,
            matchup_title TEXT NOT NULL,
            final_score TEXT NOT NULL,
            game_status TEXT NOT NULL,
            time_of_death_epoch INTEGER NOT NULL,
            flatline_triggered_epoch INTEGER NOT NULL,
            stream_start_epoch INTEGER NOT NULL,
            vod_seek_seconds INTEGER NOT NULL,
            peak_velocity_mps REAL NOT NULL,
            peak_velocity_cpm REAL NOT NULL,
            peak_sigma REAL NOT NULL,
            flatline_threshold_mps REAL NOT NULL,
            terminal_velocity_mps REAL NOT NULL,
            cause_shibboleth TEXT NOT NULL,
            sample_kill_quote TEXT NOT NULL,
            barf_call_type TEXT NOT NULL,
            barf_verdict_text TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_toe_tag_time_of_death
        ON toe_tag_receipts(time_of_death_epoch DESC)
        """
    )
    conn.commit()


def compute_sliding_10s_ring(
    epoch_timestamps: Sequence[float],
    eval_end_epoch: Optional[int] = None,
    flatline_ratio: float = FLATLINE_RATIO_THRESHOLD,
    flatline_hold_sec: int = FLATLINE_HOLD_SECONDS,
) -> Dict[str, Any]:
    """
    Quantize message timestamps into 10-second sub-buckets:
        b10 = (int(ts) // 10) * 10
    Compute 6-hop rolling 60s velocity at every 10s step:
        V_60(t) = sum_{k=0..5} hits[t - 10k] / 60.0
    Evaluate post-peak flatline decay:
        Triggers when V_60(t) <= flatline_ratio * peak_velocity_mps
        for flatline_hold_sec consecutive seconds (3 x 10s steps) after peak_center_epoch.
    """
    valid_epochs = sorted(int(ts) for ts in epoch_timestamps if ts is not None and ts > 0)
    if not valid_epochs:
        return {
            "total_messages": 0,
            "stream_start_epoch": 0,
            "last_message_epoch": 0,
            "peak_velocity_mps": 0.0,
            "peak_velocity_cpm": 0.0,
            "peak_center_epoch": 0,
            "peak_window_hits": 0,
            "mean_velocity_mps": 0.0,
            "std_velocity_mps": 0.0,
            "peak_sigma": 0.0,
            "flatline_threshold_mps": 0.0,
            "flatline_triggered": False,
            "flatline_triggered_epoch": 0,
            "terminal_velocity_mps": 0.0,
            "minute_peak_mps": {},
        }

    bins_10s: Dict[int, int] = {}
    for ts in valid_epochs:
        b10 = (ts // SUB_BUCKET_SECONDS) * SUB_BUCKET_SECONDS
        bins_10s[b10] = bins_10s.get(b10, 0) + 1

    first_bin = min(bins_10s.keys())
    last_msg_bin = max(bins_10s.keys())
    end_bin = (
        (int(eval_end_epoch) // SUB_BUCKET_SECONDS) * SUB_BUCKET_SECONDS
        if eval_end_epoch and int(eval_end_epoch) > last_msg_bin
        else last_msg_bin
    )

    # Cap lookback horizon to 6 hours (2160 x 10s steps) to keep computation bounded
    if (end_bin - first_bin) // SUB_BUCKET_SECONDS > 2160:
        first_bin = end_bin - (2160 * SUB_BUCKET_SECONDS)

    steps: List[Tuple[int, int, float]] = []
    minute_peak_mps: Dict[int, float] = {}

    for step_t in range(first_bin, end_bin + SUB_BUCKET_SECONDS, SUB_BUCKET_SECONDS):
        window_hits = sum(
            bins_10s.get(step_t - (SUB_BUCKET_SECONDS * k), 0)
            for k in range(SLIDING_HOPS)
        )
        v_mps = round(window_hits / 60.0, 4)
        steps.append((step_t, window_hits, v_mps))
        m_bucket = (step_t // 60) * 60
        if v_mps > minute_peak_mps.get(m_bucket, 0.0):
            minute_peak_mps[m_bucket] = round(v_mps, 3)

    peak_step, peak_hits, peak_v = max(steps, key=lambda x: (x[2], x[0]))

    velocities = [x[2] for x in steps]
    n_steps = len(velocities)
    mean_v = sum(velocities) / n_steps if n_steps else 0.0
    variance = (
        sum((v - mean_v) ** 2 for v in velocities) / n_steps if n_steps > 1 else 0.0
    )
    std_v = math.sqrt(variance)
    effective_std = max(std_v, 0.05)
    peak_sigma = round((peak_v - mean_v) / effective_std, 2) if peak_v > 0 else 0.0

    # Evaluate 20% of peak velocity for 30 consecutive seconds (3 x 10s ticks) after peak
    flatline_threshold = round(peak_v * flatline_ratio, 4)
    required_ticks = max(1, flatline_hold_sec // SUB_BUCKET_SECONDS)
    consecutive_below = 0
    flatline_triggered = False
    flatline_epoch = 0

    for step_t, _, v_mps in steps:
        if step_t <= peak_step:
            continue
        if v_mps <= flatline_threshold:
            consecutive_below += 1
            if consecutive_below >= required_ticks:
                flatline_triggered = True
                flatline_epoch = step_t
                break
        else:
            consecutive_below = 0

    terminal_v = steps[-1][2] if steps else 0.0

    return {
        "total_messages": len(valid_epochs),
        "stream_start_epoch": valid_epochs[0],
        "last_message_epoch": valid_epochs[-1],
        "peak_velocity_mps": round(peak_v, 3),
        "peak_velocity_cpm": round(peak_v * 60.0, 1),
        "peak_center_epoch": peak_step,
        "peak_window_hits": peak_hits,
        "mean_velocity_mps": round(mean_v, 4),
        "std_velocity_mps": round(std_v, 4),
        "peak_sigma": peak_sigma,
        "flatline_threshold_mps": round(flatline_threshold, 3),
        "flatline_triggered": flatline_triggered,
        "flatline_triggered_epoch": flatline_epoch,
        "terminal_velocity_mps": round(terminal_v, 3),
        "minute_peak_mps": minute_peak_mps,
    }


def _load_lexicon_terms(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Load subcultural shibboleth lexicon dynamically from morning_wiretap.db."""
    tables = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for candidate_table in (
        "cfb_subcultural_lexicon",
        "faas_subcultural_lexicon",
        "subcultural_shibboleths",
        "cfb_shibboleths",
    ):
        if candidate_table in tables:
            cols = [
                c["name"]
                for c in conn.execute(f"PRAGMA table_info({candidate_table})").fetchall()
            ]
            term_col = (
                "shibboleth_id"
                if "shibboleth_id" in cols
                else ("term" if "term" in cols else ("shibboleth" if "shibboleth" in cols else cols[0]))
            )
            rows = conn.execute(f"SELECT * FROM {candidate_table}").fetchall()
            return [dict(r) for r in rows if r[term_col]]
    return []


def _extract_kill_shot_context(
    rows: Sequence[sqlite3.Row],
    peak_center_epoch: int,
    lexicon: Sequence[Dict[str, Any]],
) -> Tuple[str, str]:
    """Identify the dominant shibboleth or token and verbatim quote inside [peak - 60s, peak + 30s]."""
    window_msgs = [
        r for r in rows
        if peak_center_epoch - 60 <= int(r["epoch_time"] or 0) <= peak_center_epoch + 30
    ]
    if not window_msgs:
        window_msgs = list(rows[-25:]) if rows else []

    if not window_msgs:
        return ("unclassified_burst", "")

    term_counts: Dict[str, int] = {}
    best_quote_by_term: Dict[str, str] = {}
    for item in lexicon:
        raw_term = str(
            item.get("shibboleth_id") or item.get("term") or item.get("shibboleth") or ""
        ).strip()
        if not raw_term:
            continue
        tokens: List[str] = []
        raw_json = item.get("trigger_tokens_json")
        if raw_json:
            try:
                parsed = json.loads(str(raw_json))
                if isinstance(parsed, list):
                    tokens.extend(str(t).strip().lower() for t in parsed if len(str(t).strip()) >= 3)
            except json.JSONDecodeError:
                pass
        if not tokens:
            tokens = [t.strip().lower() for t in re.split(r"[/,&\s_]+", raw_term) if len(t.strip()) >= 3]
        token_patterns = [re.compile(rf"\b{re.escape(tok)}\b") for tok in tokens]
        for msg in window_msgs:
            body_lower = str(msg["message"] or "").lower()
            if any(pat.search(body_lower) for pat in token_patterns):
                term_counts[raw_term] = term_counts.get(raw_term, 0) + 1
                if raw_term not in best_quote_by_term:
                    author = str(msg["author"] or "chatter")
                    best_quote_by_term[raw_term] = f"{author}: {str(msg['message'] or '')[:160]}"

    if term_counts:
        top_term = max(term_counts.items(), key=lambda x: x[1])[0]
        return (top_term, best_quote_by_term.get(top_term, ""))

    stopwords = {"this", "that", "with", "from", "have", "what", "your", "just", "like", "they", "them", "game"}
    word_freq: Dict[str, int] = {}
    for msg in window_msgs:
        for w in re.findall(r"[a-zA-Z]{4,}", str(msg["message"] or "").lower()):
            if w not in stopwords:
                word_freq[w] = word_freq.get(w, 0) + 1

    top_word = max(word_freq.items(), key=lambda x: x[1])[0] if word_freq else "chat_eruption"
    sample_row = window_msgs[-1]
    sample_quote = f"{sample_row['author']}: {str(sample_row['message'] or '')[:160]}"
    return (top_word, sample_quote)


def _resolve_barf_autopsy(
    channel_key: str,
    final_score: str,
    cause_shibboleth: str,
    peak_sigma: float,
) -> Tuple[str, str]:
    """Reconcile speculative Barf calls in /dev/shm/faas_vfs/barf_receipts.json against FINAL."""
    if BARF_RECEIPTS_SHM_PATH.exists():
        try:
            receipts = json.loads(BARF_RECEIPTS_SHM_PATH.read_text(encoding="utf-8"))
            if isinstance(receipts, dict) and channel_key in receipts:
                entry = receipts[channel_key]
                called_winner = str(entry.get("called_winner", ""))
                if called_winner and called_winner.upper() in final_score.upper():
                    return (
                        "VICTORY_LAP",
                        f"Called {called_winner} before the flatline ({peak_sigma}σ on {cause_shibboleth}). Pay the basement oracle.",
                    )
                return (
                    "JINX_CROW",
                    f"Prematurely yapped on {channel_key} before the 4th quarter dust settled. Eating warm Tums in disgrace.",
                )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Barf receipt read warning: %s", exc)

    if peak_sigma >= 4.0:
        return (
            "CORONER_VERDICT",
            f"Toe-tagged at +{peak_sigma}σ ({cause_shibboleth}) after 30s post-FINAL flatline decay.",
        )
    return (
        "POST_GAME_SEAL",
        f"Sealed in Yesterday's Body Bags ({final_score}) following post-whistle velocity decay.",
    )


def evaluate_and_compile_body_bags(
    db_path: Path = WIRETAP_DB_PATH,
    now_epoch: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Scan active and completed channels in morning_wiretap.db, compute 10s sliding rings,
    and commit Toe-Tag receipts for any FINAL game whose chat velocity decayed <= 20%
    of peak for 30 consecutive seconds.
    """
    now_ts = int(now_epoch if now_epoch is not None else time.time())
    if not db_path.exists():
        return {"updated_at": now_ts, "body_bags": [], "active_evaluations": []}

    conn = get_wal_connection(db_path)
    try:
        ensure_toe_tag_schema(conn)
        lexicon = _load_lexicon_terms(conn)

        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        stream_meta: Dict[str, Dict[str, Any]] = {}
        if "watch_party_streams" in tables:
            for r in conn.execute("SELECT * FROM watch_party_streams").fetchall():
                d = dict(r)
                key = str(d.get("game_id") or d.get("channel_key") or d.get("matchup") or "").strip()
                if key:
                    stream_meta[key] = d

        if "fanstack_unified_schedule" in tables:
            for r in conn.execute("SELECT * FROM fanstack_unified_schedule").fetchall():
                d = dict(r)
                key = str(d.get("game_id") or d.get("id") or "").strip()
                if key:
                    stream_meta.setdefault(key, {}).update(d)

        channels = [
            str(r["channel_key"])
            for r in conn.execute(
                """
                SELECT DISTINCT channel_key
                FROM chat_telemetry
                WHERE channel_key IS NOT NULL AND TRIM(channel_key) != ''
                """
            ).fetchall()
        ]

        committed_bags: List[Dict[str, Any]] = []
        evaluations: List[Dict[str, Any]] = []

        for channel_key in channels:
            rows = conn.execute(
                """
                SELECT id, epoch_time, author, message
                FROM chat_telemetry
                WHERE channel_key = ? AND epoch_time IS NOT NULL
                ORDER BY epoch_time ASC
                """,
                (channel_key,),
            ).fetchall()

            if not rows:
                continue

            epochs = [float(r["epoch_time"]) for r in rows if r["epoch_time"]]
            meta = stream_meta.get(channel_key, {})
            raw_status = str(meta.get("status") or meta.get("game_status") or "").upper()
            last_msg_age = now_ts - int(epochs[-1]) if epochs else 0

            is_final = ("FINAL" in raw_status) or (last_msg_age >= FLATLINE_HOLD_SECONDS)
            eval_horizon = (
                min(now_ts, int(epochs[-1]) + FLATLINE_HOLD_SECONDS + SUB_BUCKET_SECONDS)
                if is_final
                else int(epochs[-1])
            )

            ring = compute_sliding_10s_ring(epochs, eval_end_epoch=eval_horizon)
            cause_shibboleth, kill_quote = _extract_kill_shot_context(
                rows, ring["peak_center_epoch"], lexicon
            )

            matchup_title = str(
                meta.get("matchup")
                or meta.get("title")
                or meta.get("short_name")
                or channel_key
            )
            final_score = str(
                meta.get("score")
                or meta.get("final_score")
                or f"{channel_key} ({ring['total_messages']} msgs)"
            )
            game_status = "FINAL" if is_final else (raw_status or "LIVE")

            vod_seek_seconds = max(
                0, int(ring["peak_center_epoch"]) - int(ring["stream_start_epoch"]) - 15
            )
            barf_call_type, barf_verdict = _resolve_barf_autopsy(
                channel_key, final_score, cause_shibboleth, ring["peak_sigma"]
            )

            eval_record = {
                "game_id": channel_key,
                "channel_key": channel_key,
                "matchup_title": matchup_title,
                "final_score": final_score,
                "game_status": game_status,
                "time_of_death_epoch": ring["peak_center_epoch"],
                "flatline_triggered": bool(is_final and ring["flatline_triggered"]),
                "flatline_triggered_epoch": ring["flatline_triggered_epoch"],
                "stream_start_epoch": ring["stream_start_epoch"],
                "vod_seek_seconds": vod_seek_seconds,
                "peak_velocity_mps": ring["peak_velocity_mps"],
                "peak_velocity_cpm": ring["peak_velocity_cpm"],
                "peak_sigma": ring["peak_sigma"],
                "flatline_threshold_mps": ring["flatline_threshold_mps"],
                "terminal_velocity_mps": ring["terminal_velocity_mps"],
                "cause_shibboleth": cause_shibboleth,
                "sample_kill_quote": kill_quote,
                "barf_call_type": barf_call_type,
                "barf_verdict_text": barf_verdict,
            }
            evaluations.append(eval_record)

            if is_final and ring["flatline_triggered"] and ring["peak_velocity_mps"] > 0:
                canonical_bytes = json.dumps(eval_record, sort_keys=True).encode("utf-8")
                receipt_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
                created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                eval_record["receipt_sha256"] = receipt_sha256
                eval_record["created_at_utc"] = created_utc

                conn.execute(
                    """
                    INSERT INTO toe_tag_receipts (
                        game_id, channel_key, matchup_title, final_score, game_status,
                        time_of_death_epoch, flatline_triggered_epoch, stream_start_epoch,
                        vod_seek_seconds, peak_velocity_mps, peak_velocity_cpm, peak_sigma,
                        flatline_threshold_mps, terminal_velocity_mps, cause_shibboleth,
                        sample_kill_quote, barf_call_type, barf_verdict_text,
                        receipt_sha256, created_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(game_id) DO UPDATE SET
                        final_score = excluded.final_score,
                        game_status = excluded.game_status,
                        time_of_death_epoch = excluded.time_of_death_epoch,
                        flatline_triggered_epoch = excluded.flatline_triggered_epoch,
                        vod_seek_seconds = excluded.vod_seek_seconds,
                        peak_velocity_mps = excluded.peak_velocity_mps,
                        peak_velocity_cpm = excluded.peak_velocity_cpm,
                        peak_sigma = excluded.peak_sigma,
                        flatline_threshold_mps = excluded.flatline_threshold_mps,
                        terminal_velocity_mps = excluded.terminal_velocity_mps,
                        cause_shibboleth = excluded.cause_shibboleth,
                        sample_kill_quote = excluded.sample_kill_quote,
                        barf_call_type = excluded.barf_call_type,
                        barf_verdict_text = excluded.barf_verdict_text,
                        receipt_sha256 = excluded.receipt_sha256
                    """,
                    (
                        eval_record["game_id"],
                        eval_record["channel_key"],
                        eval_record["matchup_title"],
                        eval_record["final_score"],
                        eval_record["game_status"],
                        eval_record["time_of_death_epoch"],
                        eval_record["flatline_triggered_epoch"],
                        eval_record["stream_start_epoch"],
                        eval_record["vod_seek_seconds"],
                        eval_record["peak_velocity_mps"],
                        eval_record["peak_velocity_cpm"],
                        eval_record["peak_sigma"],
                        eval_record["flatline_threshold_mps"],
                        eval_record["terminal_velocity_mps"],
                        eval_record["cause_shibboleth"],
                        eval_record["sample_kill_quote"],
                        eval_record["barf_call_type"],
                        eval_record["barf_verdict_text"],
                        receipt_sha256,
                        created_utc,
                    ),
                )
                committed_bags.append(eval_record)

        conn.commit()
        committed_bags.sort(key=lambda x: (x["peak_sigma"], x["peak_velocity_mps"]), reverse=True)

        shm_payload = {
            "updated_at": now_ts,
            "flatline_rule": "velocity_mps <= 0.20 * peak_velocity_mps for 30s after FINAL",
            "total_body_bags": len(committed_bags),
            "body_bags": committed_bags,
            "active_evaluations": evaluations,
        }
        atomic_write_json(BODY_BAGS_SHM_PATH, shm_payload)
        return shm_payload
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StackLabs Post-FINAL Flatline Toe-Tag Coroner")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate and print summary")
    args = parser.parse_args()

    result = evaluate_and_compile_body_bags()
    print(
        json.dumps(
            {
                "status": "OK",
                "total_body_bags": result.get("total_body_bags", 0),
                "shm_path": str(BODY_BAGS_SHM_PATH),
                "top_bag": result["body_bags"][0] if result.get("body_bags") else None,
            },
            indent=2,
        )
    )
