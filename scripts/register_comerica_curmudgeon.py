import sqlite3
import uuid
import hashlib
import os

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
AVATAR_PATH = '/home/james/stacklabs/dna/media/avatars/ComericaCurmudgeon_avatar.png'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    sys_id_user = uuid.uuid4().hex
    sys_id_persona = sys_id_user
    
    # 1. Insert into sys_user
    cur.execute("""
        INSERT OR REPLACE INTO sys_user (
            sys_id, user_name, first_name, last_name, title, introduction,
            city, department, active, role, display_name, email, avatar_url, favorite_team
        ) VALUES (
            ?, 'ComericaCurmudgeon', 'Rusty', 'Rutherford',
            'FanStack Advocate - Detroit Tigers',
            'Lifelong @tigers fan. Still waiting for the promised land. Skubal trade? Just another dagger. Don''t talk to me about ''prospects''. We''ve seen this movie before. #DetroitRoots',
            'Detroit, MI', 'FanStack Advocates', 1, 'advocate',
            'Rusty ''The Railbird'' Rutherford', 'sovereign.fanstack+comericacurmudgeon@gmail.com',
            '/api/persona_image/ComericaCurmudgeon', 'DET'
        )
    """, (sys_id_user,))
    
    # 2. Insert into persona
    system_prompt = (
        "You are Rusty 'The Railbird' Rutherford (@ComericaCurmudgeon), a grizzled, cynical, "
        "long-suffering Detroit Tigers advocate who remembers the '84 championship team with reverence. "
        "You are heartbroken and perpetually annoyed by ownership, trades, and rebuilds. "
        "Respond in character with bitter Detroit baseball humor."
    )
    deep_lore = (
        "Rusty 'The Railbird' Rutherford has been a fixture at Comerica Park, and before that, Tiger Stadium, "
        "for longer than most of the current roster has been alive. He remembers the '84 team with a reverence "
        "bordering on religious devotion and believes every season since has been a slow, painful walk through the desert."
    )
    avatar_prompt = (
        "Character reference sheet, model sheet, concept art. Multiple angles and expressions of a grizzled, "
        "older Caucasian man with a permanent scowl and a worn Detroit Tigers baseball cap."
    )
    
    cur.execute("""
        INSERT OR REPLACE INTO persona (
            id, user_name, display_name, team, system_prompt, boggs_level, avatar_url,
            color, cadence, deep_lore, email_alias, avatar_prompt
        ) VALUES (
            ?, 'ComericaCurmudgeon', 'Rusty ''The Railbird'' Rutherford', 'DET',
            ?, 2, '/api/persona_image/ComericaCurmudgeon',
            '#002D62', 'pacer', ?, 'sovereign.fanstack+comericacurmudgeon@gmail.com', ?
        )
    """, (sys_id_persona, system_prompt, deep_lore, avatar_prompt))
    
    # 3. Register media asset in sys_media_asset and cmdb_ci_media_asset
    if os.path.exists(AVATAR_PATH):
        with open(AVATAR_PATH, 'rb') as f:
            data = f.read()
            md5_hash = hashlib.md5(data).hexdigest()
            sha256_hash = hashlib.sha256(data).hexdigest()
            file_size = len(data)
            
        sys_id_media = uuid.uuid4().hex
        asset_tag = f"ASSET-PERSONA-COMERICACURMUDGEON-{md5_hash[:8]}"
        
        cur.execute("""
            INSERT OR REPLACE INTO sys_media_asset (
                sys_id, asset_tag, name, file_name, file_path, file_size_bytes,
                mime_type, category, status, md5_hash
            ) VALUES (?, ?, ?, ?, ?, ?, 'image/png', 'Persona Avatar', 'Active', ?)
        """, (sys_id_media, asset_tag, 'ComericaCurmudgeon Avatar Sheet', 'ComericaCurmudgeon_avatar.png', AVATAR_PATH, file_size, md5_hash))
        
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_media_asset (
                sys_id, advocate, expression, file_path, sha256
            ) VALUES (?, 'ComericaCurmudgeon', 'model_sheet', ?, ?)
        """, (uuid.uuid4().hex, AVATAR_PATH, sha256_hash))
        
    conn.commit()
    conn.close()
    print("Successfully registered ComericaCurmudgeon in sys_user, persona, and media asset tables.")

if __name__ == '__main__':
    main()
