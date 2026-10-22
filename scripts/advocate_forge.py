import sys
import os
import re
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# 1. PARSE ARGUMENTS AND DETERMINE SHEET PATH
if len(sys.argv) < 2:
    print("❌ Usage: python3 scripts/advocate_forge.py <advocate_sheet.md> [--style custom]")
    print("💡 Example: python3 scripts/advocate_forge.py dna/archives/game_logs/RiggedLeagueRant_onboarding.md")
    sys.exit(1)

sheet_path = sys.argv[1]
if not os.path.exists(sheet_path):
    print(f"❌ Error: File not found at {sheet_path}")
    sys.exit(1)

# Determine if a custom style is requested
use_custom_style = "--style" in sys.argv or "--custom" in sys.argv

# Derive character handle/name from the filename or content
base = os.path.splitext(os.path.basename(sheet_path))[0]
if base.endswith("_onboarding"):
    character_name = base[:-11].lower()
else:
    character_name = base.split('_')[0].lower()

# 2. READ & PARSE MARKDOWN SHEET
print(f"📖 Ingesting FanStack Advocate Sheet: {sheet_path}...")
with open(sheet_path, 'r') as f:
    content = f.read()

handle_match = re.search(r'\*\*X Handle:\*\*\s*[`@]*([a-zA-Z0-9_]+)', content)
if handle_match:
    character_name = handle_match.group(1).lower()

# Regular expressions to parse sections cleanly
lore_match = re.search(r'# Character Lore\n(.*?)(?=\n#|\Z)', content, re.DOTALL | re.IGNORECASE)
if not lore_match:
    # Fallback to Deep Lore or standard description if Character Lore heading isn't present
    lore_match = re.search(r'## 📖 Deep Lore\n(.*?)(?=\n#|\Z)', content, re.DOTALL | re.IGNORECASE)

poses_match = re.search(r'# Poses\n(.*?)(?=\n#|\Z)', content, re.DOTALL | re.IGNORECASE)

# Default to unhinged pointing/exasperation profile poses if no Poses section exists
default_poses = {
    "avatar": "Standard 1:1 profile headshot looking directly at the camera with an intense, expressive look.",
    "pointing": "Pointing an accusatory finger forward in wild excitement, looking smug.",
    "shrug": "Shrugging in complete disbelief and exasperation, eyes wide."
}

character_lore = lore_match.group(1).strip() if lore_match else "A passionate, highly animated baseball fan."
poses = {}

if poses_match:
    poses_raw = poses_match.group(1).strip()
    for line in poses_raw.split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('*'):
            parts = line[1:].split(':', 1)
            if len(parts) == 2:
                poses[parts[0].strip()] = parts[1].strip()
else:
    poses = default_poses

# Determine Art Style Prompt based on onboarding tier
style_match = re.search(r'# Style Profile\n(.*?)(?=\n#|\Z)', content, re.DOTALL | re.IGNORECASE)
custom_style_prompt = ""
if style_match:
    style_lines = style_match.group(1).strip().split('\n')
    for line in style_lines:
        if "Base Prompt" in line or "Prompt" in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                custom_style_prompt = parts[1].strip()

# 3. CONSTRUCT STYLING RECIPE
# Golden "Wicked Smaht" Standard baseline style for single character avatars
STANDARD_STYLE = "High quality 2D vector graphic, expressive cartoon character avatar portrait, clean vibrant colors, dark solid background. Single individual character, close-up head and shoulders framing."

if use_custom_style and custom_style_prompt:
    active_style = custom_style_prompt
    print(f"✨ [A-LIST TIER] Applying custom style profile: {active_style}")
else:
    active_style = STANDARD_STYLE
    print(f"🎨 [STANDARD TIER] Applying golden single portrait avatar style.")

print(f"👤 Advocate: @{character_name.upper()}")
print(f"🏃 Actions Parsed: {list(poses.keys())}")

# 4. AUTHENTICATION & VERTEX AI INIT
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "project-114213dc-6519-49c5-a0a"
if os.path.exists(CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    try:
        with open(CREDENTIALS_PATH, "r") as f:
            sa_data = json.load(f)
            PROJECT_ID = sa_data.get("project_id", PROJECT_ID)
    except Exception:
        pass
LOCATION = "us-central1"

print("\n🌩️ INITIALIZING VERTEX AI LINK...")
sys.path.append("/home/james/stacklabs/scripts")
from imagen_util import generate_imagen_avatar, verify_imagen_model_health

is_healthy, working_model = verify_imagen_model_health()
if not is_healthy:
    print("❌ Pre-flight Imagen model health verification failed! Halting forge.")
    sys.exit(1)

print(f"✅ Verified operational Imagen model: {working_model}")

# Create FanStack public avatars output folder dynamically based on character handle
OUTPUT_DIR = f"/home/james/stacklabs/15_FanStackCreator/public/avatars/{character_name}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Construct compiled prompts for each individual pose
compiled_prompts = {}
for state_name, action in poses.items():
    compiled_prompts[state_name] = f"Single character portrait of {character_lore}.\nPose/Action: {action}.\nStyle: {active_style}.\nSingle portrait only, centered, no grid layout, no sprite sheet, no multiple characters."

# Interactive Staging / Prompt Preview and Edit Loop (Only if interactive TTY is present)
if sys.stdin.isatty():
    while True:
        print("\n" + "="*60)
        print(f"🔍 PROMPT PREVIEW FOR @{character_name.upper()}")
        print("="*60)
        for state_name, prompt_text in compiled_prompts.items():
            print(f"[{state_name}]:")
            indented = "\n".join("    " + line for line in prompt_text.split("\n"))
            print(indented)
            print("-"*60)
        
        choice = input("👉 Proceed to generate these images? (y = Yes, e = Edit a prompt, q = Quit) [y]: ").strip().lower()
        if not choice or choice == 'y':
            break
        elif choice == 'q':
            print("👋 Aborted by user.")
            sys.exit(0)
        elif choice == 'e':
            pose_to_edit = input(f"👉 Enter the name of the pose to edit ({'/'.join(compiled_prompts.keys())}): ").strip()
            if pose_to_edit not in compiled_prompts:
                print("⚠️ Invalid pose name.")
                continue
            print(f"\nEditing [{pose_to_edit}]. Current prompt:")
            print(compiled_prompts[pose_to_edit])
            new_prompt = input("\nEnter the custom prompt (or press Enter to keep current): ").strip()
            if new_prompt:
                compiled_prompts[pose_to_edit] = new_prompt
                print(f"✅ Updated prompt for [{pose_to_edit}].")

print(f"🔥 FORGING PRODUCTION AVATARS FOR @{character_name.upper()}...")

import shutil

for state_name, full_prompt in compiled_prompts.items():
    print(f"⚙️ Forging state: [{state_name}]...")
    file_path = f"{OUTPUT_DIR}/{character_name}_{state_name}.png"
    success, res_path = generate_imagen_avatar(
        prompt=full_prompt,
        output_path=file_path,
        aspect_ratio="1:1"
    )
    if success:
        print(f"✅ Saved: {res_path}")
        # Sync to all active portal public avatar directories
        for target_dir in [
            f"/home/james/stacklabs/avatars/{character_name}",
            f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{character_name}",
            f"/home/james/stacklabs/19_FanStackArena/public/avatars/{character_name}",
            f"/home/james/stacklabs/15_FanStackCreator/public/avatars/{character_name}",
            f"/home/james/stacklabs/02_Sovereign_Media/public/avatars/{character_name}"
        ]:
            os.makedirs(target_dir, exist_ok=True)
            dst_file = os.path.join(target_dir, f"{character_name}_{state_name}.png")
            if os.path.abspath(res_path) != os.path.abspath(dst_file) and not (os.path.exists(dst_file) and os.path.samefile(res_path, dst_file)):
                shutil.copy2(res_path, dst_file)
    else:
        print(f"⚠️ [API ERROR] on {state_name}: {res_path}")

print(f"🚀 PRODUCTION FORGE COMPLETE. The FanStack assets are live in: {OUTPUT_DIR}")
