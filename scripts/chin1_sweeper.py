import os
import time
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

DEAD_DROP_DIR = "/home/james/stacklabs/staging/dead_drop/"
HAILO_DROPZONE_DIR = "/home/james/stacklabs/dna/media/hailo_dropzone/"
QUARANTINE_DIR = "/home/james/stacklabs/staging/quarantine/"

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
MEDIA_EXTENSIONS = {'.mp4', '.gif', '.webm'}

def process_file(file_path):
    # Wait slightly to ensure the file is completely written by SMB transfer
    time.sleep(1)
    
    path = Path(file_path)
    if not path.exists():
        return
        
    ext = path.suffix.lower()
    
    try:
        if ext in IMAGE_EXTENSIONS:
            # Crush to 1920 WEBP
            img = Image.open(path)
            
            # Convert to RGB if necessary for WEBP
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # Resize logic (max 1920px width/height)
            img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            
            # Save compressed webp version
            fast_name = path.stem + ".webp"
            target_path = os.path.join(HAILO_DROPZONE_DIR, fast_name)
            img.save(target_path, "WEBP", quality=85)
            
            # Remove original from dead drop
            os.remove(path)
            print(f"[CHIN-1] Processed Image: {path.name} -> {target_path}")

        elif ext in MEDIA_EXTENSIONS:
            # Move raw media directly
            target_path = os.path.join(HAILO_DROPZONE_DIR, path.name)
            shutil.move(path, target_path)
            print(f"[CHIN-1] Moved Media: {path.name} -> {target_path}")

        else:
            # Unrecognized/Archive file. Move to quarantine
            target_path = os.path.join(QUARANTINE_DIR, path.name)
            shutil.move(path, target_path)
            print(f"[CHIN-1] QUARANTINED: Unrecognized asset -> {path.name}")
            
    except Exception as e:
        print(f"[CHIN-1] ERROR processing {path.name}: {e}")

class SweeperHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print(f"[CHIN-1] Ingestion detected: {event.src_path}")
            process_file(event.src_path)

if __name__ == "__main__":
    os.makedirs(DEAD_DROP_DIR, exist_ok=True)
    os.makedirs(HAILO_DROPZONE_DIR, exist_ok=True)
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    
    # Process existing files first in case of dirty restart
    print("[CHIN-1] Sweeping existing backlogs...")
    for f in os.listdir(DEAD_DROP_DIR):
        file_path = os.path.join(DEAD_DROP_DIR, f)
        if os.path.isfile(file_path):
            process_file(file_path)

    print(f"[CHIN-1] Daemon active. Locked onto {DEAD_DROP_DIR}")
    
    event_handler = SweeperHandler()
    observer = Observer()
    observer.schedule(event_handler, DEAD_DROP_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("[CHIN-1] Shutdown signaled.")
    
    observer.join()
