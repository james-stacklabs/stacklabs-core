#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import requests
import base64
import json
import tempfile
import shutil

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def extract_frames(video_path, out_dir):
    print(f"Extracting keyframes from {video_path}...")
    # Extract 1 frame every 3 seconds
    cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vf", "fps=1/3", 
        os.path.join(out_dir, "frame_%03d.jpg")
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    frames = []
    for f in sorted(os.listdir(out_dir)):
        if f.endswith('.jpg'):
            frames.append(os.path.join(out_dir, f))
    return frames

def analyze_frame(frame_path):
    with open(frame_path, "rb") as img_file:
        b64_img = base64.b64encode(img_file.read()).decode('utf-8')
    
    payload = {
        "model": "llava",
        "prompt": "Describe the specific action occurring in this baseball highlight frame. Be concise.",
        "images": [b64_img],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Error analyzing frame {frame_path}: {e}")
    return None

def synthesize_summary(descriptions):
    prompt = (
        "You are an expert sports broadcaster. I am going to give you a sequence of visual descriptions "
        "extracted from frames of a baseball highlight video. Your job is to synthesize these sequential "
        "descriptions into a cohesive, exciting play-by-play summary of the action. Make it sound professional "
        "and thrilling.\n\n"
        "Frame Sequence:\n"
    )
    for i, desc in enumerate(descriptions):
        prompt += f"- Frame {i+1}: {desc}\n"
        
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
    
    print("Synthesizing final summary with Llama 3...")
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Error synthesizing summary: {e}")
    return "Error generating summary."

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_video_local.py <video_path>")
        sys.exit(1)
        
    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        sys.exit(1)
        
    out_dir = tempfile.mkdtemp(prefix="fanstack_frames_")
    
    try:
        frames = extract_frames(video_path, out_dir)
        if not frames:
            print("No frames extracted.")
            sys.exit(1)
            
        print(f"Extracted {len(frames)} frames. Analyzing with llava...")
        descriptions = []
        for i, frame in enumerate(frames):
            print(f"  -> Analyzing frame {i+1}/{len(frames)}...")
            desc = analyze_frame(frame)
            if desc:
                descriptions.append(desc)
                
        if not descriptions:
            print("Failed to generate any frame descriptions.")
            sys.exit(1)
            
        summary = synthesize_summary(descriptions)
        
        output_md = video_path.rsplit('.', 1)[0] + "_analysis.md"
        with open(output_md, "w") as f:
            f.write("# Highlight Analysis (Local AI)\n\n")
            f.write(summary + "\n\n")
            f.write("## Raw Frame Data\n")
            for i, desc in enumerate(descriptions):
                f.write(f"- **Frame {i+1}**: {desc}\n")
                
        print(f"Analysis saved to {output_md}")
        
    finally:
        shutil.rmtree(out_dir)

if __name__ == "__main__":
    main()
