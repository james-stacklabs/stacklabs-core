import sqlite3
import sys
import textwrap

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 search_personas.py <search_term>")
        return
        
    term = sys.argv[1].lower()
    db_path = '/home/james/stacklabs/dna/sovereign_now.db'
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Search for personas matching the term in user_name or title
        query = """
            SELECT user_name, title, introduction 
            FROM sys_user 
            WHERE user_name LIKE ? OR title LIKE ?
        """
        cursor.execute(query, (f'%{term}%', f'%{term}%'))
        results = cursor.fetchall()
        
        if not results:
            print(f"No personas found matching: '{term}'")
            return
            
        print(f"--- MATCHING PERSONAS ({len(results)}) ---")
        for row in results:
            print(f"\n[{row['user_name']}] - {row['title']}")
            if row['introduction']:
                # Wrap the introduction to 80 characters without truncating the buffer
                wrapped = textwrap.fill(row['introduction'], width=80)
                print(f"Lore/Intro:\n{wrapped}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
