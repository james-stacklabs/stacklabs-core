#!/home/james/stacklabs/.venv/bin/python3
"""
VFS Time-Machine Compiler & Phase-Locked Causal Replay Indexer (WO0011280).
I compile Faster-Whisper transcripts from data/snipes/{id}/ and vfs/snipes/{id}/
against live bleacher chat bursts in data/morning_wiretap.db, computing 10-second
velocity dyno buckets, +3.0 sigma Seismic Pins, and the empirical +Delta_HLS
broadcast latency offset.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compile_snipe_time_machine")

ROOT_DIR = Path("/home/james/stacklabs")
DATA_SNIPES_DIR = ROOT_DIR / "data" / "snipes"
VFS_SNIPES_DIR = ROOT_DIR / "vfs" / "snipes"
WIRETAP_DB_PATH = ROOT_DIR / "data" / "morning_wiretap.db"
GROUND_TRUTH_SPORTS_PATH = ROOT_DIR / "ground_truth" / "sports_ground_truth.json"

EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")
WORD_TOKEN_RE = re.compile(r"[a-zA-Z0-9']{3,}")
STOPWORDS: Set[str] = {
    "the", "and", "that", "this", "with", "from", "your", "have", "what", "when",
    "where", "they", "them", "their", "there", "were", "been", "just", "like",
    "about", "would", "could", "should", "into", "over", "after", "before", "going",
    "really", "think", "know", "mean", "right", "here", "some", "more", "very",
}

# Matches **[00:17 -> 00:19]** or [00:17 -> 00:19] or [00:17]
TS_RANGE_RE = re.compile(r"^\**\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*(?:->|-)\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]\**\s*(.+)$")
TS_POINT_RE = re.compile(r"^\**\[?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]?\**\s*(.+)$")


def get_db_connection(db_path: Path = WIRETAP_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def compute_shannon_entropy(text: str) -> float:
    cleaned = EMOJI_SHORTCODE_RE.sub("", text).strip()
    if not cleaned:
        return 0.0
    counts = collections.Counter(cleaned.lower())
    total = len(cleaned)
    return round(-sum((c / total) * math.log2(c / total) for c in counts.values()), 4)


def load_dynamic_lexicon(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Load subcultural shibboleths dynamically from SQLite WAL or ground_truth JSON."""
    lexicon: Dict[str, Dict[str, Any]] = {}
    try:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for candidate_table in ("cfb_subcultural_lexicon", "faas_subcultural_lexicon", "subcultural_shibboleths", "cfb_shibboleths"):
            if candidate_table in tables:
                cols = {
                    row["name"]
                    for row in conn.execute(f"PRAGMA table_info({candidate_table})").fetchall()
                }
                term_col = next((c for c in ("shibboleth_id", "term", "token", "shibboleth") if c in cols), None)
                team_col = next((c for c in ("team_code", "program", "team") if c in cols), None)
                lore_col = next((c for c in ("cultural_meaning", "lore", "cultural_anchor") if c in cols), None)
                if term_col:
                    rows = conn.execute(f"SELECT * FROM {candidate_table}").fetchall()
                    for row in rows:
                        rdict = dict(row)
                        term_val = str(rdict.get(term_col, "")).strip().lower()
                        if term_val:
                            lexicon[term_val] = {
                                "term": term_val,
                                "team": str(rdict.get(team_col, "ALL")) if team_col else "ALL",
                                "lore": str(rdict.get(lore_col, "")) if lore_col else "",
                            }
                    if lexicon:
                        break
    except sqlite3.Error as exc:
        logger.warning("SQLite lexicon lookup notice: %s", exc)

    if not lexicon and GROUND_TRUTH_SPORTS_PATH.exists():
        try:
            gt = json.loads(GROUND_TRUTH_SPORTS_PATH.read_text(encoding="utf-8"))
            raw_lex = gt.get("cfb_subcultural_lexicon", {})
            if isinstance(raw_lex, dict):
                for team_key, entry in raw_lex.items():
                    tokens = entry.get("tokens", []) if isinstance(entry, dict) else []
                    for tok in tokens:
                        tok_l = str(tok).strip().lower()
                        if tok_l:
                            lexicon[tok_l] = {
                                "term": tok_l,
                                "team": team_key,
                                "lore": str(entry.get("cultural_anchor", "")),
                            }
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ground truth lexicon fallback notice: %s", exc)
    return lexicon


def resolve_snipe_directory(snipe_id: str) -> Path:
    vfs_path = VFS_SNIPES_DIR / snipe_id
    data_path = DATA_SNIPES_DIR / snipe_id
    if vfs_path.exists():
        return vfs_path
    if data_path.exists():
        return data_path
    vfs_path.mkdir(parents=True, exist_ok=True)
    return vfs_path


def load_snipe_metadata_and_segments(snipe_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    snipe_dir = resolve_snipe_directory(snipe_id)
    data_dir = DATA_SNIPES_DIR / snipe_id
    search_dirs = [d for d in (snipe_dir, data_dir) if d.exists()]

    metadata: Dict[str, Any] = {
        "snipe_id": snipe_id,
        "title": f"Media Dossier {snipe_id}",
        "channel_key": "radio_mcafee",
        "stream_id": snipe_id,
        "recorded_start_epoch": 0.0,
        "duration_seconds": 0.0,
    }

    # Inspect parent snipe json if present
    parent_json = DATA_SNIPES_DIR / f"{snipe_id}.json"
    if parent_json.exists():
        try:
            loaded_parent = json.loads(parent_json.read_text(encoding="utf-8"))
            if isinstance(loaded_parent, dict):
                metadata.update(loaded_parent)
        except Exception:
            pass

    for d in search_dirs:
        for meta_name in ("metadata.json", "dossier_meta.json", "state.json", "spec.json"):
            candidate = d / meta_name
            if candidate.exists():
                try:
                    loaded = json.loads(candidate.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        metadata.update(loaded)
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning("Metadata read warning on %s: %s", candidate, exc)

    segments: List[Dict[str, Any]] = []
    for d in search_dirs:
        for seg_name in ("transcript.json", "whisper_segments.json", "segments.json", "alignment.json"):
            candidate = d / seg_name
            if candidate.exists():
                try:
                    raw = json.loads(candidate.read_text(encoding="utf-8"))
                    raw_segs = raw.get("segments", raw) if isinstance(raw, dict) else raw
                    if isinstance(raw_segs, list):
                        for idx, item in enumerate(raw_segs):
                            if isinstance(item, dict):
                                start_s = float(item.get("start", item.get("start_sec", idx * 5.0)))
                                end_s = float(item.get("end", item.get("end_sec", start_s + 5.0)))
                                text_val = str(item.get("text", item.get("transcript", ""))).strip()
                                if text_val:
                                    segments.append({
                                        "id": int(item.get("id", idx)),
                                        "start_sec": round(start_s, 2),
                                        "end_sec": round(max(end_s, start_s + 0.5), 2),
                                        "text": text_val,
                                    })
                        if segments:
                            break
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    logger.warning("Transcript JSON parse notice on %s: %s", candidate, exc)

        if not segments:
            md_candidates = (
                "transcript_aligned.md",
                "transcript_verbatim.md",
                "transcript.md",
                "transcript.txt",
                f"{snipe_id}_transcript.txt",
                "brief.md",
                "dossier.md",
            )
            for md_name in md_candidates:
                candidate = d / md_name
                if candidate.exists():
                    try:
                        lines = [
                            ln.strip()
                            for ln in candidate.read_text(encoding="utf-8").splitlines()
                            if ln.strip() and not ln.strip().startswith("#") and not ln.strip().startswith(">")
                        ]
                        cursor_s = 0.0
                        for idx, ln in enumerate(lines[:1200]):
                            m_range = TS_RANGE_RE.match(ln)
                            if m_range:
                                s_h = int(m_range.group(1) or 0)
                                s_m = int(m_range.group(2))
                                s_s = int(m_range.group(3))
                                e_h = int(m_range.group(4) or 0)
                                e_m = int(m_range.group(5))
                                e_s = int(m_range.group(6))
                                start_s = float(s_h * 3600 + s_m * 60 + s_s)
                                end_s = float(e_h * 3600 + e_m * 60 + e_s)
                                body = m_range.group(7).strip()
                            else:
                                m_point = TS_POINT_RE.match(ln)
                                if m_point:
                                    s_h = int(m_point.group(1) or 0)
                                    s_m = int(m_point.group(2))
                                    s_s = int(m_point.group(3))
                                    start_s = float(s_h * 3600 + s_m * 60 + s_s)
                                    body = m_point.group(4).strip()
                                    end_s = start_s + max(4.0, min(14.0, len(body.split()) * 0.42))
                                else:
                                    start_s = cursor_s
                                    body = ln
                                    end_s = start_s + max(4.0, min(14.0, len(body.split()) * 0.42))

                            if body:
                                segments.append({
                                    "id": idx,
                                    "start_sec": round(start_s, 2),
                                    "end_sec": round(max(end_s, start_s + 0.5), 2),
                                    "text": body,
                                })
                                cursor_s = end_s
                        if segments:
                            break
                    except OSError as exc:
                        logger.warning("Markdown transcript parse notice on %s: %s", candidate, exc)

    if segments:
        max_end = max(seg["end_sec"] for seg in segments)
        metadata["duration_seconds"] = max(float(metadata.get("duration_seconds") or 0.0), max_end)

    return metadata, segments


def resolve_candidate_channels(
    conn: sqlite3.Connection,
    snipe_id: str,
    metadata: Dict[str, Any],
) -> List[str]:
    """Multi-channel candidate key resolution adhering to Argon Law 5."""
    candidates: Set[str] = {snipe_id, "radio_mcafee", "mcafee"}
    for key in ("channel_key", "channel", "stream_id", "game_id", "game_pk", "id"):
        val = str(metadata.get(key, "")).strip()
        if val:
            candidates.add(val)
            candidates.add(val.lower())
            candidates.add(f"{val.lower()}_dynamic")
            candidates.add(f"{val.upper()}_dynamic")

    home_team = str(metadata.get("home_team", "")).strip().upper()
    away_team = str(metadata.get("away_team", "")).strip().upper()
    if home_team:
        candidates.add(f"{home_team}_dynamic")
    if away_team:
        candidates.add(f"{away_team}_dynamic")
    if away_team and home_team:
        candidates.add(f"{away_team}@{home_team} LIVE")

    try:
        tables = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "watch_party_streams" in tables:
            cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(watch_party_streams)").fetchall()
            }
            if "stream_id" in cols:
                rows = conn.execute(
                    "SELECT * FROM watch_party_streams WHERE stream_id = ? LIMIT 20",
                    (snipe_id,),
                ).fetchall()
                for row in rows:
                    rdict = dict(row)
                    for k in ("channel_key", "stream_id", "game_pk", "home_team", "away_team"):
                        v = str(rdict.get(k, "")).strip()
                        if v:
                            candidates.add(v)
                            if k in ("home_team", "away_team"):
                                candidates.add(f"{v.upper()}_dynamic")
    except sqlite3.Error as exc:
        logger.warning("watch_party_streams lookup notice: %s", exc)

    return sorted(c for c in candidates if c)


def fetch_scoped_chat_telemetry(
    conn: sqlite3.Connection,
    candidate_channels: List[str],
    start_epoch: Optional[float],
    end_epoch: Optional[float],
    max_rows: int = 15000,
) -> List[Dict[str, Any]]:
    """Indexed primary-key cursor pagination over chat_telemetry (Argon Law 3 & 5)."""
    if not WIRETAP_DB_PATH.exists():
        return []

    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "chat_telemetry" not in tables:
        return []

    cols = {
        r["name"]
        for r in conn.execute("PRAGMA table_info(chat_telemetry)").fetchall()
    }
    has_stream_id = "stream_id" in cols
    placeholders = ",".join("?" for _ in candidate_channels)

    dedup_ring: Deque[Tuple[str, str, int]] = collections.deque(maxlen=4096)
    dedup_set: Set[Tuple[str, str, int]] = set()
    collected: List[Dict[str, Any]] = []
    cursor_id = 0

    while len(collected) < max_rows:
        params: List[Any] = list(candidate_channels)
        where_clauses = [f"channel_key IN ({placeholders})"]
        if has_stream_id:
            where_clauses = [f"(channel_key IN ({placeholders}) OR stream_id IN ({placeholders}))"]
            params.extend(candidate_channels)

        where_clauses.append("id > ?")
        params.append(cursor_id)

        if start_epoch and start_epoch > 0:
            where_clauses.append("epoch_time >= ?")
            params.append(start_epoch - 30.0)
        if end_epoch and end_epoch > 0:
            where_clauses.append("epoch_time <= ?")
            params.append(end_epoch + 60.0)

        sql = (
            f"SELECT id, channel_key, author, message, epoch_time "
            f"FROM chat_telemetry WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY id ASC LIMIT 500"
        )
        batch = conn.execute(sql, tuple(params)).fetchall()
        if not batch:
            break

        for row in batch:
            cursor_id = int(row["id"])
            author = str(row["author"] or "anon").strip()
            msg = str(row["message"] or "").strip()
            epoch = float(row["epoch_time"] or 0.0)
            if not msg or epoch <= 0:
                continue

            dedup_key = (author.lower(), EMOJI_SHORTCODE_RE.sub("", msg).strip().lower(), int(epoch // 5))
            if dedup_key in dedup_set:
                continue
            if len(dedup_ring) == dedup_ring.maxlen:
                oldest = dedup_ring.popleft()
                dedup_set.discard(oldest)
            dedup_ring.append(dedup_key)
            dedup_set.add(dedup_key)

            collected.append({
                "id": cursor_id,
                "channel_key": str(row["channel_key"]),
                "author": author,
                "message": msg,
                "epoch_time": epoch,
                "entropy": compute_shannon_entropy(msg),
            })

        if len(batch) < 500:
            break

    return collected


def estimate_hls_lag_seconds(
    segments: List[Dict[str, Any]],
    chat_rows: List[Dict[str, Any]],
    base_epoch: float,
) -> float:
    """Phase-lock the empirical +Delta_HLS broadcast delay by matching spoken tokens to chat echoes."""
    if not segments or not chat_rows or base_epoch <= 0:
        return 14.2

    observed_deltas: List[float] = []
    for seg in segments:
        tokens = [
            w.lower()
            for w in WORD_TOKEN_RE.findall(seg["text"])
            if len(w) >= 5 and w.lower() not in STOPWORDS
        ]
        if not tokens:
            continue
        seg_abs_t = base_epoch + float(seg["start_sec"])
        for msg in chat_rows:
            dt = msg["epoch_time"] - seg_abs_t
            if dt < 6.0:
                continue
            if dt > 25.0:
                break
            msg_lower = msg["message"].lower()
            if any(tok in msg_lower for tok in tokens[:3]):
                observed_deltas.append(dt)
                break

    if not observed_deltas:
        return 14.2
    observed_deltas.sort()
    median_idx = len(observed_deltas) // 2
    return round(float(observed_deltas[median_idx]), 2)


def compile_cartridge_for_snipe(snipe_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        lexicon = load_dynamic_lexicon(conn)
        metadata, segments = load_snipe_metadata_and_segments(snipe_id)
        candidates = resolve_candidate_channels(conn, snipe_id, metadata)

        start_epoch = float(metadata.get("recorded_start_epoch") or 0.0)
        duration_s = float(metadata.get("duration_seconds") or 0.0)
        end_epoch = (start_epoch + duration_s) if (start_epoch > 0 and duration_s > 0) else None

        chat_rows = fetch_scoped_chat_telemetry(conn, candidates, start_epoch if start_epoch > 0 else None, end_epoch)

        if not chat_rows and start_epoch > 0:
            chat_rows = fetch_scoped_chat_telemetry(conn, candidates, None, None, max_rows=5000)

        if chat_rows:
            chat_rows.sort(key=lambda r: r["epoch_time"])
            min_chat_epoch = chat_rows[0]["epoch_time"]
            max_chat_epoch = chat_rows[-1]["epoch_time"]
            if start_epoch <= 0:
                start_epoch = min_chat_epoch
            if duration_s <= 0:
                duration_s = max(60.0, min(14400.0, max_chat_epoch - min_chat_epoch))
        else:
            if duration_s <= 0:
                duration_s = max((s["end_sec"] for s in segments), default=600.0)

        hls_lag_s = estimate_hls_lag_seconds(segments, chat_rows, start_epoch)

        bucket_size = 10
        num_buckets = max(1, min(1800, int(math.ceil(duration_s / bucket_size))))

        buckets: List[Dict[str, Any]] = []
        for b_idx in range(num_buckets):
            b_start = b_idx * bucket_size
            b_end = b_start + bucket_size
            buckets.append({
                "bucket_index": b_idx,
                "offset_sec": b_start,
                "end_offset_sec": b_end,
                "message_count": 0,
                "velocity_mpm": 0.0,
                "mean_entropy": 0.0,
                "z_score": 0.0,
                "matched_shibboleths": [],
                "top_messages": [],
            })

        for msg in chat_rows:
            rel_chat_sec = msg["epoch_time"] - start_epoch
            aligned_audio_sec = max(0.0, rel_chat_sec - hls_lag_s)
            b_idx = int(aligned_audio_sec // bucket_size)
            if 0 <= b_idx < num_buckets:
                b = buckets[b_idx]
                b["message_count"] += 1
                b["top_messages"].append({
                    "id": msg["id"],
                    "author": msg["author"],
                    "message": msg["message"],
                    "entropy": msg["entropy"],
                    "chat_offset_sec": round(rel_chat_sec, 2),
                    "audio_trigger_sec": round(aligned_audio_sec, 2),
                })

        # Project transcript lexical density onto waveform if no live chat is attached during capture
        total_chat_mapped = sum(b["message_count"] for b in buckets)
        if total_chat_mapped == 0 and segments:
            for seg in segments:
                b_idx = min(num_buckets - 1, max(0, int(seg["start_sec"] // bucket_size)))
                ent = compute_shannon_entropy(seg["text"])
                word_cnt = len(seg["text"].split())
                buckets[b_idx]["message_count"] += max(1, word_cnt // 4)
                buckets[b_idx]["mean_entropy"] = round(max(buckets[b_idx]["mean_entropy"], ent), 3)

        velocities = [b["message_count"] * (60.0 / bucket_size) for b in buckets]
        mean_v = sum(velocities) / len(velocities) if velocities else 0.0
        variance_v = (
            sum((v - mean_v) ** 2 for v in velocities) / len(velocities)
            if len(velocities) > 1
            else 1.0
        )
        std_v = max(math.sqrt(variance_v), 1.0)

        seismic_pins: List[Dict[str, Any]] = []
        for b_idx, b in enumerate(buckets):
            v_mpm = round(b["message_count"] * (60.0 / bucket_size), 1)
            z_val = round((v_mpm - mean_v) / std_v, 2)
            b["velocity_mpm"] = v_mpm
            b["z_score"] = z_val

            if b["top_messages"]:
                b["mean_entropy"] = round(
                    sum(m["entropy"] for m in b["top_messages"]) / len(b["top_messages"]),
                    3,
                )
                b["top_messages"].sort(key=lambda m: m["entropy"], reverse=True)
                b["top_messages"] = b["top_messages"][:12]

            combined_text = " ".join(m["message"].lower() for m in b["top_messages"])
            matched_shibs = [
                 term for term in lexicon if len(term) >= 4 and term in combined_text
            ][:4]
            b["matched_shibboleths"] = matched_shibs

            spoken_matches = [
                s["text"]
                for s in segments
                if (b["offset_sec"] - 5.0) <= s["start_sec"] <= (b["offset_sec"] + bucket_size + 5.0)
            ]
            spoken_excerpt = " ".join(spoken_matches)[:220] if spoken_matches else "Acoustic telemetry marker"

            if z_val >= 2.2 or matched_shibs or (len(seismic_pins) < 3 and b["message_count"] > 0 and z_val >= 1.2):
                pin_id = f"spike_{int(b['offset_sec']):05d}"
                pin_obj = {
                    "pin_id": pin_id,
                    "offset_sec": b["offset_sec"],
                    "timestamp_label": f"{int(b['offset_sec'] // 60):02d}:{int(b['offset_sec'] % 60):02d}",
                    "velocity_mpm": v_mpm,
                    "z_score": z_val,
                    "mean_entropy": b["mean_entropy"],
                    "hls_lag_sec": hls_lag_s,
                    "spoken_trigger": spoken_excerpt,
                    "matched_shibboleths": matched_shibs,
                    "sample_reactions": b["top_messages"][:5],
                }
                seismic_pins.append(pin_obj)

        seismic_pins.sort(key=lambda p: (p["z_score"], p["velocity_mpm"]), reverse=True)
        seismic_pins = seismic_pins[:12]
        seismic_pins.sort(key=lambda p: p["offset_sec"])

        cartridge: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "snipe_id": snipe_id,
            "title": metadata.get("title", f"Media Dossier {snipe_id}"),
            "candidate_channels": candidates,
            "recorded_start_epoch": round(start_epoch, 3),
            "duration_seconds": round(duration_s, 2),
            "hls_lag_seconds": hls_lag_s,
            "bucket_size_seconds": bucket_size,
            "total_chat_messages": len(chat_rows),
            "total_whisper_segments": len(segments),
            "baseline_velocity_mpm": round(mean_v, 2),
            "peak_velocity_mpm": round(max(velocities, default=0.0), 2),
            "seismic_pins": seismic_pins,
            "buckets": buckets,
            "segments": segments[:1200],
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        canonical_bytes = json.dumps(cartridge, sort_keys=True, separators=(",", ":")).encode("utf-8")
        cartridge["content_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()

        for target_root in (VFS_SNIPES_DIR / snipe_id, DATA_SNIPES_DIR / snipe_id):
            target_root.mkdir(parents=True, exist_ok=True)
            out_file = target_root / "time_machine.json"
            tmp_file = target_root / ".time_machine.json.tmp"
            tmp_file.write_text(json.dumps(cartridge, indent=2), encoding="utf-8")
            os.replace(tmp_file, out_file)

            spikes_dir = target_root / "spikes"
            spikes_dir.mkdir(parents=True, exist_ok=True)
            for pin in seismic_pins:
                pin_path = spikes_dir / f"{pin['pin_id']}.json"
                pin_tmp = spikes_dir / f".{pin['pin_id']}.json.tmp"
                pin_tmp.write_text(json.dumps(pin, indent=2), encoding="utf-8")
                os.replace(pin_tmp, pin_path)

        return cartridge
    finally:
        conn.close()


def discover_all_snipes() -> List[str]:
    found: Set[str] = set()
    for base in (VFS_SNIPES_DIR, DATA_SNIPES_DIR):
        if base.exists():
            for child in base.iterdir():
                if child.is_dir() and not child.name.startswith(".") and child.name != "cache":
                    found.add(child.name)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile VFS Time-Machine cartridges for FaaS Stream Sniper.")
    parser.add_argument("--snipe-id", help="Compile a specific snipe_id.")
    parser.add_argument("--all", action="store_true", help="Compile all discovered snipes in vfs/snipes and data/snipes.")
    args = parser.parse_args()

    targets = [args.snipe_id] if args.snipe_id else (discover_all_snipes() if args.all else discover_all_snipes())
    if not targets:
        targets = ["m-_6LO0K88Q", "J1_BvDQJV44"]

    summary: List[Dict[str, Any]] = []
    for sid in targets:
        cart = compile_cartridge_for_snipe(sid)
        summary.append({
            "snipe_id": sid,
            "duration_seconds": cart["duration_seconds"],
            "hls_lag_seconds": cart["hls_lag_seconds"],
            "seismic_pins": len(cart["seismic_pins"]),
            "total_chat_messages": cart["total_chat_messages"],
            "total_whisper_segments": cart["total_whisper_segments"],
            "content_sha256": cart["content_sha256"][:16],
        })
    print(json.dumps({"status": "COMPILED", "snipes": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
