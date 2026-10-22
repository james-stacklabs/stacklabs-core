#!/home/james/stacklabs/.venv/bin/python3
"""
Surgical Wrench: Geo-Lexicon Hydrator with Auto-Team Discovery & Vertex AI Gateway Binding.
Resolves team metadata from dna/sovereign_now.db (auto-discovering from active slate or ESPN if missing),
harvests multi-channel shibboleths from data/morning_wiretap.db, and synthesizes regional folklore
via scripts.advocate_model_gateway.generate_advocate_turn into data/geo_lexicon_registry.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.advocate_model_gateway import generate_advocate_turn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_geo_hydration")

DNA_DB_PATH = PROJECT_ROOT / "dna" / "sovereign_now.db"
WIRETAP_DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
REGISTRY_PATH = PROJECT_ROOT / "data" / "geo_lexicon_registry.json"
UNIFIED_SLATE_SHM = Path("/dev/shm/vfs/schedule/unified_slate.json")

BANNED_TOURIST_CLICHES = (
    "liberty bell",
    "space needle",
    "gateway arch",
    "empire state building",
    "golden gate bridge",
    "statue of liberty",
    "times square",
    "hollywood sign",
)


class PooledHttpClient:
    """Shared HTTP client with connection pooling and jittered exponential backoff."""

    def __init__(self) -> None:
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"User-Agent": "StackLabs-GeoHydrator/1.0"})

    def get_json(self, url: str, timeout: float = 10.0, max_attempts: int = 3) -> Dict[str, Any]:
        base_backoff_s = 0.5
        max_backoff_s = 6.0
        for attempt in range(max_attempts):
            try:
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code in (429, 502, 503, 504):
                    retry_after_hdr = resp.headers.get("Retry-After")
                    retry_after = float(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else None
                    cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
                    sleep_s = retry_after if retry_after is not None else random.uniform(cap * 0.5, cap)
                    logger.warning("HTTP %s on %s; sleeping %.2fs", resp.status_code, url, sleep_s)
                    time.sleep(sleep_s)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                if attempt + 1 >= max_attempts:
                    logger.error("HTTP GET exhausted for %s: %s", url, exc)
                    return {}
                cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
                time.sleep(random.uniform(cap * 0.5, cap))
        return {}


HTTP_CLIENT = PooledHttpClient()


def open_sqlite_wal(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def discover_and_seed_team(conn: sqlite3.Connection, team_abbr: str) -> Optional[Dict[str, Any]]:
    """Auto-discover missing team from active slate or ESPN directory and upsert into sys_sports_team."""
    abbr = team_abbr.strip().upper()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Check active shared-memory slate first
    if UNIFIED_SLATE_SHM.exists():
        try:
            slate_data = json.loads(UNIFIED_SLATE_SHM.read_text(encoding="utf-8"))
            games = slate_data if isinstance(slate_data, list) else slate_data.get("games", [])
            for g in games:
                for prefix in ("home", "away"):
                    code = str(g.get(f"{prefix}_team") or g.get(f"{prefix}_abbr") or "").upper()
                    if code == abbr:
                        full_name = str(g.get(f"{prefix}_name") or g.get(f"{prefix}_full_name") or abbr)
                        sport = str(g.get("sport") or "CFB").upper()
                        league = str(g.get("league") or ("FBS" if sport == "CFB" else sport)).upper()
                        parts = full_name.rsplit(" ", 1)
                        city = parts[0] if len(parts) > 1 else abbr
                        mascot = parts[1] if len(parts) > 1 else abbr
                        syns = json.dumps(sorted({abbr.lower(), city.lower(), mascot.lower(), full_name.lower()}))
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO sys_sports_team
                            (team_abbr, city, name, full_name, sport, league, primary_color, secondary_color, synonyms_json, espn_slug, mlb_id, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, '#0B0D13', '#11141E', ?, ?, NULL, ?, ?)
                            """,
                            (abbr, city, mascot, full_name, sport, league, syns, full_name.lower().replace(" ", "-"), now_str, now_str),
                        )
                        conn.commit()
                        break
        except (OSError, ValueError, sqlite3.Error) as exc:
            logger.warning("Unified slate inspection warning for %s: %s", abbr, exc)

    # 2. Query ESPN directory if still not present
    row = conn.execute("SELECT * FROM sys_sports_team WHERE UPPER(team_abbr) = ?", (abbr,)).fetchone()
    if row is None:
        endpoints = [
            ("CFB", "FBS", "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=1000"),
            ("NFL", "NFL", "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=100"),
            ("MLB", "MLB", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams?limit=100"),
        ]
        for sport, league, url in endpoints:
            payload = HTTP_CLIENT.get_json(url)
            teams = payload.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
            for entry in teams:
                t = entry.get("team", {})
                espn_abbr = str(t.get("abbreviation") or "").upper()
                location = str(t.get("location") or espn_abbr)
                name = str(t.get("name") or espn_abbr)
                full_name = str(t.get("displayName") or f"{location} {name}")
                if espn_abbr == abbr or (abbr == "MTSU" and "middle tennessee" in full_name.lower()):
                    p_color = "#" + str(t.get("color") or "0B0D13").lstrip("#")
                    s_color = "#" + str(t.get("alternateColor") or "11141E").lstrip("#")
                    syns = json.dumps(sorted({abbr.lower(), espn_abbr.lower(), location.lower(), name.lower(), full_name.lower()}))
                    slug = str(t.get("slug") or full_name.lower().replace(" ", "-"))
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO sys_sports_team
                        (team_abbr, city, name, full_name, sport, league, primary_color, secondary_color, synonyms_json, espn_slug, mlb_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                        """,
                        (abbr, location, name, full_name, sport, league, p_color, s_color, syns, slug, now_str, now_str),
                    )
                    conn.commit()
                    break
            row = conn.execute("SELECT * FROM sys_sports_team WHERE UPPER(team_abbr) = ?", (abbr,)).fetchone()
            if row is not None:
                break

    if row is None:
        return None
    return dict(row)


def get_team_metadata(team_abbr: str) -> Dict[str, Any]:
    abbr = team_abbr.strip().upper()
    conn = open_sqlite_wal(DNA_DB_PATH)
    try:
        row = conn.execute(
            "SELECT * FROM sys_sports_team WHERE UPPER(team_abbr) = ? LIMIT 1",
            (abbr,),
        ).fetchone()
        if row is not None:
            return dict(row)
        discovered = discover_and_seed_team(conn, abbr)
        if discovered is not None:
            return discovered
        raise ValueError(f"Team {abbr} not found in dna/sovereign_now.db (sys_sports_team) and auto-discovery returned empty")
    finally:
        conn.close()


def resolve_candidate_channel_keys(conn: sqlite3.Connection, team_abbr: str) -> Tuple[str, ...]:
    abbr = team_abbr.strip().upper()
    keys = {f"{abbr}_dynamic"}
    try:
        rows = conn.execute(
            """
            SELECT game_pk, home_team, away_team, stream_id
            FROM watch_party_streams
            WHERE UPPER(home_team) = ? OR UPPER(away_team) = ?
            LIMIT 20
            """,
            (abbr, abbr),
        ).fetchall()
        for r in rows:
            home = str(r["home_team"] or "").upper()
            away = str(r["away_team"] or "").upper()
            gpk = str(r["game_pk"] or "")
            sid = str(r["stream_id"] or "")
            if home and away:
                keys.add(f"{away}@{home} LIVE")
                keys.add(f"{home}_dynamic")
                keys.add(f"{away}_dynamic")
            if gpk:
                keys.add(f"CFB_{gpk}")
                keys.add(f"NFL_{gpk}")
                keys.add(f"MLB_{gpk}")
            if sid:
                keys.add(sid)
    except sqlite3.Error as exc:
        logger.debug("watch_party_streams lookup note for %s: %s", abbr, exc)
    return tuple(sorted(keys))


def harvest_wiretap_shibboleths(team_abbr: str) -> List[str]:
    if not WIRETAP_DB_PATH.exists():
        return []
    conn = open_sqlite_wal(WIRETAP_DB_PATH)
    samples: List[str] = []
    try:
        # 1. Check cfb_subcultural_lexicon if present
        try:
            lex_rows = conn.execute(
                "SELECT shibboleth, lore_context FROM cfb_subcultural_lexicon WHERE UPPER(team_abbr) = ? LIMIT 10",
                (team_abbr.upper(),),
            ).fetchall()
            for lr in lex_rows:
                token = str(lr["shibboleth"] or "").strip()
                ctx = str(lr["lore_context"] or "").strip()
                if token:
                    samples.append(f"{token}: {ctx}" if ctx else token)
        except sqlite3.Error:
            pass

        # 2. Multi-channel indexed cursor scan on chat_telemetry
        cand_keys = resolve_candidate_channel_keys(conn, team_abbr)
        if cand_keys:
            placeholders = ",".join("?" for _ in cand_keys)
            max_row = conn.execute(
                f"SELECT COALESCE(MAX(id), 0) AS max_id FROM chat_telemetry WHERE channel_key IN ({placeholders})",
                cand_keys,
            ).fetchone()
            max_id = int(max_row["max_id"]) if max_row else 0
            floor_id = max(0, max_id - 25000)
            query = (
                f"SELECT message FROM chat_telemetry "
                f"WHERE channel_key IN ({placeholders}) AND id > ? "
                f"ORDER BY id ASC LIMIT 250"
            )
            params: Tuple[Any, ...] = (*cand_keys, floor_id)
            chat_rows = conn.execute(query, params).fetchall()
            for cr in chat_rows:
                msg = re.sub(r":[a-zA-Z0-9_+-]+:", "", str(cr["message"] or "")).strip()
                if 15 <= len(msg) <= 180 and not msg.startswith("!"):
                    samples.append(msg)
                    if len(samples) >= 15:
                        break
    except sqlite3.Error as exc:
        logger.warning("Wiretap harvest warning for %s: %s", team_abbr, exc)
    finally:
        conn.close()
    return samples[:15]


def sanitize_tourist_cliches(text: str) -> str:
    cleaned = text
    for cliche in BANNED_TOURIST_CLICHES:
        cleaned = re.sub(re.escape(cliche), "local concrete", cleaned, flags=re.IGNORECASE)
    return cleaned


def hydrate_single_team(team_abbr: str) -> Dict[str, Any]:
    meta = get_team_metadata(team_abbr)
    abbr = str(meta["team_abbr"]).upper()
    full_name = str(meta.get("full_name") or abbr)
    city = str(meta.get("city") or abbr)
    sport = str(meta.get("sport") or "CFB")
    league = str(meta.get("league") or "FBS")

    shibboleths = harvest_wiretap_shibboleths(abbr)
    shibboleth_block = "\n".join(f"- {s}" for s in shibboleths[:8]) if shibboleths else "- Pure regional sicko trench folklore"

    system_prompt = (
        "You are Burl and Sammy The Savant curating the StackLabs Geo-Lexicon Registry. "
        "Return STRICT JSON ONLY with keys: "
        '"stadium_hex", "caloric_hazard", "commuter_misery", "regional_shibboleths" (list of 4 strings), '
        '"folklore_scar". Never mention generic tourist landmarks (Liberty Bell, Space Needle, Gateway Arch).'
    )
    user_prompt = (
        f"Hydrate authentic local sports folklore for {full_name} ({abbr} - {sport}/{league}, {city}).\n"
        f"Observed wiretap context:\n{shibboleth_block}\n"
        "Respond with raw JSON object only."
    )

    combined_prompt = f"{system_prompt}\n\n{user_prompt}"
    gw_result = generate_advocate_turn(combined_prompt, persona="burl")
    if isinstance(gw_result, tuple):
        raw_text, provider = gw_result
    elif isinstance(gw_result, dict):
        raw_text = str(gw_result.get("text", ""))
        provider = str(gw_result.get("provider", "vertex_ai_stacklabs_foundry"))
    else:
        raw_text = str(gw_result)
        provider = "gateway"

    parsed: Dict[str, Any] = {}
    json_match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
        except ValueError:
            parsed = {}

    entry: Dict[str, Any] = {
        "team_abbr": abbr,
        "full_name": full_name,
        "city": city,
        "sport": sport,
        "league": league,
        "stadium_hex": sanitize_tourist_cliches(
            str(parsed.get("stadium_hex") or f"{city} turf vortex and 4th-quarter red-zone stalling curse")
        ),
        "caloric_hazard": sanitize_tourist_cliches(
            str(parsed.get("caloric_hazard") or f"{city} parking-lot smoker foil-wrapped tailgate tray")
        ),
        "commuter_misery": sanitize_tourist_cliches(
            str(parsed.get("commuter_misery") or f"{city} post-game expressway bottleneck gridlock")
        ),
        "regional_shibboleths": [
            sanitize_tourist_cliches(str(item))
            for item in (parsed.get("regional_shibboleths") or [
                f"{full_name} trench sweat",
                f"{city} late-night call-in panic",
                f"{abbr} 3rd-and-long draw play",
                f"{city} bleacher rain poncho misery",
            ])[:4]
        ],
        "folklore_scar": sanitize_tourist_cliches(
            str(parsed.get("folklore_scar") or sanitize_tourist_cliches(raw_text[:200]).strip())
        ),
        "wiretap_samples_joined": len(shibboleths),
        "provider": provider,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    canonical_bytes = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
    entry["content_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()
    return {abbr: entry}


def load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"teams": {}, "updated_at": ""}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "teams" in data and isinstance(data["teams"], dict):
            return data
        if isinstance(data, dict):
            return {"teams": data, "updated_at": ""}
    except (OSError, ValueError) as exc:
        logger.warning("Registry load fallback: %s", exc)
    return {"teams": {}, "updated_at": ""}


def save_registry_atomic(registry: Dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp_path = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, REGISTRY_PATH)


def select_next_missing_teams(limit: int) -> List[str]:
    registry = load_registry()
    teams_map = registry.get("teams", {})
    missing: List[str] = []

    if UNIFIED_SLATE_SHM.exists():
        try:
            slate_data = json.loads(UNIFIED_SLATE_SHM.read_text(encoding="utf-8"))
            games = slate_data if isinstance(slate_data, list) else slate_data.get("games", [])
            for g in games:
                for key in ("away_team", "home_team", "away_abbr", "home_abbr"):
                    code = str(g.get(key) or "").strip().upper()
                    if code and code not in teams_map and code not in missing:
                        missing.append(code)
                        if len(missing) >= limit:
                            return missing
        except (OSError, ValueError) as exc:
            logger.debug("Slate scan note: %s", exc)

    conn = open_sqlite_wal(DNA_DB_PATH)
    try:
        rows = conn.execute("SELECT team_abbr FROM sys_sports_team ORDER BY team_abbr ASC").fetchall()
        for r in rows:
            code = str(r["team_abbr"]).strip().upper()
            if code and code not in teams_map and code not in missing:
                missing.append(code)
                if len(missing) >= limit:
                    break
    finally:
        conn.close()
    return missing[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="StackLabs Surgical Geo-Lexicon Hydrator")
    parser.add_argument("--team", type=str, help="Hydrate a specific team abbreviation (e.g., MTSU, FIU)")
    parser.add_argument("--next", type=int, default=0, help="Hydrate next N missing teams (clamped <= 5)")
    parser.add_argument("--dry-run", action="store_true", help="Verify metadata resolution without mutating disk")
    args = parser.parse_args()

    targets: List[str] = []
    if args.team:
        targets = [t.strip().upper() for t in args.team.split(",") if t.strip()]
    elif args.next > 0:
        targets = select_next_missing_teams(min(int(args.next), 5))
    else:
        targets = select_next_missing_teams(2)

    if not targets:
        logger.info("No missing teams require geo hydration.")
        return 0

    registry = load_registry()
    teams_map = registry.setdefault("teams", {})
    hydrated_receipts: Dict[str, Any] = {}

    for t_code in targets:
        if args.dry_run:
            meta = get_team_metadata(t_code)
            logger.info("[DRY-RUN] Verified metadata for %s -> %s", t_code, meta.get("full_name"))
            continue
        receipt = hydrate_single_team(t_code)
        hydrated_receipts.update(receipt)
        teams_map.update(receipt)
        # Keep top-level key compatibility for swanson_geo_cmdb_collider.py
        registry.update(receipt)
        logger.info("✓ Hydrated %s (%s)", t_code, receipt[t_code]["full_name"])

    if not args.dry_run and hydrated_receipts:
        save_registry_atomic(registry)
        print(json.dumps({"status": "HYDRATED", "count": len(hydrated_receipts), "teams": list(hydrated_receipts.keys())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
