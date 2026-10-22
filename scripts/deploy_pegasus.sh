#!/bin/bash
set -x

echo "[*] Transferring Suture and Burn scripts to .168..."
sshpass -p '!!Stella1977' scp -o StrictHostKeyChecking=accept-new /home/james/stacklabs/scripts/network_suture.sh james@192.168.1.168:/tmp/
sshpass -p '!!Stella1977' scp -o StrictHostKeyChecking=accept-new /home/james/stacklabs/scripts/trigger_burn.sh james@192.168.1.168:/tmp/

echo "[*] Triggering 5GHz Suture..."
sshpass -p '!!Stella1977' ssh -n -o StrictHostKeyChecking=accept-new james@192.168.1.168 'nohup bash /tmp/network_suture.sh > /tmp/suture.log 2>&1 &'

echo "[*] Waiting 15s for the 5GHz network jump..."
sleep 15

echo "[*] Re-engaging heavy Rsync over the new 5GHz pipe to move massive payloads..."
sshpass -p '!!Stella1977' rsync -a --exclude 'node_modules' --exclude '__pycache__' -e "ssh -o StrictHostKeyChecking=accept-new" /home/james/stacklabs/ james@192.168.1.168:/home/james/stacklabs/

echo "[*] Executing NVENC Temporal Burn..."
sshpass -p '!!Stella1977' ssh -o StrictHostKeyChecking=accept-new james@192.168.1.168 'bash /tmp/trigger_burn.sh'

echo "[*] Pulling encoded assets back..."
sshpass -p '!!Stella1977' rsync -av -e "ssh -o StrictHostKeyChecking=accept-new" james@192.168.1.168:/home/james/stacklabs/dna/archives/uat_evidence/ /home/james/stacklabs/dna/archives/uat_evidence/
sshpass -p '!!Stella1977' rsync -av -e "ssh -o StrictHostKeyChecking=accept-new" james@192.168.1.168:/home/james/stacklabs/dna/logs/CMDB_GPU_BURN.log /home/james/stacklabs/dna/logs/
echo "[SYS] MASTER PEGSAUS NVENC DEPLOYMENT SUCCESSFUL."
