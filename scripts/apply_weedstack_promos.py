#!/usr/bin/env python3
import os
import sqlite3
import subprocess
import uuid
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    print("⚡ Starting WeedStack Promos Application & Mapping...")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cursor = con.cursor()

    # 1. Ensure SDLC ticket ENHC0000520 exists
    ticket_num = "ENHC0000520"
    cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number=?", (ticket_num,))
    row = cursor.fetchone()
    
    if not row:
        print(f"🌱 Inserting SDLC ticket {ticket_num} into database...")
        sys_id = str(uuid.uuid4())
        short_desc = "WeedStack Chat Persona Product Pitch & Bullpen Meltdown Deal Integration"
        desc = ("Enhance WeedStack persona system prompts to instruct them to proactively "
                "pitch products and promote the 50% off edibles deal when the Mets bullpen collapses, "
                "creating high-fidelity, interactive fan stress simulation reactions in the chat stream.")
        work_notes = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Automated Onboarding Initialization:\n- State: In Progress\n- Owner: Antigravity\n"
        con.execute("""
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, work_notes)
            VALUES (?, ?, 'ENHC', ?, ?, 2, 3, 'Antigravity', ?)
        """, (sys_id, ticket_num, short_desc, desc, work_notes))
        con.commit()
    else:
        print(f"🔄 SDLC ticket {ticket_num} already exists, ensuring state is In Progress (2)...")
        con.execute("UPDATE sovereign_tickets SET state=2 WHERE number=?", (ticket_num,))
        con.commit()

    con.close()

    # 2. Run seed_weedstack_personas.py to update database values
    print("⚙️ Executing seed_weedstack_personas.py...")
    cmd = ["/home/james/stacklabs/.venv/bin/python3", "/home/james/stacklabs/scripts/seed_weedstack_personas.py"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Error executing seeding script:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        return
    print("✅ seed_weedstack_personas.py executed successfully!")

    # 3. Map WeedStack personas to game room 823623
    game_room = "823623"
    print(f"🔗 Mapping all WeedStack personas to game room {game_room}...")
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()

    # Fetch WeedStack persona IDs
    cursor.execute("SELECT id, user_name FROM persona WHERE team='WEEDSTACK'")
    personas = cursor.fetchall()
    
    # Clean out any existing mapping of these personas to game room 823623 first to prevent duplicates
    for p_id, user_name in personas:
        cursor.execute("DELETE FROM m2m_persona_room WHERE persona=? AND room=?", (p_id, game_room))
        cursor.execute("DELETE FROM game_persona WHERE persona_id=? AND game_pk=?", (p_id, game_room))
        
        # Insert fresh mapping in m2m_persona_room
        m2m_sys_id = str(uuid.uuid4()).replace('-', '')
        overlay = f"Current Matchup Context: Deployed to Game {game_room} (MIA @ NYM)."
        cursor.execute("""
            INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay)
            VALUES (?, ?, ?, ?)
        """, (m2m_sys_id, p_id, game_room, overlay))

        # Insert fresh mapping in game_persona
        gp_sys_id = str(uuid.uuid4()).replace('-', '')
        cursor.execute("""
            INSERT INTO game_persona (id, game_pk, persona_id, overlay, seat_state)
            VALUES (?, ?, ?, ?, 'active')
        """, (gp_sys_id, game_room, p_id, overlay))
        print(f"  Mapped @{user_name} (ID: {p_id[:8]}...) to Room {game_room} (both m2m_persona_room & game_persona)")

    con.commit()
    con.close()
    print("🎉 All steps executed successfully! WeedStack personas are seeded and active in scruffys!")

if __name__ == "__main__":
    main()
