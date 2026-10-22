import time
import os
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PAYLOAD_DIR = "/home/james/stacklabs/dna/agents/FERRIS/payloads"
DROPZONE_DIR = "/home/james/stacklabs/dna/dropzone"

# Routing rules (destination directories based on file name prefixes or exact matches)
ROUTES = {
    "sovereign_ingestor.html": "/home/james/stacklabs/scripts/",
    "fanstack_": "/home/james/stacklabs/08_FanStack/",
    "wardy_": "/home/james/stacklabs/08_FanStack/",
    "uat_": "/home/james/stacklabs/08_FanStack/",
}

class PipelineHandler(FileSystemEventHandler):
    def on_modified(self, event):
        self.process(event)
        
    def on_created(self, event):
        self.process(event)
        
    def process(self, event):
        if event.is_directory:
            return
            
        filepath = event.src_path
        filename = os.path.basename(filepath)
        
        # Skip hidden files or tmp downloads
        if filename.startswith('.') or filename.endswith('~') or '.gdoc' in filename:
            return
            
        # Determine routing
        dest_dir = None
        if filename == "sovereign_ingestor.html":
            dest_dir = ROUTES["sovereign_ingestor.html"]
        else:
            for prefix, ddir in ROUTES.items():
                if prefix == "sovereign_ingestor.html": continue
                if filename.startswith(prefix):
                    dest_dir = ddir
                    break
        
        if dest_dir:
            dest_path = os.path.join(dest_dir, filename)
            try:
                # Add slight delay to ensure file is completely written by Google Drive / Gemini sync
                time.sleep(1)
                shutil.copy2(filepath, dest_path)
                print(f"[PIPELINE SYNC] Routed {filename} -> {dest_path}")
            except Exception as e:
                print(f"[PIPELINE ERROR] Failed to route {filename}: {e}")

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(PAYLOAD_DIR, exist_ok=True)
    os.makedirs(DROPZONE_DIR, exist_ok=True)
    
    observer = Observer()
    handler = PipelineHandler()
    
    observer.schedule(handler, PAYLOAD_DIR, recursive=False)
    observer.schedule(handler, DROPZONE_DIR, recursive=False)
        
    observer.start()
    print(f"[SOVEREIGN PIPELINE] Active.")
    print(f"Watching for Drive sync drops in:\n - {PAYLOAD_DIR}\n - {DROPZONE_DIR}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
