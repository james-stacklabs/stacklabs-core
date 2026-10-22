"""
Migration 001: Add auth columns to sys_user table
Adds: password_hash, role, display_name
Seeds the Pilot user (james) with a bcrypt password hash.
Safe to run multiple times (idempotent).

Usage:
    python3 001_add_auth_columns.py <your_pilot_password>
"""
import sqlite3
import bcrypt
import uuid
import os
import secrets
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ENV_PATH = "/home/james/stacklabs/scripts/.env.auth"


def run():
    # ── Password from CLI arg — no interactive prompts ───────────────────────
    if len(sys.argv) < 2:
        print("\nERROR: No password provided.")
        print("Usage: python3 001_add_auth_columns.py <your_pilot_password>")
        sys.exit(1)

    pw = sys.argv[1]
    if len(pw) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Add auth columns idempotently ────────────────────────────────────────
    for col_sql in [
        "ALTER TABLE sys_user ADD COLUMN password_hash TEXT",
        "ALTER TABLE sys_user ADD COLUMN role TEXT DEFAULT 'guest'",
        "ALTER TABLE sys_user ADD COLUMN display_name TEXT",
    ]:
        try:
            c.execute(col_sql)
            print(f"  + Added column: {col_sql.split('ADD COLUMN')[1].strip()}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  ~ Column already exists, skipping")
            else:
                raise

    conn.commit()

    # ── Hash the password and upsert the Pilot user ──────────────────────────
    pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()

    c.execute("SELECT sys_id FROM sys_user WHERE user_name = 'james'")
    row = c.fetchone()
    if row:
        c.execute("""
            UPDATE sys_user
            SET password_hash=?, role='pilot', display_name='James (Pilot)', active=1
            WHERE user_name='james'
        """, (pw_hash,))
        print("  + Updated 'james' — role=pilot, password hash set.")
    else:
        c.execute("""
            INSERT INTO sys_user
                (sys_id, user_name, first_name, last_name, display_name, role, password_hash, active)
            VALUES (?, 'james', 'James', 'Carroll', 'James (Pilot)', 'pilot', ?, 1)
        """, (uuid.uuid4().hex, pw_hash))
        print("  + Inserted Pilot user 'james'.")

    conn.commit()
    conn.close()

    # ── Generate JWT secret if not already present ───────────────────────────
    if not os.path.exists(ENV_PATH):
        secret = secrets.token_hex(32)
        with open(ENV_PATH, "w") as f:
            f.write(f"SOVEREIGN_AUTH_SECRET={secret}\n")
        print(f"  + JWT secret generated → {ENV_PATH}")
    else:
        print(f"  ~ JWT secret already exists at {ENV_PATH}, skipping.")

    print("\n✅ Migration 001 complete. Pilot user ready.")


if __name__ == "__main__":
    run()
