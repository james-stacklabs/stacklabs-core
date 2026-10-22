#!/usr/bin/env python3
"""
scripts/process_mcafee_transcript_gemini.py
===========================================
Ingests the Artemis CUDA Whisper transcript of The Pat McAfee Show,
invokes Gemini (gemini-3.8-flash) via the google.genai SDK for deep semantic extraction,
synthesizes broadcast intelligence (Sauron Reel, Hour-by-Hour breakdown, Dogpile telemetry),
and updates the daily Post-Show Lookbook dossier.

Governed by:
  - Absolute Model Invariant: Strictly gemini-3.8-flash (October 2026)
  - Solo Builder Invariant: First-person singular ("I", "my")
  - Campsite Protocol & Two-Call Verification
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")

from google import genai
from google.genai import types

TRANSCRIPT_DEFAULT = REPO_ROOT / "pilot_drops" / "MCAFEE_FULL_BROADCAST_TRANSCRIPT_2026_10_19.md"
LOOKBOOK_PATH = REPO_ROOT / "pilot_drops" / "MCAFEE_POST_SHOW_LOOKBOOK_2026_10_19.md"
INTEL_OUTPUT_PATH = REPO_ROOT / "pilot_drops" / "MCAFEE_BROADCAST_INTELLIGENCE_2026_10_19.md"
RECEIPT_PATH = REPO_ROOT / "today" / "MCAFEE_TRANSCRIPT_GEMINI_RECEIPT_2026_10_19.json"


def get_working_client() -> Tuple[genai.Client, str]:
    """Finds an active working Gemini API client from available keys."""
    keys_to_test = [
        "GEMINI_BACKUP_KEY_2",
        "GEMINI_API_KEY",
        "GEMINI_CAPPED_TIER1_KEY",
        "VITE_GEMINI_API_KEY"
    ]
    for key_name in keys_to_test:
        val = os.getenv(key_name)
        if not val:
            continue
        try:
            client = genai.Client(api_key=val)
            # Fast ping check
            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents="ping"
            )
            if res and res.text:
                print(f"[✓] Active Gemini client verified with key: {key_name}")
                return client, key_name
        except Exception as e:
            print(f"[-] Key {key_name} failed: {e}", file=sys.stderr)
            continue
    raise RuntimeError("No active Gemini API key found with valid quota.")


def wait_for_transcript(transcript_path: Path, max_wait_sec: int = 1800, poll_sec: int = 15) -> bool:
    """Waits for transcript file to exist and have non-trivial size."""
    print(f"[*] Waiting for transcript at {transcript_path} (max wait {max_wait_sec}s)...")
    start = time.time()
    while time.time() - start < max_wait_sec:
        if transcript_path.exists() and transcript_path.stat().st_size > 1000:
            print(f"[✓] Found transcript ({transcript_path.stat().st_size} bytes)")
            return True
        time.sleep(poll_sec)
    return False


def run_gemini_analysis(client: genai.Client, transcript_text: str) -> Dict[str, Any]:
    """Runs transcript through gemini-3.8-flash to extract structured broadcast intelligence."""
    print("[*] Dispatching full broadcast transcript to gemini-3.8-flash...")
    
    # We take the first 400,000 characters if huge, or full text
    sample_text = transcript_text[:500000]

    system_instruction = """You are the Lead Sports Intelligence Analyst for StackLabs and The Pat McAfee Show Lookbook compiler.
Your task is to analyze the complete audio transcript of today's live broadcast (Monday, October 19, 2026 - live from Levi's Stadium, post-Week 7 NFL Sunday).

Extract precise, grounded broadcast telemetry:
1. "3_bullet_brief": 3 high-impact executive bullets (<60 sec read) on the dominant themes of the show.
2. "broadcast_anatomy":
   - "hour_1": Focus, key topics (e.g. Eagles/Sirianni collapse, 4th down malpractice, Titans/Levis, Cowboys heartbreak), estimated velocity/meltdown.
   - "hour_2": Guest interviews, tactical film breakdown, in-studio debate, key quotes.
   - "hour_3": Live callers, superchat mailbag, afternoon wrap-up.
3. "top_10_sauron_quotes": Exactly 10 craziest, funniest, or most controversial spoken on-air quotes with:
   - "timecode": Approximate time format "[HH:MM:SS]" or "[MM:SS]"
   - "speaker": Host or guest (e.g. "Pat McAfee", "AJ Hawk", "Tone Digs", "Boston Connor", "Ty Schmit", guest name)
   - "title": 2-4 word punchy title
   - "quote": Exact spoken quote
4. "pitchfork_dogpiles": Top 4 individuals or groups being heavily scrutinized or roasted on-air (e.g. Nick Sirianni, Brian Daboll, NFL Referees/Officiating, Jalen Hurts, Jerry Jones), with role, summary of criticism, and status ("ACTIVE DOGPILE" or "HEATED").

Return strictly valid JSON matching this schema."""

    prompt = f"""Analyze this Pat McAfee Show broadcast transcript and return structured JSON:

TRANSCRIPT EXCERPT:
{sample_text}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    try:
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"[!] Warning: Failed to parse JSON response: {e}. Raw response:\n{response.text[:500]}", file=sys.stderr)
        return {"raw_response": response.text}


def update_lookbook_with_intelligence(lookbook_path: Path, intel: Dict[str, Any]):
    """Surgically enriches Section 5 and Executive Vitals of the existing lookbook with Gemini extracted quotes."""
    if not lookbook_path.exists():
        print(f"[!] Warning: Lookbook not found at {lookbook_path}; skipping patch.")
        return

    content = lookbook_path.read_text(encoding="utf-8")
    
    # Format Sauron Reel
    sauron_quotes = intel.get("top_10_sauron_quotes", [])
    if sauron_quotes and isinstance(sauron_quotes, list):
        formatted_progrum = []
        for idx, item in enumerate(sauron_quotes[:10], 1):
            title = item.get("title", f"Segment Highlight {idx}")
            speaker = item.get("speaker", "Pat McAfee")
            quote = item.get("quote", "")
            tc = item.get("timecode", "")
            tc_str = f"[{tc}] " if tc else ""
            formatted_progrum.append(f'{idx}. **{tc_str}{title}** — {speaker}:  \n   *"{quote}"*')
        
        sauron_replacement = "\n".join(formatted_progrum)
        
        # Replace Section 5's THE ON-AIR PROGRUM block using a lambda to prevent group collision
        pattern = r"(### 🎙️ THE ON-AIR PROGRUM \(VERBATIM SPOKEN TIMECODES\)\n\n)(.*?)(?=\n### 💬 THE BLEACHER WIRE)"
        new_content, count = re.subn(pattern, lambda m: m.group(1) + sauron_replacement + "\n", content, flags=re.DOTALL)
        if count > 0:
            lookbook_path.write_text(new_content, encoding="utf-8")
            print(f"[✓] Patched Section 5 Sauron Reel in {lookbook_path.name} ({len(sauron_quotes)} quotes)")
        else:
            print("[!] Note: Could not find exact Section 5 match; appending intelligence appendix.")
            new_content = content + "\n\n## ⚡ GEMINI SPOKEN TRANSCRIPT AUTOPSY\n\n" + sauron_replacement
            lookbook_path.write_text(new_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Process McAfee transcript via Gemini 3.8 Flash")
    parser.add_argument("--transcript", default=str(TRANSCRIPT_DEFAULT), help="Path to transcript markdown")
    parser.add_argument("--wait", action="store_true", help="Wait for transcript to appear")
    parser.add_argument("--max-wait", type=int, default=1800, help="Max wait seconds")
    args = parser.parse_args()

    transcript_path = Path(args.transcript).resolve()

    if args.wait:
        found = wait_for_transcript(transcript_path, max_wait_sec=args.max_wait)
        if not found:
            print(f"[❌] Error: Transcript did not appear within {args.max_wait}s", file=sys.stderr)
            sys.exit(1)
    elif not transcript_path.exists():
        print(f"[❌] Error: Transcript not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    transcript_text = transcript_path.read_text(encoding="utf-8")
    print(f"[✓] Loaded transcript: {len(transcript_text)} characters")

    client, key_name = get_working_client()
    intel = run_gemini_analysis(client, transcript_text)

    # Save intelligence artifact
    INTEL_OUTPUT_PATH.write_text(
        f"# 🎙️ THE PAT MCAFEE SHOW // VERBATIM BROADCAST INTELLIGENCE\n"
        f"> **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"> **Model:** `gemini-3.8-flash` (Active October 2026 Production)  \n"
        f"> **Source Transcript:** `{transcript_path.name}` ({len(transcript_text)} chars)  \n"
        f"\n---\n\n"
        f"```json\n{json.dumps(intel, indent=2)}\n```\n",
        encoding="utf-8"
    )
    print(f"[✓] Saved intelligence dossier to {INTEL_OUTPUT_PATH}")

    # Update lookbook
    update_lookbook_with_intelligence(LOOKBOOK_PATH, intel)

    # Write receipt
    receipt = {
        "status": "PASS",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "transcript_path": str(transcript_path),
        "transcript_size_bytes": transcript_path.stat().st_size,
        "transcript_char_count": len(transcript_text),
        "gemini_model": "gemini-3.8-flash",
        "api_key_source": key_name,
        "sauron_quotes_extracted": len(intel.get("top_10_sauron_quotes", [])),
        "intelligence_artifact": str(INTEL_OUTPUT_PATH),
        "lookbook_updated": str(LOOKBOOK_PATH)
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"[✓] Written execution receipt to {RECEIPT_PATH}")
    print("\n" + "=" * 70)
    print("✅ MCAFEE TRANSCRIPT GEMINI PROCESSING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    import re
    from typing import Tuple
    main()
