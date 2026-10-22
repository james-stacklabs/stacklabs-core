import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import subprocess
import os
import uvicorn

app = FastAPI(title="Sovereign Mission Control")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/08_FanStack", StaticFiles(directory="/home/james/stacklabs/08_FanStack", html=True), name="static_fancast")

SERVICES = {
    "fanstack_relay": {
        "path": "/home/james/stacklabs/08_FanStack/fanstack_relay.py",
        "category": "MLB Stack"
    },
    "fanstack_chatbots": {
        "path": "/home/james/stacklabs/scripts/fanstack_chatbots.py",
        "category": "MLB Stack"
    },
    "statcast_sentinel": {
        "path": "/home/james/stacklabs/scripts/statcast_sentinel.py",
        "category": "MLB Stack"
    },
    "dynamic_argus": {
        "path": "/home/james/stacklabs/scripts/dynamic_argus_fix.py",
        "category": "MLB Stack"
    },
    "masters_server": {
        "path": "/home/james/stacklabs/scripts/masters_server.py",
        "category": "PGA Masters Stack"
    },
    "masters_relay": {
        "path": "/home/james/stacklabs/scripts/masters_relay.py",
        "category": "PGA Masters Stack"
    },
    "masters_chatbots": {
        "path": "/home/james/stacklabs/scripts/masters_chatbots.py",
        "category": "PGA Masters Stack"
    },
    "cmdb_server": {
        "path": "/home/james/stacklabs/scripts/cmdb_server.py",
        "category": "Core Ops"
    },
    "sdlc_server": {
        "path": "/home/james/stacklabs/scripts/sdlc_portal_server.py",
        "category": "Core Ops"
    },
    "hailo_dashboard": {
        "path": "/home/james/stacklabs/scripts/hailo_dashboard.py",
        "category": "Core Ops"
    },
    "persona_foundry": {
        "path": "/home/james/stacklabs/scripts/persona_manager_server.py",
        "category": "Persona Core"
    }
}

def get_pid(script_name: str):
    try:
        # Looking for python.*script_name
        output = subprocess.check_output(["pgrep", "-f", script_name]).decode('utf-8').strip().split('\n')
        # Filter out current process just in case
        pids = [p for p in output if p and int(p) != os.getpid()]
        return pids[0] if pids else None
    except subprocess.CalledProcessError:
        return None

@app.get("/", response_class=HTMLResponse)
async def get_portal():
    with open("/home/james/stacklabs/portal.html", "r") as f:
        return f.read()

@app.get("/api/services")
async def list_services():
    state = []
    for s_id, s_info in SERVICES.items():
        script_file = os.path.basename(s_info["path"])
        pid = get_pid(script_file)
        
        state.append({
            "id": s_id,
            "name": script_file,
            "category": s_info["category"],
            "status": "Online" if pid else "Offline",
            "pid": pid
        })
    return {"services": state}

@app.post("/api/services/{service_id}/start")
async def start_service(service_id: str):
    if service_id not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
        
    s_info = SERVICES[service_id]
    script_file = os.path.basename(s_info["path"])
    
    # Check if already running
    if get_pid(script_file):
        return {"status": "success", "message": f"{service_id} is already running."}
        
    log_path = f"/tmp/{service_id}.log"
    # Execute detached
    with open(log_path, 'w') as log:
        subprocess.Popen(
            ["python3", "-u", s_info["path"]],
            stdout=log,
            stderr=log,
            start_new_session=True # Detach from parent
        )
        
    return {"status": "success", "message": f"{service_id} started."}

@app.post("/api/services/{service_id}/stop")
async def stop_service(service_id: str):
    if service_id not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    
    s_info = SERVICES[service_id]
    script_file = os.path.basename(s_info["path"])
    
    # Use pkill to kill strictly this script
    try:
        subprocess.run(["pkill", "-f", script_file], check=False)
        return {"status": "success", "message": f"{service_id} stopped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Sovereign Mission Control initializing on Port 420...")
    # NOTE: Run as root/sudo if binding to <1024 errors out on this Host.
    uvicorn.run(app, host="0.0.0.0", port=420)
