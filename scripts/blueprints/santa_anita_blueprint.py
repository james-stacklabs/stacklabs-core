#!/usr/bin/env python3
"""
Santa Anita Four Pillars Blueprint
Exposes lightweight, non-blocking endpoints for VFS Four Pillars.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Add project root and scripts directory to path
PROJECT_ROOT = Path("/home/james/stacklabs")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from santa_anita_evaluator import evaluate_and_project_vfs, read_current_pillars

router = APIRouter(prefix="/api/vfs/santa_anita", tags=["Santa Anita"])

class RaceEvaluateRequest(BaseModel):
    race_data: str

@router.get("/pillars")
def get_pillars():
    try:
        return read_current_pillars()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate")
def evaluate_race(req: RaceEvaluateRequest):
    try:
        res = evaluate_and_project_vfs(req.race_data)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
