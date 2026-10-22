#!/home/james/stacklabs/.venv/bin/python3
"""
SWANSON SPATIAL-CULTURAL & CMDB COLLIDER ENGINE (A -> ZIP_BRIDGE_B -> SILO_C)
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Standard: Invariant 50 / Rule 11 (< 160 lines, ZERO hardcoded nodes)

Reads spatial ground truth dynamically from data/geo_lexicon_registry.json.
Resolves nodes by Composite Key ("95054:NFL:SF"), Team Code ("SF"), or 5-Digit Zip ("95054").
"""
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BASE_DIR = Path(os.getenv("STACKLABS_ROOT", "/home/james/stacklabs"))
GEO_REGISTRY_PATH = BASE_DIR / "data" / "geo_lexicon_registry.json"
SHM_COLLISION_PATH = Path("/dev/shm/swanson_latest_geo_collision.json")

_REGISTRY_CACHE: Dict[str, Dict[str, Any]] = {}
_REGISTRY_MTIME: float = 0.0

def load_geo_registry() -> Dict[str, Dict[str, Any]]:
    """Loads and caches the geo lexicon registry dynamically from disk."""
    global _REGISTRY_CACHE, _REGISTRY_MTIME
    if not GEO_REGISTRY_PATH.exists():
        return {}

    try:
        mtime = GEO_REGISTRY_PATH.stat().st_mtime
        if mtime != _REGISTRY_MTIME or not _REGISTRY_CACHE:
            data = json.loads(GEO_REGISTRY_PATH.read_text(encoding="utf-8"))
            _REGISTRY_CACHE = data.get("nodes", data) if isinstance(data, dict) else {}
            _REGISTRY_MTIME = mtime
    except (ValueError, OSError) as e:
        print(f"[WARN] Failed loading geo registry: {e}")
    return _REGISTRY_CACHE

def resolve_node(query: str, registry: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Dynamically resolves a node by:
    1. Exact composite key (e.g. '95054:NFL:SF')
    2. Team code (e.g. 'SF', 'WSH', 'BYU')
    3. 5-digit zip code (e.g. '95054', '20019')
    """
    if not query:
        return None
    q = query.strip().upper()

    # 1. Exact match
    if q in registry:
        return registry[q]

    # 2. Case-insensitive key match
    for k, node in registry.items():
        if k.upper() == q:
            return node

    # 3. Match team code
    for node in registry.values():
        if str(node.get("team", "")).upper() == q:
            return node

    # 4. Match 5-digit zip code
    for node in registry.values():
        if str(node.get("zip", node.get("zip_5", ""))) == query.strip():
            return node

    return None

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(2.0 * r_earth * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)

def execute_swanson_zip_collision(
    away_query: str,
    home_query: str,
    silo_a_event: str,
    leverage_index: float = 0.85,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    registry = load_geo_registry()

    away_node = resolve_node(away_query, registry) or {
        "team": away_query, "zip": "00000", "city": "Away City", "venue_name": "Away Venue",
        "geo": {"lat": 38.0, "lon": -77.0, "elevation_ft": 50},
        "caloric_fuel": "Generic concession fare", "cultural_taboos": ["Road game passivity"],
        "trauma_register": ["Road underdog fatigue"]
    }
    home_node = resolve_node(home_query, registry) or {
        "team": home_query, "zip": "00000", "city": "Home City", "venue_name": "Home Venue",
        "geo": {"lat": 37.0, "lon": -122.0, "elevation_ft": 50},
        "caloric_fuel": "Home stadium fare", "cultural_taboos": ["Home turf complacency"],
        "trauma_register": ["Home stadium pressure"]
    }

    away_geo = away_node.get("geo") or {"lat": away_node.get("lat", 38.0), "lon": away_node.get("lon", -77.0), "elevation_ft": away_node.get("elevation_ft", 50)}
    home_geo = home_node.get("geo") or {"lat": home_node.get("lat", 37.0), "lon": home_node.get("lon", -122.0), "elevation_ft": home_node.get("elevation_ft", 50)}

    dist_miles = haversine_miles(float(away_geo.get("lat", 38.0)), float(away_geo.get("lon", -77.0)), float(home_geo.get("lat", 37.0)), float(home_geo.get("lon", -122.0)))
    away_zip = str(away_node.get("zip", away_node.get("zip_5", "00000")))
    home_zip = str(home_node.get("zip", home_node.get("zip_5", "00000")))

    if away_zip == home_zip and away_zip != "00000":
        collision_mode, civil_war_multiplier = "SHARED_HYPERVISOR_EVICTION_WAR", 2.50
    elif dist_miles < 25.0:
        collision_mode, civil_war_multiplier = "INTRA_METRO_TRANSIT_CIVIL_WAR", round(1.0 + (1.5 / (1.0 + dist_miles)), 2)
    else:
        collision_mode, civil_war_multiplier = "CROSS_GRID_NODAL_IMPEDANCE", 1.00

    elev_delta_ft = abs(int(home_geo.get("elevation_ft", 0)) - int(away_geo.get("elevation_ft", 0)))
    nodal_congestion_bps = int(round(leverage_index * civil_war_multiplier * 240.0 + (elev_delta_ft * 0.03)))
    elapsed_us = round((time.perf_counter() - t0) * 1_000_000.0, 2)

    # Dynamic advocate lookup from sovereign_now.db
    home_adv, away_adv, home_token = None, None, None
    try:
        import sqlite3
        db_path = BASE_DIR / "dna" / "sovereign_now.db"
        if db_path.exists():
            with sqlite3.connect(str(db_path), timeout=2.0) as conn:
                cur = conn.cursor()
                if home_node.get("team"):
                    r = cur.execute("SELECT handle FROM fanstack_advocates WHERE team = ?", (home_node["team"],)).fetchone()
                    if r: home_adv = r[0]
                if away_node.get("team"):
                    r = cur.execute("SELECT handle FROM fanstack_advocates WHERE team = ?", (away_node["team"],)).fetchone()
                    if r: away_adv = r[0]
    except Exception:
        pass

    home_adv = home_adv or home_node.get("advocate_handle") or f"@{home_node.get('team', 'home').lower()}_fan"
    away_adv = away_adv or away_node.get("advocate_handle") or f"@{away_node.get('team', 'away').lower()}_fan"
    home_token = home_node.get("control_token") or f"<|{home_adv.replace('@', '').lower()}|>"

    payload = {
        "engine": "swanson_geo_cmdb_collider",
        "execution_time_microseconds": elapsed_us,
        "marginal_token_cost_usd": 0.0,
        "silo_a_trigger_event": silo_a_event,
        "bridge_b_composite_coordinates": {
            "away_query": away_query, "home_query": home_query,
            "away_resolved_team": away_node.get("team"), "home_resolved_team": home_node.get("team"),
            "away_zip": away_zip, "home_zip": home_zip,
            "haversine_distance_miles": dist_miles, "elevation_delta_ft": elev_delta_ft,
            "collision_mode": collision_mode, "civil_war_multiplier": civil_war_multiplier,
        },
        "silo_c_bisociated_views": {
            "1_fanstack_dolphin_alu_register": {
                "home_advocate": home_adv, "away_advocate": away_adv,
                "caloric_clash": f"{away_node.get('caloric_fuel')} <=> {home_node.get('caloric_fuel')}",
                "infrastructure_and_taboo_clash": f"[AWAY {away_zip}]: {away_node.get('taboo_lore') or away_node.get('cultural_taboos')} || [HOME {home_zip}]: {home_node.get('taboo_lore') or home_node.get('cultural_taboos')}",
                "dolphin_180_token_prompt": (
                    f"{home_token} [SWANSON_BRIDGE: {away_query} AT {home_query} | MODE: {collision_mode}] "
                    f"[EVENT: {silo_a_event}] [HOME_HEX: {home_node.get('taboo_lore') or home_node.get('cultural_taboos')}] "
                    f"[AWAY_HEX: {away_node.get('taboo_lore') or away_node.get('cultural_taboos')}] "
                    f"[FUEL_CONTRAST: {home_node.get('caloric_fuel')} VS {away_node.get('caloric_fuel')}]"
                ),
            },
            "2_servicenow_cmdb_incident_topology": {
                "parent_location_ci": f"cmdb_ci_location:{home_zip}",
                "facility_ci": home_node.get("cmdb_ci_facility") or f"cmdb_ci_facility:{home_node.get('venue_name', 'stadium').lower().replace(' ', '_')}_{home_zip}",
                "upstream_cmdb_rel_ci_dependencies": home_node.get("cmdb_rel_dependencies") or home_node.get("physical_infrastructure", {}),
                "correlated_root_cause": f"Event '{silo_a_event}' in Silo A bisociated via Bridge {home_zip} to physical facility: {home_node.get('venue_name', 'Local Facility')}"
            },
            "3_pawel_horizon_nodal_arbitrage": {
                "nodal_pair": f"NODE_{away_zip} -> NODE_{home_zip}",
                "synthetic_lmp_congestion_spread_bps": nodal_congestion_bps,
                "blowout_preventer_triggered": nodal_congestion_bps >= 200,
                "asymmetric_bracket": {"stop_loss_pct": -2.5, "profit_target_pct": 5.0, "ratio": "2:1"} if nodal_congestion_bps >= 200 else None,
            },
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        tmp = SHM_COLLISION_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, SHM_COLLISION_PATH)
    except OSError:
        pass

    return payload

if __name__ == "__main__":
    import sys
    away = sys.argv[1] if len(sys.argv) > 1 else "WSH"
    home = sys.argv[2] if len(sys.argv) > 2 else "SF"
    event = sys.argv[3] if len(sys.argv) > 3 else "3rd-and-8: Jayden Daniels scrambles vs Bosa Wide-9; Kittle hamstring check"
    result = execute_swanson_zip_collision(away, home, event, 0.92)
    print(json.dumps(result, indent=2))
