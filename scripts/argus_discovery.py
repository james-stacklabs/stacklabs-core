import sqlite3
import uuid
import subprocess
import json

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def load_target_nodes_from_cmdb():
    nodes = {}
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT h.ip_address, c.name, c.short_description
            FROM cmdb_ci c
            JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id
            WHERE h.ip_address IS NOT NULL AND h.ip_address != ''
        """)
        rows = cur.fetchall()
        
        system_hosts = {'clio', 'argo', 'hobbes', 'calvin', 'grogu', 'artemis', 'pegasus', 'metsy-prime'}
        
        for ip, name, desc in rows:
            name_lower = name.lower()
            desc_lower = desc.lower() if desc else ""
            
            is_cam = ('c120' in name_lower or 'cam' in name_lower or 
                      'camera' in desc_lower or 'webcam' in desc_lower)
            
            if name_lower in system_hosts:
                nodes[ip] = (name_lower, "host")
            elif is_cam:
                nodes[ip] = (name, "camera")
        con.close()
    except Exception as e:
        print(f"[DB ERROR] Failed to load target nodes from CMDB: {e}")
        
    if not nodes:
        nodes = {
            "192.168.1.183": ("clio", "host"),
            "192.168.1.75": ("argo", "host"),
            "192.168.1.114": ("hobbes", "host"),
            "192.168.1.115": ("calvin", "host"),
            "192.168.1.117": ("grogu", "host"),
            "192.168.1.64": ("artemis", "host"),
            "192.168.1.177": ("pegasus", "host")
        }
    return nodes


def get_or_create_hardware_ci(cur, ip, name):
    # Check if exists by IP or Name
    cur.execute("SELECT c.sys_id FROM cmdb_ci c JOIN cmdb_ci_hardware h ON c.sys_id = h.sys_id WHERE h.ip_address = ? OR c.name = ?", (ip, name))
    row = cur.fetchone()
    if row:
        # Update IP just in case
        cur.execute("UPDATE cmdb_ci_hardware SET ip_address = ? WHERE sys_id = ?", (ip, row[0]))
        return row[0]
    
    # Create new
    sys_id = uuid.uuid4().hex
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status) VALUES (?, ?, 'cmdb_ci_hardware', 1)", (sys_id, name))
    cur.execute("INSERT INTO cmdb_ci_hardware (sys_id, ip_address) VALUES (?, ?)", (sys_id, ip))
    return sys_id

def create_application_ci(cur, process_name, cmdline):
    sys_id = uuid.uuid4().hex
    name = f"{process_name} Daemon"
    cur.execute("INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status) VALUES (?, ?, 'cmdb_ci_appl', 1)", (sys_id, name))
    cur.execute("INSERT INTO cmdb_ci_appl (sys_id, process_name, process_cmd) VALUES (?, ?, ?)", (sys_id, process_name, cmdline))
    return sys_id

def create_relationship(cur, parent_id, child_id, rel_type="Runs on::Runs"):
    # Check if exists
    cur.execute("SELECT sys_id FROM cmdb_rel_ci WHERE parent = ? AND child = ? AND type = ?", (parent_id, child_id, rel_type))
    if not cur.fetchone():
        rel_id = uuid.uuid4().hex
        cur.execute("INSERT INTO cmdb_rel_ci (sys_id, parent, child, type) VALUES (?, ?, ?, ?)", (rel_id, parent_id, child_id, rel_type))

def scan_node(ip, name):
    print(f"\n[SCANNING] {name} ({ip})...")
    
    cmd = f"ssh -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=no james@{ip} \"ps -eo cmd --no-headers | grep -E 'python|node|ustreamer|tailscaled' | grep -v grep\""
    if ip == "192.168.1.183":
        cmd = "ps -eo cmd --no-headers | grep -E 'python|node|ustreamer|tailscaled' | grep -v grep"
        
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if res.returncode != 0 and ip != "192.168.1.183":
            print(f"  [ERROR] SSH failed or no processes found. (RC: {res.returncode})")
            return []
        
        processes = []
        for line in res.stdout.strip().split('\n'):
            line = line.strip()
            if not line: continue
            
            # Categorize the process
            proc_name = "Unknown"
            if 'ustreamer' in line: proc_name = "uStreamer"
            elif 'tailscaled' in line: proc_name = "Tailscale"
            elif 'fanstack_server.py' in line: proc_name = "MLB Telemetry Poller"
            elif 'fanstack_relay.py' in line: proc_name = "M.A.R.D WebSocket Engine"
            elif 'persona_manager_server.py' in line: proc_name = "Persona LLM Engine"
            elif 'python' in line: proc_name = "Python Daemon"
            elif 'node' in line: proc_name = "NodeJS App"
            
            # Avoid generic python/node if too vague, or just log them
            if "bash" in line or "ssh" in line: continue
            
            processes.append({
                "process_name": proc_name,
                "cmdline": line[:100] # truncate
            })
            
        print(f"  [SUCCESS] Found {len(processes)} relevant services.")
        return processes
    except Exception as e:
        print(f"  [TIMEOUT/ERROR] {str(e)}")
        return []

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    target_nodes = load_target_nodes_from_cmdb()
    for ip, (name, node_type) in target_nodes.items():
        # Ensure HW node exists
        hw_sys_id = get_or_create_hardware_ci(cur, ip, name)
        
        if node_type == "camera":
            print(f"\n[SCANNING CAMERA] {name} ({ip})...")
            # Network cameras are verified via ping instead of SSH
            ping_cmd = f"ping -c 1 -W 2 {ip}"
            res = subprocess.run(ping_cmd, shell=True, capture_output=True)
            status = "Online" if res.returncode == 0 else "Offline"
            print(f"  [STATUS] Camera {name} is {status}.")
            
            # Update operational status
            op_status = 1 if status == "Online" else 2
            cur.execute("UPDATE cmdb_ci SET operational_status = ? WHERE sys_id = ?", (op_status, hw_sys_id))
            continue
            
        # Scan processes
        processes = scan_node(ip, name)
        
        # For each process, create Appl CI and Link it
        for proc in processes:
            # Simple deduplication per node: does this hw_sys_id already have an appl with this cmdline?
            cur.execute("""
                SELECT a.sys_id FROM cmdb_ci_appl a 
                JOIN cmdb_rel_ci r ON a.sys_id = r.child 
                WHERE r.parent = ? AND a.process_cmd = ?
            """, (hw_sys_id, proc['cmdline']))
            
            row = cur.fetchone()
            if not row:
                appl_sys_id = create_application_ci(cur, proc['process_name'], proc['cmdline'])
                create_relationship(cur, hw_sys_id, appl_sys_id)
                print(f"  -> Linked {proc['process_name']} to {name}")
            else:
                print(f"  -> {proc['process_name']} already mapped.")
                
    con.commit()
    con.close()
    print("\n[COMPLETE] Argus Discovery Run Finished.")


if __name__ == '__main__':
    main()
