#!/home/james/stacklabs/.venv/bin/python3
"""
transcribe_current_studio_drop.py - Transcribe active NotebookLM Studio audio files via Gemini 3.8 Flash File API
Outputs transcripts directly into pilot_drops/sprint_studio_20261013/transcripts/
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")
from google import genai

BASE_DIR = Path("/home/james/stacklabs/pilot_drops/sprint_studio_20261013")
AUDIO_DIR = BASE_DIR / "Audio"
TRANSCRIPT_DIR = BASE_DIR / "transcripts"
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "name": "02-Collapsing AI Latency with Local Memory",
        "file": AUDIO_DIR / "02-Collapsing AI Latency with Local Memory.mp3",
        "out": TRANSCRIPT_DIR / "02-Collapsing_AI_Latency_with_Local_Memory_transcript.md",
    },
    {
        "name": "03-Why LLMs Are Execution Engines Not Databases",
        "file": AUDIO_DIR / "03-Why LLMs Are Execution Engines Not Databases.mp3",
        "out": TRANSCRIPT_DIR / "03-Why_LLMs_Are_Execution_Engines_Not_Databases_transcript.md",
    },
    {
        "name": "01-Moving AI Search into Kernel Memory",
        "file": AUDIO_DIR / "01-Moving AI Search into Kernel Memory.mp3",
        "out": TRANSCRIPT_DIR / "01-Moving_AI_Search_into_Kernel_Memory_transcript.md",
    },
]

def transcribe_all():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    for item in TARGETS:
        print(f"\n==========================================")
        print(f"Target: {item['name']}")
        print(f"File: {item['file']}")
        
        if not item["file"].exists():
            print(f"ERROR: File not found: {item['file']}")
            continue

        if item["out"].exists() and item["out"].stat().st_size > 200:
            print(f"Transcript already exists ({item['out'].stat().st_size} bytes). Skipping.")
            continue

        print(f"Uploading {item['file'].name} ({item['file'].stat().st_size / (1024*1024):.2f} MB) to Gemini File API...")
        uploaded = client.files.upload(file=str(item["file"]))
        print(f"Uploaded as {uploaded.name}. Polling status...")

        while uploaded.state.name == "PROCESSING":
            time.sleep(3)
            uploaded = client.files.get(name=uploaded.name)
            print(f"State: {uploaded.state.name}")

        if uploaded.state.name != "ACTIVE":
            print(f"Upload failed or in bad state: {uploaded.state.name}")
            continue

        prompt = (
            f"You are the official transcription engine for StackLabs LLC.\n"
            f"Generate a comprehensive, verbatim, and professionally formatted transcription of this audio asset from Google NotebookLM Studio.\n"
            f"Asset Title: {item['name']}\n\n"
            f"Formatting Guidelines:\n"
            f"1. Include speaker labels (e.g. Host 1 [Male], Host 2 [Female]) and exact timestamps [MM:SS] at turn changes.\n"
            f"2. Capture all technical terms accurately: POSIX VFS, CMDB, ServiceNow, eBPF, inode, ALU, pagecache, "
            f"Don R. Swanson literature-based discovery, latency boundary collapse, Peter Magnusson, SQLite WAL, Datadog, Neo4j, etc.\n"
            f"3. Strictly enforce clean systems nomenclature: do NOT introduce 'bare metal' or 'sovereign'. Use 'dedicated Linux host' or 'local host memory'.\n"
            f"4. After the verbatim transcript, provide an 'Executive 3-Bullet Takeaway' highlighting the key architectural insight.\n"
        )

        print("Generating verbatim transcript via gemini-3.8-flash in cloud...")
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded, prompt]
        )

        transcript_text = response.text or ""
        header = f"# TRANSCRIPT: {item['name']}\n\n"
        header += f"- **Source File**: `{item['file'].name}`\n"
        header += f"- **Media Type**: AUDIO (NotebookLM Deep Dive)\n"
        header += f"- **Engine**: Google Gemini 3.8 Flash (Cloud Offload - Zero Clio APU Load)\n"
        header += f"- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S EDT')}\n\n---\n\n"

        full_content = header + transcript_text
        with open(item["out"], "w", encoding="utf-8") as f:
            f.write(full_content)

        print(f"Saved transcript to {item['out']} ({len(full_content)} chars).")

        # Cleanup remote file
        try:
            client.files.delete(name=uploaded.name)
            print(f"Cleaned up remote file {uploaded.name}.")
        except Exception as e:
            print(f"Warning: could not delete remote file: {e}")

if __name__ == "__main__":
    transcribe_all()
