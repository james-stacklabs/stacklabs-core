import os
import time
import requests
import base64
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DROPZONE = os.environ.get("HAILO_DROPZONE", "/home/james/stacklabs/dna/media/hailo_dropzone")
OLLAMA_URL = "http://clio.taila01894.ts.net:11434/api/generate"
VISION_MODEL = "llava"

class VisionHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        filepath = event.src_path
        self.process_file(filepath)

    def process_file(self, filepath):
        filename, ext = os.path.splitext(filepath)
        ext = ext.lower()
        if "crushed" in filepath and ext in ['.webp', '.jpg', '.png']:
            print(f"[HAILO-VISION] Acquired asset: {os.path.basename(filepath)}")
            time.sleep(2)
            self.caption_image(filepath)

    def caption_image(self, filepath):
        try:
            with open(filepath, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode('utf-8')
            
            payload = {
                "model": VISION_MODEL,
                "prompt": "Analyze this image and write a concise, one-sentence description of what's happening. Keep it extremely brief.",
                "images": [b64_img],
                "stream": False
            }
            
            print(f"  -> Offloading inference to LLaVA via Ollama...")
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            
            if response.status_code == 200:
                caption = response.json().get("response", "").strip()
                print(f"  -> SUCCESS! Caption: {caption}")
                
                desc_path = os.path.join(os.path.dirname(filepath), "image_desc.txt")
                img_name = os.path.basename(filepath)
                
                with open(desc_path, "a") as f:
                    f.write(f"[{img_name}]: {caption}\n")
            else:
                print(f"[ERROR] Ollama Vision failed: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Vision processing failed on {filepath}: {e}")

if __name__ == "__main__":
    if not os.path.exists(DROPZONE):
        os.makedirs(DROPZONE, exist_ok=True)
    print(f"=== PEGASUS MULTI-MODAL VISION WING ===")
    print(f"Watching: {DROPZONE}")
    print(f"LLM Engine: Local Ollama ({VISION_MODEL})")
    
    handler = VisionHandler()
    observer = Observer()
    observer.schedule(handler, DROPZONE, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
