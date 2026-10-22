import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("--- Before Cleanup ---")
    c.execute("SELECT COUNT(*) FROM game_persona WHERE persona_id = 'bae08370a8b74cfab2eec0b863e2afe1'")
    print("game_persona match count:", c.fetchone()[0])
    c.execute("SELECT COUNT(*) FROM m2m_persona_room WHERE persona = 'bae08370a8b74cfab2eec0b863e2afe1' OR persona = '@verdant_anarchist'")
    print("m2m_persona_room match count (excluding WEEDSTACK_SIM_001):", c.fetchone()[0])

    print("\nExecuting deletions...")
    # Delete from game_persona for NYM-PHI rooms 823610 and 823206
    c.execute("""
        DELETE FROM game_persona 
        WHERE persona_id = 'bae08370a8b74cfab2eec0b863e2afe1' 
          AND game_pk IN ('823610', '823206')
    """)
    print(f"Deleted {c.rowcount} rows from game_persona.")
    
    # Delete from m2m_persona_room for rooms 823610 and 823206
    c.execute("""
        DELETE FROM m2m_persona_room 
        WHERE (persona = 'bae08370a8b74cfab2eec0b863e2afe1' OR persona = '@verdant_anarchist')
          AND room IN ('823610', '823206')
    """)
    print(f"Deleted {c.rowcount} rows from m2m_persona_room.")
    
    conn.commit()
    
    print("\n--- After Cleanup ---")
    c.execute("SELECT game_pk, seat_state FROM game_persona WHERE persona_id = 'bae08370a8b74cfab2eec0b863e2afe1'")
    print("Remaining in game_persona:")
    for row in c.fetchall():
        print("  ", row)
        
    c.execute("SELECT room, persona FROM m2m_persona_room WHERE persona = 'bae08370a8b74cfab2eec0b863e2afe1' OR persona = '@verdant_anarchist'")
    print("Remaining in m2m_persona_room:")
    for row in c.fetchall():
        print("  ", row)
        
    conn.close()

if __name__ == "__main__":
    main()
