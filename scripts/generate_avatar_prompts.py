import sqlite3
import os
from google import genai
import time

api_key = os.environ.get("GOOGLE_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)

db_path = "/home/james/stacklabs/dna/sovereign_now.db"
output_file = "/home/james/stacklabs/dna/media/character_maps/MASTER_AVATAR_PROMPTS.md"
os.makedirs(os.path.dirname(output_file), exist_ok=True)
prompts = []

def generate_prompt(name, desc, prompt_text):
    if not api_key or not client:
        desc_fall = str(desc or name)[:100].replace('\n', ' ')
        return f"A cinematic, high-contrast waist-up studio character portrait of {name}, {desc_fall}. Deep Void (#0f1115) background with Vesper Synthwave neon cyan (#00f2fe) rim lighting. Ultra-detailed, 8k resolution."
    lore = f"Name: {name}\nDescription: {desc}\nLore: {prompt_text}"
    sys_prompt = f"Synthesize this character into a 1-sentence physical description (species, vibe, appearance). Return ONLY the physical description text.\n\n{lore}"
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=sys_prompt
        )
        physical_desc = response.text.strip().replace('\n', ' ')
        return f"A cinematic, high-contrast waist-up studio character portrait of {physical_desc}. Deep Void (#0f1115) background with Vesper Synthwave neon cyan (#00f2fe) rim lighting. Ultra-detailed, 8k resolution."
    except Exception:
        return f"A cinematic, high-contrast waist-up studio character portrait of {name}. Deep Void (#0f1115) background with Vesper Synthwave neon cyan (#00f2fe) rim lighting. Ultra-detailed, 8k resolution."

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ci.name, ci.short_description as description, p.u_system_prompt FROM cmdb_ci_ai_persona p JOIN cmdb_ci ci ON p.sys_id = ci.sys_id")
    except sqlite3.OperationalError as e:
        print(f"Error querying: {e}")
        rows = []
    else:
        rows = cursor.fetchall()
    for row in rows:
        name = row['name'] or "Unknown"
        keys = row.keys()
        desc = row['description'] if 'description' in keys else ""
        sys_prompt = row['u_system_prompt'] if 'u_system_prompt' in keys else ""
        final_prompt = generate_prompt(name, desc, sys_prompt)
        prompts.append(f"### {name}\n{final_prompt}\n")
        time.sleep(0.5) 
finally:
    if 'conn' in locals():
        conn.close()

with open(output_file, 'w') as f:
    f.write("# SOVEREIGN OS - MASTER AVATAR PROMPTS\n\n")
    f.write("\n".join(prompts))
