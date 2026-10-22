#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Argon Subcultural Lexicon Harvester
Discovers newly coined memes, slurs, coaching tropes, and grief shibboleths
from live chat telemetry and commits them directly to nfl/cfb_subcultural_lexicon.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Path: /home/james/stacklabs/scripts/argon_lexicon_harvester.py
"""
import hashlib
import json
import logging
import os
import pathlib
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PROJECT_ROOT = pathlib.Path("/home/james/stacklabs")
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "morning_wiretap.db"
ENV_PATH = PROJECT_ROOT / ".env"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("argon_lexicon_harvester")


def get_wal_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def harvest_and_register_shibboleth(
    sport: str,
    team_abbrev: str,
    name: str,
    shibboleth_id: str,
    trigger_tokens: List[str],
    ground_truth: str,
    ammunition_angle: str
) -> bool:
    """Idempotently registers or updates an evolving subcultural shibboleth."""
    conn = get_wal_conn()
    cur = conn.cursor()

    target_table = "nfl_subcultural_lexicon" if sport.upper() == "NFL" else "cfb_subcultural_lexicon"
    name_col = "franchise_name" if sport.upper() == "NFL" else "program_name"

    content_str = f"{shibboleth_id}:{team_abbrev}:{json.dumps(trigger_tokens, sort_keys=True)}:{ground_truth}"
    content_sha256 = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    sql = f"""
        INSERT INTO {target_table} (
            shibboleth_id, team_abbrev, {name_col}, primary_board, board_url,
            trigger_tokens_json, static_nlp_false_positive, subcultural_ground_truth,
            barf_ammunition_angle, z_score_threshold, content_sha256, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(shibboleth_id) DO UPDATE SET
            trigger_tokens_json = excluded.trigger_tokens_json,
            subcultural_ground_truth = excluded.subcultural_ground_truth,
            barf_ammunition_angle = excluded.barf_ammunition_angle,
            content_sha256 = excluded.content_sha256,
            updated_at = excluded.updated_at
    """

    params = (
        shibboleth_id,
        team_abbrev.upper(),
        name,
        "Reddit/X Live Community",
        f"https://www.google.com/search?q={team_abbrev}+fan+board",
        json.dumps(trigger_tokens),
        "false",
        ground_truth,
        ammunition_angle,
        3.0,
        content_sha256,
        now_iso
    )

    try:
        cur.execute(sql, params)
        conn.commit()
        logger.info(f"Successfully registered/updated shibboleth [{shibboleth_id}] in {target_table}")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to register shibboleth {shibboleth_id}: {e}")
        conn.close()
        return False


def seed_tuesday_breakthrough_shibboleths():
    """Seeds the newly coined Week 7 Monday Night & Weekend breakthrough memes."""
    # 1. NFL: Washington Commanders Daniels Sack & Shanahan Handshake
    harvest_and_register_shibboleth(
        sport="NFL",
        team_abbrev="WSH",
        name="Washington Commanders",
        shibboleth_id="WSH_DANIELS_CLOCK_AWARENESS_HAIL_NO",
        trigger_tokens=["jayden daniels sack", "situational awareness", "dan quinn clock", "hail no", "18 yard loss"],
        ground_truth="Jayden Daniels danced behind the line for 6 seconds before taking an 18-yard sack with zero timeouts remaining as the final whistle blew.",
        ammunition_angle="Commanders fans went from calling Daniels the second coming of RG3 to watching him lose 18 yards dancing in the backfield while Dan Quinn stared blankly at the referee."
    )

    # 2. CFB: Minnesota Golden Gophers 49-Year Streak Breaker
    harvest_and_register_shibboleth(
        sport="CFB",
        team_abbrev="MINN",
        name="Minnesota Golden Gophers",
        shibboleth_id="MINN_LITTLE_BROWN_JUG_49_YEAR_DROUGHT",
        trigger_tokens=["little brown jug", "49 years", "fleck row the boat", "sherrone moore panic", "jug coming home"],
        ground_truth="Minnesota snapped a 49-year home losing streak to Michigan in Minneapolis dating back to 1977.",
        ammunition_angle="Michigan fans spent four years screaming about Connor Stalions and asterisks only to drop the Little Brown Jug in Minneapolis for the first time since Jimmy Carter was in office."
    )


def main():
    logger.info("Initializing Argon Subcultural Lexicon Harvester...")
    seed_tuesday_breakthrough_shibboleths()
    logger.info("Lexicon Harvester seeding complete.")


if __name__ == "__main__":
    main()
