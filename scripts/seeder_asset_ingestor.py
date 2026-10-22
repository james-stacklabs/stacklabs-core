#!/usr/bin/env python3
import os
import sqlite3
import base64
import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

router = APIRouter()
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
VAULT_DIR = "/home/james/sovereign_inbox/daily_05282026"

@router.post("/api/system/seeder/upload_asset")
async def upload_seeder_asset(
    brand_id: str = Form(...),
    asset_type: str = Form(...),  # 'logo', 'banner', 'reference_doc'
    file: UploadFile = File(...)
):
    # Read raw binary data natively from the incoming payload stream
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file payload is empty.")
        
    # Generate an MD5 cryptographic signature to enforce uniqueness constraints
    md5_engine = hashlib.md5()
    md5_engine.update(file_bytes)
    file_hash = md5_engine.hexdigest()
    
    # Base64 encode the binary data for raw SQLite storage alignment
    encoded_string = base64.b64encode(file_bytes).decode("utf-8")
    
    # Calculate sequential asset tracking index numbers cleanly
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sys_media_asset")
    asset_count = cursor.fetchone()[0] + 1
    asset_tag = f"FS-MED-{asset_count:05d}"
    sys_id = f"att_{hashlib.sha256(file_hash.encode()).hexdigest()[:16]}"
    
    # Ensure daily vault directory exists and write a physical copy there to keep inbox pristine
    os.makedirs(VAULT_DIR, exist_ok=True)
    vault_file_path = os.path.join(VAULT_DIR, file.filename)
    try:
        with open(vault_file_path, "wb") as vf:
            vf.write(file_bytes)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to write physical backup: {str(e)}")
        
    try:
        cursor.execute("""
            INSERT INTO sys_media_asset (
                sys_id, asset_tag, name, file_name, file_path, file_size_bytes, 
                mime_type, category, status, md5_hash, brand_id, image_blob, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            sys_id, asset_tag, file.filename, file.filename, vault_file_path, len(file_bytes),
            file.content_type or 'image/png', asset_type, file_hash, brand_id, encoded_string
        ))
        conn.commit()
        
        # Enforce Rule 24: Log asset reference details back to the active ticket, ensuring valid sys_id
        ticket_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, short_description, state, type, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, 4, 'STRY', datetime('now'), datetime('now'))
        """, (ticket_sys_id, f"STRY{sys_id[4:12].upper()}", f"Programmatic Asset Ingestion: Mapped {asset_tag} to Brand {brand_id}"))
        conn.commit()
        
        return {
            "status": "INGESTED",
            "asset_tag": asset_tag,
            "sys_id": sys_id,
            "file_mapped": file.filename,
            "md5_signature": file_hash,
            "vault_path": vault_file_path
        }
    except sqlite3.IntegrityError as ie:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Duplicate asset mutation blocked or constraint failure: {str(ie)}")
    finally:
        conn.close()
