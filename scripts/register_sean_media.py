#!/usr/bin/env python3
import sqlite3
import hashlib
import uuid
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
FILE_PATH = "/home/james/stacklabs/avatars/sean_carroll/sean_carroll_avatar.png"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"[!] Error: File not found at {FILE_PATH}")
        return

    print("[*] Calculating file hashes...")
    with open(FILE_PATH, "rb") as f:
        data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()
        md5 = hashlib.md5(data).hexdigest()
        size = len(data)

    print(f"  SHA256: {sha256}")
    print(f"  MD5: {md5}")
    print(f"  Size: {size} bytes")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Check if already exists in cmdb_ci_media_asset
    cur.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = 'sean_carroll' AND expression = 'avatar'")
    row = cur.fetchone()
    if row:
        print("[+] Entry already exists in cmdb_ci_media_asset. Updating...")
        cur.execute("""
            UPDATE cmdb_ci_media_asset SET
                file_path = '/avatars/sean_carroll/sean_carroll_avatar.png',
                sha256 = ?,
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE advocate = 'sean_carroll' AND expression = 'avatar'
        """, (sha256,))
    else:
        print("[+] Inserting new entry in cmdb_ci_media_asset...")
        sys_id = str(uuid.uuid4()).replace('-', '')
        cur.execute("""
            INSERT INTO cmdb_ci_media_asset (sys_id, advocate, expression, file_path, sha256)
            VALUES (?, 'sean_carroll', 'avatar', '/avatars/sean_carroll/sean_carroll_avatar.png', ?)
        """, (sys_id, sha256))

    # 2. Check if already exists in sys_media_asset
    cur.execute("SELECT sys_id FROM sys_media_asset WHERE file_path = '/avatars/sean_carroll/sean_carroll_avatar.png'")
    row = cur.fetchone()
    if row:
        print("[+] Entry already exists in sys_media_asset. Updating...")
        cur.execute("""
            UPDATE sys_media_asset SET
                file_size_bytes = ?,
                md5_hash = ?,
                updated_at = datetime('now'),
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE file_path = '/avatars/sean_carroll/sean_carroll_avatar.png'
        """, (size, md5))
    else:
        print("[+] Inserting new entry in sys_media_asset...")
        sys_id = str(uuid.uuid4()).replace('-', '')
        tag = f"AST{sys_id[:8].upper()}"
        cur.execute("""
            INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash)
            VALUES (?, ?, 'sean_carroll_avatar', 'sean_carroll_avatar.png', '/avatars/sean_carroll/sean_carroll_avatar.png', ?, 'image/png', 'avatar', 'Active', ?)
        """, (sys_id, tag, size, md5))

    conn.commit()
    conn.close()
    print("[✔] Media asset registration complete!")

if __name__ == "__main__":
    main()
