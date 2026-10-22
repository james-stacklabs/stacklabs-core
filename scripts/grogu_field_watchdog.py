#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: GROGU FIELD CONNECTIVITY & TELEMETRY WATCHDOG
# File: /home/james/stacklabs/scripts/grogu_field_watchdog.py
# Purpose: Autonomous continuous field testing of edge node grogu over Tailscale
# ==============================================================================
import os
import sys
import time
import subprocess
import sqlite3
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LOG_PATH = "/home/james/sovereign_inbox/grogu_kroger_field_test.log"
REPORT_PATH = "/home/james/sovereign_inbox/grogu_kroger_field_report.md"
TARGET_TS_IP = "100.68.247.36"
TARGET_HOST = "grogu"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS edge_node_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT,
                ip_address TEXT,
                status TEXT,
                latency_ms REAL,
                packet_loss_pct REAL,
                network_mode TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WATCHDOG] DB init error: {e}")

def check_ping(ip: str):
    try:
        # Send 2 fast pings with 1s timeout
        res = subprocess.run(
            ["ping", "-c", "2", "-W", "1", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            # Extract latency
            avg_ms = None
            for line in lines:
                if "rtt min/avg/max/mdev" in line or "round-trip min/avg/max/stddev" in line:
                    parts = line.split("=")[1].strip().split("/")
                    avg_ms = float(parts[1])
            return True, avg_ms or 0.0, 0.0
        else:
            return False, 0.0, 100.0
    except Exception as e:
        return False, 0.0, 100.0

def get_node_status_via_ssh(ip: str):
    try:
        cmd = [
            "ssh", "-i", "/home/james/.ssh/id_ed25519",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=2",
            "-o", "StrictHostKeyChecking=no",
            f"james@{ip}",
            "nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if res.returncode == 0:
            active_ssid = res.stdout.strip()
            return active_ssid or "UNKNOWN_WIFI"
    except Exception:
        pass
    return "UNKNOWN"

def log_event(status_str: str, latency: float, mode: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{ts}] [GROGU WATCHDOG] Status: {status_str:<8} | Mode: {mode:<20} | Latency: {latency:5.1f}ms\n"
    
    with open(LOG_PATH, "a") as f:
        f.write(log_line)
    print(log_line.strip())
    
    # Save to SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO edge_node_telemetry 
                (node_name, ip_address, status, latency_ms, packet_loss_pct, network_mode)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (TARGET_HOST, TARGET_TS_IP, status_str, latency, 0.0 if status_str == "ONLINE" else 100.0, mode))
        conn.commit()
        conn.close()
    except Exception:
        pass

def update_report(total_checks: int, online_checks: int, hotspot_checks: int, last_seen: str, avg_lat: float):
    uptime_pct = (online_checks / total_checks * 100.0) if total_checks > 0 else 0.0
    report_content = f"""# 🛰️ Grogu Kroger Field Connectivity Report
**Target Node:** `{TARGET_HOST}` (`{TARGET_TS_IP}`)  
**Test Objective:** Autonomous Edge Telemetry Tracking via Pixel 10a Hotspot  
**Last Updated:** `{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`  

---

## 📊 Live Telemetry Summary
* **Total Probes:** `{total_checks}`
* **Online Success Rate:** `{uptime_pct:.1f}%` (`{online_checks}/{total_checks}` probes)
* **Mobile Hotspot Verified Pings:** `{hotspot_checks}`
* **Average Latency:** `{avg_lat:.1f} ms`
* **Last Successful Ping:** `{last_seen}`

---

## 📡 Active Network States Log
*Detailed streaming logs located at:* [`{LOG_PATH}`](file://{LOG_PATH})

```text
"""
    # Append last 20 lines of log
    try:
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r") as f:
                lines = f.readlines()
                report_content += "".join(lines[-20:])
    except Exception:
        pass

    report_content += "```\n"
    
    with open(REPORT_PATH, "w") as f:
        f.write(report_content)

def main():
    print(f"🛰️ [GROGU WATCHDOG] Starting autonomous Kroger Field Telemetry Watchdog for {TARGET_HOST} ({TARGET_TS_IP})...")
    init_db()
    
    total_probes = 0
    online_probes = 0
    hotspot_probes = 0
    last_seen_ts = "Never"
    latencies = []
    
    while True:
        total_probes += 1
        is_up, lat, loss = check_ping(TARGET_TS_IP)
        
        if is_up:
            online_probes += 1
            latencies.append(lat)
            last_seen_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check SSID
            ssid = get_node_status_via_ssh(TARGET_TS_IP)
            if "pixel_10a_hotspot" in ssid:
                hotspot_probes += 1
                mode = "MOBILE_HOTSPOT (Kroger Field)"
            elif "ATTFVVFDJD" in ssid:
                mode = "HOME_WIFI (Base Subnet)"
            else:
                mode = f"WIFI ({ssid})"
                
            log_event("ONLINE", lat, mode)
        else:
            log_event("OFFLINE", 0.0, "DISCONNECTED / ROAMING")
            
        avg_lat = (sum(latencies) / len(latencies)) if latencies else 0.0
        update_report(total_probes, online_probes, hotspot_probes, last_seen_ts, avg_lat)
        
        time.sleep(5)

if __name__ == "__main__":
    main()
