#!/usr/bin/env python3
import os
import sys
import shutil
from PIL import Image
from PIL.PngImagePlugin import PngInfo

SOURCE_DIR = "/home/james/sovereign_inbox/pilot_drops/Gonzas/avatar_sheets"
DEST_BASE = "/home/james/stacklabs/17_GonzasCantina/public/avatars"

CHARACTERS = {
    "Senora_Caos": {
        "handle": "señora_caos",
        "prompt": "A professional character reference model sheet of Señora Caos, an unhinged, highly expressive 65-year-old cartoon grandmother with curly grey hair in a messy bun, wearing a colorful floral apron over a traditional dress. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (sad, screaming in anger, laughing maniacally); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing an accusatory finger forward in rage and shrugging shoulders in complete exasperation. Flat 2D vector style, clean sharp lines, thick felt cartoon outlines, vibrant highly saturated magenta and yellow team colors, premium masterpiece quality character design."
    },
    "Mateo_the_rabbit": {
        "handle": "just_askingquestions",
        "prompt": "A professional character reference model sheet of Mateo the rabbit, a scruffy, grease-painted cartoon rabbit wearing a grease-stained apron, clutching a giant plastic convenience cup. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (smug grin, shocked wide-eyed panic, slurring speech); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a furry finger forward and shrugging shoulders in total disbelief. Flat 2D vector style, clean sharp lines, thick felt cartoon outlines, vibrant highly saturated neon blue and toxic green colors, premium masterpiece quality character design."
    },
    "Static_Shock": {
        "handle": "static_shock",
        "prompt": "A professional character reference model sheet of Static Shock, an eccentric cartoon repair technician with wild, static-charged hair, wearing thick safety goggles and an orange utility vest covered in wires. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (focusing intensely, screaming in electrical shock, wild grinning); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a screwdriver forward and shrugging shoulders with sparks flying. Flat 2D vector style, clean sharp lines, thick felt cartoon outlines, vibrant highly saturated electric cyan and hazard yellow colors, premium masterpiece quality character design."
    },
    "Cryptic_Courier": {
        "handle": "cryptic_courier",
        "prompt": "A professional character reference model sheet of the Cryptic Courier, a scruffy cartoon raccoon courier wearing a faded neon delivery messenger bag, a dark hood, and a retro lanyard. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (shifty paranoid eyes, panting from running, smug smirk); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a gloved paw forward and shrugging shoulders with a cardboard box. Flat 2D vector style, clean sharp lines, thick felt cartoon outlines, vibrant highly saturated midnight violet and neon pink colors, premium masterpiece quality character design."
    },
    "Greasy_Ghost": {
        "handle": "greasy_ghost",
        "prompt": "A professional character reference model sheet of the Greasy Ghost, a floating, cartoon ghost caricature wearing a dirty paper chef hat, dripping with translucent yellow grease droplets. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (groaning in fryer-burn, laughing eerily, looking disgusted at fresh oil); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a misty finger forward and shrugging shoulders in ghostly exasperation. Flat 2D vector style, clean sharp lines, thick felt cartoon outlines, vibrant highly saturated slime green and greasy yellow colors, premium masterpiece quality character design."
    },
    "Organic_Austin": {
        "handle": "organic_austin",
        "prompt": "A professional character reference model sheet of Organic Austin, a hyper-cynical, condescending cartoon gentrification activist with high-end designer glasses, a tight unbleached canvas linen shirt, and a look of supreme judgment. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (scowling in disgust, looking incredibly smug, squinting at a roller dog); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a finger in condemnation and shrugging shoulders in dismissive corporate superiority. Flat 2D vector style, clean sharp lines, thick minimalist outlines, desaturated organic kale green and flat copper colors, premium masterpiece quality character design."
    }
}

CROPS = {
    "_avatar.png": (0, 0, 341, 341),
    "_pointing.png": (0, 682, 341, 1024),
    "_shrug.png": (341, 682, 682, 1024)
}

COPY_DESTINATIONS = [
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
    "/home/james/stacklabs/15_FanStack/public/avatars",
    "/home/james/stacklabs/20_AetherVet/public/avatars",
    "/home/james/stacklabs/21_Wildseed_GardenStack/public/avatars",
    "/home/james/stacklabs/dna/media/avatars",
    "/home/james/stacklabs-uat/21_Wildseed_GardenStack/public/avatars",
    "/home/james/stacklabs-uat/15_FanStack/public/avatars",
    "/home/james/stacklabs-uat/dna/media/avatars",
    "/home/james/stacklabs-uat/20_AetherVet/public/avatars",
    "/home/james/stacklabs-uat/01_Sovereign_Portal/public/avatars"
]

def main():
    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    files = os.listdir(SOURCE_DIR)
    print(f"Found files in source: {files}")

    for file_name in files:
        if not file_name.lower().endswith(('.jpeg', '.jpg', '.png')):
            continue

        # Find which character this file corresponds to
        char_key = None
        for key in CHARACTERS.keys():
            if key in file_name:
                char_key = key
                break

        if not char_key:
            print(f"Skipping {file_name} (no matching character mapping)")
            continue

        char_info = CHARACTERS[char_key]
        handle = char_info["handle"]
        prompt = char_info["prompt"]

        print(f"\nProcessing {file_name} -> handle: {handle}")
        src_path = os.path.join(SOURCE_DIR, file_name)

        # Open image
        try:
            img = Image.open(src_path)
            # Ensure it is resized or operates on 1024x1024 for correct coordinates if not already
            if img.size != (1024, 1024):
                print(f"Warning: image size is {img.size}, resizing to 1024x1024 for consistent cropping")
                img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Failed to open/resize {src_path}: {e}")
            continue

        # Target directory in 17_GonzasCantina
        target_dir = os.path.join(DEST_BASE, handle)
        os.makedirs(target_dir, exist_ok=True)

        for suffix, bbox in CROPS.items():
            out_filename = f"{handle}{suffix}"
            out_path = os.path.join(target_dir, out_filename)

            # Crop
            cropped = img.crop(bbox)

            # Set metadata
            meta = PngInfo()
            meta.add_text("Description", prompt)

            # Save
            try:
                cropped.save(out_path, "PNG", pnginfo=meta)
                print(f"  Saved: {out_path}")
            except Exception as e:
                print(f"  Failed to save {out_path}: {e}")
                continue

            # Copy to other destinations
            for dest_base in COPY_DESTINATIONS:
                dest_dir = os.path.join(dest_base, handle)
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, out_filename)
                try:
                    shutil.copy2(out_path, dest_path)
                except Exception as e:
                    # Some UAT dirs or other folders might not exist, that's fine, warn but keep going
                    pass

    print("\nProcessing complete!")

if __name__ == "__main__":
    main()
