#!/usr/bin/env python3
"""
StackLabs C120 Privacy Shutter CLI Control
Path: /home/james/stacklabs/scripts/c120_shutter.py
Usage: python3 c120_shutter.py [toggle|kill|start|status]
"""
import sys
import json
import urllib.request

def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "toggle"
    endpoint_map = {
        "toggle": "toggle",
        "kill": "kill",
        "off": "kill",
        "stop": "kill",
        "start": "start",
        "on": "start",
        "status": "status"
    }

    action = endpoint_map.get(cmd, "status")
    url = f"http://127.0.0.1:3028/api/cam/{action}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Clio-Shutter/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode())
            is_closed = data.get("shutter_closed", False)
            state_str = "SHUTTER CLOSED (AIR-GAPPED)" if is_closed else "SHUTTER OPEN (LIVE STREAMING)"
            print(f"[C120 OPTICAL SENTRY] {state_str} // API Response: {data}")
    except Exception as e:
        print(f"[ERROR] Could not reach Retina Shutter API on Port 3028: {e}")

if __name__ == "__main__":
    main()
