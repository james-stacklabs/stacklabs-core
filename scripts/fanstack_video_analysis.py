#!/usr/bin/env python3
import os
import time
import json
from google import genai

# Sovereign OS Target Paths
SESSION_DIR = "/home/james/stacklabs/dna/agents/CLAUDE/active_sessions/fa2c2765-235e-46d6-b08a-9cce95a0b65a"
VIDEO_FILES = [
    "PXL 20260403 031303485.mp4",
    "PXL 20260403 031327404.mp4"
]
OUTPUT_JSON = os.path.join(SESSION_DIR, "temporal_delta_analysis.json")

def wait_for_video_processing(client, file_ref):
    print(f"Waiting for {file_ref.name} to process...")
    processed_ref = client.files.get(name=file_ref.name)
    while processed_ref.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(10)
        processed_ref = client.files.get(name=file_ref.name)
    if processed_ref.state.name == "FAILED":
        raise ValueError(f"Video processing failed for {file_ref.name}")
    print("\nProcessing complete.")
    return processed_ref

def analyze_videos():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set. Please export it before running.")
        return

    client = genai.Client(api_key=api_key)
    analysis_results = []

    prompt = """
    You are an expert patent attorney and technical analyst. 
    This video is a raw recording of a 'ground truth' test showing three monitors:
    1. A passive live TV broadcast of a baseball game.
    2. A web application (FanStack God Console/Savant Refinery) reacting to MLB Statcast telemetry.
    3. The official MLB App or live stream.

    Analyze this video and extract precise timestamps where the web application (FanStack) updates or reacts to a play BEFORE the official MLB App or TV broadcast catches up. This temporal gap is our 'predictive latency advantage'.

    Provide exactly the following structured information in pure JSON format (do not use markdown wrapping):
    {
      "file_name": "[filename]",
      "patent_relevance": "HIGH" | "MEDIUM" | "LOW",
      "best_atdc_pitch_moment_timestamp": "[MM:SS]",
      "moments": [
        {
          "timestamp": "[MM:SS]",
          "description": "What happened on the FanStack Console vs the MLB App/TV",
          "delta_seconds_estimate": 4
        }
      ]
    }
    """

    for video_name in VIDEO_FILES:
        video_path = os.path.join(SESSION_DIR, video_name)
        if not os.path.exists(video_path):
            print(f"Warning: {video_path} not found. Skipping.")
            continue
            
        print(f"\nUploading {video_name} to Gemini File API...")
        uploaded_file = client.files.upload(file=video_path)
        ready_file = wait_for_video_processing(client, uploaded_file)
        
        print(f"Analyzing {video_name}...")
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[ready_file, prompt]
            )
            # Parse JSON - assuming the model outputs valid JSON based on strict instructions
            parts_text = []
            if response and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
            if parts_text:
                result_json = "".join(parts_text)
            else:
                try:
                    result_json = response.text or ""
                except Exception:
                    result_json = ""
            result_json = result_json.strip()
            if result_json.startswith("```json"):
                result_json = result_json[7:-3]
            elif result_json.startswith("```"):
                result_json = result_json[3:-3]
                
            parsed_result = json.loads(result_json.strip())
            # Inject filename manually incase the model misses it
            parsed_result["file_name"] = video_name
            analysis_results.append(parsed_result)
            print(f"Analysis successful for {video_name}.")
        except Exception as e:
            print(f"Error during analysis of {video_name}: {e}")
            
        # Clean up the file from Gemini storage to save quota
        client.files.delete(name=uploaded_file.name)
        print(f"Cleaned up {uploaded_file.name} from Gemini File API.")

    if analysis_results:
        with open(OUTPUT_JSON, "w") as f:
            json.dump(analysis_results, f, indent=4)
        print(f"\n[SUCCESS] ATDC Temporal Delta Analysis saved to: {OUTPUT_JSON}")

if __name__ == "__main__":
    analyze_videos()
