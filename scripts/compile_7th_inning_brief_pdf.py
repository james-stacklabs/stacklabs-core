#!/usr/bin/env python3
"""
scripts/compile_7th_inning_brief_pdf.py — Automated 7th Inning Stretch PDF Compiler
==================================================================================
Compiles FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.md into a magazine-grade
Deep Void PDF deliverable using headless Playwright.
"""

import os
import sys
import shutil
import asyncio
import subprocess
from playwright.async_api import async_playwright

HTML_PATH = "/home/james/sovereign_inbox/pilot_drops/FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.html"
PDF_PATH = "/home/james/sovereign_inbox/pilot_drops/FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.pdf"
TODAY_PDF_PATH = "/home/james/sovereign_inbox/today/FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.pdf"
NOTEBOOK_PDF_PATH = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.pdf"
NOTEBOOK_HTML_PATH = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_7TH_INNING_STRETCH_INTEL_BRIEF_2026_09_29.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FAAS // THE 7TH INNING STRETCH INTEL BRIEF</title>
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
            color: #38BDF8;
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
            border-left: 3px solid #38BDF8;
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
        
        .team-badge.phi {
            background: #E8182822;
            color: #F87171;
            border: 1px solid #E8182855;
        }
        
        .team-badge.atl {
            background: #13274F44;
            color: #60A5FA;
            border: 1px solid #3B82F655;
        }
        
        .score-val {
            font-size: 22px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #F8FAFC;
        }
        
        .status-badge {
            background: #10B98122;
            color: #34D399;
            border: 1px solid #10B98155;
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
            color: #38BDF8;
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
            border-left: 3px solid #818CF8;
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 8px;
        }
        
        .recap-item {
            margin-bottom: 5px;
            font-size: 10.5px;
            color: #CBD5E1;
            line-height: 1.32;
        }
        
        .recap-item:last-child {
            margin-bottom: 0;
        }
        
        .recap-item strong {
            color: #F8FAFC;
        }
        
        .sauron-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .sauron-col h3 {
            font-size: 9.5px;
            font-weight: 800;
            color: #A855F7;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .quote-card {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 5px 8px;
            margin-bottom: 5px;
        }
        
        .quote-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2px;
        }
        
        .quote-time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 8.5px;
            color: #38BDF8;
            font-weight: 700;
        }
        
        .quote-author {
            font-size: 9px;
            font-weight: 700;
            color: #F8FAFC;
        }
        
        .quote-body {
            font-size: 9px;
            color: #94A3B8;
            font-style: italic;
            line-height: 1.2;
        }
        
        .footer {
            margin-top: 10px;
            border-top: 1px solid #1E2536;
            padding-top: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8.5px;
            color: #64748B;
        }
        
        .slate-bar {
            display: flex;
            gap: 8px;
            margin-top: 5px;
        }
        
        .slate-item {
            flex: 1;
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 5px 6px;
            font-size: 9px;
            text-align: center;
        }
        .slate-item .time {
            color: #38BDF8;
            font-weight: 700;
            font-size: 8.5px;
            font-family: 'JetBrains Mono', monospace;
        }
        .slate-item .matchup {
            color: #F8FAFC;
            font-weight: 600;
            margin-top: 1px;
        }
    </style>
</head>
<body>

    <div class="header">
        <div class="header-title-box">
            <h1>⚾ FAAS // THE 7TH INNING STRETCH</h1>
            <h2>Dual-Vector Intelligence: McAfee Broadcast Ground Truth + Live NL Wild Card Ingress</h2>
        </div>
        <div class="meta-pill">
            TUE SEP 29, 2026 • 16:08 EDT<br>
            TRUIST PARK (ATLANTA, GA)
        </div>
    </div>

    <!-- SECTION 1: LIVE 7TH INNING STRETCH STATUS -->
    <div class="section">
        <div class="section-header">⚡ 1. The 7th Inning Stretch: Phillies @ Braves</div>
        <div class="scoreboard-card">
            <div class="score-row">
                <div class="team-box">
                    <div class="team-badge phi">PHI</div>
                    <div class="score-val">3</div>
                </div>
                <div>
                    <span class="status-badge">Middle 7th • Stretch Active</span>
                </div>
                <div class="team-box">
                    <div class="score-val">2</div>
                    <div class="team-badge atl">ATL</div>
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
                        <td style="text-align: left; color: #F87171; font-weight: 800;">PHI (Away)</td>
                        <td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td style="color: #34D399; font-weight: 900;">2</td>
                        <td style="font-weight: 900; color: #F8FAFC;">3</td>
                        <td>5</td><td>0</td>
                    </tr>
                    <tr>
                        <td style="text-align: left; color: #60A5FA; font-weight: 800;">ATL (Home)</td>
                        <td>0</td><td>1</td><td>0</td><td>0</td><td>0</td><td>1</td><td>-</td>
                        <td style="font-weight: 900; color: #F8FAFC;">2</td>
                        <td>5</td><td>0</td>
                    </tr>
                </tbody>
            </table>

            <div class="turning-points">
                <div class="turn-card">
                    <h4>Sale Masterclass (6.0 IP, 8 K)</h4>
                    <p>Chris Sale threw 84 pitches of pure filth, keeping Phillies hitters guessing with high-90s fastballs and wipeout sliders.</p>
                </div>
                <div class="turn-card">
                    <h4>Albies Go-Ahead Triple (Bot 6)</h4>
                    <p>After Harris singled, Ozzie Albies drilled a 2-out RBI triple to deep center off McFarlane to break the 1-1 deadlock.</p>
                </div>
                <div class="turn-card" style="border: 1px solid #10B98155; background: #10B98111;">
                    <h4 style="color: #34D399;">Realmuto 2-Run Triple (Top 7)</h4>
                    <p>With 2 outs and runners on 1st & 3rd, J.T. Realmuto laced a go-ahead 2-run triple down the RF line off Didier Fuentes to seize a 3-2 lead.</p>
                </div>
            </div>

            <div class="radar-grid">
                <div class="radar-box" style="border-left: 3px solid #34D399;">
                    <div class="radar-title" style="color: #34D399;">Delaware Valley Sentiment: Rejuvenated Delirium</div>
                    <p style="font-size: 9px; color: #94A3B8;">Exactly 24 hours after Case Keenum humiliated the Eagles 27-7, Philadelphia was 6 outs from total October depression. Realmuto's swing flipped the emotional panic meter from 88% down to 35%.</p>
                </div>
                <div class="radar-box" style="border-left: 3px solid #EF4444;">
                    <div class="radar-title" style="color: #EF4444;">Truist Park Sentiment: Stunned Disbelief</div>
                    <p style="font-size: 9px; color: #94A3B8;">Truist Park fell dead silent after the bullpen surrendered Sale's lead. Braves face elimination pressure if they cannot respond against the Phillies back-end pen over the final 9 outs.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 2: THE PAT MCAFEE SHOW GROUND TRUTH -->
    <div class="section">
        <div class="section-header">🎙️ 2. The Pat McAfee Show: Broadcast Ground Truth</div>
        <div class="recap-box">
            <div class="recap-item">
                <strong>1. J.J. McCarthy Traded to NY Giants:</strong> Following Jaxson Dart's season-ending injury under HC John Harbaugh, the Giants acquired former Michigan national champion QB J.J. McCarthy from Minnesota for a 2027 5th-round pick. Ian Rapoport confirmed live on-air that Jameis Winston starts ~3 weeks while McCarthy ramps up.
            </div>
            <div class="recap-item">
                <strong>2. The "Old Firm" QB Renaissance & Rodgers Film Room:</strong> Dan Orlovsky and Tone Digs broke down tape of Aaron Rodgers' masterclass for the Pittsburgh Steelers (2-1), highlighting Mike McCarthy’s use of stacked receiver formations and bunches to defeat man coverage and feed DK Metcalf, alongside Kirk Cousins leading the 3-0 Raiders.
            </div>
            <div class="recap-item">
                <strong>3. Officiating Under Fire & Soldier Field Fallout:</strong> Pat McAfee and Darius Butler slammed game-altering referee blunders—specifically the overturned Josh Wallace end-zone interception in Rams-Broncos. The crew reviewed Case Keenum leading Chicago to a 27-7 MNF blowout over Philadelphia.
            </div>
        </div>
    </div>

    <!-- SECTION 3: THE ALL-SEEING SAURON REEL -->
    <div class="section">
        <div class="section-header">👁️ 3. The All-Seeing Sauron Reel // Top 10 Craziest Shit Said</div>
        <div class="sauron-grid">
            <div class="sauron-col">
                <h3>🎙️ Sourced from "The Progrum" (Verbatim Audio)</h3>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">Pat McAfee</span>
                        <span class="quote-time">[116:15]</span>
                    </div>
                    <div class="quote-body">"Did we see PJ Fleck literally wipe a player's blood across his own face on the sideline?! He didn't even flinch, just smeared it like war paint!"</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">Darius Butler</span>
                        <span class="quote-time">[40:23]</span>
                    </div>
                    <div class="quote-body">"Pat Bryant did a great job flopping right there. That should be a 5K fine in the NBA! The zebras ruined the best play of the week!"</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">Pat McAfee</span>
                        <span class="quote-time">[38:15]</span>
                    </div>
                    <div class="quote-body">"Josh Wallace: BOOM! Ball shows up in his lap! Minute left, nastiest interception I've ever seen... and the zebras completely stole it!"</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">Dan Orlovsky</span>
                        <span class="quote-time">[84:33]</span>
                    </div>
                    <div class="quote-body">"Tone, he threw the absolute tar out of the football yesterday. Oh my gosh, dude! Throwing out of muddy pockets into restricted space with guys in his face."</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">Tone Digs</span>
                        <span class="quote-time">[42:13]</span>
                    </div>
                    <div class="quote-body">"Baltimore goes 25 yards in 7 seconds in Rio de Janeiro, Tyler Loop bangs a 56-yarder off the uprights and hits the full Cristiano Ronaldo SIUUU!"</div>
                </div>
            </div>

            <div class="sauron-col">
                <h3>💬 Sourced from "The Bleacher Wire" (Live Chat)</h3>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">@BobMalone617</span>
                        <span class="quote-time">[13:57:17]</span>
                    </div>
                    <div class="quote-body">"Case Keenum has more rushing TDs than Saquon Barkley."</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">@porko8980</span>
                        <span class="quote-time">[12:11:33]</span>
                    </div>
                    <div class="quote-body">"This is what happens when Jalen Hurts has to play QB and not hide behind his o-line got smoked by Case Keenum."</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">@5JohnnySC</span>
                        <span class="quote-time">[13:56:52]</span>
                    </div>
                    <div class="quote-body">"Case Keenum has more TD passes than Drake Maye."</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">@uL7Weenie</span>
                        <span class="quote-time">[14:29:17]</span>
                    </div>
                    <div class="quote-body">"Refs had to be so ass to overtake the field conditions narrative."</div>
                </div>
                <div class="quote-card">
                    <div class="quote-header">
                        <span class="quote-author">@KatrinaChatRep</span>
                        <span class="quote-time">[14:23:45]</span>
                    </div>
                    <div class="quote-body">"I thought Luther Vandross died?"</div>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 4: SLATE ON DECK -->
    <div class="section" style="margin-bottom: 6px;">
        <div class="section-header">📺 4. Postseason Slate On Deck</div>
        <div class="slate-bar">
            <div class="slate-item">
                <div class="time">5:00 PM EDT</div>
                <div class="matchup">CWS @ HOU (AL Wild Card G1)</div>
            </div>
            <div class="slate-item">
                <div class="time">8:00 PM EDT</div>
                <div class="matchup">BOS @ NYY (AL Wild Card G1)</div>
            </div>
            <div class="slate-item">
                <div class="time">10:00 PM EDT</div>
                <div class="matchup">CHC @ SDP (NL Wild Card G1)</div>
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
    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print(f"[+] Wrote HTML template to {HTML_PATH}")

    # Also copy HTML to notebook sync if directory exists
    if os.path.exists(os.path.dirname(NOTEBOOK_HTML_PATH)):
        shutil.copyfile(HTML_PATH, NOTEBOOK_HTML_PATH)
        print(f"[+] Synced HTML to clean room: {NOTEBOOK_HTML_PATH}")

    print("[*] Launching Playwright headless browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        await page.set_content(HTML_TEMPLATE, wait_until="networkidle")
        await page.pdf(
            path=PDF_PATH,
            format="A4",
            print_background=True,
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}
        )
        await browser.close()
    
    if os.path.exists(PDF_PATH):
        size_kb = os.path.getsize(PDF_PATH) / 1024
        print(f"[+] Successfully compiled PDF: {PDF_PATH} ({size_kb:.1f} KB)")
        try:
            shutil.copyfile(PDF_PATH, TODAY_PDF_PATH)
            print(f"[+] Copied to today dir: {TODAY_PDF_PATH}")
        except Exception as e:
            print(f"[-] Warning: Failed to copy to today dir: {e}")

        if os.path.exists(os.path.dirname(NOTEBOOK_PDF_PATH)):
            try:
                shutil.copyfile(PDF_PATH, NOTEBOOK_PDF_PATH)
                print(f"[+] Synced PDF to clean room: {NOTEBOOK_PDF_PATH}")
            except Exception as e:
                print(f"[-] Warning: Failed to sync to clean room: {e}")
    else:
        print(f"[-] Failed to generate PDF at {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    print("[*] Triggering Google Drive sync...")
    try:
        res = subprocess.run(["/home/james/stacklabs/scripts/sync_to_gdrive.sh"], capture_output=True, text=True, check=True)
        print(f"[+] Google Drive sync complete:\n{res.stdout.strip()}")
    except Exception as e:
        print(f"[-] Google Drive sync warning: {e}")

if __name__ == "__main__":
    asyncio.run(main())
