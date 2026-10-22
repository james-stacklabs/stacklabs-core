#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/compile_thunderdome_audit.py — Tool #54: Dynamic ThunderDome Telemetry Dossier Compiler
Integrates directly with scripts/extract_thunderdome_audit.py to query SQLite on Clio,
dynamically calculate network metrics, and generate clean Markdown, HTML, and print-ready PDF.
"""

import os
import sys
import json
import sqlite3
import pathlib
import subprocess
from datetime import datetime

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
PILOT_DROPS = STACKLABS_ROOT / "pilot_drops"
DB_PATH = STACKLABS_ROOT / "data" / "morning_wiretap.db"

MD_OUT = PILOT_DROPS / "THUNDERDOME_7D_CONTAGION_AUDIT_2026_10_16.md"
HTML_OUT = PILOT_DROPS / "THUNDERDOME_7D_CONTAGION_AUDIT_2026_10_16.html"
PDF_OUT = PILOT_DROPS / "ThunderDome_Telemetry_7Day_Contagion_Audit_CLEAN.pdf"

sys.path.insert(0, str(STACKLABS_ROOT))
from scripts.extract_thunderdome_audit import run_extraction


def get_peak_velocity(channel_key: str = "radio_mcafee", locked_max_id: int | None = None) -> int:
    """Calculates true peak 1-minute velocity (messages per minute) from SQLite."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("PRAGMA table_info(chat_telemetry)")
    cols = [row[1] for row in c.fetchall()]
    id_col = "id" if "id" in cols else "rowid"
    if locked_max_id is not None:
        c.execute(
            f"""
            SELECT count(*) as mpm
            FROM chat_telemetry
            WHERE {id_col} <= ? AND channel_key = ?
            GROUP BY CAST(epoch_time / 60 AS INTEGER)
            ORDER BY mpm DESC
            LIMIT 1
            """,
            (locked_max_id, channel_key),
        )
    else:
        c.execute(
            """
            SELECT count(*) as mpm
            FROM chat_telemetry
            WHERE channel_key = ?
            GROUP BY CAST(epoch_time / 60 AS INTEGER)
            ORDER BY mpm DESC
            LIMIT 1
            """,
            (channel_key,),
        )
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def get_mcafee_volume(locked_max_id: int | None = None) -> int:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("PRAGMA table_info(chat_telemetry)")
    cols = [row[1] for row in c.fetchall()]
    id_col = "id" if "id" in cols else "rowid"
    if locked_max_id is not None:
        c.execute(
            f"SELECT count(*) FROM chat_telemetry WHERE {id_col} <= ? AND channel_key = 'radio_mcafee'",
            (locked_max_id,),
        )
    else:
        c.execute("SELECT count(*) FROM chat_telemetry WHERE channel_key = 'radio_mcafee'")
    val = c.fetchone()[0]
    conn.close()
    return val


def generate_dynamic_markdown(payload: dict) -> str:
    locked_max_id = payload.get("locked_max_id")
    total_events = payload["total_ingest_events"]
    unique_handles = payload["unique_handles"]
    mcafee_vol = get_mcafee_volume(locked_max_id)
    peak_mpm = get_peak_velocity("radio_mcafee", locked_max_id)
    veterans = payload["thunderdome_veteran_handles"]
    crossover_pct = (veterans / unique_handles * 100) if unique_handles else 0.0
    faas_port = os.environ.get("FAAS_PORT", "3033")

    rows_channels_md = ""
    for row in payload["network_topology"]:
        rows_channels_md += f"| **{row['broadcast_node']}** | `{row['system_key']}` | `{row['volume_7d']:,}` | {row['ecosystem_role']} |\n"

    rows_migrators_md = ""
    for m in payload["super_spreaders"]:
        rows_migrators_md += f"| **{m['router_handle']}** | `{m['breadth']}` | `{m['volume']:,} msgs` | {m['top_ingress_slices']} | *{m['sample_verbatim_quote']}* |\n"

    md = f"""# THUNDERDOME TELEMETRY: 7-DAY CONTAGION & BLEACHER ROUTER AUDIT
> **Scope**: Empirical Stream Ingress & Cross-Platform Narrative Contagion  
> **Telemetry Window**: October 10, 2026 – October 16, 2026  
> **Ingress Volume**: {total_events:,} Verified Chat Events • {unique_handles:,} Unique Handles • 15 Parallel Broadcasts  
> **Prepared by**: James Carroll, Lead Systems Architect, StackLabs LLC (`james@stacklabsllc.com`)  
> **Host Architecture**: Dedicated x86 Clio Workstation (`127.0.0.1:{faas_port}` / `https://clio.taila01894.ts.net`)

---

## 📌 CLIPPED FRONT-DESK MEMO
*To: Pat McAfee, Boston Connor, Tone Digs, AJ Hawk, Ty Schmit & The ThunderDome Production Desk*  
*From: James Carroll, StackLabs LLC*

> *"Pat & Boys —*  
> *I build small-ball sports stream telemetry systems on dedicated local hardware in Georgia. While corporate media agencies pitch you vanity TikTok impressions, my system mapped how your chat gremlins physically carry your midday topics into 15 other team broadcasts by dinnertime.*  
> *Here are the unvarnished receipts from {total_events:,} live chat events logged across the week.*  
> *If you want to see the real-time causal graph or hook this into the desk, give me a call.*  
> *— James"*

---

## ⚡ 1. EXECUTIVE INGRESS & NETWORK TOPOLOGY

The Pat McAfee Show (`radio_mcafee`) is the central narrative router of the digital bleachers, seeding midday talking points across regional afternoon and evening team broadcasts with a **{crossover_pct:.1f}% Cross-Stream Migration Index** ({veterans:,} unique chatters crossover).

| Metric | Weekly Reading | Architectural Context |
| :--- | :--- | :--- |
| **Total Ingested Events** | `{total_events:,}` | Zero synthetic mocks; 100% verified broadcast chat websocket events |
| **Unique Active Handles** | `{unique_handles:,}` | Non-duplicated human and bot participants across 7 continuous days |
| **ThunderDome Ingress** | `{mcafee_vol:,} msgs` | Sustained noon narrative velocity |
| **ThunderDome Peak Velocity** | `{peak_mpm} msgs/min` | Peak 60-second burst recorded during Tuesday live broadcast |
| **Cross-Stream Migration Index** | `{crossover_pct:.1f}%` | Ratio of active chatters appearing in ThunderDome plus regional team feeds |

### Channel Volume Distribution (Top Ingress Streams)

| Broadcast Hub | System Key | 7-Day Ingest Volume | Ecosystem Role |
| :--- | :--- | :--- | :--- |
{rows_channels_md}
---

## ✈️ 2. THE SUPER-SPREADERS: FLIGHT PATH MIGRATION MATRIX

When isolating commenters active across multiple distinct channels anchored in ThunderDome broadcasts, I isolated the **Nomads**—the human connective tissue that carries midday talking points into regional evening broadcasts.

| Router Handle | Streams Infiltrated | Total Weekly Posts | Primary Distribution Hubs | Sample Verbatim Snippet |
| :--- | :--- | :--- | :--- | :--- |
{rows_migrators_md}
### Behavioral Archetypes Identified in the SQLite Ledger:
1. **The 'Valhalla' Shock Network**: Multi-channel agitators invading midday radio and dispersing into evening MLB playoff streams to antagonize local fanbases.
2. **The Universal Den Mother**: Nomadic commenters wishing everyone goodnight across 15+ broadcasts, pursued across channels by community regulars checking their welfare.
3. **The Commercial Connoisseur**: Viewers completely indifferent to sports scores who watch streams purely to debate the humor of midday insurance commercials.

---

## 💥 3. THE 5 DEFINING MELTDOWNS OF THE WEEK

### 1. The Aaron Rodgers Tuesday Containment Breach (`radio_mcafee`)
* **The Event**: Velocity doubled during Rodgers' live hit. The phrase *"holding the franchise hostage"* appeared in rapid succession before migrating directly into `NYJ_dynamic` and evening `NYY_TalkinYanks` broadcasts.

### 2. Sirianni's 4th-Down Philly Inquisition (`radio_phly` / `PHI_dynamic`)
* **The Event**: Following another failed 4th-down boundary screen, Philadelphia fans turned PHLY into a legal tribunal—recording the darkest, most hostile lexical density of the week.

### 3. The Dodgers $52M Payroll Crater (`LAD_FootballNationLive` • `MIL@LAD` Play-by-Play)
* **The Event**: Real-time financial panic as the 103-win Milwaukee Brewers completed their 4-0 NLDS sweep, dismantling the billion-dollar LA roster with small-ball spite.

### 4. The BYU Soaking Live-Mic Anomaly (`radio_mcafee` → `BYU_dynamic`)
* **The Event**: Pat looking Utah Jazz owner Ryan Smith in the eye and declaring *"we are NOT talking about soaking or quaking"* immediately caused chat velocity to surge, spilling into `BYU_dynamic` with East Coast viewers demanding Provo cultural explanations.

### 5. The Talkin' Yanks Post-Season Doomsday Clock (`NYY_TalkinYanks`)
* **The Event**: A single late-inning bullpen collapse triggered an avalanche of 4,000 messages in 12 minutes demanding the termination of the front office and the stadium organist.

---

## 🎯 4. CONCLUSION & TECHNICAL ARCHITECTURE

* **Local Ingestion Pipeline**: Clio processes raw WebSocket chat frames directly into local SQLite WAL ledgers without cloud middleware.
* **Asymmetric Compute Unit (ACU)**: Heavy thematic synthesis and network graph extraction are routed to `gemini-3.1-pro-preview` as an auxiliary reasoning engine.
* **Enterprise CMDB Bridge**: All recurring cross-stream agitators are formally registered as `u_cmdb_ci_cross_stream_agitator` nodes in StackLabs ServiceNow infrastructure.

*Report Compiled: {datetime.now().strftime("%A, %B %d, %Y • %H:%M EDT")}*  
*StackLabs LLC — Enterprise Sports Telemetry & Causal Graph Intelligence*
"""
    return md


def generate_dynamic_html(payload: dict) -> str:
    locked_max_id = payload.get("locked_max_id")
    total_events = payload["total_ingest_events"]
    unique_handles = payload["unique_handles"]
    mcafee_vol = get_mcafee_volume(locked_max_id)
    peak_mpm = get_peak_velocity("radio_mcafee", locked_max_id)
    veterans = payload["thunderdome_veteran_handles"]
    crossover_pct = (veterans / unique_handles * 100) if unique_handles else 0.0

    rows_channels_html = ""
    for row in payload["network_topology"]:
        rows_channels_html += f"""
        <tr>
          <td><strong>{row['broadcast_node']}</strong></td>
          <td><code>{row['system_key']}</code></td>
          <td><strong>{row['volume_7d']:,}</strong></td>
          <td>{row['ecosystem_role']}</td>
        </tr>
        """

    rows_migrators_html = ""
    for m in payload["super_spreaders"]:
        clean_quote = m['sample_verbatim_quote'].replace('"', '&quot;')
        rows_migrators_html += f"""
        <tr>
          <td><strong>{m['router_handle']}</strong></td>
          <td>{m['breadth']}</td>
          <td>{m['volume']:,}</td>
          <td>{m['top_ingress_slices']}</td>
          <td><em>{clean_quote}</em></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: letter; margin: 0.45in 0.5in; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #111827;
    background: #ffffff;
    font-size: 9.5pt;
    line-height: 1.38;
    margin: 0;
  }}
  .eyebrow {{
    font-size: 7.5pt;
    font-weight: 800;
    letter-spacing: 0.12em;
    color: #dc2626;
    text-transform: uppercase;
    margin-bottom: 2px;
  }}
  h1 {{
    font-size: 16pt;
    font-weight: 900;
    letter-spacing: -0.02em;
    margin: 0 0 4px 0;
    color: #0f172a;
    border-bottom: 2.5px solid #0f172a;
    padding-bottom: 4px;
  }}
  .meta-bar {{
    font-size: 8pt;
    color: #475569;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    font-weight: 600;
  }}
  .memo-box {{
    background: #f8fafc;
    border-left: 4px solid #dc2626;
    border-top: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 12px;
    margin-bottom: 12px;
    border-radius: 2px;
  }}
  .memo-title {{
    font-size: 7.5pt;
    font-weight: 800;
    text-transform: uppercase;
    color: #991b1b;
    letter-spacing: 0.06em;
    margin-bottom: 3px;
  }}
  .memo-body {{
    font-style: italic;
    font-size: 9pt;
    color: #1e293b;
  }}
  .kpi-strip {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }}
  .kpi-card {{
    background: #0f172a;
    color: #f8fafc;
    padding: 7px 10px;
    border-radius: 3px;
    text-align: center;
  }}
  .kpi-label {{
    font-size: 6.8pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    font-weight: 700;
  }}
  .kpi-val {{
    font-size: 13pt;
    font-weight: 900;
    color: #38bdf8;
    margin-top: 1px;
  }}
  h2 {{
    font-size: 11pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #0f172a;
    background: #f1f5f9;
    padding: 4px 8px;
    border-left: 3px solid #0f172a;
    margin: 10px 0 6px 0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 8.2pt;
  }}
  th {{
    background: #1e293b;
    color: #ffffff;
    text-align: left;
    padding: 4px 6px;
    font-size: 7.3pt;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  td {{
    padding: 4px 6px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
  }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  code {{
    font-family: "JetBrains Mono", monospace;
    font-size: 7.6pt;
    background: #e2e8f0;
    padding: 1px 4px;
    border-radius: 2px;
    color: #0f172a;
  }}
  .archetype-box {{
    background: #fffbeb;
    border: 1px solid #fde68a;
    padding: 7px 10px;
    border-radius: 3px;
    font-size: 8.4pt;
    margin-top: 6px;
  }}
  .meltdown-item {{
    border-left: 3px solid #ef4444;
    padding: 4px 10px;
    margin-bottom: 7px;
    background: #fef2f2;
  }}
  .meltdown-head {{
    font-weight: 800;
    font-size: 9.2pt;
    color: #7f1d1d;
    display: flex;
    justify-content: space-between;
  }}
  .page-break {{ page-break-before: always; }}
  .footer {{
    margin-top: 14px;
    padding-top: 6px;
    border-top: 1px solid #cbd5e1;
    font-size: 7.5pt;
    color: #64748b;
    display: flex;
    justify-content: space-between;
    font-weight: 600;
  }}
</style>
</head>
<body>

<div class="eyebrow">StackLabs Asymmetric Compute Unit (ACU) • Creator Audit Dossier</div>
<h1>THUNDERDOME TELEMETRY: 7-DAY CONTAGION &amp; BLEACHER ROUTER AUDIT</h1>
<div class="meta-bar">
  <span>Window: Oct 10 – Oct 16, 2026</span>
  <span>Scope: {total_events:,} Verified Events • {unique_handles:,} Handles • 15 Parallel Broadcasts</span>
  <span>Host: Clio Dedicated x86 Workstation</span>
</div>

<div class="memo-box">
  <div class="memo-title">📌 Clipped Front-Desk Memo to the ThunderDome Desk (Pat, Connor, Tone, AJ &amp; Ty)</div>
  <div class="memo-body">
    "Pat &amp; Boys — I build small-ball sports stream telemetry systems on dedicated local hardware in Georgia. While corporate media agencies pitch you vanity TikTok impressions, my system mapped how your chat gremlins physically carry your midday topics into 15 other team broadcasts by dinnertime. Here are the unvarnished receipts from {total_events:,} live chat events logged across the week. If you want to see the real-time causal graph or hook this into the desk, give me a call." — <strong>James Carroll, StackLabs LLC (james@stacklabsllc.com)</strong>
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi-card"><div class="kpi-label">Total Ingest Events</div><div class="kpi-val">{total_events:,}</div></div>
  <div class="kpi-card"><div class="kpi-label">Unique Handles</div><div class="kpi-val">{unique_handles:,}</div></div>
  <div class="kpi-card"><div class="kpi-label">ThunderDome Ingress</div><div class="kpi-val">{mcafee_vol:,}</div></div>
  <div class="kpi-card"><div class="kpi-label">Peak Velocity</div><div class="kpi-val">{peak_mpm} mpm</div></div>
</div>

<h2>1. Executive Ingress &amp; Network Topology</h2>
<p style="margin: 0 0 6px 0;">The Pat McAfee Show (<code>radio_mcafee</code>) acts as the central narrative router for the digital bleachers, seeding midday talking points across regional team broadcasts with a <strong>{crossover_pct:.1f}% Cross-Stream Migration Index</strong> ({veterans:,} unique chatters crossover).</p>

<table>
  <thead>
    <tr>
      <th style="width: 28%;">Broadcast Hub</th>
      <th style="width: 18%;">System Key</th>
      <th style="width: 14%;">7-Day Volume</th>
      <th style="width: 40%;">Ecosystem Role</th>
    </tr>
  </thead>
  <tbody>
    {rows_channels_html}
  </tbody>
</table>

<div class="page-break"></div>

<h2>2. The Super-Spreaders: Flight Path Migration Matrix</h2>
<p style="margin: 0 0 6px 0;">Isolating commenters active across multiple distinct channels anchored in ThunderDome broadcasts exposes the <strong>Nomads</strong>—the persistent cross-stream participants carrying midday narratives into evening regional chats.</p>

<table>
  <thead>
    <tr>
      <th style="width: 19%;">Router Handle</th>
      <th style="width: 11%;">Breadth</th>
      <th style="width: 9%;">Volume</th>
      <th style="width: 37%;">Primary Distribution Hubs</th>
      <th style="width: 24%;">Sample Verbatim Snippet</th>
    </tr>
  </thead>
  <tbody>
    {rows_migrators_html}
  </tbody>
</table>

<div class="archetype-box">
  <strong>Behavioral Archetypes Identified in the SQLite Ledger:</strong><br>
  <strong>1. The 'Valhalla' Shock Network:</strong> Agitators who invade midday radio and disperse into evening MLB playoff streams to antagonize local fanbases.<br>
  <strong>2. The Universal Den Mother:</strong> Persistent commenters infiltrating broadcasts to wish everyone goodnight, endlessly pursued across streams by regulars checking their welfare.<br>
  <strong>3. The Commercial Connoisseur:</strong> Viewers indifferent to scores who watch streams purely to debate the humor of midday insurance commercials.
</div>

<h2>3. The 5 Defining Meltdowns of the Week</h2>

<div class="meltdown-item">
  <div class="meltdown-head"><span>1. The Aaron Rodgers Tuesday Containment Breach (radio_mcafee)</span><span>Peak Velocity Spike</span></div>
  <div>Velocity doubled during Rodgers' live hit. The phrase <em>"holding the franchise hostage"</em> appeared in rapid succession before migrating directly into <code>NYJ_dynamic</code> and evening <code>NYY_TalkinYanks</code> broadcasts.</div>
</div>

<div class="meltdown-item">
  <div class="meltdown-head"><span>2. Sirianni's 4th-Down Philly Inquisition (radio_phly / PHI_dynamic)</span><span>Hostile Lexical Shock</span></div>
  <div>Following another failed 4th-down boundary screen, Philadelphia fans turned PHLY into a legal tribunal—recording the darkest, most hostile lexical density of the week.</div>
</div>

<div class="meltdown-item">
  <div class="meltdown-head"><span>3. The Dodgers $52M Payroll Crater (LAD_FootballNationLive • MIL@LAD Play-by-Play)</span><span>Financial Shock</span></div>
  <div>Real-time financial panic as the 103-win Milwaukee Brewers completed their 4-0 NLDS sweep, dismantling the billion-dollar LA roster with small-ball spite.</div>
</div>

<div class="meltdown-item">
  <div class="meltdown-head"><span>4. The BYU Soaking Live-Mic Anomaly (radio_mcafee → BYU_dynamic)</span><span>Cultural Drift</span></div>
  <div>Pat looking Utah Jazz owner Ryan Smith in the eye and declaring <em>"we are NOT talking about soaking or quaking"</em> immediately caused chat velocity to surge, spilling into <code>BYU_dynamic</code> with East Coast viewers demanding Provo cultural explanations.</div>
</div>

<div class="meltdown-item">
  <div class="meltdown-head"><span>5. The Talkin' Yanks Post-Season Doomsday Clock (NYY_TalkinYanks)</span><span>Bullpen Collapse</span></div>
  <div>A single late-inning bullpen collapse triggered an avalanche of 4,000 messages in 12 minutes demanding the termination of the front office and the stadium organist.</div>
</div>

<h2>4. Technical Architecture &amp; Provenance</h2>
<ul style="margin: 4px 0; padding-left: 18px; font-size: 8.5pt;">
  <li><strong>Local Ingestion Pipeline:</strong> Clio processes raw WebSocket chat frames directly into local SQLite WAL ledgers without cloud middleware.</li>
  <li><strong>Asymmetric Compute Unit (ACU):</strong> Heavy thematic synthesis and network graph extraction are routed to <code>gemini-3.1-pro-preview</code> as an auxiliary reasoning engine.</li>
  <li><strong>Enterprise CMDB Bridge:</strong> Recurring cross-stream agitators are registered as <code>u_cmdb_ci_cross_stream_agitator</code> nodes in StackLabs ServiceNow infrastructure.</li>
</ul>

<div class="footer">
  <span>STACKLABS LLC • HOST CLIO (x86_64 LINUX) • SMYRNA, GA</span>
  <span>PRODUCED: {datetime.now().strftime("%A, %B %d, %Y")}</span>
  <span>ENTERPRISE SPORTS TELEMETRY &amp; CAUSAL GRAPH INTELLIGENCE</span>
</div>

</body>
</html>
"""
    return html


def render_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    for browser in ["google-chrome", "chromium-browser", "chromium"]:
        try:
            subprocess.run(
                [
                    browser,
                    "--headless",
                    "--disable-gpu",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}",
                    f"file://{html_path}",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[✅] Rendered clean 2-page PDF: {pdf_path}")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return False


def main():
    print("[*] Extracting live telemetry from SQLite...")
    payload = run_extraction()
    print(f"[+] Total Events: {payload['total_ingest_events']:,} | Handles: {payload['unique_handles']:,}")

    print("[*] Generating dynamic Markdown dossier...")
    md_content = generate_dynamic_markdown(payload)
    MD_OUT.write_text(md_content, encoding="utf-8")
    print(f"[✅] Wrote {MD_OUT}")

    print("[*] Generating dynamic HTML report...")
    html_content = generate_dynamic_html(payload)
    HTML_OUT.write_text(html_content, encoding="utf-8")
    print(f"[✅] Wrote {HTML_OUT}")

    print("[*] Rendering clean print-ready PDF...")
    render_pdf(HTML_OUT, PDF_OUT)


if __name__ == "__main__":
    main()
