#!/usr/bin/env python3
"""
Sovereign OS: Synchronize All Authentic Advocate Assets Across Frontends & Ledgers
Authority: James Carroll (Pilot), Lead Systems Architect

Ensures:
1. All 60+ advocate directories and multi-pose sets are synchronized across:
   - /home/james/stacklabs/avatars/
   - /home/james/stacklabs/15_FanStack/public/avatars/
   - /home/james/stacklabs/19_Sovereign_Sports/public/avatars/
   - /home/james/stacklabs/01_Sovereign_Portal/public/avatars/
2. Top-level /{advocate}.png files exist for every advocate that has a subdirectory,
   preventing 404s in frontend components that request `/avatars/${u}.png`.
3. Registers multi-pose assets into persona_lookbook and cmdb_ci_media_asset.
4. Updates persona.avatar_url in sovereign_now.db to point to their authentic image.
"""

import os
import sys
import shutil
import glob
import sqlite3
import uuid
from datetime import datetime
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
BASE_AVATARS = "/home/james/stacklabs/avatars"
FRONTEND_AVATARS = [
    "/home/james/stacklabs/19_Sovereign_Sports/public/avatars",
    "/home/james/stacklabs/01_Sovereign_Portal/public/avatars",
    "/home/james/stacklabs/15_FanStack/public/avatars"
]

def main():
    print("🚀 Starting Sovereign OS Advocate Asset Synchronization...")

    # Step 1: Ensure frontend avatar directories exist
    for fdir in FRONTEND_AVATARS:
        os.makedirs(fdir, exist_ok=True)

    # Step 2: Discover all advocate directories in avatars/ and 15_FanStack
    source_dirs = set()
    for entry in os.listdir(BASE_AVATARS):
        full = os.path.join(BASE_AVATARS, entry)
        if os.path.isdir(full) and not entry.startswith('.'):
            source_dirs.add(entry)

    fanstack_dir = "/home/james/stacklabs/15_FanStack/public/avatars"
    for entry in os.listdir(fanstack_dir):
        full = os.path.join(fanstack_dir, entry)
        if os.path.isdir(full) and not entry.startswith('.'):
            source_dirs.add(entry)

    print(f"📦 Discovered {len(source_dirs)} advocate subdirectories.")

    # Synchronize each directory across all destinations
    synced_advocates = {}
    for adv in sorted(source_dirs):
        # Determine best source
        src_path = os.path.join(BASE_AVATARS, adv)
        if not os.path.exists(src_path) or not os.listdir(src_path):
            alt_src = os.path.join(fanstack_dir, adv)
            if os.path.exists(alt_src) and os.listdir(alt_src):
                src_path = alt_src

        if not os.path.exists(src_path) or not os.path.isdir(src_path):
            continue

        files = os.listdir(src_path)
        if not files:
            continue

        # Copy directory into BASE_AVATARS and all FRONTEND_AVATARS
        targets = [BASE_AVATARS] + FRONTEND_AVATARS
        for target_root in targets:
            dest_folder = os.path.join(target_root, adv)
            os.makedirs(dest_folder, exist_ok=True)
            for f in files:
                sf = os.path.join(src_path, f)
                df = os.path.join(dest_folder, f)
                if os.path.isfile(sf):
                    shutil.copy2(sf, df)

        # Identify primary avatar file
        primary_file = None
        candidates = [
            f"{adv}_avatar.png",
            f"{adv}.png",
            "avatar.png",
            "front_neutral.png",
            f"{adv.lower()}_avatar.png",
            f"{adv}_avatar.jpg",
            f"{adv}.jpg"
        ]
        for c in candidates:
            if c in files:
                primary_file = os.path.join(src_path, c)
                break

        if not primary_file:
            for f in files:
                if 'avatar' in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    primary_file = os.path.join(src_path, f)
                    break

        if primary_file:
            synced_advocates[adv.lower()] = primary_file
            # Copy to top-level {adv}.png in all targets
            for target_root in targets:
                dest_top = os.path.join(target_root, f"{adv.lower()}.png")
                shutil.copy2(primary_file, dest_top)
                # Also with original casing if different
                if adv != adv.lower():
                    shutil.copy2(primary_file, os.path.join(target_root, f"{adv}.png"))

    print(f"✅ Synchronized {len(synced_advocates)} advocates with top-level avatar fallbacks.")

    # Step 3: Copy all standalone root avatar images across frontends
    root_images = glob.glob(os.path.join(BASE_AVATARS, "*.*"))
    for ri in root_images:
        if ri.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg')):
            fname = os.path.basename(ri)
            for fdir in FRONTEND_AVATARS:
                df = os.path.join(fdir, fname)
                shutil.copy2(ri, df)

    print("✅ All root avatar images replicated across all frontends.")

    # Step 4: Register poses into persona_lookbook and cmdb_ci_media_asset
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()

    lookbook_seeded = 0
    media_asset_seeded = 0
    persona_avatar_updated = 0

    for adv, primary_path in synced_advocates.items():
        # Check poses in folder
        folder = os.path.join(BASE_AVATARS, adv)
        if not os.path.exists(folder):
            continue

        poses = {}
        for f in os.listdir(folder):
            fl = f.lower()
            if not fl.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
            full_p = os.path.join(folder, f)

            if 'pointing' in fl:
                poses['react_point_rally'] = full_p
                poses['pointing'] = full_p
            elif 'shrug' in fl:
                poses['react_facepalm'] = full_p
                poses['shrug'] = full_p
            elif 'surprised' in fl:
                poses['react_shock'] = full_p
            elif 'talking' in fl:
                poses['react_thinking'] = full_p
            elif 'neutral' in fl or 'avatar' in fl:
                poses['front_neutral'] = full_p
                poses['avatar'] = full_p

        if 'front_neutral' not in poses and primary_path:
            poses['front_neutral'] = primary_path

        # Update persona.avatar_url
        avatar_rel_url = f"/avatars/{adv}.png"
        cur.execute("""
            UPDATE persona 
            SET avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE (user_name = ? COLLATE NOCASE OR display_name = ? COLLATE NOCASE)
              AND (avatar_url IS NULL OR avatar_url = '' OR avatar_url LIKE '%.svg' OR avatar_url LIKE '%placeholder%')
        """, (avatar_rel_url, adv, adv))
        if cur.rowcount > 0:
            persona_avatar_updated += cur.rowcount

        # Upsert poses into persona_lookbook and cmdb_ci_media_asset
        for pose_key, file_path in poses.items():
            shot_cat = "reaction" if "react" in pose_key or pose_key in ("pointing", "shrug") else "orientation"
            sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{adv}:lookbook:{pose_key}").hex
            lookbook_id = f"lb_{adv}_{pose_key}"

            cur.execute("""
                INSERT INTO persona_lookbook (
                    sys_id, lookbook_id, persona_id, shot_key, shot_category,
                    prompt_decorator, file_path, mime_type, created_at,
                    sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
                ) VALUES (?, ?, ?, ?, ?, '', ?, 'image/png', ?, ?, ?, 'james', 'james', 0)
                ON CONFLICT(persona_id, shot_key) DO UPDATE SET
                    file_path = excluded.file_path,
                    sys_updated_on = excluded.sys_updated_on,
                    sys_mod_count = persona_lookbook.sys_mod_count + 1
            """, (sys_id, lookbook_id, adv, pose_key, shot_cat, file_path, now_iso, now_iso, now_iso))
            lookbook_seeded += 1

            # cmdb_ci_media_asset
            media_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cmdb:media:{adv}:{pose_key}").hex
            cur.execute("""
                INSERT INTO cmdb_ci_media_asset (
                    sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, 'synced', ?, ?)
                ON CONFLICT(sys_id) DO UPDATE SET
                    file_path = excluded.file_path,
                    sys_updated_on = excluded.sys_updated_on
            """, (media_id, adv, pose_key, file_path, now_iso, now_iso))
            media_asset_seeded += 1

    conn.commit()
    conn.close()

    print(f"🎉 SUCCESS:")
    print(f"   - Seeded {lookbook_seeded} lookbook shots into persona_lookbook.")
    print(f"   - Seeded {media_asset_seeded} expressions into cmdb_ci_media_asset.")
    print(f"   - Replaced {persona_avatar_updated} SVG/placeholder avatar_urls with authentic PNGs.")

if __name__ == "__main__":
    main()
