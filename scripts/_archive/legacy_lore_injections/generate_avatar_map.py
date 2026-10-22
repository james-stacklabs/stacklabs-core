import os
import json
import re

AVATAR_DIR = '/home/james/stacklabs/01_Sovereign_Portal/public/avatars'
OUT_FILE = '/home/james/stacklabs/01_Sovereign_Portal/src/avatarMap.json'

avatar_map = {}
for filename in os.listdir(AVATAR_DIR):
    if filename.endswith(('.jpg', '.png', '.jpeg', '.jfif', '.webp', '.svg')):
        base_name = os.path.splitext(filename)[0]
        norm = re.sub(r'[^a-z0-9]', '', base_name.lower())
        avatar_map[norm] = f"/avatars/{filename}"

with open(OUT_FILE, 'w') as f:
    json.dump(avatar_map, f, indent=2)

print(f"Generated avatarMap.json with {len(avatar_map)} entries.")
