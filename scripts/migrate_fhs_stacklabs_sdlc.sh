#!/usr/bin/env bash
# ==============================================================================
# StackLabs Platform: Atomic FHS & SDLC Service Cutover Script
# Ticket: WO0010566
# Author: James Carroll (Lead Systems Architect)
# ==============================================================================
set -euo pipefail

echo "================================================================="
echo "⚡ [STACKLABS] Starting Atomic FHS & SDLC Service Cutover..."
echo "================================================================="

# 1. Ensure stacklabs group exists alongside sovereign
if ! getent group stacklabs >/dev/null 2>&1; then
    echo "Creating group 'stacklabs'..."
    sudo groupadd -f stacklabs
    sudo usermod -aG stacklabs james || true
fi

# 2. Establish Canonical FHS Directories
echo "Establishing /etc/stacklabs, /var/log/stacklabs, /var/lib/stacklabs/data, /srv/stacklabs..."
sudo mkdir -p /etc/stacklabs
sudo mkdir -p /var/log/stacklabs
sudo mkdir -p /var/lib/stacklabs/data
sudo mkdir -p /srv/stacklabs

sudo chown -R james:sovereign /etc/stacklabs /var/log/stacklabs /var/lib/stacklabs /srv/stacklabs
sudo chmod 775 /etc/stacklabs /var/log/stacklabs /var/lib/stacklabs /srv/stacklabs

# 3. Canonical Symlinks
echo "Establishing canonical symlinks..."
sudo ln -sfn /home/james/stacklabs /opt/stacklabs
sudo ln -sfn /home/james/stacklabs/dna/sovereign_now.db /var/lib/stacklabs/data/sovereign_now.db
sudo ln -sfn /home/james/stacklabs_inbox /srv/stacklabs/inbox

# 4. Fix Broken Legacy Symlinks & Provide Backward-Compatible Shims
echo "Bridging backward-compatible shims..."
# Link /opt/sovereign to /opt/stacklabs
sudo ln -sfn /opt/stacklabs /opt/sovereign
# Fix the broken /var/lib/sovereign/data/sovereign_now.db symlink
sudo mkdir -p /var/lib/sovereign/data
sudo ln -sfn /var/lib/stacklabs/data/sovereign_now.db /var/lib/sovereign/data/sovereign_now.db
# Ensure /srv/sovereign/inbox links to canonical inbox
sudo mkdir -p /srv/sovereign
sudo ln -sfn /srv/stacklabs/inbox /srv/sovereign/inbox

# 5. Populate /etc/stacklabs
echo "Writing /etc/stacklabs/stacklabs.env..."
sudo tee /etc/stacklabs/stacklabs.env > /dev/null << 'EOF'
# ==============================================================================
# STACKLABS PLATFORM CANONICAL ENTERPRISE ENVIRONMENT CONFIGURATION
# Single Source of Truth for Node Clio (100.73.155.70 / clio.taila01894.ts.net)
# ==============================================================================

# --- FILESYSTEM HIERARCHY STANDARD (FHS) ROOT PATHS ---
STACKLABS_ROOT="/opt/stacklabs"
STACKLABS_DB="/var/lib/stacklabs/data/sovereign_now.db"
STACKLABS_LOG_DIR="/var/log/stacklabs"
STACKLABS_INBOX="/srv/stacklabs/inbox"
STACKLABS_TAILNET_FQDN="clio.taila01894.ts.net"
STACKLABS_NODE_IP="100.73.155.70"

# Backward-Compatibility Environment Bindings for Legacy Services
SOVEREIGN_ROOT="/opt/stacklabs"
SOVEREIGN_DB="/var/lib/stacklabs/data/sovereign_now.db"
SOVEREIGN_DB_PATH="/home/james/stacklabs/dna/sovereign_now.db"
SOVEREIGN_LOG_DIR="/var/log/stacklabs"
SOVEREIGN_INBOX="/srv/stacklabs/inbox"
SOVEREIGN_TAILNET_FQDN="clio.taila01894.ts.net"
SOVEREIGN_NODE_IP="100.73.155.70"

# --- NETWORK & PORT ALLOCATION REGISTRY ---
STACKLABS_PORT_PORTAL=3016
STACKLABS_PORT_CMDB=3025
STACKLABS_PORT_APPROVAL=3027
STACKLABS_PORT_HOLODEX=3028
STACKLABS_PORT_MOBILE=3029
STACKLABS_PORT_CORE=8090
STACKLABS_PORT_SDLC=8095
STACKLABS_PORT_STREAM_SNIPER=5056

# --- RUNTIME & SERVICE IDENTITY ---
STACKLABS_USER="james"
STACKLABS_GROUP="sovereign"
NODE_ENV="production"
EOF

sudo chown james:sovereign /etc/stacklabs/stacklabs.env
sudo chmod 664 /etc/stacklabs/stacklabs.env

# Sync port registry
if [ -f /etc/sovereign/port_registry.json ]; then
    echo "Copying port_registry.json to /etc/stacklabs/..."
    sudo cp /etc/sovereign/port_registry.json /etc/stacklabs/port_registry.json
    sudo chown james:sovereign /etc/stacklabs/port_registry.json
fi

# Ensure /etc/sovereign/stacklabs.env symlink exists for legacy consumers
sudo ln -sfn /etc/stacklabs/stacklabs.env /etc/sovereign/stacklabs.env

# 6. Deploy systemd Unit File
echo "Deploying /etc/systemd/system/stacklabs-sdlc.service..."
sudo tee /etc/systemd/system/stacklabs-sdlc.service > /dev/null << 'EOF'
[Unit]
Description=StackLabs Platform SDLC Portal Server & FastAPI REST API (Port 8095)
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=james
Group=sovereign
WorkingDirectory=/opt/stacklabs
EnvironmentFile=/etc/stacklabs/stacklabs.env
ExecStart=/home/james/stacklabs/.venv/bin/python3 /opt/stacklabs/scripts/sdlc_portal_server.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 7. Atomic Service Cutover & Systemd Alias
echo "Executing atomic systemd reload and cutover..."
sudo systemctl daemon-reload

echo "Stopping legacy sovereign-sdlc.service..."
sudo systemctl stop sovereign-sdlc.service || true
sudo systemctl disable sovereign-sdlc.service || true

# Remove old sovereign-sdlc unit and replace with alias symlink to stacklabs-sdlc
sudo rm -f /etc/systemd/system/sovereign-sdlc.service
sudo ln -sfn /etc/systemd/system/stacklabs-sdlc.service /etc/systemd/system/sovereign-sdlc.service

sudo systemctl daemon-reload
echo "Starting and enabling canonical stacklabs-sdlc.service..."
sudo systemctl enable --now stacklabs-sdlc.service

# 8. Verification & Health Probing
echo "Waiting for socket bind and health response..."
LOCAL_HTTP="000"
for i in {1..10}; do
    LOCAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8095/api/health || true)
    if [ "$LOCAL_HTTP" = "200" ]; then
        echo "Socket responded on attempt $i"
        break
    fi
    sleep 1
done

if [ "$LOCAL_HTTP" != "200" ]; then
    echo "❌ [ERROR] Loopback health check failed with HTTP $LOCAL_HTTP"
    systemctl status stacklabs-sdlc.service --no-pager
    exit 1
fi
echo "✅ Loopback health check HTTP 200 OK!"

echo "Verifying Tailscale HTTPS 200 on Port 8095..."
TS_HTTP=$(curl -sk -o /dev/null -w "%{http_code}" https://clio.taila01894.ts.net:8095/api/health || true)
if [ "$TS_HTTP" != "200" ]; then
    echo "⚠️ [WARN] Tailscale FQDN check returned HTTP $TS_HTTP"
else
    echo "✅ Tailscale HTTPS health check HTTP 200 OK!"
fi

echo "Verifying systemd alias compatibility..."
systemctl is-active sovereign-sdlc.service
systemctl is-active stacklabs-sdlc.service

echo "================================================================="
echo "🎉 [STACKLABS] FHS & SDLC Cutover Completed Successfully!"
echo "================================================================="
