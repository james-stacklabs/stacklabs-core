#!/usr/bin/env python3
"""
Sovereign OS: MARD Autonomous Agentic Coding Assembly Line Router
Path: /home/james/stacklabs/scripts/routers/assembly.py
Ticket: WO0010081-MARD-AGENTIC-CODING-ASSEMBLY-LINE
Affected CI: sovereign_knot_core / mard_assembly_line
Mounted on: SDLC Portal Server (Port 8095)

REST Endpoints:
  - POST /api/assembly/dispatch          : Initialize and dispatch a new 5-station assembly run
  - GET  /api/assembly/runs              : Query recent assembly runs (state filtering, limit)
  - GET  /api/assembly/runs/{run_id}     : Fetch full run telemetry and station artifacts
  - POST /api/assembly/runs/{run_id}/step: Advance assembly run to the next station
  - POST /api/assembly/runs/{run_id}/run : Execute all stations to completion or circuit trip
  - POST /api/assembly/runs/{run_id}/reset: Reset tripped circuit breaker with optional new brief
  - GET  /api/assembly/health            : Engine health and station capabilities manifest
"""

import sys
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

if "/home/james/stacklabs" not in sys.path:
    sys.path.insert(0, "/home/james/stacklabs")
if "/home/james/stacklabs/scripts" not in sys.path:
    sys.path.insert(0, "/home/james/stacklabs/scripts")

try:
    from core.assembly_pipeline_engine import assembly_engine, STATION_NAMES
except ImportError:
    from scripts.core.assembly_pipeline_engine import assembly_engine, STATION_NAMES

logger = logging.getLogger("assembly_router")
router = APIRouter(prefix="/api/assembly", tags=["Agentic Coding Assembly Line"])


# ---------------------------------------------------------------------------
# Pydantic Request / Response Models
# ---------------------------------------------------------------------------

class DispatchRequest(BaseModel):
    ticket_id: str = Field(..., description="SDLC ticket number or hybrid ID (e.g. WO0010081-ASSEMBLY-LINE)")
    brief: str = Field(..., description="Technical requirement brief / problem statement")
    assigned_model: Optional[str] = Field("gemini-3.5-flash", description="Assigned LLM model identifier")
    max_retries: Optional[int] = Field(3, description="Max QA retries before circuit breaker trips")
    execution_node: Optional[str] = Field("clio", description="Host execution node (clio or pegasus)")
    auto_run: Optional[bool] = Field(False, description="Whether to immediately step through all stations")


class ResetCircuitRequest(BaseModel):
    new_brief: Optional[str] = Field(None, description="Optional refined requirement brief for retry")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def assembly_health() -> Dict[str, Any]:
    """Return health status and station capabilities manifest."""
    return {
        "status": "ONLINE",
        "subsystem": "MARD Autonomous Agentic Coding Assembly Line",
        "version": "1.0.0",
        "stations": STATION_NAMES,
        "circuit_breaker_limit": 3,
        "supported_models": [
            "gemini-3.5-flash",
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "claude-3-7-sonnet"
        ]
    }


@router.post("/dispatch")
def dispatch_run(req: DispatchRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Initialize a new 5-station assembly line run for an SDLC ticket."""
    try:
        run = assembly_engine.create_run(
            ticket_id=req.ticket_id,
            brief=req.brief,
            assigned_model=req.assigned_model or "gemini-3.5-flash",
            max_retries=req.max_retries or 3,
            execution_node=req.execution_node or "clio"
        )
        run_id = run["run_id"]

        if req.auto_run:
            logger.info(f"Auto-run requested for {run_id}. Starting background execution...")
            background_tasks.add_task(assembly_engine.run_pipeline, run_id)
            return {
                "message": f"Assembly run {run_id} initialized and auto-running in background.",
                "run_id": run_id,
                "status": "RUNNING",
                "run": run
            }

        return {
            "message": f"Assembly run {run_id} created in PENDING state.",
            "run_id": run_id,
            "status": run["current_state"],
            "run": run
        }
    except Exception as e:
        logger.error(f"Failed to dispatch assembly run: {e}")
        raise HTTPException(status_code=500, detail=f"Dispatch failure: {str(e)}")


@router.get("/runs")
def list_runs(
    limit: int = Query(50, ge=1, le=200, description="Max runs to return"),
    state: Optional[str] = Query(None, description="Filter by state (e.g. COMPLETED, CIRCUIT_TRIPPED, CODING)")
) -> List[Dict[str, Any]]:
    """List recent assembly line runs."""
    try:
        return assembly_engine.list_runs(limit=limit, state=state)
    except Exception as e:
        logger.error(f"Failed to list assembly runs: {e}")
        raise HTTPException(status_code=500, detail=f"Query failure: {str(e)}")


@router.get("/runs/{run_id}")
def get_run_details(run_id: str) -> Dict[str, Any]:
    """Fetch complete telemetry, current state, and immutable artifacts for a run."""
    try:
        return assembly_engine.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Assembly run not found: {run_id}")
    except Exception as e:
        logger.error(f"Failed to get assembly run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/{run_id}/step")
def step_station(run_id: str) -> Dict[str, Any]:
    """Advance the assembly run to the next station in the 5-station pipeline."""
    try:
        updated_run = assembly_engine.step_next(run_id)
        return {
            "message": f"Run {run_id} stepped to state: {updated_run['current_state']}",
            "current_station": updated_run["current_station"],
            "station_name": STATION_NAMES.get(updated_run["current_station"], "Unknown"),
            "current_state": updated_run["current_state"],
            "run": updated_run
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Assembly run not found: {run_id}")
    except PermissionError as pe:
        logger.error(f"Security/Immutability invariant violation in run {run_id}: {pe}")
        raise HTTPException(status_code=403, detail=f"INVARIANT VIOLATION: {str(pe)}")
    except Exception as e:
        logger.error(f"Station step failed for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Step execution failure: {str(e)}")


@router.post("/runs/{run_id}/run")
def execute_pipeline(run_id: str) -> Dict[str, Any]:
    """Execute all stations sequentially until terminal state (COMPLETED or CIRCUIT_TRIPPED)."""
    try:
        final_run = assembly_engine.run_pipeline(run_id)
        return {
            "message": f"Pipeline execution finished with state: {final_run['current_state']}",
            "run_id": run_id,
            "final_state": final_run["current_state"],
            "retry_count": final_run["retry_count"],
            "run": final_run
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Assembly run not found: {run_id}")
    except Exception as e:
        logger.error(f"Pipeline run failed for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runs/{run_id}/reset")
def reset_circuit_breaker(run_id: str, req: ResetCircuitRequest) -> Dict[str, Any]:
    """Reset a tripped circuit breaker to allow fresh attempts with optional new brief."""
    try:
        updated_run = assembly_engine.reset_circuit(run_id, new_brief=req.new_brief)
        return {
            "message": f"Circuit breaker reset for run {run_id}. Status set to CODING with retry_count=0.",
            "run": updated_run
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Assembly run not found: {run_id}")
    except Exception as e:
        logger.error(f"Failed to reset circuit for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}/artifacts")
def get_run_artifacts(
    run_id: str,
    station_id: Optional[int] = Query(None, ge=1, le=5, description="Filter by station (1-5)"),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type")
) -> List[Dict[str, Any]]:
    """Retrieve immutable artifact breadcrumbs for an assembly run."""
    try:
        run = assembly_engine.get_run(run_id)
        artifacts = run.get("artifacts", [])
        if station_id:
            artifacts = [a for a in artifacts if a["station_id"] == station_id]
        if artifact_type:
            artifacts = [a for a in artifacts if a["artifact_type"] == artifact_type]
        return artifacts
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Assembly run not found: {run_id}")
    except Exception as e:
        logger.error(f"Failed to retrieve artifacts for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
