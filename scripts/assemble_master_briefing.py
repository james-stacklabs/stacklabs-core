#!/usr/bin/env python3
"""
StackLabs Media Engine: 5-Act Master Architectural Briefing Video Assembly
Work Order: WO0010191-ASSEMBLE-5-ACT-MASTER-BRIEFING-VIDEO
Assignee: Clio (Forge Master)

5-Act Sequence:
  - ACT I (0:00 - 0:10): The Hook (A-Roll: James on camera) - intro.mp4 (240 frames @ 24fps)
  - ACT II (0:10 - 0:20): The Grid Ceiling (B-Roll Graphic with Voiceover)
      Audio: Man_speaking_about_data_centers_20260918150841.mp4
      Visual: grid_energy_ceiling_chart.jpg (Ken Burns slow zoom, 240 frames @ 24fps)
  - ACT III (0:20 - 0:30): The Model-S Silicon (B-Roll Graphic with Voiceover)
      Audio: Man_speaking_about_neural_silicon_20260918150841.mp4
      Visual: hardware_silicon_schematic.jpg (subtle 10s pan across NPU and heatsink, 240 frames @ 24fps)
  - ACT IV (0:30 - 0:40): Latency & Data Sovereignty (B-Roll Graphic with Voiceover)
      Audio: Man_speaking_about_data_latency_20260918150841.mp4
      Visual: latency_compliance_benchmark.jpg (slow zoom toward 14ms gauge, 240 frames @ 24fps)
  - ACT V (0:40 - 0:50): The Outro Punchline (A-Roll: James on camera) - outro.mp4 (240 frames @ 24fps)

Outputs:
  - /home/james/sovereign_inbox/pilot_drops/stacklabs_model_s_architecture_briefing.mp4
  - /home/james/stacklabs/16_StackLabsLLC/public/stacklabs_model_s_architecture_briefing.mp4
  - /home/james/stacklabs/16_StackLabsLLC/public/model_s_briefing_poster.jpg
  - /home/james/sovereign_inbox/pilot_drops/model_s_briefing_poster.jpg
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

# Paths
PILOT_DROPS_DIR = Path("/home/james/sovereign_inbox/pilot_drops")
TAKES_DIR = PILOT_DROPS_DIR / "james_video_takes"
PUBLIC_WEB_DIR = Path("/home/james/stacklabs/16_StackLabsLLC/public")
BRAIN_ASSET_DIR = Path("/home/james/.gemini/antigravity-ide/brain/741d1c15-9e4f-4fff-afee-8fb0d478f542")

ACT1_SRC = PILOT_DROPS_DIR / "intro.mp4"
ACT2_AUDIO_SRC = TAKES_DIR / "Man_speaking_about_data_centers_20260918150841.mp4"
ACT2_IMG_SRC = PILOT_DROPS_DIR / "grid_energy_ceiling_chart.jpg"
ACT3_AUDIO_SRC = TAKES_DIR / "Man_speaking_about_neural_silicon_20260918150841.mp4"
ACT3_IMG_SRC = PILOT_DROPS_DIR / "hardware_silicon_schematic.jpg"
ACT4_AUDIO_SRC = TAKES_DIR / "Man_speaking_about_data_latency_20260918150841.mp4"
ACT4_IMG_SRC = PILOT_DROPS_DIR / "latency_compliance_benchmark.jpg"
ACT5_SRC = PILOT_DROPS_DIR / "outro.mp4"

# Fallback paths for images if not found in pilot_drops
if not ACT2_IMG_SRC.exists() and (BRAIN_ASSET_DIR / "grid_energy_ceiling_chart_1789756134263.jpg").exists():
    ACT2_IMG_SRC = BRAIN_ASSET_DIR / "grid_energy_ceiling_chart_1789756134263.jpg"

if not ACT3_IMG_SRC.exists() and (BRAIN_ASSET_DIR / "hardware_silicon_schematic_1789756147459.jpg").exists():
    ACT3_IMG_SRC = BRAIN_ASSET_DIR / "hardware_silicon_schematic_1789756147459.jpg"

if not ACT4_IMG_SRC.exists() and (BRAIN_ASSET_DIR / "latency_compliance_benchmark_1789756160649.jpg").exists():
    ACT4_IMG_SRC = BRAIN_ASSET_DIR / "latency_compliance_benchmark_1789756160649.jpg"

MASTER_PILOT_OUTPUT = PILOT_DROPS_DIR / "stacklabs_model_s_architecture_briefing.mp4"
MASTER_PUBLIC_OUTPUT = PUBLIC_WEB_DIR / "stacklabs_model_s_architecture_briefing.mp4"
POSTER_PILOT_OUTPUT = PILOT_DROPS_DIR / "model_s_briefing_poster.jpg"
POSTER_PUBLIC_OUTPUT = PUBLIC_WEB_DIR / "model_s_briefing_poster.jpg"


def run_ffmpeg(cmd, description):
    print(f"[+] {description}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[-] FFmpeg error in '{description}':\n{res.stderr[-1500:]}")
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


def assemble_master_briefing():
    print("=================================================================")
    print("🎬 STACKLABS 5-ACT MASTER ARCHITECTURAL BRIEFING ASSEMBLY")
    print("   Ticket: WO0010191-ASSEMBLE-5-ACT-MASTER-BRIEFING-VIDEO")
    print("   Assignee: Clio (Forge Master)")
    print("=================================================================")

    # 0. Asset Verification
    required_assets = [
        (ACT1_SRC, "ACT I: Intro A-Roll Video/Audio"),
        (ACT2_AUDIO_SRC, "ACT II: Grid Ceiling Voiceover Take"),
        (ACT2_IMG_SRC, "ACT II: Grid Energy Ceiling Chart Graphic"),
        (ACT3_AUDIO_SRC, "ACT III: Neural Silicon Voiceover Take"),
        (ACT3_IMG_SRC, "ACT III: Hardware Silicon Schematic Graphic"),
        (ACT4_AUDIO_SRC, "ACT IV: Data Latency Voiceover Take"),
        (ACT4_IMG_SRC, "ACT IV: Latency & Compliance Benchmark Graphic"),
        (ACT5_SRC, "ACT V: Outro A-Roll Video/Audio")
    ]

    for path, desc in required_assets:
        if not path.exists():
            raise FileNotFoundError(f"Missing required asset: {desc} at {path}")
        print(f"[✓] Asset verified: {desc} -> {path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="stacklabs_master_5act_"))
    print(f"[+] Isolated workspace: {temp_dir}")

    try:
        # 1. Export first frame of intro.mp4 as poster
        poster_tmp = temp_dir / "model_s_briefing_poster.jpg"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(ACT1_SRC),
            "-vframes", "1",
            "-q:v", "2",
            str(poster_tmp)
        ], "Exporting first frame of intro.mp4 as model_s_briefing_poster.jpg")

        # 2. Render ACT I: The Hook (A-Roll: James on camera)
        # 1280x720 24fps, 240 frames (10.0s), 20ms anti-pop microfade
        act1_mp4 = temp_dir / "act1_the_hook.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(ACT1_SRC),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-af", "afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02",
            "-r", "24",
            "-frames:v", "240",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(act1_mp4)
        ], "Rendering ACT I (The Hook - James on camera, 10s / 240 frames)")

        # 3. Render ACT II: The Grid Ceiling (B-Roll Graphic with Voiceover)
        # Smooth 10s Ken Burns slow zoom: zoompan=z='min(zoom+0.0015,1.15)':d=240:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=24
        # Audio from Man_speaking_about_data_centers_20260918150841.mp4
        act2_mp4 = temp_dir / "act2_grid_ceiling.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(ACT2_IMG_SRC),
            "-i", str(ACT2_AUDIO_SRC),
            "-filter_complex",
            "[0:v]scale=2752:1536,zoompan=z='min(zoom+0.0015,1.15)':d=240:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=24,format=yuv420p[v];"
            "[1:a]afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-frames:v", "240",
            "-r", "24",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(act2_mp4)
        ], "Rendering ACT II (The Grid Ceiling - Ken Burns zoom + Data Centers Voiceover, 10s / 240 frames)")

        # 4. Render ACT III: The Model-S Silicon (B-Roll Graphic with Voiceover)
        # Subtle 10s pan across NPU and passive heatsink (s=1280x720:fps=24)
        # Audio from Man_speaking_about_neural_silicon_20260918150841.mp4
        act3_mp4 = temp_dir / "act3_model_s_silicon.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(ACT3_IMG_SRC),
            "-i", str(ACT3_AUDIO_SRC),
            "-filter_complex",
            "[0:v]scale=2752:1536,zoompan=z='1.15':d=240:x='(iw-iw/zoom)*(0.2+0.6*(on/239))':y='(ih-ih/zoom)*(0.2+0.6*(on/239))':s=1280x720:fps=24,format=yuv420p[v];"
            "[1:a]afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-frames:v", "240",
            "-r", "24",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(act3_mp4)
        ], "Rendering ACT III (The Model-S Silicon - Pan across NPU & heatsink + Neural Silicon Voiceover, 10s / 240 frames)")

        # 5. Render ACT IV: Latency & Data Sovereignty (B-Roll Graphic with Voiceover)
        # Slow zoom toward 14ms gauge (s=1280x720:fps=24)
        # Audio from Man_speaking_about_data_latency_20260918150841.mp4
        act4_mp4 = temp_dir / "act4_latency_sovereignty.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(ACT4_IMG_SRC),
            "-i", str(ACT4_AUDIO_SRC),
            "-filter_complex",
            "[0:v]scale=2752:1536,zoompan=z='min(zoom+0.0008,1.20)':d=240:x='(iw-iw/zoom)*0.85':y='ih/2-(ih/zoom/2)':s=1280x720:fps=24,format=yuv420p[v];"
            "[1:a]afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-frames:v", "240",
            "-r", "24",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(act4_mp4)
        ], "Rendering ACT IV (Latency & Data Sovereignty - Zoom toward 14ms gauge + Latency Voiceover, 10s / 240 frames)")

        # 6. Render ACT V: The Outro Punchline (A-Roll: James on camera)
        # 1280x720 24fps, 240 frames (10.0s), 20ms anti-pop microfade
        act5_mp4 = temp_dir / "act5_the_outro.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(ACT5_SRC),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-af", "afade=t=in:ss=0:d=0.02,afade=t=out:st=9.98:d=0.02",
            "-r", "24",
            "-frames:v", "240",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(act5_mp4)
        ], "Rendering ACT V (The Outro Punchline - James on camera, 10s / 240 frames)")

        # 7. Concatenate all 5 Acts with libx264, yuv420p, preset fast, +faststart, aac 192k
        master_tmp = temp_dir / "stacklabs_model_s_architecture_briefing.mp4"
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(act1_mp4),
            "-i", str(act2_mp4),
            "-i", str(act3_mp4),
            "-i", str(act4_mp4),
            "-i", str(act5_mp4),
            "-filter_complex",
            "[0:v][0:a][1:v][1:a][2:v][2:a][3:v][3:a][4:v][4:a]concat=n=5:v=1:a=1[v][a]",
            "-map", "[v]",
            "-map", "[a]",
            "-r", "24",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
            str(master_tmp)
        ], "Concatenating 5-Act Master Architectural Briefing (Faststart enabled)")

        # 8. Stage to Target Locations
        print("[+] Staging master video and poster files...")
        PUBLIC_WEB_DIR.mkdir(parents=True, exist_ok=True)
        PILOT_DROPS_DIR.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(str(master_tmp), str(MASTER_PILOT_OUTPUT))
        shutil.copyfile(str(master_tmp), str(MASTER_PUBLIC_OUTPUT))
        shutil.copyfile(str(poster_tmp), str(POSTER_PILOT_OUTPUT))
        shutil.copyfile(str(poster_tmp), str(POSTER_PUBLIC_OUTPUT))

        print(f"[✓] Staged master video to: {MASTER_PILOT_OUTPUT} ({MASTER_PILOT_OUTPUT.stat().st_size} bytes)")
        print(f"[✓] Staged master video to: {MASTER_PUBLIC_OUTPUT} ({MASTER_PUBLIC_OUTPUT.stat().st_size} bytes)")
        print(f"[✓] Staged poster frame to: {POSTER_PILOT_OUTPUT}")
        print(f"[✓] Staged poster frame to: {POSTER_PUBLIC_OUTPUT}")

        # 9. Comprehensive Integrity Audit via ffprobe
        info = probe_file(MASTER_PUBLIC_OUTPUT)
        v_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        a_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")

        duration = float(info["format"]["duration"])
        frames = int(v_stream.get("nb_read_frames", 0))
        size_mb = int(info["format"]["size"]) / (1024 * 1024)

        print("\n=================================================================")
        print("🔍 5-ACT MASTER VIDEO INTEGRITY AUDIT")
        print("=================================================================")
        print(f"Duration:        {duration:.3f}s (Target: 50.00s)")
        print(f"Total Frames:    {frames} (Target: 1200 frames @ 24fps)")
        print(f"Resolution:      {v_stream['width']}x{v_stream['height']} (Target: 1280x720)")
        print(f"Framerate:       {v_stream['r_frame_rate']} (Target: 24/1)")
        print(f"Video Codec:     {v_stream['codec_name']} / {v_stream.get('pix_fmt', 'yuv420p')}")
        print(f"Audio Codec:     {a_stream['codec_name']} ({a_stream.get('sample_rate', 48000)} Hz, 2 channels)")
        print(f"File Size:       {size_mb:.2f} MB")
        print("=================================================================\n")

        assert frames == 1200, f"Expected 1200 video frames, got {frames}"
        assert v_stream['width'] == 1280 and v_stream['height'] == 720, "Expected 1280x720 resolution"
        assert abs(duration - 50.0) < 0.25, f"Expected ~50.0s duration, got {duration}"

        return {
            "master_pilot": str(MASTER_PILOT_OUTPUT),
            "master_public": str(MASTER_PUBLIC_OUTPUT),
            "poster_pilot": str(POSTER_PILOT_OUTPUT),
            "poster_public": str(POSTER_PUBLIC_OUTPUT),
            "duration": duration,
            "video_frames": frames,
            "file_size": int(info["format"]["size"])
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    assemble_master_briefing()
