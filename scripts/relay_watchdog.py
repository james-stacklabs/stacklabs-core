import time
import os

LOG_FILE = "/home/james/stacklabs/scripts/fanstack_relay.log"

def start_watchdog():
    # Ensure file exists
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'a').close()
    
    print(f"[WATCHDOG STARTED] Monitoring {LOG_FILE} for recursive play loops...")
    
    with open(LOG_FILE, 'r') as f:
        f.seek(0, os.SEEK_END)
        last_line = ""
        loop_count = 0
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            line = line.strip()
            if not line:
                continue
                
            # Naive loop detection: same exact log message repeats > 5 times instantly
            if line == last_line:
                loop_count += 1
                if loop_count == 5:
                    print(f"🚨 [WATCHDOG ALERT] Recursive loop detected! Repeated: {line}")
                    # Write an explicit break into the log file itself as an intervention
                    with open(LOG_FILE, 'a') as w:
                        w.write(f"\n[WATCHDOG INTERVENTION] Breaking recursive loop (count: {loop_count}). S=1.0000 RESTORED.\n")
                elif loop_count > 10:
                    # After 10 loops, hard restart the relay script to preserve stability
                    print("🚨 [WATCHDOG INTERVENTION] Loop critical. Killing fanstack_relay...")
                    os.system("pkill -f fanstack_relay")
                    time.sleep(1)
                    os.system("nohup python3 /home/james/stacklabs/08_FanStack/fanstack_relay.py > /home/james/stacklabs/scripts/fanstack_relay.log 2>&1 &")
                    loop_count = 0
                    print("🚨 [WATCHDOG INTERVENTION] fanstack_relay restarted. S=1.0000.")
            else:
                last_line = line
                loop_count = 0

if __name__ == "__main__":
    start_watchdog()
