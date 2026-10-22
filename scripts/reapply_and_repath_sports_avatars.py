import os
import shutil
import base64
import sqlite3

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
BASE_DIR = '/home/james/stacklabs/15_FanStack/public/avatars'

PERSONAS = [
    {"id": "spring_league_stalwart", "team": "UFL", "sub": "ufl"},
    {"id": "chip_telemetry_tom", "team": "UFL", "sub": "ufl"},
    {"id": "stadium_phantom_stl", "team": "UFL", "sub": "ufl"},
    {"id": "metlife_meltdown", "team": "NYJ", "sub": "nfl"},
    {"id": "gridiron_gary", "team": "PIT", "sub": "nfl"},
    {"id": "star_delusion", "team": "DAL", "sub": "nfl"},
    {"id": "tundra_tim", "team": "GB", "sub": "nfl"}
]

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    for p in PERSONAS:
        src_path = os.path.join(BASE_DIR, f"{p['id']}.png")
        dest_dir = os.path.join(BASE_DIR, p['sub'])
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, f"{p['id']}.png")
        
        if os.path.exists(src_path):
            print(f"Moving {p['id']}.png to sub-folder: {dest_path}")
            shutil.copy(src_path, dest_path)
            
            # Read and encode
            with open(dest_path, "rb") as f:
                img_bytes = f.read()
            b64_str = base64.b64encode(img_bytes).decode('utf-8')
            data_url = f"data:image/png;base64,{b64_str}"
            
            avatar_url = f"/avatars/{p['sub']}/{p['id']}.png"
            
            # Update DB (avatar_blob, avatar_url) for both persona and sys_user tables
            cur.execute(
                "UPDATE persona SET avatar_blob = ?, avatar_url = ? WHERE user_name = ?",
                (data_url, avatar_url, p['id'])
            )
            cur.execute(
                "UPDATE sys_user SET avatar_url = ? WHERE user_name = ?",
                (avatar_url, p['id'])
            )
            print(f"✅ DB records successfully updated for @{p['id']}! (path: {avatar_url})")
        else:
            print(f"⚠️ Source file not found: {src_path}")
            
    con.commit()
    con.close()
    print("\n🏁 Repathing and DB patch update complete!")

if __name__ == '__main__':
    main()
