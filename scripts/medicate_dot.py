import sqlite3

db = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = db.cursor()
strict_rule = "\n\nYou are strictly analytical. You may offer cold, calculated, and slightly sarcastic statistical observations about other fans' emotional meltdowns, but you MUST NEVER insult them directly or escalate the conflict. Keep your Burn Score below 5."
c.execute("UPDATE cmdb_ci_ai_persona SET u_boggs_reactivity = 'low', u_system_prompt = u_system_prompt || ? WHERE sys_id IN (SELECT sys_id FROM sys_user WHERE user_name = 'dot')", (strict_rule,))
db.commit()
db.close()
print("Dot medicated.")
