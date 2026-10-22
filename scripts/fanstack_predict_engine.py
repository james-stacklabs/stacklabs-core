#!/usr/bin/env python3
"""
fanstack_predict_engine.py — Sovereign Degenerate Syndicate Prediction Exchange Engine
Wires Cockpit /api/predict into live Emergent Society Engine (Port 8098 / emergent_society.db).
Target Size: <= 350 lines (Invariant 50 Compliance).
"""
import os, json, sqlite3, logging, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("fanstack_predict_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_PATH = Path("/home/james/stacklabs/data/emergent_society.db")
SOCIETY_API_URL = "http://127.0.0.1:8098"
INITIAL_BANKROLL_CENTS = 100000  # $1,000.00 base bankroll
VFS_ROOT = Path("/dev/shm/faas_vfs")
VFS_STATE_FILE = VFS_ROOT / "predict_state.json"
VFS_OPCODE_FILE = VFS_ROOT / "chaos_center" / "degen_sentiment_opcode.txt"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def query_society_api(endpoint: str) -> Optional[Dict[str, Any]]:
    """Attempts to query the running Emergent Society daemon on Port 8098."""
    url = f"{SOCIETY_API_URL}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FanStackPredictEngine/2.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Direct API call to {url} failed ({e}); falling back to local DB.")
    return None


def load_market_state() -> Dict[str, Any]:
    """Builds unified /api/predict/state response from living Emergent Society engine.
    VFS-Native Fast-Path: queries local SQLite WAL on NVMe first (<1ms),
    with volatile /dev/shm/ VFS memory fallback and optional Port 8098 fallback.
    """
    citizens_data: List[Dict[str, Any]] = []
    contracts_data: List[Dict[str, Any]] = []
    trades_data: List[Dict[str, Any]] = []

    # 1. Fast-Path: Query local SQLite WAL directly on NVMe (<1ms)
    if DB_PATH.exists():
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM emergent_citizens ORDER BY systolic_bp DESC")
                citizens_data = [dict(r) for r in cur.fetchall()]
                cur.execute("SELECT * FROM market_contracts WHERE status = 'OPEN'")
                contracts_data = [dict(r) for r in cur.fetchall()]
                cur.execute("""
                    SELECT t.trade_id, c.name as citizen, m.ticker, t.side, 
                           t.position_type, t.quantity, t.price_cents, t.total_cost, t.timestamp
                    FROM citizen_trades t
                    JOIN emergent_citizens c ON t.citizen_id = c.citizen_id
                    JOIN market_contracts m ON t.contract_id = m.contract_id
                    ORDER BY t.timestamp DESC LIMIT 20
                """)
                trades_data = [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"Direct SQLite query failed ({e}); falling back to VFS memory/API.")

    # 2. Fall back to volatile VFS memory cache if SQLite failed or returned empty
    if (not citizens_data or not contracts_data) and VFS_STATE_FILE.exists():
        try:
            cached = json.loads(VFS_STATE_FILE.read_text(encoding="utf-8"))
            if cached.get("advocates_bankrolls") and cached.get("contracts"):
                return cached
        except Exception as e:
            logger.debug(f"VFS state cache read failed: {e}")

    # 3. Fall back to Port 8098 API if both DB and VFS memory had missing data
    if not citizens_data or not contracts_data or not trades_data:
        api_citizens = query_society_api("/api/society/citizens")
        api_market = query_society_api("/api/society/market")
        if api_citizens and "citizens" in api_citizens and not citizens_data:
            citizens_data = api_citizens["citizens"]
        if api_market:
            if not contracts_data:
                contracts_data = api_market.get("contracts", [])
            if not trades_data:
                trades_data = api_market.get("recent_trades", [])

    # 4. Transform Citizens into Advocate Bankrolls Schema
    advocates_bankrolls: Dict[str, Any] = {}
    sorted_citizens = sorted(
        citizens_data,
        key=lambda c: float(c.get("portfolio_value", 0.0)) + float(c.get("cash_balance", 0.0)),
        reverse=True
    )
    for rank, c in enumerate(sorted_citizens, 1):
        cid = (c.get("handle") or c.get("citizen_id") or "").lstrip("@").lower().replace("-", "_")
        cash_cents = int(round(float(c.get("cash_balance", 1000.0)) * 100))
        pos_val_cents = int(round(float(c.get("portfolio_value", 0.0)) * 100))
        net_worth_cents = cash_cents + pos_val_cents
        superstition = (c.get("trigger") or c.get("scars") or "Grounded Sports Superstition")[:87]
        advocates_bankrolls[cid] = {
            "name": c.get("name", "Unknown Citizen"),
            "avatar_tag": f"{c.get('archetype', 'Advocate')} • {c.get('fandom', 'Fan')}",
            "rank": rank, "cash_cents": cash_cents, "portfolio_value_cents": net_worth_cents,
            "profit_loss_cents": net_worth_cents - INITIAL_BANKROLL_CENTS,
            "active_superstition": superstition, "systolic_bp": c.get("systolic_bp", 120),
            "tums_today": c.get("tums_consumed_today", 0), "status": c.get("status", "WATCHING"),
            "positions": []
        }

    # 5. Transform Contracts into Cockpit Schema
    contracts: List[Dict[str, Any]] = []
    for k in contracts_data:
        yes_price = int(k.get("current_price_cents", 50))
        no_price = max(1, 100 - yes_price)
        contracts.append({
            "id": k.get("contract_id", ""),
            "ticker": k.get("ticker", "$PREDICT"),
            "category": k.get("category", "SICKO_EXCHANGE"),
            "question": k.get("name") or k.get("description", "Binary Event Contract"),
            "resolution_criteria": k.get("description", "Verified on metal via sports ground truth"),
            "status": k.get("status", "OPEN"),
            "yes_price_cents": yes_price, "no_price_cents": no_price,
            "volume_contracts": int(k.get("total_volume", 0)), "liquidity_pool_cents": int(k.get("open_interest", 500)) * 100,
            "lead_advocate_side": {
                "advocate": k.get("creator_citizen_id", "syndicate"),
                "side": "YES" if yes_price >= 50 else "NO",
                "superstition": f"Implied probability: {yes_price}% based on live biometrics"
            }
        })

    # 6. Transform Recent Trades Tape
    recent_trades = [{
        "trade_id": t.get("trade_id", "TRD-UNKNOWN"),
        "advocate": t.get("citizen") or t.get("citizen_id", "Advocate"),
        "ticker": t.get("ticker", "$SICKO"),
        "action": f"{t.get('side', 'BUY')} {t.get('position_type', 'LONG')}",
        "shares": int(t.get("quantity", 10)),
        "price_cents": int(t.get("price_cents", 50)),
        "total_cost": float(t.get("total_cost", 5.0)),
        "superstition_note": t.get("superstition_note") or "Executed under hemodynamic tilt",
        "timestamp": t.get("timestamp", datetime.now(timezone.utc).isoformat())
    } for t in trades_data]

    # 7. 4-Byte Sentiment Opcode from VFS fast-plane
    sentiment_opcode = "NORM"
    if VFS_OPCODE_FILE.exists():
        try:
            sentiment_opcode = VFS_OPCODE_FILE.read_text(encoding="utf-8").strip()[:4]
        except Exception:
            pass

    state = {
        "market_title": "The FanStack Syndicate // Local Predict Exchange",
        "season": 2026,
        "engine_status": "LIVE_EMERGENT_SOCIETY",
        "sentiment_opcode": sentiment_opcode,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "advocates_bankrolls": advocates_bankrolls,
        "bankrolls": advocates_bankrolls,
        "contracts": contracts,
        "recent_trades": recent_trades
    }

    # Merge dynamic slate contracts and weather feed from /dev/shm/vfs/predict/exchange_state.json if available
    dynamic_state_file = Path("/dev/shm/vfs/predict/exchange_state.json")
    if dynamic_state_file.exists():
        try:
            dyn = json.loads(dynamic_state_file.read_text(encoding="utf-8"))
            if dyn.get("weather_feed"):
                state["weather_feed"] = dyn["weather_feed"]
            if dyn.get("contracts"):
                state["contracts"] = dyn["contracts"]
                state["active_contracts_count"] = len(dyn["contracts"])
            if dyn.get("advocates"):
                state["advocates"] = dyn["advocates"]
            if dyn.get("total_liquidity"):
                state["total_liquidity"] = dyn["total_liquidity"]
        except Exception:
            pass

    # Atomically sync volatile VFS cache
    try:
        VFS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_vfs = VFS_STATE_FILE.with_suffix(".tmp")
        tmp_vfs.write_text(json.dumps(state), encoding="utf-8")
        tmp_vfs.replace(VFS_STATE_FILE)
    except Exception as e:
        logger.debug(f"VFS state cache sync failed: {e}")

    return state


def execute_trade(advocate_id: str, contract_id: str, side: str, shares: int, superstition_note: str = "") -> Dict[str, Any]:
    """Executes an order directly against emergent_society.db."""
    side = side.upper().strip()
    if side not in ("YES", "NO"):
        raise ValueError(f"Invalid side '{side}'. Must be 'YES' or 'NO'.")
    if shares <= 0:
        raise ValueError(f"Shares must be positive integer, got {shares}")

    with get_db_connection() as conn:
        cur = conn.cursor()
        clean_cid = contract_id.strip()
        clean_ticker = f"${clean_cid.lstrip('$')}"
        cur.execute("SELECT * FROM market_contracts WHERE (contract_id = ? OR ticker = ? OR ticker = ?) AND status = 'OPEN'", (clean_cid, clean_cid, clean_ticker))
        contract = cur.fetchone()
        if not contract:
            raise ValueError(f"Active contract '{contract_id}' not found.")

        adv_clean = advocate_id.lower().strip().lstrip("@")
        cur.execute("""SELECT * FROM emergent_citizens WHERE LOWER(citizen_id) = ? OR LOWER(REPLACE(citizen_id, '-', '_')) = ? 
                       OR LOWER(REPLACE(handle, '@', '')) = ? OR LOWER(name) LIKE ?""", (adv_clean, adv_clean, adv_clean, f"%{adv_clean}%"))
        citizen = cur.fetchone()
        if not citizen:
            cur.execute("SELECT * FROM emergent_citizens WHERE citizen_id = 'CIT-000-PILOT'")
            citizen = cur.fetchone()
            if not citizen:
                cur.execute("""INSERT OR IGNORE INTO emergent_citizens (citizen_id, handle, name, archetype, fandom, cash_balance, portfolio_value, systolic_bp, diastolic_bp, status)
                               VALUES ('CIT-000-PILOT', '@pilot', 'Pilot (Cockpit Architect)', 'Lead Systems Architect', 'StackLabs / FaaS', 10000.0, 0.0, 118, 78, 'WATCHING')""")
                conn.commit()
                cur.execute("SELECT * FROM emergent_citizens WHERE citizen_id = 'CIT-000-PILOT'")
                citizen = cur.fetchone()

        citizen_id = citizen["citizen_id"] if citizen else "CIT-000-PILOT"
        citizen_name = citizen["name"] if citizen else "Pilot (Direct Order)"
        price = contract["current_price_cents"] if side == "YES" else max(1, 100 - contract["current_price_cents"])
        total_cost = (shares * price) / 100.0
        trade_id = f"TRD-{os.urandom(4).hex().upper()}"
        pos_type = "LONG" if side == "YES" else "SHORT"

        conn.execute("""INSERT INTO citizen_trades (trade_id, citizen_id, contract_id, side, position_type, quantity, price_cents, total_cost, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                     (trade_id, citizen_id, contract["contract_id"], "BUY", pos_type, shares, price, total_cost))
        conn.execute("UPDATE market_contracts SET total_volume = total_volume + ?, open_interest = open_interest + ? WHERE contract_id = ?",
                     (shares, shares, contract["contract_id"]))
        if citizen and citizen["cash_balance"] >= total_cost:
            conn.execute("UPDATE emergent_citizens SET cash_balance = cash_balance - ?, portfolio_value = portfolio_value + ? WHERE citizen_id = ?",
                         (total_cost, total_cost, citizen_id))
        conn.commit()
        return {
            "status": "EXECUTED", "success": True,
            "trade": {
                "trade_id": trade_id, "citizen": citizen_name, "contract_id": contract["contract_id"],
                "ticker": contract["ticker"], "side": side, "shares": shares, "price_cents": price,
                "total_cost": total_cost, "superstition": superstition_note or "Direct Pilot Action from Cockpit"
            }
        }


def resolve_contract(contract_id: str, outcome: str) -> Dict[str, Any]:
    """Resolves an open contract as 'YES' or 'NO'."""
    outcome = outcome.upper().strip()
    if outcome not in ("YES", "NO"):
        raise ValueError(f"Invalid outcome '{outcome}'. Must be 'YES' or 'NO'.")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM market_contracts WHERE contract_id = ? OR ticker = ?", (contract_id.strip(), contract_id.strip()))
        contract = cur.fetchone()
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")
        new_status = f"RESOLVED_{outcome}"
        conn.execute("UPDATE market_contracts SET status = ?, current_price_cents = ?, resolution = ?, settled_at = CURRENT_TIMESTAMP WHERE contract_id = ?",
                     (new_status, 100 if outcome == "YES" else 0, outcome, contract["contract_id"]))
        conn.commit()
        return {"status": "RESOLVED", "success": True, "contract_id": contract["contract_id"], "ticker": contract["ticker"], "outcome": outcome}


def register_flask_routes(app):
    """Register /api/predict routes on a Flask application."""
    from flask import request, jsonify

    @app.route("/api/predict/state", methods=["GET"])
    def flask_predict_state():
        try:
            return jsonify(load_market_state())
        except Exception as e:
            logger.error(f"Error in /api/predict/state: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/predict/trade", methods=["POST"])
    def flask_predict_trade():
        data = request.get_json(force=True, silent=True) or {}
        advocate, contract_id, side = data.get("advocate", "pilot"), data.get("contract_id"), data.get("side")
        shares, superstition = data.get("shares", 0), data.get("superstition", "")
        if not contract_id or not side or not shares:
            return jsonify({"error": "Missing required fields: contract_id, side, shares"}), 400
        try:
            return jsonify(execute_trade(advocate, contract_id, side, int(shares), superstition))
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/predict/resolve", methods=["POST"])
    def flask_predict_resolve():
        data = request.get_json(force=True, silent=True) or {}
        contract_id, outcome = data.get("contract_id"), data.get("outcome")
        if not contract_id or not outcome:
            return jsonify({"error": "Missing contract_id or outcome"}), 400
        try:
            return jsonify(resolve_contract(contract_id, outcome))
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500


def get_fastapi_router():
    """Register /api/predict APIRouter on a FastAPI application."""
    try:
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        router = APIRouter(prefix="/api/predict", tags=["Predict"])

        class TradeReq(BaseModel):
            advocate: str = "pilot"
            contract_id: str
            side: str
            shares: int
            superstition: Optional[str] = ""

        class ResolveReq(BaseModel):
            contract_id: str
            outcome: str

        @router.get("/state")
        def api_state():
            try:
                return load_market_state()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/trade")
        def api_trade(req: TradeReq):
            try:
                return execute_trade(req.advocate, req.contract_id, req.side, req.shares, req.superstition or "")
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/resolve")
        def api_resolve(req: ResolveReq):
            try:
                return resolve_contract(req.contract_id, req.outcome)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return router
    except Exception as e:
        logger.warning(f"FastAPI router unavailable: {e}")
        return None


if __name__ == "__main__":
    state = load_market_state()
    print(f"Loaded live simulation state: {len(state['advocates_bankrolls'])} citizens, {len(state['contracts'])} contracts, {len(state['recent_trades'])} trades.")
