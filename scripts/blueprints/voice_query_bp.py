#!/usr/bin/env python3
"""
StackLabs Voice Query Blueprint (Port 8088 /drop.stacklabsllc.com)
Path: /home/james/stacklabs/scripts/blueprints/voice_query_bp.py

Exposes endpoints for real-time voice query normalization and inspection.
"""

import json
from pathlib import Path
from flask import Blueprint, request, jsonify
from scripts.voice_query_normalizer import normalize_voice_transcript, LATEST_QUERY_PATH

voice_query_bp = Blueprint("voice_query", __name__)


@voice_query_bp.route("/api/voice/normalize", methods=["POST"])
def api_normalize_voice():
    """
    Normalize unstructured voice transcript into a typed query contract.
    Expected JSON:
    {
        "transcript": "Raw voice text...",
        "source": "pilot_voice"
    }
    """
    data = request.get_json(silent=True) or {}
    transcript = str(data.get("transcript") or data.get("text") or "").strip()
    source = str(data.get("source") or "api_voice").strip()

    if not transcript:
        return jsonify({"status": "error", "error": "Missing transcript"}), 400

    result = normalize_voice_transcript(transcript, source_tag=source)
    return jsonify({"status": "success", "query": result}), 200


@voice_query_bp.route("/api/voice/latest_query", methods=["GET"])
def api_latest_query():
    """Return the most recent normalized voice query vector."""
    if not LATEST_QUERY_PATH.exists():
        return jsonify({"status": "empty", "query": None}), 200
    try:
        payload = json.loads(LATEST_QUERY_PATH.read_text(encoding="utf-8"))
        return jsonify({"status": "success", "query": payload}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@voice_query_bp.route("/api/voice/health", methods=["GET"])
def voice_health():
    return jsonify({
        "status": "ok",
        "service": "StackLabs Voice Query Normalizer (Port 8088)",
        "models": ["gemini-3.8-flash"]
    }), 200
