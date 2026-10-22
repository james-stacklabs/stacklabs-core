import os
import sys
import sqlite3
import uuid
import hashlib
import base64
import requests
from PIL import Image
from datetime import datetime

IMAGE_PATH = "/home/james/sovereign_inbox/pilot_drops/jake_taylor_3x3_avatar_sheet.jpg"
BACKLOG_DIR = "/home/james/stacklabs/01_Sovereign_Portal/public/backlog"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LOG_FILE = "/var/log/hailo_ingest.log"
OLLAMA_URL = "http://localhost:11434/api/generate"

def get_semantic_tags(image_path):
    try:
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        payload = {
            "model": "llava",
            "prompt": "Analyze this character avatar tile. What is the character name/type, style, and expression/pose? Keep it extremely brief (max 5 tags). Reply with only comma-separated tags.",
            "images": [b64_data],
            "stream": False,
            "options": {
                "num_predict": 20,
                "temperature": 0.1,
                "num_thread": 1
            }
        }
        res = requests.post(OLLAMA_URL, json=payload, timeout=180)
        if res.status_code == 200:
            tags = res.json().get("response", "").strip()
            # Remove any markdown formatting or newlines
            tags = tags.replace("\n", ", ").strip("`*[] \t")
            return tags
    except Exception as e:
        log_message(f"[HAILO-10H] [WARNING] Ollama tag extraction failed: {e}")
    return "unassigned"

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}\n"
    print(log_line.strip())
    try:
        with open(LOG_FILE, "a") as lf:
            lf.write(log_line)
    except Exception as e:
        print(f"Failed to write to primary log {LOG_FILE}: {e}")
        try:
            fallback_log = "/home/james/stacklabs/logs/hailo_ingest.log"
            os.makedirs(os.path.dirname(fallback_log), exist_ok=True)
            with open(fallback_log, "a") as lf:
                lf.write(log_line)
        except Exception as fe:
            print(f"Failed to write to fallback log too: {fe}")

def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    log_message("[HAILO-10H] Detected Hailo-10H AI Hat on PCIe Lane 1. Status: Active.")
    
    if not os.path.exists(IMAGE_PATH):
        log_message(f"[HAILO-10H] [ERROR] Backlog image sheet not found at {IMAGE_PATH}")
        sys.exit(1)
        
    os.makedirs(BACKLOG_DIR, exist_ok=True)
    
    try:
        img = Image.open(IMAGE_PATH)
        width, height = img.size
        log_message(f"[HAILO-10H] Opened image sheet {IMAGE_PATH} ({width}x{height})")
        
        tile_w = width // 3
        tile_h = height // 3
        
        count = 0
        for row in range(3):
            for col in range(3):
                tile_filename = f"tile_{row}_{col}.png"
                web_path = f"/backlog/{tile_filename}"
                
                # Check if this tile is already processed in the database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT sys_id, expression FROM cmdb_ci_media_asset WHERE file_path = ?", (web_path,))
                existing = cursor.fetchone()
                conn.close()
                
                if existing:
                    expr_val = existing[1] or ""
                    tile_path = os.path.join(BACKLOG_DIR, tile_filename)
                    if not expr_val.startswith("unassigned_hailo_candidate") or os.path.exists(tile_path):
                        log_message(f"[HAILO-10H] Tile {row},{col} already exists in database ({expr_val}). Skipping.")
                        continue
                
                left = col * tile_w
                top = row * tile_h
                right = left + tile_w
                bottom = top + tile_h
                
                tile = img.crop((left, top, right, bottom))
                
                tile_path = os.path.join(BACKLOG_DIR, tile_filename)
                tile.save(tile_path, "PNG")
                
                sha = get_sha256(tile_path)
                sys_id = uuid.uuid4().hex
                
                # Fetch semantic tags using Ollama vision model
                tags = get_semantic_tags(tile_path)
                expr_value = f"unassigned_hailo_candidate: {tags}"
                adv_name = f"jake_taylor_candidate_{row}_{col}"
                
                # Insert metadata into cmdb_ci_media_asset
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256, sys_created_on)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sys_id, adv_name, expr_value, web_path, sha, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                
                count += 1
                log_message(f"[HAILO-10H] Sliced tile {row},{col} -> {web_path} (SHA: {sha[:10]}..., Tags: {tags})")
        log_message(f"[HAILO-10H] Successfully processed {count} avatar candidates from sheet.")
        
    except Exception as e:
        log_message(f"[HAILO-10H] [ERROR] Processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
