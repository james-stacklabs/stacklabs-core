#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Cockpit Review Terminal
Path: /home/james/stacklabs/scripts/cockpit_review.py
Governed by: Invariant 1 (Small Ball Metal), Invariant 35 (Canonical .venv)

Human-in-the-loop gatekeeper for staged takes.
"""

import sys
import sqlite3
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "stacklabs_telemetry.db"
STAGING_FILE = REPO_ROOT / "pilot_drops" / "barf_staging.md"

def copy_to_clipboard(text: str) -> bool:
    """Copies text to Linux X11/Wayland clipboard with fallback to staging file."""
    # Write to local staging file regardless
    STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STAGING_FILE, "w", encoding="utf-8") as f:
        f.write(text + "\n")
        
    try:
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True, timeout=2)
        return True
    except Exception:
        try:
            subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=True, timeout=2)
            return True
        except Exception:
            return False

def main():
    if not DB_PATH.exists():
        print(f"[!] No database found at {DB_PATH}")
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_stream, meltdown_topic, tweet_draft, char_count FROM staged_takes WHERE status = 'STAGED' ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()

    if not rows:
        print("\n=== STACKLABS COCKPIT: ZERO PENDING TAKES ===")
        print("Metal is quiet. All queues clear.\n")
        return

    print("\n" + "="*60)
    print(" 📡 STACKLABS BLEACHER RADAR: STAGED TAKES FOR REVIEW")
    print("="*60)

    for row in rows:
        take_id, source, topic, draft, chars = row
        char_status = "[GREEN - OK]" if chars <= 280 else "[RED - OVER 280 LIMIT]"
        print(f"\n[ID #{take_id}] | Source: {source} | Topic: {topic}")
        print(f"Char Count: {chars}/280 {char_status}")
        print("-" * 50)
        print(draft)
        print("-" * 50)
        
        try:
            choice = input("[A]pprove & Copy | [D]iscard | [S]kip: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if choice == 'a':
            copied = copy_to_clipboard(draft)
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE staged_takes SET status = 'APPROVED' WHERE id = ?", (take_id,))
            msg = "Copied to clipboard!" if copied else "Wrote to pilot_drops/barf_staging.md"
            print(f"✅ {msg} Ready for dispatch.")
        elif choice == 'd':
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE staged_takes SET status = 'DISCARDED' WHERE id = ?", (take_id,))
            print("🗑️ Discarded.")
        else:
            print("⏭️ Skipped.")

if __name__ == "__main__":
    main()
