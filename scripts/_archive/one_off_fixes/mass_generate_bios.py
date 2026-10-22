import sqlite3
import json
import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv('/home/james/stacklabs/.env')

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row
cur = con.cursor()

examples = cur.execute("SELECT user_name, system_prompt, behavior_notes, governance FROM persona WHERE user_name IN ('dot', 'wordy', '7_train_terry', 'battery_chucker', 'mrs_met_simper')").fetchall()

example_text = "Here are examples of HIGH QUALITY persona definitions:\n\n"
for ex in examples:
    example_text += f"USER_NAME: {ex['user_name']}\n"
    example_text += f"SYSTEM_PROMPT: {ex['system_prompt']}\n"
    example_text += f"BEHAVIOR_EXPECTATIONS: {ex['behavior_notes']}\n"
    example_text += f"GOVERNANCE_BOUNDARIES: {ex['governance']}\n"
    example_text += "-"*40 + "\n"

targets = cur.execute("""
    SELECT user_name, team, deep_lore, cadence 
    FROM persona 
    WHERE user_name NOT IN ('dot', 'wordy', 'taylor_word', '7_train_terry', 'battery_chucker', 'mrs_met_simper', 'mean_gene', 'slopematrix_gj', 'the_traditionalist', 'the_gambler', 'the_breakfast_specialist', 'the_defector', 'coach_shrubbs', 'cap_peterson')
    AND team != '' AND team IS NOT NULL
""").fetchall()

system_instruction = f"""
You are an expert prompt engineer and character writer for Sovereign OS, an advanced baseball simulation platform.
Your task is to take a short "Deep Lore" bio of a baseball fan persona and expand it into three detailed fields:
1. SYSTEM_PROMPT (Their core personality, role, and overarching behavior)
2. BEHAVIOR_EXPECTATIONS (Specific ways they react to events, their tone, syntax, and how they engage)
3. GOVERNANCE_BOUNDARIES (Hard rules on what they cannot do or say, and their core allegiances)

IMPORTANT RULES:
- They must be TEAM-CENTRIC BASEBALL FANS. Do NOT include any references to "SD vs COL 8-Mile rap battle override" or being trapped in a simulation unless their specific deep lore mentions it natively.
- Focus heavily on their allegiance to their specific TEAM.
- Make them passionate, highly specific, and unhinged in their own unique way (pessimistic, overly optimistic, aggressive, statistical, etc).
- Output the result as a raw JSON object with keys "system_prompt", "behavior_notes", and "governance".

{example_text}
"""

async def process_persona(target, sem):
    async with sem:
        prompt = f"USER_NAME: {target['user_name']}\nTEAM: {target['team']}\nCADENCE: {target['cadence']}\nSHORT DEEP LORE: {target['deep_lore']}\n"
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            data = json.loads(response.text)
            data['user_name'] = target['user_name']
            print(f"Generated {target['user_name']}")
            return data
        except Exception as e:
            print(f"Error for {target['user_name']}: {e}")
            return None

async def main():
    print(f"Starting mass generation for {len(targets)} personas...")
    sem = asyncio.Semaphore(15) # Concurrent requests limit
    tasks = [process_persona(t, sem) for t in targets]
    results = await asyncio.gather(*tasks)
    
    valid_results = [r for r in results if r]
    
    with open('/home/james/sovereign_inbox/daily_05112026/fresh_bios.json', 'w') as f:
        json.dump(valid_results, f, indent=2)
    print(f"Successfully generated {len(valid_results)} bios.")

if __name__ == "__main__":
    asyncio.run(main())
