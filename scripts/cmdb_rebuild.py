import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Purge garden and hardware from cmdb_ci
cur.execute("DELETE FROM cmdb_ci_garden")
cur.execute("DELETE FROM cmdb_ci_hardware")
cur.execute("DELETE FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_garden'")
cur.execute("DELETE FROM cmdb_ci WHERE sys_class_name = 'cmdb_ci_hardware'")
con.commit()

with open('/home/james/stacklabs/dna/dropzone/daily_29042026/attfvvfdjd_network.md', 'r') as f:
    lines = f.readlines()

def insert_ci(name, ip, cls='cmdb_ci_hardware', short_desc=''):
    sys_id = str(uuid.uuid4())
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status) VALUES (?, ?, ?, ?, 1)", (sys_id, name, cls, short_desc))
    cur.execute("INSERT INTO cmdb_ci_hardware (sys_id, ip_address, mac_address, model_id) VALUES (?, ?, '', '')", (sys_id, ip))

for line in lines:
    if not line.strip() or 'Device IP' in line:
        continue
    parts = line.split('\t')
    if len(parts) > 0:
        ip_name = parts[0].strip()
        if ' / ' in ip_name:
            ip, name = ip_name.split(' / ', 1)
            ip = ip.strip()
            name = name.strip()
            
            insert_ci(name, ip)

# Insert attached logical/physical devices
insert_ci("clio-webcam-1", "", short_desc="Attached Logitech Webcam")
insert_ci("clio-suzie-q", "", short_desc="Attached Suzie Q Mic")
insert_ci("argo-vision-cam", "", short_desc="Hailo AI Feed Camera")

con.commit()
print("CMDB rebuilt successfully.")
