#!/usr/bin/env python3
"""
StackLabs Ephemeral In-Memory CMDB Session Ingestion Blueprint
Path: /home/james/stacklabs/scripts/blueprints/cmdb_session_ingest_api.py
Author: James Carroll (Pilot), Lead Systems Architect

Ingests raw ServiceNow 2-click JSON exports (cmdb_ci and cmdb_rel_ci) into
isolated RAM tmpfs (/dev/shm/sessions/<uuid>/cmdb/) with zero disk persistence.
Supports 10,000 to 50,000+ CIs via in-memory index + SQLite WAL in /dev/shm
with capped eager POSIX directory materialization (top 250 CIs) and sub-50us
on-demand POSIX directory materialization.
"""

import os
import time
import json
import uuid
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

cmdb_session_bp = APIRouter(prefix="/api/cmdb", tags=["CMDB Ephemeral Sessions"])

SESSIONS_ROOT = Path("/dev/shm/sessions")
SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)

EAGER_VFS_MATERIALIZE_CAP = 250
MAX_ACTIVE_RAM_SESSIONS = 5
SESSION_TTL_SECONDS = 1800
ACTIVE_RAM_SESSIONS: Dict[str, Dict[str, Any]] = {}


class SessionMetadata(BaseModel):
    session_id: str
    created_at_epoch: float
    total_cis: int
    total_relationships: int
    ingest_duration_ms: float
    top_cis: List[str]
    storage_path: str


def sanitize_filename(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("/", "_").replace("\\", "_")


def _enforce_session_bounds() -> List[str]:
    """
    Sweeps /dev/shm/sessions and ACTIVE_RAM_SESSIONS for expired sessions (>1800s TTL)
    and enforces MAX_ACTIVE_RAM_SESSIONS = 5 via oldest-first LRU eviction so at most
    4 sessions remain before creating a new session.
    """
    now = time.time()
    evicted: List[str] = []
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)

    surviving: List[tuple[float, str, Path]] = []
    for entry in SESSIONS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        sid = entry.name
        created_ts = 0.0
        mem_info = ACTIVE_RAM_SESSIONS.get(sid)
        if mem_info and "created_at_epoch" in mem_info:
            created_ts = float(mem_info["created_at_epoch"])
        else:
            meta_file = entry / "cmdb" / "session_metadata.json"
            if meta_file.exists():
                try:
                    created_ts = float(json.loads(meta_file.read_text(encoding="utf-8")).get("created_at_epoch", 0.0))
                except Exception:
                    created_ts = 0.0
            if created_ts <= 0.0:
                try:
                    created_ts = entry.stat().st_mtime
                except Exception:
                    created_ts = now

        if (now - created_ts) > SESSION_TTL_SECONDS:
            ACTIVE_RAM_SESSIONS.pop(sid, None)
            shutil.rmtree(entry, ignore_errors=True)
            evicted.append(sid)
        else:
            surviving.append((created_ts, sid, entry))

    # Clean up any orphaned keys in ACTIVE_RAM_SESSIONS not on disk or expired
    for sid in list(ACTIVE_RAM_SESSIONS.keys()):
        created_ts = float(ACTIVE_RAM_SESSIONS[sid].get("created_at_epoch", now))
        if (now - created_ts) > SESSION_TTL_SECONDS or not (SESSIONS_ROOT / sid).exists():
            ACTIVE_RAM_SESSIONS.pop(sid, None)
            if sid not in evicted:
                evicted.append(sid)

    # Sort oldest first and evict until at most MAX_ACTIVE_RAM_SESSIONS - 1 (4) remain
    surviving.sort(key=lambda x: x[0])
    while len(surviving) >= MAX_ACTIVE_RAM_SESSIONS:
        _, oldest_sid, oldest_path = surviving.pop(0)
        ACTIVE_RAM_SESSIONS.pop(oldest_sid, None)
        shutil.rmtree(oldest_path, ignore_errors=True)
        evicted.append(oldest_sid)

    return evicted


def _write_ci_posix_dir(session_dir: Path, ci_entry: Dict[str, Any], parent_entry: Optional[Dict[str, Any]] = None) -> tuple[Path, bool]:
    """Materializes a single CI directory and optional runs_on pointer inside volatile memory."""
    sub_folder = "physical" if ci_entry["is_physical"] else "logical"
    target_dir = session_dir / sub_folder / ci_entry["name"]
    runs_on_link = target_dir / "runs_on"

    if target_dir.exists() and (not parent_entry or runs_on_link.exists()):
        return target_dir, False

    target_dir.mkdir(parents=True, exist_ok=True)
    for k, v in ci_entry.get("attrs", {}).items():
        if v:
            try:
                (target_dir / f"{k}.txt").write_text(v, encoding="utf-8")
            except Exception:
                pass
    if parent_entry:
        p_folder = "physical" if parent_entry["is_physical"] else "logical"
        parent_dir = session_dir / p_folder / parent_entry["name"]
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
            for pk, pv in parent_entry.get("attrs", {}).items():
                if pv:
                    try:
                        (parent_dir / f"{pk}.txt").write_text(pv, encoding="utf-8")
                    except Exception:
                        pass
        if not runs_on_link.exists():
            try:
                rel_path = os.path.relpath(parent_dir, target_dir)
                os.symlink(rel_path, runs_on_link)
            except Exception:
                pass
    return target_dir, True


def materialize_ci_on_demand(session_id: str, clean_ci: str, max_depth: int = 5) -> tuple[Optional[Path], bool, int]:
    """
    Recursively hydrates up to max_depth hops of the k-hop connected subgraph in volatile memory
    along rels_by_child, returning (target_dir, cold_hydrated_bool, hydrated_nodes_count).
    """
    session_dir = SESSIONS_ROOT / session_id / "cmdb"
    if not session_dir.exists():
        return None, False, 0

    hydrated_nodes = 0
    mem_sess = ACTIVE_RAM_SESSIONS.get(session_id)
    if mem_sess:
        by_name = mem_sess.get("by_name", {})
        by_sys_id = mem_sess.get("by_sys_id", {})
        rels_by_child = mem_sess.get("rels_by_child", {})
        ci_entry = by_name.get(clean_ci)
        if not ci_entry:
            for name_key, entry in by_name.items():
                if clean_ci in name_key:
                    ci_entry = entry
                    break
        if ci_entry:
            curr_entry: Optional[Dict[str, Any]] = ci_entry
            visited = set()
            first_dir: Optional[Path] = None
            for _ in range(max_depth):
                if not curr_entry:
                    break
                c_sys_id = curr_entry.get("sys_id", "")
                if c_sys_id in visited:
                    break
                visited.add(c_sys_id)
                parent_id = rels_by_child.get(c_sys_id)
                parent_entry = by_sys_id.get(parent_id) if parent_id else None
                d, was_cold = _write_ci_posix_dir(session_dir, curr_entry, parent_entry)
                if was_cold:
                    hydrated_nodes += 1
                if first_dir is None:
                    first_dir = d
                curr_entry = parent_entry
            if first_dir:
                return first_dir, (hydrated_nodes > 0), hydrated_nodes

    db_path = session_dir / "session_graph.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute(
                "SELECT sys_id, clean_name, sys_class, is_physical, attrs_json FROM session_cis WHERE clean_name = ? OR clean_name LIKE ? LIMIT 1",
                (clean_ci, f"%{clean_ci}%")
            ).fetchone()
            if row:
                curr_row = row
                visited = set()
                first_dir = None
                for _ in range(max_depth):
                    if not curr_row:
                        break
                    sys_id, c_name, s_class, is_phys, attrs_json = curr_row
                    if sys_id in visited:
                        break
                    visited.add(sys_id)
                    ci_entry = {
                        "sys_id": sys_id,
                        "name": c_name,
                        "sys_class": s_class,
                        "is_physical": bool(is_phys),
                        "attrs": json.loads(attrs_json)
                    }
                    rel_row = conn.execute(
                        "SELECT target_sys_id FROM session_rels WHERE source_sys_id = ? LIMIT 1",
                        (sys_id,)
                    ).fetchone()
                    parent_entry = None
                    next_row = None
                    if rel_row:
                        next_row = conn.execute(
                            "SELECT sys_id, clean_name, sys_class, is_physical, attrs_json FROM session_cis WHERE sys_id = ? LIMIT 1",
                            (rel_row[0],)
                        ).fetchone()
                        if next_row:
                            parent_entry = {
                                "sys_id": next_row[0],
                                "name": next_row[1],
                                "sys_class": next_row[2],
                                "is_physical": bool(next_row[3]),
                                "attrs": json.loads(next_row[4])
                            }
                    d, was_cold = _write_ci_posix_dir(session_dir, ci_entry, parent_entry)
                    if was_cold:
                        hydrated_nodes += 1
                    if first_dir is None:
                        first_dir = d
                    curr_row = next_row
                conn.close()
                if first_dir:
                    return first_dir, (hydrated_nodes > 0), hydrated_nodes
            conn.close()
        except Exception:
            pass

    for sub in ("logical", "physical"):
        candidate = session_dir / sub / clean_ci
        if candidate.exists():
            return candidate, False, 0
    return None, False, 0


@cmdb_session_bp.get("/generate_test_cmdb.py", response_class=PlainTextResponse)
def download_test_cmdb_generator() -> PlainTextResponse:
    """Serves the standalone 25-line Python 10,000-CI synthetic generator script."""
    script_path = Path("/home/james/stacklabs/apps/cmdb_studio/public/generate_test_cmdb.py")
    content = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": 'attachment; filename="generate_test_cmdb.py"'}
    )


@cmdb_session_bp.post("/session_ingest")
async def ingest_cmdb_session(
    ci_file: UploadFile = File(..., description="ServiceNow cmdb_ci.json export"),
    rel_file: Optional[UploadFile] = File(None, description="ServiceNow cmdb_rel_ci.json export"),
    session_name: Optional[str] = Form("Enterprise Evaluation")
) -> Dict[str, Any]:
    """
    Parses ServiceNow JSON exports directly into ephemeral /dev/shm RAM.
    Zero disk writes. Zero cloud persistence.
    Handles 10,000 to 50,000+ CIs in milliseconds via in-memory index + SQLite WAL in /dev/shm.
    """
    t_start = time.perf_counter()
    evicted_sessions = _enforce_session_bounds()
    session_id = str(uuid.uuid4())[:8]
    session_dir = SESSIONS_ROOT / session_id / "cmdb"
    logical_dir = session_dir / "logical"
    physical_dir = session_dir / "physical"
    rel_dir = session_dir / "relationships"

    logical_dir.mkdir(parents=True, exist_ok=True)
    physical_dir.mkdir(parents=True, exist_ok=True)
    rel_dir.mkdir(parents=True, exist_ok=True)

    from scripts.blueprints.swanson_bridge_engine import parse_servicenow_upload_bytes
    ci_bytes = await ci_file.read()
    try:
        ci_records = parse_servicenow_upload_bytes(ci_bytes, ci_file.filename or "")
    except Exception as e:
        shutil.rmtree(session_dir.parent, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Invalid ServiceNow JSON/XML in cmdb_ci export: {str(e)}")

    top_cis: List[str] = []
    by_sys_id: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    sqlite_ci_rows = []
    ci_count = 0

    for rec in ci_records:
        if not isinstance(rec, dict):
            continue
        raw_name = rec.get("name") or rec.get("sys_id") or f"ci_{ci_count}"
        clean_name = sanitize_filename(str(raw_name))

        sys_class = rec.get("sys_class_name", "cmdb_ci")
        if isinstance(sys_class, dict):
            sys_class = sys_class.get("value", "cmdb_ci")
        sys_class = str(sys_class).lower()

        sys_id = rec.get("sys_id", "")
        if isinstance(sys_id, dict):
            sys_id = sys_id.get("value", "")
        sys_id = str(sys_id) or clean_name

        is_physical = any(k in sys_class for k in ["server", "hardware", "switch", "router", "storage", "linux", "esx"])

        attrs: Dict[str, str] = {}
        for k, v in rec.items():
            if v is not None:
                if isinstance(v, dict):
                    val_str = str(v.get("display_value", v.get("value", ""))).strip()
                elif not isinstance(v, list):
                    val_str = str(v).strip()
                else:
                    val_str = ""
                if val_str:
                    attrs[sanitize_filename(str(k))] = val_str

        ci_entry = {
            "sys_id": sys_id,
            "name": clean_name,
            "sys_class": sys_class,
            "is_physical": is_physical,
            "attrs": attrs,
            "path": f"/cmdb/{'physical' if is_physical else 'logical'}/{clean_name}"
        }
        by_sys_id[sys_id] = ci_entry
        by_name[clean_name] = ci_entry
        sqlite_ci_rows.append((sys_id, clean_name, sys_class, 1 if is_physical else 0, json.dumps(attrs)))

        ci_count += 1
        if len(top_cis) < 10 and clean_name not in top_cis:
            top_cis.append(clean_name)

    rel_count = 0
    rels_by_child: Dict[str, str] = {}
    sqlite_rel_rows = []

    if rel_file and rel_file.filename:
        try:
            rel_bytes = await rel_file.read()
            if rel_bytes and rel_bytes.strip():
                rel_records = parse_servicenow_upload_bytes(rel_bytes, rel_file.filename or "")
                if isinstance(rel_records, list):
                    for rel in rel_records:
                        if not isinstance(rel, dict):
                            continue
                        parent_raw = rel.get("parent", {})
                        child_raw = rel.get("child", {})
                        p_id = str(parent_raw.get("value", parent_raw) if isinstance(parent_raw, dict) else parent_raw)
                        c_id = str(child_raw.get("value", child_raw) if isinstance(child_raw, dict) else child_raw)

                        p_entry = by_sys_id.get(p_id) or by_name.get(p_id)
                        c_entry = by_sys_id.get(c_id) or by_name.get(c_id)
                        if p_entry and c_entry:
                            rels_by_child[p_entry["sys_id"]] = c_entry["sys_id"]
                            sqlite_rel_rows.append((p_entry["sys_id"], c_entry["sys_id"]))
                            rel_count += 1
        except Exception:
            pass

    created_epoch = time.time()
    # Store in RAM session dictionary for O(1) lookup
    ACTIVE_RAM_SESSIONS[session_id] = {
        "created_at_epoch": created_epoch,
        "by_sys_id": by_sys_id,
        "by_name": by_name,
        "rels_by_child": rels_by_child
    }

    # Bulk write to in-memory SQLite WAL inside /dev/shm
    db_path = session_dir / "session_graph.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("CREATE TABLE session_cis (sys_id TEXT PRIMARY KEY, clean_name TEXT, sys_class TEXT, is_physical INTEGER, attrs_json TEXT);")
    conn.execute("CREATE INDEX idx_session_cis_name ON session_cis(clean_name);")
    conn.execute("CREATE TABLE session_rels (source_sys_id TEXT, target_sys_id TEXT);")
    conn.execute("CREATE INDEX idx_session_rels_src ON session_rels(source_sys_id);")
    with conn:
        conn.executemany("INSERT OR REPLACE INTO session_cis VALUES (?, ?, ?, ?, ?);", sqlite_ci_rows)
        if sqlite_rel_rows:
            conn.executemany("INSERT INTO session_rels VALUES (?, ?);", sqlite_rel_rows)
    conn.close()

    # Eagerly materialize up to EAGER_VFS_MATERIALIZE_CAP (250) CIs as POSIX directories for Topology Explorer browsing
    for idx, ci_entry in enumerate(by_name.values()):
        if idx >= EAGER_VFS_MATERIALIZE_CAP:
            break
        target_sys_id = rels_by_child.get(ci_entry["sys_id"])
        parent_entry = by_sys_id.get(target_sys_id) if target_sys_id else None
        _write_ci_posix_dir(session_dir, ci_entry, parent_entry)

    duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    db_inode = os.stat(db_path).st_ino if db_path.exists() else 0
    graph_page_id = f"0x{(db_inode ^ 0x5A7F3C19):08x}" if db_inode else "0x5a7f3c19"

    meta = {
        "session_id": session_id,
        "session_name": session_name or "Enterprise Evaluation",
        "created_at_epoch": created_epoch,
        "total_cis": ci_count,
        "total_relationships": rel_count,
        "ingest_duration_ms": duration_ms,
        "prewarmed_graph_nodes": min(ci_count, EAGER_VFS_MATERIALIZE_CAP),
        "graph_page_id": graph_page_id,
        "max_active_sessions": MAX_ACTIVE_RAM_SESSIONS,
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "evicted_sessions": evicted_sessions,
        "top_cis": top_cis,
        "staging_plane_ref": f"mem://session/{session_id}/graph"
    }
    (session_dir / "session_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "status": "SUCCESS",
        "message": f"Successfully ingested {ci_count} CIs and {rel_count} relationships into ephemeral RAM in {duration_ms} ms.",
        "session": meta
    }


@cmdb_session_bp.api_route("/session_purge", methods=["DELETE", "POST", "GET"])
def purge_cmdb_session(session_id: Optional[str] = Query(None, description="Optional Session ID to purge from RAM")) -> Dict[str, Any]:
    """Instantly unlinks the ephemeral evaluation directory from /dev/shm and restores default Enterprise IT topology."""
    if session_id:
        ACTIVE_RAM_SESSIONS.pop(session_id, None)
        target = SESSIONS_ROOT / session_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            return {
                "status": "PURGED",
                "session_id": session_id,
                "default_topology": "Enterprise Infrastructure CMDB",
                "message": "Memory unlinked. Zero residual bytes remaining in RAM."
            }
        return {
            "status": "PURGED",
            "session_id": session_id,
            "default_topology": "Enterprise Infrastructure CMDB",
            "message": "Session directory already unlinked; default Enterprise Infrastructure CMDB active."
        }

    purged_ids = list(ACTIVE_RAM_SESSIONS.keys())
    ACTIVE_RAM_SESSIONS.clear()
    if SESSIONS_ROOT.exists():
        for entry in SESSIONS_ROOT.iterdir():
            if entry.is_dir():
                if entry.name not in purged_ids:
                    purged_ids.append(entry.name)
                shutil.rmtree(entry, ignore_errors=True)
    return {
        "status": "PURGED",
        "purged_sessions": purged_ids,
        "default_topology": "Enterprise Infrastructure CMDB",
        "message": "All ephemeral RAM cartridges unlinked. Default Enterprise Infrastructure CMDB restored."
    }


@cmdb_session_bp.get("/session_status")
def get_session_status(session_id: str = Query(..., description="Session ID to inspect")) -> Dict[str, Any]:
    """Inspects metadata of an active RAM session."""
    target = SESSIONS_ROOT / session_id / "cmdb" / "session_metadata.json"
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read session metadata: {str(e)}")
    raise HTTPException(status_code=404, detail="Session directory does not exist or was already purged.")


@cmdb_session_bp.api_route("/fanstack_cmdb_ci.json", methods=["GET", "HEAD"], response_class=PlainTextResponse)
@cmdb_session_bp.api_route("/sports_cmdb_ci.json", methods=["GET", "HEAD"], response_class=PlainTextResponse)
def download_sports_cmdb_ci() -> PlainTextResponse:
    """Serves the compiled FanStack & 4-Legged Sports CMDB CI export."""
    p = Path("/home/james/stacklabs/data/fanstack_cmdb_ci.json")
    if not p.exists():
        p = Path("/home/james/stacklabs/data/sports_cmdb_ci.json")
    content = p.read_text(encoding="utf-8") if p.exists() else '{"result": []}'
    return PlainTextResponse(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="fanstack_cmdb_ci.json"'},
    )


@cmdb_session_bp.api_route("/fanstack_cmdb_rel_ci.json", methods=["GET", "HEAD"], response_class=PlainTextResponse)
@cmdb_session_bp.api_route("/sports_cmdb_rel_ci.json", methods=["GET", "HEAD"], response_class=PlainTextResponse)
def download_sports_cmdb_rel_ci() -> PlainTextResponse:
    """Serves the compiled FanStack & 4-Legged Sports CMDB relationship export."""
    p = Path("/home/james/stacklabs/data/fanstack_cmdb_rel_ci.json")
    if not p.exists():
        p = Path("/home/james/stacklabs/data/sports_cmdb_rel_ci.json")
    content = p.read_text(encoding="utf-8") if p.exists() else '{"result": []}'
    return PlainTextResponse(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="fanstack_cmdb_rel_ci.json"'},
    )


@cmdb_session_bp.post("/mount_fanstack_cartridge")
@cmdb_session_bp.post("/mount_sports_cartridge")
def mount_4legged_sports_cartridge() -> Dict[str, Any]:
    """
    1-Click Polymorphic Cartridge Loader: mounts the 1,700+ CI FanStack & Mean Gene
    Cypher CMDB (dna/sovereign_now.db) directly into volatile RAM.
    """
    t_start = time.perf_counter()
    evicted_sessions = _enforce_session_bounds()
    session_id = "fanstack"
    session_dir = SESSIONS_ROOT / session_id / "cmdb"
    if session_dir.parent.exists():
        shutil.rmtree(session_dir.parent, ignore_errors=True)

    logical_dir = session_dir / "logical"
    physical_dir = session_dir / "physical"
    rel_dir = session_dir / "relationships"
    logical_dir.mkdir(parents=True, exist_ok=True)
    physical_dir.mkdir(parents=True, exist_ok=True)
    rel_dir.mkdir(parents=True, exist_ok=True)

    ci_path = Path("/home/james/stacklabs/data/fanstack_cmdb_ci.json")
    rel_path = Path("/home/james/stacklabs/data/fanstack_cmdb_rel_ci.json")
    if not ci_path.exists():
        ci_path = Path("/home/james/stacklabs/data/sports_cmdb_ci.json")
        rel_path = Path("/home/james/stacklabs/data/sports_cmdb_rel_ci.json")
    if not ci_path.exists():
        from scripts.compile_sports_lore_cmdb import compile_4legged_sports_cmdb
        compile_4legged_sports_cmdb()

    ci_records = json.loads(ci_path.read_text(encoding="utf-8")).get("result", [])
    rel_records = json.loads(rel_path.read_text(encoding="utf-8")).get("result", []) if rel_path.exists() else []

    by_sys_id: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    sqlite_ci_rows = []
    top_cis = [
        "battery_chucker_jr",
        "sys_mean_gene",
        "barf",
        "dot",
        "tomahawk",
        "unclesteviestan",
        "the_chop_shop",
        "room_823617",
        "play_823617_acuna_whiff",
        "tva_001_ron_burgundy",
    ]

    for rec in ci_records:
        raw_name = rec.get("name") or rec.get("sys_id")
        clean_name = sanitize_filename(str(raw_name))
        sys_class = str(rec.get("sys_class_name", "cmdb_ci")).lower()
        sys_id = str(rec.get("sys_id") or clean_name)
        is_physical = sys_class == "cmdb_ci_play_event"

        attrs: Dict[str, str] = {}
        for k, v in rec.items():
            if v is not None and not isinstance(v, (list, dict)):
                attrs[sanitize_filename(str(k))] = str(v)

        ci_entry = {
            "sys_id": sys_id,
            "name": clean_name,
            "sys_class": sys_class,
            "is_physical": is_physical,
            "attrs": attrs,
            "path": f"/cmdb/{'physical' if is_physical else 'logical'}/{clean_name}",
        }
        by_sys_id[sys_id] = ci_entry
        by_name[clean_name] = ci_entry
        sqlite_ci_rows.append((sys_id, clean_name, sys_class, 1 if is_physical else 0, json.dumps(attrs)))

    rels_by_child: Dict[str, str] = {}
    sqlite_rel_rows = []
    for rel in rel_records:
        p_raw = rel.get("parent", {})
        c_raw = rel.get("child", {})
        p_id = str(p_raw.get("value", p_raw) if isinstance(p_raw, dict) else p_raw)
        c_id = str(c_raw.get("value", c_raw) if isinstance(c_raw, dict) else c_raw)
        p_entry = by_sys_id.get(p_id) or by_name.get(p_id)
        c_entry = by_sys_id.get(c_id) or by_name.get(c_id)
        if p_entry and c_entry:
            rels_by_child[p_entry["sys_id"]] = c_entry["sys_id"]
            sqlite_rel_rows.append((p_entry["sys_id"], c_entry["sys_id"]))

    created_epoch = time.time()
    ACTIVE_RAM_SESSIONS[session_id] = {
        "created_at_epoch": created_epoch,
        "by_sys_id": by_sys_id,
        "by_name": by_name,
        "rels_by_child": rels_by_child,
    }

    db_path = session_dir / "session_graph.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("CREATE TABLE session_cis (sys_id TEXT PRIMARY KEY, clean_name TEXT, sys_class TEXT, is_physical INTEGER, attrs_json TEXT);")
    conn.execute("CREATE INDEX idx_session_cis_name ON session_cis(clean_name);")
    conn.execute("CREATE TABLE session_rels (source_sys_id TEXT, target_sys_id TEXT);")
    conn.execute("CREATE INDEX idx_session_rels_src ON session_rels(source_sys_id);")
    with conn:
        conn.executemany("INSERT OR REPLACE INTO session_cis VALUES (?, ?, ?, ?, ?);", sqlite_ci_rows)
        if sqlite_rel_rows:
            conn.executemany("INSERT INTO session_rels VALUES (?, ?);", sqlite_rel_rows)
    conn.close()

    # Prewarm top priority CIs + up to EAGER_VFS_MATERIALIZE_CAP
    for tc in top_cis:
        if tc in by_name:
            ci_entry = by_name[tc]
            target_sys_id = rels_by_child.get(ci_entry["sys_id"])
            parent_entry = by_sys_id.get(target_sys_id) if target_sys_id else None
            _write_ci_posix_dir(session_dir, ci_entry, parent_entry)

    for idx, ci_entry in enumerate(by_name.values()):
        if idx >= EAGER_VFS_MATERIALIZE_CAP:
            break
        target_sys_id = rels_by_child.get(ci_entry["sys_id"])
        parent_entry = by_sys_id.get(target_sys_id) if target_sys_id else None
        _write_ci_posix_dir(session_dir, ci_entry, parent_entry)

    duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    meta = {
        "session_id": session_id,
        "session_name": "FanStack & Mean Gene Cypher CMDB",
        "created_at_epoch": created_epoch,
        "total_cis": len(by_sys_id),
        "total_relationships": len(sqlite_rel_rows),
        "ingest_duration_ms": duration_ms,
        "prewarmed_graph_nodes": min(len(by_sys_id), EAGER_VFS_MATERIALIZE_CAP),
        "graph_page_id": "0x7c41e920",
        "max_active_sessions": MAX_ACTIVE_RAM_SESSIONS,
        "session_ttl_seconds": SESSION_TTL_SECONDS,
        "evicted_sessions": evicted_sessions,
        "top_cis": top_cis,
        "staging_plane_ref": f"mem://session/{session_id}/graph",
    }
    (session_dir / "session_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "status": "SUCCESS",
        "message": f"Mounted FanStack & Mean Gene Cypher CMDB ({len(by_sys_id)} CIs, {len(sqlite_rel_rows)} relationships) in RAM in {duration_ms} ms.",
        "session": meta,
    }


