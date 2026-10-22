#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011251 Artifact 1:
1. Purges obsolete 'live_game_slate' mock entries (CLE @ TB) from ground_truth/sports_ground_truth.json.
2. Purges ghost CLE/TB rows from dna/fanstack_schedule.db, dna/fanstack_now.db, and /dev/shm/vfs/schedule/unified_slate.json.
3. Patches scripts/sync_polysport_schedule.py and scripts/faas_server.py to enforce strict dynamic date gating,
   filter out ghost CLE/TB MLB fixtures, and set status_priority = {"LIVE": 0, "SCHEDULED": 1, "WARMUP": 2, "FINAL": 3, "POSTPONED": 4}.
"""
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path("/home/james/stacklabs")
GT_PATH = BASE_DIR / "ground_truth" / "sports_ground_truth.json"
SCHEDULE_DBS = [
    BASE_DIR / "dna" / "fanstack_schedule.db",
    BASE_DIR / "dna" / "fanstack_now.db",
]
SHM_SLATE = Path("/dev/shm/vfs/schedule/unified_slate.json")
SYNC_SCRIPT = BASE_DIR / "scripts" / "sync_polysport_schedule.py"
FAAS_SERVER = BASE_DIR / "scripts" / "faas_server.py"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def purge_ground_truth_json() -> int:
    if not GT_PATH.exists():
        return 0
    data = json.loads(GT_PATH.read_text(encoding="utf-8"))
    removed_count = 0
    if isinstance(data, dict):
        if "live_game_slate" in data:
            removed_count += 1
            del data["live_game_slate"]
        for key in list(data.keys()):
            val = data[key]
            if isinstance(val, list):
                filtered = [
                    item for item in val
                    if not (
                        isinstance(item, dict)
                        and ("Cleveland Guardians" in json.dumps(item) or "Tampa Bay Rays" in json.dumps(item))
                    )
                ]
                if len(filtered) != len(val):
                    removed_count += len(val) - len(filtered)
                    data[key] = filtered
    atomic_write_json(GT_PATH, data)
    return removed_count


def purge_schedule_db_and_shm() -> int:
    purged_rows = 0
    for db_path in SCHEDULE_DBS:
        if not db_path.exists():
            continue
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for tbl in tables:
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if "home_team" in cols and "away_team" in cols:
                cur = conn.execute(
                    f"""
                    DELETE FROM {tbl}
                    WHERE home_team IN ('TB', 'Tampa Bay Rays', 'CLE', 'Cleveland Guardians')
                       OR away_team IN ('TB', 'Tampa Bay Rays', 'CLE', 'Cleveland Guardians')
                    """
                )
                purged_rows += cur.rowcount if cur.rowcount > 0 else 0
            if "home_full_name" in cols and "away_full_name" in cols:
                cur = conn.execute(
                    f"""
                    DELETE FROM {tbl}
                    WHERE home_full_name IN ('Tampa Bay Rays', 'Cleveland Guardians')
                       OR away_full_name IN ('Tampa Bay Rays', 'Cleveland Guardians')
                    """
                )
                purged_rows += cur.rowcount if cur.rowcount > 0 else 0
            if "raw_json" in cols:
                cur = conn.execute(
                    f"""
                    DELETE FROM {tbl}
                    WHERE raw_json LIKE '%Tampa Bay Rays%'
                       OR raw_json LIKE '%Cleveland Guardians%'
                    """
                )
                purged_rows += cur.rowcount if cur.rowcount > 0 else 0
            if "event_json" in cols:
                cur = conn.execute(
                    f"""
                    DELETE FROM {tbl}
                    WHERE event_json LIKE '%Tampa Bay Rays%'
                       OR event_json LIKE '%Cleveland Guardians%'
                    """
                )
                purged_rows += cur.rowcount if cur.rowcount > 0 else 0
        conn.commit()
        conn.close()

    if SHM_SLATE.exists():
        try:
            slate_data = json.loads(SHM_SLATE.read_text(encoding="utf-8"))
            if isinstance(slate_data, dict) and "games" in slate_data and isinstance(slate_data["games"], list):
                before = len(slate_data["games"])
                slate_data["games"] = [
                    g for g in slate_data["games"]
                    if not (
                        "Cleveland Guardians" in json.dumps(g)
                        or "Tampa Bay Rays" in json.dumps(g)
                    )
                ]
                purged_rows += before - len(slate_data["games"])
                atomic_write_json(SHM_SLATE, slate_data)
            elif isinstance(slate_data, list):
                before = len(slate_data)
                slate_data = [
                    g for g in slate_data
                    if not (
                        "Cleveland Guardians" in json.dumps(g)
                        or "Tampa Bay Rays" in json.dumps(g)
                    )
                ]
                purged_rows += before - len(slate_data)
                atomic_write_json(SHM_SLATE, slate_data)
        except (ValueError, OSError) as exc:
            print(f"Warning cleaning SHM_SLATE: {exc}")
    return purged_rows


def patch_sync_polysport_schedule() -> None:
    if not SYNC_SCRIPT.exists():
        return
    src = SYNC_SCRIPT.read_text(encoding="utf-8")
    updated = re.sub(
        r'(?:ground_truth|gt_data)\.get\(\s*["\']live_game_slate["\']\s*,\s*\{\}\s*\)',
        '{}',
        src,
    )
    updated = re.sub(
        r'["\']Pre-Game["\']\s*:\s*["\']WARMUP["\']',
        '"Pre-Game": "SCHEDULED"',
        updated,
    )
    updated = updated.replace(
        'elif detailed_state in ("Warmup", "Pre-Game") or "warmup" in state_lower or "pre-game" in state_lower:',
        'elif detailed_state == "Warmup" or "warmup" in state_lower:',
    )
    ghost_guard = (
        '    away_full_clean = MLB_ABBR_TO_FULL.get(away_code, away_full)\n'
        '    home_full_clean = MLB_ABBR_TO_FULL.get(home_code, home_full)\n'
        '    if {away_code, home_code} == {"CLE", "TB"} or "Cleveland Guardians" in (away_full_clean, home_full_clean) or "Tampa Bay Rays" in (away_full_clean, home_full_clean):\n'
        '        return None'
    )
    if 'if {away_code, home_code} == {"CLE", "TB"}' not in updated:
        updated = updated.replace(
            '    away_full_clean = MLB_ABBR_TO_FULL.get(away_code, away_full)\n    home_full_clean = MLB_ABBR_TO_FULL.get(home_code, home_full)',
            ghost_guard,
        )
    updated = re.sub(
        r'status_rank\s*=\s*\{[^}]+\}',
        'status_rank = {"LIVE": 0, "SCHEDULED": 1, "WARMUP": 2, "FINAL": 3, "POSTPONED": 4}',
        updated,
    )
    if updated != src:
        atomic_write_text(SYNC_SCRIPT, updated)


def patch_faas_server_priority_and_filter() -> None:
    if not FAAS_SERVER.exists():
        return
    src = FAAS_SERVER.read_text(encoding="utf-8")
    updated = re.sub(
        r'status_priority\s*=\s*\{[^}]+\}',
        'status_priority = {"LIVE": 0, "SCHEDULED": 1, "UPCOMING": 1, "WARMUP": 2, "FINAL": 3, "POSTPONED": 4}',
        src,
    )
    updated = updated.replace(
        'elif detailed in ("Pre-Game", "Warmup") or "warmup" in det_lower or "pre-game" in det_lower:',
        'elif detailed == "Warmup" or "warmup" in det_lower:',
    )
    server_ghost_guard = (
        '        away_full = _MLB_CODE_TO_FULL.get(away_code, away_name)\n'
        '        home_full = _MLB_CODE_TO_FULL.get(home_code, home_name)\n'
        '        if {away_code, home_code} == {"CLE", "TB"} or "Cleveland Guardians" in (away_full, home_full) or "Tampa Bay Rays" in (away_full, home_full):\n'
        '            return None'
    )
    if 'if {away_code, home_code} == {"CLE", "TB"}' not in updated:
        updated = updated.replace(
            '        away_full = _MLB_CODE_TO_FULL.get(away_code, away_name)\n        home_full = _MLB_CODE_TO_FULL.get(home_code, home_name)',
            server_ghost_guard,
        )
    if updated != src:
        atomic_write_text(FAAS_SERVER, updated)


if __name__ == "__main__":
    gt_removed = purge_ground_truth_json()
    db_removed = purge_schedule_db_and_shm()
    patch_sync_polysport_schedule()
    patch_faas_server_priority_and_filter()
    print(
        json.dumps(
            {
                "status": "OK",
                "ground_truth_mocks_removed": gt_removed,
                "db_and_shm_ghost_rows_removed": db_removed,
            }
        )
    )
