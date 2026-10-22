#!/usr/bin/env python3
import os
import sys
import sqlite3
import hashlib
import uuid
import base64
import shutil
import json
import argparse
from datetime import datetime
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AVATAR_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
    "/home/james/stacklabs/02_Sovereign_Media/public/avatars",
    "/home/james/stacklabs/15_FanStack/public/avatars"
]

def get_hashes(filepath):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            md5.update(buf)
            sha256.update(buf)
            buf = f.read(65536)
    return md5.hexdigest(), sha256.hexdigest()

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
            if num < 99999 and num > max_num:
                max_num = num
    next_num = max_num + 1
    return f"FS-MED-{next_num:05d}"

def register_asset(cursor, name, file_name, file_path, category, b64_data, md5):
    size = os.path.getsize(file_path)
    tag = generate_next_asset_tag(cursor)
    sys_id = uuid.uuid4().hex
    if file_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif file_path.lower().endswith(".svg"):
        mime_type = "image/svg+xml"
    else:
        mime_type = "image/jpeg"
    
    cursor.execute("""
        INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
    """, (sys_id, tag, name, file_name, file_path, size, mime_type, category, md5, b64_data))
    print(f"  [+] Registered in sys_media_asset: {tag} -> {file_path}")
    return tag

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Universal Media Ingestion Engine")
    parser.add_argument("--dir", required=True, help="Path to the directory containing processed images and manifest.json")
    parser.add_argument("--ticket", required=True, help="Ticket ID / Story number (e.g. WO-2026-031-METSY-ADVENTURES)")
    parser.add_argument("--advocate", required=True, help="Target advocate handle (e.g. metsy, senora)")
    parser.add_argument("--category", required=True, help="Asset category grouping (e.g. Metsy Adventures, Senora Caos Assets)")
    
    args = parser.parse_args()
    
    manifest_path = os.path.join(args.dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"❌ ERROR: manifest.json not found in target directory: {args.dir}")
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    print("==================================================================")
    print(f"🚀 INITIATING UNIVERSAL ASSET INGESTION FOR TICKET: {args.ticket}")
    print(f"   Target Advocate: @{args.advocate.upper()} | Category: {args.category}")
    print("==================================================================")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Initialize / Stage ticket
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (args.ticket,))
    ticket_row = cursor.fetchone()
    if ticket_row:
        ticket_sys_id = ticket_row[0]
        cursor.execute("""
            UPDATE sovereign_tickets 
            SET state = 2, work_notes = work_notes || ? 
            WHERE sys_id = ?
        """, (f"\n[Ingest]: Commenced ingestion of {args.category} assets.", ticket_sys_id))
    else:
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes)
            VALUES (?, ?, 'STRY', ?, 'Automated processing of advocate assets.', 2, 3, 'james', 'DecisionDerby', 'Ticket initialized by universal ingestion engine.')
        """, (ticket_sys_id, args.ticket, f"Ingest and Catalog {args.category}"))
        
    conn.commit()
    
    registered_assets_info = []
    
    for item in manifest.get("scenarios", []):
        raw_file = item.get("raw_file")
        processed_file = item.get("processed_file")
        scenario_num = item.get("num")
        scenario_name = item.get("name")
        expr_key = item.get("expression_key")
        expr_ref = item.get("expression_reference")
        vibe = item.get("vibe")
        
        src_path = os.path.join(args.dir, processed_file)
        if not os.path.exists(src_path):
            print(f"[-] ERROR: Processed file not found: {src_path}")
            continue
            
        md5, sha256 = get_hashes(src_path)
        with open(src_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
            
        # Catalog in sys_media_asset
        asset_name = f"Advocate {args.advocate.upper()} {scenario_num}: {scenario_name}"
        tag = register_asset(cursor, asset_name, processed_file, src_path, args.category, b64_data, md5)
        registered_assets_info.append(f"- {processed_file}: {tag}")
        
        # Register in cmdb_ci_media_asset
        expr_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, ?, ?, ?, ?)
        """, (expr_sys_id, args.advocate, expr_key, src_path, sha256))
        
        # Copy to public folder structures
        clean_filename = processed_file.replace("[PROCESSED]_", "")
        for base_dir in AVATAR_DIRS:
            target_folder = os.path.join(base_dir, f"{args.advocate}_smyrna")
            os.makedirs(target_folder, exist_ok=True)
            dest_path = os.path.join(target_folder, clean_filename)
            shutil.copy2(src_path, dest_path)
            
        # Write individual receipt json
        receipt_path = os.path.join(args.dir, f"{processed_file.replace('.png', '')}_receipt.json")
        receipt_data = {
            "ticket_id": args.ticket,
            "pipeline_id": "sovereign_event_media_v1",
            "scenario_number": scenario_num,
            "scenario_name": scenario_name,
            "expression_reference": expr_ref,
            "style_anchor": "metsy_collar.png",
            "vibe": vibe,
            "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output_file": processed_file,
            "md5_hash": md5,
            "sha256_hash": sha256
        }
        with open(receipt_path, "w") as rf:
            json.dump(receipt_data, rf, indent=2)
            
    # Resolve Ticket
    print("[*] Resolving ticket...")
    work_notes_entry = f"\n[Ingest Complete]: Successfully processed assets via Universal Engine.\n" + "\n".join(registered_assets_info)
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET state = 4, work_notes = work_notes || ? 
        WHERE sys_id = ?
    """, (work_notes_entry, ticket_sys_id))
    cursor.execute("UPDATE sys_sdlc_task SET state = 'RESOLVED' WHERE task_id = ?", (args.ticket,))
    
    conn.commit()
    conn.close()
    
    print("==================================================================")
    print("🟢 SUCCESS: Universal Ingestion Complete & Ticket Resolved!")
    print("==================================================================")

if __name__ == "__main__":
    main()
