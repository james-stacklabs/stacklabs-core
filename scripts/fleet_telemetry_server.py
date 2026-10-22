import psutil
import subprocess
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stats_cache = {
    "node_73": {"cpu": 0, "ram_used": 0, "ram_total": 0, "ram_percent": 0, "swap_used": 0, "swap_total": 0, "swap_percent": 0, "load": "", "status": "Booting..."},
    "node_74": {"cpu": 0, "ram_used": 0, "ram_total": 0, "ram_percent": 0, "swap_used": 0, "swap_total": 0, "swap_percent": 0, "load": "", "status": "Targeting..."}
}

def monitor_73():
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            try:
                load1, load5, load15 = psutil.getloadavg()
                load_str = f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
            except:
                load_str = "N/A"
            
            stats_cache["node_73"] = {
                "cpu": cpu,
                "ram_used": round(mem.used / (1024**3), 2),
                "ram_total": round(mem.total / (1024**3), 2),
                "ram_percent": mem.percent,
                "swap_used": round(swap.used / (1024**3), 2),
                "swap_total": round(swap.total / (1024**3), 2),
                "swap_percent": swap.percent,
                "load": load_str,
                "status": "Online"
            }
        except Exception as e:
            stats_cache["node_73"]["status"] = f"Error: {str(e)}"
        time.sleep(2)

def monitor_74():
    cmd = [
        "ssh", "-i", "/home/james/.ssh/id_pegasus", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no", "james@192.168.1.74",
        "cat /proc/loadavg; free -m; grep 'cpu ' /proc/stat"
    ]
    
    last_cpu_time = [0, 0] # idle, total
    
    while True:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')
                load = lines[0].split()[:3]
                load_str = ", ".join(load)
                
                mem_line = [l for l in lines if l.startswith('Mem:')][0].split()
                swap_line = [l for l in lines if l.startswith('Swap:')][0].split()
                
                ram_total = int(mem_line[1]) / 1024
                ram_used = int(mem_line[2]) / 1024
                ram_pct = round((ram_used/ram_total) * 100, 1)
                
                swap_total = int(swap_line[1]) / 1024
                swap_used = int(swap_line[2]) / 1024
                swap_pct = round((swap_used/swap_total) * 100, 1) if swap_total > 0 else 0
                
                # CPU heuristic from load
                cpu = min(float(load[0]) * 12.5, 100) # rough proxy
                
                stats_cache["node_74"] = {
                    "cpu": round(cpu, 1),
                    "ram_used": round(ram_used, 2),
                    "ram_total": round(ram_total, 2),
                    "ram_percent": ram_pct,
                    "swap_used": round(swap_used, 2),
                    "swap_total": round(swap_total, 2),
                    "swap_percent": swap_pct,
                    "load": load_str,
                    "status": "Online"
                }
            else:
                stats_cache["node_74"]["status"] = "SSH Offline"
        except Exception as e:
            stats_cache["node_74"]["status"] = "Timeout/Error"
        time.sleep(3)

@app.on_event("startup")
def startup_event():
    t73 = Thread(target=monitor_73, daemon=True)
    t74 = Thread(target=monitor_74, daemon=True)
    t73.start()
    t74.start()

@app.get("/api/stats")
def get_stats():
    return stats_cache

if __name__ == "__main__":
    uvicorn.run("fleet_telemetry_server:app", host="0.0.0.0", port=8091)
