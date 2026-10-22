#!/usr/bin/env python3
import paramiko
import time
import sys

HOSTNAME = "192.168.1.185"
USERNAME = "james"
PASSWORD = "!!Stella1977"

def run_remote():
    print(f"[*] Connecting to {USERNAME}@{HOSTNAME} via Paramiko...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD, timeout=15)
        print("[✔] SSH Connected successfully!")
    except Exception as e:
        print(f"[❌] SSH Connection Failed: {e}")
        return False
        
    def exec_cmd(cmd):
        full_cmd = f"export TERM=dumb PAGER=cat DEBIAN_FRONTEND=noninteractive; {cmd}"
        print(f"\n[➔] Executing: {cmd}")
        stdin, stdout, stderr = client.exec_command(full_cmd, get_pty=False)
        out = stdout.read().decode("utf-8")
        err = stderr.read().decode("utf-8")
        exit_code = stdout.channel.recv_exit_status()
        print(f"Exit Code: {exit_code}")
        if out:
            print(f"Output:\n{out}")
        if err:
            print(f"Error:\n{err}")
        return exit_code, out

    # 1. Verify Sudo & Hostname
    exec_cmd("sudo hostnamectl set-hostname grogu")
    
    # 2. Verify NetworkManager profiles
    print("\n[*] Verifying Dual-SSID NetworkManager Profiles...")
    exec_cmd("nmcli -f NAME,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show")

    # 3. Install Tailscale
    print("\n[*] Installing Tailscale on Grogu (this may take ~45s)...")
    exec_cmd("curl -fsSL https://tailscale.com/install.sh | sudo sh")

    # 4. Check Tailscale version
    exec_cmd("tailscale version")

    # 5. Bring up Tailscale
    print("\n[*] Initializing Tailscale on Grogu...")
    exec_cmd("sudo tailscale up --hostname=grogu --accept-routes=true --ssh=true --timeout=15s || true")
    
    # 6. Check Tailscale status & auth URL
    exec_cmd("tailscale status || true")
    exec_cmd("tailscale ip || true")

    client.close()
    print("\n[✔] Remote Provisioning Sequence Complete!")
    return True

if __name__ == "__main__":
    run_remote()
