import sqlite3

def get_next_oracle_id():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/sovereign_core.db')
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(sequence_id) FROM oracle_sequences")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result is None:
            return "001"
        return f"{int(result) + 1:03d}"
    except Exception as e:
        return "000"

if __name__ == "__main__":
    print(get_next_oracle_id())
