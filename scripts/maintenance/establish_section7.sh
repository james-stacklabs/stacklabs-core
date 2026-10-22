#!/bin/bash
# ==============================================================================
# SOVEREIGN OS // SECTION 7 INITIALIZATION PROTOCOL
# TARGET: 64GB MicroSD (mmcblk0) -> "Smuggler's Bay / Un-Circle-Jerked Data"
# ==============================================================================

TARGET_DEVICE="/dev/mmcblk0"
MOUNT_POINT="/mnt/section7"

echo "==========================================================="
echo "[WARNING] INITIATING SECTION 7 OVERRIDE"
echo "Targeting Ghost Drive: $TARGET_DEVICE"
echo "All ambient data on this MicroSD card is about to be purged."
echo "==========================================================="
echo ""
read -p "Type 'AUTHORIZE' to proceed with the scrub: " auth

if [ "$auth" != "AUTHORIZE" ]; then
    echo "Aborting Section 7 Initialization."
    exit 1
fi

echo ""
echo "[1/4] Formatting $TARGET_DEVICE to ext4 (Wiping the Slate)..."
mkfs.ext4 -F $TARGET_DEVICE

echo "[2/4] Constructing the Section 7 physical mount point at $MOUNT_POINT..."
mkdir -p $MOUNT_POINT

echo "[3/4] Mounting the Ghost Drive..."
mount $TARGET_DEVICE $MOUNT_POINT

echo "[4/4] Assigning Sovereign Read/Write Permissions to Operator '$SUDO_USER'..."
chown -R $SUDO_USER:$SUDO_USER $MOUNT_POINT
chmod -R 775 $MOUNT_POINT

echo ""
echo "==========================================================="
echo "SECTION 7 IS ONLINE."
echo "==========================================================="
df -h $MOUNT_POINT
echo ""
echo "Next Step: Samba & Rclone configuration..."
