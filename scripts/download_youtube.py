import os
import sys
import subprocess
import argparse

def download_video(url, output_dir):
    """Downloads a YouTube video to the specified directory using yt-dlp."""
    print(f"Downloading video from: {url}")
    print(f"Target directory: {output_dir}")
    print("Initializing yt-dlp engine. Bypassing browser phishing vectors...")
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Using yt-dlp to download the video 
    # Opting for reliable mp4 format, max 1080p to save processing time
    command = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", f"{output_dir}/%(title)s_[%(id)s].%(ext)s",
        url
    ]
    
    try:
        subprocess.run(command, check=True)
        print(f"\n[SUCCESS] Video downloaded safely to {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to download video. yt-dlp error code: {e.returncode}")
    except FileNotFoundError:
        print("\n[ERROR] yt-dlp is not installed or not in PATH.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Securely download YouTube videos for analysis via yt-dlp.")
    parser.add_argument("url", help="The YouTube URL to download")
    parser.add_argument("--dir", default="/home/james/stacklabs/dna/dropzone/daily_19042026", help="Target directory for the download")
    args = parser.parse_args()
    
    download_video(args.url, args.dir)
