#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Google Drive & Corporate Vault Sync Telemetry Router for Cockpit (:8088).
Unifies local sprint/Mycroft staging directories, streams sync_to_gdrive.sh execution logs,
and performs post-sync rclone remote verification + Google Drive File ID extraction for NotebookLM.
"""

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, Query

drive_sync_router = APIRouter()

REPO_ROOT = Path("/home/james/stacklabs")
INBOX_ROOT = Path("/home/james/stack" + "labs_inbox")
STATUS_FILE = REPO_ROOT / "data" / "telemetry" / "drive_sync_status.json"
STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

_SYNC_LOCK = threading.Lock()
_SYNC_STATE: Dict[str, Any] = {
    "state": "IDLE",
    "task_id": None,
    "started_at": None,
    "started_epoch": None,
    "finished_at": None,
    "duration_ms": 0,
    "exit_code": None,
    "linter_status": "PASSED",
    "remote_verified": False,
    "remote_sprint_count": 0,
    "remote_mycroft_count": 0,
    "sprint_drive_ids": {},
    "mycroft_drive_ids": {},
    "log_lines": [
        "[READY] Drive Sync telemetry online. Click 'Trigger Remote Sync' to unify local sources and sync to Google Drive."
    ],
}


def _load_persisted_state() -> None:
    if STATUS_FILE.exists():
        try:
            saved = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                if saved.get("state") == "RUNNING":
                    saved["state"] = "IDLE"
                _SYNC_STATE.update(saved)
        except Exception:
            pass


def _save_persisted_state() -> None:
    try:
        tmp = STATUS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_SYNC_STATE, indent=2), encoding="utf-8")
        os.replace(tmp, STATUS_FILE)
    except Exception:
        pass


_load_persisted_state()


def _today_sprint_slug() -> str:
    return datetime.now().strftime("daily_sprint_%Y_%m_%d")


def _format_kb(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes / 1024:.1f} KB"


def _format_edt(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S EDT")


def _fetch_rclone_drive_ids(remote_path: str) -> Dict[str, str]:
    """Runs rclone lsf --format 'ip' --separator '|' and returns {filename: file_id}."""
    mapping: Dict[str, str] = {}
    try:
        res = subprocess.run(
            ["/usr/bin/rclone", "lsf", "--format", "ip", "--separator", "|", remote_path, "--timeout", "15s"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if res.returncode == 0:
            for raw in res.stdout.splitlines():
                line = raw.strip()
                if "|" in line:
                    fid, fname = line.split("|", 1)
                    fid = fid.strip()
                    fname = fname.strip()
                    if fid and fname and not fname.endswith("/"):
                        mapping[fname] = fid
    except Exception:
        pass
    return mapping


def refresh_drive_file_ids_if_missing() -> None:
    sprint_slug = _today_sprint_slug()
    if not _SYNC_STATE.get("sprint_drive_ids"):
        _SYNC_STATE["sprint_drive_ids"] = _fetch_rclone_drive_ids(f"stacklabs_edge:StackLabs_Internal/{sprint_slug}")
    if not _SYNC_STATE.get("mycroft_drive_ids"):
        _SYNC_STATE["mycroft_drive_ids"] = _fetch_rclone_drive_ids("stacklabs_edge:00_Mycroft_Ground_Truth")
    _save_persisted_state()


def unify_local_sprint_and_mycroft_sources() -> List[str]:
    logs: List[str] = []
    sprint_slug = _today_sprint_slug()

    docs_sprint = REPO_ROOT / "docs" / sprint_slug
    art_sprint = REPO_ROOT / "artifacts" / "sprints" / sprint_slug
    nb_sprint = INBOX_ROOT / "notebook_sync" / "StackLabs_Internal" / sprint_slug
    mycroft_dir = REPO_ROOT / "ground_truth" / "mycroft_sources"
    downloads_dir = REPO_ROOT / "pilot_drops" / "downloads"
    passport_file = REPO_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md"

    docs_sprint.mkdir(parents=True, exist_ok=True)
    art_sprint.mkdir(parents=True, exist_ok=True)
    nb_sprint.mkdir(parents=True, exist_ok=True)
    mycroft_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    newest_map: Dict[str, Path] = {}
    for folder in (nb_sprint, art_sprint, docs_sprint):
        if not folder.exists():
            continue
        for f in folder.glob("*.md"):
            if not f.is_file():
                continue
            cur = newest_map.get(f.name)
            if cur is None or f.stat().st_mtime >= cur.stat().st_mtime:
                newest_map[f.name] = f

    if passport_file.exists():
        newest_map["PILOT_PASSPORT_CURRENT.md"] = passport_file

    copied_count = 0
    for fname, src_path in sorted(newest_map.items()):
        for dst_dir in (docs_sprint, art_sprint, nb_sprint):
            dst_path = dst_dir / fname
            try:
                if not dst_path.exists() or src_path.resolve() != dst_path.resolve():
                    if not dst_path.exists() or src_path.stat().st_mtime > dst_path.stat().st_mtime or src_path.stat().st_size != dst_path.stat().st_size:
                        shutil.copy2(src_path, dst_path)
                        copied_count += 1
            except Exception:
                pass
        try:
            dl_target = downloads_dir / fname
            if not dl_target.exists() or src_path.stat().st_size != dl_target.stat().st_size or src_path.stat().st_mtime > dl_target.stat().st_mtime:
                shutil.copy2(src_path, dl_target)
        except Exception:
            pass

    for fname, src_path in newest_map.items():
        if fname.startswith("MYCROFT_MASTER_KNOWLEDGE") or fname == "PILOT_PASSPORT_CURRENT.md":
            dst_m = mycroft_dir / fname
            try:
                if not dst_m.exists() or src_path.stat().st_size != dst_m.stat().st_size or src_path.stat().st_mtime > dst_m.stat().st_mtime:
                    shutil.copy2(src_path, dst_m)
            except Exception:
                pass

    logs.append(
        f"[PRE-FLIGHT] Unified {len(newest_map)} sprint sources across docs/{sprint_slug}, artifacts/sprints/{sprint_slug}, notebook_sync, and pilot_drops/downloads ({copied_count} delta updates)."
    )
    return logs


def build_notebooklm_injection_prompt(sprint_slug: str, sprint_files: List[Dict[str, Any]], mycroft_files: List[Dict[str, Any]]) -> str:
    lines = [
        f"Use @Google Drive and @NotebookLM to add/refresh these exact Google Drive sources in my two active notebooks (`StackLabs - Sprint {sprint_slug.replace('daily_sprint_', '').replace('_', '-')}` and `Mycroft`):",
        "",
        f"### 1. Daily Sprint Notebook (`stacklabs_edge:StackLabs_Internal/{sprint_slug}`):"
    ]
    for f in sprint_files:
        fid = f.get("drive_file_id") or ""
        url = f.get("drive_url") or ""
        if fid:
            lines.append(f"- `{f['name']}` -> File ID: `{fid}` ({url})")
        else:
            lines.append(f"- `{f['name']}`")
    lines.append("")
    lines.append("### 2. Mycroft Ground Truth Notebook (`stacklabs_edge:00_Mycroft_Ground_Truth`):")
    for f in mycroft_files:
        fid = f.get("drive_file_id") or ""
        url = f.get("drive_url") or ""
        if fid:
            lines.append(f"- `{f['name']}` -> File ID: `{fid}` ({url})")
        else:
            lines.append(f"- `{f['name']}`")
    return "\n".join(lines)


def collect_local_inventory() -> Dict[str, Any]:
    sprint_slug = _today_sprint_slug()
    docs_sprint = REPO_ROOT / "docs" / sprint_slug
    mycroft_dir = REPO_ROOT / "ground_truth" / "mycroft_sources"
    downloads_dir = REPO_ROOT / "pilot_drops" / "downloads"

    sprint_id_map: Dict[str, str] = _SYNC_STATE.get("sprint_drive_ids") or {}
    mycroft_id_map: Dict[str, str] = _SYNC_STATE.get("mycroft_drive_ids") or {}

    sprint_files: List[Dict[str, Any]] = []
    sprint_bytes = 0
    if docs_sprint.exists():
        for f in sorted(docs_sprint.glob("*.md")):
            if f.is_file():
                st = f.stat()
                sprint_bytes += st.st_size
                in_dl = (downloads_dir / f.name).exists()
                fid = sprint_id_map.get(f.name, "")
                sprint_files.append({
                    "name": f.name,
                    "size_bytes": st.st_size,
                    "size_human": _format_kb(st.st_size),
                    "mtime_edt": _format_edt(st.st_mtime),
                    "in_downloads": in_dl,
                    "drive_file_id": fid,
                    "drive_url": f"https://drive.google.com/file/d/{fid}/view" if fid else "",
                })

    mycroft_files: List[Dict[str, Any]] = []
    mycroft_bytes = 0
    if mycroft_dir.exists():
        for f in sorted(mycroft_dir.glob("*.md")):
            if f.is_file():
                st = f.stat()
                mycroft_bytes += st.st_size
                fid = mycroft_id_map.get(f.name, "")
                mycroft_files.append({
                    "name": f.name,
                    "size_bytes": st.st_size,
                    "size_human": _format_kb(st.st_size),
                    "mtime_edt": _format_edt(st.st_mtime),
                    "drive_file_id": fid,
                    "drive_url": f"https://drive.google.com/file/d/{fid}/view" if fid else "",
                })

    vault_files: List[Dict[str, Any]] = []
    passport_path = REPO_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md"
    if passport_path.exists():
        st = passport_path.stat()
        vault_files.append({
            "name": "PILOT_PASSPORT_CURRENT.md",
            "target": "stacklabs_vault:01_Investor_Briefs/PILOT_PASSPORT_CURRENT.md",
            "size_human": _format_kb(st.st_size),
            "mtime_edt": _format_edt(st.st_mtime),
        })

    today_dir = INBOX_ROOT / "today"
    if today_dir.exists():
        reports = sorted(today_dir.glob("SESSION_REPORT_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if reports:
            r0 = reports[0]
            st = r0.stat()
            vault_files.append({
                "name": r0.name,
                "target": f"stacklabs_vault:01_Investor_Briefs/{r0.name}",
                "size_human": _format_kb(st.st_size),
                "mtime_edt": _format_edt(st.st_mtime),
            })

    prompt_text = build_notebooklm_injection_prompt(sprint_slug, sprint_files, mycroft_files)

    return {
        "sprint_folder": sprint_slug,
        "sprint_remote": f"stacklabs_edge:StackLabs_Internal/{sprint_slug}",
        "sprint_count": len(sprint_files),
        "sprint_size_human": _format_kb(sprint_bytes),
        "sprint_files": sprint_files,
        "mycroft_remote": "stacklabs_edge:00_Mycroft_Ground_Truth",
        "mycroft_count": len(mycroft_files),
        "mycroft_size_human": _format_kb(mycroft_bytes),
        "mycroft_files": mycroft_files,
        "vault_remote": "stacklabs_vault:01_Investor_Briefs",
        "vault_count": len(vault_files),
        "vault_files": vault_files,
        "notebooklm_prompt": prompt_text,
    }


def _append_log(line: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    _SYNC_STATE["log_lines"].append(f"[{ts}] {line}")
    if len(_SYNC_STATE["log_lines"]) > 120:
        _SYNC_STATE["log_lines"] = _SYNC_STATE["log_lines"][-120:]


def _execute_sync_job(task_id: str) -> None:
    t0 = time.perf_counter()
    sprint_slug = _today_sprint_slug()
    try:
        pre_logs = unify_local_sprint_and_mycroft_sources()
        for l in pre_logs:
            _append_log(l)
        _save_persisted_state()

        _append_log("[EXEC] Launching /home/james/stacklabs/scripts/sync_to_gdrive.sh...")
        proc = subprocess.Popen(
            ["/bin/bash", str(REPO_ROOT / "scripts" / "sync_to_gdrive.sh")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if proc.stdout:
            for raw_line in iter(proc.stdout.readline, ""):
                clean = raw_line.strip()
                if clean:
                    _append_log(clean)
                    if "CIRCUIT BREAKER TRIGGERED" in clean:
                        _SYNC_STATE["linter_status"] = "FAILED"
                    elif "ANTI-METAPHOR GATE] PASSED" in clean:
                        _SYNC_STATE["linter_status"] = "PASSED"
                    _save_persisted_state()
        proc.wait(timeout=120)
        rc = proc.returncode
        _SYNC_STATE["exit_code"] = rc

        if rc == 0:
            _append_log(f"[VERIFY] Extracting Google Drive File IDs from stacklabs_edge:StackLabs_Internal/{sprint_slug} and stacklabs_edge:00_Mycroft_Ground_Truth...")
            sprint_ids = _fetch_rclone_drive_ids(f"stacklabs_edge:StackLabs_Internal/{sprint_slug}")
            mycroft_ids = _fetch_rclone_drive_ids("stacklabs_edge:00_Mycroft_Ground_Truth")
            _SYNC_STATE["sprint_drive_ids"] = sprint_ids
            _SYNC_STATE["mycroft_drive_ids"] = mycroft_ids
            _SYNC_STATE["remote_sprint_count"] = len(sprint_ids)
            _SYNC_STATE["remote_mycroft_count"] = len(mycroft_ids)
            _SYNC_STATE["remote_verified"] = bool(sprint_ids and mycroft_ids)
            _append_log(
                f"[VERIFIED REMOTE] stacklabs_edge:StackLabs_Internal/{sprint_slug} ({len(sprint_ids)} Drive IDs) | stacklabs_edge:00_Mycroft_Ground_Truth ({len(mycroft_ids)} Drive IDs)"
            )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        _SYNC_STATE["duration_ms"] = elapsed_ms
        _SYNC_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
        if rc == 0:
            _SYNC_STATE["state"] = "SUCCESS"
            _append_log(f"[COMPLETE] Google Drive & Corporate Vault sync succeeded in {elapsed_ms / 1000:.2f}s (Exit Code: 0).")
        else:
            _SYNC_STATE["state"] = "FAILED"
            _append_log(f"[ERROR] sync_to_gdrive.sh exited with code {rc} after {elapsed_ms / 1000:.2f}s.")
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        _SYNC_STATE["duration_ms"] = elapsed_ms
        _SYNC_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
        _SYNC_STATE["state"] = "FAILED"
        _SYNC_STATE["exit_code"] = -1
        _append_log(f"[EXCEPTION] Sync execution error: {exc}")
    finally:
        _save_persisted_state()


@drive_sync_router.api_route("/api/cockpit/drive_sync/status", methods=["GET", "HEAD"])
def get_drive_sync_status(refresh_ids: bool = Query(False)):
    if refresh_ids or not _SYNC_STATE.get("sprint_drive_ids"):
        refresh_drive_file_ids_if_missing()
    inv = collect_local_inventory()
    live_duration = _SYNC_STATE.get("duration_ms") or 0
    if _SYNC_STATE.get("state") == "RUNNING" and _SYNC_STATE.get("started_epoch"):
        live_duration = int((time.time() - float(_SYNC_STATE["started_epoch"])) * 1000)

    return {
        "status": "success",
        "state": _SYNC_STATE.get("state", "IDLE"),
        "task_id": _SYNC_STATE.get("task_id"),
        "started_at": _SYNC_STATE.get("started_at"),
        "finished_at": _SYNC_STATE.get("finished_at"),
        "duration_ms": live_duration,
        "exit_code": _SYNC_STATE.get("exit_code"),
        "linter_status": _SYNC_STATE.get("linter_status", "PASSED"),
        "remote_verified": _SYNC_STATE.get("remote_verified", False),
        "remote_sprint_count": _SYNC_STATE.get("remote_sprint_count", inv["sprint_count"]),
        "remote_mycroft_count": _SYNC_STATE.get("remote_mycroft_count", inv["mycroft_count"]),
        "log_lines": _SYNC_STATE.get("log_lines", []),
        "inventory": inv,
    }


@drive_sync_router.post("/api/cockpit/drive_sync/execute")
def execute_drive_sync(wait: bool = Query(False)):
    with _SYNC_LOCK:
        if _SYNC_STATE.get("state") == "RUNNING":
            return {
                "status": "running",
                "task_id": _SYNC_STATE.get("task_id"),
                "state": "RUNNING",
                "message": "Drive sync is already in progress.",
            }
        task_id = f"drive-sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        _SYNC_STATE["state"] = "RUNNING"
        _SYNC_STATE["task_id"] = task_id
        _SYNC_STATE["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
        _SYNC_STATE["started_epoch"] = time.time()
        _SYNC_STATE["finished_at"] = None
        _SYNC_STATE["duration_ms"] = 0
        _SYNC_STATE["exit_code"] = None
        _SYNC_STATE["log_lines"] = [
            f"[{datetime.now().strftime('%H:%M:%S')}] [START] Initiating Drive & Vault Sync ({task_id})..."
        ]
        _save_persisted_state()

    if wait:
        _execute_sync_job(task_id)
        return get_drive_sync_status()

    worker = threading.Thread(target=_execute_sync_job, args=(task_id,), daemon=True)
    worker.start()
    return {
        "status": "dispatched",
        "task_id": task_id,
        "state": "RUNNING",
        "started_at": _SYNC_STATE["started_at"],
        "message": "Drive & Corporate Vault sync started.",
    }
