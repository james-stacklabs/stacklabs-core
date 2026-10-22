"""PDF rendering logic for persona dossiers and brand lookbooks.

Extracted verbatim from the old monolith's print_dossier_pdf (was 753 lines inline)
and print_lookbook_pdf (was 430 lines inline). Logic is untouched -- only the
@fastapi_app.get(...) decorators were stripped, since these are now plain functions
called from thin route wrappers in routers/personas.py and routers/media.py.
"""
from fastapi import BackgroundTasks
from core.db import DB_PATH

async def print_dossier_pdf(ids: str = None, background_tasks: BackgroundTasks = None):
    import base64
    import sqlite3 as _sq
    import os
    import glob
    import tempfile
    import subprocess
    import json
    from fastapi.responses import FileResponse
    from fastapi import BackgroundTasks, HTTPException
    
    if not ids:
        raise HTTPException(status_code=400, detail="Missing ids query parameter")
        
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="Invalid ids parameter")

    # Helper: Resolve local path or blob to base64 Data URL
    def resolve_media_file_to_base64(file_path: str) -> str:
        if not file_path:
            return ""
        clean_path = file_path.lstrip("/")
        search_dirs = [
            "/home/james/stacklabs/avatars",
            "/home/james/stacklabs/01_Sovereign_Portal/public",
            "/home/james/stacklabs/02_Sovereign_Media/public",
            "/home/james/stacklabs/15_FanStack/public",
            "/home/james/stacklabs/dna/media",
            "/home/james/stacklabs"
        ]
        for d in search_dirs:
            p = os.path.join(d, clean_path)
            if os.path.exists(p) and os.path.isfile(p):
                try:
                    with open(p, 'rb') as img_f:
                        raw_data = img_f.read()
                        b64 = base64.b64encode(raw_data).decode('utf-8')
                        mime = "image/png"
                        if p.lower().endswith('.webp'):
                            mime = "image/webp"
                        elif p.lower().endswith(('.jpg', '.jpeg')):
                            mime = "image/jpeg"
                        elif p.lower().endswith('.svg'):
                            mime = "image/svg+xml"
                        return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
        return ""

    def get_persona_image_base64(p_id: str, u_name: str, avatar_url_val: str) -> str:
        safe_id = u_name.lower().replace(" ", "_")
        
        # Try DB blob first
        try:
            con_img = _sq.connect(DB_PATH)
            row = con_img.execute(
                "SELECT avatar_blob FROM persona WHERE id = ? OR user_name = ? OR user_name = ?",
                (p_id, u_name, safe_id)
            ).fetchone()
            con_img.close()
            if row and row[0]:
                blob_data = row[0]
                if blob_data.startswith('data:'):
                    return blob_data
                else:
                    return f"data:image/png;base64,{blob_data}"
        except Exception as e:
            print(f"[get_persona_image_base64] DB lookup error: {e}")
            
        # Try resolving avatar_url
        if avatar_url_val:
            resolved = resolve_media_file_to_base64(avatar_url_val)
            if resolved:
                return resolved

        # Try fallback local avatar files
        for search_dir in [
            "/home/james/stacklabs/avatars",
            "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
            "/home/james/stacklabs/02_Sovereign_Media/public/avatars",
            "/home/james/stacklabs/15_FanStack/public/avatars",
            "/home/james/stacklabs/dna/media/avatars",
            "/home/james/stacklabs/dna/media/character_maps"
        ]:
            for f in glob.glob(os.path.join(search_dir, f"{safe_id}.*")):
                if f.lower().endswith(('.jpg','.jpeg','.png','.jfif','.webp','.svg')):
                    try:
                        with open(f, 'rb') as img_f:
                            b64 = base64.b64encode(img_f.read()).decode('utf-8')
                            mime = "image/png"
                            if f.lower().endswith('.webp'):
                                mime = "image/webp"
                            elif f.lower().endswith(('.jpg', '.jpeg')):
                                mime = "image/jpeg"
                            elif f.lower().endswith('.svg'):
                                mime = "image/svg+xml"
                            return f"data:{mime};base64,{b64}"
                    except Exception:
                        pass
        return ""

    con = _sq.connect(DB_PATH)
    con.row_factory = _sq.Row
    cur = con.cursor()
    
    placeholders = ",".join("?" for _ in id_list)
    # Query persona details, matching either id (sys_id) or user_name
    query = f"SELECT * FROM persona WHERE id IN ({placeholders}) OR user_name IN ({placeholders})"
    cur.execute(query, id_list + id_list)
    personas = [dict(r) for r in cur.fetchall()]
    
    if not personas:
        con.close()
        raise HTTPException(status_code=404, detail="No matching personas found")

    pages_html = []
    
    for p in personas:
        p_id = p.get("id")
        user_name = p.get("user_name", "")
        display_name = p.get("display_name", "")
        team = p.get("team", "")
        system_prompt = p.get("system_prompt", "")
        boggs_level = p.get("boggs_level", 3)
        avatar_url = p.get("avatar_url", "")
        color = p.get("color", "#00d4ff")
        cadence = p.get("cadence", "pacer")
        deep_lore = p.get("deep_lore", "")
        behavior_notes = p.get("behavior_notes", "")
        governance = p.get("governance", "")
        email_alias = p.get("email_alias", "")
        u_visual_style = p.get("u_visual_style", "default")
        avatar_prompt = p.get("avatar_prompt", "")
        character_map_prompt = p.get("character_map_prompt", "")
        canned_takes_raw = p.get("canned_takes", "[]")
        
        try:
            canned_takes = json.loads(canned_takes_raw)
        except Exception:
            canned_takes = []
            
        # Get base64 avatar
        avatar_b64 = get_persona_image_base64(p_id, user_name, avatar_url)
        
        # Get associated media assets
        cur.execute("SELECT expression, file_path, sha256 FROM cmdb_ci_media_asset WHERE advocate = ? OR advocate = ?", (user_name, user_name.lower().replace(" ", "_")))
        media_rows = cur.fetchall()
        media_assets = []
        for mr in media_rows:
            expr = mr[0]
            fp = mr[1]
            sha = mr[2]
            asset_b64 = resolve_media_file_to_base64(fp)
            media_assets.append({
                "expression": expr,
                "file_path": fp,
                "sha256": sha,
                "base64": asset_b64
            })
            
        # Format canned takes
        takes_html = ""
        if canned_takes:
            takes_html = "<ul>" + "".join(f"<li><strong style='color:#38bdf8;'>[{t.get('topic', 'LORE')}]</strong> {t.get('text', '')}</li>" for t in canned_takes) + "</ul>"
        else:
            takes_html = "<p style='color:#64748b; font-style:italic;'>No canned takes registered.</p>"
            
        # Expression gallery html
        gallery_html = ""
        if media_assets:
            gallery_html = "<div class='media-catalog'>"
            for ma in media_assets:
                img_src = ma["base64"] if ma["base64"] else ""
                fallback_avatar = f"<div class='thumbnail-fallback'>{ma['expression'][:2].upper()}</div>"
                img_tag = f"<img src='{img_src}' alt='{ma['expression']}' class='thumbnail' />" if img_src else fallback_avatar
                gallery_html += f"""
                <div class='catalog-card'>
                    <div class='thumbnail-wrapper'>{img_tag}</div>
                    <div class='catalog-details'>
                        <strong>{ma['expression']}</strong>
                        <span class='hash-code'>{ma['sha256'][:16]}...</span>
                        <span class='path-code'>{ma['file_path']}</span>
                    </div>
                </div>
                """
            gallery_html += "</div>"
        else:
            gallery_html = "<p style='color:#64748b; font-style:italic;'>No associated media assets registered.</p>"
            
        # Page html
        page_html = f"""
        <div class="dossier-page">
            <!-- Header section -->
            <div class="header-sec">
                <div>
                    <span class="badge-title">SOVEREIGN OS OPERATIONAL INTELLIGENCE REGISTER</span>
                    <h1 class="adv-title">Dossier: {display_name or user_name}</h1>
                </div>
                <div style="text-align: right;">
                    <span class="entropy-tag" style="border-color: {color}; color: {color};">TEAM: {team.upper()}</span>
                    <span class="status-code">MagicDNS Secure Connection Mapped</span>
                </div>
            </div>
            
            <div class="divider"></div>
            
            <!-- Credentials & Avatar section -->
            <div class="credentials-grid">
                <div class="left-col">
                    <table class="meta-table">
                        <tr>
                            <th>SYS_ID</th>
                            <td><code>{p_id or "N/A"}</code></td>
                        </tr>
                        <tr>
                            <th>USER_NAME</th>
                            <td><code>{user_name}</code></td>
                        </tr>
                        <tr>
                            <th>ROUTING ZONE</th>
                            <td style="color: {color}; font-weight: bold;">{team.upper()}</td>
                        </tr>
                        <tr>
                            <th>INTERACTION CADENCE</th>
                            <td><code>{cadence}</code></td>
                        </tr>
                        <tr>
                            <th>BOGGS REACTIVITY</th>
                            <td>Level {boggs_level}</td>
                        </tr>
                        <tr>
                            <th>VISUAL THEME CLASS</th>
                            <td><code>{u_visual_style}</code></td>
                        </tr>
                        <tr>
                            <th>EMAIL ALIAS</th>
                            <td>{email_alias or "None"}</td>
                        </tr>
                    </table>
                </div>
                <div class="right-col">
                    <div class="avatar-container" style="border-color: {color}60;">
                        {f"<img src='{avatar_b64}' class='avatar-img' />" if avatar_b64 else "<div class='avatar-placeholder'>?</div>"}
                        <div class="corner-tl" style="border-top-color: {color}; border-left-color: {color};"></div>
                        <div class="corner-tr" style="border-top-color: {color}; border-right-color: {color};"></div>
                        <div class="corner-bl" style="border-bottom-color: {color}; border-left-color: {color};"></div>
                        <div class="corner-br" style="border-bottom-color: {color}; border-right-color: {color};"></div>
                    </div>
                </div>
            </div>
            
            <!-- EXIF Prompt Mappings -->
            <div class="section-title">EXIF Prompt Mappings & Asset Prompts</div>
            <div class="prompt-box">
                <div class="prompt-sub-box">
                    <strong>Avatar Generation Prompt (EXIF Metadata):</strong>
                    <p>{avatar_prompt or "No avatar generation prompt specified."}</p>
                </div>
                <div class="prompt-sub-box" style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 10px;">
                    <strong>Character Map Generation Prompt:</strong>
                    <p>{character_map_prompt or "No character map generation prompt specified."}</p>
                </div>
            </div>
            
            <!-- Directives Monospace block -->
            <div class="section-title">System Instruction / Prompt Directive</div>
            <div class="directive-box">
                <pre>{system_prompt}</pre>
            </div>
            
            <!-- Lore, Behavior, Governance -->
            <div class="section-title">Cognitive Profiles & Boundaries</div>
            <div class="profiles-grid">
                <div class="profile-card">
                    <strong>Deep Lore & Operational Biography</strong>
                    <p>{deep_lore or "No lore defined."}</p>
                </div>
                <div class="profile-card">
                    <strong>Behavior Expectations & Tone Notes</strong>
                    <p>{behavior_notes or "No behavior notes defined."}</p>
                </div>
                <div class="profile-card">
                    <strong>Governance & Alignment Boundaries</strong>
                    <p>{governance or "No governance boundaries defined."}</p>
                </div>
            </div>

            <!-- Associated Media Asset Catalog -->
            <div class="section-title">Associated Media Asset Catalog (Expressions)</div>
            {gallery_html}
            
            <!-- Canned Takes -->
            <div class="section-title">Canned Injections & hot-takes</div>
            <div class="takes-box">
                {takes_html}
            </div>
            
            <div class="footer-note">
                CONFIDENTIAL — FOR SOVEREIGN OS SYSTEM COMPLIANCE ONLY — GENERATED AUTOMATICALLY BY COGNITIVE INTERFACE AGENT
            </div>
        </div>
        """
        pages_html.append(page_html)
        
    con.close()
    
    # CSS Stylesheet
    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Share+Tech+Mono&display=swap');
    
    * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    
    body {
        margin: 0;
        padding: 0;
        background-color: #04060c;
        color: #f3f4f6;
        font-family: 'Outfit', sans-serif;
    }
    
    @page {
        size: letter;
        margin: 0;
    }
    
    .dossier-page {
        page-break-after: always;
        width: 8.5in;
        min-height: 11in;
        padding: 0.5in;
        background-color: #04060c;
        border: 1px solid #1e293b;
        position: relative;
        display: flex;
        flex-direction: column;
    }
    
    .dossier-page:last-child {
        page-break-after: avoid;
    }
    
    .header-sec {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }
    
    .badge-title {
        font-family: 'Share Tech Mono', monospace;
        font-size: 8pt;
        color: #64748b;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        display: block;
    }
    
    .adv-title {
        font-size: 18pt;
        font-weight: 800;
        margin: 4px 0 0 0;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .entropy-tag {
        font-family: 'Share Tech Mono', monospace;
        font-size: 9pt;
        font-weight: bold;
        border: 1px solid #38bdf8;
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 4px;
        background-color: rgba(56, 189, 248, 0.05);
        display: inline-block;
    }
    
    .status-code {
        font-family: 'Share Tech Mono', monospace;
        font-size: 7pt;
        color: #475569;
        display: block;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .divider {
        height: 2px;
        background: linear-gradient(90deg, #1e293b, #475569, #1e293b);
        margin: 15px 0;
    }
    
    .credentials-grid {
        display: grid;
        grid-template-columns: 8fr 4fr;
        gap: 20px;
        margin-bottom: 15px;
    }
    
    .meta-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 9pt;
    }
    
    .meta-table th {
        text-align: left;
        color: #64748b;
        font-family: 'Share Tech Mono', monospace;
        padding: 4px 0;
        width: 150px;
        font-weight: normal;
        border-bottom: 1px solid #1e293b;
    }
    
    .meta-table td {
        color: #e2e8f0;
        padding: 4px 0;
        border-bottom: 1px solid #1e293b;
    }
    
    .meta-table code {
        font-family: 'Share Tech Mono', monospace;
        background-color: #0f172a;
        padding: 2px 6px;
        border-radius: 3px;
        color: #38bdf8;
    }
    
    .avatar-container {
        width: 130px;
        height: 130px;
        background-color: #020617;
        border: 2px solid #38bdf8;
        border-radius: 12px;
        position: relative;
        padding: 4px;
        margin-left: auto;
    }
    
    .avatar-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 8px;
    }
    
    .avatar-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28pt;
        color: #334155;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .corner-tl, .corner-tr, .corner-bl, .corner-br {
        position: absolute;
        width: 10px;
        height: 10px;
        border-style: solid;
        border-width: 0;
    }
    
    .corner-tl { top: -2px; left: -2px; border-top-width: 2px; border-left-width: 2px; }
    .corner-tr { top: -2px; right: -2px; border-top-width: 2px; border-right-width: 2px; }
    .corner-bl { bottom: -2px; left: -2px; border-bottom-width: 2px; border-left-width: 2px; }
    .corner-br { bottom: -2px; right: -2px; border-bottom-width: 2px; border-right-width: 2px; }
    
    .section-title {
        font-family: 'Share Tech Mono', monospace;
        font-size: 8pt;
        color: #38bdf8;
        border-bottom: 1px solid #334155;
        padding-bottom: 4px;
        margin-top: 15px;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: bold;
    }
    
    .prompt-box {
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        font-size: 8pt;
        line-height: 1.4;
    }
    
    .prompt-sub-box strong {
        color: #64748b;
        font-family: 'Share Tech Mono', monospace;
        display: block;
        margin-bottom: 4px;
    }
    
    .prompt-sub-box p {
        margin: 0;
        color: #cbd5e1;
        text-align: justify;
    }
    
    .directive-box {
        background-color: #020617;
        border: 1px dashed #334155;
        border-radius: 8px;
        padding: 10px;
        max-height: 180px;
        overflow-y: hidden;
    }
    
    .directive-box pre {
        margin: 0;
        font-family: 'Share Tech Mono', monospace;
        font-size: 7.5pt;
        color: #22c55e;
        white-space: pre-wrap;
        word-break: break-all;
        line-height: 1.3;
    }
    
    .profiles-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }
    
    .profile-card {
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        font-size: 8pt;
        display: flex;
        flex-direction: column;
    }
    
    .profile-card strong {
        font-family: 'Share Tech Mono', monospace;
        color: #64748b;
        margin-bottom: 4px;
        display: block;
        font-size: 7.5pt;
        text-transform: uppercase;
    }
    
    .profile-card p {
        margin: 0;
        color: #cbd5e1;
        text-align: justify;
        line-height: 1.4;
    }
    
    .media-catalog {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }
    
    .catalog-card {
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .thumbnail-wrapper {
        width: 100%;
        height: 120px;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #334155;
        background-color: #020617;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .thumbnail {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .thumbnail-fallback {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-family: 'Share Tech Mono', monospace;
        color: #475569;
    }
    
    .catalog-details {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .catalog-details strong {
        font-size: 10px;
        color: #ffffff;
        text-transform: capitalize;
    }
    
    .catalog-details .hash-code {
        font-family: 'Share Tech Mono', monospace;
        font-size: 7px;
        color: #f59e0b;
    }
    
    .catalog-details .path-code {
        font-family: 'Share Tech Mono', monospace;
        font-size: 6.5px;
        color: #64748b;
        word-break: break-all;
    }
    
    .takes-box {
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        max-height: 140px;
        overflow-y: hidden;
    }
    
    .takes-box ul {
        margin: 0;
        padding-left: 15px;
        font-size: 8pt;
        color: #cbd5e1;
        line-height: 1.4;
    }
    
    .footer-note {
        margin-top: auto;
        padding-top: 15px;
        border-top: 1px solid #1e293b;
        text-align: center;
        font-family: 'Share Tech Mono', monospace;
        font-size: 6.5pt;
        color: #334155;
        letter-spacing: 1px;
    }
    """
    
    # HTML compilation
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Sovereign OS AI Advocate Dossiers</title>
        <style>
            {css_content}
        </style>
    </head>
    <body>
        {"".join(pages_html)}
    </body>
    </html>
    """
    
    # Write intermediate HTML
    temp_html = tempfile.NamedTemporaryFile(dir="/home/james/stacklabs", suffix=".html", delete=False)
    temp_html.write(html_content.encode("utf-8"))
    temp_html.close()
    temp_html_path = temp_html.name
    
    # Dynamically determine filename based on selection size and route to media_vault
    out_filename = "sovereign_advocates_dossier.pdf"
    if len(personas) == 1:
        out_filename = f"{personas[0].get('user_name', 'sovereign_advocate')}_dossier.pdf"
        
    output_dir = "/home/james/stacklabs/media_vault/03_Assets/Lookbooks"
    os.makedirs(output_dir, exist_ok=True)
    temp_pdf_path = os.path.join(output_dir, out_filename)
    
    import shutil
    chrome_path = None
    for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        p = shutil.which(name)
        if p:
            chrome_path = p
            break
    if not chrome_path:
        fallbacks = [
            "/home/james/.local/bin/google-chrome",
            "/home/james/.local/bin/google-chrome-stable",
            "/home/james/.local/bin/chromium-browser",
            "/home/james/.local/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome"
        ]
        for p in fallbacks:
            if os.path.exists(p):
                chrome_path = p
                break
    if not chrome_path:
        chrome_path = "/usr/local/bin/google-chrome"

    chrome_cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={temp_pdf_path}",
        f"file://{temp_html_path}"
    ]
    
    try:
        result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            os.remove(temp_html_path)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            raise HTTPException(status_code=500, detail=f"Headless Chrome error: {result.stderr}")
    except Exception as e:
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF generation process failed: {str(e)}")
        
    # Queue cleanup tasks (keep the persistent PDF file)
    if background_tasks:
        background_tasks.add_task(os.remove, temp_html_path)
        
    return FileResponse(
        temp_pdf_path, 
        media_type="application/pdf", 
        filename=out_filename
    )


async def print_lookbook_pdf(advocate: str, ids: str = None, background_tasks: BackgroundTasks = None):
    import base64
    import sqlite3 as _sq
    import os
    import tempfile
    import json
    import shutil
    import subprocess
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    
    if not advocate:
        raise HTTPException(status_code=400, detail="Missing advocate query parameter")
        
    conn = _sq.connect(DB_PATH)
    conn.row_factory = _sq.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM persona WHERE user_name = ? OR user_name = ?", (advocate, advocate.lower().replace(" ", "_")))
    persona_row = cur.fetchone()
    p_info = dict(persona_row) if persona_row else {
        "user_name": advocate,
        "display_name": advocate.capitalize(),
        "team": "Sovereign OS",
        "color": "#10b981",
        "avatar_url": ""
    }
    
    display_name = p_info.get("display_name") or p_info.get("user_name")
    team = p_info.get("team", "Sovereign OS")
    color = p_info.get("color", "#10b981")
    
    def resolve_media_file_to_base64(file_path: str) -> str:
        if not file_path:
            return ""
        clean_path = file_path.lstrip("/")
        search_dirs = [
            "/home/james/stacklabs/avatars",
            "/home/james/stacklabs/01_Sovereign_Portal/public",
            "/home/james/stacklabs/02_Sovereign_Media/public",
            "/home/james/stacklabs/15_FanStack/public",
            "/home/james/stacklabs/dna/media",
            "/home/james/stacklabs"
        ]
        for d in search_dirs:
            p = os.path.join(d, clean_path)
            if os.path.exists(p) and os.path.isfile(p):
                try:
                    with open(p, 'rb') as img_f:
                        raw_data = img_f.read()
                        b64 = base64.b64encode(raw_data).decode('utf-8')
                        mime = "image/png"
                        if p.lower().endswith('.webp'):
                            mime = "image/webp"
                        elif p.lower().endswith(('.jpg', '.jpeg')):
                            mime = "image/jpeg"
                        elif p.lower().endswith('.svg'):
                            mime = "image/svg+xml"
                        return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
        return ""

    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        placeholders = ",".join("?" for _ in id_list)
        cur.execute(f"""
            SELECT c.sys_id, c.expression, c.file_path, c.sha256, s.category, s.name
            FROM cmdb_ci_media_asset c
            LEFT JOIN sys_media_asset s ON c.file_path = s.file_path OR c.sha256 = s.md5_hash
            WHERE (c.advocate = ? OR c.advocate = ?) AND c.sys_id IN ({placeholders})
        """, [advocate, advocate.lower().replace(" ", "_")] + id_list)
    else:
        cur.execute("""
            SELECT c.sys_id, c.expression, c.file_path, c.sha256, s.category, s.name
            FROM cmdb_ci_media_asset c
            LEFT JOIN sys_media_asset s ON c.file_path = s.file_path OR c.sha256 = s.md5_hash
            WHERE c.advocate = ? OR c.advocate = ?
        """, (advocate, advocate.lower().replace(" ", "_")))
        
    rows = cur.fetchall()
    
    categories = {
        "Adventures": [],
        "Raw Photos": [],
        "Concept Art": []
    }
    
    for r in rows:
        fp = r["file_path"]
        sha = r["sha256"] or ""
        expr = r["expression"]
        cat = r["category"] or ("Concept Art" if "concept" in expr.lower() else "Raw Photos")
        
        if cat not in categories:
            categories[cat] = []
            
        if fp.lower().endswith('.mp4'):
            img_b64 = ""
            is_video = True
        else:
            img_b64 = resolve_media_file_to_base64(fp)
            is_video = False
            
        categories[cat].append({
            "expression": expr,
            "file_path": fp,
            "sha256": sha,
            "base64": img_b64,
            "is_video": is_video
        })
        
    conn.close()
    
    sections_html = []
    for cat_name, assets in categories.items():
        if not assets:
            continue
            
        grid_items_html = ""
        for a in assets:
            if a["is_video"]:
                img_tag = f"<div class='lookbook-video-placeholder'><div class='play-icon'>&#9654;</div><span>VIDEO: {a['expression']}</span></div>"
            elif a["base64"]:
                img_tag = f"<img src='{a['base64']}' class='lookbook-img' />"
            else:
                img_tag = f"<div class='lookbook-placeholder'>No Image Data</div>"
                
            grid_items_html += f"""
            <div class="lookbook-card">
                <div class="lookbook-img-container">
                    {img_tag}
                </div>
                <div class="lookbook-details">
                    <div class="lookbook-expr-name">{a['expression']}</div>
                    <div class="lookbook-sha">SHA256: <code>{a['sha256'][:12]}...</code></div>
                    <div class="lookbook-path">Path: <code>{a['file_path']}</code></div>
                </div>
            </div>
            """
            
        sections_html.append(f"""
        <div class="category-section">
            <h2 class="category-title" style="border-left: 4px solid {color};">{cat_name.upper()} ({len(assets)})</h2>
            <div class="lookbook-grid">
                {grid_items_html}
            </div>
        </div>
        """)
        
    if not sections_html:
        sections_html.append("<p style='color:#64748b; text-align:center; margin-top:50px;'>No lookbook assets selected or found.</p>")
        
    css_content = f"""
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Share+Tech+Mono&display=swap');
    
    * {{
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    
    body {{
        margin: 0;
        padding: 0;
        background-color: #04060c;
        color: #f3f4f6;
        font-family: 'Outfit', sans-serif;
    }}
    
    @page {{
        size: letter;
        margin: 0.4in;
    }}
    
    .lookbook-dossier {{
        width: 100%;
        background-color: #04060c;
        min-height: 100%;
        display: flex;
        flex-direction: column;
    }}
    
    .header-sec {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 15px;
        margin-bottom: 25px;
    }}
    
    .badge-title {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 8pt;
        color: #64748b;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        display: block;
    }}
    
    .adv-title {{
        font-size: 20pt;
        font-weight: 800;
        margin: 4px 0 0 0;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .entropy-tag {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 9pt;
        font-weight: bold;
        border: 1px solid {color};
        color: {color};
        padding: 4px 12px;
        border-radius: 4px;
        background-color: rgba(56, 189, 248, 0.05);
        display: inline-block;
    }}
    
    .category-section {{
        margin-bottom: 30px;
        page-break-inside: avoid;
    }}
    
    .category-title {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 11pt;
        color: #ffffff;
        background: #090d16;
        padding: 8px 12px;
        margin-top: 0;
        margin-bottom: 15px;
        letter-spacing: 1.5px;
    }}
    
    .lookbook-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }}
    
    .lookbook-card {{
        background-color: #090d16;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        display: flex;
        flex-direction: column;
        page-break-inside: avoid;
    }}
    
    .lookbook-img-container {{
        width: 100%;
        height: 140px;
        background-color: #020617;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #1e293b;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    
    .lookbook-img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    
    .lookbook-video-placeholder {{
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: #0d1527;
        color: #cbd5e1;
        font-size: 8px;
        gap: 8px;
    }}
    
    .play-icon {{
        font-size: 24px;
        color: {color};
    }}
    
    .lookbook-placeholder {{
        font-size: 9pt;
        color: #475569;
    }}
    
    .lookbook-details {{
        margin-top: 10px;
    }}
    
    .lookbook-expr-name {{
        font-weight: 600;
        font-size: 9.5pt;
        color: #ffffff;
        margin-bottom: 4px;
        text-transform: capitalize;
    }}
    
    .lookbook-sha, .lookbook-path {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 6.5pt;
        color: #64748b;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    
    .lookbook-sha code, .lookbook-path code {{
        color: {color};
    }}
    
    .footer-note {{
        margin-top: 30px;
        padding-top: 15px;
        border-top: 1px solid #1e293b;
        text-align: center;
        font-family: 'Share Tech Mono', monospace;
        font-size: 6.5pt;
        color: #334155;
        letter-spacing: 1px;
        page-break-before: auto;
    }}
    """
    
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Sovereign OS AI Advocate Lookbook - {display_name}</title>
        <style>
            {css_content}
        </style>
    </head>
    <body>
        <div class="lookbook-dossier">
            <div class="header-sec">
                <div>
                    <span class="badge-title">SOVEREIGN OS OPERATIONAL LOOKBOOK REGISTER</span>
                    <h1 class="adv-title">Lookbook: {display_name}</h1>
                </div>
                <div style="text-align: right;">
                    <span class="entropy-tag">ZONE: {team.upper()}</span>
                </div>
            </div>
            
            {"".join(sections_html)}
            
            <div class="footer-note">
                CONFIDENTIAL — FOR SOVEREIGN OS SYSTEM COMPLIANCE ONLY — GENERATED AUTOMATICALLY BY COGNITIVE INTERFACE AGENT
            </div>
        </div>
    </body>
    </html>
    """
    
    temp_html = tempfile.NamedTemporaryFile(dir="/home/james/stacklabs", suffix=".html", delete=False)
    temp_html.write(html_content.encode("utf-8"))
    temp_html.close()
    temp_html_path = temp_html.name
    
    output_dir = "/home/james/stacklabs/media_vault/03_Assets/Lookbooks"
    os.makedirs(output_dir, exist_ok=True)
    temp_pdf_path = os.path.join(output_dir, f"{advocate}_lookbook.pdf")
    
    chrome_path = None
    for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        p = shutil.which(name)
        if p:
            chrome_path = p
            break
    if not chrome_path:
        fallbacks = [
            "/home/james/.local/bin/google-chrome",
            "/home/james/.local/bin/google-chrome-stable",
            "/home/james/.local/bin/chromium-browser",
            "/home/james/.local/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome"
        ]
        for p in fallbacks:
            if os.path.exists(p):
                chrome_path = p
                break
    if not chrome_path:
        chrome_path = "/usr/local/bin/google-chrome"

    chrome_cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={temp_pdf_path}",
        f"file://{temp_html_path}"
    ]
    
    try:
        subprocess.run(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as e:
        if os.path.exists(temp_html_path):
            os.unlink(temp_html_path)
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"Headless Chrome compilation failed: {e}")
        
    def cleanup_files():
        try:
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)
        except Exception:
            pass
            
    if background_tasks:
        background_tasks.add_task(cleanup_files)
        
    return FileResponse(
        temp_pdf_path,
        media_type="application/pdf",
        filename=f"{advocate}_lookbook.pdf"
    )
