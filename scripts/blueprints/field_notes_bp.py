#!/usr/bin/env python3
"""
StackLabs Field Notes Blueprint
Decoupled router serving architectural field notes JSON API and Deep Void HTML on Clio.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import html as html_lib

field_notes_bp = APIRouter(tags=["field_notes"])

FIELD_NOTE_OCT_14_PATH = Path("/home/james/stacklabs/docs/daily_sprint_2026_10_14/FIELD_NOTE_SMALL_BALL_VS_BIG_AI_DODGERS.md")

@field_notes_bp.api_route("/api/field-notes", methods=["GET", "HEAD"])
def get_field_notes_api():
    """Returns canonical architectural field notes JSON payload."""
    md_text = FIELD_NOTE_OCT_14_PATH.read_text(encoding="utf-8") if FIELD_NOTE_OCT_14_PATH.exists() else ""
    return {
        "status": "ok",
        "count": 1,
        "notes": [
            {
                "id": "small-ball-vs-big-ai-dodgers-2026-10-14",
                "title": "Small Ball vs. The Big AI Dodgers: The Ohtani Contract of Enterprise Software",
                "date": "2026-10-14",
                "work_order": "WO0011147",
                "matchup": "MIL 6 - 2 LAD (NLCS Game 3 Final | Series: MIL 3 - 0 LAD)",
                "path": str(FIELD_NOTE_OCT_14_PATH),
                "markdown": md_text
            }
        ]
    }

@field_notes_bp.api_route("/field-notes", methods=["GET", "HEAD"])
def serve_field_notes_page():
    """Renders the October 14 Architectural Field Note in Deep Void (#0B0D13) HTML."""
    md_text = FIELD_NOTE_OCT_14_PATH.read_text(encoding="utf-8") if FIELD_NOTE_OCT_14_PATH.exists() else "Field note not found."
    escaped_md = html_lib.escape(md_text)
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Field Notes — Small Ball vs. The Big AI Dodgers | StackLabs FaaS</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #0B0D13;
      color: #F0F6FC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.65;
    }}
    header {{
      border-bottom: 1px solid rgba(255,255,255,0.1);
      background-color: #11141E;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .brand {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-weight: 800;
      color: #F59E0B;
      letter-spacing: 0.06em;
      font-size: 13px;
    }}
    .back-link {{
      color: #38BDF8;
      text-decoration: none;
      font-size: 12px;
      font-family: ui-monospace, monospace;
    }}
    .back-link:hover {{
      text-decoration: underline;
    }}
    main {{
      max-width: 820px;
      margin: 40px auto;
      padding: 0 20px 80px 20px;
    }}
    pre {{
      background-color: #11141E;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px;
      padding: 24px;
      overflow-x: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
      color: #E2E8F0;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">STACKLABS // FAAS FIELD NOTES</div>
    <a class="back-link" href="/">&larr; Return to FanStack Mobile HUD</a>
  </header>
  <main>
    <pre>{escaped_md}</pre>
  </main>
</body>
</html>"""
    return HTMLResponse(content=page_html, status_code=200)
