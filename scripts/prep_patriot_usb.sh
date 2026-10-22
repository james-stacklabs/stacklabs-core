#!/bin/bash
# OMEGA-GATE: Sneakernet Patriot USB Field Deployer

echo "========================================================="
echo " OMEGA-GATE: SNEAKERNET PREP SEQUENCE "
echo "========================================================="
echo "[*] Scanning bus for Patriot 128GB USB module..."

USB_DEV=$1

if [ -z "$USB_DEV" ]; then
    echo "[-] Cannot auto-detect the Patriot USB partition reliably."
    echo "    Please run the script with the device path as an argument. Example: ./scripts/prep_patriot_usb.sh /dev/sda1"
    echo ""
    echo "Available partitions on removable drives:"
    lsblk -o NAME,SIZE,TYPE,MODEL,RM | grep -E "part|1"
    exit 1
fi

echo "[+] Detected Patriot partition at $USB_DEV"

sudo mkdir -p /mnt/patriot
sudo mount $USB_DEV /mnt/patriot 2>/dev/null

echo "[+] Staging 1.8GB Daemon Core (ollama.tgz) into the Sneakernet payload..."
sudo cp /tmp/ollama.tgz /mnt/patriot/

echo "[+] Packing Pegasus Mission Control Dashboard..."
sudo cp /home/james/stacklabs/scripts/pegasus_dashboard.py /mnt/patriot/

echo "[+] Writing Field Deployment Executable (DEPLOY_PEGASUS.sh)..."
cat << 'EOF' | sudo tee /mnt/patriot/DEPLOY_PEGASUS.sh > /dev/null
#!/bin/bash
echo "========================================================="
echo " OMEGA-GATE: FIELD DEPLOYMENT INITIATED "
echo "========================================================="
echo "[1/3] Extracting Daemon Core (This takes a minute...)"
sudo tar -C /usr -xf ollama.tgz || sudo tar -C /usr --zstd -xf ollama.tgz

echo "[2/3] Configuring Systemd and Daemon Access..."
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama 2>/dev/null || true
sudo usermod -a -G video ollama 2>/dev/null || true

echo "[Unit]
Description=Ollama Service
After=network-online.target
[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment=\"OLLAMA_HOST=0.0.0.0\"
[Install]
WantedBy=default.target" | sudo tee /etc/systemd/system/ollama.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

echo "[3/3] Rigging NASA Mission Control Dashboard..."
# Install the python rich and psutil UI frameworks so the dashboard actually renders
sudo apt update && sudo apt install -y python3-rich python3-psutil
cp pegasus_dashboard.py ~/pegasus_dashboard.py

echo "========================================================="
echo " FIELD DEPLOYMENT COMPLETE "
echo " -> To boot your dashboard, run: python3 ~/pegasus_dashboard.py "
echo " -> To start the native Llama3 pull, run: ollama pull llama3:8b "
echo "========================================================="
EOF

sudo chmod +x /mnt/patriot/DEPLOY_PEGASUS.sh

echo "[+] Safely unmounting Patriot to prevent payload corruption..."
sudo sync
sudo umount /mnt/patriot

echo "========================================================="
echo " SNEAKERNET READY."
echo " You may rip the USB drive out and walk it to Pegasus."
echo " Just run DEPLOY_PEGASUS.sh on Node .74!"
echo "========================================================="
