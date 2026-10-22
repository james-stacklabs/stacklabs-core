#!/usr/bin/env python3
"""
assemble_persona_cards.py
Programmatically compiles premium trading cards for FanStack and WeedStack personas,
arranging them in beautiful fanned arcs on a dark premium background.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = "/home/james/sovereign_inbox/dashboards/presskit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Select standard Linux system fonts or fallback
def get_fonts():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    font_mono_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ]
    font_italic_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansOblique.ttf",
    ]

    font_title = None
    font_mono = None
    font_quote = None

    for p in font_paths:
        if os.path.exists(p):
            font_title = ImageFont.truetype(p, 18)
            break
    if not font_title:
        font_title = ImageFont.load_default()

    for p in font_mono_paths:
        if os.path.exists(p):
            font_mono = ImageFont.truetype(p, 12)
            break
    if not font_mono:
        font_mono = ImageFont.load_default()

    for p in font_italic_paths:
        if os.path.exists(p):
            font_quote = ImageFont.truetype(p, 14)
            break
    if not font_quote:
        font_quote = ImageFont.load_default()

    return font_title, font_mono, font_quote

# Helper to draw text wrapped
def draw_wrapped_text(draw, text, x, y, max_width, font, fill, align="center"):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        # Check width
        line_str = " ".join(current_line)
        w = draw.textlength(line_str, font=font)
        if w > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    curr_y = y
    for line in lines:
        w = draw.textlength(line, font=font)
        if align == "center":
            draw.text((x - w/2, curr_y), line, font=font, fill=fill)
        else:
            draw.text((x, curr_y), line, font=font, fill=fill)
        curr_y += font.getbbox("A")[3] + 4
    return curr_y

# Generate a single premium card
def create_card(persona, accent_color, font_title, font_mono, font_quote):
    card_w, card_h = 360, 520
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 1. Outer premium glassmorphic border with a dark fill
    draw.rounded_rectangle(
        [(4, 4), (card_w - 4, card_h - 4)],
        radius=16,
        fill=(10, 10, 15, 235),  # Semi-transparent dark
        outline=accent_color,
        width=3
    )

    # Inner subtle highlight border
    draw.rounded_rectangle(
        [(10, 10), (card_w - 10, card_h - 10)],
        radius=12,
        fill=None,
        outline=(255, 255, 255, 15),
        width=1
    )

    # 2. Avatar slot (rounded rectangle frame)
    avatar_w, avatar_h = 180, 180
    avatar_x = (card_w - avatar_w) // 2
    avatar_y = 35

    # Check if avatar path exists
    has_avatar = False
    if "avatar" in persona and os.path.exists(persona["avatar"]):
        try:
            av_img = Image.open(persona["avatar"]).convert("RGBA")
            av_img = av_img.resize((avatar_w, avatar_h), Image.Resampling.LANCEOLATOR if hasattr(Image.Resampling, "LANCEOLATOR") else Image.Resampling.LANCZOS)
            
            # Mask to round avatar corners
            mask = Image.new("L", (avatar_w, avatar_h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([(0, 0), (avatar_w, avatar_h)], radius=12, fill=255)
            
            card.paste(av_img, (avatar_x, avatar_y), mask)
            has_avatar = True
        except Exception as e:
            print(f"Error loading avatar {persona['avatar']}: {e}")

    # Fallback botanical/geometric design if no avatar or SVG
    if not has_avatar:
        draw.rounded_rectangle(
            [(avatar_x, avatar_y), (avatar_x + avatar_w, avatar_y + avatar_h)],
            radius=12,
            fill=(20, 20, 30, 255),
            outline=accent_color,
            width=2
        )
        # Draw tech symbol inside fallback
        draw.ellipse(
            [(avatar_x + 40, avatar_y + 40), (avatar_x + avatar_w - 40, avatar_y + avatar_h - 40)],
            fill=None,
            outline=accent_color,
            width=2
        )
        draw.line(
            [(avatar_x + 90, avatar_y + 30), (avatar_x + 90, avatar_y + 150)],
            fill=accent_color,
            width=2
        )
        draw.line(
            [(avatar_x + 30, avatar_y + 90), (avatar_x + 150, avatar_y + 90)],
            fill=accent_color,
            width=2
        )

    # Frame highlight around avatar
    draw.rounded_rectangle(
        [(avatar_x - 2, avatar_y - 2), (avatar_x + avatar_w + 2, avatar_y + avatar_h + 2)],
        radius=14,
        fill=None,
        outline=(255, 255, 255, 30),
        width=1
    )

    # 3. Text details
    # Monospace role badge
    badge_text = f"[ {persona['role']} ]"
    badge_w = draw.textlength(badge_text, font=font_mono)
    draw.text(((card_w - badge_w)/2, 235), badge_text, font=font_mono, fill=accent_color)

    # Display Name
    name_w = draw.textlength(persona["name"], font=font_title)
    draw.text(((card_w - name_w)/2, 260), persona["name"], font=font_title, fill=(255, 255, 255, 255))

    # Decorative separator line
    draw.line(
        [(40, 300), (card_w - 40, 300)],
        fill=(255, 255, 255, 20),
        width=1
    )

    # Quote block in italics
    quote_text = f"\"{persona['quote']}\""
    draw_wrapped_text(
        draw, quote_text, card_w/2, 325, card_w - 80, font_quote, (210, 210, 220, 255), align="center"
    )

    return card

# Assemble fanned cards into composite image
def make_fanned_composite(personas, accent_color, output_filename):
    canvas_w, canvas_h = 1920, 1080
    
    # Premium background with deep dark glow gradient
    bg = Image.new("RGBA", (canvas_w, canvas_h), (6, 6, 8, 255))
    draw = ImageDraw.Draw(bg)

    # Subtle cyan or green radial gradient highlight in the center/bottom
    highlight_color = (accent_color[0], accent_color[1], accent_color[2], 25)
    for radius in range(900, 100, -10):
        alpha = int(25 * (1.0 - radius / 900.0))
        glow_col = (accent_color[0], accent_color[1], accent_color[2], alpha)
        draw.ellipse(
            [(canvas_w/2 - radius, canvas_h - radius/2 - 200), (canvas_w/2 + radius, canvas_h + radius/2 - 200)],
            fill=None,
            outline=glow_col,
            width=10
        )

    # Clean sans-serif title at the top
    font_title, font_mono, font_quote = get_fonts()
    title_text = "SOVEREIGN OS // COMMENTARY PERSONA SPECS"
    if accent_color == (0, 212, 255, 255):
        title_text = "SOVEREIGN FANSTACK // SPORTS MULTI-AGENT SWARM"
    elif accent_color == (0, 200, 120, 255):
        title_text = "WILDSEED WEEDSTACK // HORTICULTURAL BRAND INTAKE"
    
    draw.text((80, 60), title_text, font=font_title, fill=(255, 255, 255, 220))
    draw.text((80, 95), "ACTIVE COGNITIVE ARCHITECTURES RESOLVED NATIVELY", font=font_mono, fill=accent_color)
    draw.line([(80, 125), (600, 125)], fill=accent_color, width=2)

    # Card layout configurations
    cards = []
    for p in personas:
        card = create_card(p, accent_color, font_title, font_mono, font_quote)
        cards.append(card)

    num_cards = len(cards)
    
    # Arc positioning
    center_x = canvas_w // 2
    center_y = canvas_h + 300 # Pivot point way below screen
    arc_radius = 800

    # Determine angle offsets
    if num_cards == 4:
        angles = [-16, -5, 5, 16]
    else:
        angles = [-18, -9, 0, 9, 18]

    for i, angle in enumerate(angles):
        if i >= num_cards:
            break
        card = cards[i]
        
        # Calculate positioning on arc
        rad_angle = math.radians(angle)
        card_center_x = center_x + arc_radius * math.sin(rad_angle)
        card_center_y = center_y - arc_radius * math.cos(rad_angle) - 100

        # Rotate card image (expanding to fit rotated rect without cropping)
        # Pillow rotate takes negative degrees for clockwise rotation
        rotated_card = card.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
        rot_w, rot_h = rotated_card.size

        # Paste onto canvas
        paste_x = int(card_center_x - rot_w / 2)
        paste_y = int(card_center_y - rot_h / 2)
        bg.alpha_composite(rotated_card, (paste_x, paste_y))

    # Add premium bottom border
    draw.line([(80, canvas_h - 80), (canvas_w - 80, canvas_h - 80)], fill=(255, 255, 255, 20), width=1)
    draw.text((80, canvas_h - 65), "SYSTEM STATE: ACTIVE // NO DEPLOYMENT ERRORS", font=font_mono, fill=(255, 255, 255, 80))
    draw.text((canvas_w - 300, canvas_h - 65), "SOVEREIGN OS PRESS KIT v1.0", font=font_mono, fill=accent_color)

    # Save output
    out_path = os.path.join(OUTPUT_DIR, output_filename)
    bg.convert("RGB").save(out_path, "PNG")
    print(f"✅ Fan composite saved successfully: {out_path}")

# Run script
if __name__ == "__main__":
    # 1. FanStack Personas
    fanstack_personas = [
        {
            "name": "Barf",
            "role": "CHC // SENIOR ULCELL",
            "avatar": "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/barf.png",
            "quote": "Edwin Díaz blowing saves under neon lights... we out here rapping while the Mets collapse!"
        },
        {
            "name": "Pete the Pocket Protector",
            "role": "PIT // TRUST FUND AUDITOR",
            "avatar": "/home/james/stacklabs/media_vault/01_Assets/Inbox/welfare_bucco_avatar.png",
            "quote": "Bob Nutting is stashing our revenue-sharing checks straight into his family trust fund."
        },
        {
            "name": "Bartholomew Greene",
            "role": "CHC // CONSPIRACY TRUTH",
            "avatar": "/home/james/stacklabs/media_vault/01_Assets/Inbox/CubsConspiracy_avatar.png",
            "quote": "They want LA to win, Ohtani to shine. They don't want the Cubbies to get theirs!"
        },
        {
            "name": "Bronx Cheer Charlie",
            "role": "NYY // 27 RINGS DOOMER",
            "avatar": "/home/james/stacklabs/media_vault/01_Assets/Inbox/YankeeStadiumBully_avatar.png",
            "quote": "One strikeout and the front office is dead to me. Fire everybody and hire puppets."
        }
    ]

    # 2. WeedStack Personas
    weedstack_personas = [
        {
            "name": "Dr. Terp",
            "role": "WILDSEED // MASTER GROWER",
            "avatar": "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/terpene_titan.svg", # fallback triggers safely
            "quote": "The living soil is a high-entropy engine. 4.2% terps or we start the cure over."
        },
        {
            "name": "Terpene Trekker",
            "role": "WILDSEED // STRAIN SCRIBE",
            "avatar": "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/terp_trekker.svg",
            "quote": "Metrc trackers don't lie, but the laboratory test results sometimes do."
        },
        {
            "name": "Metrc Maven",
            "role": "WILDSEED // COMPLIANCE LEAD",
            "avatar": "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/metrc_maven.svg",
            "quote": "Your batch certificate of analysis is missing a signature. Lock the vault."
        },
        {
            "name": "Cultivar Catalyst",
            "role": "WILDSEED // BRAND SORTER",
            "avatar": "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/cultivar_catalyst.svg",
            "quote": "If this brand walked into a bar, it would order a double IPA and play ambient doom metal."
        }
    ]

    print("Assembling FanStack Card Set...")
    make_fanned_composite(fanstack_personas, (0, 212, 255, 255), "persona_cards_fanstack.png")

    print("\nAssembling WeedStack Card Set...")
    make_fanned_composite(weedstack_personas, (0, 200, 120, 255), "persona_cards_weedstack.png")

    print("\nPersona Card Set assembly complete!")
