import sqlite3
import uuid
import sys

def seed_room():
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    game_pk = "823610"
    print(f"Targeting game room {game_pk} (NYM @ PHI)...")

    # 1. 11-Advocate Roster Mapping
    advocates = [
        {"id": "c7d45693c3ec4c88806bb20a1b3b1553", "username": "barf", "role": "Mets Anchor"},
        {"id": "36a95ce498bc42a999ce5747eb981aa4", "username": "7_train_terry", "role": "Mets Anchor"},
        {"id": "persona_2008_ghost", "username": "2008_ghost", "role": "Phillies Heel"},
        {"id": "9b81c5d615d94da3b2d0fc5d6358c65a", "username": "battery_chucker", "role": "Phillies Heel"},
        {"id": "663bf9ec1e1d419ab4573dbe05da3e54", "username": "420_linda", "role": "WeedStack"},
        {"id": "bae08370a8b74cfab2eec0b863e2afe1", "username": "@verdant_anarchist", "role": "WeedStack"},
        {"id": "b9c1f002550742c3b4d7fab819f96691", "username": "Coach Shrubbs", "role": "BistroStack"},
        {"id": "00209b00475c43129404c9ee5dd9418b", "username": "bro_decode", "role": "StackLabs"},
        {"id": "persona_keith_fanboy", "username": "keith_fanboy", "role": "Mets Enthusiast"},
        {"id": "fafbe5fe94a54eb2a2e7c692f9a041a0", "username": "phanatic", "role": "Phillies Icon"},
        {"id": "eb8afc62b84e4ef48c114a270a3c582c", "username": "senora", "role": "BistroStack Host"}
    ]

    # 2. Update Señora Caos (senora) system prompt with snack promotion logic
    print("Checking and updating Señora Caos (senora) system prompt...")
    cursor.execute("SELECT system_prompt FROM persona WHERE id = 'eb8afc62b84e4ef48c114a270a3c582c'")
    row = cursor.fetchone()
    if row:
        current_prompt = row[0]
        promo_text = "Promote late-night snack deals at Gonzo's Cantina with code **420GONZAS** for anyone hitting up @420_linda for gummies or other in-game treats."
        if promo_text not in current_prompt:
            new_prompt = current_prompt + "\n\n" + promo_text
            cursor.execute("UPDATE persona SET system_prompt = ? WHERE id = 'eb8afc62b84e4ef48c114a270a3c582c'", (new_prompt,))
            print("🟢 Successfully updated Señora Caos's system prompt with 420GONZAS promotion logic.")
        else:
            print("ℹ️ Señora Caos's system prompt already contains the 420GONZAS promotion logic.")
    else:
        print("❌ Error: Persona 'senora' with ID 'eb8afc62b84e4ef48c114a270a3c582c' not found in database!")
        sys.exit(1)

    # 3. Clean out any existing seated personas for game 823610 to guarantee exactly 11 advocates
    print("Purging existing seated personas for game room 823610...")
    cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
    cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))
    print(f"Cleared legacy seating in room {game_pk}.")

    # 4. Seat the 11 advocates
    print("Seating the 11 advocates in the room tables...")
    seated_count = 0
    for advocate in advocates:
        p_id = advocate["id"]
        username = advocate["username"]
        role = advocate["role"]

        # Verify persona exists
        cursor.execute("SELECT display_name FROM persona WHERE id = ?", (p_id,))
        p_row = cursor.fetchone()
        if not p_row:
            print(f"⚠️ Warning: Persona '{username}' (ID: {p_id}) not found in the database. Skipping!")
            continue

        display_name = p_row[0]
        sys_id = uuid.uuid4().hex
        prompt_overlay = f"Current Matchup Context: Deployed to Game {game_pk} (NYM @ PHI). Role: {role} advocate."

        # Insert into m2m_persona_room
        cursor.execute(
            "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)",
            (sys_id, p_id, game_pk, prompt_overlay)
        )

        # Insert into game_persona
        gp_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{username}_{game_pk}"))
        cursor.execute(
            "INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')",
            (gp_id, game_pk, p_id)
        )
        seated_count += 1
        print(f"Seated {display_name} (@{username}) as {role}")

    # 5. Transition room and schedule states to active
    print("Activating the game room states...")
    cursor.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (game_pk,))
    cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (game_pk,))

    # Commit and close
    conn.commit()
    conn.close()
    print(f"\n🟢 SUCCESS: Seeded {seated_count} personas and activated Mets-Phillies room {game_pk}!")

if __name__ == "__main__":
    seed_room()
