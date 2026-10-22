#!/home/james/stacklabs/.venv/bin/python3
"""
KISS & LITE SQLite Sweep & VFS Liberation Engine (WO0011282).
I audit every .db file under /home/james/stacklabs, liberate trapped domain/human
tables into flat POSIX VFS (.md / .jsonl) files, and quarantine dead or redundant
binary database husks to /mnt/relics/sqlite_purge_20261021/.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path("/home/james/stacklabs")
VFS_ROOT = ROOT / "vfs"
DROPS_ROOT = ROOT / "pilot_drops"
PRIMARY_RELICS_DIR = Path("/mnt/relics/sqlite_purge_20261021")
FALLBACK_RELICS_DIR = ROOT / "data" / "relics_quarantine" / "sqlite_purge_20261021"


def _resolve_relics_dir() -> Path:
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore")
        if "/mnt/relics" in mounts and "emergency_ro" in mounts:
            FALLBACK_RELICS_DIR.mkdir(parents=True, exist_ok=True)
            return FALLBACK_RELICS_DIR
        PRIMARY_RELICS_DIR.mkdir(parents=True, exist_ok=True)
        return PRIMARY_RELICS_DIR
    except OSError:
        FALLBACK_RELICS_DIR.mkdir(parents=True, exist_ok=True)
        return FALLBACK_RELICS_DIR

# Strictly bounded L2 accelerators allowed to remain on active NVMe
ACTIVE_L2_ALLOWLIST: Set[str] = {
    str(ROOT / "data" / "morning_wiretap.db"),
    str(ROOT / "vfs" / "cmdb.db"),
    str(ROOT / "data" / "wiki_vfs.db"),
    str(ROOT / "data" / "acp_catalog.db"),
}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _find_open_db_files() -> Dict[str, List[int]]:
    """Scan /proc/[pid]/fd symlinks for active non-D-state python/uvicorn daemons."""
    open_map: Dict[str, List[int]] = {}
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat_txt = (entry / "stat").read_text(encoding="utf-8", errors="ignore")
            if ") D " in stat_txt or ") Z " in stat_txt:
                continue
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
            if not comm.startswith(("python", "uvicorn", "gunicorn", "sqlite")):
                continue
            pid = int(entry.name)
            fd_dir = entry / "fd"
            for fd in fd_dir.iterdir():
                try:
                    target = os.readlink(fd)
                    if ".db" in target and "/mnt/relics" not in target:
                        clean_target = target.split(" (deleted)")[0]
                        open_map.setdefault(clean_target, []).append(pid)
                except OSError:
                    continue
        except OSError:
            continue
    return open_map


def _inspect_sqlite_db(db_path: Path) -> Tuple[List[Dict[str, Any]], sqlite3.Connection | None]:
    tables_info: List[Dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(db_path), timeout=3.0)
        conn.row_factory = sqlite3.Row
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for t in tables:
            try:
                cnt = conn.execute(f'SELECT COUNT(*) AS c FROM "{t}"').fetchone()["c"]
            except sqlite3.Error:
                cnt = -1
            tables_info.append({"table": t, "rows": int(cnt)})
        return tables_info, conn
    except sqlite3.Error:
        return tables_info, None


def _liberate_table_to_jsonl(conn: sqlite3.Connection, table: str, dest_jsonl: Path, limit: int = 10000) -> int:
    try:
        rows = [dict(r) for r in conn.execute(f'SELECT * FROM "{table}" LIMIT ?', (limit,)).fetchall()]
        if not rows:
            return 0
        payload = "\n".join(json.dumps(r, default=str, sort_keys=True) for r in rows) + "\n"
        _atomic_write(dest_jsonl, payload)
        return len(rows)
    except sqlite3.Error:
        return 0


def _liberate_domain_data(db_path: Path, conn: sqlite3.Connection, tables: List[Dict[str, Any]]) -> List[str]:
    liberated_notes: List[str] = []
    stem = db_path.stem.lower()
    table_names = {t["table"] for t in tables if t["rows"] > 0}

    # 1. Liberate Pawel Curve Pushes -> pilot_drops/pawel_curve_pushes.jsonl & .md
    if "pawel_curve_pushes" in table_names:
        out_jsonl = DROPS_ROOT / "pawel_curve_pushes.jsonl"
        cnt = _liberate_table_to_jsonl(conn, "pawel_curve_pushes", out_jsonl)
        liberated_notes.append(f"pawel_curve_pushes ({cnt} rows -> {out_jsonl.relative_to(ROOT)})")

    # 2. Liberate Pheromone Lenses -> vfs/pheromones/lenses_ledger.jsonl
    for p_table in ("pheromone_query_lenses", "broadcast_pheromone_markers"):
        if p_table in table_names:
            out_jsonl = VFS_ROOT / "pheromones" / f"{p_table}.jsonl"
            cnt = _liberate_table_to_jsonl(conn, p_table, out_jsonl)
            liberated_notes.append(f"{p_table} ({cnt} rows -> {out_jsonl.relative_to(ROOT)})")

    # 3. Liberate SMS / Comms staging tables -> pilot_drops/comms/
    for t in table_names:
        if any(k in t.lower() for k in ("sms", "comms", "message", "mail", "draft")) and t != "chat_telemetry":
            out_jsonl = DROPS_ROOT / "comms" / f"liberated_{stem}_{t}.jsonl"
            cnt = _liberate_table_to_jsonl(conn, t, out_jsonl)
            if cnt > 0:
                liberated_notes.append(f"{t} ({cnt} rows -> {out_jsonl.relative_to(ROOT)})")

    # 4. Liberate emergent_society.db -> vfs/society/
    if "emergent_society" in stem:
        for t in table_names:
            out_jsonl = VFS_ROOT / "society" / f"{t}.jsonl"
            cnt = _liberate_table_to_jsonl(conn, t, out_jsonl)
            if cnt > 0:
                liberated_notes.append(f"{t} ({cnt} rows -> {out_jsonl.relative_to(ROOT)})")

    # 5. Liberate provocateur_graph.db -> vfs/provocateurs/
    if "provocateur" in stem:
        for t in table_names:
            out_jsonl = VFS_ROOT / "provocateurs" / f"{t}.jsonl"
            cnt = _liberate_table_to_jsonl(conn, t, out_jsonl)
            if cnt > 0:
                liberated_notes.append(f"{t} ({cnt} rows -> {out_jsonl.relative_to(ROOT)})")

    # 6. For any non-allowlisted DB with non-empty tables, export all tables to vfs/liberated/{stem}/
    if str(db_path) not in ACTIVE_L2_ALLOWLIST:
        for t in table_names:
            if t == "chat_telemetry":
                continue
            out_jsonl = VFS_ROOT / "liberated" / stem / f"{t}.jsonl"
            cnt = _liberate_table_to_jsonl(conn, t, out_jsonl)
            if cnt > 0:
                note = f"{t} ({cnt} rows -> {out_jsonl.relative_to(ROOT)})"
                if note not in liberated_notes:
                    liberated_notes.append(note)

    return liberated_notes


def run_sweep() -> Dict[str, Any]:
    relics_dir = _resolve_relics_dir()
    open_fds = _find_open_db_files()

    discovered_set: Set[Path] = set()
    search_roots = [ROOT, ROOT / "data", ROOT / "vfs", ROOT / "cmdb", ROOT / "ground_truth"]
    skip_names = {".venv", "node_modules", ".git", "models", "relics_quarantine", "archive", "dist"}
    for sroot in search_roots:
        if not sroot.exists() or sroot.is_symlink():
            continue
        for entry in sroot.iterdir():
            if entry.is_symlink() or entry.name in skip_names:
                continue
            if entry.is_file() and entry.name.endswith(".db"):
                discovered_set.add(entry)
            elif entry.is_dir():
                for sub in entry.iterdir():
                    if not sub.is_symlink() and sub.is_file() and sub.name.endswith(".db"):
                        discovered_set.add(sub)
    discovered_dbs: List[Path] = sorted(discovered_set)

    audit_rows: List[Dict[str, Any]] = []
    quarantined_count = 0
    retained_count = 0

    for db_path in discovered_dbs:
        try:
            abs_str = str(db_path.resolve())
            size_bytes = db_path.stat().st_size if db_path.exists() else 0
        except OSError:
            continue
        size_mb = round(size_bytes / (1024 * 1024), 3)
        pids = sorted(set(open_fds.get(abs_str, [])))

        tables, conn = _inspect_sqlite_db(db_path)
        liberated: List[str] = []
        if conn is not None:
            liberated = _liberate_domain_data(db_path, conn, tables)
            conn.close()

        is_allowlisted = abs_str in ACTIVE_L2_ALLOWLIST
        has_live_pids = len(pids) > 0

        if is_allowlisted or has_live_pids:
            action = "RETAINED_L2_SIDECAR" if is_allowlisted else f"RETAINED_ACTIVE_FD(pids={pids})"
            retained_count += 1
        else:
            rel_subpath = db_path.relative_to(ROOT)
            dest_path = relics_dir / rel_subpath
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(db_path), str(dest_path))
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(str(db_path) + suffix)
                try:
                    if sidecar.exists():
                        shutil.move(str(sidecar), str(dest_path) + suffix)
                except OSError:
                    pass
            action = f"QUARANTINED -> {dest_path}"
            quarantined_count += 1

        audit_rows.append({
            "db_path": str(db_path.relative_to(ROOT)),
            "size_mb": size_mb,
            "tables": tables,
            "open_pids": pids,
            "liberated": liberated,
            "action": action,
        })

    md_lines = [
        "# KISS & LITE SQLite Sweep & VFS Liberation Receipt (WO0011282)",
        f"- **Executed UTC**: `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`",
        f"- **Total `.db` Files Audited**: `{len(audit_rows)}`",
        f"- **Quarantine Vault**: `{relics_dir}`",
        f"- **Quarantined Count**: `{quarantined_count}`",
        f"- **Retained Active L2 Sidecars**: `{retained_count}`",
        "",
        "| Relative DB Path | Size (MB) | Tables & Row Counts | Liberated to VFS / Drops | Disposition |",
        "| :--- | ---: | :--- | :--- | :--- |",
    ]
    for r in audit_rows:
        t_str = ", ".join(f"`{t['table']}` ({t['rows']})" for t in r["tables"]) or "*0 tables (empty)*"
        lib_str = "<br>".join(r["liberated"]) or "—"
        md_lines.append(
            f"| `{r['db_path']}` | {r['size_mb']:.3f} | {t_str} | {lib_str} | `{r['action']}` |"
        )

    audit_md_path = DROPS_ROOT / "SQLITE_PURGE_AUDIT_2026_10_21.md"
    _atomic_write(audit_md_path, "\n".join(md_lines) + "\n")

    return {
        "total_audited": len(audit_rows),
        "quarantined": quarantined_count,
        "retained": retained_count,
        "audit_markdown": str(audit_md_path),
        "details": audit_rows,
    }


if __name__ == "__main__":
    result = run_sweep()
    print(json.dumps({
        "status": "SWEEP_COMPLETED",
        "total_audited": result["total_audited"],
        "quarantined": result["quarantined"],
        "retained": result["retained"],
        "audit_markdown": result["audit_markdown"],
    }, indent=2))
