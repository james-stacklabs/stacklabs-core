import sqlite3

def main():
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    cursor = conn.cursor()
    
    # Query m2m_persona_room for room 823608
    cursor.execute("""
        SELECT p.id, p.user_name, p.display_name, p.team, p.system_prompt 
        FROM persona p 
        WHERE p.id IN (SELECT persona FROM m2m_persona_room WHERE room = '823608')
           OR p.user_name IN (SELECT persona FROM m2m_persona_room WHERE room = '823608');
    """)
    rows = cursor.fetchall()
    print(f"Total Advocates Found: {len(rows)}")
    for idx, r in enumerate(rows, 1):
        print(f"{idx}. ID: {r[0]} | Username: {r[1]} | Display Name: {r[2]} | Team: {r[3]}")
        
    conn.close()

if __name__ == '__main__':
    main()
