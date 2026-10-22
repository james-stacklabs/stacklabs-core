#!/usr/bin/env python3
import sqlite3
import uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def seed_cmdb():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    print("Beginning CMDB Physical Asset Seeding...")

    # Hardware CIs to create
    # Format: (sys_id, name, class_name, short_desc, operational_status, ip, mac, model_id)
    hardware_items = [
        ("argo", "argo", "cmdb_ci_hardware", "Tailscale primary server node running service containers", 1, "192.168.1.150", "00:11:32:8A:4F:92", "ASUS PN64 Mini PC"),
        ("argo_usb_hub", "argo-usb-hub", "cmdb_ci_hardware", "High-speed powered USB 3.0 hub connected to argo", 1, "", "", "SABRENT 7-Port Powered Hub"),
        ("argo_1tb_drive", "argo-1tb-drive", "cmdb_ci_hardware", "Primary 1TB external storage drive ('ghost drive')", 1, "", "", "Samsung T7 Portable SSD"),
        ("govee_light_1", "govee-smart-light", "cmdb_ci_hardware", "IoT Smart LED lighting strip in office", 1, "192.168.1.182", "34:85:18:9B:C1:22", "Govee H6159 Strip Light"),
        ("govee_hygrometer_1", "govee-hygrometer", "cmdb_ci_hardware", "IoT climate & humidity environment sensor", 1, "192.168.1.194", "E4:F5:28:C9:F0:8A", "Govee H5075 Temp/Hygrometer")
    ]

    for item in hardware_items:
        sys_id, name, class_name, desc, status, ip, mac, model = item
        
        # Insert into cmdb_ci if not exists
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        if not cur.fetchone():
            print(f"Seeding parent CI: {name} ({sys_id})")
            cur.execute("""
                INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to)
                VALUES (?, ?, ?, ?, ?, 'james')
            """, (sys_id, name, class_name, desc, status))
            
            # Insert into cmdb_ci_hardware
            cur.execute("""
                INSERT INTO cmdb_ci_hardware (sys_id, ip_address, mac_address, model_id)
                VALUES (?, ?, ?, ?)
            """, (sys_id, ip, mac, model))
        else:
            print(f"CI {name} ({sys_id}) already exists, skipping seed.")

    # Relationships to define in cmdb_rel_ci
    # Format: (parent_sys_id, child_sys_id, relationship_type)
    relationships = [
        ("argo", "argo_usb_hub", "Depends on::Used by"),
        ("argo_usb_hub", "argo_1tb_drive", "Depends on::Used by"),
        ("argo", "571bfb0786664c46bf2a1c98fd0e64fe", "Connected To::Connected From"), # metsy-prime -> argo
        ("argo", "394fb1c427a142549c9d7718d4867888", "Connected To::Connected From")  # clio -> argo
    ]

    for rel in relationships:
        parent, child, rel_type = rel
        
        # Check if relationship already exists
        cur.execute("SELECT sys_id FROM cmdb_rel_ci WHERE parent = ? AND child = ? AND type = ?", (parent, child, rel_type))
        if not cur.fetchone():
            rel_sys_id = uuid.uuid4().hex
            print(f"Seeding relationship: {parent} -> {child} ({rel_type})")
            cur.execute("""
                INSERT INTO cmdb_rel_ci (sys_id, parent, child, type)
                VALUES (?, ?, ?, ?)
            """, (rel_sys_id, parent, child, rel_type))
        else:
            print(f"Relationship {parent} -> {child} ({rel_type}) already exists, skipping.")

    con.commit()
    con.close()
    print("CMDB Seeding Completed Successfully!")

if __name__ == "__main__":
    seed_cmdb()
