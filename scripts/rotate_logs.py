#!/usr/bin/env python3
"""
rotate_logs.py
==============
STRY-06072026-LOG-INTEGRATION — Phase 1: Automated Log Rotation

Monitors fanstack_chatbots.log. When the file size exceeds 50MB:
- Rotates the file.
- Compresses the rotated chunk into a .gz archive.
- Deletes files older than 5 rotations.
"""

import os
import gzip
import shutil
from datetime import datetime

LOG_FILE = "/home/james/stacklabs/logs/fanstack_chatbots.log"
LIMIT_BYTES = 50 * 1024 * 1024  # 50MB
MAX_ROTATIONS = 5

def main():
    if not os.path.exists(LOG_FILE):
        print(f"Log file {LOG_FILE} does not exist. Skipping.")
        return

    size_bytes = os.path.getsize(LOG_FILE)
    size_mb = size_bytes / (1024 * 1024)

    if size_bytes < LIMIT_BYTES:
        print(f"Log file size is {size_mb:.2f} MB, which is below the 50 MB limit. No rotation needed.")
        return

    print(f"Log file size {size_mb:.2f} MB exceeds 50 MB limit. Initiating rotation...")

    # Generate unique timestamp for the rotated chunk
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dir_name = os.path.dirname(LOG_FILE)
    base_name = os.path.basename(LOG_FILE)
    rotated_temp = os.path.join(dir_name, f"{base_name}.{timestamp}")
    zipped_file = f"{rotated_temp}.gz"

    try:
        # Perform atomic copytruncate to avoid disrupting writing process
        with open(LOG_FILE, "r+b") as f_in:
            with open(rotated_temp, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            f_in.seek(0)
            f_in.truncate(0)
        
        # Compress the temporary rotated file
        with open(rotated_temp, "rb") as f_in:
            with gzip.open(zipped_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Clean up temporary uncompressed file
        os.remove(rotated_temp)
        print(f"Successfully rotated and compressed: {zipped_file}")
    except Exception as e:
        print(f"Error during rotation/compression: {e}")
        if os.path.exists(rotated_temp):
            os.remove(rotated_temp)
        return

    # Enforce retention policy: keep only the most recent MAX_ROTATIONS
    try:
        rotations = []
        for item in os.listdir(dir_name):
            if item.startswith(base_name + ".") and item.endswith(".gz"):
                full_path = os.path.join(dir_name, item)
                rotations.append(full_path)
        
        # Sort by modification time (oldest first)
        rotations.sort(key=os.path.getmtime)
        
        if len(rotations) > MAX_ROTATIONS:
            excess = len(rotations) - MAX_ROTATIONS
            print(f"Found {len(rotations)} rotations. Retention limit is {MAX_ROTATIONS}. Cleaning up {excess} old files...")
            for i in range(excess):
                os.remove(rotations[i])
                print(f"Deleted old rotation: {rotations[i]}")
    except Exception as e:
        print(f"Error enforcing retention policy: {e}")

if __name__ == "__main__":
    main()
