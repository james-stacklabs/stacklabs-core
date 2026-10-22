#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil

# Staging Directories
PRESSKIT_DIR = "/home/james/sovereign_inbox/dashboards/presskit"
REPORTS_DIR = "/home/james/sovereign_inbox/reports/notebook_sync"

os.makedirs(PRESSKIT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# 1. Metadatabase of all Press Kit Visual Assets
ASSET_METADATA = {
    "sovereign_os_architecture.png": {
        "title": "Sovereign OS Monolithic Core Architecture Diagram",
        "doc_id": "presskit_sovereign_os_architecture.md",
        "description": "The definitive technical blueprint of the Sovereign OS monolithic core architecture. Features the dark central core module with thin neon-cyan data conduits routing to two active stacks ('FANSTACK' in cyan and 'WEEDSTACK' in green) alongside a standby socket labeled 'YOUR STACK HERE'. The lower panel displays the dedicated local hardware host 'CLIO' with an active, pulsing telemetry line. Confident, cinematic, and technical.",
        "prompt": "Dark premium technical illustration. Central monolithic core labeled 'SOVEREIGN OS' glowing with cyan light. Three ROM module shapes plugging into it: one cyan labeled 'FANSTACK', one green labeled 'WEEDSTACK', one dim gray labeled 'YOUR STACK HERE'. Thin light data flow lines connecting core to modules. Bottom: single glowing edge hardware node labeled 'NODE CLIO — AMD ZEN 4' with a heartbeat pulse. No cloud icons. Deep black background. Bloomberg terminal meets premium spirits brand aesthetic."
    },
    "mard_engine_visual.png": {
        "title": "M.A.R.D Multi-Agent Discourse Simulation Engine",
        "doc_id": "presskit_mard_engine_visual.md",
        "description": "Visualization of the Multi-Agent Relational Discourse (M.A.R.D.) Swarm. Set in a premium, dark digital war room. Faintly glowing AI persona silhouettes are arranged around a large circular desk, connected via conduits of light to a pulsing 'LIVE FEED' data node. Floating cards display active commentator chat bubbles, social feeds, and metrics in real-time, overseen by an interactive switchboard toggle panel in the corner.",
        "prompt": "Dark cinematic illustration, 16:9. A premium digital war room. Multiple AI persona avatar silhouettes arranged around a circular table, each glowing in their team color (cyan, green, amber). Central pulsing data node on the table labeled 'LIVE FEED'. Light lines connecting feed to each persona. Floating content cards above showing social posts and chat messages. Corner panel showing toggle switches — some glowing green ON, some dark STANDBY. Deep black background."
    },
    "bar_question_hero.png": {
        "title": "The Foundational Brand Intake Bar Question",
        "doc_id": "presskit_bar_question_hero.md",
        "description": "Typographical billboard layout summarizing the core Sovereign branding inquiry: 'If your brand walked into a bar — who would it be, what would it order, what would it play on the jukebox, and who would it talk to?'. Large, high-contrast, clean modern sans-serif white typography on an absolute black velvet backdrop. Below in small monospace type is the REST endpoint: 'POST /api/stacks/seed'. Pure philosophical confidence.",
        "prompt": "Minimalist dark typographic poster, 16:9. Deep near-black background. Large clean sans-serif white text centered: 'If your brand walked into a bar — who would it be, what would it order, what would it play on the jukebox, and who would it talk to?' Below in small monospace type: 'POST /api/stacks/seed' Nothing else. No decoration. Billboard confidence."
    },
    "edge_node_hero.png": {
        "title": "Edge Node Hardware & Anti-Cloud Manifesto",
        "doc_id": "presskit_edge_node_hero.md",
        "description": "Dramatic hardware close-up of a compact edge computing block (Mac Studio styled) resting on a polished dark surface. Side-lit vents glow with warm internal system heat. A single ethernet cable connects the system, representing physical decoupling. Floating cleanly above the hardware is the anti-cloud manifesto: 'MARGINAL COST: $0.00' and 'after silicon'. Confident, premium architectural product design.",
        "prompt": "Dark dramatic product photography style illustration. Single compact hardware box (Mac Studio style) on a dark surface. Dramatic side lighting, glowing vents. Single ethernet cable. No racks, no data centers. Just one box. Floating above it in clean white type: 'MARGINAL COST: $0.00' Below in smaller type: 'after silicon' Deep black background."
    },
    "content_source_matrix.png": {
        "title": "WeedStack Content Source Integration Panel",
        "doc_id": "presskit_content_source_matrix.md",
        "description": "A technical screenshot illustration of the WeedStack operator dashboard. Features a clean, dark glassmorphic control block displaying 7 content source toggles. 'Batch Drop Events' and 'Cannabis Industry News' glow in WildSeed green (#00c878) as active. A mouse cursor hovers over 'Reddit Communities' in standby, illustrating the absolute simplicity of expanding brand intelligence feeds with one click.",
        "prompt": "Dark premium UI dashboard screenshot illustration, 16:9. Clean dark panel showing a list of seven content source toggles. Two toggles glowing green (ON). Five toggles dark gray (STANDBY). A cursor hovering over the Reddit toggle. Corner: small live chat feed updating in real time. Sovereign OS dark glassmorphic design language. Green accent color #00c878. Deep black background."
    },
    "persona_cards_fanstack.png": {
        "title": "FanStack Swarm Persona Trading Cards",
        "doc_id": "presskit_persona_cards_fanstack.md",
        "description": "High-end glassmorphic trading cards showcasing the active MLB commentary team: Barf, Welfare Bucco, Cubs Conspiracy, and Yankee Stadium Bully. The cards are arranged in a dynamic, fanned layout with cyan borders. Each card details individual avatar photography, name, team alignment, and their signature unhinged quote in italics. Baseball design cues blended with sleek digital glassmorphism.",
        "prompt": "High-end glassmorphic trading cards for Barf, Welfare Bucco, Cubs Conspiracy, and Yankee Stadium Bully. Fanned composite layout, cyan borders, baseball details."
    },
    "persona_cards_weedstack.png": {
        "title": "WeedStack Swarm Persona Trading Cards",
        "doc_id": "presskit_persona_cards_weedstack.md",
        "description": "High-end botanical-technical trading cards showcasing the cannabis brand commentators: Dr. Terp, Terpene Trekker, Metrc Maven, and Cultivar Catalyst. Arranged in a dynamic fanned arc with WildSeed green borders. Each card highlights technical avatar pictures, specific expertise badges (Dabs, Lab Analysis, Compliance), and signature quotes in italics. Editorial, premium, and professional.",
        "prompt": "High-end botanical-technical trading cards for Dr. Terp, Terpene Trekker, Metrc Maven, and Cultivar Catalyst. Fanned composite, green borders."
    },
    "uat_02_weedstack_sim_001.png": {
        "title": "UAT Audit - Live WeedStack Active Simulation Room",
        "doc_id": "presskit_uat_weedstack_sim.md",
        "description": "UAT live screenshot audit of the WeedStack simulation interface. Renders the real-time Multi-Agent discourse room showing active thread streams, user roster status grids, and historical conversation cards. Verified fully responsive on both mobile viewport simulations and desktop viewports, featuring fluid CSS layouts.",
        "prompt": "UAT live screenshot of WeedStack simulation interface room, active chat logs."
    },
    "uat_03_sdlc_portal.png": {
        "title": "UAT Audit - Enterprise SDLC Ticketing Center",
        "doc_id": "presskit_uat_sdlc_portal.md",
        "description": "UAT live screenshot of the Enterprise SDLC Ticketing dashboard running on port 8095. Showcases the active Sprint Board, detailing ticket IDs (STRY/INC), ticket types, statuses, assigned owners, and cumulative story velocity metrics.",
        "prompt": "UAT live screenshot of SDLC portal dashboard."
    },
    "uat_04_cmdb_center.png": {
        "title": "UAT Audit - CMDB System & CI Roster Center",
        "doc_id": "presskit_uat_cmdb_center.md",
        "description": "UAT live screenshot of the CMDB Configuration Items dashboard. Renders active host nodes, bare-metal services, and the registered commentating agents, tracking their operational profiles and system credentials securely.",
        "prompt": "UAT live screenshot of CMDB configuration items registry."
    },
    "scruffys_weedstack_meltdown.png": {
        "title": "WeedStack Live Bullpen Meltdown Campaign in Scruffy's Tavern",
        "doc_id": "presskit_weedstack_meltdown.md",
        "description": "Live UI capture of Scruffy's Tavern during the 8th inning Mets bullpen meltdown. WeedStack promoters (dispensary_gary, compliance_karen, old_growth_pete, dr_terp) seamlessly pitch their products and trigger the automatic 50% discount program in response to Edwin Diaz blowing the lead. Confident, modern, and engaging.",
        "prompt": "Live screenshot of WeedStack simulation room, Edwin Diaz blown save, 50% off product pitches."
    }
}

# Step 1: Generate Markdown Logs for NotebookLM Ingestion
print("📂 STEP 1: Generating isolated markdown logs for NotebookLM ingestion...")
for filename, meta in ASSET_METADATA.items():
    md_path = os.path.join(REPORTS_DIR, meta["doc_id"])
    if meta["doc_id"] == "presskit_weedstack_meltdown.md":
        print(f"  ⏭️ Skipping generation for custom premium file: {md_path}")
        continue
    content = f"""# Visual Asset Log: {meta["title"]}
* **Filename:** {filename}
* **Domain Alignment:** {"WeedStack / WildSeed" if "weed" in filename or "mfg" in filename else "FanStack / SovereignOS Core"}
* **Aesthetic Standard:** Dark, glassmorphic, premium near-black (#0a0a0f), mono labels.

## 📝 Visual Description
{meta["description"]}

## 🎨 Vertex AI Prompt Structure
```text
{meta["prompt"]}
```

---
*Sovereign OS Press Kit Ledger — Compiled May 28, 2026*
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Generated: {md_path}")

# Step 2: Build HTML Manifest with absolute embeds
print("\n🎨 STEP 2: Creating aggregated HTML manifest...")
html_file = "/tmp/sovereign_press_kit_temp.html"
pdf_output = os.path.join(REPORTS_DIR, "Sovereign_OS_Press_Kit_Manifest.pdf")

html_sections = []
for filename, meta in ASSET_METADATA.items():
    img_path = os.path.join(PRESSKIT_DIR, filename)
    html_sections.append(f"""
    <div class="asset-card">
        <h3>{meta["title"]}</h3>
        <div class="meta-row">
            <span class="meta-label">File:</span> <span class="meta-value"><code>{filename}</code></span>
        </div>
        <img src="file://{img_path}" alt="{meta["title"]}">
        <div class="description-block">
            <h4>Clinical / Technical Role</h4>
            <p>{meta["description"]}</p>
            <h4>Synthesized Prompt</h4>
            <pre><code>{meta["prompt"]}</code></pre>
        </div>
    </div>
    """)

html_body = "\n".join(html_sections)

# Ultra-premium HTML/CSS Template (Bloomberg Terminal meets high-end spirits brand)
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sovereign OS Press Kit & Ingest Manifest</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root {{
            --bg-dark: #07070a;
            --card-dark: #0e0e15;
            --cyan-glow: #00d4ff;
            --green-glow: #00c878;
            --text-white: #f8fafc;
            --text-gray: #94a3b8;
            --border-dark: #1e1e2d;
        }}
        
        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        
        @page {{
            size: letter;
            margin: 20mm;
            @bottom-right {{
                content: counter(page);
                font-family: 'Outfit', sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @top-left {{
                content: "Sovereign OS • Official Media Ingest Staging Manifest";
                font-family: 'Outfit', sans-serif;
                font-size: 7.5pt;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.15em;
            }}
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            color: var(--text-white);
            background-color: var(--bg-dark);
            line-height: 1.5;
            font-size: 10pt;
            margin: 0;
            padding: 0;
        }}
        
        .cover-page {{
            page-break-after: always;
            height: 9.0in;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 50px;
            border: 2px solid var(--border-dark);
            background: linear-gradient(135deg, #07070a 0%, #0e0e15 100%);
            border-top: 5px solid var(--cyan-glow);
        }}
        
        .cover-header {{
            font-family: 'Outfit', sans-serif;
            font-size: 9pt;
            text-transform: uppercase;
            letter-spacing: 0.3em;
            color: var(--cyan-glow);
        }}
        
        .cover-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 26pt;
            font-weight: 800;
            line-height: 1.15;
            color: var(--text-white);
            margin: 0 0 15px 0;
            letter-spacing: -0.5px;
        }}
        
        .cover-subtitle {{
            font-size: 12pt;
            color: var(--green-glow);
            margin: 0 0 40px 0;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .cover-divider {{
            width: 80px;
            height: 3px;
            background-color: var(--cyan-glow);
        }}
        
        .cover-footer {{
            border-top: 1px solid var(--border-dark);
            padding-top: 30px;
            display: flex;
            justify-content: space-between;
            font-size: 9pt;
            color: var(--text-gray);
        }}
        
        .cover-footer-item strong {{
            color: var(--text-white);
            display: block;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-size: 7.5pt;
            letter-spacing: 0.1em;
            font-family: 'Outfit', sans-serif;
        }}
        
        .content-container {{
            padding: 0 10px;
        }}
        
        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 16pt;
            color: var(--text-white);
            border-bottom: 2px solid var(--border-dark);
            padding-bottom: 8px;
            margin-top: 0;
            margin-bottom: 1.5em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .asset-card {{
            background-color: var(--card-dark);
            border: 1px solid var(--border-dark);
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 40px;
            page-break-inside: avoid;
        }}
        
        h3 {{
            font-family: 'Outfit', sans-serif;
            font-size: 12pt;
            color: var(--cyan-glow);
            margin-top: 0;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .meta-row {{
            font-size: 8.5pt;
            color: var(--text-gray);
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-dark);
            padding-bottom: 10px;
        }}
        
        .meta-label {{
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        img {{
            max-width: 100%;
            height: 3.2in;
            object-fit: contain;
            display: block;
            margin: 20px auto;
            border: 1px solid var(--border-dark);
            border-radius: 6px;
        }}
        
        .description-block h4 {{
            font-family: 'Outfit', sans-serif;
            font-size: 9.5pt;
            color: var(--green-glow);
            text-transform: uppercase;
            margin-top: 20px;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }}
        
        .description-block p {{
            color: var(--text-gray);
            font-size: 9.5pt;
            margin: 0 0 15px 0;
            text-align: justify;
        }}
        
        pre {{
            background-color: #050508;
            border: 1px solid var(--border-dark);
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 8pt;
            margin: 0;
            white-space: pre-wrap;
        }}
        
        code {{
            color: var(--cyan-glow);
        }}
    </style>
</head>
<body>

    <div class="cover-page">
        <div class="cover-header">Stack Labs • Core Visual Ingestion Manifest</div>
        <div class="cover-body">
            <h1 class="cover-title">SOVEREIGN OS:<br>MEDIA ASSETS & INGESTION DIRECTORY</h1>
            <div class="cover-subtitle">Aggregated Vision Frames and Cognitive Text Log Manifest for NotebookLM</div>
            <div class="cover-divider"></div>
        </div>
        <div class="cover-footer">
            <div class="cover-footer-item">
                <strong>Project Domain</strong>
                Sovereign OS Swarm Ecosystem
            </div>
            <div class="cover-footer-item">
                <strong>Principal Architect</strong>
                James Carroll
            </div>
            <div class="cover-footer-item">
                <strong>Ingest Date</strong>
                May 28, 2026
            </div>
        </div>
    </div>

    <div class="content-container">
        <h2>📷 Aggregated Vision Frame Index</h2>
        {html_body}
    </div>

</body>
</html>
"""

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"  ✅ HTML Compiled at: {html_file}")

# Step 3: Headless Chrome Compilation to PDF
print("\n🖥️ STEP 3: Compiling Aggregated PDF Manifest via Headless Chrome...")
chrome_cmd = [
    "/usr/local/bin/google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--virtual-time-budget=10000",
    f"--print-to-pdf={pdf_output}",
    f"file://{html_file}"
]

result = subprocess.run(chrome_cmd, capture_output=True, text=True)

if os.path.exists(html_file):
    try:
        os.remove(html_file)
        print("  🧹 Cleaned up temporary HTML file.")
    except Exception as e:
        print(f"  ⚠️ Cleanup error: {e}")

if result.returncode == 0 and os.path.exists(pdf_output):
    print(f"  ✅ PDF Successfully Compiled! Size: {os.path.getsize(pdf_output) / 1024:.2f} KB")
else:
    print(f"  ❌ PDF Compilation Failed!\nstdout: {result.stdout}\nstderr: {result.stderr}")
    sys.exit(1)

# Step 4: Sync to Google Drive
print("\n🛜 STEP 4: Synchronizing directories to Google Drive...")
try:
    print("  Syncing presskit media assets...")
    subprocess.run([
        "rclone", "sync",
        PRESSKIT_DIR,
        "sovereign_os:SovereignOS_Clio_Sync/sovereign_inbox/dashboards/presskit",
        "--progress"
    ], check=True)
    
    print("  Syncing notebook_sync reports...")
    subprocess.run([
        "rclone", "sync",
        REPORTS_DIR,
        "sovereign_os:SovereignOS_Clio_Sync/sovereign_inbox/reports/notebook_sync",
        "--progress"
    ], check=True)
    
    print("  ✅ rclone Sync Successful!")
except Exception as e:
    print(f"  ❌ rclone Sync Failed: {e}")
    sys.exit(1)

# Step 5: Execute master sync_to_gdrive.sh to trigger Sorting Hat and NotebookLM buckets
print("\n🎩 STEP 5: Triggering Master Sorting Hat State Synchronization...")
try:
    subprocess.run(["bash", "/home/james/stacklabs/scripts/sync_to_gdrive.sh"], check=True)
    print("  ✅ Sorting Hat sync complete.")
except Exception as e:
    print(f"  ❌ Sorting Hat sync failed: {e}")
    sys.exit(1)

print("\n🚀 PIPELINE EXECUTION FULLY COMPLETE!")
