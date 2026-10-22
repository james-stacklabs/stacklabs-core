#!/usr/bin/env python3
"""
Sovereign SDLC Portal — Emergent Society Simulation Router
Port: 8095 | Governing Standard: Invariant 50
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("sdlc_society")

router = APIRouter(tags=["Emergent Society"])

EMERGENT_SOCIETY_DB = os.environ.get("EMERGENT_SOCIETY_DB", "/home/james/stacklabs/data/emergent_society.db")

def get_society_db():
    conn = sqlite3.connect(EMERGENT_SOCIETY_DB, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

@router.get("/api/society/status")
async def get_society_status():
    return {
        "status": "active",
        "service": "emergent-society-engine",
        "database": EMERGENT_SOCIETY_DB,
        "database_exists": os.path.exists(EMERGENT_SOCIETY_DB)
    }

@router.get("/api/society/entities")
async def get_society_entities():
    if not os.path.exists(EMERGENT_SOCIETY_DB):
        return {"entities": []}
    conn = get_society_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM emergent_citizens ORDER BY systolic_bp DESC")
        citizens = [dict(r) for r in cur.fetchall()]
        return {"entities": citizens}
    except Exception as e:
        logger.warning(f"Failed to query emergent_citizens: {e}")
        return {"entities": []}
    finally:
        conn.close()

@router.get("/api/society/citizens")
async def get_society_citizens():
    if not os.path.exists(EMERGENT_SOCIETY_DB):
        return {"citizens": []}
    conn = get_society_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM emergent_citizens ORDER BY systolic_bp DESC")
        citizens = [dict(r) for r in cur.fetchall()]
        return {"citizens": citizens}
    except Exception as e:
        logger.warning(f"Failed to query emergent_citizens: {e}")
        return {"citizens": []}
    finally:
        conn.close()

@router.get("/api/society/feed")
async def get_society_feed():
    if not os.path.exists(EMERGENT_SOCIETY_DB):
        return {"feed": []}
    conn = get_society_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT d.dialogue_id, c.name, c.fandom, d.message_text,
                   d.emotional_tone, d.bp_delta, d.tums_consumed, d.created_at
            FROM society_dialogue d
            JOIN emergent_citizens c ON d.speaker_id = c.citizen_id
            ORDER BY d.created_at DESC LIMIT 20
        """)
        feed = [dict(r) for r in cur.fetchall()]
        return {"feed": feed}
    except Exception as e:
        logger.warning(f"Failed to query society_dialogue: {e}")
        return {"feed": []}
    finally:
        conn.close()

@router.get("/api/society/market")
async def get_society_market():
    if not os.path.exists(EMERGENT_SOCIETY_DB):
        return {"contracts": [], "recent_trades": []}
    conn = get_society_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM market_contracts WHERE status = 'OPEN'")
        contracts = [dict(r) for r in cur.fetchall()]
        cur.execute("""
            SELECT t.trade_id, c.name as citizen, m.ticker, t.side, 
                   t.position_type, t.quantity, t.price_cents, t.total_cost, t.timestamp
            FROM citizen_trades t
            JOIN emergent_citizens c ON t.citizen_id = c.citizen_id
            JOIN market_contracts m ON t.contract_id = m.contract_id
            ORDER BY t.timestamp DESC LIMIT 15
        """)
        trades = [dict(r) for r in cur.fetchall()]
        return {"contracts": contracts, "recent_trades": trades}
    except Exception as e:
        logger.warning(f"Failed to query market: {e}")
        return {"contracts": [], "recent_trades": []}
    finally:
        conn.close()

@router.post("/api/society/oracle/query")
async def post_society_oracle_query(request: Request):
    payload = await request.json()
    question = payload.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Field 'question' is required")
    from core.society_oracle import SocietyOracle
    oracle = SocietyOracle(db_path=EMERGENT_SOCIETY_DB)
    res = oracle.query(question)
    return res

@router.post("/api/society/oracle/inject")
async def post_society_oracle_inject(request: Request):
    payload = await request.json()
    headline = payload.get("headline", "")
    category = payload.get("category", "DIVINE_SHOCK")
    volatility = float(payload.get("volatility_score", 0.85))
    if not headline:
        raise HTTPException(status_code=400, detail="Field 'headline' is required")
    from core.society_oracle import SocietyOracle
    oracle = SocietyOracle(db_path=EMERGENT_SOCIETY_DB)
    res = oracle.inject_event(headline, category, volatility, payload)
    return res
