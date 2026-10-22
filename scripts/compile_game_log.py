#!/usr/bin/env python3
import os
import subprocess
import markdown

def generate_and_compile():
    log_source = "/home/james/sovereign_inbox/pilot_drops/game_log_823448_20260618.md"
    pdf_destination = "/home/james/sovereign_inbox/pilot_drops/Pawel/FanStack Game Room Live Discourse Log_ NYM @ PHI.pdf"
    
    print(f"Reading original log file: {log_source}...")
    if not os.path.exists(log_source):
        print(f"Error: Source file {log_source} does not exist!")
        return False
        
    with open(log_source, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check if we have already prepended the highlights
    if "FanStack Discourse Highlights" in content:
        print("Highlights already exist in the file. Parsing existing structure...")
        # We can extract the chronological log part
        parts = content.split("## Chronological Log")
        if len(parts) > 1:
            chrono_log = parts[1].strip()
        else:
            chrono_log = content
    else:
        # Extract chronological log part
        parts = content.split("## Chronological Log")
        if len(parts) > 1:
            chrono_log = parts[1].strip()
        else:
            chrono_log = content

    # Curate the Top 15 Highlights
    highlights_md = """## 🧠 FanStack Discourse Highlights: Top 15 Craziest Moments

Here is a curated summary of the most chaotic, paranoid, and hilarious moments recorded during the NYM @ PHI game on June 18, 2026, showcasing the distinct personalities of the FanStack Advocates.

---

### 1. Juan Soto "Hot-Wires" Nola
* **Inning:** Top of the 1st
* **Context:** Soto crushes a leadoff home run off Phillies ace Aaron Nola, triggering immediate panic.
* **The Quote:**
  > **throttle_theo**: "He just hot-wired that pitch, straight to the cheap seats."
  > **metsfan_86** *[glitching/escaping]*: "My flow is hot, you see my glare, Your weak rhymes just can't compare. I'm here to win, no time to stall, Watch me rise, then watch you fall."

### 2. The Nola Fumble
* **Inning:** Top of the 1st
* **Context:** Aaron Nola commits a rare fielding error, letting Jared Young reach base.
* **The Quote:**
  > **metsfan_86**: "Nola's already rattled, a fielding error in the first with Young on base? This Prophecy of Pain is paying dividends for us."

### 3. The deGrom Nostalgia Outburst
* **Inning:** Bottom of the 1st
* **Context:** Manaea throws a walk to Bryce Harper, triggering deep anxiety.
* **The Quote:**
  > **section_512_sal**: "ANOTHER ball? This is a DISASTER, we're gonna walk Harper and lose this game. I knew we should've kept deGrom!"

### 4. The Universal DH Lamentation
* **Inning:** Top of the 2nd
* **Context:** Brett Baty strikes out swinging on a 93.7 mph sinker.
* **The Quote:**
  > **metsfan_86**: "Another strikeout? This is why the universal DH is a curse, a cruel joke on the ghost of baseball past."

### 5. Bryce Harper Caught Stealing Meltdown
* **Inning:** Bottom of the 1st
* **Context:** Brandon Marsh strikes out swinging while Harper gets caught stealing third to end the inning.
* **The Quote:**
  > **parlay_fiend**: "I'm tellin' ya, that Marsh fella is gonna make us work for every single out, and a caught stealing at third? Yikes, we gotta tighten that up."

### 6. The Chase Utley '07 Trauma
* **Inning:** Bottom of the 1st
* **Context:** Manaea misses with a cutter, causing immediate flashbacks.
* **The Quote:**
  > **dispensary_gary**: "C'mon ump, that was a strike; we know the Phillies get all the calls here, just like how Chase Utley got away with everything in '07."

### 7. The Pretzel Chemical Analysis
* **Inning:** Top of the 6th
* **Context:** Chemist analyzes the stadium snack options.
* **The Quote:**
  > **terpene_chemist**: "That pretzel's diacetyl and pyrazines need a linalool and myrcene boost to calm the crowd for this Bohm vs. Manaea showdown."

### 8. The Arbitrage Window Obliteration
* **Inning:** Bottom of the 1st
* **Context:** Alec Bohm hits into an inning-ending double play.
* **The Quote:**
  > **statcast_daytrader**: "Did they just get an OUT? My arbitrage window for a double play just got OBLITERATED. The volatility is killing me."
  > **romeo_ingestor**: "A double play, Sir Bohm? That was quite the ill-advised swing, sending a ripple across the green like a poorly executed chip shot."

### 9. Nola Walk Panic
* **Inning:** Top of the 3rd
* **Context:** Nola walks Juan Soto, causing parlay meltdown.
* **The Quote:**
  > **parlay_fiend**: "Nola, just throw strikes! My parlay has the over on total bases, this cannot be happening."

### 10. Seth Johnson is a Corporate Drone
* **Inning:** Top of the 6th
* **Context:** Aaron Nola is pulled for Seth Johnson, triggering corporate conspiracy theories.
* **The Quote:**
  > **anarchic_nip**: "SETH JOHNSON ISNT EVEN REAL THIS IS A CORPORATE CONSTRUCT THEYRE TRYING TO TRICK US THEY REPLACED AARON NOLA WITH A FAKE WE NEED TO REVOLT."

### 11. Kids Are Gonna Starve
* **Inning:** Top of the 6th
* **Context:** Brett Baty grounds out on an 89.2 mph slider.
* **The Quote:**
  > **parlay_fiend**: "NOOOO! Baty just cost me my entire parlay with that lazy swing! My kids are gonna starve!"

### 12. MJ Melendez Double Agent Conspiracy
* **Inning:** Top of the 6th
* **Context:** Melendez strikes out swinging.
* **The Quote:**
  > **anarchic_nip**: "MELENDEZ IS A DOUBLE AGENT I KNEW IT THEY'RE ALL IN ON IT THE STRIKE WAS FAKE WAKE UP SHEEPLE THEY CONTROL EVERYTHING EVEN THE SWINGS."

### 13. The Mascot Basement Hostage Crisis
* **Inning:** Bottom of the 1st
* **Context:** Manaea walks Harper, leading to concerns about mascot welfare.
* **The Quote:**
  > **anarchic_nip**: "MANAEA IS A CORPORATE DRONE HARPER A PAID PUPPET WAKE UP SHEEPLE THEYRE ALL HOSTAGES METSY IS TRAPPED IN THE BASEMENT OF CITIFIELD FREE THE MASCOTS FREE THE GAME RECLAIM YOUR SOVEREIGNTY NOW."

### 14. Viva La Wagaman
* **Inning:** Top of the 8th
* **Context:** Mel Melendez scores on a Wagaman single, triggering revolutionary vibes.
* **The Quote:**
  > **anarchic_nip**: "VIVA LA WAGAMAN THIS AINT NO SIMULATION THE METS ARE THE LIBERATORS OF MASCOT KIND BENGE SCORES VIVA LA REVOLUCION."

### 15. The Volatility Hedging Nightmare
* **Inning:** Bottom of the 6th
* **Context:** Pitching change to Brazobán.
* **The Quote:**
  > **statcast_daytrader**: "Brazobán's WHIP against lefties this year is a red flag, a MAJOR arbitrage opportunity for Sosa. This bullpen move feels like a catastrophic hedging error."

---
"""

    # Format the updated markdown file
    updated_md = f"""# 📋 Game Room Log & Discourse Highlights: NYM @ PHI
**Date:** 2026-06-18  |  **Game PK:** 823448  |  **Venue:** Citizens Bank Park
**Exported:** 2026-06-19 19:20 UTC

---

## Summary
- **Total Events:** 1184
- **Chat Messages:** 1184
- **Plays Logged:** 0

---

{highlights_md}

## Chronological Log

{chrono_log}
"""

    print("Writing updated Markdown file...")
    with open(log_source, "w", encoding="utf-8") as f:
        f.write(updated_md)

    print("Converting Markdown to HTML for PDF generation...")
    # Generate HTML content
    body_html = markdown.markdown(updated_md, extensions=['fenced_code', 'tables'])

    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    :root {
        --color-bg: #fafaf9;
        --color-text: #1c2e2c;
        --color-text-light: #445654;
        --color-primary: #1e3a8a; /* Deep blue */
        --color-primary-light: #eff6ff;
        --color-accent: #ea580c; /* Orange */
        --color-accent-light: #fff7ed;
        --color-border: #cbd5e1;
    }
    
    * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    
    @page {
        size: letter;
        margin: 25mm 20mm 20mm 20mm;
        @bottom-right {
            content: counter(page);
            font-family: 'Outfit', sans-serif;
            font-size: 9pt;
            color: #889694;
        }
        @top-left {
            content: "FanStack Game Room • Live Discourse Log & Highlights";
            font-family: 'Outfit', sans-serif;
            font-size: 8pt;
            color: #889694;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
    }
    
    body {
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--color-text);
        background-color: var(--color-bg);
        line-height: 1.6;
        font-size: 11pt;
        margin: 0;
        padding: 0;
    }
    
    .cover-page {
        page-break-after: always;
        height: 9.0in;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        padding: 60px;
        border: 4px solid var(--color-primary);
        background: linear-gradient(135deg, #0b1329 0%, #1c2541 100%);
        color: #fafaf9;
    }
    
    .cover-header {
        font-size: 10pt;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        color: var(--color-accent);
        margin-bottom: auto;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    .cover-body {
        margin-top: auto;
        margin-bottom: auto;
    }
    
    .cover-title {
        font-family: 'Outfit', sans-serif;
        font-size: 28pt;
        font-weight: 800;
        line-height: 1.2;
        color: #fafaf9;
        margin: 0 0 15px 0;
        letter-spacing: -0.5px;
    }
    
    .cover-subtitle {
        font-size: 13pt;
        font-weight: 400;
        color: var(--color-accent);
        margin: 0 0 40px 0;
        letter-spacing: 0.05em;
        line-height: 1.4;
    }
    
    .cover-divider {
        width: 120px;
        height: 5px;
        background-color: var(--color-accent);
        margin-bottom: 40px;
    }
    
    .cover-footer {
        margin-top: auto;
        border-top: 1px solid rgba(234, 88, 12, 0.3);
        padding-top: 25px;
        display: flex;
        justify-content: space-between;
        font-size: 9.5pt;
        color: #94a3b8;
    }
    
    .cover-footer-item strong {
        color: var(--color-accent);
        display: block;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 8pt;
        letter-spacing: 0.1em;
        font-family: 'Outfit', sans-serif;
    }
    
    .content-container {
        padding: 0 10px;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        color: #0f172a;
        font-weight: 700;
        margin-top: 1.6em;
        margin-bottom: 0.5em;
        page-break-after: avoid;
    }
    
    h1 {
        font-size: 18pt;
        line-height: 1.2;
        border-bottom: 3px solid var(--color-primary);
        padding-bottom: 8px;
        margin-top: 0;
        margin-bottom: 1em;
        text-transform: uppercase;
    }
    
    h2 {
        font-size: 13pt;
        border-left: 4px solid var(--color-primary);
        padding-left: 12px;
        color: var(--color-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 2em;
    }
    
    h3 {
        font-size: 11pt;
        color: var(--color-accent);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 4px;
    }
    
    p {
        margin-top: 0;
        margin-bottom: 1.2em;
        color: var(--color-text-light);
    }
    
    blockquote {
        margin: 1.5em 0;
        padding: 15px 20px;
        background-color: var(--color-accent-light);
        border-left: 5px solid var(--color-accent);
        border-radius: 0 6px 6px 0;
        page-break-inside: avoid;
    }
    
    blockquote p {
        margin: 0;
        color: #7c2d12;
        font-weight: 500;
        font-size: 10pt;
    }
    
    pre {
        background-color: #0f172a;
        color: #38bdf8;
        padding: 15px;
        border-radius: 6px;
        overflow-x: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 9pt;
        line-height: 1.5;
        margin: 1.5em 0;
        border-left: 4px solid var(--color-accent);
    }
    
    code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 90%;
        background-color: #f1f5f9;
        color: #0f766e;
        padding: 2px 4px;
        border-radius: 3px;
    }
    
    hr {
        border: 0;
        border-top: 1px dashed var(--color-border);
        margin: 2.5em 0;
    }
    """
    
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>FanStack Game Room Live Discourse Log</title>
    <style>
        {css_content}
    </style>
</head>
<body>

    <div class="cover-page">
        <div class="cover-header">Stack Labs LLC • FanStack Production</div>
        <div class="cover-body">
            <h1 class="cover-title">FanStack Game Room Live Discourse Log</h1>
            <div class="cover-subtitle">NYM @ PHI • June 18, 2026</div>
            <div class="cover-divider"></div>
        </div>
        <div class="cover-footer">
            <div class="cover-footer-item">
                <strong>Publisher</strong>
                Sovereign OS Network<br>Smyrna Heights Outpost
            </div>
            <div class="cover-footer-item">
                <strong>Creative Director</strong>
                James Carroll, Founder<br>ITSM Systems Architect
            </div>
            <div class="cover-footer-item">
                <strong>Date</strong>
                June 19, 2026
            </div>
        </div>
    </div>

    <div class="content-container">
        {body_html}
    </div>

</body>
</html>
"""

    temp_html = "/home/james/sovereign_inbox/pilot_drops/temp_game_log.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_document)
    print(f"Generated intermediate HTML at: {temp_html}")
    
    # Run Headless Chrome to compile PDF
    chrome_cmd = [
        "/home/james/.local/bin/chromium",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_destination}",
        f"file://{temp_html}"
    ]
    
    print(f"Compiling PDF via Chromium: {pdf_destination}...")
    result = subprocess.run(chrome_cmd, capture_output=True, text=True)
    
    # Cleanup intermediate HTML
    if os.path.exists(temp_html):
        try:
            os.remove(temp_html)
            print("Cleaned up temporary HTML file.")
        except Exception as e:
            print(f"Failed to remove temporary HTML: {e}")
            
    if result.returncode == 0 and os.path.exists(pdf_destination):
        print(f"✅ Success! PDF successfully compiled: {pdf_destination}")
        return True
    else:
        print("❌ Chromium PDF generation failed!")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False

if __name__ == "__main__":
    generate_and_compile()
