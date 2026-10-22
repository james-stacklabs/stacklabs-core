#!/bin/bash
echo "[*] Initializing Network Suture for Sovereign Pegasus link..."

echo "1. Disabling the Edimax dongle software profile route (wlx74da3858bbdc)..."
sudo nmcli device disconnect wlx74da3858bbdc 2>/dev/null || true
echo "2. Setting wlp6s0 (AzureWave) 5GHz priority (band a, channel 48)..."
sudo nmcli connection modify ATTFVVFDJD 802-11-wireless.band a 802-11-wireless.channel 48
echo "3. Forcing reconnect on 5GHz..."
sudo nmcli connection down ATTFVVFDJD
sleep 1
sudo nmcli connection up ATTFVVFDJD

echo "[SYS] SUTURE COMPLETE. PEGASUS LINK SECURED OVER 5GHz."
