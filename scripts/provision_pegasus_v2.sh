#!/bin/bash

echo "[*] Re-Provisioning Node .74 (Pi 5)..."

echo "[1/5] Generating a dedicated Sovereign SSH Key to bypass password prompts..."
if [ ! -f ~/.ssh/id_pegasus ]; then
    ssh-keygen -t ed25519 -f ~/.ssh/id_pegasus -N "" -q
fi

echo "-> Type your Ubuntu password ONE last time to lock the Sovereign key in:"
ssh-copy-id -f -i ~/.ssh/id_pegasus.pub -o StrictHostKeyChecking=accept-new james@192.168.1.74

echo ""
echo "[2/5] Network Diagnostic Check..."
ssh -i ~/.ssh/id_pegasus james@192.168.1.74 'ping -c 1 google.com && echo "[NET_OK]" || echo "[NET_FAIL] No internet access on Pegasus!"'

echo ""
echo "[3/5] Remotely Executing Ollama Engine Injection..."
echo "-> You will be prompted for your Ubuntu password by 'sudo' on Pegasus:"
ssh -i ~/.ssh/id_pegasus -t james@192.168.1.74 'curl -fsSL https://ollama.com/install.sh -o install.sh && sudo sh install.sh'

echo ""
echo "[4/5] Reconfiguring Systemd for LAN Exposure (OLLAMA_HOST=0.0.0.0)..."
ssh -i ~/.ssh/id_pegasus -t james@192.168.1.74 'sudo mkdir -p /etc/systemd/system/ollama.service.d && echo -e "[Service]\nEnvironment=\"OLLAMA_HOST=0.0.0.0\"" | sudo tee /etc/systemd/system/ollama.service.d/override.conf'
ssh -i ~/.ssh/id_pegasus -t james@192.168.1.74 'sudo systemctl daemon-reload && sudo systemctl restart ollama'

echo ""
echo "[5/5] Activating Standard Inference Engine (llama3)..."
ssh -i ~/.ssh/id_pegasus -t james@192.168.1.74 'ollama pull llama3'

echo ""
echo "[*] Dreadnought Core is ACTIVE. Accessible on LAN via 192.168.1.74:11434"
