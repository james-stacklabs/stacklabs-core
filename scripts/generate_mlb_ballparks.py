#!/usr/bin/env python3
"""
Sovereign OS: MLB 30 Ballparks Day & Night Asset Generator
Path: /home/james/stacklabs/scripts/generate_mlb_ballparks.py

Generates 60 high-fidelity 16:9 photographic stadium arena backdrop images
(1 Day game, 1 Night game for all 30 active MLB ballparks) using Vertex AI Imagen 3.
Stores output in: /home/james/stacklabs/19_Sovereign_Sports/public/ballparks/
"""

import os
import sys
import time
import argparse
import logging
from io import BytesIO
from typing import Dict, List, Any
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, "/home/james/stacklabs")

from google.genai import types
from scripts.imagen_util import get_imagen_client, verify_imagen_model_health

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [BallparkGen]: %(message)s"
)
logger = logging.getLogger("BallparkGen")

OUTPUT_DIR = "/home/james/stacklabs/19_Sovereign_Sports/public/ballparks"

# 30 Active MLB Teams & Ballparks Ground-Truth Manifest
MLB_BALLPARKS = [
    {
        "team": "ARI",
        "name": "Chase Field",
        "city": "Phoenix, Arizona",
        "slug": "chase_field",
        "landmarks": "massive retractable roof, iconic right-center field swimming pool and hot tub, high air-conditioned steel trusses, desert-toned stadium seating",
    },
    {
        "team": "ATL",
        "name": "Truist Park",
        "city": "Atlanta, Georgia",
        "slug": "truist_park",
        "landmarks": "classic red brick exterior façade, multi-level Chop House deck in right field, manicured Bermuda grass field, vibrant modern concourses",
    },
    {
        "team": "BAL",
        "name": "Oriole Park at Camden Yards",
        "city": "Baltimore, Maryland",
        "slug": "camden_yards",
        "landmarks": "historic eight-story B&O Railroad Warehouse towering over right field, Eutaw Street concourse, dark green steel trusses, retro-classic ballpark architecture",
    },
    {
        "team": "BOS",
        "name": "Fenway Park",
        "city": "Boston, Massachusetts",
        "slug": "fenway_park",
        "landmarks": "towering 37-foot Green Monster wall in left field with manual scoreboard and rooftop seats, Pesky's Pole in right field, historic vintage wooden ballpark charm",
    },
    {
        "team": "CHC",
        "name": "Wrigley Field",
        "city": "Chicago, Illinois",
        "slug": "wrigley_field",
        "landmarks": "iconic dark green ivy-covered brick outfield walls, historic center-field manual scoreboard with rooftop bleachers across Waveland and Sheffield Avenues",
    },
    {
        "team": "CWS",
        "name": "Guaranteed Rate Field",
        "city": "Chicago, Illinois",
        "slug": "guaranteed_rate_field",
        "landmarks": "celebrated exploding pinwheel scoreboard with spinning multi-colored lights in center field, modern open concourses, south side Chicago skyline",
    },
    {
        "team": "CIN",
        "name": "Great American Ball Park",
        "city": "Cincinnati, Ohio",
        "slug": "great_american_ball_park",
        "landmarks": "twin white riverboat smokestacks in center field shooting fireworks and steam, Ohio River and Kentucky hills visible beyond the outfield pavilion",
    },
    {
        "team": "CLE",
        "name": "Progressive Field",
        "city": "Cleveland, Ohio",
        "slug": "progressive_field",
        "landmarks": "distinctive vertical white toothbrush light towers rising high into the sky, towering left-field mini-monster wall, downtown Cleveland terminal tower skyline",
    },
    {
        "team": "COL",
        "name": "Coors Field",
        "city": "Denver, Colorado",
        "slug": "coors_field",
        "landmarks": "center-field rock garden with Colorado spruce pines, cascading water fountains, red brick masonry, distant purple-hued Rocky Mountain horizon",
    },
    {
        "team": "DET",
        "name": "Comerica Park",
        "city": "Detroit, Michigan",
        "slug": "comerica_park",
        "landmarks": "massive stainless steel roaring tiger statues, fountain water displays in center field, majestic view of the downtown Detroit historic skyline",
    },
    {
        "team": "HOU",
        "name": "Minute Maid Park",
        "city": "Houston, Texas",
        "slug": "minute_maid_park",
        "landmarks": "historic 1860s replica steam locomotive running along an 800-foot track high above the left-field wall, retractable roof, Crawford Boxes",
    },
    {
        "team": "KC",
        "name": "Kauffman Stadium",
        "city": "Kansas City, Missouri",
        "slug": "kauffman_stadium",
        "landmarks": "celebrated 322-foot wide Water Spectacular fountain cascading across outfield plaza, massive crown-shaped high-definition video board in center field",
    },
    {
        "team": "LAA",
        "name": "Angel Stadium",
        "city": "Anaheim, California",
        "slug": "angel_stadium",
        "landmarks": "left-center field California rock formation with artificial geysers shooting water and pyrotechnics, towering A-frame Big A halo sign visible in distance",
    },
    {
        "team": "LAD",
        "name": "Dodger Stadium",
        "city": "Los Angeles, California",
        "slug": "dodger_stadium",
        "landmarks": "iconic hexagonal wavy pavilion roofs, towering palm trees flanking the pavilions, serene backdrop of the sun-drenched Elysian Park and San Gabriel Mountains",
    },
    {
        "team": "MIA",
        "name": "loanDepot park",
        "city": "Miami, Florida",
        "slug": "loandepot_park",
        "landmarks": "sleek contemporary white aerodynamic retractable dome, vibrant neon-accented architecture, glass operable outfield wall framing Little Havana skyline",
    },
    {
        "team": "MIL",
        "name": "American Family Field",
        "city": "Milwaukee, Wisconsin",
        "slug": "american_family_field",
        "landmarks": "massive fan-shaped arched retractable roof structure, colorful Bernie Brewer yellow slide in left-field territory, modern baseball cathedral",
    },
    {
        "team": "MIN",
        "name": "Target Field",
        "city": "Minneapolis, Minnesota",
        "slug": "target_field",
        "landmarks": "native warm golden Kasota limestone masonry, glowing neon Minnie and Paul handshaking emblem in center field, downtown Minneapolis skyline",
    },
    {
        "team": "NYM",
        "name": "Citi Field",
        "city": "Flushing, Queens, New York",
        "slug": "citi_field",
        "landmarks": "giant motorized red Home Run Apple in center field, classic Ebbets Field inspired red brick façade, Jackie Robinson Rotunda archways, dark green seats",
    },
    {
        "team": "NYY",
        "name": "Yankee Stadium",
        "city": "Bronx, New York",
        "slug": "yankee_stadium",
        "landmarks": "regal white exterior limestone façade, iconic signature white roofline frieze bordering the upper deck, Monument Park beyond the center-field fence",
    },
    {
        "team": "OAK",
        "name": "Sutter Health Park",
        "city": "West Sacramento, California",
        "slug": "sutter_health_park",
        "landmarks": "picturesque gold-hued Tower Bridge and Sacramento downtown skyline looming just across the river, intimate open-air natural grass riverfront ballpark",
    },
    {
        "team": "PHI",
        "name": "Citizens Bank Park",
        "city": "Philadelphia, Pennsylvania",
        "slug": "citizens_bank_park",
        "landmarks": "gigantic 102-foot neon Liberty Bell towering over right-center field that glows and sways, open Ashburn Alley concourse, downtown skyline view",
    },
    {
        "team": "PIT",
        "name": "PNC Park",
        "city": "Pittsburgh, Pennsylvania",
        "slug": "pnc_park",
        "landmarks": "magnificent bright yellow Roberto Clemente Sixth Street Bridge directly framing the Allegheny River and the glittering golden Pittsburgh city skyline",
    },
    {
        "team": "SD",
        "name": "Petco Park",
        "city": "San Diego, California",
        "slug": "petco_park",
        "landmarks": "historic 1909 Western Metal Supply Co. red brick warehouse serving as the left-field foul pole, palm trees, sunny downtown San Diego gaslamp backdrop",
    },
    {
        "team": "SF",
        "name": "Oracle Park",
        "city": "San Francisco, California",
        "slug": "oracle_park",
        "landmarks": "scenic San Francisco Bay and McCovey Cove right past the right-field brick wall, giant vintage Coca-Cola bottle slide and four-fingered glove above left field bleachers",
    },
    {
        "team": "SEA",
        "name": "T-Mobile Park",
        "city": "Seattle, Washington",
        "slug": "t_mobile_park",
        "landmarks": "massive rolling retractable umbrella steel roof, historic exposed industrial steelwork, views toward Puget Sound and container port cranes",
    },
    {
        "team": "STL",
        "name": "Busch Stadium",
        "city": "St. Louis, Missouri",
        "slug": "busch_stadium",
        "landmarks": "majestic soaring stainless steel Gateway Arch perfectly framing the open center-field vista against the St. Louis downtown panorama, red brick concourses",
    },
    {
        "team": "TB",
        "name": "Tropicana Field",
        "city": "St. Petersburg, Florida",
        "slug": "tropicana_field",
        "landmarks": "distinctive slanted translucent dome roof supported by catwalk rings, vibrant teal and navy seats, indoor natural field lighting",
    },
    {
        "team": "TEX",
        "name": "Globe Life Field",
        "city": "Arlington, Texas",
        "slug": "globe_life_field",
        "landmarks": "vast 5.5-acre modern single-panel transparent retractable roof, mammoth center-field videoboard, sleek modern architecture with climate-controlled comfort",
    },
    {
        "team": "TOR",
        "name": "Rogers Centre",
        "city": "Toronto, Ontario",
        "slug": "rogers_centre",
        "landmarks": "colossal CN Tower soaring immediately adjacent to the open motorized dome roof, modern renovated outfield district bleachers, downtown Toronto vibe",
    },
    {
        "team": "WSH",
        "name": "Nationals Park",
        "city": "Washington, D.C.",
        "slug": "nationals_park",
        "landmarks": "sleek contemporary glass and steel stadium architecture, views of the U.S. Capitol dome in the distance, Anacostia River waterfront neighborhood",
    }
]

def build_prompt(ballpark: Dict[str, Any], mode: str) -> str:
    """Constructs a high-fidelity photographic prompt for Day or Night modes."""
    name = ballpark["name"]
    city = ballpark["city"]
    landmarks = ballpark["landmarks"]

    if mode == "day":
        return (
            f"Photorealistic wide cinematic broadcast photograph of {name} baseball stadium in {city}, "
            f"viewed from behind home plate looking out across the infield diamond toward the outfield fences and bleachers on a brilliant sunny afternoon day game. "
            f"Bright natural sunlight casting crisp shadows across the dirt basepaths and manicured striped green grass. "
            f"Full stadium bowl architecture clearly visible, featuring {landmarks}. "
            f"Clear blue daytime sky with light wispy clouds overhead. Clean professional Major League Baseball television broadcast angle, wide angle 16:9 aspect ratio, 8k resolution, authentic stadium details, zero blur, no cartoon elements."
        )
    else:  # night
        return (
            f"Photorealistic wide cinematic broadcast photograph of {name} baseball stadium in {city}, "
            f"viewed from behind home plate looking out across the infield diamond toward the outfield fences and bleachers during a marquee night game at twilight. "
            f"Blazing high-intensity stadium floodlights illuminating the lush green grass and rich brown clay diamond under dramatic deep indigo and warm twilight dusk skies. "
            f"Stadium bowl illuminated with stadium lights and electronic outfield ribbon boards, showcasing {landmarks}. "
            f"Atmospheric evening ballpark ambiance, Major League Baseball television broadcast camera angle, wide angle 16:9 aspect ratio, 8k resolution, photorealistic architectural perfection, zero blur, no cartoon elements."
        )

def generate_ballpark_image(
    client: Any,
    model_name: str,
    prompt: str,
    output_filepath: str,
    dry_run: bool = False
) -> bool:
    """Generates a single ballpark image and saves it as high-quality JPEG."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would generate -> {output_filepath}")
        return True

    try:
        res = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9"
            )
        )
        if res and res.generated_images:
            image_data = res.generated_images[0].image.image_bytes
            with Image.open(BytesIO(image_data)) as img:
                img.convert("RGB").save(output_filepath, format="JPEG", quality=92, optimize=True)
            logger.info(f"✅ Successfully saved: {output_filepath} ({os.path.getsize(output_filepath)} bytes)")
            return True
        else:
            logger.error(f"❌ Empty response from Imagen for: {output_filepath}")
            return False
    except Exception as e:
        logger.error(f"❌ Error generating {output_filepath}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate Day/Night Ballpark Assets for MLB")
    parser.add_argument("--team", help="Specific team code (e.g. NYM, BOS, CHC) or 'all'", default="all")
    parser.add_argument("--mode", choices=["day", "night", "all"], default="all", help="Lighting mode")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without calling API")
    parser.add_argument("--force", action="store_true", help="Overwrite existing assets")
    parser.add_argument("--throttle", type=float, default=4.0, help="Seconds to sleep between calls")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Filter target ballparks
    if args.team.upper() == "ALL":
        target_ballparks = MLB_BALLPARKS
    else:
        target_ballparks = [b for b in MLB_BALLPARKS if b["team"].upper() == args.team.upper()]
        if not target_ballparks:
            logger.error(f"Team '{args.team}' not found in MLB manifest!")
            sys.exit(1)

    modes = ["day", "night"] if args.mode == "all" else [args.mode]
    total_jobs = len(target_ballparks) * len(modes)

    logger.info(f"Preparing batch generation: {len(target_ballparks)} stadiums x {len(modes)} modes = {total_jobs} total assets.")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    if not args.dry_run:
        healthy, model_name = verify_imagen_model_health()
        if not healthy:
            logger.error("Vertex AI Imagen model health check failed. Exiting.")
            sys.exit(1)
        client = get_imagen_client()
    else:
        model_name = "imagen-3.0-generate-002"
        client = None

    completed = 0
    skipped = 0
    failed = 0

    for i, bp in enumerate(target_ballparks, 1):
        team = bp["team"].lower()
        slug = bp["slug"]

        for mode in modes:
            filename = f"{team}_{slug}_{mode}.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)

            # Check if file already exists and is non-empty (>10KB)
            if not args.force and os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
                logger.info(f"⏩ [SKIP] {filename} already exists ({os.path.getsize(filepath)} bytes)")
                skipped += 1
                continue

            prompt = build_prompt(bp, mode)
            logger.info(f"🎨 [{completed + skipped + failed + 1}/{total_jobs}] Generating {bp['name']} ({bp['team']}) - {mode.upper()}...")

            success = generate_ballpark_image(client, model_name, prompt, filepath, dry_run=args.dry_run)
            if success:
                completed += 1
            else:
                failed += 1

            # Throttle between calls to respect rate limits
            if not args.dry_run and (completed + failed) < total_jobs:
                time.sleep(args.throttle)

    logger.info(f"\n==========================================")
    logger.info(f"Batch Complete: {completed} Generated, {skipped} Skipped, {failed} Failed")
    logger.info(f"==========================================")

if __name__ == "__main__":
    main()
