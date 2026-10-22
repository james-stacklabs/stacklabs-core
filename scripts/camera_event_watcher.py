#!/usr/bin/env python3
import os
import sys
import time
import json
import uuid
import hashlib
import shutil
import sqlite3
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CONFIG_PATH = "/home/james/stacklabs/scripts/automation_config.json"
CACHE_DIR = "/home/james/stacklabs/scripts/event_media_cache"
DEST_DIR = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/metsy_smyrna"
WATCH_DIR = "/home/james/sovereign_inbox/camera_events"

os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(DEST_DIR, exist_ok=True)

def get_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_next_asset_tag():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT asset_tag FROM sys_media_asset ORDER BY asset_tag DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        match = re.search(r'FS-MED-(\d+)', row[0])
        if match:
            next_num = int(match.group(1)) + 1
            return f"FS-MED-{next_num:05d}"
    return "FS-MED-00001"

def process_pipeline(pipeline_name):
    print(f"[CAMERA-EVENT] Triggered pipeline: {pipeline_name}")
    
    # 1. Load config
    if not os.path.exists(CONFIG_PATH):
        print(f"[CAMERA-EVENT] Config file missing at {CONFIG_PATH}")
        return
        
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        
    pipelines = config.get("pipelines", {})
    if pipeline_name not in pipelines and pipeline_name != "metsy_soaked_rain":
        # Check substring match
        matched_pipeline = None
        for k in pipelines.keys():
            if k in pipeline_name:
                matched_pipeline = k
                break
        if matched_pipeline:
            pipeline_name = matched_pipeline
        else:
            print(f"[CAMERA-EVENT] Pipeline {pipeline_name} not found in config.")
            return

    # Cache image source
    src_img = os.path.join(CACHE_DIR, f"{pipeline_name}.png")
    if not os.path.exists(src_img):
        # Fallback to general soaked rain or copy whichever is closest
        src_img = os.path.join(CACHE_DIR, "metsy_soaked_rain.png")
        if not os.path.exists(src_img):
            print(f"[CAMERA-EVENT] Cache source image missing for {pipeline_name}")
            return
            
    # Destination path
    dest_filename = f"{pipeline_name}.png"
    dest_path = os.path.join(DEST_DIR, dest_filename)
    
    # Copy file to public assets directory
    shutil.copy2(src_img, dest_path)
    print(f"[CAMERA-EVENT] Copied stylized event media to: {dest_path}")
    
    # 2. Register in Database: sys_media_asset
    file_size = os.path.getsize(dest_path)
    md5_hash = get_md5(dest_path)
    sha256_hash = get_sha256(dest_path)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if md5 already exists in sys_media_asset
    cursor.execute("SELECT sys_id, asset_tag FROM sys_media_asset WHERE md5_hash = ?", (md5_hash,))
    existing = cursor.fetchone()
    
    sys_id = None
    if existing:
        sys_id = existing[0]
        tag = existing[1]
        print(f"[CAMERA-EVENT] Asset already registered in sys_media_asset as {tag}")
    else:
        sys_id = uuid.uuid4().hex
        tag = get_next_asset_tag()
        clean_name = pipeline_name.replace('_', ' ').title()
        
        cursor.execute("""
            INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sys_id, tag, clean_name, dest_filename, dest_path, file_size, "image/png", "Personas", "Active", md5_hash))
        print(f"[CAMERA-EVENT] Registered in sys_media_asset table with tag: {tag}")
        
    # 3. Register in Database: cmdb_ci_media_asset
    # Check if advocate/expression already exists
    cursor.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", ("six_dinner_inventor", pipeline_name))
    existing_ci = cursor.fetchone()
    
    db_relative_path = f"/avatars/metsy_smyrna/{dest_filename}"
    
    if existing_ci:
        cursor.execute("""
            UPDATE cmdb_ci_media_asset
            SET file_path = ?, sha256 = ?, sys_created_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (db_relative_path, sha256_hash, existing_ci[0]))
        print(f"[CAMERA-EVENT] Updated cmdb_ci_media_asset for advocate: six_dinner_inventor | expression: {pipeline_name}")
    else:
        ci_sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, ?, ?, ?, ?)
        """, (ci_sys_id, "six_dinner_inventor", pipeline_name, db_relative_path, sha256_hash))
        print(f"[CAMERA-EVENT] Inserted into cmdb_ci_media_asset for advocate: six_dinner_inventor | expression: {pipeline_name}")
        
    conn.commit()
    conn.close()
    print("[CAMERA-EVENT] Database transaction committed successfully.")

class CameraEventHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_processed = {}
        self.cooldown = 1.0

    def on_created(self, event):
        if event.is_directory:
            return
            
        filepath = event.src_path
        filename = os.path.basename(filepath)
        
        # Ignore temporary or hidden files
        if filename.startswith('.') or '~' in filename:
            return
            
        now = time.time()
        if filename in self.last_processed and (now - self.last_processed[filename] < self.cooldown):
            return
            
        self.last_processed[filename] = now
        print(f"[CAMERA-EVENT] File detected: {filename}")
        time.sleep(0.5) # Wait for file write completion
        
        # Extract pipeline name from file name
        # e.g., metsy_bird_chase.txt -> metsy_bird_chase
        pipeline_name = os.path.splitext(filename)[0]
        try:
            process_pipeline(pipeline_name)
        except Exception as e:
            print(f"[CAMERA-EVENT] Error processing pipeline {pipeline_name}: {e}")

if __name__ == "__main__":
    print(f"[CAMERA-EVENT] Starting Camera Event Watcher. Watching {WATCH_DIR}...")
    
    # Process any existing files in watch dir at startup
    for f in os.listdir(WATCH_DIR):
        if not f.startswith('.') and os.path.isfile(os.path.join(WATCH_DIR, f)):
            pipeline_name = os.path.splitext(f)[0]
            try:
                process_pipeline(pipeline_name)
            except Exception as e:
                print(f"[CAMERA-EVENT] Error processing initial file {f}: {e}")
                
    event_handler = CameraEventHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("[CAMERA-EVENT] Watcher stopped.")
