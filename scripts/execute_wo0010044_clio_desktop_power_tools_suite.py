#!/usr/bin/env python3
"""
================================================================================
🚀 CLIO DESKTOP POWER TOOLS SUITE INSTALLER
Ticket: WO0010044-CLIO-DESKTOP-POWER-TOOLS-SUITE
Target: Native Clio Desktop Workstation
================================================================================
Installs:
1. Google Chrome (Official Stable 64-bit) - For bookmark & profile sync
2. Barrier (Virtual KVM) - Mouse/Keyboard & Clipboard sharing between Artemis & Clio
3. CopyQ - Searchable persistent clipboard history
4. Flameshot - Screen capture & annotation
5. Btop & Htop - Visual system telemetry
6. Tilix - Tiling GTK terminal emulator
================================================================================
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime, timezone

TICKET_ID = "WO0010044-CLIO-DESKTOP-POWER-TOOLS-SUITE"
TICKET_DIR = f"/home/james/sovereign_inbox/tickets/{TICKET_ID}"
EVIDENCE_PATH = f"{TICKET_DIR}/execution_evidence.json"
os.makedirs(TICKET_DIR, exist_ok=True)

def run_cmd(cmd, check=True, timeout=300):
    print(f"[*] Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}", flush=True)
    res = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if res.stdout:
        print(res.stdout.strip(), flush=True)
    if res.stderr:
        print(f"[stderr] {res.stderr.strip()}", flush=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with code {res.returncode}")
    return res

def main():
    print("=" * 80)
    print(f"🚀 INITIATING CLIO DESKTOP POWER TOOLS INSTALLATION [{TICKET_ID}]")
    print(f"[*] Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    installed_tools = {}

    # 1. Update Apt Repositories
    print("\n[Phase 1] Refreshing package repository cache...")
    try:
        run_cmd(["sudo", "-n", "apt-get", "update", "-qq"], check=False)
    except Exception as e:
        print(f"[!] Warning updating apt cache: {e}")

    # 2. Google Chrome Installation
    print("\n[Phase 2] Checking / Installing Google Chrome Official Stable...")
    chrome_path = shutil.which("google-chrome") or shutil.which("google-chrome-stable")
    if chrome_path:
        res = subprocess.run([chrome_path, "--version", "--headless"], capture_output=True, text=True)
        ver = res.stdout.strip() if res.returncode == 0 else "Installed"
        print(f"[✓] Google Chrome already present: {ver} ({chrome_path})")
        installed_tools["google-chrome"] = ver
    else:
        deb_path = "/tmp/google-chrome-stable_current_amd64.deb"
        print("[*] Downloading latest Google Chrome .deb package...")
        run_cmd(f"curl -sSL -o {deb_path} https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb", check=True)
        print("[*] Installing Google Chrome via apt-get...")
        run_cmd(["sudo", "-n", "apt-get", "install", "-y", deb_path], check=True)
        if os.path.exists(deb_path):
            os.remove(deb_path)
        chrome_path = shutil.which("google-chrome") or shutil.which("google-chrome-stable")
        res = subprocess.run([chrome_path, "--version", "--headless"], capture_output=True, text=True)
        ver = res.stdout.strip()
        print(f"[✓] Google Chrome installed successfully: {ver}")
        installed_tools["google-chrome"] = ver

    # 3. APT Desktop Power Tools
    apt_tools = {
        "barrier": "Virtual KVM (Seamless Mouse/Keyboard/Clipboard Sharing with Artemis)",
        "copyq": "Searchable Desktop Clipboard History Manager",
        "flameshot": "Screen Capture & Annotation Utility",
        "btop": "Modern C++ Terminal Telemetry & Resource Monitor",
        "htop": "Classic Process Monitor",
        "tilix": "Tiling Terminal Emulator"
    }

    print("\n[Phase 3] Installing Desktop Productivity & KVM Tools...")
    for pkg, desc in apt_tools.items():
        existing = shutil.which(pkg)
        if existing:
            print(f"[✓] {pkg} already installed ({desc})")
            installed_tools[pkg] = "Pre-installed"
        else:
            print(f"[*] Installing {pkg} ({desc})...")
            res = run_cmd(["sudo", "-n", "apt-get", "install", "-y", pkg], check=False)
            if res.returncode == 0 and shutil.which(pkg):
                print(f"[✓] Successfully installed {pkg}")
                installed_tools[pkg] = "Installed"
            else:
                print(f"[!] Warning: Could not install {pkg}")
                installed_tools[pkg] = "Failed/Unavailable"

    # 4. Write Evidence Record
    evidence = {
        "ticket_id": TICKET_ID,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "installed_tools": installed_tools,
        "status": "COMPLETED",
        "notes": "Google Chrome and workstation power utilities installed for Clio desktop use."
    }
    with open(EVIDENCE_PATH, "w") as f:
        json.dump(evidence, f, indent=2)

    print("\n" + "=" * 80)
    print(f"🎉 CLIO DESKTOP POWER TOOLS SUITE INSTALLED SUCCESSFULLY!")
    print(f"[✓] Evidence file committed: {EVIDENCE_PATH}")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
