import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

DROPZONE = "/home/james/stacklabs/dna/media/hailo_dropzone"
SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
MAX_WIDTH = 1920

class CrushHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filepath = event.src_path
        filename, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        if ext in SUPPORTED_EXTS:
            print(f"[HAILO-CRUSH] Intercepted new asset: {os.path.basename(filepath)}")
            # Give SMB/Network time to finish writing the file to the Pi
            time.sleep(2)
            
            try:
                # Get original file size
                orig_size = os.path.getsize(filepath)
                
                if ext == '.gif':
                    import shutil
                    out_path = f"{filename}_crushed.gif"
                    shutil.copy2(filepath, out_path)
                    print(f"  -> Animation detected. Bypassed Pillow crushing to preserve frames.")
                else:
                    with Image.open(filepath) as img:
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        if img.width > MAX_WIDTH:
                            ratio = MAX_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                            print(f"  -> Resized from {img.width} width to {MAX_WIDTH} width.")
                            
                        out_path = f"{filename}_crushed.webp"
                        img.save(out_path, "WEBP", quality=85)
                
                new_size = os.path.getsize(out_path)
                
                # Verify crush success before deleting original
                if new_size > 0:
                    os.remove(filepath)
                    print(f"[SUCCESS] Crushed {os.path.basename(filepath)}.")
                    print(f"  -> Original: {orig_size / (1024*1024):.2f} MB")
                    print(f"  -> Crushed : {new_size / (1024*1024):.2f} MB")
                else:
                    print("[ERROR] Crush logic failed. Retaining original.")
                    
            except Exception as e:
                print(f"[ERROR] Failed to process {filepath}: {e}")

if __name__ == "__main__":
    if not os.path.exists(DROPZONE):
        os.makedirs(DROPZONE, exist_ok=True)
        
    print(f"=== HAILO COMPRESSION DAEMON ONLINE ===")
    print(f"Watching: {DROPZONE}")
    print(f"Max Width: {MAX_WIDTH}px | Output: WEBP (Q:85)")
    print(f"Listening for aggressive payloads...")

    event_handler = CrushHandler()
    observer = Observer()
    observer.schedule(event_handler, DROPZONE, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
