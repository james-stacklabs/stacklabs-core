import sqlite3
import json
import os

# Update Database
db_path = '/home/james/stacklabs/dna/sovereign_now.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE persona SET team='AZ' WHERE team='ARI'")
    # Some legacy columns might exist
    try:
        c.execute("UPDATE persona SET assigned_team='AZ' WHERE assigned_team='ARI'")
    except: pass
    c.execute("UPDATE mlb_schedule SET home_team='AZ' WHERE home_team='ARI'")
    c.execute("UPDATE mlb_schedule SET away_team='AZ' WHERE away_team='ARI'")
    conn.commit()
    conn.close()
    print("Database updated.")

# Update JSON files
json_files = [
    '/home/james/stacklabs/01_Sovereign_Portal/public/mlb_schedule_2026.json',
    '/home/james/stacklabs/01_Sovereign_Portal/public/personas.json',
    '/home/james/stacklabs/01_Sovereign_Portal/src/data/mlb_schedule_2026.json',
    '/home/james/stacklabs/01_Sovereign_Portal/src/data/personas.json'
]

for jf in json_files:
    if os.path.exists(jf):
        with open(jf, 'r') as f:
            content = f.read()
        # Replace strictly whole words or specific patterns
        content = content.replace('"ARI"', '"AZ"')
        content = content.replace('"team": "ARI"', '"team": "AZ"')
        content = content.replace('"home_team": "ARI"', '"home_team": "AZ"')
        content = content.replace('"away_team": "ARI"', '"away_team": "AZ"')
        with open(jf, 'w') as f:
            f.write(content)
        print(f"Updated {jf}")

print("Done fixing ARI -> AZ")
