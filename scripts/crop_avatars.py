from PIL import Image
import os
import glob

source_dir = "/home/james/stacklabs/media_vault/03_Assets/Personas"
dest_dir = "/home/james/stacklabs/01_Sovereign_Portal/public/avatars"

os.makedirs(dest_dir, exist_ok=True)

for persona_dir in glob.glob(os.path.join(source_dir, "*")):
    if os.path.isdir(persona_dir):
        persona_name = os.path.basename(persona_dir)
        map_path = os.path.join(persona_dir, "character_map.png")
        if os.path.exists(map_path):
            try:
                img = Image.open(map_path)
                width, height = img.size
                
                # Crop top-left quadrant (usually Front View)
                left = 0
                top = 0
                right = width // 2
                bottom = height // 2
                
                cropped = img.crop((left, top, right, bottom))
                
                # Further crop to a center square of the top-left quadrant
                cw, ch = cropped.size
                min_dim = min(cw, ch)
                cl = (cw - min_dim) // 2
                ct = (ch - min_dim) // 2
                cr = cl + min_dim
                cb = ct + min_dim
                
                final_avatar = cropped.crop((cl, ct, cr, cb))
                
                dest_path = os.path.join(dest_dir, f"{persona_name}.png")
                final_avatar.save(dest_path)
                print(f"Generated avatar for {persona_name}")
            except Exception as e:
                print(f"Failed to process {persona_name}: {e}")

