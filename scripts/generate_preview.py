import sqlite3
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv('/home/james/stacklabs/.env')

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found.")
    exit(1)

client = genai.Client(api_key=api_key)

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Get examples
examples = cur.execute("SELECT user_name, system_prompt, behavior_notes, governance FROM persona WHERE user_name IN ('dot', 'wordy', '7_train_terry', 'battery_chucker', 'mrs_met_simper')").fetchall()

example_text = "Here are examples of HIGH QUALITY persona definitions:\n\n"
for ex in examples:
    example_text += f"USER_NAME: {ex['user_name']}\n"
    example_text += f"SYSTEM_PROMPT: {ex['system_prompt']}\n"
    example_text += f"BEHAVIOR_EXPECTATIONS: {ex['behavior_notes']}\n"
    example_text += f"GOVERNANCE_BOUNDARIES: {ex['governance']}\n"
    example_text += "-"*40 + "\n"

# Get target personas for preview
targets = cur.execute("""
    SELECT user_name, team, deep_lore 
    FROM persona 
    WHERE user_name NOT IN ('dot', 'wordy', 'taylor_word', '7_train_terry', 'battery_chucker', 'mrs_met_simper', 'mean_gene', 'slopematrix_gj', 'the_traditionalist', 'the_gambler', 'the_breakfast_specialist', 'the_defector', 'coach_shrubbs', 'cap_peterson')
    AND team != '' AND team IS NOT NULL
    LIMIT 5
""").fetchall()

print(f"Generating preview for {len(targets)} personas...")

preview_md = "# Fresh Personas Preview\n\n"

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

for target in targets:
    prompt = f"""
    Please generate the 3 fields for the following persona:
    USER_NAME: {target['user_name']}
    TEAM: {target['team']}
    SHORT DEEP LORE: {target['deep_lore']}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
            )
        )
        
        data = json.loads(response.text)
        
        preview_md += f"## {target['user_name']} (Team: {target['team']})\n\n"
        preview_md += f"### System Prompt\n{data.get('system_prompt', '')}\n\n"
        preview_md += f"### Behavior Expectations\n{data.get('behavior_notes', '')}\n\n"
        preview_md += f"### Governance Boundaries\n{data.get('governance', '')}\n\n"
        preview_md += "---\n\n"
        
        print(f"Generated {target['user_name']}")
        
    except Exception as e:
        print(f"Error generating {target['user_name']}: {e}")

with open('/home/james/sovereign_inbox/daily_05112026/fresh_personas_preview.md', 'w') as f:
    f.write(preview_md)

print("Preview written to /home/james/sovereign_inbox/daily_05112026/fresh_personas_preview.md")
