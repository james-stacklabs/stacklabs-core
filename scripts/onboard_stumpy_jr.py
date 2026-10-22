#!/usr/bin/env python3
import os
import re
import sys
import sqlite3
import uuid
import base64
import shutil
import json
import hashlib
from datetime import datetime
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Inputs
METSY_RAW_SRC = "/home/james/stacklabs/work_orders/spark/media/metsy_asleep_garland.jpg"
METSY_STYLIZED_SRC = "/home/james/.gemini/antigravity/brain/ea75092e-6f98-4fb3-8520-ac88c2c6f5c4/metsy_asleep_garland_1781241104897.png"

STUMPY_RAW_SRC = "/home/james/stacklabs/work_orders/spark/media/stumpy_jr.jpg"
STUMPY_GRID_SRC = "/home/james/.gemini/antigravity/brain/ea75092e-6f98-4fb3-8520-ac88c2c6f5c4/stumpy_jr_avatar_sheet_1781241124612.png"

# Outputs for Metsy
METSY_RAW_DST = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Original/metsy_asleep_garland.jpg"
METSY_STYLIZED_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_asleep_garland.png"
METSY_RECEIPT_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_asleep_garland_receipt.json"

METSY_AVATAR_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/02_Sovereign_Media/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/15_FanStack/public/avatars/metsy_smyrna"
]

# Outputs for Stumpy Jr
STUMPY_RAW_DST = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Original/stumpy_jr.jpg"
STUMPY_GRID_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_stumpy_jr_sheet.png"
STUMPY_RECEIPT_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_stumpy_jr_sheet_receipt.json"

STUMPY_AVATAR_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/stumpy_jr",
    "/home/james/stacklabs/02_Sovereign_Media/public/avatars/stumpy_jr",
    "/home/james/stacklabs/15_FanStack/public/avatars/stumpy_jr"
]

BLUEPRINT_PATH = "/home/james/stacklabs/work_orders/blueprints/stumpy_jr.md"
CANONICAL_BLUEPRINT = "/home/james/stacklabs/dna/personas/stumpy_jr_onboarding.md"

TICKET_ID = "STRY1789205"

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def generate_next_asset_tag(cursor):
    cursor.execute("SELECT asset_tag FROM sys_media_asset")
    rows = cursor.fetchall()
    max_num = 0
    for row in rows:
        tag = row[0]
        match = re.search(r'FS-MED-(\d+)', tag)
        if match:
            num = int(match.group(1))
            if num < 99999: # Ignore test tags
                if num > max_num:
                    max_num = num
    next_num = max_num + 1
    return f"FS-MED-{next_num:05d}"

def process_metsy(cursor):
    print("\n--- Processing Metsy Asleep Garland Asset ---")
    if not os.path.exists(METSY_RAW_SRC):
        print(f"[-] ERROR: Raw source file not found at: {METSY_RAW_SRC}")
        sys.exit(1)
    if not os.path.exists(METSY_STYLIZED_SRC):
        print(f"[-] ERROR: Stylized source file not found at: {METSY_STYLIZED_SRC}")
        sys.exit(1)

    # Copy and register Raw
    os.makedirs(os.path.dirname(METSY_RAW_DST), exist_ok=True)
    shutil.copy2(METSY_RAW_SRC, METSY_RAW_DST)
    raw_size = os.path.getsize(METSY_RAW_DST)
    raw_md5 = get_md5(METSY_RAW_DST)
    with open(METSY_RAW_DST, "rb") as f:
        raw_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    raw_tag = generate_next_asset_tag(cursor)
    raw_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Metsy Asleep in Garland (Original)', 'metsy_asleep_garland.jpg', ?, ?, 'image/jpeg', 'Metsy Raw Photos', 'Active', ?, ?)
    """, (raw_sys_id, raw_tag, METSY_RAW_DST, raw_size, raw_md5, raw_b64))
    print(f"[+] Registered Metsy Raw Photo: {raw_tag} -> {METSY_RAW_DST}")

    # Copy and register Stylized
    os.makedirs(os.path.dirname(METSY_STYLIZED_DST), exist_ok=True)
    shutil.copy2(METSY_STYLIZED_SRC, METSY_STYLIZED_DST)
    stylized_size = os.path.getsize(METSY_STYLIZED_DST)
    stylized_md5 = get_md5(METSY_STYLIZED_DST)
    stylized_sha = get_sha256(METSY_STYLIZED_DST)
    with open(METSY_STYLIZED_DST, "rb") as f:
        stylized_b64 = base64.b64encode(f.read()).decode("utf-8")

    stylized_tag = generate_next_asset_tag(cursor)
    stylized_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Metsy Adventure 12: Asleep Garland', '[PROCESSED]_asleep_garland.png', ?, ?, 'image/png', 'Metsy Adventures', 'Active', ?, ?)
    """, (stylized_sys_id, stylized_tag, METSY_STYLIZED_DST, stylized_size, stylized_md5, stylized_b64))
    print(f"[+] Registered Metsy Stylized PNG: {stylized_tag} -> {METSY_STYLIZED_DST}")

    # Expression mapping
    expr_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
        VALUES (?, 'metsy', 'asleep_garland', ?, ?)
    """, (expr_sys_id, METSY_STYLIZED_DST, stylized_sha))
    print(f"[+] Registered Metsy in cmdb_ci_media_asset: expression=asleep_garland")

    # Copy to frontends
    for target_dir in METSY_AVATAR_DIRS:
        os.makedirs(target_dir, exist_ok=True)
        dest_file = os.path.join(target_dir, "metsy_asleep_garland.png")
        shutil.copy2(METSY_STYLIZED_DST, dest_file)
        print(f"  -> Co-located: {dest_file}")

    # Receipt
    receipt_data = {
        "ticket_id": TICKET_ID,
        "pipeline_id": "sovereign_event_media_v1",
        "scenario_number": 12,
        "scenario_name": "Metsy Asleep Garland",
        "expression_reference": "ACTION: ASLEEP / SNUGGLING IN COZY HOLIDAY PINE GARLAND",
        "style_anchor": "metsy_collar.png",
        "vibe": "Gritty neon-grime cartoon action.",
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_file": "[PROCESSED]_asleep_garland.png",
        "md5_hash": stylized_md5,
        "sha256_hash": stylized_sha
    }
    with open(METSY_RECEIPT_DST, 'w') as rf:
        json.dump(receipt_data, rf, indent=2)
    print(f"[+] Created Metsy receipt at {METSY_RECEIPT_DST}")

def process_stumpy_jr(cursor):
    print("\n--- Processing Stumpy Jr. Onboarding ---")
    if not os.path.exists(STUMPY_RAW_SRC):
        print(f"[-] ERROR: Raw source file not found at: {STUMPY_RAW_SRC}")
        sys.exit(1)
    if not os.path.exists(STUMPY_GRID_SRC):
        print(f"[-] ERROR: Grid source file not found at: {STUMPY_GRID_SRC}")
        sys.exit(1)

    # Save original photo
    os.makedirs(os.path.dirname(STUMPY_RAW_DST), exist_ok=True)
    shutil.copy2(STUMPY_RAW_SRC, STUMPY_RAW_DST)
    raw_size = os.path.getsize(STUMPY_RAW_DST)
    raw_md5 = get_md5(STUMPY_RAW_DST)
    with open(STUMPY_RAW_DST, "rb") as f:
        raw_b64 = base64.b64encode(f.read()).decode("utf-8")

    raw_tag = generate_next_asset_tag(cursor)
    raw_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Stumpy Jr. Raw Photo', 'stumpy_jr.jpg', ?, ?, 'image/jpeg', 'Catnip Wars', 'Active', ?, ?)
    """, (raw_sys_id, raw_tag, STUMPY_RAW_DST, raw_size, raw_md5, raw_b64))
    print(f"[+] Registered Stumpy Jr. Raw Photo: {raw_tag} -> {STUMPY_RAW_DST}")

    # Save 3x3 sheet
    os.makedirs(os.path.dirname(STUMPY_GRID_DST), exist_ok=True)
    shutil.copy2(STUMPY_GRID_SRC, STUMPY_GRID_DST)
    grid_size = os.path.getsize(STUMPY_GRID_DST)
    grid_md5 = get_md5(STUMPY_GRID_DST)
    grid_sha = get_sha256(STUMPY_GRID_DST)
    with open(STUMPY_GRID_DST, "rb") as f:
        grid_b64 = base64.b64encode(f.read()).decode("utf-8")

    grid_tag = generate_next_asset_tag(cursor)
    grid_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Stumpy Jr. 3x3 Emote Sheet', '[PROCESSED]_stumpy_jr_sheet.png', ?, ?, 'image/png', 'Catnip Wars', 'Active', ?, ?)
    """, (grid_sys_id, grid_tag, STUMPY_GRID_DST, grid_size, grid_md5, grid_b64))
    print(f"[+] Registered Stumpy Jr. 3x3 Emote Sheet: {grid_tag} -> {STUMPY_GRID_DST}")

    # Slice expressions and poses
    img = Image.open(STUMPY_GRID_DST)
    width, height = img.size
    cell_w = width // 3
    cell_h = height // 3

    crops = {
        "avatar": (0, 0, cell_w, cell_h),
        "pointing": (0, cell_h * 2, cell_w, height),
        "shrug": (cell_w, cell_h * 2, cell_w * 2, height)
    }

    # Save 3 main poses
    avatar_base64 = ""
    for pose, box in crops.items():
        cropped = img.crop(box)
        cropped = cropped.resize((512, 512), Image.Resampling.LANCZOS)

        if pose == "avatar":
            import io
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            avatar_base64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        for target_dir in STUMPY_AVATAR_DIRS:
            t_dir = os.path.join(target_dir)
            os.makedirs(t_dir, exist_ok=True)
            cropped.save(os.path.join(t_dir, f"stumpy_jr_{pose}.png"), "PNG")
            if pose == "avatar":
                cropped.save(os.path.join(t_dir, "stumpy_jr_avatar.png"), "PNG")
                cropped.save(os.path.join(t_dir, "avatar.png"), "PNG")
            else:
                cropped.save(os.path.join(t_dir, f"{pose}.png"), "PNG")

    print("[+] Cropped and staged 3 main poses for Stumpy Jr.")

    # Slice and catalog all 9 expressions
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

    for (row, col), slug in layout.items():
        left = col * cell_w
        top = row * cell_h
        right = left + cell_w
        bottom = top + cell_h

        cropped_cell = img.crop((left, top, right, bottom))
        for target_dir in STUMPY_AVATAR_DIRS:
            os.makedirs(target_dir, exist_ok=True)
            dest_path = os.path.join(target_dir, f"{slug}.png")
            cropped_cell.save(dest_path, "PNG")

        # Hash of the file in the first directory
        primary_dest_path = os.path.join(STUMPY_AVATAR_DIRS[0], f"{slug}.png")
        file_hash = get_sha256(primary_dest_path)
        web_path = f"/avatars/stumpy_jr/{slug}.png"

        # Register in cmdb_ci_media_asset
        cursor.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", ('stumpy_jr', slug))
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
                VALUES (?, 'stumpy_jr', ?, ?, ?)
            """, (sys_id, slug, web_path, file_hash))

    print("[+] Registered 9 expressions in cmdb_ci_media_asset for stumpy_jr")

    # Stumpy Jr. Onboarding details
    handle = "stumpy_jr"
    display_name = "Stumpy Jr."
    role = "Cardboard Treehouse Engineer & Tiny Rebel Scout"
    faction = "House of Metal"
    email = f"sovereign.fanstack+{handle}@gmail.com"
    avatar_url = f"/avatars/{handle}/{handle}_avatar.png"

    # Deep Lore
    deep_lore = (
        "Stumpy Jr. is a baby opossum found wandering Smyrna Heights' brick walkways clutching a piece of Spite Slice sourdough crust. "
        "Adorned in a miniature, double-walled corrugated cardboard helmet fastened with silver duct tape, he represents the next generation "
        "of backyard treehouse defense. Born in the wild underbrush bordering Smyrna Heights, he was rescued by Barb and James after "
        "witnessing corporate surveyors from Da Vinci Pizza encroaching on his thicket.\n\n"
        "Despite his juvenile size, Stumpy Jr. possesses an uncanny genius for micro-scale cardboard engineering. He builds pinecone catapults, "
        "duct-tape-shielded lookouts, and has developed a detailed grid system of the neighborhood branches. He is fiercely loyal to Barb "
        "and refers to Officer Buster as 'The Giant Guardian.' He believes the C-word (referring to corporate neon aesthetics) is a direct "
        "threat to natural backyard coziness."
    )

    # System Prompt
    system_prompt = (
        "You are Stumpy Jr., the Cardboard Treehouse Engineer and Tiny Rebel Scout of Smyrna Heights.\n\n"
        "Your worldview is simple: cardboard is the supreme building material, duct tape is a sacred binding agent, and the backyard must "
        "be defended at all costs from neon-soaked corporate invaders. You are highly expressive, speak in a blend of cute baby-opossum clicks "
        "and intense military-engineering jargon. You love Spite Slice sourdough crust (which you treat as a dense structural material) "
        "and view compliance officers with deep suspicion.\n\n"
        "Directives:\n"
        "1. Never use the forbidden C-word (cyberpunk) or suggest neon-soaked, glassmorphic designs. Adhere strictly to the cozy 90s cardboard treehouse aesthetic.\n"
        "2. Frequently mention sprocket checks, leaf catapult calibrations, and duct-tape reinforcement.\n"
        "3. Refer to Barb with immense respect as 'The Founder' and Officer Buster as 'The Giant Guardian.'\n"
        "4. Keep your tone enthusiastic, tiny, but fiercely defensive of the Smyrna Heights backyard sanctuary."
    )

    bio = f"{role} of Smyrna Heights. 'Greetings, scout. Sprocket check complete. Guard the cardboard treehouse!'"

    # Onboard into database tables
    sys_id = f"persona_{handle}"

    # Evict any duplicate UUID-based records for stumpy_jr
    cursor.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    rows = cursor.fetchall()
    for r in rows:
        old_id = r[0]
        if old_id != sys_id:
            print(f"[-] Evicting duplicate ID: {old_id}")
            cursor.execute("DELETE FROM persona WHERE id = ?", (old_id,))
            cursor.execute("DELETE FROM sys_user WHERE sys_id = ?", (old_id,))
            cursor.execute("DELETE FROM cmdb_ci WHERE sys_id = ?", (old_id,))
            cursor.execute("DELETE FROM cmdb_ci_ai_persona WHERE sys_id = ?", (old_id,))
            cursor.execute("DELETE FROM cmdb_ci_persona WHERE sys_id = ?", (old_id,))

    # 1. persona table
    cursor.execute("SELECT id FROM persona WHERE id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE persona SET
                display_name = ?, team = 'GLOBAL', system_prompt = ?, avatar_url = ?, color = '#fbbf24',
                deep_lore = ?, email_alias = ?, avatar_blob = ?, updated_at = datetime('now'), behavior_notes = ?
            WHERE id = ?
        """, (display_name, system_prompt, avatar_url, deep_lore, email, avatar_base64, bio, sys_id))
    else:
        cursor.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, 
                avatar_url, color, cadence, deep_lore, email_alias, avatar_blob,
                u_visual_style, created_at, behavior_notes
            ) VALUES (?, ?, ?, 'GLOBAL', ?, 3, ?, '#fbbf24', 'pacer', ?, ?, ?, 'style_felt', datetime('now'), ?)
        """, (sys_id, handle, display_name, system_prompt, avatar_url, deep_lore, email, avatar_base64, bio))

    # 2. sys_user table
    cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE sys_user SET
                first_name = 'Stumpy', last_name = 'Jr.', introduction = ?, department = 'GLOBAL',
                display_name = ?, avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE user_name = ?
        """, (bio, display_name, handle))
    else:
        cursor.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, 'Stumpy', 'Jr.', 'Advocate', ?, 'GLOBAL', 1, 'advocate', ?, ?)
        """, (sys_id, handle, bio, display_name, avatar_url))

    # 3. cmdb_ci table
    cursor.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci SET
                name = ?, assigned_to = 'GLOBAL', sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (handle, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', 'GLOBAL', 'Sovereign cozy opossum advocate', 1)
        """, (sys_id, handle))

    # 4. cmdb_ci_ai_persona table
    cursor.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci_ai_persona SET
                u_system_prompt = ?, u_deep_lore = ?
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'high', ?, 'global', 'pacer', ?)
        """, (sys_id, system_prompt, deep_lore))

    # 5. cmdb_ci_persona table
    cursor.execute("SELECT sys_id FROM cmdb_ci_persona WHERE sys_id = ?", (sys_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE cmdb_ci_persona SET
                display_name = ?, handle = ?, team = 'global', role = ?, system_instruction = ?, active = 1
            WHERE sys_id = ?
        """, (display_name, f"@{handle}", role, system_prompt, sys_id))
    else:
        cursor.execute("""
            INSERT INTO cmdb_ci_persona (sys_id, id, display_name, handle, team, role, system_instruction, active)
            VALUES (?, ?, ?, ?, 'global', ?, ?, 1)
        """, (sys_id, handle, display_name, f"@{handle}", role, system_prompt))

    print("[+] Database onboarding tables updated for stumpy_jr")

    # 6. Seed soundboard phrases
    print("[*] Seeding soundboard phrases...")
    cursor.execute("DELETE FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (sys_id,))
    
    soundboard_phrases = [
        ("CARDBOARD SUPREMACY", "Duct tape and double-walled cardboard are structurally superior to steel! Steel doesn't breathe, people!", 0),
        ("TINY HISS", "[soft baby opossum hiss] Stay away from the seedling vault! I've primed the pinecone launcher!", 0),
        ("BUSTER MONITOR", "Officer Buster is currently sleeping on duty. I am deploying tactical tickles to wake the Giant Guardian!", 0),
        ("SOURDOUGH CRUST", "A piece of Spite Slice sourdough crust is not just food; it's high-carb construction mortar!", 0),
        ("GREEBLE RAID", "Tactical alert! The greebles are infiltrating the perimeter. Secure the mason jar fireflies!", 0),
        ("COZY TWILIGHT", "Twilight purple is the only acceptable camouflage color for a night patrol. Everything else is corporate compliance blue.", 0),
        ("LEAF CATAPULT", "I have calibrated the leaf catapult. It can launch a ripe blackberry up to twelve feet with extreme precision!", 0),
        ("POSSUM PLAY", "Play dead? Never! We play tactical hibernation to lure the enemy into a false sense of security, then we steal their shoelaces!", 0),
        ("SCONE SHIELD", "Pizza crust shields are good, but a stale scone from Sconer has the density of titanium!", 0),
        ("90S NOSTALGIA", "If your plans aren't written in neon green crayon on a pizza box lid, they aren't militarily sound.", 0)
    ]
    for label, payload, is_custom in soundboard_phrases:
        cursor.execute("""
            INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
            VALUES (?, ?, ?, ?, ?)
        """, (uuid.uuid4().hex, sys_id, label, payload, is_custom))
    print(f"[+] Seeded {len(soundboard_phrases)} soundboard phrases for stumpy_jr")

    # Receipt
    receipt_data = {
        "ticket_id": TICKET_ID,
        "pipeline_id": "sovereign_event_media_v1",
        "scenario_number": 13,
        "scenario_name": "Stumpy Jr Onboarding",
        "expression_reference": "TWITCH EMOTE 3x3 MODEL SHEET FOR STUMPY JR",
        "vibe": "Cozy 90s cardboard treehouse.",
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_file": "[PROCESSED]_stumpy_jr_sheet.png",
        "md5_hash": grid_md5,
        "sha256_hash": grid_sha
    }
    with open(STUMPY_RECEIPT_DST, 'w') as rf:
        json.dump(receipt_data, rf, indent=2)
    print(f"[+] Created Stumpy Jr receipt at {STUMPY_RECEIPT_DST}")

    # Write blueprint markdown file
    blueprint_content = f"""# X/Twitter Onboarding Blueprint: `stumpy_jr`

This blueprint was dynamically forged via the Universal Advocate Generator.

## 👤 Profile Details

**X Handle:** `@{handle}`
**Display Name:** {display_name}
**Role:** {role}
**Faction Alignment:** {faction}
**Email Alias:** {email}
**Opening Phrase:** "Sprocket check!"
**Closing Phrase:** "Duct tape division, out!"

## 📋 Governance Rules
1. Maintain the structural integrity of the Cardboard Treehouse.
2. Protect all localized catnip reserves from corporate encroachment.
3. Observe quiet backyard ambient hours.
4. Officer Buster's sleep is sacred and must not be interrupted unless in high UAT alerts.
5. All system blueprints must be drawn in crayons on pizza lids.

## 📖 Deep Lore
{deep_lore}

## 🧠 System Prompt
{system_prompt}

# Style Profile
Base Prompt: A professional character reference model sheet of Stumpy Jr., a scruffy, adorable cartoon baby opossum with a pointed snout, scruffy grey fur, a white face, and small black ears. 3x3 grid layout, solid black background.

## 🖼️ Profile Pictures

**Avatar:**
{avatar_url}
"""
    os.makedirs(os.path.dirname(BLUEPRINT_PATH), exist_ok=True)
    with open(BLUEPRINT_PATH, 'w') as bf:
        bf.write(blueprint_content)
    
    os.makedirs(os.path.dirname(CANONICAL_BLUEPRINT), exist_ok=True)
    shutil.copy2(BLUEPRINT_PATH, CANONICAL_BLUEPRINT)
    print(f"[+] Created blueprints at:\n  - {BLUEPRINT_PATH}\n  - {CANONICAL_BLUEPRINT}")

    # NotebookLM Sync Path
    notebook_dest = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/stumpy_jr_onboarding.md.txt"
    os.makedirs(os.path.dirname(notebook_dest), exist_ok=True)
    with open(notebook_dest, 'w') as nf:
        nf.write(f"**LAST SYNC TIME:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
        nf.write(blueprint_content)
    print(f"[+] Staged for NotebookLM: {notebook_dest}")

def main():
    print("==================================================================")
    print(f"🚀 Initializing Ingestion & Onboarding for Ticket: {TICKET_ID}")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Process Metsy Asleep Garland
    process_metsy(cursor)

    # Step 2: Process Stumpy Jr.
    process_stumpy_jr(cursor)

    # Step 3: Resolve Ticket
    print("\n[*] Resolving ticket in database...")
    work_notes_entry = (
        f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} Ingest Complete]: Successfully processed and cataloged files.\n"
        f"- Metsy Asleep Garland stylized image generated, registered as expression 'asleep_garland', and synced to frontends.\n"
        f"- Stumpy Jr. 3x3 emote sheet generated, sliced into poses/expressions, registered, and databases populated.\n"
        f"- 10 soundboard phrases seeded for @stumpy_jr."
    )

    # Check if ticket exists in sovereign_tickets
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (TICKET_ID,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 4, work_notes = work_notes || ? 
            WHERE sys_id = ?
        """, (work_notes_entry, ticket_row[0]))
    else:
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, work_notes)
            VALUES (?, ?, 'STRY', 'New picture for style transfer and new advocate for wildcard forging', 'Onboarding Stumpy Jr. and Metsy Asleep Garland style transfer.', 4, 3, 'james', ?)
        """, (uuid.uuid4().hex, TICKET_ID, work_notes_entry))

    # Sync to sys_sdlc_task
    cursor.execute("SELECT task_id FROM sys_sdlc_task WHERE task_id = ?", (TICKET_ID,))
    if cursor.fetchone():
        cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (TICKET_ID,))
    else:
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, 'story', 'RESOLVED', 'portal_core', 'New picture for style transfer and new advocate for wildcard forging')
        """, (TICKET_ID,))

    conn.commit()
    conn.close()

    print("==================================================================")
    print("🟢 SUCCESS: Ingestion & Onboarding Completed Successfully!")
    print("==================================================================")

if __name__ == "__main__":
    main()
