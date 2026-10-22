import sqlite3
import json
import uuid
import os
import re

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
AVATAR_MAP_PATH = '/home/james/stacklabs/01_Sovereign_Portal/src/avatarMap.json'
ROSTER_EXPORT_PATH = '/home/james/stacklabs/15_FanStack/public/roster_export.json'

def generate_metadata(key):
    # Base derivation logic for generating realistic records
    key_lower = key.lower()
    
    # Archetype (Title)
    archetype = "Fanatic"
    if any(x in key_lower for x in ['doomer', 'victim', 'sufferer', 'ghost', 'mourner', 'cynic']):
        archetype = "Doomer"
    elif any(x in key_lower for x in ['traitor', 'barf', 'truther', 'instigator', 'bruiser', 'chucker', 'fascist']):
        archetype = "Chaos Agent"
    elif any(x in key_lower for x in ['stan', 'obsessive', 'faithful', 'prophet', 'oracle', 'hoarder']):
        archetype = "Loyalist"
        
    # Toxicity (Department)
    toxicity = "Moderate"
    if archetype == "Doomer":
        toxicity = "Low Energy / Depressed"
    elif archetype == "Chaos Agent":
        toxicity = "Maximum / Aggressive"
    elif archetype == "Loyalist":
        toxicity = "Low / Devoted"
        
    # Name formatting
    formatted_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', key).replace('_', ' ').title()
    name_parts = formatted_name.split()
    first_name = name_parts[0] if name_parts else "Unknown"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Fan"
    
    return first_name, last_name, formatted_name, archetype, toxicity

def main():
    if not os.path.exists(AVATAR_MAP_PATH):
        print(f"Error: {AVATAR_MAP_PATH} not found.")
        return
        
    with open(AVATAR_MAP_PATH, 'r') as f:
        avatar_map = json.load(f)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    export_data = []

    print(f"Ingesting {len(avatar_map)} personas into CMDB tables...")
    
    # Define A-Lister protection keys
    a_listers = ['barf', 'bartman', 'pesky', 'steel_city_sufferer', 'welfare_bucco']
    
    protected_count = 0
    stadium_fallback_count = 0
    
    for key, path in avatar_map.items():
        key_lower = key.lower()
        # Determine sync path: In compliance with the Single Source of Truth Mandate,
        # we write the true mapped asset path to the database.
        sync_path = path
        protected_count += 1
            
        first_name, last_name, format_name, title, department = generate_metadata(key)
        sys_id = str(uuid.uuid4())
        
        # 1. Update/Insert in sys_user table
        cursor.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            db_sys_id = row[0]
            cursor.execute("""
                UPDATE sys_user 
                SET first_name = ?, last_name = ?, title = ?, department = ?, introduction = ?
                WHERE sys_id = ?
            """, (first_name, last_name, title, department, sync_path, db_sys_id))
        else:
            db_sys_id = sys_id
            cursor.execute("""
                INSERT INTO sys_user (sys_id, user_name, first_name, last_name, title, department, introduction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sys_id, key, first_name, last_name, title, department, sync_path))
            
        # 2. Update avatar_url in the persona table to keep perfect alignment
        cursor.execute("""
            UPDATE persona
            SET avatar_url = ?
            WHERE user_name = ? OR user_name = ?
        """, (sync_path, key, key_lower))
            
        export_data.append({
            "sys_id": db_sys_id,
            "user_name": key,
            "display_name": format_name,
            "first_name": first_name,
            "last_name": last_name,
            "archetype": title,
            "toxicity": department,
            "avatar_path": sync_path
        })
        
    conn.commit()
    conn.close()
    
    print(f"Database ingestion complete. Synced: {protected_count}")
    
    with open(ROSTER_EXPORT_PATH, 'w') as f:
        json.dump(export_data, f, indent=4)
        
    print(f"Read-only UI payload exported to {ROSTER_EXPORT_PATH}.")

if __name__ == "__main__":
    main()
