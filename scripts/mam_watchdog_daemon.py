#!/home/james/stacklabs/.venv/bin/python3
# mam_watchdog_daemon.py — Sovereign OS: MAM Ingress Watchdog Daemon
# Monitors /home/james/sovereign_inbox/media_drop/ for new files,
# parses metadata, and populates mam_warehouse.db.

import os
import sys
import time
import uuid
import hashlib
import mimetypes
import sqlite3
import json
import subprocess
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

WATCH_DIR = "/home/james/sovereign_inbox/media_drop"
MAM_DB_PATH = "/home/james/stacklabs/dna/mam_warehouse.db"
LOG_FILE = "/home/james/sovereign_inbox/today/mam_watchdog.log"

# Ensure log and watch directory exist
os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    try:
        with open(LOG_FILE, "a") as lf:
            lf.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Failed writing to log file: {e}")

def get_hashes(file_path):
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                md5_hash.update(byte_block)
                sha256_hash.update(byte_block)
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    except Exception as e:
        log(f"Error hashing file {file_path}: {e}")
        return None, None

def get_image_dimensions(file_path):
    try:
        with Image.open(file_path) as img:
            return img.width, img.height
    except Exception as e:
        log(f"Error reading image dimensions for {file_path}: {e}")
        return None, None

def get_video_metadata(file_path):
    """Retrieve video duration, width, height using ffprobe."""
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration:stream=width,height", 
            "-of", "json", 
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0.0))
        
        streams = data.get("streams", [])
        width, height = None, None
        if streams:
            width = int(streams[0].get("width", 0))
            height = int(streams[0].get("height", 0))
            
        return duration, width, height
    except Exception as e:
        log(f"Error probing video {file_path}: {e}")
        return None, None, None

def process_file(file_path):
    # Wait for file copy to stabilize
    file_size = -1
    while True:
        try:
            current_size = os.path.getsize(file_path)
            if current_size == file_size:
                break
            file_size = current_size
            time.sleep(0.5)
        except OSError:
            # File might have been deleted/moved rapidly
            return

    log(f"Processing new file: {file_path} (Size: {file_size} bytes)")
    
    # Calculate hashes
    md5_val, sha256_val = get_hashes(file_path)
    if not md5_val:
        return
        
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Fallback MIME detection
        if file_path.lower().endswith('.mp4'):
            mime_type = 'video/mp4'
        elif file_path.lower().endswith('.mov'):
            mime_type = 'video/quicktime'
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            mime_type = f"image/{file_path.split('.')[-1].lower()}"
        else:
            mime_type = 'application/octet-stream'

    # Retrieve type-specific metadata
    width, height, duration = None, None, None
    if mime_type.startswith('image/'):
        width, height = get_image_dimensions(file_path)
    elif mime_type.startswith('video/'):
        duration, width, height = get_video_metadata(file_path)

    asset_id = str(uuid.uuid4())
    
    # Persist in DB
    try:
        conn = sqlite3.connect(MAM_DB_PATH)
        cursor = conn.cursor()
        
        # Insert asset record (ON CONFLICT REPLACE in case file_path was previously registered)
        cursor.execute("""
        INSERT INTO media_assets (asset_id, file_path, mime_type, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            mime_type = excluded.mime_type,
            created_at = CURRENT_TIMESTAMP
        RETURNING asset_id;
        """, (asset_id, file_path, mime_type, datetime.utcnow().isoformat()))
        
        row = cursor.fetchone()
        if row:
            asset_id = row[0]
            
        # Clean up existing metadata for this asset_id if doing update
        cursor.execute("DELETE FROM asset_metadata WHERE asset_id = ?", (asset_id,))
        
        # Insert metadata key-values
        metadata_pairs = [
            ("size_bytes", json.dumps(file_size)),
            ("md5", json.dumps(md5_val)),
            ("sha256", json.dumps(sha256_val))
        ]
        if width is not None:
            metadata_pairs.append(("width", json.dumps(width)))
        if height is not None:
            metadata_pairs.append(("height", json.dumps(height)))
        if duration is not None:
            metadata_pairs.append(("duration", json.dumps(duration)))
            
        cursor.executemany("""
        INSERT INTO asset_metadata (asset_id, key, value)
        VALUES (?, ?, ?);
        """, [(asset_id, k, v) for k, v in metadata_pairs])
        
        conn.commit()
        conn.close()
        
        log(f"Successfully cataloged asset {file_path} as ID {asset_id}")
    except Exception as e:
        log(f"Database insertion failed for {file_path}: {e}")

class IngressHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        # Ensure we only process files, not directories or watch temp files
        process_file(event.src_path)

def main():
    log(f"🤖 Starting MAM Watchdog Daemon...")
    log(f"[*] Watching Directory: {WATCH_DIR}")
    log(f"[*] Target Database: {MAM_DB_PATH}")
    log(f"[*] Logs written to: {LOG_FILE}")
    
    event_handler = IngressHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log("MAM Watchdog Daemon stopped.")

if __name__ == "__main__":
    main()
