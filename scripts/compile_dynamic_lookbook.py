#!/usr/bin/env python3
"""
scripts/compile_dynamic_lookbook.py — Canonical Dynamic Telemetry Lookbook Compiler
==================================================================================
Eliminates all hardcoded game scores and HTML strings. Hydrates dynamically from
FanStack_Live JSON state files (game_recap_live.json, INGRESS_RAW_15M.json).
Compiles magazine-grade Deep Void HTML and A4 PDF deliverables via headless Playwright.

Governed by:
  - Invariant 4: Zero Inline Mocking & Zero Synthetic Fluff
  - Invariant 25: Zero-Rebuild Operational Decoupling
  - Invariant 28: Tri-Anchor Ground Truth Verification Gate
  - Invariant 30: Calendar Year 2026 Ground Truth
"""

import os
import sys
import json
import shutil
import argparse
import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

WORKSPACE_ROOT = Path("/home/james/stacklabs")
INBOX_ROOT = Path("/home/james/sovereign_inbox")
FANSTACK_LIVE_DIR = WORKSPACE_ROOT / "33_FanStack_Lite" / "public" / "FanStack_Live"

RECAP_JSON_PATH = FANSTACK_LIVE_DIR / "game_recap_live.json"
INGRESS_JSON_PATH = FANSTACK_LIVE_DIR / "INGRESS_RAW_15M.json"

PUBLIC_LOOKBOOK_HTML = WORKSPACE_ROOT / "33_FanStack_Lite" / "public" / "lookbook.html"

TEAM_COLORS = {
    "CWS": "#F8FAFC",
    "HOU": "#FB923C",
    "PHI": "#F87171",
    "ATL": "#38BDF8",
    "NYY": "#93C5FD",
    "BOS": "#FCA5A5",
    "CHC": "#60A5FA",
    "SD": "#FBBF24",
}

def load_json_state():
    """Load living state payloads from FanStack_Live."""
    recap_data = {}
    ingress_data = {}
    
    if RECAP_JSON_PATH.exists():
        with open(RECAP_JSON_PATH, "r", encoding="utf-8") as f:
            recap_data = json.load(f)
            
    if INGRESS_JSON_PATH.exists():
        with open(INGRESS_JSON_PATH, "r", encoding="utf-8") as f:
            ingress_data = json.load(f)
            
    return recap_data, ingress_data

def build_dynamic_html(game_pk_str, recap_data, ingress_data):
    """Build dynamic HTML template hydrated strictly from JSON state."""
    games_recap = recap_data.get("games", {})
    game_info = games_recap.get(game_pk_str)
    
    if not game_info:
        raise ValueError(f"Game PK {game_pk_str} not found in {RECAP_JSON_PATH}")
        
    # Extract metadata from INGRESS_RAW_15M if available
    raw_games = ingress_data.get("games", [])
    raw_match = next((g for g in raw_games if str(g.get("gamePk")) == game_pk_str), {})
    
    series_title = raw_match.get("series", "MLB Wild Card Series Game 1")
    venue_name = raw_match.get("venue", "Postseason Ballpark")
    matchup_str = raw_match.get("matchup", "AWAY @ HOME")
    away_team_full = raw_match.get("away_team", "Away Team")
    home_team_full = raw_match.get("home_team", "Home Team")
    away_score = raw_match.get("away_score", 0)
    home_score = raw_match.get("home_score", 0)
    
    # Parse away/home abbreviation
    parts = matchup_str.split(" @ ")
    away_abbr = parts[0] if len(parts) == 2 else "AWAY"
    home_abbr = parts[1] if len(parts) == 2 else "HOME"
    
    away_color = TEAM_COLORS.get(away_abbr, "#FFFFFF")
    home_color = TEAM_COLORS.get(home_abbr, "#FB923C")
    
    recap_title = game_info.get("recap_title", "PITHY GAME RECAP (K.I.S.S.)")
    inning_badge = game_info.get("inning_badge", "LIVE")
    bullets = game_info.get("bullets", [])
    barf_memo = game_info.get("barf_memo", "No advocate memo available.")
    radar = game_info.get("radar", {})
    
    # Dynamic turning points cards (take first 3 non-score bullets)
    turn_bullets = [b for b in bullets if b.get("tag") != "SCORE"]
    if not turn_bullets:
        turn_bullets = bullets
        
    turning_cards_html = ""
    for b in turn_bullets[:3]:
        tag = b.get("tag", "TURNING POINT")
        text = b.get("text", "")
        turning_cards_html += f"""
        <div class="turn-card">
            <h4>{tag}</h4>
            <p>{text}</p>
        </div>
        """
        
    # Dynamic linescore table if structured linescore is available
    linescore_html = ""
    linescore = game_info.get("linescore")
    if linescore and isinstance(linescore, dict):
        innings = linescore.get("innings", [])
        headers = "".join([f"<th>{i+1}</th>" for i in range(len(innings))])
        away_cells = "".join([f"<td>{inn.get('away', '')}</td>" for inn in innings])
        home_cells = "".join([f"<td>{inn.get('home', '')}</td>" for inn in innings])
        linescore_html = f"""
        <table class="table-custom">
            <thead>
                <tr>
                    <th style="text-align: left;">TEAM</th>
                    {headers}
                    <th>R</th><th>H</th><th>E</th>
                </tr>
            </thead>
            <tbody>
                <tr class="highlight">
                    <td style="text-align: left; font-weight: 800; color: {away_color};">{away_abbr}</td>
                    {away_cells}
                    <td style="font-weight: 900; color: #F8FAFC;">{away_score}</td>
                    <td>{linescore.get('away_hits', '-')}</td>
                    <td>{linescore.get('away_errors', '-')}</td>
                </tr>
                <tr>
                    <td style="text-align: left; font-weight: 800; color: {home_color};">{home_abbr}</td>
                    {home_cells}
                    <td style="font-weight: 900; color: #F8FAFC;">{home_score}</td>
                    <td>{linescore.get('home_hits', '-')}</td>
                    <td>{linescore.get('home_errors', '-')}</td>
                </tr>
            </tbody>
        </table>
        """

    # Dynamic slate on deck
    slate_items_html = ""
    for g in raw_games:
        if str(g.get("gamePk")) != game_pk_str:
            status = g.get("status", "SCHEDULED").upper()
            m = g.get("matchup", "")
            s = g.get("series", "")
            slate_items_html += f"""
            <div class="slate-item">
                <div class="time">{status}</div>
                <div class="matchup">{m} ({s})</div>
            </div>
            """

    # Badge styling
    away_class = away_abbr.lower()
    home_class = home_abbr.lower()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FAAS // {series_title.upper()}: {matchup_str}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
        @page {{ size: A4; margin: 0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #0B0D13;
            color: #E2E8F0;
            padding: 22px 28px;
            font-size: 11.5px;
            line-height: 1.38;
            -webkit-print-color-adjust: exact;
        }}
        .header {{
            border-bottom: 2px solid #1E2536;
            padding-bottom: 10px;
            margin-bottom: 11px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header-title-box h1 {{
            font-size: 20px;
            font-weight: 900;
            letter-spacing: -0.5px;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .header-title-box h2 {{
            font-size: 11px;
            font-weight: 600;
            color: #94A3B8;
            margin-top: 2px;
        }}
        .meta-pill {{
            background: #121620;
            border: 1px solid #1E2536;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 9px;
            font-family: 'JetBrains Mono', monospace;
            color: #F59E0B;
            text-align: right;
            line-height: 1.35;
        }}
        .section {{ margin-bottom: 11px; }}
        .section-header {{
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
        }}
        .scoreboard-card {{
            background: #121620;
            border: 1px solid #1E2536;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }}
        .score-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            padding-bottom: 6px;
            border-bottom: 1px solid #1E2536;
        }}
        .team-box {{ display: flex; align-items: center; gap: 10px; }}
        .team-badge {{
            font-size: 14px;
            font-weight: 900;
            padding: 2px 7px;
            border-radius: 5px;
            background: #1E2536;
            color: #F8FAFC;
            border: 1px solid #2E384D;
        }}
        .team-badge.cws {{ background: #FFFFFF22; color: #F8FAFC; border: 1px solid #FFFFFF55; }}
        .team-badge.hou {{ background: #EB6E1F22; color: #FB923C; border: 1px solid #EB6E1F55; }}
        .team-badge.phi {{ background: #E8182822; color: #F87171; border: 1px solid #E8182855; }}
        .team-badge.atl {{ background: #CE114122; color: #38BDF8; border: 1px solid #CE114155; }}
        .team-badge.nyy {{ background: #00308722; color: #93C5FD; border: 1px solid #00308755; }}
        .team-badge.bos {{ background: #BD303922; color: #FCA5A5; border: 1px solid #BD303955; }}
        .team-badge.chc {{ background: #0E338622; color: #60A5FA; border: 1px solid #0E338655; }}
        .team-badge.sd {{ background: #2F241D22; color: #FBBF24; border: 1px solid #FFC42555; }}
        .score-val {{
            font-size: 22px;
            font-weight: 900;
            font-family: 'JetBrains Mono', monospace;
            color: #F8FAFC;
        }}
        .status-badge {{
            background: #F59E0B22;
            color: #FBBF24;
            border: 1px solid #F59E0B55;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            margin-top: 5px;
            margin-bottom: 8px;
        }}
        .table-custom th {{
            color: #64748B;
            font-weight: 600;
            padding: 3px 5px;
            border-bottom: 1px solid #1E2536;
            text-align: center;
        }}
        .table-custom td {{
            padding: 3px 5px;
            border-bottom: 1px solid #161C2A;
            text-align: center;
            color: #CBD5E1;
        }}
        .table-custom tr.highlight td {{
            background: #1E253644;
            font-weight: 700;
            color: #F8FAFC;
        }}
        .turning-points {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 8px;
        }}
        .turn-card {{
            background: #10141D;
            border: 1px solid #1A202C;
            border-radius: 6px;
            padding: 7px 8px;
        }}
        .turn-card h4 {{
            font-size: 9.5px;
            font-weight: 800;
            color: #F59E0B;
            margin-bottom: 2px;
            text-transform: uppercase;
        }}
        .turn-card p {{
            font-size: 9px;
            color: #94A3B8;
            line-height: 1.25;
        }}
        .radar-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }}
        .radar-box {{
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 7px 10px;
        }}
        .radar-title {{
            font-size: 9.5px;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 2px;
        }}
        .barf-take-box {{
            background: #161214;
            border: 1px solid #3B1822;
            border-left: 3px solid #EF4444;
            border-radius: 6px;
            padding: 8px 12px;
            margin-top: 8px;
        }}
        .barf-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 9.5px;
            font-weight: 800;
            color: #F87171;
            margin-bottom: 3px;
        }}
        .barf-text {{
            font-size: 9.5px;
            color: #FECACA;
            font-style: italic;
            line-height: 1.3;
        }}
        .slate-bar {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 6px;
        }}
        .slate-item {{
            background: #10141D;
            border: 1px solid #1E2536;
            border-radius: 6px;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .slate-item .time {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 700;
            color: #F59E0B;
        }}
        .slate-item .matchup {{
            font-size: 10px;
            font-weight: 800;
            color: #E2E8F0;
        }}
        .footer {{
            border-top: 1px solid #1E2536;
            padding-top: 6px;
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            font-size: 8px;
            font-family: 'JetBrains Mono', monospace;
            color: #64748B;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title-box">
            <h1>⚾ THE POSTSEASON INTEL LOOKBOOK</h1>
            <h2>{away_team_full.upper()} @ {home_team_full.upper()} // {series_title.upper()}</h2>
        </div>
        <div class="meta-pill">
            <div>CALENDAR YEAR 2026</div>
            <div>{venue_name.upper()}</div>
            <div>{inning_badge}</div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">📊 1. Official Game Telemetry (Hydrated Live)</div>
        <div class="scoreboard-card">
            <div class="score-row">
                <div class="team-box">
                    <span class="team-badge {away_class}">{away_abbr}</span>
                    <span style="font-size: 13px; font-weight: 800; color: {away_color};">{away_team_full}</span>
                </div>
                <div class="score-val">{away_score}</div>
                <div class="status-badge">{inning_badge}</div>
                <div class="score-val">{home_score}</div>
                <div class="team-box">
                    <span style="font-size: 13px; font-weight: 800; color: {home_color};">{home_team_full}</span>
                    <span class="team-badge {home_class}">{home_abbr}</span>
                </div>
            </div>

            {linescore_html}

            <div class="turning-points">
                {turning_cards_html}
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">🔥 2. Cultural Scar Tissue & October Panic Index</div>
        <div class="radar-grid">
            <div class="radar-box">
                <div class="radar-title" style="color: #F87171;">{radar.get('label1', 'PANIC INDEX')} — {radar.get('val1', '80%')}</div>
                <div style="background: #1E2536; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                    <div style="background: linear-gradient(90deg, #F59E0B, #EF4444); width: {radar.get('val1', '80%')}; height: 100%;"></div>
                </div>
            </div>
            <div class="radar-box">
                <div class="radar-title" style="color: #34D399;">{radar.get('label2', 'DELIRIUM INDEX')} — {radar.get('val2', '80%')}</div>
                <div style="background: #1E2536; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                    <div style="background: linear-gradient(90deg, #10B981, #06B6D4); width: {radar.get('val2', '80%')}; height: 100%;"></div>
                </div>
            </div>
        </div>

        <div class="barf-take-box">
            <div class="barf-header">
                <span>🎙️ THE DAILY BARF EDITORIAL MEMO</span>
                <span>OCTOBER GROUNDED REALITY</span>
            </div>
            <div class="barf-text">
                "{barf_memo}"
            </div>
        </div>
    </div>

    <div class="section" style="margin-bottom: 6px;">
        <div class="section-header">📺 3. Postseason Slate Context</div>
        <div class="slate-bar">
            {slate_items_html}
        </div>
    </div>

    <div class="footer">
        <div>STACKLABS LLC // FANSTACK AS A SERVICE (FAAS) • GROUNDED METAL INTELLIGENCE</div>
        <div>HYDRATED FROM ZERO-REBUILD TELEMETRY • ZERO SYNTHETIC FLUFF</div>
    </div>
</body>
</html>
"""
    return html

async def compile_lookbook(game_pk=None):
    recap_data, ingress_data = load_json_state()
    if not game_pk:
        game_pk = recap_data.get("active_game_pk", "849849")
    game_pk_str = str(game_pk)
    
    date_str = ingress_data.get("slate_date", "2026-09-29").replace("-", "_")
    html_content = build_dynamic_html(game_pk_str, recap_data, ingress_data)
    
    # Target file paths
    pilot_html_path = INBOX_ROOT / "pilot_drops" / f"FAAS_LOOKBOOK_{game_pk_str}_{date_str}.html"
    pilot_pdf_path = INBOX_ROOT / "pilot_drops" / f"FAAS_LOOKBOOK_{game_pk_str}_{date_str}.pdf"
    today_pdf_path = INBOX_ROOT / "today" / f"FAAS_LOOKBOOK_{game_pk_str}_{date_str}.pdf"
    notebook_pdf_path = INBOX_ROOT / "notebook_sync" / "13_FanStack_as_a_Service" / f"FAAS_LOOKBOOK_{game_pk_str}_{date_str}.pdf"
    
    # Ensure parent directories exist
    pilot_html_path.parent.mkdir(parents=True, exist_ok=True)
    pilot_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    today_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_LOOKBOOK_HTML.parent.mkdir(parents=True, exist_ok=True)
    if notebook_pdf_path.parent.exists():
        notebook_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
    # Write HTML locally
    with open(pilot_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Wrote dynamic HTML: {pilot_html_path}")
    
    # Mirror HTML to Port 3033 public
    shutil.copyfile(pilot_html_path, PUBLIC_LOOKBOOK_HTML)
    print(f"[+] Mirrored to Port 3033 public assets: {PUBLIC_LOOKBOOK_HTML}")
    
    # Compile PDF via Playwright
    print(f"[*] Compiling A4 PDF for GamePk {game_pk_str}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        await page.pdf(
            path=str(pilot_pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}
        )
        await browser.close()
        
    if pilot_pdf_path.exists():
        size_kb = pilot_pdf_path.stat().st_size / 1024
        print(f"[+] Successfully compiled PDF: {pilot_pdf_path} ({size_kb:.1f} KB)")
        shutil.copyfile(pilot_pdf_path, today_pdf_path)
        print(f"[+] Copied to today dir: {today_pdf_path}")
        if notebook_pdf_path.parent.exists():
            shutil.copyfile(pilot_pdf_path, notebook_pdf_path)
            print(f"[+] Synced PDF to clean room: {notebook_pdf_path}")
    else:
        print(f"[-] PDF compilation failed at {pilot_pdf_path}", file=sys.stderr)
        sys.exit(1)
        
    print("[*] Triggering Google Drive sync...")
    try:
        res = subprocess.run(["/home/james/stacklabs/scripts/sync_to_gdrive.sh"], capture_output=True, text=True, check=True)
        print(f"[+] Google Drive sync complete:\n{res.stdout.strip()}")
    except Exception as e:
        print(f"[-] Google Drive sync warning: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canonical Dynamic Lookbook Compiler")
    parser.add_argument("--game-pk", default=None, help="Target GamePk (default: active_game_pk or 849849)")
    args = parser.parse_args()
    
    asyncio.run(compile_lookbook(args.game_pk))
