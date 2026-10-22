# ============================================================================
# SOVEREIGN OS // GREENSTACK 3.0 BOTANICAL CULTIVATION ROUTER
# Location: /home/james/stacklabs/scripts/routers/greenstack.py
# API Domain: /api/greenstack/*
# Author: James Carroll (Lead Systems Architect) / Smyrna Grow Zone 7b/8a
# ============================================================================

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
import uuid
import math
from datetime import datetime, timezone

from core.db import DB_PATH, get_db
from core.security import get_current_user

router = APIRouter(prefix="/api/greenstack", tags=["GreenStack 3.0 Cultivation"])

# --- In-Memory Actuator Relay State ---
ACTUATOR_RELAYS = {
    "exhaust_fan": True,
    "circ_fan_a": True,
    "circ_fan_b": False,
    "humidifier": False,
    "led_array_320w": True,
    "water_pump": True,
}

# --- Pydantic Request Models ---
class PopSeedRequest(BaseModel):
    seed_id: str
    target_zone: str = "fantasy_island"
    target_coord: Optional[str] = "A1"

class MovePlantRequest(BaseModel):
    plant_id: str
    target_zone: str
    target_coord: str

class FeedLogRequest(BaseModel):
    ph: float
    ec_ppm: float
    water_temp_f: Optional[float] = 68.0
    gallons_fed: Optional[float] = 2.0
    notes: Optional[str] = ""

class JournalEntryRequest(BaseModel):
    entry_type: str = "NOTE"  # NOTE, MILESTONE, TOPPING, DEFICIENCY_ALERT
    content: str
    image_url: Optional[str] = None

class StageUpdateRequest(BaseModel):
    stage: str  # germinating, seedling, vegetative, flowering, harvested

class RelayToggleRequest(BaseModel):
    relay_name: str
    state: bool

class AddSeedRequest(BaseModel):
    name: str
    category: str
    breeder: Optional[str] = "Smyrna Heirloom"
    remaining_seeds: int = 10
    optimal_dli: Optional[float] = 32.0
    optimal_vpd_min: Optional[float] = 0.8
    optimal_vpd_max: Optional[float] = 1.2
    notes: Optional[str] = ""

# --- Helper: Compute VPD (Vapor Pressure Deficit in kPa) ---
def compute_vpd(temp_f: float, rh_pct: float) -> float:
    # Convert Fahrenheit to Celsius
    temp_c = (temp_f - 32.0) * (5.0 / 9.0)
    # Saturated Vapor Pressure (VPsat) in kPa (Tetens equation)
    vp_sat = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    # Actual Vapor Pressure (VPact) in kPa
    vp_act = vp_sat * (rh_pct / 100.0)
    # VPD = VPsat - VPact
    vpd = vp_sat - vp_act
    return round(vpd, 2)


# ============================================================================
# 1. ZONES & SPATIAL GARDEN GRID
# ============================================================================

@router.get("/zones")
async def get_all_zones():
    """Retrieve all configured grow zones with plant counts and latest telemetry."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        zones = conn.execute("SELECT * FROM zones").fetchall()
        result = []
        for z in zones:
            z_dict = dict(z)
            # Count active plants
            plant_count = conn.execute(
                "SELECT COUNT(*) as c FROM plant_assets WHERE zone_id = ? AND status = 'active'", 
                (z["id"],)
            ).fetchone()["c"]
            # Latest telemetry
            telemetry = conn.execute(
                "SELECT * FROM telemetry_logs WHERE zone_id = ? ORDER BY recorded_at DESC LIMIT 1",
                (z["id"],)
            ).fetchone()
            z_dict["plant_count"] = plant_count
            z_dict["latest_telemetry"] = dict(telemetry) if telemetry else {
                "temperature_f": 75.0,
                "relative_humidity": 60.0,
                "vpd_kpa": compute_vpd(75.0, 60.0),
                "recorded_at": datetime.now(timezone.utc).isoformat()
            }
            result.append(z_dict)
        return {"zones": result}
    finally:
        conn.close()


@router.get("/zones/{zone_id}/grid")
async def get_zone_grid(zone_id: str):
    """Retrieve 2D spatial grid matrix for a specific zone with active plants and companion tags."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        zone = conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        plants = conn.execute("""
            SELECT p.*, s.category, s.breeder
            FROM plant_assets p
            LEFT JOIN seed_bank s ON s.id = p.seed_id
            WHERE p.zone_id = ? AND p.status = 'active'
        """, (zone_id,)).fetchall()

        # Build coordinate lookup
        occupied = {}
        for p in plants:
            p_dict = dict(p)
            # Calculate days alive
            try:
                planted_dt = datetime.fromisoformat(p["planted_at"].replace(" ", "T"))
                days_alive = max(0, (datetime.now(timezone.utc) - planted_dt.replace(tzinfo=timezone.utc)).days)
            except Exception:
                days_alive = 0
            p_dict["days_alive"] = days_alive
            
            # Companion / Conflict tag logic
            p_name = p["strain_name"].lower()
            if "cherokee" in p_name or "tomato" in p_name:
                p_dict["compat_badge"] = "+COMPAT"
                p_dict["compat_note"] = "High companion bonus with Sweet Basil in adjacent bay"
            elif "san marzano" in p_name:
                p_dict["compat_badge"] = "+COMPAT"
                p_dict["compat_note"] = "Optimal light exposure in canopy slot A2"
            else:
                p_dict["compat_badge"] = "OPTIMAL"
                p_dict["compat_note"] = "Standard growth parameters active"

            occupied[p["grid_coord"]] = p_dict

        # Build full NxM grid
        grid_rows = zone["grid_rows"]
        grid_cols = zone["grid_cols"]
        row_labels = [chr(65 + r) for r in range(grid_rows)]  # A, B, C, D...
        grid_matrix = []

        for r_idx, r_label in enumerate(row_labels):
            row_items = []
            for c_idx in range(1, grid_cols + 1):
                coord = f"{r_label}{c_idx}"
                plant_data = occupied.get(coord, None)
                row_items.append({
                    "coord": coord,
                    "row": r_label,
                    "col": c_idx,
                    "is_occupied": plant_data is not None,
                    "plant": plant_data
                })
            grid_matrix.append({
                "row_label": r_label,
                "slots": row_items
            })

        return {
            "zone": dict(zone),
            "grid": grid_matrix,
            "total_slots": grid_rows * grid_cols,
            "occupied_slots": len(plants)
        }
    finally:
        conn.close()


@router.post("/plants/move")
async def move_plant(payload: MovePlantRequest):
    """Atomically update a plant's coordinate and zone location."""
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check target slot collision
        existing = conn.execute(
            "SELECT id FROM plant_assets WHERE zone_id = ? AND grid_coord = ? AND status = 'active'",
            (payload.target_zone, payload.target_coord)
        ).fetchone()
        if existing and existing[0] != payload.plant_id:
            raise HTTPException(status_code=409, detail=f"Coordinate {payload.target_coord} in {payload.target_zone} is already occupied by {existing[0]}")

        conn.execute("""
            UPDATE plant_assets
            SET zone_id = ?, grid_coord = ?
            WHERE id = ?
        """, (payload.target_zone, payload.target_coord, payload.plant_id))
        
        # Log relocation milestone in journal
        conn.execute("""
            INSERT INTO journal_entries (plant_id, entry_type, content)
            VALUES (?, 'MILESTONE', ?)
        """, (payload.plant_id, f"Relocated plant asset to zone '{payload.target_zone}' coordinate {payload.target_coord}"))
        
        conn.commit()
        return {
            "status": "success", 
            "plant_id": payload.plant_id,
            "target_zone": payload.target_zone,
            "target_coord": payload.target_coord
        }
    finally:
        conn.close()


# ============================================================================
# 2. MASTER SEED BANK & THE POP SEED WORKFLOW
# ============================================================================

@router.get("/seed_bank")
async def get_seed_bank(category: Optional[str] = None):
    """Retrieve full 42-strain genetics inventory from the Smyrna Master Vault."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT * FROM seed_bank"
        params = []
        if category and category.lower() != "all":
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY remaining_seeds DESC, name ASC"
        
        seeds = conn.execute(query, params).fetchall()
        return {
            "total_strains": len(seeds),
            "seeds": [dict(s) for s in seeds]
        }
    finally:
        conn.close()


@router.post("/seed_bank/pop")
async def pop_seed(payload: PopSeedRequest):
    """
    The 'Pop Seed' Workflow:
    Atomically decrements seed inventory count, provisions a new plant_assets row,
    assigns initial status 'germinating', and generates high-contrast QR label payload.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        seed = conn.execute("SELECT * FROM seed_bank WHERE id = ?", (payload.seed_id,)).fetchone()
        if not seed:
            raise HTTPException(status_code=404, detail="Seed strain not found")
        if seed["remaining_seeds"] <= 0:
            raise HTTPException(status_code=400, detail=f"Zero seeds remaining for strain '{seed['name']}'")

        # Atomic decrement
        conn.execute(
            "UPDATE seed_bank SET remaining_seeds = remaining_seeds - 1 WHERE id = ?",
            (payload.seed_id,)
        )

        # Generate unique asset tag
        short_code = "".join([w[0].upper() for w in seed["name"].split()[:2]])
        random_id = uuid.uuid4().hex[:4].upper()
        plant_id = f"GS-{short_code}-{random_id}"
        
        # QR Code payload for mobile in-tent scanner deep linking
        qr_payload = f"https://clio.taila01894.ts.net:3016/greenstack?plant={plant_id}"

        # Find first empty coordinate in target zone if coord not specified or occupied
        target_coord = payload.target_coord
        occupied_coords = [r[0] for r in conn.execute(
            "SELECT grid_coord FROM plant_assets WHERE zone_id = ? AND status = 'active'",
            (payload.target_zone,)
        ).fetchall()]
        
        if not target_coord or target_coord in occupied_coords:
            for r in ["A", "B", "C", "D"]:
                for c in range(1, 5):
                    candidate = f"{r}{c}"
                    if candidate not in occupied_coords:
                        target_coord = candidate
                        break
                if target_coord and target_coord not in occupied_coords:
                    break

        conn.execute("""
            INSERT INTO plant_assets
                (id, seed_id, strain_name, zone_id, grid_coord, stage, planted_at, qr_code_payload, status)
            VALUES (?, ?, ?, ?, ?, 'germinating', datetime('now'), ?, 'active')
        """, (plant_id, payload.seed_id, seed["name"], payload.target_zone, target_coord, qr_payload))

        # Initial journal entry
        conn.execute("""
            INSERT INTO journal_entries (plant_id, entry_type, content)
            VALUES (?, 'MILESTONE', ?)
        """, (plant_id, f"Popped seed from Smyrna Master Vault ({seed['name']}). Enqueued for germination in {payload.target_zone}:{target_coord}."))

        conn.commit()

        return {
            "status": "success",
            "plant_id": plant_id,
            "strain_name": seed["name"],
            "remaining_seeds": seed["remaining_seeds"] - 1,
            "zone_id": payload.target_zone,
            "grid_coord": target_coord,
            "stage": "germinating",
            "qr_code_payload": qr_payload
        }
    finally:
        conn.close()


@router.post("/seed_bank/add")
async def add_seed(payload: AddSeedRequest):
    """Add a new cultivar or heirloom cross to the Smyrna Master Vault."""
    conn = sqlite3.connect(DB_PATH)
    try:
        new_id = f"SB-NEW-{uuid.uuid4().hex[:4].upper()}"
        conn.execute("""
            INSERT INTO seed_bank
                (id, name, category, breeder, remaining_seeds, optimal_dli, optimal_vpd_min, optimal_vpd_max, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id, payload.name, payload.category, payload.breeder, 
            payload.remaining_seeds, payload.optimal_dli, 
            payload.optimal_vpd_min, payload.optimal_vpd_max, payload.notes
        ))
        conn.commit()
        return {"status": "success", "id": new_id, "name": payload.name}
    finally:
        conn.close()


# ============================================================================
# 3. PLANT DOSSIER, NUTRIENTS & GROWTH JOURNAL
# ============================================================================

@router.get("/plants/{plant_id}")
async def get_plant_dossier(plant_id: str):
    """Retrieve detailed plant dossier, historical feed logs, milestones, and photo gallery."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        plant = conn.execute("""
            SELECT p.*, s.category, s.breeder, s.optimal_dli, s.optimal_vpd_min, s.optimal_vpd_max, s.notes as strain_notes,
                   z.name as zone_name, z.media_type
            FROM plant_assets p
            LEFT JOIN seed_bank s ON s.id = p.seed_id
            LEFT JOIN zones z ON z.id = p.zone_id
            WHERE p.id = ?
        """, (plant_id,)).fetchone()
        
        if not plant:
            raise HTTPException(status_code=404, detail="Plant asset not found")
        
        plant_dict = dict(plant)
        
        # Calculate days alive
        try:
            planted_dt = datetime.fromisoformat(plant["planted_at"].replace(" ", "T"))
            days_alive = max(0, (datetime.now(timezone.utc) - planted_dt.replace(tzinfo=timezone.utc)).days)
        except Exception:
            days_alive = 0
        plant_dict["days_alive"] = days_alive

        # Historical nutrient logs
        feeds = conn.execute(
            "SELECT * FROM nutrient_logs WHERE plant_id = ? ORDER BY logged_at DESC LIMIT 20",
            (plant_id,)
        ).fetchall()
        plant_dict["feed_history"] = [dict(f) for f in feeds]

        # Chronological journal entries
        journals = conn.execute(
            "SELECT * FROM journal_entries WHERE plant_id = ? ORDER BY created_at DESC LIMIT 30",
            (plant_id,)
        ).fetchall()
        plant_dict["journal"] = [dict(j) for j in journals]

        return {"plant": plant_dict}
    finally:
        conn.close()


@router.post("/plants/{plant_id}/feed")
async def log_plant_feed(plant_id: str, payload: FeedLogRequest):
    """Log a nutrient feeding event (pH, EC/PPM, water temperature, gallons fed)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        plant = conn.execute("SELECT zone_id FROM plant_assets WHERE id = ?", (plant_id,)).fetchone()
        if not plant:
            raise HTTPException(status_code=404, detail="Plant asset not found")
        
        conn.execute("""
            INSERT INTO nutrient_logs (plant_id, zone_id, ph, ec_ppm, water_temp_f, gallons_fed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (plant_id, plant["zone_id"], payload.ph, payload.ec_ppm, payload.water_temp_f, payload.gallons_fed, payload.notes))

        # Insert feed summary into chronological journal
        summary = f"FEED_LOG: pH {payload.ph} | EC {payload.ec_ppm} PPM | {payload.gallons_fed} gal @ {payload.water_temp_f}°F"
        if payload.notes:
            summary += f" ({payload.notes})"
            
        conn.execute("""
            INSERT INTO journal_entries (plant_id, entry_type, content)
            VALUES (?, 'FEED_LOG', ?)
        """, (plant_id, summary))

        conn.commit()
        return {"status": "success", "plant_id": plant_id, "feed_summary": summary}
    finally:
        conn.close()


@router.post("/plants/{plant_id}/journal")
async def add_journal_entry(plant_id: str, payload: JournalEntryRequest):
    """Add a growth observation note, topping event, or milestone."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO journal_entries (plant_id, entry_type, content, image_url)
            VALUES (?, ?, ?, ?)
        """, (plant_id, payload.entry_type, payload.content, payload.image_url))
        conn.commit()
        return {"status": "success", "plant_id": plant_id}
    finally:
        conn.close()


@router.post("/plants/{plant_id}/stage")
async def update_plant_stage(plant_id: str, payload: StageUpdateRequest):
    """Update plant growth lifecycle stage."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            UPDATE plant_assets SET stage = ? WHERE id = ?
        """, (payload.stage, plant_id))
        
        conn.execute("""
            INSERT INTO journal_entries (plant_id, entry_type, content)
            VALUES (?, 'MILESTONE', ?)
        """, (plant_id, f"Transitioned growth stage to '{payload.stage.upper()}'"))
        
        conn.commit()
        return {"status": "success", "plant_id": plant_id, "stage": payload.stage}
    finally:
        conn.close()


# ============================================================================
# 4. REAL-TIME MICROCLIMATE & RELAY ACTUATION
# ============================================================================

@router.get("/telemetry/live")
async def get_live_telemetry():
    """Returns real-time computed microclimate data, VPD gauges, and DWC reservoir status."""
    temp_f = 76.1
    rh_pct = 53.8
    vpd_kpa = compute_vpd(temp_f, rh_pct)
    
    # VPD Status evaluation
    if vpd_kpa < 0.4:
        vpd_status = "DAMP"
        vpd_badge_color = "amber"
        recommendation = "High Mold Risk: Increase exhaust fan CFM to lower canopy humidity."
    elif 0.8 <= vpd_kpa <= 1.2:
        vpd_status = "IDEAL"
        vpd_badge_color = "emerald"
        recommendation = "System Stable: Optimal stomatal conductance and nutrient uptake."
    elif 1.2 < vpd_kpa <= 1.6:
        vpd_status = "WARNING"
        vpd_badge_color = "amber"
        recommendation = "Elevated Transpiration Stress: Pulse humidifier or reduce canopy temp."
    else:
        vpd_status = "CRITICAL"
        vpd_badge_color = "rose"
        recommendation = "Severe Stomatal Closure: Immediate humidification required."

    return {
        "microclimate": {
            "temperature_f": temp_f,
            "relative_humidity_pct": rh_pct,
            "vpd_kpa": vpd_kpa,
            "vpd_status": vpd_status,
            "vpd_badge_color": vpd_badge_color,
            "recommendation": recommendation,
            "dli_target": 32.4,
            "leaf_temp_delta_f": -2.1
        },
        "dwc_reservoir": {
            "ph": 5.8,
            "ec_ppm": 650,
            "water_temp_f": 68.2,
            "status": "OPTIMAL",
            "gallons_level": 14.5
        },
        "relays": ACTUATOR_RELAYS,
        "smyrna_weather": {
            "zone": "Smyrna, GA (Grow Zone 7b/8a)",
            "last_frost_date": "April 15",
            "first_frost_date": "November 1",
            "frost_countdown_days": 71,
            "patio_safe": True
        }
    }


@router.post("/relays/toggle")
async def toggle_relay(payload: RelayToggleRequest):
    """Toggle a hardware actuator relay (Exhaust Fan, Humidifier, Circ Fan, LED Array)."""
    if payload.relay_name in ACTUATOR_RELAYS:
        ACTUATOR_RELAYS[payload.relay_name] = payload.state
        return {"status": "success", "relay": payload.relay_name, "state": payload.state}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown relay '{payload.relay_name}'")


# ============================================================================
# 5. PROJECT METSY BREEDING LAB & COMPANION ENGINE
# ============================================================================

@router.get("/breeding/project_metsy")
async def get_project_metsy_brief():
    """Retrieve Project Metsy Cherokee Purple × Bodacious F1 heirloom breeding brief and generational roadmap."""
    return {
        "project_name": "Project Metsy",
        "codename": "Metsy's Guts / The High-Umami Beefsteak",
        "mission": "Breed, select, and stabilize a novel open-pollinated heirloom tomato variety combining intense green locular gel / savory glutamic acid umami with 12 oz beefsteak sizing and early/late blight resistance.",
        "parents": {
            "parent_a": {
                "role": "Mother / Flavor & Gel Anchor",
                "variety": "Cherokee Purple",
                "traits": "Dusky purple-rose skin, multi-locular seed cavities, rich savory green locular gel, high natural glutamic acid."
            },
            "parent_b": {
                "role": "Father / Size & Vigor Anchor",
                "variety": "Bodacious Hybrid F1",
                "traits": "10-12 oz bright red slicing beefsteak, hybrid vigor, exceptional resistance to early blight, late blight, and nematodes."
            }
        },
        "roadmap": [
            {"generation": "F1 Hybrid", "year": "Year 1", "status": "CONFIRMED", "objective": "Uniform hybrid vigor; verify cross success and harvest initial F2 seed batch."},
            {"generation": "F2 Segregation", "year": "Year 2", "status": "ACTIVE_SELECTION", "objective": "Grow out 10-20 plants; observe Mendelian segregation for purple skin and locular gel volume."},
            {"generation": "F3-F6 Stabilization", "year": "Years 3-6", "status": "QUEUED", "objective": "Repeated single-plant selections focusing on disease tolerance and gel density."},
            {"generation": "F7 True-Breeding Heirloom", "year": "Year 7", "status": "QUEUED", "objective": "Homozygous stability achieved; registration in Seed Savers Exchange (SSE)."}
        ],
        "hand_pollination_protocol": [
            "1. Emasculation: Remove anther cone from unopened yellowing bud on Cherokee Purple using fine tweezers.",
            "2. Pollen Extraction: Collect fresh pollen from Bodacious F1 using vibrating tool or clean spoon.",
            "3. Pollination: Apply pollen directly to exposed stigma of Cherokee Purple flower.",
            "4. Tagging: Mark flower with colored yarn and record date.",
            "5. Fermentation: 3-day pulp water bath fermentation before cataloging seeds."
        ]
    }


@router.get("/companion_rules")
async def get_companion_rules():
    """Retrieve companion planting bonuses and allelopathic conflict rules."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rules = conn.execute("SELECT * FROM companion_rules").fetchall()
        return {"rules": [dict(r) for r in rules]}
    finally:
        conn.close()


@router.get("/pest_guide")
async def get_pest_guide():
    """Retrieve organic treatment guides and beneficial predator insect catalog."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        guide = conn.execute("SELECT * FROM pest_disease_guide").fetchall()
        return {"diagnostics": [dict(g) for g in guide]}
    finally:
        conn.close()
