#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from google import genai
from google.genai import types

MEDIA_DIR = "/home/james/stacklabs/media_vault/01_Ingest/postgames"
os.makedirs(MEDIA_DIR, exist_ok=True)

def get_api_key():
    try:
        with open('/home/james/stacklabs/.env') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    return line.strip().split('=', 1)[1]
    except Exception:
        pass
    return None

gemini_key = get_api_key()
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key
else:
    print("Error: Could not find GEMINI_API_KEY in .env")
    sys.exit(1)

client = genai.Client()

def extract_audio(video_path):
    basename = os.path.basename(video_path).rsplit('.', 1)[0]
    mp3_path = os.path.join(MEDIA_DIR, f"{basename}.mp3")
    
    if os.path.exists(mp3_path):
        print(f"[+] Audio already extracted: {mp3_path}")
        return mp3_path
        
    print(f"[*] Extracting audio from {video_path} to {mp3_path}...")
    cmd = [
        "ffmpeg", "-i", video_path, 
        "-q:a", "0", "-map", "a", 
        mp3_path, "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[+] Audio extraction complete.")
    return mp3_path

def process_video(video_path, comments_path=None):
    if not os.path.exists(video_path):
        print(f"Error: File not found: {video_path}")
        return

    basename = os.path.basename(video_path).rsplit('.', 1)[0]
    transcript_path = os.path.join(MEDIA_DIR, f"{basename}_transcript.txt")
    juicy_bits_path = os.path.join(MEDIA_DIR, f"{basename}_juicy_bits.md")
    
    mp3_path = extract_audio(video_path)
    
    print(f"[*] Extracting transcript locally using Whisper (bypassing Gemini API limits)...")
    try:
        cmd = [
            "whisper", mp3_path,
            "--model", "base",
            "--output_dir", MEDIA_DIR,
            "--output_format", "txt"
        ]
        subprocess.run(cmd, check=True)
        print(f"[+] Saved transcript to {transcript_path}")
        
        # Read the generated transcript
        try:
            with open(transcript_path, 'r') as f:
                transcript_text = f.read()
        except:
            transcript_text = "Transcript failed to generate."

        # Read optional comments
        comments_text = ""
        if comments_path and os.path.exists(comments_path):
            print(f"[*] Loading live chat/comments from {comments_path}...")
            try:
                with open(comments_path, 'r') as f:
                    comments_text = f.read()
            except Exception as e:
                print(f"[-] Failed to read comments file: {e}")

        print("[*] Requesting Juicy Bits extraction using Gemini API on the text transcript...")
        try:
            comments_section = f"\n\nLIVE CHAT / COMMENTS TO CROSS-REFERENCE:\n{comments_text[:10000]}" if comments_text else ""
            
            juicy_prompt = f"""
            Analyze this postgame stream transcript. 
            Step 1: Identify the top 3-5 keywords or names that the speaker(s) use most frequently in a frustrated, angry, or desperate context (e.g., Mendoza, Stearns, Devin Williams, Soto, Cohen). List these keywords first.
            Step 2: Using those keywords, extract the "Juicy Bits". 
            A "Juicy Bit" is a highly emotional rant, a hilarious meltdown, or a great quote.
            Provide the verbatim quote for each Juicy Bit so video editors know exactly where to look.
            Format as a Markdown report.
            
            If live chat comments are provided, cross-reference the chat sentiment with the transcript. Did the streamer react to a specific comment? Did the chat lose their minds at a certain moment? Highlight these synced events as premium Juicy Bits.

            TRANSCRIPT:
            {transcript_text[:30000]} # Limiting context window to avoid token limits{comments_section}
            """
            
            juicy_res = client.models.generate_content(
                model='gemini-flash-latest',
                contents=[juicy_prompt]
            )
            
            with open(juicy_bits_path, "w") as f:
                f.write(juicy_res.text)
            print(f"[+] Saved juicy bits report to {juicy_bits_path}")
        except Exception as e:
            print(f"[-] Gemini API failed for Juicy Bits (Credit limits likely exhausted): {e}")
            with open(juicy_bits_path, "w") as f:
                f.write("Gemini API credits exhausted. Could not generate Juicy Bits automatically.\n\nPlease refer to the raw transcript.")
        
        print(f"[+] Pipeline complete for {basename}!")
        print(f"    - MP3: {mp3_path}")
        print(f"    - Transcript: {transcript_path}")
        print(f"    - Juicy Bits: {juicy_bits_path}")

    except Exception as e:
        print(f"[-] Error during processing: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 postgame_pipeline.py <video_file.mp4> [optional_comments_file.md]")
        sys.exit(1)
        
    comments_file = sys.argv[2] if len(sys.argv) > 2 else None
    process_video(sys.argv[1], comments_file)
