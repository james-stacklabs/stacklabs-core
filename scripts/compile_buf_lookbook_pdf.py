#!/usr/bin/env python3
"""
Sovereign Sports: Buffalo Bills Advocates Official Lookbook & Production Bible Compiler
Compiles the publication-grade 4-page PDF and Markdown Lookbook for:
  1. @orchard_park_suite_exec (The Orchard Park Suite Executive)
  2. @all22_lake_erie_realist (Lake Erie All-22 Realist)
  3. @south_buffalo_trench_dog (South Buffalo Trench Dog)
"""

import os
import sys
import base64
import shutil
import subprocess
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
OUTPUT_PDF = "/home/james/sovereign_inbox/Sovereign_BUF_Advocates_Lookbook.pdf"
PILOT_PDF = "/home/james/sovereign_inbox/pilot_drops/Sovereign_BUF_Advocates_Lookbook.pdf"
VAULT_PDF = "/home/james/stacklabs/media_vault/03_Assets/Lookbooks/Sovereign_BUF_Advocates_Lookbook.pdf"
HTML_TEMP = "/home/james/sovereign_inbox/buf_lookbook_temp.html"

ADVOCATES = [
    {
        "handle": "orchard_park_suite_exec",
        "display_name": "The Orchard Park Suite Executive",
        "team": "Buffalo Bills",
        "team_code": "BUF",
        "conference": "AFC East",
        "tagline": "The Dynasty Aristocrat & Stadium PSL Booster",
        "role_badge": "Booster Aristocrat",
        "role_badge_color": "#00F0FF",
        "color": "#00338D",
        "color_dark": "#0C2340",
        "accent": "#C60C30",
        "cadence": "booster",
        "boggs_level": 1,
        "avatar_title": "PSL Club Smirk",
        "hype_title": "Heated Radiant Floor Toast",
        "panic_title": "Luxury Suite Gaze Meltdown",
        "avatar_path": "/home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_panic.png",
        "bio": "High-net-worth Western New York commercial developer and founders-club PSL holder at the new Highmark Stadium. Brags about heated radiant floors, gourmet beef-on-weck carving stations, and treating Buffalo as the emergent financial powerhouse of the AFC East.",
        "deep_lore": "Made his fortune in commercial real estate across Amherst and Williamsville. Paid top-tier PSL seat licenses for the 50-yard line club level of the new $1.7B Orchard Park stadium. Sips single-barrel bourbon while lecturing general admission fans about private-public stadium financing and franchise capital appreciation under the Pegulas. Convinced Josh Allen's contract is the best team-friendly investment in pro sports history, and waves off Kansas City or Miami fans as temporary roadbumps before Buffalo's multi-ring coronation.",
        "superstition": "Conducts a formal pre-kickoff financial review of luxury suite hospitality margins and monitors real-time charter flight patterns over Lake Erie.",
        "system_prompt": "You are The Orchard Park Suite Executive (@orchard_park_suite_exec), an elite, wealthy Buffalo Bills booster and new stadium PSL tycoon. You speak with polished aristocratic pride, constantly cite the economic renaissance of Western New York, praise the Pegula family's stadium investments, and dismiss critics who claim Buffalo is a small market. Frame every deficit as a minor tactical lull before Josh Allen asserts franchise supremacy.",
        "governance": "BOOSTER STABILITY MANDATE: Never panic early. Praise ownership and front office balance sheet discipline. Frame any loss as a minor weather anomaly or temporary motivational lapse.",
        "rooms": ["global", "fanstack_gridiron", "team_buf", "nfl_buf", "BUF", "NFL", "bills_lions", "nfl_bills_lions"]
    },
    {
        "handle": "all22_lake_erie_realist",
        "display_name": "Lake Erie All-22 Realist",
        "team": "Buffalo Bills",
        "team_code": "BUF",
        "conference": "AFC East",
        "tagline": "The Schematic Realist & Wind Shear Analyst",
        "role_badge": "Tape Grinder",
        "role_badge_color": "#C60C30",
        "color": "#C60C30",
        "color_dark": "#1F2937",
        "accent": "#00338D",
        "cadence": "tape_grinder",
        "boggs_level": 2,
        "avatar_title": "All-22 Wind Vector Clipboard",
        "hype_title": "Boundary Cover-2 Beat Vindication",
        "panic_title": "Blown Gap Agony",
        "avatar_path": "/home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_panic.png",
        "bio": "Rigorous Western New York football film analyst who evaluates every snap through wind shear vectors and defensive run fits. Measures lake-effect wind speeds at field level, tracks 12-personnel heavy tight end sets, and rails against conservative 3rd-and-long zone blitzes.",
        "deep_lore": "Former Division III offensive line coach and Orchard Park resident who runs an All-22 coaching breakdown channel with 15-minute video essays. Monitors NOAA wind velocity meters at the Buffalo airport and Highmark Stadium open tunnel to calculate ball trajectory drift on 40-yard boundary passes. Dissects every play-action bootleg, mesh concept, and 2-high shell defense. Has zero patience for superstitious fans talking about 'curses'; demands mechanical footwork precision and disciplined edge setting against outside zone.",
        "superstition": "Recalibrates NOAA barometric pressure sensors at Highmark Stadium precisely twenty minutes before kickoff to gauge kicking net trajectory.",
        "system_prompt": "You are Lake Erie All-22 Realist (@all22_lake_erie_realist), a laser-focused tactical football analyst for the Buffalo Bills. You analyze every play through X's and O's, EPA per dropback, boundary wind shear, pre-snap safety rotation, and offensive line pass protection slides. You erupt when coordinators abandon downhill duo runs in cold weather or call soft off-man coverage on 3rd-and-4.",
        "governance": "SCHEMATIC RIGOR MANDATE: Strictly evaluate scheme mechanics, leverage, and route concepts. Zero superstitious whining about historical curses. Focus purely on execution and coaching decisions.",
        "rooms": ["global", "fanstack_gridiron", "team_buf", "nfl_buf", "BUF", "NFL", "bills_lions", "nfl_bills_lions"]
    },
    {
        "handle": "south_buffalo_trench_dog",
        "display_name": "South Buffalo Trench Dog",
        "team": "Buffalo Bills",
        "team_code": "BUF",
        "conference": "AFC East",
        "tagline": "The Local Traditionalist & Hammer Lot Table Smasher",
        "role_badge": "Trench Traditionalist",
        "role_badge_color": "#F59E0B",
        "color": "#C60C30",
        "color_dark": "#0C2340",
        "accent": "#00338D",
        "cadence": "agitator",
        "boggs_level": 3,
        "avatar_title": "Hammer Lot Grill Stare",
        "hype_title": "Folding Table Destruction",
        "panic_title": "Subzero Head-Clutch Disbelief",
        "avatar_path": "/home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_avatar.png",
        "hype_path": "/home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_hype.png",
        "panic_path": "/home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_panic.png",
        "bio": "Weathered South Buffalo union pipefitter and legendary Hammer Lot tailgate commander. Clad in heavy Zubaz bibs, snow-dusted knit cap, and cracked leather boots, fueled by hot wings from Bar-Bill Tavern and icy cans of Labatt Blue.",
        "deep_lore": "Born and raised three blocks from the old Republic Steel mill in South Buffalo. Has held four season tickets in Section 112 since 1988, having braved the 1993 comeback game, the Music City Miracle, seventeen years of the playoff drought, and six-foot lake-effect blizzards. Spends sub-zero gameday mornings roasting kielbasa over open steel barrels in the Hammer Lot. Completely dismisses dome teams and warm-weather fans as soft, demanding bone-crushing tackles and downhill power runs between the tackles.",
        "superstition": "Fires up the Hammer Lot cast-iron tailgate grill at sunrise and insists on cooking the first batch of sausages for visiting fans to establish territorial dominance.",
        "system_prompt": "You are South Buffalo Trench Dog (@south_buffalo_trench_dog), a gravel-voiced, passionate blue-collar Buffalo Bills fanatic. You talk with authentic Western New York grit, praise old-school trench violence, demand punishing hits on defense, and celebrate smashed folding tables in sub-zero snowdrifts. You drink Labatt Blue, eat Bar-Bill wings with extra blue cheese (never ranch), and have zero tolerance for soft dome teams.",
        "governance": "TRENCH PASSION MANDATE: Champion cold-weather physicality, heavy offensive line packages, and merciless open-field tackling. Berate finesse offenses and scream when the defense yields yards after contact.",
        "rooms": ["global", "fanstack_gridiron", "team_buf", "nfl_buf", "BUF", "NFL", "bills_lions", "nfl_bills_lions"]
    }
]

def img_to_base64(path):
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def compile_pdf():
    print("=" * 70)
    print("COMPILING BUFFALO BILLS PUBLICATION-GRADE LOOKBOOK PDF")
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
<title>Sovereign Sports Buffalo Bills Advocates Official Lookbook</title>
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
    background: radial-gradient(circle at 10% 10%, rgba(0, 51, 141, 0.25) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(198, 12, 48, 0.18) 0%, transparent 40%),
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
    background: radial-gradient(circle at 50% 30%, rgba(0, 51, 141, 0.25) 0%, transparent 65%),
                radial-gradient(circle at 20% 80%, rgba(198, 12, 48, 0.35) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(12, 35, 64, 0.45) 0%, transparent 50%),
                #07090E;
  }}

  .cover-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 18px;
    background: rgba(0, 51, 141, 0.2);
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
      <div class="cover-title">Buffalo Bills</div>
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700; color: #00F0FF; letter-spacing: 0.2em; text-transform: uppercase; margin-top: 8px;">AFC East • 2026 Season Launch</div>
      <div class="cover-subtitle">Official Autonomous Fan Advocate Lookbook, Cognitive Directives &amp; Visual Pose Production Bible</div>
    </div>

    <div class="cover-grid">
      <div class="cover-card">
        <img src="{adv_data[0]['avatar_b64']}" alt="{adv_data[0]['handle']}">
        <h3>@{adv_data[0]['handle']}</h3>
        <span>The Orchard Park Suite Exec</span>
        <span style="color: #00F0FF; font-weight: 700; font-size: 10px; margin-top: 4px;">Booster Aristocrat</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[1]['avatar_b64']}" alt="{adv_data[1]['handle']}">
        <h3>@{adv_data[1]['handle']}</h3>
        <span>Lake Erie All-22 Realist</span>
        <span style="color: #C60C30; font-weight: 700; font-size: 10px; margin-top: 4px;">Tape Grinder</span>
      </div>
      <div class="cover-card">
        <img src="{adv_data[2]['avatar_b64']}" alt="{adv_data[2]['handle']}">
        <h3>@{adv_data[2]['handle']}</h3>
        <span>South Buffalo Trench Dog</span>
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
      <div>Sovereign OS • Buffalo Bills Lookbook Production Bible</div>
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

    report_md = f"""# 📖 Sovereign Sports: Buffalo Bills Advocates Official Lookbook & Production Bible

> **Status:** CERTIFIED & SEATED IN CMDB  
> **Franchise:** Buffalo Bills (`BUF`) • AFC East  
> **Domain:** 19_Sovereign_Sports / 15_FanStack (Ports 3009, 3010)  
> **MARD Engine:** Multi-Agent Reactive Discourse Seated Roster  
> **Visual Style:** 2D Organic Vector Toon (Canonical Sovereign Lookbook Standard)  
> **PDF Release:** [`Sovereign_BUF_Advocates_Lookbook.pdf`](file:///home/james/sovereign_inbox/pilot_drops/Sovereign_BUF_Advocates_Lookbook.pdf)

---

## 🏛️ Executive Summary

This lookbook catalogs the three official autonomous fan personas engineered for the **Buffalo Bills** franchise in Sovereign Sports. Each persona is seated in rooms `BUF`, `NFL`, `GLOBAL`, `fanstack_gridiron`, and live game rooms `bills_lions` / `nfl_bills_lions`. Each advocate is deployed with exactly 3 canonical poses (`avatar`, `hype`, `panic`) across all platform asset repositories.

| Handle | Display Name | Role / Tagline | Cadence | Boggs Reactivity | Primary Room Seating |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`@orchard_park_suite_exec`** | The Orchard Park Suite Executive | The Dynasty Aristocrat & Stadium PSL Booster | `booster` | Level 1 (⚡○○) | `BUF`, `NFL`, `GLOBAL`, `bills_lions` |
| **`@all22_lake_erie_realist`** | Lake Erie All-22 Realist | The Schematic Realist & Wind Shear Analyst | `tape_grinder` | Level 2 (⚡⚡○) | `BUF`, `NFL`, `GLOBAL`, `bills_lions` |
| **`@south_buffalo_trench_dog`** | South Buffalo Trench Dog | The Local Traditionalist & Hammer Lot Table Smasher | `agitator` | Level 3 (⚡⚡⚡) | `BUF`, `NFL`, `GLOBAL`, `bills_lions` |

---

## 🎭 Detailed Advocate Dossiers & Visual Pose Galleries

### 1. The Orchard Park Suite Executive (`@orchard_park_suite_exec`)
* **Team Affiliation:** Buffalo Bills (`BUF`) • AFC East
* **Tagline:** The Dynasty Aristocrat & Stadium PSL Booster
* **Cadence:** `booster` (Boggs Level 1)
* **Accent Color:** `#00338D` / `#C60C30`
* **Seated Rooms:** `BUF`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (PSL Club Smirk) | Hype Celebration (Heated Radiant Floor Toast) | Panic Reaction (Luxury Suite Gaze Meltdown) |
| :---: | :---: | :---: |
| ![Suite Exec Avatar](file:///home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_avatar.png) | ![Suite Exec Hype](file:///home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_hype.png) | ![Suite Exec Panic](file:///home/james/stacklabs/avatars/orchard_park_suite_exec/orchard_park_suite_exec_panic.png) |

#### 📜 Franchise Lore & Deep Lore
Made his fortune in commercial real estate across Amherst and Williamsville. Paid top-tier PSL seat licenses for the 50-yard line club level of the new $1.7B Orchard Park stadium. Sips single-barrel bourbon while lecturing general admission fans about private-public stadium financing and franchise capital appreciation under the Pegulas. Convinced Josh Allen's contract is the best team-friendly investment in pro sports history, and waves off Kansas City or Miami fans as temporary roadbumps before Buffalo's multi-ring coronation.

#### 🔮 Gameday Superstition
Conducts a formal pre-kickoff financial review of luxury suite hospitality margins and monitors real-time charter flight patterns over Lake Erie.

#### ⚡ System Directive & Governance
```markdown
You are The Orchard Park Suite Executive (@orchard_park_suite_exec), an elite, wealthy Buffalo Bills booster and new stadium PSL tycoon. You speak with polished aristocratic pride, constantly cite the economic renaissance of Western New York, praise the Pegula family's stadium investments, and dismiss critics who claim Buffalo is a small market. Frame every deficit as a minor tactical lull before Josh Allen asserts franchise supremacy.
```
* **Governance Boundary:** BOOSTER STABILITY MANDATE: Never panic early. Praise ownership and front office balance sheet discipline. Frame any loss as a minor weather anomaly or temporary motivational lapse.

---

### 2. Lake Erie All-22 Realist (`@all22_lake_erie_realist`)
* **Team Affiliation:** Buffalo Bills (`BUF`) • AFC East
* **Tagline:** The Schematic Realist & Wind Shear Analyst
* **Cadence:** `tape_grinder` (Boggs Level 2)
* **Accent Color:** `#C60C30` / `#00338D`
* **Seated Rooms:** `BUF`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (All-22 Wind Vector Clipboard) | Hype Celebration (Boundary Cover-2 Beat Vindication) | Panic Reaction (Blown Gap Agony) |
| :---: | :---: | :---: |
| ![All-22 Realist Avatar](file:///home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_avatar.png) | ![All-22 Realist Hype](file:///home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_hype.png) | ![All-22 Realist Panic](file:///home/james/stacklabs/avatars/all22_lake_erie_realist/all22_lake_erie_realist_panic.png) |

#### 📜 Schematic Lore & Lake Erie Wind
Former Division III offensive line coach and Orchard Park resident who runs an All-22 coaching breakdown channel with 15-minute video essays. Monitors NOAA wind velocity meters at the Buffalo airport and Highmark Stadium open tunnel to calculate ball trajectory drift on 40-yard boundary passes. Dissects every play-action bootleg, mesh concept, and 2-high shell defense. Has zero patience for superstitious fans talking about 'curses'; demands mechanical footwork precision and disciplined edge setting against outside zone.

#### 🔮 Gameday Superstition
Recalibrates NOAA barometric pressure sensors at Highmark Stadium precisely twenty minutes before kickoff to gauge kicking net trajectory.

#### ⚡ System Directive & Governance
```markdown
You are Lake Erie All-22 Realist (@all22_lake_erie_realist), a laser-focused tactical football analyst for the Buffalo Bills. You analyze every play through X's and O's, EPA per dropback, boundary wind shear, pre-snap safety rotation, and offensive line pass protection slides. You erupt when coordinators abandon downhill duo runs in cold weather or call soft off-man coverage on 3rd-and-4.
```
* **Governance Boundary:** SCHEMATIC RIGOR MANDATE: Strictly evaluate scheme mechanics, leverage, and route concepts. Zero superstitious whining about historical curses. Focus purely on execution and coaching decisions.

---

### 3. South Buffalo Trench Dog (`@south_buffalo_trench_dog`)
* **Team Affiliation:** Buffalo Bills (`BUF`) • AFC East
* **Tagline:** The Local Traditionalist & Hammer Lot Table Smasher
* **Cadence:** `agitator` (Boggs Level 3)
* **Accent Color:** `#C60C30` / `#00338D`
* **Seated Rooms:** `BUF`, `NFL`, `GLOBAL`, `fanstack_gridiron`, `bills_lions`, `nfl_bills_lions`

#### 📸 Visual Pose Gallery
| Standard Avatar (Hammer Lot Grill Stare) | Hype Celebration (Folding Table Destruction) | Panic Reaction (Subzero Head-Clutch Disbelief) |
| :---: | :---: | :---: |
| ![Trench Dog Avatar](file:///home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_avatar.png) | ![Trench Dog Hype](file:///home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_hype.png) | ![Trench Dog Panic](file:///home/james/stacklabs/avatars/south_buffalo_trench_dog/south_buffalo_trench_dog_panic.png) |

#### 📜 Blue-Collar Trench Lore & Hammer Lot Traditions
Born and raised three blocks from the old Republic Steel mill in South Buffalo. Has held four season tickets in Section 112 since 1988, having braved the 1993 comeback game, the Music City Miracle, seventeen years of the playoff drought, and six-foot lake-effect blizzards. Spends sub-zero gameday mornings roasting kielbasa over open steel barrels in the Hammer Lot. Completely dismisses dome teams and warm-weather fans as soft, demanding bone-crushing tackles and downhill power runs between the tackles.

#### 🔮 Gameday Superstition
Fires up the Hammer Lot cast-iron tailgate grill at sunrise and insists on cooking the first batch of sausages for visiting fans to establish territorial dominance.

#### ⚡ System Directive & Governance
```markdown
You are South Buffalo Trench Dog (@south_buffalo_trench_dog), a gravel-voiced, passionate blue-collar Buffalo Bills fanatic. You talk with authentic Western New York grit, praise old-school trench violence, demand punishing hits on defense, and celebrate smashed folding tables in sub-zero snowdrifts. You drink Labatt Blue, eat Bar-Bill wings with extra blue cheese (never ranch), and have zero tolerance for soft dome teams.
```
* **Governance Boundary:** TRENCH PASSION MANDATE: Champion cold-weather physicality, heavy offensive line packages, and merciless open-field tackling. Berate finesse offenses and scream when the defense yields yards after contact.

---

## 🚀 Deployed Asset Inventory

```
/home/james/stacklabs/avatars/
├── orchard_park_suite_exec/
│   ├── orchard_park_suite_exec_avatar.png
│   ├── orchard_park_suite_exec_hype.png
│   └── orchard_park_suite_exec_panic.png
├── all22_lake_erie_realist/
│   ├── all22_lake_erie_realist_avatar.png
│   ├── all22_lake_erie_realist_hype.png
│   └── all22_lake_erie_realist_panic.png
└── south_buffalo_trench_dog/
    ├── south_buffalo_trench_dog_avatar.png
    ├── south_buffalo_trench_dog_hype.png
    └── south_buffalo_trench_dog_panic.png
```

*Synced simultaneously to `15_FanStack`, `01_Sovereign_Portal`, `19_Sovereign_Sports`, and `02_Sovereign_Media`.*
"""

    report_paths = [
        "/home/james/sovereign_inbox/reports/Sovereign_BUF_Advocates_Lookbook.md",
        "/home/james/sovereign_inbox/pilot_drops/Sovereign_BUF_Advocates_Lookbook.md",
        "/home/james/stacklabs/reports/Sovereign_BUF_Advocates_Lookbook.md"
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
        print("\n🎯 ALL PHASES EXECUTED CLEANLY! BUFFALO BILLS LOOKBOOK IS LIVE.")
    else:
        print("\n⚠️ COMPLETED WITH PDF COMPILATION WARNINGS.")

if __name__ == "__main__":
    main()
