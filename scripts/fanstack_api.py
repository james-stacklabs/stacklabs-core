"""
fanstack_api.py — FanStack Independent API
===========================================
Port 8001. Completely independent from SovereignOS Core.

FanStack components hosted here:
  POST /api/hot_take     → Hot Takes (single persona rant)
  WS   /api/skew/ws     → The Skew (panel debate session)

SovereignOS Core (port 8090) handles Auth, CMDB, ARGUS, hardware.
This service calls Core for persona lookups but is NOT part of Core.
Restarting this service has zero effect on Scruffy's Tavern or Core.
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hot_takes_service import router as hot_takes_router
# from skew_service import router as skew_router  # ← uncomment when built

app = FastAPI(title="FanStack API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── FanStack Component Routers ────────────────────────────────────────────────
app.include_router(hot_takes_router)
# app.include_router(skew_router)   # ← uncomment when skew_service.py is built
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "FanStack API", "port": 8001}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
