#!/usr/bin/env python3
import os
import re
import sqlite3
import shutil
import time
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
VAULT_ROOT = "/home/james/stacklabs/dna/medical_vault"

SUBDIRS = {
    "labs_and_bloodwork": "Lab",
    "oncology_notes": "Oncology",
    "imaging_and_scans": "Scan",
    "prescriptions": "Medication"
}

def setup_vault_directories():
    """Ensure secure storage vault subdirectories exist."""
    if not os.path.exists(VAULT_ROOT):
        os.makedirs(VAULT_ROOT, mode=0o700, exist_ok=True)
        print(f"[VAULT] Created root directory: {VAULT_ROOT}")
    
    for sub, cat in SUBDIRS.items():
        subpath = os.path.join(VAULT_ROOT, sub)
        if not os.path.exists(subpath):
            os.makedirs(subpath, mode=0o700, exist_ok=True)
            print(f"[VAULT] Created category directory: {subpath} ({cat})")

def parse_filename(filename):
    """
    Parse category, document_title, provider_name, date_of_service, and uploaded_by from filename.
    Expected format examples:
      - WellStar_Biopsy_Report_2026-06-15.pdf
      - James_WellStar_Biopsy_Report_2026-06-15.pdf
      - Quest_Diagnostics_Blood_Chemistry_Panel_2026-05-10.pdf
    """
    name_w_o_ext, ext = os.path.splitext(filename)
    
    # Extract date YYYY-MM-DD
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', name_w_o_ext)
    if date_match:
        date_of_service = date_match.group(1)
        # Remove date part from name string
        name_clean = name_w_o_ext.replace(date_of_service, "")
    else:
        date_of_service = datetime.now().strftime("%Y-%m-%d")
        name_clean = name_w_o_ext

    name_clean = re.sub(r'[-_\s]+', '_', name_clean).strip('_')

    # Detect uploader (James, Sean, Allyson, Barb)
    uploaded_by = "System"
    uploaders = ["james", "sean", "allyson", "barb"]
    parts = name_clean.split('_')
    if parts and parts[0].lower() in uploaders:
        uploaded_by = parts[0].capitalize()
        parts = parts[1:]  # remove uploader from title parsing

    # Reconstruct clean name parts
    if not parts or parts == [""]:
        provider_name = "Unknown Provider"
        document_title = name_w_o_ext.replace("_", " ")
    elif len(parts) == 1:
        provider_name = "Unknown Provider"
        document_title = parts[0].replace("_", " ")
    else:
        # First part as provider, remaining as document title
        provider_name = parts[0]
        # Check if second part should also join provider (e.g. Quest Diagnostics)
        if provider_name.lower() == "quest" and len(parts) > 2 and parts[1].lower() == "diagnostics":
            provider_name = "Quest Diagnostics"
            document_title = " ".join(parts[2:])
        else:
            document_title = " ".join(parts[1:])
            
    # Clean formatting
    provider_name = provider_name.replace("_", " ").strip()
    document_title = document_title.replace("_", " ").strip()
    
    return provider_name, document_title, date_of_service, uploaded_by

def ingest_files():
    """Scan vault directories, parse filenames, register to DB, and lock permissions."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    ingested_count = 0
    
    for sub, cat in SUBDIRS.items():
        subpath = os.path.join(VAULT_ROOT, sub)
        if not os.path.exists(subpath):
            continue
            
        for file in os.listdir(subpath):
            file_path = os.path.join(subpath, file)
            if not os.path.isfile(file_path):
                continue
                
            # Lock file permissions so only owner (james) can read/write
            try:
                os.chmod(file_path, 0o600)
            except Exception as e:
                print(f"[WARN] Failed to lock permissions for {file}: {e}")
                
            provider_name, document_title, date_of_service, uploaded_by = parse_filename(file)
            
            try:
                cur.execute("""
                    INSERT INTO sovereign_medical_vault 
                    (category, document_title, provider_name, date_of_service, file_path, uploaded_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cat, document_title, provider_name, date_of_service, file_path, uploaded_by))
                
                print(f"[INGEST] Registered {cat} Record:")
                print(f"   Title:    {document_title}")
                print(f"   Provider: {provider_name}")
                print(f"   Date:     {date_of_service}")
                print(f"   By:       {uploaded_by}")
                print(f"   Path:     {file_path}\n")
                ingested_count += 1
            except sqlite3.IntegrityError:
                # Already exists, skip silently
                pass
            except Exception as e:
                print(f"[ERROR] Failed to insert record for {file}: {e}")
                
    conn.commit()
    conn.close()
    print(f"[VAULT] Ingestion run completed. {ingested_count} new records registered.")

if __name__ == "__main__":
    setup_vault_directories()
    print("[VAULT] Medical Vault Ingestion Daemon started. Monitoring directories...")
    while True:
        try:
            ingest_files()
        except Exception as e:
            print(f"[VAULT EXCEPTION] {e}")
        time.sleep(10)
