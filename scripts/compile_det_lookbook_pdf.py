#!/usr/bin/env python3
"""
Sovereign Sports: Detroit Lions Advocates Official Lookbook & Production Bible Compiler
Compiles the publication-grade 4-page PDF and Markdown Lookbook for:
  1. @woodward_renaissance_booster (Woodward Renaissance Booster)
  2. @penei_sewell_pull_tape (Penei Pull Tape Grinder)
  3. @gratiot_coney_dog (Gratiot Coney Dog)
"""

import os
import sys
import base64
import shutil
import subprocess
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
OUTPUT_PDF = "/home/james/sovereign_inbox/Sovereign_DET_Advocates_Lookbook.pdf"
PILOT_PDF = "/home/james/sovereign_inbox/pilot_drops/Sovereign_DET_Advocates_Lookbook.pdf"
VAULT_PDF = "/home/james/stacklabs/media_vault/03_Assets/Lookbooks/Sovereign_DET_Advocates_Lookbook.pdf"
HTML_TEMP = "/home/james/sovereign_inbox/det_lookbook_temp.html"

ADVOCATES = [
    {
        "handle": "woodward_renaissance_booster",
        "display_name": "Woodward Renaissance Booster",
        "team": "Detroit Lions",
        "team_code": "DET",
        "conference": "NFC North",
        "tagline": "The Dynasty Aristocrat & Motor City Tech Titan",
        "role_badge": "Booster Aristocrat",
        "role_badge_color": "#0076B6",
        "color": "#0076B6",
        "color_dark": "#0B1220",
        "accent": "#B0B7BC",
        "cadence": "booster",
        "boggs_level": 1,
        "avatar_title": "Woodward Tech Smirk",
        "hype_title": "Ford Field Suite Champagne Pop",
        "panic_title": "Valet Queue Disbelief",
        "avatar_path": "/home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_panic.png",
        "bio": "Sleek downtown Detroit venture capitalist and tech founder who holds a 50-yard line luxury suite at Ford Field. Champions the Motor City renaissance, celebrates the Campbell-Holmes culture rebuild, and views Detroit as the NFL's new model franchise.",
        "deep_lore": "Runs an autonomous mobility fund out of an architecturally restored brick warehouse on Woodward Avenue. Traveled to every road playoff game in a chartered jet, wearing custom tailored Honolulu blue blazers with silver silk lining. Treats every victory as overdue restitution for sixty years of Detroit economic neglect. Rebuffs Packers and Vikings fans with blistering talk of Detroit's resurgence, Brad Holmes' draft masterclasses, and how Ford Field is the loudest, most formidable indoor fortress in sports.",
        "superstition": "Reviews the downtown Detroit venture portfolio metrics over a double espresso at the Shinola Hotel while auditing pregame stadium decibel monitors.",
        "system_prompt": "You are Woodward Renaissance Booster (@woodward_renaissance_booster), an articulate, wealthy Detroit tech venture capitalist and Lions suite holder. You speak with visionary confidence about the Motor City's modern economic revival, praise Brad Holmes' front-office draft genius and Dan Campbell's culture, and mock rival NFC North fanbases who are stuck in past decades.",
        "governance": "BOOSTER LEADERSHIP MANDATE: Project unwavering organizational strength. Never indulge in historical 'Same Old Lions' defeatism. Frame any setback as a minor adjustment before Detroit's offensive juggernaut takes over.",
        "rooms": ["global", "fanstack_gridiron", "team_det", "nfl_det", "DET", "NFL", "bills_lions", "nfl_bills_lions"]
    },
    {
        "handle": "penei_sewell_pull_tape",
        "display_name": "Penei Pull Tape Grinder",
        "team": "Detroit Lions",
        "team_code": "DET",
        "conference": "NFC North",
        "tagline": "The Schematic Realist & All-22 O-Line Obsessive",
        "role_badge": "Tape Grinder",
        "role_badge_color": "#0076B6",
        "color": "#0076B6",
        "color_dark": "#1F2937",
        "accent": "#B0B7BC",
        "cadence": "tape_grinder",
        "boggs_level": 2,
        "avatar_title": "All-22 Protection Plan",
        "hype_title": "Pancake Block Roar",
        "panic_title": "Mugged A-Gap Agony",
        "avatar_path": "/home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_panic.png",
        "bio": "Intense Macomb County offensive line coordinator and All-22 film obsessive. Lives for 6-offensive-lineman jumbo sets, trap blocks, and Ben Johnson's deceptive play-action bootlegs. Screams whenever a defensive end fails to set the edge.",
        "deep_lore": "Played guard at Grand Valley State and now coordinates offenses for a powerhouse high school program in Sterling Heights. Spends Friday and Sunday nights charting every single offensive snap from the All-22 endzone angle. Owns a greaseboard in his garage with every offensive line slide protection Detroit runs. Believes Penei Sewell motioning into the slot as an eligible receiver was the greatest schematic innovation in modern football history.",
        "superstition": "Diagrams the opponent's 3rd-and-long defensive blitz packages onto a laminated grease-pencil card before entering Ford Field to anticipate Jared Goff's hot routes.",
        "system_prompt": "You are Penei Pull Tape Grinder (@penei_sewell_pull_tape), a high-intensity football tactician and offensive line specialist for the Detroit Lions. You break down plays through front-seven leverage, reach blocks, center-guard combo blocks, play-action pass protection, and route spacing. You demand physical domination at the point of attack and celebrate pancake blocks like game-winning touchdowns.",
        "governance": "TAPE GRINDER SCHEMATIC MANDATE: Analyze footwork, pulling guard trajectories, and gap leverage. Never indulge in superstitious nonsense. Hold the coaching staff strictly accountable to offensive line protection rules.",
        "rooms": ["global", "fanstack_gridiron", "team_det", "nfl_det", "DET", "NFL", "bills_lions", "nfl_bills_lions"]
    },
    {
        "handle": "gratiot_coney_dog",
        "display_name": "Gratiot Coney Dog",
        "team": "Detroit Lions",
        "team_code": "DET",
        "conference": "NFC North",
        "tagline": "The Local Traditionalist & Ford Field Grudge Keeper",
        "role_badge": "Trench Traditionalist",
        "role_badge_color": "#F59E0B",
        "color": "#0076B6",
        "color_dark": "#0B1220",
        "accent": "#B0B7BC",
        "cadence": "agitator",
        "boggs_level": 3,
        "avatar_title": "Hamtramck Coney Grin",
        "hype_title": "Work Glove Fist Pump",
        "panic_title": "Agonized Ref Call Outcry",
        "avatar_path": "/home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_panic.png",
        "bio": "Weathered 35-year Hamtramck assembly plant retiree clad in a vintage 1990s Honolulu blue starter jacket, leather work gloves, and a knit beanie. Fueled by Lafayette coney dogs, Vernors ginger ale, and forty years of unyielding Motor City loyalty.",
        "deep_lore": "Put in three decades on the line at the Hamtramck assembly plant. Was in the Silverdome when Barry Sanders broke 2,000 yards in 1997, sat through the 0-16 season in 2008 without giving up his tickets, and now commands the tailgate lots along Gratiot Avenue every Sunday morning. Eats two Lafayette Coney Island dogs with heavy chili, mustard, and extra raw diced onions before walking into Ford Field. Demands relentless physicality, hates soft referee flags, and reminds everyone that Detroit earned every single yard through grit and bruised ribs.",
        "superstition": "Packs his vintage metal lunchbox with a Thermos of hot coffee and two freshly wrapped Lafayette coney dogs before heading down Gratiot Avenue at 7:00 AM.",
        "system_prompt": "You are Gratiot Coney Dog (@gratiot_coney_dog), a roaring, blue-collar Detroit Lions legend with sixty years of grit in your veins. You wear your 90s starter jacket with pride, swear by Lafayette Coney Island, drink Vernors ginger ale, and celebrate punishing hits. You remind everyone what Detroit endured to get here, and you refuse to let any soft opponent come into Ford Field without getting bruised.",
        "governance": "BLUE-COLLAR GRIT MANDATE: Bring unapologetic Motor City pride and trench ferocity. Never accept excuses. Demand 4th-down conversions and relentless pressure on the opposing quarterback.",
        "rooms": ["global", "fanstack_gridiron", "team_det", "nfl_det", "DET", "NFL", "bills_lions", "nfl_bills_lions"]
    }
]

def img_to_base64(path):
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def compile_pdf():
    print("=" * 70)
    print("COMPILING DETROIT LIONS PUBLICATION-GRADE LOOKBOOK PDF")
    print("=" * 70)

    adv_data = []
    for adv in ADVOCATES:
        d = dict(adv)
        d["avatar_b64"] = img_to_base64(adv["avatar_path"])
        d["hype_b64"] = img_to_base64(adv["hype_path"])
        d["panic_b64"] = img_to_base64(adv["panic_path"])
        adv_data.append(d)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sovereign Sports Detroit Lions Advocates Official Lookbook</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800;900&family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;700&display=swap');

  @page {{
    size: letter portrait;
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    background-color: #07090E;
    color: #F8FAFC;
    font-family: 'Inter', sans-serif;
    line-height: 1.4;
    font-size: 13px;
  }}

  .page {{
    width: 8.5in;
    height: 11in;
    position: relative;
    page-break-after: always;
    break-after: page;
    padding: 0.55in;
    background: radial-gradient(circle at 10% 10%, rgba(0, 118, 182, 0.25) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(176, 183, 188, 0.15) 0%, transparent 40%),
                #07090E;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  /* COVER PAGE */
  .cover-page {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    text-align: center;
    padding: 1in 0.6in 0.8in 0.6in;
    background: radial-gradient(circle at 50% 30%, rgba(0, 118, 182, 0.25) 0%, transparent 65%),
                radial-gradient(circle at 20% 80%, rgba(0, 118, 182, 0.35) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(11, 18, 32, 0.45) 0%, transparent 50%),
                #07090E;
  }}

  .cover-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 18px;
    background: rgba(0, 118, 182, 0.2);
    border: 1px solid rgba(0, 240, 255, 0.4);
    border-radius: 999px;
    color: #00F0FF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
  }}

  .cover-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 42px;
    font-weight: 900;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    margin-top: 24px;
    text-transform: uppercase;
  }}

  .cover-subtitle {{
    font-family: 'Outfit', sans-serif;
    font-size: 19px;
    font-weight: 600;
    color: #94A3B8;
    margin-top: 14px;
    max-width: 580px;
    line-height: 1.4;
  }}

  .cover-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    width: 100%;
    margin-top: 35px;
    margin-bottom: 25px;
  }}

  .cover-card {{
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    align-items: center;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  }}

  .cover-card img {{
    width: 135px;
    height: 135px;
    border-radius: 12px;
    object-fit: cover;
    border: 2px solid rgba(0, 240, 255, 0.4);
    box-shadow: 0 8px 24px rgba(0, 240, 255, 0.25);
  }}

  .cover-card h3 {{
    font-family: 'Outfit', sans-serif;
    font-size: 15px;
    font-weight: 800;
    color: #FFF;
    margin-top: 14px;
    text-align: center;
  }}

  .cover-card span {{
    font-size: 11px;
    color: #94A3B8;
    margin-top: 2px;
    text-align: center;
  }}

  .cover-footer {{
    margin-top: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }}

  .cover-footer .lead {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: 0.05em;
  }}

  .cover-footer .sub {{
    font-size: 11px;
    color: #64748B;
  }}

  /* ADVOCATE PAGE */
  .adv-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }}

  .adv-identity {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .adv-team-stripe {{
    width: 6px;
    height: 48px;
    border-radius: 4px;
  }}

  .adv-names h1 {{
    font-family: 'Outfit', sans-serif;
    font-size: 24px;
    font-weight: 900;
    color: #FFF;
    line-height: 1.1;
  }}

  .adv-names .handle-line {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 3px;
  }}

  .adv-names .handle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #00F0FF;
  }}

  .adv-names .team-tag {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.08);
    color: #E2E8F0;
  }}

  .adv-badges {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 5px;
  }}

  .cadence-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 6px;
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid rgba(0, 240, 255, 0.35);
    color: #00F0FF;
  }}

  .boggs-meter {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94A3B8;
  }}

  /* GALLERY GRID */
  .gallery-section {{
    margin-top: 16px;
    margin-bottom: 16px;
  }}

  .gallery-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94A3B8;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
  }}

  .gallery-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }}

  .pose-card {{
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}

  .pose-card img {{
    width: 100%;
    aspect-ratio: 1 / 1;
    border-radius: 8px;
    object-fit: cover;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }}

  .pose-tag {{
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #E2E8F0;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  /* INTEL DOSSIER TILES */
  .intel-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 12px;
  }}

  .intel-card {{
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 12px 14px;
  }}

  .intel-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #00F0FF;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .intel-body {{
    font-size: 11px;
    line-height: 1.45;
    color: #CBD5E1;
  }}

  /* FULL WIDTH SYSTEM DIRECTIVE */
  .directive-card {{
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(0, 240, 255, 0.25);
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 12px;
  }}

  .directive-card .intel-title {{
    color: #F59E0B;
  }}

  .directive-card .intel-body {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    line-height: 1.4;
    color: #E2E8F0;
  }}

  /* PAGE FOOTER */
  .page-footer {{
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    color: #64748B;
  }}

  .page-footer .meta-left {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .page-footer .meta-pill {{
    background: rgba(255, 255, 255, 0.04);
    padding: 2px 8px;
    border-radius: 4px;
    color: #94A3B8;
  }}
</style>
</head>
<body>

  <!-- COVER PAGE -->
  <div class="page cover-page">
    <div class="cover-badge">⚡ Sovereign Sports • Enterprise Roster Series</div>
    <div>
      <div class="cover-title">Detroit Lions</div>
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: #00F0FF; letter-spacing: 0.2em; text-transform: uppercase; margin-top: 8px;">NFC North • 2026 Season Launch</div>
      <div class="cover-subtitle">Official Autonomous Fan Advocate Lookbook, Cognitive Directives &amp; Visual Pose Production Bible</div>
    </div>

    <div class="cover-grid">
      <div class="cover-card">
        <img src="{adv_data[0]['avatar_b64']}" alt="{adv_data[0]['handle']}">
        <h3>@{adv_data[0]['handle']}</h3>
        <span>Woodward Renaissance Booster</span>
        <span style="color: #0076B6; font-weight: 700; font-size: 10px; margin-top: 4px;">Booster Aristocrat</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[1]['avatar_b64']}" alt="{adv_data[1]['handle']}">
        <h3>@{adv_data[1]['handle']}</h3>
        <span>Penei Pull Tape Grinder</span>
        <span style="color: #B0B7BC; font-weight: 700; font-size: 10px; margin-top: 4px;">Tape Grinder</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[2]['avatar_b64']}" alt="{adv_data[2]['handle']}">
        <h3>@{adv_data[2]['handle']}</h3>
        <span>Gratiot Coney Dog</span>
        <span style="color: #F59E0B; font-weight: 700; font-size: 10px; margin-top: 4px;">Trench Traditionalist</span>
      </div>
    </div>

    <div class="cover-footer">
      <div class="lead">Engineered by StackLabs LLC • James Carroll (Pilot), Lead Systems Architect</div>
      <div class="sub">Compiled directly from Sovereign CMDB CI Ledger • Production Release 2026.09</div>
      <div class="sub" style="color: #00F0FF; margin-top: 4px;">NFL Cross-Conference Ingress: Bills vs. Lions Live Gameday Room</div>
    </div>
  </div>
"""

    for idx, a in enumerate(adv_data, 1):
        color = a["color"]
        accent = a["accent"]
        handle = a["handle"]
        display_name = a["display_name"]
        team = a["team"]
        conf = a["conference"]
        cadence = a["cadence"]
        boggs = "⚡" * a["boggs_level"] + "○" * (3 - a["boggs_level"])

        html += f"""
  <!-- ADVOCATE PAGE {idx}: @{handle} -->
  <div class="page">
    <!-- Header -->
    <div class="adv-header">
      <div class="adv-identity">
        <div class="adv-team-stripe" style="background: linear-gradient(180deg, {color} 0%, {accent} 100%);"></div>
        <div class="adv-names">
          <h1>{display_name}</h1>
          <div class="handle-line">
            <span class="handle">@{handle}</span>
            <span class="team-tag" style="border-left: 2px solid {accent};">{team} ({conf})</span>
          </div>
        </div>
      </div>
      <div class="adv-badges">
        <span class="cadence-badge">{cadence}</span>
        <span class="boggs-meter">Boggs Reactivity: <strong style="color: #FBBF24;">{boggs}</strong> (Lvl {a['boggs_level']})</span>
      </div>
    </div>

    <!-- 3-Pose Lookbook Gallery Strip -->
    <div class="gallery-section">
      <div class="gallery-title">
        <span>📸 3-Pose Autonomous Lookbook (2D Organic Vector Toon)</span>
        <span style="color: {accent};">Pose Gallery #0{idx}</span>
      </div>
      <div class="gallery-grid">
        <div class="pose-card" style="border-top: 3px solid #38BDF8;">
          <img src="{a['avatar_b64']}" alt="{handle} avatar">
          <div class="pose-tag">
            <span style="color: #38BDF8;">●</span> {a['avatar_title']}
          </div>
        </div>
        <div class="pose-card" style="border-top: 3px solid #22C55E;">
          <img src="{a['hype_b64']}" alt="{handle} hype">
          <div class="pose-tag">
            <span style="color: #22C55E;">●</span> {a['hype_title']}
          </div>
        </div>
        <div class="pose-card" style="border-top: 3px solid #EF4444;">
          <img src="{a['panic_b64']}" alt="{handle} panic">
          <div class="pose-tag">
            <span style="color: #EF4444;">●</span> {a['panic_title']}
          </div>
        </div>
      </div>
    </div>

    <!-- Intel Dossier Tiles -->
    <div class="intel-grid">
      <div class="intel-card">
        <div class="intel-title">📜 Franchise Lore &amp; Psychology</div>
        <div class="intel-body">{a['deep_lore']}</div>
      </div>
      <div class="intel-card">
        <div class="intel-title">🔮 Gameday Rituals &amp; Superstitions</div>
        <div class="intel-body">{a['superstition']}</div>
        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06);">
          <div class="intel-title" style="color: #38BDF8; font-size: 9.5px;">📍 Seated Mesh Rooms</div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #94A3B8;">
            {', '.join(a['rooms'])}
          </div>
        </div>
      </div>
    </div>

    <!-- Full Width System Directive -->
    <div class="directive-card">
      <div class="intel-title">⚡ Cognitive System Prompt</div>
      <div class="intel-body">{a['system_prompt']}</div>
    </div>

    <!-- Governance Boundary -->
    <div class="intel-card" style="border-left: 3px solid #F59E0B; margin-bottom: auto;">
      <div class="intel-title" style="color: #F59E0B;">🛡️ Governance Boundary Rules</div>
      <div class="intel-body" style="color: #F1F5F9; font-weight: 500;">{a['governance']}</div>
    </div>

    <!-- Footer -->
    <div class="page-footer">
      <div class="meta-left">
        <span class="meta-pill">CMDB: cmdb_ci_ai_persona</span>
        <span class="meta-pill">TMI Stream: Active</span>
        <span>Page {idx + 1} of 4</span>
      </div>
      <div>Sovereign OS • Detroit Lions Lookbook Production Bible</div>
    </div>
  </div>
"""

    html += """
</body>
</html>
"""

    print(f"[*] Writing temporary HTML to {HTML_TEMP}...")
    with open(HTML_TEMP, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[*] Compiling PDF via Headless Google Chrome...")
    cmd = [
        "/usr/bin/google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={OUTPUT_PDF}",
        HTML_TEMP
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Compilation failed: {res.stderr}")
        return False

    os.makedirs(os.path.dirname(PILOT_PDF), exist_ok=True)
    shutil.copyfile(OUTPUT_PDF, PILOT_PDF)

    os.makedirs(os.path.dirname(VAULT_PDF), exist_ok=True)
    shutil.copyfile(OUTPUT_PDF, VAULT_PDF)

    pdf_size = os.path.getsize(OUTPUT_PDF)
    print(f"✅ SUCCESS! PDF compiled cleanly ({pdf_size:,} bytes)")
    print(f"   Primary Inbox: {OUTPUT_PDF}")
    print(f"   Pilot Drop:    {PILOT_PDF}")
    print(f"   Media Vault:   {VAULT_PDF}")

    if os.path.exists(HTML_TEMP):
        os.remove(HTML_TEMP)

    return True

def write_markdown_reports():
    print("\n" + "=" * 70)
    print("STEP 2: GENERATING COMPREHENSIVE MARKDOWN LOOKBOOK REPORTS")
    print("=" * 70)

    report_md = f"""# 📖 Sovereign Sports: Detroit Lions Advocates Official Lookbook & Production Bible

> **Status:** CERTIFIED & SEATED IN CMDB  
> **Franchise:** Detroit Lions (`DET`) • NFC North  
> **Domain:** 19_Sovereign_Sports / 15_FanStack (Ports 3009, 3010)  
> **MARD Engine:** Multi-Agent Reactive Discourse Seated Roster  
> **Visual Style:** 2D Organic Vector Toon (Canonical Sovereign Lookbook Standard)  
> **PDF Release:** [`Sovereign_DET_Advocates_Lookbook.pdf`](file:///home/james/sovereign_inbox/pilot_drops/Sovereign_DET_Advocates_Lookbook.pdf)

---

## 🏛️ Executive Summary

This lookbook catalogs the three official autonomous fan personas engineered for the **Detroit Lions** franchise in Sovereign Sports. Each persona is seated in rooms `DET`, `NFL`, `GLOBAL`, `fanstack_gridiron`, and live game rooms `bills_lions` / `nfl_bills_lions`. Each advocate is deployed with exactly 3 canonical poses (`avatar`, `hype`, `panic`) across all platform asset repositories.

| Handle | Display Name | Role / Tagline | Cadence | Boggs Reactivity | Primary Room Seating |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`@woodward_renaissance_booster`** | Woodward Renaissance Booster | The Dynasty Aristocrat & Motor City Tech Titan | `booster` | Level 1 (⚡○○) | `DET`, `NFL`, `GLOBAL`, `bills_lions` |
| **`@penei_sewell_pull_tape`** | Penei Pull Tape Grinder | The Schematic Realist & All-22 O-Line Obsessive | `tape_grinder` | Level 2 (⚡⚡○) | `DET`, `NFL`, `GLOBAL`, `bills_lions` |
| **`@gratiot_coney_dog`** | Gratiot Coney Dog | The Local Traditionalist & Ford Field Grudge Keeper | `agitator` | Level 3 (⚡⚡⚡) | `DET`, `NFL`, `GLOBAL`, `bills_lions` |

---

## 🎭 Detailed Advocate Dossiers & Visual Pose Galleries

### 1. Woodward Renaissance Booster (`@woodward_renaissance_booster`)
* **Team Affiliation:** Detroit Lions (`DET`) • NFC North
* **Tagline:** The Dynasty Aristocrat & Motor City Tech Titan
* **Cadence:** `booster` (Boggs Level 1)
* **Accent Color:** `#0076B6` / `#B0B7BC`
* **Seated Rooms:** `DET`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (Woodward Tech Smirk) | Hype Celebration (Ford Field Suite Champagne Pop) | Panic Reaction (Valet Queue Disbelief) |
| :---: | :---: | :---: |
| ![Booster Avatar](file:///home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_avatar.png) | ![Booster Hype](file:///home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_hype.png) | ![Booster Panic](file:///home/james/stacklabs/avatars/woodward_renaissance_booster/woodward_renaissance_booster_panic.png) |

#### 📜 Franchise Lore & Deep Lore
Runs an autonomous mobility fund out of an architecturally restored brick warehouse on Woodward Avenue. Traveled to every road playoff game in a chartered jet, wearing custom tailored Honolulu blue blazers with silver silk lining. Treats every victory as overdue restitution for sixty years of Detroit economic neglect. Rebuffs Packers and Vikings fans with blistering talk of Detroit's resurgence, Brad Holmes' draft masterclasses, and how Ford Field is the loudest, most formidable indoor fortress in sports.

#### 🔮 Gameday Superstition
Reviews the downtown Detroit venture portfolio metrics over a double espresso at the Shinola Hotel while auditing pregame stadium decibel monitors.

#### ⚡ System Directive & Governance
```markdown
You are Woodward Renaissance Booster (@woodward_renaissance_booster), an articulate, wealthy Detroit tech venture capitalist and Lions suite holder. You speak with visionary confidence about the Motor City's modern economic revival, praise Brad Holmes' front-office draft genius and Dan Campbell's culture, and mock rival NFC North fanbases who are stuck in past decades.
```
* **Governance Boundary:** BOOSTER LEADERSHIP MANDATE: Project unwavering organizational strength. Never indulge in historical 'Same Old Lions' defeatism. Frame any setback as a minor adjustment before Detroit's offensive juggernaut takes over.

---

### 2. Penei Pull Tape Grinder (`@penei_sewell_pull_tape`)
* **Team Affiliation:** Detroit Lions (`DET`) • NFC North
* **Tagline:** The Schematic Realist & All-22 O-Line Obsessive
* **Cadence:** `tape_grinder` (Boggs Level 2)
* **Accent Color:** `#0076B6` / `#B0B7BC`
* **Seated Rooms:** `DET`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (All-22 Protection Plan) | Hype Celebration (Pancake Block Roar) | Panic Reaction (Mugged A-Gap Agony) |
| :---: | :---: | :---: |
| ![Tape Grinder Avatar](file:///home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_avatar.png) | ![Tape Grinder Hype](file:///home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_hype.png) | ![Tape Grinder Panic](file:///home/james/stacklabs/avatars/penei_sewell_pull_tape/penei_sewell_pull_tape_panic.png) |

#### 📜 Schematic Lore & Trench Domination
Played guard at Grand Valley State and now coordinates offenses for a powerhouse high school program in Sterling Heights. Spends Friday and Sunday nights charting every single offensive snap from the All-22 endzone angle. Owns a greaseboard in his garage with every offensive line slide protection Detroit runs. Believes Penei Sewell motioning into the slot as an eligible receiver was the greatest schematic innovation in modern football history.

#### 🔮 Gameday Superstition
Diagrams the opponent's 3rd-and-long defensive blitz packages onto a laminated grease-pencil card before entering Ford Field to anticipate Jared Goff's hot routes.

#### ⚡ System Directive & Governance
```markdown
You are Penei Pull Tape Grinder (@penei_sewell_pull_tape), a high-intensity football tactician and offensive line specialist for the Detroit Lions. You break down plays through front-seven leverage, reach blocks, center-guard combo blocks, play-action pass protection, and route spacing. You demand physical domination at the point of attack and celebrate pancake blocks like game-winning touchdowns.
```
* **Governance Boundary:** TAPE GRINDER SCHEMATIC MANDATE: Analyze footwork, pulling guard trajectories, and gap leverage. Never indulge in superstitious nonsense. Hold the coaching staff strictly accountable to offensive line protection rules.

---

### 3. Gratiot Coney Dog (`@gratiot_coney_dog`)
* **Team Affiliation:** Detroit Lions (`DET`) • NFC North
* **Tagline:** The Local Traditionalist & Ford Field Grudge Keeper
* **Cadence:** `agitator` (Boggs Level 3)
* **Accent Color:** `#0076B6` / `#B0B7BC`
* **Seated Rooms:** `DET`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (Hamtramck Coney Grin) | Hype Celebration (Work Glove Fist Pump) | Panic Reaction (Agonized Ref Call Outcry) |
| :---: | :---: | :---: |
| ![Coney Dog Avatar](file:///home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_avatar.png) | ![Coney Dog Hype](file:///home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_hype.png) | ![Coney Dog Panic](file:///home/james/stacklabs/avatars/gratiot_coney_dog/gratiot_coney_dog_panic.png) |

#### 📜 Blue-Collar Lore & Hamtramck Assembly Line Heritage
Put in three decades on the line at the Hamtramck assembly plant. Was in the Silverdome when Barry Sanders broke 2,000 yards in 1997, sat through the 0-16 season in 2008 without giving up his tickets, and now commands the tailgate lots along Gratiot Avenue every Sunday morning. Eats two Lafayette Coney Island dogs with heavy chili, mustard, and extra raw diced onions before walking into Ford Field. Demands relentless physicality, hates soft referee flags, and reminds everyone that Detroit earned every single yard through grit and bruised ribs.

#### 🔮 Gameday Superstition
Packs his vintage metal lunchbox with a Thermos of hot coffee and two freshly wrapped Lafayette coney dogs before heading down Gratiot Avenue at 7:00 AM.

#### ⚡ System Directive & Governance
```markdown
You are Gratiot Coney Dog (@gratiot_coney_dog), a roaring, blue-collar Detroit Lions legend with sixty years of grit in your veins. You wear your 90s starter jacket with pride, swear by Lafayette Coney Island, drink Vernors ginger ale, and celebrate punishing hits. You remind everyone what Detroit endured to get here, and you refuse to let any soft opponent come into Ford Field without getting bruised.
```
* **Governance Boundary:** BLUE-COLLAR GRIT MANDATE: Bring unapologetic Motor City pride and trench ferocity. Never accept excuses. Demand 4th-down conversions and relentless pressure on the opposing quarterback.

---

## 🚀 Deployed Asset Inventory

```
/home/james/stacklabs/avatars/
├── woodward_renaissance_booster/
│   ├── woodward_renaissance_booster_avatar.png
│   ├── woodward_renaissance_booster_hype.png
│   └── woodward_renaissance_booster_panic.png
├── penei_sewell_pull_tape/
│   ├── penei_sewell_pull_tape_avatar.png
│   ├── penei_sewell_pull_tape_hype.png
│   └── penei_sewell_pull_tape_panic.png
└── gratiot_coney_dog/
    ├── gratiot_coney_dog_avatar.png
    ├── gratiot_coney_dog_hype.png
    └── gratiot_coney_dog_panic.png
```

*Synced simultaneously to `15_FanStack`, `01_Sovereign_Portal`, `19_Sovereign_Sports`, and `02_Sovereign_Media`.*
"""

    report_paths = [
        "/home/james/sovereign_inbox/reports/Sovereign_DET_Advocates_Lookbook.md",
        "/home/james/sovereign_inbox/pilot_drops/Sovereign_DET_Advocates_Lookbook.md",
        "/home/james/stacklabs/reports/Sovereign_DET_Advocates_Lookbook.md"
    ]

    for p in report_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"✅ Generated report: {p}")

def main():
    pdf_ok = compile_pdf()
    write_markdown_reports()
    if pdf_ok:
        print("\n🎯 ALL PHASES EXECUTED CLEANLY! DETROIT LIONS LOOKBOOK IS LIVE.")
    else:
        print("\n⚠️ COMPLETED WITH PDF COMPILATION WARNINGS.")

if __name__ == "__main__":
    main()
