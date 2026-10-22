#!/usr/bin/env python3
"""
label_and_prepare_logs.py
=========================
Processes all FanStack game logs, matches them against MLB schedule metadata
in sovereign_now.db, labels them descriptively, and copies them to the
dedicated labeled_logs staging folder.
"""

import os
import glob
import sqlite3
import shutil

LOG_DIR = "/home/james/stacklabs/data/logs"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
DEST_DIR = "/home/james/stacklabs/data/labeled_logs"

def main():
    print("📋 [START] Processing game logs for labeling...")
    
    # 1. Clean and recreate destination directory
    if os.path.exists(DEST_DIR):
        print(f"[-] Cleaning existing destination directory: {DEST_DIR}")
        shutil.rmtree(DEST_DIR)
    os.makedirs(DEST_DIR, exist_ok=True)
    
    # 2. Connect to database and retrieve schedule info
    print(f"[+] Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT game_pk, game_date, home_team, away_team FROM mlb_schedule")
    games = {str(row['game_pk']): row for row in c.fetchall()}
    
    # Retrieve game_pks with active chat messages
    c.execute("SELECT DISTINCT game_pk FROM game_chat")
    active_chat_game_pks = {str(row['game_pk']) for row in c.fetchall()}
    conn.close()
    print(f"[+] Loaded metadata for {len(games)} scheduled games.")
    print(f"[+] Found {len(active_chat_game_pks)} games with active chat messages in DB.")
    
    # 3. Find all game logs recursively
    md_files = glob.glob(os.path.join(LOG_DIR, "**", "auto_export_*.md"), recursive=True)
    md_files += glob.glob(os.path.join(LOG_DIR, "**", "game_log_*.md"), recursive=True)
    print(f"[+] Scanned {len(md_files)} markdown files in {LOG_DIR}")
    
    # 4. Filter and select the largest version of each unique game_pk
    game_files = {} # game_pk -> (filepath, size)
    
    for filepath in md_files:
        filename = os.path.basename(filepath)
        game_pk = None
        if "auto_export_" in filename:
            game_pk = filename.replace("auto_export_", "").replace(".md", "")
        elif "game_log_" in filename:
            parts = filename.split("_")
            for p in parts:
                if p.isdigit() and len(p) >= 6:
                    game_pk = p
                    break
        
        if not game_pk:
            continue
            
        size = os.path.getsize(filepath)
        if game_pk not in game_files or size > game_files[game_pk][1]:
            game_files[game_pk] = (filepath, size)
            
    print(f"[+] Identified {len(game_files)} unique game logs.")
    
    # 5. Copy and rename logs
    copied_count = 0
    skipped_count = 0
    for game_pk, (filepath, size) in game_files.items():
        # Only copy if the game room was actually deployed (had active chat messages)
        if game_pk not in active_chat_game_pks:
            skipped_count += 1
            continue
            
        game_info = games.get(game_pk)
        if game_info:
            date_str = game_info['game_date'].replace("-", "")
            dest_filename = f"game_log_{game_pk}_{date_str}_{game_info['away_team']}_at_{game_info['home_team']}.md"
        else:
            dest_filename = f"game_log_{game_pk}_unknown_date_unknown_teams.md"
            
        dest_path = os.path.join(DEST_DIR, dest_filename)
        shutil.copyfile(filepath, dest_path)
        copied_count += 1
        
    print(f"🟢 [SUCCESS] Labeled logs staging complete.")
    print(f"    - Total Copied/Labeled (Active Chat): {copied_count}")
    print(f"    - Skipped (No active chat or empty): {skipped_count}")
    print(f"    - Output Folder: {DEST_DIR}")

if __name__ == "__main__":
    main()
