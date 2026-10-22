#!/usr/bin/env python3
import os

files_to_update = [
    "/home/james/stacklabs/21_Wildseed_GardenStack/vite.config.ts",
    "/home/james/stacklabs/24_CardTurpey/vite.config.ts",
    "/home/james/stacklabs/01_Sovereign_Portal/src/config/PortalApps.tsx",
    "/home/james/stacklabs/scripts/restart_servers.sh",
    "/home/james/stacklabs/scripts/headed_playwright_tv_showcase.py",
    "/home/james/stacklabs/24_CardTurpey/src/GlobalSystemBar.tsx",
    "/home/james/stacklabs/23_InkwellIrony/src/GlobalSystemBar.tsx",
    "/home/james/stacklabs/21_Wildseed_GardenStack/src/GlobalSystemBar.tsx",
    "/home/james/stacklabs/15_FanStack/src/components/GlobalSystemBar.tsx",
    "/home/james/stacklabs/01_Sovereign_Portal/src/components/GlobalSystemBar.tsx",
    "/home/james/stacklabs/22_SpiteSlice/src/GlobalSystemBar.tsx"
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} - file does not exist")
        continue

    with open(filepath, "r") as f:
        content = f.read()

    original = content
    
    # Let's perform the swaps based on what each file contains!
    if "vite.config.ts" in filepath:
        if "21_Wildseed" in filepath:
            # Change 3016 to 3017
            content = content.replace("port: 3016", "port: 3017")
        elif "24_CardTurpey" in filepath:
            # Change 3017 to 3016
            content = content.replace("port: 3017", "port: 3016")

    elif "PortalApps.tsx" in filepath:
        # Swap gardenstack port from 3016 to 3017
        content = content.replace(":3016/", ":3017/")

    elif "restart_servers.sh" in filepath:
        # Swap ports inside start lines
        # Wildseed: port 3016 -> 3017
        content = content.replace("Starting 21_Wildseed_GardenStack on port 3016...", "Starting 21_Wildseed_GardenStack on port 3017...")
        content = content.replace("npm run dev -- --force --port 3016", "npm run dev -- --force --port 3017")
        
        # CardTurpey: port 3017 -> 3016
        content = content.replace("Starting 24_CardTurpey on port 3017...", "Starting 24_CardTurpey on port 3016...")
        content = content.replace("npm run dev -- --force --port 3017", "npm run dev -- --force --port 3016")

    elif "headed_playwright_tv_showcase.py" in filepath:
        # CardTurpey: port 3017 -> 3016
        content = content.replace("Port 3017", "Port 3016")
        content = content.replace("localhost:3017", "localhost:3016")

    elif "GlobalSystemBar.tsx" in filepath:
        # Swap redirect targets for gardenstack (3016 -> 3017) and cardturpey (3017 -> 3016)
        # We must do this carefully using a placeholder to avoid double replacement!
        
        # 1. Gardenstack
        content = content.replace("currentPort === '3016'", "currentPort === '3017_TEMP'")
        content = content.replace(":3016/", ":3017_TEMP/")
        
        # 2. Cardturpey
        content = content.replace("currentPort === '3017'", "currentPort === '3016'")
        content = content.replace(":3017/", ":3016/")
        
        # 3. Resolve placeholder
        content = content.replace("currentPort === '3017_TEMP'", "currentPort === '3017'")
        content = content.replace(":3017_TEMP/", ":3017/")

        # Also swap the focus/dev checks
        content = content.replace("window.location.port !== '3016'", "window.location.port !== '3017_TEMP'")
        content = content.replace("window.location.port !== '3017'", "window.location.port !== '3016'")
        content = content.replace("window.location.port !== '3017_TEMP'", "window.location.port !== '3017'")

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"✅ Swapped ports in {filepath}")
    else:
        print(f"ℹ️ No changes made in {filepath}")
