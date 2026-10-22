#!/bin/bash

# Define the ASCII Art for Grogu
cat << 'EOF' > /tmp/grogu_motd
========================================================================
   ██████╗ ██████╗  ██████╗  ██████╗ ██╗   ██╗
  ██╔════╝ ██╔══██╗██╔═══██╗██╔════╝ ██║   ██║
  ██║  ███╗██████╔╝██║   ██║██║  ███╗██║   ██║
  ██║   ██║██╔══██╗██║   ██║██║   ██║██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝╚██████╔╝
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝  ╚═════╝ 
========================================================================
             S O V E R E I G N   O P T I C S                 
                  [ NODE .170 ACTIVE ]               
========================================================================
EOF

echo "Setting MOTD on 192.168.1.170..."
cat /tmp/grogu_motd | ssh -o StrictHostKeyChecking=no james@192.168.1.170 "sudo tee /etc/motd"

echo "Installing Tailscale on 192.168.1.170..."
ssh -o StrictHostKeyChecking=no james@192.168.1.170 "curl -fsSL https://tailscale.com/install.sh | sh"

echo "Starting Tailscale on 192.168.1.170..."
ssh -o StrictHostKeyChecking=no -t james@192.168.1.170 "sudo tailscale up"
