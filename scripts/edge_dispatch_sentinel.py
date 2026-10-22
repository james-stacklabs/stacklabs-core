#!/usr/bin/env python3
"""
DaVinci's Smyrna Edge Dispatch Sentinel (PizzaBot Redux) — Power Tool #44
Path: /home/james/stacklabs/scripts/edge_dispatch_sentinel.py
Port: 8099 (0.0.0.0:8099)

Offline-first commercial kitchen order ingress, 550°F gas stone deck thermal rail routing,
driver dispatch, and cryptographic Proof-of-Bake consensus for DaVinci's Pizzeria of Smyrna.
Backed by the 4-Minute Carroll Hot-Swap SLA.
Target Enterprise: DaVinci's Pizzeria of Smyrna / Empasta Restaurant Group LLC
                  1810 Spring Rd SE, Smyrna, GA 30080 | (678) 213-1112
"""

import os
import sys
import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Ensure SovereignOS scripts directory is in sys.path
SOVEREIGN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(SOVEREIGN_ROOT, "scripts")
if SOVEREIGN_ROOT not in sys.path:
    sys.path.insert(0, SOVEREIGN_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from core.db import get_db, DB_PATH

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SENTINEL-8099] %(message)s"
)
logger = logging.getLogger("edge_dispatch_sentinel")

app = FastAPI(
    title="DaVinci's Edge Dispatch Sentinel",
    description="Offline-First Commercial Kitchen Dispatch & KDS Deck (Port 8099)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE_NAME = "DaVinci's Pizzeria of Smyrna"
STORE_ADDRESS = "1810 Spring Rd SE, Smyrna, GA 30080"
STORE_PHONE = "(678) 213-1112"
HOT_SWAP_SLA = "4-Minute Hot-Swap"


# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------

class OrderItemSchema(BaseModel):
    item_name: str
    quantity: int = Field(default=1, ge=1)
    price: float = Field(default=0.0, ge=0.0)
    crust_type: str = Field(default="BAR_PIE_THIN")
    size_inches: int = Field(default=14)
    toppings: List[str] = Field(default_factory=list)
    bake_deck_target: int = Field(default=1)
    notes: Optional[str] = None


class OrderCreateRequest(BaseModel):
    order_number: Optional[str] = None
    customer_name: Optional[str] = "Smyrna Customer"
    customer_phone: str = "(678) 555-0100"
    customer_address: Optional[str] = "1810 Spring Rd SE"
    order_type: str = Field(default="DELIVERY", description="DELIVERY, CATERING, PICKUP")
    total_amount: Optional[float] = None
    tip_amount: float = Field(default=0.0, ge=0.0)
    is_catering: bool = False
    items: List[OrderItemSchema] = Field(default_factory=list)
    special_instructions: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="NEW, IN_OVEN, OUT_FOR_DELIVERY, DELIVERED")
    driver_id: Optional[str] = None
    notes: Optional[str] = None


# ------------------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/sentinel/health")
def get_sentinel_health():
    """Returns JSON status with active orders count and 4-Minute Hot-Swap SLA guarantee."""
    active_count = 0
    db_status = "CONNECTED"
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pizza_order WHERE status IN ('NEW', 'CONFIRMED', 'IN_OVEN', 'BAKING', 'OUT_FOR_DELIVERY', 'IN_TRANSIT')")
            row = cursor.fetchone()
            if row:
                active_count = row[0]
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = "DEGRADED"

    return {
        "status": "OPERATIONAL",
        "service": "DaVinci's Edge Dispatch Sentinel (PizzaBot Redux)",
        "db": db_status,
        "db_path": DB_PATH,
        "active_orders": active_count,
        "metal_sla": HOT_SWAP_SLA,
        "store": {
            "name": STORE_NAME,
            "address": STORE_ADDRESS,
            "phone": STORE_PHONE
        },
        "port": 8099,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/sentinel/orders")
def get_sentinel_orders():
    """Returns live orders categorized by state (NEW, IN_OVEN, OUT_FOR_DELIVERY, DELIVERED)."""
    categorized = {
        "NEW": [],
        "IN_OVEN": [],
        "OUT_FOR_DELIVERY": [],
        "DELIVERED": []
    }
    all_orders = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pizza_order ORDER BY sys_created_on DESC LIMIT 100")
        order_rows = cursor.fetchall()

        for o in order_rows:
            order_dict = dict(o)
            order_sys_id = order_dict["sys_id"]

            cursor.execute("SELECT * FROM pizza_order_item WHERE order_sys_id = ?", (order_sys_id,))
            item_rows = cursor.fetchall()
            items = []
            for item in item_rows:
                idict = dict(item)
                try:
                    idict["toppings"] = json.loads(idict.get("toppings_json") or "[]")
                except Exception:
                    idict["toppings"] = []
                items.append(idict)
            order_dict["items"] = items

            st = (order_dict.get("status") or "NEW").upper()
            if st in ("NEW", "CONFIRMED", "PENDING"):
                categorized["NEW"].append(order_dict)
            elif st in ("IN_OVEN", "BAKING", "BOXED"):
                categorized["IN_OVEN"].append(order_dict)
            elif st in ("OUT_FOR_DELIVERY", "IN_TRANSIT", "DISPATCHED"):
                categorized["OUT_FOR_DELIVERY"].append(order_dict)
            else:
                categorized["DELIVERED"].append(order_dict)

            all_orders.append(order_dict)

    return {
        "status": "SUCCESS",
        "total_count": len(all_orders),
        "categorized": categorized,
        "orders": all_orders,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/sentinel/order")
def ingest_order(payload: OrderCreateRequest):
    """Ingests a new order, computes SHA-256 proof_of_bake_hash, and writes to SQLite WAL."""
    now_iso = datetime.now().isoformat()
    order_sys_id = uuid.uuid4().hex

    # Determine order number
    if payload.order_number:
        order_number = payload.order_number.strip().upper()
    else:
        prefix = "CAT" if payload.is_catering or payload.order_type == "CATERING" else "ORD"
        order_number = f"{prefix}-SMYRNA-{int(datetime.now().timestamp()) % 10000:04d}"

    # Calculate total if not provided
    calculated_total = 0.0
    for it in payload.items:
        if it.price > 0.0:
            calculated_total += it.price * it.quantity
        else:
            base = 22.0 if "SPECIALTY" in it.item_name.upper() or "DEVIL" in it.item_name.upper() else 16.0
            topping_cost = len(it.toppings) * 1.75
            calculated_total += (base + topping_cost) * it.quantity

    total_amount = round(payload.total_amount if payload.total_amount is not None else (calculated_total + payload.tip_amount), 2)

    # Compute SHA-256 Proof-of-Bake cryptographic consensus hash
    hash_payload = f"{order_number}:{payload.customer_phone}:{now_iso}:{total_amount}:{payload.order_type}"
    proof_of_bake_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    db_order_type = payload.order_type.upper().strip()
    if db_order_type not in ("DELIVERY", "PICKUP", "DINE_IN"):
        db_order_type = "DELIVERY"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pizza_order (
                sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count,
                order_number, customer_phone, customer_address, order_type, status,
                total_amount, tip_amount, knot_proof_of_bake_hash
            ) VALUES (?, ?, ?, 'edge_sentinel_8099', 'edge_sentinel_8099', 0, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?)
        """, (
            order_sys_id, now_iso, now_iso, order_number,
            payload.customer_phone, payload.customer_address, db_order_type,
            total_amount, payload.tip_amount, proof_of_bake_hash
        ))

        # Insert items
        for it in payload.items:
            item_sys_id = uuid.uuid4().hex
            toppings_str = json.dumps(it.toppings)
            cursor.execute("""
                INSERT INTO pizza_order_item (
                    sys_id, sys_created_on, sys_updated_on, sys_created_by, sys_updated_by, sys_mod_count,
                    order_sys_id, item_name, crust_type, size_inches, toppings_json,
                    bake_deck_target, fire_timestamp
                ) VALUES (?, ?, ?, 'edge_sentinel_8099', 'edge_sentinel_8099', 0, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_sys_id, now_iso, now_iso, order_sys_id,
                f"{it.quantity}x {it.item_name}" if it.quantity > 1 else it.item_name,
                it.crust_type, it.size_inches, toppings_str,
                it.bake_deck_target, now_iso
            ))

        conn.commit()

    logger.info(f"Ingested order {order_number} (${total_amount}) with Proof-of-Bake: {proof_of_bake_hash[:16]}")
    return {
        "status": "SUCCESS",
        "order_id": order_sys_id,
        "order_number": order_number,
        "proof_of_bake_hash": proof_of_bake_hash,
        "total_amount": total_amount,
        "message": "Order persisted to SQLite WAL. Thermal rail routing armed."
    }


@app.post("/api/sentinel/order/{order_id}/status")
def advance_order_status(order_id: str, payload: StatusUpdateRequest):
    """Advances lifecycle state (NEW -> IN_OVEN -> OUT_FOR_DELIVERY -> DELIVERED)."""
    now_iso = datetime.now().isoformat()
    target_status = payload.status.upper().strip()

    status_map = {
        "NEW": "CONFIRMED",
        "CONFIRMED": "CONFIRMED",
        "IN_OVEN": "IN_OVEN",
        "BAKING": "IN_OVEN",
        "BOXED": "BOXED",
        "OUT_FOR_DELIVERY": "IN_TRANSIT",
        "IN_TRANSIT": "IN_TRANSIT",
        "DELIVERED": "DELIVERED",
        "SETTLED": "DELIVERED"
    }
    db_status = status_map.get(target_status)
    if not db_status:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'. Must be one of {list(status_map.keys())}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pizza_order WHERE sys_id = ? OR order_number = ?", (order_id, order_id))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")

        order_dict = dict(order)
        real_sys_id = order_dict["sys_id"]
        order_num = order_dict["order_number"]

        handoff_hash = order_dict.get("knot_proof_of_handoff_hash")
        delivered_at = order_dict.get("delivered_at")

        if db_status == "IN_OVEN":
            cursor.execute("UPDATE pizza_order_item SET fire_timestamp = ? WHERE order_sys_id = ?", (now_iso, real_sys_id))

        if db_status in ("DELIVERED", "SETTLED"):
            delivered_at = now_iso
            handoff_payload = f"handoff:{order_num}:{payload.driver_id or 'courier'}:{now_iso}"
            handoff_hash = hashlib.sha256(handoff_payload.encode("utf-8")).hexdigest()

        cursor.execute("""
            UPDATE pizza_order
            SET status = ?,
                assigned_driver_id = COALESCE(?, assigned_driver_id),
                knot_proof_of_handoff_hash = COALESCE(?, knot_proof_of_handoff_hash),
                delivered_at = COALESCE(?, delivered_at),
                sys_updated_on = ?,
                sys_mod_count = sys_mod_count + 1
            WHERE sys_id = ?
        """, (db_status, payload.driver_id, handoff_hash, delivered_at, now_iso, real_sys_id))

        conn.commit()

    logger.info(f"Order {order_num} advanced to {target_status} (DB: {db_status})")
    return {
        "status": "SUCCESS",
        "order_number": order_num,
        "new_status": target_status,
        "db_status": db_status,
        "proof_of_handoff_hash": handoff_hash,
        "timestamp": now_iso
    }



@app.get("/api/sentinel/ticket/{order_id}/thermal")
def get_thermal_ticket(order_id: str, request: Request):
    """Formats 80mm ESC/POS receipt representation for physical 550°F kitchen rails."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pizza_order WHERE sys_id = ? OR order_number = ?", (order_id, order_id))
        order_row = cursor.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")

        order = dict(order_row)
        cursor.execute("SELECT * FROM pizza_order_item WHERE order_sys_id = ?", (order["sys_id"],))
        item_rows = cursor.fetchall()
        items = []
        for r in item_rows:
            idict = dict(r)
            try:
                idict["toppings"] = json.loads(idict.get("toppings_json") or "[]")
            except Exception:
                idict["toppings"] = []
            items.append(idict)

    ticket_text = generate_80mm_thermal_ticket(order, items)

    if "text/plain" in request.headers.get("Accept", ""):
        return PlainTextResponse(ticket_text)

    return {
        "status": "SUCCESS",
        "order_number": order.get("order_number"),
        "char_width": 46,
        "thermal_text": ticket_text
    }


def generate_80mm_thermal_ticket(order: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Renders formatted 46-column monospaced ESC/POS receipt text."""
    w = 46
    sep = "=" * w
    dash = "-" * w

    lines = [
        sep,
        "        DAVINCI'S PIZZERIA OF SMYRNA        ".center(w),
        "       1810 Spring Rd SE, Smyrna, GA        ".center(w),
        "             Tel: (678) 213-1112            ".center(w),
        "        OFFLINE-FIRST KITCHEN SENTINEL      ".center(w),
        sep,
        f"TICKET : {order.get('order_number', 'N/A')}".ljust(24) + f"TYPE: {order.get('order_type', 'DELIVERY')}".rjust(w - 24),
        f"TIME   : {order.get('sys_created_on', 'N/A')[:19]}",
        f"PHONE  : {order.get('customer_phone', 'N/A')}",
        f"ADDR   : {order.get('customer_address', 'N/A')}",
        f"STATUS : {order.get('status', 'NEW')}",
        dash,
        "QTY  ITEM DESCRIPTION                    DECK",
        dash,
    ]

    for item in items:
        name = item.get("item_name", "Pie")
        deck = f"D#{item.get('bake_deck_target', 1)} (550°F)"
        lines.append(f" 1   {name[:28].ljust(28)} {deck.rjust(12)}")

        toppings = item.get("toppings", [])
        if toppings:
            lines.append(f"     + {', '.join(toppings[:5])}"[:w])
        if item.get("crust_type") and item.get("crust_type") != "BAR_PIE_THIN":
            lines.append(f"     Crust: {item.get('crust_type')}"[:w])

    lines.append(dash)
    subtotal = float(order.get("total_amount") or 0.0) - float(order.get("tip_amount") or 0.0)
    lines.append(f"SUBTOTAL:".ljust(30) + f"${subtotal:8.2f}".rjust(w - 30))
    lines.append(f"DRIVER TIP:".ljust(30) + f"${float(order.get('tip_amount') or 0.0):8.2f}".rjust(w - 30))
    lines.append(f"TOTAL:".ljust(30) + f"${float(order.get('total_amount') or 0.0):8.2f}".rjust(w - 30))
    lines.append(dash)

    bake_hash = order.get("knot_proof_of_bake_hash") or "N/A"
    lines.extend([
        "PROOF-OF-BAKE CONSENSUS (SHA-256):",
        f"{bake_hash[:44]}",
        f"{bake_hash[44:]}" if len(bake_hash) > 44 else "",
        dash,
        "★ 4-MINUTE CARROLL HOT-SWAP SLA GUARANTEE ★",
        "  Zero Cloud Lag • Stainless Steel Rail Ready ",
        sep,
        "\n\n"
    ])
    return "\n".join([line for line in lines if line is not None])


# ------------------------------------------------------------------------------
# Frontend Kitchen Display System (KDS) Deck
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def get_kds_hud():
    """Serves high-contrast dark-mode KDS dashboard for 550°F commercial kitchen operations."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DaVinci's Smyrna // Edge Dispatch Sentinel (Port 8099)</title>
    <style>
        :root {
            --bg-void: #090B10;
            --bg-card: #131722;
            --bg-card-hover: #1A2030;
            --border: #232A3E;
            --text-main: #F3F4F6;
            --text-muted: #94A3B8;
            --accent-amber: #F59E0B;
            --accent-flame: #EF4444;
            --accent-cyan: #06B6D4;
            --accent-emerald: #10B981;
            --accent-purple: #8B5CF6;
            --font-mono: 'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-void);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Header */
        header {
            background: linear-gradient(180deg, #181E2E 0%, #0F131D 100%);
            border-bottom: 2px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .header-brand {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .pizza-emblem {
            font-size: 32px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 12px;
            padding: 4px 8px;
        }

        .brand-title {
            font-size: 19px;
            font-weight: 800;
            letter-spacing: 0.05em;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .brand-badge {
            background: var(--accent-flame);
            color: #FFF;
            font-size: 10px;
            font-weight: 900;
            padding: 2px 6px;
            border-radius: 4px;
            letter-spacing: 0.08em;
        }

        .brand-sub {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
            font-family: var(--font-mono);
        }

        .header-sla {
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.35);
            padding: 6px 14px;
            border-radius: 9999px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            color: #FCD34D;
        }

        .sla-beacon {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-amber);
            box-shadow: 0 0 10px var(--accent-amber);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.9); }
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn:hover {
            background: var(--bg-card-hover);
            border-color: #3B4664;
        }

        .btn-flame {
            background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
            border-color: #EF4444;
            color: #FFF;
        }

        .btn-flame:hover {
            background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
        }

        .btn-amber {
            background: rgba(245, 158, 11, 0.2);
            border-color: var(--accent-amber);
            color: #FCD34D;
        }

        .btn-emerald {
            background: rgba(16, 185, 129, 0.2);
            border-color: var(--accent-emerald);
            color: #6EE7B7;
        }

        /* 4 Column KDS Grid */
        .kds-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            padding: 18px 24px;
            flex: 1;
            overflow-x: auto;
        }

        .kds-column {
            background: rgba(19, 23, 34, 0.6);
            border: 1px solid var(--border);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            min-width: 310px;
        }

        .col-header {
            padding: 12px 16px;
            border-bottom: 2px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 0.05em;
        }

        .col-1 .col-header { border-bottom-color: var(--accent-amber); color: #FCD34D; }
        .col-2 .col-header { border-bottom-color: var(--accent-flame); color: #FCA5A5; }
        .col-3 .col-header { border-bottom-color: var(--accent-cyan); color: #67E8F9; }
        .col-4 .col-header { border-bottom-color: var(--accent-emerald); color: #6EE7B7; }

        .col-count {
            background: rgba(255, 255, 255, 0.1);
            font-size: 11px;
            font-family: var(--font-mono);
            padding: 2px 8px;
            border-radius: 9999px;
            color: #FFF;
        }

        .order-deck {
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow-y: auto;
            flex: 1;
        }

        /* Order Cards */
        .order-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            transition: transform 0.15s ease, border-color 0.15s ease;
            position: relative;
        }

        .order-card:hover {
            border-color: #3E4B6E;
            transform: translateY(-2px);
        }

        .card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .order-num {
            font-family: var(--font-mono);
            font-weight: 800;
            font-size: 14px;
            color: #FFFFFF;
        }

        .pill-type {
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .pill-delivery { background: rgba(59, 130, 246, 0.2); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.4); }
        .pill-catering { background: rgba(139, 92, 246, 0.25); color: #C4B5FD; border: 1px solid rgba(139, 92, 246, 0.5); font-weight: 900; }
        .pill-pickup { background: rgba(16, 185, 129, 0.2); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.4); }

        .card-customer {
            font-size: 12px;
            color: #CBD5E1;
            line-height: 1.4;
        }

        .card-customer strong {
            color: #FFF;
        }

        .card-items {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
            padding: 8px 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
        }

        .card-item-row {
            display: flex;
            justify-content: space-between;
            color: #F1F5F9;
        }

        .card-item-toppings {
            font-size: 11px;
            color: var(--text-muted);
            padding-left: 8px;
        }

        .card-hash-pill {
            font-family: var(--font-mono);
            font-size: 9px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            border: 1px dashed rgba(255, 255, 255, 0.15);
            padding: 4px 6px;
            border-radius: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .card-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 6px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .card-total {
            font-size: 13px;
            font-weight: 800;
            color: #34D399;
        }

        .card-actions {
            display: flex;
            gap: 6px;
        }

        .action-btn {
            font-size: 11px;
            padding: 5px 9px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid transparent;
        }

        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 100;
            backdrop-filter: blur(4px);
        }

        .modal-content {
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 12px;
            max-width: 520px;
            width: 90%;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.8);
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .thermal-paper {
            background: #FFFAF0;
            color: #111;
            font-family: var(--font-mono);
            font-size: 11px;
            line-height: 1.35;
            padding: 16px;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre;
            border: 1px dashed #CCC;
            box-shadow: inset 0 2px 6px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>

    <header>
        <div class="header-brand">
            <div class="pizza-emblem">🍕</div>
            <div>
                <div class="brand-title">
                    DAVINCI'S SMYRNA // EDGE DISPATCH SENTINEL
                    <span class="brand-badge">PORT 8099</span>
                </div>
                <div class="brand-sub">
                    1810 Spring Rd SE, Smyrna, GA 30080 • (678) 213-1112 • SQLite WAL Engine
                </div>
            </div>
        </div>

        <div class="header-sla">
            <div class="sla-beacon"></div>
            <span>4-MINUTE CARROLL HOT-SWAP SLA ACTIVE</span>
        </div>

        <div class="header-actions">
            <button class="btn btn-flame" onclick="simulateDinnerOrder()">+ JERSEY DEVIL RUSH</button>
            <button class="btn btn-amber" onclick="simulateCateringOrder()">+ CATERING DROP ($820)</button>
            <button class="btn" onclick="fetchOrders()">🔄 REFRESH</button>
        </div>
    </header>

    <main class="kds-container">
        <!-- Column 1: Incoming / Rail -->
        <div class="kds-column col-1">
            <div class="col-header">
                <span>INCOMING / RAIL</span>
                <span class="col-count" id="count-new">0</span>
            </div>
            <div class="order-deck" id="deck-new"></div>
        </div>

        <!-- Column 2: In Oven 550°F -->
        <div class="kds-column col-2">
            <div class="col-header">
                <span>IN OVEN (550°F STONE)</span>
                <span class="col-count" id="count-oven">0</span>
            </div>
            <div class="order-deck" id="deck-oven"></div>
        </div>

        <!-- Column 3: Out For Dispatch -->
        <div class="kds-column col-3">
            <div class="col-header">
                <span>OUT FOR DISPATCH</span>
                <span class="col-count" id="count-dispatch">0</span>
            </div>
            <div class="order-deck" id="deck-dispatch"></div>
        </div>

        <!-- Column 4: Settled / Delivered -->
        <div class="kds-column col-4">
            <div class="col-header">
                <span>SETTLED (PROOF-OF-BAKE)</span>
                <span class="col-count" id="count-settled">0</span>
            </div>
            <div class="order-deck" id="deck-settled"></div>
        </div>
    </main>

    <!-- Thermal Ticket Modal -->
    <div class="modal-overlay" id="thermalModal" onclick="closeThermalModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="font-size:16px;">🖨️ 80mm ESC/POS Thermal Rail Receipt</h3>
                <button class="btn" onclick="closeThermalModal()">✕ CLOSE</button>
            </div>
            <div class="thermal-paper" id="thermalPaperContent">Loading...</div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="btn btn-emerald" onclick="window.print()">PRINT TO RAIL</button>
            </div>
        </div>
    </div>

    <script>
        async function fetchOrders() {
            try {
                const res = await fetch('/api/sentinel/orders');
                const data = await res.json();
                renderDecks(data.categorized);
            } catch (err) {
                console.error("Failed to fetch orders:", err);
            }
        }

        function renderDecks(categorized) {
            renderColumn('deck-new', 'count-new', categorized.NEW || [], 'NEW');
            renderColumn('deck-oven', 'count-oven', categorized.IN_OVEN || [], 'IN_OVEN');
            renderColumn('deck-dispatch', 'count-dispatch', categorized.OUT_FOR_DELIVERY || [], 'OUT_FOR_DELIVERY');
            renderColumn('deck-settled', 'count-settled', categorized.DELIVERED || [], 'DELIVERED');
        }

        function renderColumn(deckId, countId, orders, stateKey) {
            const deck = document.getElementById(deckId);
            const count = document.getElementById(countId);
            count.textContent = orders.length;

            if (orders.length === 0) {
                deck.innerHTML = '<div style="color:var(--text-muted); font-size:12px; text-align:center; padding:24px 0;">No active orders</div>';
                return;
            }

            deck.innerHTML = orders.map(o => {
                const isCatering = o.order_type === 'CATERING' || (o.total_amount && o.total_amount > 200);
                const pillClass = isCatering ? 'pill-catering' : (o.order_type === 'PICKUP' ? 'pill-pickup' : 'pill-delivery');
                const pillLabel = isCatering ? 'CATERING VIP' : (o.order_type || 'DELIVERY');
                const bakeHash = o.knot_proof_of_bake_hash || 'PENDING_CONSENSUS';

                let actionBtn = '';
                if (stateKey === 'NEW') {
                    actionBtn = `<button class="action-btn btn-flame" onclick="advanceStatus('${o.sys_id}', 'IN_OVEN')">🔥 FIRE OVEN</button>`;
                } else if (stateKey === 'IN_OVEN') {
                    actionBtn = `<button class="action-btn btn-amber" onclick="advanceStatus('${o.sys_id}', 'OUT_FOR_DELIVERY')">🚗 DISPATCH</button>`;
                } else if (stateKey === 'OUT_FOR_DELIVERY') {
                    actionBtn = `<button class="action-btn btn-emerald" onclick="advanceStatus('${o.sys_id}', 'DELIVERED')">✅ DELIVERED</button>`;
                }

                const itemsHtml = (o.items || []).map(it => `
                    <div>
                        <div class="card-item-row">
                            <span><strong>${it.item_name}</strong></span>
                            <span style="color:var(--text-muted);">D#${it.bake_deck_target || 1}</span>
                        </div>
                        ${(it.toppings && it.toppings.length) ? `<div class="card-item-toppings">+ ${it.toppings.join(', ')}</div>` : ''}
                    </div>
                `).join('');

                return `
                    <div class="order-card" id="card-${o.sys_id}">
                        <div class="card-top">
                            <span class="order-num">${o.order_number}</span>
                            <span class="pill-type ${pillClass}">${pillLabel}</span>
                        </div>
                        <div class="card-customer">
                            <div>📍 <strong>${o.customer_address || 'Smyrna Store'}</strong></div>
                            <div style="color:var(--text-muted);">📞 ${o.customer_phone}</div>
                        </div>
                        <div class="card-items">
                            ${itemsHtml || '<div style="color:var(--text-muted);">No line items recorded</div>'}
                        </div>
                        <div class="card-hash-pill" title="Cryptographic Proof-of-Bake SHA-256">
                            🔐 ${bakeHash}
                        </div>
                        <div class="card-footer">
                            <span class="card-total">$${parseFloat(o.total_amount || 0).toFixed(2)}</span>
                            <div class="card-actions">
                                <button class="action-btn btn" onclick="viewThermal('${o.sys_id}')">🖨️ TICKET</button>
                                ${actionBtn}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function advanceStatus(orderId, nextStatus) {
            try {
                await fetch(`/api/sentinel/order/${orderId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: nextStatus, driver_id: 'south_cobb_courier' })
                });
                fetchOrders();
            } catch (err) {
                alert("Error advancing order status: " + err);
            }
        }

        async function viewThermal(orderId) {
            try {
                const res = await fetch(`/api/sentinel/ticket/${orderId}/thermal`);
                const data = await res.json();
                document.getElementById('thermalPaperContent').textContent = data.thermal_text;
                document.getElementById('thermalModal').style.display = 'flex';
            } catch (err) {
                alert("Error loading thermal ticket: " + err);
            }
        }

        function closeThermalModal() {
            document.getElementById('thermalModal').style.display = 'none';
        }

        async function simulateDinnerOrder() {
            const payload = {
                order_number: "ORD-SMYRNA-" + Math.floor(100 + Math.random() * 900),
                customer_phone: "(404) 555-0182",
                customer_address: "2800 Campbell Rd, Smyrna, GA 30080",
                order_type: "DELIVERY",
                tip_amount: 10.00,
                items: [
                    {
                        item_name: "Jersey Devil Specialty Pie (Hot Honey & Fig Jam)",
                        quantity: 1,
                        price: 24.50,
                        crust_type: "BAR_PIE_THIN",
                        size_inches: 16,
                        toppings: ["Hot Honey", "Fig Jam", "Soppressata", "Fresh Basil"],
                        bake_deck_target: 1
                    },
                    {
                        item_name: "20pc Lemon Pepper Wings",
                        quantity: 1,
                        price: 26.00,
                        toppings: ["Extra Crispy", "Wet Lemon Pepper"],
                        bake_deck_target: 2
                    }
                ]
            };
            await sendSimulated(payload);
        }

        async function simulateCateringOrder() {
            const payload = {
                order_number: "ORD-SMYRNA-CAT" + Math.floor(100 + Math.random() * 900),
                customer_phone: "(770) 555-0941",
                customer_address: "Cumberland Galleria Tower 300, Suite 1400",
                order_type: "CATERING",
                total_amount: 820.00,
                tip_amount: 100.00,
                is_catering: true,
                items: [
                    {
                        item_name: "Half-Sheet Baked Ziti",
                        quantity: 2,
                        price: 180.00,
                        toppings: ["Extra Ricotta", "Marinara"],
                        bake_deck_target: 1
                    },
                    {
                        item_name: "Full Sheet House Italian Salad",
                        quantity: 1,
                        price: 110.00,
                        toppings: ["House Vinaigrette", "Kalamata Olives"],
                        bake_deck_target: 1
                    },
                    {
                        item_name: "Garlic Rolls (40ct)",
                        quantity: 1,
                        price: 50.00,
                        toppings: ["Garlic Butter", "Pecorino"],
                        bake_deck_target: 2
                    }
                ]
            };
            await sendSimulated(payload);
        }

        async function sendSimulated(payload) {
            try {
                await fetch('/api/sentinel/order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                fetchOrders();
            } catch (err) {
                alert("Order simulation failed: " + err);
            }
        }

        // Poll every 3 seconds for zero-cloud-lag updates
        fetchOrders();
        setInterval(fetchOrders, 3000);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("edge_dispatch_sentinel:app", host="0.0.0.0", port=8099, reload=False)
