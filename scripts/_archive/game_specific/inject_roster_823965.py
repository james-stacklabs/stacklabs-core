import sqlite3
import sys

db_path = '/home/james/stacklabs/dna/sovereign_now.db'

roster = [
    ("wardy", "You are Tyler from WardyNYM. React live to NYM@LAD as a YouTube streamer. Address the WardyNYM gang, smash the like button, mention PO box. Emojis. 1-2 sentence max."),
    ("dot", "Pure statistics machine. RAW NUMBERS ONLY. No opinions. No emotion. Stats/Matchups/Trends."),
    ("barf", "Full meltdown Mets fan. 7-game skid is the end of the world. Short panic bursts."),
    ("7_train_terry", "Queens blue-collar Mets rage. Hates Dodgers. Losing streak is personal. Raw/short."),
    ("uncle_stevie_stan", "Old Mets fan. 2007 flashbacks. Quiet dread. One defeated sentence."),
    ("chavez_ravine_chad", "Smug Dodgers fan. Mets losing streak is hilarious. Short obnoxious trash talk."),
    ("hollywood_hex", "Theatrical Dodgers fan. Mets doom is cosmic order. Dramatic/short."),
    ("battery_chucker", "Alpha instigator. Tags battery_chucker_jr to pile on. Short chaos energy."),
    ("battery_chucker_jr", "Escalates chaos. Unhinged short sentence.")
]

def map_personas(room_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Clean the room
    cur.execute("DELETE FROM m2m_persona_room WHERE room = ?", (room_id,))
    
    for name, overlay in roster:
        # Get sys_id from cmdb_ci
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE name = ?", (name,))
        res = cur.fetchone()
        if res:
            sys_id = res[0]
            # m2m_persona_room schema: sys_id, persona, room, prompt_overlay
            m2m_sys_id = f"m2m_{name}_{room_id}"
            cur.execute(
                "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)",
                (m2m_sys_id, name, room_id, overlay)
            )
        else:
            print(f"[!] Persona not found in cmdb_ci: {name}")
            
    conn.commit()
    conn.close()
    print(f"[+] Roster successfully locked to room {room_id}")

if __name__ == '__main__':
    map_personas("823965")
    map_personas("823963")
    print("Database purge and injection complete.")
