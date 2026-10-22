import os
import argparse
import math
import sqlite3
import base64
import io
import glob
import hashlib
from PIL import Image, ImageDraw, ImageFont

# Color Palette
BG_COLOR = (10, 15, 20, 255)
GRID_COLOR = (15, 30, 25, 255)
NEON_GREEN = (0, 255, 128, 255)
NEON_BLUE = (0, 192, 255, 255)
TEXT_COLOR = (240, 248, 255, 255)
TEXT_MUTED = (120, 140, 150, 255)
BORDER_COLOR = (0, 128, 64, 255)

FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

def draw_arrow(draw, start, end, color, width=3, arrowhead_length=15):
    # Draw main line
    draw.line([start, end], fill=color, width=width)
    
    # Calculate angle of line
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    
    # Arrow head points
    p1 = (end[0] - arrowhead_length * math.cos(angle - math.pi/6),
          end[1] - arrowhead_length * math.sin(angle - math.pi/6))
    p2 = (end[0] - arrowhead_length * math.cos(angle + math.pi/6),
          end[1] - arrowhead_length * math.sin(angle + math.pi/6))
    
    draw.polygon([end, p1, p2], fill=color)

def generate_whiff_graphic(args):
    # Create image
    img = Image.new("RGBA", (800, 800), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_large = ImageFont.truetype(FONT_BOLD, 28)
        font_med = ImageFont.truetype(FONT_BOLD, 18)
        font_small = ImageFont.truetype(FONT_SANS, 14)
        font_header = ImageFont.truetype(FONT_BOLD, 14)
    except IOError:
        font_large = font_med = font_small = font_header = ImageFont.load_default()

    # Draw grid lines
    grid_spacing = 40
    for x in range(0, 800, grid_spacing):
        draw.line([(x, 0), (x, 800)], fill=GRID_COLOR, width=1)
    for y in range(0, 800, grid_spacing):
        draw.line([(0, y), (800, y)], fill=GRID_COLOR, width=1)
        
    # Draw outer frame border
    draw.rectangle([(10, 10), (790, 790)], outline=BORDER_COLOR, width=2)
    # Corner brackets
    bracket_len = 30
    # Top Left
    draw.line([(10, 10), (10 + bracket_len, 10)], fill=NEON_GREEN, width=4)
    draw.line([(10, 10), (10, 10 + bracket_len)], fill=NEON_GREEN, width=4)
    # Top Right
    draw.line([(790, 10), (790 - bracket_len, 10)], fill=NEON_GREEN, width=4)
    draw.line([(790, 10), (790, 10 + bracket_len)], fill=NEON_GREEN, width=4)
    # Bottom Left
    draw.line([(10, 790), (10 + bracket_len, 790)], fill=NEON_GREEN, width=4)
    draw.line([(10, 790), (10, 790 - bracket_len)], fill=NEON_GREEN, width=4)
    # Bottom Right
    draw.line([(790, 790), (790 - bracket_len, 790)], fill=NEON_GREEN, width=4)
    draw.line([(790, 790), (790, 790 - bracket_len)], fill=NEON_GREEN, width=4)

    # Header Bar
    draw.rectangle([(10, 10), (790, 50)], fill=(20, 30, 40, 200), outline=BORDER_COLOR, width=1)
    draw.text((25, 22), "STATUS: SWING ANALYSIS", fill=NEON_GREEN, font=font_header)
    draw.text((280, 22), f"PLAYER: {args.batter.upper()}", fill=TEXT_COLOR, font=font_header)
    draw.text((560, 22), f"PITCHER: {args.pitcher.upper()}", fill=TEXT_COLOR, font=font_header)
    
    # Draw home plate outline in perspective (centered bottom)
    plate_points = [
        (400, 700),  # Front tip
        (460, 640),  # Right corner
        (460, 580),  # Right back
        (340, 580),  # Left back
        (340, 640),  # Left corner
    ]
    draw.polygon(plate_points, outline=(0, 128, 96, 255), width=2)
    
    # Draw baseball (Target)
    ball_center = (400, 450)
    ball_radius = 28
    draw.ellipse([
        (ball_center[0] - ball_radius, ball_center[1] - ball_radius),
        (ball_center[0] + ball_radius, ball_center[1] + ball_radius)
    ], fill=(20, 60, 40, 255), outline=NEON_GREEN, width=3)
    # Stitches
    draw.arc([
        (ball_center[0] - ball_radius - 5, ball_center[1] - ball_radius),
        (ball_center[0] + 5, ball_center[1] + ball_radius)
    ], 310, 50, fill=(255, 64, 64, 255), width=2)
    draw.arc([
        (ball_center[0] - 5, ball_center[1] - ball_radius),
        (ball_center[0] + ball_radius + 5, ball_center[1] + ball_radius)
    ], 130, 230, fill=(255, 64, 64, 255), width=2)
    draw.text((ball_center[0] - 50, ball_center[1] + 35), "TARGET: BASEBALL", fill=TEXT_MUTED, font=font_small)

    # Draw swing path dotted line
    path_points = []
    for t in range(0, 50, 5):
        # Parametric curve representing swing arc passing over the plate
        # Bat comes from right/top down, sweeps through, exit left/up
        x = 650 - (t * 8)
        y = 250 + (t * 4) + (0.15 * (t - 25)**2)
        path_points.append((x, y))
        draw.ellipse([(x-3, y-3), (x+3, y+3)], fill=NEON_BLUE)
        
    # Draw bat cylinder wireframe (sweeping through)
    bat_x = 400
    bat_y = 270 # Over the top of the ball
    
    # Draw bat barrel cylindrical lines
    draw.ellipse([(bat_x - 120, bat_y - 20), (bat_x + 120, bat_y + 20)], outline=NEON_BLUE, width=1)
    
    # Draw bat cylinder
    bat_start = (180, 450) # handle
    bat_end = (600, 200) # barrel end
    draw.line([bat_start, bat_end], fill=(0, 96, 192, 100), width=35)
    
    # Draw bat wireframe rings
    steps = 15
    for s in range(steps):
        ratio = s / (steps - 1)
        px = bat_start[0] + ratio * (bat_end[0] - bat_start[0])
        py = bat_start[1] + ratio * (bat_end[1] - bat_start[1])
        thickness = 8 + int(ratio * 20)
        draw.ellipse([(px - thickness, py - thickness/2), (px + thickness, py + thickness/2)], outline=NEON_BLUE, width=1)
        
    draw.text((540, 240), "SWING PATH", fill=TEXT_MUTED, font=font_small)

    # Miss Distance Spatial Gap line
    sweet_spot = (400, 310)
    gap_start = sweet_spot
    gap_end = (400, ball_center[1] - ball_radius)
    
    # Draw vertical double headed arrow showing miss gap
    draw_arrow(draw, (400, gap_start[1] + 10), gap_end, NEON_GREEN, width=3)
    draw_arrow(draw, (400, gap_end[1] - 10), gap_start, NEON_GREEN, width=3)
    
    # Miss Distance Value Label
    miss_text = f"MISS DISTANCE: {args.miss_distance} INCHES"
    draw.text((420, 370), miss_text, fill=NEON_GREEN, font=font_large)

    # Telemetry data card (bottom right)
    card_x = 440
    card_y = 560
    draw.rectangle([(card_x, card_y), (770, 770)], fill=(15, 25, 35, 220), outline=NEON_BLUE, width=1)
    
    # Card Header
    draw.text((card_x + 15, card_y + 15), "STATCAST TELEMETRY", fill=NEON_BLUE, font=font_med)
    draw.line([(card_x + 15, card_y + 42), (755, card_y + 42)], fill=GRID_COLOR, width=1)
    
    # Card Data Lines
    draw.text((card_x + 15, card_y + 55), "VERTICAL DELTA:", fill=TEXT_MUTED, font=font_small)
    draw.text((card_x + 180, card_y + 55), f"{args.vertical_delta} IN ({args.vertical_alignment})", fill=NEON_GREEN, font=font_small)
    
    draw.text((card_x + 15, card_y + 85), "HORIZONTAL DELTA:", fill=TEXT_MUTED, font=font_small)
    draw.text((card_x + 180, card_y + 85), f"{args.horizontal_delta} IN ({args.horizontal_alignment})", fill=NEON_GREEN, font=font_small)
    
    draw.text((card_x + 15, card_y + 115), "SWING SPEED:", fill=TEXT_MUTED, font=font_small)
    draw.text((card_x + 180, card_y + 115), f"{args.swing_speed} MPH", fill=NEON_GREEN, font=font_small)
    
    draw.text((card_x + 15, card_y + 145), "PITCH METRIC:", fill=TEXT_MUTED, font=font_small)
    draw.text((card_x + 180, card_y + 145), f"{args.pitch_name} @ {args.pitch_speed} MPH", fill=NEON_GREEN, font=font_small)

    # Save Image
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    img.save(args.output, "PNG")
    print(f"Generated whiff graphic at {args.output}")

def get_persona_avatar(username):
    db_path = "/home/james/stacklabs/dna/sovereign_now.db"
    safe_name = username.lower().replace(" ", "_").lstrip('@')
    
    if "james" in safe_name:
        safe_name = "pilot_james"
    elif "barb" in safe_name:
        if "warden" in safe_name:
            safe_name = "warden_barb"
        else:
            safe_name = "barb_the_founder"

    is_full_body = False

    # Check canonical Barf dog asset
    if safe_name == "barf":
        canonical_barf = "/home/james/stacklabs/media_vault/03_Assets/Advocates/Barf/character_maps/barf_canonical_map.png"
        if os.path.exists(canonical_barf):
            try:
                return Image.open(canonical_barf).convert("RGBA"), "#00b4d8", True
            except:
                pass

    # Try database character_map_url or avatar_url
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT character_map_url, avatar_blob, avatar_url, color FROM persona WHERE user_name = ? OR user_name = ? OR display_name = ?", (safe_name, username, username))
        row = cursor.fetchone()
        conn.close()
        if row:
            char_map, blob_data, avatar_url, color = row
            if char_map and os.path.exists(char_map):
                try:
                    return Image.open(char_map).convert("RGBA"), color or "#00b4d8", True
                except:
                    pass
            if blob_data:
                try:
                    if blob_data.startswith('data:'):
                        header, b64 = blob_data.split(',', 1)
                    else:
                        b64 = blob_data
                    data = base64.b64decode(b64)
                    return Image.open(io.BytesIO(data)).convert("RGBA"), color or "#00b4d8", False
                except:
                    pass
            if avatar_url:
                filename = avatar_url
                if filename.startswith('/api/persona_image/'):
                    filename = filename.replace('/api/persona_image/', '')
                if filename.startswith('/avatars/'):
                    filename = filename.replace('/avatars/', '')
                elif filename.startswith('avatars/'):
                    filename = filename.replace('avatars/', '')
                
                for ext in ['.png', '.jpg', '.jpeg', '.webp', '.jfif']:
                    local_path = os.path.join("/home/james/stacklabs/avatars", filename)
                    if os.path.exists(local_path):
                        try:
                            return Image.open(local_path).convert("RGBA"), color or "#00b4d8", False
                        except:
                            pass
                    local_path_direct = os.path.join("/home/james/stacklabs/avatars", f"{safe_name}{ext}")
                    if os.path.exists(local_path_direct):
                        try:
                            return Image.open(local_path_direct).convert("RGBA"), color or "#00b4d8", False
                        except:
                            pass
    except Exception as e:
        print(f"Error fetching avatar for {username} from DB: {e}")

    # Fallback filesystem search for character maps / fullbody assets
    for search_dir in [
        "/home/james/stacklabs/media_vault/03_Assets/Advocates",
        "/home/james/stacklabs/media_vault/03_Assets/Harvested_Artifacts",
        "/home/james/stacklabs/avatars",
        "/home/james/stacklabs/15_FanStack/public/avatars"
    ]:
        for pattern in [f"*{safe_name}*charmap*", f"*{safe_name}*character_map*", f"{safe_name}.*"]:
            for f in glob.glob(os.path.join(search_dir, pattern)):
                if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp')):
                    try:
                        is_fb = "charmap" in f.lower() or "character_map" in f.lower()
                        return Image.open(f).convert("RGBA"), "#00b4d8", is_fb
                    except:
                        pass

    # Initial-based default avatar
    h = hashlib.md5(safe_name.encode()).hexdigest()
    color_hex = "#" + h[:6]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    
    img = Image.new("RGBA", (200, 200), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(10, 10), (190, 190)], fill=(r, g, b, 255), outline=(0, 180, 216, 255), width=4)
    try:
        font = ImageFont.truetype(FONT_BOLD, 96)
    except:
        font = ImageFont.load_default()
    letter = safe_name[0].upper() if safe_name else "?"
    draw.text((70, 45), letter, fill=(255, 255, 255, 255), font=font)
    return img, color_hex, False

def make_circular(img, size):
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse([(0, 0), (size, size)], fill=255)
    
    output = Image.new("RGBA", (size, size), (0,0,0,0))
    output.paste(img, (0, 0), mask=mask)
    return output

def draw_speech_bubble(draw, text, x_center, y_bottom, max_width=300):
    try:
        font = ImageFont.truetype(FONT_SANS, 14)
    except:
        font = ImageFont.load_default()
        
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w < max_width - 24:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
        
    line_widths = []
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
        
    bubble_w = max(line_widths) + 30 if line_widths else 120
    bubble_h = sum(line_heights) + 8 * len(line_heights) + 20 if line_heights else 50
    
    bx = int(x_center - bubble_w / 2)
    by = int(y_bottom - bubble_h)
    
    if bx < 20: bx = 20
    if bx + bubble_w > 980: bx = 980 - bubble_w
    if by < 20: by = 20
    
    # Glassmorphism dark bubble with vibrant neon cyan border
    draw.rounded_rectangle([(bx, by), (bx + bubble_w, by + bubble_h)], radius=12, fill=(11, 13, 19, 230), outline=(0, 180, 216, 255), width=2)
    
    curr_y = by + 12
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        tx = bx + (bubble_w - w) / 2
        draw.text((tx, curr_y), line, fill=(240, 248, 255, 255), font=font)
        curr_y += line_heights[i] + 8
        
    # Draw pointer triangle pointing down
    px = x_center
    py = y_bottom
    if px < bx + 15: px = bx + 15
    if px > bx + bubble_w - 15: px = bx + bubble_w - 15
    
    ptr_points = [
        (px - 10, by + bubble_h),
        (px + 10, by + bubble_h),
        (x_center, py)
    ]
    draw.polygon(ptr_points, fill=(11, 13, 19, 255), outline=(0, 180, 216, 255))
    draw.line([(px - 8, by + bubble_h), (px + 8, by + bubble_h)], fill=(11, 13, 19, 255), width=3)

def generate_dive_bar_composite(args):
    # Load background image
    bg_path = "/home/james/stacklabs/19_Sovereign_Sports/public/images/dive_bar_bg.png"
    if not os.path.exists(bg_path):
        # Fallback to creating a dark slate image if background is missing
        img = Image.new("RGBA", (1000, 1000), (11, 13, 19, 255))
    else:
        img = Image.open(bg_path).convert("RGBA")
        img = img.resize((1000, 1000), Image.Resampling.LANCZOS)
        
    draw = ImageDraw.Draw(img)
    
    # Parse list of personas
    persona_list = [p.strip() for p in args.personas.split(",") if p.strip()]
    active_persona = args.active_persona.strip() if args.active_persona else ""
    
    # Move active persona to the front of the roster so they are drawn at a prominent stool
    if active_persona:
        clean_active = active_persona.lower().lstrip('@')
        filtered = [p for p in persona_list if p.lower().lstrip('@') != clean_active]
        persona_list = [active_persona] + filtered
        
    # Define seating/stool coordinates
    positions = [
        {"x": 120, "y": 620, "size": 160}, # Stool 1 (front left)
        {"x": 320, "y": 570, "size": 140}, # Stool 2 (mid left)
        {"x": 480, "y": 520, "size": 120}, # Stool 3 (center left)
        {"x": 620, "y": 490, "size": 110}, # Stool 4 (center)
        {"x": 750, "y": 490, "size": 100}, # Stool 5 (mid right)
        {"x": 860, "y": 470, "size": 90},  # Booth 1 (right)
    ]
    
    active_coords = None
    
    # Draw personas
    for idx, p_name in enumerate(persona_list[:6]):
        pos = positions[idx]
        avatar_img, color_hex, is_full_body = get_persona_avatar(p_name)
        
        if is_full_body:
            # Scale full-body image proportionally to fit stool area
            target_h = int(pos["size"] * 1.8)
            aspect = avatar_img.width / float(avatar_img.height)
            target_w = int(target_h * aspect)
            fb_img = avatar_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            paste_x = pos["x"] + (pos["size"] - target_w) // 2
            paste_y = pos["y"] - (target_h - pos["size"])
            img.paste(fb_img, (paste_x, paste_y), mask=fb_img if fb_img.mode == 'RGBA' else None)
        else:
            # Render circular avatar fallback
            circular_av = make_circular(avatar_img, pos["size"])
            img.paste(circular_av, (pos["x"], pos["y"]), mask=circular_av)
            
            # Parse color
            try:
                if color_hex.startswith("#"):
                    r = int(color_hex[1:3], 16)
                    g = int(color_hex[3:5], 16)
                    b = int(color_hex[5:7], 16)
                    border_color = (r, g, b, 255)
                else:
                    border_color = (0, 180, 216, 255)
            except:
                border_color = (0, 180, 216, 255)
                
            # Border
            draw.ellipse([
                (pos["x"] - 2, pos["y"] - 2), 
                (pos["x"] + pos["size"] + 2, pos["y"] + pos["size"] + 2)
            ], outline=border_color, width=4)
        
        # Draw Name label pill below avatar
        try:
            font_lbl = ImageFont.truetype(FONT_BOLD, 12)
        except:
            font_lbl = ImageFont.load_default()
            
        clean_lbl = p_name.lstrip('@')
        bbox = draw.textbbox((0, 0), clean_lbl, font=font_lbl)
        lbl_w = bbox[2] - bbox[0]
        lbl_h = bbox[3] - bbox[1]
        
        lbl_x = pos["x"] + (pos["size"] - lbl_w) // 2
        lbl_y = pos["y"] + pos["size"] + 8
        
        # Pill background
        draw.rounded_rectangle([
            (lbl_x - 8, lbl_y - 4), 
            (lbl_x + lbl_w + 8, lbl_y + lbl_h + 4)
        ], radius=6, fill=(11, 13, 19, 220), outline=(0, 180, 216, 255), width=1)
        draw.text((lbl_x, lbl_y - 2), clean_lbl, fill=TEXT_COLOR, font=font_lbl)
        
        # Cache coordinate of active speaker
        if active_persona and p_name.lower().lstrip('@') == active_persona.lower().lstrip('@'):
            active_coords = (pos["x"] + pos["size"] // 2, pos["y"] - 15)

    # Draw speech bubble if there is an active text bubble
    if active_persona and args.chat_text and active_coords:
        draw_speech_bubble(draw, args.chat_text, active_coords[0], active_coords[1])

        
    # Save Image
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    img.save(args.output, "PNG")
    print(f"Generated Dive Bar composite image at {args.output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Mode switch
    parser.add_argument("--mode", type=str, choices=["whiff", "dive_bar"], default="whiff")
    
    # Whiff parameters
    parser.add_argument("--miss_distance", type=float, default=8.4)
    parser.add_argument("--vertical_alignment", type=str, default="OVER")
    parser.add_argument("--vertical_delta", type=float, default=-5.2)
    parser.add_argument("--horizontal_alignment", type=str, default="FLAILED")
    parser.add_argument("--horizontal_delta", type=float, default=6.6)
    parser.add_argument("--swing_speed", type=float, default=78.2)
    parser.add_argument("--pitch_speed", type=float, default=90.5)
    parser.add_argument("--pitch_name", type=str, default="Slider")
    parser.add_argument("--batter", type=str, default="Ronald Acuna Jr.")
    parser.add_argument("--pitcher", type=str, default="Edwin Diaz")
    
    # Dive Bar parameters
    parser.add_argument("--personas", type=str, default="")
    parser.add_argument("--active_persona", type=str, default="")
    parser.add_argument("--chat_text", type=str, default="")
    
    # General parameters
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()
    
    if args.mode == "whiff":
        generate_whiff_graphic(args)
    else:
        generate_dive_bar_composite(args)
