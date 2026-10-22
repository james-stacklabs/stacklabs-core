import sqlite3
import hashlib
import os
import uuid
from datetime import datetime

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_sha256(file_path):
    hash_sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha.update(chunk)
    return hash_sha.hexdigest()

def register_assets():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    assets = [
        {
            'name': 'Barf Prime Mascot Avatar',
            'file_name': 'barf.png',
            'file_path': '/home/james/stacklabs/24_TesseractStack/public/barf.png',
            'category': 'Tesseract',
            'mime_type': 'image/png',
            'advocate': 'barf',
            'expression': 'prime_avatar',
            'web_path': '/barf.png'
        },
        {
            'name': 'Barf 1970 Pirates Uniform Throwback Avatar',
            'file_name': 'barf-1970.png',
            'file_path': '/home/james/stacklabs/24_TesseractStack/public/barf-1970.png',
            'category': 'Tesseract',
            'mime_type': 'image/png',
            'advocate': 'barf',
            'expression': '1970_pirates_avatar',
            'web_path': '/barf-1970.png'
        }
    ]

    # Find the maximum asset_tag number to increment
    c.execute("SELECT asset_tag FROM sys_media_asset WHERE asset_tag LIKE 'FS-MED-%'")
    tags = c.fetchall()
    max_num = 0
    for row in tags:
        try:
            num = int(row[0].replace('FS-MED-', ''))
            if num > max_num:
                max_num = num
        except ValueError:
            pass

    for asset in assets:
        if not os.path.exists(asset['file_path']):
            print(f"File not found: {asset['file_path']}")
            continue

        md5_val = get_md5(asset['file_path'])
        sha256_val = get_sha256(asset['file_path'])
        file_size = os.path.getsize(asset['file_path'])

        # 1. Register in sys_media_asset idempotently
        c.execute("SELECT sys_id FROM sys_media_asset WHERE md5_hash = ? OR file_path = ?", (md5_val, asset['file_path']))
        sys_row = c.fetchone()
        if not sys_row:
            sys_id = str(uuid.uuid4()).replace('-', '')
            max_num += 1
            asset_tag = f"FS-MED-{max_num:05d}"
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            c.execute("""
                INSERT INTO sys_media_asset 
                (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, created_at, updated_at, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?, ?)
            """, (sys_id, asset_tag, asset['name'], asset['file_name'], asset['file_path'], file_size, asset['mime_type'], asset['category'], md5_val, now_str, now_str, now_str, now_str))
            print(f"Registered {asset['name']} in sys_media_asset with tag {asset_tag}")
        else:
            print(f"{asset['name']} already exists in sys_media_asset")

        # 2. Register in cmdb_ci_media_asset idempotently
        c.execute("SELECT sys_id FROM cmdb_ci_media_asset WHERE advocate = ? AND expression = ?", (asset['advocate'], asset['expression']))
        cmdb_row = c.fetchone()
        if not cmdb_row:
            sys_id_cmdb = str(uuid.uuid4()).replace('-', '')
            c.execute("""
                INSERT INTO cmdb_ci_media_asset 
                (sys_id, advocate, expression, file_path, sha256)
                VALUES (?, ?, ?, ?, ?)
            """, (sys_id_cmdb, asset['advocate'], asset['expression'], asset['web_path'], sha256_val))
            print(f"Registered {asset['advocate']} ({asset['expression']}) in cmdb_ci_media_asset")
        else:
            c.execute("""
                UPDATE cmdb_ci_media_asset 
                SET file_path = ?, sha256 = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE advocate = ? AND expression = ?
            """, (asset['web_path'], sha256_val, asset['advocate'], asset['expression']))
            print(f"Updated {asset['advocate']} ({asset['expression']}) in cmdb_ci_media_asset")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    register_assets()
