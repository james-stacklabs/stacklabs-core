#!/bin/bash

# Ensure non-interactive prompts don't block known hosts
echo "[*] Provisioning Node .74 (Pi 5)..."

echo "[1/4] Establishing secure SSH keys..."
echo "-> You may be prompted to enter your Ubuntu (.74) password here to push the keys:"
ssh-copy-id -o StrictHostKeyChecking=accept-new james@192.168.1.74

echo ""
echo "[2/4] Remotely Executing Ollama Engine Injection..."
ssh james@192.168.1.74 'curl -fsSL https://ollama.com/install.sh | sudo sh'

echo ""
echo "[3/4] Reconfiguring Systemd for LAN Exposure (OLLAMA_HOST=0.0.0.0)..."
ssh james@192.168.1.74 'sudo mkdir -p /etc/systemd/system/ollama.service.d && echo -e "[Service]\nEnvironment=\"OLLAMA_HOST=0.0.0.0\"" | sudo tee /etc/systemd/system/ollama.service.d/override.conf'
ssh james@192.168.1.74 'sudo systemctl daemon-reload && sudo systemctl restart ollama'

echo ""
echo "[4/4] Activating Standard Inference Engine (llama3)..."
ssh james@192.168.1.74 'ollama pull llama3'

echo ""
echo "[*] Dreadnought Core is ACTIVE. Accessible on LAN via 192.168.1.74:11434"
