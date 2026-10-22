#!/usr/bin/env python3
import os
import sys
import uuid
import hashlib
import sqlite3
from PIL import Image

def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 slice_avatars.py <username> <master_image_path>")
        sys.exit(1)

    username = sys.argv[1]
    master_image_path = sys.argv[2]

    if not os.path.exists(master_image_path):
        print(f"Error: Master image not found at {master_image_path}")
        sys.exit(1)

    # Output directory
    output_dir = f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{username}"
    os.makedirs(output_dir, exist_ok=True)

    # Layout mapping: row, col -> slug
    # Row 0: front, Row 1: left, Row 2: right
    # Col 0: neutral, Col 1: talking, Col 2: surprised
    layout = {
        (0, 0): "front_neutral",
        (0, 1): "front_talking",
        (0, 2): "front_surprised",
        (1, 0): "left_neutral",
        (1, 1): "left_talking",
        (1, 2): "left_surprised",
        (2, 0): "right_neutral",
        (2, 1): "right_talking",
        (2, 2): "right_surprised"
    }

    try:
        img = Image.open(master_image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        sys.exit(1)

    width, height = img.size
    cell_w = width // 3
    cell_h = height // 3

    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for (row, col), slug in layout.items():
        # Coordinates for cropping
        left = col * cell_w
        top = row * cell_h
        right = left + cell_w
        bottom = top + cell_h

        # Crop and save as PNG
        cropped = img.crop((left, top, right, bottom))
        dest_filename = f"{slug}.png"
        dest_path = os.path.join(output_dir, dest_filename)
        cropped.save(dest_path, "PNG")

        # Compute hash
        file_hash = compute_sha256(dest_path)
        web_path = f"/avatars/{username}/{dest_filename}"

        # Register in SQLite cmdb_ci_media_asset
        cursor.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (username, slug))
        existing = cursor.fetchone()

        if existing:
            sys_id = existing[0]
            cursor.execute("""
                UPDATE cmdb_ci_media_asset
                SET file_path = ?, sha256 = ?, sys_created_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (web_path, file_hash, sys_id))
            print(f"Updated media asset: {username} -> {slug} ({file_hash[:8]})")
        else:
            sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
                VALUES (?, ?, ?, ?, ?)
            """, (sys_id, username, slug, web_path, file_hash))
            print(f"Registered new media asset: {username} -> {slug} ({file_hash[:8]})")

    conn.commit()
    conn.close()
    print("Slicing and cataloging complete successfully.")

if __name__ == "__main__":
    main()
