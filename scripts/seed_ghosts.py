import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def seed_ustreamer():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Get nodes
    nodes = ['calvin', 'grogu', 'artemis', 'pegasus']
    for n in nodes:
        cur.execute("SELECT sys_id FROM cmdb_ci WHERE name = ?", (n,))
        row = cur.fetchone()
        if row:
            hw_sys_id = row[0]
            appl_id = uuid.uuid4().hex
            cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status) VALUES (?, 'uStreamer Daemon', 'cmdb_ci_appl', 1)", (appl_id,))
            cur.execute("INSERT INTO cmdb_ci_appl (sys_id, process_name, process_cmd) VALUES (?, 'uStreamer', '/usr/bin/ustreamer --device=/dev/video0 -m MJPEG -r 1920x1080')", (appl_id,))
            rel_id = uuid.uuid4().hex
            cur.execute("INSERT INTO cmdb_rel_ci (sys_id, parent, child, type) VALUES (?, ?, ?, 'Runs on::Runs')", (rel_id, hw_sys_id, appl_id))
            print(f"Seeded uStreamer for {n}")
            
            # also tailscale
            tail_id = uuid.uuid4().hex
            cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status) VALUES (?, 'Tailscale Daemon', 'cmdb_ci_appl', 1)", (tail_id,))
            cur.execute("INSERT INTO cmdb_ci_appl (sys_id, process_name, process_cmd) VALUES (?, 'Tailscale', '/usr/sbin/tailscaled')", (tail_id,))
            rel_id = uuid.uuid4().hex
            cur.execute("INSERT INTO cmdb_rel_ci (sys_id, parent, child, type) VALUES (?, ?, ?, 'Runs on::Runs')", (rel_id, hw_sys_id, tail_id))
    
    con.commit()
    con.close()

if __name__ == '__main__':
    seed_ustreamer()
