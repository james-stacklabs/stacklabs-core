from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import psutil
import time
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = "/home/james/stacklabs/scripts/nuke_74.log"

async def tail_log(file_path):
    if not os.path.exists(file_path):
        yield "Awaiting nuke_74.log creation...\n"
        while not os.path.exists(file_path):
            await asyncio.sleep(1)
            
    with open(file_path, "r") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            yield line

def get_system_stats():
    # Attempt to get Pi temperature
    temp = 0.0
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000.0
    except Exception:
        pass

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "temperature": temp
    }

@app.websocket("/ws/nuke_monitor")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    log_generator = tail_log(LOG_FILE)
    
    try:
        while True:
            # Check for new logs
            try:
                line = await asyncio.wait_for(anext(log_generator), timeout=0.01)
                await websocket.send_json({"type": "log", "data": line.strip()})
            except asyncio.TimeoutError:
                pass
            
            # Send system stats every 1 second
            if int(time.time() * 10) % 10 == 0:
                stats = get_system_stats()
                await websocket.send_json({"type": "stats", "data": stats})
                
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        print("Client disconnected")

@app.post("/nuke")
async def trigger_nuke():
    # Trigger the nuke_74.py script in the background
    os.system("python3 /home/james/stacklabs/scripts/nuke_74.py > /home/james/stacklabs/scripts/nuke_74.log 2>&1 &")
    return {"status": "Bombardment Initiated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
