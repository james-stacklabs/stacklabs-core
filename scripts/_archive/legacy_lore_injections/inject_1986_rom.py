import sqlite3
import json
import time

DB_PATH = '/home/james/stacklabs/data/sovereign_intelligence.db'

def inject_mock_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if 111111 already exists to avoid duplicates
    c.execute("DELETE FROM statcast_pitches WHERE game_pk = 111111")
    
    mock_pitches = [
        # At-bat 1: Mookie Wilson (Bot 10th)
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 0, 0, 'foul', 'Strike (Foul)', 85.0, 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 92.0, 1, 1, 0, 1),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 0, 1, 'ball', 'Ball', '', 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 91.5, 1, 1, 0, 2),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 1, 1, 'ball', 'Ball', '', 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 90.0, 1, 1, 0, 3),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 2, 1, 'foul', 'Strike (Foul)', 80.0, 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 92.5, 1, 1, 0, 4),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 2, 2, 'ball', 'Wild Pitch. Mitchell scores.', '', 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 88.0, 1, 0, 1, 5), # Knight goes to second
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 3, 2, 'foul', 'Strike (Foul)', 86.0, 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 92.2, 0, 1, 0, 6),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 3, 2, 'foul', 'Strike (Foul)', 87.0, 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 93.0, 0, 1, 0, 7),
        (111111, '1986-10-25', 'BOS', 'NYM', 10, 'Bot', 2, 3, 2, 'field_error', 'In play, run(s). Ground ball through Buckner.', 94.0, 'Stanley, Bob', 'Wilson, Mookie', 'Sinker', 91.8, 0, 1, 0, 8),
    ]

    for p in mock_pitches:
        c.execute("""
            INSERT INTO statcast_pitches (
                game_pk, game_date, away_team, home_team, inning, inning_topbot, outs_when_up,
                balls, strikes, events, description, launch_speed, player_name,
                des, pitch_name, release_speed, on_1b, on_2b, on_3b, pitch_number, at_bat_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], f"{p[13]} {p[10]}", p[14], p[15], p[16], p[17], p[18], p[19], 1))
        
    conn.commit()
    conn.close()
    print("Injected 1986 mock data successfully.")

if __name__ == '__main__':
    inject_mock_data()
