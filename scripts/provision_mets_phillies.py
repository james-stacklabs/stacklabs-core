import sqlite3
import uuid

def provision():
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    game_pk = "823448"
    print(f"Provisioning game room {game_pk} (NYM @ PHI)...")

    advocates = [
        "barf_prime",
        "keith_fanboy",
        "dot",
        "section_512_sal",
        "panic_city_architect",
        "cold_beer_cutoff",
        "romeo_ingestor",
        "statcast_daytrader",
        "coach_shrubbs",
        "cap_peterson",
        "couch_philosopher",
        "terpene_chemist",
        "dr_gonzo",
        "parlay_fiend",
        "2008_ghost",
        "anarchic_nip"
    ]

    # Delete existing mappings for this game
    cursor.execute("DELETE FROM m2m_persona_room WHERE room = ?", (game_pk,))
    cursor.execute("DELETE FROM game_persona WHERE game_pk = ?", (game_pk,))
    print(f"Deleted old mappings for room {game_pk}.")

    # Insert new mappings
    inserted_count = 0
    for username in advocates:
        # Get persona UUID id
        cursor.execute("SELECT id, display_name FROM persona WHERE user_name = ?", (username,))
        row = cursor.fetchone()
        if not row:
            print(f"Warning: Persona '{username}' not found in database.")
            continue
        
        p_id, display_name = row
        sys_id = uuid.uuid4().hex
        prompt_overlay = f"Current Matchup Context: Deployed to Game {game_pk} (NYM @ PHI)."
        
        cursor.execute(
            "INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES (?, ?, ?, ?)",
            (sys_id, p_id, game_pk, prompt_overlay)
        )
        
        gp_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{username}_{game_pk}"))
        cursor.execute(
            "INSERT INTO game_persona (id, game_pk, persona_id, seat_state) VALUES (?, ?, ?, 'active')",
            (gp_id, game_pk, p_id)
        )
        inserted_count += 1
        print(f"Seated {display_name} ({username}) in room {game_pk} with ID {sys_id} and game_persona ID {gp_id}")

    # Commit changes
    conn.commit()
    conn.close()
    print(f"Successfully provisioned {inserted_count} advocates in game room {game_pk}.")

if __name__ == "__main__":
    provision()
