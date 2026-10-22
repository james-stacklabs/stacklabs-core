import sqlite3
import requests
import sys

# 1. Database Check
print("=== [1/3] Running Database Persona Styles Check ===")
try:
    conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT sys_id, u_visual_style, u_avatar_prompt FROM cmdb_ci_ai_persona WHERE sys_id IN ('8bea7fb1511f4c9f8181c0b152b87999', '287a773da7f9446880eadc797d165a16')")
    rows = cur.fetchall()
    for r in rows:
        print(f"  Persona sys_id: {r['sys_id']} | Visual Style: {r['u_visual_style']} | Avatar Prompt: {r['u_avatar_prompt']}")
    conn.close()
    print("  [✓] Database check completed successfully.")
except Exception as e:
    print(f"  [✗] Database check failed: {e}")
    sys.exit(1)

# 2. API Style Verification Check
print("\n=== [2/3] Running API Prompt Decoder Style Sheet Verification ===")
API_URL = "http://127.0.0.1:8090/api/system/seeder/optimize"
styles_to_test = [
    ("style_a", "Muppet Hell - Rowdy Fleece Puppets"),
    ("style_b", "90s Saturday Morning Cartoons"),
    ("style_c", "Flat Cardboard Cutouts"),
    ("style_d", "16-Bit Sandbox Retro"),
    ("style_e", "Classic Print Caricatures")
]

for style_sheet, expected_phrase in styles_to_test:
    payload = {
        "raw_text": "GOAL!",
        "macro_mode": "mixed_media",
        "style_sheet": style_sheet,
        "city_name": "Seattle",
        "character_description": "an anxious sports advocate"
    }
    try:
        r = requests.post(API_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        if data["status"] != "SUCCESS":
            raise ValueError(f"Expected status SUCCESS, got {data['status']}")
        if expected_phrase not in data["optimized_prompt"]:
            raise ValueError(f"Expected phrase '{expected_phrase}' not found in optimized prompt.")
        print(f"  [✓] Style sheet '{style_sheet}' verified correctly.")
    except Exception as e:
        print(f"  [✗] Style sheet '{style_sheet}' verification failed: {e}")
        sys.exit(1)

# 3. Token Budget Boundary Check
print("\n=== [3/3] Running API Token Budget Boundary Verification ===")
long_payload = {
    "raw_text": "A" * 1100,
    "macro_mode": "mixed_media",
    "style_sheet": "style_a",
    "city_name": "Seattle",
    "character_description": "an anxious sports advocate"
}
try:
    r = requests.post(API_URL, json=long_payload)
    r.raise_for_status()
    data = r.json()
    if data["status"] != "WARNING":
        raise ValueError(f"Expected status WARNING for long prompt, got {data['status']}")
    if "warning" not in data or "Prompt truncated to 1000 characters" not in data["warning"]:
        raise ValueError(f"Expected truncation warning in response, got: {data.get('warning')}")
    # Verify prompt text starts with exactly 1000 'A's
    prompt_text = data["optimized_prompt"]
    base_prefix = prompt_text.split(".")[0]
    if len(base_prefix) != 1000:
        raise ValueError(f"Expected base text length of 1000, got {len(base_prefix)}")
    print("  [✓] Token budget boundary truncation warning verified successfully.")
except Exception as e:
    print(f"  [✗] Token budget boundary verification failed: {e}")
    sys.exit(1)

print("\n=== All Visual Style Sheet and Token Boundary UAT Checks Passed! [✓] ===")
