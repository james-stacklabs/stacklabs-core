#!/usr/bin/env python3
import os
import sys
import base64
import sqlite3
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
EXTRACTED_DIR = "/home/james/sovereign_inbox/StackLabs_LLC/extracted_sheets"

# Mapping between advocate handle and filename substring
MAPPING = {
    "sysop_barker": "Grizzled_technician_blueprints",
    "barf_prime": "Barf_prime_character_reference",
    "mando_enforcer": "Mando_Droid_sentinel",
    "six_dinner_inventor": "Invento_Technician_assembling",
    "trop": "Baseball_data_analyst",
    "abner_aether_craft": "Pilot_Silver_fox_engineer",
    "bro_decode": "bro_decode_character_reference_sheet",
    "isolated_silo": "isolated_silo_character_reference_sheet"
}

COORDS = {
    "avatar": (0, 0, 341, 341),
    "pointing": (0, 682, 341, 1024),
    "shrug": (341, 682, 682, 1024)
}

def get_matching_file(pattern):
    for f in os.listdir(EXTRACTED_DIR):
        if pattern in f:
            return os.path.join(EXTRACTED_DIR, f)
    return None

def main():
    print("✂️ Starting StackLabs Avatar Cropping Campaign...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    for handle, pattern in MAPPING.items():
        src_path = get_matching_file(pattern)
        if not src_path:
            print(f"❌ Error: Could not find sheet matching '{pattern}' for handle @{handle}")
            continue
            
        print(f"🧬 Processing @{handle} using source: {os.path.basename(src_path)}")
        try:
            img = Image.open(src_path)
            w, h = img.size
            if w != 1024 or h != 1024:
                print(f"⚠️ Warning: Image dimensions {w}x{h} for @{handle} are not 1024x1024!")
        except Exception as e:
            print(f"❌ Failed to load image {src_path}: {e}")
            continue
            
        # Target directories
        target_dirs = [
            f"/home/james/stacklabs/15_FanStack/public/avatars/{handle}",
            f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{handle}",
            f"/home/james/stacklabs/20_AetherVet/public/avatars/{handle}",
            f"/home/james/stacklabs/21_Wildseed_GardenStack/public/avatars/{handle}",
            f"/home/james/stacklabs-uat/01_Sovereign_Portal/public/avatars/{handle}",
            f"/home/james/stacklabs-uat/20_AetherVet/public/avatars/{handle}"
        ]
        
        avatar_blob = None
        
        for pose, box in COORDS.items():
            try:
                cropped = img.crop(box)
                cropped = cropped.resize((512, 512), Image.Resampling.LANCZOS)
                
                # Copy to all target directories
                for t_dir in target_dirs:
                    os.makedirs(t_dir, exist_ok=True)
                    
                    # Remove stale SVGs to prevent browser layout issues
                    stale_svg = os.path.join(t_dir, f"{handle}_{pose}.svg")
                    if os.path.exists(stale_svg):
                        os.remove(stale_svg)
                        
                    # Save both file patterns (with and without handle prefix)
                    cropped.save(os.path.join(t_dir, f"{pose.png if '.' in pose else pose + '.png'}"), "PNG")
                    cropped.save(os.path.join(t_dir, f"{handle}_{pose}.png"), "PNG")
                
                # Base64 encode the default avatar pose for database storage
                if pose == "avatar":
                    import io
                    buffer = io.BytesIO()
                    cropped.save(buffer, format="PNG")
                    encoded_blob = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    avatar_blob = f"data:image/png;base64,{encoded_blob}"
                    
            except Exception as e:
                print(f"  ❌ Error cropping pose '{pose}' for @{handle}: {e}")
                
        # Database updates
        rel_avatar_url = f"/avatars/{handle}/{handle}_avatar.png"
        try:
            # 1. persona table
            cur.execute("""
                UPDATE persona 
                SET avatar_url = ?, avatar_blob = ? 
                WHERE user_name = ?
            """, (rel_avatar_url, avatar_blob, handle))
            
            # 2. sys_user table
            cur.execute("""
                UPDATE sys_user 
                SET avatar_url = ? 
                WHERE user_name = ?
            """, (rel_avatar_url, handle))
            
            print(f"  ✅ Database records and Base64 blobs committed for @{handle}.")
        except Exception as dbe:
            print(f"  ❌ Database update failed for @{handle}: {dbe}")
            
    conn.commit()
    conn.close()
    print("🎉 Avatar Cropping Campaign Complete!")

if __name__ == "__main__":
    main()
