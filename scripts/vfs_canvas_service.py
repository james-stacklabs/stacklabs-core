#!/usr/bin/env python3
"""
VFS Canvas Service: Lightweight, dynamic HTTP daemon serving the declarative
layout schema and raw POSIX folder contents without database queries.
Author: James Carroll (Pilot), Lead Systems Architect.
Target: Clio bare metal.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="StackLabs VFS Canvas Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LAYOUT_FILE = Path("/dev/shm/retina_layout.json")
ALLOWED_BASE = Path("/dev/shm/canvas").resolve()

# Ensure base directory exists on boot
ALLOWED_BASE.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "nominal", "node": "clio", "subsystem": "vfs_canvas"}

@app.get("/api/canvas/layout")
def get_layout():
    if not LAYOUT_FILE.exists():
        raise HTTPException(status_code=404, detail="Layout schema not materialized in /dev/shm")
    try:
        data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
        for p in data.get("pillars", []):
            src = Path(p.get("source_file", ""))
            if src.exists() and src.is_file():
                p["preview_text"] = src.read_text(encoding="utf-8", errors="replace")
            else:
                p["preview_text"] = "No telemetry available"
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/canvas/node")
def get_node(path: str = Query(..., description="Target directory path")):
    target = Path(path).resolve()
    # Strict path traversal security check
    if not target.is_relative_to(ALLOWED_BASE):
        raise HTTPException(status_code=403, detail="Access denied: path traversal boundary violation")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Target node path does not exist")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Target node is not a directory")

    items: List[Dict[str, Any]] = []
    for entry in sorted(target.iterdir()):
        item = {
            "name": entry.name,
            "path": str(entry),
            "is_dir": entry.is_dir(),
            "size_bytes": entry.stat().st_size
        }
        if entry.is_file():
            try:
                item["content"] = entry.read_text(encoding="utf-8", errors="replace")
            except Exception:
                item["content"] = "[Binary or unreadable file]"
        items.append(item)

    return {
        "current_path": str(target),
        "parent_path": str(target.parent) if str(target) != str(ALLOWED_BASE) else None,
        "items": items
    }

if __name__ == "__main__":
    env_port = int(os.getenv("CANVAS_PORT", "8092"))
    uvicorn.run(app, host="127.0.0.1", port=env_port, log_level="info")
