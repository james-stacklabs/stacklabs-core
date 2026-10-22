USER="james"
STREAMER_PATH="/home/james/stacklabs/scripts/maintenance/argus_streamer.py"

for ip in 192.168.1.114 192.168.1.115 192.168.1.183; do
    echo "====================================="
    echo "Starting streamer on $ip..."
    
    # Kill any existing ones just in case
    ssh -o StrictHostKeyChecking=no $USER@$ip "pkill -f argus_streamer.py" || true
    
    echo "Copying streamer to $ip..."
    scp -o StrictHostKeyChecking=no $STREAMER_PATH $USER@$ip:/home/james/argus_streamer.py
    
    echo "Starting streamer on $ip..."
    ssh -o StrictHostKeyChecking=no $USER@$ip "nohup python3 /home/james/argus_streamer.py > /dev/null 2>&1 &"
    
    echo "Done on $ip"
done
