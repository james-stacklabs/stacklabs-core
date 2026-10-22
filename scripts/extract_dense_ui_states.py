#!/usr/bin/env python3
"""
Sovereign OS Dense UI State Extractor
Parses webcam recordings of user interactions, extracts frames, and uses template matching 
to filter out duplicate/static frames to generate clean training datasets.
"""

import cv2
import os
import sys
import argparse
import numpy as np

def extract_dense_ui_states(video_path, output_dir, similarity_threshold=0.995):
    if not os.path.exists(video_path):
        print(f"[-] Error: Input video file not found at {video_path}")
        return False

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[+] Created output directory: {output_dir}")

    print(f"[*] Ingesting video: {video_path}")
    print(f"[*] Similarity threshold: {similarity_threshold}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[-] Error: Could not open video file.")
        return False

    count, saved_count = 0, 0
    last_frame_gray = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert to grayscale and downsample to accelerate template matching
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_resized = cv2.resize(gray, (320, 180))
        
        if last_frame_gray is not None:
            # Perform normalized cross-correlation
            res = cv2.matchTemplate(gray_resized, last_frame_gray, cv2.TM_CCOEFF_NORMED)
            if res[0][0] > similarity_threshold:
                count += 1
                continue
        
        frame_name = f"ui_state_{saved_count:05d}.png"
        cv2.imwrite(os.path.join(output_dir, frame_name), frame)
        
        last_frame_gray = gray_resized
        saved_count += 1
        count += 1
        
        # Display progress update every 100 frames
        if count % 100 == 0:
            print(f"[*] Processed {count} frames... Saved {saved_count} unique UI states.", end="\r")

    cap.release()
    print(f"\n[+] Ingestion complete. Compressed {count} video frames down to {saved_count} dense UI layouts.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and deduplicate unique UI states from webcam recordings.")
    parser.add_argument("--video", type=str, default="/home/james/stacklabs/media_vault/01_Assets/Inbox/EXHIBIT_LINDOR_093.png", help="Path to input video file.")
    parser.add_argument("--output", type=str, default="/home/james/sovereign_inbox/staging/dense_ui_dataset", help="Path to output directory for unique frames.")
    parser.add_argument("--threshold", type=float, default=0.995, help="Similarity threshold for frame deduplication (0.0 to 1.0).")
    
    args = parser.parse_args()
    
    # Simple check for help or direct execution
    print("=" * 60)
    print(" Sovereign OS Dense UI Frame Extractor Pipeline")
    print("=" * 60)
    
    # If the default video doesn't exist, we can create a mock run or show usage
    if not os.path.exists(args.video):
        print(f"[!] Target video '{args.video}' not found. Run with --video <path>.")
        sys.exit(0)
        
    extract_dense_ui_states(args.video, args.output, args.threshold)
