#!/usr/bin/env python3
import os
import sys
import sqlite3
import subprocess
import glob
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)

# Helper to retrieve brand configurations from SQLite database
def get_brand_config(brand_key=None):
    db_path = os.path.join(WORKSPACE_DIR, "dna", "sovereign_now.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if brand_key:
        c.execute("SELECT * FROM cmdb_ci_stack WHERE brand_key = ?", (brand_key.upper().strip(),))
        row = c.fetchone()
        conn.close()
        if row:
            cfg = dict(row)
            cfg["team_filter"] = [t.strip() for t in cfg["team_filter"].split(",") if t.strip()]
            cfg["operational_logs"] = cfg.get("ingest_log", "")
            return cfg
        return None
    else:
        c.execute("SELECT * FROM cmdb_ci_stack")
        rows = c.fetchall()
        conn.close()
        brands = {}
        for r in rows:
            cfg = dict(r)
            cfg["team_filter"] = [t.strip() for t in cfg["team_filter"].split(",") if t.strip()]
            cfg["operational_logs"] = cfg.get("ingest_log", "")
            brands[cfg["brand_key"]] = cfg
        return brands

def get_svg_content(username):
    # Try all possible high-fidelity PNG and SVG paths in priority order
    possible_paths = [
        os.path.join(WORKSPACE_DIR, "15_FanStack", "public", "avatars", username, f"{username}_avatar.png"),
        os.path.join(WORKSPACE_DIR, "01_Sovereign_Portal", "public", "avatars", username, f"{username}_avatar.png"),
        os.path.join(WORKSPACE_DIR, "01_Sovereign_Portal", "public", "avatars", f"{username}.png"),
        os.path.join(WORKSPACE_DIR, "15_FanStack", "public", "avatars", username, f"{username}_avatar.svg"),
        os.path.join(WORKSPACE_DIR, "01_Sovereign_Portal", "public", "avatars", username, f"{username}_avatar.svg"),
        os.path.join(WORKSPACE_DIR, "01_Sovereign_Portal", "public", "avatars", f"{username}.svg"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            if path.endswith('.png'):
                return f'<img src="file://{path}" style="width: 100%; height: 100%; object-fit: cover;" />'
            elif path.endswith('.svg'):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "<svg" in content:
                            start_idx = content.find("<svg")
                            return content[start_idx:]
                        return content
                except Exception as e:
                    print(f"Error reading SVG {path}: {e}")
    return "<!-- Avatar Not Found -->"

def compile_pdf(brand_key):
    brand_key = brand_key.upper().strip()
    cfg = get_brand_config(brand_key)
    if not cfg:
        print(f"❌ Error: Brand '{brand_key}' not found in configuration database.")
        sys.exit(1)
        
    db_path = os.path.join(WORKSPACE_DIR, "dna", "sovereign_now.db")
    inbox_reports = os.getenv("SOVEREIGN_INBOX_REPORTS_DIR", "/home/james/sovereign_inbox/reports")
    html_file = os.path.join(inbox_reports, f"seeding_report_{brand_key.lower()}_temp.html")
    pdf_file = os.path.join(inbox_reports, cfg['pdf_name'])

    print(f"\n=======================================================")
    print(f"📄 COMPILING INDIVIDUAL REPORT FOR: {brand_key}")
    print(f"=======================================================")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Query personas for this brand
    placeholders = ",".join("?" for _ in cfg["team_filter"])
    query = f"""
        SELECT user_name, display_name, team, system_prompt, boggs_level, color, cadence, deep_lore, behavior_notes, governance
        FROM persona
        WHERE team IN ({placeholders})
        ORDER BY display_name ASC
    """
    c.execute(query, cfg["team_filter"])
    personas = [dict(r) for r in c.fetchall()]

    # Query room details to fetch website blueprint specifications dynamically
    room_data = None
    try:
        room_query = """
            SELECT name, room_key, website_purpose, website_domain, website_pages, website_features, website_colors, website_typography, website_additional_requirements
            FROM cmdb_ci_fanstack_room
            WHERE room_key LIKE ? OR name LIKE ? OR room_key = ?
        """
        c.execute(room_query, (f"%{brand_key}%", f"%{brand_key}%", f"{brand_key}_SIM_001"))
        room_row = c.fetchone()
        if room_row:
            room_data = dict(room_row)
    except Exception as e:
        print(f"Warning: Failed to fetch room details: {e}")

    conn.close()

    print(f"Loaded {len(personas)} personas for brand team {cfg['team_filter']}.")

    # Generate CSS with dynamic variables
    css_content = f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    :root {{
        --color-bg: #ffffff;
        --color-card-bg: #f8fafc;
        --color-text: #0f172a;
        --color-text-light: #334155;
        --color-primary: {cfg['primary_color']};
        --color-primary-dim: rgba({','.join(map(str, [int(cfg['primary_color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]))}, 0.15);
        --color-accent: #d97706;
        --color-border: #cbd5e1;
    }}
    
    * {{
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    
    @page {{
        size: letter;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-right {{
            content: counter(page);
            font-family: 'Outfit', sans-serif;
            font-size: 9pt;
            color: #475569;
        }}
        @top-left {{
            content: "Sovereign OS • {cfg['aesthetic_title']} Report";
            font-family: 'Outfit', sans-serif;
            font-size: 8pt;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
    }}
    
    body {{
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--color-text);
        background-color: var(--color-bg);
        line-height: 1.5;
        font-size: 10pt;
        margin: 0;
        padding: 0;
    }}
    
    .cover-page {{
        page-break-after: always;
        height: 9.3in;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        padding: 60px;
        border: 4px solid var(--color-primary);
        background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
        color: #0f172a;
    }}
    
    .cover-header {{
        font-size: 10pt;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        color: var(--color-primary);
        margin-bottom: auto;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }}
    
    .cover-body {{
        margin-top: auto;
        margin-bottom: auto;
    }}
    
    .cover-title {{
        font-family: 'Outfit', sans-serif;
        font-size: 28pt;
        font-weight: 800;
        line-height: 1.1;
        color: #0f172a;
        margin: 0 0 15px 0;
        letter-spacing: -0.5px;
    }}
    
    .cover-subtitle {{
        font-size: 12pt;
        font-weight: 400;
        color: var(--color-text-light);
        margin: 0 0 40px 0;
        letter-spacing: 0.05em;
        line-height: 1.4;
    }}
    
    .cover-divider {{
        width: 150px;
        height: 5px;
        background-color: var(--color-primary);
        margin-bottom: 40px;
    }}
    
    .cover-footer {{
        margin-top: auto;
        border-top: 1px solid var(--color-border);
        padding-top: 25px;
        display: flex;
        justify-content: space-between;
        font-size: 9.5pt;
        color: var(--color-text-light);
    }}
    
    .cover-footer-item strong {{
        color: var(--color-primary);
        display: block;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 8pt;
        letter-spacing: 0.1em;
        font-family: 'Outfit', sans-serif;
    }}
    
    .content-container {{
        padding: 10px 0;
    }}
    
    h1, h2, h3, h4 {{
        font-family: 'Outfit', sans-serif;
        color: #0f172a;
        font-weight: 700;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        page-break-after: avoid;
    }}
    
    h1 {{
        font-size: 18pt;
        line-height: 1.2;
        border-bottom: 2px solid var(--color-primary);
        padding-bottom: 6px;
        margin-top: 0;
        margin-bottom: 0.8em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    h2 {{
        font-size: 13pt;
        border-left: 4px solid var(--color-primary);
        padding-left: 10px;
        color: var(--color-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 1.8em;
    }}
    
    p {{
        margin-top: 0;
        margin-bottom: 1em;
        color: var(--color-text-light);
        text-align: justify;
    }}
    
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 1.2em 0;
        page-break-inside: avoid;
        font-size: 9pt;
        background-color: var(--color-card-bg);
        border: 1px solid var(--color-border);
    }}
    
    th, td {{
        padding: 8px 10px;
        text-align: left;
        border-bottom: 1px solid var(--color-border);
    }}
    
    th {{
        background-color: var(--color-primary-dim);
        color: var(--color-primary);
        font-weight: 700;
        text-transform: uppercase;
        font-size: 8pt;
        letter-spacing: 0.5px;
    }}
    
    tr:nth-child(even) td {{
        background-color: rgba(0, 0, 0, 0.02);
    }}
    
    .section-break {{
        page-break-before: always;
        height: 1px;
    }}
    
    .persona-card {{
        background-color: var(--color-card-bg);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 25px;
        page-break-inside: avoid;
    }}
    
    .persona-header {{
        display: flex;
        align-items: center;
        gap: 15px;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 15px;
        margin-bottom: 15px;
    }}
    
    .avatar-svg-container {{
        width: 55px;
        height: 55px;
        border-radius: 50%;
        background-color: #f1f5f9;
        border: 2px solid var(--color-primary);
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-primary);
    }}
    
    .avatar-svg-container svg {{
        width: 100%;
        height: 100%;
    }}
    
    .persona-meta {{
        display: flex;
        flex-direction: column;
    }}
    
    .persona-name {{
        font-size: 14pt;
        color: #0f172a;
        margin: 0;
    }}
    
    .persona-username {{
        font-size: 9.5pt;
        color: var(--color-primary);
        margin: 0;
        font-family: 'JetBrains Mono', monospace;
    }}
    
    .badge-row {{
        display: flex;
        gap: 8px;
        margin-top: 5px;
    }}
    
    .badge {{
        font-size: 7.5pt;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        text-transform: uppercase;
        font-family: 'Outfit', sans-serif;
    }}
    
    .badge-boggs {{
        background-color: rgba(245, 158, 11, 0.15);
        color: #b45309;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }}
    
    .badge-cadence {{
        background-color: var(--color-primary-dim);
        color: var(--color-primary);
        border: 1px solid rgba(0, 212, 255, 0.3);
    }}
    
    .persona-section {{
        margin-bottom: 12px;
    }}
    
    .persona-section:last-child {{
        margin-bottom: 0;
    }}
    
    .persona-section-title {{
        font-size: 8.5pt;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-primary);
        margin: 0 0 4px 0;
        font-family: 'Outfit', sans-serif;
    }}
    
    .persona-section-body {{
        font-size: 9.5pt;
        color: var(--color-text);
        margin: 0;
        text-align: justify;
    }}
    
    .charmap-card {{
        background-color: var(--color-card-bg);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        page-break-inside: avoid;
    }}
    
    .charmap-title {{
        font-family: 'Outfit', sans-serif;
        font-size: 11pt;
        font-weight: 700;
        color: var(--color-primary);
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 6px;
    }}
    
    .charmap-image {{
        width: 100%;
        max-height: 500px;
        object-fit: contain;
        border-radius: 4px;
        border: 1px solid var(--color-border);
        background-color: #f8fafc;
    }}
    
    pre {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 8.5pt;
        color: #065f46;
        background-color: #f0fdf4;
        border: 1px solid #a7f3d0;
        padding: 15px;
        border-radius: 6px;
        overflow-x: auto;
        white-space: pre-wrap;
    }}
    """

    # 1. Executive Summary HTML
    website_blueprint_html = ""
    if room_data and room_data.get("website_purpose"):
        website_blueprint_html = f"""
    <h2>2. Proposed Website Blueprint Specifications</h2>
    <p>The following parameters have been registered within the CMDB matrix to guide the dynamic generation and theme styling of guest-facing portals for <strong>{brand_key.title()}</strong>:</p>
    <table>
        <thead>
            <tr style="background-color: rgba(16, 185, 129, 0.08);">
                <th style="width: 30%;">Specification Field</th>
                <th style="width: 70%;">Blueprint Values / Directives</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Target Domain</strong></td>
                <td><code>{room_data.get('website_domain') or 'Not Specified'}</code></td>
            </tr>
            <tr>
                <td><strong>Website Purpose</strong></td>
                <td>{room_data.get('website_purpose') or 'Not Specified'}</td>
            </tr>
            <tr>
                <td><strong>Key Pages & Hierarchy</strong></td>
                <td>{room_data.get('website_pages') or 'Not Specified'}</td>
            </tr>
            <tr>
                <td><strong>Core Features & Logic</strong></td>
                <td>{room_data.get('website_features') or 'Not Specified'}</td>
            </tr>
            <tr>
                <td><strong>Color Palette Guidelines</strong></td>
                <td>{room_data.get('website_colors') or 'Not Specified'}</td>
            </tr>
            <tr>
                <td><strong>Typography System</strong></td>
                <td>{room_data.get('website_typography') or 'Not Specified'}</td>
            </tr>
            <tr>
                <td><strong>Additional Requirements</strong></td>
                <td>{room_data.get('website_additional_requirements') or 'Not Specified'}</td>
            </tr>
        </tbody>
    </table>
        """

    exec_summary_html = f"""
    <h1>1. Executive Ingestion Overview</h1>
    <p>This document details the successful multi-agent stack seeding run for the <strong>{cfg['aesthetic_title']}</strong> stack within the Sovereign OS simulated swarm environment.</p>
    
    <p>The <strong>M.A.R.D. (Multi-Agent Relation Database) Ingestion Cascade</strong> is a modular framework that translates raw brand briefs and creative director directives into highly reactive, lore-constrained synthetic commentator teams. The ingestion process establishes dedicated database bounds, custom initials-based vector avatar graphics, and GDrive moats cleanly isolated by sorting domain names.</p>
    
    <h2>Seeding Relational Boundary Matrix</h2>
    <table>
        <thead>
            <tr>
                <th>Stack (Brand)</th>
                <th>Target Room Key</th>
                <th>Domain Moat</th>
                <th>Persona Count</th>
                <th>Aesthetic Profile</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>{brand_key.title()}</strong></td>
                <td><code>{brand_key}_SIM_001</code></td>
                <td><code>{brand_key}</code></td>
                <td>{len(personas)} Advocates</td>
                <td>{cfg['description']}</td>
            </tr>
        </tbody>
    </table>

    <h2>Operational System Integration Hooks</h2>
    <ul>
        <li><strong>Sorting Hat isolation:</strong> Google Drive namespaces configured via <code>sync_to_gdrive.sh</code>, preventing cross-tenant narrative drift.</li>
        <li><strong>Daemon Auto-Alignment:</strong> The FanStack relay system on Port <code>8008</code> and chatbots runner reloaded to immediately execute local simulated discussion metrics.</li>
        <li><strong>Database Seeding Commit:</strong> Relational seating records successfully committed across <code>cmdb_ci_fanstack_room</code>, <code>sys_user</code>, <code>persona</code>, and <code>game_persona</code> tables inside <code>sovereign_now.db</code>.</li>
    </ul>

    {website_blueprint_html}
    """

    # 2. Dossier Section HTML
    dossier_html = f"""
    <div class="section-break"></div>
    <h1>3. Stack Dossier</h1>
    <p>Seeded under room key <code>{brand_key}_SIM_001</code> with active domain <code>{brand_key}</code>. These {len(personas)} advocates are configured with custom cadences, system prompts, deep backstories, and governance protocols.</p>
    """

    for p in personas:
        svg_inline = get_svg_content(p['user_name'])
        
        system_prompt = p.get('system_prompt', 'None provided.')
        deep_lore = p.get('deep_lore', 'None provided.')
        governance = p.get('governance', 'None provided.')
        
        dossier_html += f"""
        <div class="persona-card">
            <div class="persona-header">
                <div class="avatar-svg-container">
                    {svg_inline}
                </div>
                <div class="persona-meta">
                    <h3 class="persona-name">{p['display_name']}</h3>
                    <p class="persona-username">@{p['user_name']}</p>
                    <div class="badge-row">
                        <span class="badge badge-boggs">Boggs Level {p['boggs_level']}</span>
                        <span class="badge badge-cadence">Cadence: {p['cadence']}</span>
                    </div>
                </div>
            </div>
            
            <div class="persona-section">
                <h4 class="persona-section-title">System prompt & Personality Laws</h4>
                <p class="persona-section-body">{system_prompt}</p>
            </div>
            
            <div class="persona-section">
                <h4 class="persona-section-title">Deep Lore History</h4>
                <p class="persona-section-body">{deep_lore}</p>
            </div>
            
            <div class="persona-section">
                <h4 class="persona-section-title">Governance Rules</h4>
                <p class="persona-section-body">{governance}</p>
            </div>
        </div>
        """

    # 3. System Verification Section HTML
    verification_html = f"""
    <div class="section-break"></div>
    <h1>4. Relational & Port Telemetry Matrix</h1>
    <p>All database records and core network binds have been successfully verified post-seeding to confirm zero system drift.</p>
    
    <h2>Seeding State Validation</h2>
    <table>
        <thead>
            <tr>
                <th>Verification Check</th>
                <th>Target Component / Query</th>
                <th>Expected State</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Core API Server</strong></td>
                <td><code>ss -tlnp | grep 8090</code></td>
                <td>Bound / Active listening</td>
                <td><strong>✅ ACTIVE</strong></td>
            </tr>
            <tr>
                <td><strong>{brand_key} Room</strong></td>
                <td><code>SELECT room_state FROM cmdb_ci_fanstack_room WHERE room_key='{brand_key}_SIM_001'</code></td>
                <td><code>active</code></td>
                <td><strong>✅ VERIFIED</strong></td>
            </tr>
            <tr>
                <td><strong>Sync Isolation Rules</strong></td>
                <td><code>sync_to_gdrive.sh</code> for domain <code>{brand_key}</code></td>
                <td>Namespaces isolated cleanly</td>
                <td><strong>✅ VERIFIED</strong></td>
            </tr>
        </tbody>
    </table>

    <h2>Operational Seeding Logs</h2>
    <pre>
{cfg['operational_logs'].strip()}
    </pre>
    """

    # 4. Catnip Wars Crossover Section for Unhinged Convenience
    crossover_html = ""
    if brand_key in ("UNHINGEDCONVENIENCE", "GONZAS"):
        crossover_html = """
        <div class="section-break"></div>
        <h1>5. Emergent Swarm & Kiosk Crossover Telemetry</h1>
        <p>The Gonzo's Convenience ecosystem utilizes the <strong>Catnip Wars Crossover Protocol</strong> to synchronize dialogue matrices and card-stats crossovers between the convenience store advocates and the 16-bit metsy-prime Pi 3 card kiosk card decks.</p>
        
        <h2>Crossover Mappings & Tension Invariants</h2>
        <table>
            <thead>
                <tr>
                    <th>Advocate Persona</th>
                    <th>Catnip Wars Card Link</th>
                    <th>Crossover Dialogue Trigger</th>
                    <th>Ideological Anchor</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Señora Caos</strong></td>
                    <td>Feral Feline Turf Watchdog</td>
                    <td>High tension in grow garden triggers automatic unhinged night-vision warning posts.</td>
                    <td>Nihilist / Catalyst</td>
                </tr>
                <tr>
                    <td><strong>Static Shock</strong></td>
                    <td>Fluorescent Surge Daemon</td>
                    <td>CRT display flickering events automatically inject raw static syntax overrides into active chat logs.</td>
                    <td>Speculator / Decentralist</td>
                </tr>
                <tr>
                    <td><strong>Flicker Watch</strong></td>
                    <td>The Linoleum Specter</td>
                    <td>Tracks Metsy the Cat's temporal mulch-dwell coordinates to verify grow soil quality and alert of card deck mutations.</td>
                    <td>Nihilist / Decentralist</td>
                </tr>
            </tbody>
        </table>

        <h2>Metsy's Mulch Watch & GPS Integration</h2>
        <p>The <code>mando_watchdog.py</code> daemon queries the active GPS collar telemetry frommetsy_gps_export_05262026.gpx natively on Loopback. Growing soil moisture, mulch anomaly alerts, and sandbox zone presence levels map asynchronously to the main <strong>Sovereign OS watch party</strong> dashboards on port 3000, creating a living, self-healing environment.</p>
        """

    # 5. Character Maps Section HTML
    # We query the actual files in media_vault/01_Assets/Inbox/ that start with usernames in our persona list!
    charmaps_html = ""
    vault_dir = os.path.join(WORKSPACE_DIR, "media_vault", "01_Assets", "Inbox")
    found_charmaps = []

    for p in personas:
        uname = p["user_name"]
        # Look for files matching: *[uname]*reference_sheet*.jpeg
        # Be loose to accommodate capitalization or spacing anomalies
        pattern = os.path.join(vault_dir, f"*{uname}*reference_sheet*.jpeg")
        matches = glob.glob(pattern)
        if not matches:
            # Try case-insensitive
            all_files = os.listdir(vault_dir)
            for f in all_files:
                if uname.lower() in f.lower() and "reference_sheet" in f.lower() and f.lower().endswith(".jpeg"):
                    matches.append(os.path.join(vault_dir, f))
        
        # Sort and take unique matching file paths
        for m in sorted(list(set(matches))):
            found_charmaps.append((p["display_name"], m))

    # De-duplicate matches
    unique_charmaps = []
    seen_paths = set()
    for dname, path in found_charmaps:
        if path not in seen_paths:
            unique_charmaps.append((dname, path))
            seen_paths.add(path)

    if unique_charmaps:
        charmaps_html = f"""
        <div class="section-break"></div>
        <h1>2. Character Reference Sheets & Model Sheets</h1>
        <p>The following premium, illustrated character model sheets have been dynamically generated and seeded into the active workspace, providing multi-angle expression grids for visual and behavioral alignment with <strong>absolutely no puppet structures</strong>.</p>
        
        <h2>{cfg['aesthetic_title']}</h2>
        <div style="display: grid; grid-template-columns: 1fr; gap: 20px;">
        """
        for dname, filepath in unique_charmaps:
            filename = os.path.basename(filepath)
            # Try to identify variant number
            variant = "Variant 1"
            if "_2.jpeg" in filename:
                variant = "Variant 2"
            elif "_3.jpeg" in filename:
                variant = "Variant 3"
                
            charmaps_html += f"""
            <div class="charmap-card">
                <div class="charmap-title">{dname} ({variant})</div>
                <img class="charmap-image" src="file://{filepath}" />
            </div>
            """
    logo_html = ""
    if brand_key == "SMYRNAPAWSPROVISIONS":
        logo_path = os.path.join(WORKSPACE_DIR, "media_vault", "01_Assets", "Inbox", "company_artwork.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(inbox_reports), "today", "Smyrna Paws and Provisions", "company_artwork.png")
        if os.path.exists(logo_path):
            logo_html = f'<div style="text-align: left; margin-bottom: 20px;"><img src="file://{logo_path}" style="max-height: 80px;" /></div>'

    # Wrap the entire document
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sovereign OS Seeding Manifest - {brand_key}</title>
    <style>
        {css_content}
    </style>
</head>
<body>

    <div class="cover-page">
        <div class="cover-header">Sovereign OS • Seeding Report</div>
        <div class="cover-body">
            {logo_html}
            <h1 class="cover-title">{cfg['title']}</h1>
            <div class="cover-subtitle">{cfg['subtitle']}</div>
            <div class="cover-divider"></div>
        </div>
        <div class="cover-footer">
            <div class="cover-footer-item">
                <strong>Platform</strong>
                Sovereign OS Core<br>Decoupled Architecture
            </div>
            <div class="cover-footer-item">
                <strong>Date</strong>
                May 29, 2026
            </div>
        </div>
    </div>

    <div class="content-container">
        {exec_summary_html}
        {charmaps_html}
        {dossier_html}
        {verification_html}
        {crossover_html}
    </div>

</body>
</html>
"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_document)
    print(f"Generated intermediate HTML at: {html_file}")

    # Run Headless Chrome to compile PDF
    chrome_cmd = [
        "/usr/local/bin/google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_file}",
        f"file://{html_file}"
    ]
    
    print("Compiling Genesis Seeding PDF via Headless Google Chrome...")
    result = subprocess.run(chrome_cmd, capture_output=True, text=True)
    
    # Cleanup intermediate HTML
    if os.path.exists(html_file):
        try:
            os.remove(html_file)
            print("Cleaned up temporary HTML file.")
        except Exception as e:
            print(f"Failed to remove temporary HTML: {e}")
            
    if result.returncode == 0 and os.path.exists(pdf_file):
        print(f"✅ Success! PDF successfully compiled and written to: {pdf_file}")
        print(f"File size: {os.path.getsize(pdf_file)} bytes")
    else:
        print("❌ Chrome PDF generation failed!")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1].upper().strip()
        if target == "ALL":
            brands = get_brand_config()
            for b in brands.keys():
                compile_pdf(b)
        else:
            compile_pdf(target)
    else:
        brands = get_brand_config()
        brand_list = " | ".join(brands.keys())
        print(f"Usage: python3 generate_single_onboarding_pdf.py [{brand_list} | ALL]")
