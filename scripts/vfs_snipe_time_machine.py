#!/home/james/stacklabs/.venv/bin/python3
"""
KISS & LITE VFS Time-Machine Materializer & Stigmergic Discord Lock (WO0011282).
I keep all snipe telemetry inside vfs/snipes/{id}/ as flat JSON/Markdown files
so humans, SLMs, and the browser UI can read them directly from pagecache.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path("/home/james/stacklabs")
VFS_SNIPES = ROOT / "vfs" / "snipes"
DATA_SNIPES = ROOT / "data" / "snipes"
WIRETAP_DB = ROOT / "data" / "morning_wiretap.db"
LOCK_FILE = ROOT / ".state" / "DISCORD_AUTH_TRIP.lock"


def check_or_trip_discord_lock(status_code: int = 0) -> bool:
    """2-microsecond kernel dentry check for Discord 401/403 protection."""
    if status_code in (401, 403):
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(f"TRIPPED_HTTP_{status_code}_{int(time.time())}\n", encoding="utf-8")
        return True
    return LOCK_FILE.exists()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _load_segments_from_folder(folder: Path) -> List[Dict[str, Any]]:
    if not folder.exists():
        return []
    for name in ("transcript.json", "segments.json", "whisper_segments.json"):
        p = folder / name
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                items = raw.get("segments", raw) if isinstance(raw, dict) else raw
                if isinstance(items, list):
                    return [
                        {
                            "id": i,
                            "start_sec": round(float(s.get("start", s.get("start_sec", i * 5.0))), 2),
                            "end_sec": round(float(s.get("end", s.get("end_sec", (i + 1) * 5.0))), 2),
                            "text": str(s.get("text", "")).strip(),
                        }
                        for i, s in enumerate(items)
                        if isinstance(s, dict) and str(s.get("text", "")).strip()
                    ]
            except (OSError, ValueError, json.JSONDecodeError):
                pass

    ts_re = re.compile(r"^\[?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.\d+)?\]?\s*(?:-|\u2013|\u2014)?\s*(.+)$")
    for name in (
        "transcript_aligned.md",
        "transcript_verbatim.md",
        "transcript.md",
        "summary_intel_brief.md",
        "brief.md",
        "dossier.md",
    ):
        p = folder / name
        if p.exists():
            segs: List[Dict[str, Any]] = []
            cursor = 0.0
            for idx, ln in enumerate(p.read_text(encoding="utf-8").splitlines()):
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                m = ts_re.match(ln)
                if m:
                    cursor = float(int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3)))
                    text = m.group(4).strip()
                else:
                    text = ln
                dur = max(4.0, min(12.0, len(text.split()) * 0.4))
                segs.append({"id": idx, "start_sec": round(cursor, 2), "end_sec": round(cursor + dur, 2), "text": text})
                cursor += dur
            if segs:
                return segs
    return []


def _load_or_liberate_chat(snipe_id: str, folder: Path) -> List[Dict[str, Any]]:
    chat_file = folder / "chat.jsonl"
    if chat_file.exists():
        rows = []
        for ln in chat_file.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    rows.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
        if rows:
            return rows

    if not WIRETAP_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(WIRETAP_DB), timeout=3.0)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, author, message, epoch_time FROM chat_telemetry "
            "WHERE channel_key IN (?, 'radio_mcafee', 'NFL_live', 'CFB_GameDay_Live') "
            "ORDER BY id DESC LIMIT 1500",
            (snipe_id,),
        )
        fetched = [dict(r) for r in cur.fetchall()][::-1]
        conn.close()
        if fetched:
            lines = "\n".join(json.dumps(r, separators=(",", ":")) for r in fetched) + "\n"
            _atomic_write(chat_file, lines)
        return fetched
    except sqlite3.Error:
        return []


def build_snipe_time_machine(snipe_id: str) -> Dict[str, Any]:
    vfs_dir = VFS_SNIPES / snipe_id
    data_dir = DATA_SNIPES / snipe_id
    source_dir = vfs_dir if vfs_dir.exists() else data_dir
    source_dir.mkdir(parents=True, exist_ok=True)

    segments = _load_segments_from_folder(source_dir) or _load_segments_from_folder(data_dir)
    chat_rows = _load_or_liberate_chat(snipe_id, source_dir)

    duration_s = max((s["end_sec"] for s in segments), default=600.0)
    hls_lag_s = 14.0
    bucket_sec = 10
    num_buckets = max(1, min(1200, int(math.ceil(duration_s / bucket_sec))))

    buckets = [
        {
            "bucket_index": i,
            "offset_sec": i * bucket_sec,
            "end_offset_sec": (i + 1) * bucket_sec,
            "velocity_mpm": 0.0,
            "z_score": 0.0,
            "top_messages": [],
        }
        for i in range(num_buckets)
    ]

    if chat_rows:
        base_epoch = float(chat_rows[0].get("epoch_time") or 0.0)
        span = max(1.0, float(chat_rows[-1].get("epoch_time") or base_epoch) - base_epoch)
        for idx, msg in enumerate(chat_rows):
            raw_dt = float(msg.get("epoch_time") or base_epoch) - base_epoch
            rel_sec = (raw_dt / span) * duration_s if span > duration_s * 2 else raw_dt
            trigger_sec = max(0.0, rel_sec - hls_lag_s)
            b_idx = min(num_buckets - 1, max(0, int(trigger_sec // bucket_sec)))
            buckets[b_idx]["top_messages"].append({
                "id": int(msg.get("id", idx)),
                "author": str(msg.get("author", "fan")),
                "message": str(msg.get("message", "")),
                "audio_trigger_sec": round(trigger_sec, 1),
            })

    for b in buckets:
        cnt = len(b["top_messages"])
        b["velocity_mpm"] = round(cnt * 6.0, 1)
        b["top_messages"] = b["top_messages"][:10]

    if sum(b["velocity_mpm"] for b in buckets) == 0 and segments:
        for seg in segments:
            b_idx = min(num_buckets - 1, max(0, int(seg["start_sec"] // bucket_sec)))
            buckets[b_idx]["velocity_mpm"] = round(buckets[b_idx]["velocity_mpm"] + len(seg["text"].split()) * 1.5, 1)

    vels = [b["velocity_mpm"] for b in buckets]
    mean_v = sum(vels) / len(vels) if vels else 1.0
    std_v = max(1.0, math.sqrt(sum((v - mean_v) ** 2 for v in vels) / max(1, len(vels))))

    pins: List[Dict[str, Any]] = []
    md_lines = [f"# Seismic Spikes Chronicle — {snipe_id}", ""]

    for b in buckets:
        z = round((b["velocity_mpm"] - mean_v) / std_v, 2)
        b["z_score"] = z
        if z >= 1.8 and len(pins) < 10:
            ts = f"{int(b['offset_sec'] // 60):02d}:{int(b['offset_sec'] % 60):02d}"
            trig = next(
                (s["text"] for s in segments if abs(s["start_sec"] - b["offset_sec"]) <= 12.0),
                "Spoken broadcast trigger",
            )
            pin = {
                "pin_id": f"spike_{int(b['offset_sec']):04d}",
                "offset_sec": b["offset_sec"],
                "timestamp_label": ts,
                "velocity_mpm": b["velocity_mpm"],
                "z_score": z,
                "spoken_trigger": trig[:180],
            }
            pins.append(pin)
            md_lines.append(f"## [{ts}] +{z}σ ({b['velocity_mpm']} mpm)")
            md_lines.append(f"- **Spoken Trigger (T0)**: {trig[:180]}")
            for m in b["top_messages"][:3]:
                md_lines.append(f"  - `{m['author']}`: {m['message']}")
            md_lines.append("")

    payload = {
        "snipe_id": snipe_id,
        "duration_seconds": round(duration_s, 2),
        "hls_lag_seconds": hls_lag_s,
        "peak_velocity_mpm": round(max(vels, default=0.0), 1),
        "seismic_pins": pins,
        "buckets": buckets,
        "segments": segments[:800],
    }

    json_text = json.dumps(payload, indent=2)
    md_text = "\n".join(md_lines) + "\n"
    seen_targets = set()
    for target in (vfs_dir, data_dir):
        target.mkdir(parents=True, exist_ok=True)
        resolved = str(target.resolve())
        if resolved in seen_targets:
            continue
        seen_targets.add(resolved)
        _atomic_write(target / "time_machine.json", json_text)
        _atomic_write(target / "spikes.md", md_text)

    return payload


if __name__ == "__main__":
    discovered = sorted({
        d.name for base in (VFS_SNIPES, DATA_SNIPES) if base.exists()
        for d in base.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "cache"
    }) or ["m-_6LO0K88Q", "J1_BvDQJV44"]
    out = [
        {"snipe_id": sid, "pins": len(build_snipe_time_machine(sid)["seismic_pins"])}
        for sid in discovered
    ]
    print(json.dumps({"materialized_vfs_snipes": out}, indent=2))
