#!/usr/bin/env python3
"""
verify_cockpit_vision_atf.py — Multimodal Gemini 3.8 Flash Cloud Vision Audit
=============================================================================
Performs an automated visual audit on the 5 Pegasus Playwright visual twins:
- Mission Deck
- JIT Approvals
- Queue Air-Gap Stage
- Fleet & CMDB
- Sovereign Horizon Radar
Verifies Vantablack depth (#090A0F), flat black cards (#0B0D13), #1E2330 borders,
Inter typography legibility, and navigation hover states.
"""

import os
import sys
import json
from pathlib import Path
import dotenv
from google import genai
from google.genai import types
from PIL import Image

# Load environment credentials
dotenv.load_dotenv('/home/james/stacklabs/.env')
dotenv.load_dotenv('/home/james/stacklabs/scripts/.env.auth')

MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
IMAGES = [
    ("Mission Deck", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_mission_deck.png"),
    ("JIT Approvals", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_jit.png"),
    ("Queue Air-Gap Stage", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_queue.png"),
    ("Fleet & CMDB", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_fleet.png"),
    ("Sovereign Horizon Radar", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_horizon.png"),
    ("Navigation Hover", MOCKUPS_DIR / "pegasus_uat_wo0010511_cockpit_nav_hover.png"),
]

def main():
    print("=" * 72)
    print("👁️ GEMINI 3.8 FLASH CLOUD VISION ATF AUDIT // WO0010511")
    print("=" * 72)

    client = genai.Client()
    audit_results = []
    all_passed = True

    for label, img_path in IMAGES:
        if not img_path.exists():
            print(f"❌ Missing mockup image: {img_path}")
            sys.exit(1)

        print(f"\n[*] Auditing visual twin for: {label} ({img_path.name})...")
        pil_img = Image.open(img_path)

        prompt = """
You are a senior UI/UX aesthetic auditor and systems designer inspecting a production control plane cockpit interface.
Analyze this high-resolution visual capture and verify the following criteria:

1. Vantablack Void Depth:
   - Is the overall canvas deep dark/void (#090A0F) with zero blinding white or light-mode background?
   - Is there a subtle, tasteful cyan ceiling glow/aura along the top border?

2. Card & Surface Hierarchy:
   - Are the container cards flat black (#0B0D13) with clean gunmetal hairline borders (#1E2330)?
   - Are there ANY light-gray, white, or bleached card backgrounds? (Must be ZERO).

3. Typography & Legibility:
   - Is the typography crisp and legible (Inter font hierarchy, JetBrains Mono for metrics)?
   - Are text elements easily readable with high contrast against the dark background?

4. Navigation Bar:
   - Is the navigation bar clean and readable?
   - Are button labels legible without low-contrast muddy gray-on-dark text?

Provide your evaluation in JSON format:
{
  "tab": "<tab name>",
  "vantablack_void_verified": true/false,
  "zero_white_cards_verified": true/false,
  "typography_legible": true/false,
  "navigation_legible": true/false,
  "critique": "<2 sentence analysis of contrast, depth, and palette adherence>",
  "verdict": "PASS" or "FAIL"
}
Output strictly valid JSON and nothing else.
"""

        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[pil_img, prompt]
        )

        raw_text = response.text.strip()
        # Clean JSON markdown fences if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        try:
            result = json.loads(raw_text)
            audit_results.append(result)
            status_icon = "✓" if result.get("verdict") == "PASS" else "❌"
            print(f"[{status_icon}] Verdict: {result.get('verdict')} | Vantablack: {result.get('vantablack_void_verified')} | Zero White Cards: {result.get('zero_white_cards_verified')}")
            print(f"    Critique: {result.get('critique')}")
            if result.get("verdict") != "PASS":
                all_passed = False
        except Exception as e:
            print(f"⚠️ Error parsing JSON response: {e}\nRaw output: {raw_text}")
            all_passed = False

    print("\n" + "=" * 72)
    print("📊 CLOUD VISION AUDIT SUMMARY")
    print("=" * 72)
    print(f"Total screens audited: {len(audit_results)}")
    print(f"Passed: {sum(1 for r in audit_results if r.get('verdict') == 'PASS')}")
    print(f"Failed: {sum(1 for r in audit_results if r.get('verdict') != 'PASS')}")

    out_json = MOCKUPS_DIR / "vision_atf_audit_results.json"
    out_json.write_text(json.dumps(audit_results, indent=2))
    print(f"Audit results recorded at: {out_json}")

    if not all_passed:
        print("❌ Cloud vision audit failed.")
        sys.exit(1)

    print("✨ All visual twins PASSED Gemini 3.8 Flash Cloud Vision ATF audit.")
    sys.exit(0)

if __name__ == "__main__":
    main()
