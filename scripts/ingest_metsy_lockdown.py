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
TICKET_ID = "WO-2026-0612-METSY-LOCKDOWN"

RAW_SRC = "/home/james/sovereign_inbox/pilot_drops/Metsy Prime/metsy_lockdown_response_1.jpg"
CARTOON_SRC = "/home/james/sovereign_inbox/pilot_drops/Metsy Prime/metsy_lockdown_response_1.jfif"

RAW_DST = "/home/james/stacklabs/media_vault/01_Assets/Metsy_Original/metsy_lockdown_response.jpg"
CARTOON_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_lockdown_response.png"
RECEIPT_DST = "/home/james/stacklabs/work_orders/spark/media/[PROCESSED]_lockdown_response_receipt.json"

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


def main():
    print("==================================================================")
    print(f"🚀 Initializing Ingestion for Ticket: {TICKET_ID}")
    print("==================================================================")

    # Verify sources exist
    if not os.path.exists(RAW_SRC):
        print(f"[-] ERROR: Raw source file not found at: {RAW_SRC}")
        return
    if not os.path.exists(CARTOON_SRC):
        print(f"[-] ERROR: Cartoon source file not found at: {CARTOON_SRC}")
        return

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Stage/Initialize Ticket in DB
    print("[*] Staging ticket in database...")
    # Check if exists
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (TICKET_ID,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        ticket_sys_id = ticket_row[0]
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 2, work_notes = work_notes || '\n[Ingest]: Commenced ingestion of Metsy lockdown assets.' 
            WHERE sys_id = ?
        """, (ticket_sys_id,))
    else:
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, 'STRY', 'Ingest and Catalog Metsy Lockdown Response Assets', 'Automated processing and registration of raw and cartoon assets for Metsy Lockdown Response.', 2, 3, 'james', 'DecisionDerby', 'Ticket initialized by ingestion daemon.')
        """, (ticket_sys_id, TICKET_ID))

    cursor.execute("SELECT task_id FROM sys_sdlc_task WHERE task_id = ?", (TICKET_ID,))
    if cursor.fetchone():
        cursor.execute("UPDATE sys_sdlc_task SET state = 'WIP' WHERE task_id = ?", (TICKET_ID,))
    else:
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, 'story', 'WIP', 'portal_core', 'Ingest and Catalog Metsy Lockdown Response Assets')
        """, (TICKET_ID,))
    conn.commit()

    # Step 2: Copy and Catalog Raw Photo
    print("[*] Processing Raw Photo...")
    os.makedirs(os.path.dirname(RAW_DST), exist_ok=True)
    shutil.copy2(RAW_SRC, RAW_DST)
    raw_size = os.path.getsize(RAW_DST)
    raw_md5 = get_md5(RAW_DST)
    with open(RAW_DST, "rb") as f:
        raw_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Generate sequential asset tag
    raw_tag = generate_next_asset_tag(cursor)
    raw_sys_id = uuid.uuid4().hex

    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Metsy Lockdown Response (Original)', 'metsy_lockdown_response.jpg', ?, ?, 'image/jpeg', 'Metsy Raw Photos', 'Active', ?, ?)
    """, (raw_sys_id, raw_tag, RAW_DST, raw_size, raw_md5, raw_b64))
    conn.commit()
    print(f"  [+] Registered Raw Photo: {raw_tag} -> {RAW_DST}")

    # Step 3: Process Cartoon JFIF -> PNG
    print("[*] Converting and registering Cartoon Avatar (JFIF -> PNG)...")
    os.makedirs(os.path.dirname(CARTOON_DST), exist_ok=True)
    
    # Use Pillow to perform clean conversion
    with Image.open(CARTOON_SRC) as img:
        img.save(CARTOON_DST, "PNG")

    cartoon_size = os.path.getsize(CARTOON_DST)
    cartoon_md5 = get_md5(CARTOON_DST)
    cartoon_sha = get_sha256(CARTOON_DST)
    with open(CARTOON_DST, "rb") as f:
        cartoon_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Generate sequential tag
    cartoon_tag = generate_next_asset_tag(cursor)
    cartoon_sys_id = uuid.uuid4().hex

    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, 'Metsy Adventure 11: Lockdown Response', '[PROCESSED]_lockdown_response.png', ?, ?, 'image/png', 'Metsy Adventures', 'Active', ?, ?)
    """, (cartoon_sys_id, cartoon_tag, CARTOON_DST, cartoon_size, cartoon_md5, cartoon_b64))
    conn.commit()
    print(f"  [+] Registered Cartoon PNG: {cartoon_tag} -> {CARTOON_DST}")

    # Step 4: Register in cmdb_ci_media_asset (Advocate Expression)
    print("[*] Registering advocate expression mapping...")
    expr_sys_id = uuid.uuid4().hex
    cursor.execute("""
        INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
        VALUES (?, 'metsy', 'lockdown_response', ?, ?)
    """, (expr_sys_id, CARTOON_DST, cartoon_sha))
    conn.commit()
    print(f"  [+] Registered in cmdb_ci_media_asset: advocate=metsy, expression=lockdown_response")

    # Step 5: Copy PNG to frontends
    print("[*] Copying PNG to frontend avatar directories...")
    for target_dir in AVATAR_DIRS:
        os.makedirs(target_dir, exist_ok=True)
        dest_file = os.path.join(target_dir, "metsy_lockdown_response.png")
        shutil.copy2(CARTOON_DST, dest_file)
        print(f"  -> Mapped to: {dest_file}")

    # Step 6: Create JSON receipt
    print("[*] Creating Spark execution receipt...")
    receipt_data = {
        "ticket_id": TICKET_ID,
        "pipeline_id": "sovereign_event_media_v1",
        "scenario_number": 11,
        "scenario_name": "Metsy Lockdown Response",
        "expression_reference": "STANCE: HOSTILE or ACTION: EYE ROLL / THREATENING TO KNOCK SOMETHING OFF TABLE",
        "style_anchor": "metsy_collar.png",
        "vibe": "Gritty neon-grime cartoon action.",
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_file": "[PROCESSED]_lockdown_response.png",
        "md5_hash": cartoon_md5,
        "sha256_hash": cartoon_sha
    }
    with open(RECEIPT_DST, 'w') as rf:
        json.dump(receipt_data, rf, indent=2)
    print(f"  [+] Created receipt at {RECEIPT_DST}")

    # Step 7: Resolve the ticket in DB
    print("[*] Resolving ticket...")
    work_notes_entry = f"\n[Ingest Complete]: Successfully processed and cataloged files.\n- Raw photo: {raw_tag}\n- Cartoon avatar: {cartoon_tag}\n- Expression 'lockdown_response' registered for advocate metsy."
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET state = 4, work_notes = work_notes || ? 
        WHERE sys_id = ?
    """, (work_notes_entry, ticket_sys_id))
    cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (TICKET_ID,))
    conn.commit()
    conn.close()

    print("==================================================================")
    print("🟢 SUCCESS: Metsy lockdown response ingestion complete!")
    print("==================================================================")

if __name__ == "__main__":
    main()
