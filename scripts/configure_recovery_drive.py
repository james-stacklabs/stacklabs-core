#!/home/james/stacklabs/.venv/bin/python3
"""
Configure RTL9210 USB Storage Quirk and Mount Recovery Drive.
Path: /home/james/stacklabs/scripts/configure_recovery_drive.py

1. Creates /etc/modprobe.d/disable-uas-rtl9210.conf with options usb-storage quirks=0bda:9210:u
2. Resets USB device 0bda:9210 to apply driver binding
3. Runs fsck.ext4 -y /dev/sda1 to verify and repair filesystem
4. Ensures /mnt/relics exists and mounts /dev/sda1
5. Enforces ownership james:james on /mnt/relics
"""

import os
import pathlib
import subprocess
import sys
import time


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"[EXEC] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed ({result.returncode}): {result.stderr.strip()}")
        sys.exit(result.returncode)
    return result


def main() -> int:
    print("=== Step 1: Apply RTL9210 UAS Quirk ===")
    modprobe_file = pathlib.Path("/etc/modprobe.d/disable-uas-rtl9210.conf")
    quirk_line = "options usb-storage quirks=0bda:9210:u\n"
    
    current_content = ""
    if modprobe_file.exists():
        try:
            current_content = modprobe_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Could not read existing modprobe file: {e}")
            
    if quirk_line.strip() not in current_content:
        p = subprocess.Popen(["sudo", "tee", str(modprobe_file)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        p.communicate(input=quirk_line)
        print(f"[OK] Wrote UAS quirk to {modprobe_file}")
    else:
        print(f"[SKIP] UAS quirk already present in {modprobe_file}")

    print("=== Step 2: Cycle USB Device to Bind to usb-storage ===")
    quirks_param = pathlib.Path("/sys/module/usb_storage/parameters/quirks")
    if quirks_param.exists():
        current_quirks = quirks_param.read_text(encoding="utf-8").strip()
        if "0bda:9210:u" not in current_quirks:
            p = subprocess.Popen(["sudo", "tee", str(quirks_param)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            p.communicate(input="0bda:9210:u\n")
            print("[OK] Applied runtime usb_storage quirk 0bda:9210:u")

    mountpoint = pathlib.Path("/mnt/relics")
    if not pathlib.Path("/dev/sda1").exists():
        usb4_disable = pathlib.Path("/sys/bus/usb/devices/usb4/4-0:1.0/usb4-port2/disable")
        usb3_disable = pathlib.Path("/sys/bus/usb/devices/usb3/3-0:1.0/usb3-port2/disable")
        if usb4_disable.exists() and usb3_disable.exists():
            subprocess.run(["sudo", "tee", str(usb4_disable)], input="1\n", text=True, capture_output=True)
            subprocess.run(["sudo", "tee", str(usb3_disable)], input="0\n", text=True, capture_output=True)
            time.sleep(3)

    print("=== Step 3: Run Filesystem Check on /dev/sda1 ===")
    mount_check = run_cmd(["mountpoint", "-q", str(mountpoint)], check=False)
    if mount_check.returncode == 0:
        print(f"[INFO] {mountpoint} is already mounted; skipping offline fsck.")
    else:
        fsck_res = run_cmd(["sudo", "fsck.ext4", "-y", "/dev/sda1"], check=False)
        print(f"[FSCK RESULT] Exit code {fsck_res.returncode}")
        if fsck_res.stdout:
            print(fsck_res.stdout.strip())

    print("=== Step 4: Ensure Mountpoint /mnt/relics ===")
    if not mountpoint.exists():
        run_cmd(["sudo", "mkdir", "-p", str(mountpoint)])
        print(f"[OK] Created mountpoint {mountpoint}")

    print("=== Step 5: Mount /dev/sda1 ===")
    mount_check = run_cmd(["mountpoint", "-q", str(mountpoint)], check=False)
    if mount_check.returncode != 0:
        run_cmd(["sudo", "mount", "/dev/sda1", str(mountpoint)])
        print(f"[OK] Mounted /dev/sda1 to {mountpoint}")
    else:
        print(f"[INFO] {mountpoint} is already mounted")

    run_cmd(["sudo", "chown", "-R", "james:james", str(mountpoint)])
    print(f"[OK] Set ownership to james:james on {mountpoint}")

    print("=== Step 6: Verify Mount Receipt ===")
    df_res = run_cmd(["df", "-h", str(mountpoint)])
    print(df_res.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
