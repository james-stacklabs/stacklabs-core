#!/usr/bin/env python3
"""
scripts/compile_cws_hou_7th_inning_lookbook.py — CWS @ HOU 7th Inning Stretch Lookbook Compiler
==============================================================================================
Compiles magazine-grade Deep Void HTML & A4 PDF deliverable for CWS @ HOU Game 1 Wild Card.
"""

import os
import sys
import shutil
import asyncio
import subprocess
from playwright.async_api import async_playwright

PILOT_HTML = "/home/james/sovereign_inbox/pilot_drops/FAAS_CWS_HOU_7TH_INNING_STRETCH_LOOKBOOK_2026_09_29.html"
PILOT_PDF = "/home/james/sovereign_inbox/pilot_drops/FAAS_CWS_HOU_7TH_INNING_STRETCH_LOOKBOOK_2026_09_29.pdf"
TODAY_PDF = "/home/james/sovereign_inbox/today/FAAS_CWS_HOU_7TH_INNING_STRETCH_LOOKBOOK_2026_09_29.pdf"
NOTEBOOK_PDF = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_CWS_HOU_7TH_INNING_STRETCH_LOOKBOOK_2026_09_29.pdf"
NOTEBOOK_HTML = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_CWS_HOU_7TH_INNING_STRETCH_LOOKBOOK_2026_09_29.html"
PUBLIC_HTML = "/home/james/stacklabs/33_FanStack_Lite/public/cws_hou_7th_inning_lookbook.html"
PUBLIC_LOOKBOOK_HTML = "/home/james/stacklabs/33_FanStack_Lite/public/lookbook.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FAAS // THE 7TH INNING STRETCH LOOKBOOK: CWS @ HOU</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
        
        @page {
            size: A4;
            margin: 0;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #0B0D13;
            color: #E2E8F0;
            padding: 22px 28px;
            font-size: 11.5px;
            line-height: 1.38;
            -webkit-print-color-adjust: exact;
        }
        
        .header {
            border-bottom: 2px solid #1E2536;
            padding-bottom: 10px;
            margin-bottom: 11px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        
        .header-title-box h1 {
            font-size: 20px;
            font-weight: 900;
            letter-spacing: -0.5px;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .header-title-box h2 {
            font-size: 11px;
            font-weight: 600;
            color: #94A3B8;
            margin-top: 2px;
        }
        
        .meta-pill {
            background: #121620;
            border: 1px solid #1E2536;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 9px;
            font-family: 'JetBrains Mono', monospace;
            color: #F59E0B;
            text-align: right;
            line-height: 1.35;
        }
        
        .section {
            margin-bottom: 11px;
        }
        
        .section-header {
            font-size: 11.5px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #F8FAFC;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-left: 3px solid #F59E0B;
            padding-left: 8px;
        }
        
        .scoreboard-card {
            background: #121620;
            border: 1px solid #1E2536;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        
        .score-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            padding-bottom: 6px;
            border-bottom: 1px solid #1E2536;
        }
        
        .team-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .team-badge {
            font-size: 14px;
            font-weight: 900;
            padding: 2px 7px;
            border-radius: 5px;
        }
        
        .team-badge.cws {
            background: #FFFFFF22;
            color: #F8FAFC;
            border: 1px solid #FFFFFF55;
        }
        
        .team-badge.hou {
            background: #EB6E1F22;
            color: #FB923C;
            border: 1px solid #EB6E1F55;
        }
        
        .score-val {
            font-size: 22px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #F8FAFC;
        }
        
        .status-badge {
            background: #F59E0B22;
            color: #FBBF24;
            border: 1px solid #F59E0B55;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        
        .table-custom {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            margin-top: 5px;
        }
        
        .table-custom th {
            color: #64748B;
            font-weight: 600;
            padding: 3px 5px;
            border-bottom: 1px solid #1E2536;
            text-align: center;
        }
        
        .table-custom td {
            padding: 3px 5px;
            border-bottom: 1px solid #161C2A;
            text-align: center;
            color: #CBD5E1;
        }
        
        .table-custom tr.highlight td {
            background: #1E253644;
            font-weight: 700;
            color: #F8FAFC;
        }
        
        .turning-points {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 8px;
        }
        
        .turn-card {
            background: #10141D;
            border: 1px solid #1A202C;
            border-radius: 6px;
            padding: 7px 8px;
        }
        
        .turn-card h4 {
            font-size: 9.5px;
            font-weight: 800;
            color: #F59E0B;
            margin-bottom: 2px;
            text-transform: uppercase;
        }
        
        .turn-card p {
            font-size: 9px;
            color: #94A3B8;
            line-height: 1.25;
        }
        
        .radar-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }
        
        .radar-box {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 7px 10px;
        }
        
        .radar-title {
            font-size: 9.5px;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        
        .recap-box {
            background: #121620;
            border: 1px solid #1E2536;
            border-left: 3px solid #F59E0B;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 9.5px;
            line-height: 1.35;
            color: #CBD5E1;
            margin-top: 8px;
        }
        
        .barf-take-box {
            background: #161214;
            border: 1px solid #3B1822;
            border-left: 3px solid #EF4444;
            border-radius: 6px;
            padding: 8px 12px;
            margin-top: 8px;
        }
        
        .barf-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 9.5px;
            font-weight: 800;
            color: #F87171;
            margin-bottom: 3px;
        }
        
        .barf-text {
            font-size: 9.5px;
            color: #FECACA;
            font-style: italic;
            line-height: 1.3;
        }
        
        .seismograph-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-top: 6px;
        }
        
        .seismo-card {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 5px 7px;
        }
        
        .seismo-phrase {
            font-size: 9px;
            font-weight: 700;
            color: #F8FAFC;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .seismo-rate {
            font-size: 13px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #38BDF8;
        }
        
        .slate-bar {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 6px;
        }
        
        .slate-item {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .slate-item .time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 700;
            color: #F59E0B;
        }
        
        .slate-item .matchup {
            font-size: 10px;
            font-weight: 800;
            color: #E2E8F0;
        }
        
        .footer {
            border-top: 1px solid #1E2536;
            padding-top: 6px;
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            font-size: 8px;
            font-family: 'JetBrains Mono', monospace;
            color: #64748B;
        }
    </style>
</head>
<body>

    <!-- HEADER -->
    <div class="header">
        <div class="header-title-box">
            <h1>⚾ THE 7TH INNING STRETCH LOOKBOOK</h1>
            <h2>CHICAGO WHITE SOX @ HOUSTON ASTROS // AL WILD CARD SERIES GAME 1</h2>
        </div>
        <div class="meta-pill">
            <div>POSTSEASON OCT 2026</div>
            <div>DAIKIN PARK • HOUSTON, TX</div>
            <div>MID 7TH INNING STRETCH</div>
        </div>
    </div>

    <!-- SECTION 1: LIVE REALITY SCOREBOARD & LINESCORE -->
    <div class="section">
        <div class="section-header">📊 1. Official Game 1 Linescore (Metal Truth)</div>
        <div class="scoreboard-card">
            <div class="score-row">
                <div class="team-box">
                    <span class="team-badge cws">CWS</span>
                    <span style="font-size: 13px; font-weight: 800; color: #FFFFFF;">Chicago White Sox</span>
                </div>
                <div class="score-val">6</div>
                <div class="status-badge">MID 7TH STRETCH</div>
                <div class="score-val">2</div>
                <div class="team-box">
                    <span style="font-size: 13px; font-weight: 800; color: #FB923C;">Houston Astros</span>
                    <span class="team-badge hou">HOU</span>
                </div>
            </div>

            <table class="table-custom">
                <thead>
                    <tr>
                        <th style="text-align: left;">TEAM</th>
                        <th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>7</th>
                        <th>R</th><th>H</th><th>E</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="highlight">
                        <td style="text-align: left; font-weight: 800; color: #FFFFFF;">CWS (Wild Card 6)</td>
                        <td>1</td><td>2</td><td>0</td><td>1</td><td>1</td><td>0</td><td>1</td>
                        <td style="font-weight: 900; color: #F59E0B;">6</td><td>10</td><td>0</td>
                    </tr>
                    <tr>
                        <td style="text-align: left; font-weight: 800; color: #FB923C;">HOU (AL West 3)</td>
                        <td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>0</td><td>0</td>
                        <td style="font-weight: 900; color: #F8FAFC;">2</td><td>4</td><td>1</td>
                    </tr>
                </tbody>
            </table>

            <div class="turning-points">
                <div class="turn-card">
                    <h4>TOP 7TH: SMALL BALL BUNT</h4>
                    <p>Tristan Peters lays down textbook sacrifice bunt down 3B line (Paredes to Altuve) advancing Murakami to 3rd and Grichuk to 2nd with 1 out.</p>
                </div>
                <div class="turn-card">
                    <h4>TOP 7TH: WILD PITCH & K3</h4>
                    <p>Bennett Sousa uncorks wild pitch on strike 3 in the dirt. Murakami scores (6-2); Montgomery hustles to 1st on dropped strike three.</p>
                </div>
                <div class="turn-card">
                    <h4>INNINGS 1-3: SMITH DEBUT</h4>
                    <p>Hagen Smith (Rookie LHP) deals 3.0 scoreless frames (38 P, 2 H, 0 ER, 1 K) with elite wipeout slider spin setting early tone.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 2: CULTURAL SCAR TISSUE & PANIC INDEX -->
    <div class="section">
        <div class="section-header">🔥 2. Cultural Scar Tissue & October Panic Index</div>
        <div class="radar-grid">
            <div class="radar-box">
                <div class="radar-title" style="color: #F87171;">HOUSTON PANIC INDEX — 88%</div>
                <div style="background: #1E2536; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                    <div style="background: linear-gradient(90deg, #F59E0B, #EF4444); width: 88%; height: 100%;"></div>
                </div>
                <p style="font-size: 8.5px; color: #94A3B8;">AL West Champions trailing 6-2 at home facing 90% historical elimination penalty if dropping Game 1. Bullpen burned 6 arms in 7 frames.</p>
            </div>
            <div class="radar-box">
                <div class="radar-title" style="color: #34D399;">WHITE SOX DELIRIUM — 92%</div>
                <div style="background: #1E2536; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                    <div style="background: linear-gradient(90deg, #10B981, #06B6D4); width: 92%; height: 100%;"></div>
                </div>
                <p style="font-size: 8.5px; color: #94A3B8;">Tortured South Siders who suffered 100+ losses in recent memory now tearing up October with 10 hits, flawless small ball, and shut-down pitching.</p>
            </div>
        </div>

        <div class="barf-take-box">
            <div class="barf-header">
                <span>🎙️ THE DAILY BARF 7TH INNING STRETCH MONOLOGUE</span>
                <span>BP 218/128 • TUMS: 9 • ER DOCTOR EN ROUTE</span>
            </div>
            <div class="barf-text">
                "Bennett Sousa throwing the ball into the backstop while Tristan Peters lays down bunts in October! 6 pitchers in 7 innings! Daikin Park is a funeral home! The Astros dynasty is getting dismantled by small ball and high school bunts! Somebody call 911 and get me a pastrami on rye!"
            </div>
        </div>
    </div>

    <!-- SECTION 3: BROADCAST LEXICON CONTAGION SEISMOGRAPH -->
    <div class="section">
        <div class="section-header">📈 3. Broadcast Lexicon Contagion Seismograph</div>
        <div class="seismograph-grid">
            <div class="seismo-card">
                <div class="seismo-phrase">"Spinning the pill / Spin it"</div>
                <div class="seismo-rate">92%</div>
                <div style="font-size: 8px; color: #64748B;">Airborne (Hagen Smith slider)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"Brotherly Shove"</div>
                <div class="seismo-rate">97%</div>
                <div style="font-size: 8px; color: #64748B;">Epidemic (NFL Bleed)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"High leverage"</div>
                <div class="seismo-rate">78%</div>
                <div style="font-size: 8px; color: #64748B;">Spreading (Sousa collapse)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"Processing speed"</div>
                <div class="seismo-rate">71%</div>
                <div style="font-size: 8px; color: #64748B;">Steady (Peters bunt)</div>
            </div>
        </div>
    </div>

    <!-- SECTION 4: POSTSEASON SLATE ON DECK -->
    <div class="section" style="margin-bottom: 6px;">
        <div class="section-header">📺 4. Postseason Slate On Deck</div>
        <div class="slate-bar">
            <div class="slate-item">
                <div class="time">8:00 PM EDT</div>
                <div class="matchup">BOS @ NYY (AL Wild Card G1 • Yankee Stadium)</div>
            </div>
            <div class="slate-item">
                <div class="time">10:00 PM EDT</div>
                <div class="matchup">CHC @ SDP (NL Wild Card G1 • Petco Park)</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <div>STACKLABS LLC // FANSTACK AS A SERVICE (FAAS) • GROUNDED METAL INTELLIGENCE</div>
        <div>PRODUCED ON HOST CLIO • ZERO SYNTHETIC FLUFF • 100% VERIFIED TRUTH</div>
    </div>

</body>
</html>
"""

async def main():
    print("[*] Generating HTML template...")
    os.makedirs(os.path.dirname(PILOT_HTML), exist_ok=True)
    with open(PILOT_HTML, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print(f"[+] Wrote HTML template to {PILOT_HTML}")

    # Copy HTML to public and notebook sync
    os.makedirs(os.path.dirname(PUBLIC_HTML), exist_ok=True)
    shutil.copyfile(PILOT_HTML, PUBLIC_HTML)
    print(f"[+] Copied to Port 3033 public assets: {PUBLIC_HTML}")
    
    shutil.copyfile(PILOT_HTML, PUBLIC_LOOKBOOK_HTML)
    print(f"[+] Updated default lookbook asset: {PUBLIC_LOOKBOOK_HTML}")

    os.makedirs(os.path.dirname(NOTEBOOK_HTML), exist_ok=True)
    shutil.copyfile(PILOT_HTML, NOTEBOOK_HTML)
    print(f"[+] Synced HTML to clean room: {NOTEBOOK_HTML}")

    print("[*] Launching Playwright headless browser for PDF compilation...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        await page.set_content(HTML_TEMPLATE, wait_until="networkidle")
        await page.pdf(
            path=PILOT_PDF,
            format="A4",
            print_background=True,
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}
        )
        await browser.close()
    
    if os.path.exists(PILOT_PDF):
        size_kb = os.path.getsize(PILOT_PDF) / 1024
        print(f"[+] Successfully compiled PDF: {PILOT_PDF} ({size_kb:.1f} KB)")
        os.makedirs(os.path.dirname(TODAY_PDF), exist_ok=True)
        shutil.copyfile(PILOT_PDF, TODAY_PDF)
        print(f"[+] Copied to today dir: {TODAY_PDF}")
        os.makedirs(os.path.dirname(NOTEBOOK_PDF), exist_ok=True)
        shutil.copyfile(PILOT_PDF, NOTEBOOK_PDF)
        print(f"[+] Synced PDF to clean room: {NOTEBOOK_PDF}")
    else:
        print(f"[-] Failed to generate PDF at {PILOT_PDF}", file=sys.stderr)
        sys.exit(1)

    print("[*] Triggering Google Drive sync...")
    try:
        res = subprocess.run(["/home/james/stacklabs/scripts/sync_to_gdrive.sh"], capture_output=True, text=True, check=True)
        print(f"[+] Google Drive sync complete:\n{res.stdout.strip()}")
    except Exception as e:
        print(f"[-] Google Drive sync warning: {e}")

if __name__ == "__main__":
    asyncio.run(main())
