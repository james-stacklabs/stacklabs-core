USER="james"
for ip in 192.168.1.114 192.168.1.115 192.168.1.183; do
    echo "Installing deps on $ip..."
    ssh -o StrictHostKeyChecking=no $USER@$ip "echo '!!Stella1977' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y python3-opencv python3-flask"
done
