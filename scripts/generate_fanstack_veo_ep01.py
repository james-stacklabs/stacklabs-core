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

# Initialize Client using Vertex AI for Agent Platform Project gen-lang-client-0840454416
client = genai.Client(
    vertexai=True,
    project="gen-lang-client-0840454416",
    location="us-central1"
)

# 2. Config Definitions
VEO_DIR = "/home/james/sovereign_inbox/today/veo"
os.makedirs(VEO_DIR, exist_ok=True)

# Load the 3 primary character reference sheets (2 for Barf, 1 for Dot)
REF_IMG_FILES = [
    "barf_ref_sheet_1.jpeg",
    "barf_ref_sheet_2.png",
    "dot_sheet_1.jpeg"
]


CLIP_PROMPTS = [
    # CLIP 1
    ("fanstack_clip_01.mp4", 
     "BARF is slumped behind the oak anchor desk in the VHS sports broadcast studio. "
     "Both bulging eyes half-crushed in psychological defeat. He squeezes a tiny Turk Wendell "
     "bobblehead with both paws until the seams visibly fray. DOT sits perfectly motionless beside him on the desk. "
     "DOT green LED ticker scrolls: EXPECTANCY VOID: CONSUME MEDS. Studio fluorescent lights buzz. "
     "VHS tracking lines flicker across frame. No dialogue. Pure despair."),
    
    # CLIP 2
    ("fanstack_clip_02.mp4",
     "Continuing from clip 1. BARF slams both paws on the oak desk and lurches upright screaming. "
     "The Turk Wendell bobblehead flies across frame in slow motion. DOT rotates dome head exactly 45 degrees to watch it fall. "
     "DOT green LED ticker updates to: CALF MUSCLE INTEGRITY: UNVERIFIED. Studio fluorescent lights flicker violently. "
     "Loose fur catches the light. VHS grain heavy."),
    
    # CLIP 3
    ("fanstack_clip_03.mp4",
     "Continuing from clip 2. Camera pulls back wide to reveal the full sports bar behind the anchor desk. "
     "Packed with puppet fans in team jerseys — Mets blue and orange, Yankees pinstripes, Marlins teal — "
     "all frozen in various states of existential horror. One puppet in a 7 Train conductor hat has his head face down on the bar. "
     "Hand-painted scoreboard on back wall reads NYM 1 MIA 2. BARF visible in foreground staring into the void. "
     "DOT ticker reads: CROWD AFFECT: IRRELEVANT. VHS grain throughout."),
    
    # CLIP 4
    ("fanstack_clip_04.mp4",
     "Continuing from clip 3. Tight close-up on BARF's face. PANIC expression. "
     "He slowly raises a tiny hand-written cardboard sign reading $765M and stares directly into the camera. "
     "A single tear rolls down his cheek. DOT ticker reads: THIS IS FINE: CALCULATING. "
     "Studio lights dim to a single overhead spot on BARF. Distant stadium crowd noise fades in. "
     "VHS tracking lines crawl across frame. Slow fade to black.")
]

# 3. Load and Prepare Reference Images
print("[+] Preparing the 3 Reference Images (API limit cap)...")
ref_images = []
for filename in REF_IMG_FILES:
    img_path = os.path.join(VEO_DIR, filename)
    mime = "image/png" if filename.endswith(".png") else "image/jpeg"
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

# 4. Generate the 4 Veo Clips
video_objects = {}
current_resolution = "1080p"

for i, (filename, prompt) in enumerate(CLIP_PROMPTS):
    clip_num = i + 1
    output_path = os.path.join(VEO_DIR, filename)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"\n[+] CLIP {clip_num} already exists at {output_path} ({os.path.getsize(output_path)} bytes). Skipping generation...")
        continue
        
    print(f"\n[+] STARTING GENERATION FOR CLIP {clip_num}: {filename}")
    print(f"    Prompt: {prompt}")
    
    # Pass the previous video for scene extension (for clips 2, 3, 4)
    video_input = None
    refs_to_use = ref_images
    if clip_num > 1:
        prev_filename = CLIP_PROMPTS[i-1][0]
        prev_output_path = os.path.join(VEO_DIR, prev_filename)
        video_input = types.Video.from_file(location=prev_output_path)
        refs_to_use = None
        print(f"    --> Enabling Scene Extension from previous clip file: {prev_output_path} (Reference images disabled for extension)")
        
    def run_generation(res, refs):
        dur = 7 if video_input else 8
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
        try:
            ref_count = len(refs_to_use) if refs_to_use else 0
            print(f"    Submitting video generation request at {current_resolution} with {ref_count} reference images...")
            operation = run_generation(current_resolution, refs_to_use)
        except Exception as api_err:
            err_str = str(api_err).upper()
            # Handle reference image count limits
            if any(term in err_str for term in ["REFERENCE_IMAGE", "IMAGE_LIMIT", "REFERENCE", "LIMIT", "TOO_MANY"]):
                print(f"    [WARNING] Reference image limit error: {api_err}")
                print("    --> Retrying with 3 primary reference images...")
                try:
                    operation = run_generation(current_resolution, refs_to_use[:3] if refs_to_use else None)
                except Exception as api_err2:
                    err_str2 = str(api_err2).upper()
                    if "RESOLUTION" in err_str2 or "720P" in err_str2 or "INVALID_ARGUMENT" in api_err2:
                        print(f"    [WARNING] Resolution fallback needed during fallback: {api_err2}")
                        current_resolution = "720p"
                        operation = run_generation(current_resolution, refs_to_use[:3] if refs_to_use else None)
                    else:
                        raise api_err2
            elif "RESOLUTION" in err_str or "720P" in err_str or "INVALID_ARGUMENT" in err_str:
                print(f"    [WARNING] Generation at {current_resolution} failed: {api_err}")
                print("    --> Attempting fallback to 720p...")
                current_resolution = "720p"
                operation = run_generation(current_resolution, refs_to_use)
            else:
                raise api_err
        
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
                
                # Extracted raw video predictions
                resp = raw_dict.get("response", {})
                videos = resp.get("videos", [])
                if not videos:
                    raise RuntimeError("No videos found in response predictions!")
                
                # Decode and write video bytes directly
                print(f"    [+] Operation completed successfully! Extracting bytes...")
                video_b64 = videos[0].get("bytesBase64Encoded")
                video_bytes = base64.b64decode(video_b64)
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print(f"    [SUCCESS] Saved Clip {clip_num} to: {output_path}")
                print(f"    File Size: {os.path.getsize(output_path)} bytes")
                break
                
            elapsed = time.time() - start_time
            print(f"    [Polling] Operation {operation.name} in progress (elapsed: {int(elapsed)}s)...")
            time.sleep(15)
            
    except Exception as e:
        print(f"    [ERROR] Failed generating Clip {clip_num}: {e}")
        raise e

# 5. Save the final cumulative clip as the final episode
print("\n[+] Initiating Final Episode Assembly...")
final_output_path = os.path.join(VEO_DIR, "fanstack_barf_episode_01.mp4")
last_clip_filename, _ = CLIP_PROMPTS[-1]
last_clip_path = os.path.join(VEO_DIR, last_clip_filename)

print(f"    Veo 3.1 video extensions are natively cumulative.")
print(f"    Extracting final cumulative scene extension from: {last_clip_path}")

try:
    # Copy the final cumulative clip to the final output file
    import shutil
    shutil.copy2(last_clip_path, final_output_path)
    print(f"[SUCCESS] Saved final cumulative sequence to: {final_output_path}")
    
except Exception as e:
    print(f"[ERROR] Failed to save final episode: {e}")
    raise e

# 6. Verify and Print File Sizes
print("\n=== FINAL FILE SIZE VERIFICATION ===")
files_to_check = [
    "fanstack_clip_01.mp4",
    "fanstack_clip_02.mp4",
    "fanstack_clip_03.mp4",
    "fanstack_clip_04.mp4",
    "fanstack_barf_episode_01.mp4"
]

for filename in files_to_check:
    path = os.path.join(VEO_DIR, filename)
    if os.path.exists(path):
        size_bytes = os.path.getsize(path)
        size_mb = size_bytes / (1024 * 1024)
        print(f"📄 {filename}: {size_bytes} bytes ({size_mb:.2f} MB)")
    else:
        print(f"❌ {filename} does not exist!")

print("\n=== SYSTEM COMPLETE ===")
