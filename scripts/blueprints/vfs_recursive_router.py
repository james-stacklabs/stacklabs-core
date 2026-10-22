#!/usr/bin/env python3
"""
scripts/blueprints/vfs_recursive_router.py
StackLabs Hardened Recursive VFS Layout Engine Router
Author: James Carroll (Lead Systems Architect, StackLabs LLC)
Target Silicon: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 8, 15, 32, 35, 50
"""

import os
import sys
import stat
import json
import time
import signal
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/vfs/recursive", tags=["vfs-recursive"])

# Canonical base directory for VFS tree
DEFAULT_VFS_ROOT = Path(os.getenv("VFS_BASE_PATH", "/dev/shm/vfs"))
RUNBOOKS_DIR = Path("/home/james/stacklabs/scripts/runbooks")
OUTBOX_RECEIPTS_DIR = Path("/home/james/stacklabs/data/outbox/vfs_actions")
OUTBOX_RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)

# Concurrency semaphore for action execution
ACTION_SEMAPHORE = asyncio.Semaphore(2)

# Pre-approved runbook allowlist: action_id -> relative script path in RUNBOOKS_DIR
RUNBOOK_REGISTRY: Dict[str, str] = {
    "system_pump_cycle": "system_pump_cycle.sh",
    "retina_arbitration_execute": "retina_arbitration_execute.sh"
}


class ActionRequest(BaseModel):
    action_id: str = Field(..., description="Pre-approved runbook ID")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CallerIdentity(BaseModel):
    identity: str
    role: str  # "allocator" | "admin" | "guest"


def get_current_caller(request: Request) -> CallerIdentity:
    """Derive authenticated identity strictly from server headers, never client params."""
    auth_header = request.headers.get("Authorization", "")
    api_key = request.headers.get("X-StackLabs-Key", "")
    expected_token = os.getenv("VFS_AUTH_TOKEN", "stacklabs_metal_pawel_2026")

    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif api_key:
        token = api_key.strip()

    if token and token == expected_token:
        return CallerIdentity(identity="pawel", role="allocator")
    return CallerIdentity(identity="guest", role="guest")


def resolve_safe_path(rel_path: str, base_root: Path = DEFAULT_VFS_ROOT) -> Path:
    """Strictly resolve and normalize path, preventing directory traversal escaping root."""
    clean_rel = rel_path.strip().lstrip("/")
    base_resolved = base_root.resolve()
    target = (base_resolved / clean_rel).resolve()

    if not target.is_relative_to(base_resolved):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal detected")
    return target


def check_vfs_access(path: Path, caller: CallerIdentity) -> None:
    """Enforce access boundaries across browse, read, and execute."""
    # Hidden files or folders with '_vault' or '.restricted' require non-guest role
    is_vault = "_vault" in path.parts or any(p.startswith(".") for p in path.parts)
    if is_vault and caller.role == "guest":
        raise HTTPException(status_code=404, detail="Resource not found")


def classify_leaf_type(path: Path) -> str:
    """Classify file extension into deterministic UI leaf primitive."""
    suffix = path.suffix.lower()
    if suffix in [".stream", ".m3u8"]:
        return "stream"
    if suffix == ".mp4":
        return "video"
    if suffix in [".tail", ".wal", ".log"]:
        return "tail"
    if suffix in [".md", ".txt"]:
        return "doc"
    if suffix == ".json":
        return "json"
    if suffix == ".action":
        return "action"
    return "file"


@router.get("/browse")
def browse_vfs_path(
    path: str = Query("", description="Relative path within VFS"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    caller: CallerIdentity = Depends(get_current_caller)
) -> Dict[str, Any]:
    """Browse a directory level in the VFS tree with pagination and auth gates."""
    target = resolve_safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path '{path}' not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path '{path}' is a leaf, not a container")

    check_vfs_access(target, caller)

    rel_from_root = target.relative_to(DEFAULT_VFS_ROOT.resolve())
    parts = [p for p in rel_from_root.parts if p and p != "."]
    breadcrumbs = [{"label": "ROOT", "path": ""}]
    accumulated = ""
    for part in parts:
        accumulated = f"{accumulated}/{part}".lstrip("/")
        breadcrumbs.append({"label": part.upper(), "path": accumulated})

    raw_containers: List[Dict[str, Any]] = []
    raw_leaves: List[Dict[str, Any]] = []

    try:
        with os.scandir(target) as entries:
            sorted_entries = sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in sorted_entries:
                if entry.name.startswith("."):
                    continue

                entry_path = Path(entry.path)
                is_symlink = entry.is_symlink()

                # Handle broken or unreadable symlinks gracefully
                try:
                    entry_stat = entry.stat(follow_symlinks=True)
                    is_dir = entry.is_dir(follow_symlinks=True)
                    is_dangling = False
                except OSError:
                    entry_stat = None
                    is_dir = False
                    is_dangling = True

                rel_entry_path = str(entry_path.relative_to(DEFAULT_VFS_ROOT.resolve()))

                # Apply vault restriction check
                if "_vault" in entry_path.parts and caller.role == "guest":
                    continue

                if is_dangling:
                    raw_leaves.append({
                        "name": entry.name,
                        "label": f"{entry.name} [BROKEN LINK]",
                        "path": rel_entry_path,
                        "extension": entry_path.suffix,
                        "leaf_type": "dangling",
                        "size_bytes": 0,
                        "is_symlink": True,
                        "type": "leaf"
                    })
                elif is_dir:
                    raw_containers.append({
                        "name": entry.name,
                        "label": entry.name.replace("_", " ").upper(),
                        "path": rel_entry_path,
                        "is_symlink": is_symlink,
                        "target_link": os.readlink(entry.path) if is_symlink else None,
                        "type": "container"
                    })
                else:
                    leaf_type = classify_leaf_type(entry_path)
                    raw_leaves.append({
                        "name": entry.name,
                        "label": entry_path.stem.replace("_", " ").title(),
                        "path": rel_entry_path,
                        "extension": entry_path.suffix,
                        "leaf_type": leaf_type,
                        "size_bytes": entry_stat.st_size if entry_stat else 0,
                        "is_symlink": is_symlink,
                        "type": "leaf"
                    })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to access directory")

    total_containers = len(raw_containers)
    total_leaves = len(raw_leaves)
    total_nodes = total_containers + total_leaves

    # Paginate across combined view
    paged_containers = raw_containers[offset: offset + limit]
    remaining_limit = max(0, limit - len(paged_containers))
    leaves_offset = max(0, offset - total_containers)
    paged_leaves = raw_leaves[leaves_offset: leaves_offset + remaining_limit]

    return {
        "status": "ok",
        "current_path": str(rel_from_root) if str(rel_from_root) != "." else "",
        "caller": {"identity": caller.identity, "role": caller.role},
        "breadcrumbs": breadcrumbs,
        "containers": paged_containers,
        "leaves": paged_leaves,
        "pagination": {
            "total_nodes": total_nodes,
            "total_containers": total_containers,
            "total_leaves": total_leaves,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total_nodes
        }
    }


@router.get("/read")
def read_vfs_leaf(
    path: str = Query(..., description="Relative path to file leaf"),
    tail_lines: int = Query(50, ge=1, le=500, description="Lines to read if tail leaf"),
    caller: CallerIdentity = Depends(get_current_caller)
) -> Dict[str, Any]:
    """Read contents of a scalar file, media metadata, or optimized log tail."""
    target = resolve_safe_path(path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File leaf not found")

    check_vfs_access(target, caller)
    leaf_type = classify_leaf_type(target)

    try:
        if leaf_type in ["doc", "json", "file", "action"]:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(65536)  # 64KB bounded cap
            return {
                "status": "ok",
                "path": path,
                "leaf_type": leaf_type,
                "content": content
            }
        elif leaf_type == "tail":
            # Optimized reverse seek: read only trailing 64KB without loading full file
            file_size = target.stat().st_size
            seek_pos = max(0, file_size - 65536)
            with open(target, "rb") as f:
                f.seek(seek_pos)
                raw_bytes = f.read()
            decoded = raw_bytes.decode("utf-8", errors="replace")
            lines = decoded.splitlines()
            trimmed = "\n".join(lines[-tail_lines:])
            return {
                "status": "ok",
                "path": path,
                "leaf_type": "tail",
                "content": trimmed,
                "lines_returned": min(len(lines), tail_lines)
            }
        elif leaf_type == "stream":
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                raw_url = f.read().strip()
            # Sanitize RTSP credentials before transmitting to client
            sanitized_url = raw_url
            if sanitized_url.startswith("rtsp://") and "@" in sanitized_url:
                prefix = sanitized_url.split("@")[0]
                host_part = sanitized_url.split("@")[1]
                sanitized_url = f"rtsp://***:***@{host_part}"
            return {
                "status": "ok",
                "path": path,
                "leaf_type": "stream",
                "stream_url": sanitized_url
            }
        elif leaf_type == "video":
            return {
                "status": "ok",
                "path": path,
                "leaf_type": "video",
                "media_url": f"/api/vfs/media?path={path}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    raise HTTPException(status_code=400, detail="Unsupported leaf type")


@router.post("/execute_action")
async def execute_vfs_action(
    req: ActionRequest,
    caller: CallerIdentity = Depends(get_current_caller)
) -> Dict[str, Any]:
    """
    Execute an action leaf strictly through the pre-approved Runbook Registry.
    Guarantees process group isolation, sanitized minimal env, and audit outbox receipt.
    """
    if caller.role not in ["allocator", "admin"]:
        raise HTTPException(status_code=403, detail="Forbidden: Action execution requires authenticated role")

    if req.action_id not in RUNBOOK_REGISTRY:
        raise HTTPException(status_code=403, detail=f"Forbidden: Action '{req.action_id}' is not in the approved Runbook Registry")

    script_rel_path = RUNBOOK_REGISTRY[req.action_id]
    script_target = (RUNBOOKS_DIR / script_rel_path).resolve()

    if not script_target.exists() or not script_target.is_file():
        raise HTTPException(status_code=500, detail="Allowlisted runbook executable missing on metal")

    # Acquire concurrency lock (max 2 concurrent actions)
    async with ACTION_SEMAPHORE:
        minimal_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "STACKLABS_CALLER_IDENTITY": caller.identity,
            "STACKLABS_ACTION_ID": req.action_id,
            "STACKLABS_ACTION_PARAMS": json.dumps(req.parameters)
        }

        start_time = time.time()
        try:
            proc = subprocess.Popen(
                ["/bin/bash", str(script_target)],
                env=minimal_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True
            )

            try:
                stdout_data, stderr_data = proc.communicate(timeout=10.0)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                stdout_data, stderr_data = proc.communicate()
                raise HTTPException(status_code=504, detail="Runbook execution timed out after 10.0s")

            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            stdout_bounded = stdout_data[:16384].strip()
            stderr_bounded = stderr_data[:16384].strip()

            receipt = {
                "receipt_id": f"rcpt_{int(time.time() * 1000)}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "caller_identity": caller.identity,
                "caller_role": caller.role,
                "action_id": req.action_id,
                "parameters": req.parameters,
                "returncode": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "stdout": stdout_bounded,
                "stderr": stderr_bounded
            }

            # Atomically persist outbox receipt on NVMe
            receipt_file = OUTBOX_RECEIPTS_DIR / f"{receipt['receipt_id']}.json"
            receipt_tmp = receipt_file.with_suffix(".tmp")
            receipt_tmp.write_text(json.dumps(receipt, indent=2))
            receipt_tmp.replace(receipt_file)

            return {
                "status": "success" if proc.returncode == 0 else "error",
                "receipt_id": receipt["receipt_id"],
                "returncode": proc.returncode,
                "elapsed_ms": elapsed_ms,
                "stdout": stdout_bounded,
                "stderr": stderr_bounded
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to execute runbook: {str(e)}")
