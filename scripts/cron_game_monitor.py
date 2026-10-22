import time
import requests
import sqlite3
from datetime import datetime, timezone, timedelta

def check_games():
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Determine date using Eastern Time to align with schedule
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo('America/New_York'))
    if now_et.hour < 10:
        target_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target_date = now_et.strftime('%Y-%m-%d')

    print(f"Game monitor aligning check with target date: {target_date}")

    cursor.execute("""
        SELECT r.sys_id, r.room_key, r.game_pk, r.room_state, s.sport 
        FROM cmdb_ci_fanstack_room r
        JOIN sport_schedule s ON r.game_pk = s.game_pk
        WHERE s.game_date = ? AND (r.is_simulated = 0 OR r.is_simulated IS NULL)
    """, (target_date,))
    rooms = cursor.fetchall()
    
    now = datetime.now(timezone.utc)

    for room_sys_id, room_key, game_pk, room_state, sport in rooms:
        try:
            if sport == 'NFL' or str(game_pk).startswith('4018') or str(game_pk).startswith('826'):
                # NFL Game Room - keep active
                continue

            resp = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live")
            if resp.status_code != 200:
                print(f"Failed to fetch game data for {game_pk}")
                continue
                
            data = resp.json()
            game_status = data.get('gameData', {}).get('status', {}).get('statusCode', 'S')
            game_time_str = data.get('gameData', {}).get('datetime', {}).get('dateTime')
            if not game_time_str:
                continue
            game_time = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            
            # Find associated user group
            cursor.execute("SELECT sys_id, name FROM sys_user_group WHERE name LIKE ?", (f"%{game_pk}%",))
            group = cursor.fetchone()
            
            # Is game active or about to be active?
            # F = Final, I = In Progress, P = Pregame, S = Scheduled
            time_until_game = (game_time - now).total_seconds()
            
            is_active_game = game_status in ['I', 'P']
            is_pregame_time = 0 < time_until_game <= 15 * 60  # less than 15 mins
            is_recent_final = game_status == 'F' and time_until_game > -3600 # Let it linger for an hour or so? Maybe just use status
            
            # Determine new state
            should_be_active = is_active_game or is_pregame_time
            new_state = 'pregame' if is_pregame_time else ('active' if is_active_game else 'inactive')
            
            if new_state != room_state:
                print(f"Room {room_key} transitioning from {room_state} to {new_state}")
                cursor.execute("UPDATE cmdb_ci_fanstack_room SET room_state = ? WHERE sys_id = ?", (new_state, room_sys_id))
                cursor.execute("UPDATE sport_schedule SET room_state = ? WHERE game_pk = ?", (new_state, game_pk))
                
                # Update users' active status
                if group:
                    active_val = 1 if should_be_active else 0
                    cursor.execute("""
                        UPDATE sys_user 
                        SET active = ? 
                        WHERE sys_id IN (
                            SELECT user FROM sys_user_grmember WHERE group_id = ?
                        )
                    """, (active_val, group[0]))
                    print(f"Updated personas for room {room_key} to active={active_val}")
                    
        except Exception as e:
            print(f"Error processing game {game_pk}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Running initial game monitor check...")
    check_games()
    print("Entering monitoring loop (every 60 seconds)...")
    while True:
        time.sleep(60)
        check_games()
