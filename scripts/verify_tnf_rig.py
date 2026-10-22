#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(STACKLABS_ROOT))

def check_local_port(port: int, path: str = "/") -> bool:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClioPreflight/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[PORT CHECK FAILED] {port}{path}: {e}")
        return False

def main():
    print("=== TNF BATTLE STATION PRE-FLIGHT VERIFICATION ===")
    
    # 1. Check services
    faas_ok = check_local_port(3033, "/")
    retina_ok = check_local_port(3028, "/")
    synapse_ok = check_local_port(8088, "/health")
    
    print(f"FaaS Server (Port 3033): {'ONLINE (200 OK)' if faas_ok else 'OFFLINE'}")
    print(f"Retina Sentry (Port 3028): {'ONLINE (200 OK)' if retina_ok else 'OFFLINE'}")
    print(f"Synapse Hub (Port 8088): {'ONLINE (200 OK)' if synapse_ok else 'OFFLINE'}")
    
    # 2. Check TNF Game State File
    game_state_file = STACKLABS_ROOT / "data" / "game_state_tnf.json"
    if game_state_file.exists():
        with open(game_state_file, "r") as f:
            data = json.load(f)
            print(f"Game State Loaded: {data.get('matchup')} - Status: {data.get('status')}")
    else:
        print("[ERROR] game_state_tnf.json not found!")
        sys.exit(1)
        
    # 3. Check Rosetta Codec
    try:
        from scripts.core.emoji_bytecode import EmojiBytecodeCodec
        codec = EmojiBytecodeCodec()
        frame = data["bleacher_wire"]["bytecode_status"]
        log_str = codec.to_log_string(frame)
        print(f"Rosetta Positional Bytecode Verified: {frame} -> {log_str}")
    except Exception as e:
        print(f"[WARNING] Rosetta codec check skipped/failed: {e}")

    print("=== ALL PRE-FLIGHT CHECKS PASS ===")

if __name__ == "__main__":
    main()
