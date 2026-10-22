#!/bin/bash
NODES=("192.168.1.114" "192.168.1.115")
NAMES=("Mando" "Calvin")

echo "=== ARGUS FLEET RESTART ==="
for i in "${!NODES[@]}"; do
    ip="${NODES[$i]}"
    name="${NAMES[$i]}"
    echo ""
    echo "--- $name ($ip) ---"
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no james@$ip \
        "sudo systemctl restart argus-streamer.service && \
         sleep 2 && \
         systemctl is-active argus-streamer.service" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ $name Argus restarted"
    else
        echo "✗ $name failed — trying reboot..."
        ssh -o ConnectTimeout=5 james@$ip "sudo reboot" 2>/dev/null
        echo "↻ $name rebooting — back in ~60 seconds"
    fi
done

echo ""
echo "=== STREAM VERIFICATION ==="
sleep 5
for i in "${!NODES[@]}"; do
    ip="${NODES[$i]}"
    name="${NAMES[$i]}"
    curl -s --max-time 3 http://$ip:8081 > /dev/null && \
        echo "✓ $name :8081 STREAMING" || \
        echo "✗ $name :8081 NOT STREAMING"
done
echo ""
echo "=== DONE ==="
