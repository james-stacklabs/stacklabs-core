#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import uuid
import base64
import shutil
import json
from datetime import datetime
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
TICKET_ID = "WO-2026-0613-METSY-PIRATE"

# Source files from work_orders/spark/media
RAW_SRC_JPG = "/home/james/stacklabs/work_orders/spark/media/metsy_pirate.jpg"
RAW_SRC_JFIF = "/home/james/stacklabs/work_orders/spark/media/metsy_pirate.jfif"
CARTOON_SRC_FULL = "/home/james/stacklabs/work_orders/spark/media/metsy_pirate.png"
CARTOON_SRC_1X1 = "/home/james/stacklabs/work_orders/spark/media/metsy_pirate_1x1.png"

# Target destinations in media_vault and work_orders/spark/media
RAW_DST_JPG = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Original/metsy_pirate.jpg"
RAW_DST_JFIF = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Original/metsy_pirate.jfif"
CARTOON_DST_FULL = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_metsy_pirate.png"
CARTOON_DST_1X1 = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_metsy_pirate_1x1.png"
RECEIPT_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_metsy_pirate_receipt.json"

AVATAR_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/02_Sovereign_Media/public/avatars/metsy_smyrna",
    "/home/james/stacklabs/15_FanStack/public/avatars/metsy_smyrna"
]

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
    import re
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

def register_asset(cursor, name, file_name, file_path, category):
    size = os.path.getsize(file_path)
    md5 = get_md5(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    tag = generate_next_asset_tag(cursor)
    sys_id = uuid.uuid4().hex
    
    mime_type = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
    
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
    """, (sys_id, tag, name, file_name, file_path, size, mime_type, category, md5, b64))
    print(f"  [+] Registered Asset: {tag} -> {file_path}")
    return tag, md5

def main():
    print("==================================================================")
    print(f"🚀 Initializing Ingestion for Ticket: {TICKET_ID}")
    print("==================================================================")

    # Verify sources exist
    for src in [RAW_SRC_JPG, RAW_SRC_JFIF, CARTOON_SRC_FULL, CARTOON_SRC_1X1]:
        if not os.path.exists(src):
            print(f"[-] ERROR: Source file not found at: {src}")
            return

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Stage/Initialize Ticket in DB
    print("[*] Staging ticket in database...")
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (TICKET_ID,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        ticket_sys_id = ticket_row[0]
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 2, work_notes = work_notes || '\n[Ingest]: Commenced ingestion of Metsy pirate assets.' 
            WHERE sys_id = ?
        """, (ticket_sys_id,))
    else:
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, 'STRY', 'Ingest and Catalog Metsy Pirate Assets', 'Automated processing and registration of raw and cartoon assets for Metsy Pirate.', 2, 3, 'james', 'DecisionDerby', 'Ticket initialized by ingestion script.')
        """, (ticket_sys_id, TICKET_ID))

    cursor.execute("SELECT task_id FROM sys_sdlc_task WHERE task_id = ?", (TICKET_ID,))
    if cursor.fetchone():
        cursor.execute("UPDATE sys_sdlc_task SET state = 'WIP' WHERE task_id = ?", (TICKET_ID,))
    else:
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, 'story', 'WIP', 'portal_core', 'Ingest and Catalog Metsy Pirate Assets')
        """, (TICKET_ID,))
    conn.commit()

    # Step 2: Copy and Catalog Raw JPG
    print("[*] Processing Raw JPG...")
    os.makedirs(os.path.dirname(RAW_DST_JPG), exist_ok=True)
    shutil.copy2(RAW_SRC_JPG, RAW_DST_JPG)
    jpg_tag, _ = register_asset(cursor, "Metsy Pirate (Original JPG)", "metsy_pirate.jpg", RAW_DST_JPG, "Metsy Raw Photos")

    # Step 3: Copy and Catalog Raw JFIF
    print("[*] Processing Raw JFIF...")
    shutil.copy2(RAW_SRC_JFIF, RAW_DST_JFIF)
    jfif_tag, _ = register_asset(cursor, "Metsy Pirate (Original JFIF)", "metsy_pirate.jfif", RAW_DST_JFIF, "Metsy Raw Photos")
    conn.commit()

    # Step 4: Convert and Catalog Cartoon PNGs (Full and 1x1)
    print("[*] Processing Cartoon PNG (Full)...")
    # Save a clean copy
    with Image.open(CARTOON_SRC_FULL) as img:
        img.save(CARTOON_DST_FULL, "PNG")
    full_tag, full_md5 = register_asset(cursor, "Metsy Adventure 14: Pirate Style (Full)", "[PROCESSED]_metsy_pirate.png", CARTOON_DST_FULL, "Metsy Adventures")
    full_sha = get_sha256(CARTOON_DST_FULL)

    print("[*] Processing Cartoon PNG (1x1)...")
    with Image.open(CARTOON_SRC_1X1) as img:
        img.save(CARTOON_DST_1X1, "PNG")
    avatar_tag, avatar_md5 = register_asset(cursor, "Metsy Adventure 14: Pirate Style (1x1 Avatar)", "[PROCESSED]_metsy_pirate_1x1.png", CARTOON_DST_1X1, "Metsy Adventures")
    avatar_sha = get_sha256(CARTOON_DST_1X1)
    conn.commit()

    # Step 5: Register in cmdb_ci_media_asset (Advocate Expression)
    print("[*] Registering advocate expression mapping...")
    expr_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
        VALUES (?, 'metsy', 'pirate', ?, ?)
    """, (expr_sys_id, CARTOON_DST_FULL, full_sha))
    conn.commit()
    print("  [+] Registered in cmdb_ci_media_asset: advocate=metsy, expression=pirate")

    # Step 6: Copy PNGs to frontends
    print("[*] Copying cartoon PNGs to frontend avatar directories...")
    for target_dir in AVATAR_DIRS:
        os.makedirs(target_dir, exist_ok=True)
        # Copy full cartoon as metsy_pirate.png
        dest_full = os.path.join(target_dir, "metsy_pirate.png")
        shutil.copy2(CARTOON_DST_FULL, dest_full)
        # Copy 1x1 cartoon as metsy_pirate_1x1.png
        dest_1x1 = os.path.join(target_dir, "metsy_pirate_1x1.png")
        shutil.copy2(CARTOON_DST_1X1, dest_1x1)
        print(f"  -> Mapped to: {dest_full} and {dest_1x1}")

    # Step 7: Create JSON receipt
    print("[*] Creating Spark execution receipt...")
    receipt_data = {
        "ticket_id": TICKET_ID,
        "pipeline_id": "sovereign_event_media_v1",
        "scenario_number": 14,
        "scenario_name": "Metsy Pirate",
        "expression_reference": "ACTION: PIRATE / WEARING TRICORN HAT AND PATCH OVER EYE",
        "style_anchor": "metsy_collar.png",
        "vibe": "Gritty neon-grime cartoon action.",
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_file": "[PROCESSED]_metsy_pirate.png",
        "md5_hash": full_md5,
        "sha256_hash": full_sha
    }
    with open(RECEIPT_DST, 'w') as rf:
        json.dump(receipt_data, rf, indent=2)
    print(f"  [+] Created receipt at {RECEIPT_DST}")

    # Step 8: Resolve the ticket in DB
    print("[*] Resolving ticket...")
    work_notes_entry = f"\n[Ingest Complete]: Successfully processed and cataloged files.\n- Raw JPG: {jpg_tag}\n- Raw JFIF: {jfif_tag}\n- Cartoon full: {full_tag}\n- Cartoon 1x1: {avatar_tag}\n- Expression 'pirate' registered for advocate metsy."
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET state = 4, work_notes = work_notes || ? 
        WHERE sys_id = ?
    """, (work_notes_entry, ticket_sys_id))
    cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (TICKET_ID,))
    conn.commit()
    conn.close()

    print("==================================================================")
    print("🟢 SUCCESS: Metsy pirate ingestion complete!")
    print("==================================================================")

if __name__ == "__main__":
    main()
