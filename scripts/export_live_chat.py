#!/usr/bin/env python3
"""
export_live_chat.py
===================
STRY-06072026-LOG-INTEGRATION — Phase 2: Live Game Log Exporter

Accesses the game_chat table in the local SQLite database to retrieve and export
formatted chronological chat logs for the active game PK (e.g., 824916).
"""

import sqlite3
import sys
import os
import argparse
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    parser = argparse.ArgumentParser(description="Export live game chat logs to Markdown.")
    parser.add_argument("--game_pk", type=str, default="824916", help="MLB Game PK to export")
    parser.add_argument("--output", type=str, help="Output file path (Markdown)")
    args = parser.parse_args()

    game_pk = args.game_pk
    output_path = args.output

    if not output_path:
        # Default destination path as specified
        output_path = f"/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/game_log_{game_pk}_live.md"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # 1. Fetch game details from schedule
        game_row = conn.execute(
            "SELECT * FROM mlb_schedule WHERE game_pk = ?", (game_pk,)
        ).fetchone()

        if game_row:
            game = dict(game_row)
        else:
            # Fallback metadata if game not in schedule
            game = {
                "game_pk": game_pk,
                "game_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "away_team": "PIT",
                "home_team": "ATL",
                "venue": "Truist Park"
            }

        matchup = f"{game.get('away_team', '?')} @ {game.get('home_team', '?')}"
        game_date = game.get("game_date", "Unknown Date")
        venue = game.get("venue", "N/A")

        # 2. Query game_chat table for chronological log
        chats = conn.execute("""
            SELECT created_at AS ts, persona, text, model
            FROM game_chat
            WHERE game_pk = ?
            ORDER BY created_at ASC
        """, (game_pk,)).fetchall()

        conn.close()

        total_events = len(chats)
        chat_messages = len(chats)

        # 3. Format into pristine Markdown conforming to standard log schema
        lines = [
            f"# 📋 Game Room Log: {matchup}",
            f"**Date:** {game_date}  |  **Game PK:** {game_pk}  |  **Venue:** {venue}",
            f"**Exported:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## Summary",
            f"- **Total Events:** {total_events}",
            f"- **Chat Messages:** {chat_messages}",
            "- **Plays Logged:** 0",
            "",
            "---",
            "",
            "## Chronological Log",
            "",
        ]

        for row in chats:
            ts = (row["ts"] or "")[:19].replace("T", " ")
            persona = row["persona"] or "?"
            model = row["model"] or ""
            text = row["text"] or ""
            model_tag = f" `[{model}]`" if model else ""
            lines.append(f"**{ts}** 🗣️ **{persona}**{model_tag}")
            lines.append(f"> {text}")
            lines.append("")

        content = "\n".join(lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Successfully exported {chat_messages} messages for game {game_pk} to {output_path}")

    except Exception as e:
        print(f"Error during chat log export: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
