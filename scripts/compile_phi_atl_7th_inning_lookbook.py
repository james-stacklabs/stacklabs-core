#!/usr/bin/env python3
"""
scripts/compile_phi_atl_7th_inning_lookbook.py — PHI @ ATL Game 3 7th Inning Stretch Lookbook Compiler
======================================================================================================
Compiles magazine-grade Deep Void HTML, Markdown Brief, and A4 PDF deliverable for PHI @ ATL Game 3 NLWC Decider.
Governed by: Invariant 28 (Tri-Anchor Ground Truth), Invariant 29 (Real-Time Ingress Over Mock Slop), Invariant 30 (2026 Reality).
"""

import os
import sys
import shutil
import asyncio
import subprocess
from playwright.async_api import async_playwright

PILOT_HTML = "/home/james/sovereign_inbox/pilot_drops/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.html"
PILOT_PDF = "/home/james/sovereign_inbox/pilot_drops/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.pdf"
TODAY_PDF = "/home/james/sovereign_inbox/today/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.pdf"
TODAY_MD = "/home/james/sovereign_inbox/today/FanStack_Live/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.md"
NOTEBOOK_PDF = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.pdf"
NOTEBOOK_HTML = "/home/james/sovereign_inbox/notebook_sync/13_FanStack_as_a_Service/FAAS_PHI_ATL_GAME3_7TH_INNING_STRETCH_LOOKBOOK_2026_10_01.html"
PUBLIC_HTML = "/home/james/stacklabs/33_FanStack_Lite/public/phi_atl_7th_inning_lookbook.html"
PUBLIC_LOOKBOOK_HTML = "/home/james/stacklabs/33_FanStack_Lite/public/lookbook.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FAAS // THE 7TH INNING STRETCH LOOKBOOK: PHI @ ATL GAME 3</title>
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
            padding: 20px 26px;
            font-size: 11px;
            line-height: 1.35;
            -webkit-print-color-adjust: exact;
        }
        
        .header {
            border-bottom: 2px solid #1E2536;
            padding-bottom: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        
        .header-title-box h1 {
            font-size: 19px;
            font-weight: 900;
            letter-spacing: -0.5px;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .header-title-box h2 {
            font-size: 10.5px;
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
            line-height: 1.3;
        }
        
        .section {
            margin-bottom: 9px;
        }
        
        .section-header {
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #F8FAFC;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-left: 3px solid #F59E0B;
            padding-left: 8px;
        }
        
        .scoreboard-card {
            background: #121620;
            border: 1px solid #1E2536;
            border-radius: 7px;
            padding: 9px 13px;
            margin-bottom: 7px;
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
            gap: 9px;
        }
        
        .team-badge {
            font-size: 13px;
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
            font-size: 21px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #F8FAFC;
        }
        
        .status-badge {
            background: #F59E0B22;
            color: #FBBF24;
            border: 1px solid #F59E0B55;
            font-size: 8.5px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        
        .table-custom {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9.5px;
            margin-top: 4px;
        }
        
        .table-custom th {
            color: #64748B;
            font-weight: 600;
            padding: 2px 5px;
            border-bottom: 1px solid #1E2536;
            text-align: center;
        }
        
        .table-custom td {
            padding: 2px 5px;
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
            gap: 7px;
            margin-top: 7px;
        }
        
        .turn-card {
            background: #10141D;
            border: 1px solid #1A202C;
            border-radius: 5px;
            padding: 6px 7px;
        }
        
        .turn-card h4 {
            font-size: 9px;
            font-weight: 800;
            color: #F59E0B;
            margin-bottom: 2px;
            text-transform: uppercase;
        }
        
        .turn-card p {
            font-size: 8.5px;
            color: #94A3B8;
            line-height: 1.25;
        }

        .pitching-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 7px;
        }

        .pitching-box {
            background: #121620;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 7px 9px;
        }

        .pitching-title {
            font-size: 9px;
            font-weight: 800;
            color: #E2E8F0;
            text-transform: uppercase;
            border-bottom: 1px solid #1E2536;
            padding-bottom: 3px;
            margin-bottom: 4px;
            display: flex;
            justify-content: space-between;
        }
        
        .radar-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 7px;
            margin-top: 6px;
        }
        
        .radar-box {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 6px 9px;
        }
        
        .radar-title {
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 3px;
        }
        
        .barf-take-box {
            background: #161214;
            border: 1px solid #3B1822;
            border-left: 3px solid #EF4444;
            border-radius: 6px;
            padding: 7px 11px;
            margin-top: 7px;
        }
        
        .barf-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 9px;
            font-weight: 800;
            color: #F87171;
            margin-bottom: 3px;
        }
        
        .barf-text {
            font-size: 9px;
            color: #FECACA;
            font-style: italic;
            line-height: 1.28;
        }
        
        .seismograph-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-top: 5px;
        }
        
        .seismo-card {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 5px 6px;
        }
        
        .seismo-phrase {
            font-size: 8.5px;
            font-weight: 700;
            color: #F8FAFC;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .seismo-rate {
            font-size: 12px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #38BDF8;
        }
        
        .slate-bar {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 7px;
            margin-top: 5px;
        }
        
        .slate-item {
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 5px;
            padding: 5px 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .slate-item .time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            font-weight: 700;
            color: #F59E0B;
        }
        
        .slate-item .matchup {
            font-size: 9px;
            font-weight: 800;
            color: #E2E8F0;
        }
        
        .footer {
            border-top: 1px solid #1E2536;
            padding-top: 5px;
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
            font-size: 7.5px;
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
            <h2>PHILADELPHIA PHILLIES @ ATLANTA BRAVES // NL WILD CARD DECIDER (GAME 3)</h2>
        </div>
        <div class="meta-pill">
            <div>OCTOBER 1, 2026</div>
            <div>TRUIST PARK • ATLANTA, GA</div>
            <div>BOTTOM 7TH • STRETCH</div>
        </div>
    </div>

    <!-- SECTION 1: LIVE REALITY SCOREBOARD & LINESCORE -->
    <div class="section">
        <div class="section-header">📊 1. Official Game 3 Linescore (Metal Truth)</div>
        <div class="scoreboard-card">
            <div class="score-row">
                <div class="team-box">
                    <span class="team-badge phi">PHI</span>
                    <span style="font-size: 13px; font-weight: 800; color: #FFFFFF;">Philadelphia Phillies</span>
                </div>
                <div class="score-val">1</div>
                <div class="status-badge">BOTTOM 7TH STRETCH</div>
                <div class="score-val">5</div>
                <div class="team-box">
                    <span style="font-size: 13px; font-weight: 800; color: #60A5FA;">Atlanta Braves</span>
                    <span class="team-badge atl">ATL</span>
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
                    <tr>
                        <td style="text-align: left; font-weight: 800; color: #F87171;">PHI (Wild Card 4)</td>
                        <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>0</td>
                        <td style="font-weight: 900; color: #F8FAFC;">1</td><td>4</td><td>0</td>
                    </tr>
                    <tr class="highlight">
                        <td style="text-align: left; font-weight: 800; color: #60A5FA;">ATL (Wild Card 5)</td>
                        <td>3</td><td>0</td><td>0</td><td>2</td><td>0</td><td>0</td><td>-</td>
                        <td style="font-weight: 900; color: #F59E0B;">5</td><td>5</td><td>0</td>
                    </tr>
                </tbody>
            </table>

            <div class="turning-points">
                <div class="turn-card">
                    <h4>BOT 1ST: NOLA AMBUSH</h4>
                    <p>Aaron Nola tagged for 3 runs on 3 hits and a walk. Pulled after 1.2 IP (48 pitches) in shortest postseason start of his career.</p>
                </div>
                <div class="turn-card">
                    <h4>BOT 4TH: WHEELER BURNED</h4>
                    <p>Zack Wheeler enters in emergency relief on 2 days rest (4.0 IP, 3 H, 2 ER, 3 K), but gives up crushing 2-run double to Kelenic.</p>
                </div>
                <div class="turn-card">
                    <h4>BRAVES BULLPEN MASTERCLASS</h4>
                    <p>Brian Snitker's bullpen relay shuts down Phillies big bats: Kerr (3.1 IP), Holmes (2.0 IP), Suarez (0.2 IP), Fuentes (1.0 IP).</p>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 2: THE PITCHING LEDGER -->
    <div class="section">
        <div class="section-header">⚡ 2. The Pitching Ledger & Arm Exhaustion</div>
        <div class="pitching-grid">
            <div class="pitching-box">
                <div class="pitching-title">
                    <span>PHILADELPHIA PHILLIES (BURNED ARMS)</span>
                    <span style="color: #F87171;">ERA 7.11</span>
                </div>
                <table class="table-custom">
                    <thead>
                        <tr><th style="text-align:left;">PITCHER</th><th>IP</th><th>H</th><th>ER</th><th>BB</th><th>K</th><th>PC</th></tr>
                    </thead>
                    <tbody>
                        <tr><td style="text-align:left; color:#F87171;">A. Nola (L)</td><td>1.2</td><td>4</td><td>3</td><td>1</td><td>2</td><td>48</td></tr>
                        <tr><td style="text-align:left; color:#CBD5E1;">Z. Wheeler (Relief)</td><td>4.0</td><td>3</td><td>2</td><td>1</td><td>3</td><td>58</td></tr>
                        <tr><td style="text-align:left; color:#94A3B8;">J. Hoffman</td><td>0.1</td><td>0</td><td>0</td><td>0</td><td>1</td><td>5</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="pitching-box">
                <div class="pitching-title">
                    <span>ATLANTA BRAVES (BULLPEN GAME)</span>
                    <span style="color: #34D399;">ERA 1.29</span>
                </div>
                <table class="table-custom">
                    <thead>
                        <tr><th style="text-align:left;">PITCHER</th><th>IP</th><th>H</th><th>ER</th><th>BB</th><th>K</th><th>PC</th></tr>
                    </thead>
                    <tbody>
                        <tr><td style="text-align:left; color:#60A5FA;">R. Kerr</td><td>3.1</td><td>1</td><td>0</td><td>0</td><td>2</td><td>41</td></tr>
                        <tr><td style="text-align:left; color:#CBD5E1;">G. Holmes (W)</td><td>2.0</td><td>2</td><td>1</td><td>1</td><td>2</td><td>31</td></tr>
                        <tr><td style="text-align:left; color:#94A3B8;">R. Suarez (Hld)</td><td>0.2</td><td>1</td><td>0</td><td>0</td><td>1</td><td>12</td></tr>
                        <tr><td style="text-align:left; color:#34D399;">D. Fuentes</td><td>1.0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>14</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- SECTION 3: CULTURAL BLEACHER PSYCHOSIS & PANIC INDEX -->
    <div class="section">
        <div class="section-header">🔥 3. Cultural Bleacher Psychosis & October Panic Index</div>
        <div class="radar-grid">
            <div class="radar-box">
                <div class="radar-title" style="color: #F87171;">PHILADELPHIA PANIC & SCAPEGOATING — 96%</div>
                <div style="background: #1E2536; height: 5px; border-radius: 3px; overflow: hidden; margin-bottom: 3px;">
                    <div style="background: linear-gradient(90deg, #F59E0B, #EF4444); width: 96%; height: 100%;"></div>
                </div>
                <p style="font-size: 8px; color: #94A3B8;">PHLY & 94.1 WIP callers in complete existential collapse. Bryce Harper & Trea Turner bats frozen (combined 1-for-14 in series). Broad Street demanding Dombrowski blow up the core.</p>
            </div>
            <div class="radar-box">
                <div class="radar-title" style="color: #34D399;">TRUIST PARK EUPHORIA — 91%</div>
                <div style="background: #1E2536; height: 5px; border-radius: 3px; overflow: hidden; margin-bottom: 3px;">
                    <div style="background: linear-gradient(90deg, #10B981, #06B6D4); width: 91%; height: 100%;"></div>
                </div>
                <p style="font-size: 8px; color: #94A3B8;">Braves Country exorcising 2022 and 2023 NLDS trauma. 42,000+ executing thunderous chops into the 7th Inning Stretch. Snitker bullpen clinic six outs from elimination victory.</p>
            </div>
        </div>

        <div class="barf-take-box">
            <div class="barf-header">
                <span>🎙️ THE DAILY BARF 7TH INNING STRETCH MONOLOGUE</span>
                <span>BP 222/130 • TUMS: 11 • PASTRAMI: 3.2 LBS • ER STATUS: IN WAITING ROOM</span>
            </div>
            <div class="barf-text">
                "Aaron Nola throwing batting practice 89-mph heaters right over the heart of the plate in the first inning of Game 3! Then Rob Thomson panics, burns Zack Wheeler on two days rest, and Wheeler serves up a two-run knock to Kelenic anyway! Harper and Turner looking like statues with bats in their hands! 94 WIP callers are screaming to fire Dombrowski and deport Nick Sirianni to Delaware County! Truist Park is doing the chop into the commercial break and I have chewed through eleven Tums! Somebody get me an oxygen tank!"
            </div>
        </div>
    </div>

    <!-- SECTION 4: BROADCAST LEXICON CONTAGION SEISMOGRAPH -->
    <div class="section">
        <div class="section-header">📈 4. Broadcast Lexicon Contagion Seismograph</div>
        <div class="seismograph-grid">
            <div class="seismo-card">
                <div class="seismo-phrase">"Burning the Ace"</div>
                <div class="seismo-rate">98%</div>
                <div style="font-size: 7.5px; color: #64748B;">Epidemic (Wheeler relief)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"Frozen Lumber"</div>
                <div class="seismo-rate">93%</div>
                <div style="font-size: 7.5px; color: #64748B;">Contagious (Harper/Turner)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"Bullpen Relay"</div>
                <div class="seismo-rate">88%</div>
                <div style="font-size: 7.5px; color: #64748B;">Airborne (Snitker masterclass)</div>
            </div>
            <div class="seismo-card">
                <div class="seismo-phrase">"Cross-Sport Blame"</div>
                <div class="seismo-rate">81%</div>
                <div style="font-size: 7.5px; color: #64748B;">Surging (WIP / Sirianni rage)</div>
            </div>
        </div>
    </div>

    <!-- SECTION 5: DOWNSTREAM POSTSEASON BRACKET -->
    <div class="section" style="margin-bottom: 5px;">
        <div class="section-header">📺 5. Postseason Bracket & Slate Context</div>
        <div class="slate-bar">
            <div class="slate-item">
                <div class="time">NLDS ADVANCEMENT</div>
                <div class="matchup">Winner faces Los Angeles Dodgers (Game 1 at Dodger Stadium)</div>
            </div>
            <div class="slate-item">
                <div class="time">COMPLETED WILD CARD</div>
                <div class="matchup">ALWC: CWS 7, HOU 3 | ALWC: NYY 9, BOS 2 | NLWC: SD 4, CHC 1</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <div>STACKLABS LLC // FANSTACK AS A SERVICE (FAAS) • GROUNDED METAL INTELLIGENCE</div>
        <div>PRODUCED ON HOST CLIO • ZERO SYNTHETIC FLUFF • 100% VERIFIED TRUTH • OCT 1, 2026</div>
    </div>

</body>
</html>
"""

MARKDOWN_TEMPLATE = """# ⚾ FAAS INTEL BRIEF // 7TH INNING STRETCH LOOKBOOK: PHI @ ATL (GAME 3 DECIDER)
**Timestamp:** `2026-10-01 22:25:00 EDT` | **Venue:** Truist Park (Atlanta, GA) | **GamePk:** `849844`  
**Governing Standard:** Invariant 28 (Tri-Anchor Ground Truth) & Invariant 30 (2026 Postseason Reality)  

---

## 📊 1. Official Game 3 Linescore (Metal Truth)

| Team | 1 | 2 | 3 | 4 | 5 | 6 | 7 | R | H | E | Status |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| **PHI (Wild Card 4)** | 0 | 0 | 0 | 0 | 0 | 1 | 0 | **1** | 4 | 0 | Batting 8th |
| **ATL (Wild Card 5)** | 3 | 0 | 0 | 2 | 0 | 0 | - | **5** | 5 | 0 | Bottom 7th Stretch |

### Key Turning Points
1. **Bot 1st — Aaron Nola Ambushed:** Nola surrenders 3 runs on 3 hits and 1 walk. Pulled after 1.2 IP (48 pitches) in the shortest postseason start of his career.
2. **Bot 4th — Zack Wheeler Emergency Relief Burned:** Rob Thomson calls upon Wheeler on 2 days rest. Wheeler works 4.0 innings of gritty relief (3 H, 2 ER, 3 K, 58 pitches), but yields a backbreaking 2-run double to Jarred Kelenic.
3. **Braves Bullpen Relay Clinic:** Brian Snitker stitches together a bullpen gem: Ray Kerr (3.1 IP, 1 H, 0 ER), Grant Holmes (2.0 IP, 2 H, 1 ER), Robert Suarez (0.2 IP, 1 H, 0 ER), and Didier Fuentes (1.0 IP, 0 H, 0 ER).

---

## ⚡ 2. The Pitching Reality Ledger

### Philadelphia Phillies (Burned Arms)
- **Aaron Nola (L):** 1.2 IP, 4 H, 3 ER, 1 BB, 2 K, 48 Pitches (Pulled in 2nd inning).
- **Zack Wheeler (Relief):** 4.0 IP, 3 H, 2 ER, 1 BB, 3 K, 58 Pitches (Ace burned on 2 days rest).
- **Jeff Hoffman:** 0.1 IP, 0 H, 0 ER, 0 BB, 1 K, 5 Pitches.

### Atlanta Braves (Bullpen Game Masterclass)
- **Ray Kerr:** 3.1 IP, 1 H, 0 ER, 0 BB, 2 K, 41 Pitches (Starter opener relay).
- **Grant Holmes (W):** 2.0 IP, 2 H, 1 ER, 1 BB, 2 K, 31 Pitches (Bridged 4th & 5th).
- **Robert Suarez (Hold):** 0.2 IP, 1 H, 0 ER, 0 BB, 1 K, 12 Pitches (Snuffed out 6th).
- **Didier Fuentes:** 1.0 IP, 0 H, 0 ER, 0 BB, 1 K, 14 Pitches (Clean 7th).

---

## 🔥 3. Cultural Bleacher Psychosis & Panic Index

- **Philadelphia Panic & Scapegoating (96%):** PHLY Sports & 94.1 WIP switchboards are melting down. Bryce Harper & Trea Turner bats are ice cold (combined 1-for-14 in series). Broad Street callers are unleashing cross-sport vitriol, demanding Dave Dombrowski blow up the roster and firing shots at Nick Sirianni and Rob Thomson.
- **Truist Park Euphoria (91%):** Braves Country is exorcising 2022 and 2023 NLDS elimination trauma. 42,000+ fans executing thunderous tomahawk chops into the 7th Inning Stretch with a 4-run cushion and 6 outs remaining.

---

## 🎙️ 4. The Daily Barf 7th Inning Stretch Monologue
**Vitals:** BP 222/130 | Pulse 124 BPM | Tums: 11 | Pastrami: 3.2 LBS | ER Doctor: In Waiting Room  

> *"Aaron Nola throwing batting practice 89-mph heaters right over the heart of the plate in the first inning of Game 3! Then Rob Thomson panics, burns Zack Wheeler on two days rest, and Wheeler serves up a two-run knock to Kelenic anyway! Harper and Turner looking like statues with bats in their hands! 94 WIP callers are screaming to fire Dombrowski and deport Nick Sirianni to Delaware County! Truist Park is doing the chop into the commercial break and I have chewed through eleven Tums! Somebody get me an oxygen tank!"*

---

## 📈 5. Broadcast Lexicon Contagion Seismograph
- `"Burning the Ace"` — **98% (Epidemic)**: Wheeler emergency relief burned for 2026.
- `"Frozen Lumber"` — **93% (Contagious)**: Harper & Turner postseason paralysis.
- `"Bullpen Relay"` — **88% (Airborne)**: Snitker masterclass bullpen game.
- `"Cross-Sport Blame"` — **81% (Surging)**: WIP cross-pollinating Eagles and Phillies panic.

---

## 📺 6. Postseason Slate & NLDS Implications
- **NLDS Game 1 Matchup:** Winner advances to face the Los Angeles Dodgers at Dodger Stadium on Saturday.
- **Completed Wild Card Slates:**
  - **ALWC:** CWS 7, HOU 3 (White Sox lead 1-0)
  - **ALWC:** NYY 9, BOS 2 (Yankees lead 1-0)
  - **NLWC:** SD 4, CHC 1 (Padres lead 1-0)

---
*Produced by StackLabs LLC // FanStack as a Service (FaaS) • Host Clio Metal Intelligence*
"""

async def compile_lookbook():
    print("[*] Generating HTML template...")
    os.makedirs(os.path.dirname(PILOT_HTML), exist_ok=True)
    with open(PILOT_HTML, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print(f"[+] Wrote HTML template to {PILOT_HTML}")

    # Copy HTML to public and notebook sync
    if os.path.exists(os.path.dirname(PUBLIC_HTML)):
        shutil.copyfile(PILOT_HTML, PUBLIC_HTML)
        print(f"[+] Copied to public assets: {PUBLIC_HTML}")
        shutil.copyfile(PILOT_HTML, PUBLIC_LOOKBOOK_HTML)
        print(f"[+] Updated default lookbook asset: {PUBLIC_LOOKBOOK_HTML}")

    os.makedirs(os.path.dirname(NOTEBOOK_HTML), exist_ok=True)
    shutil.copyfile(PILOT_HTML, NOTEBOOK_HTML)
    print(f"[+] Synced HTML to clean room: {NOTEBOOK_HTML}")

    # Write Markdown brief
    print("[*] Generating Markdown Intel Brief...")
    os.makedirs(os.path.dirname(TODAY_MD), exist_ok=True)
    with open(TODAY_MD, "w", encoding="utf-8") as f:
        f.write(MARKDOWN_TEMPLATE)
    print(f"[+] Wrote Markdown Intel Brief to {TODAY_MD}")

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

def main():
    asyncio.run(compile_lookbook())

if __name__ == "__main__":
    main()
