#!/home/james/stacklabs/.venv/bin/python3
"""
Float Valve Sensor: Zero-token (<2ms) audit comparing active slate and sys_sports_team
against data/geo_lexicon_registry.json.
Returns Exit 0 when all active slate teams are hydrated and cliche-free, or Exit 1 when hydration is needed.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Set

PROJECT_ROOT = Path("/home/james/stacklabs")
DNA_DB_PATH = PROJECT_ROOT / "dna" / "sovereign_now.db"
REGISTRY_PATH = PROJECT_ROOT / "data" / "geo_lexicon_registry.json"
UNIFIED_SLATE_SHM = Path("/dev/shm/vfs/schedule/unified_slate.json")

BANNED_CLICHES = (
    "liberty bell",
    "space needle",
    "gateway arch",
    "empire state building",
    "golden gate bridge",
)


def load_hydrated_keys() -> Dict[str, dict]:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            nested = raw.get("teams", {})
            merged = dict(nested) if isinstance(nested, dict) else {}
            for k, v in raw.items():
                if isinstance(v, dict) and "team_abbr" in v:
                    merged[k.upper()] = v
            return merged
    except (OSError, ValueError):
        return {}
    return {}


def get_active_slate_teams() -> List[str]:
    teams: List[str] = []
    if UNIFIED_SLATE_SHM.exists():
        try:
            data = json.loads(UNIFIED_SLATE_SHM.read_text(encoding="utf-8"))
            games = data if isinstance(data, list) else data.get("games", [])
            for g in games:
                for key in ("away_team", "home_team", "away_abbr", "home_abbr"):
                    val = str(g.get(key) or "").strip().upper()
                    if val and val not in teams:
                        teams.append(val)
        except (OSError, ValueError):
            pass
    return teams


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero-Token Float Valve Sensor for Geo-Lexicon Registry")
    parser.add_argument("--team", type=str, help="Check specific team abbreviation(s)")
    parser.add_argument("--slate-only", action="store_true", help="Audit only active slate teams")
    args = parser.parse_args()

    hydrated = load_hydrated_keys()
    missing: List[str] = []
    cliche_violations: List[str] = []

    if args.team:
        check_list = [t.strip().upper() for t in args.team.split(",") if t.strip()]
    else:
        check_list = get_active_slate_teams()
        if not check_list and not args.slate_only and DNA_DB_PATH.exists():
            conn = sqlite3.connect(str(DNA_DB_PATH), timeout=5.0)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                rows = conn.execute("SELECT team_abbr FROM sys_sports_team LIMIT 100").fetchall()
                check_list = [str(r[0]).upper() for r in rows]
            finally:
                conn.close()

    for code in check_list:
        entry = hydrated.get(code)
        if not entry:
            missing.append(code)
            continue
        blob = json.dumps(entry).lower()
        for cliche in BANNED_CLICHES:
            if cliche in blob:
                cliche_violations.append(f"{code}:{cliche}")

    status = {
        "hydrated_total": len(hydrated),
        "checked_count": len(check_list),
        "missing_teams": missing[:20],
        "cliche_violations": cliche_violations,
    }
    print(json.dumps(status))
    if missing or cliche_violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
