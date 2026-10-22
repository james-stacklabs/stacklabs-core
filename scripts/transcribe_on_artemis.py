#!/usr/bin/env python3
"""
StackLabs Remote Transcriber Dispatcher (Clio -> Artemis)
Orchestrates high-speed CUDA audio transcription on Artemis (GTX 1060 6GB)
via SSH and reads back verbatim markdown transcripts across the SSHFS bridge.
"""
import os
import sys
import time
import shlex
import argparse
import subprocess
from pathlib import Path

ARTEMIS_HOSTS = ["100.108.185.53", "192.168.1.64"]
ARTEMIS_USER = "james"
REMOTE_LAUNCHER = "/home/james/stacklabs/scripts/artemis_whisper.sh"

def find_active_artemis_host(timeout_sec: int = 2) -> str:
    """Pings candidates to find an active Artemis node."""
    for host in ARTEMIS_HOSTS:
        try:
            res = subprocess.run(
                ["ssh", "-o", f"ConnectTimeout={timeout_sec}", "-o", "StrictHostKeyChecking=no",
                 f"{ARTEMIS_USER}@{host}", "echo ready"],
                capture_output=True, text=True, timeout=timeout_sec + 1
            )
            if res.returncode == 0 and "ready" in res.stdout:
                return host
        except Exception:
            continue
    return ""

def main():
    parser = argparse.ArgumentParser(description="Dispatch audio transcription to Artemis GTX 1060 CUDA")
    parser.add_argument("audio", help="Path to audio file on Clio (under stacklabs or pilot_drops)")
    parser.add_argument("--output", "-o", help="Optional explicit output path on Clio")
    parser.add_argument("--model", "-m", default="base.en", help="Whisper model (default: base.en)")
    parser.add_argument("--compute", "-c", default="int8_float32", help="Compute type (default: int8_float32)")
    args = parser.parse_args()

    local_audio = Path(args.audio).resolve()
    if not local_audio.exists():
        print(f"Error: audio file does not exist: {local_audio}", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    if args.output:
        local_output = Path(args.output).resolve()
    else:
        local_output = local_audio.parent / f"{local_audio.stem}_transcript.md"

    print("=" * 70)
    print("⚡ STACKLABS MULTI-NODE DISPATCHER: CLIO -> ARTEMIS CUDA")
    print("=" * 70)
    print(f"📁 Target Audio: {local_audio.name} ({local_audio.stat().st_size / (1024*1024):.1f} MB)")
    print(f"🎯 Output File:  {local_output}")

    # Check node reachability
    host = find_active_artemis_host()
    if not host:
        print("❌ Error: Artemis node unreachable at 100.108.185.53 or 192.168.1.64", file=sys.stderr)
        sys.exit(2)

    print(f"✓ Connected to Artemis node on metal ({host})")

    # Map local Clio path to Artemis path via SSHFS mount
    # On Artemis, Clio's /home/james/stacklabs_inbox is mounted at /home/james/stacklabs_inbox
    # and /home/james/stacklabs is mounted at /home/james/stacklabs
    remote_audio_path = str(local_audio)
    remote_output_path = str(local_output)

    # Build remote command with shell-safe escaping
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{ARTEMIS_USER}@{host}",
        f"{REMOTE_LAUNCHER} {shlex.quote(remote_audio_path)} --output {shlex.quote(remote_output_path)} --model {shlex.quote(args.model)} --compute {shlex.quote(args.compute)}"
    ]

    print(f"🚀 Launching Faster-Whisper on GTX 1060 Pascal silicon...")
    t0 = time.time()
    proc = subprocess.run(cmd)

    elapsed = time.time() - t0
    if proc.returncode != 0:
        print(f"❌ Remote transcription failed with exit code {proc.returncode}", file=sys.stderr)
        sys.exit(proc.returncode)

    # Verify transcript arrived on Clio NVMe via SSHFS
    if local_output.exists() and local_output.stat().st_size > 0:
        print("-" * 70)
        print(f"✅ Verified transcript on Clio NVMe: {local_output} ({local_output.stat().st_size} bytes)")
        print(f"⚡ Total Multi-Node Roundtrip: {elapsed:.2f}s")
        print("=" * 70)
    else:
        print(f"⚠️ Warning: Process completed but output file not yet visible: {local_output}")

if __name__ == "__main__":
    main()
