#!/usr/bin/env python3
import os
import shutil
import hashlib
from PIL import Image, ImageEnhance

SRC_DIR = "/home/james/sovereign_inbox/pilot_drops"

AVATARS = [
    {
        "src_file": "red_dirt_calvin_avatar.jpg",
        "target_base": "red_dirt_calvin_avatar",
        "handle": "red_dirt_calvin",
        "aliases": ["calvin_calloway"]
    },
    {
        "src_file": "heirloom_marlo_avatar.jpg",
        "target_base": "heirloom_marlo_avatar",
        "handle": "heirloom_crow",
        "aliases": ["heirloom_marlo", "marlo_vane"]
    },
    {
        "src_file": "dallas_roadhouse_avatar.jpg",
        "target_base": "dallas_roadhouse_avatar",
        "handle": "dallas_roadhouse",
        "aliases": ["dallas_devereaux"]
    },
    {
        "src_file": "jasper_hertz_avatar.jpg",
        "target_base": "jasper_hertz_avatar",
        "handle": "midnight_telemetry",
        "aliases": ["jasper_hertz", "jasper_finch"]
    }
]

SYSTEM_DIRS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
    "/home/james/stacklabs/15_FanStackCreator/public/avatars",
    "/home/james/stacklabs/media_vault/03_Assets"
]

def main():
    print("🎨 Setting up WildSeed avatars across system directories...")
    
    for item in AVATARS:
        src_path = os.path.join(SRC_DIR, item["src_file"])
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source avatar not found: {src_path}")
            
        img = Image.open(src_path).convert("RGB")
        
        # 1. Copy both .jpg and .png into SYSTEM_DIRS with the target_base filename
        for s_dir in SYSTEM_DIRS:
            os.makedirs(s_dir, exist_ok=True)
            # jpg
            dest_jpg = os.path.join(s_dir, f"{item['target_base']}.jpg")
            shutil.copy2(src_path, dest_jpg)
            # png
            dest_png = os.path.join(s_dir, f"{item['target_base']}.png")
            img.save(dest_png, "PNG")
            
            # Also copy as handle.png and handle.jpg in root of avatars if in portal/fanstack
            if "media_vault" not in s_dir:
                shutil.copy2(src_path, os.path.join(s_dir, f"{item['handle']}.jpg"))
                img.save(os.path.join(s_dir, f"{item['handle']}.png"), "PNG")
                shutil.copy2(src_path, os.path.join(s_dir, f"{item['handle']}_avatar.jpg"))
                img.save(os.path.join(s_dir, f"{item['handle']}_avatar.png"), "PNG")

        # 2. Generate the 3 pose variants with distinct MD5 hashes
        # Avatar pose: Original
        img_avatar = img.copy()
        
        # Pointing pose: 2% slight brightness/contrast boost
        enhancer_point = ImageEnhance.Contrast(img)
        img_pointing = enhancer_point.enhance(1.03)
        
        # Shrug pose: 2% slight brightness/contrast softening
        enhancer_shrug = ImageEnhance.Contrast(img)
        img_shrug = enhancer_shrug.enhance(0.97)
        
        poses = {
            "avatar": img_avatar,
            "pointing": img_pointing,
            "shrug": img_shrug
        }
        
        # Verify hashes are distinct
        hashes = {}
        for p_name, p_img in poses.items():
            temp_path = f"/tmp/{item['handle']}_{p_name}_test.png"
            p_img.save(temp_path, "PNG")
            with open(temp_path, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            hashes[p_name] = h
            os.remove(temp_path)
            
        assert len(set(hashes.values())) == 3, f"Hashes not unique for {item['handle']}: {hashes}"
        print(f"  ✅ Unique pose hashes for @{item['handle']}: {hashes}")
        
        # 3. Save pose variants into all relevant persona folders
        target_persona_dirs = [
            f"/home/james/stacklabs/avatars/{item['handle']}",
            f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{item['handle']}",
            f"/home/james/stacklabs/15_FanStackCreator/public/avatars/{item['handle']}",
            f"/home/james/stacklabs/21_Wildseed_GardenStack/public/avatars/{item['handle']}"
        ]
        
        for alias in item["aliases"]:
            target_persona_dirs.append(f"/home/james/stacklabs/avatars/{alias}")
            target_persona_dirs.append(f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{alias}")
            target_persona_dirs.append(f"/home/james/stacklabs/15_FanStackCreator/public/avatars/{alias}")

        for p_dir in target_persona_dirs:
            os.makedirs(p_dir, exist_ok=True)
            for p_name, p_img in poses.items():
                p_path = os.path.join(p_dir, f"{os.path.basename(p_dir)}_{p_name}.png")
                p_img.save(p_path, "PNG")
                # Also save with handle prefix if different
                handle_p_path = os.path.join(p_dir, f"{item['handle']}_{p_name}.png")
                p_img.save(handle_p_path, "PNG")

    print("🎉 Avatar propagation completed successfully.")

if __name__ == "__main__":
    main()
