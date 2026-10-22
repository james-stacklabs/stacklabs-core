#!/usr/bin/env python3
import os
import subprocess
import time
import json

MEDIA_VAULT_PATH = "/home/james/stacklabs/media_vault"
UNSUPPORTED_CODECS = {"eac3", "ac3", "dts", "truehd"}

def get_audio_codec(filepath):
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-select_streams", "a:0", 
            "-show_entries", "stream=codec_name", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip().lower()
    except Exception as e:
        print(f"Error checking codec for {filepath}: {e}")
        return None

def optimize_file(filepath):
    print(f"Optimizing audio for: {filepath}")
    temp_filepath = filepath + ".optimized.mkv"
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", filepath,
        "-c:v", "copy",
        "-c:a", "libopus",
        "-b:a", "128k",
        "-ac", "2",
        temp_filepath
    ]
    
    try:
        # Run ffmpeg
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print(f"Successfully optimized {filepath}. Replacing original.")
            os.replace(temp_filepath, filepath)
            return True
        else:
            print(f"Failed to optimize {filepath}. FFmpeg error:\n{result.stderr.decode()}")
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            return False
    except Exception as e:
        print(f"Exception during optimization of {filepath}: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return False

def scan_and_optimize():
    print(f"Starting media vault sweep at {time.ctime()}")
    if not os.path.exists(MEDIA_VAULT_PATH):
        print("Media vault path does not exist.")
        return
        
    for root, dirs, files in os.walk(MEDIA_VAULT_PATH):
        for file in files:
            if file.endswith(('.mkv', '.mp4')):
                filepath = os.path.join(root, file)
                codec = get_audio_codec(filepath)
                if codec in UNSUPPORTED_CODECS:
                    print(f"Found unsupported codec '{codec}' in {file}")
                    optimize_file(filepath)

if __name__ == "__main__":
    print("Sovereign Media Vault Optimizer initialized.")
    while True:
        scan_and_optimize()
        print("Sweep complete. Sleeping for 1 hour...")
        time.sleep(3600)
