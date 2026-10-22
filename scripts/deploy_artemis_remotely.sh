#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Artemis Workstation Automated Remote Provisioner
# Executed from Clio -> Artemis (over Tailscale / LAN)
# ==============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_HOST="${1:-100.108.185.53}"
TARGET_USER="james"

echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN} Sovereign OS: Artemis Cockpit Remote Provisioning Engine${NC}"
echo -e "${CYAN} Target: ${TARGET_USER}@${TARGET_HOST}${NC}"
echo -e "${CYAN}====================================================================${NC}"

# 1. Test connectivity
echo -e "${CYAN}[1/6] Verifying network reachability to Artemis...${NC}"
if ! ping -c 1 -W 3 "${TARGET_HOST}" > /dev/null 2>&1; then
    echo -e "${RED}[ERROR] Cannot ping ${TARGET_HOST}. Ensure Tailscale is up on Artemis!${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Artemis is online and responding (${TARGET_HOST}).${NC}"

# 2. Setup SSH Key if needed
echo -e "${CYAN}[2/6] Ensuring passwordless SSH authentication...${NC}"
if [ ! -f ~/.ssh/id_rsa.pub ] && [ ! -f ~/.ssh/id_ed25519.pub ]; then
    ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q
fi

# 3. Base Developer Stack & Utilities
echo -e "${CYAN}[3/6] Installing developer utilities, shells, runtimes & Barrier on Artemis...${NC}"
ssh -t "${TARGET_USER}@${TARGET_HOST}" 'sudo bash -c "
DEBIAN_FRONTEND=noninteractive apt-get update -y && \
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl wget git build-essential \
    ripgrep fzf btop htop tmux jq tree tilix barrier \
    python3 python3-pip python3-venv python3-dev \
    nodejs npm net-tools openssh-server \
    libnspr4 libnss3 libgtk-3-0t64 libasound2t64 libgbm1 libxss1
"'

# 4. Install Google Chrome (Native Linux DEB)
echo -e "${CYAN}[4/6] Installing Google Chrome on Artemis...${NC}"
ssh -t "${TARGET_USER}@${TARGET_HOST}" 'bash -c "
if ! command -v google-chrome &> /dev/null; then
    wget -q -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y /tmp/google-chrome-stable_current_amd64.deb
    rm -f /tmp/google-chrome-stable_current_amd64.deb
fi
"'

# 5. Mirror Antigravity CLI & Antigravity IDE from Clio
echo -e "${CYAN}[5/6] Mirroring Antigravity IDE & agy CLI to Artemis...${NC}"
ssh "${TARGET_USER}@${TARGET_HOST}" "mkdir -p ~/.local/bin ~/.gemini/config"

# Copy agy binary
rsync -avz /home/james/.local/bin/agy "${TARGET_USER}@${TARGET_HOST}:~/.local/bin/agy"
ssh "${TARGET_USER}@${TARGET_HOST}" "chmod +x ~/.local/bin/agy"

# Mirror /opt/antigravity
echo "Syncing /opt/antigravity distribution..."
ssh -t "${TARGET_USER}@${TARGET_HOST}" "sudo mkdir -p /opt/antigravity && sudo chown -R ${TARGET_USER}:${TARGET_USER} /opt/antigravity"
rsync -avz --progress /opt/antigravity/ "${TARGET_USER}@${TARGET_HOST}:/opt/antigravity/"
ssh -t "${TARGET_USER}@${TARGET_HOST}" "
sudo chown -R root:root /opt/antigravity
sudo chmod 4755 /opt/antigravity/chrome-sandbox || true
sudo ln -sf /opt/antigravity/antigravity-ide /usr/local/bin/antigravity
ln -sf /usr/local/bin/antigravity ~/.local/bin/antigravity
"

# 6. Sovereign Shell Aliases & Environment
echo -e "${CYAN}[6/6] Injecting Sovereign aliases and cockpit profile...${NC}"
ssh "${TARGET_USER}@${TARGET_HOST}" 'cat << "EOF" >> ~/.bashrc

# Sovereign OS Fleet Aliases
export PATH="$HOME/.local/bin:$PATH"
alias agy="$HOME/.local/bin/agy"
alias clio="ssh james@clio.taila01894.ts.net"
alias pegasus="ssh james@100.96.77.20"
alias argo="ssh james@argo.taila01894.ts.net"
alias mando="ssh james@100.120.34.87"
alias metsy="ssh james@metsy-prime.taila01894.ts.net"
alias cldb="curl -s http://clio.taila01894.ts.net:8095/api/tickets"
alias ll="ls -la --color=auto"
EOF'

# Prevent unintended sleep during cockpit sessions
ssh -t "${TARGET_USER}@${TARGET_HOST}" 'sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target || true'

echo ""
echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN} 🎉 Artemis Cockpit Provisioning Complete!${NC}"
echo -e "${GREEN} Antigravity IDE, agy CLI, Chrome, Node, Python & Fleet Mesh Active!${NC}"
echo -e "${GREEN}====================================================================${NC}"
