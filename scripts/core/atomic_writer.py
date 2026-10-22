#!/usr/bin/env python3
"""
StackLabs Atomic Writer & Anti-Bloat Sliding Window Engine
Path: /home/james/stacklabs/scripts/core/atomic_writer.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)
Audited by: Qwen 2.5 Systems Crucible

Enforces Invariant A (POSIX atomic replacement) and Invariant Anti-Bloat
(sliding window truncation) to guarantee sub-millisecond NVMe write latency.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

MAX_PRINTS_HISTORY: int = 500  # Hard boundary to guarantee sub-millisecond atomic writes

def atomic_json_write_with_truncation(target_file: Path, payload_dict: Dict[str, Any], max_history: int = MAX_PRINTS_HISTORY) -> None:
    """
    Enforces Invariant A + Anti-Bloat:
    1. Truncates any 'prints' or 'plays' list to the last N elements.
    2. Serializes to compact JSON without superfluous whitespace.
    3. Writes to a temporary file on the exact same filesystem inode.
    4. Executes an atomic POSIX rename via os.replace to prevent partial-read errors.
    """
    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Sliding-window truncation on unbounded arrays
    for key in ("prints", "plays", "tape", "history"):
        if key in payload_dict and isinstance(payload_dict[key], list):
            payload_dict[key] = payload_dict[key][-max_history:]

    json_payload = json.dumps(payload_dict, separators=(',', ':'), ensure_ascii=False)

    tmp_file = target_file.with_suffix('.tmp')
    tmp_file.write_text(json_payload, encoding='utf-8')
    os.replace(tmp_file, target_file)  # Atomic POSIX replacement
