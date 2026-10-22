import sqlite3

db_path = "/home/james/stacklabs/dna/sovereign_now.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

sys_id = "7d8d1238ec594b1ba187f5182c0d9a8b"

# 1. Update cmdb_ci name
cursor.execute("UPDATE cmdb_ci SET name = 'Señora Caos' WHERE sys_id = ?", (sys_id,))
print("Updated cmdb_ci name to Señora Caos")

# 2. Update cmdb_ci_ai_persona columns
cursor.execute("PRAGMA table_info(cmdb_ci_ai_persona);")
columns = [col[1] for col in cursor.fetchall()]

cursor.execute("SELECT * FROM cmdb_ci_ai_persona WHERE sys_id = ?", (sys_id,))
row = cursor.fetchone()
if row:
    row_dict = dict(zip(columns, row))
    for col in columns:
        if col == "sys_id":
            continue
        val = row_dict[col]
        if isinstance(val, str):
            new_val = val.replace("Madame Mayhem", "Señora Caos")
            new_val = new_val.replace("madame_mayhem", "senora_caos")
            new_val = new_val.replace("Unhinged Convenience", "Gonzas")
            new_val = new_val.replace("UnhingedConvenience", "GONZAS")
            if new_val != val:
                cursor.execute(f"UPDATE cmdb_ci_ai_persona SET {col} = ? WHERE sys_id = ?", (new_val, sys_id))
                print(f"Updated cmdb_ci_ai_persona.{col}")

# 3. Rename any other occurrences in sovereign_tickets
cursor.execute("UPDATE sovereign_tickets SET description = REPLACE(REPLACE(description, 'UNHINGEDCONVENIENCE', 'GONZAS'), 'Madame Mayhem', 'Señora Caos') WHERE description LIKE '%UNHINGEDCONVENIENCE%' OR description LIKE '%Madame Mayhem%';")
print("Updated sovereign_tickets description occurrences")

conn.commit()
conn.close()
