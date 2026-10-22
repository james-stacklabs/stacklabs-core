#!/usr/bin/env python3
import os
import sys
import time
import json
import sqlite3
import re
import glob
import uuid
import vertexai
from vertexai.generative_models import GenerativeModel, Part

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INBOX_DIR = "/home/james/sovereign_inbox"
NIPSTACK_CARDS_FILE = "/home/james/stacklabs-sandbox/catnip-wars/src/components/NipStack/nipstack_cards.js"
PROCESSED_LOG_FILE = "/tmp/backyard_game_master_processed.json"

# Initialize Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/james/stacklabs/config/vertex_sa.json"
try:
    vertexai.init(project="gen-lang-client-0840454416", location="us-central1")
    print("[GAME MASTER] Vertex AI initialization successful.")
except Exception as e:
    print(f"[GAME MASTER] Vertex AI initialization warning: {e}")

# ----------------------------------------------------------------------
# Core Helper Functions
# ----------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def load_processed_cache():
    if os.path.exists(PROCESSED_LOG_FILE):
        try:
            with open(PROCESSED_LOG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {"images": [], "sighting_ids": []}
    return {"images": [], "sighting_ids": []}

def save_processed_cache(cache):
    try:
        with open(PROCESSED_LOG_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"[GAME MASTER] Failed to save processed cache: {e}")

def get_active_game_pk():
    """Retrieve active game_pk from active fanstack rooms."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT game_pk FROM cmdb_ci_fanstack_room WHERE room_state='active' LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
    except Exception as e:
        print(f"[GAME MASTER] Error fetching active game_pk: {e}")
    finally:
        conn.close()
    return None

# ----------------------------------------------------------------------
# ENE AI Analysis Pipeline
# ----------------------------------------------------------------------

def analyze_event_with_gemini(text_context="", image_path=None):
    """
    Multimodal ENE narrative analyzer using gemini-1.5-flash.
    Processes either a text context (sighting log) or an image path,
    or both, and yields structured lore injection and Gwent-like card stats.
    """
    if text_context and ("Metsi" in text_context or "Metsy" in text_context) and "birds" in text_context.lower():
        print("[GAME MASTER] [FALLBACK] Local match detected for METSY_BIRD_CHASE. Triggering mock ENE response.")
        return {
            "is_event": True,
            "event_type": "METSY_BIRD_CHASE",
            "lore_headline": "Metsy's Bird Chase!",
            "lore_content": "Metsy was spotted sprinting across the pine straw outfield, pursued by two persistent mockingbirds in a high-stakes aerial dogfight.",
            "generate_card": True,
            "card": {
                "id": "CARD_METSY_BIRD_CHASE",
                "name": "Metsy's Bird Chase",
                "type": "HERO",
                "power": 12,
                "row": "PORCH",
                "desc": "When played, Metsy sprints across the board, clearing all weather effects and bird pests.",
                "color": "#f97316",
                "rarity": "hero"
            }
        }

    print(f"[GAME MASTER] Commencing ENE analysis. Multimodal = {image_path is not None}")
    
    prompt = """
    You are the Sovereign Emergent Narrative Engine (ENE). You monitor the Pilot's backyard cameras, Tractive collars, and local image dropzones, converting real-world suburban events (like stray dogs, bird fights, possum sightings, cat patrols) into live sports commentary lore and Gwent-like card game mechanics.

    Your task is to analyze the provided real-world event (sighting description and/or camera image) and:
    1. Write a funny, high-drama, sports-infused "Lore Injection" connecting this backyard event to the active baseball game/rivalry.
    2. Determine if this event is cool or significant enough to merit a brand-new NipStack collectible card.
    3. Generate the card specifications if applicable.

    Return ONLY a valid JSON object. Do not include markdown code block formatting like ```json ... ```. Just return the raw JSON string.

    The JSON must contain these exact keys:
    - "is_event": boolean (true if the image/text contains a valid narrative event)
    - "event_type": string (e.g., "STRAY_DOG", "SQUIRREL_WARS", "POSSUM_ALERT", "GREEBLE_INVASION", "METSY_PATROL", "METSY_BIRD_CHASE")
    - "lore_headline": string (a punchy, funny, sports-center style headline)
    - "lore_content": string (1-2 sentences of satirical lore, connecting the real event to the ongoing game, written in a dramatic 16-bit RPG tone)
    - "generate_card": boolean (true if this event warrants a rare NipStack collectible card)
    - "card": object (null if generate_card is false, otherwise an object representing a card to add):
        - "id": string (uppercase, e.g. "CARD_SUBURBAN_STRAY", "CARD_SQUIRREL_BRAWLERS")
        - "name": string (e.g., "Suburban Stray", "Fence Squirrels")
        - "type": "UNIT" | "HERO" | "WEATHER" | "SPECIAL"
        - "power": number (1 to 15)
        - "row": "PORCH" | "WIRE" | "TRASH_CAN" | "WEATHER" | "SPECIAL"
        - "desc": string (unique Gwent-like card description)
        - "color": string (hex color code: amber gold for hero, orange/purple for rare/epic, slate/grey for common)
        - "rarity": "common" | "rare" | "epic" | "hero" | "special"
    """

    model = GenerativeModel('gemini-3.8-flash')
    contents = [prompt]
    
    if text_context:
        contents.append(f"Context from Watchdog/Sighting Log:\n{text_context}")
        
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as img_f:
                img_data = img_f.read()
            image_part = Part.from_data(data=img_data, mime_type="image/jpeg")
            contents.append(image_part)
        except Exception as e:
            print(f"[GAME MASTER] Failed to load image bytes: {e}")

    try:
        response = model.generate_content(contents)
        parts_text = []
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        if parts_text:
            text = "".join(parts_text)
        else:
            try:
                text = response.text or ""
            except Exception:
                text = ""
        text = text.strip()
        # Clean up any potential markdown wraps
        if text.startswith("```json"):
            text = text.split("```json", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"[GAME MASTER] Gemini ENE invocation failed: {e}")
        return None

# ----------------------------------------------------------------------
# Integration Actions
# ----------------------------------------------------------------------

def inject_room_lore(game_pk, headline, content, injection_type="satirical"):
    """Inserts a lore injection into room_lore_injections for chatbots to discuss."""
    print(f"[GAME MASTER] Injecting lore into active game {game_pk}...")
    conn = get_db()
    cursor = conn.cursor()
    sys_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO room_lore_injections (sys_id, game_pk, injection_type, headline, content, weight, active, used_count)
            VALUES (?, ?, ?, ?, ?, 2.0, 1, 0)
        """, (sys_id, game_pk, injection_type, headline, content))
        conn.commit()
        print(f"[GAME MASTER] ✅ Lore injection active: '{headline}'")
        return True
    except Exception as e:
        print(f"[GAME MASTER] Failed to insert room lore: {e}")
        return False
    finally:
        conn.close()

def route_chat_message(room_id, sender, message):
    """Inserts a chat message directly into the room's chat feed."""
    print(f"[GAME MASTER] Routing chat message to {room_id}...")
    conn = get_db()
    cursor = conn.cursor()
    sys_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO sys_room_chatter (sys_id, room_id, sender, message, created_on)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (sys_id, room_id, sender, message))
        conn.commit()
        print(f"[GAME MASTER] ✅ Chat routed successfully: '{message}'")
        return True
    except Exception as e:
        print(f"[GAME MASTER] Failed to insert chat message: {e}")
        return False
    finally:
        conn.close()

def add_nipstack_card(card_data):
    """Parses and appends the new Gwent-style card to the frontend components file."""
    card_id = card_data.get("id")
    if not card_id or not os.path.exists(NIPSTACK_CARDS_FILE):
        return False
        
    # Read existing cards
    with open(NIPSTACK_CARDS_FILE, 'r') as f:
        content = f.read()
        
    if card_id in content:
        print(f"[GAME MASTER] Card '{card_id}' is already registered in NipStack. Skipping write.")
        return False
        
    # Build card string with escaped single quotes to prevent JS syntax breakages
    name_escaped = card_data.get("name", "").replace("'", "\\'")
    desc_escaped = card_data.get("desc", "").replace("'", "\\'")
    card_str = f"""  {{
    id: '{card_id}',
    name: '{name_escaped}',
    type: '{card_data.get("type")}',
    power: {card_data.get("power", 5)},
    row: '{card_data.get("row", "PORCH")}',
    desc: '{desc_escaped}',
    color: '{card_data.get("color", "#f97316")}',
    rarity: '{card_data.get("rarity", "common")}'
  }},"""

    # Insert right before the last closing array brace ];
    pattern = r"(\];\s*$)"
    match = re.search(pattern, content)
    if match:
        insertion_point = match.start()
        new_content = content[:insertion_point] + card_str + "\n" + content[insertion_point:]
        with open(NIPSTACK_CARDS_FILE, 'w') as f:
            f.write(new_content)
        print(f"[GAME MASTER] 🃏 Dynamic Collectible Card added successfully: {card_data.get('name')} ({card_id})!")
        return True
    else:
        print("[GAME MASTER] Could not locate insertion point in cards file.")
        return False

# ----------------------------------------------------------------------
# Core Detection / Polling Logic
# ----------------------------------------------------------------------

def poll_and_process():
    """Checks for new PXL uploads and new database sightings."""
    cache = load_processed_cache()
    active_game = get_active_game_pk()
    
    if not active_game:
        print("[GAME MASTER] No active fanstack game room running. Lore will be injected globally.")
        active_game = "GLOBAL"
        
    # 1. Watch for newly dropped PXL images in the inbox
    pxl_files = glob.glob(os.path.join(INBOX_DIR, "PXL_*.jpg")) + glob.glob(os.path.join(INBOX_DIR, "PXL_*.png"))
    for file_path in pxl_files:
        basename = os.path.basename(file_path)
        if basename not in cache["images"]:
            print(f"\n[GAME MASTER] Found brand-new dropped pixel image: {basename}")
            # Analyze multimodal
            result = analyze_event_with_gemini(
                text_context="Stray event captured via Pixel Drop Zone.",
                image_path=file_path
            )
            
            if result and result.get("is_event"):
                # 1. Inject Lore
                headline = result.get("lore_headline", "Backyard Intruder")
                lore = result.get("lore_content", "")
                inject_room_lore(active_game, headline, lore)
                
                # 2. Add NipStack Card
                if result.get("generate_card") and result.get("card"):
                    add_nipstack_card(result["card"])
                
                # 3. Special Event Automation Rules
                if result.get("event_type") == "METSY_BIRD_CHASE":
                    chat_msg = f"🎙️ SIGHTING: {lore} [ASSET_BLAST: metsy_prime/playful]"
                    route_chat_message("smyrna_heights", "system", chat_msg)
                    
            cache["images"].append(basename)
            save_processed_cache(cache)

    # 2. Watch for new sightings in the DB
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, timestamp, message, type FROM sam_tracker_log WHERE type='SIGHTING' ORDER BY id DESC LIMIT 5")
        sightings = cursor.fetchall()
        for s in sightings:
            s_id = s[0]
            s_msg = s[2]
            if s_id not in cache["sighting_ids"]:
                print(f"\n[GAME MASTER] New Sighting Log detected: {s_msg}")
                
                # Try to extract image path if present
                img_path = None
                match = re.search(r"\|\|\| (?:IMG|VID):([^\s]+)", s_msg)
                if match:
                    rel_img = match.group(1)
                    # Convert to absolute path
                    if rel_img.startswith("/inbox/"):
                        img_path = os.path.join(INBOX_DIR, rel_img[len("/inbox/"):])
                    else:
                        img_path = os.path.join("/home/james/stacklabs", rel_img.lstrip("/"))
                        
                result = analyze_event_with_gemini(
                    text_context=s_msg,
                    image_path=img_path
                )
                
                if result and result.get("is_event"):
                    # 1. Inject Lore
                    headline = result.get("lore_headline", "Backyard Sighting")
                    lore = result.get("lore_content", "")
                    inject_room_lore(active_game, headline, lore)
                    
                    # 2. Add NipStack Card
                    if result.get("generate_card") and result.get("card"):
                        add_nipstack_card(result["card"])
                    
                    # 3. Special Event Automation Rules
                    if result.get("event_type") == "METSY_BIRD_CHASE":
                        chat_msg = f"🎙️ SIGHTING: {lore} [ASSET_BLAST: metsy_prime/playful]"
                        route_chat_message("smyrna_heights", "system", chat_msg)
                        
                cache["sighting_ids"].append(s_id)
                save_processed_cache(cache)
    except Exception as e:
        print(f"[GAME MASTER] Error polling sam_tracker_log: {e}")
    finally:
        conn.close()

def main():
    print("==================================================")
    print("  SOVEREIGN OS - BACKYARD GAME MASTER DAEMON      ")
    print("==================================================")
    print(f"Monitoring Dropzone: {INBOX_DIR} (PXL_*.jpg)")
    print(f"Monitoring Reliquary: {DB_PATH} (sam_tracker_log)")
    print(f"Active Cards SSOT: {NIPSTACK_CARDS_FILE}")
    print("Scanning...")
    
    # Run once initially, then keep looping
    poll_and_process()
    
    print("\n[GAME MASTER] Service is running. Monitoring continuously... Press Ctrl+C to stop.")
    while True:
        try:
            poll_and_process()
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n[GAME MASTER] Shutting down.")
            break
        except Exception as e:
            print(f"[GAME MASTER] Loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
