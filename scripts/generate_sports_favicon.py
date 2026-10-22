#!/home/james/stacklabs/.venv/bin/python3
import os
from PIL import Image, ImageDraw

def main():
    # Create a 32x32 image with transparent background
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer Ring (Mets Blue)
    draw.ellipse([2, 2, 29, 29], fill=None, outline='#002D62', width=3)
    
    # Inner Ring (Scoreboard Orange)
    draw.ellipse([6, 6, 25, 25], fill=None, outline='#FC5C1D', width=2)
    
    # Center core dot
    draw.ellipse([12, 12, 19, 19], fill='#FC5C1D', outline=None)
    
    # Ensure directory exists
    target_dir = '/home/james/stacklabs/19_Sovereign_Sports/public'
    os.makedirs(target_dir, exist_ok=True)
    
    # Save as favicon.ico
    target_path = os.path.join(target_dir, 'favicon.ico')
    img.save(target_path, format='ICO')
    print(f"[+] Favicon generated successfully at: {target_path}")

if __name__ == '__main__':
    main()
