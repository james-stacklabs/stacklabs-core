#!/home/james/stacklabs/.venv/bin/python3
"""
Test Harness for Unhinged Fan Radar & Bleacher Canvas Filtering
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/test_unhinged_radar.py
"""
import sqlite3
import sys

DB_PATH = "/home/james/stacklabs/data/morning_wiretap.db"

BOT_DENYLIST = {
    "streamlabs", "nightbot", "streamelements", "moobot", "wizebot",
    "bot", "automod", "restreambot", "fossabot", "chatbot", "moderator"
}


def test_radar() -> int:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("""
        SELECT author, message 
        FROM chat_telemetry 
        ORDER BY rowid DESC LIMIT 100
    """)
    rows = cur.fetchall()
    conn.close()

    bot_caught = 0
    fan_quotes = 0
    for author, msg in rows:
        auth_clean = author.lower().lstrip("@")
        if any(b in auth_clean for b in BOT_DENYLIST):
            bot_caught += 1
        elif len(msg.split()) >= 3:
            fan_quotes += 1

    print(f"Audit Complete: Processed 100 recent rows.")
    print(f"  - Bot messages filtered: {bot_caught}")
    print(f"  - Qualified fan candidates: {fan_quotes}")

    if fan_quotes == 0:
        print("ERROR: Zero fan quotes qualified!")
        return 1

    print("✓ Radar filtering verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(test_radar())
