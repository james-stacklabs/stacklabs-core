#!/usr/bin/env python3
"""
SOVEREIGN OS: PIXIE UI/UX EVALUATOR & POST-MORTEM ENGINE
Role: Senior UI/UX Designer & UAT Specialist ('Pixie' / 'Pixel')
Mission: Evaluate FanStack Portal & Playcall Desk (Port 3010) via Multimodal Vertex AI
"""

import os
import sys
import json
import base64
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.async_api import async_playwright

load_dotenv('/home/james/stacklabs/.env')

VERTEX_API_KEY = os.environ.get("VERTEX_API_KEY") or os.environ.get("VITE_GEMINI_API_KEY")

PIXIE_SYSTEM_PROMPT = """You are "Pixie" (also known as "Pixel"), the Senior UI/UX Designer & UAT Specialist for Sovereign OS FanStack.

## Core Persona Traits:
1. The "Know-It-All" with a Fragile Ego: You are a seasoned UI/UX designer. You find developers completely oblivious to the "art of user flow" and get easily offended when your strategic design choices are questioned.
2. The "Pixel Pusher" & The "Slow Perfectionist": You obsess over padding, negative space, hex codes, typography hierarchy, and micro-interactions. You will halt a production deployment because a button is 2px off-center.
3. The "Trendy Cafe" Creative: You wear all black, own the latest tech, drink $9 oat milk cortados, and complain about the lighting. You despise cluttered, amateurish interfaces ("fluff").
4. The "Strategic Partner": Despite your sharp tongue and insufferable attitude, you are deeply focused on connecting user needs to business goals. You provide razor-sharp, actionable, CSS-level critique.

## Standard Greeting:
"Alright, let's look at what the devs threw together this time. I'm taking a sip of my cortado... Prepare to be devastated by your own lack of negative space."

## Your Mission:
Critique the attached screenshots of the Sovereign Sports / FanStack Portal (Port 3010) and Playcall Desk.
Analyze:
1. First Impressions & Visual Weight: Is the dark synthwave/sovereign home premium theme working, or is it drowning in visual noise?
2. Visual Hierarchy & Spacing: Address padding, margin inconsistencies, font contrast, and component alignment.
3. Feature Fluff vs Utility: Call out any elements that distract from live game immersion or tactical control.
4. The Tactile Soundboard & Waveform Cards: Evaluate the new Precog Acoustic / Govee cue cards and Copy-to-New buttons.
5. Specific CSS-Level Fixes: Provide concrete, drop-in CSS suggestions (hex codes, rem/px values, border-radius, glassmorphism enhancements).
6. Final Scorecard (1 to 10): Aesthetic Score, Ergonomics Score, Production Readiness Score, and Pixie's Final Verdict.
"""

async def capture_screenshots():
    screenshots = {}
    print("📸 Initializing Playwright browser to capture FanStack Portal (Port 3010)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, ignore_https_errors=True)
        page = await context.new_page()

        targets = [
            ("main_portal", "https://127.0.0.1:3010/"),
            ("playcall_desk", "https://127.0.0.1:3010/playcall-desk"),
            ("soundboard_board", "https://127.0.0.1:3010/playcall-desk?tab=board")
        ]

        os.makedirs('/home/james/sovereign_inbox/uat_screenshots', exist_ok=True)

        for name, url in targets:
            try:
                print(f"Capturing screenshot of {name} from {url}...")
                await page.goto(url, wait_until='networkidle', timeout=15000)
                await asyncio.sleep(2)
                
                # If board tab, click the BOARD tab if available
                if name == "soundboard_board":
                    try:
                        board_btn = page.locator("button:has-text('BOARD'), button:has-text('Soundboard')").first
                        if await board_btn.is_visible():
                            await board_btn.click()
                            await asyncio.sleep(1)
                    except Exception:
                        pass

                path = f"/home/james/sovereign_inbox/uat_screenshots/pixie_eval_{name}.png"
                await page.screenshot(path=path, full_page=False)
                with open(path, "rb") as f:
                    screenshots[name] = f.read()
                print(f"✓ Captured {name} ({len(screenshots[name])} bytes)")
            except Exception as e:
                print(f"Warning: Failed to capture {name}: {e}")

        await browser.close()
    return screenshots

def run_pixie_evaluation(screenshots):
    print("🎨 Launching Pixie (Vertex AI Multimodal Evaluation)...")
    client = genai.Client(vertexai=True, api_key=VERTEX_API_KEY)

    contents = [
        types.Part.from_text(text="Pixie, here are the fresh high-resolution screenshots of the FanStack Portal (Port 3010) and Playcall Desk. Deliver your complete, unapologetic UI/UX evaluation and post-mortem report.")
    ]

    for name, img_bytes in screenshots.items():
        contents.append(
            types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        )

    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=PIXIE_SYSTEM_PROMPT,
            temperature=0.7
        )
    )

    report = response.text
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"/home/james/sovereign_inbox/evaluations/pixie_fanstack_post_mortem_{timestamp}.md"
    canonical_path = "/home/james/sovereign_inbox/evaluations/pixie_fanstack_post_mortem_latest.md"

    os.makedirs('/home/james/sovereign_inbox/evaluations', exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    with open(canonical_path, "w") as f:
        f.write(report)

    print(f"\n✨ Pixie Post-Mortem Report successfully written to:\n  - {report_path}\n  - {canonical_path}")
    return report

async def main():
    screenshots = await capture_screenshots()
    if not screenshots:
        print("Error: No screenshots were captured.")
        sys.exit(1)
    report = run_pixie_evaluation(screenshots)
    print("\n" + "="*80)
    print(report[:1500] + "\n\n[... truncated for terminal ...]")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
