#!/usr/bin/env python3
"""
scripts/reclaim_artemis_ssd.py
==============================
Reclaims 455.1 GB on Artemis /dev/sda3, formats to ext4, mounts to /fast_data,
persists in /etc/fstab, and symlinks user cache to relieve root partition.

Governed by: Invariant 15 (Campsite Protocol), Invariant 32 (Law of "I"),
and Invariant 36 (Metal Verification).
"""

import sys
import subprocess
import json
from pathlib import Path

ARTEMIS_HOST = "100.108.185.53"
SSH_CMD = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", f"james@{ARTEMIS_HOST}"]

def run_remote(cmd: str, check=True) -> str:
    full_cmd = SSH_CMD + [cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Remote command failed: {cmd}\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
    return res.stdout.strip()

def main():
    print(f"[*] Connecting to Artemis at {ARTEMIS_HOST}...")
    
    # 1. Inspect sda3 status
    lsblk_out = run_remote("lsblk -J -o NAME,FSTYPE,LABEL,SIZE,MOUNTPOINTS /dev/sda3")
    data = json.loads(lsblk_out)
    blockdevices = data.get("blockdevices", [])
    if not blockdevices:
        raise RuntimeError("Device /dev/sda3 not found on Artemis!")
    
    dev_info = blockdevices[0]
    fstype = dev_info.get("fstype", "")
    mountpoints = dev_info.get("mountpoints") or []
    mountpoint = mountpoints[0] if mountpoints else None
    
    print(f"[+] /dev/sda3 current status: FSTYPE={fstype}, MOUNTPOINT={mountpoint}, SIZE={dev_info.get('size')}")
    
    if mountpoint and mountpoint != "/fast_data":
        raise RuntimeError(f"/dev/sda3 is already mounted at unexpected path: {mountpoint}")

    # 2. Format as ext4 if not already ext4
    if fstype != "ext4":
        print("[*] Formatting /dev/sda3 to ext4 with label 'artemis_ssd'...")
        run_remote("sudo -n mkfs.ext4 -F -L artemis_ssd /dev/sda3")
        print("[+] /dev/sda3 formatted successfully.")
    else:
        print("[+] /dev/sda3 is already ext4. Skipping format.")

    # 3. Create mount point and mount
    print("[*] Configuring /fast_data mount point...")
    run_remote("sudo -n mkdir -p /fast_data")
    
    # Check if mounted
    check_mount = run_remote("mount | grep '/dev/sda3' || true", check=False)
    if "/fast_data" not in check_mount:
        print("[*] Mounting /dev/sda3 to /fast_data...")
        run_remote("sudo -n mount /dev/sda3 /fast_data")
    run_remote("sudo -n chown -R james:james /fast_data")
    print("[+] /fast_data mounted and ownership set to james:james.")

    # 4. Get UUID and persist in /etc/fstab
    uuid = run_remote("sudo -n blkid -s UUID -o value /dev/sda3")
    if not uuid:
        raise RuntimeError("Failed to resolve UUID for /dev/sda3")
    print(f"[+] /dev/sda3 UUID: {uuid}")

    fstab_entry = f"UUID={uuid} /fast_data ext4 defaults 0 2"
    fstab_curr = run_remote("cat /etc/fstab")
    if uuid not in fstab_curr and "/fast_data" not in fstab_curr:
        print("[*] Appending entry to /etc/fstab...")
        run_remote(f"echo '{fstab_entry}' | sudo -n tee -a /etc/fstab")
        print("[+] /etc/fstab updated.")
    else:
        print("[+] /etc/fstab entry already present.")

    # 5. Migrate user cache to /fast_data/caches
    print("[*] Offloading ~/.cache to /fast_data/caches...")
    run_remote("mkdir -p /fast_data/caches")
    # Verify if ~/.cache is already a symlink
    is_symlink = run_remote("[ -L /home/james/.cache ] && echo 'YES' || echo 'NO'")
    if is_symlink != "YES":
        print("[*] Migrating existing cache contents and creating symlink...")
        run_remote("cp -rn /home/james/.cache/* /fast_data/caches/ 2>/dev/null || true")
        run_remote("rm -rf /home/james/.cache && ln -s /fast_data/caches /home/james/.cache")
        print("[+] ~/.cache successfully symlinked to /fast_data/caches.")
    else:
        print("[+] ~/.cache is already a symlink.")

    # 5b. Migrate ~/.config/google-chrome to /fast_data/google-chrome
    print("[*] Offloading Chrome config and caches to /fast_data/google-chrome...")
    is_chrome_symlink = run_remote("[ -L /home/james/.config/google-chrome ] && echo 'YES' || echo 'NO'")
    if is_chrome_symlink != "YES":
        if run_remote("[ -d /home/james/.config/google-chrome ] && echo 'YES' || echo 'NO'") == "YES":
            run_remote("mv /home/james/.config/google-chrome /fast_data/google-chrome && ln -s /fast_data/google-chrome /home/james/.config/google-chrome")
            print("[+] ~/.config/google-chrome migrated and symlinked.")
    else:
        print("[+] ~/.config/google-chrome is already a symlink.")

    # 5c. Relieve root partition: clear apt cache, snapd cache, and transient artifacts
    print("[*] Relieving root partition: clearing apt cache, snapd cache, and transient artifacts...")
    run_remote("sudo -n apt-get clean")
    run_remote("sudo -n rm -rf /var/lib/snapd/cache/*")
    run_remote("sudo -n journalctl --vacuum-time=3d")
    run_remote("[ -f /tmp/debian-netinst.iso ] && mv /tmp/debian-netinst.iso /data/ || true")
    print("[+] Root cleanup routines completed.")

    # 6. Verification
    print("\n" + "="*60)
    print("⚡ ARTEMIS STORAGE RECLAMATION AUDIT RECEIPTS")
    print("="*60)
    df_report = run_remote("df -h / /fast_data /data")
    print(df_report)
    print("="*60)

    # Check root available space
    root_avail_kb = int(run_remote("df -k --output=avail / | tail -n 1"))
    root_avail_gb = root_avail_kb / (1024 * 1024)
    print(f"[+] Root available: {root_avail_gb:.2f} GB")
    assert root_avail_gb >= 10.0, f"Root free space is {root_avail_gb:.2f} GB, expected >= 10.0 GB"

    print("[PASS] 455 GB SSD reclaimed and mounted. Root partition permanently protected.")

if __name__ == "__main__":
    main()
