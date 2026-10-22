from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import sqlite3
import os
import uuid
import json
from datetime import datetime

router = APIRouter()

MAM_DB_PATH = "/home/james/stacklabs/dna/mam_warehouse.db"

class RuleModel(BaseModel):
    rule_id: str | None = None
    condition: str
    conditions_json: str | None = None
    action: str
    target_asset_type: str
    active_status: int = 1

class PinModel(BaseModel):
    pin_id: str | None = None
    asset_id: str
    pos_x: float
    pos_y: float
    timestamp: int
    label: str | None = None

# ── MAM Assets Endpoints ──────────────────────────────────────────────────────

@router.get("/api/mam/assets")
async def get_assets():
    if not os.path.exists(MAM_DB_PATH):
        return []
    conn = sqlite3.connect(MAM_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        assets = conn.execute("SELECT * FROM media_assets ORDER BY created_at DESC").fetchall()
        result = []
        for asset in assets:
            asset_dict = dict(asset)
            # Fetch metadata
            metadata_rows = conn.execute(
                "SELECT key, value FROM asset_metadata WHERE asset_id = ?", 
                (asset_dict["asset_id"],)
            ).fetchall()
            meta = {}
            for row in metadata_rows:
                try:
                    meta[row["key"]] = json.loads(row["value"])
                except Exception:
                    meta[row["key"]] = row["value"]
            asset_dict["metadata"] = meta
            result.append(asset_dict)
        return result
    finally:
        conn.close()

@router.delete("/api/mam/assets/{asset_id}")
async def delete_asset(asset_id: str):
    if not os.path.exists(MAM_DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized")
    conn = sqlite3.connect(MAM_DB_PATH)
    try:
        row = conn.execute("SELECT file_path FROM media_assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if row:
            file_path = row[0]
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
        conn.execute("DELETE FROM media_assets WHERE asset_id = ?", (asset_id,))
        conn.commit()
        return {"status": "ok", "message": "Asset deleted"}
    finally:
        conn.close()

# ── TMI Rules Endpoints ───────────────────────────────────────────────────────

@router.get("/api/mam/rules")
async def get_rules():
    if not os.path.exists(MAM_DB_PATH):
        return []
    conn = sqlite3.connect(MAM_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM tmi_rules ORDER BY sys_created_on DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("/api/mam/rules")
async def post_rule(rule: RuleModel):
    if not os.path.exists(MAM_DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized")
    conn = sqlite3.connect(MAM_DB_PATH)
    try:
        rule_id = rule.rule_id or str(uuid.uuid4())
        conn.execute("""
        INSERT INTO tmi_rules (rule_id, condition, conditions_json, action, target_asset_type, active_status, sys_created_on)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(rule_id) DO UPDATE SET
            condition = excluded.condition,
            conditions_json = excluded.conditions_json,
            action = excluded.action,
            target_asset_type = excluded.target_asset_type,
            active_status = excluded.active_status
        """, (rule_id, rule.condition, rule.conditions_json, rule.action, rule.target_asset_type, rule.active_status))
        conn.commit()
        return {"status": "ok", "rule_id": rule_id}
    finally:
        conn.close()

@router.delete("/api/mam/rules/{rule_id}")
async def delete_rule(rule_id: str):
    if not os.path.exists(MAM_DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized")
    conn = sqlite3.connect(MAM_DB_PATH)
    try:
        conn.execute("DELETE FROM tmi_rules WHERE rule_id = ?", (rule_id,))
        conn.commit()
        return {"status": "ok", "message": "Rule deleted"}
    finally:
        conn.close()

# ── Media Pins Endpoints ──────────────────────────────────────────────────────

@router.get("/api/mam/pins")
async def get_pins(asset_id: str | None = None):
    if not os.path.exists(MAM_DB_PATH):
        return []
    conn = sqlite3.connect(MAM_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if asset_id:
            rows = conn.execute("SELECT * FROM media_pins WHERE asset_id = ? ORDER BY timestamp ASC", (asset_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM media_pins ORDER BY sys_created_on DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("/api/mam/pins")
async def post_pin(pin: PinModel):
    if not os.path.exists(MAM_DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized")
    conn = sqlite3.connect(MAM_DB_PATH)
    try:
        pin_id = pin.pin_id or str(uuid.uuid4())
        conn.execute("""
        INSERT INTO media_pins (pin_id, asset_id, pos_x, pos_y, timestamp, label, sys_created_on)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(pin_id) DO UPDATE SET
            pos_x = excluded.pos_x,
            pos_y = excluded.pos_y,
            timestamp = excluded.timestamp,
            label = excluded.label
        """, (pin_id, pin.asset_id, pin.pos_x, pin.pos_y, pin.timestamp, pin.label))
        conn.commit()
        return {"status": "ok", "pin_id": pin_id}
    finally:
        conn.close()

@router.delete("/api/mam/pins/{pin_id}")
async def delete_pin(pin_id: str):
    if not os.path.exists(MAM_DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized")
    conn = sqlite3.connect(MAM_DB_PATH)
    try:
        conn.execute("DELETE FROM media_pins WHERE pin_id = ?", (pin_id,))
        conn.commit()
        return {"status": "ok", "message": "Pin deleted"}
    finally:
        conn.close()
