import asyncio
import websockets
import json
import random

async def telemetry_stream(websocket, path):
    print("AI Hat Vision Daemon: Connection established.")
    
    events = [
        "VISUAL ANOMALY: Motor function lag detected. Speech slurred.",
        "COGNITIVE MAPPING: Delayed blink rate. Potential synaptic misfire.",
        "ACOUSTIC DECAY: Syllable compression. Breathing erratic.",
        "PHYSICAL FLUB: Micro-tremor detected in left hand.",
        "LINGUISTIC COLLAPSE: Sudden pivot in sentence structure without logical bridge.",
        "EYE TRACKING: Saccadic movement irregular. Glazing effect.",
        "POSTURE ALERT: Sloping shoulder mechanics.",
        "MICRO-EXPRESSION: Involuntary grimace. Neurological tension."
    ]

    base_s = 5.0
    while True:
        await asyncio.sleep(random.uniform(1.0, 3.5))
        event = random.choice(events)
        confidence = random.randint(75, 99)
        base_s += random.uniform(-0.5, 1.5)
        
        # Reset to keep bouncing around 5
        if base_s > 9.5: base_s = random.uniform(4.0, 7.0)
        if base_s < 1.0: base_s = random.uniform(2.0, 4.0)
        
        payload = {
            "type": "VLM_INFERENCE",
            "telemetry": f"[{event} Confidence: {confidence}%]",
            "sundown_coefficient": round(base_s, 2)
        }
        try:
            await websocket.send(json.dumps(payload))
        except:
            break

async def main():
    print("AI Hat Vision Daemon LIVE on ws://localhost:3004")
    async with websockets.serve(telemetry_stream, "localhost", 3004):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
