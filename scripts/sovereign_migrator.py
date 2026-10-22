#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Automated Database Migration & Seeding Hotfolder Pipeline
# Path: /home/james/stacklabs/scripts/sovereign_migrator.py
# ==============================================================================
import os
import sys
import sqlite3
import datetime
import shutil
import subprocess
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATIONS_INCOMING = "/home/james/stacklabs/dna/migrations/incoming/"
MIGRATIONS_EXECUTED = "/home/james/stacklabs/dna/migrations/executed/"


def init_migrations_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        description TEXT,
        executed_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def raise_incident_ticket(version, error_msg):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    sys_id = uuid.uuid4().hex
    try:
        # Find next incident number safely
        cursor.execute("SELECT number FROM sovereign_tickets WHERE type='INC' ORDER BY number DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            import re
            m = re.search(r'\d+', row[0])
            if m:
                last_num = int(m.group(0))
                next_num = f"INC{last_num + 1}"
            else:
                next_num = "INC1779560001"
        else:
            next_num = "INC1779560001"
            
        cursor.execute("""
            INSERT INTO sovereign_tickets (
                sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id, next_num, 'INC',
            f"Migration Failure: {version}",
            f"Automated migration execution failed for version {version}. System halted to prevent database drift.",
            1, 1, 'Antigravity', 'cmdb_ci_ai_persona',
            f"Error details: {error_msg}",
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat()
        ))
        conn.commit()
        print(f"[INCIDENT RAISED] Created priority ticket {next_num} for migration failure on {version}")
    except Exception as e:
        print(f"[ERROR] Failed to insert incident ticket: {e}")
    finally:
        conn.close()


def run_migrations():
    init_migrations_table()
    if not os.path.exists(MIGRATIONS_INCOMING):
        os.makedirs(MIGRATIONS_INCOMING, exist_ok=True)
    if not os.path.exists(MIGRATIONS_EXECUTED):
        os.makedirs(MIGRATIONS_EXECUTED, exist_ok=True)
        
    try:
        files = sorted([f for f in os.listdir(MIGRATIONS_INCOMING) if f.endswith(('.sql', '.py'))])
    except Exception as e:
        print(f"[ERROR] Failed to read incoming migrations directory: {e}")
        return

    if not files:
        print("[INFO] No pending database migrations in the hotfolder.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for filename in files:
        file_path = os.path.join(MIGRATIONS_INCOMING, filename)
        
        if '__' in filename:
            version, description_raw = filename.split('__', 1)
            description = description_raw.rsplit('.', 1)[0].replace('_', ' ')
        else:
            version = filename.split('.', 1)[0]
            description = "Ad-hoc automated database schema migration"
            
        cursor.execute("SELECT count(*) FROM schema_migrations WHERE version = ?", (version,))
        already_run = cursor.fetchone()[0] > 0
        
        if already_run:
            print(f"[INFO] Skipping migration {version} (already executed).")
            try:
                shutil.move(file_path, os.path.join(MIGRATIONS_EXECUTED, filename))
            except Exception as move_err:
                print(f"[WARNING] Failed to move already executed migration: {move_err}")
            continue
            
        print(f"[MIGRATION RUNNING] Executing: {filename}...")
        
        try:
            if filename.endswith('.sql'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as sf:
                    sql_content = sf.read()
                conn.executescript(sql_content)
                
            elif filename.endswith('.py'):
                result = subprocess.run([sys.executable, file_path], capture_output=True, text=True, check=True)
                print(f"[PYTHON OUTPUT] {result.stdout.strip()}")
                
            cursor.execute("""
                INSERT INTO schema_migrations (version, description, executed_at)
                VALUES (?, ?, ?)
            """, (version, description, datetime.datetime.now().isoformat()))
            conn.commit()
            
            try:
                shutil.move(file_path, os.path.join(MIGRATIONS_EXECUTED, filename))
            except Exception as move_err:
                print(f"[WARNING] Failed to archive migration file: {move_err}")
                
            print(f"[MIGRATION SUCCESS] {version} successfully finalized.")
            
        except Exception as e:
            error_details = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                error_details += f" | stderr: {e.stderr}"
            print(f"[MIGRATION FAILED] Error executing {filename}: {error_details}")
            
            conn.rollback()
            conn.close()
            
            raise_incident_ticket(version, error_details)
            sys.exit(1)
            
    conn.close()


if __name__ == '__main__':
    run_migrations()
