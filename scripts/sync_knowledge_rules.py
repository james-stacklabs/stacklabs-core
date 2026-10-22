import os
import sqlite3
import json
import uuid
import sys
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
KNOWLEDGE_DIR = "/home/james/.gemini/antigravity/knowledge"

def sync_rules():
    print("Starting sync of Knowledge Items to sys_rules...")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Iterate through knowledge directories
    if not os.path.exists(KNOWLEDGE_DIR):
        print(f"Error: {KNOWLEDGE_DIR} does not exist.")
        return

    for item_dir in os.listdir(KNOWLEDGE_DIR):
        full_dir = os.path.join(KNOWLEDGE_DIR, item_dir)
        if not os.path.isdir(full_dir):
            continue

        metadata_path = os.path.join(full_dir, "metadata.json")
        if not os.path.exists(metadata_path):
            continue

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            summary = metadata.get('summary', '')
            
            # Check for artifacts/rule.md
            rule_path = os.path.join(full_dir, "artifacts", "rule.md")
            content = ""
            if os.path.exists(rule_path):
                with open(rule_path, 'r') as f:
                    content = f.read()

            title = item_dir.replace("ki_", "").replace("_", " ").title()

            # Upsert into database
            cur.execute("SELECT sys_id FROM sys_rules WHERE rule_id = ?", (item_dir,))
            row = cur.fetchone()
            
            if row:
                sys_id = row[0]
                cur.execute("""
                    UPDATE sys_rules 
                    SET title = ?, summary = ?, content = ?, sys_updated_on = CURRENT_TIMESTAMP
                    WHERE sys_id = ?
                """, (title, summary, content, sys_id))
                print(f"Updated rule: {item_dir}")
            else:
                sys_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO sys_rules (sys_id, rule_id, title, summary, content)
                    VALUES (?, ?, ?, ?, ?)
                """, (sys_id, item_dir, title, summary, content))
                print(f"Inserted new rule: {item_dir}")

        except Exception as e:
            print(f"Failed to process {item_dir}: {e}")

    con.commit()
    con.close()
    print("Sync complete.")

if __name__ == "__main__":
    sync_rules()
