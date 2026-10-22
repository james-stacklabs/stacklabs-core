import psutil
import time
import requests
import socket
import json
import subprocess
import re
import os
import datetime

NTFY_URL = "https://ntfy.sh/sovereign_alerts_jxw92"
GOVEE_PORT = 40033

# Required daemons
CORE_DAEMONS = [
    "fanstack_background_poller.py",
    "fanstack_relay.py"
]

def get_active_ips():
    try:
        output = subprocess.check_output(['arp', '-an']).decode()
        ips = re.findall(r'\((192\.168\.\d+\.\d+)\)', output)
        return list(set(ips))
    except:
        return [f"192.168.1.{i}" for i in range(1, 255)]

def fire_govee_alert():
    print("[ALERT] Firing Govee UDP Red Alert...")
    color = {"r": 255, "g": 0, "b": 0} # Solid Red
    msg = {
        "msg": {
            "cmd": "colorwc",
            "data": {
                "color": color,
                "colorTemInKelvin": 0
            }
        }
    }
    payload = json.dumps(msg).encode('utf-8')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    ips = get_active_ips()
    for ip in ips:
        try:
            sock.sendto(payload, (ip, GOVEE_PORT))
        except: pass
    sock.close()

def send_push_notification(missing_daemons):
    print(f"[ALERT] Firing ntfy.sh push notification...")
    message = f"🚨 SOVEREIGN NODE .73 CRASH DETECTED 🚨\n\nThe following daemons are offline:\n"
    for d in missing_daemons:
        message += f"- {d}\n"
    message += f"\nTime: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), headers={
            "Title": "Node .73 Critical Failure",
            "Tags": "warning,skull"
        })
    except Exception as e:
        print(f"[ERROR] Failed to send push notification: {e}")

def check_daemons():
    running_scripts = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.info['cmdline']:
                cmd = " ".join(p.info['cmdline'])
                for daemon in CORE_DAEMONS:
                    if daemon in cmd and "sovereign_monitor.py" not in cmd:
                        running_scripts.append(daemon)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    missing = [d for d in CORE_DAEMONS if d not in running_scripts]
    return missing

def main():
    print("==================================================")
    print(" 🛡️ SOVEREIGN ALERT WATCHDOG ONLINE 🛡️ ")
    print("==================================================")
    print(f"Monitoring: {CORE_DAEMONS}")
    print("Push Notifications: Active (sovereign_alerts_jxw92)")
    print("Govee UDP Alert: Active\n")
    
    # Cooldown to prevent spamming notifications every 5 seconds
    # Set to 5 minutes (300 seconds)
    cooldown_seconds = 300
    last_alert_time = 0
    
    while True:
        missing = check_daemons()
        
        if missing:
            now = time.time()
            if now - last_alert_time > cooldown_seconds:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🚨 CRITICAL: Missing daemons detected: {missing}")
                
                # 1. Fire local Govee blast
                fire_govee_alert()
                
                # 2. Fire external push notification
                send_push_notification(missing)
                
                # 3. Attempt Auto-Heal
                print("[AUTO-HEAL] Attempting to execute restart_stack.sh...")
                os.system("bash /home/james/stacklabs/scripts/restart_stack.sh")
                
                last_alert_time = now
            else:
                pass # In cooldown
        
        time.sleep(10) # Check every 10 seconds

if __name__ == "__main__":
    main()
