#!/usr/bin/env python3
import os
import sys
import random
import argparse
from PIL import Image, ImageDraw

def apply_rustic_frame(input_path, output_path, border_width=40):
    """
    Applies a programmatically generated rustic weathered wood grain frame border
    around the input canvas image.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} does not exist.")
        sys.exit(1)
        
    img = Image.open(input_path)
    width, height = img.size
    
    # 1. Create outer canvas to hold the original image + border
    new_w = width + 2 * border_width
    new_h = height + 2 * border_width
    
    # Base weathered wood grain color (Warm brown / slate-ish undertone)
    base_color = (139, 90, 60, 255) # Rustic brown
    framed_img = Image.new("RGBA", (new_w, new_h), base_color)
    draw = ImageDraw.Draw(framed_img)
    
    # 2. Draw wood grain texture lines procedurally
    random.seed(42 + border_width) # Stable seed for reproducible frames
    
    # We draw horizontal grain for top & bottom borders, vertical grain for side borders
    # Top & Bottom Wood grain lines
    for _ in range(120):
        # horizontal top lines
        y_top = random.randint(0, border_width)
        color_offset = random.randint(-25, 25)
        line_color = (base_color[0] + color_offset, base_color[1] + color_offset - 10, base_color[2] + color_offset - 15, 255)
        draw.line([(0, y_top), (new_w, y_top)], fill=line_color, width=random.randint(1, 2))
        
        # horizontal bottom lines
        y_bottom = random.randint(new_h - border_width, new_h)
        draw.line([(0, y_bottom), (new_w, y_bottom)], fill=line_color, width=random.randint(1, 2))
        
    # Left & Right Wood grain lines
    for _ in range(120):
        # vertical left lines
        x_left = random.randint(0, border_width)
        color_offset = random.randint(-25, 25)
        line_color = (base_color[0] + color_offset, base_color[1] + color_offset - 10, base_color[2] + color_offset - 15, 255)
        draw.line([(x_left, 0), (x_left, new_h)], fill=line_color, width=random.randint(1, 2))
        
        # vertical right lines
        x_right = random.randint(new_w - border_width, new_w)
        draw.line([(x_right, 0), (x_right, new_h)], fill=line_color, width=random.randint(1, 2))

    # 3. Add rustic joinery details: 45-degree corner seams
    joinery_color = (75, 45, 30, 255)
    draw.line([(0, 0), (border_width, border_width)], fill=joinery_color, width=2)
    draw.line([(new_w, 0), (new_w - border_width, border_width)], fill=joinery_color, width=2)
    draw.line([(0, new_h), (border_width, new_h - border_width)], fill=joinery_color, width=2)
    draw.line([(new_w, new_h), (new_w - border_width, new_h - border_width)], fill=joinery_color, width=2)

    # 4. Draw inner weathered shadow/bevel inside the frame
    draw.rectangle([border_width - 3, border_width - 3, new_w - border_width + 2, new_h - border_width + 2], outline=(60, 40, 30, 255), width=3)
    
    # 5. Paste original image in center
    # Convert original to RGBA to preserve any transparency correctly
    img_rgba = img.convert("RGBA")
    framed_img.paste(img_rgba, (border_width, border_width), img_rgba)
    
    # 6. Save as target image
    # We save as PNG or JPEG depending on request, default back to format from target path extension
    ext = os.path.splitext(output_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        framed_img.convert("RGB").save(output_path, "JPEG", quality=90)
    else:
        framed_img.save(output_path, "PNG")
        
    print(f"Programmatically applied rustic frame: {input_path} -> {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Programmatically apply weathered wood frames to canvases.")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("output", help="Path to save framed image")
    parser.add_argument("--border", type=int, default=40, help="Border width in pixels (default: 40)")
    
    args = parser.parse_args()
    apply_rustic_frame(args.input, args.output, args.border)
