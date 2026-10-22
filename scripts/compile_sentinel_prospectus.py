#!/usr/bin/env python3
"""
Sovereign Sentinel: Executive Brief & Technical Prospectus PDF Compiler
Target CI: 29_Sovereign_Sentinel
Ticket: WO0010102-SENTINEL-PROSPECTUS-EXECUTIVE-DOSSI
Recipient: Pawel Rudnicki (Co-Owner WildSeed LLC / Macroeconomic Strategist)

Compiles an 8-page publication-grade, glossy executive prospectus PDF adhering
to Sovereign Home Premium aesthetic standards via Headless Google Chrome 150.
"""

import os
import sys
import re
import base64
import subprocess
import shutil
from pathlib import Path

# Paths
ROOT_DIR = Path("/home/james/stacklabs")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

INBOX_TODAY = Path("/home/james/sovereign_inbox/today")
REPORTS_DIR = ROOT_DIR / "scripts" / "reports"
OUTPUT_HTML = REPORTS_DIR / "sentinel_prospectus_template.html"
OUTPUT_PDF = INBOX_TODAY / "Sovereign_Sentinel_Executive_Prospectus_Pawel_Rudnicki.pdf"

# Asset Paths
MOCKUP_DIR = Path("/home/james/sovereign_inbox/tickets/WO-2026-0907-SENTINEL-SIM/mockups")
IMG_RADAR = MOCKUP_DIR / "sentinel_radar_live.png"
IMG_DRAWER = MOCKUP_DIR / "sentinel_telemetry_drawer.png"
IMG_OVERVIEW = MOCKUP_DIR / "sentinel_overview_live.png"
IMG_VOICE = MOCKUP_DIR / "sentinel_voice_heal_live.png"
IMG_LEDGER = MOCKUP_DIR / "sentinel_herd_ledger_live.png"
IMG_PAWEL = ROOT_DIR / "avatars" / "pawel.png"

def get_base64_img(path: Path) -> str:
    if not path.exists():
        print(f"⚠️ Warning: Image not found: {path}")
        return ""
    with open(path, "rb") as f:
        data = f.read()
    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"

def build_prospectus_html() -> str:
    print("Loading visual assets and encoding to Base64...")
    b64_radar = get_base64_img(IMG_RADAR)
    b64_drawer = get_base64_img(IMG_DRAWER)
    b64_overview = get_base64_img(IMG_OVERVIEW)
    b64_voice = get_base64_img(IMG_VOICE)
    b64_ledger = get_base64_img(IMG_LEDGER)
    b64_pawel = get_base64_img(IMG_PAWEL)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sovereign Sentinel: Executive Brief & Technical Prospectus — Pawel Rudnicki</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        @page {{
            size: A4 portrait;
            margin: 0;
        }}
        @media print {{
            html, body {{
                width: 210mm;
                height: 100%;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .page {{
                page-break-after: always;
                break-after: page;
            }}
            .page:last-of-type {{
                page-break-after: avoid;
                break-after: avoid;
            }}
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: #07090e;
            color: #cbd5e1;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 8.8pt;
            line-height: 1.42;
            -webkit-font-smoothing: antialiased;
        }}

        /* Sovereign Home Premium Page Container */
        .page {{
            width: 210mm;
            height: 297mm;
            max-height: 297mm;
            min-height: 297mm;
            position: relative;
            padding: 14mm 16mm 14mm 16mm;
            background: radial-gradient(circle at 90% 10%, rgba(0, 229, 255, 0.04), transparent 50%),
                        radial-gradient(circle at 10% 90%, rgba(16, 185, 129, 0.03), transparent 50%),
                        #080a0f;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            border-bottom: 1px solid rgba(0, 229, 255, 0.1);
        }}

        /* Header & Footer */
        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 3mm;
            border-bottom: 1px solid rgba(0, 229, 255, 0.2);
            font-family: 'JetBrains Mono', monospace;
            font-size: 7pt;
            letter-spacing: 0.8px;
            color: #64748b;
            text-transform: uppercase;
        }}
        .header-brand {{
            color: #00e5ff;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .header-brand span {{
            color: #94a3b8;
        }}

        .page-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 3mm;
            border-top: 1px solid rgba(255, 255, 255, 0.07);
            font-family: 'JetBrains Mono', monospace;
            font-size: 6.8pt;
            color: #475569;
            letter-spacing: 0.5px;
        }}
        .footer-secure {{
            color: #10b981;
            font-weight: 600;
        }}

        .page-content {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            padding: 3.5mm 0;
            gap: 3.5mm;
        }}

        /* Typography */
        h1, h2, h3, h4 {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            letter-spacing: -0.2px;
            color: #f8fafc;
        }}
        .section-tag {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 7pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #00e5ff;
            display: inline-block;
            margin-bottom: 1mm;
        }}
        .section-title {{
            font-size: 15pt;
            line-height: 1.15;
            color: #ffffff;
            margin-bottom: 1mm;
        }}
        .section-desc {{
            font-size: 8.5pt;
            color: #94a3b8;
            line-height: 1.35;
        }}

        /* Cards and Panels */
        .glass-card {{
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(0, 229, 255, 0.18);
            border-radius: 6px;
            padding: 3mm 3.5mm;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        }}
        .glass-card-emerald {{
            background: rgba(6, 28, 24, 0.65);
            border: 1px solid rgba(16, 185, 129, 0.28);
        }}
        .glass-card-amber {{
            background: rgba(30, 22, 10, 0.65);
            border: 1px solid rgba(245, 158, 11, 0.28);
        }}
        .glass-card-cyan {{
            background: rgba(8, 30, 45, 0.65);
            border: 1px solid rgba(0, 229, 255, 0.28);
        }}

        .card-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 9.5pt;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 1.5mm;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        /* Grid Layouts */
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 3.5mm;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 3mm;
        }}
        .grid-4 {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 2.5mm;
        }}

        /* Badges & Tags */
        .badge {{
            display: inline-block;
            padding: 1.5px 5px;
            border-radius: 3px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 6.8pt;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-cyan {{
            background: rgba(0, 229, 255, 0.15);
            color: #00e5ff;
            border: 1px solid rgba(0, 229, 255, 0.3);
        }}
        .badge-emerald {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .badge-amber {{
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        .badge-purple {{
            background: rgba(139, 92, 246, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.3);
        }}

        /* Tables */
        .spec-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.8pt;
            margin-top: 1mm;
        }}
        .spec-table th {{
            text-align: left;
            padding: 2mm 2.5mm;
            background: rgba(0, 229, 255, 0.08);
            color: #00e5ff;
            font-family: 'JetBrains Mono', monospace;
            font-size: 7pt;
            font-weight: 700;
            text-transform: uppercase;
            border-bottom: 1px solid rgba(0, 229, 255, 0.2);
        }}
        .spec-table td {{
            padding: 2mm 2.5mm;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #cbd5e1;
        }}
        .spec-table tr:nth-child(even) td {{
            background: rgba(255, 255, 255, 0.015);
        }}

        /* Visual Images */
        .asset-frame {{
            border-radius: 5px;
            overflow: hidden;
            border: 1px solid rgba(0, 229, 255, 0.25);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
            background: #000;
        }}
        .asset-frame img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .asset-caption {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 6.8pt;
            color: #64748b;
            padding: 1.5mm 2mm;
            background: #0d131f;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .asset-caption strong {{
            color: #38bdf8;
        }}

        /* Quote / Callout */
        .callout {{
            border-left: 3px solid #00e5ff;
            background: rgba(0, 229, 255, 0.04);
            padding: 2.5mm 3.5mm;
            border-radius: 0 5px 5px 0;
            font-style: italic;
            color: #e2e8f0;
            font-size: 8.4pt;
        }}
        .callout-author {{
            display: block;
            margin-top: 1mm;
            font-style: normal;
            font-family: 'JetBrains Mono', monospace;
            font-size: 7pt;
            color: #38bdf8;
            font-weight: 600;
        }}

        /* Key Metric Box */
        .metric-box {{
            text-align: center;
            padding: 2.5mm 1.5mm;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 4px;
        }}
        .metric-value {{
            font-family: 'Outfit', sans-serif;
            font-size: 13pt;
            font-weight: 800;
            color: #00e5ff;
            line-height: 1;
        }}
        .metric-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 6.2pt;
            color: #94a3b8;
            margin-top: 1mm;
            text-transform: uppercase;
        }}

        /* Math container */
        .math-block {{
            background: rgba(0, 229, 255, 0.04);
            border: 1px solid rgba(0, 229, 255, 0.2);
            border-radius: 4px;
            padding: 2mm 3mm;
            font-family: 'JetBrains Mono', monospace;
            font-size: 7.8pt;
            color: #38bdf8;
            text-align: center;
            margin: 1.5mm 0;
        }}

        /* Cover Specific */
        .cover-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 10mm 4mm 6mm 4mm;
        }}
        .cover-badge-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .cover-title-block {{
            margin-top: 8mm;
        }}
        .cover-supertitle {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 2px;
            color: #00e5ff;
            text-transform: uppercase;
            margin-bottom: 2mm;
        }}
        .cover-main-title {{
            font-size: 26pt;
            font-weight: 800;
            line-height: 1.05;
            color: #ffffff;
            letter-spacing: -0.5px;
            text-transform: uppercase;
        }}
        .cover-subtitle {{
            font-size: 11pt;
            font-weight: 400;
            color: #94a3b8;
            margin-top: 3mm;
            max-width: 155mm;
            line-height: 1.4;
        }}
        .cover-divider {{
            width: 45mm;
            height: 3px;
            background: linear-gradient(90deg, #00e5ff, #10b981);
            margin: 5mm 0;
            border-radius: 2px;
        }}

        .cover-meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4mm;
            margin-top: 6mm;
        }}
        .cover-meta-card {{
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(0, 229, 255, 0.2);
            border-radius: 6px;
            padding: 4mm 4.5mm;
        }}
        .cover-meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 6.8pt;
            color: #64748b;
            text-transform: uppercase;
            margin-bottom: 1mm;
        }}
        .cover-meta-value {{
            font-family: 'Outfit', sans-serif;
            font-size: 10.5pt;
            font-weight: 700;
            color: #f8fafc;
        }}
        .cover-meta-sub {{
            font-size: 7.5pt;
            color: #94a3b8;
            margin-top: 0.5mm;
        }}

        .avatar-slot {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            border: 2px solid #00e5ff;
            overflow: hidden;
            box-shadow: 0 0 12px rgba(0, 229, 255, 0.4);
        }}
        .avatar-slot img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
    </style>
</head>
<body>

    <!-- =================================================================== -->
    <!-- PAGE 1: COVER SHEET                                                 -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                STACKLABS LLC <span>// AUTONOMOUS EDGE SYSTEMS</span>
            </div>
            <div>SPEC SOW-2026-SENTINEL-01 // CONFIDENTIAL</div>
        </div>

        <div class="cover-container">
            <div>
                <div class="cover-badge-row">
                    <span class="badge badge-cyan">BARE-METAL CLOUD IMMUNITY</span>
                    <span class="badge badge-emerald">ZERO API COGS</span>
                    <span class="badge badge-amber">AGRICULTURE & BIO-TELEMETRY</span>
                </div>

                <div class="cover-title-block">
                    <div class="cover-supertitle">Enterprise Infrastructure & Investment Brief</div>
                    <div class="cover-main-title">SOVEREIGN<br>SENTINEL</div>
                    <div class="cover-subtitle">Autonomous Edge Telemetry & Multi-Agent Dialectic Triage Platform for Agricultural Ecosystems and Registered Livestock Herds.</div>
                    <div class="cover-divider"></div>
                </div>

                <div class="callout" style="max-width: 165mm; margin-top: 3mm;">
                    "Bridging <em>The Pendulum and the Algorithm</em> into empirical dedicated AMD Zen 4 APU silicon: Why local inference and physical hardware arbitrage form the only unassailable moat against the 1,100 TWh cloud energy ceiling."
                    <span class="callout-author">— Strategic Thesis for Pawel Rudnicki</span>
                </div>
            </div>

            <div>
                <div class="cover-meta-grid">
                    <div class="cover-meta-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <div class="cover-meta-label">PREPARED FOR / TARGET STRATEGIST</div>
                                <div class="cover-meta-value">Pawel Rudnicki</div>
                                <div class="cover-meta-sub">Co-Owner, WildSeed LLC | Lead Pre-Seed Investor</div>
                                <div class="cover-meta-sub" style="color:#00e5ff;">Author: <em>The Pendulum and the Algorithm</em></div>
                            </div>
                            <div class="avatar-slot">
                                <img src="{b64_pawel}" alt="Pawel Rudnicki">
                            </div>
                        </div>
                    </div>

                    <div class="cover-meta-card">
                        <div class="cover-meta-label">LEAD SYSTEMS ARCHITECT / FOUNDER</div>
                        <div class="cover-meta-value">James Carroll</div>
                        <div class="cover-meta-sub">Certified ServiceNow Specialist (20+ Yrs Enterprise ITSM)</div>
                        <div class="cover-meta-sub">Founder & Principal Engineer, StackLabs LLC</div>
                    </div>

                    <div class="cover-meta-card glass-card-cyan">
                        <div class="cover-meta-label">COMMERCIAL PROPOSITION & STRUCTURE</div>
                        <div class="cover-meta-value">$40,000 USD Pre-Seed SAFE</div>
                        <div class="cover-meta-sub">$1,500,000 Valuation Cap | 6-Month Hardened Runway</div>
                        <div class="cover-meta-sub" style="color: #38bdf8;">Allocation: $18K Dedicated Silicon / $12K Field Trials</div>
                    </div>

                    <div class="cover-meta-card glass-card-emerald">
                        <div class="cover-meta-label">DEPLOYED HARDWARE TOPOLOGY</div>
                        <div class="cover-meta-value">Clio, Argo & Raspberry Pi 5</div>
                        <div class="cover-meta-sub">Private Tailscale Mesh | Local Whisper / Qwen / Hailo-8</div>
                        <div class="cover-meta-sub" style="color: #10b981;">Port 3038 Active Live Console | Sector 4 Telemetry</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 1 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 2: THE MACROECONOMIC & THERMODYNAMIC THESIS                    -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>01 // MACROECONOMIC & THERMODYNAMIC THESIS</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">THE GROUND-TRUTH ECONOMIC MOAT</span>
                <h2 class="section-title">The Pendulum, The Algorithm & Ghost GDP</h2>
                <div class="section-desc">Why the centralization of cloud AI threatens rural and physical industries, and how dedicated local hardware arbitrage establishes permanent thermodynamic immunity.</div>
            </div>

            <div class="callout">
                "AI is the first technology in human civilization that is more productive the fewer humans it needs, yet it operates entirely inside an economic system that only functions if humans have disposable income to spend. Unlike steam or electricity, which expanded the horizontal capability of labor, AI vertically compresses the cognitive stack."
                <span class="callout-author">— Pawel Rudnicki, <em>The Pendulum and the Algorithm</em> (2026)</span>
            </div>

            <div class="grid-2">
                <div class="glass-card">
                    <div class="card-title">
                        <span>The 1,100 TWh Energy Wall</span>
                        <span class="badge badge-amber">PHYSICAL CEILING</span>
                    </div>
                    <p style="font-size: 8pt; color: #94a3b8; margin-bottom: 2mm;">
                        By late 2026, global data center energy draw is projected to surpass <strong>1,100 Terawatt-hours</strong>. The physical grid cannot build substations, cooling towers, or high-voltage lines fast enough to satisfy multi-billion-dollar hyperscalers.
                    </p>
                    <p style="font-size: 8pt; color: #cbd5e1;">
                        As hyperscalers face escalating electrical and water tariffs, they pass variable costs down to end-users via <strong>per-token SaaS surcharges</strong>. For industrial and rural operators, paying recurring cloud token tolls to monitor cows, crops, or extraction tanks is financial suicide.
                    </p>
                </div>

                <div class="glass-card glass-card-cyan">
                    <div class="card-title">
                        <span>The "Ghost GDP" Trap</span>
                        <span class="badge badge-cyan">STRUCTURAL PARADOX</span>
                    </div>
                    <p style="font-size: 8pt; color: #94a3b8; margin-bottom: 2mm;">
                        Corporate balance sheets and equity indexes print record highs because automated cognitive tools slash enterprise payroll. However, this creates <strong>Ghost GDP</strong>—value created without corresponding wage distribution.
                    </p>
                    <p style="font-size: 8pt; color: #cbd5e1;">
                        The counter-strategy is not more SaaS. It is <strong>decentralized ownership of sovereign compute</strong>. When agricultural operators own their silicon, they retain 100% of their operational surplus rather than leasing their autonomy back from Silicon Valley.
                    </p>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">
                    <span>Cloud SaaS vs. Sovereign Sentinel Thermodynamic Arbitrage</span>
                    <span class="badge badge-emerald">ZERO-COGS ARCHITECTURE</span>
                </div>
                <table class="spec-table">
                    <thead>
                        <tr>
                            <th>Architectural Dimension</th>
                            <th>Conventional Cloud SaaS (AWS / Metrc / Canix)</th>
                            <th>Sovereign Sentinel (StackLabs Bare-Metal)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Marginal Inference Cost</strong></td>
                            <td style="color:#f87171;">$0.02 – $0.06 per 1,000 tokens (compounds indefinitely)</td>
                            <td style="color:#34d399; font-weight:700;">$0.00 / token (bounded strictly by local electricity)</td>
                        </tr>
                        <tr>
                            <td><strong>Network Dependency</strong></td>
                            <td style="color:#f87171;">Hard requirement for 24/7 broadband; fails on remote ranches</td>
                            <td style="color:#34d399; font-weight:700;">100% Air-gapped offline edge inference (Tailscale optional)</td>
                        </tr>
                        <tr>
                            <td><strong>Data Sovereignty & Privacy</strong></td>
                            <td style="color:#f87171;">Exfiltrates herd biometrics & batch yields to cloud corporate silos</td>
                            <td style="color:#34d399; font-weight:700;">Zero external egress; stored in immutable SQLite WAL ledger</td>
                        </tr>
                        <tr>
                            <td><strong>Failure Mode During Outage</strong></td>
                            <td style="color:#f87171;">Total system paralysis (cannot triage calves or check gates)</td>
                            <td style="color:#34d399; font-weight:700;">Autonomous local MARD triage continues uninterrupted</td>
                        </tr>
                        <tr>
                            <td><strong>3-Year Total Cost of Ownership</strong></td>
                            <td style="color:#f87171;">$72,000 – $140,000+ (perpetual license + seat fees)</td>
                            <td style="color:#34d399; font-weight:700;">$14,500 one-time hardware amortized + nominal support</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="grid-3">
                <div class="metric-box">
                    <div class="metric-value">$0.00</div>
                    <div class="metric-label">Marginal Token Cost</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">100%</div>
                    <div class="metric-label">Cloud Outage Immunity</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">&lt;2.2s</div>
                    <div class="metric-label">Local Edge Triage Latency</div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 2 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 3: THE DUAL-VECTOR COMMERCIAL CHASSIS                          -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>02 // DUAL-VECTOR COMMERCIAL CHASSIS</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">COMMERCIAL GO-TO-MARKET STRATEGY</span>
                <h2 class="section-title">The Purse Seine Net & The Bluefin Tuna</h2>
                <div class="section-desc">A complementary two-pronged revenue chassis pairing high-volume, low-friction consumer cashflow with high-ticket, high-margin industrial ranch enterprise contracts.</div>
            </div>

            <div class="grid-2">
                <!-- Vector A -->
                <div class="glass-card glass-card-cyan">
                    <div class="card-title">
                        <div>
                            <span style="color: #00e5ff;">VECTOR A: THE PURSE SEINE NET</span>
                            <div style="font-size: 7pt; color: #94a3b8; font-weight: 400;">Consumer & Suburban Pet Bio-Sentinel</div>
                        </div>
                        <span class="badge badge-cyan">$5.99 / MO</span>
                    </div>
                    <div style="margin-bottom: 2mm;">
                        <span class="badge badge-cyan">MASS MARKET VOLUME</span>
                        <span class="badge badge-emerald">ZERO-FRICTION D2C</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        <strong>Target Market:</strong> 85M+ US pet owners, veterinary clinic telehealth subscribers (Arkle Vet pilot model), suburban canine/feline caretakers.
                    </p>
                    <ul style="font-size: 7.6pt; color: #94a3b8; padding-left: 3.5mm; margin-bottom: 2.5mm; line-height: 1.35;">
                        <li><strong>Continuous Actigraphy:</strong> Real-time sleep, pacing, and velocity vector monitoring.</li>
                        <li><strong>Litterbox Telemetry:</strong> Weight trend scales and urination frequency anomaly detection.</li>
                        <li><strong>Autonomous Sample Interception:</strong> Pushes exact GPS drop-coordinates to owners within minutes of defecation for sterile collection.</li>
                        <li><strong>Clinical SOAP Dossier:</strong> Auto-generates veterinary PDF records for telemedicine consultations.</li>
                    </ul>
                    <div class="metric-box" style="background: rgba(0, 229, 255, 0.05);">
                        <div class="metric-value" style="font-size: 11pt;">$718,800 ARR</div>
                        <div class="metric-label">Year 2 Projection (10,000 Active Units)</div>
                    </div>
                </div>

                <!-- Vector B -->
                <div class="glass-card glass-card-emerald">
                    <div class="card-title">
                        <div>
                            <span style="color: #10b981;">VECTOR B: THE 500-LB BLUEFIN TUNA</span>
                            <div style="font-size: 7pt; color: #94a3b8; font-weight: 400;">Industrial Ranch & Registered Herd Sentinel</div>
                        </div>
                        <span class="badge badge-emerald">$500–$1,500 / MO</span>
                    </div>
                    <div style="margin-bottom: 2mm;">
                        <span class="badge badge-emerald">HIGH MARGIN ENTERPRISE</span>
                        <span class="badge badge-amber">ASSET PROTECTION</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        <strong>Target Market:</strong> Registered Texas Longhorn ranches, elite breeding operations ($12K–$55K/head asset valuation), commercial cow-calf ranches.
                    </p>
                    <ul style="font-size: 7.6pt; color: #94a3b8; padding-left: 3.5mm; margin-bottom: 2.5mm; line-height: 1.35;">
                        <li><strong>Calving Dystocia Alerting:</strong> Isolates prolonged recumbency to prevent maternal and calf mortality ($15K–$35K loss saved per incident).</li>
                        <li><strong>Bovine Respiratory Disease (BRD):</strong> Detects rumination drops 48 hours before visible physical symptoms appear.</li>
                        <li><strong>Solar Water Infrastructure:</strong> Ultrasonic flow and depth telemetry prevents catastrophic dehydration events.</li>
                        <li><strong>Hands-Free Voice Heal:</strong> Operators report issues through barn transceivers while wearing leather gloves.</li>
                    </ul>
                    <div class="metric-box" style="background: rgba(16, 185, 129, 0.05);">
                        <div class="metric-value" style="font-size: 11pt; color: #10b981;">$360,000 ARR</div>
                        <div class="metric-label">Year 2 Projection (30 Commercial Ranches)</div>
                    </div>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">
                    <span>Unified Unit Economics & Blended ARR Funnel</span>
                    <span class="badge badge-cyan">STACKLABS PROJECTION</span>
                </div>
                <table class="spec-table">
                    <thead>
                        <tr>
                            <th>Operating Metric</th>
                            <th>Phase 1 (Pilot Deployment)</th>
                            <th>Phase 2 (Regional Expansion)</th>
                            <th>Phase 3 (National Platform)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Active Pet Sentinels (Vector A)</strong></td>
                            <td>250 units ($1,497/mo)</td>
                            <td>2,500 units ($14,975/mo)</td>
                            <td>15,000 units ($89,850/mo)</td>
                        </tr>
                        <tr>
                            <td><strong>Active Ranch Gateways (Vector B)</strong></td>
                            <td>3 ranches ($2,250/mo)</td>
                            <td>18 ranches ($14,400/mo)</td>
                            <td>65 ranches ($58,500/mo)</td>
                        </tr>
                        <tr>
                            <td><strong>Total Monthly Recurring Revenue (MRR)</strong></td>
                            <td style="color:#38bdf8; font-weight:700;">$3,747 / mo</td>
                            <td style="color:#38bdf8; font-weight:700;">$29,375 / mo</td>
                            <td style="color:#38bdf8; font-weight:700;">$148,350 / mo</td>
                        </tr>
                        <tr>
                            <td><strong>Annual Run-Rate (ARR)</strong></td>
                            <td style="color:#34d399; font-weight:700;">$44,964 ARR</td>
                            <td style="color:#34d399; font-weight:700;">$352,500 ARR</td>
                            <td style="color:#34d399; font-weight:700;">$1,780,200 ARR</td>
                        </tr>
                        <tr>
                            <td><strong>Gross Software Margin</strong></td>
                            <td>91.4% (Zero Cloud Token COGS)</td>
                            <td>93.2% (Local Silicon Amortized)</td>
                            <td>94.8% (Scale Hardware Arbitrage)</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 3 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 4: SPATIAL BOUNDARY MATH & GEOFENCE INTELLIGENCE               -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>03 // SPATIAL BOUNDARY MATH & DWELL HEURISTICS</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">MATHEMATICAL PRIMITIVES & ALGORITHMIC PARITY</span>
                <h2 class="section-title">2D Pasture Radar & The Dwell Vector</h2>
                <div class="section-desc">How identical spatial polygon containment algorithms bridge table-top tactical battle grids to 500-acre grazing pastures, isolating acute distress before injury occurs.</div>
            </div>

            <div class="math-block">
                State(Entity_ID, \vec{{x}}, \vec{{y}}, t, \Delta\text{{State}}) \quad \longrightarrow \quad \text{{Dwell}}(\tau) = \int_{{t_0}}^{{t}} \mathbb{{I}}(\|\vec{{v}}(t)\| &lt; v_{{\text{{thresh}}}}) \, dt
            </div>

            <div class="grid-2">
                <div class="glass-card">
                    <div class="card-title">
                        <span>The Universal Spatial Primitive</span>
                        <span class="badge badge-cyan">SHARED CODEBASE</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        The Sovereign OS core does not reinvent spatial math between sub-applications. The ray-casting point-in-polygon algorithm originally built for our <strong>Port 3032 MARD TTRPG battle grid</strong> runs unmodified inside Sovereign Sentinel.
                    </p>
                    <p style="font-size: 7.8pt; color: #94a3b8;">
                        Whether determining if a player's token is inside a wizard's <em>Fireball</em> zone or verifying if <strong>Heifer #42</strong> has breached Pasture A perimeter, the execution engine evaluates boundary coordinates against relational tables in under 1.2ms.
                    </p>
                </div>

                <div class="glass-card glass-card-amber">
                    <div class="card-title">
                        <span>The Calving Dystocia Heuristic</span>
                        <span class="badge badge-amber">CRITICAL SAVING</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        Derived from the canine "Poop Recovery Vector" in Smyrna, the livestock recumbency heuristic monitors continuous rest posture.
                    </p>
                    <p style="font-size: 7.8pt; color: #94a3b8;">
                        When a pregnant heifer exhibits <strong>lateral recumbency $>45$ minutes</strong> paired with <strong>herd centroid separation $>350$ meters</strong>, the system rules out normal rumination and flags active calving labor dystocia, instantly notifying ranch staff before calf asphyxiation.
                    </p>
                </div>
            </div>

            <!-- Live Asset Frame -->
            <div class="asset-frame">
                <img src="{b64_radar}" alt="2D Pasture Radar Live Console">
                <div class="asset-caption">
                    <div><strong>FIGURE 3.1:</strong> Live 2D Pasture Radar on Port 3038 &bull; Pasture A Boundary & Herd Distribution (25 Head)</div>
                    <div style="color:#00e5ff;">VERIFIED PEGASUS TWIN &bull; KI-095 COMPLIANT</div>
                </div>
            </div>

            <div class="grid-3">
                <div class="metric-box">
                    <div class="metric-value">120m</div>
                    <div class="metric-label">Nominal Herd Centroid Radius</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">0.8 mph</div>
                    <div class="metric-label">Mean Grazing Velocity</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">&gt;350m</div>
                    <div class="metric-label">Isolation Alert Threshold</div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 4 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 5: THE 4-AGENT M.A.R.D. DIALECTIC TRIAGE CORE                  -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>04 // M.A.R.D. DIALECTIC TRIAGE & CONSENSUS</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">MULTI-AGENT REACTIVE DISCOURSE</span>
                <h2 class="section-title">The 4-Agent Triage Swarm & Anti-Alarm Fatigue</h2>
                <div class="section-desc">Why single-threshold IoT sensors fail in agriculture, and how an adversarial 4-persona dialectic debate suppresses false alarms while catching real emergencies.</div>
            </div>

            <div class="grid-2">
                <div class="glass-card" style="border-left: 3px solid #00e5ff;">
                    <div class="card-title">
                        <span style="color: #00e5ff;">1. Spatial Scout</span>
                        <span class="badge badge-cyan">PORT 8095</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1;">
                        <strong>Domain:</strong> Perimeter geometry, pasture vectors, centroid dispersion.
                    </p>
                    <p style="font-size: 7.5pt; color: #94a3b8; margin-top: 1mm;">
                        Monitors GPS tags every 10 seconds. Detects boundary drift, gate proximity, and herd cohesion. Rejects panic alarms if herd is moving together toward water.
                    </p>
                </div>

                <div class="glass-card" style="border-left: 3px solid #10b981;">
                    <div class="card-title">
                        <span style="color: #10b981;">2. Clinical DVM Specialist</span>
                        <span class="badge badge-emerald">BIOMETRIC ENGINE</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1;">
                        <strong>Domain:</strong> Rumination actigraphy, core body temperature, estrus cycles.
                    </p>
                    <p style="font-size: 7.5pt; color: #94a3b8; margin-top: 1mm;">
                        Maintains 14-day rolling baselines. Correlates temperature spikes with heat index to distinguish acute septic fever from hot afternoon solar load.
                    </p>
                </div>

                <div class="glass-card" style="border-left: 3px solid #f59e0b;">
                    <div class="card-title">
                        <span style="color: #f59e0b;">3. Environmental Sentinel</span>
                        <span class="badge badge-amber">INFRASTRUCTURE IOT</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1;">
                        <strong>Domain:</strong> Solar trough flow (GPM), tank depth, ambient microclimate.
                    </p>
                    <p style="font-size: 7.5pt; color: #94a3b8; margin-top: 1mm;">
                        Ultrasonic sensors audit water supply. Flags float valve failures before tanks run dry, providing 18-hour advance warning before cattle experience dehydration.
                    </p>
                </div>

                <div class="glass-card" style="border-left: 3px solid #a78bfa;">
                    <div class="card-title">
                        <span style="color: #a78bfa;">4. Range Foreman</span>
                        <span class="badge badge-purple">CONSENSUS GATE</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1;">
                        <strong>Domain:</strong> Operational prioritization, labor cost impact, dispatch gate.
                    </p>
                    <p style="font-size: 7.5pt; color: #94a3b8; margin-top: 1mm;">
                        Weighs dialectic inputs. Only promotes an advisory to an emergency phone alert if at least 2 agents confirm acute physical risk, completely eliminating alarm fatigue.
                    </p>
                </div>
            </div>

            <!-- Live Asset Frame -->
            <div class="asset-frame">
                <img src="{b64_drawer}" alt="MARD Dialectic Stream & Consensus Drawer">
                <div class="asset-caption">
                    <div><strong>FIGURE 4.1:</strong> Live M.A.R.D. Swarm Dialectic Drawer &bull; Turn-by-turn Consensus Engine (Port 3038)</div>
                    <div style="color:#00e5ff;">100% LOCAL PARSING &bull; ZERO TOKEN EGRESS</div>
                </div>
            </div>

            <div class="callout" style="border-left-color: #10b981;">
                "Single-sensor thresholds cause ranchers to shut off notifications within 3 days. By pitting the Spatial Scout against the Clinical Specialist and Environmental Sentinel, Sovereign Sentinel acts like an experienced morning foreman team gathered at the coffee pot."
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 5 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 6: HANDS-FREE VOICE HEAL & AUTONOMOUS FIELD DISPATCH           -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>05 // HANDS-FREE VOICE HEAL & FIELD DISPATCH</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">TACTILE OPERATOR INTERFACE & ITSM LOGGING</span>
                <h2 class="section-title">Hands-Free Voice Heal & Barnyard Dispatch</h2>
                <div class="section-desc">Designed for harsh agricultural realities: How operators wearing muddy leather work gloves execute enterprise-grade ITIL state changes using localized voice commands.</div>
            </div>

            <div class="grid-2">
                <div class="glass-card">
                    <div class="card-title">
                        <span>The Muddy Glove Paradox</span>
                        <span class="badge badge-amber">RANCH REALITY</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        Enterprise software fails on ranches because it assumes clean hands, warm offices, and capacitive touchscreens. A rancher in a calving barn at 2:00 AM wearing manure-covered leather gloves cannot type on an iPhone.
                    </p>
                    <p style="font-size: 7.8pt; color: #94a3b8;">
                        Sovereign Sentinel installs ruggedized, wall-mounted acoustic transceivers in barn alleys and UTV cabs. Plain-English voice input is captured, filtered through local DSP noise suppression, and processed offline.
                    </p>
                </div>

                <div class="glass-card glass-card-cyan">
                    <div class="card-title">
                        <span>Two-Track Execution Engine</span>
                        <span class="badge badge-cyan">DUAL ROUTING</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        Every decoded voice command generates a deterministic ITIL incident ticket in <code>sovereign_now.db</code> and bifurcates into two automated execution tracks:
                    </p>
                    <ul style="font-size: 7.5pt; color: #94a3b8; padding-left: 3.5mm; line-height: 1.35;">
                        <li><strong>Track A (Autonomous Self-Healing):</strong> Resets stuck solar pump relays, cycles telemetry gateways, and verifies tank flow with instant acoustic voice confirmation.</li>
                        <li><strong>Track B (Physical Field Dispatch):</strong> Dispatches coordinates, RFID numbers, and medical protocols directly to ranch hands.</li>
                    </ul>
                </div>
            </div>

            <!-- Live Asset Frame -->
            <div class="asset-frame">
                <img src="{b64_voice}" alt="Voice Heal Console & Incident Creation">
                <div class="asset-caption">
                    <div><strong>FIGURE 5.1:</strong> Live Voice Heal Console on Port 3038 &bull; Offline Whisper/Qwen Intent Parser & Incident Ledger</div>
                    <div style="color:#00e5ff;">TRANSCRIBED IN 1.8S &bull; POST /api/sentinel/voice_heal</div>
                </div>
            </div>

            <div class="glass-card glass-card-emerald">
                <div class="card-title">
                    <span>Sample Operator Interaction & State Machine Transition</span>
                    <span class="badge badge-emerald">PROVEN PROTOCOL</span>
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 7.5pt; color: #cbd5e1; line-height: 1.45;">
                    <span style="color:#38bdf8;">[OPERATOR AUDIO]:</span> "Trough two is overflowing, North Gate latch is loose, check heifer forty-two."<br>
                    <span style="color:#10b981;">[VOICE HEAL ENGINE]:</span> Parsing intent &bull; Matched entity <code>animal_id: HEIFER_42</code> &bull; Sector 4 pasture coordinates.<br>
                    <span style="color:#f59e0b;">[ITSM TICKET GENERATED]:</span> Logged <code>INC0029014</code> (P2 - Infrastructure & Livestock Alert).<br>
                    <span style="color:#a78bfa;">[SYSTEM ACTION]:</span> Actuated solenoid shutoff valve on Tank #2 &bull; Dispatched gate repair work order to crew.
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 6 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 7: AGRICULTURAL EDGE VISION & BIOMETRICS                       -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>06 // AGRICULTURAL EDGE VISION & BIOMETRICS</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">COMPUTER VISION ON EMBEDDED SILICON</span>
                <h2 class="section-title">Pasture Flora Toxicology & Livestock Biometrics</h2>
                <div class="section-desc">Deploying local Hailo-8 and Raspberry Pi 5 vision arrays at chute lanes and water troughs to automate botanical toxicity detection and continuous herd scoring.</div>
            </div>

            <div class="grid-2">
                <div class="glass-card glass-card-amber">
                    <div class="card-title">
                        <span>Pasture Flora Bovine Toxicology</span>
                        <span class="badge badge-amber">WEED SCANNER</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        Toxic plant ingestion causes millions of dollars in annual livestock losses. Sovereign Sentinel vision nodes mounted on UTV sprayers and fence lines scan foliage continuously:
                    </p>
                    <ul style="font-size: 7.5pt; color: #94a3b8; padding-left: 3.5mm; line-height: 1.35;">
                        <li><strong>Bracken Fern (Pteridium):</strong> Detects thiaminase poisoning risk before neurotoxicity and bone marrow damage occurs.</li>
                        <li><strong>Jimsonweed (Datura stramonium):</strong> Flags lethal tropane alkaloid patches in disturbed grazing grounds.</li>
                        <li><strong>Black Nightshade (Solanum):</strong> Identifies solanine concentration hotspots near creeks.</li>
                        <li><strong>Perennial Ryegrass:</strong> Monitors fungal endophyte staggers risk during late summer pasture stress.</li>
                    </ul>
                </div>

                <div class="glass-card glass-card-cyan">
                    <div class="card-title">
                        <span>Automated Livestock Biometrics</span>
                        <span class="badge badge-cyan">CHUTE VISION</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        Every time cattle pass through water alley gates or mineral troughs, high-speed edge cameras capture multi-angle frames:
                    </p>
                    <ul style="font-size: 7.5pt; color: #94a3b8; padding-left: 3.5mm; line-height: 1.35;">
                        <li><strong>Body Condition Scoring (BCS 1–9):</strong> Evaluates dorsal spine fat coverage and rib prominence without human handling stress.</li>
                        <li><strong>Ocular & Nasal Telemetry:</strong> Detects early discharge, corneal opacity, and facial symmetry (Infectious Bovine Keratoconjunctivitis).</li>
                        <li><strong>Locomotion Lameness Index:</strong> Analyzes head bob and weight distribution across legs to catch foot rot 5 days early.</li>
                    </ul>
                </div>
            </div>

            <!-- Live Asset Frame -->
            <div class="asset-frame">
                <img src="{b64_ledger}" alt="Herd Ledger View and Live Telemetry">
                <div class="asset-caption">
                    <div><strong>FIGURE 6.1:</strong> Live Herd Ledger on Port 3038 &bull; Asset Valuations ($106,600 Total), RFID Tag Registry & Status</div>
                    <div style="color:#00e5ff;">REAL-TIME SQLITE LEDGER &bull; 25 HEAD ACTIVE</div>
                </div>
            </div>

            <div class="grid-4">
                <div class="metric-box">
                    <div class="metric-value">25 Head</div>
                    <div class="metric-label">Sector 4 Longhorns</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">$106,600</div>
                    <div class="metric-label">Total Asset Value</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">BCS 5.8</div>
                    <div class="metric-label">Herd Mean Condition</div>
                </div>
                <div class="metric-box">
                    <div class="metric-value">98.4%</div>
                    <div class="metric-label">Weed Class Accuracy</div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 7 OF 8</div>
        </div>
    </div>


    <!-- =================================================================== -->
    <!-- PAGE 8: WILDSEED LLC SYNERGY & INVESTMENT MATRIX                    -->
    <!-- =================================================================== -->
    <div class="page">
        <div class="page-header">
            <div class="header-brand">STACKLABS LLC <span>// SOVEREIGN SENTINEL</span></div>
            <div>07 // WILDSEED SYNERGY & INVESTMENT MATRIX</div>
        </div>

        <div class="page-content">
            <div>
                <span class="section-tag">STRATEGIC PARTNERSHIP & PRE-SEED FINANCING</span>
                <h2 class="section-title">WildSeed Synergy & Investment Matrix</h2>
                <div class="section-desc">Direct architectural crossover to WildSeed's California cannabis extraction facility and the formal pre-seed investment allocation structure.</div>
            </div>

            <div class="grid-2">
                <div class="glass-card glass-card-emerald">
                    <div class="card-title">
                        <span>WildSeed LLC California Synergy</span>
                        <span class="badge badge-emerald">1:1 CROSSOVER</span>
                    </div>
                    <p style="font-size: 7.8pt; color: #cbd5e1; margin-bottom: 2mm;">
                        The exact same edge gateway stack deployed on the ranch ports seamlessly into WildSeed's California extraction laboratory:
                    </p>
                    <ul style="font-size: 7.5pt; color: #94a3b8; padding-left: 3.5mm; line-height: 1.35;">
                        <li><strong>Hydrocarbon Extraction Pressure & Vapor:</strong> Sub-second local monitoring of closed-loop extraction rigs with zero internet latency.</li>
                        <li><strong>Decoupled Climate & Curing Vaults:</strong> Local PID control of temperature, relative humidity, and nitrogen flush without cloud dependence.</li>
                        <li><strong>Starlink Mesh Resilience:</strong> Maintains 100% telemetry, tracking, and compliance logs during rural grid outages.</li>
                    </ul>
                </div>

                <div class="glass-card glass-card-cyan">
                    <div class="card-title">
                        <span>StackLabs LLC Pre-Seed SAFE</span>
                        <span class="badge badge-cyan">TERM SHEET</span>
                    </div>
                    <table class="spec-table">
                        <tbody>
                            <tr>
                                <td><strong>Investment Instrument</strong></td>
                                <td style="color:#00e5ff; font-weight:700;">Simple Agreement for Future Equity (SAFE)</td>
                            </tr>
                            <tr>
                                <td><strong>Valuation Cap</strong></td>
                                <td style="color:#34d399; font-weight:700;">$1,500,000 USD (Post-Money)</td>
                            </tr>
                            <tr>
                                <td><strong>Target Investment Amount</strong></td>
                                <td style="color:#38bdf8; font-weight:700;">$40,000 USD</td>
                            </tr>
                            <tr>
                                <td><strong>Target Runway</strong></td>
                                <td>6 Months Hardened Operating Capital</td>
                            </tr>
                            <tr>
                                <td><strong>Primary Compute Allocation</strong></td>
                                <td>$18,000 (Dedicated Local Silicon Expansion)</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">
                    <span>Use of Funds: Disciplined Hardware & Deployment Allocation</span>
                    <span class="badge badge-cyan">CAPITAL DISCIPLINE</span>
                </div>
                <div class="grid-4" style="margin-top: 1mm;">
                    <div class="metric-box">
                        <div class="metric-value" style="font-size: 11pt;">$18,000</div>
                        <div class="metric-label">Local Silicon & Nodes (45%)</div>
                        <div style="font-size: 6pt; color: #64748b; margin-top: 1mm;">NVIDIA Orin, Mac Studio, Pi 5</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value" style="font-size: 11pt;">$12,000</div>
                        <div class="metric-label">Ranch & Lab Pilots (30%)</div>
                        <div style="font-size: 6pt; color: #64748b; margin-top: 1mm;">Sensor arrays, tags, transceivers</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value" style="font-size: 11pt;">$6,000</div>
                        <div class="metric-label">IP & Legal Ledgering (15%)</div>
                        <div style="font-size: 6pt; color: #64748b; margin-top: 1mm;">Defensive IP, SAFE compliance</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value" style="font-size: 11pt;">$4,000</div>
                        <div class="metric-label">Operating Buffer (10%)</div>
                        <div style="font-size: 6pt; color: #64748b; margin-top: 1mm;">Tailscale, domain, emergency float</div>
                    </div>
                </div>
            </div>

            <!-- Signature Block -->
            <div class="glass-card" style="margin-top: 1mm; border-color: rgba(255,255,255,0.15);">
                <div class="grid-2">
                    <div style="border-right: 1px solid rgba(255,255,255,0.08); padding-right: 4mm;">
                        <div class="cover-meta-label">LEAD SYSTEMS ARCHITECT / FOUNDER</div>
                        <div style="font-family:'Outfit', sans-serif; font-size:10pt; font-weight:700; color:#fff; margin-top:1mm;">James Carroll</div>
                        <div style="font-size:7pt; color:#94a3b8;">Founder & Lead Architect, StackLabs LLC</div>
                        <div style="margin-top: 3mm; border-bottom: 1px dashed rgba(0, 229, 255, 0.4); width: 80%;"></div>
                        <div style="font-family:'JetBrains Mono', monospace; font-size:6.5pt; color:#64748b; margin-top:1mm;">SIGNATURE // DATE: SEPTEMBER 2026</div>
                    </div>

                    <div style="padding-left: 2mm;">
                        <div class="cover-meta-label">LEAD PRE-SEED INVESTOR / STRATEGIST</div>
                        <div style="font-family:'Outfit', sans-serif; font-size:10pt; font-weight:700; color:#fff; margin-top:1mm;">Pawel Rudnicki</div>
                        <div style="font-size:7pt; color:#94a3b8;">Co-Owner, WildSeed LLC | Strategic Advisor</div>
                        <div style="margin-top: 3mm; border-bottom: 1px dashed rgba(16, 185, 129, 0.4); width: 80%;"></div>
                        <div style="font-family:'JetBrains Mono', monospace; font-size:6.5pt; color:#64748b; margin-top:1mm;">SIGNATURE // DATE: SEPTEMBER 2026</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>STACKLABS LLC &bull; SOVEREIGN OS PLATFORM</div>
            <div class="footer-secure">&bull; IMMUTABLE LOCAL LEDGER // 100% DECOUPLED</div>
            <div>PAGE 8 OF 8</div>
        </div>
    </div>

</body>
</html>
"""
    return html

def compile_pdf():
    print(f"Generating HTML template at: {OUTPUT_HTML}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_TODAY.mkdir(parents=True, exist_ok=True)

    html_content = build_prospectus_html()
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ HTML template written ({len(html_content)} bytes)")

    # Execute Chrome 150 Headless
    chrome_bin = "/home/james/.local/bin/google-chrome"
    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=8000",
        f"--print-to-pdf={OUTPUT_PDF}",
        f"file://{OUTPUT_HTML}"
    ]

    print(f"Executing Headless Chrome compilation to: {OUTPUT_PDF}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Error compiling PDF: {res.stderr}")
        sys.exit(1)

    if not OUTPUT_PDF.exists() or OUTPUT_PDF.stat().st_size == 0:
        print("❌ PDF was not generated or is 0 bytes.")
        sys.exit(1)

    pdf_size = OUTPUT_PDF.stat().st_size
    print(f"🎉 PDF successfully compiled! Size: {pdf_size:,} bytes")

    # Check page count
    try:
        page_count_res = subprocess.run(["pdfinfo", str(OUTPUT_PDF)], capture_output=True, text=True)
        for line in page_count_res.stdout.splitlines():
            if "Pages:" in line:
                print(f"📄 Document Page Count: {line.strip()}")
    except Exception:
        pass

    # Register in sys_media_asset / cmdb_ci_media_asset via FastAPI REST
    register_media_asset()

    # Rclone Sync to GDrive
    sync_to_gdrive()

def register_media_asset():
    print("Registering PDF asset in Sovereign Media Ledgers...")
    try:
        from scripts.core.api_client import upload_ticket_attachment
        ticket_id = "WO0010102-SENTINEL-PROSPECTUS-EXECUTIVE-DOSSI"
        res = upload_ticket_attachment(
            ticket_id=ticket_id,
            file_path=str(OUTPUT_PDF),
            description="Sovereign Sentinel Executive Brief & Technical Prospectus PDF for Pawel Rudnicki"
        )
        print(f"✅ Attachment registered to ticket {ticket_id}: {res}")
    except Exception as e:
        print(f"⚠️ Note on ticket attachment: {e}")

def sync_to_gdrive():
    print("Syncing generated prospectus to Google Drive via rclone...")
    try:
        date_folder = subprocess.check_output(["date", "+%Y-%m-%d"], text=True).strip()
        cmd_inbox = [
            "rclone", "copy",
            str(OUTPUT_PDF),
            f"sovereign_os:SovereignOS/Inbox/{date_folder}/",
            "--progress"
        ]
        cmd_exports = [
            "rclone", "copy",
            str(OUTPUT_PDF),
            "sovereign_os:SovereignOS/persona_exports/",
            "--progress"
        ]
        res1 = subprocess.run(cmd_inbox, capture_output=True, text=True)
        res2 = subprocess.run(cmd_exports, capture_output=True, text=True)
        print(f"✅ Rclone sync status: Inbox ({res1.returncode}), Persona Exports ({res2.returncode})")
    except Exception as e:
        print(f"⚠️ Warning on rclone sync: {e}")

if __name__ == "__main__":
    compile_pdf()
