#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import markdown

def generate_pdf():
    # Target files
    html_file = "/home/james/stacklabs/arkle_prospectus_temp.html"
    pdf_file = "/home/james/sovereign_inbox/today/Arkle_Vet_Sovereign_Prospectus.pdf"
    
    print("Initializing AetherVet Prospectus Compilation for Dr. Rox...")
    
    # Document content in Markdown
    md_content = """
## 1. Executive Summary: The Remote Diagnostics Gap

Veterinary medicine has entered an era of highly advanced in-clinic diagnostics, yet **clinical triage still fails when the patient is at home.** 

Remote practitioners lack objective, longitudinal, and high-frequency physiological data. Standard pet telemedicine relies almost entirely on retrospective, qualitative accounts from pet owners—which are frequently delayed, subjective, and clinically incomplete. 

**AetherVet** bridges this diagnostic gap. By leveraging secure local edge gateways, Tailscale telemetry channels, and low-latency pet IoT biometric integrations (cellular velocity vectors, sleep actigraphy, and litterbox scales), AetherVet continuously monitors and profiles patient behaviors in their natural habitats. 

This prospectus outlines the **AetherVet Biometric Triage Platform** and details how **Arkle Veterinary Clinic** can leverage this industrial-grade clinical telemetry to:
1. **Reduce Clinical Anomaly Time-to-Treatment**: Detect acute and chronic anomalies (gastrointestinal distress, mobility decline, renal frequency changes) days before visual symptoms present.
2. **Automate Sample Interception**: Auto-detect fecal or urinary deposits in real-time, providing owners with exact coordinates for sterile collection before environmental degradation occurs.
3. **Establish a High-Margin Telehealth Revenue Channel**: Integrate objective, live telemetry feeds directly into your clinic's remote consulting workflows.

---

## 2. The AetherVet Biometric Telemetry Pipeline

Rather than overloading pet owners with raw numbers, AetherVet operates a sophisticated cloud-decoupled pipeline that distills complex behavioral data into actionable clinical markers:

```mermaid
graph TD
    A[Pet IoT Device: GPS/Actigraphy] -->|Raw Lat/Lon & Velocity| B(Tailscale Telemetry Channel)
    B -->|High-Frequency Ingestion| C(Local Edge Gateway Cluster)
    C -->|Dwell & Squat Logic| D(Triage & Anomaly Scoring)
    D -->|Continuous Anomaly Alerts| E(Arkle Vet Clinical Portal)
    D -->|Coordinate Drop Alert| F(Pet Owner Mobile App)
```

### Technical System Elements:
* **Decoupled Edge Computing**: Clinical inference runs directly on local edge hardware. This keeps data secure, guarantees sub-second reaction times, and eliminates public cloud subscription and hosting overhead (translating to near-zero marginal scale costs).
* **Clinical Anomaly Detection (CAD)**: Machine-learning models profile patient baselines for sleep duration, average velocity, pacing patterns, and voiding schedules. Any variance exceeding $\pm 2.2\sigma$ automatically triggers an alert on the Arkle Vet dashboard.
* **Telemetry Telepresence**: Integrates secure, peer-to-peer WebRTC video consultations alongside synchronous, live-scrolled diagnostic timelines. Vets can observe patient behaviors while auditing objective timeline charts in real-time.

---

## 3. Live Case Study: Metsy Smyrna Telemetry (May 24–26, 2026)

To demonstrate the high fidelity and diagnostic validity of the AetherVet platform, we initiated a continuous 48-hour biometric surveillance run on a canine subject (**Metsy**, a 14lb unit) residing at `2816 Parkwood Rd SE, Smyrna, GA`.

### Data Volume & Sample Optimization
Over the course of the study, the AetherVet edge server ingested **29,319 raw GPS trackpoints** at high frequency. To optimize mobile loading speeds and prevent battery drain on the telemetry channel, the pipeline dynamically thinned the stream to **983 highly salient timeline points** (spanning May 24 to May 26, 2026).

| Telemetry Metric | Raw Value | Target-Thinned Value | Optimization Ratio |
| :--- | :--- | :--- | :--- |
| **Total Trackpoints Ingested** | 29,319 points | 983 points | 29.8x reduction |
| **Distance Extracted** | 7.93 miles | 7.93 miles | 100% path preservation |
| **Active Excursion Segments** | 61 outside perimeter | 16 primary dwells | 3.8x noise pruning |

### Autonomous Stool Sample Interception (May 26, 7:50 AM EDT)
In-clinic parasitology, endocrine tracking, and microbiome profiling require highly fresh, uncontaminated stool samples. Under normal conditions, owners struggle to locate deposits on larger properties, leading to dried, degraded, or dirt-contaminated samples.

On the morning of **May 26, 2026**, AetherVet demonstrated autonomous drop-zone targeting:
1. **Perimeter Excursion**: The subject was let out at **7:30 AM EDT**.
2. **Dwell Vector Lock**: The AetherVet edge gateway isolated a sustained outside dwell event beginning at **7:50:54 AM** and ending at **7:58:04 AM EDT** (Duration: **430 seconds**).
3. **Soil Match & Anomaly Score**: The system matched the coordinates against historical soil layers, registering a high Biological Squat Score of **`121.7`** (Candidate #4).
4. **Autonomous Sample Target**: The platform identified the exact coordinates (**`33.885078, -84.530525`**) located in a mulch/pine straw clearing, pushing an instant drop zone map lock to the owner's phone for immediate collection.

```
Subject: Metsy (Node .171)  |  Target: Primary Soil Sample Lock  |  Time: May 26, 7:50 AM
Coordinates: 33.885078, -84.530525 (Mulch/pine straw clearing, 18.3m from Historic Throne)
Telemetry Status: Sterile Collection Opportunity Window Open (Freshness: ~2 Hours)
```

---

## 4. Arkle Vet Clinical Portal Integration

The clinical portal is designed to fit seamlessly into the busy daily schedules of Dr. Rox and the Arkle Vet staff:

* **Geriatric Care & Osteoarthritis Monitoring**: Quantify the efficacy of joint supplements or pain-management protocols by monitoring continuous velocity and pacing baselines. If a dog with chronic arthritis shows a 25% increase in daily average speed, you have empirical proof of treatment success.
* **Post-Operative Recovery Watch**: Secure WebRTC feeds let you monitor surgical wounds and post-op activity levels. If the patient's velocity spikes (indicating jumping or play that could rupture sutures), or drops below baseline (indicating severe pain or infection), an immediate alert is flagged.
* **Endocrine & Renal Triage**: Track the frequency of litterbox visits or outdoor excursions. Early-stage feline diabetes or canine urinary tract infections are flagged weeks before the owner notices physical symptoms, allowing for early, non-invasive therapeutic interventions.

---

## 5. B2B Commercial & Pilot Partnership

AetherVet commercializes through a simple, high-margin dual-licensing structure that drives recurring revenue to both your clinic and the platform:

| License Tier | Cost | Target Audience | Features |
| :--- | :--- | :--- | :--- |
| **B2B Clinic Dashboard** | $499/month | Veterinary Clinics | Clinic portal access, multi-staff dashboards, 100 concurrent patient slots, secure WebRTC telehealth gateway. |
| **D2C Pet Wellness Tier** | $19/month | Pet Owners | Owner mobile app, live maps, push notifications for sample interception, raw data export. |

> [!IMPORTANT]
> **Exclusive Arkle Vet Beta Partnership Offer**
> To secure Product-Market Fit (PMF) and build clinical proof-of-concept publications, we are offering Dr. Rox and the Arkle Vet team a premium slot in our **Phase 1 Beta Cohort**:
> 1. **Clinical Licensing Waived**: $0 clinical software license fee for the first 6 months.
> 2. **Free Edge Gateways**: We will supply and install 3 on-prem edge gateways at your clinic at zero hardware cost.
> 3. **Priority Registry Integration**: Direct, secure integration of the AetherVet telemetry engine with your existing clinical database.

---

**Confidential Partnership Proposal Approved for Clinical Strategic Use:**  
*James Carroll, Founder, Sovereign OS*  
*Co-Signed: AetherVet Biomedical Engineering Team*  
*Date: May 26, 2026*
"""

    # Convert standard markdown to HTML
    body_html = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])

    # Premium CSS Design System matching Clinical/Medical Teal & Outfits
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
            content: "AetherVet • Clinical Telepresence & Biometric Triage";
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
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        padding: 40px;
        border: 2px solid #0f766e;
        background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%);
        color: #fafaf9;
        position: relative;
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
        font-size: 32pt;
        font-weight: 800;
        line-height: 1.15;
        color: #fafaf9;
        margin: 0 0 15px 0;
        letter-spacing: -0.5px;
    }
    
    .cover-subtitle {
        font-size: 14pt;
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
        font-size: 22pt;
        line-height: 1.2;
        border-bottom: 3px solid var(--color-primary);
        padding-bottom: 8px;
        margin-top: 0;
        margin-bottom: 1em;
        text-transform: uppercase;
    }
    
    h2 {
        font-size: 15pt;
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
    
    /* Executive Alerts */
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
    
    pre code {
        background-color: transparent;
        color: inherit;
        padding: 0;
        border-radius: 0;
    }
    
    /* Mermaid diagram representation block */
    .mermaid {
        margin: 1.5em 0;
        padding: 15px;
        background-color: #f8fafc;
        border: 1px solid var(--color-border);
        border-radius: 6px;
        font-family: 'Outfit', sans-serif;
        text-align: center;
        page-break-inside: avoid;
    }
    
    hr {
        border: 0;
        border-top: 1px dashed var(--color-border);
        margin: 2em 0;
    }
    """
    
    # HTML Document Wrapper
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>AetherVet B2B Partnership Prospectus</title>
    <style>
        {css_content}
    </style>
    <!-- Include Mermaid from CDN -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'forest',
            flowchart: {{
                useWidth: true,
                htmlLabels: true
            }},
            securityLevel: 'loose'
        }});
        
        window.addEventListener('load', () => {{
            setTimeout(() => {{
                document.body.classList.add('ready');
            }}, 2000);
        }});
    </script>
</head>
<body>

    <div class="cover-page">
        <div class="cover-header">AetherVet Clinical Partnerships</div>
        <div class="cover-body">
            <h1 class="cover-title">AETHERVET:<br>CLINICAL TELEPRESENCE & BIOMETRIC TRIAGE</h1>
            <div class="cover-subtitle">Continuous Pet Biometric Surveillance, Autonomous Anomaly Profiling, and Real-Time Sample Interception</div>
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

    # Post-process body HTML to replace math formats with nicely styled containers
    html_document = re.sub(
        r'\$\$(.*?)\$\$',
        r'<div style="text-align:center; font-family:\'Outfit\', sans-serif; font-style:italic; margin:15px 0; background:#f0fdfa; padding:10px; border-radius:4px; border:1px solid #0f766e; color:#0f766e;">\1</div>',
        html_document,
        flags=re.DOTALL
    )
    
    # Process inline math e.g. $E_q$ or $L$
    html_document = re.sub(
        r'\$([a-zA-Z0-9_\{\}\s\+\-\*\\\\\=\.]+)\$',
        r'<em>\1</em>',
        html_document
    )

    # Ensure target output folders exist
    os.makedirs(os.path.dirname(html_file), exist_ok=True)
    os.makedirs(os.path.dirname(pdf_file), exist_ok=True)
    
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
    
    # Cleanup temp html file to maintain clean workspace
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
