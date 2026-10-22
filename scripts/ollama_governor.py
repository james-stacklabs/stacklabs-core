#!/usr/bin/env python3
import sqlite3
import subprocess
import os
import sys

import urllib.request
import json

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def check_active_summarize_jobs():
    if os.path.exists("/tmp/ollama_active_lock"):
        return True
    try:
        req = urllib.request.Request("http://127.0.0.1:5056/api/snipe/active_jobs", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
            for job in data.values():
                if job.get('status') == 'summarizing':
                    return True
        return False
    except Exception:
        return False

def check_active_rooms():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM cmdb_ci_fanstack_room WHERE room_state = 'active'")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"Error checking DB: {e}")
        return False

def get_ollama_status():
    try:
        res = subprocess.run(["systemctl", "is-active", "ollama"], capture_output=True, text=True)
        return res.stdout.strip() == "active"
    except Exception:
        return False

def main():
    print("[OLLAMA GOVERNOR] Local Ollama integration has been permanently sunset.")
    is_active_service = get_ollama_status()
    if is_active_service:
        print("[OLLAMA GOVERNOR] Stopping and disabling local Ollama service to enforce sunset status...")
        subprocess.run(["sudo", "systemctl", "stop", "ollama"], check=True)
        subprocess.run(["sudo", "systemctl", "disable", "ollama"], check=True)
        print("[OLLAMA GOVERNOR] Successfully stopped and disabled Ollama.")
    else:
        print("[OLLAMA GOVERNOR] Ollama is confirmed offline.")

if __name__ == "__main__":
    main()
