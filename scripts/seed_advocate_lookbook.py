#!/usr/bin/env python3
"""
Sovereign OS: Enterprise Advocate Lookbook Seeder Daemon
Path: /home/james/stacklabs/scripts/seed_advocate_lookbook.py
Ticket: WO-2026-0910-FANSTACK-BARF-LOOKBOOK-SEEDER
Authority: James Carroll (Lead Systems Architect)

Ingests, normalizes, and registers deterministic multi-angle pose and emotion reaction
lookbooks for FanStack advocates (e.g. Barf, Metsy, Keith, Dot).
Supports Google Flow 22-shot persona pose packs, reference-conditioned local storage,
and SQLite relational registration in persona_lookbook and CMDB media catalogs.
"""

import os
import sys
import json
import uuid
import shutil
import hashlib
import sqlite3
import argparse
import zipfile
from datetime import datetime
from pathlib import Path
from PIL import Image

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
DEFAULT_MATRIX_PATH = "/home/james/stacklabs/dna/prompts/persona_pose_matrix.json"
LOOKBOOK_BASE_DIR = "/home/james/stacklabs/dna/media/lookbooks"
ADVOCATE_BASE_DIR = "/home/james/stacklabs/dna/media/advocates"
AVATARS_BASE_DIR = "/home/james/stacklabs/avatars"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.row_factory = sqlite3.Row
    return conn

def calculate_hashes(file_path: str):
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()

def match_flow_files(source_dir: str, matrix_shots: dict) -> tuple[dict, str]:
    files = sorted(os.listdir(source_dir))
    mapping = {}
    canonical_ref_file = None

    for f in files:
        if f.lower().startswith("barf.png") or "canonical" in f.lower() or "ref" in f.lower():
            if not canonical_ref_file:
                canonical_ref_file = os.path.join(source_dir, f)
            continue

        f_is_variant2 = f.endswith("_2.jpeg")
        for shot_key, shot_info in matrix_shots.items():
            if shot_key in mapping:
                continue
            patterns = shot_info.get("flow_match_patterns", [])
            matched = False
            for pattern in patterns:
                pat_is_variant2 = pattern.endswith("_2.jpeg") or "_2." in pattern
                pat_base = pattern.split("_2")[0].lower()
                if pat_is_variant2 == f_is_variant2 and pat_base in f.lower():
                    mapping[shot_key] = os.path.join(source_dir, f)
                    matched = True
                    break
            if matched:
                break

    return mapping, canonical_ref_file

def seed_lookbook(advocate: str, preset: str = "full22", zip_source: str = None, 
                  source_dir: str = None, ref_image: str = None, matrix_path: str = DEFAULT_MATRIX_PATH):
    advocate = advocate.lower().strip()
    
    if not os.path.exists(matrix_path):
        raise FileNotFoundError(f"Pose matrix definition missing: {matrix_path}")

    with open(matrix_path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    shots_catalog = matrix.get("shots", {})
    presets = matrix.get("presets", {})

    if preset not in presets:
        raise ValueError(f"Invalid preset '{preset}'. Available: {list(presets.keys())}")

    target_shot_keys = presets[preset]

    target_lookbook_dir = os.path.join(LOOKBOOK_BASE_DIR, advocate)
    target_advocate_dir = os.path.join(ADVOCATE_BASE_DIR, advocate)
    os.makedirs(target_lookbook_dir, exist_ok=True)
    os.makedirs(target_advocate_dir, exist_ok=True)
    os.makedirs(AVATARS_BASE_DIR, exist_ok=True)

    temp_extract_dir = None
    input_dir = source_dir

    if zip_source and os.path.exists(zip_source):
        temp_extract_dir = f"/tmp/sovereign_lookbook_{advocate}_{uuid.uuid4().hex[:8]}"
        os.makedirs(temp_extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_source, "r") as z:
            z.extractall(temp_extract_dir)
        input_dir = temp_extract_dir
    elif not input_dir:
        candidate_zip = f"/home/james/sovereign_inbox/pilot_drops/{advocate}_22.zip"
        if os.path.exists(candidate_zip):
            temp_extract_dir = f"/tmp/sovereign_lookbook_{advocate}_{uuid.uuid4().hex[:8]}"
            os.makedirs(temp_extract_dir, exist_ok=True)
            with zipfile.ZipFile(candidate_zip, "r") as z:
                z.extractall(temp_extract_dir)
            input_dir = temp_extract_dir

    if not input_dir or not os.path.exists(input_dir):
        raise FileNotFoundError(f"No valid source directory or zip found for advocate '{advocate}'.")

    file_mapping, canonical_ref_file = match_flow_files(input_dir, shots_catalog)

    # Save canonical reference anchor if found
    canonical_anchor_path = os.path.join(target_advocate_dir, "canonical_ref.png")
    if canonical_ref_file and os.path.exists(canonical_ref_file):
        try:
            with Image.open(canonical_ref_file) as im:
                im.save(canonical_anchor_path, "PNG")
                # Also synchronize primary avatar
                im.save(os.path.join(AVATARS_BASE_DIR, f"{advocate}.png"), "PNG")
                im.save(os.path.join(AVATARS_BASE_DIR, f"{advocate}_prime.png"), "PNG")
            print(f"✅ Canonical reference anchor saved: {canonical_anchor_path}")
        except Exception as err:
            print(f"⚠️ Warning saving canonical reference: {err}")

    conn = get_db_connection()
    results = []

    try:
        now_iso = datetime.now().isoformat()
        
        with conn:
            cursor = conn.cursor()

            for shot_key in target_shot_keys:
                shot_info = shots_catalog.get(shot_key)
                if not shot_info:
                    continue

                source_file = file_mapping.get(shot_key)
                if not source_file or not os.path.exists(source_file):
                    print(f"⚠️ Missing source image for shot '{shot_key}' — skipping")
                    continue

                dest_png = os.path.join(target_lookbook_dir, f"{shot_key}.png")
                dest_jpeg = os.path.join(target_lookbook_dir, f"{shot_key}.jpeg")

                # Normalize and save as PNG & JPEG
                with Image.open(source_file) as im:
                    im_rgb = im.convert("RGB")
                    im_rgb.save(dest_png, "PNG")
                    im_rgb.save(dest_jpeg, "JPEG", quality=95)

                file_size = os.path.getsize(dest_png)
                sha256_hash, md5_hash = calculate_hashes(dest_png)
                
                # Deterministic sys_id
                sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{advocate}:lookbook:{shot_key}").hex
                lookbook_id = f"lb_{advocate}_{shot_key}"
                shot_category = shot_info.get("shot_category", "orientation")
                prompt_decorator = shot_info.get("prompt_decorator", "")

                # 1. Upsert into persona_lookbook
                cursor.execute("""
                    INSERT INTO persona_lookbook (
                        sys_id, lookbook_id, persona_id, shot_key, shot_category,
                        prompt_decorator, file_path, mime_type, created_at,
                        sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'image/png', ?, ?, ?, 'james', 'james', 0)
                    ON CONFLICT(persona_id, shot_key) DO UPDATE SET
                        file_path = excluded.file_path,
                        prompt_decorator = excluded.prompt_decorator,
                        shot_category = excluded.shot_category,
                        sys_updated_on = excluded.sys_updated_on,
                        sys_mod_count = persona_lookbook.sys_mod_count + 1
                """, (
                    sys_id, lookbook_id, advocate, shot_key, shot_category,
                    prompt_decorator, dest_png, now_iso, now_iso, now_iso
                ))

                # 2. Upsert into cmdb_ci_media_asset
                media_sys_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cmdb:media:{advocate}:{shot_key}").hex
                cursor.execute("""
                    INSERT INTO cmdb_ci_media_asset (
                        sys_id, advocate, expression, file_path, sha256, sys_created_on, sys_updated_on
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sys_id) DO UPDATE SET
                        file_path = excluded.file_path,
                        sha256 = excluded.sha256,
                        sys_updated_on = excluded.sys_updated_on
                """, (
                    media_sys_id, advocate, f"lookbook_{shot_key}", dest_png, sha256_hash, now_iso, now_iso
                ))

                # 3. Upsert into sys_media_asset
                sys_media_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"sys:media:{advocate}:{shot_key}").hex
                cursor.execute("""
                    INSERT INTO sys_media_asset (
                        sys_id, name, file_name, file_path, category, mime_type, file_size_bytes,
                        md5_hash, status, brand_id, asset_tag, sys_created_on, sys_updated_on
                    ) VALUES (?, ?, ?, ?, 'Persona Lookbook', 'image/png', ?, ?, 'Active', ?, ?, ?, ?)
                    ON CONFLICT(sys_id) DO UPDATE SET
                        file_path = excluded.file_path,
                        file_size_bytes = excluded.file_size_bytes,
                        md5_hash = excluded.md5_hash,
                        sys_updated_on = excluded.sys_updated_on
                """, (
                    sys_media_id, f"{advocate.title()} {shot_key.replace('_', ' ').title()}",
                    f"{shot_key}.png", dest_png, file_size, md5_hash, advocate.upper(),
                    f"LOOKBOOK_{shot_key.upper()}", now_iso, now_iso
                ))

                results.append({
                    "shot_key": shot_key,
                    "shot_category": shot_category,
                    "label": shot_info.get("label"),
                    "file_path": dest_png,
                    "sha256": sha256_hash,
                    "size_bytes": file_size
                })

            # Ensure default active_pose_key in m2m_persona_room
            cursor.execute("""
                UPDATE m2m_persona_room 
                SET active_pose_key = 'front_neutral' 
                WHERE (persona = ? OR persona = ?) AND (active_pose_key IS NULL OR active_pose_key = '')
            """, (advocate, advocate.upper()))

        print(f"🎉 Successfully seeded {len(results)} lookbook shots for advocate '{advocate}'.")
        return {
            "status": "SUCCESS",
            "advocate": advocate,
            "preset": preset,
            "total_shots": len(results),
            "canonical_anchor": canonical_anchor_path if os.path.exists(canonical_anchor_path) else None,
            "shots": results
        }

    finally:
        conn.close()
        if temp_extract_dir and os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Advocate Lookbook Seeder")
    parser.add_argument("--advocate", default="barf", help="Advocate handle (e.g. barf)")
    parser.add_argument("--preset", default="full22", choices=["core3", "telemetry8", "full22"], help="Shot preset")
    parser.add_argument("--zip-source", default="/home/james/sovereign_inbox/pilot_drops/barf_22.zip", help="Zip file source")
    parser.add_argument("--source-dir", help="Directory with extracted images")
    parser.add_argument("--ref-image", help="Explicit canonical reference image path")
    parser.add_argument("--matrix", default=DEFAULT_MATRIX_PATH, help="Path to pose matrix JSON")
    
    args = parser.parse_args()

    summary = seed_lookbook(
        advocate=args.advocate,
        preset=args.preset,
        zip_source=args.zip_source,
        source_dir=args.source_dir,
        ref_image=args.ref_image,
        matrix_path=args.matrix
    )
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
