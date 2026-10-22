#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import markdown

def generate_pdf():
    # Target files
    html_file = "/home/james/sovereign_inbox/today/aether_press_kit_temp.html"
    pdf_file = "/home/james/sovereign_inbox/today/Aether_Vet_Press_Kit.pdf"
    
    print("Initializing AetherVet Press Kit Compilation...")
    
    # Document content in Markdown
    md_content = """
# Aether Vet — B2B Veterinary Telemedicine Press Kit & Operator Guide

Welcome to the **Aether Vet** B2B Veterinary Telemedicine Portal. Aether Vet is a state-of-the-art, decoupled digital healthcare ecosystem designed for advanced feline and canine bio-telemetry, veterinary diagnostic reviews, and secure real-time telehealth telepresence.

This press kit and operator guide provides a detailed walkthrough of each interface tab, outlining their clinical purposes, technical implementations, and value propositions for partner clinics such as Dr. Rox at Arkle Vet.

---

## 🗺️ POOP RECOVERY VECTOR: FRESH UNCONTAMINATED SPECIMEN FINDER (MAY 26)

> [!IMPORTANT]
> **Weather Alert & Specimen Contamination Notice**: 
> Due to heavy rainfall yesterday (May 25), all historical defecation candidates from yesterday are contaminated. The Smyrna field centroid has exactly **one uncontaminated specimen candidate** dropped this morning (May 26). 

Based on high-velocity GPX dwell filtering from Metsy's GPS collar, here are the precise vector coordinates for retrieving the clean, uncontaminated fecal sample:

*   **Poop Event Candidate ID**: `Candidate #4`
*   **Defecation Window**: **May 26, 2026 at 07:50 AM to 07:58 AM EDT** (UTC `11:50:54` to `11:58:04`)
*   **Defecation Duration**: **430 seconds (7 minutes, 10 seconds)** — *Extremely high-confidence dwell signature.*
*   **Exact GPS Coordinates**:
    *   **Latitude**: `33.885078`
    *   **Longitude**: `-84.530526`
*   **Yard Substrate / Area**: **Mulch / pine straw clearing cluster** (located in the north-eastern quadrant of the Smyrna centroid range).

*Please reference these exact coordinates on your phone's GPS or mapping app to retrieve the uncontaminated specimen directly.*

---

## 📺 Interface Walkthrough & Tab-by-Tab Guide

### 1. The Dashboard Tab

The main clinical command center provides an aggregate view of physiological trends, behavioral charts, and critical automated alerts for the active patient.

![Aether Vet Dashboard View](dashboard_tab.png)

*   **Clinical Purpose**: Offers immediate, zero-click triage oversight. It aggregates data from multiple IoT sensors (such as smart litterboxes and GPS active collars) into digestible trends, exposing subclinical signs of disease before visual symptoms manifest.
*   **Key Features**:
    *   **Telemetry Trends Chart**: 12-month dual-axis visualization overlaying weight regression (in kg) against daily litterbox frequency averages, highlighting critical anomalies.
    *   **Activity Saturation Graph**: 30-day view tracking active time (mins) and daily steps, exposing sudden behavioral regressions (such as the mobility drops seen post-op or during arthritis onset).
    *   **High Priority Alert Box**: A glowing warning card that highlights clinical alerts (e.g., *Degenerative Joint Disease* in Metsy or *Post-Op Restrictions* in Sam) alongside diagnostic summaries and recommended actions.
*   **Clinic Value**: Minimizes triage overhead by serving diagnostic indicators on a single screen, helping vets plan exams proactively.

---

### 2. The Telemetry Tab

The GIS maps page, rendering high-velocity spatial telemetry and excursions across the patient’s home perimeter.

![Aether Vet Telemetry View](telemetry_tab.png)

*   **Clinical Purpose**: Monitors physical range-of-motion, outdoor safety, and bowel elimination events to guide diagnostic sample collection.
*   **Key Features**:
    *   **Leaflet GIS Map**: Styled in premium clinical slate with low-opacity trace trails showing Metsy’s exact backyard coordinates, search perimeter, and defecation cluster hotspots.
    *   **Temporal Scrubber**: Allows filtering of GPS coordinates by custom date windows.
    *   **Poop/Squat Candidate Feed**: Integrates coordinates, dwell times, and substrate classifications for direct biological sample recovery.
*   **Clinic Value**: Empowers pet owners to harvest clean samples for lab tests, reducing diagnostic wait times.

---

### 3. The Patients Tab

A comprehensive Pet Family & Patient EMR Registry showing registered family members side-by-side.

![Aether Vet Patients View](patients_tab.png)

*   **Clinical Purpose**: Manages multiple family pets on a single billing account, allowing the user to select and manage patients globally, updating all diagnostic charts, connected collar telemetry, alerts, and prescriptions dynamically.
*   **Key Features**:
    *   **Pet Family Cards**: Showcase Metsy (Cat, 8y, DSH, alert active) and Sam (Dog, 4y, Beagle/Mix, recovery check) side-by-side with individual avatars, species, breed, age, and chip IDs.
    *   **Active Patient Switcher**: Clicking "Select Patient" triggers a seamless transition, globally refreshing EMR cards, active telemetry charts, prescriptions, and connected device nodes.
    *   **Connected Devices Status Grid**: Visualizes collar battery percentage, signal strength, and live device health status.
*   **Clinic Value**: Streamlines EMR administration, providing a cohesive single-pane overview of the entire family registry without having to shuffle paper charts or log into distinct portals.

---

### 4. The Telepresence Tab

The secure clinic telemedicine video consultation portal.

![Aether Vet Telepresence View](telepresence_tab.png)

*   **Clinical Purpose**: Establishes high-fidelity virtual consultation links between vet practitioners and pet owners directly inside the active EMR chart window.
*   **Key Features**:
    *   **WebRTC HoloLink Video Grid**: Low-latency secure peer-to-peer audio/video connection with local camera previews.
    *   **Integrated EMR Sidebar**: Keeps the complete Patient Chart (Overview, active prescriptions, diagnostics PDFs, and vaccine history) visible next to the video stream, enabling real-time clinical review.
    *   **Incoming Call Ring Interface**: Features a beautiful full-screen overlay for incoming calls, allowing operators to accept or decline telehealth requests with one click.
*   **Clinic Value**: Eliminates the need to switch between Zoom and EMR software, increasing veterinarian consult efficiency and clinical charting accuracy during calls.

---

> [!TIP]
> **Partner Portal Sync**: All diagnostic summaries and EMR profiles updated on Aether Vet synchronize with the master core database (`/home/james/stacklabs/dna/sovereign_now.db`).
"""

    # Convert standard markdown to HTML
    body_html = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])

    # CSS design system matching a clinical teal & outfit theme
    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    :root {
        --color-bg: #fafaf9;
        --color-text: #1c2e2c;
        --color-text-light: #445654;
        --color-primary: #0f766e;
        --color-primary-light: #f0fdfa;
        --color-accent: #b45309;
        --color-accent-light: #fef3c7;
        --color-border: #e2e8f0;
    }
    
    * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    
    @page {
        size: letter;
        margin: 20mm 20mm 20mm 20mm;
        @bottom-right {
            content: counter(page);
            font-family: 'Outfit', sans-serif;
            font-size: 9pt;
            color: #889694;
        }
        @top-left {
            content: "AetherVet • B2B Telemedicine Portal Press Kit";
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
        height: 9.2in;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        padding: 40px;
        border: 2px solid #0f766e;
        background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%);
        color: #fafaf9;
    }
    
    .cover-header {
        font-size: 10pt;
        text-transform: uppercase;
        letter-spacing: 0.25em;
        color: #fbc02d;
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
        line-height: 1.15;
        color: #fafaf9;
        margin: 0 0 15px 0;
        letter-spacing: -0.5px;
    }
    
    .cover-subtitle {
        font-size: 13pt;
        font-weight: 400;
        color: #fbc02d;
        margin: 0 0 40px 0;
        letter-spacing: 0.05em;
        line-height: 1.4;
    }
    
    .cover-divider {
        width: 120px;
        height: 4px;
        background-color: #fbc02d;
        margin-bottom: 40px;
    }
    
    .cover-footer {
        margin-top: auto;
        border-top: 1px solid rgba(251, 192, 45, 0.3);
        padding-top: 25px;
        display: flex;
        justify-content: space-between;
        font-size: 9.5pt;
        color: #ccdbd8;
    }
    
    .cover-footer-item strong {
        color: #fbc02d;
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
        font-size: 20pt;
        line-height: 1.2;
        border-bottom: 3px solid var(--color-primary);
        padding-bottom: 8px;
        margin-top: 0;
        margin-bottom: 1em;
        text-transform: uppercase;
    }
    
    h2 {
        font-size: 14pt;
        border-left: 4px solid var(--color-primary);
        padding-left: 12px;
        color: var(--color-primary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    h3 {
        font-size: 12pt;
        color: var(--color-accent);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        page-break-before: always;
    }
    
    p {
        margin-top: 0;
        margin-bottom: 1.2em;
        color: var(--color-text-light);
        text-align: justify;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1.5em 0;
        page-break-inside: avoid;
        font-size: 9.5pt;
    }
    
    th, td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid var(--color-border);
    }
    
    th {
        background-color: var(--color-primary-light);
        color: var(--color-primary);
        font-weight: 700;
        text-transform: uppercase;
        font-size: 8.5pt;
        letter-spacing: 0.5px;
    }
    
    tr:nth-child(even) td {
        background-color: #fcfcfb;
    }
    
    /* Alerts */
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
        color: #78350f;
        font-weight: 500;
        font-size: 10pt;
    }
    
    img {
        max-width: 100%;
        max-height: 4.2in;
        object-fit: contain;
        display: block;
        margin: 20px auto;
        border: 1px solid var(--color-border);
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        page-break-inside: avoid;
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
        margin: 2em 0;
    }
    """
    
    # HTML document wrap
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>AetherVet B2B Telemedicine Press Kit</title>
    <style>
        {css_content}
    </style>
</head>
<body>

    <div class="cover-page">
        <div class="cover-header">AetherVet Clinical Partner Materials</div>
        <div class="cover-body">
            <h1 class="cover-title">AETHERVET:<br>CLINICAL TELEPRESENCE & BIOMETRIC TRIAGE</h1>
            <div class="cover-subtitle">B2B Veterinary Telemedicine Portal Press Kit & Operator Guide</div>
            <div class="cover-divider"></div>
        </div>
        <div class="cover-footer">
            <div class="cover-footer-item">
                <strong>Prepared For</strong>
                Dr. Rox, DVM, Lead Clinician<br>Arkle Veterinary Clinic
            </div>
            <div class="cover-footer-item">
                <strong>Prepared By</strong>
                James Carroll, Founder<br>Sovereign OS
            </div>
            <div class="cover-footer-item">
                <strong>Date</strong>
                May 26, 2026
            </div>
        </div>
    </div>

    <div class="content-container">
        {body_html}
    </div>

</body>
</html>
"""

    # Post-process GitHub alert style blocks
    html_document = html_document.replace('<blockquote>\n<p>&gt; [!IMPORTANT]', '<blockquote style="background-color: #fef2f2; border-left-color: #ef4444;"><p style="color: #991b1b;"><strong>⚠️ IMPORTANT NOTICE:</strong>')
    html_document = html_document.replace('<blockquote>\n<p>&gt; [!TIP]', '<blockquote style="background-color: #f0fdf4; border-left-color: #22c55e;"><p style="color: #166534;"><strong>💡 PARTNER PORTAL TIP:</strong>')

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
    
    print("Compiling PDF via Headless Google Chrome...")
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
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
