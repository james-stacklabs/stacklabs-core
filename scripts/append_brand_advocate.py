#!/usr/bin/env python3
import os
import sys
import uuid
import argparse
import sqlite3
from PIL import Image

# Setup paths
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"

def crop_pose_local(anchor_path, pose_name, target_path, handle=None):
    """
    Local PIL Fallback: Crops three distinct sections from a 1376x768 landscape reference sheet
    representing different poses (avatar/front, pointing, shrug/expressive) to ensure 100% offline
    local rendering compliance. Supports custom coordinate matrices for known advocates.
    """
    img = Image.open(anchor_path)
    w, h = img.size
    
    handle_lower = (handle or "").lower()
    anchor_lower = os.path.basename(anchor_path).lower()
    
    is_keith = "keith" in handle_lower or "keith" in anchor_lower
    is_triplea = "triplea" in handle_lower or "triple_a" in handle_lower or "triple" in anchor_lower
    is_bluecrew = "bluecrew" in handle_lower or "blue_crew" in handle_lower or "bluecrew" in anchor_lower
    
    if is_keith:
        if w == 1024 and h == 1024:
            # Keith Hernandez Fanboy custom 1024x1024 coordinates
            coords = {
                "avatar": (0, 0, 341, 341),
                "pointing": (0, 682, 341, 1024),
                "shrug": (341, 682, 682, 1024)
            }
        else:
            # Keith Hernandez Fanboy custom landscape coordinates
            coords = {
                "avatar": (580, 60, 840, 320),
                "pointing": (190, 440, 510, 760),
                "shrug": (960, 40, 1260, 340)
            }
        box = coords.get(pose_name)
    elif is_triplea:
        if w == 1024 and h == 1024:
            # Triple A Truther custom 1024x1024 coordinates
            coords = {
                "avatar": (0, 0, 341, 341),
                "pointing": (682, 0, 1024, 341),
                "shrug": (0, 341, 341, 682)
            }
        else:
            # Triple A Truther custom landscape coordinates
            coords = {
                "avatar": (30, 500, 298, 768),
                "pointing": (374, 500, 642, 768),
                "shrug": (718, 500, 986, 768)
            }
        box = coords.get(pose_name)
    elif is_bluecrew:
        if w == 1024 and h == 1024:
            # BlueCrewBoss custom 1024x1024 coordinates
            coords = {
                "avatar": (0, 0, 341, 341),
                "pointing": (341, 0, 682, 341),
                "shrug": (682, 0, 1024, 341)
            }
        else:
            coords = {
                "avatar": (0, 0, 341, 341),
                "pointing": (341, 0, 682, 341),
                "shrug": (682, 0, 1024, 341)
            }
        box = coords.get(pose_name)
    else:
        # Fall back to default horizontal-slice heuristic
        if pose_name == "avatar":
            cx = int(w * 0.22)
        elif pose_name == "pointing":
            cx = int(w * 0.50)
        else:  # shrug
            cx = int(w * 0.78)
            
        crop_size = min(h, w)
        half_size = crop_size // 2
        
        left = max(0, min(cx - half_size, w - crop_size))
        top = max(0, min(int(h * 0.5) - half_size, h - crop_size))
        right = left + crop_size
        bottom = top + crop_size
        box = (left, top, right, bottom)
        
    cropped = img.crop(box)
    cropped = cropped.resize((512, 512), Image.Resampling.LANCZOS)
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    cropped.save(target_path, "PNG")
    print(f"  [PIL Fallback] Successfully cropped {pose_name} from {box} -> {target_path}")


def generate_pose_vertex(client, anchor_path, pose_name, prompt_details, target_path):
    """
    Vertex AI Style Reference generator.
    """
    from google.genai import types
    
    print(f"  [Vertex AI] Generating {pose_name} with style reference from {anchor_path}...")
    ref_image = types.Image.from_file(location=anchor_path)
    
    style_ref = types.StyleReferenceImage(
        reference_image=ref_image,
        reference_id=1,
        config=types.StyleReferenceConfig(style_description=prompt_details)
    )
    
    prompt_map = {
        "avatar": f"A 1:1 portrait avatar headshot looking directly at the camera, {prompt_details}",
        "pointing": f"A 1:1 portrait headshot pointing dynamically with a hand, {prompt_details}",
        "shrug": f"A 1:1 portrait headshot shrugging shoulders and looking expressive, {prompt_details}"
    }
    
    sys.path.append("/home/james/stacklabs/scripts")
    from imagen_util import verify_imagen_model_health
    _, working_model = verify_imagen_model_health()
    if not working_model:
        working_model = "imagen-3.0-generate-002"
        
    response = client.models.edit_image(
        model=working_model,
        prompt=prompt_map[pose_name],
        reference_images=[style_ref],
        config=types.EditImageConfig(
            number_of_images=1,
            aspect_ratio="1:1",
            edit_mode="EDIT_MODE_STYLE"
        )
    )
    
    if response.generated_images:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(response.generated_images[0].image.image_bytes)
        print(f"  [Vertex AI] Saved {pose_name} to {target_path}")
    else:
        raise ValueError("Vertex AI returned empty generation results")

def append_advocate(args):
    print(f"[*] Ingesting advocate handle: @{args.handle} under team {args.team}...")
    
    # 1. Database connection and ID resolution
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if advocate exists in persona
    cur.execute("SELECT id FROM persona WHERE user_name = ?", (args.handle,))
    row = cur.fetchone()
    if row:
        sys_id = row[0]
        print(f"[*] Found existing advocate record. Reusing ID: {sys_id}")
    else:
        sys_id = uuid.uuid4().hex
        print(f"[*] Generating new UUID for advocate: {sys_id}")
        
    # 2. Path definitions for output files
    relative_avatar_path = f"/avatars/{args.handle}/{args.handle}_avatar.png"
    
    portal_base = f"/home/james/stacklabs/01_Sovereign_Portal/public/avatars/{args.handle}"
    fanstack_base = f"/home/james/stacklabs/15_FanStack/public/avatars/{args.handle}"
    
    poses = ["avatar", "pointing", "shrug"]
    
    # 3. Avatar Generation Loop
    use_vertex = False
    client = None
    if not args.local_only and os.path.exists(CREDENTIALS_PATH):
        try:
            import google.genai as genai
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
            client = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=LOCATION
            )
            use_vertex = True
            print("[*] Vertex AI client successfully initialized.")
        except Exception as e:
            print(f"[!] Failed to initialize Vertex AI client: {e}. Falling back to local cropping.")
            
    for pose in poses:
        portal_path = f"{portal_base}/{pose}.png"
        fanstack_path = f"{fanstack_base}/{pose}.png"
        portal_prefix_path = f"{portal_base}/{args.handle}_{pose}.png"
        fanstack_prefix_path = f"{fanstack_base}/{args.handle}_{pose}.png"
        
        generated = False
        if use_vertex:
            try:
                generate_pose_vertex(client, args.anchor_image, pose, args.avatar_prompt, portal_path)
                generated = True
            except Exception as e:
                print(f"[!] Vertex generation failed for pose '{pose}': {e}. Falling back to PIL crop.")
                
        if not generated:
            # Fall back to local cropping
            crop_pose_local(args.anchor_image, pose, portal_path, args.handle)
            
        # Replicate cropped pose to all target files
        import shutil
        os.makedirs(os.path.dirname(fanstack_path), exist_ok=True)
        for dest in [fanstack_path, portal_prefix_path, fanstack_prefix_path]:
            try:
                if os.path.exists(dest) and os.path.samefile(portal_path, dest):
                    continue
                shutil.copy2(portal_path, dest)
            except (shutil.SameFileError, AttributeError, OSError):
                pass
        print(f"  [Replication] Synchronized {pose} across standard and prefixed paths.")
            
    # Double-check files exist and are not SVGs
    for pose in poses:
        for path in [f"{portal_base}/{pose}.png", f"{portal_base}/{args.handle}_{pose}.png"]:
            if not os.path.exists(path):
                raise ValueError(f"Required PNG pose file {path} was not created!")
            if path.lower().endswith(".svg"):
                raise ValueError(f"Forbidden SVG asset type detected: {path}")
            
    # 4. Database Updates (Non-destructive upsert)
    try:
        # a. persona table
        cur.execute("""
            INSERT OR REPLACE INTO persona
            (id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence, deep_lore, behavior_notes, governance, u_visual_style, u_deployment_zone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt', ?)
        """, (
            sys_id, args.handle, args.display_name, args.team, args.system_prompt,
            args.boggs_level, relative_avatar_path, args.color, args.cadence,
            args.deep_lore, args.behavior, args.governance, args.deployment_zone
        ))
        
        # b. cmdb_ci_ai_persona table
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_ai_persona
            (sys_id, u_system_prompt, u_deployment_zone, u_boggs_reactivity, u_cadence, u_deep_lore, u_governance_boundaries, u_behavior_expectations, u_avatar_prompt, u_visual_style)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'style_felt')
        """, (
            sys_id, args.system_prompt, args.deployment_zone, str(args.boggs_level),
            args.cadence, args.deep_lore, args.governance, args.behavior, args.avatar_prompt
        ))
        
        # c. cmdb_ci table
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci
            (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, 'cmdb_ci_ai_persona', ?, 1)
        """, (
            sys_id, args.display_name, args.system_prompt[:100]
        ))
        
        # d. sys_user table
        cur.execute("""
            INSERT OR REPLACE INTO sys_user
            (sys_id, user_name, display_name, active, role, avatar_url, favorite_team)
            VALUES (?, ?, ?, 1, 'creator', ?, ?)
        """, (
            sys_id, args.handle, args.display_name, relative_avatar_path, args.team
        ))
        
        # e. Ensure room mapping exists in m2m_persona_room if deployment_zone is set
        if args.deployment_zone and args.deployment_zone != "BENCHED":
            cur.execute("""
                INSERT OR IGNORE INTO m2m_persona_room
                (sys_id, persona, room, prompt_overlay)
                VALUES (?, ?, ?, '')
            """, (uuid.uuid4().hex, args.handle, args.deployment_zone))
            
        conn.commit()
        print(f"[+] Successfully registered advocate {args.handle} in all system registries.")
    except Exception as dbe:
        conn.rollback()
        raise ValueError(f"Database insertion error: {dbe}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modular PNG-native Advocate Ingestion Tool")
    parser.add_argument("--handle", required=True, help="Advocate username/handle without @ prefix")
    parser.add_argument("--team", required=True, help="Parent brand/team code (e.g., NYM, GLOBAL)")
    parser.add_argument("--display_name", required=True, help="Display Name")
    parser.add_argument("--role", required=True, help="Role or title of the advocate")
    parser.add_argument("--bio", required=True, help="Profile short biography")
    parser.add_argument("--system_prompt", required=True, help="AI system instructions")
    parser.add_argument("--deep_lore", required=True, help="Background lore")
    parser.add_argument("--behavior", required=True, help="Behavior notes")
    parser.add_argument("--governance", required=True, help="Governance boundaries")
    parser.add_argument("--color", required=True, help="Hex color code")
    parser.add_argument("--anchor_image", required=True, help="Absolute path to the anchor image sheet")
    parser.add_argument("--avatar_prompt", required=True, help="Prompt details for Imagen generation style reference")
    parser.add_argument("--deployment_zone", default="BENCHED", help="Target room or BENCHED")
    parser.add_argument("--cadence", default="agitator", help="Posting cadence")
    parser.add_argument("--boggs_level", type=int, default=4, help="Boggs reactivity level (1-5)")
    parser.add_argument("--local-only", action="store_true", help="Force local Pillow cropping without calling Vertex")
    
    args = parser.parse_args()
    try:
        append_advocate(args)
        print("✅ Advocate Ingestion Campaign Successful.")
        sys.exit(0)
    except Exception as err:
        print(f"❌ Advocate Ingestion Failed: {err}")
        sys.exit(1)
