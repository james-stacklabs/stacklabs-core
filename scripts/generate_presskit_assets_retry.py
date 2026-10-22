#!/usr/bin/env python3
"""
generate_presskit_assets_retry.py
Robust retry script for generating missing press kit assets, handling 429 quotas.
"""
import os
import time
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

OUTPUT_DIR = "/home/james/sovereign_inbox/dashboards/presskit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"

print(f"Initializing Vertex AI with Project ID: {PROJECT_ID}...")
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)

print("Loading ImageGenerationModel (imagen-3.0-generate-001)...")
model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

ASSETS = [
    {
        "filename": "sovereign_os_architecture.png",
        "prompt": (
            "Dark premium technical illustration, 16:9 landscape. "
            "Central dark monolithic core labeled 'SOVEREIGN OS' glowing with cyan light. "
            "Three ROM module shapes plugging into it: one cyan labeled 'FANSTACK', "
            "one green labeled 'WEEDSTACK', one dim gray labeled 'YOUR STACK HERE'. "
            "Thin light data flow lines connecting core to modules. "
            "Bottom: single glowing edge hardware node labeled 'NODE CLIO — AMD ZEN 4' "
            "with a heartbeat pulse. No cloud icons. Deep black background. "
            "Bloomberg terminal meets premium spirits brand aesthetic. "
            "Cinematic, architectural, confident."
        ),
    },
    {
        "filename": "mard_engine_visual.png",
        "prompt": (
            "Dark cinematic illustration, 16:9. A premium digital war room. "
            "Multiple AI persona avatar silhouettes arranged around a circular table, "
            "each glowing in their team color (cyan, green, amber). "
            "Central pulsing data node on the table labeled 'LIVE FEED'. "
            "Light lines connecting feed to each persona. "
            "Floating content cards above showing social posts and chat messages. "
            "Corner panel showing toggle switches — some glowing green ON, some dark STANDBY. "
            "Deep black background. Intimate but powerful. Premium hacker den aesthetic. "
            "No generic tech imagery. Cinematic lighting."
        ),
    },
    {
        "filename": "bar_question_hero.png",
        "prompt": (
            "Minimalist dark typographic poster, 16:9. "
            "Deep near-black background. "
            "Large clean sans-serif white text centered: "
            "'If your brand walked into a bar — who would it be, what would it order, "
            "what would it play on the jukebox, and who would it talk to?' "
            "Below in small monospace type: 'POST /api/stacks/seed' "
            "Nothing else. No decoration. No illustration. "
            "The question IS the image. "
            "Billboard confidence. Premium editorial aesthetic."
        ),
    },
    {
        "filename": "edge_node_hero.png",
        "prompt": (
            "Dark dramatic product photography style illustration. "
            "Single compact hardware box (Mac Studio style) on a dark surface. "
            "Dramatic side lighting, glowing vents. "
            "Single ethernet cable. No racks, no data centers. Just one box. "
            "Floating above it in clean white type: 'MARGINAL COST: $0.00' "
            "Below in smaller type: 'after silicon' "
            "Deep black background. Anti-cloud manifesto as product photo. "
            "Confident. Architectural. Cinematic."
        ),
    },
    {
        "filename": "content_source_matrix.png",
        "prompt": (
            "Dark premium UI dashboard screenshot illustration, 16:9. "
            "Clean dark panel showing a list of seven content source toggles. "
            "Labels: Batch Drop Events, Cannabis Industry News, COA Lab Results, "
            "Reddit Communities, Competitor Drops, Pricing Feed, Harvest Reports. "
            "Two toggles glowing green (ON). Five toggles dark gray (STANDBY). "
            "A cursor hovering over the Reddit toggle. "
            "Corner: small live chat feed updating in real time. "
            "Sovereign OS dark glassmorphic design language. "
            "Green accent color #00c878. Deep black background. "
            "Control and precision. The operator is in command."
        ),
    },
]

for asset in ASSETS:
    out_path = os.path.join(OUTPUT_DIR, asset["filename"])
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"✅ {asset['filename']} already exists. Skipping.")
        continue

    print(f"\nGenerating: {asset['filename']}...")
    success = False
    retries = 5
    backoff = 20

    for attempt in range(1, retries + 1):
        try:
            print(f"  Attempt {attempt}/{retries}...")
            response = model.generate_images(
                prompt=asset["prompt"],
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="block_some",
                person_generation="dont_allow",
            )
            response.images[0].save(location=out_path, include_generation_parameters=False)
            print(f"  ✅ Saved: {out_path}")
            success = True
            break
        except Exception as e:
            print(f"  ❌ Attempt {attempt} failed: {e}")
            if attempt < retries:
                sleep_time = backoff * attempt
                print(f"  Sleeping for {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print(f"  ❌ All retries failed for {asset['filename']}")

    if success:
        # Prevent immediate 429 on the next file
        print("Sleeping 15 seconds between different assets...")
        time.sleep(15)

print("\nPress kit retry generation flow complete.")
