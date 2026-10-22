#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

def translate_path_to_pegasus(local_path):
    """
    Translates a Node .73 path to the Pi 5 .74 SMB mount path.
    Node .73: /home/james/stacklabs/...
    Node .74: /mnt/apiary_mesh/apiary/...
    """
    abs_path = os.path.abspath(local_path)
    if not abs_path.startswith("/home/james/ai_projects/"):
        print(f"ERROR: Input file must be within /home/james/ai_projects/ for the SMB mount to work.")
        print(f"Path given: {abs_path}")
        sys.exit(1)
        
    return abs_path.replace("/home/james/ai_projects/", "/mnt/apiary_mesh/")

def run_ssh_command(cmd, desc=""):
    print(f"\n[Pegasus] {desc}...")
    full_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "james@192.168.1.74", cmd]
    print(f"Command: {cmd}")
    try:
        subprocess.run(full_cmd, check=True)
        print("[Pegasus] Done.")
    except subprocess.CalledProcessError as e:
        print(f"[Pegasus] SSH Command Failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Squash a video natively on Pi 5 (Node .74) via NVENC.")
    parser.add_argument("input", help="Local path to the video file")
    parser.add_argument("--overwrite", action="store_true", help="Replace the original file instead of appending _squashed")
    parser.add_argument("--pluck", action="store_true", help="Also extract 1 FPS keyframes and save in an adjacent folder")
    
    args = parser.parse_args()

    # 1. Validation and File Parsing
    if not os.path.isfile(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    local_input = os.path.abspath(args.input)
    pegasus_input = translate_path_to_pegasus(local_input)

    # Output paths
    base_name, ext = os.path.splitext(local_input)
    pegasus_base = translate_path_to_pegasus(base_name)
    
    if args.overwrite:
        # We write to a temp file, then mv it over the original
        pegasus_output = f"{pegasus_base}_tmp_encode.mp4"
    else:
        pegasus_output = f"{pegasus_base}_squashed.mp4"
        local_output = f"{base_name}_squashed.mp4"

    # 2. Build the NVENC squashing command
    # Using h264_nvenc. Preset p5 is a sweet spot for quality/speed. 
    # 2M bitrate is extremely aggressive for massive Web/Reaction payload squashing.
    ffmpeg_cmd = (
        f"ffmpeg -y -v warning -stats -i '{pegasus_input}' "
        f"-c:v h264_nvenc -preset p5 -tune hq -b:v 2M -maxrate 2.5M -bufsize 4M "
        f"-c:a aac -b:a 128k '{pegasus_output}'"
    )

    # 3. Fire the SSH Command
    run_ssh_command(ffmpeg_cmd, desc="Squashing Multimodal Payload")

    # 4. Handle Overwriting
    if args.overwrite:
        mv_cmd = f"mv '{pegasus_output}' '{pegasus_input}'"
        run_ssh_command(mv_cmd, desc="Replacing original payload")
        print(f"\n[SUCCESS] Squashed and replaced payload at: {local_input}")
    else:
        print(f"\n[SUCCESS] Squashed payload delivered to: {local_output}")

    # 5. Handle Plucking (Optional)
    if args.pluck:
        pegasus_frames_dir = f"{pegasus_base}_frames"
        local_frames_dir = f"{base_name}_frames"
        
        pluck_cmd = (
            f"mkdir -p '{pegasus_frames_dir}' && "
            f"ffmpeg -y -v warning -stats -i '{pegasus_input}' "
            f"-vf fps=1 -q:v 2 '{pegasus_frames_dir}/frame_%04d.jpg'"
        )
        run_ssh_command(pluck_cmd, desc="Plucking highly-structured 1FPS keyframes")
        print(f"\n[SUCCESS] Extracted keyframes delivered to: {local_frames_dir}")


if __name__ == "__main__":
    main()
