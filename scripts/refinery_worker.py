import json
import sqlite3
import time
import os
import re

LEDGER_PATH = '/home/james/stacklabs/master_ledger.json'
DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'

def process_intel_request(ticket_title):
    # Extremely basic natural language to SQL router
    # e.g., "[INTEL_REQ] Lindor Exit Velo vs Sweepers"
    
    query_text = ticket_title.replace("[INTEL_REQ]", "").strip().lower()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    response = "No data found."
    
    # Very rudimentary keyword matching for MVP
    if "lindor" in query_text and "exit velo" in query_text and "sweeper" in query_text:
        sql = """
            SELECT AVG(launch_speed) as avg_exit_velo, COUNT(*) as sample_size 
            FROM statcast_pitches 
            WHERE player_name LIKE '%Lindor%' 
            AND pitch_name LIKE '%Sweeper%' 
            AND launch_speed IS NOT NULL
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        if row and row[0]:
            response = f"Lindor Avg Exit Velo vs Sweepers: {round(row[0], 2)} MPH (Sample size: {row[1]})"
        else:
            response = "Not enough data for Lindor vs Sweepers."
            
    elif "alonso" in query_text and "home run" in query_text:
        sql = """
            SELECT COUNT(*) FROM statcast_pitches
            WHERE player_name LIKE '%Alonso%' AND events = 'home_run'
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        response = f"Pete Alonso Total HRs in DB: {row[0]}"
        
    else:
        # Fallback query
        response = "Query not understood by rudimentary model. Try 'Lindor Exit Velo vs Sweepers'."

    conn.close()
    return response

def worker_loop():
    print("🐝 Refinery Worker Agent (The Bee) Starting...")
    while True:
        try:
            with open(LEDGER_PATH, 'r') as f:
                ledger = json.load(f)
                
            tickets = ledger.get("Tickets", [])
            modified = False
            
            for ticket in tickets:
                if ticket.get("status") == "Open" and ticket.get("title", "").startswith("[INTEL_REQ]"):
                    print(f"[*] Found INTEL_REQ: {ticket['title']}")
                    
                    # Process the request
                    result = process_intel_request(ticket['title'])
                    print(f"      -> Result: {result}")
                    
                    # Close the ticket and append result to description
                    ticket['status'] = "Closed"
                    ticket['description'] = f"{ticket.get('description', '')}\n\n[REFINERY RESULT]: {result}"
                    modified = True
                    
            if modified:
                with open(LEDGER_PATH, 'w') as f:
                    json.dump(ledger, f, indent=4)
                print("[+] LEDGER Updated. Tickets Closed.")
                    
        except Exception as e:
            print(f"[!] Worker Error: {e}")
            
        time.sleep(5) # Poll every 5 seconds

if __name__ == "__main__":
    worker_loop()
