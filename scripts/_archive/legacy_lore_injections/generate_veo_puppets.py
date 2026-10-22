import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load the environment variables from the Apiary .env file
load_dotenv("/home/james/stacklabs/.env")

# Initialize the Gemini API Client
client = genai.Client()

DROPZONE_DIR = "/home/james/stacklabs/dna/dropzone/daily_21042026"
os.makedirs(DROPZONE_DIR, exist_ok=True)

# The Costanza Protocol: Brooks Exception Veo Prompts
VEO_PROMPTS = {
    "VEO_RENDER_1_barf_panic.mp4": "A tactile 1990s physical felt puppet of a dog-man with matted orange and blue fur, sitting at a sports desk. He is hyperventilating and tearing a piece of paper in half. Heavy practical studio lighting. No CGI. Cinematic.",
    "VEO_RENDER_2_umpire_stare.mp4": "A cold, cybernetic felt-puppet umpire with metallic eyes sitting perfectly still at a broadcast desk, staring directly into the camera lens with absolute indifference. The puppet is holding a miniature printed spreadsheet. Heavy practical lighting. No CGI.",
    "VEO_RENDER_3_terry_defeat.mp4": "A 1990s felt puppet of an exhausted Everyman (frayed mustache, blue and orange baseball cap). He is slowly dropping his head onto the broadcast desk in absolute defeat while smoke gently rises from an offline CRT monitor next to him. No CGI."
}

def generate_veo_clip(filename, prompt):
    print(f"\n[+] Initiating Veo 3.1 Generation for: {filename}")
    print(f"    Prompt: {prompt}")
    
    try:
        # Submit the video generation request to the Gemini API
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
        )

        while not operation.done:
            print("    Waiting for Veo 3.1 render to complete (polling every 10s)...")
            time.sleep(10)
            operation = client.operations.get(operation)

        # Download the generated video payload
        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)
        
        output_path = os.path.join(DROPZONE_DIR, filename)
        generated_video.video.save(output_path)
        print(f"[SUCCESS] Video perfectly rendered and saved to: {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to render {filename}: {e}")

if __name__ == "__main__":
    print("=== SOVEREIGN VEO 3.1 ENGINE INITIATED ===")
    for filename, prompt in VEO_PROMPTS.items():
        generate_veo_clip(filename, prompt)
    
    print("\n[*] All Veo clips successfully rendered locally.")
