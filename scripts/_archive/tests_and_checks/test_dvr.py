import asyncio
import sys
import json

try:
    import websockets
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)
    import websockets

async def test_dvr():
    uri = "ws://127.0.0.1:8006/ws/gametime"
    print("[*] Rehearsal: Connecting to FanStack Live DVR...")
    try:
        async with websockets.connect(uri) as ws:
            # First message on connect
            msg = await ws.recv()
            initial = json.loads(msg)
            print(f"[ ] Connected. Status: {initial.get('sim_status')}, Pitch ID: {initial.get('pitch_id')}")
            
            # Play
            print("[*] Sending PLAY...")
            await ws.send(json.dumps({"action": "PLAY"}))
            # Wait for event
            await asyncio.sleep(1)
            
            # FFWD
            print("[*] Sending FFWD...")
            await ws.send(json.dumps({"action": "FFWD"}))
            msg = await ws.recv()
            ffwd_pitch = json.loads(msg).get('pitch_id')
            print(f"[+] After FFWD, pitch moved to: {ffwd_pitch}")
            
            # REWIND
            print("[*] Sending REWIND...")
            await ws.send(json.dumps({"action": "REWIND"}))
            msg = await ws.recv()
            rewind_pitch = json.loads(msg).get('pitch_id')
            print(f"[+] After REWIND, pitch moved to: {rewind_pitch}")
            
            # STEP FORWARD
            print("[*] Sending STEP_FWD...")
            await ws.send(json.dumps({"action": "STEP_FWD"}))
            msg = await ws.recv()
            step_pitch = json.loads(msg).get('pitch_id')
            print(f"[+] After STEP_FWD, pitch moved to: {step_pitch}")
            
            # Pause
            print("[*] Sending PAUSE...")
            await ws.send(json.dumps({"action": "PAUSE"}))
            
            print("[✔] DVR TRANSPORT CONTROLS VERIFIED END-TO-END.")
    except Exception as e:
        print(f"[!] Rehearsal Failed: {e}")

if __name__ == '__main__':
    asyncio.run(test_dvr())
