#!/usr/bin/env python3
"""
StackLabs Metal Transcriber for Artemis (GTX 1060 6GB CUDA)
Extracts audio transcripts at 10x-20x real-time on Pascal silicon with live progress bar.
"""
import os
import sys
import time
import argparse
import subprocess

# Ensure CUDA 12 libraries from pip packages are in LD_LIBRARY_PATH
cublas_lib = "/data/artemis_env/lib/python3.12/site-packages/nvidia/cublas/lib"
cudnn_lib = "/data/artemis_env/lib/python3.12/site-packages/nvidia/cudnn/lib"
extra_paths = [p for p in [cublas_lib, cudnn_lib] if os.path.exists(p)]

if extra_paths:
    cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    new_ld = ":".join(extra_paths) + (":" + cur_ld if cur_ld else "")
    if "ARTEMIS_LD_LOADED" not in os.environ:
        os.environ["ARTEMIS_LD_LOADED"] = "1"
        os.environ["LD_LIBRARY_PATH"] = new_ld
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            pass

def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def get_gpu_telemetry() -> str:
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 3:
                return f"VRAM: {parts[0]}/{parts[1]}MB | {parts[2]}°C"
    except Exception:
        pass
    return "GTX 1060 CUDA"

def main():
    parser = argparse.ArgumentParser(description="Artemis CUDA Faster-Whisper Transcriber")
    parser.add_argument("audio", help="Path to input audio file")
    parser.add_argument("--output", "-o", help="Path to output markdown file (default: same path with _transcript.md)")
    parser.add_argument("--model", "-m", default="base.en", help="Whisper model name (default: base.en)")
    parser.add_argument("--compute", "-c", default="int8_float32", help="Compute type (default: int8_float32 for Pascal)")
    parser.add_argument("--beam-size", "-b", type=int, default=1, help="Beam size (default: 1 for maximum speed)")
    args = parser.parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.exists(audio_path):
        print(f"Error: audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    if not args.output:
        base, _ = os.path.splitext(audio_path)
        output_path = f"{base}_transcript.md"
    else:
        output_path = os.path.abspath(args.output)

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print("\n" + "=" * 70)
    print("⚡ STACKLABS METAL TRANSCRIBER [ARTEMIS / GTX 1060 CUDA]")
    print("=" * 70)
    print(f"📁 Target Audio: {os.path.basename(audio_path)} ({file_size_mb:.1f} MB)")
    print(f"🧠 Model: {args.model} | Compute Type: {args.compute} (Beam Size: {args.beam_size})")
    print(f"💾 Output: {output_path}")
    print(f"🖥️  Node: {get_gpu_telemetry()}")
    print("-" * 70)

    from faster_whisper import WhisperModel

    print(f"[*] Initializing WhisperModel('{args.model}') on CUDA...")
    t_load = time.time()
    model = WhisperModel(
        args.model,
        device="cuda",
        compute_type=args.compute,
        download_root="/data/cache/models"
    )
    print(f"✓ Model loaded in {time.time() - t_load:.2f}s")

    print("[*] Starting transcription stream...")
    t_start = time.time()
    segments, info = model.transcribe(
        audio_path,
        beam_size=args.beam_size,
        word_timestamps=False
    )

    total_duration = info.duration
    print(f"⏱️  Audio Duration: {format_time(total_duration)} ({total_duration:.1f}s) | Detected: {info.language} ({info.language_probability*100:.0f}%)")
    print("-" * 70)

    transcribed_segments = []
    bar_width = 30

    for seg in segments:
        transcribed_segments.append(seg)
        cur_pos = seg.end
        elapsed = time.time() - t_start
        if elapsed <= 0:
            elapsed = 0.001
        
        speed = cur_pos / elapsed
        pct = min(100.0, (cur_pos / total_duration) * 100) if total_duration > 0 else 0
        rem_seconds = (total_duration - cur_pos) / speed if speed > 0 else 0

        filled = int(bar_width * (pct / 100.0))
        bar = "█" * filled + "░" * (bar_width - filled)

        # Print real-time progress bar line
        status_line = (
            f"\r[{bar}] {pct:5.1f}% | {format_time(cur_pos)}/{format_time(total_duration)} | "
            f"{speed:4.1f}x real-time | ETA: {format_time(rem_seconds)} | {get_gpu_telemetry()}"
        )
        sys.stdout.write(status_line)
        sys.stdout.flush()

    total_elapsed = time.time() - t_start
    final_speed = total_duration / total_elapsed if total_elapsed > 0 else 0

    # Fill bar to 100%
    full_bar = "█" * bar_width
    sys.stdout.write(f"\r[{full_bar}] 100.0% | {format_time(total_duration)}/{format_time(total_duration)} | {final_speed:4.1f}x real-time | Completed in {format_time(total_elapsed)}!            \n")
    sys.stdout.flush()

    # Compile Markdown Document
    md_lines = [
        f"# 🎙️ Audio Transcript: {os.path.basename(audio_path)}",
        "",
        "> **Transcribed by**: Artemis Metal Workstation (NVIDIA GTX 1060 6GB GDDR5 / CUDA)  ",
        f"> **Model**: Faster-Whisper `{args.model}` (`{args.compute}`)  ",
        f"> **Audio Duration**: {format_time(total_duration)} ({total_duration:.1f}s)  ",
        f"> **Processing Time**: {total_elapsed:.2f}s ({final_speed:.1f}x real-time speed)  ",
        f"> **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        "",
        "---",
        "",
        "## 📜 Verbatim Transcript",
        ""
    ]

    for seg in transcribed_segments:
        start_ts = format_time(seg.start)
        end_ts = format_time(seg.end)
        md_lines.append(f"**[{start_ts} -> {end_ts}]** {seg.text.strip()}\n")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print("-" * 70)
    print(f"✅ SUCCESS: Wrote full transcript ({len(transcribed_segments)} segments) to:")
    print(f"👉 {output_path}")
    print(f"⚡ Benchmark: Transcribed {format_time(total_duration)} in {total_elapsed:.1f}s ({final_speed:.1f}x faster than real time)")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
