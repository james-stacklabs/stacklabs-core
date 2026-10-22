#!/home/james/stacklabs/.venv/bin/python3
import os
import sys
import json
import sqlite3
import datetime
import requests
from urllib.parse import urlparse

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
INBOX_DIR = "/home/james/sovereign_inbox"

def parse_timestamp(ts_val):
    """
    Robust timestamp parser that supports:
    1. Firestore timestamp dicts: {'_seconds': 1234, '_nanoseconds': 0}
    2. Seconds or milliseconds floats/ints
    3. ISO or format string representations
    Returns a string formatted as YYYY-MM-DD HH:MM:SS.
    """
    if not ts_val:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Firestore timestamp format
    if isinstance(ts_val, dict):
        if 'timestampValue' in ts_val:
            return parse_timestamp(ts_val['timestampValue'])
        seconds = ts_val.get('_seconds') or ts_val.get('seconds')
        if seconds is not None:
            return datetime.datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")

    # 2. Number formats
    if isinstance(ts_val, (int, float)):
        # Check if milliseconds (13 digits or more)
        if ts_val > 10000000000:
            ts_val /= 1000.0
        return datetime.datetime.fromtimestamp(ts_val).strftime("%Y-%m-%d %H:%M:%S")

    # 3. String formats
    if isinstance(ts_val, str):
        # Clean potential ISO T/Z characters
        ts_val_clean = ts_val.replace('T', ' ').replace('Z', '')
        # Try parsing standard formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
        ):
            try:
                dt = datetime.datetime.strptime(ts_val_clean.split('+')[0].strip(), fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

    # Fallback to now if unparseable
    try:
        dt = datetime.datetime.fromisoformat(str(ts_val))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def download_asset(photo_url, event_id):
    """
    Downloads historical image/video from Firebase and saves it to sovereign_inbox.
    Returns the local path or None if failed.
    """
    if not photo_url or not isinstance(photo_url, str) or not photo_url.startswith("http"):
        return None

    try:
        parsed_url = urlparse(photo_url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1]
        if not ext:
            # Try guessing extension or default to .jpg
            ext = ".jpg"
            if ".mp4" in photo_url.lower():
                ext = ".mp4"

        # Sanitize extension
        if '?' in ext:
            ext = ext.split('?')[0]

        filename = f"firebase_{event_id}{ext}"
        local_path = os.path.join(INBOX_DIR, filename)

        print(f"Downloading asset: {photo_url} -> {local_path} ...")
        resp = requests.get(photo_url, timeout=15)
        if resp.status_code == 200:
            os.makedirs(INBOX_DIR, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(resp.content)
            print(f"Successfully saved asset locally as: {filename}")
            return f"/inbox/{filename}"
        else:
            print(f"Failed download with status code: {resp.status_code}")
    except Exception as e:
        print(f"Error downloading asset: {e}")

    return None

def import_json(filepath):
    print(f"Opening Firebase export JSON file at: {filepath}")
    with open(filepath, 'r') as f:
        data = json.load(f)

    events_to_process = []
    config_updates = {}

    # Identify the structure of the JSON
    if isinstance(data, list):
        print(f"Detected JSON array containing {len(data)} items.")
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                events_to_process.append((f"idx_{idx}", item))
    elif isinstance(data, dict):
        # Check if nested events/logs
        if "events" in data:
            events_node = data["events"]
            if isinstance(events_node, list):
                for idx, item in enumerate(events_node):
                    events_to_process.append((f"evt_{idx}", item))
            elif isinstance(events_node, dict):
                for key, item in events_node.items():
                    events_to_process.append((key, item))
        
        # Check if config is in top-level or separate node
        for cfg_key in ["status", "status_text", "note_text", "note_title", "daily_naps", "adventures", "tuna_snacks", "picture_url"]:
            if cfg_key in data:
                config_updates[cfg_key] = data[cfg_key]

        # If it wasn't explicitly nested under 'events', maybe the entire dictionary is key->event map
        if not events_to_process:
            # Check if values look like event dicts
            is_event_map = False
            for k, v in data.items():
                if isinstance(v, dict) and any(x in v for x in ["message", "type", "timestamp", "photoUrl"]):
                    is_event_map = True
                    events_to_process.append((k, v))
            
            if not is_event_map and not config_updates:
                # Fallback: treat the entire dict as a single event/sighting or config
                events_to_process.append(("single", data))

    print(f"Identified {len(events_to_process)} event entries to process.")
    print(f"Identified configuration values: {config_updates}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Idempotent DB schemas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sam_tracker_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sam_tracker_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        note_title TEXT,
        note_text TEXT,
        status_text TEXT,
        daily_naps TEXT,
        adventures TEXT,
        tuna_snacks TEXT,
        picture_url TEXT
    )
    """)
    cur.execute("INSERT OR IGNORE INTO sam_tracker_config (id, note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url) VALUES (1, 'Note for Jeannine', '', 'Feline Great!', '0', '0', '0', 'sam.jpg')")

    inserted_count = 0
    skipped_count = 0

    # Process events
    for key, event in events_to_process:
        if not isinstance(event, dict):
            continue

        # Extract fields from Cloud Firestore REST format if present
        if "fields" in event:
            fields = event["fields"]
            msg_field = fields.get("message", {})
            raw_msg = msg_field.get("stringValue") or "Saw Sam"
            
            type_field = fields.get("type", {})
            raw_type = type_field.get("stringValue") or "SIGHTING"
            
            ts_field = fields.get("timestamp", {})
            raw_ts = ts_field.get("timestampValue") or ts_field.get("stringValue")
            
            photo_field = fields.get("photoUrl", {})
            photo_url = photo_field.get("stringValue")
            
            media_field = fields.get("mediaType", {})
            media_type = media_field.get("stringValue") or "image"
        else:
            raw_msg = event.get('message') or event.get('note') or event.get('text') or event.get('desc') or "Saw Sam"
            raw_type = event.get('type') or event.get('category') or event.get('event_type') or "SIGHTING"
            raw_ts = event.get('timestamp') or event.get('time') or event.get('date') or event.get('created_at')
            photo_url = event.get('photoUrl') or event.get('photo_url') or event.get('imageUrl') or event.get('image_url')
            media_type = event.get('mediaType') or event.get('media_type') or "image"

        raw_type = raw_type.upper()
        timestamp = parse_timestamp(raw_ts)

        # Check if local asset download is requested/possible
        local_path = None
        if photo_url:
            local_path = download_asset(photo_url, key)

        # Build message with embedded asset metadata matching backend spec
        message = raw_msg
        asset_path = local_path or photo_url
        if asset_path:
            if media_type == 'video' or '.mp4' in asset_path.lower() or '.mov' in asset_path.lower():
                message += f" ||| VID:{asset_path}"
            else:
                message += f" ||| IMG:{asset_path}"

        # Idempotency check: prevent duplicate inserts of identical events
        cur.execute("SELECT 1 FROM sam_tracker_log WHERE timestamp = ? AND message = ?", (timestamp, message))
        if cur.fetchone():
            skipped_count += 1
            continue

        cur.execute("INSERT INTO sam_tracker_log (timestamp, type, message) VALUES (?, ?, ?)", (timestamp, raw_type, message))
        inserted_count += 1

    # Update config if present
    if config_updates:
        # Normalize status -> status_text
        if "status" in config_updates and "status_text" not in config_updates:
            config_updates["status_text"] = config_updates.pop("status")

        # Get existing config values
        cur.execute("SELECT note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url FROM sam_tracker_config WHERE id=1")
        existing_cfg = cur.fetchone()
        if existing_cfg:
            note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url = existing_cfg
        else:
            note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url = ("Note for Jeannine", "", "Feline Great!", "0", "0", "0", "sam.jpg")

        note_title = config_updates.get("note_title", note_title)
        note_text = config_updates.get("note_text", note_text)
        status_text = config_updates.get("status_text", status_text)
        daily_naps = str(config_updates.get("daily_naps", daily_naps))
        adventures = str(config_updates.get("adventures", adventures))
        tuna_snacks = str(config_updates.get("tuna_snacks", tuna_snacks))
        picture_url = config_updates.get("picture_url", picture_url)

        cur.execute("""
            UPDATE sam_tracker_config 
            SET note_title=?, note_text=?, status_text=?, daily_naps=?, adventures=?, tuna_snacks=?, picture_url=?
            WHERE id=1
        """, (note_title, note_text, status_text, daily_naps, adventures, tuna_snacks, picture_url))
        print("Updated sam_tracker_config with historical config data.")

    conn.commit()
    conn.close()

    print("\n--- MIGRATION RUN COMPLETE ---")
    print(f"Total entries loaded: {len(events_to_process)}")
    print(f"New entries inserted: {inserted_count}")
    print(f"Duplicates skipped:   {skipped_count}")
    print("------------------------------")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 import_firebase_tracker.py <path_to_firebase_export.json>")
        sys.exit(1)

    import_json(sys.argv[1])
