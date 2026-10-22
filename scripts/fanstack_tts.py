#!/usr/bin/env python3
"""
fanstack_tts.py — Gemini TTS audio generator for Flowmercial scripts

Generates a single clean audio track from a Flowmercial MD script using
Gemini TTS. No hallucinations, no slurring, no duplicate sections.

Usage:
  python fanstack_tts.py <script.md> [voice_name] [output.wav]

Voice options (pick what fits the persona):
  Charon   — Confident, authoritative (good for Barf's hot take energy)
  Puck     — Upbeat, animated
  Fenrir   — Gravelly, intense
  Orus     — Deep, dramatic
  Zephyr   — Bright, fast-paced
  (Full list: https://ai.google.dev/gemini-api/docs/speech-generation#voices)

Examples:
  python fanstack_tts.py my_script.md Charon
  python fanstack_tts.py hot_take.md Puck /tmp/barf_audio.wav
"""

import os, re, wave, sys, subprocess
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
SOVEREIGN_ROOT = Path('/home/james/stacklabs')
ENV_FILE       = SOVEREIGN_ROOT / '.env'
MODEL          = 'gemini-1.5-flash-preview-tts'
SAMPLE_RATE    = 24000
OUTPUT_DIR     = SOVEREIGN_ROOT / 'media_vault' / '02_Projects'

# ── Helpers ────────────────────────────────────────────────────────────────
def load_api_key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith('GEMINI_API_KEY='):
            return line.split('=', 1)[1].strip()
    return os.environ.get('GEMINI_API_KEY', '')

def save_wav(path: str, pcm: bytes):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)

def parse_script(md_path: str) -> list[str]:
    """
    Extract dialogue lines from a Flowmercial MD script.
    Handles both:
      - ### PROMPT N / ### BASE INTRO sections
      - Plain numbered lists
    Returns list of spoken lines in order.
    """
    text = Path(md_path).read_text()
    lines = []

    for block in re.split(r'\n---+\n', text):
        block = block.strip()
        if not block:
            continue
        # Skip the file header note (italicised lines starting with *)
        if block.startswith('*') or block.startswith('#!'):
            continue
        # Grab the content line(s) under a ### heading
        match = re.search(r'###[^\n]*\n(.+?)(?:\n\n|\Z)', block, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # Skip pure heading blocks with no real content
            if content and not content.startswith('*'):
                lines.append(content)

    return lines

def build_prompt(lines: list[str], persona_note: str) -> str:
    """
    Build the full TTS prompt with persona direction + all script lines.
    Sending everything in one call = consistent voice, no seams, no stitching.
    """
    script = '\n'.join(lines)
    return f"{persona_note}\n\n{script}"

# ── Main ───────────────────────────────────────────────────────────────────
def generate(md_path: str, voice: str = 'Charon', output_wav: str = None):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("📦  google-genai not found — installing...")
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'google-genai', '-q'],
            check=True
        )
        from google import genai
        from google.genai import types

    api_key = load_api_key()
    if not api_key:
        print("❌  No GEMINI_API_KEY found in .env")
        sys.exit(1)

    # Parse script
    lines = parse_script(md_path)
    if not lines:
        print(f"❌  No script lines found in {md_path}")
        sys.exit(1)

    print(f"📋  Parsed {len(lines)} lines from {Path(md_path).name}")
    print(f"🎙️  Voice: {voice}  |  Model: {MODEL}")
    print(f"📝  First line: {lines[0][:70]}...")

    # Barf persona direction — controls delivery style
    persona_note = (
        "[excitedly, fast-talking New York sports fan, passionate and slightly unhinged] "
        "Deliver the following hot take with building energy. "
        "Start confident, get louder and more intense as it goes. "
        "Natural pauses between thoughts:"
    )

    prompt = build_prompt(lines, persona_note)

    # Build output path
    if not output_wav:
        stem = Path(md_path).stem.replace(' ', '_')[:40]
        output_wav = str(OUTPUT_DIR / f"tts_{stem}_{voice.lower()}.wav")

    output_mp3 = output_wav.replace('.wav', '.mp3')

    # Call Gemini TTS
    print(f"\n⏳  Generating audio via Gemini TTS...")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                )
            ),
        )
    )

    pcm_data = response.candidates[0].content.parts[0].inline_data.data
    duration  = len(pcm_data) / (SAMPLE_RATE * 2)

    # Save WAV
    save_wav(output_wav, pcm_data)
    print(f"✅  WAV saved:  {output_wav}  ({duration:.1f}s)")

    # Convert to MP3 (smaller, easier to handle)
    result = subprocess.run(
        ['ffmpeg', '-i', output_wav, '-q:a', '2', '-y', output_mp3],
        capture_output=True
    )
    if result.returncode == 0:
        mp3_size = Path(output_mp3).stat().st_size // 1024
        print(f"✅  MP3 saved:  {output_mp3}  ({mp3_size}KB)")
    else:
        print("⚠️  ffmpeg MP3 conversion failed — WAV still available")

    print(f"\n🎬  To overlay on a video:")
    print(f"    ffmpeg -i YOUR_VIDEO.mp4 -i {output_mp3} \\")
    print(f"           -map 0:v -map 1:a -c:v copy -shortest output_final.mp4")

    return output_wav, output_mp3


if __name__ == '__main__':
    md   = sys.argv[1] if len(sys.argv) > 1 else str(
        SOVEREIGN_ROOT / 'media_vault/03_Assets/Harvested_Artifacts/55c406d9_wrexham_hot_take.md'
    )
    voice  = sys.argv[2] if len(sys.argv) > 2 else 'Charon'
    output = sys.argv[3] if len(sys.argv) > 3 else None

    generate(md, voice, output)
