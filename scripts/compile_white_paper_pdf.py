#!/usr/bin/env python3
"""
Sovereign Knot Architecture White Paper PDF Compiler
Converts markdown white paper content into a high-fidelity Sovereign Home Premium PDF report.
"""

import os
import sys
import subprocess
import tempfile
import markdown

MARKDOWN_PATH = "/home/james/stacklabs/dna/docs/SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.md"
PDF_DESTINATION = "/home/james/stacklabs/dna/docs/SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.pdf"
STACKLABS_PUBLIC_PDF = "/home/james/stacklabs/16_StackLabsLLC/public/docs/Sovereign_Knot_Hardware_Consensus_Whitepaper.pdf"
STACKLABS_DIST_PDF = "/home/james/stacklabs/16_StackLabsLLC/dist/docs/Sovereign_Knot_Hardware_Consensus_Whitepaper.pdf"
PORTAL_PUBLIC_PDF = "/home/james/stacklabs/01_Sovereign_Portal/public/docs/Sovereign_Knot_Hardware_Consensus_Whitepaper.pdf"
INBOX_DESTINATION = "/home/james/sovereign_inbox/SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.pdf"
INBOX_TODAY_PDF = "/home/james/sovereign_inbox/today/Sovereign_Knot_Hardware_Consensus_Whitepaper.pdf"

HTML_FRAME_START = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SOVEREIGN KNOT // EXECUTIVE ARCHITECTURE WHITE PAPER</title>
    <style>
        @page {
            size: A4;
            margin: 15mm;
        }
        body {
            background-color: #ffffff;
            color: #1e293b;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 10.5pt;
            line-height: 1.6;
            margin: 0;
            padding: 10px;
        }
        .header-banner {
            border-bottom: 2px solid #0f172a;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        h1 {
            color: #0f172a;
            font-size: 18pt;
            letter-spacing: 1px;
            margin: 0 0 10px 0;
            text-transform: uppercase;
            font-weight: 800;
        }
        .meta-bar {
            color: #475569;
            font-size: 8.5pt;
            font-weight: 700;
        }
        h2 {
            color: #0f172a;
            font-size: 13pt;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 5px;
            margin-top: 25px;
            text-transform: uppercase;
            font-weight: 700;
        }
        h3 {
            color: #1e293b;
            font-size: 11pt;
            margin-top: 18px;
            font-weight: 700;
        }
        p, li {
            color: #334155;
        }
        strong {
            color: #0f172a;
            font-weight: 700;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 18px 0;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
        }
        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            font-size: 9.5pt;
            color: #334155;
        }
        th {
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 700;
        }
        pre, code {
            background-color: #f1f5f9;
            border: 1px solid #cbd5e1;
            color: #0f172a;
            padding: 10px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
            font-size: 9pt;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        pre code {
            border: none;
            padding: 0;
            background: transparent;
        }
        blockquote {
            border-left: 4px solid #0284c7;
            background-color: #f8fafc;
            margin: 15px 0;
            padding: 10px 15px;
            color: #334155;
            border-radius: 0 4px 4px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 15px;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 8pt;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header-banner">
        <h1>SOVEREIGN KNOT // EXECUTIVE ARCHITECTURE WHITE PAPER</h1>
        <div class="meta-bar">
            DOCUMENT ID: SK-ARCH-2026-V1 &nbsp;|&nbsp; CLASSIFICATION: PUBLIC RELEASE &nbsp;|&nbsp; STATUS: OPERATIONAL SPECIFICATION
        </div>
    </div>
    <div class="content">
"""

HTML_FRAME_END = r"""
    </div>
    <div class="footer">
        CONFIDENTIAL & PROPRIETARY &mdash; STACKLABS / SOVEREIGN KNOT &mdash; ARCHITECTURE SPECIFICATION
    </div>
</body>
</html>
"""

def compile_pdf():
    print(f"[*] Reading Markdown source from: {MARKDOWN_PATH}")
    if not os.path.exists(MARKDOWN_PATH):
        print(f"[!] Error: Markdown file not found at {MARKDOWN_PATH}")
        return False

    with open(MARKDOWN_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Convert markdown to HTML with tables & fenced code blocks
    body_html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    full_html = HTML_FRAME_START + body_html + HTML_FRAME_END

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write(full_html)
        temp_html_path = f.name

    chrome_bin = "/usr/bin/google-chrome"
    if not os.path.exists(chrome_bin):
        chrome_bin = "google-chrome"

    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={PDF_DESTINATION}",
        temp_html_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if os.path.exists(PDF_DESTINATION):
            pdf_size = os.path.getsize(PDF_DESTINATION)
            print(f"[+] Primary PDF Successfully Generated at: {PDF_DESTINATION} ({pdf_size} bytes)")
            
            # Sync to all target public and inbox destinations
            destinations = [
                STACKLABS_PUBLIC_PDF,
                STACKLABS_DIST_PDF,
                PORTAL_PUBLIC_PDF,
                INBOX_DESTINATION,
                INBOX_TODAY_PDF
            ]

            for dest in destinations:
                try:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    subprocess.run(["cp", PDF_DESTINATION, dest], check=True)
                    print(f"  [✔] Synced PDF -> {dest}")
                except Exception as sync_err:
                    print(f"  [!] Sync warning for {dest}: {sync_err}")

            return True
        else:
            print(f"[!] PDF generation failed: Destination file missing.")
            return False
    except Exception as e:
        print(f"[!] Error during PDF compilation: {e}")
        return False
    finally:
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

if __name__ == "__main__":
    success = compile_pdf()
    sys.exit(0 if success else 1)
