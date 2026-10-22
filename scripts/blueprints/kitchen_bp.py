"""
Unified Multi-Zone Lighting Blueprint for Synapse Bus
Mounted at /kitchen and /lights on Port 8088.
Controls 8 StackLabs Nodes across Kitchen (BLE 5.2), Hallway (WiZ UDP), and Living Room (Govee UDP).
"""

import os
import json
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()

TEMPLATE_PATH = Path("/home/james/stacklabs/templates/kitchen_controller.html")
STATE_PATH = Path("/dev/shm/telemetry/lighting_state.json")

class LightingCommand(BaseModel):
    zone: Optional[str] = Field(default="all", description="Target zone: all, kitchen, hallway, living_room")
    action: str = Field(..., description="Action: on, off, warm_white, night, cyan, amber")
    brightness: int = Field(default=100, ge=1, le=100)
    color: Optional[List[int]] = None
    target: Optional[str] = "all"


@router.get("/kitchen", response_class=HTMLResponse)
@router.get("/kitchen/", response_class=HTMLResponse)
@router.get("/lights", response_class=HTMLResponse)
@router.get("/lights/", response_class=HTMLResponse)
async def get_lighting_ui():
    """Serves the standalone mobile-first Deep Void multi-zone lighting HUD."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=404, detail="Lighting UI template not found")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/api/kitchen/state")
@router.get("/api/lights/state")
async def get_lighting_state():
    """Returns the latest memory-mapped multi-zone lighting telemetry."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return JSONResponse(json.load(f))
        except Exception:
            pass

    return JSONResponse({
        "power": "unknown",
        "active_zone": "all",
        "action": "none",
        "brightness": 100,
        "nodes": {
            "kitchen": {"count": 3, "protocol": "BLE 5.2", "models": ["H6008"]},
            "hallway": {"count": 1, "protocol": "UDP 38899", "ip": "192.168.1.201"},
            "living_room": {"count": 4, "protocol": "UDP 4003", "ips": ["192.168.1.173", ".174", ".176", ".188"]}
        },
        "total_nodes": 8
    })


@router.post("/api/kitchen/command")
@router.post("/api/lights/command")
async def execute_lighting_command(cmd: LightingCommand, background_tasks: BackgroundTasks):
    """Executes asynchronous direct metal dispatch across BLE and UDP sockets."""
    from scripts.unified_lighting_dispatcher import dispatch_zone

    start_time = asyncio.get_event_loop().time()
    target_zone = (cmd.zone or cmd.target or "all").lower()

    # Optimistic telemetry state update
    state_payload = {
        "power": "off" if cmd.action == "off" else "on",
        "active_zone": target_zone,
        "action": cmd.action,
        "brightness": cmd.brightness,
        "updated_at": asyncio.get_event_loop().time()
    }
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state_payload, f)
    except Exception:
        pass

    # Execute dispatch
    result = await dispatch_zone(target_zone, cmd.action, cmd.brightness, cmd.color)
    elapsed_ms = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
    result["elapsed_ms"] = elapsed_ms
    result["active_zone"] = target_zone

    return JSONResponse(result)
