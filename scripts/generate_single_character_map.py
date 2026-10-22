#!/usr/bin/env python3
import os
import sys
import time
import sqlite3
import argparse
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# Environment & Constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(WORKSPACE_DIR, "dna", "sovereign_now.db")
SA_KEY_PATH = os.path.join(WORKSPACE_DIR, "config", "vertex_sa.json")

FOLDER_MAPPING = {
    "WEEDSTACK": "WeedStack",
    "STACKLABS": "StackLabs",
    "UNHINGEDCONVENIENCE": "Gonzo's Convenience",
    "ANVILANDTWINE": "Anvil & Twine Hardware"
}

def init_vertex():
    if not os.path.exists(SA_KEY_PATH):
        print(f"❌ Error: Service Account credentials not found at {SA_KEY_PATH}")
        sys.exit(1)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SA_KEY_PATH
    print("Initializing Vertex AI platform...")
    try:
        vertexai.init(project='gen-lang-client-0840454416', location='us-central1')
        model = ImageGenerationModel.from_pretrained('imagen-3.0-generate-002')
        print("Vertex AI Imagen 3.0 successfully initialized.")
        return model
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        sys.exit(1)

def get_characters_from_db(brand_key, character_key=None, style_name=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT character_key, prompt_text, style_name FROM sys_character_prompt WHERE brand_key = ?"
    params = [brand_key]
    
    if character_key and character_key.upper() != "ALL":
        query += " AND character_key = ?"
        params.append(character_key)
        
    if style_name:
        query += " AND style_name = ?"
        params.append(style_name)
        
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def main():
    parser = argparse.ArgumentParser(description="Generic Character Map Image Generator using Vertex AI Imagen 3.0")
    parser.add_argument("brand", help="Brand key (e.g. WEEDSTACK, STACKLABS, UNHINGEDCONVENIENCE, ANVILANDTWINE)")
    parser.add_argument("character", nargs="?", default="ALL", help="Character key (e.g. dr_terp) or ALL (default)")
    parser.add_argument("--style", help="Filter by specific style name in the database")
    args = parser.parse_args()
    
    brand_key = args.brand.upper().strip()
    
    # Query brand info to verify brand exists
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT brand_key, aesthetic_title FROM cmdb_ci_stack WHERE brand_key = ?", (brand_key,))
    brand_row = c.fetchone()
    conn.close()
    
    if not brand_row:
        print(f"❌ Error: Brand '{brand_key}' not found in database registry (cmdb_ci_stack).")
        sys.exit(1)
        
    aesthetic_title = brand_row[1]
    
    # Resolve target directory
    folder_name = FOLDER_MAPPING.get(brand_key, brand_key)
    target_dir = os.path.join("/home/james/sovereign_inbox/today", folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    characters = get_characters_from_db(brand_key, args.character, args.style)
    if not characters:
        print(f"⚠️ No character prompt records found for brand '{brand_key}' with character '{args.character}'")
        sys.exit(0)
        
    print(f"\n=======================================================")
    print(f"🎨 GENERATING CHARACTER MAPS FOR: {brand_key}")
    print(f"📂 Output directory: {target_dir}")
    print(f"👥 Found {len(characters)} matching character prompts in DB.")
    print(f"=======================================================")
    
    model = init_vertex()
    
    for idx, char in enumerate(characters):
        char_key = char["character_key"]
        prompt = char["prompt_text"]
        style = char["style_name"]
        
        print(f"\n[{idx+1}/{len(characters)}] Character: {char_key} ({style})")
        print(f"  Prompt: {prompt[:120]}...")
        
        # We will generate 2 variants per character to match original behavior
        for variant in [1, 2]:
            suffix = f"_{variant}" if variant > 1 else ""
            filename = f"{char_key}_reference_sheet_20260528{suffix}.jpeg"
            filepath = os.path.join(target_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"  Removed old map: {filename}")
                except Exception as e:
                    print(f"  Failed to remove old file: {e}")
                    
            print(f"  Generating variant {variant} -> {filename}...")
            success = False
            retry_count = 0
            max_retries = 5
            
            while not success and retry_count < max_retries:
                try:
                    response = model.generate_images(
                        prompt=prompt,
                        number_of_images=1,
                        aspect_ratio="1:1",
                        safety_filter_level="block_some",
                        person_generation="allow_adult"
                    )
                    
                    if response.images:
                        response.images[0].save(location=filepath, include_generation_parameters=False)
                        print(f"  ✓ Saved variant {variant} successfully.")
                        success = True
                    else:
                        print("  ✗ Empty response received from Vertex AI.")
                        break
                except Exception as e:
                    err_msg = str(e)
                    if "Quota exceeded" in err_msg or "429" in err_msg:
                        retry_count += 1
                        wait_time = 35 * retry_count
                        print(f"  ⚠️ Quota limit hit (429). Sleeping {wait_time}s before retry {retry_count}/{max_retries}...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ✗ Failed to generate: {e}")
                        break
            
            if success:
                # Small rate-limiting sleep between variants
                time.sleep(3)
                
    print("\n✅ Character map generation complete!")

if __name__ == "__main__":
    main()
