#!/bin/bash

# ==========================================
# SOVEREIGN OS - DRIVE-BY MESH RECONFIG DAEMON
# Target Node: 114 (Hobbes)
# Target IP: 100.88.5.122
# ==========================================

TARGET_IP="100.88.5.122"
SSID="Spectrum WiFi 6"
PASSWORD="swiftlion305"

echo "======================================================"
echo "🛡️ ARMING DRIVE-BY MESH RECONFIG DAEMON 🛡️"
echo "Target Node: $TARGET_IP"
echo "Target Network: $SSID"
echo "Status: SCANNING FOR HOTSPOT RECONNECTION..."
echo "======================================================"

while true; do
    if ping -c 1 -W 1 "$TARGET_IP" &> /dev/null; then
        echo -e "\n[!] TARGET ACQUIRED! NODE 114 IS ON THE MESH!"
        echo "[!] INITIATING SECURE SSH INJECTION..."
        
        # Inject the Wi-Fi credentials via SSH
        ssh -o StrictHostKeyChecking=no james@"$TARGET_IP" << EOF
            echo "[*] Injecting via NetworkManager (nmcli)..."
            sudo nmcli dev wifi connect "$SSID" password "$PASSWORD" || true
            
            echo "[*] Injecting backup via wpa_supplicant..."
            echo -e "\nnetwork={\n  ssid=\"$SSID\"\n  psk=\"$PASSWORD\"\n}\n" | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf
            sudo wpa_cli -i wlan0 reconfigure || true
            
            echo "[*] INJECTION COMPLETE. Node 114 should now connect to Spectrum."
EOF
        
        echo -e "\n======================================================"
        echo "🚨 MISSION ACCOMPLISHED! THE DRIVE-BY WAS A SUCCESS! 🚨"
        echo "Node 114 has been injected with Eileen's Wi-Fi credentials."
        echo "You may now drive away. Verify via 'tailscale status' in 2 mins."
        echo "======================================================"
        break
    else
        echo -ne "Scanning... Node 114 offline. Waiting for drive-by approach...\r"
        sleep 2
    fi
done
