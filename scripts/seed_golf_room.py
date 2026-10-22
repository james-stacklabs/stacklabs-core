import sqlite3
import datetime
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Insert schedule row for 'amen_corner'
    today = datetime.date.today().isoformat()
    c.execute("""
        INSERT OR REPLACE INTO mlb_schedule 
        (game_pk, game_date, home_team, away_team, status, room_state, boggs_level, venue)
        VALUES ('amen_corner', ?, 'PGA', 'GOLF', 'Active', 'active', 2, 'Augusta National')
    """, (today,))
    print("Seeded mlb_schedule for amen_corner.")
    
    # 2. Get the golf personas to map
    c.execute("""
        SELECT id, user_name FROM persona 
        WHERE team = 'golf_room'
    """)
    personas = c.fetchall()
    print(f"Found {len(personas)} golf personas to seed.")
    
    # 3. Insert game_persona mappings
    for p_id, user_name in personas:
        # Generate a stable UUID based on name and game_pk for idempotency
        mapping_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{user_name}_amen_corner"))
        c.execute("""
            INSERT OR REPLACE INTO game_persona 
            (id, game_pk, persona_id, seat_state)
            VALUES (?, 'amen_corner', ?, 'active')
        """, (mapping_id, p_id))
        print(f"Mapped {user_name} ({p_id}) to amen_corner.")
        
    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed()
