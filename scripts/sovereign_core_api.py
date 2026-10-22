import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Schema migrations + auth helpers must run before routers mount
import core.schema  # noqa: F401  (runs ensure_*_exists() migrations on import)

# ============================================================================
# SOVEREIGN OS CORE API
# Decoupled Hardware and OS-Level Infrastructure from FanStack
# ============================================================================

fastapi_app = FastAPI()

# Mount Sovereign Inbox for media access (e.g. SamTracker images)
fastapi_app.mount("/inbox", StaticFiles(directory="/home/james/sovereign_inbox"), name="inbox")

# Mount Sovereign Media Vault for Loot & Collectibles
if os.path.exists("/home/james/stacklabs/media_vault"):
    fastapi_app.mount("/media_vault", StaticFiles(directory="/home/james/stacklabs/media_vault"), name="media_vault")

# Mount Sovereign Voice Heal Router (Self-Healing Engine)
try:
    from scripts.voice_heal_service import router as voice_heal_router
except ImportError:
    from voice_heal_service import router as voice_heal_router
fastapi_app.include_router(voice_heal_router)

# Mount Sovereign Prompt Decoder Router (Stack Seeder Prompt Optimization)
try:
    from scripts.prompt_decoder_service import router as prompt_decoder_router
except ImportError:
    from prompt_decoder_service import router as prompt_decoder_router
fastapi_app.include_router(prompt_decoder_router)

# Mount Stack Seeder Multi-Modal Ingestion Assets Sub-Router
try:
    from scripts.seeder_asset_ingestor import router as asset_router
except ImportError:
    from seeder_asset_ingestor import router as asset_router
fastapi_app.include_router(asset_router)

# Mount Omega Key Gatekeeper Router
try:
    from scripts.omega_gate_service import router as omega_gate_router
except ImportError:
    from omega_gate_service import router as omega_gate_router
fastapi_app.include_router(omega_gate_router)

# ============================================================================
# DOMAIN ROUTERS  (was ~7,800 lines inline; now split by domain -- see routers/)
# ============================================================================
from routers.auth import router as auth_router
from routers.public import router as public_router
from routers.entertainment import router as entertainment_router
from routers.ingest import router as ingest_router
from routers.fanstack import router as fanstack_router
from routers.system_ops import router as system_ops_router
from routers.wildseed import router as wildseed_router
from routers.cmdb import router as cmdb_router
from routers.hailo import router as hailo_router
from routers.personas import router as personas_router
from routers.brand import router as brand_router
from routers.media import router as media_router
from routers.mam import router as mam_router
from routers.greenstack import router as greenstack_router
from routers.holodex_loot import router as holodex_loot_router
from routers.command_hub import router as command_hub_router
from routers.truecost import router as truecost_router

fastapi_app.include_router(auth_router)
fastapi_app.include_router(public_router)
fastapi_app.include_router(entertainment_router)
fastapi_app.include_router(ingest_router)
fastapi_app.include_router(fanstack_router)
fastapi_app.include_router(system_ops_router)
fastapi_app.include_router(wildseed_router)
fastapi_app.include_router(cmdb_router)
fastapi_app.include_router(hailo_router)
fastapi_app.include_router(personas_router)
fastapi_app.include_router(brand_router)
fastapi_app.include_router(media_router)
fastapi_app.include_router(mam_router)
fastapi_app.include_router(greenstack_router)
fastapi_app.include_router(holodex_loot_router)
fastapi_app.include_router(command_hub_router)
fastapi_app.include_router(truecost_router)


@fastapi_app.exception_handler(Exception)
async def global_cors_exception_handler(request: Request, exc: Exception):
    """Ensures CORS headers are present on all 500 responses so browser sees the real error."""
    import traceback
    traceback.print_exc()
    CORS_HEADERS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=CORS_HEADERS
    )

# Allow cross-origin requests from the Unified MLB UI
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Optional sub-services (graceful no-op if module is absent) ────────────────
# ── Hot Takes Service ─────────────────────────────────────────────────────────
# POST /api/hot_take        — fire a persona rant
# POST /api/hot_take/dub    — upload Flow video + script → dubbed output
# GET  /api/hot_take/voices — available TTS voices
# GET  /api/hot_takes       — retrieve saved hot takes from DB
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hot_takes_service import router as _hot_takes_router
    fastapi_app.include_router(_hot_takes_router)
except Exception as _ht_err:
    print(f"⚠️  Hot takes routes NOT mounted: {_ht_err}")

# ── Persona Call Routes (ENHC0000044) ─────────────────────────────────────────
# POST /api/persona-call/offer    — WebRTC SDP offer, returns SDP answer
# POST /api/persona-call/ice      — ICE candidate exchange
# POST /api/persona-call/hangup   — End active session
# GET  /api/persona-call/status   — Active sessions overview
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hololink_persona_call import (
        handle_offer   as _pc_offer,
        handle_ice     as _pc_ice,
        handle_hangup  as _pc_hangup,
        handle_status  as _pc_status,
    )
    fastapi_app.add_api_route("/api/persona-call/offer",  _pc_offer,  methods=["POST"])
    fastapi_app.add_api_route("/api/persona-call/ice",    _pc_ice,    methods=["POST"])
    fastapi_app.add_api_route("/api/persona-call/hangup", _pc_hangup, methods=["POST"])
    fastapi_app.add_api_route("/api/persona-call/status", _pc_status, methods=["GET"])
    print("✅ Persona call routes mounted on /api/persona-call/*")
except Exception as _pc_err:
    print(f"⚠️  Persona call routes NOT mounted: {_pc_err}")
# ── End Persona Call Routes ────────────────────────────────────────────────────

# ── Token Analytics API (STRY1779338715) ──────────────────────────────────────
# GET /api/token-analytics/games          — games with token data
# GET /api/token-analytics/game/{game_pk} — full per-game report
# GET /api/token-analytics/trends         — daily rollup
# GET /api/token-analytics/leaderboard    — all-time persona burn
# GET /api/token-analytics/summary        — fleet-wide headline numbers
# GET /api/token-analytics/export/{pk}    — CSV download
try:
    from token_analytics_api import router as _token_analytics_router
    fastapi_app.include_router(_token_analytics_router)
    print("✅ Token analytics routes mounted on /api/token-analytics/*")
except Exception as _ta_err:
    print(f"⚠️  Token analytics routes NOT mounted: {_ta_err}")
# ── End Token Analytics API ────────────────────────────────────────────────────

# ── Game Log Export API (STRY1779341054) ──────────────────────────────────────
# GET /api/game-log/games              — games with chat data
# GET /api/game-log/export/{game_pk}   — MD / JSON / CSV export
# GET /api/game-log/chat/{game_pk}     — chat messages only
# GET /api/game-log/plays/{game_pk}    — play-by-play only
try:
    from game_log_export_api import router as _game_log_router
    fastapi_app.include_router(_game_log_router)
    print("✅ Game log export routes mounted on /api/game-log/*")
except Exception as _gl_err:
    print(f"⚠️  Game log export routes NOT mounted: {_gl_err}")
# ── End Game Log Export API ────────────────────────────────────────────────────


if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8090)
