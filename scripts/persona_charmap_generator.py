#!/usr/bin/env python3
"""
========================================================================
SOVEREIGN OS — Persona Character Map Generator
========================================================================
Uses Gemini to read persona bios and generate Flow-style character
reference sheets (model sheets / character maps) via Imagen 3.

Style target:
  Character reference sheet, model sheet, concept art. Multiple angles
  and expressions. Flat 2D vector style, expressive cartoon, clean lines,
  solid black background, arranged in grid layout.

Run modes:
  python3 persona_charmap_generator.py --pilot 4        # do first N only
  python3 persona_charmap_generator.py --persona barf   # single persona
  python3 persona_charmap_generator.py --all            # full batch (sandbox)

Outputs to: /home/james/stacklabs/dna/media/character_maps/
========================================================================
"""

import os
import sys
import time
import sqlite3
import argparse
import requests
import base64
import json
from pathlib import Path
from datetime import datetime
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH        = "/home/james/stacklabs/dna/sovereign_now.db"
OUTPUT_DIR     = Path("/home/james/stacklabs/dna/media/character_maps")
ENV_PATH       = "/home/james/stacklabs/01_Sovereign_Portal/.env"
SLEEP_BETWEEN  = 8   # seconds between API calls (rate limit courtesy)
LOG_FILE       = "/tmp/charmap_generator.log"

# ── Style constants ────────────────────────────────────────────────────────────
STYLE_SUFFIX = (
    "Character reference sheet, model sheet, concept art. "
    "Multiple angles and expressions arranged in a grid layout. "
    "Flat 2D vector style, expressive Twitch emote cartoon style, "
    "clean lines, thick outlines, solid black background. "
    "Masterpiece quality, highly detailed character design."
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
    if not key and os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("VITE_GEMINI_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip().strip('"')
    if not key:
        raise RuntimeError("No GEMINI_API_KEY found. Check .env or environment.")
    return key


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_personas(limit: int | None = None, name: str | None = None, teams: list[str] | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Exclude personas that already have a character map
    existing = {p.stem.lower() for p in OUTPUT_DIR.glob("*") if p.is_file()}

    if name:
        c.execute("""
            SELECT user_name, display_name, team, system_prompt, deep_lore, behavior_notes, governance
            FROM persona
            WHERE lower(user_name) = lower(?)
        """, (name,))
    elif teams:
        placeholders = ",".join(["?"] * len(teams))
        c.execute(f"""
            SELECT user_name, display_name, team, system_prompt, deep_lore, behavior_notes, governance
            FROM persona
            WHERE system_prompt IS NOT NULL AND system_prompt != ''
              AND upper(team) IN ({placeholders})
            ORDER BY user_name
        """, [t.upper() for t in teams])
    else:
        c.execute("""
            SELECT user_name, display_name, team, system_prompt, deep_lore, behavior_notes, governance
            FROM persona
            WHERE system_prompt IS NOT NULL AND system_prompt != ''
            ORDER BY user_name
        """)

    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # Filter already-done unless targeting single
    if not name:
        rows = [r for r in rows if r["user_name"].lower() not in existing]
        log(f"Found {len(rows)} personas without existing character maps.")

    if limit:
        rows = rows[:limit]

    return rows


def build_prompt(persona: dict) -> str:
    """
    Ask Gemini Flash to synthesize a one-paragraph character description
    from the persona bio, then wrap it in our style template.
    This is the 'prompt engineer' step before image gen.
    """
    name = persona["user_name"]
    display = persona.get("display_name") or name
    team = persona.get("team") or "MLB"
    bio = (persona.get("system_prompt") or "")[:800]
    lore = (persona.get("deep_lore") or "")[:400]
    notes = (persona.get("behavior_notes") or "")[:200]

    # Build a descriptive narrative for Gemini to refine
    raw = f"""
Persona: {display} ({team} fan)
Bio summary: {bio}
Deep lore: {lore}
Behavior notes: {notes}
""".strip()

    api_key = get_api_key()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "You are an expert character concept artist. "
                    "Given a persona bio, write a single concise paragraph (2-4 sentences) "
                    "describing how this character should look visually as a cartoon/illustration. "
                    "Focus on: physical appearance, clothing, signature props, emotional expression, "
                    "colors, and any distinctive features. Be specific and vivid. "
                    "Do NOT include style directions — just describe the character."
                )
            }]
        },
        "contents": [{"parts": [{"text": raw}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 300}
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    character_desc = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    log(f"  ✓ Prompt generated for {name}: {character_desc[:80]}...")

    # Compose the full Flow-style image prompt
    full_prompt = (
        f"{display} ({team} fan baseball persona). "
        f"{character_desc} "
        f"{STYLE_SUFFIX}"
    )
    return full_prompt


def generate_image(prompt: str, persona_name: str) -> Path | None:
    """
    Call Imagen 3 via Vertex AI SDK to generate the character map image.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/james/stacklabs/config/vertex_sa.json'

    try:
        vertexai.init(project='gen-lang-client-0840454416', location='us-central1')
        model = ImageGenerationModel.from_pretrained('imagen-3.0-generate-002')
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_some",
            person_generation="allow_adult"
        )
        out_path = OUTPUT_DIR / f"{persona_name.lower()}.png"
        response.images[0].save(location=str(out_path), include_generation_parameters=False)
        log(f"  ✓ Vertex Imagen 3 → {out_path}")
        return out_path
    except Exception as e:
        log(f"  ✗ Vertex Imagen 3 failed for {persona_name}: {e}")
        return None


def process_persona(persona: dict) -> bool:
    name = persona["user_name"]
    log(f"\n{'='*60}")
    log(f"Processing: {name} ({persona.get('team','?')})")

    try:
        prompt = build_prompt(persona)
        log(f"  Full prompt ({len(prompt)} chars): {prompt[:120]}...")

        # Save the prompt for reference
        prompt_path = OUTPUT_DIR / f"{name.lower()}_prompt.txt"
        prompt_path.write_text(prompt)

        out = generate_image(prompt, name)
        if out:
            log(f"  ✓ Complete: {out.name}")
            try:
                char_map_url = f"/media/character_maps/{name.lower()}.png"
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE persona
                    SET character_map_url = ?, character_map_prompt = ?
                    WHERE user_name = ? OR LOWER(user_name) = ?
                """, (char_map_url, prompt, name, name.lower()))
                cursor.execute("""
                    UPDATE cmdb_ci_ai_persona
                    SET u_character_map_url = ?, u_character_map_prompt = ?
                    WHERE sys_id IN (
                        SELECT sys_id FROM sys_user WHERE user_name = ? OR LOWER(user_name) = ?
                    )
                """, (char_map_url, prompt, name, name.lower()))
                conn.commit()
                conn.close()
                log(f"  🔒 Relational DB records updated with character_map_url and prompts for @{name}.")
            except Exception as dbe:
                log(f"  ⚠️ Database update failed for {name}: {dbe}")
            return True
        else:
            log(f"  ✗ No image generated for {name}")
            return False

    except Exception as e:
        log(f"  ✗ Error processing {name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sovereign Persona Character Map Generator")
    parser.add_argument("--pilot", type=int, metavar="N", help="Process first N personas only")
    parser.add_argument("--persona", type=str, help="Process a single persona by user_name")
    parser.add_argument("--teams", type=str, help="Process personas for specific teams (comma-separated, e.g. CHC,PIT,CIN)")
    parser.add_argument("--all", action="store_true", help="Process all personas (sandbox mode)")
    parser.add_argument("--list", action="store_true", help="List pending personas without generating")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Sovereign Persona Character Map Generator — {datetime.now().isoformat()}")
    log(f"Output dir: {OUTPUT_DIR}")

    # Determine run mode
    if args.persona:
        personas = get_personas(name=args.persona)
    elif args.teams:
        team_list = [t.strip() for t in args.teams.split(",") if t.strip()]
        if args.list:
            personas = get_personas(teams=team_list)
            print(f"\nPending personas for teams {args.teams} ({len(personas)}):")
            for p in personas:
                print(f"  {p['user_name']} ({p['team']})")
            return
        personas = get_personas(teams=team_list)
    elif args.pilot:
        personas = get_personas(limit=args.pilot)
    elif args.all:
        personas = get_personas()
    elif args.list:
        personas = get_personas()
        print(f"\nPending personas ({len(personas)}):")
        for p in personas:
            print(f"  {p['user_name']} ({p['team']})")
        return
    else:
        # Default: pilot 4
        personas = get_personas(limit=4)
        log("No mode specified — defaulting to pilot 4.")

    if not personas:
        log("No pending personas found. All caught up!")
        return

    log(f"Queue: {len(personas)} persona(s) — {[p['user_name'] for p in personas]}")

    success, fail = 0, 0
    for i, persona in enumerate(personas):
        ok = process_persona(persona)
        if ok:
            success += 1
        else:
            fail += 1

        # Rate limit courtesy — don't hammer the API
        if i < len(personas) - 1:
            log(f"  Sleeping {SLEEP_BETWEEN}s before next...")
            time.sleep(SLEEP_BETWEEN)

    log(f"\n{'='*60}")
    log(f"DONE — Success: {success} | Failed: {fail}")
    log(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
