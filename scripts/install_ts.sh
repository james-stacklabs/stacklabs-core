PASSWORD='!!Stella1977'
ssh -o StrictHostKeyChecking=no james@192.168.1.183 "echo '$PASSWORD' | sudo -S sh -c '
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null &&
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list &&
apt-get update &&
apt-get install -y tailscale
'"
