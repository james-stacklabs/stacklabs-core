import sqlite3

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
export_path = '/home/james/sovereign_inbox/today/sovereign_personas_export.md'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT user_name, team, cadence, boggs_level, system_prompt, behavior_notes, deep_lore, governance, avatar_url FROM persona ORDER BY user_name")
rows = cursor.fetchall()

with open(export_path, 'w') as f:
    f.write("# Sovereign OS \u2014 AI Personas Export\n\n")
    for row in rows:
        user_name, team, cadence, boggs_level, system_prompt, behavior_notes, deep_lore, governance, avatar_url = row
        
        f.write(f"## {user_name}\n\n")
        
        if avatar_url:
            f.write(f"![{user_name} Avatar]({avatar_url})\n\n")
            
        f.write(f"**Team:** {team or 'N/A'}\n\n")
        f.write(f"**Cadence:** {cadence or 'N/A'}\n\n")
        f.write(f"**Boggs Reactivity:** {boggs_level or 'N/A'}\n\n")
        
        f.write("**System Prompt:**\n```\n")
        f.write((system_prompt or 'N/A') + "\n```\n\n")
        
        f.write("**Behavior Notes:**\n")
        f.write((behavior_notes or 'N/A') + "\n\n")
        
        f.write("**Deep Lore:**\n")
        f.write((deep_lore or 'N/A') + "\n\n")
        
        f.write("**Governance:**\n")
        f.write((governance or 'N/A') + "\n\n")
        
        f.write("---\n\n")

conn.close()
print("Export complete.")
