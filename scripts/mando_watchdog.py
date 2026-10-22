#!/usr/bin/env python3
import socket
import time
import subprocess
import uuid
import sqlite3
import os
import datetime
import urllib.request
import json

# Mando Watchdog Configuration
TARGET_HOST = "clio.taila01894.ts.net"  # Tailscale hostname, NO hardcoded IP (KI-001)
CHECK_INTERVAL = 30  # Polling interval in seconds
COOLDOWN_PERIOD = 3600  # 1 hour cooldown per incident / service

# DB Path (KI-038)
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

# Services to monitor
# Services to monitor with their designated identity verification keywords
SERVICES = {
    "Sovereign OS Portal": {
        "port": 3016,
        "ci": "SovereignPortal",
        "keyword": "Sovereign",
        "restart_cmd": "cd /home/james/stacklabs/01_Sovereign_Portal && nohup npm run dev -- --force --port 3016 >> /home/james/stacklabs/logs/vite_portal.log 2>&1 &"
    },

    "Sovereign Core API": {
        "port": 8090,
        "ci": "SovereignCore",
        "keyword": "fastapi",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/sovereign_core_api.py >> /home/james/stacklabs/logs/sovereign_core_8090.log 2>&1 &"
    },
    "SDLC Ticketing Server": {
        "port": 8095,
        "ci": "SDLC",
        "keyword": "sdlc",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/sdlc_portal_server.py >> /home/james/stacklabs/logs/sdlc_portal_server.log 2>&1 &"
    },
    "JIT Mobile Approval Gateway": {
        "port": 3027,
        "ci": "app_3027_44eb1a",
        "keyword": "Sovereign",
        "restart_cmd": "sudo systemctl restart jit_approval_gateway.service"
    },
    "Sovereign CMDB Studio": {
        "port": 3025,
        "ci": "25_CmdbStudio",
        "keyword": "CMDB",
        "restart_cmd": "sudo systemctl restart cmdb_studio.service"
    },
    "Sovereign Power Tools": {
        "port": 3028,
        "ci": "26_MARD_Studio",
        "keyword": "mard-studio",
        "restart_cmd": "cd /home/james/stacklabs/26_MARD_Studio && nohup npm run dev -- --force --host 0.0.0.0 --port 3028 >> /home/james/stacklabs/logs/vite_powertools.log 2>&1 &"
    },
    "Sovereign Mobile Ticket App": {
        "port": 3029,
        "ci": "28_Sovereign_Mobile_Dispatch",
        "keyword": "SOVEREIGN DISPATCH",
        "restart_cmd": "sudo systemctl restart mobile_ticket_app.service"
    },
    "FanStack Relay Hub": {
        "port": 8000,
        "ci": "FanStackRelay",
        "keyword": "Sovereign",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 -u /home/james/stacklabs/scripts/fanstack_relay.py >> /home/james/stacklabs/logs/fanstack_relay.log 2>&1 &"
    },
    "MARD Chat Engine": {
        "port": None,
        "script": "scripts/fanstack_chatbots.py",
        "ci": "MARDChatEngine",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 -u /home/james/stacklabs/scripts/fanstack_chatbots.py >> /home/james/stacklabs/logs/fanstack_chatbots.log 2>&1 &"
    },
    "FanStack Telemetry Poller": {
        "port": None,
        "script": "scripts/fanstack_background_poller.py",
        "ci": "FanStackPoller",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 -u /home/james/stacklabs/scripts/fanstack_background_poller.py >> /home/james/stacklabs/logs/fanstack_background_poller.log 2>&1 &"
    },

    "StackLabs Benchmark Console": {
        "port": 8080,
        "ci": "app_stacklabs_benchmark",
        "keyword": "StackLabs",
        "restart_cmd": "cd /home/james/stacklabs && nohup /home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/demo_funnel_gateway.py >> /home/james/stacklabs/logs/demo_funnel_8080.log 2>&1 &"
    }
}

active_incidents = {}
active_paa7_tickets = {}   # Maps port -> list of ticket numbers [str]
paa7_failures = {}        # Maps port -> consecutive failure count
active_hardware_incident = None

def verify_port_identity(port, expected_keyword):
    """PAA-7 identity verification check: Probes port and looks for expected keyword."""
    import ssl
    
    # Check if port is open first
    if not check_port(TARGET_HOST, port):
        return False, "DARK"
        
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    paths = ["/", "/docs"]
    if port == 3008:
        paths.append("/cinema-portal/")
        
    targets = ["127.0.0.1", TARGET_HOST]
    for target in targets:
        for protocol in ["http", "https"]:
            for path in paths:
                url = f"{protocol}://{target}:{port}{path}"
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'PAA7-Watchdog/1.0'})
                    with urllib.request.urlopen(req, context=ctx, timeout=2) as response:
                        content = response.read().decode('utf-8', errors='ignore')
                        # Check keyword or common Sovereign OS keywords
                        if expected_keyword.lower() in content.lower():
                            return True, "OK"
                        if port in (3009, 3010) and ("sovereign" in content.lower() or "fanstack" in content.lower()):
                            return True, "OK"
                        if port == 8080 and ("stacklabs" in content.lower() or "visual twin" in content.lower()):
                            return True, "OK"
                        if "docs" in path and ("swagger" in content.lower() or "redoc" in content.lower()):
                            return True, "OK"
                except Exception:
                    pass
        
    return False, "SQUATTERS"

def generate_paa7_incident_ticket(port, incident_type, desc, ci="PortAuthority"):
    """Generates an INC incident ticket in the database for a Port Authority drift/squatter violation, checking for existing active tickets first."""
    existing_sql = "SELECT number FROM sovereign_tickets WHERE state < 4 AND short_description LIKE ?;"
    existing_rows = fetch_db_rows(existing_sql, (f"PAA-7 PORT AUTHORITY ALERT: Port {port}%",))
    if existing_rows and len(existing_rows) > 0 and existing_rows[0]:
        inc_num = existing_rows[0][0]
        print(f"[PAA-7] Active ticket {inc_num} already exists for port {port}. Re-using ticket (suppressing duplicate).")
        return inc_num

    sys_id = uuid.uuid4().hex
    import random
    inc_num = f"INC{random.randint(1780000, 1789999)}"
    short_desc = f"PAA-7 PORT AUTHORITY ALERT: Port {port} {incident_type}"
    
    sql = """
    INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on) 
    VALUES (?, ?, 'INC', ?, ?, 1, 2, 'james', ?, 'Port Authority PAA-7 integrity violation detected.', ?, ?);
    """
    now_str = datetime.datetime.now().isoformat()
    if execute_db_query(sql, (sys_id, inc_num, short_desc, desc, ci, now_str, now_str)):
        print(f"[PAA-7] Generated incident ticket {inc_num} for port {port} violation: {incident_type}")
        return inc_num
    return None

def resolve_paa7_tickets(port):
    """Auto-resolves/closes all active PAA-7 tickets for the given port when it returns to manifest compliance."""
    global active_paa7_tickets
    ticket_list = active_paa7_tickets.get(port, [])
    if not ticket_list:
        return
    print(f"[PAA-7] Port {port} recovered. Resolving {len(ticket_list)} active ticket(s): {ticket_list}...")
    now_str = datetime.datetime.now().isoformat()
    for t_num in ticket_list:
        sql = "UPDATE sovereign_tickets SET state = 4, sys_updated_on = ?, work_notes = COALESCE(work_notes, '') || char(10) || '[PAA-7 Watchdog] Port integrity recovered and verified. Resolving ticket.' WHERE number = ?;"
        execute_db_query(sql, (now_str, t_num))
    active_paa7_tickets[port] = []

def check_port(host, port):
    """Check if a TCP port is open. Tries 127.0.0.1 first, then the Tailscale host."""
    for target in ["127.0.0.1", host]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((target, port))
            if result == 0:
                return True
        except Exception:
            pass
        finally:
            sock.close()
    return False

def check_process_running(script_name):
    """Check if a process is running locally or via SSH fallback."""
    target_cmd = f"pgrep -f {script_name}"
    if os.path.exists(DB_PATH):
        try:
            res = subprocess.run(target_cmd, shell=True, capture_output=True)
            return res.returncode == 0
        except Exception:
            return False
    else:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
            f"james@{TARGET_HOST}", target_cmd
        ]
        try:
            res = subprocess.run(ssh_cmd, capture_output=True)
            return res.returncode == 0
        except Exception:
            return False

def execute_db_query(sql, params=()):
    """Executes a database query locally or via SSH fallback."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Local SQL Error: {e}")
            return False
    else:
        # Fallback to SSH via Tailscale Hostname (KI-001)
        formatted_sql = sql
        for p in params:
            if isinstance(p, str):
                escaped_p = p.replace("'", "''")
                formatted_sql = formatted_sql.replace("?", f"'{escaped_p}'", 1)
            else:
                formatted_sql = formatted_sql.replace("?", str(p), 1)
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
            f"james@{TARGET_HOST}",
            f'sqlite3 {DB_PATH} "{formatted_sql.strip()}"'
        ]
        try:
            subprocess.run(ssh_cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"SSH DB Error: {e.stderr.decode('utf-8')}")
            return False

def fetch_db_val(sql, params=()):
    """Fetches a single database value locally or via SSH fallback."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            print(f"Local Fetch SQL Error: {e}")
            return None
    else:
        # Fallback to SSH via Tailscale Hostname (KI-001)
        formatted_sql = sql
        for p in params:
            if isinstance(p, str):
                escaped_p = p.replace("'", "''")
                formatted_sql = formatted_sql.replace("?", f"'{escaped_p}'", 1)
            else:
                formatted_sql = formatted_sql.replace("?", str(p), 1)
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
            f"james@{TARGET_HOST}",
            f'sqlite3 {DB_PATH} "{formatted_sql.strip()}"'
        ]
        try:
            res = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True)
            out = res.stdout.strip()
            return out if out else None
        except subprocess.CalledProcessError as e:
            print(f"SSH DB Fetch Error: {e.stderr}")
            return None

def fetch_db_rows(sql, params=()):
    """Fetches multiple rows from database locally or via SSH fallback."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"Local Fetch Rows SQL Error: {e}")
            return []
    else:
        # Fallback to SSH via Tailscale Hostname (KI-001)
        formatted_sql = sql
        for p in params:
            if isinstance(p, str):
                escaped_p = p.replace("'", "''")
                formatted_sql = formatted_sql.replace("?", f"'{escaped_p}'", 1)
            else:
                formatted_sql = formatted_sql.replace("?", str(p), 1)
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
            f"james@{TARGET_HOST}",
            f'sqlite3 {DB_PATH} "{formatted_sql.strip()}"'
        ]
        try:
            res = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True)
            out = res.stdout.strip()
            rows = []
            if out:
                for line in out.splitlines():
                    rows.append(line.split('|'))
            return rows
        except subprocess.CalledProcessError as e:
            print(f"SSH DB Fetch Rows Error: {e.stderr}")
            return []

def load_active_paa7_tickets():
    """Queries the database to load any active (state < 4) PAA-7 tickets (supporting both legacy STRY and INC)."""
    global active_paa7_tickets
    sql = "SELECT number, short_description FROM sovereign_tickets WHERE state < 4 AND short_description LIKE 'PAA-7 PORT AUTHORITY ALERT: Port %';"
    rows = fetch_db_rows(sql)
    for row in rows:
        if len(row) >= 2:
            num, short_desc = row[0], row[1]
            try:
                parts = short_desc.split("Port ")
                if len(parts) > 1:
                    port_str = parts[1].split()[0]
                    port = int(port_str)
                    if port not in active_paa7_tickets:
                        active_paa7_tickets[port] = []
                    if num not in active_paa7_tickets[port]:
                        active_paa7_tickets[port].append(num)
                    print(f"[PAA-7] Loaded active ticket {num} for Port {port} from database.")
            except Exception as e:
                print(f"[PAA-7] Failed to parse port from ticket {num} ({short_desc}): {e}")

def load_active_incidents():
    """Queries the database to load any active (state < 4) INC tickets."""
    global active_incidents
    sql = "SELECT number, short_description FROM sovereign_tickets WHERE type = 'INC' AND state < 4 AND short_description LIKE 'CRITICAL: % Offline';"
    rows = fetch_db_rows(sql)
    for row in rows:
        if len(row) >= 2:
            num, short_desc = row[0], row[1]
            try:
                service_name = short_desc.replace("CRITICAL: ", "").replace(" Offline", "")
                active_incidents[service_name] = {"time": time.time(), "inc_num": num}
                print(f"[Watchdog] Loaded active incident {num} for service '{service_name}' from database.")
            except Exception as e:
                print(f"[Watchdog] Failed to parse service name from incident {num} ({short_desc}): {e}")

def load_active_hardware_incident():
    """Queries the database to load any active hardware telemetry incident."""
    global active_hardware_incident
    sql = "SELECT number FROM sovereign_tickets WHERE type = 'INC' AND state < 4 AND short_description LIKE 'CRITICAL: Hardware Telemetry Breached%';"
    rows = fetch_db_rows(sql)
    if rows and len(rows[0]) > 0:
        num = rows[0][0]
        active_hardware_incident = {"time": time.time(), "inc_num": num}
        print(f"[Watchdog] Loaded active hardware incident {num} from database.")

def get_expression_avatar(ci):
    """Fetch expression avatar URL from the database for the given CI system."""
    target_ci_sys_id = "ci_metsy_prime" if ci == "SamTracker" else "ci_mando"
    avatar = fetch_db_val("SELECT avatar_url FROM cmdb_ci_expression_avatar WHERE ci_sys_id = ?", (target_ci_sys_id,))
    if avatar:
        return avatar
    return "/avatars/mando/mando_warning.png"

def update_ci_status(ci_sys_id, status_int):
    """Updates operational_status of a CI node in the database."""
    sql = "UPDATE cmdb_ci SET operational_status = ? WHERE sys_id = ?;"
    execute_db_query(sql, (status_int, ci_sys_id))

def is_ci_in_maintenance(ci):
    """
    Enterprise ITSM Maintenance Check (ENHC2026082203):
    Queries cmdb_ci table. Returns True if operational_status == 2 (Maintenance/Hibernation) or 3 (Retired).
    Returns False if operational_status == 1 (Operational) or not found.
    """
    sql = "SELECT operational_status FROM cmdb_ci WHERE name = ? OR sys_id = ? LIMIT 1;"
    status = fetch_db_val(sql, (ci, ci))
    if status is not None:
        try:
            return int(status) in (2, 3)
        except Exception:
            return False
    return False

def trigger_websocket_broadcast():
    """Triggers an immediate WebSocket system broadcast via FanStack Relay."""
    url = "http://127.0.0.1:8000/api/system/broadcast"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=2) as response:
            pass
    except Exception as e:
        print(f"Failed to trigger WebSocket broadcast: {e}")

def dispatch_comet_alert(service_name, ci, inc_num, avatar_url):
    """Dispatches a priority alert HTTP POST to the Comet Relay webhook."""
    url = "http://127.0.0.1:8015/webhook/alert"
    payload = {
        "alert_type": f"CRITICAL: {service_name} Offline",
        "service_name": service_name,
        "ci": ci,
        "sys_ticket_id": inc_num,
        "avatar_url": avatar_url
    }
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            pass
    except Exception as e:
        print(f"[COMET DISPATCH] Failed to send alert to Comet Relay: {e}")

def dispatch_comet_resolve(service_name, inc_num):
    """Dispatches a priority resolution HTTP POST to the Comet Relay webhook."""
    url = "http://127.0.0.1:8015/webhook/resolve"
    payload = {
        "sys_ticket_id": inc_num,
        "service_name": service_name
    }
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            pass
    except Exception as e:
        print(f"[COMET DISPATCH] Failed to send resolve to Comet Relay: {e}")

def dispatch_mando_repair_overlay(service_name="SYSTEM", reason="AUTOMATED AUTO-HEAL RESTORATION"):
    """Dispatches Mando Robot Repair broadcast overlay to FanStack Relay."""
    url = "http://127.0.0.1:8000/api/overlay/mando-repair"
    payload = {
        "target_game_pk": "GLOBAL",
        "reason": f"{service_name}: {reason}"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            pass
        print(f"[MANDO WATCHDOG] 🛠️ Dispatched Mando Robot Repair overlay for {service_name}")
    except Exception as e:
        print(f"[MANDO WATCHDOG] Failed to dispatch Mando overlay: {e}")

def generate_service_ticket(service_name, ci):
    """Generates an INC ticket for a down port or service, checking for existing active tickets first."""
    existing_sql = "SELECT number FROM sovereign_tickets WHERE type = 'INC' AND state < 4 AND (cmdb_ci = ? OR short_description LIKE ?);"
    existing_rows = fetch_db_rows(existing_sql, (ci, f"%{service_name}%"))
    if existing_rows and len(existing_rows) > 0 and existing_rows[0]:
        existing_num = existing_rows[0][0]
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Active INC {existing_num} already exists for {service_name}. Re-using ticket (suppressing duplicate).")
        return existing_num

    sys_id = uuid.uuid4().hex
    import random
    inc_num = f"INC{random.randint(1000000, 9999999)}"
    short_desc = f"CRITICAL: {service_name} Offline"
    desc = f"The Mando Watchdog detected that {service_name} is no longer responding on its designated port on {TARGET_HOST}."
    
    sql = """
    INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on) 
    VALUES (?, ?, 'INC', ?, ?, 1, 1, 'Antigravity', ?, 'Ticket auto-generated by Mando Watchdog.', ?, ?);
    """
    now_str = datetime.datetime.now().isoformat()
    if execute_db_query(sql, (sys_id, inc_num, short_desc, desc, ci, now_str, now_str)):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully generated ticket {inc_num} for {service_name}.")
        return inc_num
    return None

def resolve_service_ticket(inc_num, service_name):
    """Auto-resolves all active INC tickets for the service when it recovers."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {service_name} recovered. Auto-resolving ticket(s)...")
    sql = """
    UPDATE sovereign_tickets 
    SET state = 4, sys_updated_on = ?, 
        work_notes = COALESCE(work_notes, '') || char(10) || '[Mando Watchdog] Service recovered. Auto-resolving ticket.' 
    WHERE type = 'INC' AND state < 4 AND (number = ? OR short_description LIKE ?);
    """
    execute_db_query(sql, (datetime.datetime.now().isoformat(), inc_num, f"%{service_name}%"))
    dispatch_comet_resolve(service_name, inc_num)

# Hardware Metrics Resolution
def get_cpu_load():
    try:
        with open("/proc/loadavg", "r") as f:
            return float(f.read().split()[0])
    except Exception:
        return 0.0

def get_memory_usage():
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].replace(":", "")] = int(parts[1])
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", 0)
        if available > 0 and total > 0:
            used = total - available
            ram_pct = (used / total) * 100.0
        else:
            free = meminfo.get("MemFree", 0)
            buffers = meminfo.get("Buffers", 0)
            cached = meminfo.get("Cached", 0)
            used = total - free - buffers - cached
            ram_pct = (used / total) * 100.0 if total > 0 else 0.0
        
        swap_total = meminfo.get("SwapTotal", 0)
        swap_free = meminfo.get("SwapFree", 0)
        if swap_total > 0:
            swap_used = swap_total - swap_free
            swap_pct = (swap_used / swap_total) * 100.0
        else:
            swap_pct = 0.0
            # Auto-re-enable swap if configured in /etc/fstab but deactivated
            try:
                subprocess.run("sudo swapon -a", shell=True, capture_output=True)
            except Exception:
                pass
        
        return ram_pct, swap_pct
    except Exception:
        return 0.0, 0.0

def get_cpu_temp():
    try:
        for p in ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"]:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return float(f.read().strip()) / 1000.0
    except Exception:
        pass
    return 45.0

def get_top_cpu_processes():
    try:
        res = subprocess.run("ps -eo pcpu,pmem,args --sort=-pcpu | head -n 6", shell=True, capture_output=True, text=True)
        return res.stdout
    except Exception:
        return "Unknown"

def monitor_hardware():
    global active_hardware_incident
    cpu_load = get_cpu_load()
    ram_use, swap_use = get_memory_usage()
    cpu_temp = get_cpu_temp()
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telemetry check -> CPU Load: {cpu_load:.2f}, RAM: {ram_use:.1f}%, Swap: {swap_use:.1f}%, Temp: {cpu_temp:.1f}°C")
    
    # Thresholds
    breached = []
    if cpu_load > 20.0:
        breached.append(f"CPU Load ({cpu_load:.2f} > 20)")
    if ram_use > 85.0:
        breached.append(f"RAM Usage ({ram_use:.1f}% > 85%)")
    if swap_use > 90.0:
        breached.append(f"Swap Usage ({swap_use:.1f}% > 90%)")
    if cpu_temp > 80.0:
        breached.append(f"CPU Temp ({cpu_temp:.1f}°C > 80°C)")
        
    if breached:
        existing_sql = "SELECT number FROM sovereign_tickets WHERE type = 'INC' AND state < 4 AND short_description LIKE 'CRITICAL: Hardware Telemetry Breached%';"
        existing_rows = fetch_db_rows(existing_sql)
        if existing_rows and len(existing_rows) > 0 and existing_rows[0]:
            inc_num = existing_rows[0][0]
            if not active_hardware_incident:
                active_hardware_incident = {"time": time.time(), "inc_num": inc_num}
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Active hardware incident {inc_num} already exists. Re-using ticket (suppressing duplicate).")
        elif not active_hardware_incident:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Hardware threshold breached: {', '.join(breached)}! Generating incident...")
            
            sys_id = uuid.uuid4().hex
            import random
            inc_num = f"INC{random.randint(1000000, 9999999)}"
            
            top_procs = get_top_cpu_processes()
            
            # Find the top process name to suggest killing
            top_proc_name = "unknown"
            try:
                lines = top_procs.strip().split("\n")
                if len(lines) > 1:
                    top_proc_name = lines[1].split()[-1]
            except Exception:
                pass
                
            short_desc = f"CRITICAL: Hardware Telemetry Breached - {', '.join(breached)}"
            desc = (
                f"Sovereign Hardware Telemetry Alert!\n"
                f"Metrics Breached:\n"
                f"- CPU Load: {cpu_load:.2f} (Threshold: 20.0)\n"
                f"- RAM Usage: {ram_use:.1f}% (Threshold: 85.0%)\n"
                f"- Swap Usage: {swap_use:.1f}% (Threshold: 50.0%)\n"
                f"- CPU Temp: {cpu_temp:.1f}°C (Threshold: 80.0°C)\n\n"
                f"Top CPU Consuming Processes:\n"
                f"{top_procs}\n\n"
                f"Recommended Mitigation:\n"
                f"Consider killing process '{top_proc_name}' immediately to alleviate load."
            )
            
            sql = """
            INSERT INTO sovereign_tickets (sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on) 
            VALUES (?, ?, 'INC', ?, ?, 1, 1, 'Antigravity', 'cmdb_ci_hardware', 'Hardware threshold breach auto-generated ticket.', ?, ?);
            """
            now_str = datetime.datetime.now().isoformat()
            if execute_db_query(sql, (sys_id, inc_num, short_desc, desc, now_str, now_str)):
                active_hardware_incident = {"time": time.time(), "inc_num": inc_num}
                avatar_url = get_expression_avatar("cmdb_ci_hardware")
                dispatch_comet_alert("Hardware Telemetry", "cmdb_ci_hardware", inc_num, avatar_url)
    else:
        if active_hardware_incident:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Hardware telemetry recovered. Auto-resolving ticket {active_hardware_incident['inc_num']}...")
            sql = "UPDATE sovereign_tickets SET state = 4, sys_updated_on = ?, work_notes = COALESCE(work_notes, '') || char(10) || '[Mando Watchdog] Hardware metrics recovered within limits.' WHERE type = 'INC' AND state < 4 AND short_description LIKE 'CRITICAL: Hardware Telemetry Breached%';"
            execute_db_query(sql, (datetime.datetime.now().isoformat(),))
            dispatch_comet_resolve("Hardware Telemetry", active_hardware_incident["inc_num"])
            active_hardware_incident = None

    # High swap usage alert - DO NOT run swapoff -a under load (causes instant kernel OOM panic)
    if swap_use > 90.0:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Swap usage high ({swap_use:.1f}% > 90%). Preserving swap pages to prevent OOM panic.")

def main():
    print("=========================================")
    print("   Sovereign Watchdog (Project Mando)    ")
    print("=========================================")
    print(f"Target: {TARGET_HOST}")
    print(f"Polling Interval: {CHECK_INTERVAL}s")
    print("Monitoring services and hardware...")
    
    last_sam_status = 1
    last_mando_status = 1
    global active_hardware_incident
    
    # Load active tickets/incidents from database on startup to prevent redundant alerts (PAA-7 resolution)
    load_active_paa7_tickets()
    load_active_incidents()
    load_active_hardware_incident()
    
    while True:
        now = time.time()
        
        # Check Hardware Telemetry
        monitor_hardware()
        
        # Check Port Services
        for name, info in SERVICES.items():
            port = info.get("port")
            script = info.get("script")
            ci = info["ci"]
            restart_cmd = info.get("restart_cmd")
            
            if port is not None:
                is_up = check_port(TARGET_HOST, port)
            elif script is not None:
                is_up = check_process_running(script)
            else:
                is_up = True
            
            if not is_up:
                # --- ENTERPRISE ITSM CMDB MAINTENANCE GATING (ENHC2026082203) ---
                if is_ci_in_maintenance(ci):
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⏸️ [HIBERNATION] CI '{ci}' ({name}) is in planned maintenance (operational_status = 2). Suppressing INC ticket and auto-restart.")
                    continue

                incident = active_incidents.get(name)
                last_ticket_time = incident["time"] if incident else 0
                if (now - last_ticket_time) > COOLDOWN_PERIOD:
                    desc_str = f"Port {port}" if port is not None else f"Process {script}"
                    
                    if not incident:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {desc_str} down for {name}. Generating INC and attempting Auto-Restart...")
                        inc_num = generate_service_ticket(name, ci)
                        if inc_num:
                            active_incidents[name] = {"time": now, "inc_num": inc_num}
                            avatar_url = get_expression_avatar(ci)
                            dispatch_comet_alert(name, ci, inc_num, avatar_url)
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {name} is still down (Active ticket: {incident['inc_num']}). Retrying Auto-Restart...")
                        active_incidents[name]["time"] = now
                        inc_num = incident["inc_num"]
                    
                    if restart_cmd:
                        ssh_restart = [
                            "ssh", "-f", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", 
                            f"james@{TARGET_HOST}", restart_cmd
                        ]
                        try:
                            subprocess.run(ssh_restart, check=True)
                        except Exception as e:
                            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-Restart execution failed: {e}")
                            
                        time.sleep(10)
                        
                        if port is not None:
                            is_up_now = check_port(TARGET_HOST, port)
                        elif script is not None:
                            is_up_now = check_process_running(script)
                        else:
                            is_up_now = True
                    
                        if is_up_now:
                            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-Restart successful for {name}! Resolving ticket...")
                            if inc_num:
                                resolve_service_ticket(inc_num, name)
                                if name in active_incidents:
                                    del active_incidents[name]
                        else:
                            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Auto-Restart failed. {name} is still down.")
            else:
                if name in active_incidents:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {name} has recovered!")
                    inc_num = active_incidents[name]["inc_num"]
                    resolve_service_ticket(inc_num, name)
                    del active_incidents[name]
            
            # --- PAA-7 Integrity & Identity Checks ---
            if port is not None and "keyword" in info:
                if is_ci_in_maintenance(ci):
                    continue  # Suppress PAA-7 alerts for hibernated ports
                ok, status = verify_port_identity(port, info["keyword"])
                if not ok:
                    paa7_failures[port] = paa7_failures.get(port, 0) + 1
                    print(f"[PAA-7] Port {port} failed integrity check ({status}). Failure count: {paa7_failures[port]}/3")
                    if paa7_failures[port] >= 3:
                        if port not in active_paa7_tickets or not active_paa7_tickets[port]:
                            desc = f"PAA-7 Port Authority Alert!\nService: {name}\nPort: {port}\nStatus: {status}\n3 consecutive cycles of integrity drift/squatting detected. Action Required: Realign service port binding."
                            t_num = generate_paa7_incident_ticket(port, status, desc, ci)
                            if t_num:
                                if port not in active_paa7_tickets:
                                    active_paa7_tickets[port] = []
                                active_paa7_tickets[port].append(t_num)
                else:
                    paa7_failures[port] = 0
                    if port in active_paa7_tickets and active_paa7_tickets[port]:
                        resolve_paa7_tickets(port)

        # Update CMDB CI statuses based on check results
        sam_down = ("SamTracker Frontend" in active_incidents) or ("SamTracker Backend" in active_incidents)
        other_down = any(name in active_incidents for name in SERVICES if name not in ("SamTracker Frontend", "SamTracker Backend"))
        hardware_down = active_hardware_incident is not None
        
        sam_status = 3 if sam_down else 1
        mando_status = 2 if (other_down or hardware_down) else 1
        
        status_changed = False
        if sam_status != last_sam_status:
            update_ci_status("ci_metsy_prime", sam_status)
            last_sam_status = sam_status
            status_changed = True
            
        if mando_status != last_mando_status:
            update_ci_status("ci_mando", mando_status)
            last_mando_status = mando_status
            status_changed = True
            
        if status_changed:
            trigger_websocket_broadcast()
                    
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
