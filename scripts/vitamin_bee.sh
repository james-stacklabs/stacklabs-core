#!/bin/bash
# Sovereign OS - Vitamin Bee Injection Payload
# Upgrades freshly minted SD cards into Sovereign Argus Nodes

echo "[!] IGNITING VITAMIN BEE INJECTION ON $(hostname)..."

# 1. Purge the legacy configuration hugging Port 8081
echo "[*] Purging legacy motion daemons..."
sudo systemctl stop motion 2>/dev/null
sudo systemctl disable motion 2>/dev/null
sudo killall -9 motion 2>/dev/null

# 2. Inject Sovereign DNA (Dependencies)
echo "[*] Splicing Python DNA (Flask/OpenCV)..."
sudo apt-get update > /dev/null
sudo apt-get install -y python3-flask python3-opencv > /dev/null

# 3. Cement the Sovereign Systemd Service
echo "[*] Cementing new argus-streamer service..."
cat << 'SVC' | sudo tee /etc/systemd/system/argus-streamer.service > /dev/null
[Unit]
Description=Argus Node Streamer (Sovereign OS Dynamic Dual-Optic)
After=network.target

[Service]
User=james
WorkingDirectory=/home/james
ExecStart=/usr/bin/python3 /home/james/argus_streamer.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SVC

# 4. Ignite the Node
echo "[*] Igniting new biological pathways..."
sudo systemctl daemon-reload
sudo systemctl enable argus-streamer
sudo systemctl restart argus-streamer

echo "[============ SOVEREIGN NODE ONLINE ============]"
echo "[+] DNA Injected successfully."
echo "[+] Optic Array now streaming dynamically on /cam/X"
