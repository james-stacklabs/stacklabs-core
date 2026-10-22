#!/usr/bin/env python3
"""
hot_takes_audio_merge.py
========================
Takes a Flow-generated video (muted or bad audio) and overlays it
with TTS-generated audio from the hot take script.

Usage:
  python3 hot_takes_audio_merge.py --video path/to/video.mp4 --script "your script text" [--voice en-US-GuyNeural] [--rate +10%] [--output output.mp4]

Free pipeline — edge-tts (Microsoft neural voices, no API key) + ffmpeg.
Upgrade to ElevenLabs later when revenue allows.
"""

import asyncio
import argparse
import subprocess
import tempfile
import os
import sys

# ── Voice presets for each persona ───────────────────────────────────────────
# Override per persona as needed. These are edge-tts voice names.
PERSONA_VOICES = {
    "barf":    {"voice": "en-US-ChristopherNeural", "rate": "+15%", "pitch": "-5Hz"},
    "dot":     {"voice": "en-US-AriaNeural",        "rate": "+5%",  "pitch": "+0Hz"},
    "default": {"voice": "en-US-GuyNeural",          "rate": "+10%", "pitch": "+0Hz"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_duration(path: str) -> float:
    """Get media file duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


async def generate_tts(text: str, voice: str, rate: str, pitch: str, output_path: str):
    """Generate TTS audio using edge-tts (free, no API key)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def adjust_audio_speed(input_audio: str, target_duration: float, output_audio: str):
    """
    Stretch or compress audio to match target duration using ffmpeg atempo.
    atempo range is 0.5-2.0; chain filters for values outside that range.
    """
    audio_duration = get_duration(input_audio)
    ratio = audio_duration / target_duration

    print(f"  Audio: {audio_duration:.2f}s | Video: {target_duration:.2f}s | Ratio: {ratio:.3f}x")

    # Build chained atempo filters if ratio is outside 0.5-2.0
    filters = []
    r = ratio
    while r > 2.0:
        filters.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        filters.append("atempo=0.5")
        r *= 2.0
    filters.append(f"atempo={r:.4f}")
    filter_str = ",".join(filters)

    subprocess.run([
        "ffmpeg", "-y", "-i", input_audio,
        "-filter:a", filter_str,
        output_audio
    ], check=True, capture_output=True)


def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """Replace video's audio track with our TTS audio. Keeps video stream untouched."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",        # don't re-encode video
        "-c:a", "aac",
        "-map", "0:v:0",       # video from source
        "-map", "1:a:0",       # audio from TTS
        "-shortest",
        output_path
    ], check=True, capture_output=True)


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(args):
    video_path = args.video
    script_text = args.script
    persona = args.persona.lower() if args.persona else "default"

    # Resolve voice settings
    preset = PERSONA_VOICES.get(persona, PERSONA_VOICES["default"])
    voice = args.voice or preset["voice"]
    rate  = args.rate  or preset["rate"]
    pitch = args.pitch or preset["pitch"]

    # Resolve output path
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_dubbed.mp4"

    print(f"\n🎙️  Hot Takes Audio Merge")
    print(f"   Video:   {video_path}")
    print(f"   Persona: {persona} → voice={voice}, rate={rate}, pitch={pitch}")
    print(f"   Output:  {output_path}\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_audio  = os.path.join(tmpdir, "tts_raw.mp3")
        adj_audio  = os.path.join(tmpdir, "tts_adjusted.mp3")

        # Step 1 — Get video duration
        video_duration = get_duration(video_path)
        print(f"📹 Video duration: {video_duration:.2f}s")

        # Step 2 — Generate TTS
        print(f"🗣️  Generating TTS audio...")
        await generate_tts(script_text, voice, rate, pitch, raw_audio)
        raw_duration = get_duration(raw_audio)
        print(f"✅ TTS generated: {raw_duration:.2f}s")

        # Step 3 — Adjust audio speed to match video
        print(f"⚙️  Adjusting audio speed to fit video...")
        adjust_audio_speed(raw_audio, video_duration, adj_audio)

        # Step 4 — Merge
        print(f"🎬 Merging audio + video...")
        merge_audio_video(video_path, adj_audio, output_path)

    print(f"\n✅ Done! Dubbed video saved to:\n   {output_path}\n")


def main():
    parser = argparse.ArgumentParser(description="Hot Takes Audio Merge — free TTS + ffmpeg pipeline")
    parser.add_argument("--video",   required=True, help="Path to Flow-generated video")
    parser.add_argument("--script",  required=True, help="The hot take script text to voice")
    parser.add_argument("--persona", default="default", help="Persona name (barf, dot, etc.) for voice preset")
    parser.add_argument("--voice",   default=None,  help="Override edge-tts voice name")
    parser.add_argument("--rate",    default=None,  help="Override speech rate e.g. +15%%")
    parser.add_argument("--pitch",   default=None,  help="Override pitch e.g. -5Hz")
    parser.add_argument("--output",  default=None,  help="Output file path")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
