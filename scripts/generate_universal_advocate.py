#!/usr/bin/env python3
import os
import sys
import json
import argparse
import subprocess
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "project-114213dc-6519-49c5-a0a"
LOCATION = "us-central1"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"

def main():
    parser = argparse.ArgumentParser(description="Universal Advocate Generator (The Wildcard Forge)")
    parser.add_argument("--name", required=True, help="Proposed display name of the advocate")
    parser.add_argument("--concept", required=True, help="Short concept description or vibe")
    args = parser.parse_args()

    print(f"🔮 [WILDCARD FORGE] Starting synthesis for proposed advocate: {args.name}")
    print(f"💡 Concept: {args.concept}")

    # Set up auth
    if os.path.exists(CREDENTIALS_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        sys.exit(1)

    sys_instr = """
    You are the Sovereign OS Deep Lore Engine. Your task is to synthesize a complete, highly-detailed, and production-ready AI advocate based on the name and concept provided.
    
    You MUST respond with a valid JSON object matching the following schema EXACTLY:
    {
      "display_name": "The display name of the advocate",
      "handle": "A unique, lowercase alphanumeric X/Twitter handle without the '@', using underscores if needed (e.g. tech_priest)",
      "role": "The functional role or archetype of the advocate",
      "system_prompt": "Master instructions, specialized vocabulary, cognitive triggers, and chat behavior. This MUST be a comprehensive block of text containing approximately 600 words.",
      "deep_lore": "Detailed background story, origin, and private obsessions. This MUST be a visceral narrative of approximately 500 words.",
      "governance_rules": [
        "Rule 1",
        "Rule 2",
        "Rule 3",
        "Rule 4",
        "Rule 5"
      ], // You MUST generate EXACTLY 5 immutable governance rules
      "faction_alignment": "The alignment or faction of the advocate (e.g., House of Metal, House of Glass, independent)",
      "signature_phrases": {
        "opening": "Opening signature phrase or greeting",
        "closing": "Closing signature phrase or sign-off"
      },
      "avatar_prompt": "A detailed character prompt for Imagen-3. It must describe a front-view, high-detail model/reference sheet in a flat 2D vector style, expressive Twitch emote cartoon style, clean lines, solid black background, showing multiple angles and expressions, wearing theme merchandise."
    }
    
    Ensure both the system_prompt and deep_lore are extremely detailed and meet the word count requirements (approx. 600 words and 500 words respectively). Do not abbreviate.
    """

    prompt = f"Name: {args.name}\nConcept: {args.concept}\n\nSynthesize the advocate in JSON."

    # Try gemini-3.8-flash first as requested, fallback to gemini-1.5-flash if needed
    model_versions = ["gemini-3.8-flash", "gemini-1.5-flash"]
    response_text = None

    for mv in model_versions:
        print(f"⚡ Requesting cognitive synthesis via Vertex AI using model: {mv}...")
        try:
            model = GenerativeModel(mv, system_instruction=[sys_instr])
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.85, "response_mime_type": "application/json"}
            )
            response_text = response.text.strip()
            print(f"✅ Cognitive synthesis successful using {mv}.")
            break
        except Exception as e:
            print(f"⚠️ Failed to generate with {mv}: {e}")

    if not response_text:
        print("❌ Error: Could not get a response from Vertex AI with any model version.")
        sys.exit(1)

    try:
        advocate_data = json.loads(response_text)
    except Exception as e:
        print(f"❌ Failed to parse response text as JSON: {e}")
        print("Response was:")
        print(response_text)
        sys.exit(1)

    # Validate schema
    handle = advocate_data.get("handle", "wildcard_advocate").lower().replace(" ", "_")
    display_name = advocate_data.get("display_name", args.name)
    gov_rules = advocate_data.get("governance_rules", [])
    if len(gov_rules) != 5:
        print(f"⚠️ Generated governance rules count was {len(gov_rules)} instead of 5. Adjusting to exactly 5.")
        while len(gov_rules) < 5:
            gov_rules.append("Observe systems integrity.")
        gov_rules = gov_rules[:5]

    # Generate Markdown blueprint
    blueprint_dir = "/home/james/stacklabs/work_orders/blueprints"
    os.makedirs(blueprint_dir, exist_ok=True)
    blueprint_path = os.path.join(blueprint_dir, f"{handle}.md")

    md_content = f"""# X/Twitter Onboarding Blueprint: `{display_name}`

This blueprint was dynamically forged via the Universal Advocate Generator.

## 👤 Profile Details

**X Handle:** `@{handle}`
**Display Name:** {display_name}
**Role:** {advocate_data.get("role", "Wildcard Advocate")}
**Faction Alignment:** {advocate_data.get("faction_alignment", "Independent")}
**Opening Phrase:** "{advocate_data.get("signature_phrases", {}).get("opening", "Hello.")}"
**Closing Phrase:** "{advocate_data.get("signature_phrases", {}).get("closing", "Goodbye.")}"

## 📋 Governance Rules
1. {gov_rules[0]}
2. {gov_rules[1]}
3. {gov_rules[2]}
4. {gov_rules[3]}
5. {gov_rules[4]}

## 📖 Deep Lore
{advocate_data.get("deep_lore", "Synthesized wildcard advocate.")}

## 🧠 System Prompt
{advocate_data.get("system_prompt", "Conduct yourself according to specifications.")}

# Style Profile
Base Prompt: {advocate_data.get("avatar_prompt", "Twitch emote vector layout style.")}

## 🖼️ Profile Pictures

**Avatar Prompt Used:**
{advocate_data.get("avatar_prompt", "Twitch emote vector layout style.")}
"""

    with open(blueprint_path, "w") as f:
        f.write(md_content)

    print(f"📂 Saved onboarding blueprint to: {blueprint_path}")

    # Launch Advocate Forge subprocess
    print("🚀 Triggering background asset generation via Advocate Forge...")
    python_bin = "/home/james/stacklabs/.venv/bin/python3"
    if not os.path.exists(python_bin):
        python_bin = "python3"

    try:
        subprocess.Popen([
            python_bin,
            "/home/james/stacklabs/scripts/advocate_forge.py",
            blueprint_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Advocate Forge triggered successfully in the background.")
    except Exception as e:
        print(f"⚠️ Failed to trigger Advocate Forge: {e}")

    print("🎉 UNIVERSAL ADVOCATE PROVISIONING PIPELINE COMPLETE.")

if __name__ == "__main__":
    main()
