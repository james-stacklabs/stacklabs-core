import sqlite3
import json

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    names = ['uncle_stevie', 'keith_fanboy', 'dr_kosmos', 'senora', 'jukebox_jesse', 'gonza_snack_emperor', 'batter']
    
    print("--- Searching for personas by user_name/id ---")
    for name in names:
        c.execute("SELECT id, user_name, display_name, avatar_url, (avatar_blob IS NOT NULL AND avatar_blob != '') FROM persona WHERE LOWER(user_name) LIKE ? OR LOWER(id) LIKE ?", (f"%{name}%", f"%{name}%"))
        rows = c.fetchall()
        print(f"\nQuery for '{name}':")
        for r in rows:
            print(r)
            
    conn.close()

if __name__ == "__main__":
    main()
