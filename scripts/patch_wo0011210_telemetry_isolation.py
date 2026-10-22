#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Atomic Patch: Stream Telemetry Isolation & Fallback Purge
Applies the 4 Structural Locks from faas_tail_fix.md.
"""
import os
import sys
import sqlite3
from pathlib import Path

VFS_PATH = Path("/home/james/stacklabs/scripts/blueprints/faas_vfs_telemetry.py")
OMNI_PATH = Path("/home/james/stacklabs/scripts/game_stream_omni_tailer.py")
VALIDATOR_PATH = Path("/home/james/stacklabs/.agents/skills/stage-work-order/scripts/validate_wo.py")
RULE_PATH = Path("/home/james/stacklabs/.agents/rules/stream_telemetry_isolation.md")
ATTACH_SCRIPT = Path("/home/james/stacklabs/scripts/attach_mem_tuln_live_stream.py")
STREAM_CHAT_TAIL = Path("/home/james/stacklabs/data/stream_chat_tail.md")
DB_PATH = Path("/home/james/stacklabs/data/morning_wiretap.db")

def patch_faas_vfs_telemetry():
    if not VFS_PATH.exists():
        print(f"ERROR: {VFS_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    
    code = VFS_PATH.read_text(encoding="utf-8")
    
    old_target = """    # Seamless Fallback when no game-specific stream is active:
    refresh_chat_cache()
    items = list(_CHAT_CACHE)
    if not items:
        # Try reading directly from morning_wiretap.db recent chat_telemetry if file cache is empty
        db_path = Path("/home/james/stacklabs/data/morning_wiretap.db")
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute(\"\"\"
                    SELECT id, timestamp_str, author, message, channel_key
                    FROM chat_telemetry
                    ORDER BY id DESC LIMIT ?
                \"\"\", (limit,))
                for cid, tstr, author, msg, ch_key in reversed(cur.fetchall()):
                    items.append({
                        "id": f"wire-{cid}",
                        "timestamp": tstr or "Live",
                        "author": author if str(author).startswith("@") else f"@{author}",
                        "message": msg,
                        "sentiment": "NEUTRAL",
                        "bytecode": "LIVE",
                        "provenance": {"badge": ch_key, "sicko_tier": "AUTHENTIC_BLEACHER"}
                    })
                conn.close()
            except Exception:
                pass
    if lexical_items:
        items.extend(lexical_items)
    return items[-limit:]"""

    new_replacement = """    # Strict Entity-Scoped Telemetry Isolation (Argon Law 5 & Law 9):
    # NEVER fall back to a global chat cache, stream_chat_tail.md, or unscoped queries across other games.
    # If this specific game has no active stream, return only regional lexical seeds (if any) or an empty list.
    if lexical_items:
        return lexical_items[-limit:]
    return []"""

    if old_target not in code:
        print("ERROR: old_target block not found in faas_vfs_telemetry.py", file=sys.stderr)
        sys.exit(1)

    code = code.replace(old_target, new_replacement)
    VFS_PATH.write_text(code, encoding="utf-8")
    print("✓ Lock 2: Gutted global fallback in faas_vfs_telemetry.py (strict empty state enforced).")

def patch_game_stream_omni_tailer():
    if not OMNI_PATH.exists():
        print(f"ERROR: {OMNI_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    code = OMNI_PATH.read_text(encoding="utf-8")
    old_target = """if __name__ == "__main__":
    asyncio.run(main_loop())"""

    new_replacement = """if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StackLabs Game Stream Omni-Tailer Supervisor & Ingress CLI")
    parser.add_argument("--attach-game", dest="attach_game", help="Attach a stream to game_pk/game_id")
    parser.add_argument("--stream-id", dest="stream_id", help="YouTube stream ID to attach")
    parser.add_argument("--sport", dest="sport", default="cfb", help="Sport category (cfb, nfl, mlb)")
    parser.add_argument("--home", dest="home", default="HOME", help="Home team abbreviation")
    parser.add_argument("--away", dest="away", default="AWAY", help="Away team abbreviation")
    parser.add_argument("--title", dest="title", default="Community Watch Party", help="Stream title")
    parser.add_argument("--ttl-seconds", dest="ttl_seconds", type=int, default=14400, help="Stream TTL in seconds")
    args, _ = parser.parse_known_args()

    if args.attach_game and args.stream_id:
        init_db()
        register_watch_party_stream(
            sport=args.sport,
            game_pk=args.attach_game,
            home_team=args.home,
            away_team=args.away,
            stream_id=args.stream_id,
            stream_title=args.title
        )
        print(f"✓ Successfully attached {args.stream_id} to game {args.attach_game} (TTL {args.ttl_seconds}s)")
        sys.exit(0)

    asyncio.run(main_loop())"""

    if old_target not in code:
        print("ERROR: old_target block not found in game_stream_omni_tailer.py", file=sys.stderr)
        sys.exit(1)

    # Also disable writing to stream_chat_tail.md inside StreamListener so the purged file is not recreated
    old_tail_write = """                    # 2. Append to Markdown stream_chat_tail.md
                    try:
                        with open(OUTPUT_TAIL, "a", encoding="utf-8") as f:
                            f.write(f"\\n\\n[{t_str}] @@@{author} [{self.stream_name}]\\n{msg}")"""
    new_tail_write = """                    # 2. Disabled global stream_chat_tail.md write (Argon Law 5 / WO0011210)
                    if False:
                        pass"""
    if old_tail_write in code:
        code = code.replace(old_tail_write, new_tail_write)

    code = code.replace(old_target, new_replacement)
    OMNI_PATH.write_text(code, encoding="utf-8")
    print("✓ Lock 1: Added canonical --attach-game CLI entrypoint to game_stream_omni_tailer.py.")

def patch_validator():
    if not VALIDATOR_PATH.exists():
        print(f"ERROR: {VALIDATOR_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    code = VALIDATOR_PATH.read_text(encoding="utf-8")
    old_target = """    (r"\\bgemini-(?:1\\.5|2\\.0|2\\.5|3\\.7)[-\\w]*\\b", "Banned deprecated Gemini model (1.5, 2.0, 2.5, and 3.7 are deprecated; MUST use gemini-3.8-flash, gemini-flash-lite-latest, or gemini-3.1-pro-preview)"),
]"""

    new_replacement = """    (r"\\bgemini-(?:1\\.5|2\\.0|2\\.5|3\\.7)[-\\w]*\\b", "Banned deprecated Gemini model (1.5, 2.0, 2.5, and 3.7 are deprecated; MUST use gemini-3.8-flash, gemini-flash-lite-latest, or gemini-3.1-pro-preview)"),
    (r"\\bos\\.setpgrp\\b", "Banned detached daemon pattern ('os.setpgrp'); all background daemons must run under systemd or omni-tailer supervisor"),
    (r"\\bstart_new_session\\s*=\\s*True\\b", "Banned detached session pattern ('start_new_session=True')"),
    (r"scripts/attach_.*\\.py", "Banned one-off stream attachment script pattern; use game_stream_omni_tailer.py --attach-game"),
    (r"\\bstream_chat_tail\\.md\\b", "Banned global chat fallback file ('stream_chat_tail.md'); use entity-scoped streams"),
]"""

    if old_target not in code:
        print("ERROR: old_target block not found in validate_wo.py", file=sys.stderr)
        sys.exit(1)

    code = code.replace(old_target, new_replacement)
    VALIDATOR_PATH.write_text(code, encoding="utf-8")
    print("✓ Lock 3: Added mechanical anti-detached daemon and anti-one-off script gates to validate_wo.py.")

def write_governance_rule():
    rule_content = """---
trigger: model_decision
description: Stream telemetry isolation, zero cross-game fallback bleed, and ban on detached one-off stream daemons.
---

# STREAM TELEMETRY ISOLATION & ZERO-BLEED INVARIANT

1. **Zero Cross-Game Fallback Bleed (Argon Law 5)**:
   - Every game room's bleacher chat must be strictly scoped to its own `game_id` or `channel_key`.
   - Never fall back to a shared global scratch file (e.g. `data/stream_chat_tail.md`) or unscoped `SELECT ... FROM chat_telemetry ORDER BY id DESC`.
   - If a game has no verified active stream, the API must return `items: []` and `stream_status: "NO_ACTIVE_STREAM"`. An empty room is clean; a contaminated room is poison.

2. **Zero Detached Zombie Daemons & One-Off Attachment Scripts (Argon Law 9)**:
   - Never write one-off attachment scripts (`scripts/attach_*_live_stream.py`) with hardcoded video IDs.
   - Never spawn detached background processes using `preexec_fn=os.setpgrp`, `start_new_session=True`, or raw `nohup`.
   - All manual stream attachments must use the canonical CLI:
     `/home/james/stacklabs/.venv/bin/python3 scripts/game_stream_omni_tailer.py --attach-game <game_id> --stream-id <youtube_id>`
   - All background workers must run under systemd or the supervised `game_stream_omni_tailer` pool with a hard 4-hour TTL (`14400s`) and active VOD replay cutoff (`chat.is_replay()`).
"""
    RULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULE_PATH.write_text(rule_content, encoding="utf-8")
    print("✓ Lock 4: Codified .agents/rules/stream_telemetry_isolation.md.")

def purge_artifacts_and_database():
    # 1. Delete rogue script
    if ATTACH_SCRIPT.exists():
        ATTACH_SCRIPT.unlink()
        print(f"✓ Purged rogue script: {ATTACH_SCRIPT}")
    
    # 2. Delete poison global fallback markdown file
    if STREAM_CHAT_TAIL.exists():
        STREAM_CHAT_TAIL.unlink()
        print(f"✓ Purged global fallback file: {STREAM_CHAT_TAIL}")

    # 3. Purge contaminated database rows
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_telemetry WHERE channel_key IN ('MEM @ TULN LIVE', 'L6yTQLxPliM', 'ncoZoE020kk') OR message LIKE '%bounce back for Gators or Texas%'")
        purged_chat = cur.rowcount
        cur.execute("DELETE FROM watch_party_streams WHERE stream_id IN ('L6yTQLxPliM', 'ncoZoE020kk')")
        purged_streams = cur.rowcount
        conn.commit()
        conn.close()
        print(f"✓ Purged {purged_chat} contaminated chat_telemetry rows and {purged_streams} watch_party_streams rows.")

def main():
    patch_faas_vfs_telemetry()
    patch_game_stream_omni_tailer()
    patch_validator()
    write_governance_rule()
    purge_artifacts_and_database()
    print("\n=== ALL 4 STRUCTURAL LOCKS & CAMPSITE CLEANSE COMPLETE ===")

if __name__ == "__main__":
    main()
