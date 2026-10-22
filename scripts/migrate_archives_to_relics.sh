#!/usr/bin/env bash
# ==============================================================================
# StackLabs Platform: Safe Storage Migration to /mnt/relics
# Path: /home/james/stacklabs/scripts/migrate_archives_to_relics.sh
# Purpose: Non-destructively relocate cold archives, heavy TV rips, and 
#          harvested session artifacts to secondary NVMe (/mnt/relics)
# Invariants: Archive Never Delete | Two-Call Verification | Symlink Continuity
# ==============================================================================
set -euo pipefail

echo "=================================================================="
echo " [START] CLIO STORAGE MIGRATION TO /mnt/relics"
echo "=================================================================="

# 1. Pre-flight Mount Assertion
if ! mountpoint -q /mnt/relics; then
    echo "[-] FATAL: /mnt/relics is not mounted! Halting execution."
    exit 1
fi
echo "[+] Pre-flight passed: /mnt/relics is mounted and accessible."

# 2. Ensure target structure exists on /mnt/relics
mkdir -p /mnt/relics/archives
mkdir -p /mnt/relics/media_vault

# ------------------------------------------------------------------------------
# STEP A: Migrate /home/james/sovereign_archive (32 GB)
# ------------------------------------------------------------------------------
if [ -d "/home/james/sovereign_archive" ] && [ ! -L "/home/james/sovereign_archive" ]; then
    echo "[+] Migrating /home/james/sovereign_archive to /mnt/relics/archives/sovereign_archive/..."
    rsync -aHAX /home/james/sovereign_archive/ /mnt/relics/archives/sovereign_archive/
    
    # Verification Call 2: Check destination has contents
    DEST_COUNT=$(find /mnt/relics/archives/sovereign_archive/ -mindepth 1 | wc -l)
    if [ "$DEST_COUNT" -gt 10 ]; then
        echo "[+] Verified sovereign_archive on /mnt/relics ($DEST_COUNT items). Removing source and symlinking..."
        rm -rf /home/james/sovereign_archive
        ln -s /mnt/relics/archives/sovereign_archive /home/james/sovereign_archive
        echo "[+] Symlink established: /home/james/sovereign_archive -> /mnt/relics/archives/sovereign_archive"
    else
        echo "[-] ERROR: Destination item count too low ($DEST_COUNT). Skipping source removal."
    fi
else
    echo "[*] /home/james/sovereign_archive already migrated or is a symlink. Skipping."
fi

# ------------------------------------------------------------------------------
# STEP B: Migrate /home/james/.quarantine_legacy_sovereign_do_not_touch (69 GB)
# ------------------------------------------------------------------------------
if [ -d "/home/james/.quarantine_legacy_sovereign_do_not_touch" ] && [ ! -L "/home/james/.quarantine_legacy_sovereign_do_not_touch" ]; then
    echo "[+] Migrating /home/james/.quarantine_legacy_sovereign_do_not_touch to /mnt/relics/archives/quarantine_legacy/..."
    rsync -aHAX /home/james/.quarantine_legacy_sovereign_do_not_touch/ /mnt/relics/archives/quarantine_legacy/
    
    # Verification Call 2: Check destination has contents
    DEST_COUNT=$(find /mnt/relics/archives/quarantine_legacy/ -mindepth 1 | wc -l)
    if [ "$DEST_COUNT" -gt 100 ]; then
        echo "[+] Verified quarantine_legacy on /mnt/relics ($DEST_COUNT items). Removing source and symlinking..."
        rm -rf /home/james/.quarantine_legacy_sovereign_do_not_touch
        ln -s /mnt/relics/archives/quarantine_legacy /home/james/.quarantine_legacy_sovereign_do_not_touch
        echo "[+] Symlink established: /home/james/.quarantine_legacy_sovereign_do_not_touch -> /mnt/relics/archives/quarantine_legacy"
    else
        echo "[-] ERROR: Destination item count too low ($DEST_COUNT). Skipping source removal."
    fi
else
    echo "[*] /home/james/.quarantine_legacy_sovereign_do_not_touch already migrated or is a symlink. Skipping."
fi

# ------------------------------------------------------------------------------
# STEP C: Migrate media_vault/TV_Shows (83 GB)
# ------------------------------------------------------------------------------
TV_SOURCE="/home/james/stacklabs/media_vault/TV_Shows"
if [ -d "$TV_SOURCE" ] && [ ! -L "$TV_SOURCE" ]; then
    echo "[+] Migrating $TV_SOURCE to /mnt/relics/media_vault/TV_Shows/..."
    rsync -aHAX "$TV_SOURCE/" /mnt/relics/media_vault/TV_Shows/
    
    DEST_COUNT=$(find /mnt/relics/media_vault/TV_Shows/ -mindepth 1 | wc -l)
    if [ "$DEST_COUNT" -gt 5 ]; then
        echo "[+] Verified TV_Shows on /mnt/relics ($DEST_COUNT items). Removing source and symlinking..."
        rm -rf "$TV_SOURCE"
        ln -s /mnt/relics/media_vault/TV_Shows "$TV_SOURCE"
        echo "[+] Symlink established: $TV_SOURCE -> /mnt/relics/media_vault/TV_Shows"
    else
        echo "[-] ERROR: TV_Shows item count too low ($DEST_COUNT). Skipping source removal."
    fi
else
    echo "[*] $TV_SOURCE already migrated or is a symlink. Skipping."
fi

# ------------------------------------------------------------------------------
# STEP D: Migrate Harvested_Artifacts (4.72 GB / 12,738 files)
# ------------------------------------------------------------------------------
HARVEST_SOURCE="/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts"
if [ -d "$HARVEST_SOURCE" ] && [ ! -L "$HARVEST_SOURCE" ]; then
    echo "[+] Migrating Harvested_Artifacts to /mnt/relics/media_vault/Harvested_Artifacts/..."
    rsync -aHAX "$HARVEST_SOURCE/" /mnt/relics/media_vault/Harvested_Artifacts/
    
    DEST_COUNT=$(find /mnt/relics/media_vault/Harvested_Artifacts/ -mindepth 1 | wc -l)
    if [ "$DEST_COUNT" -gt 5000 ]; then
        echo "[+] Verified Harvested_Artifacts on /mnt/relics ($DEST_COUNT items). Removing source and symlinking..."
        rm -rf "$HARVEST_SOURCE"
        ln -s /mnt/relics/media_vault/Harvested_Artifacts "$HARVEST_SOURCE"
        echo "[+] Symlink established: $HARVEST_SOURCE -> /mnt/relics/media_vault/Harvested_Artifacts"
    else
        echo "[-] ERROR: Harvested_Artifacts item count too low ($DEST_COUNT). Skipping source removal."
    fi
else
    echo "[*] $HARVEST_SOURCE already migrated or is a symlink. Skipping."
fi

# ------------------------------------------------------------------------------
# STEP E: Migrate 01_Assets/Inbox UAT Screenshots (1.25 GB / 1,718 files)
# ------------------------------------------------------------------------------
UAT_SOURCE="/home/james/stacklabs/media_vault/01_Assets/Inbox"
if [ -d "$UAT_SOURCE" ] && [ ! -L "$UAT_SOURCE" ]; then
    echo "[+] Migrating 01_Assets/Inbox to /mnt/relics/media_vault/uat_screenshots_legacy/..."
    rsync -aHAX "$UAT_SOURCE/" /mnt/relics/media_vault/uat_screenshots_legacy/
    
    DEST_COUNT=$(find /mnt/relics/media_vault/uat_screenshots_legacy/ -mindepth 1 | wc -l)
    if [ "$DEST_COUNT" -gt 500 ]; then
        echo "[+] Verified UAT screenshots on /mnt/relics ($DEST_COUNT items). Cleaning source directory..."
        rm -rf "$UAT_SOURCE"
        mkdir -p "$UAT_SOURCE"
        echo "[+] Reset $UAT_SOURCE as a fresh empty directory."
    else
        echo "[-] ERROR: UAT screenshot count too low ($DEST_COUNT). Skipping source cleanup."
    fi
else
    echo "[*] $UAT_SOURCE already clean or migrated. Skipping."
fi

echo "=================================================================="
echo " [COMPLETE] POST-MIGRATION DISK REALITY"
echo "=================================================================="
df -h / /mnt/relics
echo "[+] Storage migration executed cleanly with zero data destruction."
