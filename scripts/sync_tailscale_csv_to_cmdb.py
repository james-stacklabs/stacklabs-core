import csv
import sqlite3
import uuid
import datetime
import os

CSV_FILE = "/home/james/stacklabs/dna/dropzone/daily_02052026/jc2pointzero@gmail.com-devices-2026-05-02T10-01-33-709Z.csv"
DB_FILE = "/home/james/stacklabs/dna/sovereign_now.db"

def sync_cmdb():
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file not found at {CSV_FILE}")
        return
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Pre-process: Rename 'Raspberry Pi (Trading) Ltd' to 'argo' so we can catch it correctly
    cursor.execute("UPDATE cmdb_ci SET name = 'argo' WHERE name = 'Raspberry Pi (Trading) Ltd'")
    conn.commit()
    
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device_name = row.get("Device name", "").strip()
            ips_raw = row.get("Tailscale IPs", "")
            
            if not device_name or not ips_raw:
                continue
                
            # Grab the 100.x.x.x IPv4 address
            ipv4 = ""
            for ip in ips_raw.split(','):
                ip = ip.strip()
                if ip.startswith("100."):
                    ipv4 = ip
                    break
                    
            if not ipv4:
                continue
                
            # Specific rename handling
            if device_name.lower() == "sov73":
                device_name = "argo"
                
            cursor.execute("SELECT sys_id FROM cmdb_ci WHERE name = ?", (device_name,))
            record = cursor.fetchone()
            
            if record:
                sys_id = record[0]
                # Check if it exists in cmdb_ci_hardware
                cursor.execute("SELECT sys_id FROM cmdb_ci_hardware WHERE sys_id = ?", (sys_id,))
                if cursor.fetchone():
                    # Update existing hardware CI
                    cursor.execute("UPDATE cmdb_ci_hardware SET ip_address = ? WHERE sys_id = ?", (ipv4, sys_id))
                    print(f"Updated existing CI: {device_name} with IP {ipv4}")
                else:
                    # Insert into hardware table if it somehow exists only in cmdb_ci
                    cursor.execute("INSERT INTO cmdb_ci_hardware (sys_id, ip_address) VALUES (?, ?)", (sys_id, ipv4))
                    print(f"Inserted missing hardware CI details for existing generic CI: {device_name}")
            else:
                # Insert new CI
                new_sys_id = str(uuid.uuid4())
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status, sys_created_on, sys_updated_on) VALUES (?, ?, ?, ?, ?, ?)",
                    (new_sys_id, device_name, 'cmdb_ci_hardware', 1, now, now)
                )
                cursor.execute("INSERT INTO cmdb_ci_hardware (sys_id, ip_address) VALUES (?, ?)", (new_sys_id, ipv4))
                print(f"Inserted NEW CI: {device_name} with IP {ipv4}")
                
    conn.commit()
    conn.close()
    print("CMDB Tailscale Sync Complete.")

if __name__ == "__main__":
    sync_cmdb()
