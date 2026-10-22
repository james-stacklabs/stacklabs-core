#!/usr/bin/env python3
import sqlite3
import base64
import os

HISTORICAL_DB = "/home/james/sovereign_inbox/executed/sovereign_now_historical_backup.db"
PATHS = [
    "/home/james/stacklabs/avatars/sean_carroll/sean_carroll_avatar.png",
    "/home/james/stacklabs/15_FanStack/public/avatars/sean_carroll/sean_carroll_avatar.png"
]

def main():
    print("[*] Connecting to historical backup database...")
    conn = sqlite3.connect(HISTORICAL_DB)
    cur = conn.cursor()
    
    cur.execute("SELECT avatar_blob FROM persona WHERE user_name = 'sean_carroll'")
    row = cur.fetchone()
    if not row or not row[0]:
        print("[!] Error: No avatar_blob found for sean_carroll.")
        conn.close()
        return
        
    blob_str = row[0]
    conn.close()
    
    # If the blob starts with a data URI scheme, strip it
    if blob_str.startswith("data:image"):
        header, base64_data = blob_str.split(",", 1)
    else:
        base64_data = blob_str
        
    print("[*] Decoding base64 avatar image...")
    try:
        img_data = base64.b64decode(base64_data)
    except Exception as e:
        print(f"[!] Base64 decode failed: {e}")
        return
        
    for path in PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(img_data)
        print(f"[+] Saved avatar to {path}")
        
    print("[✔] Avatar extraction complete!")

if __name__ == "__main__":
    main()
