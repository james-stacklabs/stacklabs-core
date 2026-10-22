import os
import glob
import urllib.request
import urllib.parse
import json
import base64
import cv2

DROPZONE_DIR = "/home/james/stacklabs/dna/media/hailo_dropzone"

def get_savant_context():
    # Provide a cinematic walk-off context for the batch processing
    return "[TELEMETRY INJECT: 10th Inning Walk-Off Situation, Bases Loaded, Full Count, 99mph Slider]"

def generate_cinematic_description(frame, filename):
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
        telemetry = get_savant_context()
        
        prompt = (
            "You are Vanguard, the elite AI Video Director for the Sovereign FanStack broadcast. "
            "Examine this frame of a baseball broadcast closely. "
            f"Here is the real-time Baseball Savant Telemetry for this play: {telemetry}. "
            "Using ONLY the image and telemetry, write a very brief, intense cinematic description of this frame, predicting the play's action. "
            "Focus on lighting, player tension, and camera moves. Keep it under 3 sentences."
        )
        payload = {
            "model": "llava",
            "prompt": prompt,
            "images": [img_b64],
            "stream": False
        }
        
        print(f"\n[LLaVA] Generative Vision Cortex Online. Ingesting frame for: {filename}")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req, timeout=120)
        result = json.loads(response.read().decode('utf-8'))
        
        desc = result.get("response", "").strip()
        print(f"\n[VANGUARD] --- SCENE DESCRIPTION ({filename}) ---")
        for line in desc.split('\\n'):
            print(f"  > {line}")
        print(f"[VANGUARD] ---------------------------------------")
        return desc
    except Exception as e:
        print(f"[VANGUARD-FAILURE] {e}")
        return None

def process_video(video_path):
    filename = os.path.basename(video_path)
    print(f"\n[CORTEX] Ingesting Walk-Off Capture: {filename}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[CORTEX] ERROR: Stream failed.")
        return

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[CORTEX] Total Frames: {frame_count}")
    
    # Grab the middle frame roughly
    target_frame_idx = frame_count // 2 if frame_count > 0 else 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
    ret, frame = cap.read()
    
    if ret:
        print(f"         > Frame {target_frame_idx} captured as Peak Action Vector")
        generate_cinematic_description(frame, filename)
    else:
        print(f"[CORTEX] Could not extract frame.")
        
    cap.release()

if __name__ == "__main__":
    print("==================================================")
    print(" VANGUARD AIRGAP - 10TH INNING WALK-OFF BATCH ")
    print("==================================================")
    
    mp4_files = sorted(glob.glob(os.path.join(DROPZONE_DIR, "*.mp4")))[-5:] # Just do the latest 5 captures to save time, or do all 16? I will do all. Let's do all.
    mp4_files = sorted(glob.glob(os.path.join(DROPZONE_DIR, "*.mp4")))
    print(f"[DAEMON] Processing {len(mp4_files)} raw captures from dropzone via LLaVA...")
    
    for vf in mp4_files:
        process_video(vf)
        print("--------------------------------------------------")
    
    print("\n[✔] AIRGAP BATCH COMPLETE.")
