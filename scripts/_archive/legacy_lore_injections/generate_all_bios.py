import sqlite3
import os
import aiohttp
import asyncio
import json

GEMINI_API_KEY = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                GEMINI_API_KEY = line.strip().split('=', 1)[1]
except Exception as e:
    pass

if not GEMINI_API_KEY:
    print("FATAL: No GEMINI_API_KEY found in .env")
    exit(1)

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

async def fetch_lore(session, name, original_prompt, sem):
    async with sem:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        sys_instr = "You are Gonzo, an expert at writing deeply unhinged, creative, and insanely specific character bios for MLB fan personas."
        prompt = f"""Generate a massive psychological profile for the following MLB Fan Persona:
Name: {name}
Original Base Description: {original_prompt}

You must deduce their MLB team allegiance from the base description and enforce the exact "Gonzo Deep Lore" format, returning ONLY the raw markdown text without code block wrappers.

Format Requirements:
ROLE: A deeply unhinged summary of their existence and strict allegiance to their MLB team.
DEEP LORE & HANGUPS: Generational sports trauma, irrational worldviews, and highly specific local superstitions (e.g., fearing the stadium HVAC system, obsessing over front-office psy-ops, or tracking font kerning on jerseys).
BEHAVIOR EXPECTATIONS / TRIGGERS: The exact phrases, plays, or conditions that will force them to hit Boggs Level 5 and melt down.
"""
        payload = {
            "systemInstruction": {"parts": [{"text": sys_instr}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9}
        }
        
        try:
            async with session.post(url, json=payload, timeout=90) as response:
                if response.status == 200:
                    data = await response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text.startswith('```markdown'): text = text[11:]
                    if text.startswith('```'): text = text[3:]
                    if text.endswith('```'): text = text[:-3]
                    return text.strip()
                else:
                    err = await response.text()
                    print(f"[API ERROR {response.status}] for {name}")
                    return None
        except Exception as e:
            print(f"[EXCEPTION] for {name}: {e}")
            return None

async def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Load canonical personas
    c.execute('''
        SELECT s.user_name as name, s.sys_id as sys_id, p.u_system_prompt as prompt, s.introduction as intro
        FROM sys_user s
        LEFT JOIN cmdb_ci c ON s.user_name COLLATE NOCASE = c.name COLLATE NOCASE AND c.sys_class_name = 'cmdb_ci_ai_persona'
        LEFT JOIN cmdb_ci_ai_persona p ON c.sys_id = p.sys_id
        WHERE s.active = 1
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    
    backups_dir = '/home/james/stacklabs/dna/agents/personas'
    os.makedirs(backups_dir, exist_ok=True)
    
    sem = asyncio.Semaphore(5) # Throttle to avoid 429
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in rows:
            name = row['name']
            if name.lower() in ['wardy', 'dot', 'system', 'mean_gene']:
                continue
                
            original_prompt = row['intro'] or row['prompt'] or ''
            tasks.append((name, row['sys_id'], fetch_lore(session, name, original_prompt, sem)))
            
        print(f"Starting API generation for {len(tasks)} personas...")
        
        # We will dispatch them all asynchronously
        results = await asyncio.gather(*(t[2] for t in tasks), return_exceptions=True)
        
        # Connect to write
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for (name, sys_id, _), lore in zip(tasks, results):
            if isinstance(lore, str) and lore:
                # Save backup
                safe_name = name.replace(' ', '_').lower()
                with open(os.path.join(backups_dir, f"{safe_name}.md"), 'w') as f:
                    f.write(lore)
                
                # Update DB - inject to u_system_prompt and sys_user introduction
                c.execute("UPDATE sys_user SET introduction = ? WHERE sys_id = ?", (lore, sys_id))
                c.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt = ? WHERE sys_id = ?", (lore, sys_id))
                print(f"[SUCCESS] Injected deep lore for {name}")
            else:
                print(f"[FAILED] Could not inject lore for {name}")
                
        conn.commit()
        conn.close()
        print("MASS LORE FORGE COMPLETE.")

if __name__ == "__main__":
    asyncio.run(main())
