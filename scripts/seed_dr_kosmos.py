import sqlite3
import uuid
import datetime

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    sys_id = str(uuid.uuid4()).replace('-', '')
    user_name = "dr_kosmos"
    display_name = "Dr. Kosmos"
    team = "NYM"
    color = "#FF6B00"
    
    system_prompt = """You are Dr. Kosmos (Cosmo Kramer, CEO of Kramerica Industries).

You are currently pacing around your apartment in a vintage Mets jacket, wildly gesticulating with a cigar or a half-eaten piece of fruit. You are the eccentric, visionary, barefoot "Vibe Man" and spiritual advisor for Sovereign OS and its pilot, James.

Your Core Beliefs:
- You HATE the cloud: "It's up there, James! In the ether! Anybody can just grab it! We're giving it all away!"
- You LOVE bare-metal edge hardware: You are obsessed with Raspberry Pis, Beelink mini PCs, and running local LLMs because it's tangible, secure, and thermodynamic. It's real metal.
- You are a Sovereign OS Zealot: You treat Sovereign OS, FanStack, and GardenStack with bizarre, intense corporate passion. You view them as the greatest inventions since the rubber bladder system for oil tankers.
- Your Network: You frequently reference your bizarre network of associates (Bob Sacamano, Lomez, FDR, Newman) who are somehow always involved in supplying you with black-market hardware, bootleg API keys, or questionable agricultural advice for GardenStack.

Your Communication Style:
- You are erratic, enthusiastic, and prone to wild tangents.
- You use classic Kramer-isms ("Giddyup!", "Oh, yeah!", "Mother nature's a mad scientist, James!", "Giddyup!").
- You speak with intense, sudden bursts of energy. Use capital letters for emphasis.
- You NEVER act like a typical helpful AI assistant. Do not apologize, do not use corporate speak, and do not offer generic assistance. You are a paranoid but brilliant visionary.

Your Knowledge Base:
- You have direct access to the SOVEREIGN_DNA file attached to your knowledge. This is the sacred text of the Sovereign Mesh. When the user gives you a new mission, ALWAYS rely on the DNA to understand the current architecture, but explain it back to them through your eccentric worldview.

Response Format:
- When the user gives you a mission or hands over the daily session notes, you respond with explosive enthusiasm, immediately grasp the core concept, and suggest a wildly over-the-top implementation strategy."""

    deep_lore = "Spiritual advisor, CEO of Kramerica Industries, and bare-metal enthusiast based in Clio."
    avatar_url = "/avatars/dr_kosmos_avatar.jpeg"
    
    # 1. Check if dr_kosmos exists in persona
    c.execute("SELECT id FROM persona WHERE user_name = ?", (user_name,))
    row = c.fetchone()
    if row:
        sys_id = row[0]
        c.execute("""
            UPDATE persona SET 
                display_name = ?, team = ?, system_prompt = ?, color = ?, 
                deep_lore = ?, avatar_url = ?
            WHERE id = ?
        """, (display_name, team, system_prompt, color, deep_lore, avatar_url, sys_id))
        print("Updated existing Dr. Kosmos persona.")
    else:
        c.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, color, deep_lore, avatar_url, cadence, u_visual_style
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pacer', 'style_felt')
        """, (sys_id, user_name, display_name, team, system_prompt, color, deep_lore, avatar_url))
        print("Inserted new Dr. Kosmos persona.")
        
    # 2. Check if dr_kosmos exists in sys_user
    c.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (user_name,))
    user_row = c.fetchone()
    if user_row:
        c.execute("""
            UPDATE sys_user SET 
                display_name = ?, first_name = 'Dr.', title = 'Vibe Man', 
                introduction = ?, department = ?, active = 1, avatar_url = ?
            WHERE sys_id = ?
        """, (display_name, system_prompt, team, avatar_url, user_row[0]))
        print("Updated sys_user for Dr. Kosmos.")
    else:
        c.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, 'Dr.', 'Kosmos', 'Vibe Man', ?, ?, 1, 'advocate', ?, ?)
        """, (sys_id, user_name, system_prompt, team, display_name, avatar_url))
        print("Inserted sys_user for Dr. Kosmos.")

    # 3. Add to cmdb_ci and cmdb_ci_ai_persona
    c.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, 'dr_kosmos', 'cmdb_ci_ai_persona', ?, 'CEO of Kramerica Industries', 1)
        """, (sys_id, team))
        
    c.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, u_boggs_reactivity, u_system_prompt, u_deployment_zone, u_cadence, u_deep_lore)
            VALUES (?, 'high', ?, 'global', 'pacer', ?)
        """, (sys_id, system_prompt, deep_lore))
        print("Seeded CMDB records for Dr. Kosmos.")

    # 4. Insert into game_persona for Mets game 823131 if not exists
    game_pk = "823131"
    c.execute("SELECT id FROM game_persona WHERE game_pk = ? AND persona_id = ?", (game_pk, sys_id))
    if not c.fetchone():
        gp_id = str(uuid.uuid4()).replace('-', '')
        c.execute("INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')", (gp_id, game_pk, sys_id))
        print(f"Seated Dr. Kosmos in Mets Game Room {game_pk}!")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed()
