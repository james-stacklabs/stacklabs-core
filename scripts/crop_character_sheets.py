#!/usr/bin/env python3
import sys
import os
from PIL import Image

def crop_sheet(image_path, output_dir, handle):
    if not os.path.exists(image_path):
        print(f"Error: {image_path} does not exist.")
        return False
        
    img = Image.open(image_path)
    width, height = img.size
    print(f"Processing {image_path} ({width}x{height}) for handle '{handle}'")
    
    # Custom coordinates based on projection profile analysis of the generated images
    if handle == "shea_vintage":
        # Shea dividers: X: 359, 657; Y: 427, 742
        avatar = img.crop((0, 0, 359, 427))
        pointing = img.crop((657, 0, 1024, 427))
        shrug = img.crop((657, 742, 1024, 1024))
    elif handle == "bucky_dent_blues":
        # Bucky dividers: X: 351, 667; Y: 508, 807
        avatar = img.crop((0, 0, 351, 508))
        pointing = img.crop((667, 0, 1024, 508))
        shrug = img.crop((667, 807, 1024, 1024))
    else:
        # Default fallback: mathematical division
        cell_w = width // 3
        cell_h = height // 3
        avatar = img.crop((0, 0, cell_w, cell_h))
        pointing = img.crop((cell_w * 2, 0, width, cell_h))
        shrug = img.crop((cell_w * 2, cell_h * 2, width, height))
    
    os.makedirs(output_dir, exist_ok=True)
    
    avatar.save(os.path.join(output_dir, f"{handle}_avatar.png"))
    pointing.save(os.path.join(output_dir, f"{handle}_pointing.png"))
    shrug.save(os.path.join(output_dir, f"{handle}_shrug.png"))
    
    print(f"Successfully cropped poses for {handle} in {output_dir}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 crop_character_sheets.py <IMAGE_PATH> <OUTPUT_DIR> <HANDLE>")
        sys.exit(1)
        
    crop_sheet(sys.argv[1], sys.argv[2], sys.argv[3])
