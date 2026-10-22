#!/usr/bin/env python3
"""
StackLabs Phone Bridge & SMS Ingress Blueprint (Port 8088 /drop.stacklabsllc.com)
Path: /home/james/stacklabs/scripts/blueprints/phone_bridge_bp.py

Receives mobile SMS events from MacroDroid, routes counterparty communications,
and executes automated edge handlers (Mom-Bot via Gemini 3.8 Flash).
"""

import os
import re
import sys
import json
import logging
from datetime import datetime
import zoneinfo
from pathlib import Path
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

# Ensure environment loaded
ENV_FILE = Path("/home/james/stacklabs/.env")
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

logger = logging.getLogger("PhoneBridge")

phone_bridge_bp = Blueprint("phone_bridge", __name__)

DATA_DIR = Path("/home/james/stacklabs/data")
AUDIT_LOG_PATH = DATA_DIR / "phone_bridge_audit.json"
SCRATCH_PAD_PATH = Path("/home/james/stacklabs/pilot_drops/pilot_scratch_pad.md")

MOM_REGEX = re.compile(r"(?i)^what(?:'s|\s+is)\s+(.*?)\??$")


def resolve_mom_bot(query_term: str) -> str:
    """Invoke Gemini 3.8 Flash to answer mom's inquiry in 1-2 plain sentences."""
    clean_query = query_term.strip().rstrip("?")
    prompt = (
        f"You are a warm, helpful SMS auto-responder for my mom, Eileen Carroll. "
        f"Explain what '{clean_query}' is in 1 to 2 plain-English sentences under 140 characters. "
        f"STRICT RULES: No markdown, no bold asterisks, no quotes, no bullet points. Plain text only."
    )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY missing; using local fallback for Mom-Bot.")
        return f"It is {clean_query}. James will tell you more when he is off metal."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        answer = response.text.strip().replace("*", "").replace('"', "")
        # Enforce character constraint
        if len(answer) > 200:
            sentences = answer.split(". ")
            answer = ". ".join(sentences[:2]).rstrip(".") + "."
        return answer
    except Exception as e:
        logger.error(f"Gemini Mom-Bot generation failed: {e}")
        return f"It is {clean_query}. Checking on metal for you."


def record_phone_audit(entry: dict):
    """Append structured entry to data/phone_bridge_audit.json."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        current = []
        if AUDIT_LOG_PATH.exists():
            try:
                current = json.loads(AUDIT_LOG_PATH.read_text(encoding="utf-8"))
            except Exception:
                current = []
        current.append(entry)
        if len(current) > 200:
            current = current[-200:]
        AUDIT_LOG_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to record phone audit: {e}")


def notify_pilot_scratchpad(sender_name: str, body: str, reply_sent: str = None):
    """Append brief event notification to pilot scratchpad."""
    if SCRATCH_PAD_PATH.exists():
        try:
            preview = body.strip().replace("\n", " ")[:80]
            ts = datetime.now().strftime("%H:%M:%S EDT")
            reply_tag = f" -> Replied: \"{reply_sent[:40]}...\"" if reply_sent else ""
            alert = f"\n- **⚡ [PHONE BRIDGE]** {sender_name}: \"{preview}\"{reply_tag} ({ts})\n"
            with open(SCRATCH_PAD_PATH, "a", encoding="utf-8") as f:
                f.write(alert)
        except Exception as e:
            logger.warning(f"Scratchpad alert failed: {e}")


@phone_bridge_bp.route("/api/ingress/sms", methods=["POST"])
@phone_bridge_bp.route("/api/phone/inbound", methods=["POST"])
def handle_inbound_sms():
    """
    Ingest SMS event from mobile phone bridge (MacroDroid).
    Expected JSON:
    {
        "sender": "+1...",
        "contact_name": "Eileen Carroll",
        "body": "What is CDS?"
    }
    """
    data = request.get_json(silent=True) or {}
    sender = str(data.get("sender") or data.get("phone_number") or "Unknown").strip()
    contact_name = str(data.get("contact_name") or data.get("name") or sender).strip()
    body = str(data.get("body") or data.get("message") or "").strip()

    if not body:
        return jsonify({"status": "error", "error": "Empty message body"}), 400

    eastern = zoneinfo.ZoneInfo("America/New_York")
    now_str = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S EDT")

    is_mom = any(x in contact_name.lower() for x in ["eileen", "mom", "carroll"])
    mom_match = MOM_REGEX.match(body)

    action = "none"
    reply_text = None

    if is_mom and mom_match:
        query_term = mom_match.group(1).strip()
        explanation = resolve_mom_bot(query_term)
        reply_text = f"🤖 Mom-Bot: {explanation}\n\n(Powered by Google & your son)"
        action = "reply"

    audit_entry = {
        "timestamp": now_str,
        "sender": sender,
        "contact_name": contact_name,
        "body": body,
        "action": action,
        "reply_text": reply_text
    }
    record_phone_audit(audit_entry)
    notify_pilot_scratchpad(contact_name, body, reply_text)

    return jsonify({
        "status": "success",
        "action": action,
        "reply_text": reply_text,
        "counterparty": contact_name,
        "timestamp": now_str
    }), 200


@phone_bridge_bp.route("/api/phone/health", methods=["GET"])
@phone_bridge_bp.route("/api/ingress/sms/health", methods=["GET"])
def phone_bridge_health():
    return jsonify({
        "status": "ok",
        "service": "StackLabs Phone Bridge (Port 8088)",
        "models": ["gemini-3.8-flash"]
    }), 200
