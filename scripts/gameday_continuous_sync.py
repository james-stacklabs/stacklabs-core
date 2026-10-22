#!/usr/bin/env python3
import os
import sys
import time
import sqlite3
import subprocess
import argparse
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TELEMETRY_LOG = "/home/james/sovereign_inbox/today/statcast_telemetry.log"

SYNC_DIRS = [
    "/home/james/sovereign_inbox/notebook_sync/SovereignOS",
    "/home/james/sovereign_inbox/notebook_sync/SovereignOS_Internal",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal",
    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Syndicate"
]

ROOM_TO_STACK_MAP = {
    "weedstack": "fanstack",
    "stacklabs": "stacklabs",
    "catnip": "catnipwars",
    "gonzas": "gonzas",
    "spiteslice": "spite_slice",
    "eileen": "eileen_stack",
    "wild_paws": "wild_paws",
    "samtracker": "samtracker",
    "aethervet": "aethervet"
}

RCLONE_TARGETS = [
    ("/home/james/sovereign_inbox/notebook_sync/SovereignOS/", "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/SovereignOS/"),
    ("/home/james/sovereign_inbox/notebook_sync/SovereignOS_Internal/", "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/SovereignOS_Internal/"),
    ("/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/", "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Internal/"),
    ("/home/james/sovereign_inbox/notebook_sync/StackLabs_Syndicate/", "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Syndicate/")
]

def run_sync(no_rclone=False):
    print("=== Gameday Live Feed Sync: Starting Compilation ===")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if gameday sync is enabled globally
        cursor.execute("SELECT value FROM sys_properties WHERE name = 'system.gameday_sync.enabled'")
        prop_row = cursor.fetchone()
        sync_enabled = prop_row['value'].strip().lower() == 'true' if prop_row else True

        if not sync_enabled:
            print("=== Gameday Live Feed Sync is DISABLED via sys_properties ===")
            # Clean any existing managed livefeed files and raw log files to prevent stale sync files
            for d in SYNC_DIRS:
                if os.path.exists(d):
                    for f in os.listdir(d):
                        if (f.startswith("livefeed_") and (f.endswith(".md") or f.endswith(".md.txt"))) or f == "statcast_telemetry.log.txt":
                            try:
                                os.remove(os.path.join(d, f))
                                print(f"Cleaned up disabled sync file: {f} in {d}")
                            except Exception as e:
                                print(f"Warning: Could not remove old file {f} in {d}: {e}")
            # Mirror the cleaned staging directories to Google Drive via rclone to propagate deletion
            if not no_rclone:
                print("Syncing cleanup to Google Drive remotes...")
                filter_file = "/home/james/stacklabs/dna/sync/notebooklm_sync_filter.txt"
                for local_dir, remote_path in RCLONE_TARGETS:
                    if os.path.exists(local_dir):
                        if "StackLabs_Internal" in remote_path and os.path.exists(filter_file):
                            cmd = ["rclone", "sync", local_dir, remote_path, "--filter-from", filter_file, "--delete-excluded", "--quiet"]
                        else:
                            cmd = ["rclone", "sync", local_dir, remote_path, "--delete-after", "--quiet"]
                        subprocess.run(cmd, check=True)
                print("🟢 Google Drive sync cleanup completed.")
            print("=== Gameday Live Feed Sync: Completed cleanup and bypassed ===")
            return

        # Fetch active modules from sys_module to filter rooms from inactive stacks
        cursor.execute("SELECT module_name FROM sys_module WHERE active = 1")
        active_modules = {row['module_name'] for row in cursor.fetchall()}


        # 1. Fetch active rooms from registry
        cursor.execute("SELECT room_key, game_pk, name FROM cmdb_ci_fanstack_room WHERE room_state IN ('active', 'live')")
        raw_rooms = [dict(r) for r in cursor.fetchall()]

        active_rooms = []
        for r in raw_rooms:
            room_key = r['room_key'] or ''
            lower_key = room_key.lower()
            room_stack = None
            for key_sub, module_name in ROOM_TO_STACK_MAP.items():
                if key_sub in lower_key:
                    room_stack = module_name
                    break
            if room_stack and room_stack not in active_modules:
                print(f"Skipping sync for room {room_key} as its stack {room_stack} is inactive.")
                continue
            active_rooms.append(r)
        
        # Build active keys set to avoid duplicates
        active_keys = set()
        for r in active_rooms:
            if r['game_pk']:
                active_keys.add(str(r['game_pk']))
            if r['room_key']:
                active_keys.add(str(r['room_key']))
                
        # Dynamically discover other active streams (chats in last 2 hours or global system streams)
        cursor.execute("""
            SELECT DISTINCT game_pk FROM game_chat 
            WHERE created_at >= datetime('now', '-2 hours') 
               OR game_pk IN ('global', 'GLOBAL', 'live_chat_sniper', 'the_skew')
        """)
        additional_pks = [str(row['game_pk']) for row in cursor.fetchall() if row['game_pk']]
        
        for apk in additional_pks:
            if apk not in active_keys:
                active_rooms.append({
                    'room_key': apk,
                    'game_pk': apk if apk.isdigit() else None,
                    'name': apk if not apk.isdigit() else f"Game Room {apk}"
                })
                active_keys.add(apk)
                
        print(f"Found {len(active_rooms)} active room(s) / dynamic stream(s) to process.")
        
        # 2. Ensure target directories exist
        for d in SYNC_DIRS:
            os.makedirs(d, exist_ok=True)
            
        # 3. Clean any existing managed livefeed files to prevent stale sync files
        for d in SYNC_DIRS:
            for f in os.listdir(d):
                if f.startswith("livefeed_") and (f.endswith(".md") or f.endswith(".md.txt")):
                    try:
                        os.remove(os.path.join(d, f))
                    except Exception as e:
                        print(f"Warning: Could not remove old file {f} in {d}: {e}")
                        
        # 4. Generate markdown feed for each active room
        for room in active_rooms:
            room_key = room['room_key'] or 'unknown_room'
            game_pk = room['game_pk']
            room_name = room['name'] or 'Active Game Room'
            
            print(f"Compiling live feed for {room_name} ({room_key})")
            
            # Retrieve game metadata from schedule if game_pk is populated
            game_metadata = {"away_team": "?", "home_team": "?", "game_date": "Unknown", "venue": ""}
            if game_pk:
                cursor.execute("SELECT away_team, home_team, game_date, venue FROM mlb_schedule WHERE game_pk = ?", (game_pk,))
                sched_row = cursor.fetchone()
                if sched_row:
                    game_metadata = dict(sched_row)
                    
            matchup = f"{game_metadata['away_team']} @ {game_metadata['home_team']}" if game_pk else room_name
            game_date = game_metadata['game_date']
            venue = game_metadata['venue']
            
            # Fetch chats (if game_pk is blank, check room_key)
            chats = []
            query_key = game_pk if game_pk else room_key
            if query_key:
                cursor.execute("""
                    SELECT 'chat' AS log_type, created_at AS ts, persona, text, model, msg_type,
                           NULL AS inning, NULL AS half, NULL AS event_type,
                           NULL AS batter, NULL AS pitcher, NULL AS pitch_speed, NULL AS description
                    FROM game_chat WHERE game_pk = ?
                    ORDER BY id ASC
                """, (query_key,))
                chats = [dict(r) for r in cursor.fetchall()]
                
            # Fetch plays (if game_pk is populated)
            plays = []
            if game_pk:
                cursor.execute("""
                    SELECT 'play' AS log_type, recorded_at AS ts, NULL AS persona, description AS text,
                           NULL AS model, NULL AS msg_type,
                           inning, half, event_type, batter, pitcher, pitch_speed, description
                    FROM game_play WHERE game_pk = ?
                    ORDER BY id ASC
                """, (game_pk,))
                plays = [dict(r) for r in cursor.fetchall()]
                
            # Merge and sort chronologically
            all_events = chats + plays
            all_events.sort(key=lambda e: e.get("ts") or "")
            
            # Format Markdown
            md_lines = [
                f"# 📋 Live Discourse Stream: {matchup}",
                f"**Date:** {game_date}  |  **Room Key:** {room_key}  |  **Venue:** {venue if venue else 'N/A'}",
                f"**Last Sync Update:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "",
                "---",
                "",
                f"## Summary",
                f"- **Total Events Logged:** {len(all_events)}",
                f"- **Chat Messages:** {len(chats)}",
                f"- **Plays Logged:** {len(plays)}",
                "",
                "---",
                "",
                "## Chronological Log",
                ""
            ]
            
            for e in all_events:
                ts = (e.get("ts") or "")[:19].replace("T", " ")
                if e["log_type"] == "chat":
                    persona = e.get("persona") or "?"
                    model = e.get("model") or ""
                    text = e.get("text") or ""
                    model_tag = f" `[{model}]`" if model else ""
                    md_lines.append(f"**{ts}** 🗣️ **{persona}**{model_tag}")
                    md_lines.append(f"> {text}")
                    md_lines.append("")
                else:
                    inning = e.get("inning") or "?"
                    half = e.get("half") or ""
                    batter = e.get("batter") or ""
                    pitcher = e.get("pitcher") or ""
                    desc = e.get("description") or ""
                    speed = e.get("pitch_speed") or ""
                    speed_tag = f" @ {speed} mph" if speed else ""
                    md_lines.append(f"**{ts}** ⚾ **Inning {inning} {half}** — {batter} vs {pitcher}{speed_tag}")
                    md_lines.append(f"*{desc}*")
                    md_lines.append("")
                    
            md_content = "\n".join(md_lines)
            
            # Route target folders based on room_key:
            target_dirs = []
            lower_key = room_key.lower()
            if "weedstack" in lower_key:
                target_dirs = [
                    "/home/james/sovereign_inbox/notebook_sync/SovereignOS",
                    "/home/james/sovereign_inbox/notebook_sync/SovereignOS_Internal"
                ]
            elif "stacklabs" in lower_key:
                target_dirs = [
                    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal",
                    "/home/james/sovereign_inbox/notebook_sync/StackLabs_Syndicate"
                ]
            else:
                target_dirs = SYNC_DIRS
            # Clean matchup/name to make it filename-safe
            safe_matchup = matchup.replace(" @ ", "_at_").replace(" ", "_").replace("/", "_").replace("@", "_at_").lower()
            # Remove any trailing/leading underscores or double underscores
            import re
            safe_matchup = re.sub(r'_+', '_', safe_matchup).strip('_')
            filename = f"livefeed_{room_key}_{safe_matchup}.md"
            for d in target_dirs:
                file_path = os.path.join(d, filename)
                tmp_path = file_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                os.replace(tmp_path, file_path)
            print(f"Staged {filename} to target directories: {', '.join([os.path.basename(d) for d in target_dirs])}")
            
        # 5. Copy the raw statcast_telemetry.log if it exists
        if os.path.exists(TELEMETRY_LOG):
            print("Staging raw statcast telemetry log...")
            import shutil
            for d in SYNC_DIRS:
                dest_path = os.path.join(d, "statcast_telemetry.log.txt")
                tmp_dest = dest_path + ".tmp"
                shutil.copy2(TELEMETRY_LOG, tmp_dest)
                os.replace(tmp_dest, dest_path)
        else:
            print("No active statcast_telemetry.log found to stage.")
            
        # 6. Mirror staging directories to Google Drive via rclone (unless --no-rclone is specified)
        if not no_rclone:
            print("Syncing files to Google Drive remotes...")
            filter_file = "/home/james/stacklabs/dna/sync/notebooklm_sync_filter.txt"
            for local_dir, remote_path in RCLONE_TARGETS:
                if os.path.exists(local_dir):
                    if "StackLabs_Internal" in remote_path and os.path.exists(filter_file):
                        cmd = ["rclone", "sync", local_dir, remote_path, "--filter-from", filter_file, "--delete-excluded", "--quiet"]
                    else:
                        cmd = ["rclone", "sync", local_dir, remote_path, "--delete-after", "--quiet"]
                    subprocess.run(cmd, check=True)
            print("🟢 Google Drive sync pass completed.")
        else:
            print("Skipping rclone pass (--no-rclone active).")
            
        print("=== Gameday Live Feed Sync: Completed successfully ===")
        
    except Exception as e:
        print(f"❌ Exception in Gameday Sync Compile: {e}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Continuous Gameday Live Feed Sync")
    parser.add_argument("--one-shot", action="store_true", help="Compile and sync once, then exit")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely in a 60-second loop")
    parser.add_argument("--no-rclone", action="store_true", help="Skip the rclone sync execution")
    
    args = parser.parse_args()
    
    if args.daemon:
        print("Starting gameday sync daemon (60-second polling)...")
        try:
            while True:
                run_sync(no_rclone=args.no_rclone)
                sys.stdout.flush()
                time.sleep(60)
        except KeyboardInterrupt:
            print("Daemon stopped by keyboard interrupt.")
    else:
        # Default is --one-shot if nothing else specified
        run_sync(no_rclone=args.no_rclone)

if __name__ == "__main__":
    main()
