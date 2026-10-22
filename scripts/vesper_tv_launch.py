import os
import sys
import subprocess

def check_adb():
    if subprocess.call(["which", "adb"], stdout=subprocess.DEVNULL) != 0:
        print("ADB not found. Installing...")
        os.system("sudo apt-get install -y adb")

def main():
    check_adb()
    tv_ip = "192.168.1.192:5555"
    print(f"[*] Connecting to TV DOM node: {tv_ip}")
    os.system(f"adb connect {tv_ip}")

    payload_url = sys.argv[1] if len(sys.argv) > 1 else "http://clio.taila01894.ts.net:8000/sovereign_kanban_tv.html"
    print(f"[*] Pushing URL: {payload_url}")
    
    # Send Android VIEW intent to open default browser (Silk on Fire TV)
    cmd = f"adb -s {tv_ip} shell am start -a android.intent.action.VIEW -d '{payload_url}'"
    os.system(cmd)
    print("\n[+] FanStack TV launched.")

if __name__ == '__main__':
    main()
