#!/home/james/stacklabs/.venv/bin/python3
"""
Rule 11 Compliant Decoupled Blueprint (< 70 lines)
Exposes the 300-microsecond Swanson Spatial-Cultural & CMDB Zip Collider on Port 3033.
"""
from typing import Any, Dict
from fastapi import APIRouter, Query
from scripts.swanson_geo_cmdb_collider import execute_swanson_zip_collision, load_geo_registry

router = APIRouter(prefix="/api/swanson-geo", tags=["swanson_geo_collider"])

@router.get("/registry")
def get_geo_zip_registry() -> Dict[str, Any]:
    reg = load_geo_registry()
    return {
        "status": "OK",
        "node_count": len(reg),
        "nodes": reg,
    }

@router.get("/collide")
def collide_zip_nodes(
    away: str = Query(default="20019:NFL:WSH", description="Away Composite Zip-Tribe Key"),
    home: str = Query(default="95054:NFL:SF", description="Home Composite Zip-Tribe Key"),
    event: str = Query(
        default="Jayden Daniels 3rd-down scramble vs Nick Bosa Wide-9; Shanahan 21-personnel clock pressure",
        description="Silo A Live Event Trigger",
    ),
    leverage: float = Query(default=0.90, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    return execute_swanson_zip_collision(
        away_key=away,
        home_key=home,
        silo_a_event=event,
        leverage_index=leverage,
    )
