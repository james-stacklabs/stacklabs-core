#!/usr/bin/env python3
"""
Autonomous Voice Drop Syndicate Dossier & Deliverable Generator
Path: /home/james/stacklabs/scripts/voice_drop_syndicate_builder.py
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dotenv
dotenv.load_dotenv(REPO_ROOT / ".env")

APPROVAL_DIR = REPO_ROOT / "pilot_drops" / "pending_approval"
APPROVAL_DIR.mkdir(parents=True, exist_ok=True)


def build_strategic_dossier(channel: str, sender: str, transcript: str, audio_filename: str) -> dict:
    """Analyze inbound transcript and formulate an institutional strategic white paper."""
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is missing.")

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You are the Cockpit Architect for StackLabs LLC, working directly with Lead Systems Architect James Carroll. "
        "Strictly adhere to the Law of 'I' (Solo Builder voice: James Carroll operates on dedicated local hardware; strictly zero corporate 'we' or 'our'). "
        "Analyze the inbound counterparty voice memo. Extract their exact thesis, analogies, and questions. "
        "Formulate a definitive, institutional 4-section Strategic White Paper: "
        "1. Executive Summary & Counterparty Thesis Deconstruction "
        "2. Dedicated Systems Architecture & Deterministic Moat "
        "3. High-Throughput Market Microstructure & Unit Economics "
        "4. Actionable Pilot Deliverable Roadmap (The 4-Asset Stack: Executive Brief, Deep Dive Audio, Architecture Twin, Institutional Presentation). "
        "Return the output as valid JSON with keys: 'title', 'slug', 'core_thesis', 'whitepaper_markdown', 'podcast_focus_prompt'."
    )

    prompt = (
        f"Counterparty: {sender} (Channel: #{channel})\n"
        f"Audio Source File: {audio_filename}\n"
        f"Transcript:\n{transcript}\n\n"
        "Generate the complete strategic white paper and deliverables spec in JSON."
    )

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[prompt],
        config={
            "system_instruction": system_instruction,
            "response_mime_type": "application/json"
        }
    )

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    data = json.loads(raw_text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = data.get("slug", f"briefing_{timestamp}")
    dossier_id = f"DOSSIER_{timestamp}_{slug}"

    payload = {
        "dossier_id": dossier_id,
        "timestamp": datetime.now().isoformat(),
        "channel": channel,
        "sender": sender,
        "audio_filename": audio_filename,
        "title": data.get("title", "Executive Syndicate Briefing"),
        "core_thesis": data.get("core_thesis", ""),
        "podcast_focus_prompt": data.get("podcast_focus_prompt", ""),
        "whitepaper_markdown": data.get("whitepaper_markdown", ""),
        "status": "PENDING_PILOT_APPROVAL"
    }

    # Save to pending approval directory
    out_file = APPROVAL_DIR / f"{dossier_id}.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Also write readable markdown whitepaper
    md_file = APPROVAL_DIR / f"{dossier_id}.md"
    md_content = f"""# {payload['title']}

> **Dossier ID**: `{dossier_id}`  
> **Source Audio**: `{audio_filename}`  
> **Channel**: `#{channel}`  
> **Sender**: `{sender}`  
> **Status**: `PENDING_PILOT_APPROVAL`  

---

### Core Thesis
{payload['core_thesis']}

---

{payload['whitepaper_markdown']}
"""
    md_file.write_text(md_content, encoding="utf-8")

    return payload


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: voice_drop_syndicate_builder.py <transcript_file_or_text> <audio_filename>")
        sys.exit(1)

    input_arg = sys.argv[1]
    audio_file = sys.argv[2]

    if Path(input_arg).exists():
        transcript_text = Path(input_arg).read_text(encoding="utf-8")
    else:
        transcript_text = input_arg

    print(f"Generating syndicate dossier for {audio_file}...")
    res = build_strategic_dossier("pawel", "pawel", transcript_text, audio_file)
    print(f"Dossier generated: {res['dossier_id']}")
    print(f"Staged at: {APPROVAL_DIR / res['dossier_id']}.json")
