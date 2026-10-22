import sqlite3

db_path = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(db_path)
cur = con.cursor()

# Get Barf's sys_id
cur.execute("SELECT c.sys_id, p.u_system_prompt FROM cmdb_ci_ai_persona p JOIN cmdb_ci c ON c.sys_id = p.sys_id WHERE c.name LIKE '%barf%'")
row = cur.fetchone()
if row:
    sys_id, prompt = row
    append_text = "\n\n[ANTI-LOOP DIRECTIVE]: DO NOT SOUND LIKE A BROKEN RECORD. YOU MUST VARY YOUR RESPONSES. DO NOT repeat the same phrases or rants over and over. React spontaneously to the specific situation and users instead of falling back on your scripted rants."
    if "[ANTI-LOOP DIRECTIVE]" not in prompt:
        new_prompt = prompt + append_text
        cur.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt = ? WHERE sys_id = ?", (new_prompt, sys_id))
        con.commit()
        print("Successfully updated Barf's Persona with Anti-Loop Directive.")
    else:
        print("Directive already present.")

con.close()
