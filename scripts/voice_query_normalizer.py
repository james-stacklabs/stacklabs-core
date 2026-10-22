#!/usr/bin/env python3
"""
StackLabs Voice Query Normalizer & Semantic Extractor
Path: /home/james/stacklabs/scripts/voice_query_normalizer.py

Converts unstructured, conversational voice transcripts into deterministic,
typed JSON query contracts for FaaS, Horizon SCADA, and Cockpit systems.
"""

import os
import re
import sys
import json
import logging
from datetime import datetime, timezone
import zoneinfo
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
ENV_PATH = REPO_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

logger = logging.getLogger("VoiceQueryNormalizer")

DATA_DIR = REPO_ROOT / "data" / "voice_queries"
LATEST_QUERY_PATH = DATA_DIR / "latest_query.json"
SCRATCH_PAD_PATH = REPO_ROOT / "pilot_drops" / "pilot_scratch_pad.md"

SYSTEM_PROMPT = """You are the StackLabs Voice Query Normalizer on Clio metal.
Analyze this raw conversational voice memo from the Pilot or counterparty.
Strip out all conversational filler, expletives, side thoughts, and hesitation.
Extract the core semantic intent, entities, and executable query vectors.

Output strictly valid JSON with this exact schema:
{
  "domain": "MLB_POSTSEASON | HORIZON_ENERGY_SCADA | GENERAL_OPS | ENTERPRISE_CMDB",
  "intent": "TACTICAL_ANOMALY_QUERY | SCADA_PRESSURE_PROBE | SYSTEM_STATUS_QUERY | COUNTERPARTY_DISPATCH",
  "entities": {
    "key": "value"
  },
  "query_vectors": [
    {
      "target": "STREAM_CHAT_WIRETAP | STATCAST_TELEMETRY | SCADA_DATA_PLANE | GAME_THEORY_ENGINE | SYSTEM_METRICS",
      "action": "SEARCH_SENTIMENT | GET_PLAY_METRICS | GET_SERIES | CALCULATE_DELTA | GET_STATUS",
      "params": {}
    }
  ],
  "pithy_summary": "1-2 crisp sentences describing the exact hypothesis or query."
}"""


def normalize_voice_transcript(transcript: str, source_tag: str = "pilot_voice") -> dict:
    """Normalize raw speech into a structured executable query object."""
    clean_text = transcript.strip()
    if not clean_text:
        return {
            "status": "error",
            "error": "Empty transcript"
        }

    eastern = zoneinfo.ZoneInfo("America/New_York")
    now_dt = datetime.now(eastern)
    timestamp_str = now_dt.isoformat()
    ts_compact = now_dt.strftime("%Y%m%d_%H%M%S")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY missing; using rule-based fallback normalization.")
        parsed_payload = _fallback_normalization(clean_text, source_tag, timestamp_str)
    else:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[SYSTEM_PROMPT, f"Raw Audio Transcript:\n{clean_text}"],
                config={"response_mime_type": "application/json"}
            )
            parsed_payload = json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini normalization failed: {e}; falling back.")
            parsed_payload = _fallback_normalization(clean_text, source_tag, timestamp_str)

    # Wrap envelope
    contract = {
        "source": source_tag,
        "timestamp": timestamp_str,
        "raw_transcript": clean_text,
        "domain": parsed_payload.get("domain", "GENERAL_OPS"),
        "intent": parsed_payload.get("intent", "SYSTEM_STATUS_QUERY"),
        "entities": parsed_payload.get("entities", {}),
        "query_vectors": parsed_payload.get("query_vectors", []),
        "pithy_summary": parsed_payload.get("pithy_summary", clean_text[:120])
    }

    # Persist to local NVMe
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_]+", "", contract["domain"].lower())[:20]
    out_file = DATA_DIR / f"{ts_compact}_{slug}.json"
    out_file.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    LATEST_QUERY_PATH.write_text(json.dumps(contract, indent=2), encoding="utf-8")

    # Notify Scratchpad
    _notify_scratchpad(contract)

    return contract


def _fallback_normalization(text: str, source: str, ts: str) -> dict:
    """Deterministic heuristic fallback when external inference is unreachable."""
    lower = text.lower()
    if any(k in lower for k in ["ohtani", "braves", "dodgers", "sale", "rojas", "catcher", "interference"]):
        domain = "MLB_POSTSEASON"
        intent = "TACTICAL_ANOMALY_QUERY"
        vectors = [
            {"target": "STREAM_CHAT_WIRETAP", "action": "SEARCH_SENTIMENT", "params": {"keywords": ["interference", "Ohtani", "Rojas"]}},
            {"target": "STATCAST_TELEMETRY", "action": "GET_PLAY_METRICS", "params": {"event": "CATCHERS_INTERFERENCE"}}
        ]
    elif any(k in lower for k in ["sabine", "pipeline", "pressure", "psi", "compressor"]):
        domain = "HORIZON_ENERGY_SCADA"
        intent = "SCADA_PRESSURE_PROBE"
        vectors = [
            {"target": "SCADA_DATA_PLANE", "action": "GET_SERIES", "params": {"metric": "PSI"}}
        ]
    else:
        domain = "GENERAL_OPS"
        intent = "SYSTEM_STATUS_QUERY"
        vectors = [
            {"target": "SYSTEM_METRICS", "action": "GET_STATUS", "params": {}}
        ]

    return {
        "domain": domain,
        "intent": intent,
        "entities": {"summary": text[:80]},
        "query_vectors": vectors,
        "pithy_summary": f"Fallback extraction for: {text[:100]}"
    }


def _notify_scratchpad(contract: dict):
    """Log normalized query event to pilot scratchpad."""
    if SCRATCH_PAD_PATH.exists():
        try:
            domain = contract.get("domain", "OPS")
            summary = contract.get("pithy_summary", "")
            ts = datetime.now().strftime("%H:%M:%S EDT")
            entry = f"\n- **⚡ [VOICE NORMALIZER]** `{domain}`: \"{summary}\" ({ts})\n"
            with open(SCRATCH_PAD_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning(f"Failed to append to scratchpad: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: voice_query_normalizer.py <text_transcript>")
        sys.exit(1)
    input_text = " ".join(sys.argv[1:])
    result = normalize_voice_transcript(input_text)
    print(json.dumps(result, indent=2))
