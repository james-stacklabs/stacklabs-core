import os
import time
import subprocess
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Load and Configure Google Cloud Vertex AI Authentication
load_dotenv("/home/james/stacklabs/.env")

# Configure the Service Account from config/vertex_sa.json
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/james/stacklabs/config/vertex_sa.json"

# Initialize Client using Vertex AI
client = genai.Client(
    vertexai=True,
    project="gen-lang-client-0840454416",
    location="us-central1"
)

# 2. Config Definitions
VEO_DIR = "/home/james/sovereign_inbox/today/veo"
os.makedirs(VEO_DIR, exist_ok=True)

# Staged mutant character images (1:1 aspect ratio)
REF_IMG_FILES = [
    "RiggedLeagueRant_nose_accusation.png",
    "RiggedLeagueRant_nose_asl_doom.png"
]

# Copy reference images to veo folder so they are in context
for filename in REF_IMG_FILES:
    src = os.path.join("/home/james/stacklabs/media_vault/01_Assets/Inbox", filename)
    dst = os.path.join(VEO_DIR, filename)
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, dst)

CLIP_PROMPTS = [
    # CLIP 1: The Accusation
    ("fanstank_bart_clip_01.mp4", 
     "A disappointed middle-aged male Chicago Cubs fan in a stained pinstripe jersey standing in front of a baseball corkboard. "
     "A small, fully formed secondary human hand emerges directly from the bridge of his nose, aggressively pointing an accusatory finger "
     "straight at the camera. His eyes are wide, bloodshot, and filled with manic paranoia. Flat 2D vector style, bold outlines."),
    
    # CLIP 2: The Secret ASL Message
    ("fanstank_bart_clip_02.mp4",
     "Continuing from clip 1. The Cubs fan is desperately trying to look calm and speak into a sports microphone. "
     "However, the small hand emerging from his nose goes rogue and begins actively and rapidly spelling out the letters in "
     "American Sign Language (ASL) while his real arms are crossed tightly. Flat 2D vector style, bold outlines, glitchy VHS tracking lines.")
]

# 3. Load and Prepare Reference Images
print("[+] Preparing the 2 Mutant Reference Images...")
ref_images = []
for filename in REF_IMG_FILES:
    img_path = os.path.join(VEO_DIR, filename)
    mime = "image/png"
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    img = types.Image(imageBytes=img_bytes, mimeType=mime)
    ref_images.append(
        types.VideoGenerationReferenceImage(
            image=img,
            referenceType="ASSET"
        )
    )
print(f"[+] Loaded {len(ref_images)} reference images successfully.")

# 4. Generate the 2 Veo Clips
current_resolution = "720p"  # Fall back to 720p immediately for lightning speed and stability

for i, (filename, prompt) in enumerate(CLIP_PROMPTS):
    clip_num = i + 1
    output_path = os.path.join(VEO_DIR, filename)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"\n[+] CLIP {clip_num} already exists at {output_path}. Skipping...")
        continue
        
    print(f"\n[+] STARTING GENERATION FOR CLIP {clip_num}: {filename}")
    print(f"    Prompt: {prompt}")
    
    # Pass the previous video for scene extension (for clip 2)
    video_input = None
    refs_to_use = ref_images
    if clip_num > 1:
        prev_filename = CLIP_PROMPTS[i-1][0]
        prev_output_path = os.path.join(VEO_DIR, prev_filename)
        video_input = types.Video.from_file(location=prev_output_path)
        refs_to_use = None
        print(f"    --> Scene Extension enabled from previous clip: {prev_output_path}")
        
    def run_generation(res, refs):
        dur = 5  # Keep it short and sweet (5s) for fast polling
        config = types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution=res,
            duration_seconds=dur,
            reference_images=refs
        )
        return client.models.generate_videos(
            model="veo-3.1-generate-001",
            prompt=prompt,
            video=video_input,
            config=config
        )

    try:
        operation = run_generation(current_resolution, refs_to_use)
        
        # Poll until the operation is done
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
                    raise RuntimeError("No videos found in response!")
                
                print(f"    [+] Operation completed successfully! Extracting bytes...")
                video_b64 = videos[0].get("bytesBase64Encoded")
                video_bytes = base64.b64decode(video_b64)
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print(f"    [SUCCESS] Saved Clip {clip_num} to: {output_path}")
                break
                
            elapsed = time.time() - start_time
            print(f"    [Polling] Operation {operation.name} in progress (elapsed: {int(elapsed)}s)...")
            time.sleep(15)
            
    except Exception as e:
        print(f"    [ERROR] Failed generating Clip {clip_num}: {e}")
        raise e

# 5. Assemble Final Episode
print("\n[+] Assembling Final Cumulative Clip...")
final_output_path = os.path.join(VEO_DIR, "fanstank_bart_episode_01.mp4")
last_clip_filename, _ = CLIP_PROMPTS[-1]
last_clip_path = os.path.join(VEO_DIR, last_clip_filename)

try:
    import shutil
    shutil.copy2(last_clip_path, final_output_path)
    print(f"[SUCCESS] Saved final cumulative sequence to: {final_output_path}")
    
except Exception as e:
    print(f"[ERROR] Failed to save final episode: {e}")
    raise e

print("\n=== SYSTEM COMPLETE ===")
