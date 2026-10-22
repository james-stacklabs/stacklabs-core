#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Instant Meme Engine
Generates high-contrast Deep Void (#0B0D13) sports fan meme cards from livechat telemetry
and Barf the Dog's unhinged reactions, ready for direct Discord webhook attachment.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/instant_meme_engine.py
"""
import argparse
import json
import logging
import os
import pathlib
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.advocate_model_gateway import call_vertex_ai

DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
ENV_PATH = PROJECT_ROOT / ".env"
OUTPUT_DIR = PROJECT_ROOT / "evidence" / "memes"
TEMP_DIR = pathlib.Path("/dev/shm")

# Deep Void & Slate Palette
COLOR_BG = (11, 13, 19, 255)         # #0B0D13 Deep Void
COLOR_CARD = (17, 20, 30, 255)       # #11141E Dark Slate
COLOR_BORDER = (30, 37, 56, 255)     # #1E2538 Slate Hairline
COLOR_QUOTE_BG = (22, 27, 38, 255)   # #161B26 Callout Box
COLOR_AMBER = (230, 126, 34, 255)    # #E67E22 Radio Amber Accent
COLOR_WHITE = (248, 250, 252, 255)   # #F8FAFC Primary Text
COLOR_MUTED = (148, 163, 184, 255)   # #94A3B8 Secondary Text
COLOR_BARF = (245, 158, 11, 255)     # #F59E0B Barf Accent

FONT_BOLD_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("instant_meme_engine")


def get_webhook() -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("STACKLABS_PRIVATE_DISCORD_WEBHOOK="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def load_fonts() -> Tuple[Any, Any, Any, Any]:
    try:
        font_header = ImageFont.truetype(FONT_BOLD_PATH, 24)
        font_quote = ImageFont.truetype(FONT_BOLD_PATH, 32)
        font_roast = ImageFont.truetype(FONT_BOLD_PATH, 26)
        font_small = ImageFont.truetype(FONT_REG_PATH, 18)
    except Exception:
        font_header = font_quote = font_roast = font_small = ImageFont.load_default()
    return font_header, font_quote, font_roast, font_small


def wrap_text(text: str, font: Any, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    lines = []
    words = text.split()
    if not words:
        return lines
    current_line = words[0]
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def fetch_latest_wiretap_quote() -> Dict[str, Any]:
    if not DB_PATH.exists():
        return {
            "author": "queens_bleacher_bum",
            "channel_key": "radio_wfan",
            "message": "They're punting on 4th and 1 while down two touchdowns! I want to chew through the television wire!"
        }
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        query = """
            SELECT author, channel_key, message
            FROM chat_telemetry
            WHERE length(message) >= 30
              AND message NOT LIKE '!%'
              AND channel_key NOT LIKE '%Wardy%'
              AND message NOT LIKE '%Wardy%'
            ORDER BY id DESC
            LIMIT 1
        """
        row = cur.execute(query).fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        logger.warning(f"Could not read from wiretap DB: {e}")

    return {
        "author": "diehard_49ers",
        "channel_key": "radio_phly",
        "message": "Watching this offensive line pass-protect is like watching four folding chairs trying to stop a tidal wave."
    }


def generate_barf_meme_roast(quote_text: str, author: str, topic: Optional[str] = None) -> str:
    prompt = f"""You are Barf the Dog (@BarfFanStack), an unhinged New York sports fan watching live TV from a booth at Ben's Deli.
Context:
Fan @{author} just posted this sports comment:
"{quote_text}"
{f"Target Topic: {topic}" if topic else ""}

Write Barf's savage, hilarious 2-sentence reaction.
- Tone: Queens cynical, high blood pressure, absurd deli analogies, complete sports despair.
- Start with 'BARK BARK!' or 'HOLY SOTO!' or similar dog/fan barking.
- Keep it punchy, <= 180 characters. Zero hashtags, zero corporate fluff, zero AI mentions."""

    try:
        resp = call_vertex_ai(prompt, temperature=0.8)
        if resp and resp.strip():
            return resp.strip().replace('"', '')
    except Exception as e:
        logger.warning(f"Vertex AI call failed for meme roast: {e}")

    return "BARK BARK! My cardiologist just called to cancel my life insurance after reading that take! Pass the pastrami and let me weep into my mustard!"


def render_meme_card(
    quote: str,
    author: str,
    source: str,
    roast: str,
    output_path: Optional[pathlib.Path] = None
) -> pathlib.Path:
    width, height = 1200, 675
    img = Image.new("RGBA", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)
    font_header, font_quote, font_roast, font_small = load_fonts()

    # Draw Outer Card Container
    card_rect = [(30, 30), (width - 30, height - 30)]
    draw.rounded_rectangle(card_rect, radius=16, fill=COLOR_CARD, outline=COLOR_BORDER, width=2)

    # Accent Top Strip
    draw.rounded_rectangle([(30, 30), (width - 30, 42)], radius=4, fill=COLOR_AMBER)

    # Header Bar
    draw.text((60, 60), "🐕 BARF THE DOG // BLEACHER WIRETAP", font=font_header, fill=COLOR_AMBER)
    draw.text((width - 360, 64), f"SOURCE: {source.upper()}", font=font_small, fill=COLOR_MUTED)

    # Quote Callout Box
    quote_box = [(60, 110), (width - 60, 340)]
    draw.rounded_rectangle(quote_box, radius=12, fill=COLOR_QUOTE_BG, outline=COLOR_BORDER, width=1)

    # Author Pill
    author_text = f"🗣️ @{author.lstrip('@')}"
    draw.text((85, 130), author_text, font=font_small, fill=COLOR_AMBER)

    # Wrap & Draw Quote
    max_quote_w = width - 180
    quote_lines = wrap_text(f"\"{quote}\"", font_quote, max_quote_w, draw)[:4]
    y_text = 175
    for line in quote_lines:
        draw.text((85, y_text), line, font=font_quote, fill=COLOR_WHITE)
        y_text += 42

    # Barf's Reaction Container
    roast_box = [(60, 360), (width - 60, height - 90)]
    draw.rounded_rectangle(roast_box, radius=12, fill=COLOR_CARD, outline=COLOR_AMBER, width=2)

    # Barf Header Label
    draw.text((85, 380), "🐶 BARF THE DOG'S VERDICT:", font=font_small, fill=COLOR_BARF)

    # Wrap & Draw Roast
    max_roast_w = width - 180
    roast_lines = wrap_text(roast, font_roast, max_roast_w, draw)[:4]
    y_roast = 425
    for line in roast_lines:
        draw.text((85, y_roast), line, font=font_roast, fill=COLOR_WHITE)
        y_roast += 38

    # Watermark Footer
    footer_text = "STACKLABS INSTANT MEME ENGINE • ZERO AI SLOP • QUEENS NY"
    draw.text((60, height - 60), footer_text, font=font_small, fill=COLOR_MUTED)

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S EDT")
    draw.text((width - 320, height - 60), timestamp_str, font=font_small, fill=COLOR_MUTED)

    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"meme_{int(time.time())}.png"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    img.save(str(output_path), "PNG")
    logger.info(f"Meme card rendered to: {output_path}")
    return output_path


def dispatch_meme_to_discord(meme_path: pathlib.Path, caption: str) -> bool:
    import requests
    webhook_url = get_webhook()
    if not webhook_url:
        logger.error("No Discord webhook configured.")
        return False

    with open(meme_path, "rb") as f:
        files = {"files[0]": (meme_path.name, f, "image/png")}
        data = {
            "username": "Barf the Dog (@BarfFanStack)",
            "content": caption
        }
        try:
            r = requests.post(webhook_url, data=data, files=files, timeout=15)
            logger.info(f"Dispatched meme to Discord: HTTP {r.status_code}")
            return r.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Failed to upload meme to Discord: {e}")
            return False


def build_instant_meme(topic: Optional[str] = None, dispatch: bool = False) -> Tuple[pathlib.Path, Dict[str, Any]]:
    wiretap = fetch_latest_wiretap_quote()
    quote = wiretap.get("message", "")
    author = wiretap.get("author", "anonymous")
    source = wiretap.get("channel_key", "wiretap")

    roast = generate_barf_meme_roast(quote, author, topic)
    out_path = TEMP_DIR / f"barf_instant_meme_{int(time.time())}.png"
    rendered_path = render_meme_card(quote, author, source, roast, out_path)

    metadata = {
        "author": author,
        "source": source,
        "quote": quote,
        "roast": roast,
        "path": str(rendered_path)
    }

    if dispatch:
        caption = f"🐕 **[INSTANT MEME DROP]** *Overheard in {source.upper()}*: @{author}\n\"{roast}\""
        dispatch_meme_to_discord(rendered_path, caption)

    return rendered_path, metadata


def main():
    parser = argparse.ArgumentParser(description="StackLabs Instant Meme Engine")
    parser.add_argument("--topic", type=str, help="Optional sports topic to steer the roast")
    parser.add_argument("--dispatch", action="store_true", help="Post directly to Discord webhook")
    parser.add_argument("--dry-run", action="store_true", help="Generate image locally without posting")
    args = parser.parse_args()

    out_file, meta = build_instant_meme(topic=args.topic, dispatch=args.dispatch and not args.dry_run)
    print(f"✅ Meme Engine Complete: {out_file} ({out_file.stat().st_size} bytes)")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
