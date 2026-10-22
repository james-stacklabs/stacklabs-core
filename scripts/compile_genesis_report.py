import sqlite3
import os
import base64
import re
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(WORKSPACE_DIR, 'dna', 'sovereign_now.db')
AVATARS_DIR = os.path.join(WORKSPACE_DIR, '01_Sovereign_Portal', 'public', 'avatars')
OUTPUT_DIR = os.getenv('SOVEREIGN_INBOX_REPORTS_DIR', '/home/james/sovereign_inbox/reports')
TEMP_HTML_PATH = os.path.join(OUTPUT_DIR, 'seeding_report_temp.html')

def get_active_brand_teams(cursor):
    cursor.execute("SELECT DISTINCT team FROM persona WHERE team IS NOT NULL AND team != ''")
    all_teams = [r[0] for r in cursor.fetchall()]
    
    # Exclude sports teams and global/generic names
    exclude_list = {
        'global', 'GLOBAL', 'golf_room', 'MLB', 'ATL', 'NYM', 'PHI', 'STL', 'CHC', 
        'BOS', 'MIL', 'SF', 'CLE', 'KC', 'AZ', 'LAA', 'BAL', 'CWS', 'SEA', 'TEX', 
        'HOU', 'COL', 'WSH', 'TB', 'CIN', 'MIA', 'ATH', 'NYY', 'MIN', 'LAD', 'TOR', 
        'DET', 'SD', 'PIT', 'OAK', 'NYJ', 'DAL', 'GB', 'UFL', 'BISTROSTACK'
    }
    
    brand_teams = [t for t in all_teams if t not in exclude_list]
    return sorted(brand_teams)

def update_database_avatar_urls():
    # Decommissioned to prevent overwriting dynamic, database-driven avatar url configurations
    pass

def get_avatar_html_from_db_path(avatar_url, user_name):
    if not avatar_url:
        # Ultimate fallback: initials badge
        initials = "".join([part[0].upper() for part in user_name.split('_') if part])[:2]
        return f'<div class="avatar-fallback">{initials}</div>'
        
    # Resolve the avatar_url relative to public/
    clean_mapped = avatar_url.lstrip('/')
    avatar_path = os.path.join(WORKSPACE_DIR, '01_Sovereign_Portal', 'public', clean_mapped)
    
    if not os.path.exists(avatar_path):
        print(f"Warning: Avatar path does not exist on disk: {avatar_path}")
        initials = "".join([part[0].upper() for part in user_name.split('_') if part])[:2]
        return f'<div class="avatar-fallback">{initials}</div>'
        
    # If SVG, read and inline it
    if avatar_path.endswith('.svg'):
        try:
            with open(avatar_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Clean up xml tags
                content = re.sub(r'<\?xml[^>]*\?>', '', content)
                content = re.sub(r'<!DOCTYPE[^>]*>', '', content)
                return f'<div class="avatar-svg-container">{content}</div>'
        except Exception as e:
            print(f"Error reading SVG {avatar_path}: {e}")
            
    # If raster, base64 encode it
    else:
        try:
            ext = os.path.splitext(avatar_path)[1].lower().replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            elif ext == 'jfif': ext = 'jpeg'
            with open(avatar_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            return f'<img class="avatar-raster" src="data:image/{ext};base64,{b64}" alt="{user_name}" />'
        except Exception as e:
            print(f"Error reading raster {avatar_path}: {e}")
            
    initials = "".join([part[0].upper() for part in user_name.split('_') if part])[:2]
    return f'<div class="avatar-fallback">{initials}</div>'

def compile_report():
    import sys
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Update db with proper URLs first
    update_database_avatar_urls()
    
    # Establish connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if len(sys.argv) > 1:
        target_teams = [t.upper().strip() for t in sys.argv[1:]]
    else:
        target_teams = get_active_brand_teams(cursor)
        if not target_teams:
            target_teams = ['WEEDSTACK', 'STACKLABS']
            
    # Set output PDF path based on targeted teams
    if sorted(target_teams) == sorted(['WEEDSTACK', 'STACKLABS']):
        pdf_name = 'WeedStack_and_StackLabs_Seeding_Report.pdf'
    else:
        pdf_name = f"{'_and_'.join(sorted(target_teams))}_Seeding_Report.pdf"
    
    final_pdf_path = os.path.join(OUTPUT_DIR, pdf_name)
    
    # Resolve target_teams to actual database team names (e.g. STACKLABS -> STACKLABSLLC)
    db_teams = []
    for team in target_teams:
        cursor.execute("SELECT DISTINCT team FROM persona WHERE team LIKE ? OR team = ?", (f"{team}%", team))
        matched = [r[0] for r in cursor.fetchall()]
        if matched:
            db_teams.extend(matched)
        else:
            db_teams.append(team)
    db_teams = list(set(db_teams))
    
    # Query targeted personas using the resolved db_teams
    placeholders = ','.join('?' for _ in db_teams)
    cursor.execute(f"""
        SELECT id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, governance
        FROM persona
        WHERE team IN ({placeholders})
        ORDER BY team, display_name ASC;
    """, db_teams)
    personas = cursor.fetchall()

    # Query room details to fetch website blueprint specifications dynamically
    room_data_list = []
    try:
        for team in target_teams:
            # Clean team name to strip common suffixes for room matching
            clean_team = team
            if clean_team.endswith("LLC"):
                clean_team = clean_team[:-3]
            if "/" in clean_team:
                clean_team = clean_team.split("/")[0]

            cursor.execute("""
                SELECT name, room_key, website_purpose, website_domain, website_pages, website_features, website_colors, website_typography, website_additional_requirements
                FROM cmdb_ci_fanstack_room
                WHERE room_key = ? OR name LIKE ? OR room_key = ? OR room_key = ? OR name LIKE ? OR room_key = ?
            """, (f"{clean_team}_SIM_001", f"%{clean_team}%", f"{clean_team}_SIM_001_SIM_001", f"{team}_SIM_001", f"%{team}%", f"{team}_SIM_001_SIM_001"))
            room_row = cursor.fetchone()
            if room_row:
                room_data_list.append(dict(room_row))
    except Exception as e:
        print(f"Warning: Failed to fetch room details: {e}")
        
    # We now map target_teams to db_teams so that the HTML generator processes all matched DB teams
    target_teams = db_teams

    conn.close()
    
    # CSS Template
    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    @page {
        size: letter;
        margin: 20mm;
        @bottom-right {
            content: counter(page);
            font-family: 'Outfit', sans-serif;
            font-size: 8pt;
            color: #475569;
        }
    }
    
    * {
        box-sizing: border-box;
    }
    
    body {
        background-color: #ffffff;
        color: #0f172a;
        font-family: 'Outfit', sans-serif;
        margin: 0;
        padding: 0;
        line-height: 1.6;
        -webkit-print-color-adjust: exact;
    }
    
    .page {
        page-break-after: always;
    }
    
    .page:last-child {
        page-break-after: avoid;
    }
    
    header {
        border-bottom: 2px solid #0284c7;
        padding-bottom: 15px;
        margin-bottom: 30px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .logo-text {
        font-weight: 700;
        font-size: 24pt;
        letter-spacing: -0.05em;
        color: #0f172a;
    }
    
    .logo-text span {
        color: #0284c7;
    }
    
    .dossier-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9pt;
        background-color: #f1f5f9;
        border: 1px solid #0284c7;
        color: #0284c7;
        padding: 4px 10px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    h1, h2, h3 {
        margin-top: 0;
        font-weight: 600;
    }
    
    h1 {
        font-size: 28pt;
        color: #0f172a;
        letter-spacing: -0.03em;
        margin-bottom: 10px;
    }
    
    h2 {
        font-size: 20pt;
        color: #0f172a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 8px;
        margin-top: 40px;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .intro-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 30px;
        margin-bottom: 40px;
    }
    
    .intro-main {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 25px;
    }
    
    .intro-meta {
        background-color: #f1f5f9;
        border-left: 3px solid #0284c7;
        padding: 25px;
        border-radius: 0 8px 8px 0;
    }
    
    .meta-item {
        margin-bottom: 15px;
    }
    
    .meta-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 8pt;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .meta-value {
        font-size: 11pt;
        font-weight: 500;
        color: #0f172a;
    }
    
    /* Feature Highlight - Linda's Mets Win Climax */
    .featured-climax {
        background: linear-gradient(135deg, #fff5f7 0%, #ffe4e6 100%);
        border: 1px solid #f43f5e;
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 40px;
        display: grid;
        grid-template-columns: 180px 1fr;
        gap: 30px;
        align-items: center;
        page-break-inside: avoid;
    }
    
    .featured-photo-frame {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        overflow: hidden;
        border: 3px solid #f43f5e;
        box-shadow: 0 0 20px rgba(244, 63, 94, 0.15);
        background-color: #f1f5f9;
    }
    
    .featured-photo-frame img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .featured-content h3 {
        color: #9f1239;
        font-size: 16pt;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .featured-tag {
        font-size: 8pt;
        font-family: 'JetBrains Mono', monospace;
        background-color: rgba(244, 63, 94, 0.1);
        color: #9f1239;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    
    .featured-quote {
        font-size: 14pt;
        font-style: italic;
        color: #4c0519;
        line-height: 1.5;
        position: relative;
        margin-bottom: 15px;
    }
    
    .featured-quote::before {
        content: '"';
        font-size: 36pt;
        color: rgba(244, 63, 94, 0.2);
        position: absolute;
        left: -20px;
        top: -15px;
    }
    
    .featured-author {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10pt;
        color: #881337;
    }
    
    /* Persona Cards Grid */
    .cards-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 25px;
    }
    
    .persona-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 25px;
        page-break-inside: avoid;
        display: grid;
        grid-template-columns: 120px 1fr;
        gap: 20px;
    }
    
    .avatar-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .avatar-container {
        width: 120px;
        height: 120px;
        border-radius: 8px;
        overflow: hidden;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .avatar-raster {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .avatar-svg-container {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .avatar-svg-container svg {
        width: 100%;
        height: 100%;
    }
    
    .avatar-fallback {
        font-family: 'JetBrains Mono', monospace;
        font-size: 16pt;
        font-weight: 700;
        color: #64748b;
    }
    
    .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    
    .persona-name {
        font-size: 18pt;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
    }
    
    .persona-role {
        font-size: 10pt;
        color: #475569;
        margin-top: 2px;
    }
    
    .persona-badges {
        display: flex;
        gap: 8px;
    }
    
    .badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5pt;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-team {
        background-color: rgba(2, 132, 199, 0.1);
        color: #0284c7;
        border: 1px solid rgba(2, 132, 199, 0.3);
    }
    
    .badge-cadence {
        background-color: rgba(245, 158, 11, 0.1);
        color: #b45309;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-boggs {
        background-color: rgba(16, 185, 129, 0.1);
        color: #047857;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .card-body-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .card-section-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 8pt;
        color: #475569;
        text-transform: uppercase;
        margin-bottom: 5px;
        letter-spacing: 0.05em;
    }
    
    .prompt-block {
        background-color: #f0fdf4;
        border: 1px solid #a7f3d0;
        border-radius: 6px;
        padding: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 8.5pt;
        color: #065f46;
        white-space: pre-wrap;
        max-height: 120px;
        overflow-y: auto;
    }
    
    .lore-block {
        font-size: 10pt;
        color: #334155;
    }
    
    .gov-block {
        font-size: 9.5pt;
        color: #475569;
        border-left: 2px solid #ef4444;
        padding-left: 10px;
    }
    
    .footer-ledger {
        margin-top: 60px;
        border-top: 1px solid #cbd5e1;
        padding-top: 20px;
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 7.5pt;
        color: #64748b;
    }
    """

    # Format cover titles
    formatted_teams = []
    for t in target_teams:
        clean = t.replace('_', ' ').replace('FANSTACKSILO', 'FanStack Silo').replace('WWEDRAMA', 'WWE Drama').replace('MMAPURIST', 'MMA Purist')
        formatted_teams.append(clean.title())
    teams_title = " & ".join(formatted_teams)
    
    plural_suffix = "s" if len(target_teams) > 1 else ""
    
    # Check if Linda is in our query results to render the climax reaction
    has_linda = any(p['user_name'] == '420_linda' for p in personas)
    featured_html = ""
    if has_linda:
        linda_avatar_html = get_avatar_html_from_db_path('/avatars/420_linda.jpeg', '420_linda')
        featured_html = f"""
            <!-- FEATURED HIGHLIGHT: Linda's Climax Reaction -->
            <div class="featured-climax">
                <div class="featured-photo-frame">
                    {linda_avatar_html}
                </div>
                <div class="featured-content">
                    <h3>
                        <span>Featured Climax Advocate Response</span>
                        <span class="featured-tag">WeedStack Hive Mind</span>
                    </h3>
                    <div class="featured-quote">
                        OMG THE METS WON THE GIRLS AND I ARE VIBRATING WITH JOY WE DIDNT EVEN NEED OUR WEEDSTACK LAVENDER MINTS MY THERAPIST WILL BE SO PROUD THIS IS BETTER THAN ANY BOOK CLUB
                    </div>
                    <div class="featured-author">
                        — <strong>420 Linda</strong>, speaking directly following the walk-off victory in the game room (05:54:28Z)
                    </div>
                </div>
            </div>
        """

    # Assemble HTML document
    html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Sovereign OS Stack Seeding Report</title>
        <style>
            {css_content}
        </style>
    </head>
    <body>
        <!-- FIRST PAGE: COVER & OVERVIEW -->
        <div class="page">
            <header>
                <div class="logo-container">
                    <span class="logo-text">SOVEREIGN<span>OS</span></span>
                </div>
                <div class="dossier-tag">Genesis Seeding Dossier</div>
            </header>
            <h1>Genesis Seeding Dossier</h1>
            <div style="font-size: 15pt; color: #0284c7; font-weight: 300; margin-bottom: 30px;">
                Active Brand Stack{plural_suffix}: {teams_title}
            </div>
            
            <div class="intro-grid">
                <div class="intro-main">
                    <p style="margin-top: 0; font-size: 11.5pt; color: #0f172a;">
                        This official Genesis Seeding Report documents the successful integration and initialization parameters of the brand stack{plural_suffix} <strong>{teams_title}</strong> into the Sovereign OS live CMDB workspace.
                    </p>
                    <p style="font-size: 11.5pt; color: #334155;">
                        The stack{plural_suffix} establish a stateful, interactive swarm of autonomous persona advocates. These advocates act statefully, responding in real-time to external data streams, spatial triggers, and governance decisions under the omniscient cockpit control structures.
                    </p>
                    <p style="margin-bottom: 0; font-size: 11pt; color: #475569; font-style: italic;">
                        Confidential and proprietary memorandum. Generated under authentication Pilot (James).
                    </p>
                </div>
                <div class="intro-meta">
                    <div class="meta-item">
                        <div class="meta-label">Dossier ID</div>
                        <div class="meta-value" style="font-family: 'JetBrains Mono', monospace;">SOV-GEN-2026-0530</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">System Date</div>
                        <div class="meta-value">2026-05-30</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Authority</div>
                        <div class="meta-value">James (Pilot)</div>
                    </div>
                    <div class="meta-item" style="margin-bottom: 0;">
                        <div class="meta-label">Seated Personas</div>
                        <div class="meta-value">{len(personas)} Active Units</div>
                    </div>
                </div>
            </div>
            
            {featured_html}
            
            <div class="footer-ledger">
                <div>SOVEREIGN OS METRICS LEDGER</div>
                <div>CLASSIFIED INTERNAL ONLY</div>
            </div>
        </div>
        """

    # Proposed Website Specifications Page
    for rdata in room_data_list:
        if rdata.get("website_purpose"):
            html_content += f"""
            <!-- PROPOSED WEBSITE BLUEPRINT SPECIFICATIONS -->
            <div class="page">
                <header>
                    <div class="logo-container">
                        <span class="logo-text">SOVEREIGN<span>OS</span></span>
                    </div>
                    <div class="dossier-tag">Website Blueprint</div>
                </header>
                
                <h1 style="color: #0284c7;">Proposed Specs: {rdata.get('name') or 'Website'}</h1>
                <p style="margin-top: 0; font-size: 11pt; color: #475569; margin-bottom: 30px;">
                    Strategic specifications registered within the CMDB matrix to guide dynamic generation and design systems.
                </p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead>
                        <tr style="background-color: rgba(2, 132, 199, 0.08); border-bottom: 2px solid #0284c7;">
                            <th style="padding: 12px; text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 9pt; color: #0284c7; width: 30%;">Specification Field</th>
                            <th style="padding: 12px; text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 9pt; color: #0284c7; width: 70%;">Blueprint Values / Directives</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Target Domain</td>
                            <td style="padding: 12px; font-family: 'JetBrains Mono', monospace; color: #334155;"><code>{rdata.get('website_domain') or 'Not Specified'}</code></td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Website Purpose</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_purpose') or 'Not Specified'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Key Pages & Hierarchy</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_pages') or 'Not Specified'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Core Features & Logic</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_features') or 'Not Specified'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Color Palette Guidelines</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_colors') or 'Not Specified'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Typography System</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_typography') or 'Not Specified'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #cbd5e1;">
                            <td style="padding: 12px; font-weight: 600; color: #0f172a;">Additional Requirements</td>
                            <td style="padding: 12px; color: #334155;">{rdata.get('website_additional_requirements') or 'Not Specified'}</td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="footer-ledger">
                    <div>SOVEREIGN OS METRICS LEDGER — SECTION I.B</div>
                    <div>PROPOSED WEBSITE BLUEPRINT SPECIFICATIONS</div>
                </div>
            </div>
            """

    for team in target_teams:
        team_personas = [p for p in personas if p['team'] == team]
        if not team_personas:
            continue
            
        team_title = team.replace('_', ' ').upper()
        # Find primary color from first persona or default to standard
        team_color = team_personas[0]['color'] or '#0284c7'
        
        html_content += f"""
        <!-- BRAND STACK: {team_title} -->
        <div class="page">
            <header style="border-bottom: 2px solid {team_color}">
                <div class="logo-container">
                    <span class="logo-text">SOVEREIGN<span>OS</span></span>
                </div>
                <div class="dossier-tag" style="border-color: {team_color}; color: {team_color}">{team_title} Stack</div>
            </header>
            
            <h1 style="color: {team_color}">{team_title} STACK</h1>
            <p style="margin-top: 0; font-size: 11pt; color: #475569; margin-bottom: 30px;">
                Stateful roster of autonomous brand advocates instantiated within the {team_title.lower()} context.
            </p>
            
            <div class="cards-grid">
        """
        
        for p in team_personas:
            avatar_html = get_avatar_html_from_db_path(p['avatar_url'], p['user_name'])
            html_content += f"""
                <div class="persona-card">
                    <div class="avatar-wrapper">
                        <div class="avatar-container">
                            {avatar_html}
                        </div>
                    </div>
                    <div class="card-content">
                        <div class="card-header-row">
                            <div>
                                <h3 class="persona-name">{p['display_name']}</h3>
                                <div class="persona-role">{p['user_name']}</div>
                            </div>
                            <div class="persona-badges">
                                <span class="badge badge-team" style="color: {p['color'] or team_color}; border-color: {p['color'] or team_color}; background-color: {p['color'] or team_color}15">{p['team']}</span>
                                <span class="badge badge-cadence">{p['cadence']}</span>
                                <span class="badge badge-boggs">Boggs Lvl {p['boggs_level']}</span>
                            </div>
                        </div>
                        
                        <div class="card-body-grid">
                            <div>
                                <div class="card-section-title">System Prompt & Directives</div>
                                <div class="prompt-block">{p['system_prompt']}</div>
                            </div>
                            
                            {"<div><div class='card-section-title'>Deep Lore</div><div class='lore-block'>" + p['deep_lore'] + "</div></div>" if p['deep_lore'] else ""}
                            
                            {"<div><div class='card-section-title'>Governance Parameters</div><div class='gov-block'>" + p['governance'] + "</div></div>" if p['governance'] else ""}
                        </div>
                    </div>
                </div>
            """
            
        html_content += f"""
            </div>
            
            <div class="footer-ledger">
                <div>SOVEREIGN OS METRICS LEDGER — SECTION FOR {team_title}</div>
                <div>SECURE DATA VAULT — {team_title}</div>
            </div>
        </div>
        """

    html_content += """
    </body>
    </html>
    """
    
    # Write temporary staged HTML
    with open(TEMP_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Staged temporary HTML at {TEMP_HTML_PATH}")
    
    # Run Headless Chrome Compilation
    chrome_cmd = [
        "/usr/bin/google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={final_pdf_path}",
        f"file://{TEMP_HTML_PATH}"
    ]
    
    # Try /usr/bin/google-chrome, fallback to /usr/local/bin/google-chrome
    if not os.path.exists(chrome_cmd[0]):
        chrome_cmd[0] = "/usr/local/bin/google-chrome"
        
    print(f"Running compilation command: {' '.join(chrome_cmd)}")
    result = subprocess.run(chrome_cmd, capture_output=True, text=True)
    
    # Cleanup temporary HTML file to satisfy the Zero-Litter Workspace Policy
    if os.path.exists(TEMP_HTML_PATH):
        os.remove(TEMP_HTML_PATH)
        print("Cleaned up staged temporary HTML.")
        
    if result.returncode == 0:
        print(f"Success! Seeding report compiled to {final_pdf_path}")
        return True
    else:
        print(f"Compilation failed: {result.stderr}")
        return False

if __name__ == '__main__':
    compile_report()
