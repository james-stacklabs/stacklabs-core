import os
import time
import subprocess

TARGET_IP = "clio.taila01894.ts.net"
CHECK_INTERVAL = 2  # seconds
TIMEOUT_THRESHOLD = 10  # seconds

def ping_target():
    result = subprocess.run(['ping', '-c', '1', '-W', '1', TARGET_IP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def start_backup_services():
    print(f"NODE {TARGET_IP} OFFLINE. INITIATING GHOST PROTOCOL.")
    os.system("cd /home/james/stacklabs && python3 scripts/cmdb_server.py &")
    os.system("cd /home/james/stacklabs && python3 scripts/fanstack_server.py &")
    os.system("cd /home/james/stacklabs/01_Sovereign_Portal && npm run dev -- --host &")
    print("Backup services initiated.")

def main():
    offline_duration = 0
    services_started = False
    
    print("Rogue Failover Daemon monitoring Node .73...")
    while True:
        if ping_target():
            offline_duration = 0
            if services_started:
                print(f"Node {TARGET_IP} is back online. Rogue node standing down. Killing backup services.")
                os.system("pkill -f cmdb_server.py")
                os.system("pkill -f fanstack_server.py")
                os.system("pkill -f 'npm run dev'")
                services_started = False
        else:
            offline_duration += CHECK_INTERVAL
            if offline_duration >= TIMEOUT_THRESHOLD and not services_started:
                start_backup_services()
                services_started = True
                
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
