import sqlite3

def main():
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    cursor = conn.cursor()
    
    gamePk = '823608'
    cursor.execute("""
        SELECT p.user_name, p.team, p.color, COALESCE(gp.gemini_tokens, 0), COALESCE(gp.local_tokens, 0)
        FROM persona p
        LEFT JOIN game_persona gp ON (gp.persona_id = p.id AND gp.game_pk = ?)
        LEFT JOIN m2m_persona_room m2m ON (m2m.room = ? AND (m2m.persona = p.id OR m2m.persona = p.user_name OR m2m.persona = (SELECT sys_id FROM sys_user WHERE user_name = p.user_name COLLATE NOCASE)))
        WHERE (gp.game_pk = ? AND gp.seat_state = 'active') OR m2m.sys_id IS NOT NULL
        GROUP BY p.user_name
        ORDER BY p.team, p.user_name
    """, (gamePk, gamePk, gamePk))
    rows = cursor.fetchall()
    print(f"Total rows fetched: {len(rows)}")
    for idx, r in enumerate(rows, 1):
        print(f"{idx}. {r[0]} | Team: {r[1]} | Color: {r[2]}")
        
    conn.close()

if __name__ == '__main__':
    main()
