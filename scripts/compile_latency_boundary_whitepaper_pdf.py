#!/usr/bin/env python3
"""
StackLabs Executive Whitepaper PDF Compiler
Compiles 'When the Latency Boundary Collapses' into an executive publication-grade PDF.
"""

import os
import sys
import subprocess
import tempfile
import markdown

SRC_MARKDOWN = "/home/james/stacklabs/docs/WHITEPAPER_WHEN_THE_LATENCY_BOUNDARY_COLLAPSES_THE_DEATH_OF_VECTOR_RAG.md"
PDF_PRIMARY = "/home/james/stacklabs/docs/WHITEPAPER_WHEN_THE_LATENCY_BOUNDARY_COLLAPSES_THE_DEATH_OF_VECTOR_RAG.pdf"
PDF_INBOX_TODAY = "/home/james/stacklabs/stacklabs_inbox/today/WHITEPAPER_WHEN_THE_LATENCY_BOUNDARY_COLLAPSES_THE_DEATH_OF_VECTOR_RAG.pdf"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>STACKLABS // WHEN THE LATENCY BOUNDARY COLLAPSES</title>
    <style>
        @page {
            size: letter;
            margin: 18mm 16mm 18mm 16mm;
            @bottom-right {
                content: counter(page);
                font-size: 8pt;
                color: #64748b;
            }
        }
        body {
            background-color: #ffffff;
            color: #0f172a;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }
        .header-banner {
            border-bottom: 2.5px solid #0f172a;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }
        .header-banner .sup-title {
            font-size: 8pt;
            font-weight: 800;
            letter-spacing: 1.5px;
            color: #2563eb;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        h1 {
            color: #0f172a;
            font-size: 18pt;
            letter-spacing: -0.5px;
            margin: 0 0 6px 0;
            line-height: 1.25;
            font-weight: 800;
        }
        .subtitle {
            color: #475569;
            font-size: 11pt;
            font-style: italic;
            margin: 0 0 14px 0;
            line-height: 1.4;
        }
        .meta-bar {
            color: #334155;
            font-size: 8pt;
            font-weight: 600;
            background: #f1f5f9;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
            margin-top: 10px;
            line-height: 1.5;
        }
        h2 {
            color: #0f172a;
            font-size: 12.5pt;
            border-bottom: 1.5px solid #cbd5e1;
            padding-bottom: 4px;
            margin-top: 24px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 800;
            page-break-after: avoid;
        }
        h3 {
            color: #1e293b;
            font-size: 10.5pt;
            margin-top: 16px;
            margin-bottom: 6px;
            font-weight: 700;
            page-break-after: avoid;
        }
        p, li {
            color: #1e293b;
            text-align: justify;
        }
        ul, ol {
            margin-top: 6px;
            margin-bottom: 10px;
            padding-left: 22px;
        }
        li {
            margin-bottom: 5px;
        }
        strong {
            color: #0f172a;
            font-weight: 700;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            background: #ffffff;
            border: 1px solid #cbd5e1;
            font-size: 9pt;
            page-break-inside: avoid;
        }
        th, td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 700;
            font-size: 8.5pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        tr:nth-child(even) {
            background-color: #f8fafc;
        }
        blockquote {
            border-left: 3.5px solid #2563eb;
            background-color: #f8fafc;
            margin: 14px 0;
            padding: 10px 14px;
            color: #1e293b;
            border-radius: 0 4px 4px 0;
            font-size: 9.5pt;
        }
        blockquote p {
            margin: 0;
        }
        pre, code {
            background-color: #f1f5f9;
            color: #0f172a;
            font-family: "JetBrains Mono", "Courier New", Courier, monospace;
            font-size: 8.5pt;
        }
        code {
            padding: 1px 4px;
            border-radius: 3px;
        }
        .footer {
            margin-top: 35px;
            padding-top: 12px;
            border-top: 1px solid #cbd5e1;
            color: #64748b;
            font-size: 7.5pt;
            text-align: center;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        hr {
            border: 0;
            height: 1px;
            background: #e2e8f0;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header-banner">
        <div class="sup-title">StackLabs Systems Architecture Group &bull; Executive Monograph</div>
        <h1>When the Latency Boundary Collapses</h1>
        <div class="subtitle">The Structural Limits of Vector RAG, the Resurgence of Swanson Literature-Based Discovery, and the Emergence of Zero-Copy Knowledge Topologies</div>
        <div class="meta-bar">
            <strong>AUTHOR:</strong> James Carroll, Lead Systems Architect, StackLabs LLC &nbsp;&bull;&nbsp;
            <strong>DATE:</strong> October 2026 &nbsp;&bull;&nbsp;
            <strong>CLASSIFICATION:</strong> Executive Technical Whitepaper (Public & Institutional Counterparty Release)
        </div>
    </div>
    <div class="content">
        __BODY_CONTENT__
    </div>
    <div class="footer">
        StackLabs LLC &bull; Enterprise Systems Architecture &bull; Smyrna, Georgia &bull; stacklabsllc.com
    </div>
</body>
</html>
"""

def compile_pdf():
    print(f"[*] Reading source markdown from: {SRC_MARKDOWN}")
    if not os.path.exists(SRC_MARKDOWN):
        print(f"[!] File not found: {SRC_MARKDOWN}")
        return False

    with open(SRC_MARKDOWN, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Strip the redundant top markdown title and metadata since they are cleanly embedded in the HTML banner
    lines = md_text.splitlines()
    body_lines = []
    skip = True
    for line in lines:
        if skip:
            if line.strip() == "---":
                skip = False
            continue
        body_lines.append(line)
    
    clean_md = "\n".join(body_lines)

    # Convert to HTML
    body_html = markdown.markdown(clean_md, extensions=['tables', 'fenced_code', 'nl2br'])
    full_html = HTML_TEMPLATE.replace("__BODY_CONTENT__", body_html)

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(full_html)
        tmp_path = tmp.name

    chrome_bin = "/home/james/.local/bin/google-chrome"
    if not os.path.exists(chrome_bin):
        chrome_bin = "google-chrome"

    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={PDF_PRIMARY}",
        tmp_path
    ]

    print(f"[*] Compiling publication-grade PDF via Headless Chrome...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Compilation error: {res.stderr}")
        return False

    if os.path.exists(PDF_PRIMARY):
        size = os.path.getsize(PDF_PRIMARY)
        print(f"[✔] Master Whitepaper PDF generated: {PDF_PRIMARY} ({size:,} bytes)")
        
        # Mirror to today's inbox
        os.makedirs(os.path.dirname(PDF_INBOX_TODAY), exist_ok=True)
        subprocess.run(["cp", PDF_PRIMARY, PDF_INBOX_TODAY], check=True)
        print(f"[✔] Inbox Mirror generated: {PDF_INBOX_TODAY}")
        return True
    else:
        print("[!] Target PDF was not found after execution.")
        return False

if __name__ == "__main__":
    success = compile_pdf()
    sys.exit(0 if success else 1)
