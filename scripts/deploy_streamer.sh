USER="james"
STREAMER_PATH="/home/james/stacklabs/scripts/maintenance/argus_streamer.py"

for ip in 192.168.1.114 192.168.1.115 192.168.1.183; do
    echo "====================================="
    echo "Deploying to Node $ip..."
    
    # Check if running
    if ssh -o StrictHostKeyChecking=no $USER@$ip "pgrep -f argus_streamer.py > /dev/null"; then
        echo "argus_streamer.py is already running on $ip"
    else
        echo "Copying streamer to $ip..."
        scp -o StrictHostKeyChecking=no $STREAMER_PATH $USER@$ip:/home/james/argus_streamer.py
        
        echo "Starting streamer on $ip..."
        ssh -o StrictHostKeyChecking=no $USER@$ip "nohup python3 /home/james/argus_streamer.py > /dev/null 2>&1 &"
        
        # Verify it started
        sleep 2
        if ssh -o StrictHostKeyChecking=no $USER@$ip "pgrep -f argus_streamer.py > /dev/null"; then
            echo "Successfully started on $ip"
        else
            echo "Failed to start on $ip"
        fi
    fi
done
