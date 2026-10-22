#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import shutil

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
BLUEPRINT_PATH = "/home/james/stacklabs/work_orders/blueprints/command_pilot_jc.md"
CANONICAL_BLUEPRINT = "/home/james/stacklabs/dna/personas/pilot_james_onboarding.md"
STAGE_SYNC_PATH = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/pilot_james_onboarding.md.txt"

def parse_blueprint(filepath):
    print(f"Reading blueprint: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse details
    handle_match = re.search(r"\*\*X Handle:\*\*\s*`@?(\w+)`", content)
    display_name_match = re.search(r"\*\*Display Name:\*\*\s*(.+)", content)
    role_match = re.search(r"\*\*Role:\*\*\s*(.+)", content)
    faction_match = re.search(r"\*\*Faction Alignment:\*\*\s*(.+)", content)
    
    # Extract deep lore
    lore_match = re.search(r"## 📖 Deep Lore\n(.*?)(?=\n#|\n##|$)", content, re.DOTALL)
    
    # Extract system prompt
    prompt_match = re.search(r"## 🧠 System Prompt\n(.*?)(?=\n#|\n##|$)", content, re.DOTALL)

    display_name = display_name_match.group(1).strip() if display_name_match else "James Carroll"
    role = role_match.group(1).strip() if role_match else "Sovereign OS Command Pilot, Lead Systems Architect"
    faction = faction_match.group(1).strip() if faction_match else "House of Metal"
    
    deep_lore = lore_match.group(1).strip() if lore_match else ""
    system_prompt_raw = prompt_match.group(1).strip() if prompt_match else ""

    # Assemble bio
    bio = f"{role} of the {faction}. 'System diagnostics initiated. Report operational parameters and current loop status.'"
    
    return {
        "handle": "pilot_james",  # Keep the canonical handle from database
        "display_name": display_name,
        "role": role,
        "faction": faction,
        "bio": bio,
        "deep_lore": deep_lore,
        "system_prompt": system_prompt_raw
    }

def process_avatars(handle):
    print("Processing generated avatars...")
    source_dir = "/home/james/stacklabs/15_FanStack/public/avatars/command"
    avatar_src = os.path.join(source_dir, "command_avatar.png")
    pointing_src = os.path.join(source_dir, "command_pointing.png")

    if not os.path.exists(avatar_src):
        raise FileNotFoundError(f"Source avatar not found at {avatar_src}")

    # Read base64
    with open(avatar_src, "rb") as img_f:
        encoded = base64.b64encode(img_f.read()).decode("utf-8")
        avatar_base64 = f"data:image/png;base64,{encoded}"

    target_dirs = [
        f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{handle}",
        f"/home/james/stacklabs/02_Sovereign_Media/public/avatars/{handle}",
        f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}"
    ]

    for t_dir in target_dirs:
        os.makedirs(t_dir, exist_ok=True)
        # Copy standard files
        shutil.copy(avatar_src, os.path.join(t_dir, f"{handle}_avatar.png"))
        shutil.copy(avatar_src, os.path.join(t_dir, "avatar.png"))
        
        if os.path.exists(pointing_src):
            shutil.copy(pointing_src, os.path.join(t_dir, f"{handle}_pointing.png"))
            shutil.copy(pointing_src, os.path.join(t_dir, "pointing.png"))
        else:
            shutil.copy(avatar_src, os.path.join(t_dir, f"{handle}_pointing.png"))
            shutil.copy(avatar_src, os.path.join(t_dir, "pointing.png"))

        # Fallback shrug pose (using avatar since quota hit)
        shutil.copy(avatar_src, os.path.join(t_dir, f"{handle}_shrug.png"))
        shutil.copy(avatar_src, os.path.join(t_dir, "shrug.png"))

        # Generate 9 layout expressions (use avatar as fallback for all expressions)
        layout_slugs = [
            "front_neutral", "front_talking", "front_surprised",
            "left_neutral", "left_talking", "left_surprised",
            "right_neutral", "right_talking", "right_surprised"
        ]
        for slug in layout_slugs:
            shutil.copy(avatar_src, os.path.join(t_dir, f"{slug}.png"))

    # Register expressions in media asset table
    import hashlib
    def sha256_file(path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for slug in layout_slugs:
        dest_filename = f"{slug}.png"
        dest_path = f"/home/james/stacklabs/02_Sovereign_Media/public/avatars/{handle}/{dest_filename}"
        file_hash = sha256_file(dest_path)
        web_path = f"/avatars/{handle}/{dest_filename}"

        cursor.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (handle, slug))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE cmdb_ci_media_asset
                SET file_path = ?, sha256 = ?, sys_created_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (web_path, file_hash, existing[0]))
        else:
            sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
                VALUES (?, ?, ?, ?, ?)
            """, (sys_id, handle, slug, web_path, file_hash))

    conn.commit()
    conn.close()

    print("Cropped and registered standard poses successfully.")
    return avatar_base64

def onboard_database(data, avatar_base64):
    handle = data["handle"]
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    email = "sovereign.fanstack+pilot_james@gmail.com"
    sys_id = "persona_james_carroll"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print(f"Targeting canonical sys_id: {sys_id}")

    # 1. persona Table
    cur.execute("SELECT id FROM persona WHERE id = ?", (sys_id,))
    if cur.fetchone():
        print(f"Updating existing persona record (sys_id: {sys_id})")
        cur.execute("""
            UPDATE persona SET
                display_name = ?,
                team = 'GLOBAL',
                system_prompt = ?,
                avatar_url = ?,
                color = '#00f2fe',
                deep_lore = ?,
                email_alias = ?,
                avatar_blob = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (data["display_name"], data["system_prompt"], avatar_url, data["deep_lore"], email, avatar_base64, sys_id))
    else:
        print(f"Inserting new persona record (sys_id: {sys_id})")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore, email_alias, avatar_blob,
                u_visual_style, created_at
            ) VALUES (?, ?, ?, 'GLOBAL', ?, 2, ?, '#00f2fe', 'pacer', ?, ?, ?, 'style_vector', datetime('now'))
        """, (sys_id, handle, data["display_name"], data["system_prompt"], avatar_url, data["deep_lore"], email, avatar_base64))

    # 2. sys_user Table (Advocate profile)
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    if cur.fetchone():
        cur.execute("""
            UPDATE sys_user SET
                first_name = 'James',
                last_name = 'Carroll',
                introduction = ?,
                department = 'GLOBAL',
                display_name = ?,
                avatar_url = ?,
                active = 1,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE user_name = ?
        """, (data["bio"], data["display_name"], avatar_url, handle))
    else:
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, 'James', 'Carroll', 'Advocate', ?, 'GLOBAL', 1, 'advocate', ?, ?)
        """, (sys_id, handle, data["bio"], data["display_name"], avatar_url))

    # 3. cmdb_ci Table
    cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE cmdb_ci SET
                name = ?,
                assigned_to = 'GLOBAL',
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (handle, sys_id))
    else:
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', 'GLOBAL', 'Sovereign command pilot advocate', 1)
        """, (sys_id, handle))

    # 4. cmdb_ci_ai_persona Table
    cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?,
                u_deep_lore = ?
            WHERE sys_id = ?
        """, (data["system_prompt"], data["deep_lore"], sys_id))
    else:
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'medium', ?, 'global', 'pacer', ?)
        """, (sys_id, data["system_prompt"], data["deep_lore"]))

    # 5. cmdb_ci_persona Table
    cur.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE cmdb_ci_persona SET
                display_name = ?,
                handle = ?,
                team = 'global',
                role = ?,
                system_instruction = ?,
                active = 1
            WHERE sys_id = ?
        """, (data["display_name"], f"@{handle}", data["role"], data["system_prompt"], sys_id))
    else:
        cur.execute("""
            INSERT INTO cmdb_ci_persona (sys_id, id, display_name, handle, team, role, system_instruction, active)
            VALUES (?, ?, ?, ?, 'global', ?, ?, 1)
        """, (sys_id, handle, data["display_name"], f"@{handle}", data["role"], data["system_prompt"]))

    conn.commit()
    conn.close()
    print("Database transaction committed successfully.")

def copy_and_stage_blueprint():
    # Copy to canonical personas folder
    os.makedirs(os.path.dirname(CANONICAL_BLUEPRINT), exist_ok=True)
    shutil.copy(BLUEPRINT_PATH, CANONICAL_BLUEPRINT)
    print(f"Blueprint copied to: {CANONICAL_BLUEPRINT}")

    # Sync directly to Google Drive 'work_orders > spark > documentation'
    print("📡 Uploading blueprint directly to Google Drive work_orders/spark/documentation...")
    import subprocess
    gdrive_dest = "sovereign_os:SovereignOS_Clio_Sync/work_orders/spark/documentation/"
    cmd = ["rclone", "copy", BLUEPRINT_PATH, gdrive_dest]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Blueprint successfully synced to Google Drive at {gdrive_dest}")
    except Exception as e:
        print(f"⚠️ Failed to sync blueprint directly to Google Drive: {e}")

    # Also stage for NotebookLM sync in the notebook_sync root
    notebook_dest = STAGE_SYNC_PATH
    os.makedirs(os.path.dirname(notebook_dest), exist_ok=True)
    with open(BLUEPRINT_PATH, "r", encoding="utf-8") as src_f:
        blueprint_content = src_f.read()

    import datetime
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(notebook_dest, "w", encoding="utf-8") as dest_f:
        dest_f.write(f"**LAST SYNC TIME:** {timestamp} UTC\n\n")
        dest_f.write(blueprint_content)
    print(f"Blueprint staged for NotebookLM indexing: {notebook_dest}")

def main():
    print("🚀 Starting Pilot James Advocate Custom Onboarding...")
    
    # 1. Parse blueprint
    data = parse_blueprint(BLUEPRINT_PATH)
    
    # 2. Slice and crop avatar
    avatar_base64 = process_avatars(data["handle"])
    
    # 3. Update databases
    onboard_database(data, avatar_base64)
    
    # 4. Stage blueprint files
    copy_and_stage_blueprint()
    
    print("\n🟢 SUCCESS: Pilot James Advocate successfully onboarded!")

if __name__ == "__main__":
    main()
