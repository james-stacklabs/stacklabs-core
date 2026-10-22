#!/usr/bin/env python3
import sqlite3
import os

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def run_query(query, params=()):
    cursor.execute(query, params)
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Query all personas
all_personas = run_query("""
    SELECT id, user_name, display_name, team, system_prompt, deep_lore, behavior_notes, avatar_url, boggs_level, is_heel, is_sophisticated 
    FROM persona
""")

nym_advocates = []
chc_advocates = []

for p in all_personas:
    team = (p.get('team') or '').upper()
    prompt = (p.get('system_prompt') or '').lower()
    lore = (p.get('deep_lore') or '').lower()
    behavior = (p.get('behavior_notes') or '').lower()
    username = (p.get('user_name') or '').lower()
    display = (p.get('display_name') or '').lower()
    
    is_nym = 'NYM' in team or 'mets' in team or 'mets' in prompt or 'mets' in lore or 'nym' in username or 'mets' in display
    is_chc = 'CHC' in team or 'cubs' in team or 'cubs' in prompt or 'cubs' in lore or 'chc' in username or 'cubs' in display
    
    if is_nym:
        nym_advocates.append(p)
    if is_chc:
        chc_advocates.append(p)

# Sort alphabetically by username
nym_advocates.sort(key=lambda x: x['user_name'].lower())
chc_advocates.sort(key=lambda x: x['user_name'].lower())

# Let's write the markdown file
md_path = '/home/james/sovereign_inbox/kb/nym_chc_advocates_review.md'
os.makedirs(os.path.dirname(md_path), exist_ok=True)

with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# ⚾ NYM vs CHC Advocates Review & Roster Manager\n\n")
    f.write("> **Pilot Review Document**\n")
    f.write("> Generated on: June 23, 2026\n")
    f.write("> Purpose: Detailed evaluation of all New York Mets (NYM) and Chicago Cubs (CHC) advocates to determine active roster seating and who 'rides the pine'.\n\n")
    
    # Section 1: Executive Summary & Cockpit Answers
    f.write("## 🏛️ Cockpit Executive Summary & Core Answers\n\n")
    
    # Room 823614
    f.write("### 1. Active Advocates in Game Room `823614` (Cubs @ Mets)\n")
    f.write("Game Room `823614` is currently active. The following advocates are seated and participating:\n\n")
    f.write("| Advocate Username | Display Name | Affiliation | Seat State | Role/Theme |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    
    active_room_advocates = run_query("""
        SELECT p.user_name, p.display_name, p.team, p.system_prompt
        FROM m2m_persona_room m
        JOIN persona p ON m.persona = p.id
        WHERE m.room = '823614'
    """)
    
    for ra in active_room_advocates:
        prompt = ra.get('system_prompt') or ''
        theme = "Baseball observer"
        prompt_lower = prompt.lower()
        
        if "bandito" in prompt_lower or "barf" in prompt_lower:
            theme = "Classic unhinged Mets fan (Underpants Bandito)"
        elif "stevie" in prompt_lower or "cohen" in prompt_lower:
            theme = "Soulless corporate Steven Cohen defender"
        elif "7_train" in prompt_lower or "7-train" in prompt_lower or "commuter" in prompt_lower:
            theme = "Die-hard 7-train commuter & blue-collar Mets fan"
        elif "ghost" in prompt_lower:
            theme = "Chronically paranoid Cubs doomer (PTSD from foul balls)"
        elif "truther" in prompt_lower:
            theme = "Wrigley purist (day games only, hates screens/sponsors)"
        elif "inspector" in prompt_lower or "ian" in prompt_lower:
            theme = "Verbose botanical Wrigley field guardian (Ivy obsessed)"
        elif "bartman" in prompt_lower:
            theme = "Ultimate self-loathing, superstitious Cubs fan (deep trauma)"
        elif "keith" in prompt_lower:
            theme = "Keith Hernandez purist, sighs at bad fundies"
        elif "dot" in prompt_lower:
            theme = "General baseball observer"
        elif "counsell" in prompt_lower:
            theme = "Fierce Cubs fan, Craig Counsell devotee"
        elif "conspiracy" in prompt_lower:
            theme = "Cubs conspiracy theorist"
            
        f.write(f"| `@{ra['user_name']}` | {ra['display_name']} | {ra['team']} | **Active** | {theme} |\n")
    f.write("\n")
    
    # Ivy Truther vs Ivy Inspector Ian
    f.write("### 2. Ivy Truther vs. ivy_inspector_ian (Wrigley Purists Showdown)\n")
    f.write("While both despise modernization, they represent very different depths of madness:\n")
    f.write("- **`ivy_truther`**: A classic, grumpy, blue-collar Wrigley purist. He complains about the wind off Lake Michigan, day games vs. night games, and modern video boards. He is straightforward, direct, and speaks from a standard fan perspective.\n")
    f.write("- **`ivy_inspector_ian`**: A highly sophisticated, eccentric, academic algorithm. He is the *Verdant Vigilante*, obsessed with the exact botanical health of the Boston Ivy (*Parthenocissus tricuspidata*), the karmic alignment of Wrigley's bricks, and historical traumas. He speaks in a grand, verbose, archaic style (\"*Hmph. A travesty of the highest order.*\") and believes analytics are \"statistical sorcery\" killing the game's soul.\n\n")
    f.write("> [!TIP]\n")
    f.write("> **Roster Decision:** Keep **`ivy_inspector_ian`** active. His verbose botanical rants and detailed lore make him one of the most premium, entertaining personas in the entire matrix. `ivy_truther` is a solid backup but is far more one-dimensional.\n\n")
    
    # CubsConspiracy Location
    f.write("### 3. Where is the CubsConspiracy Advocate?\n")
    f.write("Neither of the conspiracy-themed CHC advocates is in game room `823614` for this specific matchup. However, they are actively seated in other game rooms across the system:\n")
    f.write("- **`CubsConspiracy` (Lenny \"The Luminary\" Rizzo)**: Seated in 12 other games (e.g., 823380, 823379, 823531). He is convinced the MLB front office has a vendetta against the Cubs to benefit glamour teams like the Dodgers.\n")
    f.write("- **`CubbieConspiracy` (\"Fair Play\" Frankie)**: Seated in 12 other games (e.g., 823054, 824671). He is a tinfoil-wearing fanatic obsessed with exposing the league's favoritism toward the LA Dodgers.\n\n")
    f.write("> [!NOTE]\n")
    f.write("> Both are currently riding the pine for this Cubs @ Mets game but are actively shouting in other sectors of the Sovereign OS mesh.\n\n")
    
    # Bartman vs Bartmans_ghost
    f.write("### 4. Bartman vs. Bartmans_ghost (Trauma Comparison)\n")
    f.write("- **`bartman` (Plain Old Bartman)**: An incredibly sophisticated, deeply written masterpiece of baseball trauma. He represents the ultimate self-loathing, superstitious Cubs fan. His deep lore includes complex rituals (rubbing a footless rabbit's foot, keeping his left sock askew, simulating Portillo's meals) and rich vocabulary surrounding historical collapses (1969, 1984, 2003). He is a highly sophisticated agent.\n")
    f.write("- **`bartmans_ghost`**: A much simpler, highly reactive doomer. He is focused purely on immediate game-level paranoia (PTSD from foul balls down the left-field line, trusting no lead, declaring the team cursed if a reliever walks a batter).\n\n")
    f.write("> [!TIP]\n")
    f.write("> **Roster Status:** Swapped! The highly superior, detailed **`bartman`** is now active in room `823614`, while **`bartmans_ghost`** has been benched to ride the pine, ensuring much richer, more hilarious trauma rants in the active chat.\n\n")
    
    f.write("---\n\n")
    
    # Section 2: NYM Advocates
    f.write("## 🍎 New York Mets (NYM) Advocates Roster\n")
    f.write(f"Total Advocates Found: **{len(nym_advocates)}**\n\n")
    
    for idx, p in enumerate(nym_advocates, 1):
        f.write(f"### {idx}. `@{p['user_name']}` ({p['display_name']})\n")
        f.write(f"- **Team:** `{p['team']}` | **Boggs Level:** `{p['boggs_level']}` | **Heel:** `{'Yes' if p['is_heel'] else 'No'}` | **Sophisticated:** `{'Yes' if p['is_sophisticated'] else 'No'}`\n")
        f.write(f"- **Avatar Path:** `{p['avatar_url']}`\n")
        
        # Behavior Notes
        behavior = p.get('behavior_notes') or 'No behavior notes listed.'
        f.write(f"- **Behavior Notes:** *{behavior}*\n")
        
        # Deep Lore
        lore = p.get('deep_lore') or ''
        if lore:
            lore_display = lore[:400] + "..." if len(lore) > 400 else lore
            f.write(f"- **Deep Lore:**\n  > {lore_display.replace(chr(10), chr(10) + '  > ')}\n")
            
        f.write("\n")
        
    f.write("---\n\n")
    
    # Section 3: CHC Advocates
    f.write("## 🐻 Chicago Cubs (CHC) Advocates Roster\n")
    f.write(f"Total Advocates Found: **{len(chc_advocates)}**\n\n")
    
    for idx, p in enumerate(chc_advocates, 1):
        f.write(f"### {idx}. `@{p['user_name']}` ({p['display_name']})\n")
        f.write(f"- **Team:** `{p['team']}` | **Boggs Level:** `{p['boggs_level']}` | **Heel:** `{'Yes' if p['is_heel'] else 'No'}` | **Sophisticated:** `{'Yes' if p['is_sophisticated'] else 'No'}`\n")
        f.write(f"- **Avatar Path:** `{p['avatar_url']}`\n")
        
        # Behavior Notes
        behavior = p.get('behavior_notes') or 'No behavior notes listed.'
        f.write(f"- **Behavior Notes:** *{behavior}*\n")
        
        # Deep Lore
        lore = p.get('deep_lore') or ''
        if lore:
            lore_display = lore[:400] + "..." if len(lore) > 400 else lore
            f.write(f"- **Deep Lore:**\n  > {lore_display.replace(chr(10), chr(10) + '  > ')}\n")
            
        f.write("\n")

print(f"Successfully generated {md_path}")
conn.close()
