#!/usr/bin/env python3
"""
Sovereign OS: FanStack Chat Dossier Engine & Cross-Stream Persona Reconciler
Path: /home/james/stacklabs/scripts/extract_chat_personas.py

Autonomously parses high-volume live stream chat logs (stream_chat_tail.md,
wardy_chat_tail.md, and active slice files in FanStack_Live/), detects users appearing
across multiple creator streams, extracts their verbatim receipts, deterministically
scores their behavioral archetypes and reactivity, and persists a flat, decoupled
read-model to data/fanstack_chat_dossiers.json.

Governing Invariants:
- Rule Zero: Executed on Clio metal forge
- Invariant 21: Tenant Clean Room (Zero corporate host terms in consumer dossiers)
- Invariant 25: Decoupled Flat JSON Read-Model
- Invariant 35: Canonical Python venv enforcement
"""

import os
import sys

# Invariant 35: Enforce canonical SovereignOS virtual environment
VENV_PYTHON = "/home/james/stacklabs/.venv/bin/python3"
if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import re
import json
import glob
import argparse
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional

# Canonical Paths
DATA_DIR = "/home/james/stacklabs/data"
DEFAULT_PRIMARY_TAIL = "/home/james/stacklabs/data/stream_chat_tail.md"
DEFAULT_SECONDARY_TAIL = "/home/james/stacklabs/data/wardy_chat_tail.md"
FANSTACK_LIVE_DIR = "/home/james/stacklabs/33_FanStack_Lite/public/FanStack_Live"
DEFAULT_OUTPUT_FILE = "/home/james/stacklabs/data/fanstack_chat_dossiers.json"

# Invariant 21: Strict Clean Room Banned Terms
BANNED_CORPORATE_TERMS = [
    "amd zen 4", "35w apu", "12.53-day payback", "12.53 day payback",
    "ucc 2a", "$600 bom", "host lease", "payback period"
]

# Regex patterns for line parsing
RE_BRACKET = re.compile(r"^\[(\d{1,2}:\d{2}:\d{2})\]\s*(@+[^\s\[]+)\s*(?:\[(.*?)\])?\s*$")
RE_AUTHOR_ONLY = re.compile(r"^(@+[a-zA-Z0-9_\-]+)\s*$")
RE_SECTION = re.compile(r"^#+\s+(.+)$")


def normalize_handle(raw_author: str) -> str:
    """
    Normalizes any handle variant (@@@@Bob, @@@Bob, @@Bob, @Bob, Bob)
    to a single canonical @username string.
    """
    cleaned = raw_author.strip()
    cleaned = cleaned.lstrip("@").strip()
    return f"@{cleaned}"


def sanitize_clean_room(text: str) -> str:
    """
    Invariant 21: Prevents corporate host lease terms from appearing in consumer fan dossiers.
    """
    cleaned = text
    for term in BANNED_CORPORATE_TERMS:
        if term in cleaned.lower():
            cleaned = re.sub(re.escape(term), "[REDACTED]", cleaned, flags=re.IGNORECASE)
    return cleaned


def parse_chat_file(file_path: str) -> List[Tuple[str, str, str, str]]:
    """
    Parses a single chat file into a list of tuples:
    (timestamp, normalized_handle, stream_source, message_text)
    """
    if not os.path.exists(file_path):
        return []

    # Infer default stream name from filename or parent directory
    base_name = os.path.basename(file_path).lower()
    if "wardy" in base_name:
        current_stream = "Eagles Postgame"
    elif "stream_chat_part" in base_name or "stream_chat_tail" in base_name:
        current_stream = "The Pat McAfee Show"
    else:
        current_stream = os.path.splitext(os.path.basename(file_path))[0]

    messages: List[Tuple[str, str, str, str]] = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[WARN] Failed to read {file_path}: {e}", file=sys.stderr)
        return []

    i = 0
    n = len(lines)

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        if not line:
            i += 1
            continue

        # Markdown section header updates current stream
        sec_m = RE_SECTION.match(line)
        if sec_m:
            current_stream = sec_m.group(1).strip()
            i += 1
            continue

        # Pattern: [HH:MM:SS] @author [Optional Stream]
        bm = RE_BRACKET.match(line)
        if bm:
            ts = bm.group(1)
            raw_author = bm.group(2)
            stream = bm.group(3).strip() if bm.group(3) else current_stream
            handle = normalize_handle(raw_author)

            # Ingest message body until next message header or blank line
            i += 1
            msg_lines = []
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    break
                if RE_BRACKET.match(nxt.strip()) or RE_AUTHOR_ONLY.match(nxt.strip()) or RE_SECTION.match(nxt.strip()):
                    break
                msg_lines.append(nxt.rstrip())
                i += 1
            text = " ".join([l.strip() for l in msg_lines]).strip()
            if text:
                text = sanitize_clean_room(text)
                messages.append((ts, handle, stream, text))
            continue

        # Pattern: @@author (standalone)
        am = RE_AUTHOR_ONLY.match(line)
        if am:
            raw_author = am.group(1)
            handle = normalize_handle(raw_author)

            i += 1
            msg_lines = []
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    break
                if RE_BRACKET.match(nxt.strip()) or RE_AUTHOR_ONLY.match(nxt.strip()) or RE_SECTION.match(nxt.strip()):
                    break
                msg_lines.append(nxt.rstrip())
                i += 1
            text = " ".join([l.strip() for l in msg_lines]).strip()
            if text:
                text = sanitize_clean_room(text)
                messages.append(("", handle, current_stream, text))
            continue

        i += 1

    return messages


def classify_behavioral_archetype(
    handle: str,
    streams: List[str],
    receipts: List[Dict[str, str]],
    total_messages: int
) -> str:
    """
    Deterministically classifies a persona into one of 5 archetypes:
    - CROSS_SPORT_HEEL: Active across multiple streams with antagonistic / troll banter
    - HYPER_VELOCITY_CHAOS: Rapid-fire messages, high emoji density, hype screams
    - CAP_SPACE_CYNIC: Obsessed with player contracts, payroll, GM dead money
    - MORAL_VICTORY_COPE: Rationalizes losses with silver linings and future rebuilds
    - DOOMER_REALIST: Predicts catastrophic failure, benchings, and front office firing
    """
    combined_text = " ".join(r.get("text", "") for r in receipts).lower()

    # 1. CROSS_SPORT_HEEL: Priority check for multi-stream troll/antagonism
    if len(streams) >= 2:
        heel_keywords = [
            "miss", "fankees", "cry", "stinks", "troll", "heel", "sucks", "trash",
            "clowns", "bums", ":_tyomg:", "eagles lose", "cry eagles cry", "snit the bed",
            "alex acuna", "yuck", "whipped", "fightless birds"
        ]
        if any(k in combined_text for k in heel_keywords):
            return "CROSS_SPORT_HEEL"

    # 2. CAP_SPACE_CYNIC
    cap_space_keywords = [
        "paid", "contract", "salary", "cap space", "dead cap", "gm", "front office",
        "trade", "fleeced", "overpaid", "extension", "guaranteed money", "cut him",
        "2 dts", "no dbs", "cheap", "payroll", "tax", "million", "worth"
    ]
    if any(k in combined_text for k in cap_space_keywords):
        return "CAP_SPACE_CYNIC"

    # 3. MORAL_VICTORY_COPE
    cope_keywords = [
        "at least", "still better", "moral victory", "next year", "bright side",
        "silver lining", "not as bad", "barely lost", "proud of", "building",
        "rebuild", "cope harder", "could be worse", "growing pains", "7 second l"
    ]
    if any(k in combined_text for k in cope_keywords):
        return "MORAL_VICTORY_COPE"

    # 4. HYPER_VELOCITY_CHAOS
    chaos_markers = [
        ":_howyoudoin", ":_keepmovin", ":_letsgo", ":_wh1", ":_aa2", ":_ad3",
        "lfg", "gang fight", ":face_with_tears_of_joy:", ":red_heart:", ":folded_hands:",
        "here we go", "shaaaaht", "boom"
    ]
    has_high_emoji_or_markers = sum(1 for r in receipts if any(m in r.get("text", "").lower() for m in chaos_markers)) >= 2
    if total_messages >= 8 or has_high_emoji_or_markers:
        return "HYPER_VELOCITY_CHAOS"

    # 5. DOOMER_REALIST
    doomer_keywords = [
        "season over", "trash", "fire", "bench", "cooked", "washed", "stinks",
        "terrible", "embarrassing", "horrible", "disaster", "never winning", "done",
        "blow it up", "hate this", "worst"
    ]
    if any(k in combined_text for k in doomer_keywords):
        return "DOOMER_REALIST"

    # Deterministic fallback
    if len(streams) >= 2:
        return "CROSS_SPORT_HEEL"
    return "DOOMER_REALIST"


def calculate_reactivity_score(
    streams: List[str],
    receipts: List[Dict[str, str]],
    total_messages: int
) -> float:
    """
    Computes a grounded reactivity score between 1.0 and 5.0 based on
    cross-stream breadth, message frequency, and punctuation/sentiment intensity.
    """
    score = 2.5
    # Multi-stream bonus (+0.6 per extra stream, capped at +1.2)
    score += min(1.2, max(0, len(streams) - 1) * 0.6)
    # Velocity bonus (+0.05 per message, capped at +1.0)
    score += min(1.0, total_messages * 0.05)

    # Emotional intensity signals
    combined = " ".join(r.get("text", "") for r in receipts)
    exclamations = combined.count("!")
    questions = combined.count("?")
    caps_count = sum(1 for word in combined.split() if len(word) > 2 and word.isupper())
    emoji_count = combined.count(":") // 2

    intensity = 0.0
    if exclamations >= 2:
        intensity += 0.3
    if questions >= 2:
        intensity += 0.2
    if caps_count >= 3:
        intensity += 0.4
    if emoji_count >= 3:
        intensity += 0.3

    score += min(1.3, intensity)
    score = max(1.0, min(5.0, score))
    return round(score, 1)


def discover_input_files(
    custom_inputs: Optional[List[str]] = None,
    max_slice_files: int = 50
) -> List[str]:
    """
    Discovers chat telemetry files following Quarter 1 spec:
    1. Primary: data/stream_chat_tail.md
    2. Secondary: data/wardy_chat_tail.md
    3. Dynamic Fallback: data/*chat_tail*.md, data/*telemetry*.md
    4. Active slice files in FanStack_Live/
    """
    if custom_inputs:
        return [f for f in custom_inputs if os.path.exists(f)]

    collected: List[str] = []
    seen = set()

    def add_file(path: str):
        real = os.path.realpath(path) if os.path.exists(path) else path
        if os.path.exists(path) and real not in seen:
            seen.add(real)
            collected.append(path)

    # 1. Primary & Secondary
    add_file(DEFAULT_PRIMARY_TAIL)
    add_file(DEFAULT_SECONDARY_TAIL)

    # 2. Dynamic Fallback in data/
    for p in sorted(glob.glob(os.path.join(DATA_DIR, "*chat_tail*.md"))):
        add_file(p)
    for p in sorted(glob.glob(os.path.join(DATA_DIR, "*telemetry*.md"))):
        add_file(p)

    # 3. Active slice files in FanStack_Live/
    add_file(os.path.join(FANSTACK_LIVE_DIR, "stream_chat_tail.md"))
    add_file(os.path.join(FANSTACK_LIVE_DIR, "wardy_chat_tail.md"))

    # Add today's active date directory slice files if present
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_slices = sorted(glob.glob(os.path.join(FANSTACK_LIVE_DIR, today_str, "stream_chat_part*.md")))
    for p in today_slices[:max_slice_files]:
        add_file(p)

    # Also check yesterday's slice files if today has fewer than 10
    if len(today_slices) < 10:
        for date_dir in sorted(glob.glob(os.path.join(FANSTACK_LIVE_DIR, "2026-*")), reverse=True):
            slices = sorted(glob.glob(os.path.join(date_dir, "stream_chat_part*.md")))
            for p in slices[:max_slice_files]:
                add_file(p)
            if len(collected) >= 20:
                break

    return collected


def extract_dossiers(
    input_files: List[str],
    min_streams: int = 2,
    min_messages: int = 5
) -> Dict[str, Any]:
    """
    Processes all input files, aggregates messages by user, filters by threshold,
    and returns the structured dossier payload.
    """
    user_records = defaultdict(lambda: {
        "streams": set(),
        "receipts": [],
        "total": 0
    })

    total_corpus_messages = 0

    for fpath in input_files:
        msgs = parse_chat_file(fpath)
        total_corpus_messages += len(msgs)
        for ts, handle, stream, text in msgs:
            user_records[handle]["total"] += 1
            user_records[handle]["streams"].add(stream)
            user_records[handle]["receipts"].append({
                "timestamp": ts,
                "stream": stream,
                "text": text
            })

    unique_handles_count = len(user_records)
    dossiers_list = []
    multi_stream_count = 0

    for handle, data in user_records.items():
        total_msgs = data["total"]
        streams = sorted(list(data["streams"]))
        is_multi_stream = len(streams) >= min_streams
        meets_frequency = total_msgs >= min_messages

        if is_multi_stream:
            multi_stream_count += 1

        # Minimum threshold: >= 2 distinct streams OR >= 5 total messages
        if not (is_multi_stream or meets_frequency):
            continue

        # Deduplicate receipts while preserving chronological order
        dedup_receipts = []
        seen_receipt_keys = set()
        for r in data["receipts"]:
            key = (r.get("timestamp", ""), r.get("stream", ""), r.get("text", ""))
            if key not in seen_receipt_keys:
                seen_receipt_keys.add(key)
                dedup_receipts.append(r)

        # Retain up to 20 representative receipts
        capped_receipts = dedup_receipts[:20]

        archetype = classify_behavioral_archetype(handle, streams, capped_receipts, total_msgs)
        reactivity = calculate_reactivity_score(streams, capped_receipts, total_msgs)

        dossier = {
            "handle": handle,
            "archetype": archetype,
            "behavioral_archetype": archetype,
            "reactivity_score": reactivity,
            "total_messages": total_msgs,
            "streams_active": streams,
            "distinct_streams": streams,
            "receipts": capped_receipts,
            "verified_receipts": capped_receipts
        }
        dossiers_list.append(dossier)

    # Sort dossiers by reactivity_score descending, then total_messages descending
    dossiers_list.sort(key=lambda d: (d["reactivity_score"], d["total_messages"]), reverse=True)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_corpus_messages_scanned": total_corpus_messages,
        "unique_handles_tracked": unique_handles_count,
        "multi_stream_dossiers_count": multi_stream_count,
        "dossiers": dossiers_list
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="FanStack Chat Dossier Engine")
    parser.add_argument("--inputs", nargs="+", help="Specific chat log files to parse")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path for output JSON file")
    parser.add_argument("--max-slices", type=int, default=50, help="Max slice files to include from FanStack_Live")
    args = parser.parse_args()

    files = discover_input_files(args.inputs, max_slice_files=args.max_slices)
    print(f"[*] Ingesting {len(files)} telemetry sources on Clio metal...")
    for f in files[:5]:
        print(f"    - {f}")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more files")

    payload = extract_dossiers(files)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[+] Output written to {args.output}")
    print(f"[+] Corpus messages scanned: {payload['total_corpus_messages_scanned']}")
    print(f"[+] Unique handles tracked:  {payload['unique_handles_tracked']}")
    print(f"[+] Multi-stream personas:   {payload['multi_stream_dossiers_count']}")
    print(f"[+] Total dossiers indexed:  {len(payload['dossiers'])}")


if __name__ == "__main__":
    main()
