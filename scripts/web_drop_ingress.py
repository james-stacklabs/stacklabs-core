#!/usr/bin/env python3
"""
Sovereign OS — Web Drop Ingress Gateway
Path: /home/james/stacklabs/scripts/web_drop_ingress.py
Endpoint: GET/POST /drop (Mounted on Port 8088 / Tailscale mesh)

Provides a minimal, zero-bloat web ingress page for queuing Work Orders.
Submitting the form immediately writes an atomic markdown file with a
unique timestamped ID directly into /home/james/stacklabs/queue/incoming/.
"""

import os
import re
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, render_template_string

logger = logging.getLogger("WebDropIngress")

web_drop_ingress_bp = Blueprint("web_drop_ingress", __name__)

INCOMING_DIR = Path("/home/james/stacklabs/queue/incoming")
INCOMING_DIR.mkdir(parents=True, exist_ok=True)

DROP_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DROP WORK ORDER // WEB INGRESS</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-void: #080A0F;
      --bg-card: #0F141F;
      --bg-card-hover: #161D2D;
      --border-subtle: #242B38;
      --color-gold: #FFB020;
      --color-gold-hover: #F59E0B;
      --color-emerald: #10B981;
      --color-crimson: #EF4444;
      --text-primary: #F0F6FC;
      --text-muted: #8B949E;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-void);
      color: var(--text-primary);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px;
    }
    .container {
      width: 100%;
      max-width: 980px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 20px;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--color-gold);
      background: rgba(255, 176, 32, 0.12);
      border: 1px solid rgba(255, 176, 32, 0.3);
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }
    .title {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text-primary);
    }
    .status-pill {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--color-emerald);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--color-emerald);
      box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
    }
    .form-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .label-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
    textarea {
      width: 100%;
      min-height: 420px;
      height: 60vh;
      background: #05070A;
      color: #E2E8F0;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13.5px;
      line-height: 1.6;
      padding: 16px;
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      resize: vertical;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    textarea:focus {
      border-color: var(--color-gold);
      box-shadow: 0 0 12px rgba(255, 176, 32, 0.2);
    }
    textarea::placeholder {
      color: #475569;
    }
    .action-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .hint-text {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
    .btn-submit {
      background: linear-gradient(135deg, #FFB020 0%, #D97706 100%);
      color: #000000;
      font-family: 'JetBrains Mono', monospace;
      font-size: 14px;
      font-weight: 700;
      padding: 12px 26px;
      border: 1px solid rgba(255, 176, 32, 0.5);
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
      letter-spacing: 0.02em;
    }
    .btn-submit:hover {
      background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
      box-shadow: 0 0 15px rgba(255, 176, 32, 0.35);
      transform: translateY(-1px);
    }
    .btn-submit:active {
      transform: translateY(0);
    }
    .btn-submit:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
    .toast {
      position: fixed;
      top: 24px;
      right: 24px;
      max-width: 480px;
      background: #0F141F;
      color: #F0F6FC;
      border: 1px solid var(--color-emerald);
      border-radius: 8px;
      padding: 14px 20px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(16, 185, 129, 0.25);
      display: none;
      opacity: 0;
      transform: translateY(-10px);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 1000;
    }
    .toast.show {
      display: block;
      opacity: 1;
      transform: translateY(0);
    }
    .toast.error {
      border-color: var(--color-crimson);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(239, 68, 68, 0.25);
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-left">
        <span class="badge">INGRESS</span>
        <span class="title">DROP WORK ORDER</span>
      </div>
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>QUEUE READY</span>
      </div>
    </div>

    <div class="form-panel">
      <div class="label-row">
        <span>MARKDOWN WORK ORDER PAYLOAD</span>
        <span id="charCount">0 characters</span>
      </div>

      <form id="dropForm" action="/drop" method="POST">
        <textarea
          id="payload"
          name="content"
          placeholder="# WORK ORDER: WO0010XXX_DESCRIPTIVE_SLUG&#10;# TARGET: Aggie Background Runner&#10;# SYSTEM: Clio&#10;# PRIORITY: Immediate&#10;&#10;## Q1: OBJECTIVE & SCOPE&#10;Describe task requirements...&#10;&#10;## Q2: SPECIFICATION&#10;List target files and logic...&#10;&#10;## Q3: IMPLEMENTATION&#10;Step-by-step changes...&#10;&#10;## Q4: VERIFICATION&#10;Commands to verify..."
          required
        >{{ prefill_content or '' }}</textarea>

        <div class="action-row" style="margin-top: 16px;">
          <span class="hint-text">Atomic queue ingress &bull; clio_queue_watcher auto-pickup</span>
          <button type="submit" id="submitBtn" class="btn-submit">[ INGEST TO QUEUE ]</button>
        </div>
      </form>
    </div>
  </div>

  <div id="toast" class="toast{% if success_toast %} show{% elif error %} show error{% endif %}">
    {% if success_toast %}
      {{ success_toast }}
    {% elif error %}
      {{ error }}
    {% endif %}
  </div>

  <script>
    const form = document.getElementById('dropForm');
    const textarea = document.getElementById('payload');
    const submitBtn = document.getElementById('submitBtn');
    const toast = document.getElementById('toast');
    const charCount = document.getElementById('charCount');

    function updateCount() {
      const len = textarea.value.length;
      charCount.textContent = len.toLocaleString() + ' characters';
    }

    textarea.addEventListener('input', updateCount);
    updateCount();

    function showToast(msg, isError = false) {
      toast.textContent = msg;
      toast.className = 'toast show' + (isError ? ' error' : '');
      setTimeout(() => {
        toast.className = 'toast';
      }, 5000);
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const content = textarea.value;
      if (!content.trim()) {
        showToast('Payload cannot be empty', true);
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = '[ INGESTING... ]';

      try {
        const resp = await fetch('/drop', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({ content: content })
        });

        const data = await resp.json();
        if (resp.ok && data.status === 'success') {
          showToast(data.message || ('Ticket queued: ' + data.filename));
          textarea.value = '';
          updateCount();
        } else {
          showToast(data.message || 'Ingestion failed', true);
        }
      } catch (err) {
        showToast('Network error: ' + err.message, true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '[ INGEST TO QUEUE ]';
      }
    });
  </script>
</body>
</html>
"""


def write_atomic_work_order(raw_text: str) -> tuple[str, str, Path]:
    """
    Validates, strips null bytes, and writes atomic markdown file to queue/incoming/.
    Naming convention: WO_WEB_DROP_<YYYYMMDD_HHMMSS>.md
    Returns: (ticket_id, filename, target_path)
    """
    # Validation gate: strip leading/trailing null bytes & whitespace
    cleaned = raw_text.strip('\x00').strip()
    if not cleaned:
        raise ValueError("Payload cannot be empty")

    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    filename = f"WO_WEB_DROP_{ts}.md"
    target_path = INCOMING_DIR / filename

    # Avoid collisions if called within the same second
    if target_path.exists():
        ts = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
        filename = f"WO_WEB_DROP_{ts}.md"
        target_path = INCOMING_DIR / filename

    tmp_path = INCOMING_DIR / f".{filename}.tmp"

    # Atomic file write via .tmp rename
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(cleaned + "\n")
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, target_path)
    ticket_id = f"WO_WEB_DROP_{ts}"
    return ticket_id, filename, target_path


@web_drop_ingress_bp.route('/drop', methods=['GET', 'POST'], strict_slashes=False)
def route_web_drop():
    """Renders the drop form on GET; processes and ingests payload on POST."""
    if request.method == 'GET':
        return render_template_string(DROP_HTML_TEMPLATE)

    # POST handling: accepts JSON, form-data, or raw text body
    raw_text = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        for key in ("content", "text", "work_order", "payload", "body"):
            if key in data:
                raw_text = data[key]
                break
        if raw_text is None and data:
            raw_text = next(iter(data.values()), None)
    elif request.form:
        for key in ("content", "text", "work_order", "payload", "body"):
            if key in request.form:
                raw_text = request.form[key]
                break
        if raw_text is None:
            body_text = request.get_data(as_text=True)
            if body_text and '=' not in body_text:
                raw_text = body_text

    if raw_text is None:
        try:
            raw_text = request.get_data(as_text=True)
        except Exception:
            raw_text = ""

    if not isinstance(raw_text, str):
        raw_text = str(raw_text or "")

    # Validation check: reject empty or null-only payloads
    cleaned_check = raw_text.strip('\x00').strip()
    is_json_client = request.is_json or (request.headers.get("Accept") == "application/json") or (request.headers.get("X-Requested-With") == "XMLHttpRequest")

    if not cleaned_check:
        if is_json_client:
            return jsonify({"status": "error", "message": "Payload cannot be empty"}), 400
        return render_template_string(DROP_HTML_TEMPLATE, error="Payload cannot be empty"), 400

    try:
        ticket_id, filename, target_path = write_atomic_work_order(raw_text)
    except Exception as e:
        logger.error(f"Failed to write work order: {e}")
        if is_json_client:
            return jsonify({"status": "error", "message": str(e)}), 500
        return render_template_string(DROP_HTML_TEMPLATE, error=str(e)), 500

    toast_msg = f"Ticket queued: {filename}"
    logger.info(f"Successfully ingested drop: {filename} -> {target_path}")

    # Respond to curl / AJAX clients with JSON
    if is_json_client:
        return jsonify({
            "status": "success",
            "message": toast_msg,
            "ticket_id": ticket_id,
            "filename": filename,
            "path": str(target_path)
        }), 200

    # Fallback response for standard browser form POST without JS
    return render_template_string(DROP_HTML_TEMPLATE, success_toast=toast_msg, queued_file=filename), 200


def create_standalone_app():
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(web_drop_ingress_bp)
    return app


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8088))
    host = os.environ.get("HOST", "127.0.0.1")
    app = create_standalone_app()
    logger.info(f"⚡ Starting Standalone Web Drop Ingress on {host}:{port}...")
    app.run(host=host, port=port, debug=False)
