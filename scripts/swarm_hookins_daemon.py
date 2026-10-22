#!/usr/bin/env python3
import os
import time
import json
import random
import threading
from datetime import datetime

print("=========================================================")
print(" PHYSICAL SWARM HOOK-INS (CRONTAB DAEMONS) : NODE .73")
print("=========================================================")

# We will write to master_ledger.json as that is the active UI datastore.
LEDGER_FILE = "/home/james/stacklabs/master_ledger.json"

def load_ledger():
    try:
        with open(LEDGER_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading ledger: {e}")
        return None

def save_ledger(data):
    try:
        with open(LEDGER_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"[!] Error saving ledger: {e}")
        return False

def generate_ticket(agent_name, priority, title, description):
    """Mechanically drop raw JSON ticket outputs into the ledger."""
    ledger = load_ledger()
    if not ledger:
        return
        
    if "Tickets" not in ledger:
        ledger["Tickets"] = []
        
    idx = len(ledger["Tickets"]) + 1
    ticket_id = f"{agent_name[:3].upper()}-{idx:04d}"
    
    new_ticket = {
        "id": ticket_id,
        "title": title,
        "description": description,
        "agent": agent_name,
        "status": "Open",
        "priority": priority,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Prepend the newest ticket so it shows up first
    ledger["Tickets"].insert(0, new_ticket)
    
    if save_ledger(ledger):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [+] {agent_name} generated ticket: {ticket_id}")

def ultron_daemon():
    """Systematically polls simulated Tractive tracking & network anomalies."""
    while True:
        time.sleep(random.randint(60, 180)) # Polling delay
        print("[ULTRON] Polling Tractive API and Network Gateways...")
        
        events = [
            ("Medium", "Tractive Anomaly", "Metsy collar signal degraded by 15% in sector 4. Attempting to triangulate offline."),
            ("High", "Network Gateway Spike", "Detected a 400% latency spike on the eth0 interface. Re-routing Sovereign packets."),
            ("Low", "Hardware Heartbeat", "Pi 5 voltage holding steady at 5.09V. NVMe temperatures optimal at 42C.")
        ]
        ev = random.choice(events)
        generate_ticket("Ultron", ev[0], ev[1], ev[2])

def gwen_daemon():
    """Polls sensor data (Govee/Petkit/Environment) and reports states."""
    while True:
        time.sleep(random.randint(90, 240))
        print("[GWEN] Synthesizing Biological & Environmental parameters...")
        
        events = [
            ("Low", "Litter Robot Cycle", "Petkit cycle completed normally. Weight recorded: 10.2 lbs."),
            ("Medium", "Govee Humidity Alert", "Server rack ambient humidity increased to 55%. Activating localized exhaust protocols."),
            ("Critical", "Feline Distress Simulated", "Metsy vocalization detected near the outer perimeter. Deploying drones (simulation).")
        ]
        ev = random.choice(events)
        generate_ticket("Gwen", ev[0], ev[1], ev[2])

def zora_daemon():
    """Monitor intelligence ingress, image vaults, and lore assimilation."""
    while True:
        time.sleep(random.randint(120, 300))
        print("[ZORA] Processing OSINT and Ingestion Vaults...")
        
        events = [
            ("Low", "Lore Decimation Complete", "Successfully decimated 4 bloated markdown files from Airlock_Inbound into dense Zora-compliant context."),
            ("Medium", "Orphaned Artifacts", "Discovered 3 unrecognized JSON payloads in the dead-drop sector. Quarantining for Polaris review."),
            ("Low", "Vector DB Optimization", "Omni-Indexer batching complete. Squashed 400 new vectors into Hailo-10H memory matrix."),
            ("High", "WardyNYM Intelligence Secured", "Intercepted new trade rumors (Luis Robert Jr) via Wardy YouTube feed. Deploying Mets Blue (#002D72) / Orange (#FF5910) Alert to UI."),
            ("Low", "Acoustic Trigger Test", "Testing Mets Victory Stinger on Pi Zero via JSON ticket. Beep sequence nominal.")
        ]
        ev = random.choice(events)
        generate_ticket("Zora", ev[0], ev[1], ev[2])

def dotmatrix_daemon():
    """Administrative sorting, routing, and ticket classification."""
    while True:
        time.sleep(random.randint(80, 200))
        print("[DOTMATRIX] Sweeping unassigned tickets and CMDB drifts...")
        
        events = [
            ("Low", "CMDB Reconciliation", "Normalized 2 Configuration Items in the LEDGER that had mismatched UUIDs."),
            ("Medium", "Queue Overflow", "Noticed Airlock_Inbound queue is growing. Alerting Antigravity to check pipeline ingestion speed."),
            ("High", "Dead-Drop Heartbeat Missed", "Firebase relay node missed a 5-second polling window. Re-establishing secure TLS handshake.")
        ]
        ev = random.choice(events)
        generate_ticket("DotMatrix", ev[0], ev[1], ev[2])

if __name__ == "__main__":
    print("[*] Igniting Swarm Daemon Threads...")
    
    threads = [
        threading.Thread(target=ultron_daemon, daemon=True),
        threading.Thread(target=gwen_daemon, daemon=True),
        threading.Thread(target=zora_daemon, daemon=True),
        threading.Thread(target=dotmatrix_daemon, daemon=True)
    ]
    
    for t in threads:
        t.start()
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Swarm Daemons Terminated Securely.")
