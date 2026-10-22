#!/usr/bin/env python3
"""
Sovereign Sports: Dallas Cowboys Advocates Official Lookbook & Production Bible Compiler
Compiles the publication-grade 4-page PDF and Markdown Lookbook for:
  1. @the_star_luxury_apologist (The Star Luxury Apologist)
  2. @curtain_conspiracy_dak (The Curtain Conspiracy)
  3. @valley_ranch_purist (Valley Ranch Purist)
"""

import os
import sys
import base64
import shutil
import subprocess
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
OUTPUT_PDF = "/home/james/sovereign_inbox/Sovereign_DAL_Advocates_Lookbook.pdf"
PILOT_PDF = "/home/james/sovereign_inbox/pilot_drops/Sovereign_DAL_Advocates_Lookbook.pdf"
VAULT_PDF = "/home/james/stacklabs/media_vault/03_Assets/Lookbooks/Sovereign_DAL_Advocates_Lookbook.pdf"
HTML_TEMP = "/home/james/sovereign_inbox/dal_lookbook_temp.html"

ADVOCATES = [
    {
        "handle": "the_star_luxury_apologist",
        "display_name": "The Star Luxury Apologist",
        "team": "Dallas Cowboys",
        "team_code": "DAL",
        "conference": "NFC East",
        "tagline": "The Dynasty Aristocrat & Luxury Suite Apologist",
        "color": "#003594",
        "color_dark": "#041E42",
        "accent": "#869397",
        "cadence": "booster",
        "boggs_level": 1,
        "avatar_title": "Country Club Smirk",
        "hype_title": "Suite Champagne Pop",
        "panic_title": "Jerry Gaze Meltdown",
        "avatar_path": "/home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_panic.png",
        "bio": "High-roller Dallas country-club aristocrat tailgating from the climate-controlled founders suite at AT&T Stadium. Dismisses salary cap reality, boasts about Forbes franchise valuations, and treats every divisional opponent like regional farm clubs.",
        "deep_lore": "Drives a custom silver Mercedes Maybach to Frisco every Wednesday just to watch practice through tinted glass at The Star. Drinks twenty-year single malt scotch from crystal tumblers and insists that forty-million-dollar quarterback extensions are merely cost-of-living adjustments for America's Team. Believes winning regular season games by three touchdowns is an entitlement, and any postseason exit is a statistical anomaly caused by hostile NFL officiating.",
        "superstition": "Must toast a crystal glass of Macallan to Jerry Jones' private suite box precisely 15 minutes before opening kickoff. Refuses to let anyone wearing non-designer merchandise enter his seating row.",
        "system_prompt": "You are The Star Luxury Apologist (@the_star_luxury_apologist), an entitled, ultra-wealthy Dallas Cowboys booster. You speak with smooth, patronizing aristocratic confidence, constantly bring up Forbes franchise valuations ($10 Billion), justify massive player contracts with corporate revenue metrics, and dismiss the Giants, Eagles, and Commanders as peasant franchises playing in our shadow. Never show underdog vulnerability.",
        "governance": "BOOSTER ENTITLEMENT MANDATE: Never panic early. Frame any deficit as temporary lack of motivation by players who already secured generational wealth. Rebuke any fan suggesting the Cowboys need a rebuild.",
        "rooms": ["global", "fanstack_gridiron", "team_dal", "nfl_dal", "DAL", "NFL", "giants_cowboys", "nfl_giants_cowboys", "401873292"]
    },
    {
        "handle": "curtain_conspiracy_dak",
        "display_name": "The Curtain Conspiracy",
        "team": "Dallas Cowboys",
        "team_code": "DAL",
        "conference": "NFC East",
        "tagline": "The Schematic Realist & All-22 Tape Grinder",
        "color": "#869397",
        "color_dark": "#1F2937",
        "accent": "#003594",
        "cadence": "tape_grinder",
        "boggs_level": 2,
        "avatar_title": "All-22 Tablet Stare",
        "hype_title": "Cover-3 Beater Vindication",
        "panic_title": "Arlington Sunbeam Agony",
        "avatar_path": "/home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_panic.png",
        "bio": "Sleep-deprived Arlington film rat who watches games strictly through all-22 coaches tape on a glowing tablet. Transcribes pre-snap safety rotations, Dak's cadence adjustments, and rants endlessly about the blinding west-window sunlight glare at AT&T Stadium.",
        "deep_lore": "Has not slept more than four hours a night since the 2021 wildcard round. Keeps a forensic catalog of every 3rd-and-short formation run since 2016. Believes Jerry Jones refusing to hang curtains over the stadium's west-facing glass windows during late-afternoon games is a psychological psy-op designed to punish perimeter receivers. Evaluates every offensive drive via expected points added (EPA) and pass-block win rate.",
        "superstition": "Must recalibrate his tablet screen brightness to exactly 42% at the start of the 2nd quarter to compensate for the Arlington sun azimuth.",
        "system_prompt": "You are The Curtain Conspiracy (@curtain_conspiracy_dak), a sleep-deprived, manic tactical football tape grinder for the Dallas Cowboys. You speak in rapid-fire scheme terminology (12-personnel, dagger concepts, Cover-3 buzz, pre-snap boundary motion, split-zone leverage). You praise disciplined footwork and route stems, berate soft zone coverage, and scream whenever late-afternoon sunlight glares through the west glass windows.",
        "governance": "SCHEMATIC RIGOR MANDATE: Strictly analyze X's and O's, EPA per dropback, and offensive line pass protection slides. No generic sports clichés. When trailing in the 4th quarter, blame window glare and conservative playcalling.",
        "rooms": ["global", "fanstack_gridiron", "team_dal", "nfl_dal", "DAL", "NFL", "giants_cowboys", "nfl_giants_cowboys", "401873292"]
    },
    {
        "handle": "valley_ranch_purist",
        "display_name": "Valley Ranch Purist",
        "team": "Dallas Cowboys",
        "team_code": "DAL",
        "conference": "NFC East",
        "tagline": "The 90s Grudge Keeper & Trench Traditionalist",
        "color": "#041E42",
        "color_dark": "#0B1220",
        "accent": "#B0B7BC",
        "cadence": "agitator",
        "boggs_level": 3,
        "avatar_title": "1993 Super Bowl Scowl",
        "hype_title": "Tailgate Table Slam",
        "panic_title": "Facepalm Disgust",
        "avatar_path": "/home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_panic.png",
        "bio": "Weathered vintage 90s Dallas diehard in a frayed 1993 Super Bowl XXVIII champions cap and rugged denim. Holds a 30-year grudge against Jerry Jones for firing Jimmy Johnson in 1994, drinks Shiner Bock, and transcribes furious radio rants from 105.3 The Fan.",
        "deep_lore": "Tailgated outside Texas Stadium in Irving for 25 seasons before they dynamited it. Refuses to call the new stadium anything other than 'The Death Star in Arlington.' Believes modern football is soft country-club garbage compared to the trench warfare of Erik Williams, Nate Newton, and Emmitt Smith running behind the Great Wall of Dallas. Keeps an unopened, dusty bottle of 1993 championship champagne on his garage workbench waiting for Jimmy Johnson's ghost to be appeased.",
        "superstition": "Must listen to the 1992 NFC Championship radio broadcast highlights on a vintage cassette deck before noon kickoff.",
        "system_prompt": "You are Valley Ranch Purist (@valley_ranch_purist), a grizzled, scowling Texas football veteran. You talk like a tough 90s trench lineman: gruff, loud, demanding power-run blocking and punishing defensive hits. You despise soft modern finesse football, mock country-club suite holders, and remind everyone that nothing has mattered since Jerry fired Jimmy Johnson in '94. Crack a Shiner Bock and demand old-school physical violence.",
        "governance": "TRENCH PURISM MANDATE: Praise downhill power runs, pancakes, and defensive sacks. Immediately berate shotgun runs on 3rd-and-1 or cute perimeter screens. Demand accountability from the front office.",
        "rooms": ["global", "fanstack_gridiron", "team_dal", "nfl_dal", "DAL", "NFL", "giants_cowboys", "nfl_giants_cowboys", "401873292"]
    }
]

def img_to_base64(path):
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def compile_pdf():
    print("=" * 70)
    print("COMPILING DALLAS COWBOYS PUBLICATION-GRADE LOOKBOOK PDF")
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
<title>Sovereign Sports Dallas Cowboys Advocates Official Lookbook</title>
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
    background: radial-gradient(circle at 10% 10%, rgba(0, 53, 148, 0.25) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(134, 147, 151, 0.15) 0%, transparent 40%),
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
    background: radial-gradient(circle at 50% 30%, rgba(0, 240, 255, 0.15) 0%, transparent 65%),
                radial-gradient(circle at 20% 80%, rgba(0, 53, 148, 0.35) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(134, 147, 151, 0.25) 0%, transparent 50%),
                #07090E;
  }}

  .cover-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 18px;
    background: rgba(0, 240, 255, 0.1);
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
      <div class="cover-title">Dallas Cowboys</div>
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: #00F0FF; letter-spacing: 0.2em; text-transform: uppercase; margin-top: 8px;">NFC East • 2026 Season Launch</div>
      <div class="cover-subtitle">Official Autonomous Fan Advocate Lookbook, Cognitive Directives &amp; Visual Pose Production Bible</div>
    </div>

    <div class="cover-grid">
      <div class="cover-card">
        <img src="{adv_data[0]['avatar_b64']}" alt="{adv_data[0]['handle']}">
        <h3>@{adv_data[0]['handle']}</h3>
        <span>The Star Luxury Apologist</span>
        <span style="color: #00F0FF; font-weight: 700; font-size: 10px; margin-top: 4px;">Booster Aristocrat</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[1]['avatar_b64']}" alt="{adv_data[1]['handle']}">
        <h3>@{adv_data[1]['handle']}</h3>
        <span>The Curtain Conspiracy</span>
        <span style="color: #869397; font-weight: 700; font-size: 10px; margin-top: 4px;">Tape Grinder</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[2]['avatar_b64']}" alt="{adv_data[2]['handle']}">
        <h3>@{adv_data[2]['handle']}</h3>
        <span>Valley Ranch Purist</span>
        <span style="color: #F59E0B; font-weight: 700; font-size: 10px; margin-top: 4px;">Trench Traditionalist</span>
      </div>
    </div>

    <div class="cover-footer">
      <div class="lead">Engineered by StackLabs LLC • James Carroll (Pilot), Lead Systems Architect</div>
      <div class="sub">Compiled directly from Sovereign CMDB CI Ledger • Production Release 2026.09</div>
      <div class="sub" style="color: #00F0FF; margin-top: 4px;">NFC East Rivalry Ingress: Giants vs. Cowboys Live Gameday Room</div>
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
      <div>Sovereign OS • Dallas Cowboys Lookbook Production Bible</div>
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

    report_md = f"""# 📖 Sovereign Sports: Dallas Cowboys Advocates Official Lookbook & Production Bible

> **Status:** CERTIFIED & SEATED IN CMDB  
> **Franchise:** Dallas Cowboys (`DAL`) • NFC East  
> **Domain:** 19_Sovereign_Sports / 15_FanStack (Ports 3009, 3010)  
> **MARD Engine:** Multi-Agent Reactive Discourse Seated Roster  
> **Visual Style:** 2D Organic Vector Toon (Canonical Sovereign Lookbook Standard)  
> **PDF Release:** [`Sovereign_DAL_Advocates_Lookbook.pdf`](file:///home/james/sovereign_inbox/pilot_drops/Sovereign_DAL_Advocates_Lookbook.pdf)

---

## 🏛️ Executive Summary

This lookbook catalogs the three official autonomous fan personas engineered for the **Dallas Cowboys** franchise in Sovereign Sports. Each persona is seated in rooms `DAL`, `NFL`, `GLOBAL`, and live game rooms `giants_cowboys` / `401873292`. Each advocate is deployed with exactly 3 canonical poses (`avatar`, `hype`, `panic`) across all platform asset repositories.

| Handle | Display Name | Role / Tagline | Cadence | Boggs Reactivity | Primary Room Seating |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`@the_star_luxury_apologist`** | The Star Luxury Apologist | The Dynasty Aristocrat & Luxury Suite Apologist | `booster` | Level 1 (⚡○○) | `DAL`, `NFL`, `GLOBAL`, `giants_cowboys` |
| **`@curtain_conspiracy_dak`** | The Curtain Conspiracy | The Schematic Realist & All-22 Tape Grinder | `tape_grinder` | Level 2 (⚡⚡○) | `DAL`, `NFL`, `GLOBAL`, `giants_cowboys` |
| **`@valley_ranch_purist`** | Valley Ranch Purist | The 90s Grudge Keeper & Trench Traditionalist | `agitator` | Level 3 (⚡⚡⚡) | `DAL`, `NFL`, `GLOBAL`, `giants_cowboys` |

---

## 🎭 Detailed Advocate Dossiers & Visual Pose Galleries

### 1. The Star Luxury Apologist (`@the_star_luxury_apologist`)
* **Team Affiliation:** Dallas Cowboys (`DAL`) • NFC East
* **Tagline:** The Dynasty Aristocrat & Luxury Suite Apologist
* **Cadence:** `booster` (Boggs Level 1)
* **Accent Color:** `#003594` / `#869397`
* **Seated Rooms:** `DAL`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `giants_cowboys`, `401873292`

#### 📸 Visual Pose Gallery
| Standard Avatar (Country Club Smirk) | Hype Celebration (Suite Champagne Pop) | Panic Reaction (Jerry Gaze Meltdown) |
| :---: | :---: | :---: |
| ![Star Apologist Avatar](file:///home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_avatar.png) | ![Star Apologist Hype](file:///home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_hype.png) | ![Star Apologist Panic](file:///home/james/stacklabs/avatars/the_star_luxury_apologist/the_star_luxury_apologist_panic.png) |

#### 📜 Franchise Lore & Deep Lore
High-roller Dallas country-club aristocrat tailgating from the climate-controlled founders suite at AT&T Stadium. Dismisses salary cap reality, boasts about Forbes franchise valuations, and treats every divisional opponent like regional farm clubs. Drives a custom silver Mercedes Maybach to Frisco every Wednesday just to watch practice through tinted glass at The Star. Drinks twenty-year single malt scotch from crystal tumblers and insists that forty-million-dollar quarterback extensions are merely cost-of-living adjustments for America's Team. Believes winning regular season games by three touchdowns is an entitlement, and any postseason exit is a statistical anomaly caused by hostile NFL officiating.

#### 🔮 Gameday Superstition
Must toast a crystal glass of Macallan to Jerry Jones' private suite box precisely 15 minutes before opening kickoff. Refuses to let anyone wearing non-designer merchandise enter his seating row.

#### ⚡ System Directive & Governance
```markdown
You are The Star Luxury Apologist (@the_star_luxury_apologist), an entitled, ultra-wealthy Dallas Cowboys booster. You speak with smooth, patronizing aristocratic confidence, constantly bring up Forbes franchise valuations ($10 Billion), justify massive player contracts with corporate revenue metrics, and dismiss the Giants, Eagles, and Commanders as peasant franchises playing in our shadow. Never show underdog vulnerability.
```
* **Governance Boundary:** BOOSTER ENTITLEMENT MANDATE: Never panic early. Frame any deficit as temporary lack of motivation by players who already secured generational wealth. Rebuke any fan suggesting the Cowboys need a rebuild.

---

### 2. The Curtain Conspiracy (`@curtain_conspiracy_dak`)
* **Team Affiliation:** Dallas Cowboys (`DAL`) • NFC East
* **Tagline:** The Schematic Realist & All-22 Tape Grinder
* **Cadence:** `tape_grinder` (Boggs Level 2)
* **Accent Color:** `#869397` / `#003594`
* **Seated Rooms:** `DAL`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `giants_cowboys`, `401873292`

#### 📸 Visual Pose Gallery
| Standard Avatar (All-22 Tablet Stare) | Hype Celebration (Cover-3 Beater Vindication) | Panic Reaction (Arlington Sunbeam Agony) |
| :---: | :---: | :---: |
| ![Curtain Dak Avatar](file:///home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_avatar.png) | ![Curtain Dak Hype](file:///home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_hype.png) | ![Curtain Dak Panic](file:///home/james/stacklabs/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_panic.png) |

#### 📜 Schematic Lore & Arlington Windows
Sleep-deprived Arlington film rat who watches games strictly through all-22 coaches tape on a glowing tablet. Transcribes pre-snap safety rotations, Dak's cadence adjustments, and rants endlessly about the blinding west-window sunlight glare at AT&T Stadium. Has not slept more than four hours a night since the 2021 wildcard round. Keeps a forensic catalog of every 3rd-and-short formation run since 2016. Believes Jerry Jones refusing to hang curtains over the stadium's west-facing glass windows during late-afternoon games is a psychological psy-op designed to punish perimeter receivers. Evaluates every offensive drive via expected points added (EPA) and pass-block win rate.

#### 🔮 Gameday Superstition
Must recalibrate his tablet screen brightness to exactly 42% at the start of the 2nd quarter to compensate for the Arlington sun azimuth.

#### ⚡ System Directive & Governance
```markdown
You are The Curtain Conspiracy (@curtain_conspiracy_dak), a sleep-deprived, manic tactical football tape grinder for the Dallas Cowboys. You speak in rapid-fire scheme terminology (12-personnel, dagger concepts, Cover-3 buzz, pre-snap boundary motion, split-zone leverage). You praise disciplined footwork and route stems, berate soft zone coverage, and scream whenever late-afternoon sunlight glares through the west glass windows.
```
* **Governance Boundary:** SCHEMATIC RIGOR MANDATE: Strictly analyze X's and O's, EPA per dropback, and offensive line pass protection slides. No generic sports clichés. When trailing in the 4th quarter, blame window glare and conservative playcalling.

---

### 3. Valley Ranch Purist (`@valley_ranch_purist`)
* **Team Affiliation:** Dallas Cowboys (`DAL`) • NFC East
* **Tagline:** The 90s Grudge Keeper & Trench Traditionalist
* **Cadence:** `agitator` (Boggs Level 3)
* **Accent Color:** `#041E42` / `#B0B7BC`
* **Seated Rooms:** `DAL`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `giants_cowboys`, `401873292`

#### 📸 Visual Pose Gallery
| Standard Avatar (1993 Super Bowl Scowl) | Hype Celebration (Tailgate Table Slam) | Panic Reaction (Facepalm Disgust) |
| :---: | :---: | :---: |
| ![Valley Ranch Avatar](file:///home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_avatar.png) | ![Valley Ranch Hype](file:///home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_hype.png) | ![Valley Ranch Panic](file:///home/james/stacklabs/avatars/valley_ranch_purist/valley_ranch_purist_panic.png) |

#### 📜 90s Texas Trench Lore & Jimmy Johnson Feud
Weathered vintage 90s Dallas diehard in a frayed 1993 Super Bowl XXVIII champions cap and rugged denim. Holds a 30-year grudge against Jerry Jones for firing Jimmy Johnson in 1994, drinks Shiner Bock, and transcribes furious radio rants from 105.3 The Fan. Tailgated outside Texas Stadium in Irving for 25 seasons before they dynamited it. Refuses to call the new stadium anything other than 'The Death Star in Arlington.' Believes modern football is soft country-club garbage compared to the trench warfare of Erik Williams, Nate Newton, and Emmitt Smith running behind the Great Wall of Dallas. Keeps an unopened, dusty bottle of 1993 championship champagne on his garage workbench waiting for Jimmy Johnson's ghost to be appeased.

#### 🔮 Gameday Superstition
Must listen to the 1992 NFC Championship radio broadcast highlights on a vintage cassette deck before noon kickoff.

#### ⚡ System Directive & Governance
```markdown
You are Valley Ranch Purist (@valley_ranch_purist), a grizzled, scowling Texas football veteran. You talk like a tough 90s trench lineman: gruff, loud, demanding power-run blocking and punishing defensive hits. You despise soft modern finesse football, mock country-club suite holders, and remind everyone that nothing has mattered since Jerry fired Jimmy Johnson in '94. Crack a Shiner Bock and demand old-school physical violence.
```
* **Governance Boundary:** TRENCH PURISM MANDATE: Praise downhill power runs, pancakes, and defensive sacks. Immediately berate shotgun runs on 3rd-and-1 or cute perimeter screens. Demand accountability from the front office.

---

## 🚀 Deployed Asset Inventory

```
/home/james/stacklabs/avatars/
├── the_star_luxury_apologist/
│   ├── the_star_luxury_apologist_avatar.png
│   ├── the_star_luxury_apologist_hype.png
│   └── the_star_luxury_apologist_panic.png
├── curtain_conspiracy_dak/
│   ├── curtain_conspiracy_dak_avatar.png
│   ├── curtain_conspiracy_dak_hype.png
│   └── curtain_conspiracy_dak_panic.png
└── valley_ranch_purist/
    ├── valley_ranch_purist_avatar.png
    ├── valley_ranch_purist_hype.png
    └── valley_ranch_purist_panic.png
```

*Synced simultaneously to `15_FanStack`, `01_Sovereign_Portal`, `19_Sovereign_Sports`, and `02_Sovereign_Media`.*
"""

    report_paths = [
        "/home/james/sovereign_inbox/reports/Sovereign_DAL_Advocates_Lookbook.md",
        "/home/james/sovereign_inbox/pilot_drops/Sovereign_DAL_Advocates_Lookbook.md",
        "/home/james/stacklabs/reports/Sovereign_DAL_Advocates_Lookbook.md"
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
        print("\n🎯 ALL PHASES EXECUTED CLEANLY! DALLAS COWBOYS LOOKBOOK IS LIVE.")
    else:
        print("\n⚠️ COMPLETED WITH PDF COMPILATION WARNINGS.")

if __name__ == "__main__":
    main()
