#!/home/james/stacklabs/.venv/bin/python3
"""
Surgically purges legacy ghost shares from /etc/samba/smb.conf and establishes canonical StackLabs shares.
Enforces Invariant 1.9, anti-cosplay standards, and clean-room VFS exposure.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SMB_CONF = Path("/etc/samba/smb.conf")
BACKUP_DIR = Path("/etc/samba/backups")

CANONICAL_SHARES = """
[stacklabs]
   comment = StackLabs Dedicated Workspace
   path = /home/james/stacklabs
   browseable = yes
   read only = no
   writable = yes
   valid users = james
   force user = james

[vfs]
   comment = StackLabs POSIX VFS & CMDB Graph
   path = /home/james/stacklabs/vfs
   browseable = yes
   read only = no
   writable = yes
   valid users = james
   force user = james

[pilot_drops]
   comment = Pilot Drops Ingress (Audio, Photos, Transcripts)
   path = /home/james/stacklabs/pilot_drops
   browseable = yes
   read only = no
   writable = yes
   valid users = james
   force user = james

[gemini]
   comment = Gemini Antigravity Brain
   path = /home/james/.gemini
   browseable = yes
   read only = no
   writable = yes
   valid users = james
   force user = james
"""


def main() -> int:
    if not SMB_CONF.exists():
        print(f"Error: {SMB_CONF} not found.", file=sys.stderr)
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    backup_file = BACKUP_DIR / f"smb.conf.bak.{ts}"
    shutil.copy2(SMB_CONF, backup_file)
    print(f"✓ Backed up {SMB_CONF} -> {backup_file}")

    content = SMB_CONF.read_text(encoding="utf-8")

    sections = re.split(r"(?m)^(\[[a-zA-Z0-9_\$-]+\])", content)
    cleaned_parts: list[str] = []
    if sections:
        cleaned_parts.append(sections[0])

    i = 1
    while i < len(sections):
        header = sections[i]
        body = sections[i + 1] if i + 1 < len(sections) else ""
        section_name = header.strip("[] \n\r\t")

        # Prune legacy shares and existing versions of canonical shares
        low_name = section_name.lower()
        if (
            low_name.startswith("sov")
            or "sandbox" in low_name
            or "inbox" in low_name
            or section_name in ["stacklabs", "vfs", "pilot_drops", "gemini"]
        ):
            print(f"✓ Pruned share: [{section_name}]")
        else:
            cleaned_parts.append(header)
            cleaned_parts.append(body)
        i += 2

    base_text = "".join(cleaned_parts).rstrip()
    updated_content = base_text + "\n\n" + CANONICAL_SHARES.strip() + "\n"

    tmp_file = SMB_CONF.with_suffix(".tmp")
    tmp_file.write_text(updated_content, encoding="utf-8")

    res = subprocess.run(["testparm", "-s", str(tmp_file)], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ testparm failed on {tmp_file}:\n{res.stderr}", file=sys.stderr)
        if tmp_file.exists():
            tmp_file.unlink()
        return 1

    os.replace(tmp_file, SMB_CONF)
    print("✓ Successfully updated /etc/samba/smb.conf")

    reload_res = subprocess.run(["systemctl", "restart", "smbd"], capture_output=True, text=True)
    if reload_res.returncode != 0:
        print(f"❌ systemctl restart smbd failed: {reload_res.stderr}", file=sys.stderr)
        return 1
    print("✓ Restarted smbd.service successfully.")

    verify_res = subprocess.run(["testparm", "-s"], capture_output=True, text=True)
    print("✓ Active shares verified:")
    for line in verify_res.stdout.splitlines():
        if line.startswith("["):
            print(f"  - {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
