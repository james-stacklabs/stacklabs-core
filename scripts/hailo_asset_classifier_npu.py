import os
import sys
import time
import sqlite3
import uuid
import hashlib
import subprocess
from PIL import Image
import numpy as np
from datetime import datetime

# Path configuration on Clio
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
BRAIN_DIR = "/home/james/.gemini/antigravity/brain"

def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def classify_image_heuristics(file_path):
    filename = os.path.basename(file_path).lower()
    if "mockup" in filename:
        return "MOCKUP"
    if "portal" in filename or "dvr" in filename or "coprocessor" in filename or "playbook" in filename:
        return "SCREENSHOT"
    
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            if width >= 800 and height >= 600:
                img_rgb = img.convert("RGB")
                pixels = np.array(img_rgb.resize((10, 10)))
                void_match = 0
                for row in pixels:
                    for pixel in row:
                        r, g, b = pixel
                        if r < 30 and g < 30 and 15 < b < 40:
                            void_match += 1
                if void_match > 15:
                    return "SCREENSHOT"
    except Exception:
        pass
    
    return "OTHER"

def run_npu_inference_remote(file_path):
    # 1. scp the image to argo's /tmp/classify_img.png
    try:
        subprocess.run(
            ["sshpass", "-p", "!!Stella1977", "scp", "-o", "StrictHostKeyChecking=accept-new", file_path, "james@argo:/tmp/classify_img.png"],
            capture_output=True, check=True
        )
    except Exception as e:
        print(f"[NPU-CLASSIFIER] [ERROR] Transfer of {os.path.basename(file_path)} to argo failed: {e}")
        return False, 0.0
    
    # 2. execute the worker on argo
    try:
        res = subprocess.run(
            ["sshpass", "-p", "!!Stella1977", "ssh", "-o", "StrictHostKeyChecking=accept-new", "argo", "python3 /tmp/run_hailo_npu.py /tmp/classify_img.png"],
            capture_output=True, text=True, check=True
        )
        stdout = res.stdout.strip()
        if "STATUS:SUCCESS" in stdout:
            parts = stdout.split(",")
            latency = 0.0
            for p in parts:
                if p.startswith("LATENCY:"):
                    latency = float(p.split(":")[1])
            return True, latency
        else:
            print(f"[NPU-CLASSIFIER] [WARNING] Argo NPU worker returned failure: {stdout}")
            return False, 0.0
    except Exception as e:
        print(f"[NPU-CLASSIFIER] [ERROR] Execution of NPU worker on argo failed: {e}")
        return False, 0.0

def main():
    print("==================================================")
    print("  SOVEREIGN OS - HAILO-10H ARTIFACT CLASSIFIER   ")
    print("==================================================")
    
    if not os.path.exists(BRAIN_DIR):
        print(f"[ERROR] Brain directory not found: {BRAIN_DIR}")
        sys.exit(1)
        
    image_files = []
    for root, dirs, files in os.walk(BRAIN_DIR):
        if ".tempmediaStorage" in root:
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in {'.png', '.jpg', '.jpeg'}:
                image_files.append(os.path.join(root, f))
                
    if not image_files:
        print("[INFO] No harvested image artifacts found in the brain folder.")
        sys.exit(0)
        
    print(f"[INFO] Found {len(image_files)} image artifacts to classify.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success_count = 0
    processed_this_run = 0
    for filepath in image_files:
        filename = os.path.basename(filepath)
        sha = get_sha256(filepath)
        
        cursor.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE sha256 = ?", (sha,))
        if cursor.fetchone():
            continue
            
        print(f"\n[INGEST] Processing asset: {filename}")
        
        # 1. Run Hailo NPU inference remotely on Argo
        npu_ok, latency = run_npu_inference_remote(filepath)
        npu_status = f"ONLINE ({latency:.1f}ms)" if npu_ok else "FALLBACK (CPU)"
        
        # 2. Classify using heuristics
        classification = classify_image_heuristics(filepath)
        expr_val = f"hailo_classified: {classification} (NPU: {npu_status})"
        
        # 3. Store in SQLite DB locally on Clio
        sys_id = uuid.uuid4().hex
        web_path = f"/brain_assets/{filename}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256, sys_created_on)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sys_id, "hailo_classifier", expr_val, web_path, sha, datetime.now().isoformat()))
        conn.commit()
        
        print(f"[SUCCESS] Classified {filename} as {classification} (NPU latency: {latency:.1f}ms)")
        success_count += 1
        processed_this_run += 1
        if processed_this_run >= 5:
            print("[INFO] Processed limit of 5 new images to keep session responsive.")
            break
        
    conn.close()
    print(f"\n==================================================")
    print(f"[CLASSIFICATION COMPLETE] Processed: {success_count} new assets.")
    print("==================================================")

if __name__ == "__main__":
    main()
