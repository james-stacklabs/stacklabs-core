#!/usr/bin/env python3
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/20260916_seed_soto_misser_persona.sql"
EXECUTED_DIR = "/home/james/stacklabs/dna/migrations/executed"

def main():
    print(f"Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cur = conn.cursor()

    # Ensure email column exists on persona
    cur.execute("PRAGMA table_info(persona);")
    cols = [r[1] for r in cur.fetchall()]
    if "email" not in cols:
        print("Adding column 'email' to persona table...")
        cur.execute("ALTER TABLE persona ADD COLUMN email TEXT;")
        conn.commit()

    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    cur.executescript(sql)

    # Also ensure email_alias is aligned
    cur.execute("UPDATE persona SET email_alias = email WHERE id = 'persona_soto_misser';")

    conn.commit()
    conn.close()

    os.makedirs(EXECUTED_DIR, exist_ok=True)
    target = os.path.join(EXECUTED_DIR, os.path.basename(MIGRATION_FILE))
    with open(target, "w") as f:
        f.write(sql)

    print("Migration applied and archived successfully.")

if __name__ == "__main__":
    main()
