"""
StackLabs Retina Schema Engine & Intent-to-Schema Compiler
Path: /home/james/stacklabs/scripts/blueprints/retina_schema_engine.py
Manages registered data cartridges, atomic profile schemas, and WebSocket broadcasts.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/retina/schema", tags=["retina_schema"])

SCHEMA_DIR = Path("/home/james/stacklabs/data/retina_profiles")
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

class CartridgeSlot(BaseModel):
    slot: int = Field(..., ge=1, le=4)
    cartridge: str
    title: str
    badge: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None

class DeckManifest(BaseModel):
    deck_id: str
    title: str
    mode: str
    slots: List[CartridgeSlot]

class ProfileManifest(BaseModel):
    profile_id: str
    display_name: str
    version: str = "2.5.0"
    active_deck: str
    decks: Dict[str, DeckManifest]

# Active WebSockets connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Registered Cartridge Catalog
CARTRIDGE_CATALOG: Dict[str, Dict[str, Any]] = {
    "santa_anita_pace": {
        "title": "SANTA ANITA // TURF PACE",
        "category": "turf",
        "telemetry": {
            "track": "Santa Anita Park",
            "surface": "Turf / Firm",
            "rail": "Zero Rail (+0 ft)",
            "speed_bias": "Early Speed +1.8σ",
            "mud_factor": "Dry / Fast"
        }
    },
    "burst_momentum_10d": {
        "title": "10-STOCK // 10-DAY BURST",
        "category": "equity_burst",
        "telemetry": {
            "bracket": "2:1 Asymmetric (+5.0% TP / -2.5% SL)",
            "soak_status": "Paper Metal Soak Day 14/30",
            "win_rate_required": "33.4%",
            "active_positions": 10
        }
    },
    "consensus_arbiter_dual": {
        "title": "CONSEN-SYS // ARBITER",
        "category": "ai_consensus",
        "telemetry": {
            "models": "Claude 3.5 Sonnet & GPT-4o",
            "veto_rule": "2/2 Unanimous Required",
            "search_latency_ms": 0.0,
            "ground_truth_source": "Local NVMe Pagecache"
        }
    },
    "options_wire_collar": {
        "title": "MARA // 2:1 COLLAR",
        "category": "derivatives",
        "telemetry": {
            "strike_spread": "18.50 / 22.00",
            "net_receipts": "$1,585.00 Realized",
            "circuit_breaker": "ARMED",
            "execution_wire": "Direct Metal Router"
        }
    },
    "family_syndicate_core": {
        "title": "FAMILY // SYNDICATE",
        "category": "sovereign_life",
        "telemetry": {
            "paloma": "Common App v4 · Stanford/Duke/ND",
            "luke": "LOTR Screening · Cello Match",
            "ana": "Foundation Trust Review · Dinner 20:00",
            "clara": "Equestrian Practice · Weekend Prep"
        }
    },
    "estate_montecito_sentry": {
        "title": "MONTECITO // ESTATE SENTRY",
        "category": "physical_estate",
        "telemetry": {
            "enclave": "California Coastal Enclave",
            "optical_feed": "Discrete Perimeter Feed (Private)",
            "microgrid_power": "Solar 11.4 kW · Battery 98%",
            "texas_ranch": "SOLD // Zero Cattle Telemetry"
        }
    },
    "treasury_liquidity_covenants": {
        "title": "TREASURY // LIQUIDITY COVENANTS",
        "category": "allocator_capital",
        "telemetry": {
            "liquid_reserves": "Sub-30 Day T-Bills & Cash",
            "horizon_syndicate": "Active Tranche Nominal",
            "pe_covenants": "WildSeed Craft Extraction Safe",
            "margin_status": "Zero Leverage"
        }
    },
    "dora_rv_craft_ip": {
        "title": "DORA RV // RESTOMOD & BRAND IP",
        "category": "bespoke_craft",
        "telemetry": {
            "vehicle": "Chopped-Top 1974 Restomod American Camper",
            "shop_progress": "Chassis Reinforced · Drivetrain Drop",
            "salvage_radar": "Detroit Diesel 6V53 & Rare Trim Pings",
            "tour_status": "PCH Overlook / Big Sur Route Active",
            "ip_filing": "Heritage Marque Trademark Clearance Pending"
        }
    }
}

def get_profile_path(profile_id: str) -> Path:
    return SCHEMA_DIR / f"{profile_id}.json"

def load_profile(profile_id: str) -> ProfileManifest:
    filepath = get_profile_path(profile_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found.")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ProfileManifest(**data)

def save_profile(profile: ProfileManifest):
    filepath = get_profile_path(profile.profile_id)
    dump_data = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dump_data, f, indent=2)

@router.get("/cartridges")
async def list_cartridges():
    """List all registered data cartridges available on metal."""
    return {"status": "ok", "cartridges": CARTRIDGE_CATALOG}

@router.get("/profile/{profile_id}")
async def get_profile_endpoint(profile_id: str):
    """Retrieve full declarative profile for an allocator."""
    profile = load_profile(profile_id)
    dump_data = profile.model_dump() if hasattr(profile, "model_dump") else profile.dict()
    return {"status": "ok", "profile": dump_data}

@router.post("/profile/{profile_id}/toggle-deck")
async def toggle_deck_endpoint(profile_id: str, target_deck: Optional[str] = None):
    """Toggle the active viewport deck with zero code rebuild."""
    profile = load_profile(profile_id)
    deck_keys = list(profile.decks.keys())
    if not deck_keys:
        raise HTTPException(status_code=400, detail="Profile contains no decks.")
    
    if target_deck:
        if target_deck not in profile.decks:
            raise HTTPException(status_code=400, detail=f"Deck {target_deck} not found.")
        profile.active_deck = target_deck
    else:
        current_idx = deck_keys.index(profile.active_deck) if profile.active_deck in deck_keys else 0
        next_idx = (current_idx + 1) % len(deck_keys)
        profile.active_deck = deck_keys[next_idx]

    save_profile(profile)
    deck_data = profile.decks[profile.active_deck].model_dump() if hasattr(profile.decks[profile.active_deck], "model_dump") else profile.decks[profile.active_deck].dict()
    await manager.broadcast({
        "event": "deck_switched",
        "profile_id": profile.profile_id,
        "active_deck": profile.active_deck,
        "deck_manifest": deck_data
    })
    return {"status": "ok", "active_deck": profile.active_deck}

@router.websocket("/ws/{profile_id}")
async def websocket_endpoint(websocket: WebSocket, profile_id: str):
    """Hot-wire live WebSocket connection pushing real-time layout updates."""
    await manager.connect(websocket)
    try:
        profile = load_profile(profile_id)
        deck_data = profile.decks[profile.active_deck].model_dump() if hasattr(profile.decks[profile.active_deck], "model_dump") else profile.decks[profile.active_deck].dict()
        await websocket.send_json({
            "event": "connected",
            "profile_id": profile_id,
            "active_deck": profile.active_deck,
            "deck_manifest": deck_data
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
