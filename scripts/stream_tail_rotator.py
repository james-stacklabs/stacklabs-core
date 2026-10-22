#!/usr/bin/env python3
"""
Stream Tail Rotator & Ring Buffer Engine
Path: /home/james/stacklabs/scripts/stream_tail_rotator.py
Tool #72 // StackLabs Data Plane

Maintains bounded rolling buffers for stream chat tails on local host.
Prevents flat file runaway bloat while preserving historical telemetry
in gzip-compressed partition archives.
"""

import os
import sys
import gzip
import shutil
import argparse
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_TAIL_PATH = Path("/home/james/stacklabs/data/stream_chat_tail.md")
DEFAULT_ARCHIVE_DIR = Path("/home/james/stacklabs/data/archive")
DEFAULT_KEEP_LINES = 5000
DEFAULT_MAX_SIZE_MB = 2.0


def rotate_tail_file(
    tail_path: Path = DEFAULT_TAIL_PATH,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    keep_lines: int = DEFAULT_KEEP_LINES,
    max_size_mb: float = DEFAULT_MAX_SIZE_MB,
    force: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Inspects target tail file. If size exceeds max_size_mb (or force=True),
    compresses current contents into archive_dir, and atomically replaces
    the tail file with only the last keep_lines.
    """
    if not tail_path.exists():
        return {"status": "skipped", "reason": f"File does not exist: {tail_path}"}

    original_size_bytes = tail_path.stat().st_size
    original_size_mb = original_size_bytes / (1024 * 1024)

    if not force and original_size_mb < max_size_mb:
        return {
            "status": "noop",
            "size_mb": round(original_size_mb, 3),
            "threshold_mb": max_size_mb,
            "message": "File is within size threshold."
        }

    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"stream_chat_tail_{timestamp_str}.md.gz"
    archive_path = archive_dir / archive_filename

    if dry_run:
        return {
            "status": "dry_run",
            "original_size_mb": round(original_size_mb, 2),
            "planned_archive": str(archive_path),
            "keep_lines": keep_lines
        }

    # Step 1: Compress existing file to archive
    with open(tail_path, "rb") as f_in:
        with gzip.open(archive_path, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)

    compressed_size_bytes = archive_path.stat().st_size
    compressed_size_mb = compressed_size_bytes / (1024 * 1024)

    # Step 2: Read only the last keep_lines using deque
    tail_buffer = deque(maxlen=keep_lines)
    total_lines = 0
    with open(tail_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            tail_buffer.append(line)

    # Step 3: Write retained lines to a temporary file and atomically replace
    temp_path = tail_path.parent / f".{tail_path.name}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f_temp:
        f_temp.writelines(tail_buffer)

    os.replace(temp_path, tail_path)
    os.chmod(tail_path, 0o664)

    new_size_bytes = tail_path.stat().st_size
    new_size_kb = new_size_bytes / 1024

    result = {
        "status": "rotated",
        "archive_file": str(archive_path),
        "archive_size_mb": round(compressed_size_mb, 2),
        "original_lines": total_lines,
        "original_size_mb": round(original_size_mb, 2),
        "retained_lines": len(tail_buffer),
        "new_size_kb": round(new_size_kb, 2),
        "timestamp": datetime.now().isoformat()
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Rotate and bound stream_chat_tail.md ring buffer")
    parser.add_argument("--tail-path", type=str, default=str(DEFAULT_TAIL_PATH), help="Path to tail file")
    parser.add_argument("--archive-dir", type=str, default=str(DEFAULT_ARCHIVE_DIR), help="Archive directory")
    parser.add_argument("--keep-lines", type=int, default=DEFAULT_KEEP_LINES, help="Number of trailing lines to retain")
    parser.add_argument("--max-size-mb", type=float, default=DEFAULT_MAX_SIZE_MB, help="Size threshold in MB triggering rotation")
    parser.add_argument("--force", action="store_true", help="Force rotation regardless of file size")
    parser.add_argument("--dry-run", action="store_true", help="Check status without modifying files")

    args = parser.parse_args()
    res = rotate_tail_file(
        tail_path=Path(args.tail_path),
        archive_dir=Path(args.archive_dir),
        keep_lines=args.keep_lines,
        max_size_mb=args.max_size_mb,
        force=args.force,
        dry_run=args.dry_run
    )

    import json
    print(json.dumps(res, indent=2))
    if res.get("status") in ["rotated", "noop", "dry_run"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
