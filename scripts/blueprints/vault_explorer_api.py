#!/home/james/stacklabs/.venv/bin/python3
"""
FastAPI Blueprint: StackLabs Vault Explorer & Curated IDE Brain Harvester API (Decoupled Index Plane)
Mounted on scripts/synapse_bus.py (Port 8088) under /api/cockpit/vault/*
Supports sub-millisecond tree/folder/search queries plus 1-click Sprint Promotion (/api/cockpit/vault/promote_to_sprint).
"""

import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from scripts.artifact_harvester import (
    VAULT_ROOT,
    STACKLABS_ROOT,
    SECONDARY_ROOT,
    BRAIN_ROOT,
    SEARCH_INDEX_PATH,
    CATEGORY_META,
    build_vault_navigator,
    compile_decoupled_search_index,
    audit_brain_markdown_candidate,
    _extract_markdown_title,
    _human_size,
    _slugify,
)

EDT = ZoneInfo("America/New_York")
vault_explorer_router = APIRouter(tags=["vault_explorer"])

_INDEX_CACHE = {
    "mtime_ns": 0,
    "data": None,
}


class PromoteToSprintRequest(BaseModel):
    path: str
    target_filename: Optional[str] = None
    sprint_date: Optional[str] = None


def _get_cached_index() -> dict:
    if not SEARCH_INDEX_PATH.exists():
        build_vault_navigator(harvest_brain=False)
    try:
        st_ns = SEARCH_INDEX_PATH.stat().st_mtime_ns
    except OSError:
        st_ns = 0

    if _INDEX_CACHE["data"] is None or _INDEX_CACHE["mtime_ns"] != st_ns:
        raw = json.loads(SEARCH_INDEX_PATH.read_text(encoding="utf-8"))
        _INDEX_CACHE["data"] = raw
        _INDEX_CACHE["mtime_ns"] = st_ns
    return _INDEX_CACHE["data"]


def _is_safe_path(target: Path) -> bool:
    try:
        resolved = target.resolve()
    except Exception:
        return False
    allowed_roots = [
        STACKLABS_ROOT.resolve(),
        SECONDARY_ROOT.resolve(),
        BRAIN_ROOT.resolve(),
    ]
    return any(str(resolved).startswith(str(r)) for r in allowed_roots if r.exists())


@vault_explorer_router.get("/api/cockpit/vault/tree")
def get_vault_tree():
    t0 = time.perf_counter()
    idx = _get_cached_index()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "status": "ok",
        "index_source": "decoupled_vault_search_index",
        "compiled_at": idx.get("compiled_at", ""),
        "vault_root": idx.get("vault_root", str(VAULT_ROOT)),
        "total_files": idx.get("total_files", 0),
        "latency_ms": elapsed_ms,
        "categories": idx.get("categories", []),
    }


@vault_explorer_router.get("/api/cockpit/vault/folder")
def get_vault_folder_files(
    category: str = Query(..., description="Category ID, e.g. 01_Daily_Sprints"),
    subcategory: str = Query("", description="Optional subfolder name"),
    limit: int = Query(150, ge=1, le=500),
):
    t0 = time.perf_counter()
    idx = _get_cached_index()
    cat_files = idx.get("files_by_category", {}).get(category)
    if cat_files is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    if subcategory:
        filtered = [
            f for f in cat_files
            if f.get("subcategory") == subcategory or f.get("rel_path", "").startswith(f"{subcategory}/")
        ]
    else:
        filtered = list(cat_files)

    seen = set()
    deduped = []
    for f in filtered:
        if f["abs_path"] not in seen:
            seen.add(f["abs_path"])
            deduped.append(f)
        if len(deduped) >= limit:
            break

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "status": "ok",
        "index_source": "decoupled_vault_search_index",
        "category": category,
        "subcategory": subcategory,
        "count": len(deduped),
        "latency_ms": elapsed_ms,
        "files": deduped,
    }


@vault_explorer_router.get("/api/cockpit/vault/search")
def search_vault(
    q: str = Query("", description="Search query across filenames, titles, and content"),
    category: str = Query("ALL", description="Category filter or ALL"),
    limit: int = Query(80, ge=1, le=250),
):
    t0 = time.perf_counter()
    idx = _get_cached_index()
    query = q.strip().lower()
    tokens = [t for t in re.split(r"\s+", query) if t]

    cats_to_scan = [c["id"] for c in CATEGORY_META if category in ("ALL", "", c["id"])]
    files_by_cat = idx.get("files_by_category", {})

    matches = []
    seen_paths = set()

    for cat_id in cats_to_scan:
        for item in files_by_cat.get(cat_id, []):
            abs_p = item["abs_path"]
            if abs_p in seen_paths:
                continue

            if not tokens:
                seen_paths.add(abs_p)
                matches.append({**item, "score": 1, "snippet": item["rel_path"]})
                continue

            hay_name = f"{item['name']} {item['title']} {item['rel_path']}".lower()
            score = 0
            snippet = ""

            if all(tok in hay_name for tok in tokens):
                score += 10
                snippet = f"Matched indexed title/path: {item['rel_path']}"
            elif item["size_bytes"] <= 256 * 1024:
                try:
                    content = Path(abs_p).read_text(encoding="utf-8", errors="ignore")
                    content_lower = content.lower()
                    if all(tok in content_lower for tok in tokens):
                        score += 4
                        pos = content_lower.find(tokens[0])
                        start = max(0, pos - 60)
                        end = min(len(content), pos + 140)
                        raw_snip = content[start:end].replace("\n", " ").strip()
                        snippet = f"...{raw_snip}..."
                except Exception:
                    pass

            if score > 0:
                seen_paths.add(abs_p)
                matches.append({**item, "score": score, "snippet": snippet})

    matches.sort(key=lambda x: (x["score"], x["mtime"]), reverse=True)
    trimmed = matches[:limit]
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "status": "ok",
        "index_source": "decoupled_vault_search_index",
        "query": q,
        "category": category,
        "count": len(trimmed),
        "latency_ms": elapsed_ms,
        "results": trimmed,
    }


@vault_explorer_router.get("/api/cockpit/vault/file")
def read_vault_file(path: str = Query(..., description="Absolute path to file in vault")):
    target = Path(path)
    if not target.exists() or not target.is_file() or not _is_safe_path(target):
        raise HTTPException(status_code=404, detail="Requested file is outside allowed vault paths or does not exist.")

    st = target.stat()
    ext = target.suffix.lower()
    title = _extract_markdown_title(target) if ext == ".md" else target.name
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    lines = content.count("\n") + 1
    dt_str = datetime.fromtimestamp(st.st_mtime, tz=EDT).strftime("%Y-%m-%d %H:%M:%S EDT")

    return {
        "status": "ok",
        "name": target.name,
        "title": title,
        "abs_path": str(target.resolve()),
        "ext": ext,
        "size_human": _human_size(st.st_size),
        "line_count": lines,
        "mtime_edt": dt_str,
        "content": content[:250000],
    }


@vault_explorer_router.post("/api/cockpit/vault/harvest")
def trigger_vault_harvest():
    t0 = time.perf_counter()
    summary = build_vault_navigator(harvest_brain=True)
    _INDEX_CACHE["mtime_ns"] = 0
    _get_cached_index()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        **summary,
        "latency_ms": elapsed_ms,
    }


@vault_explorer_router.post("/api/cockpit/vault/promote_to_sprint")
def promote_vault_file_to_sprint(req: PromoteToSprintRequest):
    t0 = time.perf_counter()
    src_path = Path(req.path)
    if not src_path.exists() or not src_path.is_file() or not _is_safe_path(src_path):
        raise HTTPException(status_code=404, detail="Source file not found or outside allowed vault roots.")

    if src_path.suffix.lower() == ".md":
        violations = audit_brain_markdown_candidate(src_path)
        if violations:
            raise HTTPException(
                status_code=422,
                detail=f"GANDALF Linter Gate blocked sprint promotion: {'; '.join(violations[:3])}",
            )

    sprint_slug = (
        f"daily_sprint_{req.sprint_date.replace('-', '_')}"
        if req.sprint_date
        else datetime.now(EDT).strftime("daily_sprint_%Y_%m_%d")
    )

    if req.target_filename:
        dest_name = req.target_filename if req.target_filename.endswith(src_path.suffix) else f"{req.target_filename}{src_path.suffix}"
    elif src_path.suffix.lower() == ".md":
        title = _extract_markdown_title(src_path)
        slug = _slugify(title, max_len=56).upper()
        dest_name = f"03_{slug}.md"
    else:
        dest_name = src_path.name

    docs_sprint = STACKLABS_ROOT / "docs" / sprint_slug
    art_sprint = STACKLABS_ROOT / "artifacts" / "sprints" / sprint_slug
    nb_sprint = SECONDARY_ROOT / "notebook_sync" / "StackLabs_Internal" / sprint_slug
    downloads_dir = STACKLABS_ROOT / "pilot_drops" / "downloads"

    promoted_targets = []
    for folder in (docs_sprint, art_sprint, nb_sprint, downloads_dir):
        folder.mkdir(parents=True, exist_ok=True)
        dst = folder / dest_name
        shutil.copy2(src_path, dst)
        promoted_targets.append(str(dst))

    compile_decoupled_search_index()
    _INDEX_CACHE["mtime_ns"] = 0
    _get_cached_index()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    return {
        "status": "ok",
        "sprint_folder": sprint_slug,
        "promoted_filename": dest_name,
        "source_path": str(src_path),
        "promoted_targets": promoted_targets,
        "latency_ms": elapsed_ms,
    }
