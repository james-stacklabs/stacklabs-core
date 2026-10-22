#!/usr/bin/env python3
import sys
import os
import sqlite3
import argparse
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    parser = argparse.ArgumentParser(description="Export a unified, chronological log of chat messages and play-by-play events.")
    parser.add_argument("--game_pk", required=True, help="The game PK to export.")
    parser.add_argument("--output", help="Output path for the generated log. Defaults to /home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/game_room_log_{game_pk}.md")
    args = parser.parse_args()

    game_pk = args.game_pk
    output_path = args.output

    if not output_path:
        output_dir = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"game_room_log_{game_pk}.md")

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Fetch Game Metadata
    home_team = "Unknown"
    away_team = "Unknown"
    game_date = "Unknown"
    venue = "Unknown"

    try:
        cursor.execute("SELECT home_team, away_team, game_date, venue FROM mlb_schedule WHERE CAST(game_pk AS TEXT) = CAST(? AS TEXT)", (game_pk,))
        row = cursor.fetchone()
        if row:
            home_team = row["home_team"] or "Unknown"
            away_team = row["away_team"] or "Unknown"
            game_date = row["game_date"] or "Unknown"
            venue = row["venue"] or "Unknown"
        else:
            cursor.execute("SELECT home_team, away_team, game_date FROM cmdb_ci_game_room WHERE CAST(game_pk AS TEXT) = CAST(? AS TEXT)", (game_pk,))
            row = cursor.fetchone()
            if row:
                home_team = row["home_team"] or "Unknown"
                away_team = row["away_team"] or "Unknown"
                game_date = row["game_date"] or "Unknown"
    except Exception as e:
        print(f"[Warning] Failed to fetch metadata: {e}")

    matchup = f"{away_team} @ {home_team}"

    # 2. Run the Unified Relational Query combining chat and play logs ordered globally by timestamp ASC
    query = """
    SELECT 
        'chat' AS log_type,
        timestamp AS timestamp,
        persona_id AS persona,
        comment_text AS text,
        inning,
        half_inning AS half,
        NULL AS event_type,
        NULL AS batter,
        NULL AS pitcher,
        NULL AS pitch_speed,
        NULL AS description
    FROM m2m_persona_room_ledger
    WHERE CAST(game_pk AS TEXT) = CAST(? AS TEXT)

    UNION ALL

    SELECT 
        'play' AS log_type,
        recorded_at AS timestamp,
        NULL AS persona,
        description AS text,
        inning,
        half,
        event_type,
        batter,
        pitcher,
        pitch_speed,
        description
    FROM game_play
    WHERE CAST(game_pk AS TEXT) = CAST(? AS TEXT)

    ORDER BY timestamp ASC;
    """

    print(f"Running unified chronological log query for Game PK {game_pk}...")
    cursor.execute(query, (game_pk, game_pk))
    rows = cursor.fetchall()
    
    total_events = len(rows)
    chat_count = sum(1 for r in rows if r["log_type"] == "chat")
    play_count = total_events - chat_count

    print(f"Found {total_events} events ({chat_count} chat, {play_count} plays).")

    # 3. Format the log into clean Markdown
    lines = [
        f"# 📋 Unified Game Room Log: {matchup}",
        f"**Date:** {game_date}  |  **Game PK:** {game_pk}  |  **Venue:** {venue}",
        f"**Exported:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## Summary",
        f"- **Total Interleaved Events:** {total_events}",
        f"- **Chat Messages (Relational Ledger):** {chat_count}",
        f"- **Plays Logged (Statcast):** {play_count}",
        "",
        "---",
        "",
        "## Chronological Log",
        "",
    ]

    for r in rows:
        ts = r["timestamp"]
        if ts:
            ts = ts[:19].replace("T", " ")
        else:
            ts = "Unknown Time"

        if r["log_type"] == "chat":
            persona = r["persona"] or "Unknown"
            text = r["text"] or ""
            # Acknowledge inning context if available
            inn = r["inning"]
            half = r["half"]
            inn_ctx = f" (Inning {inn} {half})" if inn else ""
            lines.append(f"**{ts}** 🗣️ **@{persona}**{inn_ctx}")
            lines.append(f"> {text}")
            lines.append("")
        else:
            inn = r["inning"] or "?"
            half = r["half"] or ""
            batter = r["batter"] or "Unknown"
            pitcher = r["pitcher"] or "Unknown"
            desc = r["description"] or r["text"] or ""
            speed = r["pitch_speed"]
            speed_tag = f" @ {speed} mph" if speed else ""
            lines.append(f"**{ts}** ⚾ **Inning {inn} {half}** — {batter} vs {pitcher}{speed_tag}")
            lines.append(f"*{desc}*")
            lines.append("")

    conn.close()

    print(f"Writing output to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Export completed successfully.")

if __name__ == "__main__":
    main()
