from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import datetime, timezone
from pathlib import Path

from core.sovereign_code_hygiene_sentinel import SovereignHygieneSentinel

router = APIRouter(prefix="/api/hygiene", tags=["Hygiene Sentinel"])

class AuditRequest(BaseModel):
    target: str = "."
    fail_fast: bool = False

class ExportRequest(BaseModel):
    target: str = "."
    markdown_content: Optional[str] = None

PRESET_TARGETS = [
    {
        "id": "repo_root",
        "label": "Entire Repository",
        "path": ".",
        "badge": "GLOBAL",
        "color": "cyan",
        "description": "Full scan of all Python, TypeScript, React, and Shell scripts across Sovereign OS."
    },
    {
        "id": "backend_scripts",
        "label": "Backend Scripts & Daemons",
        "path": "scripts/",
        "badge": "BACKEND",
        "color": "emerald",
        "description": "Scans all daemons, TMI engine, MARD cartridge runner, and worker scripts."
    },
    {
        "id": "api_routers",
        "label": "FastAPI REST Routers",
        "path": "scripts/routers/",
        "badge": "REST API",
        "color": "indigo",
        "description": "Audits FastAPI endpoints for raw DB bypasses and proper error handling."
    },
    {
        "id": "sports_portal",
        "label": "19_FanStackArena",
        "path": "19_FanStackArena/src/",
        "badge": "FRONTEND",
        "color": "amber",
        "description": "Audits FanStack sports portal, 3D arcade games, and Statcast particle canvases."
    },
    {
        "id": "creator_studio",
        "label": "15_FanStackCreator",
        "path": "15_FanStackCreator/src/",
        "badge": "CREATOR",
        "color": "cyan",
        "description": "Audits FanStack Creator studio, lookbook emote forge, and playcall desk."
    },
    {
        "id": "catnip_wars",
        "label": "25_CatnipWars",
        "path": "25_CatnipWars/src/",
        "badge": "RETRO ARCADE",
        "color": "orange",
        "description": "Audits 16-bit Smyrna syndicate brawler, NipStack cards, and anti-cyberpunk compliance."
    },
    {
        "id": "sovereign_portal",
        "label": "01_Sovereign_Portal",
        "path": "01_Sovereign_Portal/src/",
        "badge": "COCKPIT",
        "color": "purple",
        "description": "Audits Executive Command Center, Kanban board, and CMDB inspectors."
    },
    {
        "id": "cmdb_studio",
        "label": "25_CmdbStudio",
        "path": "25_CmdbStudio/src/",
        "badge": "CMDB",
        "color": "blue",
        "description": "Audits CMDB Configuration Item matrix and Multi-LL OS control room."
    }
]

@router.get("/presets")
async def get_audit_presets():
    """Retrieve canonical preset targets for 1-click scanning."""
    return {"presets": PRESET_TARGETS}

@router.post("/audit")
async def run_hygiene_audit(req: AuditRequest):
    """Execute static code hygiene analysis on requested target."""
    repo_root = Path("/home/james/stacklabs")
    target_clean = req.target.strip()
    
    # Resolve relative or absolute path
    if os.path.isabs(target_clean):
        target_path = Path(target_clean)
    else:
        target_path = repo_root / target_clean

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Target path '{target_clean}' does not exist.")

    sentinel = SovereignHygieneSentinel(repo_root=str(repo_root))
    violations = sentinel.scan_path(str(target_path))
    
    # Calculate stats
    criticals = [v._asdict() for v in violations if v.severity == "CRITICAL"]
    majors = [v._asdict() for v in violations if v.severity == "MAJOR"]
    minors = [v._asdict() for v in violations if v.severity == "MINOR"]

    if criticals or majors:
        verdict = "REJECTED"
    elif violations:
        verdict = "WARNINGS"
    else:
        verdict = "PASS"

    markdown_report = sentinel.generate_report(target_clean, violations, as_json=False)

    return {
        "target": target_clean,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "metrics": {
            "total_violations": len(violations),
            "critical_count": len(criticals),
            "major_count": len(majors),
            "minor_count": len(minors)
        },
        "violations": [v._asdict() for v in violations],
        "markdown_report": markdown_report
    }

@router.post("/export")
async def export_hygiene_report(req: ExportRequest):
    """Save an official Markdown audit report into sovereign_inbox/reports/."""
    target_clean = req.target.replace("/", "_").replace(".", "ROOT").strip("_")
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"CODE_HYGIENE_AUDIT_{target_clean}_{date_str}.md"
    out_dir = Path("/home/james/sovereign_inbox/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename

    if req.markdown_content:
        content = req.markdown_content
    else:
        repo_root = Path("/home/james/stacklabs")
        sentinel = SovereignHygieneSentinel(repo_root=str(repo_root))
        target_path = repo_root / req.target
        violations = sentinel.scan_path(str(target_path))
        content = sentinel.generate_report(req.target, violations, as_json=False)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "exported",
        "file_path": str(out_file),
        "filename": filename
    }
