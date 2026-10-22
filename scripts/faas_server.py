#!/usr/bin/env python3
"""
FANSTACK LITE // FAAS MOBILE UTILITY — BACKEND & STATIC RUNNER
Path: /home/james/stacklabs/scripts/fanstack_lite_server.py
Port: 3033 (faas_server.service)

Lightweight Mobile Utility running on Clio local host.
Decoupled from legacy 15_FanStack watch party monolith.
Adheres strictly to Invariant 24 (Lightweight info only: Stream sniper, 3-bullet brief, quick takes).
"""

import asyncio
import hashlib
import os
import re
import subprocess
import sys
import json
import shlex
import urllib.request
import urllib.error
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field
from google import genai

SNIPES_DIR = Path("/home/james/stacklabs/data/snipes")
SNIPES_CACHE_DIR = SNIPES_DIR / "cache"
SNIPES_DIR.mkdir(parents=True, exist_ok=True)
SNIPES_CACHE_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = "/home/james/stacklabs"
STATIC_DIR = os.path.join(PROJECT_ROOT, "apps", "faas", "dist")


# --- WO0011251 DYNAMIC LOOKBOOK & BROADCAST SEARCH HELPERS ---
def _resolve_latest_lookbook_pdf() -> Path:
    search_dirs = [
        Path("/home/james/stacklabs/pilot_drops"),
        Path("/home/james/stacklabs/data/lookbooks"),
        Path("/home/james/stacklabs/reports"),
        Path("/home/james/stacklabs"),
    ]
    candidates = []
    for d in search_dirs:
        if d.exists():
            candidates.extend(d.glob("*LOOKBOOK*.pdf"))
            candidates.extend(d.glob("*lookbook*.pdf"))
    if not candidates:
        raise FileNotFoundError("No lookbook PDF files found in canonical directories.")
    candidates.sort(key=lambda p: (p.name, p.stat().st_mtime), reverse=True)
    return candidates[0]
# --- END WO0011251 HELPERS ---

app = FastAPI(
    title="FAAS MOBILE UTILITY CONSOLE",
    description="Mobile-first lightweight stream sniper, 3-bullet brief, and advocate takes on Port 3033",
    version="1.0.0"
)

import logging
logger = logging.getLogger("faas_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount FaaS Deranged Kalshi Prediction Market API Router
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.fanstack_predict_engine import get_fastapi_router
    predict_router = get_fastapi_router()
    if predict_router:
        app.include_router(predict_router)
        logger.info("Mounted Deranged Kalshi Prediction Market router on /api/predict")
except Exception as e:
    logger.error(f"Failed to mount predict router: {e}")

# Mount Tell Sniper Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.tell_sniper import tell_sniper_bp
    app.include_router(tell_sniper_bp)
    logger.info("Mounted Tell Sniper router on /api/snipe_tell")
except Exception as e:
    logger.error(f"Failed to mount tell_sniper router: {e}")

# Mount decoupled Stream Sniper and Field Notes blueprints (WO0011252)
try:
    from scripts.blueprints.stream_sniper_bp import stream_sniper_bp
    app.include_router(stream_sniper_bp)
    logger.info("Mounted decoupled Stream Sniper router on /api/snipe")
except Exception as e:
    logger.warning(f"Could not mount stream sniper blueprint: {e}")

try:
    from scripts.blueprints.field_notes_bp import field_notes_bp
    app.include_router(field_notes_bp)
    logger.info("Mounted decoupled Field Notes router on /field-notes")
except Exception as e:
    logger.warning(f"Could not mount field notes blueprint: {e}")

# Mount CMDB Benchmark Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.cmdb_benchmark_api import cmdb_benchmark_bp
    app.include_router(cmdb_benchmark_bp)
    logger.info("Mounted CMDB Benchmark router on /api/benchmark")
except Exception as e:
    logger.error(f"Failed to mount cmdb_benchmark router: {e}")

# Mount CMDB Session Ingest Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.cmdb_session_ingest_api import cmdb_session_bp
    app.include_router(cmdb_session_bp)
    logger.info("Mounted CMDB Session Ingest router on /api/cmdb")
except Exception as e:
    logger.error(f"Failed to mount cmdb_session router: {e}")

# Mount Santa Anita Four Pillars Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.santa_anita_blueprint import router as santa_anita_router
    app.include_router(santa_anita_router)
    logger.info("Mounted Santa Anita Four Pillars router on /api/vfs/santa_anita")
except Exception as e:
    logger.error(f"Failed to mount santa_anita router: {e}")

# Mount VFS Telemetry Fast-Path Blueprint (WO0011031 Dogfood & WO0011212 Lexicon Bursts)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.faas_vfs_telemetry import (
        get_body_bags_payload,
        router as vfs_telemetry_bp,
        faas_lexicon_router,
        get_active_slate_games,
    )
    app.include_router(vfs_telemetry_bp)
    app.include_router(faas_lexicon_router)
    try:
        from scripts.blueprints.faas_carnage_telemetry import router as carnage_router
        app.include_router(carnage_router)
        logger.info("Mounted CFB Carnage Telemetry router on /api/faas/cfb")
    except Exception as e:
        logger.error(f"Failed to mount carnage_router: {e}")
    app.add_api_route("/api/faas/slate/active_games", get_active_slate_games, methods=["GET", "HEAD"])
    # === WO0011233_FAAS_BODY_BAGS_ROOT_ROUTE ===
    app.add_api_route("/api/faas/body_bags", get_body_bags_payload, methods=["GET", "HEAD"])
    logger.info("Mounted Toe-Tag Body Bags route on /api/faas/body_bags")

    logger.info("Mounted VFS Telemetry & Lexicon Bursts routers on /api/vfs_telemetry, /api/faas/lexicon, and /api/faas/slate/active_games")
except Exception as e:
    logger.error(f"Failed to mount vfs_telemetry router: {e}")

# Mount Hardened Recursive VFS Layout Engine Router
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.vfs_recursive_router import router as vfs_recursive_router
    app.include_router(vfs_recursive_router)
    logger.info("Mounted Hardened Recursive VFS Layout Engine router on /api/vfs/recursive")
except Exception as e:
    logger.error(f"Failed to mount vfs_recursive_router: {e}")

# Mount Swanson Crawl VFS Wiki Knowledge Explorer Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.vfs_wiki_api import vfs_wiki_bp
    app.include_router(vfs_wiki_bp)
    logger.info("Successfully mounted vfs_wiki_bp on /api/wiki")
except Exception as e:
    logger.error(f"Failed mounting vfs_wiki_bp: {e}")

# Mount ACP Detail Supply B2B Parts & Dilution Oracle Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.acp_oracle_api import acp_oracle_bp
    app.include_router(acp_oracle_bp)
    logger.info("Successfully mounted acp_oracle_bp on /api/acp")
except Exception as e:
    logger.error(f"Failed mounting acp_oracle_bp: {e}")

@app.middleware("http")
async def acp_subdomain_root_router(request: Request, call_next):
    host = request.headers.get("host", "").lower()
    if "acp-demo.stacklabsllc.com" in host and request.url.path == "/":
        from scripts.blueprints.acp_oracle_api import render_acp_live_demo
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=render_acp_live_demo(), status_code=200)
    return await call_next(request)

# Mount Bleacher Provocateur Hot-Take Ledger Blueprint
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.hot_take_ledger_api import hot_take_ledger_bp
    app.include_router(hot_take_ledger_bp)
    logger.info("Successfully mounted hot_take_ledger_bp on /api/provocateur")
except Exception as e:
    logger.error(f"Failed mounting hot_take_ledger_bp: {e}")

# Mount Causal Stream Tail Replay Studio & Dual-Pane Inspector Blueprint (WO0011188)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.stream_tail_replay import router as stream_tail_router
    app.include_router(stream_tail_router)
    logger.info("Successfully mounted stream_tail_router on /api/stream_tail/replay and /stream_tail")
except Exception as e:
    logger.error(f"Failed mounting stream_tail_router: {e}")

# Mount Barf On-Demand Hot Take API Blueprint (WO0011191)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.barf_hot_take_api import router as barf_router
    app.include_router(barf_router)
    logger.info("Successfully mounted barf_router on /api/barf")
except Exception as e:
    logger.error(f"Failed mounting barf_router: {e}")

# Mount CMDB Companion Oracle Blueprint (WO0011194)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.cmdb_companion_oracle_api import router as companion_oracle_router
    app.include_router(companion_oracle_router)
    logger.info("Successfully mounted companion_oracle_router on /api/companion")
except Exception as e:
    logger.error(f"Failed mounting companion_oracle_router: {e}")

@app.get("/api/snipe/{snipe_id}/time_machine")
def serve_vfs_snipe_time_machine(snipe_id: str):
    from scripts.vfs_snipe_time_machine import VFS_SNIPES, DATA_SNIPES, build_snipe_time_machine
    import json
    for base in (VFS_SNIPES, DATA_SNIPES):
        p = base / snipe_id / "time_machine.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return build_snipe_time_machine(snipe_id)

# Mount FaaS Time Machine Blueprint (WO0011280)
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.blueprints.faas_time_machine_bp import router as faas_time_machine_router
    app.include_router(faas_time_machine_router)
    logger.info("Mounted FaaS Time Machine router on /api/snipe/{id}/time_machine")
except Exception as e:
    logger.error(f"Failed to mount faas_time_machine_router: {e}")

# Import Broadcast Engine
try:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from scripts.broadcast_intelligence_engine import BroadcastIntelligenceEngine
    broadcast_engine = BroadcastIntelligenceEngine()
    logger.info("Initialized BroadcastIntelligenceEngine for /api/broadcast/query")
except Exception as e:
    logger.warning(f"Failed to load broadcast_intelligence_engine: {e}")
    broadcast_engine = None

# ---------------------------------------------------------------------------
# API ROUTES & STARTUP
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def setup_3033_forwarder():
    """Binds 127.0.0.1:3033 via asyncio stream server and proxies to 127.0.0.1:3032 without leaking threads or sockets."""
    async def handle_proxy(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        target_writer = None
        try:
            target_reader, target_writer = await asyncio.open_connection('127.0.0.1', 3032)
        except Exception as e:
            logger.warning(f"Failed to connect to 127.0.0.1:3032 upstream: {e}")
            client_writer.close()
            await client_writer.wait_closed()
            return

        async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            try:
                while not reader.at_eof():
                    data = await reader.read(65536)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except Exception:
                pass
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        try:
            await asyncio.gather(
                forward(client_reader, target_writer),
                forward(target_reader, client_writer),
                return_exceptions=True
            )
        finally:
            for w in (client_writer, target_writer):
                if w:
                    try:
                        w.close()
                        await w.wait_closed()
                    except Exception:
                        pass

    try:
        server = await asyncio.start_server(handle_proxy, '127.0.0.1', 3033, reuse_address=True)
        asyncio.create_task(server.serve_forever())
        logger.info("Bound 127.0.0.1:3033 forwarder -> 127.0.0.1:3032 via asyncio")
    except Exception as e:
        logger.info(f"Port 3033 forwarder not started (likely already bound): {e}")

@app.api_route("/api/health", methods=["GET", "HEAD"])
def healthcheck():
    """Healthcheck endpoint for Pegasus sentry and monitoring."""
    return {
        "status": "ok",
        "service": "FANSTACK LITE // FAAS MOBILE UTILITY",
        "port": 3033,
        "host": "clio",
        "aesthetic": "The Daily Barf Void (#0B0D13)",
        "invariant": "Invariant 24 Compliant (Lightweight Info Only)",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.api_route("/api/broadcast/query", methods=["GET", "HEAD"])
def query_broadcast_telemetry(q: str = Query(...), date: Optional[str] = Query(None), show: str = Query("mcafee")):
    if not broadcast_engine:
        raise HTTPException(status_code=503, detail="Broadcast intelligence engine unavailable")
    res = broadcast_engine.search(query=q, date_str=date, show=show)
    return JSONResponse(res)

@app.api_route("/api/lookbook/latest.pdf", methods=["GET", "HEAD"])
def get_latest_lookbook_pdf():
    try:
        latest_pdf = _resolve_latest_lookbook_pdf()
        if latest_pdf.exists():
            return FileResponse(latest_pdf, media_type="application/pdf", filename=latest_pdf.name)
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Lookbook PDF not found")

# SnipeRequest and /api/snipe decoupled to scripts.blueprints.stream_sniper_bp (WO0011252)

@app.get("/api/hourly-stats")
@app.get("/mcafee_hourly_stats.json")
def get_hourly_stats():
    """Serves real-time decoupled hourly stats payload (Invariant 25)."""
    candidates = [
        "/home/james/stacklabs_inbox/today/mcafee_hourly_stats.json",
        os.path.join(PROJECT_ROOT, "apps", "faas", "public", "mcafee_hourly_stats.json"),
        os.path.join(STATIC_DIR, "mcafee_hourly_stats.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return FileResponse(c, media_type="application/json")
    raise HTTPException(status_code=404, detail="Hourly stats payload not found")

@app.get("/api/alpha_trader_stats")
@app.get("/FanStack_Live/alpha_trader_stats.json")
def get_alpha_trader_stats():
    """Serves real-time decoupled alpha trader payload (Invariant 25)."""
    candidates = [
        "/home/james/stacklabs_inbox/today/alpha_trader_stats.json",
        os.path.join(PROJECT_ROOT, "apps", "faas", "public", "FanStack_Live", "alpha_trader_stats.json"),
        os.path.join(STATIC_DIR, "FanStack_Live", "alpha_trader_stats.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return FileResponse(c, media_type="application/json")
    raise HTTPException(status_code=404, detail="Alpha trader stats payload not found")


# ---------------------------------------------------------------------------
# STADIUM VENUES & GROUND TRUTH GEOGRAPHY
# ---------------------------------------------------------------------------
STADIUM_VENUES_FILE = Path("/home/james/stacklabs/ground_truth/stadium_venues.json")
_stadium_venues_cache: Dict[str, Any] = {}

def load_stadium_venues() -> Dict[str, Any]:
    global _stadium_venues_cache
    if not _stadium_venues_cache and STADIUM_VENUES_FILE.exists():
        try:
            with open(STADIUM_VENUES_FILE, "r") as f:
                data = json.load(f)
                _stadium_venues_cache = data.get("venues", {})
        except Exception as e:
            logger.warning(f"Failed to load stadium venues: {e}")
    return _stadium_venues_cache

load_stadium_venues()


_SUPPLEMENTAL_VENUES: Dict[str, Dict[str, Any]] = {
    "MIZ_CFB": {"venue_name": "Memorial Stadium / Faurot Field", "city": "Columbia", "state": "MO", "roof": "open", "surface": "turf", "elevation_ft": 700},
    "UNC_CFB": {"venue_name": "Kenan Memorial Stadium", "city": "Chapel Hill", "state": "NC", "roof": "open", "surface": "turf", "elevation_ft": 500},
    "CWS_MLB": {"venue_name": "Guaranteed Rate Field", "city": "Chicago", "state": "IL", "roof": "open", "surface": "grass", "elevation_ft": 595},
    "CHC_MLB": {"venue_name": "Wrigley Field", "city": "Chicago", "state": "IL", "roof": "open", "surface": "grass", "elevation_ft": 600},
    "TB_MLB": {"venue_name": "Tropicana Field", "city": "St. Petersburg", "state": "FL", "roof": "dome", "surface": "turf", "elevation_ft": 45},
}


def resolve_venue(team_abbrev: str, sport: str = "cfb", raw_venue_name: Optional[str] = None) -> Dict[str, Any]:
    """O(1) memory lookup for canonical FanStackVenuePhysics ground-truth geography, roof, surface, and elevation."""
    venues = {**_SUPPLEMENTAL_VENUES, **load_stadium_venues()}
    clean_team = re.sub(r"^#\d+\s+", "", (team_abbrev or "").strip()).split(" ")[-1].upper()
    sport_lower = (sport or "cfb").lower()
    alt_team = "WAS" if (clean_team == "WSH" and sport_lower == "nfl") else clean_team

    entry = None
    sport_key = f"{clean_team}_{sport_lower.upper()}"
    if sport_key in venues:
        entry = venues[sport_key]
    else:
        for candidate in (clean_team, alt_team):
            if candidate in venues and str(venues[candidate].get("sport", "")).lower() == sport_lower:
                entry = venues[candidate]
                break
        if not entry and clean_team in venues:
            entry = venues[clean_team]

    cleaned_raw = _normalize_venue_name(raw_venue_name or ("Ballpark" if sport_lower == "mlb" else "Stadium"))
    if not entry and raw_venue_name:
        raw_lower = cleaned_raw.lower()
        for v in venues.values():
            v_name = str(v.get("venue_name", "")).lower()
            if v_name and (v_name in raw_lower or raw_lower in v_name):
                entry = v
                break

    if entry:
        return {
            "venue_name": _normalize_venue_name(entry.get("venue_name", cleaned_raw)),
            "city": str(entry.get("city", "")),
            "state": str(entry.get("state", "")),
            "roof": str(entry.get("roof", "open")),
            "surface": str(entry.get("surface", "grass" if sport_lower == "mlb" else "turf")),
            "elevation_ft": int(entry.get("elevation_ft", 0) or 0),
        }

    return {
        "venue_name": cleaned_raw,
        "city": "",
        "state": "",
        "roof": "open",
        "surface": "grass" if sport_lower == "mlb" else "turf",
        "elevation_ft": 0,
    }


@app.get("/api/venues")
def get_venues():
    """Returns canonical stadium venues ground truth registry."""
    return {"count": len(_stadium_venues_cache), "venues": _stadium_venues_cache}


@app.get("/api/venues/{team}")
def get_venue_by_team(team: str, sport: str = Query("nfl")):
    """Returns canonical FanStackVenuePhysics details for a given team code or zip code."""
    venues = {**_SUPPLEMENTAL_VENUES, **load_stadium_venues()}
    clean = team.strip().upper()
    for venue_data in venues.values():
        if venue_data.get("zip_code") == clean or venue_data.get("team", "").upper() == clean:
            return resolve_venue(venue_data.get("team", clean), sport=venue_data.get("sport", sport))
    raise HTTPException(status_code=404, detail=f"Venue for team '{team}' not found")


# ---------------------------------------------------------------------------
# CANONICAL `FanStackGameEvent` DATA CONTRACT & SINGLE-PASS NORMALIZER
# ---------------------------------------------------------------------------
class FanStackGameClock(BaseModel):
    period: int = Field(..., ge=0, description="Inning (1-9+) or Quarter (1-4, OT=5+)")
    period_name: str = Field(..., description="'Inning', 'Quarter', or 'Overtime'")
    display_clock: str = Field(..., description="'Top 3rd', '12:45', '00:00'")
    is_intermission: bool = Field(default=False, description="Halftime, 7th-inning stretch, pitching change")


class FanStackTeamNode(BaseModel):
    code: str = Field(..., description="Clean team code: 'MIL', 'SEA', 'UGA'")
    full_name: str = Field(..., description="Full team name: 'Milwaukee Brewers'")
    score: int = Field(default=0, ge=0)
    rank: Optional[int] = Field(default=None, ge=1, le=25)
    logo_url: str = Field(..., description="Official team logo URL")


class FanStackBettingOdds(BaseModel):
    spread: str = Field(..., description="'DEN -3.5', 'LAD -1.5'")
    over_under: float = Field(..., gt=0, description="44.5, 7.5")
    moneyline_away: Optional[int] = None
    moneyline_home: Optional[int] = None


class FanStackVenuePhysics(BaseModel):
    venue_name: str
    city: str = ""
    state: str = ""
    roof: str = "open"
    surface: str = "grass"
    elevation_ft: int = 0


class FanStackTimestamps(BaseModel):
    scheduled_start_iso: str
    last_updated_iso: str


class FanStackGameEvent(BaseModel):
    """Authoritative Unified PolySport Event Contract for MLB, NFL, and NCAA FBS (CFB)."""

    id: str = Field(..., description="${sport}_${raw_id}")
    sport: str = Field(..., description="mlb | nfl | cfb")
    name: Optional[str] = None
    league: str = Field(..., description="MLB | NFL | CFB")
    status: str = Field(..., description="SCHEDULED | WARMUP | LIVE | FINAL | POSTPONED")
    status_detail: str
    clock: FanStackGameClock
    away_team: FanStackTeamNode
    home_team: FanStackTeamNode
    odds: Optional[FanStackBettingOdds] = None
    venue: FanStackVenuePhysics
    timestamps: FanStackTimestamps

    def to_clean_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(exclude_none=True)
        return self.dict(exclude_none=True)

    @classmethod
    def from_json(cls, raw_json: str) -> "FanStackGameEvent":
        if hasattr(cls, "model_validate_json"):
            return cls.model_validate_json(raw_json)
        return cls.parse_raw(raw_json)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FanStackGameEvent":
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)
        return cls.parse_obj(data)


polysport_slate_cache: Dict[str, Any] = {"timestamp": 0.0, "data": []}
mlb_schedule_cache = polysport_slate_cache  # Alias retained for blueprint compatibility
cfb_live_cache: Dict[str, Any] = {}

_MLB_ABBR_LOOKUP: Dict[str, str] = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK", "Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD",
    "San Francisco Giants": "SF", "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB", "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
}
_MLB_CODE_TO_FULL: Dict[str, str] = {v: k for k, v in _MLB_ABBR_LOOKUP.items() if k != "Athletics"}
_MLB_TEAM_IDS: Dict[str, int] = {
    "ARI": 109, "ATL": 144, "BAL": 110, "BOS": 111, "CHC": 112, "CWS": 145,
    "CIN": 113, "CLE": 114, "COL": 115, "DET": 116, "HOU": 117, "KC": 118,
    "LAA": 108, "LAD": 119, "MIA": 146, "MIL": 158, "MIN": 142, "NYM": 121,
    "NYY": 147, "OAK": 133, "PHI": 143, "PIT": 134, "SD": 135, "SF": 137,
    "SEA": 136, "STL": 138, "TB": 139, "TEX": 140, "TOR": 141, "WSH": 120,
}
_NFL_CODE_TO_FULL: Dict[str, str] = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders", "WSH": "Washington Commanders",
}


def _utc_now_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_et_clock(iso_str: str) -> str:
    if not iso_str:
        return "SCHEDULED"
    try:
        import zoneinfo
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_et = dt.astimezone(zoneinfo.ZoneInfo("America/New_York"))
        hr = dt_et.strftime("%I").lstrip("0") or "12"
        return f"{hr}:{dt_et.strftime('%M %p %Z')}"
    except Exception:
        return iso_str


def _normalize_single_pass_event(raw_item: Dict[str, Any], sport: str) -> Optional[FanStackGameEvent]:
    """Single-pass normalizer converting raw MLB StatsAPI or ESPN NFL/CFB JSON into FanStackGameEvent."""
    now_iso = _utc_now_iso()
    sport_norm = sport.lower().strip()

    if sport_norm == "mlb":
        raw_pk = str(raw_item.get("gamePk") or raw_item.get("id") or "").replace("mlb_", "").strip()
        if not raw_pk:
            return None
        teams = raw_item.get("teams", {})
        away_node = teams.get("away", {})
        home_node = teams.get("home", {})
        away_t = away_node.get("team", {})
        home_t = home_node.get("team", {})

        away_name = str(away_t.get("name") or raw_item.get("away_team") or "Away")
        home_name = str(home_t.get("name") or raw_item.get("home_team") or "Home")
        away_code = str(away_t.get("abbreviation") or _MLB_ABBR_LOOKUP.get(away_name) or away_name[:3]).upper()
        home_code = str(home_t.get("abbreviation") or _MLB_ABBR_LOOKUP.get(home_name) or home_name[:3]).upper()
        away_full = _MLB_CODE_TO_FULL.get(away_code, away_name)
        home_full = _MLB_CODE_TO_FULL.get(home_code, home_name)
        if {away_code, home_code} == {"CLE", "TB"} or "Cleveland Guardians" in (away_full, home_full) or "Tampa Bay Rays" in (away_full, home_full):
            return None

        ls = raw_item.get("linescore", {}) or {}
        away_score = int(away_node.get("score") if away_node.get("score") is not None else ls.get("teams", {}).get("away", {}).get("runs", 0) or 0)
        home_score = int(home_node.get("score") if home_node.get("score") is not None else ls.get("teams", {}).get("home", {}).get("runs", 0) or 0)

        st_obj = raw_item.get("status", {})
        detailed = str(st_obj.get("detailedState", "Scheduled") if isinstance(st_obj, dict) else st_obj)
        abstract = str(st_obj.get("abstractGameState", "") if isinstance(st_obj, dict) else "")
        coded = str(st_obj.get("codedGameState", "") if isinstance(st_obj, dict) else "")
        det_lower = detailed.lower()
        sched_iso = str(raw_item.get("gameDate") or now_iso)

        if any(k in det_lower for k in ("postponed", "suspended", "cancelled", "canceled")):
            status = "POSTPONED"
        elif detailed in ("Final", "Game Over", "Completed Early") or abstract == "Final" or coded == "F":
            status = "FINAL"
        elif detailed == "Warmup" or "warmup" in det_lower:
            status = "WARMUP"
        elif detailed in ("In Progress", "Manager Challenge", "Umpire Review", "Pitching Change", "Delayed") or abstract == "Live":
            status = "LIVE"
        else:
            status = "SCHEDULED"

        inn_num = int(ls.get("currentInning", 0) or (9 if status == "FINAL" else 1))
        inn_ord = str(ls.get("currentInningOrdinal") or _format_inning_ordinal(inn_num))
        inn_state = str(ls.get("inningState") or ls.get("inningHalf") or "Top").strip()
        outs = ls.get("outs")
        is_intermission = inn_state.lower() in ("middle", "mid", "end") or "pitching change" in det_lower

        if status == "FINAL":
            display_clock = f"FINAL/{inn_num}" if inn_num > 9 else "FINAL"
            status_detail = display_clock
        elif status == "POSTPONED":
            display_clock = "POSTPONED"
            status_detail = "POSTPONED"
        elif status == "LIVE":
            half_lbl = "Mid" if inn_state.lower() == "middle" else ("Bot" if inn_state.lower() == "bottom" else inn_state)
            display_clock = f"{half_lbl} {inn_ord}".strip()
            if outs is not None and not is_intermission:
                status_detail = f"{display_clock} ({int(outs)} {'out' if int(outs) == 1 else 'outs'})"
            else:
                status_detail = display_clock
        elif status == "WARMUP":
            et_str = _format_et_clock(sched_iso)
            display_clock = et_str
            status_detail = f"WARMUP • {et_str}" if et_str != "SCHEDULED" else "WARMUP"
        else:
            et_str = _format_et_clock(sched_iso)
            display_clock = et_str
            status_detail = et_str

        away_tid = away_t.get("id") or _MLB_TEAM_IDS.get(away_code)
        home_tid = home_t.get("id") or _MLB_TEAM_IDS.get(home_code)
        away_logo = f"https://www.mlbstatic.com/team-logos/{away_tid}.svg" if away_tid else f"https://a.espncdn.com/i/teamlogos/mlb/500/{away_code.lower()}.png"
        home_logo = f"https://www.mlbstatic.com/team-logos/{home_tid}.svg" if home_tid else f"https://a.espncdn.com/i/teamlogos/mlb/500/{home_code.lower()}.png"

        venue_dict = resolve_venue(home_code, sport="mlb", raw_venue_name=raw_item.get("venue", {}).get("name"))
        odds_raw = raw_item.get("odds")
        odds_model = FanStackBettingOdds(**odds_raw) if isinstance(odds_raw, dict) and odds_raw.get("spread") and odds_raw.get("over_under") else None

        return FanStackGameEvent(
            id=f"mlb_{raw_pk}",
            sport="mlb",
            league="MLB",
            status=status,
            status_detail=status_detail,
            clock=FanStackGameClock(
                period=inn_num,
                period_name="Inning",
                display_clock=display_clock,
                is_intermission=is_intermission,
            ),
            away_team=FanStackTeamNode(code=away_code, full_name=away_full, score=away_score, logo_url=away_logo),
            home_team=FanStackTeamNode(code=home_code, full_name=home_full, score=home_score, logo_url=home_logo),
            odds=odds_model,
            venue=FanStackVenuePhysics(**venue_dict),
            timestamps=FanStackTimestamps(scheduled_start_iso=sched_iso, last_updated_iso=now_iso),
        )

    raw_id = str(raw_item.get("id") or "").replace(f"{sport_norm}_", "").strip()
    if not raw_id:
        return None
    comp = (raw_item.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []
    home = next((c for c in competitors if c.get("homeAway") == "home"), {}) or {}
    away = next((c for c in competitors if c.get("homeAway") == "away"), {}) or {}
    h_team = home.get("team") or {}
    a_team = away.get("team") or {}

    h_code = re.sub(r"^#\d+\s+", "", str(h_team.get("abbreviation") or h_team.get("location") or "HME").strip()).upper()[:6]
    a_code = re.sub(r"^#\d+\s+", "", str(a_team.get("abbreviation") or a_team.get("location") or "AWY").strip()).upper()[:6]
    h_full = str(h_team.get("displayName") or (_NFL_CODE_TO_FULL.get(h_code) if sport_norm == "nfl" else None) or h_team.get("name") or h_code)
    a_full = str(a_team.get("displayName") or (_NFL_CODE_TO_FULL.get(a_code) if sport_norm == "nfl" else None) or a_team.get("name") or a_code)

    h_score = int(home.get("score", 0) or 0)
    a_score = int(away.get("score", 0) or 0)

    h_rank: Optional[int] = None
    a_rank: Optional[int] = None
    if sport_norm == "cfb":
        hr_val = home.get("curatedRank", {}).get("current", 99)
        ar_val = away.get("curatedRank", {}).get("current", 99)
        if isinstance(hr_val, int) and 1 <= hr_val <= 25:
            h_rank = hr_val
        if isinstance(ar_val, int) and 1 <= ar_val <= 25:
            a_rank = ar_val

    st_obj = raw_item.get("status") or comp.get("status") or {}
    st_type = st_obj.get("type") or {}
    state = str(st_type.get("state") or "pre").lower()
    completed = bool(st_type.get("completed", False))
    detail_raw = str(st_type.get("detail") or st_type.get("shortDetail") or "Scheduled")
    short_detail = str(st_type.get("shortDetail") or detail_raw)
    det_lower = detail_raw.lower()
    period_num = int(st_obj.get("period", 0) or 0)
    raw_clock = str(st_obj.get("displayClock") or "00:00")
    sched_iso = str(raw_item.get("date") or comp.get("date") or now_iso)

    if any(k in det_lower for k in ("postponed", "canceled", "cancelled", "suspended")):
        status = "POSTPONED"
    elif state == "post" or completed or "final" in det_lower:
        status = "FINAL"
    elif state == "in":
        status = "LIVE"
    elif "warmup" in det_lower or "pre-game" in det_lower:
        status = "WARMUP"
    else:
        status = "SCHEDULED"

    is_intermission = any(k in det_lower for k in ("halftime", "half time", "end of"))
    period_name = "Overtime" if period_num >= 5 else "Quarter"

    if status == "FINAL":
        period_num = max(period_num, 4)
        display_clock = "00:00"
        status_detail = "FINAL/OT" if period_num >= 5 else "FINAL"
    elif status == "POSTPONED":
        display_clock = "00:00"
        status_detail = "POSTPONED"
    elif status == "LIVE":
        period_num = max(period_num, 1)
        if is_intermission:
            display_clock = "HALFTIME" if "half" in det_lower else short_detail
            status_detail = display_clock
        else:
            q_lbl = f"OT{period_num - 4}" if period_num > 5 else ("OT" if period_num == 5 else f"Q{period_num}")
            display_clock = raw_clock or short_detail
            status_detail = f"{q_lbl} {raw_clock}".strip() if raw_clock else short_detail
    else:
        period_num = 1
        if " at " in detail_raw:
            status_detail = detail_raw.split(" at ")[-1].strip()
        else:
            status_detail = _format_et_clock(sched_iso)
        display_clock = status_detail

    odds_list = comp.get("odds") or []
    odds_obj = odds_list[0] if odds_list and isinstance(odds_list[0], dict) else {}
    spread_str = str(odds_obj.get("details") or "").strip()
    ou_val = odds_obj.get("overUnder")
    odds_model: Optional[FanStackBettingOdds] = None
    if spread_str and ou_val is not None:
        try:
            ml_a = odds_obj.get("awayTeamOdds", {}).get("moneyLine")
            ml_h = odds_obj.get("homeTeamOdds", {}).get("moneyLine")
            odds_model = FanStackBettingOdds(
                spread=spread_str,
                over_under=float(ou_val),
                moneyline_away=int(ml_a) if ml_a is not None else None,
                moneyline_home=int(ml_h) if ml_h is not None else None,
            )
        except (ValueError, TypeError):
            odds_model = None

    venue_dict = resolve_venue(h_code, sport=sport_norm, raw_venue_name=comp.get("venue", {}).get("fullName"))
    logo_slug = "ncaa" if sport_norm == "cfb" else "nfl"
    a_logo = str(a_team.get("logo") or f"https://a.espncdn.com/i/teamlogos/{logo_slug}/500/{a_code.lower()}.png")
    h_logo = str(h_team.get("logo") or f"https://a.espncdn.com/i/teamlogos/{logo_slug}/500/{h_code.lower()}.png")

    return FanStackGameEvent(
        id=f"{sport_norm}_{raw_id}",
        sport=sport_norm,
        name=f"{a_full} at {h_full} ({a_code} @ {h_code})",
        league=sport_norm.upper(),
        status=status,
        status_detail=status_detail,
        clock=FanStackGameClock(
            period=period_num,
            period_name=period_name,
            display_clock=display_clock,
            is_intermission=is_intermission,
        ),
        away_team=FanStackTeamNode(code=a_code, full_name=a_full, score=a_score, rank=a_rank, logo_url=a_logo),
        home_team=FanStackTeamNode(code=h_code, full_name=h_full, score=h_score, rank=h_rank, logo_url=h_logo),
        odds=odds_model,
        venue=FanStackVenuePhysics(**venue_dict),
        timestamps=FanStackTimestamps(scheduled_start_iso=sched_iso, last_updated_iso=now_iso),
    )


def fetch_unified_polysport_slate(
    sport_filter: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """Single-pass normalizer aggregating MLB, NFL, and CFB schedules into pure FanStackGameEvent models."""
    now = time.time()
    filter_norm = sport_filter.lower().strip() if (isinstance(sport_filter, str) and sport_filter) else "all"

    if not force_refresh and now - polysport_slate_cache["timestamp"] < 5.0 and polysport_slate_cache["data"]:
        cached = polysport_slate_cache["data"]
        if filter_norm in ("mlb", "nfl", "cfb"):
            return [g for g in cached if g.get("sport") == filter_norm]
        return cached

    import zoneinfo
    from datetime import timedelta

    eastern = zoneinfo.ZoneInfo("America/New_York")
    now_eastern = datetime.now(eastern)
    today_str = now_eastern.strftime("%Y-%m-%d")
    yesterday_str = (now_eastern - timedelta(days=1)).strftime("%Y-%m-%d")

    sources = [
        ("mlb", f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={yesterday_str}&endDate={today_str}&hydrate=linescore,team"),
        ("nfl", "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"),
        ("cfb", "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&limit=100"),
    ]

    events_by_id: Dict[str, FanStackGameEvent] = {}

    for sport_key, url in sources:
        if filter_norm not in ("all", sport_key):
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FanStack-PolySport/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                if sport_key == "mlb":
                    for d_block in payload.get("dates", []):
                        for g_raw in d_block.get("games", []):
                            ev = _normalize_single_pass_event(g_raw, "mlb")
                            if ev:
                                events_by_id[ev.id] = ev
                else:
                    for ev_raw in payload.get("events", []):
                        ev = _normalize_single_pass_event(ev_raw, sport_key)
                        if ev:
                            events_by_id[ev.id] = ev
        except Exception as exc:
            logger.warning("Upstream %s schedule fetch warning: %s", sport_key.upper(), exc)

    # Fallback 1: Read from canonical SQLite WAL table `fanstack_unified_schedule`
    if not events_by_id:
        try:
            import sqlite3
            db_candidates = [
                Path(os.environ.get("FANSTACK_DB_PATH", "/home/james/stacklabs/dna/fanstack_schedule.db")),
                Path("/home/james/stacklabs/dna/fanstack_now.db"),
            ]
            for db_p in db_candidates:
                if db_p.exists():
                    conn = sqlite3.connect(f"file:{db_p}?mode=ro", uri=True, timeout=5.0)
                    cur = conn.cursor()
                    cur.execute("SELECT event_json FROM fanstack_unified_schedule")
                    for (ev_json,) in cur.fetchall():
                        ev = FanStackGameEvent.from_json(ev_json)
                        events_by_id[ev.id] = ev
                    conn.close()
                    if events_by_id:
                        break
        except Exception as db_exc:
            logger.debug("SQLite WAL fallback read skipped: %s", db_exc)

    # Fallback 2: Hydrate from canonical Ground Truth Registry (`sports_ground_truth.json`)
    if not events_by_id:
        try:
            from sync_polysport_schedule import load_ground_truth_fallback_events
            for ev in load_ground_truth_fallback_events(sport_filter=filter_norm):
                events_by_id[ev.id] = FanStackGameEvent.from_dict(ev.to_clean_dict())
        except Exception:
            pass

    status_priority = {"LIVE": 0, "SCHEDULED": 1, "UPCOMING": 1, "WARMUP": 2, "FINAL": 3, "POSTPONED": 4}
    sport_priority = {"cfb": 0, "nfl": 1, "mlb": 2}

    sorted_events = sorted(
        events_by_id.values(),
        key=lambda e: (
            status_priority.get(e.status, 5),
            e.timestamps.scheduled_start_iso,
            sport_priority.get(e.sport, 9),
            e.id,
        ),
    )

    unified_dicts = [ev.to_clean_dict() for ev in sorted_events]

    if not unified_dicts and polysport_slate_cache["data"]:
        cached = polysport_slate_cache["data"]
        if filter_norm in ("mlb", "nfl", "cfb"):
            return [g for g in cached if g.get("sport") == filter_norm]
        return cached

    try:
        vfs_sched_dir = Path("/dev/shm/vfs/schedule")
        vfs_sched_dir.mkdir(parents=True, exist_ok=True)
        (vfs_sched_dir / "unified_slate.json").write_text(json.dumps(unified_dicts, indent=2), encoding="utf-8")
    except Exception:
        pass

    if filter_norm == "all":
        polysport_slate_cache["timestamp"] = now
        polysport_slate_cache["data"] = unified_dicts

    if filter_norm in ("mlb", "nfl", "cfb"):
        return [g for g in unified_dicts if g.get("sport") == filter_norm]
    return unified_dicts


@app.get("/api/polysport/slate")
@app.get("/api/schedule")
@app.get("/api/mlb/schedule")
def get_mlb_schedule(sport: Optional[str] = Query(None)):
    """Returns canonical unified FanStackGameEvent slate across MLB, NFL, and CFB with 5-second cache."""
    return fetch_unified_polysport_slate(sport_filter=sport)


@app.get("/api/cfb/scores")
def get_cfb_scores():
    """Returns normalized College Football FanStackGameEvent schedule."""
    return fetch_unified_polysport_slate(sport_filter="cfb")


@app.get("/api/cfb/live/{game_id}")
def get_cfb_live_data(game_id: str):
    """Fetches live down, distance, possession, yardline, and last play from ESPN event summary."""
    now = time.time()
    clean_id = game_id.replace("cfb_", "").strip()
    if clean_id in cfb_live_cache and now - cfb_live_cache[clean_id]["timestamp"] < 3.0:
        return cfb_live_cache[clean_id]["data"]

    url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={clean_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FanStack/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            header = data.get("header", {})
            comp = header.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})

            drives = data.get("drives", {})
            prev_drives = drives.get("previous", []) or []
            curr_drive = drives.get("current", {}) or {}
            
            all_raw_plays = []
            for d in prev_drives:
                for p in (d.get("plays") or []):
                    all_raw_plays.append(p)
            for p in (curr_drive.get("plays") or []):
                all_raw_plays.append(p)

            last_play_obj = all_raw_plays[-1] if all_raw_plays else {}
            last_play_text = last_play_obj.get("text", "No plays yet")

            # Extract full play-by-play chronological history (up to 40 most recent plays)
            play_list = []
            for p in all_raw_plays[-40:]:
                period_num = p.get("period", {}).get("number", 1)
                clock_val = p.get("clock", {}).get("displayValue", "")
                play_list.append({
                    "id": str(p.get("id") or f"p_{time.time()}_{len(play_list)}"),
                    "clock": clock_val,
                    "periodText": f"Q{period_num}",
                    "description": p.get("text", ""),
                    "isScoringPlay": bool(p.get("scoringPlay", False)),
                    "scoreAfterPlay": {
                        "away": int(p.get("awayScore", away.get("score", 0)) or 0),
                        "home": int(p.get("homeScore", home.get("score", 0)) or 0)
                    }
                })

            sit = comp.get("situation", {})
            down = sit.get("down", 1)
            distance = sit.get("distance", 10)
            yardline = sit.get("yardLine", 50)
            possession_id = sit.get("possession")
            possession_text = sit.get("possessionText", "")
            down_dist_text = sit.get("shortDownDistanceText") or sit.get("downDistanceText", "")
            yards_to_endzone = sit.get("yardsToEndzone")

            if last_play_obj:
                end_st = last_play_obj.get("end", {})
                if (not sit or not sit.get("down")) and end_st.get("down"):
                    down = end_st.get("down", 1)
                    distance = end_st.get("distance", 10)
                    yardline = end_st.get("yardLine", 50)
                    possession_id = end_st.get("team", {}).get("id")
                if not possession_text:
                    possession_text = end_st.get("possessionText", "")
                if not down_dist_text:
                    down_dist_text = end_st.get("shortDownDistanceText") or end_st.get("downDistanceText", "")
                if yards_to_endzone is None:
                    yards_to_endzone = end_st.get("yardsToEndzone")

            home_abbrev = home.get("team", {}).get("abbreviation", "HME")
            away_abbrev = away.get("team", {}).get("abbreviation", "AWY")

            if str(possession_id) == str(home.get("id")):
                poss_team = home_abbrev
            elif str(possession_id) == str(away.get("id")):
                poss_team = away_abbrev
            else:
                poss_team = away_abbrev

            status_type = comp.get("status", {}).get("type", {})
            clock_detail = status_type.get("detail", "")

            result = {
                "gameId": f"cfb_{clean_id}",
                "rawGameId": clean_id,
                "awayTeam": away_abbrev,
                "homeTeam": home_abbrev,
                "awayScore": int(away.get("score", 0) or 0),
                "homeScore": int(home.get("score", 0) or 0),
                "down": down,
                "distance": distance,
                "yardline": yardline,
                "yardsToEndzone": yards_to_endzone,
                "possession": poss_team,
                "possessionText": possession_text,
                "lastPlay": last_play_text,
                "downDistanceText": down_dist_text or f"{down} & {distance}",
                "clock": clock_detail,
                "status": status_type.get("description", "Scheduled"),
                "playByPlay": play_list
            }
            cfb_live_cache[clean_id] = {"timestamp": now, "data": result}
            return result
    except Exception as e:
        logger.warning(f"Failed to fetch CFB live data for {clean_id}: {e}")
        if clean_id in cfb_live_cache:
            return cfb_live_cache[clean_id]["data"]
        raise HTTPException(status_code=502, detail=f"Failed to fetch CFB live data: {e}")

mlb_cache: Dict[str, Any] = {}

def _format_inning_ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def _normalize_venue_name(raw_name: str) -> str:
    if not raw_name:
        return "Ballpark"
    cleaned = re.sub(r"^UNIQLO Field at\s+", "", raw_name, flags=re.IGNORECASE).strip()
    if "dodger stadium" in cleaned.lower():
        return "Dodger Stadium"
    return cleaned

@app.get("/api/mlb/live/{game_pk}")
def get_mlb_live_data(game_pk: str):
    """Fetches and normalizes official MLB Gameday live data with 3-second memory cache."""
    now = time.time()
    clean_pk = str(game_pk).replace("mlb_", "").strip()
    if clean_pk in mlb_cache and now - mlb_cache[clean_pk]["timestamp"] < 3.0:
        return mlb_cache[clean_pk]["data"]

    url = f"https://statsapi.mlb.com/api/v1.1/game/{clean_pk}/feed/live"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FanStack/2.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = json.loads(response.read().decode("utf-8"))
            
            ls = raw.get("liveData", {}).get("linescore", {})
            current_play = raw.get("liveData", {}).get("plays", {}).get("currentPlay", {})
            matchup = current_play.get("matchup", {})
            count = current_play.get("count", {})
            play_events = current_play.get("playEvents", [])
            last_pitch_event = next((e for e in reversed(play_events) if e.get("isPitch")), {})
            
            # Format innings
            innings_list = []
            for inn in ls.get("innings", []):
                innings_list.append({
                    "num": inn.get("num"),
                    "away": inn.get("away", {}).get("runs", 0),
                    "home": inn.get("home", {}).get("runs", 0)
                })

            # Format plays & pre-compute scoring play RBI credits by batter ID
            all_plays_raw = raw.get("liveData", {}).get("plays", {}).get("allPlays", [])
            play_rbi_by_batter: Dict[int, int] = {}
            for p in all_plays_raw:
                b_id = p.get("matchup", {}).get("batter", {}).get("id")
                res = p.get("result", {})
                ev_name = res.get("event", "")
                p_rbi = int(res.get("rbi", 0) or 0)
                if ev_name == "Home Run" and p_rbi == 0:
                    scoring_runners = [r for r in p.get("runners", []) if r.get("details", {}).get("isScoringEvent")]
                    p_rbi = max(1, len(scoring_runners))
                if b_id and p_rbi > 0:
                    play_rbi_by_batter[int(b_id)] = play_rbi_by_batter.get(int(b_id), 0) + p_rbi

            formatted_plays = []
            for p in reversed(all_plays_raw):
                about = p.get("about", {})
                result = p.get("result", {})
                desc = result.get("description")
                half_cap = about.get("halfInning", "").capitalize()
                inn_num = int(about.get("inning", 1) or 1)
                inn_label = f"{half_cap} {_format_inning_ordinal(inn_num)}".strip()

                if desc:
                    ev_name = result.get("event", "Play")
                    p_rbi = int(result.get("rbi", 0) or 0)
                    if ev_name == "Home Run" and p_rbi == 0:
                        p_rbi = 1
                    is_scoring = bool(
                        about.get("isScoringPlay")
                        or p_rbi > 0
                        or (result.get("isOut") is False and ("scores" in desc.lower() or "homers" in desc.lower()))
                    )
                    formatted_plays.append({
                        "id": f"play-{about.get('atBatIndex', len(formatted_plays))}",
                        "inning": half_cap,
                        "inningNum": inn_num,
                        "inningLabel": inn_label,
                        "event": ev_name,
                        "description": desc,
                        "rbi": p_rbi,
                        "isScoring": is_scoring
                    })

                # Also surface mid-at-bat scoring action events (e.g., Wild Pitch / Passed Ball / Balk scoring a runner)
                for idx_ev, ev in enumerate(reversed(p.get("playEvents", []))):
                    ev_det = ev.get("details", {})
                    ev_desc = ev_det.get("description") or ""
                    ev_type = ev_det.get("event") or ""
                    if ev_type and ("scores" in ev_desc.lower()) and ev_desc != desc:
                        formatted_plays.append({
                            "id": f"play-{about.get('atBatIndex', 0)}-ev-{idx_ev}",
                            "inning": half_cap,
                            "inningNum": inn_num,
                            "inningLabel": inn_label,
                            "event": ev_type,
                            "description": ev_desc,
                            "rbi": 0,
                            "isScoring": True
                        })

            # Helper to resolve batter AVG and OPS from seasonStats first, with hits/atBats dynamic fallback
            def _resolve_avg_ops(p_obj: Dict[str, Any]) -> tuple[str, str]:
                st_b = p_obj.get("stats", {}).get("batting", {})
                sst_b = p_obj.get("seasonStats", {}).get("batting", {})
                hits_val = int(st_b.get("hits", 0) or 0)
                ab_val = int(st_b.get("atBats", 0) or 0)
                avg_str = sst_b.get("avg") or st_b.get("avg") or ".000"
                if (not avg_str or avg_str in (".000", "0.000", ".---", "-.--")) and hits_val > 0 and ab_val > 0:
                    ratio = hits_val / ab_val
                    avg_str = f"{ratio:.3f}".lstrip("0") if ratio < 1.0 else f"{ratio:.3f}"
                ops_str = sst_b.get("ops") or st_b.get("ops") or ".000"
                if (not ops_str or ops_str in (".000", "0.000", ".---", "-.--")) and hits_val > 0 and ab_val > 0:
                    bb_val = int(st_b.get("baseOnBalls", 0) or 0)
                    hbp_val = int(st_b.get("hitByPitch", 0) or 0)
                    sf_val = int(st_b.get("sacFlies", 0) or 0)
                    tb_val = int(st_b.get("totalBases", hits_val) or hits_val)
                    pa_denom = ab_val + bb_val + hbp_val + sf_val
                    obp_v = (hits_val + bb_val + hbp_val) / pa_denom if pa_denom > 0 else (hits_val / ab_val)
                    slg_v = tb_val / ab_val if ab_val > 0 else 0.0
                    ops_v = obp_v + slg_v
                    ops_str = f"{ops_v:.3f}".lstrip("0") if ops_v < 1.0 else f"{ops_v:.3f}"
                return avg_str, ops_str

            def _build_team_batters(team_box: Dict[str, Any]) -> List[Dict[str, Any]]:
                players_map = team_box.get("players", {})
                ordered_entries = []
                for p_id in team_box.get("batters", []):
                    p = players_map.get(f"ID{p_id}", {})
                    bo_raw = p.get("battingOrder")
                    if not bo_raw:
                        continue
                    try:
                        bo_int = int(bo_raw)
                    except (ValueError, TypeError):
                        bo_int = 9999
                    ordered_entries.append((bo_int, int(p_id), p))
                ordered_entries.sort(key=lambda item: item[0])

                rows = []
                for bo_int, pid_int, p in ordered_entries:
                    st = p.get("stats", {}).get("batting", {})
                    avg_str, ops_str = _resolve_avg_ops(p)
                    raw_rbi = int(st.get("rbi", 0) or 0)
                    hr_cnt = int(st.get("homeRuns", 0) or 0)
                    final_rbi = max(raw_rbi, play_rbi_by_batter.get(pid_int, 0), hr_cnt)
                    is_sub = (bo_int % 100) != 0
                    rows.append({
                        "name": p.get("person", {}).get("fullName", "Unknown"),
                        "pos": p.get("position", {}).get("abbreviation", ""),
                        "ab": int(st.get("atBats", 0) or 0),
                        "r": int(st.get("runs", 0) or 0),
                        "h": int(st.get("hits", 0) or 0),
                        "rbi": final_rbi,
                        "bb": int(st.get("baseOnBalls", 0) or 0),
                        "k": int(st.get("strikeOuts", 0) or 0),
                        "avg": avg_str,
                        "ops": ops_str,
                        "battingOrder": str(bo_int),
                        "isSub": is_sub
                    })
                return rows

            def _build_team_totals(team_box: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
                t_bat = team_box.get("teamStats", {}).get("batting", {})
                return {
                    "ab": int(t_bat.get("atBats", sum(r["ab"] for r in rows)) or 0),
                    "r": int(t_bat.get("runs", sum(r["r"] for r in rows)) or 0),
                    "h": int(t_bat.get("hits", sum(r["h"] for r in rows)) or 0),
                    "rbi": int(t_bat.get("rbi", sum(r["rbi"] for r in rows)) or 0),
                    "bb": int(t_bat.get("baseOnBalls", sum(r["bb"] for r in rows)) or 0),
                    "k": int(t_bat.get("strikeOuts", sum(r["k"] for r in rows)) or 0),
                    "avg": t_bat.get("avg", ".000"),
                    "ops": t_bat.get("ops", ".000")
                }

            # Format boxscore
            box = raw.get("liveData", {}).get("boxscore", {}).get("teams", {})
            away_batters = _build_team_batters(box.get("away", {}))
            home_batters = _build_team_batters(box.get("home", {}))
            away_totals = _build_team_totals(box.get("away", {}), away_batters)
            home_totals = _build_team_totals(box.get("home", {}), home_batters)

            # Pitcher stats (lookup across both away and home players)
            pitcher_id = matchup.get("pitcher", {}).get("id")
            pitcher_stats = {}
            if pitcher_id:
                away_players = box.get("away", {}).get("players", {})
                home_players = box.get("home", {}).get("players", {})
                if f"ID{pitcher_id}" in away_players:
                    p_box = away_players[f"ID{pitcher_id}"]
                    p_team_box = box.get("away", {})
                else:
                    p_box = home_players.get(f"ID{pitcher_id}", {})
                    p_team_box = box.get("home", {})
                p_st = p_box.get("stats", {}).get("pitching", {})
                p_sst = p_box.get("seasonStats", {}).get("pitching", {})
                team_era = p_team_box.get("teamStats", {}).get("pitching", {}).get("era", "0.00")
                era_str = p_sst.get("era") or p_st.get("era") or team_era or "0.00"
                if era_str in ("0.00", "-.--", ".---") and team_era and team_era not in ("0.00", "-.--"):
                    era_str = team_era
                pitcher_stats = {
                    "ip": p_st.get("inningsPitched", "0.0"),
                    "k": p_st.get("strikeOuts", 0),
                    "era": era_str,
                    "pitches": p_st.get("numberOfPitches", 0),
                    "strikes": p_st.get("strikes", 0)
                }

            # Batter stats (lookup across both away and home players)
            batter_id = matchup.get("batter", {}).get("id")
            batter_stats = {}
            if batter_id:
                b_box = (
                    box.get("away", {}).get("players", {}).get(f"ID{batter_id}")
                    or box.get("home", {}).get("players", {}).get(f"ID{batter_id}")
                    or {}
                )
                b_st = b_box.get("stats", {}).get("batting", {})
                b_avg, b_ops = _resolve_avg_ops(b_box)
                b_raw_rbi = int(b_st.get("rbi", 0) or 0)
                b_hr = int(b_st.get("homeRuns", 0) or 0)
                b_final_rbi = max(b_raw_rbi, play_rbi_by_batter.get(int(batter_id), 0), b_hr)
                batter_stats = {
                    "ab": b_st.get("atBats", 0),
                    "r": b_st.get("runs", 0),
                    "h": b_st.get("hits", 0),
                    "rbi": b_final_rbi,
                    "k": b_st.get("strikeOuts", 0),
                    "avg": b_avg,
                    "ops": b_ops
                }

            status_obj = raw.get("gameData", {}).get("status", {})
            raw_status = status_obj.get("detailedState", "In Progress")
            abstract_state = status_obj.get("abstractGameState", "")
            coded_state = status_obj.get("codedGameState", "")
            if raw_status in ("Game Over", "Final", "Completed Early") or abstract_state == "Final" or coded_state == "F":
                clean_status = "Final"
            elif raw_status in ("Pre-Game", "Warmup"):
                clean_status = "Warmup"
            else:
                clean_status = raw_status

            away_abbrev = raw.get("gameData", {}).get("teams", {}).get("away", {}).get("abbreviation", "AWY")
            home_abbrev = raw.get("gameData", {}).get("teams", {}).get("home", {}).get("abbreviation", "HME")
            away_w = int(raw.get("gameData", {}).get("teams", {}).get("away", {}).get("record", {}).get("leagueRecord", {}).get("wins", 0) or 0)
            home_w = int(raw.get("gameData", {}).get("teams", {}).get("home", {}).get("record", {}).get("leagueRecord", {}).get("wins", 0) or 0)
            if away_w > home_w:
                series_status_str = f"SERIES: {away_abbrev} {away_w} - {home_w} {home_abbrev}"
            elif home_w > away_w:
                series_status_str = f"SERIES: {home_abbrev} {home_w} - {away_w} {away_abbrev}"
            else:
                series_status_str = f"SERIES TIED: {away_abbrev} {away_w} - {home_w} {home_abbrev}"

            decisions_raw = raw.get("liveData", {}).get("decisions", {})
            wp_name = decisions_raw.get("winner", {}).get("fullName")
            lp_name = decisions_raw.get("loser", {}).get("fullName")
            sv_name = decisions_raw.get("save", {}).get("fullName")
            dec_parts = []
            if wp_name:
                dec_parts.append(f"WP: {wp_name}")
            if lp_name:
                dec_parts.append(f"LP: {lp_name}")
            if sv_name:
                dec_parts.append(f"SV: {sv_name}")
            decisions_summary = " • ".join(dec_parts)

            clean_venue = _normalize_venue_name(raw.get("gameData", {}).get("venue", {}).get("name", "Ballpark"))

            normalized = {
                "gamePk": f"mlb_{clean_pk}",
                "gameStatus": clean_status,
                "venue": clean_venue,
                "seriesStatus": series_status_str,
                "decisions": {
                    "winner": wp_name,
                    "loser": lp_name,
                    "save": sv_name,
                    "summary": decisions_summary
                },
                "linescore": {
                    "currentInning": ls.get("currentInningOrdinal", "1st"),
                    "inningState": ls.get("inningState", "Top"),
                    "isTopInning": ls.get("isTopInning", True),
                    "away": {
                        "team": away_abbrev,
                        "runs": ls.get("teams", {}).get("away", {}).get("runs", 0),
                        "hits": ls.get("teams", {}).get("away", {}).get("hits", 0),
                        "errors": ls.get("teams", {}).get("away", {}).get("errors", 0)
                    },
                    "home": {
                        "team": home_abbrev,
                        "runs": ls.get("teams", {}).get("home", {}).get("runs", 0),
                        "hits": ls.get("teams", {}).get("home", {}).get("hits", 0),
                        "errors": ls.get("teams", {}).get("home", {}).get("errors", 0)
                    },
                    "innings": innings_list
                },
                "currentMatchup": {
                    "pitcher": {
                        "name": matchup.get("pitcher", {}).get("fullName", "Pitcher"),
                        "hand": matchup.get("pitchHand", {}).get("code", "RHP"),
                        **pitcher_stats
                    },
                    "batter": {
                        "name": matchup.get("batter", {}).get("fullName", "Batter"),
                        "pos": current_play.get("matchup", {}).get("batter", {}).get("position", "DH"),
                        **batter_stats
                    },
                    "count": {
                        "balls": 0 if clean_status == "Final" else count.get("balls", 0),
                        "strikes": 0 if clean_status == "Final" else count.get("strikes", 0),
                        "outs": 3 if clean_status == "Final" else count.get("outs", 0)
                    },
                    "runners": {
                        "onFirst": False if clean_status == "Final" else bool(ls.get("offense", {}).get("first") or current_play.get("matchup", {}).get("postOnFirst")),
                        "onSecond": False if clean_status == "Final" else bool(ls.get("offense", {}).get("second") or current_play.get("matchup", {}).get("postOnSecond")),
                        "onThird": False if clean_status == "Final" else bool(ls.get("offense", {}).get("third") or current_play.get("matchup", {}).get("postOnThird"))
                    },
                    "lastPitch": {
                        "speed": last_pitch_event.get("pitchData", {}).get("startSpeed", "---"),
                        "type": last_pitch_event.get("details", {}).get("type", {}).get("description", "Pitch"),
                        "result": last_pitch_event.get("details", {}).get("description", "---")
                    },
                    "seriesStatus": series_status_str,
                    "decisions": decisions_summary
                },
                "plays": formatted_plays,
                "boxscore": {
                    "away": away_batters,
                    "home": home_batters,
                    "awayTotals": away_totals,
                    "homeTotals": home_totals
                }
            }

            mlb_cache[clean_pk] = {"timestamp": now, "data": normalized}
            return normalized
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch MLB feed: {str(e)}")

nfl_live_cache: Dict[str, Any] = {}

def fetch_nfl_live_summary(clean_id: str) -> Dict[str, Any]:
    """Fetches live down, distance, possession, yardline, and plays from ESPN NFL summary."""
    now = time.time()
    if clean_id in nfl_live_cache and now - nfl_live_cache[clean_id]["timestamp"] < 3.0:
        return nfl_live_cache[clean_id]["data"]

    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={clean_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "FanStack/2.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    header = data.get("header", {}) or {}
    comp = (header.get("competitions", [{}]) or [{}])[0]
    competitors = comp.get("competitors", []) or []
    home = next((c for c in competitors if c.get("homeAway") == "home"), {}) or {}
    away = next((c for c in competitors if c.get("homeAway") == "away"), {}) or {}

    drives = data.get("drives", {}) or {}
    prev_drives = drives.get("previous", []) or []
    curr_drive = drives.get("current", {}) or {}
    
    all_nfl_plays = []
    for d in prev_drives:
        for p in (d.get("plays") or []):
            all_nfl_plays.append(p)
    for p in (curr_drive.get("plays") or []):
        all_nfl_plays.append(p)
        
    last_play_obj = all_nfl_plays[-1] if all_nfl_plays else {}
    last_play_text = last_play_obj.get("text", "No plays yet")

    sit = comp.get("situation", {}) or {}
    down = sit.get("down", 1)
    distance = sit.get("distance", 10)
    yardline = sit.get("yardLine", 50)
    possession_id = sit.get("possession")
    possession_text = sit.get("possessionText", "")
    down_dist_text = sit.get("shortDownDistanceText") or sit.get("downDistanceText", "")
    yards_to_endzone = sit.get("yardsToEndzone")

    if last_play_obj:
        end_st = last_play_obj.get("end", {}) or {}
        if (not sit or not sit.get("down")) and end_st.get("down"):
            down = end_st.get("down", 1)
            distance = end_st.get("distance", 10)
            yardline = end_st.get("yardLine", 50)
            possession_id = end_st.get("team", {}).get("id")
        if not possession_text:
            possession_text = end_st.get("possessionText", "")
        if not down_dist_text:
            down_dist_text = end_st.get("shortDownDistanceText") or end_st.get("downDistanceText", "")
        if yards_to_endzone is None:
            yards_to_endzone = end_st.get("yardsToEndzone")

    home_abbrev = home.get("team", {}).get("abbreviation", "HME")
    away_abbrev = away.get("team", {}).get("abbreviation", "AWY")

    if str(possession_id) == str(home.get("id")):
        poss_team = home_abbrev
    elif str(possession_id) == str(away.get("id")):
        poss_team = away_abbrev
    else:
        poss_team = curr_drive.get("team", {}).get("abbreviation", away_abbrev)

    status_type = comp.get("status", {}).get("type", {}) or {}
    clock_detail = status_type.get("detail", "")

    play_list = []
    for p in all_nfl_plays[-40:]:
        play_list.append({
            "id": str(p.get("id") or f"p_{time.time()}_{len(play_list)}"),
            "clock": p.get("clock", {}).get("displayValue", ""),
            "periodText": f"Q{p.get('period', {}).get('number', 1)}",
            "description": p.get("text", ""),
            "isScoringPlay": bool(p.get("scoringPlay", False)),
            "scoreAfterPlay": {
                "away": int(p.get("awayScore", away.get("score", 0)) or 0),
                "home": int(p.get("homeScore", home.get("score", 0)) or 0)
            }
        })

    result = {
        "gameId": f"nfl_{clean_id}",
        "rawGameId": clean_id,
        "sport": "nfl",
        "awayTeam": away_abbrev,
        "homeTeam": home_abbrev,
        "awayScore": int(away.get("score", 0) or 0),
        "homeScore": int(home.get("score", 0) or 0),
        "down": down,
        "distance": distance,
        "yardline": yardline,
        "yardsToEndzone": yards_to_endzone,
        "possession": poss_team,
        "possessionText": possession_text,
        "lastPlay": last_play_text,
        "downDistanceText": down_dist_text or f"{down} & {distance}",
        "clock": clock_detail,
        "status": status_type.get("description", "Scheduled"),
        "playByPlay": play_list
    }
    nfl_live_cache[clean_id] = {"timestamp": now, "data": result}
    return result

@app.get("/api/nfl/live/{game_id}")
def get_nfl_live_data(game_id: str):
    clean_id = game_id.replace("nfl_", "").strip()
    try:
        return fetch_nfl_live_summary(clean_id)
    except Exception as e:
        logger.warning(f"Failed to fetch NFL live data for {clean_id}: {e}")
        if clean_id in nfl_live_cache:
            return nfl_live_cache[clean_id]["data"]
        raise HTTPException(status_code=502, detail=f"Failed to fetch NFL live data: {e}")

@app.get("/api/live/{game_id}")
def get_unified_live_game_data(game_id: str):
    """Unified live telemetry gateway for NFL, CFB, and MLB."""
    if game_id.startswith("nfl_"):
        clean_id = game_id.replace("nfl_", "").strip()
        return fetch_nfl_live_summary(clean_id)
    elif game_id.startswith("cfb_"):
        return get_cfb_live_data(game_id)
    elif game_id.startswith("mlb_") or (game_id.isdigit() and len(game_id) == 6):
        clean_id = game_id.replace("mlb_", "").strip()
        return get_mlb_live_data(clean_id)
    else:
        try:
            return get_mlb_live_data(game_id)
        except Exception:
            try:
                return fetch_nfl_live_summary(game_id)
            except Exception:
                return get_cfb_live_data(game_id)

@app.api_route("/api/nfl/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_nfl_api(request: Request, path: str):
    """Transparent proxy forwarding NFL live telemetry requests to SDLC Portal Server."""
    import httpx
    target_url = f"http://127.0.0.1:8095/api/nfl/{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
                params=dict(request.query_params),
                content=body
            )
            try:
                content = resp.json()
                return JSONResponse(status_code=resp.status_code, content=content)
            except Exception:
                return JSONResponse(status_code=resp.status_code, content={"text": resp.text})
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Failed to proxy NFL API: {str(e)}"})


# ---------------------------------------------------------------------------
# IN-MEMORY CROSS-STREAM PROVENANCE CACHE
# ---------------------------------------------------------------------------
_provenance_cache = {}
_provenance_last_mtime = 0

def update_provenance_cache():
    global _provenance_cache, _provenance_last_mtime
    chat_file = "/home/james/stacklabs/data/stream_chat_tail.md"
    if not os.path.exists(chat_file):
        chat_file = "/home/james/stacklabs_inbox/today/stream_chat_tail.md"
    if not os.path.exists(chat_file):
        chat_file = "/home/james/stacklabs/apps/faas/public/FanStack_Live/stream_chat_tail.md" 
    wardy_file = "/home/james/stacklabs_inbox/today/wardy_chat_tail.md"
    
    if not os.path.exists(chat_file):
        return
        
    try:
        mtime = os.path.getmtime(chat_file)
        if mtime == _provenance_last_mtime and _provenance_cache:
            return
            
        cache = {}
        with open(chat_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("[") and "]" in line_str and ("@@@" in line_str or "@@" in line_str):
                    sep = "@@@" if "@@@" in line_str else "@@"
                    parts = line_str.split(sep)
                    ts = parts[0].replace("[", "").replace("]", "").strip()
                    user = parts[1].strip()
                    u_key = user.lower().lstrip("@")
                    if u_key not in cache:
                        cache[u_key] = {"streams": set(), "first_seen": ts, "count": 0}
                    cache[u_key]["streams"].add("game_stream")
                    cache[u_key]["count"] += 1
                elif line_str.startswith("@@") and not line_str.startswith("@@@"):
                    user = line_str.replace("@@", "").strip()
                    u_key = user.lower().lstrip("@")
                    if u_key not in cache:
                        cache[u_key] = {"streams": set(), "first_seen": "12:00:00", "count": 0}
                    cache[u_key]["streams"].add("postgame_stream")
                    cache[u_key]["count"] += 1

        if os.path.exists(wardy_file):
            with open(wardy_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_str = line.strip()
                    if "@@@" in line_str:
                        parts = line_str.split("@@@")
                        ts = parts[0].replace("[", "").replace("]", "").strip() if "[" in parts[0] else "Live"
                        user = parts[1].strip()
                        u_key = user.lower().lstrip("@")
                        if u_key not in cache:
                            cache[u_key] = {"streams": set(), "first_seen": ts, "count": 0}
                        cache[u_key]["streams"].add("wardy_channel")
                        cache[u_key]["count"] += 1
                    elif line_str.startswith("@@") and not line_str.startswith("@@@"):
                        user = line_str.replace("@@", "").strip()
                        u_key = user.lower().lstrip("@")
                        if u_key not in cache:
                            cache[u_key] = {"streams": set(), "first_seen": "Live", "count": 0}
                        cache[u_key]["streams"].add("wardy_channel")
                        cache[u_key]["count"] += 1

        _provenance_cache = cache
        _provenance_last_mtime = mtime
    except Exception as e:
        print(f"Error updating provenance cache: {e}")

@app.get("/api/stream/resolve/{league}/{team_or_game}")
async def proxy_sports_stream_resolve(league: str, team_or_game: str):
    """Proxy stream resolution request to Port 8095 JetExtractors resolver."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://127.0.0.1:8095/api/stream/resolve/{league}/{team_or_game}")
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        try:
            from scripts.sports.resolvers.jetextractors_resolver import JetExtractorsResolver
            resolver = JetExtractorsResolver()
            payload = resolver.resolve(league, team_or_game)
            return {"status": "ok", "payload": payload}
        except Exception as inner_e:
            return JSONResponse(status_code=500, content={"status": "error", "error": f"{e} // fallback failed: {inner_e}"})

@app.get("/api/stream/chat_tail")
@app.get("/api/stream/chat")
def get_stream_chat_tail(limit: int = 40, game_id: Optional[str] = None):
    from scripts.blueprints.faas_vfs_telemetry import get_vfs_chat_tail
    return get_vfs_chat_tail(limit=limit, game_id=game_id)

@app.get("/api/snipe/ticker_feed")
def get_snipe_ticker_feed():
    from scripts.blueprints.faas_vfs_telemetry import get_vfs_ticker_feed
    return get_vfs_ticker_feed(limit=20)

@app.get("/api/stream/game_telemetry")
@app.get("/api/vfs/telemetry")
def get_stream_game_telemetry():
    from scripts.blueprints.faas_vfs_telemetry import get_companion_telemetry_state
    return get_companion_telemetry_state()

@app.get("/api/vfs/synthetic/{filename:path}")
def get_vfs_synthetic_file(filename: str):
    syn_path = Path("/dev/shm/vfs/synthetic") / filename
    if syn_path.exists() and syn_path.is_file():
        try:
            return json.loads(syn_path.read_text(encoding="utf-8"))
        except Exception:
            return PlainTextResponse(syn_path.read_text(encoding="utf-8"))
    if filename == "pegasus_companion_state.json":
        from scripts.blueprints.faas_vfs_telemetry import get_companion_telemetry_state
        return get_companion_telemetry_state()
    raise HTTPException(status_code=404, detail="Synthetic VFS file not found")

@app.get("/api/vfs/predict/state")
def get_vfs_predict_state():
    """Serves real-time advocate bankroll and trade state from VFS (WO0011059)."""
    from scripts.blueprints.faas_vfs_telemetry import get_predict_exchange_state
    return get_predict_exchange_state()


# ---------------------------------------------------------------------------
# BATTLESTATION 1-TAP STREAM INGRESS & TELEMETRY
# ---------------------------------------------------------------------------
ACTIVE_STREAM_TAILS: Dict[str, dict] = {}

class TailStreamRequest(BaseModel):
    game_id: str
    stream_url: str
    channel_name: Optional[str] = None

class TailStreamResponse(BaseModel):
    success: bool
    game_id: str
    stream_id: str
    channel_id: str
    channel_name: str
    status: str
    message: str

def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    clean_input = url_or_id.strip()
    if len(clean_input) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', clean_input):
        return clean_input

    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, clean_input)
        if m:
            return m.group(1)
    return None

@app.post("/api/stream/tail", response_model=TailStreamResponse)
async def tail_stream(request: TailStreamRequest):
    video_id = extract_youtube_video_id(request.stream_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube Live URL or Video ID format.")

    # 1. Resolve teams from active slate
    from scripts.blueprints.faas_vfs_telemetry import _resolve_teams_from_slate
    away_code, home_code = _resolve_teams_from_slate(request.game_id)
    away_val = away_code or "AWAY"
    home_val = home_code or "HOME"
    channel_name = request.channel_name or f"{away_val}@{home_val} LIVE"
    channel_id = f"ch_{video_id[:8]}"

    # 2. Persist into watch_party_streams in morning_wiretap.db
    try:
        import sqlite3
        db_path = "/home/james/stacklabs/data/morning_wiretap.db"
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            cur = conn.cursor()
            today_str = datetime.now().strftime("%Y-%m-%d")
            # Insert for primary game_id
            cur.execute("""
                INSERT OR REPLACE INTO watch_party_streams (sport, game_pk, game_date, home_team, away_team, stream_id, stream_title, stream_url, source, resolved_at, is_live)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'youtube', datetime('now'), 1)
            """, ("cfb" if "cfb" in request.game_id else ("nfl" if "nfl" in request.game_id else "mlb"), request.game_id, today_str, home_val, away_val, video_id, channel_name, f"https://www.youtube.com/watch?v={video_id}"))
            # Insert team slug alias
            if away_code and home_code:
                team_pk = f"{away_code}_{home_code}"
                cur.execute("""
                    INSERT OR REPLACE INTO watch_party_streams (sport, game_pk, game_date, home_team, away_team, stream_id, stream_title, stream_url, source, resolved_at, is_live)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'youtube', datetime('now'), 1)
                """, ("cfb" if "cfb" in request.game_id else ("nfl" if "nfl" in request.game_id else "mlb"), team_pk, today_str, home_val, away_val, video_id, channel_name, f"https://www.youtube.com/watch?v={video_id}"))
            conn.commit()
    except Exception as db_err:
        logger.warning(f"Failed inserting watch_party_stream: {db_err}")

    # 3. Supervised daemon launch of tail_stream_chat.py if not already running
    try:
        check_cmd = f"pgrep -f 'tail_stream_chat.py {video_id}'"
        res = subprocess.run(check_cmd, shell=True, capture_output=True)
        if res.returncode != 0:
            tail_cmd = [
                "/home/james/stacklabs/.venv/bin/python3",
                "/home/james/stacklabs/scripts/tail_stream_chat.py",
                video_id,
                "/home/james/stacklabs/data/stream_chat_tail.md",
                channel_name
            ]
            subprocess.Popen(tail_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Spawned tail_stream_chat.py for {video_id} ({channel_name})")
    except Exception as spawn_err:
        logger.warning(f"Failed spawning tail_stream_chat.py: {spawn_err}")

    tail_info = {
        "game_id": request.game_id,
        "stream_id": video_id,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "live_url": f"https://www.youtube.com/watch?v={video_id}",
        "status": "active",
        "started_at": datetime.now().isoformat(),
    }
    ACTIVE_STREAM_TAILS[video_id] = tail_info
    logger.info(f"[STREAM TAIL] Attached listener for video {video_id} (game: {request.game_id})")

    return TailStreamResponse(
        success=True,
        game_id=request.game_id,
        stream_id=video_id,
        channel_id=channel_id,
        channel_name=channel_name,
        status="active",
        message=f"Live stream listener attached for {channel_name}."
    )

@app.get("/api/stream/active_tails")
async def get_active_tails(game_id: Optional[str] = None):
    if game_id:
        tails = [t for t in ACTIVE_STREAM_TAILS.values() if t.get("game_id") == game_id]
        return {"count": len(tails), "tails": tails}
    return {"count": len(ACTIVE_STREAM_TAILS), "tails": list(ACTIVE_STREAM_TAILS.values())}

# ---------------------------------------------------------------------------
# KALSHI PREDICTION ODDS & SENTIMENT DIVERGENCE ENDPOINTS
# ---------------------------------------------------------------------------
KALSHI_ODDS_FILE = Path("/home/james/stacklabs_inbox/today/kalshi_live_odds.json")

@app.get("/api/kalshi/odds")
def get_kalshi_odds():
    """Returns the latest Kalshi prediction market lines and implied probabilities."""
    if KALSHI_ODDS_FILE.exists():
        try:
            with open(KALSHI_ODDS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading odds cache: {e}")
    # Run inline poll if file doesn't exist
    from scripts.kalshi_odds_poller import poll_kalshi_odds
    return poll_kalshi_odds()

@app.get("/api/kalshi/divergence")
def get_kalshi_divergence(game_id: Optional[str] = None):
    """Returns the sentiment overreaction divergence metric for active matchups."""
    odds_data = get_kalshi_odds()
    markets = odds_data.get("markets", {})
    if game_id:
        if game_id in markets:
            return {"game_id": game_id, "data": markets[game_id]}
        raise HTTPException(status_code=404, detail="Game not found in active markets.")
    return {"timestamp": odds_data.get("timestamp"), "divergences": markets}

# ---------------------------------------------------------------------------
# STACKLABS VFS (VIRTUAL FILE SYSTEM) DATA PLANE
# ---------------------------------------------------------------------------
FAAS_VFS_ROOT = Path("/dev/shm/faas_vfs")

# Canonical seed registry ensuring instant availability even before daemons populate /dev/shm
SEED_VFS_REGISTRY = {
    "/shows": {
        "title": "Shows & Live Broadcasts",
        "items": [
            {
                "id": "artemis-quad",
                "label": "Artemis GP106 Hardware Mosaic",
                "category": "LIVE",
                "type": "stream",
                "badge": "1080P/60FPS",
                "description": "Hardware-composited 4-stream gameday mosaic grid running on Artemis Pascal GPU.",
                "url": "/api/artemis/mosaic/master_grid.m3u8",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "akamai-hls",
                "label": "Live Broadcast Master Feed",
                "category": "SPORTS",
                "type": "stream",
                "badge": "1080P MASTER",
                "description": "Ultra-low latency HLS broadcast master stream.",
                "url": "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "saturday-sports",
                "label": "Live Saturday Sports HLS Ingress",
                "category": "SPORTS",
                "type": "stream",
                "badge": "1080P/60FPS",
                "description": "Live Saturday sports game broadcast HLS master ingress.",
                "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "mcafee-live",
                "label": "The Pat McAfee Show (Live ESPN)",
                "category": "SHOW",
                "type": "stream",
                "badge": "LIVE ESPN",
                "description": "Daily sports analysis, live breakdown, and NFL/CFB guests.",
                "url": "https://www.youtube.com/watch?v=live_stream?channel=UCxcTeAKWJca6XyJ37_WmKIQ",
                "is_embeddable": True,
                "tail_url": "/api/vfs/tail?path=/shows/mcafee/chat.tail"
            },
            {
                "id": "theo-von",
                "label": "This Past Weekend (Theo Von)",
                "category": "TALK",
                "type": "stream",
                "badge": "PODCAST",
                "description": "Long-form conversational comedy, storytelling, and interviews.",
                "url": "https://www.youtube.com/watch?v=2O7K1t0C95c",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "wardy",
                "label": "Wardy Sports Network",
                "category": "SHOW",
                "type": "stream",
                "badge": "LIVE INGRESS",
                "description": "Live Mets postseason watch parties and sports reaction stream.",
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                "is_embeddable": True,
                "tail_url": "/api/vfs/tail?path=/shows/wardy/chat.tail"
            },
            {
                "id": "test-4k",
                "label": "4K TV Stream Test Pattern",
                "category": "TEST",
                "type": "stream",
                "badge": "1080P/60FPS",
                "description": "Direct hardware video decoding test for 65-inch Silk browser.",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "is_embeddable": True,
                "tail_url": None
            }
        ]
    },
    "/sports": {
        "title": "Live Sports Matches",
        "items": [
            {
                "id": "cfb-fsu-lou",
                "label": "CFB: Florida State vs Louisville",
                "category": "CFB",
                "type": "stream",
                "badge": "FRIDAY SLATE",
                "description": "ACC conference clash in Louisville. Live highlights and telemetry.",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "external_url": "https://streameast.to",
                "is_embeddable": True,
                "tail_url": "/api/vfs/tail?path=/tails/stream_chat.tail"
            },
            {
                "id": "cfb-iowa-wash",
                "label": "CFB: #20 Iowa @ Washington",
                "category": "CFB",
                "type": "stream",
                "badge": "BIG TEN",
                "description": "Big Ten matchup at Husky Stadium. Defensive trenches and punt battle.",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "external_url": "https://streameast.to",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "mlb-postseason",
                "label": "NLDS: 2026 Milwaukee Brewers Postseason",
                "category": "MLB",
                "type": "stream",
                "badge": "#1 SEED 103-59",
                "description": "Milwaukee Brewers NLDS Division Series live baseball action.",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "external_url": "https://streameast.to",
                "is_embeddable": True,
                "tail_url": None
            },
            {
                "id": "wnba-finals",
                "label": "WNBA Finals: Minnesota Lynx @ NY Liberty",
                "category": "WNBA",
                "type": "stream",
                "badge": "FINALS G1",
                "description": "WNBA Championship Game 1 clash at Barclays Center.",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "external_url": "https://streameast.to",
                "is_embeddable": True,
                "tail_url": None
            }
        ]
    },
    "/tails": {
        "title": "Real-Time Telemetry & Log Tails",
        "items": [
            {
                "id": "stream-chat",
                "label": "Live Stream Chat Tail",
                "category": "TAIL",
                "type": "tail",
                "badge": "40 LINES",
                "tail_url": "/api/vfs/tail?path=/tails/stream_chat.tail"
            },
            {
                "id": "steno-wire",
                "label": "Steno Wire Pressbox Tail",
                "category": "TAIL",
                "type": "tail",
                "badge": "LIVE AP WIRE",
                "tail_url": "/api/vfs/tail?path=/tails/steno_wire.tail"
            }
        ]
    },
    "/cameras": {
        "title": "Local Optical Sentries & Security",
        "items": [
            {
                "id": "c120",
                "label": "Tapo C120 // Smyrna Lab Optical Sentry",
                "category": "CAM",
                "type": "stream",
                "badge": "1080P RTSP",
                "description": "Local presence detection and hardware testbench stream from Smyrna command lab.",
                "url": "/api/vfs/cameras/c120/stream",
                "is_embeddable": True,
                "tail_url": None
            }
        ]
    }
}

@app.get("/api/vfs/guide")
def vfs_guide() -> Dict[str, Any]:
    """Consolidated Channel Guide endpoint for big-screen TV navigation."""
    try:
        from scripts.blueprints.faas_vfs_telemetry import get_vfs_live_guide
        return get_vfs_live_guide()
    except Exception as e:
        logger.warning(f"Failed to load dynamic live guide: {e}")
        all_channels: List[Dict[str, Any]] = []
        for category_path in ["/shows", "/sports", "/cameras"]:
            if category_path in SEED_VFS_REGISTRY:
                for item in SEED_VFS_REGISTRY[category_path]["items"]:
                    all_channels.append(dict(item))
        return {
            "status": "online",
            "title": "Pegasus TV Channel Guide",
            "total_channels": len(all_channels),
            "channels": all_channels
        }

@app.api_route("/api/vfs/cameras/c120/stream", methods=["GET", "HEAD"])
def vfs_camera_c120_stream():
    """Proxy live Tapo C120 MJPEG stream from Port 3028 through StackLabs VFS."""
    def frame_generator():
        try:
            req = urllib.request.Request("http://127.0.0.1:3028/stream/c120")
            with urllib.request.urlopen(req, timeout=10) as stream:
                while True:
                    chunk = stream.read(16384)
                    if not chunk:
                        break
                    yield chunk
        except Exception:
            return

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )

# ---------------------------------------------------------------------------
# ARTEMIS MOSAIC HTTPS STREAM PROXY & RECALIBRATION ENGINE (WO0011064)
# ---------------------------------------------------------------------------
class MosaicRecalibrateRequest(BaseModel):
    q0: Optional[str] = ""
    q1: Optional[str] = ""
    q2: Optional[str] = ""
    q3: Optional[str] = ""

@app.api_route("/api/artemis/mosaic/{file_path:path}", methods=["GET", "HEAD"])
def proxy_artemis_mosaic(file_path: str, request: Request):
    """Proxies HLS .m3u8 playlists and .ts video chunks directly from Artemis over Tailscale."""
    upstream_url = f"http://100.108.185.53:8088/{file_path}"
    
    if file_path.endswith(".m3u8"):
        media_type = "application/vnd.apple.mpegurl"
        cache_control = "no-cache, no-store, must-revalidate"
    elif file_path.endswith(".ts"):
        media_type = "video/mp2t"
        cache_control = "public, max-age=60"
    else:
        media_type = "application/octet-stream"
        cache_control = "no-cache"

    headers = {
        "Content-Type": media_type,
        "Cache-Control": cache_control,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }

    try:
        req = urllib.request.Request(upstream_url, method=request.method)
        upstream_resp = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as he:
        raise HTTPException(status_code=he.code, detail=f"Artemis stream error: {he.reason}")
    except Exception as e:
        logger.warning(f"Failed to connect to Artemis upstream {upstream_url}: {e}")
        raise HTTPException(status_code=502, detail=f"Artemis stream connection failed: {e}")

    if request.method == "HEAD":
        content_length = upstream_resp.headers.get("Content-Length")
        upstream_resp.close()
        head_headers = dict(headers)
        if content_length:
            head_headers["Content-Length"] = str(content_length)
        return PlainTextResponse("", status_code=200, headers=head_headers)

    def stream_content(resp):
        try:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            resp.close()

    return StreamingResponse(
        stream_content(upstream_resp),
        media_type=media_type,
        headers=headers
    )

@app.post("/api/mosaic/recalibrate")
def recalibrate_artemis_mosaic(req: MosaicRecalibrateRequest):
    """Dynamic recalibration of Artemis GTX 1060 NVENC 4-quadrant mosaic composition."""
    q0 = req.q0.strip() if req.q0 else ""
    q1 = req.q1.strip() if req.q1 else ""
    q2 = req.q2.strip() if req.q2 else ""
    q3 = req.q3.strip() if req.q3 else ""

    config_payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "q0": q0,
        "q1": q1,
        "q2": q2,
        "q3": q3
    }
    
    # Save quadrant selections to /dev/shm/faas_vfs/mosaic_config.json
    try:
        FAAS_VFS_ROOT.mkdir(parents=True, exist_ok=True)
        (FAAS_VFS_ROOT / "mosaic_config.json").write_text(json.dumps(config_payload, indent=2))
    except Exception as e:
        logger.warning(f"Failed to write mosaic_config.json: {e}")

    # Execute SSH command to Artemis
    ssh_cmd = f"/home/james/stacklabs/scripts/artemis_quad_grid.sh --recalibrate {shlex.quote(q0)} {shlex.quote(q1)} {shlex.quote(q2)} {shlex.quote(q3)}"
    try:
        res = subprocess.run([
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
            "100.108.185.53", ssh_cmd
        ], capture_output=True, text=True, timeout=8)
        if res.returncode != 0:
            logger.warning(f"Artemis recalibrate non-zero return: {res.stderr}")
    except Exception as e:
        logger.error(f"Failed to execute recalibrate over SSH: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to command Artemis over SSH: {e}")

    return {
        "status": "recalibrated",
        "timestamp": config_payload["timestamp"],
        "stream_url": "/api/artemis/mosaic/master_grid.m3u8",
        "quadrants": {
            "q0": q0 or "Default / Sentry",
            "q1": q1 or "Default / Radar",
            "q2": q2 or "Default / CMDB",
            "q3": q3 or "Default / Matrix"
        }
    }


def ensure_vfs_seeded():
    """Seeds /dev/shm/faas_vfs with initial directory nodes if not present."""
    try:
        FAAS_VFS_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

ensure_vfs_seeded()

# ---------------------------------------------------------------------------
# VFS VOLATILE MEMORY CEILING WATCHDOG (100 MB CEILING)
# ---------------------------------------------------------------------------
MAX_VFS_SHM_MB = 100

def get_vfs_shm_usage() -> tuple[int, int]:
    """Returns (total_bytes, file_count) for /dev/shm/faas_vfs."""
    if not FAAS_VFS_ROOT.exists():
        return 0, 0
    total_bytes = 0
    file_count = 0
    for p in FAAS_VFS_ROOT.rglob("*"):
        if p.is_file():
            try:
                total_bytes += p.stat().st_size
                file_count += 1
            except OSError:
                pass
    return total_bytes, file_count

def enforce_vfs_ceiling(max_mb: int = MAX_VFS_SHM_MB):
    """Prunes oldest volatile tails if /dev/shm/faas_vfs exceeds MAX_VFS_SHM_MB."""
    total_bytes, _ = get_vfs_shm_usage()
    max_bytes = max_mb * 1024 * 1024
    if total_bytes > max_bytes:
        logger.warning(
            f"[VFS Watchdog] /dev/shm/faas_vfs ({total_bytes / (1024*1024):.1f} MB)"
            f" exceeds {max_mb} MB ceiling. Pruning oldest tail logs..."
        )
        # Gather tail files sorted by mtime
        tail_files = []
        for p in FAAS_VFS_ROOT.rglob("*.tail"):
            if p.is_file():
                try:
                    tail_files.append((p.stat().st_mtime, p))
                except OSError:
                    pass
        tail_files.sort()
        for _, fpath in tail_files:
            try:
                # Truncate file to last 32KB
                size = fpath.stat().st_size
                if size > 32 * 1024:
                    with open(fpath, "rb+") as f:
                        f.seek(size - 32 * 1024)
                        data = f.read()
                        f.seek(0)
                        f.write(data)
                        f.truncate()
            except Exception as e:
                logger.warning(f"Error pruning {fpath}: {e}")
            # Recheck
            cur_bytes, _ = get_vfs_shm_usage()
            if cur_bytes <= max_bytes * 0.75:
                break

def check_vfs_memory_ceiling(max_mb: int = MAX_VFS_SHM_MB):
    """Scans /dev/shm/faas_vfs and enforces volatile memory ceiling."""
    return enforce_vfs_ceiling(max_mb)

@app.get("/api/vfs/health")
def vfs_health() -> Dict[str, Any]:
    """Returns volatile memory health metrics for the StackLabs VFS."""
    enforce_vfs_ceiling()
    total_bytes, file_count = get_vfs_shm_usage()
    return {
        "status": "healthy",
        "shm_root": str(FAAS_VFS_ROOT),
        "shm_bytes": total_bytes,
        "shm_mb": round(total_bytes / (1024 * 1024), 3),
        "ceiling_mb": MAX_VFS_SHM_MB,
        "node_count": file_count,
        "headroom_pct": round(
            (1.0 - (total_bytes / (MAX_VFS_SHM_MB * 1024 * 1024))) * 100, 1
        ),
    }

@app.get("/api/cmdb/browse")
@app.get("/api/vfs/browse")
def vfs_browse(path: str = "/shows", session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """In-Memory State Graph directory browse endpoint.
    Returns nodes for any given path (/shows, /sports, /tails, or /).
    Supports optional ephemeral RAM session_id.
    """
    clean_path = path.rstrip("/")
    if not clean_path:
        clean_path = "/" if path.strip() == "/" else "/shows"

    # Route to ephemeral in-memory session if session_id provided
    if session_id:
        sess_base = Path("/dev/shm/sessions") / session_id / "cmdb"
        if not sess_base.exists():
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or purged from RAM")

        if clean_path == "/" or clean_path == "" or clean_path == "/cmdb":
            items = []
            for entry in sorted(sess_base.iterdir()):
                if entry.name in ("session_metadata.json", "session_graph.db", "session_graph.db-wal", "session_graph.db-shm"):
                    continue
                try:
                    is_dir = entry.is_dir()
                except Exception:
                    is_dir = False
                if is_dir:
                    items.append({
                        "id": entry.name,
                        "name": entry.name,
                        "label": entry.name.replace("_", " ").title(),
                        "type": "folder",
                        "path": f"/cmdb/{entry.name}"
                    })
                else:
                    items.append({
                        "id": entry.name,
                        "name": entry.name,
                        "label": entry.stem.replace("_", " ").title(),
                        "type": "leaf",
                        "url": f"/api/cmdb/tail?path=/cmdb/{entry.name}&session_id={session_id}"
                    })
            return {
                "path": "/cmdb",
                "title": f"Ephemeral Session CMDB ({session_id})",
                "items": items,
                "status": "ephemeral_ram"
            }

        rel_subpath = clean_path.lstrip("/")
        if rel_subpath.startswith("cmdb/"):
            rel_subpath = rel_subpath[5:]
        elif rel_subpath == "cmdb":
            rel_subpath = ""

        target_dir = sess_base / rel_subpath if rel_subpath else sess_base
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail=f"Session path '{clean_path}' not found")

        items = []
        attributes = {}
        for entry in sorted(target_dir.iterdir()):
            try:
                is_directory = entry.is_dir()
            except Exception:
                is_directory = False

            if is_directory:
                items.append({
                    "id": entry.name,
                    "name": entry.name,
                    "label": entry.name.replace("_", " ").title(),
                    "type": "folder",
                    "path": f"{clean_path}/{entry.name}"
                })
            else:
                leaf_item = {
                    "id": entry.name,
                    "name": entry.name,
                    "label": entry.stem.replace("_", " ").title(),
                    "type": "leaf",
                    "url": f"/api/cmdb/tail?path={clean_path}/{entry.name}&session_id={session_id}"
                }
                if entry.suffix in [".txt", ".url", ".json"]:
                    try:
                        val = entry.read_text(encoding="utf-8").strip()
                        leaf_item["value"] = val
                        leaf_item["key"] = entry.stem
                        attributes[entry.stem] = val
                    except Exception:
                        pass
                items.append(leaf_item)
        res = {
            "path": clean_path,
            "title": clean_path.split("/")[-1].title(),
            "items": items,
            "status": "ephemeral_ram"
        }
        if attributes:
            res["attributes"] = attributes
        return res

    # If root path requested, return top-level directory list
    if clean_path == "/" or clean_path == "":
        return {
            "path": "/",
            "title": "Root State Graph",
            "items": [
                {"id": "shows", "label": "Shows & Broadcasts", "type": "folder", "path": "/shows"},
                {"id": "sports", "label": "Live Match Streams", "type": "folder", "path": "/sports"},
                {"id": "cameras", "label": "Local Optical Sentries", "type": "folder", "path": "/cameras"},
                {"id": "tails", "label": "Telemetry & Log Tails", "type": "folder", "path": "/tails"},
                {"id": "cmdb", "label": "Fleet CMDB (State Graph)", "type": "folder", "path": "/cmdb"}
            ]
        }
    
    # Check seed registry
    if clean_path in SEED_VFS_REGISTRY:
        node = SEED_VFS_REGISTRY[clean_path]
        items = [dict(item) for item in node["items"]]
        # Merge dynamic stream URLs and live leaves from /dev/shm/faas_vfs
        disk_dir = FAAS_VFS_ROOT / clean_path.lstrip("/")
        if disk_dir.exists() and disk_dir.is_dir():
            for itm in items:
                itm_dir = disk_dir / itm["id"]
                if itm_dir.exists():
                    url_file = itm_dir / "stream.url"
                    if url_file.exists():
                        try:
                            live_url = url_file.read_text(encoding="utf-8").strip()
                            if live_url:
                                itm["url"] = live_url
                                itm["badge"] = "LIVE SNIPER"
                        except Exception:
                            pass
        return {
            "path": clean_path,
            "title": node["title"],
            "items": items,
            "status": "online"
        }
    
    # Also inspect live disk path in /dev/shm/faas_vfs if populated (or NVMe persistent fallback)
    disk_dir = FAAS_VFS_ROOT / clean_path.lstrip("/")
    if not (disk_dir.exists() and disk_dir.is_dir()):
        fallback_dir = Path("/home/james/stacklabs/vfs") / clean_path.lstrip("/")
        if fallback_dir.exists() and fallback_dir.is_dir():
            disk_dir = fallback_dir

    if disk_dir.exists() and disk_dir.is_dir():
        items = []
        attributes = {}
        for entry in sorted(disk_dir.iterdir()):
            if entry.name == "personas":
                continue
            try:
                is_directory = entry.is_dir()
            except Exception:
                is_directory = False

            if is_directory:
                items.append({
                    "id": entry.name,
                    "name": entry.name,
                    "label": entry.name.replace("_", " ").title(),
                    "type": "folder",
                    "path": f"{clean_path}/{entry.name}"
                })
            else:
                leaf_item = {
                    "id": entry.name,
                    "name": entry.name,
                    "label": entry.stem.replace("_", " ").title(),
                    "type": "leaf",
                    "url": f"/api/cmdb/tail?path={clean_path}/{entry.name}"
                }
                if entry.suffix in [".txt", ".url"]:
                    try:
                        val = entry.read_text(encoding="utf-8").strip()
                        leaf_item["value"] = val
                        leaf_item["key"] = entry.stem
                        attributes[entry.stem] = val
                        if entry.suffix == ".url":
                            leaf_item["target_url"] = val
                    except Exception:
                        pass
                items.append(leaf_item)
        res = {
            "path": clean_path,
            "title": clean_path.split("/")[-1].title(),
            "items": items,
            "status": "live_memory"
        }
        if attributes:
            res["attributes"] = attributes
        return res
        
    raise HTTPException(status_code=404, detail=f"Path '{clean_path}' not found")

@app.get("/api/cmdb/tail")
@app.get("/api/vfs/tail")
def vfs_tail(path: str, lines: int = 50, session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Sub-millisecond tail reader for memory-mapped log and stream tails."""
    clean_path = path.lstrip("/")
    
    if session_id:
        sess_base = Path("/dev/shm/sessions") / session_id / "cmdb"
        rel_subpath = clean_path
        if rel_subpath.startswith("cmdb/"):
            rel_subpath = rel_subpath[5:]
        sess_file = sess_base / rel_subpath
        if sess_file.exists() and sess_file.is_file():
            try:
                content = sess_file.read_text(encoding="utf-8", errors="ignore").strip()
                return {
                    "path": path,
                    "lines": [content],
                    "total_lines": 1,
                    "status": "ephemeral_ram"
                }
            except Exception:
                pass
    
    # Map common tails to active files
    target_file = None
    direct = FAAS_VFS_ROOT / clean_path
    if not (direct.exists() and direct.is_file()):
        fallback = Path("/home/james/stacklabs/vfs") / clean_path
        if fallback.exists() and fallback.is_file():
            direct = fallback

    if direct.exists() and direct.is_file():
        try:
            content = direct.read_text(encoding="utf-8").strip()
            if os.path.exists(content) and os.path.isfile(content):
                target_file = content
            else:
                target_file = str(direct)
        except Exception:
            target_file = str(direct)

    if not target_file:
        if "stream_chat" in clean_path or "chat.tail" in clean_path:
            for candidate in [
                "/home/james/stacklabs/data/stream_chat_tail.md",
                "/home/james/stacklabs_inbox/today/stream_chat_tail.md",
                "/home/james/stacklabs/apps/faas/public/FanStack_Live/stream_chat_tail.md"
            ]:
                if os.path.exists(candidate):
                    target_file = candidate
                    break
        elif "steno_wire" in clean_path or "transcript.tail" in clean_path:
            for candidate in [
                "/home/james/stacklabs_inbox/today/steno_transcript_tail.md",
                "/home/james/stacklabs/data/steno_wire.txt"
            ]:
                if os.path.exists(candidate):
                    target_file = candidate
                    break
            
    if not target_file or not os.path.exists(target_file):
        return {
            "path": path,
            "lines": [f"[VFS TAIL STANDBY] No active stream attached for {clean_path}."],
            "count": 1
        }
        
    try:
        with open(target_file, "rb") as f:
            size = os.path.getsize(target_file)
            seek_size = min(size, 32 * 1024)
            f.seek(size - seek_size)
            raw = f.read().decode("utf-8", errors="ignore")
            all_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            tail_lines = all_lines[-lines:] if lines > 0 else all_lines
            return {
                "path": path,
                "lines": tail_lines,
                "count": len(tail_lines)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to tail VFS path: {e}")

# Field notes decoupled to scripts.blueprints.field_notes_bp (WO0011252)

# ---------------------------------------------------------------------------
# STATIC FILES SERVING & SPA FALLBACK
# ---------------------------------------------------------------------------
if os.path.exists(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(target):
            headers = {
                "Cache-Control": "no-cache, must-revalidate",
                "Pragma": "no-cache"
            }
            return FileResponse(target, headers=headers)
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache"
            }
            return FileResponse(index_file, headers=headers)
        return JSONResponse(status_code=404, content={"error": "SPA index.html not found"})
else:
    @app.get("/")
    def fallback_root():
        return {
            "service": "FANSTACK LITE // FAAS MOBILE UTILITY",
            "port": 3033,
            "status": "dist not built",
            "message": "Run npm run build in /home/james/stacklabs/33_FanStack_Lite/"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3032)
