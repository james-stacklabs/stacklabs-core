#!/usr/bin/env bash
# ==============================================================================
# Sovereign OS: Pegasus Ubuntu Desktop Provisioning & Configuration Script
# Node: pegasus (x86_64 / GTX 980 Maxwell / Dual-Boot Windows + Ubuntu)
# ==============================================================================

set -euo pipefail

# Visual formatting
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[PEGASUS-SETUP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Require root/sudo
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root or with sudo:"
   echo "  sudo bash $0"
   exit 1
fi

TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo "james")}"

log_info "=========================================================="
log_info " Sovereign OS: Pegasus Desktop Environment Initializer"
log_info " Target User: ${TARGET_USER}"
log_info " Kernel: $(uname -r) | Hostname: $(hostname)"
log_info "=========================================================="

# -----------------------------------------------------------------------------
# 1. Update Package Sources & Upgrade Base System
# -----------------------------------------------------------------------------
log_info "[1/7] Updating apt repositories and package lists..."
apt-get update -y

# -----------------------------------------------------------------------------
# 2. Install Desktop Environment & Display Manager
# -----------------------------------------------------------------------------
log_info "[2/7] Installing Ubuntu Desktop Environment & GDM3..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ubuntu-desktop-minimal \
    gdm3 \
    gnome-terminal \
    gnome-shell-extensions \
    gnome-tweaks \
    dbus-x11 \
    x11-xserver-utils \
    xorg \
    mesa-utils

# Set default boot target to graphical UI
log_info "Enabling graphical.target as systemd default boot mode..."
systemctl set-default graphical.target
systemctl enable gdm3 || systemctl enable gdm

# -----------------------------------------------------------------------------
# 3. Detect & Install NVIDIA Drivers for GTX 980 (Maxwell GM204)
# -----------------------------------------------------------------------------
log_info "[3/7] Inspecting GPU hardware & configuring NVIDIA proprietary drivers..."
if lspci | grep -i -E "vga|3d|display" | grep -i "nvidia" > /dev/null 2>&1; then
    log_info "NVIDIA GPU Detected: $(lspci | grep -i -E "vga|3d|display" | grep -i "nvidia" | cut -d: -f3)"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y ubuntu-drivers-common
    
    # Auto-detect and install recommended NVIDIA driver (e.g. nvidia-driver-535 or 470)
    log_info "Installing recommended NVIDIA driver via ubuntu-drivers..."
    ubuntu-drivers install || apt-get install -y nvidia-driver-535
    
    # Configure GDM for NVIDIA stability (X11 is recommended for Maxwell architecture)
    if [ -f /etc/gdm3/custom.conf ]; then
        log_info "Configuring /etc/gdm3/custom.conf (X11 fallback enabled for NVIDIA stability)..."
        sed -i 's/^#\?WaylandEnable=.*/WaylandEnable=false/' /etc/gdm3/custom.conf
    fi
else
    log_warn "No discrete NVIDIA GPU detected via lspci. Skipping proprietary driver install."
fi

# -----------------------------------------------------------------------------
# 4. Preserve Dual-Boot GRUB Configuration (Windows Detection)
# -----------------------------------------------------------------------------
log_info "[4/7] Verifying GRUB configuration & OS-Prober for Windows Dual-Boot..."
DEBIAN_FRONTEND=noninteractive apt-get install -y os-prober

if [ -f /etc/default/grub ]; then
    if grep -q "GRUB_DISABLE_OS_PROBER" /etc/default/grub; then
        sed -i 's/^#\?GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
    else
        echo "GRUB_DISABLE_OS_PROBER=false" >> /etc/default/grub
    fi
    log_info "Updating GRUB bootloader to detect Windows partition..."
    update-grub
fi

# -----------------------------------------------------------------------------
# 5. Remote Access (RDP & Tailscale Mesh)
# -----------------------------------------------------------------------------
log_info "[5/7] Configuring Remote Access (XRDP & Tailscale)..."

# Install XRDP for easy remote desktop from Windows / Artemis
DEBIAN_FRONTEND=noninteractive apt-get install -y xrdp gnome-remote-desktop
adduser xrdp ssl-cert || true
systemctl enable xrdp
systemctl restart xrdp

# Ensure Tailscale is installed on Linux
if ! command -v tailscale &> /dev/null; then
    log_info "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    systemctl enable --now tailscaled
else
    log_info "Tailscale is already installed."
fi

# -----------------------------------------------------------------------------
# 6. Essential Desktop Workstation Utilities
# -----------------------------------------------------------------------------
log_info "[6/7] Installing standard developer & desktop utilities..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    htop \
    nvtop \
    ffmpeg \
    vlc \
    pipewire \
    wireplumber \
    network-manager-gnome \
    pulseaudio-utils

# Prevent unintended system suspend when running background compute tasks
log_info "Configuring systemd to prevent sleep during background daemon execution..."
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target || true

# -----------------------------------------------------------------------------
# 7. Summary & Next Steps
# -----------------------------------------------------------------------------
log_info "[7/7] Finalizing configuration..."

echo ""
log_success "=========================================================="
log_success " Pegasus Ubuntu Desktop Installation Complete!"
log_success "=========================================================="
echo ""
echo "Summary of actions performed:"
echo " 1. Installed Ubuntu Desktop (GNOME minimal) + GDM3 Display Manager."
echo " 2. Configured systemd default target to 'graphical.target'."
echo " 3. Installed NVIDIA proprietary drivers for GTX 980 + X11 fallback."
echo " 4. Enabled 'os-prober' in GRUB to preserve Windows dual-boot menu."
echo " 5. Installed XRDP for Remote Desktop access (port 3389)."
echo " 6. Configured Tailscale & developer utilities (nvtop, htop, ffmpeg)."
echo ""
echo "Next Steps:"
echo "  1. If Tailscale is not authenticated on this Linux instance, run:"
echo "     sudo tailscale up --hostname=pegasus-ubuntu --accept-routes"
echo "  2. Reboot the system to initialize the NVIDIA kernel modules & launch the GUI:"
echo "     sudo reboot"
echo ""
