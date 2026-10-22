import os
import sys
import base64
import sqlite3
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

# Define the commentators, their prompts, and team keys
COMMENTATORS = [
    {
        "id": "spring_league_stalwart",
        "team": "UFL",
        "prompt": "Gritty 1990s Underground Comic Print style portrait of Barty Vance, a weathered, intense spring-league journeyman football linebacker. Harsh cross-hatched ink shading, deep midnight charcoal accents, and heavy sweat-and-turf grit texture maps. Aggressive, veteran expression. Solid black background.",
    },
    {
        "id": "chip_telemetry_tom",
        "team": "UFL",
        "prompt": "High-Contrast Blueprint Technical Sketch of Tom, a data-obsessed football analyst scout. Matte slate backplate, crisp ivory diagram outlines, schematic layout and technical blueprint drawing lines. Serious intellectual analytical expression. Solid dark background.",
    },
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
        "id": "star_delusion",
        "team": "DAL",
        "prompt": "High-Contrast Premium Screen Print vector illustration of Lone Star Larry, a delusional Cowboys zealot cowboy puppet made of coarse yellow foam, with wide unblinking wobbly pupils. Shiny royal blue and silver star cowboy hat, clutching a vintage 1990s championship trophy like a religious relic. Delusional, smug grin. Solid navy background.",
    },
    {
        "id": "tundra_tim",
        "team": "GB",
        "prompt": "Weather-Beaten Canvas Oil Painting portrait of Frozen Tundra Tim, a weathered green-bay purist fan wearing a heavy, snow-covered canvas coat. Textured, desaturated frostbite palettes, heavy ice-cracked frost overlay frames, frozen breath. Weather-beaten stoic expression. Solid dark background.",
    }
]

def main():
    PROJECT_ID = "gen-lang-client-0840454416"
    LOCATION = "us-central1"
    CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
    
    if os.path.exists(CREDENTIALS_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
        print(f"🔑 Using Vertex SA credentials from {CREDENTIALS_PATH}")
    else:
        print("⚠️ Warning: Vertex SA credentials not found, using ambient environment.")

    sys.path.append("/home/james/stacklabs/scripts")
    from imagen_util import generate_imagen_avatar
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    for c in COMMENTATORS:
        print(f"\n🎨 Forging premium avatar for @{c['id']}...")
        print(f"👉 Prompt: {c['prompt']}")
        
        pub_dir = f"/home/james/stacklabs/15_FanStack/public/avatars"
        os.makedirs(pub_dir, exist_ok=True)
        file_path = os.path.join(pub_dir, f"{c['id']}.png")
        
        success, res_path = generate_imagen_avatar(
            prompt=c['prompt'],
            output_path=file_path,
            aspect_ratio="1:1"
        )
        if success:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            b64_str = base64.b64encode(img_bytes).decode('utf-8')
            data_url = f"data:image/png;base64,{b64_str}"
            
            cur.execute(
                "UPDATE persona SET avatar_blob = ?, avatar_url = ?, color = ? WHERE user_name = ?",
                (data_url, f"/avatars/{c['id']}.png", None, c['id'])
            )
            print(f"🚀 SQLite DB record updated for {c['id']}!")
        else:
            print(f"❌ Failed to forge avatar for {c['id']}: {res_path}")
            
    con.commit()
    con.close()
    print("\n🏁 Avatar forging pipeline complete!")

if __name__ == '__main__':
    main()
