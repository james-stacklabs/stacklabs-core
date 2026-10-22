#!/usr/bin/env python3
"""
Sovereign OS: FaaS Source Chunker and Daily Partition Engine
Path: /home/james/stacklabs/scripts/core/source_chunker.py

Enforces the NotebookLM 500,000 character hard limit across continuous
FaaS chat streams and telemetry assets:
1. Partitions continuous raw stream chat into sequential daily parts <= 450,000 chars.
2. Extracts a rolling tail <= 450,000 chars at the root so NotebookLM sources never error.
3. Mirrors daily parts to Port 3033 (FanStack Lite public assets) and Google Drive staging.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

MAX_SOURCE_CHARS: int = 450_000


def get_rolling_tail(source_file: Union[str, Path], max_chars: int = MAX_SOURCE_CHARS) -> str:
    """
    Extracts the most recent <= max_chars characters cleanly from the end of the file.
    Breaks cleanly on message (\n\n) or newline (\n) boundaries.
    Uses seek for sub-second performance on large files.
    """
    path = Path(source_file)
    if not path.exists():
        return ""

    file_size = path.stat().st_size
    if file_size <= max_chars:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) <= max_chars:
            return content

    # Read the last max_chars * 1.5 bytes to ensure we cover enough UTF-8 characters
    read_bytes = min(file_size, int(max_chars * 1.5))
    with open(path, "rb") as f:
        f.seek(file_size - read_bytes)
        raw_tail = f.read()

    text = raw_tail.decode("utf-8", errors="replace")
    if len(text) > max_chars:
        candidate = text[-max_chars:]
        # Find clean boundary near the start of the candidate
        idx = candidate.find("\n\n")
        if idx != -1 and idx < max_chars * 0.2:
            candidate = candidate[idx + 2:]
        else:
            idx2 = candidate.find("\n")
            if idx2 != -1 and idx2 < max_chars * 0.2:
                candidate = candidate[idx2 + 1:]
        text = candidate

    return text


def partition_file_to_daily(
    source_file: Union[str, Path],
    daily_dir: Union[str, Path],
    base_stem: str = "stream_chat",
    max_chars: int = MAX_SOURCE_CHARS
) -> List[Path]:
    """
    Splits any source file into sequential _partXX.md chunks strictly <= max_chars characters,
    breaking cleanly on message (\n\n) or newline (\n) boundaries.
    Only writes files to disk when necessary to preserve I/O bandwidth.
    """
    src = Path(source_file)
    if not src.exists():
        return []

    dest_dir = Path(daily_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    text = src.read_text(encoding="utf-8", errors="replace")
    total_len = len(text)

    chunks: List[Path] = []
    curr_idx = 1
    pos = 0

    while pos < total_len:
        remaining = total_len - pos
        if remaining <= max_chars:
            chunk = text[pos:]
            pos = total_len
        else:
            candidate = text[pos:pos + max_chars]
            split_idx = candidate.rfind("\n\n")
            if split_idx != -1 and split_idx > max_chars * 0.8:
                cut = split_idx + 2
            else:
                split_idx2 = candidate.rfind("\n")
                if split_idx2 != -1 and split_idx2 > max_chars * 0.8:
                    cut = split_idx2 + 1
                elif split_idx != -1:
                    cut = split_idx + 2
                elif split_idx2 != -1:
                    cut = split_idx2 + 1
                else:
                    cut = max_chars

            chunk = candidate[:cut]
            pos += cut

        part_name = f"{base_stem}_part{curr_idx:02d}.md"
        part_file = dest_dir / part_name

        chunk_bytes = chunk.encode("utf-8")
        if not part_file.exists() or part_file.stat().st_size != len(chunk_bytes):
            part_file.write_bytes(chunk_bytes)

        chunks.append(part_file)
        curr_idx += 1

    return chunks


def process_daily_fanstack_sources(
    inbox_today: Union[str, Path],
    local_fanstack_live: Union[str, Path],
    public_fanstack_live: Union[str, Path],
    date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Top-level orchestrator:
    1. Chunks continuous stream_chat_tail.md into sequential daily parts in YYYY-MM-DD/.
    2. Writes rolling tail <= 450,000 characters to root stream_chat_tail.md in both
       local_fanstack_live and public_fanstack_live.
    3. Mirrors daily chunked files to public_fanstack_live.
    """
    inbox_path = Path(inbox_today)
    local_dir = Path(local_fanstack_live)
    public_dir = Path(public_fanstack_live)

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Locate source file
    source_candidates = [
        inbox_path / "stream_chat_tail.md",
        local_dir / "stream_chat_tail.md"
    ]
    source_file = None
    for cand in source_candidates:
        if cand.exists() and cand.stat().st_size > 0:
            source_file = cand
            break

    daily_local = local_dir / date_str
    daily_public = public_dir / date_str
    daily_local.mkdir(parents=True, exist_ok=True)
    daily_public.mkdir(parents=True, exist_ok=True)

    rolling_tail_chars = 0
    chunks_count = 0

    if source_file:
        # 1. Partition into daily local folder
        parts = partition_file_to_daily(source_file, daily_local, base_stem="stream_chat", max_chars=MAX_SOURCE_CHARS)
        chunks_count = len(parts)

        # 2. Mirror daily parts to public directory
        for part in parts:
            dest = daily_public / part.name
            if not dest.exists() or dest.stat().st_size != part.stat().st_size:
                shutil.copy2(part, dest)

        # 3. Extract rolling tail <= 450,000 characters
        rolling_tail = get_rolling_tail(source_file, max_chars=MAX_SOURCE_CHARS)
        rolling_tail_chars = len(rolling_tail)

        # 4. Write rolling tail to root locations
        local_root_tail = local_dir / "stream_chat_tail.md"
        public_root_tail = public_dir / "stream_chat_tail.md"
        local_root_tail.write_text(rolling_tail, encoding="utf-8")
        public_root_tail.write_text(rolling_tail, encoding="utf-8")

    # 5. Mirror other daily telemetry files into dated folders
    telemetry_to_mirror = [
        "VALIDATED_INTEL_15M.md",
        "wardy_chat_tail.md",
        "active_sports_ground_truth.json",
        "game_recap_live.json",
        "INGRESS_RAW_15M.json"
    ]
    for fname in telemetry_to_mirror:
        src_item = local_dir / fname
        if src_item.exists():
            for target_folder in [daily_local, daily_public]:
                target_file = target_folder / fname
                if not target_file.exists() or target_file.stat().st_mtime < src_item.stat().st_mtime:
                    shutil.copy2(src_item, target_file)

    return {
        "status": "OK",
        "date": date_str,
        "source_file": str(source_file) if source_file else None,
        "chunks_count": chunks_count,
        "rolling_tail_chars": rolling_tail_chars
    }


if __name__ == "__main__":
    import sys
    today_inbox = Path("/home/james/sovereign_inbox/today")
    local_live = today_inbox / "FanStack_Live"
    pub_live = Path("/home/james/stacklabs/33_FanStack_Lite/public/FanStack_Live")

    res = process_daily_fanstack_sources(today_inbox, local_live, pub_live)
    print(f"[OK] Source chunker executed: {res}")
