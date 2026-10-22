import sqlite3

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

yardbarker_trauma = (
    " CURRENT FIXATIONS: You are acutely aware that the Mariners just destroyed their own bronze "
    "Ichiro statue, the Yankees are on a pathetic 17-inning scoreless streak, and the Rockies "
    "just got bought by the Walmart heirs. "
)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cmdb_ci_ai_persona")
    count = cursor.fetchone()[0]
    print(f"[{count}] personas found. Preparing mass trauma injection...")
    
    if count > 0:
        cursor.execute("""
            UPDATE cmdb_ci_ai_persona 
            SET u_system_prompt = u_system_prompt || ?
        """, (yardbarker_trauma,))
        
        conn.commit()
        print("SUCCESS: Persona profiles successfully updated with Yardbarker context.")
    else:
        print("ERROR: No personas found in the database. Aborting.")
        
except Exception as e:
    print(f"CRITICAL SYSTEM ERROR: {e}")
finally:
    if conn:
        conn.close()
