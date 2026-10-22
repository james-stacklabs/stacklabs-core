#!/bin/bash
set -e
echo "[*] Bridging the Sovereign Key securely to .168..."
sshpass -p '!!Stella1977' ssh-copy-id -o StrictHostKeyChecking=accept-new -i /home/james/.ssh/id_ed25519.pub james@192.168.1.168 2>/dev/null || true

echo "[*] Trust established. Securing target structure via RSA/ED25519..."
ssh -o StrictHostKeyChecking=accept-new james@192.168.1.168 "mkdir -p /home/james/stacklabs/dna/archives/uat_evidence /home/james/stacklabs/dna/logs"

echo "[*] Syphoning APIARY architecture across 5GHz Link..."
rsync -avz --exclude 'node_modules' --exclude '__pycache__' -e "ssh -o StrictHostKeyChecking=accept-new" /home/james/stacklabs/ james@192.168.1.168:/home/james/stacklabs/

echo "[*] Dropping NVENC Temporal Render logic into GTX 980 pipeline..."
ssh -o StrictHostKeyChecking=accept-new james@192.168.1.168 "bash /home/james/stacklabs/scripts/trigger_burn.sh"

echo "[*] Render Complete. Synchronizing decoded 60FPS artifacts back to Native Node .73..."
rsync -avz -e "ssh -o StrictHostKeyChecking=accept-new" james@192.168.1.168:/home/james/stacklabs/dna/archives/uat_evidence/ /home/james/stacklabs/dna/archives/uat_evidence/
rsync -avz -e "ssh -o StrictHostKeyChecking=accept-new" james@192.168.1.168:/home/james/stacklabs/dna/logs/CMDB_GPU_BURN.log /home/james/stacklabs/dna/logs/

echo "[SYS] MASTER NVENC BURN COMPILED LOCALLY."
