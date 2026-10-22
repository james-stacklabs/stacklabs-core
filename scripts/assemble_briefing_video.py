#!/usr/bin/env python3
"""
StackLabs Media Engine: Architectural Briefing Video Assembly Pipeline
Ticket: WO0010190-STACKLABS-BRIEFING-VIDEO-ASSEMBLY-AND-GATEWAY-EMBED
Assignee: Clio (Forge Master)

Assembles:
  - Part 1: A-Roll Intro (James speaking) - 10.0s (240 frames @ 24fps)
  - Part 2a: B-Roll Visual 1 (Grid Energy Ceiling Chart) synced to 1st half of clip_2 audio (5.375s / 129 frames)
  - Part 2b: B-Roll Visual 2 (Hardware Silicon Schematic) synced to 2nd half of clip_2 audio (4.625s / 111 frames)
  - Part 3: B-Roll Visual 3 (Latency & Compliance Benchmark) synced to clip_3 audio (10.0s / 240 frames)
  - Part 4: A-Roll Outro (James speaking) - 10.0s (240 frames @ 24fps)

Outputs:
  - /home/james/sovereign_inbox/pilot_drops/stacklabs_model_s_architecture_briefing.mp4
  - /home/james/stacklabs/16_StackLabsLLC/public/stacklabs_model_s_architecture_briefing.mp4
  - Poster frames: model_s_briefing_poster.jpg in both locations
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

# Source assets
PILOT_DROPS_DIR = Path("/home/james/sovereign_inbox/pilot_drops")
PUBLIC_WEB_DIR = Path("/home/james/stacklabs/16_StackLabsLLC/public")
BRAIN_ASSET_DIR = Path("/home/james/.gemini/antigravity-ide/brain/741d1c15-9e4f-4fff-afee-8fb0d478f542")

INTRO_SRC = PILOT_DROPS_DIR / "intro.mp4"
CLIP2_SRC = PILOT_DROPS_DIR / "clip_2.mp4"
CLIP3_SRC = PILOT_DROPS_DIR / "clip_3.mp4"
OUTRO_SRC = PILOT_DROPS_DIR / "outro.mp4"

BROLL1_SRC = BRAIN_ASSET_DIR / "grid_energy_ceiling_chart_1789756134263.jpg"
BROLL2_SRC = BRAIN_ASSET_DIR / "hardware_silicon_schematic_1789756147459.jpg"
BROLL3_SRC = BRAIN_ASSET_DIR / "latency_compliance_benchmark_1789756160649.jpg"

MASTER_PILOT_OUTPUT = PILOT_DROPS_DIR / "stacklabs_model_s_architecture_briefing.mp4"
MASTER_PUBLIC_OUTPUT = PUBLIC_WEB_DIR / "stacklabs_model_s_architecture_briefing.mp4"

POSTER_PILOT_OUTPUT = PILOT_DROPS_DIR / "model_s_briefing_poster.jpg"
POSTER_PUBLIC_OUTPUT = PUBLIC_WEB_DIR / "model_s_briefing_poster.jpg"


def run_ffmpeg(cmd, description):
    print(f"[+] {description}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[-] FFmpeg error in '{description}':\n{res.stderr[-1000:]}")
        raise RuntimeError(f"FFmpeg command failed with code {res.returncode}")
    return res


def probe_file(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-count_frames",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,nb_read_frames,duration",
        "-of", "json",
        str(file_path)
    ]
    out = subprocess.check_output(cmd).decode("utf-8")
    return json.loads(out)


def build_briefing_video():
    print("=================================================================")
    print("🚀 STACKLABS ARCHITECTURAL BRIEFING: MASTER VIDEO ASSEMBLY")
    print("=================================================================")

    # Verify input assets
    for path, name in [
        (INTRO_SRC, "Intro A-Roll"),
        (CLIP2_SRC, "Clip 2"),
        (CLIP3_SRC, "Clip 3"),
        (OUTRO_SRC, "Outro A-Roll"),
        (BROLL1_SRC, "B-Roll 1 (Grid Energy Ceiling)"),
        (BROLL2_SRC, "B-Roll 2 (Hardware Silicon Schematic)"),
        (BROLL3_SRC, "B-Roll 3 (Latency & Compliance Benchmark)")
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required asset: {name} at {path}")
        print(f"[✓] Staged asset verified: {name} -> {path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="stacklabs_briefing_"))
    print(f"[+] Working directory: {temp_dir}")

    try:
        # 1. Extract Poster Frame from intro.mp4 (James looking straight at camera, sharp pose)
        poster_tmp = temp_dir / "poster.jpg"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-ss", "1.8",
            "-i", str(INTRO_SRC),
            "-vframes", "1",
            "-q:v", "2",
            str(poster_tmp)
        ], "Extracting high-resolution poster frame from Intro")

        # 2. Render Part 1 (Intro A-Roll normalized with clean 20ms audio anti-pop microfade)
        part1_mp4 = temp_dir / "part1_intro.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(INTRO_SRC),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-af", "afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02",
            "-r", "24",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(part1_mp4)
        ], "Normalizing Part 1 (Intro A-Roll)")

        # 3. Render Part 2a: Grid Energy Ceiling Chart (Ken Burns slow push-in, 129 frames = 5.375s)
        part2a_video = temp_dir / "part2a_video.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(BROLL1_SRC),
            "-vf", "scale=2752:1536,zoompan=z='min(zoom+0.0005,1.065)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=129:s=1280x720:fps=24",
            "-frames:v", "129",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            str(part2a_video)
        ], "Rendering Part 2a (Grid Energy Ceiling Chart Ken Burns)")

        # 4. Render Part 2b: Hardware Silicon Schematic (Ken Burns slow push-in, 111 frames = 4.625s)
        part2b_video = temp_dir / "part2b_video.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(BROLL2_SRC),
            "-vf", "scale=2752:1536,zoompan=z='min(zoom+0.0005,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=111:s=1280x720:fps=24",
            "-frames:v", "111",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            str(part2b_video)
        ], "Rendering Part 2b (Hardware Silicon Schematic Ken Burns)")

        # 5. Composite Part 2: Concatenate Part 2a + 2b video with Clip 2 continuous voiceover audio
        part2_mp4 = temp_dir / "part2_broll.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(part2a_video),
            "-i", str(part2b_video),
            "-i", str(CLIP2_SRC),
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a]afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-r", "24",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(part2_mp4)
        ], "Compositing Part 2 (B-Roll Dual Visuals + Clip 2 Continuous Voiceover)")

        # 6. Render Part 3: Latency & Compliance Benchmark (Ken Burns slow push-in, 240 frames = 10.0s) with Clip 3 voiceover
        part3_mp4 = temp_dir / "part3_broll.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(BROLL3_SRC),
            "-i", str(CLIP3_SRC),
            "-filter_complex",
            "[0:v]scale=2752:1536,zoompan=z='min(zoom+0.00028,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s=1280x720:fps=24[v];[1:a]afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-frames:v", "240",
            "-r", "24",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(part3_mp4)
        ], "Compositing Part 3 (Latency & Compliance Benchmark + Clip 3 Voiceover)")

        # 7. Render Part 4 (Outro A-Roll normalized with clean 20ms audio anti-pop microfade)
        part4_mp4 = temp_dir / "part4_outro.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(OUTRO_SRC),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-af", "afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02",
            "-r", "24",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(part4_mp4)
        ], "Normalizing Part 4 (Outro A-Roll)")

        # 8. Master Concatenation: Part 1 + Part 2 + Part 3 + Part 4
        master_tmp = temp_dir / "stacklabs_model_s_architecture_briefing.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(part1_mp4),
            "-i", str(part2_mp4),
            "-i", str(part3_mp4),
            "-i", str(part4_mp4),
            "-filter_complex", "[0:v][0:a][1:v][1:a][2:v][2:a][3:v][3:a]concat=n=4:v=1:a=1[v][a]",
            "-map", "[v]",
            "-map", "[a]",
            "-r", "24",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
            str(master_tmp)
        ], "Master Concatenation (All 4 Chapters + Faststart Metadata)")

        # 9. Copy to Destination Locations
        print("[+] Staging master briefing video and poster...")
        PUBLIC_WEB_DIR.mkdir(parents=True, exist_ok=True)
        PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(str(master_tmp), str(MASTER_PILOT_OUTPUT))
        shutil.copyfile(str(master_tmp), str(MASTER_PUBLIC_OUTPUT))
        shutil.copyfile(str(poster_tmp), str(POSTER_PILOT_OUTPUT))
        shutil.copyfile(str(poster_tmp), str(POSTER_PUBLIC_OUTPUT))

        print(f"[✓] Saved master video to: {MASTER_PILOT_OUTPUT} ({MASTER_PILOT_OUTPUT.stat().st_size} bytes)")
        print(f"[✓] Saved master video to: {MASTER_PUBLIC_OUTPUT} ({MASTER_PUBLIC_OUTPUT.stat().st_size} bytes)")
        print(f"[✓] Saved poster frame to: {POSTER_PILOT_OUTPUT}")
        print(f"[✓] Saved poster frame to: {POSTER_PUBLIC_OUTPUT}")

        # 10. Run ffprobe Integrity Validation
        info = probe_file(MASTER_PUBLIC_OUTPUT)
        v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        a_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")

        print("\n=================================================================")
        print("🔍 MASTER VIDEO INTEGRITY AUDIT")
        print("=================================================================")
        print(f"Format Duration: {info['format']['duration']}s")
        print(f"Format Size:     {int(info['format']['size']) / 1024 / 1024:.2f} MB")
        print(f"Video Codec:     {v_stream['codec_name']} ({v_stream['width']}x{v_stream['height']} @ {v_stream['r_frame_rate']})")
        print(f"Video Frames:    {v_stream['nb_read_frames']} (Expected: 960)")
        print(f"Audio Codec:     {a_stream['codec_name']} ({a_stream['r_frame_rate']} / {a_stream.get('sample_rate', 48000)} Hz)")
        print("=================================================================\n")

        assert int(v_stream['nb_read_frames']) == 960, f"Expected 960 video frames, got {v_stream['nb_read_frames']}"
        assert v_stream['width'] == 1280 and v_stream['height'] == 720, "Expected 1280x720 resolution"

        return {
            "master_pilot": str(MASTER_PILOT_OUTPUT),
            "master_public": str(MASTER_PUBLIC_OUTPUT),
            "poster_pilot": str(POSTER_PILOT_OUTPUT),
            "poster_public": str(POSTER_PUBLIC_OUTPUT),
            "duration": float(info['format']['duration']),
            "video_frames": int(v_stream['nb_read_frames']),
            "file_size": int(info['format']['size'])
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    build_briefing_video()
