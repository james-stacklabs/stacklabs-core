#!/usr/bin/env python3
import os
import sys
import sqlite3
import subprocess

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INTAKE_PATH = "/home/james/sovereign_inbox/today/stacklabs_intake.md"

def main():
    print("🏢 Starting StackLabs Seeding Protocol...")
    
    # 1. Validate Intake file exists and is formatted correctly
    if not os.path.exists(INTAKE_PATH):
        print(f"❌ Error: StackLabs intake form not found at {INTAKE_PATH}")
        sys.exit(1)
        
    with open(INTAKE_PATH, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if not first_line.startswith("# BRAND:"):
            print(f"❌ Error: StackLabs intake form does not start with '# BRAND:' - got '{first_line}'")
            sys.exit(1)
            
    # 2. Connect to sovereign_now.db and purge existing StackLabs records
    print("🧹 Purging existing StackLabs records from DB...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Purge from persona table
        cursor.execute("""
            DELETE FROM persona 
            WHERE team IN ('STACKLABS', 'STACKLABSLLC')
        """)
        persona_count = cursor.rowcount
        
        # Purge from sim_agents table
        cursor.execute("""
            DELETE FROM sim_agents 
            WHERE team IN ('STACKLABS', 'STACKLABSLLC')
        """)
        sim_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        print(f"✅ DB Purge Complete: Removed {persona_count} personas and {sim_count} sim agents.")
    except Exception as e:
        print(f"❌ Error while cleaning database: {e}")
        sys.exit(1)
        
    # 3. Invoke stack_seeder_cli.py
    print("🚀 Invoking stack_seeder_cli.py with StackLabs intake...")
    python_exec = "/home/james/stacklabs/.venv/bin/python3"
    if not os.path.exists(python_exec):
        python_exec = "python3"
        
    cmd = [python_exec, "/home/james/stacklabs/scripts/stack_seeder_cli.py", INTAKE_PATH]
    res = subprocess.run(cmd, capture_output=False)
    
    if res.returncode != 0:
        print("❌ Error: StackLabs seeding failed.")
        sys.exit(res.returncode)
        
    print("✅ StackLabs Seeding Protocol complete!")

if __name__ == "__main__":
    main()
