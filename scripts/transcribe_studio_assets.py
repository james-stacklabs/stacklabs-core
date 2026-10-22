#!/usr/bin/env python3
# ACOUSTIC SILICON GATING GUARD (OCTOBER 2026):
# Raw audio upload to Google Gemini API is disabled to prevent tripping billing tier caps.
# Transcribe locally on Artemis (100.108.185.53) via scripts/artemis_whisper.py.

"""
transcribe_studio_assets.py - High-fidelity verbatim transcription of StackLabs VFS Studio media assets
Protects Clio APU by leveraging Google Gemini 3.8 Flash File API in cloud.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")
from google import genai

BASE_DIR = Path("/home/james/stacklabs/artifacts/studio_coprocessor_oct10")
AUDIO_DIR = BASE_DIR / "Audio"
VIDEO_DIR = BASE_DIR / "Videos"
TRANSCRIPT_DIR = BASE_DIR / "transcripts"
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "name": "02-Replacing Cloud APIs with Local Linux Files",
        "file": AUDIO_DIR / "02-Replacing Cloud APIs with Local Linux Files.mp3",
        "out": TRANSCRIPT_DIR / "02-Replacing_Cloud_APIs_with_Local_Linux_Files_transcript.md",
        "type": "audio"
    },
    {
        "name": "03-How Microsecond AI Fixes Server Crashes",
        "file": AUDIO_DIR / "03-How Microsecond AI Fixes Server Crashes.mp3",
        "out": TRANSCRIPT_DIR / "03-How_Microsecond_AI_Fixes_Server_Crashes_transcript.md",
        "type": "audio"
    },
    {
        "name": "01-How Virtual File Systems Fix Enterprise AI",
        "file": AUDIO_DIR / "01-How Virtual File Systems Fix Enterprise AI.mp3",
        "out": TRANSCRIPT_DIR / "01-How_Virtual_File_Systems_Fix_Enterprise_AI_transcript.md",
        "type": "audio"
    },
    {
        "name": "01-VFS Logic and the CMDB",
        "file": VIDEO_DIR / "01-VFS Logic and the CMDB.mp4",
        "out": TRANSCRIPT_DIR / "04-VFS_Logic_and_the_CMDB_video_transcript.md",
        "type": "video"
    }
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

        if item["out"].exists() and item["out"].stat().st_size > 100:
            print(f"Transcript already exists ({item['out'].stat().st_size} bytes). Skipping.")
            continue

        print(f"Uploading {item['file'].name} to Gemini File API...")
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
            f"Generate a comprehensive, verbatim, and professionally formatted transcription of this {item['type']} asset.\n"
            f"Asset Title: {item['name']}\n\n"
            f"Formatting Guidelines:\n"
            f"1. Include speaker labels (e.g. Speaker 1, Speaker 2, Host, Co-host) and exact timestamps [MM:SS] at turn changes.\n"
            f"2. Capture all technical terms accurately: POSIX VFS, CMDB, ServiceNow, CI (Configuration Item), "
            f"FastAPI, SQLite WAL, sys_id, JSON, tokens, 1,200ms TTR, sub-50us, pagecache, etc.\n"
            f"3. After the verbatim transcript, provide an 'Executive 3-Bullet Summary' highlighting the key architectural takeaway.\n"
        )

        print("Generating verbatim transcript via gemini-3.8-flash...")
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded, prompt]
        )

        transcript_text = response.text or ""
        header = f"# TRANSCRIPT: {item['name']}\n\n"
        header += f"- **Source File**: `{item['file'].name}`\n"
        header += f"- **Media Type**: {item['type'].upper()}\n"
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
