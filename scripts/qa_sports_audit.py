import os
import sys
import json
import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PUBLIC_DIR = "/home/james/stacklabs/15_FanStack/public"

COMMENTATORS = {
    "NFL (MetLife Slate - Room 826001)": [
        "metlife_meltdown",
        "gridiron_gary",
        "star_delusion",
        "tundra_tim"
    ],
    "UFL (BattleDome - Room 826100)": [
        "spring_league_stalwart",
        "chip_telemetry_tom",
        "stadium_phantom_stl"
    ]
}

ROOM_MAPPINGS = {
    "826001": "NFL (MetLife Slate)",
    "826100": "UFL (BattleDome)"
}

def run_sports_qa_audit():
    print("🕵️‍♂️ Starting Sovereign Sports Stack QA Audit...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    failures = []
    passes = []
    
    # 1. Audit Room Configurations & Schemas
    print("\n📁 Phase 1: Auditing CMDB & Schedule Room States...")
    for room_key, league in ROOM_MAPPINGS.items():
        # Check mlb_schedule
        sched = cursor.execute(
            "SELECT status, room_state FROM mlb_schedule WHERE game_pk = ?", (room_key,)
        ).fetchone()
        
        if not sched:
            failures.append(f"Room {room_key} ({league}) is missing from mlb_schedule.")
        elif sched["room_state"] != "active":
            failures.append(f"Room {room_key} ({league}) has room_state = '{sched['room_state']}' in mlb_schedule (expected 'active').")
        else:
            passes.append(f"Room {room_key} is active in mlb_schedule.")
            
        # Check cmdb_ci_fanstack_room
        cmdb_rooms = cursor.execute(
            "SELECT sys_id, name, room_state FROM cmdb_ci_fanstack_room WHERE room_key = ?", (room_key,)
        ).fetchall()
        
        if not cmdb_rooms:
            failures.append(f"Room {room_key} ({league}) is missing from cmdb_ci_fanstack_room.")
        else:
            for r in cmdb_rooms:
                if r["room_state"] != "active":
                    failures.append(f"Room {room_key} ({league}) in CMDB has room_state = '{r['room_state']}' (expected 'active').")
                else:
                    passes.append(f"Room {room_key} ({r['name']}) is active in cmdb_ci_fanstack_room.")

    # 2. Audit Persona & Sys User Seeds
    print("\n👥 Phase 2: Auditing Persona & Sys User Roster Seeds...")
    all_commentators = []
    for league, comms in COMMENTATORS.items():
        all_commentators.extend(comms)
        
    for username in all_commentators:
        # Check persona table
        p = cursor.execute(
            "SELECT * FROM persona WHERE user_name = ?", (username,)
        ).fetchone()
        
        if not p:
            failures.append(f"Persona @{username} is missing from persona table.")
            continue
            
        # Anti-Laziness Mandate: System Prompt Length check
        sys_prompt = p["system_prompt"]
        if not sys_prompt or len(sys_prompt) < 1000:
            failures.append(f"Persona @{username} has truncated/empty system_prompt (length: {len(sys_prompt) if sys_prompt else 0} chars, expected >= 1000).")
        else:
            passes.append(f"Persona @{username} system prompt length: {len(sys_prompt)} chars (PASSED).")
            
        # Check avatar_url and avatar_blob integrity
        avatar_url = p["avatar_url"]
        avatar_blob = p["avatar_blob"]
        
        if not avatar_url:
            failures.append(f"Persona @{username} has null/empty avatar_url.")
        elif avatar_url.endswith(".svg"):
            failures.append(f"Persona @{username} has legacy SVG avatar_url: '{avatar_url}' (expected PNG).")
        else:
            passes.append(f"Persona @{username} has correct PNG avatar_url: '{avatar_url}'.")
            
        if not avatar_blob:
            failures.append(f"Persona @{username} has null/empty avatar_blob.")
        elif not avatar_blob.startswith("data:image/png;base64,"):
            failures.append(f"Persona @{username} has invalid base64 avatar_blob header (expected PNG data URL).")
        else:
            passes.append(f"Persona @{username} has populated base64 avatar_blob ({len(avatar_blob)} bytes).")
            
        # Check sys_user table alignment
        su = cursor.execute(
            "SELECT * FROM sys_user WHERE user_name = ?", (username,)
        ).fetchone()
        
        if not su:
            failures.append(f"User @{username} is missing from sys_user table.")
        else:
            if su["avatar_url"] != avatar_url:
                failures.append(f"User @{username} avatar_url in sys_user ('{su['avatar_url']}') does not match persona table ('{avatar_url}').")
            else:
                passes.append(f"User @{username} avatar_url is perfectly aligned in sys_user.")

    # 3. Audit Seating Assignments
    print("\n🪑 Phase 3: Auditing Game Seating & M2M Seating Assignments...")
    for room_key, league in ROOM_MAPPINGS.items():
        expected_comms = COMMENTATORS["NFL (MetLife Slate - Room 826001)"] if room_key == "826001" else COMMENTATORS["UFL (BattleDome - Room 826100)"]
        
        for username in expected_comms:
            # Query persona ID
            p = cursor.execute("SELECT id FROM persona WHERE user_name = ?", (username,)).fetchone()
            if not p:
                continue
            persona_id = p["id"]
            
            # Check game_persona table
            gp = cursor.execute(
                "SELECT seat_state FROM game_persona WHERE game_pk = ? AND persona_id = ?", (room_key, persona_id)
            ).fetchone()
            
            if not gp:
                failures.append(f"Persona @{username} is not seated in game_persona for Room {room_key}.")
            elif gp["seat_state"] != "active":
                failures.append(f"Persona @{username} has seat_state = '{gp['seat_state']}' in game_persona for Room {room_key} (expected 'active').")
            else:
                passes.append(f"Persona @{username} is seated and active in game_persona for Room {room_key}.")
                
            # Check m2m_persona_room table
            m2m = cursor.execute(
                "SELECT sys_id FROM m2m_persona_room WHERE room = ? AND persona = ?", (room_key, persona_id)
            ).fetchone()
            
            if not m2m:
                failures.append(f"Persona @{username} is missing from m2m_persona_room for Room {room_key}.")
            else:
                passes.append(f"Persona @{username} is linked correctly in m2m_persona_room for Room {room_key}.")

    # 4. Audit Physical Disk Files (Moat check)
    print("\n💾 Phase 4: Auditing Premium PNG Asset Moats on Disk...")
    for username in all_commentators:
        p = cursor.execute("SELECT avatar_url FROM persona WHERE user_name = ?", (username,)).fetchone()
        if not p or not p["avatar_url"]:
            continue
            
        clean_path = p["avatar_url"].lstrip("/")
        full_disk_path = os.path.join(PUBLIC_DIR, clean_path)
        
        if not os.path.exists(full_disk_path):
            failures.append(f"Physical PNG avatar asset is missing on disk at: {full_disk_path}")
        else:
            size_kb = os.path.getsize(full_disk_path) / 1024.0
            passes.append(f"Physical asset exists: {clean_path} ({size_kb:.1f} KB).")

    conn.close()
    
    print("\n🏁 ==================== AUDIT SUMMARY ====================")
    if failures:
        print(f"❌ AUDIT FAILED with {len(failures)} Compliance Errors:")
        for err in failures:
            print(f"  - {err}")
        return {"status": "FAIL", "errors": failures, "passed_checks": len(passes)}
    else:
        print(f"✅ AUDIT PASSED successfully! All {len(passes)} compliance checks verified.")
        return {"status": "PASS", "errors": [], "passed_checks": len(passes)}

if __name__ == "__main__":
    result = run_sports_qa_audit()
    sys.exit(0 if result["status"] == "PASS" else 1)
