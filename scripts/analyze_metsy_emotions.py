#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
from datetime import datetime
import google.genai as genai
from google.genai import types

# Configuration & Paths
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
BEST_REND_DIR = "/home/james/stacklabs/avatars/metsy_smyrna/best_renderings"
REGISTRY_PATH = os.path.join(BEST_REND_DIR, "metsy_emotions_registry.json")

# Map of extracted file patterns to canonical emotion names
FILE_MAPPING = {
    "confused": "confused.jpeg",
    "defcon_greebles": "defcon_greebles.jpeg",
    "excited": "excited.jpeg",
    "zoomies": "full_on_zoomies.jpeg",
    "happy": "happy.jpeg",
    "inquisitive": "inquisitive.jpeg",
    "intrigued": "intrigued.jpeg",
    "sad": "sad.jpeg",
    "upset": "upset.jpeg",
    "wiggling_hindquarters": "playful.jpeg"
}

def rename_files():
    print("[*] Renaming extracted files to canonical names...")
    files = os.listdir(BEST_REND_DIR)
    renamed_count = 0
    for filename in files:
        filepath = os.path.join(BEST_REND_DIR, filename)
        if not os.path.isfile(filepath) or filename == "metsy_emotions_key.zip":
            continue
            
        for pattern, canonical_name in FILE_MAPPING.items():
            if pattern in filename.lower() and filename != canonical_name:
                dest_path = os.path.join(BEST_REND_DIR, canonical_name)
                # If destination already exists, remove it first to avoid collision
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                os.rename(filepath, dest_path)
                print(f"  ✓ Renamed: {filename} -> {canonical_name}")
                renamed_count += 1
                break
    print(f"[+] Standardized {renamed_count} files in best_renderings.")

def analyze_emotions():
    print("==================================================================")
    print("🧠 Metsy Smyrna Heights Multi-Modal Visual Analysis")
    print("==================================================================")
    
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[-] ERROR: Vertex credentials not found at {CREDENTIALS_PATH}")
        sys.exit(1)
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    
    # Initialize google-genai Client
    print("Initializing Google GenAI Client...")
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )
    
    # Target emotions list
    emotions = [
        ("excited", "excited.jpeg", "overjoyed, tail high, eyes sparkling"),
        ("confused", "confused.jpeg", "head tilted, ears slightly askew, questioning gaze"),
        ("intrigued", "intrigued.jpeg", "focused, leaning forward, pupils dilated with deep curiosity"),
        ("upset", "upset.jpeg", "ears flat in airplane mode, narrowed eyes, grumpy pout or sass"),
        ("happy", "happy.jpeg", "relaxed posture, contented expression, soft squinty eyes"),
        ("sad", "sad.jpeg", "ears drooped, big teary eyes, downcast look"),
        ("playful", "playful.jpeg", "butt in the air, pupils huge, ready to pounce, wiggling hindquarters"),
        ("inquisitive", "inquisitive.jpeg", "one paw raised, nose twitching, investigating with alert curiosity"),
        ("full-on zoomies", "full_on_zoomies.jpeg", "wild, hyperactive blur of motion, crazed wide eyes, energetic posture"),
        ("defcon greebles", "defcon_greebles.jpeg", "wide-eyed spooked stare at nothing, tail puffed, reacting to unseen entities (Greeble Defcon alert)")
    ]
    
    registry = {}
    
    for emotion_key, filename, brief_desc in emotions:
        filepath = os.path.join(BEST_REND_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[-] WARNING: Missing image file for '{emotion_key}': {filename}")
            continue
            
        print(f"\n[*] Analyzing image for emotion: '{emotion_key}' ({filename})...")
        
        with open(filepath, "rb") as f:
            image_bytes = f.read()
            
        prompt = f"""You are a world-class prompt engineer and director for the Sovereign OS daily cartoon comic strip "Metsy's Daily Adventures".
Analyze this hand-drawn 90s cardboard comic illustration of Metsy the cat. 
She is a brown striped tabby cat with green eyes, wearing a blue tactical harness with orange trim and a glowing multicolored LED tracker collar.

The image shows Metsy exhibiting the specific emotion: "{emotion_key}" (briefly: {brief_desc}).

Analyze her facial features, eyes, ears, tail, body posture, and harness placement.
Based on your observation of this specific image, write a highly descriptive, vivid single-sentence prompt clause (e.g., "Metsy looking incredibly excited with wide sparkling green eyes, ears perked forward, and a joyful grin") that perfectly captures her expression and posture in this image so we can replicate it in future generations.
Output ONLY the raw descriptive string. Do not include any preamble, markdown, or explanation."""

        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                    prompt
                ]
            )
            result_prompt = response.text.strip()
            # Clean quotes if model returned them
            if result_prompt.startswith('"') and result_prompt.endswith('"'):
                result_prompt = result_prompt[1:-1]
            if result_prompt.startswith("'") and result_prompt.endswith("'"):
                result_prompt = result_prompt[1:-1]
                
            print(f"  ✓ Extracted Prompt: \"{result_prompt}\"")
            registry[emotion_key] = {
                "file_name": filename,
                "file_path": filepath,
                "brief_description": brief_desc,
                "extracted_prompt_clause": result_prompt,
                "analyzed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        except Exception as e:
            print(f"  ✗ Analysis failed for {emotion_key}: {e}")
            
    # Save to registry JSON
    with open(REGISTRY_PATH, "w", encoding="utf-8") as rf:
        json.dump(registry, rf, indent=2)
    print(f"\n[+] Saved complete emotion prompt registry to: {REGISTRY_PATH}")
    print("==================================================================")
    print("🟢 SUCCESS: Metsy Multi-Modal Analysis Complete!")
    print("==================================================================")

def main():
    rename_files()
    analyze_emotions()

if __name__ == "__main__":
    main()
