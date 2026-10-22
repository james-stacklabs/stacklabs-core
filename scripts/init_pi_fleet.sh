#!/usr/bin/env bash
# /home/james/stacklabs/scripts/init_pi_fleet.sh

echo "=========================================="
echo "Sovereign OS: Pi Fleet Initialization"
echo "=========================================="
echo "This script will deploy static IPs (.150 block) and Tailscale to the fresh Pis."
echo "You will be prompted for your SSH password for the 'james' user."
echo ""

read -s -p "Enter SSH/Sudo Password for Pis: " PI_PASS
echo ""

declare -A PI_NODES
# FORMAT: [Current_IP]="Target_IP"
PI_NODES=(
    ["192.168.1.115"]="192.168.1.152" # calvin
    ["192.168.1.116"]="192.168.1.153" # mando
    ["192.168.1.185"]="192.168.1.154" # grogu
    ["192.168.1.186"]="192.168.1.155" # stimpy
)

for CURRENT_IP in "${!PI_NODES[@]}"; do
    TARGET_IP="${PI_NODES[$CURRENT_IP]}"
    echo "[*] Connecting to $CURRENT_IP (Target: $TARGET_IP)..."
    
    # We use sshpass to inject the password for ssh and sudo
    # First, verify connection
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 james@$CURRENT_IP "echo 'Connection successful'" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "  [!] Failed to connect to $CURRENT_IP. Skipping."
        continue
    fi

    # 1. Install Tailscale
    echo "  [+] Installing Tailscale..."
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no james@$CURRENT_IP "echo $PI_PASS | sudo -S curl -fsSL https://tailscale.com/install.sh | sh" > /dev/null 2>&1

    # 2. Configure Static IP
    echo "  [+] Setting static IP to $TARGET_IP..."
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no james@$CURRENT_IP "echo $PI_PASS | sudo -S nmcli con mod 'netplan-wlan0-ATTFVVFDJD' ipv4.addresses '$TARGET_IP/24' ipv4.gateway '192.168.1.1' ipv4.dns '8.8.8.8' ipv4.method 'manual' || echo $PI_PASS | sudo -S nmcli con mod 'preconfigured' ipv4.addresses '$TARGET_IP/24' ipv4.gateway '192.168.1.1' ipv4.dns '8.8.8.8' ipv4.method 'manual'" > /dev/null 2>&1

    # 3. Reboot to apply network changes
    echo "  [+] Rebooting node to apply new network configuration..."
    sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no james@$CURRENT_IP "echo $PI_PASS | sudo -S reboot" > /dev/null 2>&1
    
    echo "  [OK] $CURRENT_IP initialized and moving to $TARGET_IP!"
    echo "------------------------------------------"
done

echo "Fleet Initialization Complete. They will appear on Tailscale shortly."
