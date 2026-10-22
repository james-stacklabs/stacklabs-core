import sys
import os
import time
import json
import argparse
from google import genai
from dotenv import load_dotenv

def main():
    parser = argparse.ArgumentParser(description="DVR Video Analyzer")
    parser.add_argument("video_path", help="Path to the captured DVR video file")
    parser.add_argument("--vision", type=str, default="", help="User's comedic vision or context for the play")
    args = parser.parse_args()

    video_path = args.video_path
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} not found.")
        sys.exit(1)

    # Load environment variables
    load_dotenv("/home/james/stacklabs/.env")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print(f"[*] Uploading video {video_path} to Gemini File API...")
    video_file = client.files.upload(file=video_path)
    
    print(f"[*] Uploaded as: {video_file.uri}")
    
    # Wait for the file to be processed
    while video_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        print("\n[!] Video processing failed on Gemini servers.")
        sys.exit(1)
        
    print("\n[*] Video processed. Running 'Director Mode' Analysis via gemini-flash-latest...")
    
    prompt = f"""
    Act as a viral YouTube Shorts scriptwriter in 'Director Mode'. 
    Watch this short baseball clip and provide a timestamped breakdown of the action.
    Format your response exactly like this:
    0-2s: [Punchy action description]
    2-5s: [Next punchy action]
    ...
    
    Here is the specific comedic vision and context you MUST incorporate into the script:
    "{args.vision if args.vision else 'Keep it high-energy and focus on the crazy or engaging elements.'}"
    
    Make it sound like a fast-paced storyboard for a viral video. If the vision mentions absurd scenarios (like doing taxes or making dinner reservations), aggressively weave those comedic exaggerations into the timestamps where the player is waiting!
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[video_file, prompt]
        )
        analysis_text = response.text
        
        # Save the manifest alongside the video
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        dir_name = os.path.dirname(video_path)
        manifest_path = os.path.join(dir_name, f"{base_name}.json")
        
        manifest = {
            "rom_id": base_name,
            "video_file": os.path.basename(video_path),
            "script": analysis_text,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)
            
        print(f"[*] ROM Manifest Saved: {manifest_path}")
        print("\n--- DIRECTOR MODE SCRIPT ---\n")
        print(analysis_text)
        print("\n----------------------------")
        
    except Exception as e:
        print(f"[!] Analysis Failed: {e}")
    finally:
        # Clean up the file to ensure we don't pay storage fees long-term
        print("[*] Cleaning up temporary video from Gemini File API...")
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass

if __name__ == "__main__":
    main()
