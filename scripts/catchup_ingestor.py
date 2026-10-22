import pandas as pd
from pybaseball import statcast
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import os

DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'
engine = create_engine(f'sqlite:///{DB_PATH}')
table_name = 'statcast_pitches'

def sync_season_catchup():
    print(f"\n[!] INITIATING STACK-LIFT CATCHUP")
    
    # Season boundaries
    start_date = datetime(2026, 4, 1)
    end_date = datetime(2026, 4, 4)
    
    current_date = start_date
    chunk_size = 3  # Days per request to prevent Baseball Savant blacklisting

    while current_date <= end_date:
        next_date = current_date + timedelta(days=chunk_size - 1)
        
        if next_date > end_date:
            next_date = end_date
            
        start_str = current_date.strftime('%Y-%m-%d')
        end_str = next_date.strftime('%Y-%m-%d')
        
        print(f"  > Lifting {start_str} to {end_str}...")
        
        try:
            # Download chunk
            df = statcast(start_dt=start_str, end_dt=end_str)
            
            if not df.empty:
                # Append to SQL table
                df.to_sql(table_name, engine, if_exists='append', index=False)
                print(f"  [+] Saved {len(df)} records to {os.path.basename(DB_PATH)}")
            else:
                print(f"  [-] No data for this window.")
            
        except Exception as e:
            print(f"  [ERROR] Window {start_str} Failed: {e}")
            
        # Move to the next chunk
        current_date += timedelta(days=chunk_size)

if __name__ == "__main__":
    sync_season_catchup()
    print("\n[✔] SOVEREIGN STACK-LIFT COMPLETE.")
    print(f"Location: {DB_PATH}")
