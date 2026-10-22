#!/usr/bin/env python3
"""
Render Barf 1-Page Teaser Card for Tyler Ward (@WardyNYM)
Outputs:
  - /home/james/sovereign_inbox/pilot_drops/barf_teaser_card.png
  - /home/james/sovereign_inbox/pilot_drops/barf_teaser_card.pdf
  - /home/james/stacklabs/screenshots/barf_teaser_card.png
"""

import os
import sys
import base64
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

IMG_DIR = Path("/home/james/sovereign_inbox/pilot_drops/the_real_barf_22")
OUTPUT_DIR = Path("/home/james/sovereign_inbox/pilot_drops")
SCREENSHOTS_DIR = Path("/home/james/stacklabs/screenshots")

def get_b64_image(filename: str) -> str:
    path = IMG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing required puppet photo: {path}")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{data}"

async def render():
    print("[*] Encoding authentic terrier puppet photos (Anti-Deadpool Invariant)...")
    img_panel1 = get_b64_image("shot_7_close-up_portrait.jpg")
    img_panel2 = get_b64_image("shot_6_close-up_portrait.jpg")
    img_panel3 = get_b64_image("shot_14_close-up.jpg")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

  @page {{
    size: 1200px 1650px;
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    width: 1200px;
    height: 1650px;
    background: linear-gradient(145deg, #070e17 0%, #0c1827 50%, #08111e 100%);
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    padding: 40px 48px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }}

  /* Top Bar */
  .header {{
    border-bottom: 2px solid rgba(255, 89, 16, 0.35);
    padding-bottom: 24px;
  }}

  .badge-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}

  .badge-tag {{
    background: #FF5910;
    color: #070e17;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 6px 14px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }}

  .target-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 5px 12px;
    border-radius: 6px;
  }}

  .title-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}

  .title-area h1 {{
    font-size: 46px;
    font-weight: 900;
    letter-spacing: -1px;
    color: #ffffff;
    line-height: 1.1;
  }}

  .title-area h1 span {{
    color: #FF5910;
  }}

  .title-area .subtitle {{
    font-size: 18px;
    font-weight: 600;
    color: #38bdf8;
    margin-top: 4px;
    letter-spacing: 0.5px;
  }}

  .quote-box {{
    background: rgba(255, 89, 16, 0.08);
    border-left: 4px solid #FF5910;
    padding: 12px 18px;
    border-radius: 0 8px 8px 0;
    max-width: 480px;
  }}

  .quote-box p {{
    font-size: 15px;
    font-style: italic;
    color: #fed7aa;
    line-height: 1.4;
  }}

  .quote-box .author {{
    font-size: 12px;
    font-style: normal;
    color: #94a3b8;
    margin-top: 4px;
    font-weight: 600;
  }}

  /* Section Title */
  .section-label {{
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #FF5910;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .section-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
  }}

  /* Reaction Panels Grid */
  .reaction-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-bottom: 24px;
  }}

  .reaction-card {{
    background: #0f1c2e;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
  }}

  .reaction-card.meltdown {{
    border-color: rgba(239, 68, 68, 0.5);
    background: linear-gradient(180deg, #131b2e 0%, #1c1219 100%);
  }}

  .reaction-card.panic {{
    border-color: rgba(249, 115, 22, 0.5);
    background: linear-gradient(180deg, #131b2e 0%, #1f1712 100%);
  }}

  .card-img-wrapper {{
    position: relative;
    width: 100%;
    height: 240px;
    overflow: hidden;
    background: #050b14;
  }}

  .card-img-wrapper img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 20%;
  }}

  .card-tag {{
    position: absolute;
    bottom: 8px;
    left: 8px;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(4px);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #f1f5f9;
    padding: 4px 8px;
    border-radius: 4px;
    border-left: 3px solid #38bdf8;
  }}

  .card-tag.orange {{
    border-left-color: #FF5910;
  }}

  .card-tag.red {{
    border-left-color: #ef4444;
  }}

  .card-body {{
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;
  }}

  .card-state {{
    font-size: 13px;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 6px;
  }}

  .card-quote {{
    font-size: 13px;
    line-height: 1.5;
    color: #f8fafc;
    font-weight: 500;
  }}

  .card-quote em {{
    color: #fca5a5;
    font-style: normal;
    font-weight: 700;
  }}

  /* Value Proposition Section */
  .value-prop-container {{
    background: #0a1424;
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 12px;
    padding: 22px;
    margin-bottom: 20px;
  }}

  .value-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }}

  .value-item {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 14px 16px;
  }}

  .value-item-title {{
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }}

  .value-item-title .icon {{
    color: #FF5910;
    font-size: 16px;
  }}

  .value-item p {{
    font-size: 12.5px;
    line-height: 1.45;
    color: #cbd5e1;
  }}

  .value-item strong {{
    color: #38bdf8;
  }}

  .raid-banner {{
    background: rgba(239, 68, 68, 0.12);
    border: 1px dashed rgba(239, 68, 68, 0.4);
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #fca5a5;
  }}

  /* Footer */
  .footer {{
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #64748b;
  }}

  .footer-left {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .footer-status {{
    color: #10b981;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .footer-status::before {{
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }}

  .footer-right {{
    font-family: 'JetBrains Mono', monospace;
  }}
</style>
</head>
<body>

  <!-- Header Block -->
  <div class="header">
    <div class="badge-row">
      <div class="badge-tag">⚡ FanStack Creator Partnership // Tyler Ward (@WardyNYM)</div>
      <div class="target-badge">M.A.R.D. Boggs Level 5 • Game PK 823574 Simulation</div>
    </div>
    <div class="title-row">
      <div class="title-area">
        <h1>BARF <span>(@barf)</span></h1>
        <div class="subtitle">The Chronicler of Inevitable Collapse // South Queens Bureau</div>
      </div>
      <div class="quote-box">
        <p>"The bullpen is warming up just to ruin our lives."</p>
        <div class="author">— Barf, Mets Gameday Mascot & Resident Nihilist</div>
      </div>
    </div>
  </div>

  <!-- Verified Reaction Strip -->
  <div>
    <div class="section-label">3-Panel Statcast Reaction Arc // Baltimore Orioles @ New York Mets (Sep 15, 2026)</div>
    <div class="reaction-grid">

      <!-- Panel 1 -->
      <div class="reaction-card">
        <div class="card-img-wrapper">
          <img src="{img_panel1}" alt="Barf Panel 1">
          <div class="card-tag">PANEL 1 • TOP 1ST (0-0)</div>
        </div>
        <div class="card-body">
          <div class="card-state">Pre-Game Delusional Hope</div>
          <div class="card-quote">
            "Kodai Senga's ghost fork is dancing today. Pete is back in Citi Field, but Baltimore's bats look cold. Today is the day we turn the corner, I can feel it in my whiskers. LFGM baby!"
          </div>
        </div>
      </div>

      <!-- Panel 2 -->
      <div class="reaction-card panic">
        <div class="card-img-wrapper">
          <img src="{img_panel2}" alt="Barf Panel 2">
          <div class="card-tag orange">PANEL 2 • TOP 9TH (3-3 TIE)</div>
        </div>
        <div class="card-body">
          <div class="card-state" style="color: #f97316;">Pete Alonso 300th HR off Senga</div>
          <div class="card-quote">
            "NO NO NO NO NO! ARE YOU KIDDING ME?! ARE YOU ABSOLUTELY, POSITIVELY KIDDING ME RIGHT NOW?! I KNEW IT! I F*CKING KNEW IT! PETE ALONSO, IN A GODDAMN ORIOLES UNIFORM, OFF KODAI SENGA, OUR ACE! IN THE NINTH! TIES THE GAME! IN CITI FIELD! THE POETIC INJUSTICE, THE SHEER CRUELTY, IT'S A MASTERCLASS IN METS PAIN!"
          </div>
        </div>
      </div>

      <!-- Panel 3 -->
      <div class="reaction-card meltdown">
        <div class="card-img-wrapper">
          <img src="{img_panel3}" alt="Barf Panel 3">
          <div class="card-tag red">PANEL 3 • TOP 11TH (7-4 BAL)</div>
        </div>
        <div class="card-body">
          <div class="card-state" style="color: #ef4444;">Inside-The-Park 3-Run Meltdown</div>
          <div class="card-quote">
            "INSIDE THE PARK?! A THREE-RUNNER?! IN THE ELEVENTH?! PINTARO?! THIS IS THE WAY! MY THERAPIST IS GOING TO NEED A THERAPIST. THE SCRIPT WRITERS ARE PURE SADISTS! I CAN'T EVEN SEE STRAIGHT!"
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- Value Proposition Footer -->
  <div class="value-prop-container">
    <div class="section-label" style="color: #38bdf8; margin-bottom: 14px;">The Creator Value Proposition // Built for Tyler Ward (@WardyNYM)</div>
    <div class="value-grid">

      <!-- Pillar 1 -->
      <div class="value-item">
        <div class="value-item-title"><span class="icon">👥</span> Audience Multiplier, Not Competition</div>
        <p>Fans gather in your branded lounge during the live 3 hours of play watching vector Statcast telemetry and bantering. <strong>Zero host babysitting required</strong>—relax before your postgame show while FanStack runs fully autonomous.</p>
      </div>

      <!-- Pillar 2 -->
      <div class="value-item">
        <div class="value-item-title"><span class="icon">🚀</span> Automated Final-Out YouTube Raid</div>
        <p>The millisecond the official final out is certified, FanStack executes an instant full-screen handoff transferring 850+ pre-hyped fans straight to your live stream.</p>
        <div class="raid-banner">🚨 AUTO-RAID TARGET: https://www.youtube.com/@WardyNYM/live</div>
      </div>

      <!-- Pillar 3 -->
      <div class="value-item">
        <div class="value-item-title"><span class="icon">🛡️</span> Zero MLB Copyright Risk</div>
        <p>Proprietary 60 FPS vector Statcast pitch radar and tactical field diamond eliminate 100% of DMCA strikes, takedowns, and YouTube Content ID demonetization risks.</p>
      </div>

      <!-- Pillar 4 -->
      <div class="value-item">
        <div class="value-item-title"><span class="icon">🎮</span> Downtime In-Break Suite & Monetization</div>
        <p>Commercial breaks stay electric with Shea Zork retro text adventure, trivia showdowns, and live fan tipping. In-game Superchats queue high-heat debates for your postgame mailbag.</p>
      </div>

    </div>
  </div>

  <!-- Card Footer -->
  <div class="footer">
    <div class="footer-left">
      <div class="footer-status">STAGED FOR SERIES FINALE (GAME PK 823576)</div>
      <div>Mascot Anchor: Authentic Physical Terrier Puppet (#86)</div>
      <div>Anti-Deadpool Guardrail: Enforced</div>
    </div>
    <div class="footer-right">
      Sovereign OS • FanStack Creator Engineering (Port 3009)
    </div>
  </div>

</body>
</html>"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    png_path = OUTPUT_DIR / "barf_teaser_card.png"
    pdf_path = OUTPUT_DIR / "barf_teaser_card.pdf"
    twin_path = SCREENSHOTS_DIR / "barf_teaser_card.png"
    pegasus_twin = Path("/home/james/stacklabs/screenshots/pegasus_visual_twin_WO0010172_teaser.png")

    print("[*] Launching Playwright to render teaser card...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page(
            viewport={"width": 1200, "height": 1650},
            device_scale_factor=2
        )
        await page.set_content(html_content, wait_until="networkidle")

        # Capture PNG
        await page.screenshot(path=str(png_path), full_page=True)
        await page.screenshot(path=str(twin_path), full_page=True)
        await page.screenshot(path=str(pegasus_twin), full_page=True)
        print(f"✔ Saved Teaser Card PNG to: {png_path}")
        print(f"✔ Saved Twin PNG to: {twin_path}")

        # Capture PDF
        await page.pdf(
            path=str(pdf_path),
            width="1200px",
            height="1650px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        print(f"✔ Saved Teaser Card PDF to: {pdf_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(render())
