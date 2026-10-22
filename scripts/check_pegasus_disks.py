import paramiko
import sys

host = "192.168.1.177"
user = "james"
password = "!!Stella1977"

print(f"[*] Connecting to {host} via Paramiko...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

print("[+] Connected successfully!")

# Step 1: Install SSH public key for key-based SSH
try:
    with open('/home/james/.ssh/id_ed25519.pub', 'r') as f:
        pub_key = f.read().strip()
    cmd_key = f'mkdir -p ~/.ssh && chmod 700 ~/.ssh && grep -qF "{pub_key}" ~/.ssh/authorized_keys 2>/dev/null || echo "{pub_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
    client.exec_command(cmd_key)
    print("[+] Deployed SSH public key to ~/.ssh/authorized_keys")
except Exception as e:
    print(f"[-] Key deployment warning: {e}")

def run_cmd(cmd, sudo=False):
    print(f"\n==========================================")
    print(f"--- RUNNING: {cmd} ---")
    print(f"==========================================")
    if sudo:
        full_cmd = f"echo '{password}' | sudo -S {cmd}"
    else:
        full_cmd = cmd
    stdin, stdout, stderr = client.exec_command(full_cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out.strip():
        print(out)
    if err.strip():
        # filter out sudo password prompt line
        err_lines = [l for l in err.splitlines() if '[sudo] password for' not in l]
        if err_lines:
            print("[STDERR]\n" + "\n".join(err_lines))
    return out

run_cmd("hostname && uname -a")
lsblk_out = run_cmd("sudo -S lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL,MODEL,SERIAL", sudo=True)
run_cmd("df -h")
run_cmd("sudo -S smartctl --scan", sudo=True)
run_cmd("sudo -S dmesg | grep -i -E 'ata[0-9]|nvme|sda|sdb|sdc|sdd|sde|error|fail|corrupt|reset|io-error' | tail -n 40", sudo=True)
run_cmd("sudo -S fdisk -l", sudo=True)

# Query smartctl on all detected block devices
stdin, stdout, _ = client.exec_command("echo '!!Stella1977' | sudo -S lsblk -dn -o NAME,TYPE")
devices = [line.split()[0] for line in stdout.read().decode('utf-8').splitlines() if line.strip() and ('disk' in line or 'nvme' in line)]

for dev in set(devices):
    dev_path = f"/dev/{dev}"
    run_cmd(f"sudo -S smartctl -H -i -A {dev_path}", sudo=True)

client.close()
print("\n[+] Health check completed!")
