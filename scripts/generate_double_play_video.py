import os
import time
import subprocess
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Load and Configure Gemini API Authentication
load_dotenv("/home/james/stacklabs/.env")
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

TARGET_VIDEO_DIR = "/home/james/stacklabs/19_Sovereign_Sports/public/videos"
OUTPUT_PATH = os.path.join(TARGET_VIDEO_DIR, "double_play_flow.mp4")
BACKUP_PATH = os.path.join(TARGET_VIDEO_DIR, "double_play_flow_hallucination_backup.mp4")

# Backup existing flawed video if not backed up yet
if os.path.exists(OUTPUT_PATH) and not os.path.exists(BACKUP_PATH):
    subprocess.run(["cp", OUTPUT_PATH, BACKUP_PATH])
    print(f"Backed up flawed video to: {BACKUP_PATH}")

PROMPT = (
    "Cinematic high-stakes Major League Baseball highlight of a classic 6-4-3 double play under bright stadium floodlights at night. "
    "Camera tracking from low angle behind home plate: A sharp ground ball is hit to the shortstop on the infield dirt. "
    "The shortstop cleanly scoops the grounder and flips it to the second baseman covering second base who touches the bag for the first out. "
    "The second baseman leaps gracefully in the air and fires a fast bullet throw across the infield diamond to the first baseman who stretches on first base to catch the ball for the second out. "
    "Explosive stadium crowd cheering, motion blur, sharp 8k photorealistic broadcast camera angle, dynamic lighting."
)

print(f"[*] Submitting Veo Video Generation Request for realistic Double Play physics...")
print(f"    Prompt: {PROMPT}")

try:
    config = types.GenerateVideosConfig(
        aspect_ratio="16:9",
        duration_seconds=6
    )
    operation = client.models.generate_videos(
        model="veo-3.1-fast-generate-preview",
        prompt=PROMPT,
        config=config
    )
    
    print(f"[*] Polling Veo generation operation: {operation.name}...")
    start_time = time.time()
    while True:
        resource_name = operation.name.rpartition('/operations/')[0]
        raw_dict = client.operations._fetch_predict_videos_operation(
            operation_name=operation.name,
            resource_name=resource_name
        )
        if raw_dict.get("done"):
            if "error" in raw_dict:
                raise RuntimeError(f"API Error: {raw_dict['error']}")
            
            resp = raw_dict.get("response", {})
            videos = resp.get("videos", [])
            if not videos:
                raise RuntimeError("No videos found in response predictions!")
            
            video_b64 = videos[0].get("bytesBase64Encoded")
            video_bytes = base64.b64decode(video_b64)
            with open(OUTPUT_PATH, "wb") as f:
                f.write(video_bytes)
            
            # Also copy to dist and 15_FanStack if needed
            dist_path = "/home/james/stacklabs/19_Sovereign_Sports/dist/videos/double_play_flow.mp4"
            if os.path.exists(os.path.dirname(dist_path)):
                with open(dist_path, "wb") as f:
                    f.write(video_bytes)
                    
            print(f"[SUCCESS] Saved generated Double Play video to: {OUTPUT_PATH} ({len(video_bytes)} bytes)")
            break
            
        elapsed = int(time.time() - start_time)
        print(f"    ... Generating ({elapsed}s elapsed)...")
        time.sleep(10)

except Exception as e:
    print(f"[ERROR] Generation failed: {e}")
