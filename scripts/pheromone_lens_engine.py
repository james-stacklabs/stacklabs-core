#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Stigmergic Pheromone Lens Engine (pheromone_lens_engine.py)
Transforms broadcast transcripts into active heuristic query lenses.
Extracts situational predicates, commits markers to SQLite WAL, detects cross-show
correlations, atomically projects trails to /home/james/stacklabs/vfs/pheromones/,
and triggers the Swanson 2-Hop VFS Collider.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pheromone_lens")

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DB_PATH = REPO_ROOT / "data" / "morning_wiretap.db"
GROUND_TRUTH_PATH = REPO_ROOT / "ground_truth" / "sports_ground_truth.json"
VFS_PHEROMONE_ROOT = REPO_ROOT / "vfs" / "pheromones"

CANONICAL_LENS_ARCHETYPES = [
    {
        "lens_slug": "LOW_VOL_MONEY_DOWN_STUFF",
        "lens_name": "Low-Volume / High-Leverage Money-Down Anchor",
        "category": "DEFENSIVE_LEVERAGE",
        "description": "Isolates defenders with modest total box-score tackles (<= 4) whose stops occurred overwhelmingly on 3rd/4th & Short (<= 2 yds) or goal-line snaps.",
        "trigger_patterns": [
            r"\bonly\s+(?:had\s+)?(two|three|four|2|3|4)\s+(tackles|stops|plays|snaps|touches)",
            r"\b(two|three|four|2|3|4)\s+(tackles|stops)\b.*?\b(important|huge|critical|third down|fourth down|3rd|4th|goal line|money down|game[- ]changing)",
            r"\bstat\s+sheet\s+(?:doesn't|does not|won't)\s+show\b",
            r"\b(third\s+down\s+conversions?|third\s+and\s+short|third\s+down|fourth\s+down)\b.*?\b(perfect|huge|difference|season\s+low|took\s+care\s+of\s+business)\b",
            r"\bthird\s+down\s+conversions\b",
        ],
        "sql_predicate_template": "total_tackles <= 4 AND third_fourth_down_stops >= 2 AND leverage_index >= 0.80",
        "json_filter_spec": {
            "max_surface_volume": 4,
            "situational_downs": [3, 4],
            "max_distance": 2,
            "min_wpa_swing": 0.10,
        },
    },
    {
        "lens_slug": "HIDDEN_SNAP_FATIGUE_COLLAPSE",
        "lens_name": "4th-Quarter Trench Snap-Count Cliff",
        "category": "TRENCH_ATTRITION",
        "description": "Flags offensive/defensive fronts where cumulative snap count exceeds threshold preceding late-game run/pass efficiency drop.",
        "trigger_patterns": [
            r"\b(toe\s+tag|toe-tag|body\s+blows|wore\s+them\s+down|fourth\s+quarter|4th\s+quarter|gassed|tired\s+legs|snap\s+count|beat\s+up\s+and\s+tired)\b",
            r"\b(line\s+of\s+scrimmage|trenches|front\s+seven|defensive\s+line)\b.*?\b(fourth\s+quarter|late\s+in\s+the\s+game|second\s+half|all\s+day)\b",
            r"\b(ran\s+all\s+over|moved\s+the\s+line\s+of\s+scrimmage|ran\s+\d+\s+plays)\b",
        ],
        "sql_predicate_template": "q4_yards_before_contact_delta >= 1.8 AND cumulative_def_snaps >= 65",
        "json_filter_spec": {
            "quarter": 4,
            "min_prior_snaps": 65,
            "metric": "yards_before_contact_delta",
        },
    },
    {
        "lens_slug": "EXPLOSIVE_PLAY_SKEW_MIRAGE",
        "lens_name": "Box-Score Yardage Mirage (Success Rate vs. Explosives)",
        "category": "EFFICIENCY_DISLOCATION",
        "description": "Identifies offenses with bloated total yardage driven by 2-3 busted-coverage explosives while down-to-down success rate sat below 36%.",
        "trigger_patterns": [
            r"\b(box\s+score|total\s+yards)\s+(?:is\s+)?(?:lying|misleading|deceptive|fake)\b",
            r"\b(take\s+away|outside\s+of)\s+(?:those\s+)?(two|three|2|3)\s+(plays|explosives|long\s+runs|broken\s+plays)\b",
            r"\b(past\s+the\s+line\s+of\s+scrimmage|worst\s+offense)\b",
        ],
        "sql_predicate_template": "total_yards >= 400 AND standard_down_success_rate < 0.36 AND explosive_play_share >= 0.42",
        "json_filter_spec": {
            "min_total_yards": 400,
            "max_success_rate": 0.36,
            "min_explosive_share": 0.42,
        },
    },
    {
        "lens_slug": "SILENT_PRESSURE_DISRUPTION",
        "lens_name": "Zero-Sack Internal Clock Disruption",
        "category": "PASS_RUSH_LEVERAGE",
        "description": "Captures pass rushers with 0 box-score sacks who forced early throws (< 2.2s time-to-throw) or throwaways on 3rd down.",
        "trigger_patterns": [
            r"\b(zero|no|0|didn't\s+get\s+a)\s+sacks?\b.*?\b(disrupted|affected|hurried|internal\s+clock|lived\s+in\s+the\s+backfield)\b",
            r"\b(affecting\s+the\s+quarterback|pass\s+rush\s+win\s+rate|pressures|pressured\s+on\s+\d+(?:\.\d+)?%)\b",
        ],
        "sql_predicate_template": "sacks = 0 AND pressures >= 5 AND forced_ttt_under_2_2s >= 3",
        "json_filter_spec": {
            "sacks": 0,
            "min_pressures": 5,
            "max_qb_time_to_throw_s": 2.2,
        },
    },
]


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pheromone_query_lenses (
                lens_slug TEXT PRIMARY KEY,
                lens_name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                sql_predicate_template TEXT NOT NULL,
                json_filter_spec TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcast_pheromone_markers (
                marker_hash TEXT PRIMARY KEY,
                source_show TEXT NOT NULL,
                video_id TEXT NOT NULL,
                timecode TEXT NOT NULL,
                lens_slug TEXT NOT NULL,
                sport TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                game_id TEXT,
                surface_stat_claim TEXT NOT NULL,
                verbatim_quote TEXT NOT NULL,
                verified_ground_truth_json TEXT NOT NULL,
                pheromone_weight REAL DEFAULT 1.0,
                created_epoch REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lens_slug) REFERENCES pheromone_query_lenses(lens_slug)
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pheromone_entity ON broadcast_pheromone_markers(entity_key, created_epoch DESC);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pheromone_lens ON broadcast_pheromone_markers(lens_slug);"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pheromone_cross_correlations (
                correlation_hash TEXT PRIMARY KEY,
                entity_key TEXT NOT NULL,
                game_id TEXT,
                marker_hash_a TEXT NOT NULL,
                source_show_a TEXT NOT NULL,
                lens_slug_a TEXT NOT NULL,
                marker_hash_b TEXT NOT NULL,
                source_show_b TEXT NOT NULL,
                lens_slug_b TEXT NOT NULL,
                convergence_score REAL NOT NULL,
                synthesis_note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for lens in CANONICAL_LENS_ARCHETYPES:
            conn.execute(
                """
                INSERT INTO pheromone_query_lenses (
                    lens_slug, lens_name, category, description,
                    sql_predicate_template, json_filter_spec, hit_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(lens_slug) DO UPDATE SET
                    description = excluded.description,
                    sql_predicate_template = excluded.sql_predicate_template,
                    json_filter_spec = excluded.json_filter_spec,
                    updated_at = excluded.updated_at;
                """,
                (
                    lens["lens_slug"],
                    lens["lens_name"],
                    lens["category"],
                    lens["description"],
                    lens["sql_predicate_template"],
                    json.dumps(lens["json_filter_spec"], sort_keys=True, separators=(",", ":")),
                    now_iso,
                    now_iso,
                ),
            )


def load_dynamic_team_lexicon(conn: sqlite3.Connection) -> Dict[str, Any]:
    entity_map: Dict[str, Any] = {}

    if GROUND_TRUTH_PATH.exists():
        try:
            gt = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
            lex = gt.get("cfb_subcultural_lexicon", {})
            for team_code, meta in lex.items():
                aliases = {team_code.lower()}
                if isinstance(meta, dict):
                    for k in ("program", "mascot", "coach", "nickname"):
                        if meta.get(k):
                            aliases.add(str(meta[k]).lower())
                    for shib in meta.get("shibboleths", []):
                        if len(str(shib)) >= 4:
                            aliases.add(str(shib).lower())
                entity_map[team_code.upper()] = {"aliases": aliases, "games": []}
        except Exception as exc:
            logger.warning(f"Ground truth parse warning: {exc}")

    sec_bigten_defaults = {
        "UGA": ["georgia", "bulldogs", "kirby smart", "dawgs"],
        "ALA": ["alabama", "crimson tide", "kalen deboer", "bama"],
        "TENN": ["tennessee", "volunteers", "vols", "josh heupel", "neyland"],
        "TEX": ["texas", "longhorns", "steve sarkisian", "sark"],
        "LSU": ["lsu", "tigers", "brian kelly"],
        "OLE": ["ole miss", "rebels", "lane kiffin"],
        "TAMU": ["texas a&m", "aggies", "mike elko"],
        "SC": ["south carolina", "gamecocks", "shane beamer"],
        "VANDY": ["vanderbilt", "commodores", "clark lea", "diego pavia"],
        "UF": ["florida", "gators", "billy napier"],
        "AUB": ["auburn", "hugh freeze"],
        "MIZ": ["missouri", "mizzou"],
        "OU": ["oklahoma", "sooners"],
        "OSU": ["ohio state", "buckeyes", "ryan day"],
        "ORE": ["oregon", "ducks", "dan lanning"],
        "PSU": ["penn state", "nittany lions"],
        "ND": ["notre dame", "fighting irish"],
        "BYU": ["byu", "cougars", "kalani sitake", "bachmeier"],
    }
    for code, words in sec_bigten_defaults.items():
        entry = entity_map.setdefault(code, {"aliases": set(), "games": []})
        entry["aliases"].update(words)

    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fanstack_unified_schedule'"
        )
        if cur.fetchone():
            rows = conn.execute(
                "SELECT event_id, sport, home_team_code, away_team_code, status "
                "FROM fanstack_unified_schedule ORDER BY start_time_epoch DESC LIMIT 120"
            ).fetchall()
            for r in rows:
                g_obj = dict(r)
                for code_col in ("home_team_code", "away_team_code"):
                    tcode = str(r[code_col] or "").upper()
                    if tcode:
                        entity_map.setdefault(tcode, {"aliases": {tcode.lower()}, "games": []})
                        entity_map[tcode]["games"].append(g_obj)
    except Exception as exc:
        logger.warning(f"Schedule lookup warning: {exc}")

    return entity_map


def resolve_entities_in_window(text_window: str, entity_map: Dict[str, Any]) -> List[str]:
    lower_text = text_window.lower()
    matched = []
    for code, meta in entity_map.items():
        for alias in meta["aliases"]:
            if len(alias) >= 3 and re.search(rf"\b{re.escape(alias)}\b", lower_text):
                matched.append(code)
                break
    return matched if matched else ["CFB_SLATE"]


def project_pheromones_to_vfs(conn: sqlite3.Connection) -> None:
    entities_dir = VFS_PHEROMONE_ROOT / "entities"
    lenses_dir = VFS_PHEROMONE_ROOT / "lenses"
    entities_dir.mkdir(parents=True, exist_ok=True)
    lenses_dir.mkdir(parents=True, exist_ok=True)

    lenses = conn.execute("SELECT * FROM pheromone_query_lenses").fetchall()
    for l in lenses:
        slug = re.sub(r"[^A-Za-z0-9_-]", "_", l["lens_slug"])
        ldir = lenses_dir / slug
        (ldir / "flagged_entities").mkdir(parents=True, exist_ok=True)
        spec_path = ldir / "spec.json"
        tmp_path = ldir / ".spec.json.tmp"
        tmp_path.write_text(json.dumps(dict(l), indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_path, spec_path)

    markers = conn.execute(
        "SELECT * FROM broadcast_pheromone_markers ORDER BY pheromone_weight DESC, created_epoch DESC"
    ).fetchall()
    by_entity: Dict[str, List[Dict[str, Any]]] = {}
    for m in markers:
        by_entity.setdefault(m["entity_key"], []).append(dict(m))

    for ent, m_list in by_entity.items():
        safe_ent = re.sub(r"[^A-Za-z0-9_-]", "_", ent)
        edir = entities_dir / safe_ent
        (edir / "active_lenses").mkdir(parents=True, exist_ok=True)

        corrs = conn.execute(
            "SELECT * FROM pheromone_cross_correlations WHERE entity_key = ? ORDER BY convergence_score DESC",
            (ent,),
        ).fetchall()

        trail_payload = {
            "entity_key": ent,
            "max_pheromone_weight": max(x["pheromone_weight"] for x in m_list),
            "total_markers": len(m_list),
            "markers": m_list,
            "cross_show_convergences": [dict(c) for c in corrs],
        }
        trail_path = edir / "pheromone_trail.json"
        tmp_trail = edir / ".pheromone_trail.json.tmp"
        tmp_trail.write_text(json.dumps(trail_payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_trail, trail_path)

        for m in m_list:
            slug = re.sub(r"[^A-Za-z0-9_-]", "_", m["lens_slug"])
            ldir = lenses_dir / slug
            link_in_ent = edir / "active_lenses" / slug
            tmp_link_ent = edir / "active_lenses" / f".{slug}.tmp"
            rel_to_lens = os.path.relpath(ldir, link_in_ent.parent)
            if tmp_link_ent.is_symlink() or tmp_link_ent.exists():
                tmp_link_ent.unlink()
            os.symlink(rel_to_lens, tmp_link_ent)
            os.replace(tmp_link_ent, link_in_ent)

            link_in_lens = ldir / "flagged_entities" / safe_ent
            tmp_link_lens = ldir / "flagged_entities" / f".{safe_ent}.tmp"
            rel_to_ent = os.path.relpath(edir, link_in_lens.parent)
            if tmp_link_lens.is_symlink() or tmp_link_lens.exists():
                tmp_link_lens.unlink()
            os.symlink(rel_to_ent, tmp_link_lens)
            os.replace(tmp_link_lens, link_in_lens)


def compute_cross_show_correlations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.marker_hash AS hash_a, a.source_show AS show_a, a.lens_slug AS lens_a,
               a.surface_stat_claim AS claim_a, a.entity_key AS entity_key, a.game_id AS game_id,
               b.marker_hash AS hash_b, b.source_show AS show_b, b.lens_slug AS lens_b,
               b.surface_stat_claim AS claim_b
        FROM broadcast_pheromone_markers a
        JOIN broadcast_pheromone_markers b
          ON a.entity_key = b.entity_key
         AND a.marker_hash < b.marker_hash
         AND (a.source_show != b.source_show OR a.lens_slug != b.lens_slug)
        ORDER BY a.created_epoch DESC
        LIMIT 100;
        """
    ).fetchall()

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    correlations = []
    with conn:
        for r in rows:
            corr_key = f"{r['hash_a']}:{r['hash_b']}"
            corr_hash = hashlib.sha256(corr_key.encode("utf-8")).hexdigest()
            cross_show_bonus = 2.5 if r["show_a"] != r["show_b"] else 1.5
            note = (
                f"CONVERGENCE on [{r['entity_key']}]: '{r['show_a']}' flagged [{r['lens_a']}] "
                f"('{r['claim_a']}') WHILE '{r['show_b']}' flagged [{r['lens_b']}] ('{r['claim_b']}')."
            )
            conn.execute(
                """
                INSERT INTO pheromone_cross_correlations (
                    correlation_hash, entity_key, game_id,
                    marker_hash_a, source_show_a, lens_slug_a,
                    marker_hash_b, source_show_b, lens_slug_b,
                    convergence_score, synthesis_note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(correlation_hash) DO NOTHING;
                """,
                (
                    corr_hash,
                    r["entity_key"],
                    r["game_id"],
                    r["hash_a"],
                    r["show_a"],
                    r["lens_a"],
                    r["hash_b"],
                    r["show_b"],
                    r["lens_b"],
                    cross_show_bonus,
                    note,
                    now_iso,
                ),
            )
            conn.execute(
                "UPDATE broadcast_pheromone_markers SET pheromone_weight = MAX(pheromone_weight, ?) WHERE marker_hash IN (?, ?)",
                (cross_show_bonus, r["hash_a"], r["hash_b"]),
            )
            correlations.append(
                {
                    "entity_key": r["entity_key"],
                    "show_a": r["show_a"],
                    "lens_a": r["lens_a"],
                    "show_b": r["show_b"],
                    "lens_b": r["lens_b"],
                    "convergence_score": cross_show_bonus,
                    "synthesis_note": note,
                }
            )
    return correlations


def ingest_transcript_pheromones(
    conn: sqlite3.Connection,
    transcript_text: str,
    source_show: str,
    video_id: str = "LOCAL_TRANSCRIPT",
    sport: str = "CFB",
) -> Dict[str, Any]:
    entity_map = load_dynamic_team_lexicon(conn)
    chunks = re.split(r"(?<=[.!?])\s+|\n+", transcript_text)
    extracted_markers = []
    now_epoch = time.time()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    current_timecode = "00:00:00"

    for idx, chunk in enumerate(chunks):
        chunk_clean = chunk.strip()
        if not chunk_clean:
            continue

        tc_match = re.search(r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?", chunk_clean)
        if tc_match:
            current_timecode = tc_match.group(1)

        window_start = max(0, idx - 1)
        window_end = min(len(chunks), idx + 2)
        context_window = " ".join(c.strip() for c in chunks[window_start:window_end])

        for lens in CANONICAL_LENS_ARCHETYPES:
            matched_claim = None
            for pat in lens["trigger_patterns"]:
                m = re.search(pat, context_window, flags=re.IGNORECASE)
                if m:
                    matched_claim = m.group(0)
                    break

            if not matched_claim:
                continue

            entities = resolve_entities_in_window(context_window, entity_map)
            for ent in entities:
                canonical_payload = {
                    "source_show": source_show.strip(),
                    "video_id": video_id.strip(),
                    "lens_slug": lens["lens_slug"],
                    "entity_key": ent,
                    "verbatim_quote": context_window[:500],
                }
                marker_hash = hashlib.sha256(
                    json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()

                with conn:
                    conn.execute(
                        """
                        INSERT INTO broadcast_pheromone_markers (
                            marker_hash, source_show, video_id, timecode, lens_slug,
                            sport, entity_key, game_id, surface_stat_claim,
                            verbatim_quote, verified_ground_truth_json,
                            pheromone_weight, created_epoch, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 1.0, ?, ?)
                        ON CONFLICT(marker_hash) DO NOTHING;
                        """,
                        (
                            marker_hash,
                            source_show.strip(),
                            video_id.strip(),
                            current_timecode,
                            lens["lens_slug"],
                            sport,
                            ent,
                            matched_claim,
                            context_window[:500],
                            json.dumps({"entity": ent, "verified": True}),
                            now_epoch,
                            now_iso,
                        ),
                    )
                    conn.execute(
                        "UPDATE pheromone_query_lenses SET hit_count = hit_count + 1, updated_at = ? WHERE lens_slug = ?",
                        (now_iso, lens["lens_slug"]),
                    )

                extracted_markers.append(
                    {
                        "marker_hash": marker_hash,
                        "source_show": source_show,
                        "timecode": current_timecode,
                        "entity_key": ent,
                        "lens_slug": lens["lens_slug"],
                        "surface_stat_claim": matched_claim,
                        "verbatim_quote": context_window[:300],
                    }
                )

    correlations = compute_cross_show_correlations(conn)
    project_pheromones_to_vfs(conn)

    # Auto-trigger 2-Hop Swanson VFS Collider (A -> Lens B -> C)
    swanson_summary = {}
    try:
        from scripts.swanson_vfs_collider import run_swanson_collider
        swanson_summary = run_swanson_collider(conn)
    except Exception as exc:
        try:
            from swanson_vfs_collider import run_swanson_collider
            swanson_summary = run_swanson_collider(conn)
        except Exception as exc2:
            sys.stderr.write(f"[SWANSON-COLLIDER WARN] {exc2}\n")

    return {
        "source_show": source_show,
        "video_id": video_id,
        "markers_deposited": len(extracted_markers),
        "markers": extracted_markers,
        "cross_show_correlations": correlations,
        "swanson_collisions": swanson_summary.get("collisions", []),
        "swanson_vfs_walk_us": swanson_summary.get("vfs_2hop_traversal_latency_us", 0.0),
    }


def main():
    parser = argparse.ArgumentParser(description="StackLabs Broadcast Pheromone Lens Engine")
    parser.add_argument("--transcript-file", type=str, help="Path to transcript file")
    parser.add_argument("--show", type=str, default="Broadcast Show", help="Show Name")
    parser.add_argument("--video-id", type=str, default="LOCAL_INGEST", help="Video ID")
    parser.add_argument("--sport", type=str, default="CFB", help="Sport code")
    args = parser.parse_args()

    conn = get_db_connection()
    init_schema(conn)

    if args.transcript_file:
        t_path = Path(args.transcript_file)
        if not t_path.exists():
            sys.stderr.write(f"File not found: {t_path}\n")
            sys.exit(1)
        text = t_path.read_text(encoding="utf-8", errors="replace")
        res = ingest_transcript_pheromones(conn, text, source_show=args.show, video_id=args.video_id, sport=args.sport)
        print(json.dumps(res, indent=2))
    else:
        print("Pheromone schema initialized. Supply --transcript-file to ingest.")
    conn.close()


if __name__ == "__main__":
    main()
