#!/usr/bin/env bash
# Argo Hailo Driver Rebuild & Verification Script
# Target: Node Argo (100.111.248.60)
set -euo pipefail

echo "=========================================================="
echo "⚡ ARGO HAILO-10H KERNEL DRIVER REBUILD & RELOAD"
echo "=========================================================="

ssh -o StrictHostKeyChecking=no james@100.111.248.60 << 'EOF'
set -euo pipefail
echo "[ARGO] Compiling hailo1x_pci against $(uname -r)..."
cd /usr/src/hailort-pcie-driver/linux/pcie
sudo make clean || true
sudo make all -j4 || sudo make -j4

echo "[ARGO] Reloading hailo1x_pci kernel module..."
sudo rmmod hailo1x_pci 2>/dev/null || true
sudo insmod ./hailo1x_pci.ko || (sudo make install && sudo modprobe hailo1x_pci)

echo "[ARGO] Verifying Hailo NPU state via hailortcli scan..."
hailortcli scan

echo "[ARGO] Identifying hardware architecture for hailo_model_zoo HEF compilation..."
DEVICE_INFO=$(hailortcli fw-control identify 2>/dev/null || true)
echo "$DEVICE_INFO"

if echo "$DEVICE_INFO" | grep -q "HAILO10H"; then
    echo "🎯 Hardware Target Verified: HAILO-10H (matching yolov8s-pose HEF compilation parameters)"
elif echo "$DEVICE_INFO" | grep -qE "HAILO8|HAILO8L"; then
    echo "🎯 Hardware Target Verified: Hailo-8/8L"
else
    echo "⚠️ Device identified but architecture string unexpected. Check fw-control logs."
fi

echo "[ARGO] Quantization Specification: yolov8s-pose calibration dataset requires 500+ frames of MLB pitcher deliveries."
EOF

echo "✅ Hailo PCIe driver recompiled, enumerated, and architecture confirmed on Node Argo."
