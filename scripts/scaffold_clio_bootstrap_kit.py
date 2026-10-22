#!/home/james/stacklabs/.venv/bin/python3
"""
Scaffold Clio Barebones Recovery & Disaster Kit on External Storage.
Path: /home/james/stacklabs/scripts/scaffold_clio_bootstrap_kit.py

Populates /mnt/relics/bootstrap with:
1. recover_clio.sh: Automated single-command machine restoration script
2. system_configs: /etc/fstab, /etc/modprobe.d quirks, systemd services
3. identity_and_certs: Tailscale certs/keys, SSH public keys, TLS certs
4. dotfiles: .bashrc, .bash_aliases, .profile, .gitconfig
5. ground_truth: Full copy of /home/james/stacklabs/ground_truth/ ledgers
6. workspace_bundle: Clean git bundle of /home/james/stacklabs/
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

BOOTSTRAP_ROOT = pathlib.Path("/mnt/relics/bootstrap")
STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
HOME_DIR = pathlib.Path("/home/james")


def run_cmd(cmd: list[str], cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    print(f"[EXEC] {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if res.returncode != 0:
        print(f"[WARN] Non-zero exit ({res.returncode}): {res.stderr.strip()}")
    return res


def main() -> int:
    if not pathlib.Path("/mnt/relics").exists() or not os.path.ismount("/mnt/relics"):
        print("[ERROR] /mnt/relics is not mounted. Run configure_recovery_drive.py first.")
        return 1

    print("=== Step 1: Create Bootstrap Kit Directory Structure ===")
    dirs = [
        BOOTSTRAP_ROOT / "system_configs",
        BOOTSTRAP_ROOT / "identity_and_certs",
        BOOTSTRAP_ROOT / "dotfiles",
        BOOTSTRAP_ROOT / "ground_truth",
        BOOTSTRAP_ROOT / "workspace_bundle",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Ensured bootstrap directories at {BOOTSTRAP_ROOT}")

    print("=== Step 2: Archive System Configurations ===")
    fstab_src = pathlib.Path("/etc/fstab")
    if fstab_src.exists():
        shutil.copy2(fstab_src, BOOTSTRAP_ROOT / "system_configs" / "fstab")
        print("[OK] Copied /etc/fstab")

    quirk_src = pathlib.Path("/etc/modprobe.d/disable-uas-rtl9210.conf")
    if quirk_src.exists():
        shutil.copy2(quirk_src, BOOTSTRAP_ROOT / "system_configs" / "disable-uas-rtl9210.conf")
        print("[OK] Copied UAS quirk config")

    systemd_dir = pathlib.Path("/etc/systemd/system")
    for s_file in systemd_dir.glob("stacklabs-*.service"):
        shutil.copy2(s_file, BOOTSTRAP_ROOT / "system_configs" / s_file.name)
        print(f"[OK] Copied systemd service: {s_file.name}")

    print("=== Step 3: Archive Identity and Security Certificates ===")
    cert_files = [
        HOME_DIR / "clio.taila01894.ts.net.crt",
        HOME_DIR / "clio.taila01894.ts.net.key",
        HOME_DIR / "ts_cert.pem",
        HOME_DIR / "ts_key.pem",
    ]
    for c in cert_files:
        if c.exists():
            shutil.copy2(c, BOOTSTRAP_ROOT / "identity_and_certs" / c.name)
            print(f"[OK] Copied certificate: {c.name}")

    ssh_dir = HOME_DIR / ".ssh"
    if ssh_dir.exists():
        dest_ssh = BOOTSTRAP_ROOT / "identity_and_certs" / "ssh"
        dest_ssh.mkdir(parents=True, exist_ok=True)
        for pub in ssh_dir.glob("*.pub"):
            shutil.copy2(pub, dest_ssh / pub.name)
        auth_keys = ssh_dir / "authorized_keys"
        if auth_keys.exists():
            shutil.copy2(auth_keys, dest_ssh / "authorized_keys")
        print("[OK] Copied SSH public credentials")

    print("=== Step 4: Archive Dotfiles ===")
    dotfiles = [".bashrc", ".bash_aliases", ".profile", ".gitconfig"]
    for df in dotfiles:
        src_df = HOME_DIR / df
        if src_df.exists():
            shutil.copy2(src_df, BOOTSTRAP_ROOT / "dotfiles" / df)
            print(f"[OK] Copied dotfile: {df}")

    print("=== Step 5: Mirror Ground Truth Vault ===")
    gt_src = STACKLABS_ROOT / "ground_truth"
    if gt_src.exists():
        for item in gt_src.glob("*.json"):
            shutil.copy2(item, BOOTSTRAP_ROOT / "ground_truth" / item.name)
        for item in gt_src.glob("*.db"):
            shutil.copy2(item, BOOTSTRAP_ROOT / "ground_truth" / item.name)
        for item in gt_src.glob("*.md"):
            shutil.copy2(item, BOOTSTRAP_ROOT / "ground_truth" / item.name)
        print("[OK] Mirrored Ground Truth Vault ledgers and DBs")

    print("=== Step 6: Create Clean Workspace Git Bundle ===")
    bundle_path = BOOTSTRAP_ROOT / "workspace_bundle" / "stacklabs_recovery.bundle"
    if (STACKLABS_ROOT / ".git").exists():
        run_cmd(["git", "bundle", "create", str(bundle_path), "--all"], cwd=STACKLABS_ROOT)
    else:
        staging_repo = BOOTSTRAP_ROOT / "workspace_bundle" / "_staging_git"
        if staging_repo.exists():
            shutil.rmtree(staging_repo)
        staging_repo.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "init", "-b", "main"], cwd=staging_repo)
        run_cmd(["git", "config", "user.email", "james@stacklabsllc.com"], cwd=staging_repo)
        run_cmd(["git", "config", "user.name", "James Carroll"], cwd=staging_repo)
        for fname in ["AGENTS.md", "GEMINI.md"]:
            src_f = STACKLABS_ROOT / fname
            if src_f.exists():
                shutil.copy2(src_f, staging_repo / fname)
        for dname in [".agents", "core", "config", "ground_truth"]:
            src_d = STACKLABS_ROOT / dname
            if src_d.exists():
                shutil.copytree(src_d, staging_repo / dname, symlinks=True, dirs_exist_ok=True)
        scripts_dest = staging_repo / "scripts"
        scripts_dest.mkdir(parents=True, exist_ok=True)
        for py_file in (STACKLABS_ROOT / "scripts").glob("*.py"):
            shutil.copy2(py_file, scripts_dest / py_file.name)
        for sh_file in (STACKLABS_ROOT / "scripts").glob("*.sh"):
            shutil.copy2(sh_file, scripts_dest / sh_file.name)
        run_cmd(["git", "add", "."], cwd=staging_repo)
        run_cmd(["git", "commit", "-m", "Clio disaster recovery baseline snapshot"], cwd=staging_repo)
        run_cmd(["git", "bundle", "create", str(bundle_path), "--all"], cwd=staging_repo)
        shutil.rmtree(staging_repo, ignore_errors=True)
    if bundle_path.exists():
        size_mb = bundle_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Created Git bundle: {bundle_path} ({size_mb:.2f} MB)")

    print("=== Step 7: Write Standalone recover_clio.sh Script ===")
    recovery_script = BOOTSTRAP_ROOT / "recover_clio.sh"
    script_content = """#!/usr/bin/env bash
# ==============================================================================
# CLIO DISASTER RECOVERY & BAREBONES REBUILD SCRIPT
# Target: Any standard x86 Ubuntu LTS installation
# Restores: StackLabs workspace, Tailscale certs, systemd units, dotfiles, Ground Truth
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="james"
TARGET_HOME="/home/${TARGET_USER}"
TARGET_WORKSPACE="${TARGET_HOME}/stacklabs"

echo "=== 1. Restoring Dotfiles ==="
cp -v "${SCRIPT_DIR}/dotfiles/.bashrc" "${TARGET_HOME}/.bashrc"
cp -v "${SCRIPT_DIR}/dotfiles/.bash_aliases" "${TARGET_HOME}/.bash_aliases" || true
cp -v "${SCRIPT_DIR}/dotfiles/.profile" "${TARGET_HOME}/.profile"
cp -v "${SCRIPT_DIR}/dotfiles/.gitconfig" "${TARGET_HOME}/.gitconfig" || true

echo "=== 2. Restoring Kernel Quirks & fstab ==="
if [ -f "${SCRIPT_DIR}/system_configs/disable-uas-rtl9210.conf" ]; then
    sudo cp -v "${SCRIPT_DIR}/system_configs/disable-uas-rtl9210.conf" /etc/modprobe.d/
fi

echo "=== 3. Restoring Identity & Certificates ==="
cp -v "${SCRIPT_DIR}/identity_and_certs/"*.crt "${TARGET_HOME}/" 2>/dev/null || true
cp -v "${SCRIPT_DIR}/identity_and_certs/"*.key "${TARGET_HOME}/" 2>/dev/null || true
cp -v "${SCRIPT_DIR}/identity_and_certs/"*.pem "${TARGET_HOME}/" 2>/dev/null || true

if [ -d "${SCRIPT_DIR}/identity_and_certs/ssh" ]; then
    mkdir -p "${TARGET_HOME}/.ssh"
    chmod 700 "${TARGET_HOME}/.ssh"
    cp -v "${SCRIPT_DIR}/identity_and_certs/ssh/"* "${TARGET_HOME}/.ssh/"
    chmod 600 "${TARGET_HOME}/.ssh/authorized_keys" 2>/dev/null || true
fi

echo "=== 4. Restoring StackLabs Workspace Repository ==="
if [ ! -d "${TARGET_WORKSPACE}/.git" ]; then
    mkdir -p "${TARGET_WORKSPACE}"
    git clone "${SCRIPT_DIR}/workspace_bundle/stacklabs_recovery.bundle" "${TARGET_WORKSPACE}"
    echo "Cloned clean workspace repository from recovery bundle."
fi

echo "=== 5. Restoring Ground Truth Vault ==="
mkdir -p "${TARGET_WORKSPACE}/ground_truth"
cp -v "${SCRIPT_DIR}/ground_truth/"* "${TARGET_WORKSPACE}/ground_truth/"

echo "=== 6. Restoring Systemd Services ==="
for svc in "${SCRIPT_DIR}/system_configs/"*.service; do
    if [ -f "${svc}" ]; then
        sudo cp -v "${svc}" /etc/systemd/system/
    fi
done
sudo systemctl daemon-reload

echo "=== 7. Setting Ownership ==="
chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}"

echo "================================================================================"
echo "✅ Clio Barebones Disaster Recovery Complete. Ready for Python venv bootstrap."
echo "================================================================================"
"""
    recovery_script.write_text(script_content, encoding="utf-8")
    recovery_script.chmod(0o755)
    print(f"[OK] Wrote executable disaster recovery script: {recovery_script}")

    manifest_file = BOOTSTRAP_ROOT / "bootstrap_manifest.json"
    manifest_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "node": "Clio (100.96.77.20)",
        "bootstrap_root": str(BOOTSTRAP_ROOT),
        "recovery_script": str(recovery_script),
        "git_bundle": str(bundle_path),
        "git_bundle_bytes": bundle_path.stat().st_size if bundle_path.exists() else 0,
        "ground_truth_files": len(list((BOOTSTRAP_ROOT / "ground_truth").glob("*"))),
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"[OK] Wrote bootstrap manifest to {manifest_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
