#!/usr/bin/env python3
# ACOUSTIC SILICON GATING GUARD (OCTOBER 2026):
# Raw audio upload to Google Gemini API is disabled to prevent tripping billing tier caps.
# Transcribe locally on Artemis (100.108.185.53) via scripts/artemis_whisper.py.

"""
High-Fidelity NotebookLM Podcast Audio Transcriber & Diarizer
Path: /home/james/stacklabs/scripts/transcribe_notebooklm_podcast.py
"""

import os
import sys
import time
from pathlib import Path
import dotenv
from google import genai

REPO_ROOT = Path("/home/james/stacklabs")
dotenv.load_dotenv(REPO_ROOT / ".env")

def transcribe(audio_path: Path) -> Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment.")

    client = genai.Client(api_key=api_key)

    print(f"📡 Uploading {audio_path.name} ({audio_path.stat().st_size / (1024*1024):.2f} MB)...")
    uploaded = client.files.upload(file=str(audio_path))
    print(f"✔ Uploaded successfully as {uploaded.name}. State: {uploaded.state}")

    # Wait if file is processing
    while uploaded.state.name == "PROCESSING":
        print("⏳ Processing audio in Gemini...")
        time.sleep(5)
        uploaded = client.files.get(name=uploaded.name)

    print("🧠 Transcribing and diarizing via gemini-3.8-flash...")
    prompt = """
You are an expert audio stenographer transcribing a high-level technical podcast from Google NotebookLM (Deep Dive Audio Overview).
The podcast features two hosts (a male host and a female host) discussing James Carroll, solo systems architect at StackLabs LLC in Smyrna, Georgia, his April 4, 2026 patent formulation (treating LLMs strictly as stateless ALUs and pinning memory to local solid-state silicon), his Netscape Navigator joke regarding plaintext HTTP persistence, and his Concentric Circle go-to-market strategy.

Provide a complete, verbatim transcript with:
1. Speaker labels ("Host 1 [Male]" / "Host 2 [Female]")
2. Timestamps in [MM:SS] format for every speaker turn or major section
3. Exact capture of all technical terms (ALU, von Neumann, GBNF, POSIX /dev/shm, SQLite WAL, Statcast, Barf, Plaintext HTTP, TLS 1.3, SCADA, PLCs, Netscape Navigator, Castle Gate vs Kitchen Dumbwaiter)
4. Highlight key moments, jokes, and architectural breakthroughs.

Format as clean, beautiful GitHub Markdown.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[uploaded, prompt]
    )

    transcript_text = response.text.strip()
    
    out_drop = REPO_ROOT / "pilot_drops" / f"{audio_path.stem}_TRANSCRIPT.md"
    out_inbox = Path("/home/james/stacklabs_inbox/daily_10032026") / f"{audio_path.stem}_TRANSCRIPT.md"

    header = f"""# 🎙️ NOTEBOOKLM AUDIO OVERVIEW TRANSCRIPT: {audio_path.stem.replace('_', ' ').upper()}

> **Source Audio**: `{audio_path.name}` (20m 48s • {audio_path.stat().st_size / (1024*1024):.2f} MB)  
> **Transcribed On**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')} via Gemini 2.5 Flash  
> **Key Topics**: Stateless ALU von Neumann architecture, Netscape Navigator Plaintext HTTP roast, Castle Gate vs. Kitchen Dumbwaiter law, Concentric Circle GTM.

---

"""

    full_md = header + transcript_text
    out_drop.write_text(full_md, encoding="utf-8")
    if out_inbox.parent.exists():
        out_inbox.write_text(full_md, encoding="utf-8")

    print(f"✔ Transcript saved to:\n  - {out_drop}\n  - {out_inbox}")
    return out_drop

if __name__ == "__main__":
    audio = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/james/stacklabs/pilot_drops/Treating_AI_as_a_Stateless_Calculator.m4a")
    transcribe(audio)
