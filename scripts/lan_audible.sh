#!/bin/bash
echo "[1/3] Multiplexing download on Node .73 (bypassing CDN throttle)..."
sudo apt update > /dev/null 2>&1
sudo apt install -y aria2 > /dev/null 2>&1
rm -f /tmp/ollama.tgz
aria2c -x 16 -s 16 -d /tmp -o ollama.tgz "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tgz" || aria2c -x 16 -s 16 -d /tmp -o ollama.tgz "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst"

echo "[2/3] Transferring payload to Pegasus via LAN..."
scp -o "StrictHostKeyChecking=accept-new" -i ~/.ssh/id_pegasus /tmp/ollama.tgz james@192.168.1.74:/tmp/ollama.tgz

echo "[3/3] Remotely installing on Pegasus..."
ssh -t -i ~/.ssh/id_pegasus james@192.168.1.74 << 'EOF'
    sudo tar -C /usr -xf /tmp/ollama.tgz || sudo tar -C /usr -xvf /tmp/ollama.tgz || sudo tar -C /usr --zstd -xf /tmp/ollama.tgz
    sudo rm -f /tmp/ollama.tgz
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
    echo "Daemon active. Native pull initializing."
    ollama pull llama3:8b
EOF
