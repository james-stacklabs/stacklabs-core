#!/usr/bin/env python3
import os
import sys
import time
import zipfile
import json
import shutil
import sqlite3
import subprocess
import traceback
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Paths
SOVEREIGN_HOME = "/home/james/stacklabs"
DB_PATH = f"{SOVEREIGN_HOME}/dna/sovereign_now.db"
LOG_PATH = f"{SOVEREIGN_HOME}/logs/sovereign_ingest_d.log"
DROPZONE_DIR = f"{SOVEREIGN_HOME}/dna/dropzone"
PAYLOAD_DIR = f"{SOVEREIGN_HOME}/dna/agents/FERRIS/payloads"
VENV_PYTHON = f"{SOVEREIGN_HOME}/.venv/bin/python3"
INGEST_MEDIA_SCRIPT = f"{SOVEREIGN_HOME}/scripts/ingest_media_assets.py"
PULL_SYNC_SCRIPT = f"{SOVEREIGN_HOME}/scripts/sovereign_pull_sync.sh"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(DROPZONE_DIR, exist_ok=True)
os.makedirs(PAYLOAD_DIR, exist_ok=True)

def log_message(level, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level.upper()}] {message}"
    print(log_line, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}", flush=True)

def get_known_advocates():
    """Fetch known advocate handles from the sqlite database."""
    handles = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_name FROM persona")
        handles = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        log_message("error", f"Failed to fetch advocates from DB: {e}")
    return handles

def parse_metadata_from_name(filename, known_advocates):
    """Fallback parser if manifest.json has no metadata fields."""
    import re
    # Extract ticket: WO-XXXX-XXX or STRYXXXX or INCXXXX or DFCTXXXX
    ticket = None
    ticket_match = re.search(r'(WO-\d{4}-\d+|STRY-\d+|STRY\d+|INC\d+|DFCT\d+)', filename, re.IGNORECASE)
    if ticket_match:
        ticket = ticket_match.group(1).upper()
    
    # Extract advocate handle
    advocate = None
    filename_lower = filename.lower()
    for adv in known_advocates:
        if adv.lower() in filename_lower:
            advocate = adv
            break
            
    # Extract category
    category = "Media Assets"
    if "adventure" in filename_lower:
        category = "Metsy Adventures"
    elif "lookbook" in filename_lower:
        category = "Metsy Lookbook"
        
    return ticket, advocate, category

class AssetIngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        self.handle_event(event)

    def on_modified(self, event):
        # We also handle modified events in case files are copied incrementally
        self.handle_event(event)

    def handle_event(self, event):
        if event.is_directory:
            return
            
        filepath = event.src_path
        filename = os.path.basename(filepath)
        
        # Only process completed zip files
        if not filename.endswith('.zip'):
            return
            
        log_message("info", f"Detected zip file drop: {filename}")
        
        # Wait a few seconds to ensure file is completely written (e.g. size remains constant)
        time.sleep(2)
        try:
            prev_size = -1
            while True:
                curr_size = os.path.getsize(filepath)
                if curr_size == prev_size:
                    break
                prev_size = curr_size
                time.sleep(1)
        except OSError:
            # File might have been deleted or moved rapidly
            return

        # Double check if it's a valid zip
        if not zipfile.is_zipfile(filepath):
            log_message("warning", f"File {filename} is not a valid zip archive. Skipping.")
            return
            
        self.process_zip(filepath)

    def process_zip(self, zip_path):
        filename = os.path.basename(zip_path)
        zip_name_no_ext = os.path.splitext(filename)[0]
        extracted_dir = f"/tmp/{zip_name_no_ext}_extracted"
        
        try:
            # Clean extraction directory if it already exists
            if os.path.exists(extracted_dir):
                shutil.rmtree(extracted_dir)
            os.makedirs(extracted_dir, exist_ok=True)
            
            # Extract zip
            log_message("info", f"Extracting {filename} to {extracted_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_dir)
                
            # Perform metadata validation
            manifest_path = os.path.join(extracted_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                log_message("error", f"Metadata validation failed: manifest.json is missing in {filename}")
                return
                
            try:
                with open(manifest_path, "r") as f:
                    manifest_data = json.load(f)
            except Exception as json_err:
                log_message("error", f"Metadata validation failed: manifest.json in {filename} is not valid JSON: {json_err}")
                return
                
            if "scenarios" not in manifest_data:
                log_message("error", f"Metadata validation failed: manifest.json in {filename} is missing 'scenarios' array")
                return
                
            # Perform file existence checks within the manifest
            scenarios = manifest_data.get("scenarios", [])
            for idx, scenario in enumerate(scenarios):
                for file_key in ["raw_file", "processed_file"]:
                    if file_key in scenario:
                        ref_file = scenario[file_key]
                        ref_path = os.path.join(extracted_dir, ref_file)
                        if not os.path.exists(ref_path):
                            log_message("error", f"Metadata validation failed: scenario {idx} references missing file {ref_file}")
                            return

            log_message("info", f"Metadata validation successful for {filename}")
            
            # Extract execution parameters
            known_advocates = get_known_advocates()
            metadata = manifest_data.get("metadata", {})
            
            ticket = metadata.get("ticket")
            advocate = metadata.get("advocate")
            category = metadata.get("category")
            
            # Fallback to filename parsing
            fn_ticket, fn_advocate, fn_category = parse_metadata_from_name(filename, known_advocates)
            if not ticket:
                ticket = fn_ticket or "UNKNOWN_TICKET"
            if not advocate:
                advocate = fn_advocate or "anonymous"
            if not category:
                category = fn_category or "Media Assets"
                
            log_message("info", f"Execution parameters: Ticket={ticket}, Advocate={advocate}, Category={category}")
            
            # Execute post-ingress hook (ingest_media_assets.py)
            cmd = [
                VENV_PYTHON,
                INGEST_MEDIA_SCRIPT,
                "--dir", extracted_dir,
                "--ticket", ticket,
                "--advocate", advocate,
                "--category", category
            ]
            log_message("info", f"Executing post-ingress hook: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            log_message("info", f"Ingest media assets STDOUT: {res.stdout}")
            if res.returncode != 0:
                log_message("error", f"Ingest media assets failed (exit code {res.returncode}): {res.stderr}")
                return
                
            # Orchestrate rclone/gclone transfers across the Tailscale mesh
            # Check for gclone first, fallback to rclone
            rclone_bin = "gclone" if shutil.which("gclone") else "rclone"
            remote_dest = f"sovereign_os:SovereignOS_Clio_Sync/ingested_packages/{filename}"
            log_message("info", f"Syncing package {filename} to Google Drive using {rclone_bin}...")
            sync_cmd = [rclone_bin, "copyto", zip_path, remote_dest]
            sync_res = subprocess.run(sync_cmd, capture_output=True, text=True)
            if sync_res.returncode == 0:
                log_message("info", f"Successfully backed up package to Google Drive: {remote_dest}")
            else:
                log_message("warning", f"Rclone/Gclone sync failed (exit code {sync_res.returncode}): {sync_res.stderr}")
                
            # Final cleanup
            log_message("info", f"Cleaning up local staging files for {filename}")
            try:
                os.remove(zip_path)
                shutil.rmtree(extracted_dir)
                log_message("info", f"Cleanup successful for {filename}")
            except Exception as cleanup_err:
                log_message("warning", f"Failed to cleanup staging files: {cleanup_err}")
                
        except Exception as e:
            log_message("critical", f"Exception processing zip {filename}: {e}")
            traceback.print_exc()

def periodic_pull_sync_loop():
    """Background loop that periodically runs the Google Drive pull sync script."""
    log_message("info", "Starting periodic pull sync background loop (every 300s)...")
    while True:
        try:
            log_message("info", "Executing periodic pull sync loop...")
            res = subprocess.run(["/bin/bash", PULL_SYNC_SCRIPT], capture_output=True, text=True)
            if res.returncode == 0:
                log_message("info", "Periodic pull sync completed successfully.")
            else:
                log_message("error", f"Periodic pull sync failed (exit code {res.returncode}): {res.stderr}")
        except Exception as ex:
            log_message("error", f"Exception in periodic sync loop: {ex}")
            
        # Sleep for 5 minutes
        time.sleep(300)

def main():
    log_message("info", "=========================================================")
    log_message("info", "Sovereign Ingestion Watcher Daemon armed and initializing...")
    log_message("info", f"Watching Dropzone: {DROPZONE_DIR}")
    log_message("info", f"Watching Payloads: {PAYLOAD_DIR}")
    
    # Start the periodic pull sync loop in a background thread
    sync_thread = threading.Thread(target=periodic_pull_sync_loop, daemon=True)
    sync_thread.start()
    
    # Setup filesystem watcher
    event_handler = AssetIngestHandler()
    observer = Observer()
    observer.schedule(event_handler, DROPZONE_DIR, recursive=False)
    observer.schedule(event_handler, PAYLOAD_DIR, recursive=False)
    
    observer.start()
    log_message("info", "Filesystem watcher active. Listening for zip packages...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_message("info", "Shutdown signal received. Stopping watcher...")
        observer.stop()
    observer.join()
    log_message("info", "Watcher stopped. Daemon offline.")

if __name__ == "__main__":
    main()
