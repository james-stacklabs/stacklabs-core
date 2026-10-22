#!/usr/bin/env python3
"""
StackLabs Ground Truth Mesh Ingestion Daemon
Path: /home/james/stacklabs/scripts/sync_ground_truth_mesh.py

Pulls deterministic state across 4 pillars:
1. NOAA / NWS Active Alerts & NHC Tropical Cyclones
2. Direct Market Volatility (SPY, XLE, USO, BTC-USD)
3. USGS Seismic Telemetry (M2.5+ quakes)
4. CISA Known Exploited Vulnerabilities (Active CVE Catalog)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

PRIMARY_DIR = Path("/home/james/stacklabs/ground_truth")
DATA_DIR = Path("/home/james/stacklabs/data/ground_truth")
INBOX_DIR = Path("/home/james/stacklabs_inbox/today")

TARGET_FILE = PRIMARY_DIR / "telemetry_state.json"
TMP_FILE = PRIMARY_DIR / "telemetry_state.json.tmp"

HEADERS = {
    "User-Agent": "StackLabs-GroundTruth/1.0 (contact: james@stacklabsllc.com)",
    "Accept": "application/geo+json, application/json"
}

MARKET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}


def fetch_json(url: str, headers: Dict[str, str] = HEADERS, timeout: int = 10) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "status": "failed"}


# ------------------------------------------------------------------------------
# PILLAR 1: NOAA / NWS & NHC (Atmosphere & Tropical Risk)
# ------------------------------------------------------------------------------

def pull_noaa_alerts() -> Dict[str, Any]:
    url = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
    data = fetch_json(url)
    if "features" not in data:
        return {"count": 0, "alerts": [], "status": "error", "raw_error": data.get("error")}

    parsed = []
    for feat in data.get("features", [])[:15]:
        props = feat.get("properties", {})
        parsed.append({
            "id": props.get("id"),
            "event": props.get("event"),
            "headline": props.get("headline"),
            "severity": props.get("severity"),
            "urgency": props.get("urgency"),
            "area_desc": props.get("areaDesc"),
            "sent": props.get("sent")
        })
    return {"count": len(data.get("features", [])), "top_alerts": parsed, "status": "nominal"}


def pull_nhc_cyclones() -> Dict[str, Any]:
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    data = fetch_json(url)
    storms = []
    for s in data.get("activeStorms", []):
        try:
            kt = int(s.get("intensity", 0))
            mph = int(kt * 1.15078)
            mb = int(s.get("pressure", 0))
            storms.append({
                "id": s.get("id", ""),
                "name": s.get("name", "UNNAMED"),
                "classification": s.get("classification", "UNKNOWN"),
                "intensity_kt": kt,
                "intensity_mph": mph,
                "pressure_mb": mb,
                "latitude": float(s.get("latitudeNumeric", 0.0)),
                "longitude": float(s.get("longitudeNumeric", 0.0)),
                "movement_dir": int(s.get("movementDir", 0)) if s.get("movementDir") is not None else None,
                "movement_speed_mph": int(s.get("movementSpeed", 0)) if s.get("movementSpeed") is not None else None,
                "public_advisory_url": s.get("publicAdvisory", {}).get("url"),
                "last_update": s.get("lastUpdate")
            })
        except Exception:
            continue
    return {
        "count": len(storms),
        "hurricanes_count": len([s for s in storms if s.get("classification") == "HU"]),
        "storms": storms,
        "status": "nominal"
    }


# ------------------------------------------------------------------------------
# PILLAR 2: DIRECT MARKET BASKETS (Capital & Energy Volatility)
# ------------------------------------------------------------------------------

def pull_market_baskets() -> Dict[str, Any]:
    symbols = ["SPY", "XLE", "USO", "BTC-USD"]
    baskets = {}
    for sym in symbols:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2d"
        data = fetch_json(url, headers=MARKET_HEADERS, timeout=5)
        try:
            result = data.get("chart", {}).get("result", [])[0]
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice", 0.0)
            prev_close = meta.get("chartPreviousClose", price)
            net_change = round(price - prev_close, 2)
            pct_change = round((net_change / prev_close) * 100, 2) if prev_close else 0.0
            baskets[sym] = {
                "symbol": sym,
                "price": price,
                "previous_close": prev_close,
                "net_change": net_change,
                "pct_change": pct_change,
                "currency": meta.get("currency", "USD")
            }
        except Exception:
            baskets[sym] = {"symbol": sym, "status": "unavailable"}

    return {"baskets": baskets, "status": "nominal"}


# ------------------------------------------------------------------------------
# PILLAR 3: USGS REAL-TIME SEISMIC ACTIVITY
# ------------------------------------------------------------------------------

def pull_usgs_quakes() -> Dict[str, Any]:
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    data = fetch_json(url)
    if "features" not in data:
        return {"count": 0, "quakes": [], "status": "error", "raw_error": data.get("error")}

    parsed = []
    for feat in data.get("features", [])[:10]:
        props = feat.get("properties", {})
        parsed.append({
            "id": feat.get("id"),
            "place": props.get("place"),
            "mag": props.get("mag"),
            "time": props.get("time"),
            "tsunami": props.get("tsunami")
        })
    return {"count": len(data.get("features", [])), "recent_significant": parsed, "status": "nominal"}


# ------------------------------------------------------------------------------
# PILLAR 4: CISA KNOWN EXPLOITED VULNERABILITIES (CVE Wire)
# ------------------------------------------------------------------------------

def pull_cisa_exploits() -> Dict[str, Any]:
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    data = fetch_json(url, timeout=12)
    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return {"count": 0, "recent_added": [], "status": "error", "raw_error": data.get("error")}

    sorted_vulns = sorted(vulns, key=lambda x: x.get("dateAdded", ""), reverse=True)
    recent = []
    for v in sorted_vulns[:10]:
        recent.append({
            "cveID": v.get("cveID"),
            "vendorProject": v.get("vendorProject"),
            "product": v.get("product"),
            "vulnerabilityName": v.get("vulnerabilityName"),
            "dateAdded": v.get("dateAdded")
        })
    return {"total_catalog_count": data.get("count", len(vulns)), "recent_exploits": recent, "status": "nominal"}


# ------------------------------------------------------------------------------
# MESH AGGREGATOR & ATOMIC COMMIT
# ------------------------------------------------------------------------------

def sync_mesh():
    PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "schema_version": "1.0.0",
        "timestamp_utc": now_iso,
        "pillars": {
            "noaa_weather": pull_noaa_alerts(),
            "nhc_hurricanes": pull_nhc_cyclones(),
            "market_volatility": pull_market_baskets(),
            "usgs_seismic": pull_usgs_quakes(),
            "cisa_threats": pull_cisa_exploits()
        }
    }

    # Atomic write to canonical ground truth
    with open(TMP_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(TMP_FILE, TARGET_FILE)

    # Mirror to data/ground_truth/telemetry_state.json
    compat_file = DATA_DIR / "telemetry_state.json"
    compat_tmp = DATA_DIR / "telemetry_state.json.tmp"
    with open(compat_tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(compat_tmp, compat_file)

    # Mirror to inbox active telemetry
    inbox_file = INBOX_DIR / "active_telemetry_mesh.json"
    with open(inbox_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[{now_iso}] Ground truth mesh synced successfully to {TARGET_FILE} and mirrors.")


if __name__ == "__main__":
    sync_mesh()
