#!/usr/bin/env python3
import os
import sys
import re
import argparse
import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
import jwt

# Canonical Paths
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AUTH_ENV_PATH = "/home/james/stacklabs/scripts/.env.auth"
SNAPSHOT_DIR = "/home/james/sovereign_inbox/uat_snapshots"

TARGET_MAP = {
    "savant_query": "https://clio.taila01894.ts.net/?domain=ROOT&room=savant_query",
    "savant_oracle": "https://clio.taila01894.ts.net/?domain=ROOT&room=savant_query",
    "savant oracle": "https://clio.taila01894.ts.net/?domain=ROOT&room=savant_query",
    "fanstack - savant oracle": "https://clio.taila01894.ts.net/?domain=ROOT&room=savant_query",
    "app_directory": "https://clio.taila01894.ts.net/?domain=ROOT&room=app_directory",
    "directory": "https://clio.taila01894.ts.net/?domain=ROOT&room=app_directory",
    "sovereign os / stack directory": "https://clio.taila01894.ts.net/?domain=ROOT&room=app_directory",
    "sdlc": "http://clio.taila01894.ts.net:8095/",
    "sdlc_portal": "http://clio.taila01894.ts.net:8095/",
    "sdlc portal": "http://clio.taila01894.ts.net:8095/",
}

def get_user_details(user_name: str) -> dict:
    """Retrieve stakeholder details from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_name, role, display_name FROM sys_user WHERE user_name = ?", (user_name.lower(),))
    row = c.fetchone()
    conn.close()
    if not row:
        print(f"⚠️ User '{user_name}' not found in sys_user. Using guest defaults.")
        return {"user_name": user_name, "role": "guest", "display_name": user_name.capitalize()}
    return dict(row)

def get_user_modules(user_name: str) -> list:
    """Retrieve list of active module grants for user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT m.module_name
        FROM m2m_user_module um
        JOIN sys_user u ON u.sys_id = um.user_sys_id
        JOIN sys_module m ON m.module_name = um.module_name
        WHERE u.user_name = ? AND um.active = 1 AND m.active = 1
    """, (user_name.lower(),))
    modules = [r[0] for r in c.fetchall()]
    conn.close()
    return modules

def get_jwt_secret() -> str:
    """Read JWT Secret from .env.auth or environment variables."""
    secret = os.getenv("SOVEREIGN_AUTH_SECRET")
    if not secret and os.path.exists(AUTH_ENV_PATH):
        with open(AUTH_ENV_PATH) as f:
            for line in f:
                if line.startswith("SOVEREIGN_AUTH_SECRET="):
                    secret = line.strip().split("=", 1)[1]
    if not secret:
        raise RuntimeError("SOVEREIGN_AUTH_SECRET not set in .env.auth or environment.")
    return secret

def generate_uat_token(user_name: str) -> str:
    """Sign a temporary 1-hour JWT token for UAT headless verification."""
    user = get_user_details(user_name)
    modules = get_user_modules(user_name)
    secret = get_jwt_secret()
    
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": user["user_name"],
        "role": user["role"] or "guest",
        "display_name": user["display_name"] or user["user_name"],
        "modules": modules,
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def mileInMyShoes(node: str, target: str, user: str = "james", ticket: str = None) -> str:
    """
    Main functional implementation.
    Generates a UAT JWT token for the user, runs headless screenshot on remote/local node,
    and returns the local file path to the saved screenshot.
    """
    # 1. Resolve Target URL
    resolved_url = target
    target_clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', target).lower()
    
    if not (target.startswith("http://") or target.startswith("https://")):
        key = target.lower().strip()
        if key in TARGET_MAP:
            resolved_url = TARGET_MAP[key]
        else:
            raise ValueError(f"Unknown target shortcut '{target}'. Must be an absolute URL or one of {list(TARGET_MAP.keys())}")

    # 2. Inject JWT Token
    token = generate_uat_token(user)
    separator = "&" if "?" in resolved_url else "?"
    authenticated_url = f"{resolved_url}{separator}token={token}"

    # 3. Formulate Output Filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ticket_part = f"_{ticket}" if ticket else ""
    local_filename = f"uat_{node}_{target_clean}{ticket_part}_{timestamp}.png"
    local_filepath = os.path.join(SNAPSHOT_DIR, local_filename)

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    print(f"\n======================================================================")
    print(f"🥾 WALK A MILE IN MY SHOES — UAT PIPELINE")
    print(f"======================================================================")
    print(f"👤 Active Persona : {user}")
    print(f"🖥️  Target Node    : {node}")
    print(f"🔗 Target App     : {target} -> {resolved_url}")
    print(f"🔒 Auth Token     : [Injected Successfully]")
    print(f"📸 Screenshot Dest: {local_filepath}")
    print(f"----------------------------------------------------------------------")

    # 4. Execute Headless Screenshot Capture
    remote_path = f"/tmp/uat_snap_{timestamp}.png"
    chrome_cmd = f'chromium --headless --disable-gpu --ignore-certificate-errors --virtual-time-budget=10000 --screenshot={remote_path} --window-size=1920,1080 "{authenticated_url}"'

    if node == "clio" or node == "localhost":
        # Local Headless Execution (restricted to headless/virtual background process only)
        print("🏃 Running local background headless capture...")
        try:
            subprocess.run(chrome_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(f"mv {remote_path} {local_filepath}", shell=True, check=True)
            print(f"✅ Success! Local snapshot written to {local_filepath}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed local screenshot: {e}")
            raise
    else:
        # Remote Tailscale Node SSH Execution
        print(f"🚀 Sending headless command to remote mesh node '{node}'...")
        ssh_cmd = f"ssh {node} '{chrome_cmd}'"
        scp_cmd = f"scp {node}:{remote_path} {local_filepath}"
        cleanup_cmd = f"ssh {node} 'rm -f {remote_path}'"

        try:
            # Take screenshot remotely
            subprocess.run(ssh_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Copy back to Clio
            subprocess.run(scp_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Cleanup remote node tmp folder (Zero-Litter)
            subprocess.run(cleanup_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"🎉 Success! Remote snapshot retrieved to {local_filepath}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed remote execution or retrieval over SSH/SCP: {e}")
            if e.stderr:
                print(f"   Details: {e.stderr.decode().strip()}")
            raise

    return local_filepath

def main():
    parser = argparse.ArgumentParser(description="Walk a Mile in My Shoes: Remote Headless UAT Snapshot CLI")
    
    # Allow both positional (functional-style) and named arguments
    parser.add_argument("node_pos", nargs="?", default=None, help="Target node (positional)")
    parser.add_argument("target_pos", nargs="?", default=None, help="Target page/URL (positional)")
    
    parser.add_argument("--node", help="Target node (e.g. metsy-prime, argo)")
    parser.add_argument("--target", help="Target page/URL (e.g. savant_query, sdlc, http://...)")
    parser.add_argument("--user", default="james", help="Persona user to authenticate as (default: james)")
    parser.add_argument("--ticket", default=None, help="Ticket ID (e.g. STRY-002) for ticket-linked naming")

    args = parser.parse_args()

    node = args.node or args.node_pos
    target = args.target or args.target_pos

    if not node or not target:
        parser.print_help()
        sys.exit(1)

    try:
        mileInMyShoes(node=node, target=target, user=args.user, ticket=args.ticket)
    except Exception as e:
        print(f"💥 Execution Error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
