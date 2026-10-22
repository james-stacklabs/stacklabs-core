from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import uvicorn
from contextlib import contextmanager

app = FastAPI(title="Sovereign Console Backend", version="1.1")
app.mount("/ui", StaticFiles(directory="/home/james/stacklabs/scripts"), name="ui")

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

from typing import Dict, Any, Optional

# Models
class TicketUpdate(BaseModel):
    status: str = None
    priority: str = None
    cab_approval: str = None
    assigned_ci: str = None


# --- TICKETS ENDPOINTS ---
@app.get("/api/tickets")
def get_tickets():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

@app.put("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build update query dynamically
        updates = []
        params = []
        for key, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{key} = ?")
                params.append(value)
        
        if not updates:
            return {"status": "no shifts"}
            
        params.append(ticket_id)
        query = f"UPDATE tickets SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        return {"status": "success", "ticket_id": ticket_id}

# --- CI REGISTRY ENDPOINTS ---
@app.get("/api/ci")
def get_cis():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ci_registry ORDER BY zone DESC, ci_id ASC")
        return [dict(row) for row in cursor.fetchall()]

import subprocess
import json

import os

from fastapi import File, UploadFile, Form
import shutil

@app.post("/api/upload")
async def handle_upload(file: UploadFile = File(...), target_path: str = Form(...)):
    try:
        os.makedirs(target_path, exist_ok=True)
        file_location = os.path.join(target_path, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        return {"status": "SUCCESS", "message": f"Saved {file.filename} to {target_path}"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

# --- INGESTION ENDPOINT ---
@app.post("/api/ingest")
def universal_ingestor(payload: dict):
    meta = payload.get("meta", {})
    target = meta.get("target_path", "")
    operation = meta.get("operation", "WRITE")
    data = payload.get("data", {})

    # File append for .md files
    if operation == "APPEND" and target.endswith(".md"):
        entries = data.get("entries", [])
        try:
            with open(target, "a") as f:
                f.write("\n")
                for entry in entries:
                    f.write(entry + "\n")
            return {"status": "SUCCESS", "message": f"appended {len(entries)} lines"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    if target.endswith(".db"):
        with get_db() as conn:
            cursor = conn.cursor()
            if operation == "INSERT":
                import uuid
                if "sys_id" not in data:
                    data["sys_id"] = uuid.uuid4().hex
                
                table_name = data.pop("sys_class_name", "rm_story")
                keys = ", ".join(data.keys())
                placeholders = ", ".join(["?"] * len(data))
                query = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})"
                
                try:
                    cursor.execute(query, list(data.values()))
                    conn.commit()
                    return {"status": "SUCCESS", "message": f"{table_name} inserted successfully", "ticket_id": data.get("number", data.get("id"))}
                except Exception as e:
                    return {"status": "ERROR", "message": str(e)}
            
            elif operation == "UPDATE":
                if "sys_id" not in data and "id" not in data:
                    return {"status": "ERROR", "message": "Missing 'sys_id' or 'id' for UPDATE operation"}
                update_data = dict(data)
                
                record_id = update_data.pop("sys_id", update_data.pop("id", None))
                table_name = update_data.pop("sys_class_name", "rm_story")
                
                updates = [f"{key} = ?" for key in update_data.keys()]
                query = f"UPDATE {table_name} SET {', '.join(updates)} WHERE sys_id = ?"
                try:
                    params = list(update_data.values()) + [record_id]
                    cursor.execute(query, params)
                    conn.commit()
                    return {"status": "SUCCESS", "message": f"{table_name} {record_id} updated successfully"}
                except Exception as e:
                    return {"status": "ERROR", "message": str(e)}
            else:
                return {"status": "ERROR", "message": f"Unsupported DB operation {operation}"}

    else:
        try:
            mode = 'a' if operation == "APPEND" else 'w'
            content = data.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
                
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, mode) as f:
                if mode == 'a':
                    f.write("\n" + str(content))
                else:
                    f.write(str(content))
            return {"status": "SUCCESS", "message": f"File {operation} successful to {target}"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    return {"status": "ERROR", "message": "Unknown ingest type or malformed path"}

@app.get("/api/ci_roster")
def get_ci_roster():
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, short_description FROM cmdb_ci WHERE sys_class_name='cmdb_ci_ai_persona'")
        rows = cursor.fetchall()
        
        # Also grab the core Sovereign fleet if they exist under a different class, or just return them statically
        core_agents = [
            {"ci_name": "ANTIGRAVITY", "ci_role": "Core CI/CD"},
            {"ci_name": "FERRIS", "ci_role": "UI Web Builder"},
            {"ci_name": "WARDY", "ci_role": "Studio Host"}
        ]
        
        personas = [{"ci_name": row[0], "ci_role": row[1] if row[1] else "Persona"} for row in rows]
        conn.close()
        return {"agents": core_agents + personas}
    except Exception as e:
        return {"agents": [], "error": str(e)}


# --- PEGASUS TELEMETRY ENDPOINT ---
@app.get("/api/pegasus/telemetry")
def pegasus_telemetry():
    try:
        # We chain bash commands via SSH to minimize connection overhead
        ssh_cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", 
            "-i", "/home/james/.ssh/id_pegasus", "james@192.168.1.74",
            "uptime | sed 's/.*load average://'; " +
            "free -m | awk '/Mem:/ {print $3\"/\"$2\"MB\"}'; " +
            "df -h / | awk 'NR==2 {print $5}'; " +
            "DISPLAY=:0 nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total --format=csv,noheader || echo 'N/A,N/A,N/A'; " +
            "systemctl is-active ollama || echo 'inactive'; " +
            "ollama list | wc -l || echo '0'; " +
            "sudo ufw status | grep Status || echo 'Status: inactive'"
        ]
        
        result = subprocess.check_output(ssh_cmd, stderr=subprocess.STDOUT, timeout=10).decode('utf-8').strip().split('\n')
        
        # Parse the sequential output
        telemetry = {
            "load_average": result[0].strip() if len(result) > 0 else "N/A",
            "ram_usage": result[1].strip() if len(result) > 1 else "N/A",
            "disk_usage": result[2].strip() if len(result) > 2 else "N/A",
            "gpu_stats": result[3].strip() if len(result) > 3 else "N/A",
            "ollama_status": result[4].strip() if len(result) > 4 else "N/A",
            "ollama_models": str(int(result[5].strip()) - 1) if len(result) > 5 and result[5].strip().isdigit() else "0",
            "firewall": result[6].strip() if len(result) > 6 else "N/A"
        }
        
        return {"status": "SUCCESS", "data": telemetry}
    
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "data": "SSH Connection Timed Out"}
    except Exception as e:
        return {"status": "ERROR", "data": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
