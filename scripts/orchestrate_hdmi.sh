#!/bin/bash
# Sovereign OS HDMI Orchestrator for Node .114
# Pushes the Sovereign OS splash screen to the node and displays it via the framebuffer.

TARGET="james@100.88.5.122"
IMAGE_SRC="/home/james/.gemini/antigravity/brain/5b95468e-6c4d-417b-abce-b41ca20145d5/sovereign_splash_1777332628788.png"
IMAGE_DEST="/tmp/sovereign_splash.png"

echo "[*] Connecting to Hobbes via Tailscale ($TARGET)..."
echo "[*] Pushing Tactical UI Splash Screen..."

# Push the image
scp -q "$IMAGE_SRC" "$TARGET:$IMAGE_DEST"
if [ $? -ne 0 ]; then
    echo "[!] Failed to transfer image to $TARGET."
    exit 1
fi

echo "[*] Triggering Framebuffer Injection on TV..."
ssh -q "$TARGET" "sudo apt-get install -y fbi > /dev/null 2>&1 && sudo killall fbi > /dev/null 2>&1 || true && sudo fbi -d /dev/fb0 -T 1 -noverbose -a $IMAGE_DEST"

echo "[+] Done! The TV should now display the Sovereign OS Tactical Interface."
