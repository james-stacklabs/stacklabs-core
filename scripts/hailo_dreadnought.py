import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image

# Configurable Dropzone so Pegasus can mount it easily if needed
DROPZONE = os.environ.get("HAILO_DROPZONE", "/home/james/stacklabs/dna/media/hailo_dropzone")
SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp'}
SUPPORTED_VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv'}
MAX_WIDTH = 1920

class DreadnoughtHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        filepath = event.src_path
        self.process_file(filepath)

    def process_file(self, filepath):
        filename, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        # Avoid processing already crushed files
        if "crushed" in filepath: return

        if ext in SUPPORTED_IMAGE_EXTS:
            self.crush_image(filepath, filename, ext)
        elif ext in SUPPORTED_VIDEO_EXTS:
            self.crush_video(filepath, filename, ext)
        elif ext == '.gif':
            # Handle GIF by renaming (same as old logic)
            import shutil
            out_path = f"{filename}_crushed.gif"
            if not os.path.exists(out_path):
                shutil.copy2(filepath, out_path)
                os.remove(filepath)
                print(f"[HAILO-DREADNOUGHT] Preserved {os.path.basename(filepath)} animation -> GIF")

    def crush_image(self, filepath, filename, ext):
        print(f"[HAILO-DREADNOUGHT] Intercepted IMAGE: {os.path.basename(filepath)}")
        time.sleep(2) # Give SMB sync time
        try:
            orig_size = os.path.getsize(filepath)
            with Image.open(filepath) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if img.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                out_path = f"{filename}_crushed.webp"
                img.save(out_path, "WEBP", quality=85)
            
            if os.path.getsize(out_path) > 0:
                os.remove(filepath)
                print(f"  -> SUCCESS (WEBP) | Original: {orig_size/(1024*1024):.2f} MB -> Crushed: {os.path.getsize(out_path)/(1024*1024):.2f} MB")
        except Exception as e:
            print(f"[ERROR] Image Crush failed on {filepath}: {e}")

    def crush_video(self, filepath, filename, ext):
        print(f"[HAILO-DREADNOUGHT] Intercepted VIDEO: {os.path.basename(filepath)}")
        time.sleep(5) # Give video file time to fully transfer over SMB
        out_path = f"{filename}_crushed.mp4"
        try:
            orig_size = os.path.getsize(filepath)
            # FFmpeg call utilizing NVENC HEVC (H.265) for maximum compression on GTX 980
            # Note: GTX 980 supports NVENC HEVC or at least H264. We will use h264_nvenc for max compatibility, 
            # or hevc_nvenc if supported. GTX 980 is Maxwell (GM204), which actually supports NVENC HEVC (v1) in some variants, 
            # but h264_nvenc is 100% guaranteed on GTX 980. We will use h264_nvenc with a moderate CQ to squash bits.
            cmd = [
                "ffmpeg", "-y", "-i", filepath,
                "-c:v", "hevc_nvenc", "-preset", "p7", "-tune", "hq", "-cq", "28",
                "-c:a", "aac", "-b:a", "128k",
                out_path
            ]
            print(f"  -> Hardware Accelerated NVENC Encoding Initialized...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                os.remove(filepath)
                print(f"  -> SUCCESS (NVENC) | Original: {orig_size/(1024*1024):.2f} MB -> Crushed: {os.path.getsize(out_path)/(1024*1024):.2f} MB")
            else:
                print(f"[ERROR] Video Crush failed: FFmpeg exit {result.returncode}")
                # Fallback to H264 NVENC if HEVC fails on GTX 980 Maxwell
                print(f"  -> Retrying with H.264 NVENC fallback...")
                cmd_fallback = [
                    "ffmpeg", "-y", "-i", filepath,
                    "-c:v", "h264_nvenc", "-preset", "p6", "-cq", "30",
                    "-c:a", "aac", "-b:a", "128k",
                    out_path
                ]
                result2 = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result2.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    os.remove(filepath)
                    print(f"  -> SUCCESS (H264 NVENC) | Crushed: {os.path.getsize(out_path)/(1024*1024):.2f} MB")
                else:
                    print(f"[FATAL] H.264 NVENC Fallback failed. Review GPU drivers.")
        except Exception as e:
            print(f"[ERROR] Video processing failed on {filepath}: {e}")

if __name__ == "__main__":
    if not os.path.exists(DROPZONE):
        os.makedirs(DROPZONE, exist_ok=True)
    print(f"=== PEGASUS HAILO DREADNOUGHT ONLINE ===")
    print(f"Watching: {DROPZONE}")
    print(f"GPU Hardware: NVIDIA NVENC Active")
    
    handler = DreadnoughtHandler()
    
    # Process backlog
    print("Sweeping backlog...")
    for f in os.listdir(DROPZONE):
        full_path = os.path.join(DROPZONE, f)
        if os.path.isfile(full_path):
            handler.process_file(full_path)
            
    observer = Observer()
    observer.schedule(handler, DROPZONE, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
