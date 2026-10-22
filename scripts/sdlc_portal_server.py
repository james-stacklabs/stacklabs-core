#!/usr/bin/env python3
"""
StackLabs Platform SDLC Portal Server v2 — Decoupled Application Factory
Port: 8095 | Service: stacklabs-sdlc.service
Governing Standard: Invariant 50 (Decoupling & Orchestrator <= 300 Lines)
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

PROJECT_ROOT = Path("/home/james/stacklabs")
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sdlc_portal_server_v2")

DB_PATH = os.getenv("SOVEREIGN_DB_PATH", "/home/james/stacklabs/dna/sovereign_now.db")
INBOX_PATH = Path(os.getenv("SOVEREIGN_INBOX", "/home/james/sovereign_inbox"))
INBOX_PATH.mkdir(parents=True, exist_ok=True)

try:
    from scripts.core.audit_chain import SovereignAuditChain
    audit_chain = SovereignAuditChain(db_path=DB_PATH)
except Exception as e:
    logger.warning(f"SovereignAuditChain unavailable: {e}")
    audit_chain = None

app = FastAPI(
    title="Sovereign SDLC Portal v2",
    description="Decoupled local ticketing, CMDB, and simulation engine for Apiary fleet",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MOUNT MODULAR ROUTERS (INVARIANT 50)
# ---------------------------------------------------------------------------
try:
    from scripts.routers.sdlc_core import router as sdlc_core_router
    app.include_router(sdlc_core_router, tags=["SDLC Core"])
except Exception as e:
    logger.warning(f"Router sdlc_core not yet extracted: {e}")

try:
    from scripts.routers.sdlc_cmdb import router as sdlc_cmdb_router
    app.include_router(sdlc_cmdb_router, tags=["CMDB"])
except Exception as e:
    logger.warning(f"Router sdlc_cmdb not yet extracted: {e}")

try:
    from scripts.routers.sdlc_society import router as sdlc_society_router
    app.include_router(sdlc_society_router, tags=["Emergent Society"])
except Exception as e:
    logger.warning(f"Router sdlc_society not yet extracted: {e}")

try:
    from scripts.routers.sdlc_gaming import router as sdlc_gaming_router
    app.include_router(sdlc_gaming_router, tags=["Gaming & Media"])
except Exception as e:
    logger.warning(f"Router sdlc_gaming not yet extracted: {e}")

# Mount 13 Legacy Domain Routers
try:
    from routers.cmdb import router as legacy_cmdb
    from routers.personas import router as legacy_personas
    from routers.auth import router as legacy_auth
    from routers.public import router as legacy_public
    from routers.legal import router as legacy_legal
    from routers.fanstack import router as legacy_fanstack
    from routers.hygiene import router as legacy_hygiene
    from routers.broadcast import router as legacy_broadcast
    from routers.sentinel import router as legacy_sentinel
    from routers.pizzabot import router as legacy_pizzabot
    from routers.shield import router as legacy_shield
    from routers.assembly import router as legacy_assembly
    from routers.sports import router as legacy_sports

    for r in (legacy_cmdb, legacy_personas, legacy_auth, legacy_public,
              legacy_legal, legacy_fanstack, legacy_hygiene, legacy_broadcast,
              legacy_sentinel, legacy_pizzabot, legacy_shield, legacy_assembly, legacy_sports):
        app.include_router(r)
    logger.info("Mounted 13 legacy domain routers successfully.")
except Exception as err:
    logger.error(f"Failed mounting legacy sub-routers: {err}")

try:
    from routers.command_hub import router as command_hub_router, cockpit_router
    app.include_router(command_hub_router)
    app.include_router(cockpit_router)
    logger.info("Mounted command_hub and cockpit routers successfully.")
except Exception as err:
    logger.error(f"Failed mounting command_hub router: {err}")

try:
    from routers.vector6_chat import router as vector6_chat_router
    app.include_router(vector6_chat_router)
    logger.info("Mounted vector6_chat router successfully.")
except Exception as err:
    logger.error(f"Failed mounting vector6_chat router: {err}")

try:
    from scripts.blueprints.stream_sniper_bp import stream_sniper_bp
    app.include_router(stream_sniper_bp)
    logger.info("Mounted stream_sniper_bp router on Port 8095 (/sniper, /snipes, /api/snipe).")
except Exception as err:
    logger.error(f"Failed mounting stream_sniper_bp router: {err}")

# Static and Inbox Mounts
ATTACHMENTS_DIR = INBOX_PATH / "attachments"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/attachments_static", StaticFiles(directory=str(ATTACHMENTS_DIR)), name="attachments_static")

STATIC_DIR = PROJECT_ROOT / "scripts" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/api/health")
@app.get("/healthz")
async def health_check():
    return {
        "status": "healthy",
        "service": "stacklabs-sdlc-portal-v2",
        "port": 8095,
        "database": DB_PATH,
        "audit_chain": audit_chain is not None,
        "invariant": "Invariant 50 Compliant (Decoupled)"
    }

# ---------------------------------------------------------------------------
# JETEXTRACTORS LIVE SPORTS STREAM RESOLVER (WO0011060)
# ---------------------------------------------------------------------------
try:
    from scripts.sports.resolvers.jetextractors_resolver import JetExtractorsResolver
    _jet_resolver = JetExtractorsResolver()
    logger.info("[Portal] JetExtractorsResolver initialized successfully.")
except Exception as e:
    logger.warning(f"[Portal] Failed to initialize JetExtractorsResolver: {e}")
    _jet_resolver = None

@app.get("/api/stream/resolve/{league}/{team_or_game}")
async def resolve_sports_stream(league: str, team_or_game: str):
    """Auto-resolves live sports stream to HLS master playlist with headers."""
    if _jet_resolver is None:
        return {"status": "error", "error": "JetExtractors resolver not initialized"}
    try:
        payload = _jet_resolver.resolve(league, team_or_game)
        return {"status": "ok", "payload": payload}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8095, reload=False)
