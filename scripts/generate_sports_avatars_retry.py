import os
import sys
import time
import base64
import sqlite3
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

# Define the missing commentators, their prompts, and team keys
MISSING_COMMENTATORS = [
    {
        "id": "stadium_phantom_stl",
        "team": "UFL",
        "prompt": "Textured Acrylic Canvas Overlay painting of the STL BattleDome King, a fanatical spring-league football ultra fan. Intense desaturated stadium lights, rough industrial concrete textures, weathered hoodie fabric. Wild fanatical expression. Solid dark background.",
    },
    {
        "id": "gang_green_greg",
        "team": "NYJ",
        "prompt": "Grimy 1990s MTV-Style Underground Cartoon illustration of MetLife Meltdown. A matted, grey felt gundog puppet with mismatched, frantic googly eyes, looking completely traumatized and stressed. Mud-stained canvas textures and heavily saturated dark charcoal cross-hatched outlines. Solid black background.",
    },
    {
        "id": "gridiron_gary",
        "team": "PIT",
        "prompt": "Harsh, heavy ink comic sketch of Gary, a hard-nosed industrial steel-worker accountant puppet, wearing a yellow safety hardhat, clutching an ancient mechanical calculator. Volumetric iron dust grit textures. Grim analytical expression. Solid dark background.",
    },
    {
        "id": "tundra_tim",
        "team": "GB",
        "prompt": "Weather-Beaten Canvas Oil Painting portrait of Frozen Tundra Tim, a weathered green-bay purist fan wearing a heavy, snow-covered canvas coat. Textured, desaturated frostbite palettes, heavy ice-cracked frost overlay frames, frozen breath. Weather-beaten stoic expression. Solid dark background.",
    }
]

def generate_image(model, prompt):
    # Try generating image
    try:
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1"
        )
        return response[0]._image_bytes
    except AttributeError:
        # Fallback to response.images[0] for older SDK versions
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1"
        )
        return response.images[0]._image_bytes

def main():
    PROJECT_ID = "gen-lang-client-0840454416"
    LOCATION = "us-central1"
    CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
    
    if os.path.exists(CREDENTIALS_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        print(f"🔑 Using Vertex SA credentials from {CREDENTIALS_PATH}")

    print("🌩️ Initializing Vertex AI...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    # Load models
    model_3 = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    model_fallback = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    for c in MISSING_COMMENTATORS:
        print(f"\n🎨 Forging premium avatar for @{c['id']}...")
        print(f"👉 Prompt: {c['prompt']}")
        
        img_bytes = None
        
        # Try Imagen 3.0 first
        try:
            print("Trying Imagen 3.0 (v001)...")
            img_bytes = generate_image(model_3, c['prompt'])
            print("✅ Successfully generated with Imagen 3.0 (v001)!")
        except Exception as e:
            print(f"⚠️ Imagen 3.0 (v001) failed or rate-limited: {e}")
            print("🔄 Falling back to imagen-3.0-generate-002...")
            try:
                img_bytes = generate_image(model_fallback, c['prompt'])
                print("✅ Successfully generated with imagen-3.0-generate-002!")
            except Exception as fe:
                print(f"❌ Fallback model 002 also failed: {fe}")
                
        if img_bytes:
            b64_str = base64.b64encode(img_bytes).decode('utf-8')
            data_url = f"data:image/png;base64,{b64_str}"
            
            # Save to public directory for static file fallback
            pub_dir = f"/home/james/stacklabs/15_FanStack/public/avatars"
            os.makedirs(pub_dir, exist_ok=True)
            file_path = os.path.join(pub_dir, f"{c['id']}.png")
            with open(file_path, "wb") as f:
                f.write(img_bytes)
            print(f"💾 Static fallback image saved to: {file_path}")
            
            # Update the SQLite DB (both avatar_blob and avatar_url)
            cur.execute(
                "UPDATE persona SET avatar_blob = ?, avatar_url = ?, color = ? WHERE user_name = ?",
                (data_url, f"/avatars/{c['id']}.png", None, c['id'])
            )
            con.commit()
            print(f"🚀 SQLite DB record updated for {c['id']}!")
        
        # Sleep to avoid rate limit/quota limits
        print("Sleeping 30 seconds to respect API quota boundaries...")
        time.sleep(30)
            
    con.close()
    print("\n🏁 Roster avatar forge retry pipeline complete!")

if __name__ == '__main__':
    main()
