import os
import json
import sqlite3
import time

DB_PATH = "/home/james/stacklabs/scripts/sovereign_core.db"
LEGACY_CMDB = "/home/james/stacklabs/dna/vault/quarantine/legacy_folder_architecture/04_Sovereign_Core/sovereign_cmdb.json"
MASTER_LEDGER = "/home/james/stacklabs/master_ledger.json"

print("\n=======================================================")
print("🕵️‍♀️  THE NANCY DREW PROTOCOL (CHINDŌGU LEVEL 7)  🕵️‍♀️")
print("=======================================================\n")
print(f"Executing Deep Sweep of Legacy JSON Archives...")
time.sleep(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

points = 0

# 1. Sweep sovereign_cmdb.json (The Vesper Store)
if os.path.exists(LEGACY_CMDB):
    print(f"🔍 Investigating Legacy Clue: sovereign_cmdb.json...")
    with open(LEGACY_CMDB, "r") as f:
        try:
            data = json.load(f)
            
            # Port CIs
            for ci in data.get("Configuration_Items", []):
                node_id = ci.get("id", "UNKNOWN")
                hardware = ci.get("name", "Unknown Hardware")
                agent_class = ci.get("attributes", {}).get("role", ci.get("role", "Node"))
                status = ci.get("status", "ARCHIVED")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO fleet_nodes 
                    (node_id, hardware, agent_class, status, primary_directives, manifest_path, s_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (node_id, hardware, agent_class, status, json.dumps(ci), LEGACY_CMDB, 1.0))
                points += 5
            
            # Port Tickets
            for t in data.get("Tickets", []):
                ticket_id = t.get("id", "UNKNOWN")
                title = t.get("title", "Legacy Ticket")
                status = t.get("status", "Archived")
                priority = "High" if t.get("priority") else "Low"
                ci_link = t.get("related_ci", t.get("assignee", "N/A"))
                desc = t.get("notes", "No description provided.")
                
                # Check if it exists
                cursor.execute('SELECT ticket_id FROM sdlc_tickets WHERE ticket_id=?', (ticket_id,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO sdlc_tickets (ticket_id, ci_id, title, description, priority, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (ticket_id, ci_link, title, desc, priority, status, "2026-03-20T00:00:00Z"))
                points += 10
                
            conn.commit()
            print(f"   🎯 BINGO! Ground truth extracted >> CIs & Tickets recovered from sovereign_cmdb.json")
        except Exception as e:
            print(f"   ❌ Anomaly encountered: {e}")

# 2. Sweep Master Ledger
if os.path.exists(MASTER_LEDGER):
    print(f"🔍 Investigating Legacy Clue: master_ledger.json...")
    with open(MASTER_LEDGER, "r") as f:
        try:
            ledger = json.load(f)
            if "nodes" in ledger:
                for node_id, ci in ledger["nodes"].items():
                    cursor.execute("""
                        INSERT OR IGNORE INTO fleet_nodes 
                        (node_id, hardware, agent_class, status, primary_directives, manifest_path, s_value)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (node_id, ci.get("hardware", "Unknown"), ci.get("class", "Node"), ci.get("status", "LEGACY"), '{}', MASTER_LEDGER, 1.0))
                    points += 5
            
            if "backlog" in ledger:
                for t in ledger["backlog"]:
                    ticket_id = t.get("id", "UNKNOWN")
                    cursor.execute('SELECT ticket_id FROM sdlc_tickets WHERE ticket_id=?', (ticket_id,))
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO sdlc_tickets (ticket_id, ci_id, title, description, priority, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (ticket_id, "N/A", t.get("title", "Ledger Task"), t.get("notes", ""), "Low", t.get("status", "Open"), "2026-03-25T00:00:00Z"))
                        points += 10
            conn.commit()
            print(f"   🎯 BINGO! Ground truth extracted >> Ledgers ported.")
        except Exception as e:
             print(f"   ❌ Anomaly encountered: {e}")

conn.close()
print(f"\n✅ SWEEP COMPLETE! Total Points Scored: {points}")
print("Mansion rooms cleared of legacy flat-files. SQLite Comb explicitly reinforced.\n")
