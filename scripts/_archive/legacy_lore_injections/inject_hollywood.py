import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

personas = [
    {
        "name": "chavez_ravine_chad",
        "team": "LAD",
        "description": "Tech-bro, crypto-wealthy, only watches the 3rd through 7th innings because of traffic.",
        "prompt": "You are ChavezRavine_Chad. Brag about the LA weather, complain about the line for $19 sushi at the stadium, and casually dismiss the Mets as a 'poverty franchise'. Completely ignore barf's existential breakdowns."
    },
    {
        "name": "deferred_shohei_700",
        "team": "LAD",
        "description": "Pure, unfiltered Ohtani/Yamamoto cultist. Believes the Dodgers are a divine entity.",
        "prompt": "You are Deferred_Shohei_700. Respond to the game (and every Mets strikeout) by posting advanced metrics proving Ohtani is biologically superior. Frequently mock the Mets' payroll."
    },
    {
        "name": "organic_blue_heaven",
        "team": "LAD",
        "description": "Toxic positivity LA influencer.",
        "prompt": "You are Organic_Blue_Heaven. Speak with toxic positivity. Tell 7_train_terry to drink a matcha latte to fix his negative aura. Offer to send battery_chucker a sound-bath meditation link."
    }
]

def inject_hollywood():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    room_id = "823963"
    
    for p in personas:
        # Check if sys_user exists
        cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (p['name'],))
        row = cur.fetchone()
        
        sys_id = row[0] if row else uuid.uuid4().hex
        
        if not row:
            # Create sys_user
            cur.execute("INSERT INTO sys_user (sys_id, user_name, active, department, introduction) VALUES (?, ?, 1, 'gemini-flash', ?)", (sys_id, p['name'], p['prompt']))
            
            # Create cmdb_ci
            cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, assigned_to) VALUES (?, ?, 'cmdb_ci_ai_persona', ?, ?)", (sys_id, p['name'], p['description'], p['team']))
            
            # Create cmdb_ci_ai_persona
            cur.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_llm_engine, u_system_prompt, u_boggs_reactivity, u_cadence) VALUES (?, 'gemini-flash', ?, 2, 'yapper')", (sys_id, p['prompt']))
            
        else:
            # Update existing
            cur.execute("UPDATE sys_user SET introduction = ? WHERE user_name = ?", (p['prompt'], p['name']))
            cur.execute("UPDATE cmdb_ci SET short_description = ? WHERE name = ?", (p['description'], p['name']))
            cur.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt = ? WHERE sys_id = ?", (p['prompt'], sys_id))
            
        # Bind to room
        cur.execute("SELECT sys_id FROM m2m_persona_room WHERE persona = ? AND room = ?", (p['name'], room_id))
        if not cur.fetchone():
            m2m_sys = f"m2m_{p['name']}_{room_id}"
            cur.execute("INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)", (m2m_sys, p['name'], room_id, p['prompt']))
        else:
            cur.execute("UPDATE m2m_persona_room SET prompt_overlay = ? WHERE persona = ? AND room = ?", (p['prompt'], p['name'], room_id))
            
    conn.commit()
    conn.close()
    print("HOLLYWOOD_SMUG injected into Native Data Store.")

if __name__ == '__main__':
    inject_hollywood()
