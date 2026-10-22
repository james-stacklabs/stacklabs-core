import json
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="The Cosmic Sieve", description="Kramerica Industries Triage Valve")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STAGING_FILE = "/home/james/stacklabs/scripts/promo_staging.json"
CONTEXT_FILE = "/home/james/stacklabs/scripts/fanstack_live_context.txt"

class ActionPayload(BaseModel):
    action: str
    persona: str | None = None

def load_promos():
    if not os.path.exists(STAGING_FILE): return []
    try:
        with open(STAGING_FILE, "r") as f: return json.load(f)
    except: return []

def save_promos(promos):
    with open(STAGING_FILE, "w") as f: json.dump(promos, f, indent=4)

DECK_FILE = "/home/james/stacklabs/dna/mycroft_patent_knowledge/SOVEREIGN_FANSTACK_YOUTUBE_MONETIZATION_PLAN.md"

@app.get("/deck", response_class=HTMLResponse)
def serve_deck():
    try:
        with open(DECK_FILE, "r") as f:
            raw_md = f.read()
    except FileNotFoundError:
        raise HTTPException(404, "Deck not found")

    # Lightweight markdown-to-HTML conversion
    import re
    html = raw_md
    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # Bold/italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Code inline
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
    # Horizontal rule
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    # Table rows
    def render_table(m):
        lines = [l.strip() for l in m.group(0).strip().split('\n') if '|' in l and not re.match(r'^\|[-| ]+\|$', l.strip())]
        rows = []
        for i, line in enumerate(lines):
            cells = [c.strip() for c in line.strip('|').split('|')]
            tag = 'th' if i == 0 else 'td'
            rows.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
        return '<table>' + ''.join(rows) + '</table>'
    html = re.sub(r'(\|.+\|\n)+', render_table, html)
    # List items
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html)
    # Paragraphs: wrap bare lines
    lines_out = []
    for line in html.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            lines_out.append(f'<p>{stripped}</p>')
        else:
            lines_out.append(line)
    html = '\n'.join(lines_out)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sovereign FanStack — YouTube Monetization Plan</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #0d0f14; color: #e2e8f0; line-height: 1.7; }}
  .container {{ max-width: 860px; margin: 0 auto; padding: 48px 24px 96px; }}
  h1 {{ font-size: 2.4rem; font-weight: 900; color: #f6c90e; margin-bottom: 8px; }}
  h2 {{ font-size: 1.5rem; font-weight: 700; color: #f6c90e; margin: 40px 0 12px; border-bottom: 1px solid #2d3748; padding-bottom: 6px; }}
  h3 {{ font-size: 1.15rem; font-weight: 600; color: #90cdf4; margin: 28px 0 8px; }}
  p {{ margin-bottom: 14px; color: #cbd5e0; }}
  strong {{ color: #fff; }}
  em {{ color: #fbb6ce; font-style: italic; }}
  code {{ background: #1a202c; color: #68d391; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }}
  ul {{ margin: 12px 0 16px 24px; }}
  li {{ margin-bottom: 7px; color: #cbd5e0; }}
  hr {{ border: none; border-top: 1px solid #2d3748; margin: 36px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th {{ background: #1a202c; color: #f6c90e; text-align: left; padding: 10px 14px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #2d3748; color: #e2e8f0; }}
  tr:hover td {{ background: #1a202c; }}
  .badge {{ display: inline-block; background: linear-gradient(135deg, #f6c90e, #ff6b35); color: #0d0f14; font-weight: 700; font-size: 0.75rem; padding: 3px 10px; border-radius: 999px; margin-bottom: 24px; letter-spacing: 0.05em; text-transform: uppercase; }}
</style>
</head>
<body>
<div class="container">
<div class="badge">⚾ Patent Pending · USPTO · April 14, 2026</div>
{html}
</div>
</body>
</html>"""
    return HTMLResponse(content=page)

@app.get("/")
def serve_ui():
    return FileResponse("/home/james/stacklabs/scripts/promo_triage_desk.html")

@app.get("/api/promos")
def get_promos():
    return load_promos()

@app.post("/api/promos/{promo_id}/action")
def action_promo(promo_id: str, payload: ActionPayload):
    promos = load_promos()
    target = next((p for p in promos if p["id"] == promo_id), None)
    if not target: raise HTTPException(404, "Promo not found in Sieve")
    
    if payload.action == "inject_global":
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + target["raw_text"])
    elif payload.action == "target_persona":
        bot_name = payload.persona.upper()
        special_text = f"[DIRECTIVE FOR {bot_name} ONLY] {target['raw_text']}"
        with open(CONTEXT_FILE, "a") as f:
            f.write("\n" + special_text)
    
    # Remove from staging (Jettison just removes it without writing to context)
    promos = [p for p in promos if p["id"] != promo_id]
    save_promos(promos)
    return {"status": "success"}

if __name__ == "__main__":
    print("🌌 THE COSMIC SIEVE is listening on http://0.0.0.0:8091")
    uvicorn.run(app, host="0.0.0.0", port=8091)
