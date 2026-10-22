#!/usr/bin/env python3
"""
StackLabs Google Cloud TTS Audio Brief Dispatcher
Path: /home/james/stacklabs/scripts/generate_daily_audio.py
Author: James Carroll (Lead Systems Architect)

Reads markdown sprint notes, structures conversational SSML,
and calls Google Cloud Text-to-Speech (Journey / Studio voices)
using active developer credits.
Outputs atomic MP3 to /home/james/stacklabs/audio/daily_sprint.mp3.
"""

import os
import sys
import re
import argparse
from pathlib import Path
from google.cloud import texttospeech

AUDIO_DIR = Path("/home/james/stacklabs/audio")
DEFAULT_SOURCE = Path("/home/james/sovereign_inbox/pilot_drops/GROUND_TRUTH_PROMPT_CONTEXT.md")
OUTPUT_FILE = AUDIO_DIR / "daily_sprint.mp3"

def clean_markdown_for_speech(text: str) -> str:
    """Strips code blocks, markdown links, and raw URLs to produce natural speech text."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", " [Code block omitted] ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove markdown links, keep label
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Strip raw URLs
    text = re.sub(r"http[s]?://\S+", "", text)
    # Clean up excess whitespace and bullet artifacts
    text = re.sub(r"^[ \t]*[\*\-\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def build_ssml(text: str, speaking_rate: float = 1.0) -> str:
    """Wraps clean text into structured SSML with measured pauses."""
    paragraphs = text.split("\n")
    ssml_parts = ["<speak>"]
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        ssml_parts.append(f"<p>{p_clean}</p><break time='350ms'/>")
    ssml_parts.append("</speak>")
    return "".join(ssml_parts)

def synthesize_audio(input_file: Path, voice_name: str = "en-US-Journey-D"):
    if not input_file.exists():
        print(f"[ERROR] Source file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    raw_content = input_file.read_text(encoding="utf-8", errors="ignore")
    speech_text = clean_markdown_for_speech(raw_content)

    # Scrape first 4000 characters if payload exceeds single-chunk quotas
    if len(speech_text) > 4500:
        speech_text = speech_text[:4500] + "... [Brief truncated for audio overview]"

    ssml = build_ssml(speech_text)

    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        default_sa = Path("/home/james/stacklabs/config/vertex_sa.json")
        if default_sa.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(default_sa)

    client = texttospeech.TextToSpeechClient()
    s_input = texttospeech.SynthesisInput(ssml=ssml)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.02,
        pitch=0.0
    )

    print(f"[*] Calling Google Cloud TTS ({voice_name})...")
    try:
        response = client.synthesize_speech(
            input=s_input, voice=voice, audio_config=audio_config
        )
        OUTPUT_FILE.write_bytes(response.audio_content)
        size_kb = len(response.audio_content) / 1024
        print(f"✅ Audio generated successfully: {OUTPUT_FILE} ({size_kb:.1f} KB)")
    except Exception as e:
        if "SERVICE_DISABLED" in str(e) or "texttospeech.googleapis.com" in str(e):
            print(f"[ERROR] Google Cloud TTS API (texttospeech.googleapis.com) is not enabled for the GCP project.", file=sys.stderr)
            print("[INFO] Enable at: https://console.developers.google.com/apis/api/texttospeech.googleapis.com/overview", file=sys.stderr)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StackLabs Google Cloud TTS Audio Brief Dispatcher")
    parser.add_argument("--source", type=str, default="/home/james/sovereign_inbox/pilot_drops/GROUND_TRUTH_PROMPT_CONTEXT.md", help="Path to markdown source")
    parser.add_argument("--voice", type=str, default="en-US-Journey-D", help="Google Cloud TTS voice identifier")
    args = parser.parse_args()

    synthesize_audio(Path(args.source), args.voice)
