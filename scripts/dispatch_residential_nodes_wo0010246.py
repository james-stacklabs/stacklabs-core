#!/usr/bin/env python3
"""
WO0010246 Residential Sentry Dispatch Script
Executes live curl dwell hits from residential sentinel nodes:
  - calvin (100.104.14.75) @ Barb's House (AT&T ISP)
  - hobbes (100.88.5.122) @ Mom's House (Comcast ISP)
Logs telemetry to /home/james/sovereign_inbox/today/DISTRIBUTED_NODE_DISPATCH_LOG.json
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timezone

NODES = [
    {
        "name": "hobbes",
        "ip": "100.88.5.122",
        "location": "Mom's House (Comcast ISP)"
    },
    {
        "name": "calvin",
        "ip": "100.104.14.75",
        "location": "Barb's House (AT&T ISP)"
    }
]

SEARCH_QUERIES = [
    "WildSeed Extracts",
    "WildSeed Extracts Humboldt",
    "Michael Mclaren living soil rosin"
]

TARGET_URLS = [
    "https://www.stacklabsllc.com/wildseed",
    "https://www.stacklabsllc.com/wildseed#delivery",
    "https://www.stacklabsllc.com/wildseed#fieldnotes",
    "https://www.stacklabsllc.com/wildseed/wildseed_lookbook.pdf"
]

def run_ssh_cmd(node_ip, cmd, timeout=20):
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
        f"james@{node_ip}", cmd
    ]
    try:
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip(), res.returncode
    except Exception as e:
        return str(e), -1

def main():
    print(f"==================================================")
    print(f"🚀 WO0010246 RESIDENTIAL SENTRY DISPATCH")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}Z")
    print(f"Target: https://www.stacklabsllc.com/wildseed#fieldnotes")
    print(f"==================================================")

    results = []

    for node in NODES:
        name = node["name"]
        ip = node["ip"]
        loc = node["location"]
        print(f"\n[*] Engaging Node: {name} ({loc} - Tailscale: {ip})")

        # 1. Resolve External Public IP
        ext_ip, code = run_ssh_cmd(ip, "curl -s ifconfig.me")
        print(f"    -> Public Outbound IP: {ext_ip} (Exit Code: {code})")

        node_report = {
            "node": name,
            "tailscale_ip": ip,
            "public_ip": ext_ip,
            "location": loc,
            "hits": [],
            "searches": []
        }

        # 2. Dwell & Traffic Hits
        for url in TARGET_URLS:
            print(f"    -> Visiting Target Portal: {url}...")
            visit_cmd = f"curl -s -o /dev/null -w 'HTTP_%{{http_code}} Time_%{{time_total}}s' -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)' '{url}'"
            visit_out, vcode = run_ssh_cmd(ip, visit_cmd, timeout=15)
            print(f"       Telemetry: {visit_out} (Exit Code: {vcode})")
            node_report["hits"].append({
                "url": url,
                "telemetry": visit_out
            })

        # 3. Search Queries Simulation
        for query in SEARCH_QUERIES:
            print(f"    -> Simulating Search Query: '{query}'...")
            q_enc = query.replace(" ", "+")
            search_cmd = f"curl -s -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'https://html.duckduckgo.com/html/?q={q_enc}' | grep -i 'wildseed' | head -n 3"
            search_out, scode = run_ssh_cmd(ip, search_cmd, timeout=15)
            snippet = search_out[:120] if search_out else "Query executed (No raw grep match)"
            print(f"       Result: {snippet}")
            node_report["searches"].append({
                "query": query,
                "status": "DISPATCHED",
                "sample": snippet
            })

        results.append(node_report)

    # Save to canonical dispatch log
    out_file = "/home/james/sovereign_inbox/today/DISTRIBUTED_NODE_DISPATCH_LOG.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[+] Dispatch successfully logged to: {out_file}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
