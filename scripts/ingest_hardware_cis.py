import sqlite3
import uuid
import datetime

db_path = "/home/james/stacklabs/dna/sovereign_now.db"

# List of hardware to ingest
# Format: (name, description, class_name)
assets = [
    # Node .73 (Eagle 5)
    ("Node .73 Raspberry Pi 5", "Primary Sovereign Core and Omega Gate host (Eagle 5)", "cmdb_ci_hardware"),
    ("Hailo-10H AI Processor", "Edge TPU attached to Node .73 via PCIe", "cmdb_ci_hardware"),
    ("Realtek RTL9210 M.2 NVME Adapter", "External 1TB USB SSD Vault on Node .73", "cmdb_ci_hardware"),
    ("Silicon Motion Flash Drive", "Boot/Utility Drive on Node .73", "cmdb_ci_hardware"),
    ("Powered USB Hub (Node .73)", "Peripheral load manager for Eagle 5", "cmdb_ci_hardware"),
    ("Active Cooling System", "Eagle 5 Ice Tower / Fan assembly", "cmdb_ci_hardware"),
    ("HD Desk Webcam", "Logitech-style webcam mounted on desk acting as Omega Gate Eye", "cmdb_ci_hardware"),
    ("65-inch TV/Display", "Primary broadcast endpoint casting MLB/Vientos feed", "cmdb_ci_hardware"),
    ("ASUS Center Monitor", "Secondary display", "cmdb_ci_hardware"),
    ("Dell Laptop", "Terminal running Omega Gate Live Edge DVR UI on Port 5051", "cmdb_ci_hardware"),
    ("BCM2712 PCIe Bridge", "Logical CI - PCIe Bridge on Node .73", "cmdb_ci_hardware"),
    ("RP1 PCIe 2.0 South Bridge", "Logical CI - South Bridge on Node .73", "cmdb_ci_hardware"),

    # Node .183 (Clio)
    ("Node .183 Beelink SER5 MAX", "Clio Dreadnought / Powerhouse Media Server", "cmdb_ci_hardware"),
    ("Microdia IC800 1080P HD", "Webcam attached to Clio", "cmdb_ci_hardware"),
    ("IMC Networks Wireless_Device", "Bluetooth/WiFi adapter on Clio", "cmdb_ci_hardware"),
    ("Logitech Unifying Receiver", "Keyboard/Mouse receiver on Clio", "cmdb_ci_hardware")
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for name, desc, class_name in assets:
    # Check if exists
    cursor.execute("SELECT sys_id FROM cmdb_ci WHERE name=?", (name,))
    res = cursor.fetchone()
    if not res:
        sys_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insert into cmdb_ci
        cursor.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (sys_id, name, class_name, desc, now, now))
        
        # Insert into cmdb_ci_hardware
        cursor.execute("""
            INSERT INTO cmdb_ci_hardware (sys_id, model_id)
            VALUES (?, ?)
        """, (sys_id, name))

conn.commit()
conn.close()
print(f"Successfully ingested {len(assets)} items into CMDB.")
