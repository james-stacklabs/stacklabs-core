#!/usr/bin/env python3
import os
import sys
import shutil
from PIL import Image
from PIL.PngImagePlugin import PngInfo

SOURCE_DIR = "/home/james/sovereign_inbox/pilot_drops/SpiteSlice/avatar_sheets"
DEST_BASE = "/home/james/stacklabs/22_SpiteSlice/public/avatars"

CHARACTERS = {
    "blistering_becky": {
        "handle": "blistering_becky",
        "prompt": "A professional character reference model sheet of Blistering Becky, an authoritative, sharp-eyed 45-year-old cartoon kitchen supervisor wearing a flour-dusted dark denim apron, holding a laser thermometer over her chest. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (glaring in quality audit, laughing mockingly, looking deeply unimpressed); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a wooden pizza peel forward in rage, slicing a crust with a heavy rocker-blade, and shrugging in exasperation. Gritty woodcut illustration style, raw ink textures, high-contrast shadows, bold neon-crimson border highlights on the figure, premium masterpiece character design."
    },
    "spiteful_sal": {
        "handle": "spiteful_sal",
        "prompt": "A professional character reference model sheet of Spiteful Sal, a grizzled, highly animated 65-year-old cartoon pizzaiolo with wild grey hair, wearing a white sleeveless undershirt and a flour-dusted red apron. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (screaming in entrepreneurial spite, smirking behind binoculars, laughing maniacally at a competitor's crash); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a finger in condemnation, tossing a raw pizza dough sheet overhead, and shrugging shoulders in total dismissive spite. Gritty woodcut illustration style, raw ink textures, high-contrast shadows, bold neon-crimson border highlights on the figure, premium masterpiece character design."
    },
    "delivery_dan": {
        "handle": "delivery_dan",
        "prompt": "A professional character reference model sheet of Delivery Dan, a hyperactive, condescending corporate tech executive with frameless designer glasses, wearing a sleek black technical fleece vest over a desaturated corporate blue dress shirt, clutching a glowing white data tablet. The image must be arranged in a perfectly balanced 3x3 grid layout containing exactly 9 clean, standalone 1:1 profile square blocks on an absolute solid black background, with zero text overlays, zero labels, and zero detail circles. Explicit views layout: top row contains three standalone frontal portrait headshots with different intense expressions (scowling at a physical cash register, looking incredibly smug, squinting at a brick oven); middle row contains three clean side profile views looking left and right; bottom row contains three expressive action poses including pointing a finger in commission-fee condemnation, holding up a digital terms-of-service agreement, and shrugging shoulders in corporate superiority. Gritty woodcut illustration style, desaturated slate blue and cold corporate white accents, raw ink textures, sharp clean lines, premium character design."
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

        # Target directory in 22_SpiteSlice
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
