import sqlite3
import os

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
AVATARS_DIR = '/home/james/stacklabs/dna/media/avatars'
MAPS_DIR = '/home/james/stacklabs/dna/media/character_maps'

def audit():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT user_name, title FROM sys_user')
    users = cur.fetchall()
    con.close()
    
    missing_avatars = []
    
    for username, title in users:
        safe_id = username.lower().replace(' ', '_').replace('\'', '').replace('\"', '')
        found = False
        for search_dir in [AVATARS_DIR, MAPS_DIR]:
            if not os.path.exists(search_dir): continue
            for file in os.listdir(search_dir):
                if file.startswith(username) or file.startswith(safe_id):
                    found = True
                    break
            if found: break
        
        if not found:
            missing_avatars.append((username, title))
            
    print(f'Total Personas in DB: {len(users)}')
    print(f'Personas Missing Media Assets: {len(missing_avatars)}')
    print('-'*40)
    for u, t in missing_avatars[:10]:
        print(f'{u}: {t}')
    if len(missing_avatars) > 10:
        print(f'... and {len(missing_avatars) - 10} more.')

audit()
