#!/usr/bin/env python3
"""
generate_character_maps.py
===========================
Reads all active personas from the Sovereign CMDB and uses Gemini to generate
a full character map for each one. Character maps are:
  - Saved as markdown files to /home/james/stacklabs/dna/character_maps/
  - Printed to console as they complete
  - Stored back to CMDB (short_description / u_deep_lore fields)

Run on clio from any machine via Tailscale:
  /home/james/stacklabs/.venv/bin/python3 scripts/generate_character_maps.py

Cost: ~$0.00 using Gemini 2.5 Flash free tier
"""

import os
import re
import sqlite3
import requests
import json
import time
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH    = "/home/james/stacklabs/dna/sovereign_now.db"
OUTPUT_DIR = Path("/home/james/stacklabs/dna/character_maps")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load Gemini key from .env
def _load_gemini_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "") or os.getenv("VITE_GEMINI_API_KEY", "")
    if not key:
        env_path = Path(__file__).parent.parent / "01_Sovereign_Portal" / ".env"
        try:
            for line in env_path.read_text().splitlines():
                m = re.match(r"VITE_GEMINI_API_KEY\s*=\s*[\"']?([^\"'\s]+)", line)
                if m: return m.group(1)
        except Exception:
            pass
    return key

GEMINI_KEY = _load_gemini_key()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_KEY}"

# ── Character Map Prompt ──────────────────────────────────────────────────────
SYSTEM = """You are the Creative Director for FanStack — an AI sports content platform.
Your job is to write detailed, vivid CHARACTER MAPS for AI fan personas.
These maps are used to:
  1. Generate consistent visual images and video in Google Flow / Veo
  2. Give each persona a distinct, memorable voice for AI-generated content
  3. Power Hot Takes (solo rant) and The Skew (panel debate) sessions

Be specific. Be creative. Be hilarious where appropriate. Make them feel REAL."""

def build_prompt(name: str, team: str, bio: str) -> str:
    return f"""Generate a full CHARACTER MAP for the following FanStack persona:

NAME: {name}
TEAM: {team}
BIO: {bio}

Output EXACTLY this structure (use the headers as written):

## Visual Description
A detailed physical description for use in image/video generation prompts.
Include: species or human, age range, body type, signature clothing/accessories, 
facial features, color palette, environment they'd appear in. 
Be specific enough that an AI image generator produces a consistent result every time.

## Voice & Personality
2-3 sentences describing how they talk. Vocabulary, cadence, energy level, 
what topics make them explode vs go quiet. What's their baseline emotional state?

## Catchphrases (3-5)
Short, memorable phrases they say constantly. The kind of thing fans quote.

## Hot Take Style
How do they deliver a Hot Take? What's their opening energy? Do they build slow 
or come out swinging? What's their tell when they're REALLY heated?

## Hot Take Intro
Write their signature Hot Take opener (2-3 sentences). This plays before every 
Hot Take they deliver — like a news anchor intro but unhinged.

## The Skew Role
On a panel discussion, what role do they play? The contrarian? The stats guy?
The emotional wildcard? How do they react when someone disagrees with them?

## Flow/Veo Prompt Seed
A ready-to-use image generation prompt (1 sentence) that captures their look.
Format: "[character description], [art style], [setting], ultra-detailed"
"""

# ── CMDB Query ────────────────────────────────────────────────────────────────
def get_personas() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT 
            c.sys_id,
            c.name,
            c.assigned_to as team,
            c.short_description as bio,
            a.u_deep_lore as deep_lore,
            a.u_system_prompt as system_prompt
        FROM cmdb_ci c
        JOIN cmdb_ci_ai_persona a ON a.sys_id = c.sys_id
        WHERE c.operational_status = 1
          AND c.name NOT LIKE '%_8%'
        ORDER BY c.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Gemini Call ───────────────────────────────────────────────────────────────
def generate_character_map(persona: dict) -> str:
    name = persona["name"]
    team = persona["team"] or "Unknown"
    bio  = persona["bio"] or persona["system_prompt"] or persona["deep_lore"] or f"A passionate {team} fan."

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": build_prompt(name, team, bio)}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1200}
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    if resp.status_code == 200:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise Exception(f"Gemini error {resp.status_code}: {resp.text[:200]}")

# ── Save ──────────────────────────────────────────────────────────────────────
def save_map(persona: dict, content: str):
    name      = persona["name"]
    safe_name = re.sub(r"[^a-z0-9_]", "_", name.lower())
    out_file  = OUTPUT_DIR / f"{safe_name}.md"
    
    header = f"# Character Map: {name}\n**Team:** {persona['team']} | **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    out_file.write_text(header + content)
    print(f"  ✅ Saved → {out_file.name}")

    # Write Flow/Veo prompt seed to a quick-reference file
    veo_match = re.search(r"## Flow/Veo Prompt Seed\n(.+)", content)
    if veo_match:
        veo_file = OUTPUT_DIR / "_veo_prompts.txt"
        with open(veo_file, "a") as f:
            f.write(f"{name}: {veo_match.group(1).strip()}\n")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--names", nargs="+", help="Only generate maps for these persona names (sandbox mode)")
    parser.add_argument("--all", action="store_true", help="Run for ALL personas including ones already generated")
    args = parser.parse_args()

    if not GEMINI_KEY:
        print("❌ GEMINI_API_KEY not found. Check .env file.")
        return

    personas = get_personas()

    # Sandbox mode — limit to approved list only
    if args.names:
        approved = [n.lower() for n in args.names]
        personas = [p for p in personas if p["name"].lower() in approved]
        print(f"🔒 Sandbox mode — restricted to: {[p['name'] for p in personas]}")
    elif not args.all:
        # Skip already-generated maps
        existing = {f.stem for f in OUTPUT_DIR.glob("*.md")}
        personas = [p for p in personas if re.sub(r"[^a-z0-9_]", "_", p["name"].lower()) not in existing]

    total = len(personas)
    print(f"\n🎭 Character Map Generator")
    print(f"   Personas to process: {total}")
    print(f"   Output: {OUTPUT_DIR}\n")

    if total == 0:
        print("✅ All character maps already generated. Delete files in dna/character_maps/ to regenerate.")
        return

    for i, persona in enumerate(personas, 1):
        name = persona["name"]
        print(f"[{i}/{total}] Generating → {name}...")
        try:
            content = generate_character_map(persona)
            save_map(persona, content)
            # Gemini Flash rate limit buffer
            time.sleep(1.5)
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            time.sleep(3)

    print(f"\n✅ Done! {total} character maps written to:")
    print(f"   {OUTPUT_DIR}")
    print(f"\n   Veo/Flow prompt seeds: {OUTPUT_DIR / '_veo_prompts.txt'}\n")

if __name__ == "__main__":
    main()
