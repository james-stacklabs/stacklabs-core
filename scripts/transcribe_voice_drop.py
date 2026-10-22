#!/usr/bin/env python3
"""
Autonomous Audio Transcription Hot-Path for Voice Drops
Path: /home/james/stacklabs/scripts/transcribe_voice_drop.py
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dotenv
dotenv.load_dotenv(REPO_ROOT / ".env")


def transcribe_audio_file(audio_path: Path) -> str:
    """Transcribe an audio file using Artemis CUDA first, falling back to Gemini Flash."""
    transcript = ""
    
    # 1. Primary: Artemis Pascal CUDA Dispatcher
    dispatcher = REPO_ROOT / "scripts" / "transcribe_on_artemis.py"
    if dispatcher.exists():
        try:
            cmd = ["/home/james/stacklabs/.venv/bin/python3", str(dispatcher), str(audio_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                expected_md = audio_path.parent / f"{audio_path.stem}_transcript.md"
                if expected_md.exists() and expected_md.stat().st_size > 10:
                    transcript = expected_md.read_text(encoding="utf-8").strip()
                    # Also write .txt for paired compatibility
                    audio_path.with_suffix(".txt").write_text(transcript, encoding="utf-8")
                    print(f"Transcribed via Artemis CUDA: {len(transcript)} chars")
        except Exception as e:
            print(f"Artemis dispatch error: {e}; falling back to Cloud Gemini")

    # 2. Fallback: Cloud Gemini
    if not transcript:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing.")

        from google import genai
        client = genai.Client(api_key=api_key)

        uploaded = client.files.upload(file=str(audio_path))
        prompt = (
            "Provide a clean, full, verbatim transcript of this audio memo. "
            "Preserve exact terminology, numbers, analogies, and institutional concepts. "
            "Format as clean markdown with timestamps if multiple distinct topics occur."
        )

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded, prompt]
        )
        transcript = response.text.strip()
        transcript_path = audio_path.with_suffix(".txt")
        transcript_path.write_text(transcript, encoding="utf-8")

    # Autonomous pipeline: invoke strategic dossier synthesis
    try:
        from scripts.voice_drop_syndicate_builder import build_strategic_dossier
        parts = audio_path.stem.split("_")
        sender = parts[2] if len(parts) >= 3 else "pawel"
        channel = sender if sender in ["pawel", "barb"] else "pawel"
        build_strategic_dossier(channel, sender, transcript, audio_path.name)
    except Exception as e:
        print(f"Warning: Failed to auto-generate syndicate dossier: {e}")

    # Autonomous pipeline: invoke voice query normalizer
    try:
        from scripts.voice_query_normalizer import normalize_voice_transcript
        normalize_voice_transcript(transcript, source_tag=f"voice_drop_{audio_path.stem}")
    except Exception as e:
        print(f"Warning: Failed to normalize voice query: {e}")

    return transcript


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: transcribe_voice_drop.py <path_to_audio>")
        sys.exit(1)

    target_audio = Path(sys.argv[1])
    if not target_audio.exists():
        print(f"Error: File not found: {target_audio}")
        sys.exit(1)

    print(f"Transcribing {target_audio.name}...")
    res = transcribe_audio_file(target_audio)
    print("Transcription complete:")
    print(res[:300] + "..." if len(res) > 300 else res)
