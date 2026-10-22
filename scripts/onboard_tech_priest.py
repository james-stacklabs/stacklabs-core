#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import shutil
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
BLUEPRINT_PATH = "/home/james/stacklabs/work_orders/blueprints/tech_priest.md"
AVATAR_GRID_PATH = "/home/james/sovereign_inbox/pilot_drops/tech_priest/tech_priest_avatar_map_grid_hood.jpeg"
CANONICAL_BLUEPRINT = "/home/james/stacklabs/dna/personas/tech_priest_onboarding.md"
STAGE_SYNC_PATH = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/dna/tech_priest_onboarding.md.txt"

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

    if not handle_match:
        raise ValueError("Could not parse X Handle from blueprint.")

    handle = handle_match.group(1).strip().lower()
    display_name = display_name_match.group(1).strip() if display_name_match else "Tech Priest"
    role = role_match.group(1).strip() if role_match else "Hardware-Obsessed System Optimization Ascetic"
    faction = faction_match.group(1).strip() if faction_match else "House of Metal"
    
    deep_lore = lore_match.group(1).strip() if lore_match else ""
    system_prompt_raw = prompt_match.group(1).strip() if prompt_match else ""

    # Assemble a beautiful bio
    bio = f"{role} of the {faction}. Guardian of the Machine Spirit. 'Greetings, supplicant. State your system's malady.'"
    
    return {
        "handle": handle,
        "display_name": display_name,
        "role": role,
        "faction": faction,
        "bio": bio,
        "deep_lore": deep_lore,
        "system_prompt": system_prompt_raw
    }

def process_avatars(handle, image_path):
    print(f"Processing avatar grid from: {image_path}")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Avatar grid image not found at {image_path}")

    img = Image.open(image_path)
    width, height = img.size
    cell_w = width // 3
    cell_h = height // 3

    # Define crop coordinates
    crops = {
        "avatar": (0, 0, cell_w, cell_h),                     # Row 0, Col 0
        "pointing": (0, cell_h * 2, cell_w, height),           # Row 2, Col 0
        "shrug": (cell_w, cell_h * 2, cell_w * 2, height)      # Row 2, Col 1
    }

    target_dirs = [
        f"/home/james/stacklabs/02_Sovereign_Media/public/avatars/{handle}"
    ]

    avatar_base64 = ""

    # Crop and save standard poses
    for pose, box in crops.items():
        cropped = img.crop(box)
        cropped = cropped.resize((512, 512), Image.Resampling.LANCZOS)

        # Base64 encode the main avatar
        if pose == "avatar":
            import io
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            avatar_base64 = f"data:image/png;base64,{encoded}"

        for t_dir in target_dirs:
            os.makedirs(t_dir, exist_ok=True)
            # Remove old SVGs
            stale_svg = os.path.join(t_dir, f"{handle}_{pose}.svg")
            if os.path.exists(stale_svg):
                os.remove(stale_svg)

            # Save pose image
            cropped.save(os.path.join(t_dir, f"{pose}.png"), "PNG")
            cropped.save(os.path.join(t_dir, f"{handle}_{pose}.png"), "PNG")

    print("Cropped standard poses successfully.")

    # Slice and catalog all 9 expressions
    portal_avatar_dir = f"/home/james/stacklabs/02_Sovereign_Media/public/avatars/{handle}"
    layout = {
        (0, 0): "front_neutral",
        (0, 1): "front_talking",
        (0, 2): "front_surprised",
        (1, 0): "left_neutral",
        (1, 1): "left_talking",
        (1, 2): "left_surprised",
        (2, 0): "right_neutral",
        (2, 1): "right_talking",
        (2, 2): "right_surprised"
    }

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

    for (row, col), slug in layout.items():
        left = col * cell_w
        top = row * cell_h
        right = left + cell_w
        bottom = top + cell_h

        cropped_cell = img.crop((left, top, right, bottom))
        dest_filename = f"{slug}.png"
        dest_path = os.path.join(portal_avatar_dir, dest_filename)
        cropped_cell.save(dest_path, "PNG")

        file_hash = sha256_file(dest_path)
        web_path = f"/avatars/{handle}/{dest_filename}"

        # Register in media asset
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
    print("Slicing and cataloging of all 9 expressions complete.")
    return avatar_base64

def onboard_database(data, avatar_base64):
    handle = data["handle"]
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
    email = f"sovereign.fanstack+{handle}@gmail.com"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get sys_id - Evict old UUID-based records first if they exist
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    rows = cur.fetchall()
    for r in rows:
        old_id = r[0]
        if old_id != f"persona_{handle}":
            print(f"Evicting old UUID-based records under: {old_id}")
            cur.execute("DELETE FROM persona WHERE id = ?", (old_id,))
            cur.execute("DELETE FROM sys_user WHERE sys_id = ?", (old_id,))
            cur.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (old_id,))
            cur.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (old_id,))
            cur.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (old_id,))

    sys_id = f"persona_{handle}"
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
            ) VALUES (?, ?, ?, 'GLOBAL', ?, 2, ?, '#00f2fe', 'pacer', ?, ?, ?, 'style_felt', datetime('now'))
        """, (sys_id, handle, data["display_name"], data["system_prompt"], avatar_url, data["deep_lore"], email, avatar_base64))

    # 2. sys_user Table
    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    if cur.fetchone():
        cur.execute("""
            UPDATE sys_user SET
                first_name = 'Tech',
                last_name = 'Priest',
                introduction = ?,
                department = 'GLOBAL',
                display_name = 'Tech Priest',
                avatar_url = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE user_name = ?
        """, (data["bio"], avatar_url, handle))
    else:
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, 'Tech', 'Priest', 'Advocate', ?, 'GLOBAL', 1, 'advocate', 'Tech Priest', ?)
        """, (sys_id, handle, data["bio"], avatar_url))

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
            VALUES (?, ?, 'cmdb_ci_ai_persona', 'GLOBAL', 'Sovereign tech priest advocate', 1)
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

def copy_and_stage_blueprint(data):
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

    # Also stage for NotebookLM sync in the notebook_sync root, avoiding the dna folder
    notebook_dest = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/tech_priest_onboarding.md.txt"
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
    print("🚀 Starting Tech Priest Custom Onboarding...")
    
    # 1. Parse blueprint
    data = parse_blueprint(BLUEPRINT_PATH)
    
    # 2. Slice and crop avatar
    avatar_base64 = process_avatars(data["handle"], AVATAR_GRID_PATH)
    
    # 3. Update databases
    onboard_database(data, avatar_base64)
    
    # 4. Stage blueprint files
    copy_and_stage_blueprint(data)
    
    print("\n🟢 SUCCESS: Tech Priest successfully onboarded!")
    print("Please run /home/james/stacklabs/scripts/sync_to_gdrive.sh to sync the blueprints to Google Drive.")

if __name__ == "__main__":
    main()
