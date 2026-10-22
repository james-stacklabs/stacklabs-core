#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Retrograde Precog Stream Sniper
Extracts a synchronized high-res frame, MP4 clip, and audio from the /dev/shm ring buffer.
Ensures audio WAV is placed on the SSHFS-accessible NVMe path for Artemis CUDA transcription.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

KEY = "97c385957ccd4c120fa7d6823bd80f1b"
RING_DIR = Path("/dev/shm/espn2_ring")
PHOTO_DEST = Path("/home/james/stacklabs/pilot_drops/photos")
VIDEO_DEST = Path("/home/james/stacklabs/pilot_drops/video")
AUDIO_DEST = Path("/home/james/stacklabs/pilot_drops/audio")
TEMP_WORK = Path("/dev/shm/precog_sniper")


def snip_retrograde_window(
    num_segments: int = 45,
    offset_back: int = 1,
    tag: str = "latest",
    run_artemis: bool = True,
) -> dict[str, str]:
    TEMP_WORK.mkdir(parents=True, exist_ok=True)
    PHOTO_DEST.mkdir(parents=True, exist_ok=True)
    VIDEO_DEST.mkdir(parents=True, exist_ok=True)
    AUDIO_DEST.mkdir(parents=True, exist_ok=True)

    vid_files = sorted(RING_DIR.glob("vid_*.m4s"), key=lambda p: p.stat().st_mtime)
    aud_files = sorted(RING_DIR.glob("aud_*.m4s"), key=lambda p: p.stat().st_mtime)

    if not vid_files:
        raise RuntimeError("No segments in ring buffer. Is stream_ring_buffer.py running?")

    actual_segments = min(len(vid_files) - offset_back, num_segments)
    if actual_segments <= 0:
        actual_segments = min(len(vid_files), num_segments)
        offset_back = 0

    end_idx = len(vid_files) - offset_back
    start_idx = max(0, end_idx - actual_segments)

    selected_vids = vid_files[start_idx:end_idx]
    selected_auds = aud_files[start_idx:end_idx]

    vid_init = RING_DIR / "vid_init.mp4"
    aud_init = RING_DIR / "aud_init.mp4"

    raw_vid = TEMP_WORK / f"raw_vid_{tag}.mp4"
    raw_aud = TEMP_WORK / f"raw_aud_{tag}.mp4"

    with open(raw_vid, "wb") as f_out:
        f_out.write(vid_init.read_bytes())
        for v in selected_vids:
            f_out.write(v.read_bytes())

    with open(raw_aud, "wb") as f_out:
        f_out.write(aud_init.read_bytes())
        for a in selected_auds:
            f_out.write(a.read_bytes())

    dec_vid = TEMP_WORK / f"dec_vid_{tag}.mp4"
    dec_aud = TEMP_WORK / f"dec_aud_{tag}.mp4"

    subprocess.run(
        ["ffmpeg", "-y", "-decryption_key", KEY, "-i", str(raw_vid), "-c", "copy", str(dec_vid)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    subprocess.run(
        ["ffmpeg", "-y", "-decryption_key", KEY, "-i", str(raw_aud), "-c", "copy", str(dec_aud)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    out_mp4 = VIDEO_DEST / f"live_snip_{tag}.mp4"
    out_jpg = PHOTO_DEST / f"live_snip_{tag}.jpg"

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(dec_vid), "-i", str(dec_aud), "-c", "copy", str(out_mp4)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(out_mp4), "-vframes", "1", "-update", "1", str(out_jpg)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Audio placed on NVMe for Artemis SSHFS access
    audio_wav = AUDIO_DEST / f"snip_{tag}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(dec_aud), "-ar", "16000", "-ac", "1", str(audio_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    transcript_text = ""
    transcript_file = AUDIO_DEST / f"snip_{tag}_transcript.md"
    if run_artemis and audio_wav.exists():
        dispatcher = Path("/home/james/stacklabs/scripts/transcribe_on_artemis.py")
        if dispatcher.exists():
            cmd = [
                "/home/james/stacklabs/.venv/bin/python3",
                str(dispatcher),
                str(audio_wav),
                "--output",
                str(transcript_file),
                "--model",
                "base.en",
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                if transcript_file.exists():
                    transcript_text = transcript_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    return {
        "video": str(out_mp4),
        "photo": str(out_jpg),
        "audio": str(audio_wav),
        "transcript": transcript_text,
        "segments": actual_segments,
        "duration": actual_segments * 2.048,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="StackLabs Precog Stream Sniper")
    parser.add_argument("--segments", "-s", type=int, default=45, help="Number of 2s segments (default: 45 = ~90s)")
    parser.add_argument("--offset", "-o", type=int, default=1, help="Segments back from latest (default: 1)")
    parser.add_argument("--tag", "-t", default="latest", help="Output filename tag")
    parser.add_argument("--no-artemis", action="store_true", help="Skip remote Artemis transcription")
    args = parser.parse_args()

    t0 = time.time()
    res = snip_retrograde_window(
        num_segments=args.segments,
        offset_back=args.offset,
        tag=args.tag,
        run_artemis=not args.no_artemis,
    )
    elapsed = time.time() - t0

    print("=" * 70, flush=True)
    print(f"✅ PRECOG SNIP COMPLETE ({elapsed:.2f}s)", flush=True)
    print(f"⏱️ Duration:   {res['duration']:.1f}s ({res['segments']} segments)", flush=True)
    print(f"📸 Snapshot:   {res['photo']}", flush=True)
    print(f"🎥 Video Clip: {res['video']}", flush=True)
    print(f"🔊 Audio WAV:  {res['audio']}", flush=True)
    print(f"📝 Transcript: {res['transcript'] or '(No speech detected or Artemis offline)'}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
