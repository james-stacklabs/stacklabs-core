#!/usr/bin/env python3
"""
Sovereign Anti-Surveillance Price Shield Router
Author: James Carroll (Pilot), Lead Systems Architect / Antigravity
Ticket: WO0010080-SOVEREIGN-ANTI-SURVEILLANCE-PRICE-SHIELD
ENHC:   Multi-IP Distributed Edge Sentry Network (hobbes + grogu-1)
Affected CI: sovereign_knot_core

REST endpoints on Port 8095 for multi-vantage price surveillance auditing,
tracker stripping, delta calculation, adversarial noise generation, and audit history.

Edge Sentry Network (port 8710 on each node):
  - hobbes (100.88.5.122) : Mom's house ISP  — Pi Zero 2 W
  - calvin (100.104.14.75) : Barb's house ISP — Pi Zero 2 W
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from core.price_shield_engine import DEVICE_PROFILES, price_shield_engine
except ImportError:
    from scripts.core.price_shield_engine import DEVICE_PROFILES, price_shield_engine

logger = logging.getLogger("shield_router")
router = APIRouter(prefix="/api/shield", tags=["Price Shield"])

# ---------------------------------------------------------------------------
# Distributed Edge Sentry Registry
# Each entry is a physical node at a distinct ISP/public IP.
# ---------------------------------------------------------------------------
EDGE_SENTRIES: list[dict[str, Any]] = [
    {
        "name": "hobbes",
        "tailscale_ip": "100.88.5.122",
        "location": "Mom's house",
        "port": 8710,
        "enabled": True,
    },
    {
        "name": "calvin",
        "tailscale_ip": "100.104.14.75",
        "location": "Barb's house",
        "port": 8710,
        "enabled": True,
    },
]

SENTRY_SECRET = "sovereign-sentry-v1"
SENTRY_TIMEOUT = 30.0   # seconds per remote scrape


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sentry_url(sentry: dict[str, Any], path: str) -> str:
    return f"http://{sentry['tailscale_ip']}:{sentry['port']}{path}"


async def _ping_sentry(sentry: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
    """Return sentry health dict; marks offline gracefully on failure."""
    try:
        resp = await client.get(
            _sentry_url(sentry, "/health"),
            timeout=5.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {**sentry, "online": True, "health": data}
        return {**sentry, "online": False, "health": None}
    except Exception:
        return {**sentry, "online": False, "health": None}


async def _dispatch_sentry_scrape(
    sentry: dict[str, Any],
    url: str,
    profiles: list[str],
    client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """
    POST a scrape job to a remote sentry node.
    Returns None on timeout/connection failure (node offline — not fatal).
    """
    try:
        resp = await client.post(
            _sentry_url(sentry, "/scrape"),
            json={"url": url, "profiles": profiles},
            headers={"X-Sentry-Secret": SENTRY_SECRET},
            timeout=SENTRY_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "Sentry %s returned HTTP %d for url=%s", sentry["name"], resp.status_code, url
        )
        return None
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning("Sentry %s unreachable (%s) — skipping vantage.", sentry["name"], e)
        return None
    except Exception as e:
        logger.exception("Unexpected error from sentry %s: %s", sentry["name"], e)
        return None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AuditPriceRequest(BaseModel):
    url: str
    requested_by: Optional[str] = "pilot"
    profiles: Optional[List[str]] = None


class GenerateNoiseRequest(BaseModel):
    category: Optional[str] = "retail"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/audit_price")
async def api_audit_price(payload: AuditPriceRequest) -> Dict[str, Any]:
    """
    Audit a target retail/travel URL across multi-vantage browser profiles.

    Dispatches concurrent scrape jobs to:
      1. clio local Playwright engine (home ISP)
      2. hobbes edge sentry (Mom's house ISP)
      3. grogu-1 edge sentry (Barb's house ISP — if online)

    Merges results, recalculates IP-aware markup delta, and persists to DB.
    """
    if not payload.url or not payload.url.strip():
        raise HTTPException(status_code=400, detail="Target URL cannot be empty.")

    profiles = payload.profiles or list(DEVICE_PROFILES.keys())

    # --- 1. Local Playwright engine (existing) ---
    local_task = asyncio.create_task(
        price_shield_engine.audit_url(
            target_url=payload.url,
            requested_by=payload.requested_by or "pilot",
            profiles=profiles,
        )
    )

    # --- 2. Edge sentries (concurrent, failure-tolerant) ---
    async with httpx.AsyncClient() as client:
        sentry_tasks = [
            asyncio.create_task(
                _dispatch_sentry_scrape(s, payload.url, profiles, client)
            )
            for s in EDGE_SENTRIES
            if s.get("enabled")
        ]
        results = await asyncio.gather(local_task, *sentry_tasks, return_exceptions=True)

    local_report = results[0] if not isinstance(results[0], Exception) else None
    if not local_report:
        err = results[0] if isinstance(results[0], Exception) else "unknown"
        logger.exception("Local Playwright engine failed: %s", err)
        raise HTTPException(status_code=500, detail=f"Price Shield local audit failed: {err}")

    # Merge edge sentry telemetry into the report
    edge_results: list[dict[str, Any]] = []
    for i, sentry in enumerate(EDGE_SENTRIES):
        raw = results[1 + i]
        if isinstance(raw, Exception) or raw is None:
            edge_results.append({"node": sentry["name"], "location": sentry["location"], "status": "offline"})
        else:
            edge_results.append({
                "node": sentry["name"],
                "location": sentry["location"],
                "status": "online",
                "results": raw.get("results", {}),
            })

    local_report["edge_sentry_network"] = edge_results
    local_report["distributed_vantage_count"] = 1 + sum(
        1 for e in edge_results if e["status"] == "online"
    )

    # Compute cross-IP delta (baseline_desktop price variance across nodes)
    ip_prices: list[float] = []
    if local_report.get("baseline_price"):
        ip_prices.append(local_report["baseline_price"])
    for er in edge_results:
        if er["status"] == "online":
            bp = er.get("results", {}).get("baseline_desktop", {}).get("price")
            if bp:
                ip_prices.append(bp)

    if len(ip_prices) > 1:
        local_report["ip_price_variance"] = round(max(ip_prices) - min(ip_prices), 2)
        local_report["ip_prices_observed"] = ip_prices
    else:
        local_report["ip_price_variance"] = 0.0

    return local_report


@router.get("/audits")
async def api_get_audits(limit: int = Query(default=20, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Retrieves paginated historical price surveillance audits from the database."""
    try:
        return price_shield_engine.get_audit_history(limit=limit)
    except Exception as e:
        logger.exception("Error fetching audit history: %s", e)
        raise HTTPException(status_code=500, detail=f"Could not fetch audits: {str(e)}")


@router.get("/status")
async def api_get_status() -> Dict[str, Any]:
    """
    Reports full distributed sentry mesh health: local engine + all edge nodes.
    """
    async with httpx.AsyncClient() as client:
        sentry_checks = await asyncio.gather(
            *[_ping_sentry(s, client) for s in EDGE_SENTRIES],
            return_exceptions=True,
        )

    sentry_statuses = []
    for i, s in enumerate(EDGE_SENTRIES):
        check = sentry_checks[i]
        if isinstance(check, Exception):
            sentry_statuses.append({**s, "online": False, "health": None})
        else:
            sentry_statuses.append(check)

    online_count = sum(1 for s in sentry_statuses if s.get("online"))

    return {
        "status": "online",
        "engine": "PriceShieldEngine v1.1 (Distributed)",
        "local_engine": {
            "node": "clio",
            "tailscale_ip": "100.73.155.70",
            "location": "Home (primary)",
            "mode": "Playwright headless",
            "online": True,
        },
        "edge_sentry_network": sentry_statuses,
        "total_vantage_points": 1 + online_count,
        "supported_profiles": list(DEVICE_PROFILES.keys()),
        "profile_metadata": DEVICE_PROFILES,
        "surveillance_protection_active": True,
    }


@router.get("/sentries")
async def api_get_sentries() -> List[Dict[str, Any]]:
    """Returns the edge sentry registry with live reachability ping."""
    async with httpx.AsyncClient() as client:
        checks = await asyncio.gather(
            *[_ping_sentry(s, client) for s in EDGE_SENTRIES],
            return_exceptions=True,
        )
    return [
        checks[i] if not isinstance(checks[i], Exception) else {**s, "online": False}
        for i, s in enumerate(EDGE_SENTRIES)
    ]


@router.post("/generate_noise")
async def api_generate_noise(payload: GenerateNoiseRequest) -> Dict[str, Any]:
    """Dispatches synthetic adversarial browsing queries to dilute data broker graphs."""
    try:
        return price_shield_engine.generate_adversarial_noise(category=payload.category or "retail")
    except Exception as e:
        logger.exception("Error generating adversarial noise: %s", e)
        raise HTTPException(status_code=500, detail=f"Adversarial noise generation failed: {str(e)}")
