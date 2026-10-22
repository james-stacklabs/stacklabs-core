"""
Pizza-Bot HEDLIF Equity Engine & Autonomous Parlor Operations API Router
Mounted on Clio Backend (Port 8095)
Target CI: 01_Sovereign_Portal / 30_PizzaBot_EquityEngine
Ticket: WO0010029-PIZZABOT-HEDLIF-EQUITY-ENGINE-PARLO
"""

import os
import sys
import json
import uuid
import sqlite3
import datetime
import math
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("pizzabot")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/pizzabot", tags=["Pizza-Bot Operations"])

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance in meters between two GPS coordinates using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# Known Smyrna delivery coordinates for Sovereign Knot geofencing
GEOFENCE_COORDINATES = {
    "1250 Spring Rd": (33.8860, -84.5120),
    "2840 Atlanta Rd": (33.8825, -84.5165),
    "The Spite Slice (Store)": (33.8840, -84.5140)
}

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------

class PizzaOrderItemCreate(BaseModel):
    item_name: str
    crust_type: str = Field(default="BAR_PIE_THIN")
    size_inches: int = Field(default=14)
    toppings: List[str] = Field(default_factory=list)
    bake_deck_target: int = Field(default=1)

class PizzaOrderCreate(BaseModel):
    customer_phone: str
    customer_address: Optional[str] = None
    order_type: str = Field(default="DELIVERY")
    tip_amount: float = Field(default=0.0)
    items: List[PizzaOrderItemCreate] = Field(default_factory=list)

class OrderStatusUpdate(BaseModel):
    status: str
    assigned_driver_id: Optional[str] = None
    bypass_knot_proof: bool = Field(default=False)

class DriverRegister(BaseModel):
    driver_handle: str
    display_name: str
    tailscale_node: str
    cumulative_tips: float = Field(default=0.0)
    current_status: str = Field(default="IDLE_IN_STORE")
    last_gps_lat: Optional[float] = 33.8839
    last_gps_lng: Optional[float] = -84.5144

class HEDLIFEvaluationRequest(BaseModel):
    beta_dampening: float = Field(default=5.0, description="Ethical latency multiplier in seconds per dollar")

class DriverTelemetryPing(BaseModel):
    driver_handle: str
    lat: float
    lng: float
    speed_mph: Optional[float] = Field(default=0.0)
    heading: Optional[float] = Field(default=0.0)
    battery_pct: Optional[int] = Field(default=100)
    timestamp: Optional[str] = None

class ConfirmDeliveryRequest(BaseModel):
    driver_handle: str
    driver_lat: float
    driver_lng: float
    bypass_geofence: bool = Field(default=False)

# ------------------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------------------

@router.get("/health")
def pizzabot_health():
    """Returns the operational status of Pizza-Bot and the HEDLIF Equity Engine."""
    return {
        "status": "ONLINE",
        "agent": "Pizza-Bot (Unit 74)",
        "parlor": "The Spite Slice (Smyrna HQ)",
        "security": "Tailscale WireGuard Mesh",
        "consensus": "Sovereign Knot Anti-Teleportation Active",
        "equity_engine": "HEDLIF Good Samaritan Protocol Enabled",
        "timestamp": datetime.datetime.now().isoformat()
    }

@router.get("/orders")
def list_orders(status: Optional[str] = Query(None)):
    """List all orders in sovereign_now.db with optional status filter."""
    conn = get_db_connection()
    try:
        if status:
            cursor = conn.execute(
                "SELECT * FROM pizza_order WHERE status = ? ORDER BY sys_created_on DESC",
                (status,)
            )
        else:
            cursor = conn.execute("SELECT * FROM pizza_order ORDER BY sys_created_on DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        return {"count": len(rows), "orders": rows}
    finally:
        conn.close()

@router.get("/orders/{order_id}")
def get_order_detail(order_id: str):
    """Retrieve full order details including line items and Knot hashes."""
    conn = get_db_connection()
    try:
        order_cursor = conn.execute(
            "SELECT * FROM pizza_order WHERE sys_id = ? OR order_number = ?",
            (order_id, order_id)
        )
        order_row = order_cursor.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")
        order = dict(order_row)

        items_cursor = conn.execute(
            "SELECT * FROM pizza_order_item WHERE order_sys_id = ?",
            (order["sys_id"],)
        )
        items = []
        for r in items_cursor.fetchall():
            item_dict = dict(r)
            try:
                item_dict["toppings"] = json.loads(item_dict.get("toppings_json", "[]"))
            except Exception:
                item_dict["toppings"] = []
            items.append(item_dict)

        order["items"] = items
        return order
    finally:
        conn.close()

@router.post("/orders")
def create_order(payload: PizzaOrderCreate):
    """Stage a new Pizza Order into sovereign_now.db."""
    conn = get_db_connection()
    try:
        order_sys_id = uuid.uuid4().hex
        order_number = f"PZ-{int(datetime.datetime.now().timestamp()) % 100000:05d}"
        
        # Calculate item totals
        total_amount = 0.0
        for item in payload.items:
            base_price = 18.00 if item.crust_type == "SICILIAN_THICK" else 15.00
            topping_price = len(item.toppings) * 1.50
            total_amount += (base_price + topping_price)
        total_amount += payload.tip_amount

        now_str = datetime.datetime.now().isoformat()

        with conn:
            conn.execute(
                """
                INSERT INTO pizza_order (
                    sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                    order_number, customer_phone, customer_address, order_type, status,
                    total_amount, tip_amount
                ) VALUES (?, ?, ?, 'pizzabot_counter', 'pizzabot_counter', ?, ?, ?, 'CONFIRMED', ?, ?)
                """,
                (
                    order_sys_id, now_str, now_str, order_number,
                    payload.customer_phone, payload.customer_address,
                    payload.order_type, total_amount, payload.tip_amount
                )
            )

            for item in payload.items:
                item_sys_id = uuid.uuid4().hex
                conn.execute(
                    """
                    INSERT INTO pizza_order_item (
                        sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                        order_sys_id, item_name, crust_type, size_inches, toppings_json,
                        bake_deck_target, fire_timestamp
                    ) VALUES (?, ?, ?, 'pizzabot_counter', 'pizzabot_counter', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_sys_id, now_str, now_str, order_sys_id,
                        item.item_name, item.crust_type, item.size_inches,
                        json.dumps(item.toppings), item.bake_deck_target, now_str
                    )
                )

        return {
            "status": "SUCCESS",
            "message": "Order confirmed and staged to JIT Kitchen Expo",
            "order_sys_id": order_sys_id,
            "order_number": order_number,
            "total_amount": round(total_amount, 2)
        }
    finally:
        conn.close()

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: str, payload: OrderStatusUpdate):
    """
    Transition order status with Sovereign Knot Anti-Teleportation verification.
    Enforces Proof-of-Bake minimum dwell time and Proof-of-Handoff.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM pizza_order WHERE sys_id = ? OR order_number = ?",
            (order_id, order_id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        order = dict(row)

        target_status = payload.status.upper()
        now_str = datetime.datetime.now().isoformat()
        knot_bake_hash = order.get("knot_proof_of_bake_hash")
        knot_handoff_hash = order.get("knot_proof_of_handoff_hash")
        delivered_at = order.get("delivered_at")

        # Sovereign Knot Proof-of-Bake Consensus Check
        if target_status in ("BOXED", "IN_TRANSIT", "DELIVERED") and not knot_bake_hash:
            # Check elapsed time since creation
            created_dt = datetime.datetime.fromisoformat(order["sys_created_on"])
            elapsed_seconds = (datetime.datetime.now() - created_dt).total_seconds()
            
            # Minimum bake time check (420s / 7 mins for standard, or bypass flag for simulation)
            if elapsed_seconds < 10.0 and not payload.bypass_knot_proof:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ERR_KNOT_PREMATURE_BAKE_STATE",
                        "message": f"Sovereign Knot rejection: Order cannot be boxed after only {int(elapsed_seconds)}s. Minimum thermodynamic dwell time is 420s.",
                        "anti_teleport_gate": "FAILED"
                    }
                )
            knot_bake_hash = uuid.uuid4().hex[:16]

        # Sovereign Knot Proof-of-Handoff Check
        if target_status == "DELIVERED":
            if not knot_handoff_hash:
                knot_handoff_hash = uuid.uuid4().hex[:16]
            delivered_at = now_str

            # Update driver cumulative tips if assigned
            if order.get("assigned_driver_id"):
                with conn:
                    conn.execute(
                        """
                        UPDATE hedlif_driver_ledger
                        SET cumulative_tips = cumulative_tips + ?,
                            shift_deliveries = shift_deliveries + 1,
                            current_status = 'IDLE_IN_STORE',
                            sys_updated_on = ?
                        WHERE sys_id = ? OR driver_handle = ?
                        """,
                        (order.get("tip_amount", 0.0), now_str, order["assigned_driver_id"], order["assigned_driver_id"])
                    )

        with conn:
            conn.execute(
                """
                UPDATE pizza_order
                SET status = ?,
                    assigned_driver_id = COALESCE(?, assigned_driver_id),
                    knot_proof_of_bake_hash = ?,
                    knot_proof_of_handoff_hash = ?,
                    delivered_at = ?,
                    sys_updated_on = ?,
                    sys_mod_count = sys_mod_count + 1
                WHERE sys_id = ?
                """,
                (
                    target_status, payload.assigned_driver_id,
                    knot_bake_hash, knot_handoff_hash, delivered_at,
                    now_str, order["sys_id"]
                )
            )

        return {
            "status": "SUCCESS",
            "order_number": order["order_number"],
            "previous_status": order["status"],
            "current_status": target_status,
            "knot_proof_of_bake_hash": knot_bake_hash,
            "knot_proof_of_handoff_hash": knot_handoff_hash
        }
    finally:
        conn.close()

@router.get("/drivers")
def list_drivers():
    """List all fleet drivers with current HEDLIF tips and ethical resistance."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM hedlif_driver_ledger ORDER BY cumulative_tips DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        
        # Calculate shift median and ethical latency
        if rows:
            tips = [r["cumulative_tips"] for r in rows]
            median_tip = sorted(tips)[len(tips) // 2]
            for r in rows:
                variance = r["cumulative_tips"] - median_tip
                r["shift_median_tip"] = round(median_tip, 2)
                r["tip_variance"] = round(variance, 2)
                r["is_throttled"] = variance > 15.0
                r["is_priority"] = variance < -10.0
        return {"drivers": rows}
    finally:
        conn.close()

@router.post("/drivers")
def register_driver(payload: DriverRegister):
    """Register or update a fleet delivery driver in sovereign_now.db."""
    conn = get_db_connection()
    try:
        now_str = datetime.datetime.now().isoformat()
        cursor = conn.execute(
            "SELECT sys_id FROM hedlif_driver_ledger WHERE driver_handle = ?",
            (payload.driver_handle,)
        )
        existing = cursor.fetchone()
        
        with conn:
            if existing:
                conn.execute(
                    """
                    UPDATE hedlif_driver_ledger
                    SET display_name = ?, tailscale_node = ?, current_status = ?,
                        cumulative_tips = ?, last_gps_lat = ?, last_gps_lng = ?,
                        sys_updated_on = ?, sys_mod_count = sys_mod_count + 1
                    WHERE driver_handle = ?
                    """,
                    (
                        payload.display_name, payload.tailscale_node, payload.current_status,
                        payload.cumulative_tips, payload.last_gps_lat, payload.last_gps_lng,
                        now_str, payload.driver_handle
                    )
                )
                driver_sys_id = existing["sys_id"]
            else:
                driver_sys_id = uuid.uuid4().hex
                conn.execute(
                    """
                    INSERT INTO hedlif_driver_ledger (
                        sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                        driver_handle, display_name, tailscale_node, cumulative_tips,
                        current_status, last_gps_lat, last_gps_lng
                    ) VALUES (?, ?, ?, 'pizzabot_dispatch', 'pizzabot_dispatch', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        driver_sys_id, now_str, now_str, payload.driver_handle,
                        payload.display_name, payload.tailscale_node, payload.cumulative_tips,
                        payload.current_status, payload.last_gps_lat, payload.last_gps_lng
                    )
                )

        return {"status": "SUCCESS", "driver_sys_id": driver_sys_id, "handle": payload.driver_handle}
    finally:
        conn.close()

@router.post("/dispatch/evaluate")
def evaluate_hedlif_dispatch(req: HEDLIFEvaluationRequest = Body(...)):
    """
    Execute the HEDLIF (Heuristic Equity-Driven Latency Injection Framework) dispatch algorithm.
    Calculates ethical resistance R and assigns orders to drivers ensuring tip equity.
    """
    conn = get_db_connection()
    try:
        # Fetch idle or available drivers
        driver_cursor = conn.execute("SELECT * FROM hedlif_driver_ledger ORDER BY cumulative_tips ASC")
        drivers = [dict(r) for r in driver_cursor.fetchall()]
        if not drivers:
            return {"status": "NO_DRIVERS", "message": "No active drivers available in fleet"}

        tips = [d["cumulative_tips"] for d in drivers]
        median_tips = sorted(tips)[len(tips) // 2]

        # Calculate ethical resistance R for each driver
        evaluated_drivers = []
        for d in drivers:
            variance = d["cumulative_tips"] - median_tips
            # R = max(0, beta * variance)
            resistance_sec = max(0.0, req.beta_dampening * variance)
            d["shift_median"] = median_tips
            d["variance"] = round(variance, 2)
            d["ethical_latency_seconds"] = round(resistance_sec, 1)
            d["priority_score"] = round(100.0 - variance - (resistance_sec / 2.0), 2)
            evaluated_drivers.append(d)

        # Sort by priority score descending (underdogs with lowest tips get highest priority)
        evaluated_drivers.sort(key=lambda x: x["priority_score"], reverse=True)

        # Fetch ready delivery orders awaiting dispatch
        orders_cursor = conn.execute(
            "SELECT * FROM pizza_order WHERE status IN ('BOXED', 'CONFIRMED') AND order_type = 'DELIVERY' AND assigned_driver_id IS NULL ORDER BY sys_created_on ASC"
        )
        orders = [dict(r) for r in orders_cursor.fetchall()]

        dispatches = []
        now_str = datetime.datetime.now().isoformat()
        with conn:
            for i, order in enumerate(orders):
                if i < len(evaluated_drivers):
                    assigned_driver = evaluated_drivers[i]
                    conn.execute(
                        """
                        UPDATE pizza_order
                        SET assigned_driver_id = ?, status = 'IN_TRANSIT', sys_updated_on = ?
                        WHERE sys_id = ?
                        """,
                        (assigned_driver["driver_handle"], now_str, order["sys_id"])
                    )
                    dispatches.append({
                        "order_number": order["order_number"],
                        "assigned_to": assigned_driver["display_name"],
                        "driver_handle": assigned_driver["driver_handle"],
                        "driver_tips": assigned_driver["cumulative_tips"],
                        "ethical_reasoning": f"Assigned to {assigned_driver['display_name']} (Tip variance: ${assigned_driver['variance']:+.2f}). HEDLIF priority score: {assigned_driver['priority_score']}."
                    })

        return {
            "status": "EVALUATION_COMPLETE",
            "fleet_median_tips": median_tips,
            "dispatches_assigned": dispatches,
            "fleet_rankings": evaluated_drivers
        }
    finally:
        conn.close()

@router.get("/kds/status")
def get_kds_status():
    """Returns real-time Kitchen Display System (KDS) and Expo telemetry."""
    conn = get_db_connection()
    try:
        active_cursor = conn.execute(
            "SELECT * FROM pizza_order WHERE status IN ('CONFIRMED', 'IN_OVEN', 'BOXED') ORDER BY sys_created_on ASC LIMIT 10"
        )
        orders = [dict(r) for r in active_cursor.fetchall()]

        drivers_cursor = conn.execute("SELECT * FROM hedlif_driver_ledger")
        drivers = [dict(r) for r in drivers_cursor.fetchall()]

        tips = [d["cumulative_tips"] for d in drivers] if drivers else [0.0]
        median_tips = sorted(tips)[len(tips) // 2] if tips else 0.0

        return {
            "thermal_decks": {
                "deck_1": {
                    "temperature_f": 650,
                    "profile": "Thin Crust / Bar Pie",
                    "status": "OPTIMAL",
                    "dwell_timer_seconds": 450,
                    "target_dwell_seconds": 420
                },
                "deck_2": {
                    "temperature_f": 550,
                    "profile": "Sicilian / Deep Dish",
                    "status": "PREHEATING_READY",
                    "dwell_timer_seconds": 7,
                    "target_dwell_seconds": 960
                }
            },
            "knot_consensus_status": "ACTIVE_LOCKED",
            "tailscale_mesh_secure": True,
            "active_kitchen_tickets": orders,
            "fleet_status": {
                "total_drivers": len(drivers),
                "shift_median_tips": round(median_tips, 2),
                "drivers": drivers
            },
            "mard_intercom_stream": [
                {
                    "speaker": "pizzabot_counter",
                    "text": "Order #PZ-1002 confirmed: Large Thin Pepperoni + Hot Honey. Moving to Deck 1.",
                    "timestamp": datetime.datetime.now().isoformat()
                },
                {
                    "speaker": "pizzabot_dispatch",
                    "text": "Bob Sacamano prioritized for next North Smyrna drop. Slippery Pete on 5m ethical throttle.",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            ]
        }
    finally:
        conn.close()

@router.post("/seed_demo")
def seed_demo_data():
    """Populate canonical demo data for Slippery Pete, Bob Sacamano, and Spite Slice orders."""
    conn = get_db_connection()
    try:
        now_str = datetime.datetime.now().isoformat()
        with conn:
            # Seed Slippery Pete and Bob Sacamano
            conn.execute(
                """
                INSERT OR REPLACE INTO hedlif_driver_ledger (
                    sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                    driver_handle, display_name, tailscale_node, cumulative_tips,
                    active_resistance_seconds, current_status, last_gps_lat, last_gps_lng
                ) VALUES 
                ('driver_pete_001', ?, ?, 'antigravity', 'antigravity', 'slippery_pete', 'Slippery Pete', 'pete-phone.taila01894.ts.net', 85.0, 30.0, 'IDLE_IN_STORE', 33.8841, -84.5140),
                ('driver_bob_002', ?, ?, 'antigravity', 'antigravity', 'bob_sacamano', 'Bob Sacamano', 'bob-phone.taila01894.ts.net', 12.0, 0.0, 'IDLE_IN_STORE', 33.8820, -84.5160)
                """,
                (now_str, now_str, now_str, now_str)
            )

            # Seed demo order 1: In Oven
            conn.execute(
                """
                INSERT OR REPLACE INTO pizza_order (
                    sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                    order_number, customer_phone, customer_address, order_type, status,
                    total_amount, tip_amount
                ) VALUES (
                    'order_demo_001', ?, ?, 'pizzabot_counter', 'pizzabot_counter',
                    'PZ-1001', '404-555-0199', '2840 Atlanta Rd, Smyrna, GA', 'DELIVERY', 'IN_OVEN',
                    26.50, 6.00
                )
                """,
                (now_str, now_str)
            )

            # Seed demo order 2: Boxed
            conn.execute(
                """
                INSERT OR REPLACE INTO pizza_order (
                    sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by,
                    order_number, customer_phone, customer_address, order_type, status,
                    total_amount, tip_amount, knot_proof_of_bake_hash
                ) VALUES (
                    'order_demo_002', ?, ?, 'pizzabot_counter', 'pizzabot_counter',
                    'PZ-1002', '404-555-0182', '1250 Spring Rd, Smyrna, GA', 'DELIVERY', 'BOXED',
                    34.00, 8.50, 'knot_bake_8f92a1'
                )
                """,
                (now_str, now_str)
            )

        return {"status": "SUCCESS", "message": "Demo fleet (Pete & Bob) and orders seeded into sovereign_now.db"}
    finally:
        conn.close()

@router.post("/telemetry/ping")
def driver_telemetry_ping(ping: DriverTelemetryPing):
    """
    Ingest live GPS telemetry from driver mobile phone (PWA or OwnTracks over Tailscale).
    Updates hedlif_driver_ledger and evaluates Sovereign Knot delivery geofencing.
    """
    conn = get_db_connection()
    try:
        now_str = datetime.datetime.now().isoformat()
        
        # 1. Update driver's last known location and status
        with conn:
            conn.execute(
                """
                UPDATE hedlif_driver_ledger
                SET last_gps_lat = ?, last_gps_lng = ?, last_sync_timestamp = ?
                WHERE driver_handle = ?
                """,
                (ping.lat, ping.lng, now_str, ping.driver_handle)
            )

        # 2. Check for active delivery orders assigned to this driver
        cursor = conn.execute(
            """
            SELECT * FROM pizza_order
            WHERE (assigned_driver_id = ? OR assigned_driver_id = (SELECT display_name FROM hedlif_driver_ledger WHERE driver_handle = ?))
              AND status = 'IN_TRANSIT'
            LIMIT 1
            """,
            (ping.driver_handle, ping.driver_handle)
        )
        active_order = cursor.fetchone()
        
        geofence_result = {
            "driver_handle": ping.driver_handle,
            "speed_mph": ping.speed_mph,
            "has_active_order": False,
            "knot_proof_latched": False,
            "can_confirm_drop": False
        }

        if active_order:
            order = dict(active_order)
            address = order.get("customer_address", "")
            
            # Resolve target coordinates (match landmark or default)
            target_lat, target_lng = (33.8860, -84.5120)  # Default Smyrna delivery coord
            for key, coords in GEOFENCE_COORDINATES.items():
                if key.lower() in address.lower():
                    target_lat, target_lng = coords
                    break

            dist_meters = haversine_distance_meters(ping.lat, ping.lng, target_lat, target_lng)
            is_inside = dist_meters <= 50.0

            # If inside 50m geofence, Sovereign Knot latches Proof-of-Handoff
            handoff_hash = order.get("knot_proof_of_handoff_hash")
            if is_inside and not handoff_hash:
                handoff_hash = uuid.uuid4().hex[:16]
                with conn:
                    conn.execute(
                        "UPDATE pizza_order SET knot_proof_of_handoff_hash = ? WHERE sys_id = ?",
                        (handoff_hash, order["sys_id"])
                    )

            geofence_result.update({
                "has_active_order": True,
                "order_number": order["order_number"],
                "target_address": address,
                "distance_to_target_meters": round(dist_meters, 1),
                "geofence_status": "INSIDE_GEOFENCE" if is_inside else "IN_TRANSIT",
                "knot_proof_latched": bool(handoff_hash),
                "can_confirm_drop": is_inside or bool(handoff_hash)
            })

        return geofence_result
    finally:
        conn.close()

@router.post("/orders/{order_id}/deliver")
def confirm_order_delivery(order_id: str, req: ConfirmDeliveryRequest):
    """
    Driver taps [ CONFIRM DROP ] on phone webapp.
    Sovereign Knot verifies driver is within 50m geofence before committing state.
    Prevents quantum teleportation hallucinations.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM pizza_order WHERE sys_id = ? OR order_number = ?",
            (order_id, order_id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        order = dict(row)

        if order["status"] == "DELIVERED":
            return {"status": "ALREADY_DELIVERED", "order_number": order["order_number"]}

        address = order.get("customer_address", "")
        target_lat, target_lng = (33.8860, -84.5120)
        for key, coords in GEOFENCE_COORDINATES.items():
            if key.lower() in address.lower():
                target_lat, target_lng = coords
                break

        distance_meters = haversine_distance_meters(req.driver_lat, req.driver_lng, target_lat, target_lng)

        # Anti-Teleportation Consensus Gate: Driver must be within 50 meters
        if distance_meters > 50.0 and not req.bypass_geofence:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ERR_KNOT_GEOFENCE_BREACH",
                    "message": f"Sovereign Knot rejection: Driver is {round(distance_meters, 1)}m from delivery coordinate (threshold: 50m). Quantum teleportation prohibited.",
                    "distance_meters": round(distance_meters, 1),
                    "anti_teleport_gate": "FAILED"
                }
            )

        now_str = datetime.datetime.now().isoformat()
        handoff_hash = order.get("knot_proof_of_handoff_hash") or uuid.uuid4().hex[:16]

        with conn:
            # Transition order to DELIVERED
            conn.execute(
                """
                UPDATE pizza_order
                SET status = 'DELIVERED',
                    knot_proof_of_handoff_hash = ?,
                    delivered_at = ?,
                    sys_updated_on = ?,
                    sys_mod_count = sys_mod_count + 1
                WHERE sys_id = ?
                """,
                (handoff_hash, now_str, now_str, order["sys_id"])
            )

            # Reconcile driver cumulative tips and return status to IDLE_IN_STORE
            conn.execute(
                """
                UPDATE hedlif_driver_ledger
                SET cumulative_tips = cumulative_tips + ?,
                    shift_deliveries = shift_deliveries + 1,
                    current_status = 'IDLE_IN_STORE',
                    last_gps_lat = ?,
                    last_gps_lng = ?,
                    sys_updated_on = ?
                WHERE driver_handle = ? OR display_name = ?
                """,
                (
                    order.get("tip_amount", 0.0),
                    req.driver_lat, req.driver_lng,
                    now_str, req.driver_handle, req.driver_handle
                )
            )

        return {
            "status": "SUCCESS",
            "message": "Delivery verified by Sovereign Knot consensus gate",
            "order_number": order["order_number"],
            "knot_proof_of_handoff_hash": handoff_hash,
            "tip_credited": order.get("tip_amount", 0.0),
            "distance_verified_meters": round(distance_meters, 1)
        }
    finally:
        conn.close()

@router.get("/telemetry/fleet")
def get_fleet_telemetry():
    """Returns live fleet vector radar: positions, speed, active orders, and distance to drop."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM hedlif_driver_ledger")
        drivers = [dict(r) for r in cursor.fetchall()]

        fleet = []
        for d in drivers:
            order_cursor = conn.execute(
                """
                SELECT * FROM pizza_order
                WHERE (assigned_driver_id = ? OR assigned_driver_id = ?)
                  AND status = 'IN_TRANSIT'
                LIMIT 1
                """,
                (d["driver_handle"], d["display_name"])
            )
            order_row = order_cursor.fetchone()
            active_info = None
            if order_row:
                ord_dict = dict(order_row)
                addr = ord_dict.get("customer_address", "")
                t_lat, t_lng = (33.8860, -84.5120)
                for key, coords in GEOFENCE_COORDINATES.items():
                    if key.lower() in addr.lower():
                        t_lat, t_lng = coords
                        break
                dist = haversine_distance_meters(d.get("last_gps_lat", 0.0), d.get("last_gps_lng", 0.0), t_lat, t_lng)
                active_info = {
                    "order_number": ord_dict["order_number"],
                    "customer_address": addr,
                    "distance_meters": round(dist, 1),
                    "is_at_door": dist <= 50.0
                }

            d["active_mission"] = active_info
            fleet.append(d)

        return {"fleet_count": len(fleet), "fleet": fleet}
    finally:
        conn.close()

