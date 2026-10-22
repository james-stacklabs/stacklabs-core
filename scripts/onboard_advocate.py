#!/usr/bin/env python3
"""
Sovereign OS: Unified FanStack & Sovereign Sports Advocate Onboarding Engine
Path: /home/james/stacklabs/scripts/onboard_advocate.py

Single-command, deterministic onboarding for new advocates from a markdown profile or flags.
Syncs visual assets, upserts database tables, registers CMDB CIs, and seats into game rooms.

Usage:
  python3 scripts/onboard_advocate.py <advocate_sheet.md> [--image <path_to_image>] [--rooms room1,room2]
  python3 scripts/onboard_advocate.py --handle googly_bastard --team NYJ --name "Major Eddie Vance" --image ...
"""

import os
import sys
import re
import json
import uuid
import shutil
import base64
import hashlib
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Root & DB Paths
SOVEREIGN_ROOT = Path("/home/james/stacklabs")
DB_PATH = SOVEREIGN_ROOT / "dna" / "sovereign_now.db"

# Destination directories for avatar distribution
DEST_AVATAR_DIRS = [
    SOVEREIGN_ROOT / "avatars",
    SOVEREIGN_ROOT / "15_FanStack" / "public" / "avatars",
    SOVEREIGN_ROOT / "01_Sovereign_Portal" / "public" / "avatars",
    SOVEREIGN_ROOT / "19_Sovereign_Sports" / "public" / "avatars",
    SOVEREIGN_ROOT / "apps" / "fanstack_creator" / "public" / "avatars",
    SOVEREIGN_ROOT / "33_FanStack_Lite" / "public" / "avatars"
]

def get_hashes(filepath):
    md5_h = hashlib.md5()
    sha_h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            md5_h.update(chunk)
            sha_h.update(chunk)
    return md5_h.hexdigest(), sha_h.hexdigest()

def generate_next_asset_tag(cur):
    try:
        cur.execute("SELECT asset_tag FROM sys_media_asset")
        max_num = 0
        for (tag,) in cur.fetchall():
            if tag and tag.startswith("FS-MED-"):
                match = re.search(r'FS-MED-(\d+)', tag)
                if match:
                    num = int(match.group(1))
                    if num < 99999 and num > max_num:
                        max_num = num
        return f"FS-MED-{max_num + 1:05d}"
    except Exception:
        return f"FS-MED-{int(datetime.now().timestamp())}"

def parse_markdown_sheet(sheet_path):
    with open(sheet_path, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {
        "handle": None,
        "display_name": None,
        "team": "GLOBAL",
        "cadence": "pacer",
        "boggs_level": 2,
        "system_prompt": "",
        "deep_lore": "",
        "behavior_notes": "",
        "governance": "",
        "color": "#125740",
        "rooms": [],
        "canned_takes": []
    }

    # 1. Parse JSON metadata block if present
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            meta = json.loads(json_match.group(1))
            data.update({
                "handle": meta.get("user_name") or meta.get("handle"),
                "display_name": meta.get("display_name"),
                "team": meta.get("team", data["team"]),
                "cadence": meta.get("cadence", data["cadence"]),
                "boggs_level": meta.get("boggs_level", data["boggs_level"]),
                "color": meta.get("color", data["color"]),
                "rooms": meta.get("rooms", []),
                "canned_takes": meta.get("canned_takes", [])
            })
        except Exception as e:
            print(f"[!] Warning parsing JSON block: {e}")

    # 2. Parse Standard Section 4 Advocate Lore Forge Header: ##### @<handle> — <Display Title>
    hdr_match = re.search(r'#####\s*@([a-zA-Z0-9_]+)\s*—\s*([^\n]+)', content)
    if hdr_match:
        if not data["handle"]:
            data["handle"] = hdr_match.group(1).strip().lower()
        if not data["display_name"]:
            data["display_name"] = hdr_match.group(2).strip()

    # 3. Fallback Header format: # @<handle> or # Character Lore
    if not data["handle"]:
        h_match = re.search(r'\*\*X Handle:\*\*\s*[`@]*([a-zA-Z0-9_]+)', content)
        if h_match:
            data["handle"] = h_match.group(1).strip().lower()
        else:
            base = os.path.splitext(os.path.basename(sheet_path))[0]
            data["handle"] = base.split('_')[-1].lower() if '_' in base else base.lower()

    if not data["display_name"]:
        data["display_name"] = data["handle"].replace('_', ' ').title()

    # 4. Parse key fields via Regex
    team_m = re.search(r'-\s*\*\*Team:\*\*\s*[`"]?([A-Z0-9_]+)[`"]?', content)
    if team_m and data["team"] == "GLOBAL":
        data["team"] = team_m.group(1).strip()

    cadence_m = re.search(r'-\s*\*\*Interaction Cadence:\*\*\s*[`"]?([a-zA-Z0-9_]+)[`"]?', content)
    if cadence_m:
        data["cadence"] = cadence_m.group(1).strip()

    boggs_m = re.search(r'-\s*\*\*Boggs Reactivity.*?:\*\*\s*Level\s*(\d+)', content, re.IGNORECASE)
    if boggs_m:
        data["boggs_level"] = int(boggs_m.group(1))

    prompt_m = re.search(r'-\s*\*\*System Instruction / Directive:\*\*\s*(.*?)(?=\n-\s*\*|\Z)', content, re.DOTALL)
    if prompt_m:
        data["system_prompt"] = prompt_m.group(1).strip()

    lore_m = re.search(r'-\s*\*\*Deep Lore & Cultural DNA:\*\*\s*(.*?)(?=\n-\s*\*|\Z)', content, re.DOTALL)
    if lore_m:
        data["deep_lore"] = lore_m.group(1).strip()

    notes_m = re.search(r'-\s*\*\*Tactical Obsession & Schematic Trigger:\*\*\s*(.*?)(?=\n-\s*\*|\Z)', content, re.DOTALL)
    if notes_m:
        data["behavior_notes"] = notes_m.group(1).strip()

    gov_m = re.search(r'-\s*\*\*Governance & Alignment Boundaries:\*\*\s*(.*?)(?=\n-\s*\*|\Z)', content, re.DOTALL)
    if gov_m:
        data["governance"] = gov_m.group(1).strip()

    # Default rooms if empty
    if not data["rooms"]:
        t = data["team"].lower()
        data["rooms"] = ["global", "fanstack_gridiron", f"team_{t}", f"nfl_{t}", data["team"]]

    return data

def process_image(handle, display_name, image_path, cur):
    if not image_path or not os.path.exists(image_path):
        print(f"[~] No image provided or file not found at {image_path}. Using placeholder avatar URL.")
        return f"/avatars/{handle}/{handle}_avatar.png"

    from PIL import Image

    print(f"[*] Processing visual asset: {image_path}")
    img = Image.open(image_path).convert("RGB")

    # Target filenames
    avatar_rel_path = f"/avatars/{handle}/{handle}_avatar.png"

    # Distribute across destination directories
    for dest_dir in DEST_AVATAR_DIRS:
        char_dir = dest_dir / handle
        char_dir.mkdir(parents=True, exist_ok=True)

        # Save both full and avatar
        img.save(char_dir / f"{handle}_avatar.png", "PNG")
        img.save(char_dir / f"{handle}.png", "PNG")
        img.save(char_dir / "avatar.png", "PNG")
        if dest_dir.name == "avatars":
            img.save(dest_dir / f"{handle}.png", "PNG")

    print(f"[+] Distributed avatar across {len(DEST_AVATAR_DIRS)} platform directories.")

    # Register into sys_media_asset
    canonical_file = SOVEREIGN_ROOT / "avatars" / handle / f"{handle}_avatar.png"
    size = os.path.getsize(canonical_file)
    md5_h, sha256_h = get_hashes(canonical_file)

    with open(canonical_file, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")

    cur.execute("SELECT sys_id FROM sys_media_asset WHERE file_path = ?", (str(canonical_file),))
    existing = cur.fetchone()

    asset_name = f"{display_name} Avatar"
    if existing:
        sys_id = existing[0]
        cur.execute("""
            UPDATE sys_media_asset
            SET name = ?, file_size_bytes = ?, md5_hash = ?, image_blob = ?, updated_at = datetime('now'), sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (asset_name, size, md5_h, b64_data, sys_id))
        print(f"[+] Updated sys_media_asset: {sys_id}")
    else:
        sys_id = uuid.uuid4().hex
        tag = generate_next_asset_tag(cur)
        cur.execute("""
            INSERT INTO sys_media_asset (sys_id, asset_tag, name, file_name, file_path, file_size_bytes, mime_type, category, status, md5_hash, image_blob, created_at, updated_at, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, ?, ?, 'image/png', 'FanStack Avatars', 'Active', ?, ?, datetime('now'), datetime('now'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (sys_id, tag, asset_name, f"{handle}_avatar.png", str(canonical_file), size, md5_h, b64_data))
        print(f"[+] Inserted sys_media_asset: {sys_id} with tag {tag}")

    return avatar_rel_path

def onboard_advocate(data, image_path=None):
    handle = data["handle"]
    display_name = data["display_name"]
    team = data["team"]
    color = data["color"]
    cadence = data["cadence"]
    boggs_level = data["boggs_level"]
    system_prompt = data["system_prompt"]
    deep_lore = data["deep_lore"]
    behavior_notes = data["behavior_notes"]
    governance = data["governance"]
    rooms = data["rooms"]
    canned_takes = data["canned_takes"]

    print("=" * 75)
    print(f"ONBOARDING ADVOCATE: @{handle} — {display_name} ({team})")
    print("=" * 75)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout = 30000;")
    cur = con.cursor()

    # 1. Image Processing & Media Registration
    avatar_url = process_image(handle, display_name, image_path, cur)

    # 2. Check / Upsert `persona` table
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (handle,))
    row = cur.fetchone()

    email_alias = f"sovereign.fanstack+{handle}@gmail.com"
    canned_takes_json = json.dumps(canned_takes) if canned_takes else "[]"

    if row:
        persona_id = row[0]
        print(f"[*] Updating persona record: {handle} ({persona_id})")
        cur.execute("""
            UPDATE persona SET
                display_name = ?,
                team = ?,
                system_prompt = ?,
                avatar_url = ?,
                color = ?,
                deep_lore = ?,
                cadence = ?,
                boggs_level = ?,
                behavior_notes = ?,
                governance = ?,
                email_alias = ?,
                canned_takes = ?,
                updated_at = datetime('now'),
                sys_updated_on = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (display_name, team, system_prompt, avatar_url, color, deep_lore, cadence, boggs_level, behavior_notes, governance, email_alias, canned_takes_json, persona_id))
    else:
        persona_id = f"adv_{team.lower()}_{handle}"
        print(f"[+] Inserting new persona record: {handle} ({persona_id})")
        cur.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level,
                avatar_url, color, cadence, deep_lore, behavior_notes, governance,
                email_alias, canned_takes, visual_style, deployment_zone, is_heel, is_sophisticated,
                created_at, updated_at, sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', 'bleachers', 0, 1, datetime('now'), datetime('now'), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (persona_id, handle, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, behavior_notes, governance, email_alias, canned_takes_json))

    # 3. Check / Upsert `sys_user` table
    name_parts = display_name.split(" ")
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    cur.execute("SELECT sys_id FROM sys_user WHERE user_name = ?", (handle,))
    user_row = cur.fetchone()
    if user_row:
        user_sys_id = user_row[0]
        cur.execute("""
            UPDATE sys_user SET
                first_name = ?, last_name = ?, introduction = ?, department = ?, display_name = ?, avatar_url = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (first_name, last_name, behavior_notes, team, display_name, avatar_url, user_sys_id))
    else:
        user_sys_id = uuid.uuid4().hex
        cur.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, first_name, last_name, title, introduction, department, active, role, display_name, avatar_url
            ) VALUES (?, ?, ?, ?, 'Advocate', ?, ?, 1, 'advocate', ?, ?)
        """, (user_sys_id, handle, first_name, last_name, behavior_notes, team, display_name, avatar_url))

    # 4. Check / Upsert `cmdb_ci` and `cmdb_ci_ai_persona`
    cur.execute("SELECT sys_id FROM cmdb_ci WHERE name = ?", (handle,))
    ci_row = cur.fetchone()
    if ci_row:
        ci_id = ci_row[0]
        cur.execute("""
            UPDATE cmdb_ci SET assigned_to = ?, short_description = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ?
        """, (team, f"Sovereign Advocate: {display_name}", ci_id))
    else:
        ci_id = uuid.uuid4().hex
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, assigned_to, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', ?, ?, 1)
        """, (ci_id, handle, team, f"Sovereign Advocate: {display_name}"))

    cur.execute("SELECT sys_id FROM cmdb_ci_ai_persona WHERE sys_id = ?", (ci_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE cmdb_ci_ai_persona SET
                system_prompt = ?, deep_lore = ?, cadence = ?, boggs_reactivity = ?, sys_updated_on = CURRENT_TIMESTAMP
            WHERE sys_id = ?
        """, (system_prompt, deep_lore, cadence, str(boggs_level), ci_id))
    else:
        cur.execute("""
            INSERT INTO cmdb_ci_ai_persona (sys_id, system_prompt, deep_lore, cadence, boggs_reactivity, visual_style)
            VALUES (?, ?, ?, ?, ?, 'style_felt')
        """, (ci_id, system_prompt, deep_lore, cadence, str(boggs_level)))

    # 5. Seat into `m2m_persona_room`
    seated_rooms = []
    for r in rooms:
        cur.execute("SELECT sys_id FROM m2m_persona_room WHERE persona = ? AND room = ?", (handle, r))
        if not cur.fetchone():
            room_link_id = uuid.uuid4().hex
            cur.execute("""
                INSERT INTO m2m_persona_room (sys_id, persona, room, sys_created_on, sys_updated_on, active_pose_key)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'front_neutral')
            """, (room_link_id, handle, r))
            seated_rooms.append(r)
        else:
            seated_rooms.append(r)

    con.commit()
    con.close()
    print(f"[+] SQLite WAL commit confirmed on metal ({DB_PATH}). Seated across {len(seated_rooms)} rooms.")

    # 6. Optional: Deploy through Portal FastAPI if online
    try:
        sys.path.insert(0, str(SOVEREIGN_ROOT))
        from scripts.core import api_client
        res = api_client.deploy_persona(
            handle=handle,
            display_name=display_name,
            team=team,
            system_prompt=system_prompt,
            deep_lore=deep_lore,
            behavior_notes=behavior_notes,
            governance=governance,
            color=color,
            cadence=cadence,
            boggs_level=boggs_level,
            avatar_url=avatar_url,
            rooms=rooms,
            canned_takes=canned_takes
        )
        if res.get("status") == "success":
            print(f"[+] FastAPI Portal mesh sync confirmed (Port 8095): {res.get('persona_id')}")
    except Exception as e:
        print(f"[~] Note: Portal FastAPI daemon offline or skipped ({e}). Direct SQLite state is locked.")

    receipt = {
        "status": "ONBOARDED",
        "handle": f"@{handle}",
        "display_name": display_name,
        "team": team,
        "cadence": cadence,
        "boggs_level": boggs_level,
        "avatar_url": avatar_url,
        "rooms": seated_rooms,
        "persona_id": persona_id,
        "email_alias": email_alias
    }

    print("\n" + json.dumps(receipt, indent=2))
    return receipt

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Advocate Onboarding Engine")
    parser.add_argument("sheet", nargs="?", help="Path to markdown advocate profile")
    parser.add_argument("--image", help="Path to avatar/source image file")
    parser.add_argument("--handle", help="Override handle")
    parser.add_argument("--team", help="Override team code")
    parser.add_argument("--name", help="Override display name")
    parser.add_argument("--rooms", help="Comma-separated list of room IDs")

    args = parser.parse_args()

    if args.sheet:
        data = parse_markdown_sheet(args.sheet)
    else:
        if not args.handle or not args.team:
            print("❌ Error: Must provide either a markdown sheet path or --handle and --team flags.")
            sys.exit(1)
        data = {
            "handle": args.handle.replace('@', '').lower(),
            "display_name": args.name or args.handle.title(),
            "team": args.team.upper(),
            "cadence": "pacer",
            "boggs_level": 2,
            "system_prompt": "",
            "deep_lore": "",
            "behavior_notes": "",
            "governance": "",
            "color": "#125740",
            "rooms": args.rooms.split(',') if args.rooms else [],
            "canned_takes": []
        }

    if args.handle:
        data["handle"] = args.handle.replace('@', '').lower()
    if args.team:
        data["team"] = args.team.upper()
    if args.name:
        data["display_name"] = args.name
    if args.rooms:
        data["rooms"] = [r.strip() for r in args.rooms.split(',')]

    onboard_advocate(data, image_path=args.image)

if __name__ == "__main__":
    main()
