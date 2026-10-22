import os
import json
import sqlite3
import requests

# Local system configuration
DRIVE_MISC_INBOUND = "/home/james/sovereign_inbox/spark/misc/"
DB_PATH = "/home/james/sovereign_inbox/tickets/sovereign_now.db" # local tracking table
LOCAL_TICKET_API = "http://127.0.0.1:3016/api/tickets/" # local loopback ingress port

def process_spark_receipts():
    if not os.path.exists(DRIVE_MISC_INBOUND):
        return

    # Scan for files matching the receipt pattern
    for filename in os.listdir(DRIVE_MISC_INBOUND):
        if filename.endswith("_receipt.json"):
            file_path = os.path.join(DRIVE_MISC_INBOUND, filename)
            
            try:
                with open(file_path, 'r') as f:
                    payload = json.load(f)
                
                ticket_id = payload.get("ticket_id")
                new_status = payload.get("status")
                notes = payload.get("completion_notes", "Processed by Spark scheduled run.")
                
                if ticket_id and new_status:
                    print(f"[REAKING NEWS]: Caught Spark Receipt for {ticket_id}. Processing local state transition...")
                    
                    # 1. Update your local SQLite source of truth directly
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE cmdb_ci_ticket SET status = ?, work_notes = work_notes || ? WHERE number = ?",
                        (new_status, f"\n[Spark Scheduled Run]: {notes}", ticket_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    # 2. Hit your local UI API loopback to instantly refresh your portal dashboard
                    # This tells port 3016 that the ticket state has changed!
                    api_url = f"{LOCAL_TICKET_API}{ticket_id}/update"
                    requests.post(api_url, json={"status": new_status, "notes": notes})
                    
                    # 3. Clean up the receipt from the loading dock to avoid re-processing
                    os.remove(file_path)
                    print(f"[SUCCESS]: {ticket_id} updated and receipt cleared from staging.")
                    
            except Exception as e:
                print(f"[INGRESS ERROR]: Failed to parse receipt file {filename}: {str(e)}")

if __name__ == "__main__":
    process_spark_receipts()