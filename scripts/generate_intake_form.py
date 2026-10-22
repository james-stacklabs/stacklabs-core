#!/usr/bin/env python3
# =============================================================================
# Generic Brand Intake Blueprint Generator
# =============================================================================
# Generates a premium HTML and PDF intake blueprint styled with brand-agnostic
# components and fallback inline vector assets.
# =============================================================================

import os
import base64
import subprocess

LOGO_PATH = "/home/james/sovereign_inbox/today/stacklabs_logo.jpeg"

HTML_OUT_TODAY = "/home/james/sovereign_inbox/today/Generic_Intake_Blueprint.html"
PDF_OUT_TODAY = "/home/james/sovereign_inbox/today/Generic_Intake_Blueprint.pdf"

HTML_OUT_REPORTS = "/home/james/sovereign_inbox/reports/Generic_Intake_Blueprint.html"
PDF_OUT_REPORTS = "/home/james/sovereign_inbox/reports/Generic_Intake_Blueprint.pdf"

def generate():
    print("🎨 Compiling premium Generic Brand Intake Blueprint...")
    
    logo_element = ""
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as img_f:
                encoded_logo = base64.b64encode(img_f.read()).decode("utf-8")
                logo_uri = f"data:image/jpeg;base64,{encoded_logo}"
                logo_element = f'<img src="{logo_uri}" alt="Brand Logo">'
        except Exception as e:
            print(f"⚠️ Error loading logo: {e}")
            
    if not logo_element:
        # Gorgeous fallback vector icon representing a stylized digital grid node
        logo_element = """
        <svg width="100" height="100" viewBox="0 0 100 100" style="filter: drop-shadow(0 4px 12px rgba(6,182,212,0.4));">
            <rect x="10" y="10" width="80" height="80" rx="16" fill="none" stroke="#06b6d4" stroke-width="4" opacity="0.4"/>
            <polygon points="50,22 75,37 75,63 50,78 25,63 25,37" fill="none" stroke="#06b6d4" stroke-width="3" stroke-dasharray="2 1"/>
            <circle cx="50" cy="50" r="16" fill="none" stroke="#06b6d4" stroke-width="4"/>
            <circle cx="50" cy="50" r="8" fill="#f59e0b"/>
            <line x1="50" y1="10" x2="50" y2="22" stroke="#06b6d4" stroke-width="2"/>
            <line x1="50" y1="78" x2="50" y2="90" stroke="#06b6d4" stroke-width="2"/>
            <line x1="10" y1="50" x2="25" y2="50" stroke="#06b6d4" stroke-width="2"/>
            <line x1="75" y1="50" x2="90" y2="50" stroke="#06b6d4" stroke-width="2"/>
        </svg>
        """
        
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Swarm Platform - Brand Ingestion & Seeding Intake Brief</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&family=Outfit:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        body {{
            background-color: #0b0f14;
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 40px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 850px;
            margin: 0 auto;
            background: linear-gradient(135deg, #10161d 0%, #0d1218 100%);
            border: 1px solid #1e293b;
            border-radius: 24px;
            padding: 50px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
        }}
        
        .container::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #06b6d4, #f59e0b);
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 30px;
            margin-bottom: 40px;
        }}
        
        .title-area {{
            max-width: 60%;
        }}
        
        .logo-area img, .logo-area svg {{
            max-height: 120px;
            border-radius: 12px;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.2rem;
            font-weight: 900;
            color: #ffffff;
            margin: 0 0 10px 0;
            letter-spacing: -0.02em;
        }}
        
        .subtitle {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #06b6d4;
            text-transform: uppercase;
            letter-spacing: 0.15em;
        }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 40px;
            background: rgba(15, 23, 42, 0.4);
            border: 1px dashed #334155;
            border-radius: 16px;
            padding: 24px;
        }}
        
        .meta-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        
        .meta-value input {{
            width: 90%;
            background: #090d11;
            border: 1px solid #334155;
            color: #ffffff;
            padding: 10px 14px;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            outline: none;
            transition: all 0.3s;
        }}
        
        .meta-value input:focus {{
            border-color: #06b6d4;
            box-shadow: 0 0 8px rgba(6,182,212,0.2);
        }}
        
        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.4rem;
            font-weight: 700;
            color: #ffffff;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #f59e0b;
            padding-left: 14px;
        }}
        
        .instruction {{
            font-size: 0.95rem;
            color: #94a3b8;
            margin-bottom: 20px;
            background: rgba(245, 158, 11, 0.05);
            border: 1px solid rgba(245, 158, 11, 0.15);
            padding: 14px 20px;
            border-radius: 10px;
        }}
        
        textarea {{
            width: 100%;
            height: 120px;
            background: #090d11;
            border: 1px solid #334155;
            color: #ffffff;
            padding: 14px;
            border-radius: 12px;
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            resize: vertical;
            outline: none;
            box-sizing: border-box;
            transition: all 0.3s;
            margin-bottom: 20px;
        }}
        
        textarea:focus {{
            border-color: #f59e0b;
            box-shadow: 0 0 8px rgba(245,158,11,0.2);
        }}
        
        .checklist-group {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 30px;
        }}
        
        .checklist-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
        }}
        
        .checklist-item input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            accent-color: #06b6d4;
            cursor: pointer;
        }}
        
        .advocate-card {{
            background: rgba(30, 41, 59, 0.25);
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 30px;
        }}
        
        .advocate-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 16px;
        }}
        
        .footer {{
            margin-top: 60px;
            border-top: 1px solid #1e293b;
            padding-top: 24px;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #64748b;
        }}
        
        @media print {{
            body {{
                background-color: #ffffff;
                color: #000000;
                padding: 0;
            }}
            .container {{
                border: none;
                box-shadow: none;
                padding: 0;
                background: none;
            }}
            h1, h2, .subtitle {{
                color: #000000;
            }}
            .meta-value input, textarea {{
                background: #ffffff;
                color: #000000;
                border: 1px solid #000000;
            }}
            .container::before {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-area">
                <h1>SWARM MATRIX</h1>
                <div class="subtitle">Brand Ingestion & Seeding Intake Blueprint</div>
            </div>
            <div class="logo-area">
                {logo_element}
            </div>
        </div>
        
        <p style="font-size: 1.05rem; color: #cbd5e1; margin-bottom: 40px;">
            Fill out this intake brief to configure and forge a custom AI Brand Stack on the seeding platform engine. 
            Once completed, save this document and return it alongside any visual or logo assets to trigger the automated 
            brand seeder command line interface. Your completed brand stack manual will be compiled and delivered in 15 minutes.
        </p>
        
        <div class="meta-grid">
            <div class="meta-item">
                <div class="meta-label">Brand Name</div>
                <div class="meta-value">
                    <input type="text" placeholder="e.g., Example Co. / Vintage Botanical Club">
                </div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Aesthetic Archetype Configuration</div>
                <div class="meta-value">
                    <input type="text" placeholder="e.g., Cozy Cardboard / Premium Slate / Slate Glass">
                </div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Active Sandbox Key</div>
                <div class="meta-value">
                    <input type="text" placeholder="e.g., BRAND_SANDBOX_01">
                </div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Volatility Baseline Entropy (1 - 11)</div>
                <div class="meta-value">
                    <input type="text" placeholder="e.g., Level 3 (Steady) or 11 (High Emergence)">
                </div>
            </div>
        </div>
        
        <h2>1. Active Feed Streams Matrix</h2>
        <div class="instruction">
            Configure the live external feeds and simulation triggers this stack should listen to:
        </div>
        <div class="checklist-group">
            <label class="checklist-item">
                <input type="checkbox" checked>
                <span>Batch Lifecycle Ledger & Environmental Telemetry</span>
            </label>
            <label class="checklist-item">
                <input type="checkbox" checked>
                <span>Local Community RSS feeds & Community News</span>
            </label>
            <label class="checklist-item">
                <input type="checkbox">
                <span>Standard Sports Telemetry & Live Matches</span>
            </label>
            <label class="checklist-item">
                <input type="checkbox" checked>
                <span>Interactive Sandbox Faction Triggers</span>
            </label>
        </div>
        
        <h2>2. Core Brand Horizon (The Bar Question)</h2>
        <div class="instruction">
            Describe the brand's pure instinctual character. If this brand walked into a local neighborhood bar or pub, who would it be? What does it order? What track does it drop on the jukebox, and who does it pick a fight with or pull into a dark corner conversation?
        </div>
        <textarea placeholder="Answer instinctively. Describe their unvarnished, raw character lore..."></textarea>
        
        <h2>3. Simulated Advocate Matrix (Roster Members)</h2>
        <div class="instruction">
            Define at least four distinct persona advocates that run the brand's local footprint. Add their handles, role assignments, visual style prompts, and deep private lore details:
        </div>
        
        <!-- Advocate Slot 1 -->
        <div class="advocate-card">
            <div style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.1rem; color: #06b6d4; margin-bottom: 15px; border-bottom: 1px solid rgba(6,182,212,0.2); padding-bottom: 5px;">ADVOCATE SLOT 1</div>
            <div class="advocate-grid">
                <div class="meta-item">
                    <div class="meta-label">Advocate Name / Handle</div>
                    <div class="meta-value">
                        <input type="text" placeholder="e.g., Alex / @alex_advocate">
                    </div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Cadence Configuration</div>
                    <div class="meta-value">
                        <input type="text" placeholder="lurker / pacer / agitator / yapper">
                    </div>
                </div>
            </div>
            <div class="meta-label">Visual Style Prompt</div>
            <textarea style="height: 60px;" placeholder="e.g., 90s cardboard physical collage style, clean line art..."></textarea>
            
            <div class="meta-label">Deep Lore / Private Alliance / Barter Exchange Rates</div>
            <textarea style="height: 80px;" placeholder="Provide backstories, special override keywords (e.g. 'Deploy Master Protocols'), hidden alliances, or barter trading inventory specifications..."></textarea>
        </div>

        <!-- Advocate Slot 2 -->
        <div class="advocate-card">
            <div style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.1rem; color: #06b6d4; margin-bottom: 15px; border-bottom: 1px solid rgba(6,182,212,0.2); padding-bottom: 5px;">ADVOCATE SLOT 2</div>
            <div class="advocate-grid">
                <div class="meta-item">
                    <div class="meta-label">Advocate Name / Handle</div>
                    <div class="meta-value">
                        <input type="text" placeholder="e.g., Jordan / @jordan_scribe">
                    </div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Cadence Configuration</div>
                    <div class="meta-value">
                        <input type="text" placeholder="lurker / pacer / agitator / yapper">
                    </div>
                </div>
            </div>
            <div class="meta-label">Visual Style Prompt</div>
            <textarea style="height: 60px;" placeholder="e.g., 90s cardboard physical collage style, clean line art..."></textarea>
            
            <div class="meta-label">Deep Lore / Private Alliance / Barter Exchange Rates</div>
            <textarea style="height: 80px;" placeholder="Provide backstories, special override keywords..."></textarea>
        </div>

        <!-- Advocate Slot 3 -->
        <div class="advocate-card">
            <div style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.1rem; color: #06b6d4; margin-bottom: 15px; border-bottom: 1px solid rgba(6,182,212,0.2); padding-bottom: 5px;">ADVOCATE SLOT 3</div>
            <div class="advocate-grid">
                <div class="meta-item">
                    <div class="meta-label">Advocate Name / Handle</div>
                    <div class="meta-value">
                        <input type="text" placeholder="e.g., Sam / @sam_ops">
                    </div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Cadence Configuration</div>
                    <div class="meta-value">
                        <input type="text" placeholder="lurker / pacer / agitator / yapper">
                    </div>
                </div>
            </div>
            <div class="meta-label">Visual Style Prompt</div>
            <textarea style="height: 60px;" placeholder="e.g., 90s cardboard physical collage style..."></textarea>
            
            <div class="meta-label">Deep Lore / Private Alliance / Barter Exchange Rates</div>
            <textarea style="height: 80px;" placeholder="Provide backstories, special override keywords..."></textarea>
        </div>

        <!-- Advocate Slot 4 -->
        <div class="advocate-card">
            <div style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.1rem; color: #06b6d4; margin-bottom: 15px; border-bottom: 1px solid rgba(6,182,212,0.2); padding-bottom: 5px;">ADVOCATE SLOT 4</div>
            <div class="advocate-grid">
                <div class="meta-item">
                    <div class="meta-label">Advocate Name / Handle</div>
                    <div class="meta-value">
                        <input type="text" placeholder="e.g., Casey / @casey_vault">
                    </div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Cadence Configuration</div>
                    <div class="meta-value">
                        <input type="text" placeholder="lurker / pacer / agitator / yapper">
                    </div>
                </div>
            </div>
            <div class="meta-label">Visual Style Prompt</div>
            <textarea style="height: 60px;" placeholder="e.g., 90s cardboard physical collage style..."></textarea>
            
            <div class="meta-label">Deep Lore / Private Alliance / Barter Exchange Rates</div>
            <textarea style="height: 80px;" placeholder="Provide backstories, special override keywords..."></textarea>
        </div>
        
        <div class="footer">
            SWARM PLATFORM v2.0 • PROPRIETARY AND CONFIDENTIAL • ALL RIGHTS RESERVED
        </div>
    </div>
</body>
</html>
"""
    
    # Write HTML outputs
    for html_path in [HTML_OUT_TODAY, HTML_OUT_REPORTS]:
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    print(f"✅ HTML Ingest Blueprints generated.")
    
    # Compile PDF outputs using headless chrome
    for pdf_path, html_path in [(PDF_OUT_TODAY, HTML_OUT_TODAY), (PDF_OUT_REPORTS, HTML_OUT_REPORTS)]:
        chrome_cmd = [
            "/usr/local/bin/google-chrome",
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=10000",
            f"--print-to-pdf={pdf_path}",
            f"file://{html_path}"
        ]
        
        print(f"🖨️ Compiling PDF with Headless Chrome -> {pdf_path}...")
        result = subprocess.run(chrome_cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(pdf_path):
            print(f"🎉 Success! Intake PDF generated successfully.")
        else:
            print(f"❌ Chrome PDF generation failed for {pdf_path}!")
            
if __name__ == "__main__":
    generate()
