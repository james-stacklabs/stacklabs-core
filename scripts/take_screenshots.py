#!/usr/bin/env python3
"""
take_screenshots.py
Refactored, reusable, and parameterizable visual UAT capture utility.
Can be run standalone or triggered dynamically as part of the Stack Seeding process.
Now includes automatic 3D perspective tilt processing for seeder UI presentation cards.
"""
import os
import sys
import argparse
import asyncio
from PIL import Image, ImageDraw

def apply_perspective_tilt(src_path, dest_path, tilt_factor=0.06):
    """
    Applies a premium 3D quad-perspective tilt and floating drop shadow
    to a screenshot canvas using pure Pillow to avoid heavy CV2 dependencies.
    """
    print(f"Applying premium 3D tilt effect: {src_path} -> {dest_path}")
    try:
        src = Image.open(src_path).convert("RGBA")
        sw, sh = src.size

        # Create padded canvas to prevent edge cropping and allow drop shadow space
        pad_x, pad_y = 100, 100
        canvas_w = sw + pad_x * 2
        canvas_h = sh + pad_y * 2
        
        padded = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        padded.paste(src, (pad_x, pad_y))

        # Quad transformation coefficients: (x0, y0, x1, y1, x2, y2, x3, y3)
        # We tilt the right side backward (compressed vertically and shifted in)
        tilt_y = int(sh * tilt_factor)
        tilt_x = int(sw * 0.03)

        x0, y0 = pad_x, pad_y
        x1, y1 = pad_x, pad_y + sh
        x2, y2 = pad_x + sw - tilt_x, pad_y + sh - tilt_y
        x3, y3 = pad_x + sw - tilt_x, pad_y + tilt_y

        coeffs = (
            x0, y0,
            x1, y1,
            x2, y2,
            x3, y3
        )

        tilted = padded.transform((canvas_w, canvas_h), Image.QUAD, coeffs, Image.Resampling.BICUBIC)

        # Apply a soft dark drop shadow behind the card
        shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        
        # Soft dark outline matching the tilted quad
        s_draw.polygon([(x0+5, y0+5), (x1+5, y1+5), (x2+5, y2+5), (x3+5, y3+5)], fill=(0, 0, 0, 80))
        # Blur the shadow for premium soft appearance
        from PIL import ImageFilter
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))

        # Composite shadow + tilted card
        final = Image.alpha_composite(shadow, tilted)

        # Save output
        final.convert("RGB").save(dest_path, "PNG")
        print(f"✅ Premium 3D UAT card generated at: {dest_path}")
    except Exception as e:
        print(f"❌ Failed to apply perspective tilt: {e}")

async def run_capture(args):
    from playwright.async_api import async_playwright

    os.makedirs(args.outdir, exist_ok=True)
    print(f"Initializing Playwright UAT crawl targeting: {args.host}")
    
    async with async_playwright() as p:
        # Launch Chromium bypassing HSTS self-signed cert prompts natively
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': args.width, 'height': args.height},
            is_mobile=True,
            has_touch=True,
            ignore_https_errors=True
        )
        page = await context.new_page()

        # Step 1: Brand Seeder Intake Form Capture
        seeder_url = f"{args.host}/?room=stack_seeder"
        print(f"1. Navigating to Brand Intake Seeder: {seeder_url}")
        try:
            await page.goto(seeder_url, timeout=15000)
            await page.wait_for_timeout(3000)
            
            # Fill the WeedStack preset dynamically if we are on the WeedStack stack
            if args.domain.lower() == "weedstack":
                print("Autofilling WeedStack UAT preset for visual seeding check...")
                await page.fill("input[placeholder*='Brand Name']", "WeedStack")
                await page.fill("textarea[placeholder*='walked into a bar']", 
                                "WeedStack orders a green smoothie and lectures the bartender about Metrc compliance.")
                await page.fill("input[placeholder*='aesthetic']", "glassmorphic, earthy green, premium, organic, neon")
            
            temp_intake_path = os.path.join(args.outdir, "stack_seeder_ui_raw.png")
            await page.screenshot(path=temp_intake_path)
            
            # Transform raw screenshot into premium 3D tilted presentation card
            final_intake_path = os.path.join(args.outdir, "stack_seeder_ui.png")
            apply_perspective_tilt(temp_intake_path, final_intake_path)
            
            # Cleanup temp file
            if os.path.exists(temp_intake_path):
                os.remove(temp_intake_path)

        except Exception as e:
            print(f"❌ Failed to capture seeder intake: {e}")

        # Step 2: Main Simulation Room
        room_url = f"{args.host}/?room={args.room}"
        print(f"2. Navigating to Emergent Simulation Room: {room_url}")
        try:
            await page.goto(room_url, timeout=15000)
            await page.wait_for_timeout(4000)
            await page.screenshot(path=os.path.join(args.outdir, f"uat_02_{args.room.lower()}.png"))
        except Exception as e:
            print(f"❌ Failed to capture simulation room: {e}")

        # Step 3: SDLC Ticketing / Enhancements
        sdlc_url = f"{args.host}/?domain=ROOT"
        print(f"3. Navigating to SDLC/ITSM Portal: {sdlc_url}")
        try:
            await page.goto(sdlc_url, timeout=15000)
            await page.wait_for_timeout(2000)
            # Try clicking SDLC tab if visible
            try:
                await page.click("text=SDLC / Enhancements", timeout=3000)
                await page.wait_for_timeout(2000)
            except Exception:
                pass
            await page.screenshot(path=os.path.join(args.outdir, "uat_03_sdlc_portal.png"))
        except Exception as e:
            print(f"❌ Failed to capture SDLC Portal: {e}")

        # Step 4: CMDB Configuration Portal
        try:
            print("4. Navigating to CMDB configuration screen...")
            await page.goto(f"{args.host}/?domain=ROOT", timeout=15000)
            await page.wait_for_timeout(2000)
            try:
                await page.click("text=Employee Center (CMDB)", timeout=3000)
                await page.wait_for_timeout(2000)
            except Exception:
                pass
            await page.screenshot(path=os.path.join(args.outdir, "uat_04_cmdb_center.png"))
        except Exception as e:
            print(f"❌ Failed to capture CMDB Center: {e}")

        await browser.close()
        print(f"Done capturing all visual UAT screenshots in: {args.outdir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StackLabs visual UAT screen grabber.")
    parser.add_argument("--host", default="https://127.0.0.1:3000", help="Root host URL including protocol")
    parser.add_argument("--domain", default="WeedStack", help="Brand Sorting Hat domain name")
    parser.add_argument("--room", default="WEEDSTACK_SIM_001", help="Target simulation room key")
    parser.add_argument("--outdir", default="/home/james/sovereign_inbox/dashboards/presskit", help="Output directory")
    parser.add_argument("--width", type=int, default=390, help="Mobile viewport width")
    parser.add_argument("--height", type=int, default=844, help="Mobile viewport height")

    args = parser.parse_args()
    
    asyncio.run(run_capture(args))
