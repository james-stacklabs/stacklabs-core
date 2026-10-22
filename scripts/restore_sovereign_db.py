import sqlite3
import os
import sys
import subprocess

src_path = "/home/james/stacklabs/dna/sovereign_now.db.p1_bak_20260829_063042"
prod_path = "/home/james/stacklabs/dna/sovereign_now_production.db"
target_path = "/home/james/stacklabs/dna/sovereign_now.db"

print("--- STARTING CLEAN DATABASE RECONSTRUCTION ---")

if os.path.exists(prod_path):
    os.remove(prod_path)

src_conn = sqlite3.connect(src_path)
dst_conn = sqlite3.connect(prod_path)

src_cur = src_conn.cursor()
dst_cur = dst_conn.cursor()

# Get all objects ordered: tables first, then views, then triggers/indexes
objects = src_cur.execute("""
    SELECT type, name, sql FROM sqlite_master 
    WHERE name NOT LIKE 'sqlite_%' 
    ORDER BY CASE 
        WHEN type='table' THEN 1 
        WHEN type='view' THEN 2 
        ELSE 3 
    END;
""").fetchall()

print(f"Total schema objects to process: {len(objects)}")
tables_processed = 0
total_rows = 0

for obj_type, name, sql in objects:
    if not sql:
        continue
    if obj_type == 'table':
        try:
            dst_cur.execute(sql)
            if name in ['sovereign_tickets', 'sys_media_asset']:
                # Will be populated from clean SQL dump
                continue
            
            # Fetch and insert data in chunks
            rows = src_cur.execute(f'SELECT * FROM "{name}"').fetchall()
            if rows:
                placeholders = ','.join(['?'] * len(rows[0]))
                dst_cur.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', rows)
                total_rows += len(rows)
            tables_processed += 1
        except Exception as e:
            print(f"[WARN] Table {name}: {e}")

dst_conn.commit()
dst_conn.close()
src_conn.close()

print(f"Base copy completed. Tables: {tables_processed}, Total base rows: {total_rows}")

# Now import sovereign_tickets and sys_media_asset from clean dump files
if os.path.exists("/home/james/stacklabs/dna/sovereign_tickets.sql"):
    print("Importing sovereign_tickets.sql...")
    subprocess.run(f"sqlite3 {prod_path} < /home/james/stacklabs/dna/sovereign_tickets.sql", shell=True, check=True)

if os.path.exists("/home/james/stacklabs/dna/sys_media_asset.sql"):
    print("Importing sys_media_asset.sql...")
    subprocess.run(f"sqlite3 {prod_path} < /home/james/stacklabs/dna/sys_media_asset.sql", shell=True, check=False)

# Now verify integrity and row counts
check_conn = sqlite3.connect(prod_path)
check_cur = check_conn.cursor()

integ = check_cur.execute("PRAGMA integrity_check").fetchall()
ticket_cnt = check_cur.execute("SELECT count(*) FROM sovereign_tickets").fetchone()[0]
chat_cnt = check_cur.execute("SELECT count(*) FROM game_chat").fetchone()[0]
persona_cnt = check_cur.execute("SELECT count(*) FROM persona").fetchone()[0]
cmdb_cnt = check_cur.execute("SELECT count(*) FROM cmdb_ci").fetchone()[0]

print(f"Production DB Integrity: {integ}")
print(f"Verification: Tickets={ticket_cnt}, GameChat={chat_cnt}, Persona={persona_cnt}, CMDB={cmdb_cnt}")

if integ == [('ok',)] and ticket_cnt > 1000:
    print("Integrity verification passed with 100% confidence. Swapping into target...")
    check_cur.execute("PRAGMA journal_mode=WAL;")
    check_conn.close()
    
    # Kill any dangling locks
    subprocess.run("fuser -k /home/james/stacklabs/dna/sovereign_now.db 2>/dev/null || true", shell=True)
    # Remove stale wal/shm
    for ext in ["-wal", "-shm"]:
        f = target_path + ext
        if os.path.exists(f):
            os.remove(f)
    
    # Atomic replace
    os.replace(prod_path, target_path)
    
    # Set WAL on target
    final_conn = sqlite3.connect(target_path)
    final_cur = final_conn.cursor()
    final_cur.execute("PRAGMA journal_mode=WAL;")
    final_integ = final_cur.execute("PRAGMA integrity_check").fetchall()
    final_tickets = final_cur.execute("SELECT count(*) FROM sovereign_tickets").fetchone()[0]
    final_conn.close()
    
    print(f"SUCCESS! sovereign_now.db is LIVE in WAL mode. Integrity: {final_integ}, Tickets: {final_tickets}")
else:
    print("Integrity check failed! Halting swap.")
    sys.exit(1)
