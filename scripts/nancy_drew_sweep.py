import os
import json
import sqlite3
import shutil
import time

DB_PATH = "/home/james/stacklabs/04_Sovereign_Core/sovereign_core.db"
CI_DIR = "/home/james/stacklabs/dna/ci"
VAULT_DIR = "/home/james/stacklabs/dna/vault/legacy_ci"

# Create the Ship of Shadows vault if it doesn't exist
os.makedirs(VAULT_DIR, exist_ok=True)

# Connect to the Comb
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("\n=======================================================")
print("🕵️‍♀️  THE NANCY DREW PROTOCOL (CHINDŌGU LEVEL 7)  🕵️‍♀️")
print("=======================================================\n")
print("Scanning /dna/ci/ for Hidden Objects (Orphaned JSONs)...\n")
time.sleep(1)

# Grab all potential configuration item JSONs
files = [f for f in os.listdir(CI_DIR) if f.endswith("_ci.json")]

points = 0
for file in files:
    file_path = os.path.join(CI_DIR, file)
    vault_path = os.path.join(VAULT_DIR, file)
    
    print(f"🔍 Investigating Flat-File Clue: {file}...")
    time.sleep(0.8)  # Dramatic Nancy Drew suspense
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            
        # Extract the ground truth
        node_id = data.get("ci_id", "UNKNOWN-" + file)
        
        # Determine if it's an Agent or Hardware node based on the keys
        hardware = data.get("metadata", {}).get("host_environment", data.get("name", "Unknown Hardware"))
        agent_class = data.get("archetype", data.get("type", "Hardware/Sensor Node"))
        status = data.get("status", "LEGACY_IMPORTED")
        
        # Port to SQLite Comb (Fleet Nodes table)
        c.execute("""
            INSERT OR REPLACE INTO fleet_nodes 
            (node_id, hardware, agent_class, status, primary_directives, manifest_path, s_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (node_id, hardware, agent_class, status, json.dumps(data.get("metadata", {})), vault_path, 1.0))
        
        conn.commit()
        print(f"   🎯 BINGO! Ground truth extracted >> Node ID: {node_id}")
        time.sleep(0.5)
        
        # Ship of Shadows: Vault the legacy flat file
        shutil.move(file_path, vault_path)
        print(f"   📦 Ship of Shadows: Vaulted {file} permanently.")
        points += 10
        
    except Exception as e:
        print(f"   ❌ Anomaly encountered parsing {file}: {e}. Leaving for manual review.")
        
    print("-" * 65)
    time.sleep(0.5)

conn.close()
print(f"\n✅ SWEEP COMPLETE! Total Points Scored: {points}")
print("Mansion rooms cleared of legacy flat-files. SQLite Comb explicitly reinforced.\n")
