import cv2
import time
import os
import json
import asyncio
import websockets
from PIL import Image

# Load API Key
api_key = None
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY"):
                api_key = line.strip().split("=", 1)[1].strip()

from google import genai
client = genai.Client(api_key=api_key)

class ArgusOpticalSync:
    def __init__(self):
        self.cap = cv2.VideoCapture(0) # Microdia 1080P HD
        # Try to set resolution lower for faster processing
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.mesh_ws_url = "ws://localhost:8008"
        self.latest_api_pitch_count = None
        self.api_timestamp_map = {} # pitch_count -> timestamp received
        self.rolling_deltas = []
        self.active_latency_sec = 0
        
    async def capture_and_analyze(self):
        print("[ARGUS] Activating Optical Sensor on /dev/video0...")
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[ARGUS] Error: Failed to grab frame.")
                await asyncio.sleep(5)
                continue
                
            # Compress and encode to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            with open("/tmp/argus_frame.jpg", "wb") as f:
                f.write(buffer)
                
            img = Image.open("/tmp/argus_frame.jpg")
            
            try:
                # Ask Gemini purely for the Pitch Count integer to compute Delta
                prompt = "Look at this TV broadcast of a baseball game. Locate the scorebug graphics (usually bottom right or top left). Extract ONLY the total Pitch Count for the current pitcher. Return ONLY the integer number. If not visible, return 'None'."
                
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[prompt, img]
                )
                text = response.text.strip()
                
                if text.isdigit():
                    tv_pitch_count = int(text)
                    print(f"[ARGUS] Detected TV Pitch Count: {tv_pitch_count}")
                    
                    # Compute Latency Delta if we have a matching API log
                    if tv_pitch_count in self.api_timestamp_map:
                        api_time = self.api_timestamp_map[tv_pitch_count]
                        current_time = time.time()
                        delta = current_time - api_time
                        
                        if delta > 5 and delta < 300: # Sanity bounds (5s to 5 mins lag)
                            self.rolling_deltas.append(delta)
                            if len(self.rolling_deltas) > 3:
                                self.rolling_deltas.pop(0)
                                
                            avg_delta = sum(self.rolling_deltas) / len(self.rolling_deltas)
                            print(f"[PLIE ENGINE] Calculated Piracy Delta: {'%.2f' % delta}s | Rolling Average: {'%.2f' % avg_delta}s")
                            
                            # Update the Mesh Relay with the new Temporal Offset
                            if abs(avg_delta - self.active_latency_sec) > 3: # Only update if drifting more than 3s
                                self.active_latency_sec = avg_delta
                                await self.broadcast_latency_to_mesh(avg_delta)
                else:
                    print(f"[ARGUS] Frame scan unclear: {text}")
                    
            except Exception as e:
                 print(f"[ARGUS] Vision API Error: {e}")
                 
            await asyncio.sleep(5) # Scan every 5 seconds to preserve quota

    async def broadcast_latency_to_mesh(self, latency_sec):
        try:
            async with websockets.connect(self.mesh_ws_url) as ws:
                payload = {
                    "type": "CMD_SET_LATENCY",
                    "latency_sec": latency_sec
                }
                await ws.send(json.dumps(payload))
                print(f"[PLIE ENGINE] Deployed -{latency_sec:.2f}s Latency Buffer to Sovereign FanMesh.")
        except Exception as e:
            print(f"[ARGUS] Failed to connect to Mesh: {e}")

    async def mesh_listener(self):
        while True:
            try:
                async with websockets.connect(self.mesh_ws_url) as ws:
                    print("[ARGUS] Subscribed to Mesh Telemetry for Ground Truth Sync.")
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("type") == "STATE_UPDATE":
                            api_pitch_count = data.get("data", {}).get("pitchCount")
                            if api_pitch_count and api_pitch_count != "-" and str(api_pitch_count).isdigit():
                                current_pc = int(api_pitch_count)
                                if current_pc != self.latest_api_pitch_count:
                                    self.api_timestamp_map[current_pc] = time.time()
                                    self.latest_api_pitch_count = current_pc
                                    print(f"[GROUND TRUTH] MLB API reports Pitch Count: {current_pc}")
            except Exception as e:
                print(f"[ARGUS] Mesh Listener Error: {e}")
                await asyncio.sleep(3)

    async def run(self):
        task1 = asyncio.create_task(self.capture_and_analyze())
        task2 = asyncio.create_task(self.mesh_listener())
        await asyncio.gather(task1, task2)

if __name__ == "__main__":
    argus = ArgusOpticalSync()
    asyncio.run(argus.run())
