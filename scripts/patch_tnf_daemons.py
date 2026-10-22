#!/usr/bin/env python3
"""
Surgical Patcher for TNF Stream Sniper, Omni-Tailer & FaaS Server
Path: /home/james/stacklabs/scripts/patch_tnf_daemons.py
"""
import os
import re
import sys
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")

def patch_stream_sniper():
    path = STACKLABS_ROOT / "scripts" / "stream_sniper_daemon.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update hardcoded video_id in watchdog to xyYgJ0vTd2g (Cowboys Report live now)
    content = re.sub(
        r'video_id = "[A-Za-z0-9_-]{11}"',
        'video_id = "xyYgJ0vTd2g"',
        content,
        count=1
    )

    # 2. Fix output_file / TRANSCRIBE_DIR / OUTPUT_DIR to canonical stacklabs paths
    content = content.replace(
        '/home/james/sovereign_inbox/media_transcribe',
        '/home/james/stacklabs/data/media_transcribe'
    )
    content = content.replace(
        'output_md = f"/home/james/sovereign_inbox/today/stream_chat_tail.md"',
        'output_md = "/home/james/stacklabs/data/stream_chat_tail.md"'
    )
    content = content.replace(
        'output_file = "/home/james/sovereign_inbox/today/stream_chat_tail.md"',
        'output_file = "/home/james/stacklabs/data/stream_chat_tail.md"'
    )
    content = content.replace(
        'chat_file = "/home/james/sovereign_inbox/today/stream_chat_tail.md"',
        'chat_file = "/home/james/stacklabs/data/stream_chat_tail.md"'
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✔ [PATCH] stream_sniper_daemon.py updated (xyYgJ0vTd2g + canonical path)")

def patch_omni_tailer():
    path = STACKLABS_ROOT / "scripts" / "game_stream_omni_tailer.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Ensure EXPLICIT_ACTIVE_STREAMS includes tonight's streams
    old_explicit = "EXPLICIT_ACTIVE_STREAMS: List[Dict[str, str]] = []"
    new_explicit = """EXPLICIT_ACTIVE_STREAMS: List[Dict[str, str]] = [
    {"key": "DAL_cowboys_report", "name": "Cowboys Report by Chat Sports", "stream_id": "xyYgJ0vTd2g"},
    {"key": "TB_pewter_report", "name": "Pewter Report Live React", "stream_id": "d3G8B6AdDMg"}
]"""
    if old_explicit in content:
        content = content.replace(old_explicit, new_explicit)

    # 2. Fix OUTPUT_TAIL
    content = content.replace(
        'OUTPUT_TAIL = "/home/james/sovereign_inbox/today/stream_chat_tail.md"',
        'OUTPUT_TAIL = "/home/james/stacklabs/data/stream_chat_tail.md"'
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✔ [PATCH] game_stream_omni_tailer.py updated (explicit TNF streams + canonical path)")

def patch_faas_server():
    path = STACKLABS_ROOT / "scripts" / "faas_server.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update chat_file resolution in update_provenance_cache and get_stream_chat_tail
    chat_path_snippet = """    chat_file = "/home/james/stacklabs/data/stream_chat_tail.md"
    if not os.path.exists(chat_file):
        chat_file = "/home/james/stacklabs_inbox/today/stream_chat_tail.md"
    if not os.path.exists(chat_file):
        chat_file = "/home/james/stacklabs/apps/faas/public/FanStack_Live/stream_chat_tail.md" """

    # Replace legacy sovereign_inbox references in chat endpoints
    pattern = r'    chat_file = "/home/james/sovereign_inbox/today/FanStack_Live/stream_chat_tail\.md"\s+if not os\.path\.exists\(chat_file\):\s+chat_file = "/home/james/sovereign_inbox/today/stream_chat_tail\.md"'
    content = re.sub(pattern, chat_path_snippet, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✔ [PATCH] faas_server.py updated (canonical chat_file paths)")

def main():
    print("=== PATCHING TNF DAEMONS ===")
    patch_stream_sniper()
    patch_omni_tailer()
    patch_faas_server()
    print("=== PATCHING COMPLETE ===")

if __name__ == "__main__":
    main()
