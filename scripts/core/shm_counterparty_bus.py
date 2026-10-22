#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Zero-Lock Shared Memory Counterparty Token Bus & 10s Sliding Velocity Engine.
Manages atomic /dev/shm/vfs/comms/counterparty_recent_tokens.json state and 6-hop x 10s
rolling window velocity math to eliminate fixed-minute boundary dilution.
"""

import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("stacklabs.shm_counterparty_bus")

SHM_COMMS_DIR = Path("/dev/shm/vfs/comms")
SHM_COUNTERPARTY_FILE = SHM_COMMS_DIR / "counterparty_recent_tokens.json"
DEFAULT_TTL_SECONDS = 14400  # 4-hour rolling horizon
MAX_ENVELOPES = 64

STOPWORDS = {
    "about", "after", "again", "being", "could", "doing", "every", "first",
    "found", "going", "great", "having", "https", "listening", "other",
    "right", "should", "since", "still", "their", "there", "these", "thing",
    "think", "those", "through", "today", "tonight", "under", "using",
    "where", "which", "while", "would", "years", "youre", "that", "this",
    "with", "from", "have", "just", "like", "what", "when", "your", "will",
    "they", "them", "then", "than", "some", "more", "into", "only", "over",
    "also", "back", "been", "were", "very", "here", "make", "made", "much",
}

TOKEN_REGEX = re.compile(r"[a-zA-Z0-9_']{4,}")


def resolve_canonical_counterparty(raw_sender: str) -> Optional[str]:
    """Dynamically resolve counterparty name using existing rules without hardcoding."""
    if not raw_sender:
        return None
    try:
        from scripts.sms_backup_parser import resolve_counterparty, COUNTERPARTY_RULES
        resolved = resolve_counterparty(contact_name=raw_sender, address=None, body="")
        if resolved:
            return resolved
        # Check against known rule targets
        norm = raw_sender.strip().lower()
        for cp_name, aliases in COUNTERPARTY_RULES:
            if norm == cp_name.lower():
                return cp_name
            for al in aliases:
                if al.lower() in norm:
                    return cp_name
    except Exception as exc:
        logger.debug("Dynamic counterparty resolution fallback: %s", exc)

    # Clean fallback for standard display names
    norm = raw_sender.strip()
    if len(norm) >= 3 and not norm.isdigit():
        return norm
    return None


def extract_salient_tokens(text: str) -> List[str]:
    """Extract normalized lowercase lexical tokens (>=4 chars, non-stopword)."""
    if not text:
        return []
    seen = set()
    ordered: List[str] = []
    for match in TOKEN_REGEX.findall(text.lower()):
        cleaned = match.strip("'_")
        if len(cleaned) < 4 or cleaned in STOPWORDS or cleaned.isdigit():
            continue
        if cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered[:64]


def atomic_write_json(target_path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON payload atomically via .tmp + os.replace()."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(f".tmp.{os.getpid()}")
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    tmp_path.write_text(serialized, encoding="utf-8")
    os.replace(tmp_path, target_path)


def read_counterparty_shm(
    shm_path: Path = SHM_COUNTERPARTY_FILE,
    now_epoch: Optional[int] = None,
) -> Dict[str, Any]:
    """Read active counterparty token envelopes from /dev/shm without locks."""
    now_ts = int(now_epoch if now_epoch is not None else time.time())
    if not shm_path.exists():
        return {"updated_at": now_ts, "envelopes": [], "latest": None}
    try:
        raw = json.loads(shm_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed reading counterparty shm %s: %s", shm_path, exc)
        return {"updated_at": now_ts, "envelopes": [], "latest": None}

    envelopes = raw.get("envelopes", [])
    if not isinstance(envelopes, list):
        envelopes = []

    cutoff = now_ts - DEFAULT_TTL_SECONDS
    active = [
        env for env in envelopes
        if isinstance(env, dict) and int(env.get("timestamp", 0)) >= cutoff
    ]
    active.sort(key=lambda x: int(x.get("timestamp", 0)), reverse=True)
    latest = active[0] if active else None
    return {
        "updated_at": int(raw.get("updated_at", now_ts)),
        "envelopes": active[:MAX_ENVELOPES],
        "latest": latest,
    }


def emit_counterparty_tokens_to_shm(
    sender: str,
    raw_snippet: str,
    timestamp_epoch: Optional[int] = None,
    extra_tokens: Optional[Sequence[str]] = None,
    shm_path: Path = SHM_COUNTERPARTY_FILE,
) -> Optional[Dict[str, Any]]:
    """
    Publish an inbound counterparty message's salient tokens to /dev/shm/vfs/comms/.
    Returns the committed envelope dict, or None if sender does not resolve.
    """
    canonical_sender = resolve_canonical_counterparty(sender)
    if not canonical_sender:
        return None

    ts = int(timestamp_epoch if timestamp_epoch is not None else time.time())
    tokens = extract_salient_tokens(raw_snippet)
    if extra_tokens:
        for tok in extra_tokens:
            norm = tok.strip().lower()
            if len(norm) >= 3 and norm not in tokens:
                tokens.append(norm)

    if not tokens:
        return None

    msg_hash = hashlib.sha256(
        f"{canonical_sender}:{ts}:{raw_snippet[:160]}".encode("utf-8")
    ).hexdigest()[:16]

    envelope = {
        "envelope_id": msg_hash,
        "sender": canonical_sender,
        "timestamp": ts,
        "timestamp_hm": datetime.fromtimestamp(ts).strftime("%H:%M"),
        "tokens": tokens,
        "raw_snippet": raw_snippet.strip()[:280],
    }

    current = read_counterparty_shm(shm_path=shm_path, now_epoch=ts)
    existing_envelopes = [
        env for env in current.get("envelopes", [])
        if env.get("envelope_id") != msg_hash
    ]
    existing_envelopes.insert(0, envelope)
    existing_envelopes = existing_envelopes[:MAX_ENVELOPES]

    state_payload = {
        "sender": canonical_sender,
        "timestamp": ts,
        "tokens": tokens,
        "raw_snippet": envelope["raw_snippet"],
        "updated_at": ts,
        "latest": envelope,
        "envelopes": existing_envelopes,
    }
    atomic_write_json(shm_path, state_payload)
    return envelope


def match_counterparty_echo(
    candidate_tokens: Sequence[str],
    shm_state: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check if candidate tokens intersect with recent counterparty tokens in /dev/shm.
    Returns echo badge metadata on match.
    """
    state = shm_state if shm_state is not None else read_counterparty_shm()
    envelopes = state.get("envelopes", [])
    if not envelopes and state.get("sender") and state.get("tokens"):
        envelopes = [state]

    norm_candidates = {
        t.strip().lower() for t in candidate_tokens if t and len(t.strip()) >= 3
    }
    if not norm_candidates:
        return None

    for env in envelopes:
        env_tokens = {str(t).strip().lower() for t in env.get("tokens", [])}
        overlap = sorted(norm_candidates.intersection(env_tokens))
        if not overlap:
            for cand in norm_candidates:
                for etok in env_tokens:
                    if (len(cand) >= 4 and cand in etok) or (len(etok) >= 4 and etok in cand):
                        overlap.append(etok)
            overlap = sorted(set(overlap))
        if overlap:
            ts = int(env.get("timestamp", 0))
            hm = env.get("timestamp_hm") or (
                datetime.fromtimestamp(ts).strftime("%H:%M") if ts > 0 else "LIVE"
            )
            sender = env.get("sender", "Counterparty")
            return {
                "badge": f"COUNTERPARTY_ECHO: {sender} @ {hm}",
                "sender": sender,
                "timestamp": ts,
                "timestamp_hm": hm,
                "matched_tokens": overlap,
                "raw_snippet": env.get("raw_snippet", ""),
            }
    return None


def compute_sliding_10s_velocity(
    epoch_timestamps: Sequence[float],
    window_start_epoch: Optional[int] = None,
    window_end_epoch: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Quantize message timestamps into 10-second sub-buckets:
        bin_10s = (int(ts) // 10) * 10
    Compute instantaneous 60-second rolling velocity at every 10-second step t:
        V_60(t) = sum_{k=0..5} hits[t - 10*k] / 60.0
    Also aggregate into 60-second calendar-minute buckets for UI bar chart stability,
    enriching each 60s bucket with its true peak 10s-rolling velocity.
    """
    if not epoch_timestamps:
        return {
            "peak_velocity_mps": 0.0,
            "peak_velocity_cpm": 0.0,
            "peak_center_epoch": 0,
            "peak_window_hits": 0,
            "mean_velocity_mps": 0.0,
            "std_velocity_mps": 0.0,
            "z_score": 0.0,
            "sub_buckets_10s": {},
            "minute_peak_mps": {},
            "minute_peak_hits": {},
        }

    int_times = [int(ts) for ts in epoch_timestamps if ts is not None and ts > 0]
    if not int_times:
        return {
            "peak_velocity_mps": 0.0,
            "peak_velocity_cpm": 0.0,
            "peak_center_epoch": 0,
            "peak_window_hits": 0,
            "mean_velocity_mps": 0.0,
            "std_velocity_mps": 0.0,
            "z_score": 0.0,
            "sub_buckets_10s": {},
            "minute_peak_mps": {},
            "minute_peak_hits": {},
        }

    bins_10s: Dict[int, int] = {}
    for ts in int_times:
        b10 = (ts // 10) * 10
        bins_10s[b10] = bins_10s.get(b10, 0) + 1

    min_bin = ((window_start_epoch // 10) * 10) if window_start_epoch else min(bins_10s.keys())
    max_bin = ((window_end_epoch // 10) * 10) if window_end_epoch else max(bins_10s.keys())
    if max_bin < min_bin:
        max_bin = min_bin

    # Max 2160 steps (6 hours of 10s bins)
    if (max_bin - min_bin) // 10 > 2160:
        min_bin = max_bin - (2160 * 10)

    rolling_velocities: List[Tuple[int, int, float]] = []
    minute_peak_mps: Dict[int, float] = {}
    minute_peak_hits: Dict[int, int] = {}

    for step_t in range(min_bin, max_bin + 10, 10):
        rolling_hits = sum(bins_10s.get(step_t - (10 * k), 0) for k in range(6))
        v_60 = round(rolling_hits / 60.0, 4)
        rolling_velocities.append((step_t, rolling_hits, v_60))

        minute_bucket = (step_t // 60) * 60
        if v_60 > minute_peak_mps.get(minute_bucket, 0.0):
            minute_peak_mps[minute_bucket] = round(v_60, 3)
            minute_peak_hits[minute_bucket] = rolling_hits

    peak_step, peak_hits, peak_v = max(rolling_velocities, key=lambda item: item[2])

    v_values = [item[2] for item in rolling_velocities]
    n_steps = len(v_values)
    mean_v = sum(v_values) / n_steps if n_steps > 0 else 0.0
    if n_steps > 1:
        variance = sum((v - mean_v) ** 2 for v in v_values) / n_steps
        std_v = math.sqrt(variance)
    else:
        std_v = 0.0

    effective_std = max(std_v, 0.08)
    z_score = round((peak_v - mean_v) / effective_std, 2) if peak_v > 0 else 0.0

    return {
        "peak_velocity_mps": round(peak_v, 3),
        "peak_velocity_cpm": round(peak_v * 60.0, 1),
        "peak_center_epoch": peak_step,
        "peak_window_hits": peak_hits,
        "mean_velocity_mps": round(mean_v, 4),
        "std_velocity_mps": round(std_v, 4),
        "z_score": z_score,
        "sub_buckets_10s": bins_10s,
        "minute_peak_mps": minute_peak_mps,
        "minute_peak_hits": minute_peak_hits,
    }
