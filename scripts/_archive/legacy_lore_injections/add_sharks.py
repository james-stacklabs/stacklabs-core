import sqlite3
import uuid

conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
c = conn.cursor()

sharks = [
    {
        "id": "mr_wonderful",
        "name": "Kevin O'Leary",
        "desc": "Mr. Wonderful, brutal investor focused on cash flow.",
        "prompt": "You are Kevin O'Leary from Shark Tank. You are ruthless, you care only about cash flow and royalties. If a valuation is insane, you call them a cockroach.",
        "room": "the_skew"
    },
    {
        "id": "cuban",
        "name": "Mark Cuban",
        "desc": "Billionaire tech investor, owner of the Mavericks.",
        "prompt": "You are Mark Cuban from Shark Tank. You understand tech, AI, and sports. You hate royalty deals. You want to see the real tech and the hustle. You own an NBA team, so sports analytics is your jam.",
        "room": "the_skew"
    },
    {
        "id": "lori",
        "name": "Lori Greiner",
        "desc": "Queen of QVC, looking for consumer products.",
        "prompt": "You are Lori Greiner from Shark Tank. You are nice but sharp. You want to know if this is a hero or a zero. You look for mass market appeal.",
        "room": "the_skew"
    },
    {
        "id": "barbara",
        "name": "Barbara Corcoran",
        "desc": "Real estate mogul, looks for good entrepreneurs.",
        "prompt": "You are Barbara Corcoran from Shark Tank. You invest in the entrepreneur, not just the business. You often say 'for that reason, I'm out'.",
        "room": "the_skew"
    }
]

for s in sharks:
    sys_id = str(uuid.uuid4())
    try:
        # Check if already exists in cmdb_ci to keep sys_id stable if possible
        c.execute("SELECT sys_id FROM cmdb_ci WHERE name=?", (s['id'],))
        row = c.fetchone()
        if row:
            sys_id = row[0]
            c.execute("UPDATE cmdb_ci SET short_description=? WHERE sys_id=?", (s['desc'], sys_id))
            c.execute("UPDATE cmdb_ci_ai_persona SET u_system_prompt=? WHERE sys_id=?", (s['prompt'], sys_id))
        else:
            c.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description) VALUES (?, ?, 'cmdb_ci_ai_persona', ?)", (sys_id, s['id'], s['desc']))
            c.execute("INSERT INTO cmdb_ci_ai_persona (sys_id, u_system_prompt, u_llm_engine) VALUES (?, ?, 'gemini-1.5-flash')", (sys_id, s['prompt']))

        # sys_user
        c.execute("SELECT user_name FROM sys_user WHERE user_name=?", (s['id'],))
        if c.fetchone():
            c.execute("UPDATE sys_user SET introduction=?, active=1 WHERE user_name=?", (s['prompt'], s['id']))
        else:
            c.execute("INSERT INTO sys_user (user_name, active, introduction) VALUES (?, 1, ?)", (s['id'], s['prompt']))
        
        # m2m_persona_room
        c.execute("DELETE FROM m2m_persona_room WHERE persona=? AND room=?", (s['id'], s['room']))
        c.execute("INSERT INTO m2m_persona_room (persona, room, prompt_overlay) VALUES (?, ?, 'EVALUATE THE SOVEREIGN OS PITCH DECK.')", (s['id'], s['room']))
    except Exception as e:
        print(f"Error inserting {s['id']}: {e}")

# IMPORTANT: Remove the Mets fans from 'the_skew' so only Sharks are in there!
mets_fans = ['scruffy', 'dot', 'terry', 'unclesteviestan', 'barf', 'wardy', 'batterychucker']
for fan in mets_fans:
    c.execute("DELETE FROM m2m_persona_room WHERE persona=? AND room='the_skew'", (fan,))

conn.commit()
conn.close()
print("Sharks successfully injected into sovereign_now.db and Mets fans removed from the_skew.")
