import sqlite3
import uuid

def seed_room():
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    game_pk = "823441"
    print(f"Targeting game room {game_pk} (NYM @ PHI)...")

    # The 15 selected personas
    advocates = [
        "2008_ghost",
        "420_linda",
        "7_train_terry",
        "UncleStevieStan",
        "barf",
        "battery_chucker",
        "bro_decode",
        "catnip_greta",
        "compliance_karen",
        "gary_bot",
        "keith_fanboy",
        "phanatic",
        "pizzabot_74",
        "ron_bot",
        "spiteful_sal"
    ]

    # Clean out any existing seated personas for game 823441
    print(f"Purging existing seated personas for game room {game_pk}...")
    cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
    cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))
    print(f"Cleared legacy seating in room {game_pk}.")

    # Seat the 15 advocates
    print("Seating the 15 advocates in the room tables...")
    seated_count = 0
    for username in advocates:
        # Verify persona exists
        cursor.execute("SELECT id, display_name FROM persona WHERE user_name = ?", (username,))
        p_row = cursor.fetchone()
        if not p_row:
            print(f"⚠️ Warning: Persona '{username}' not found in the database. Skipping!")
            continue

        p_id, display_name = p_row
        sys_id = uuid.uuid4().hex
        prompt_overlay = f"Current Matchup Context: Deployed to Game {game_pk} (PHI @ NYM)."

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
        # Ensure user is active in sys_user
        cursor.execute("UPDATE sys_user SET active = 1 WHERE sys_id = ?", (p_id,))
        
        seated_count += 1
        print(f"Seated {display_name} (@{username})")

    # Transition room and schedule states to active
    print("Activating the game room states...")
    cursor.execute("UPDATE mlb_schedule SET room_state = 'active' WHERE game_pk = ?", (game_pk,))
    cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = 'active' WHERE game_pk = ?", (game_pk,))

    # Commit and close
    conn.commit()
    conn.close()
    print(f"\n🟢 SUCCESS: Seeded {seated_count} personas and activated Mets-Phillies room {game_pk}!")

if __name__ == "__main__":
    seed_room()
