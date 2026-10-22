#!/home/james/stacklabs/.venv/bin/python3
"""
lore_tripwire_engine.py — StackLabs Lore Tripwire & Chatter Hypocrisy Engine
Location: /home/james/stacklabs/scripts/lore_tripwire_engine.py

Tracks targeted stream chatters, identifies cross-sport sacrifice declarations,
pairs early panic pledges with subsequent victory-lap gloats, and synthesizes
structured HypocrisyCard receipts for FaaS telemetry and Barf retort wires.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path("/home/james/stacklabs")
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "morning_wiretap.db"
DEFAULT_WATCHLIST_PATH = DATA_DIR / "wiretap_watchlist.json"
DEFAULT_OUTPUT_VFS = Path("/dev/shm/faas_vfs/telemetry/lore_tripwires.json")
DEFAULT_OUTPUT_DATA = DATA_DIR / "lore_tripwire_receipts.json"


@dataclass
class TripwireHit:
    author: str
    message: str
    timestamp_str: str
    epoch_time: float
    channel_key: str
    rule_id: str
    category: str


@dataclass
class HypocrisyCard:
    card_id: str
    author: str
    sacrifice_quote: str
    sacrifice_timestamp: str
    sacrifice_channel: str
    victory_quote: str
    victory_timestamp: str
    victory_channel: str
    flip_delta: float
    summary: str
    barf_roast_ammo: str


def load_watchlist(filepath: Path = DEFAULT_WATCHLIST_PATH) -> Dict[str, Any]:
    """Load the canonical wiretap watchlist configuration."""
    if not filepath.exists():
        return {"tracked_authors": [], "tripwire_rules": []}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_message_against_rules(
    message: str,
    rules: List[Dict[str, Any]],
) -> Optional[Tuple[str, str]]:
    """
    Evaluates message text against tripwire rules in sub-millisecond time.
    Returns (rule_id, category) if a rule matches, else None.
    """
    text_lower = message.lower()
    for rule in rules:
        rule_id = rule.get("rule_id", "")
        category = rule.get("category", "")
        keywords = rule.get("keywords", [])

        keyword_match = any(kw.lower() in text_lower for kw in keywords)
        if not keyword_match:
            continue

        if rule.get("require_cross_tokens", False):
            tokens_a = rule.get("token_group_a", [])
            tokens_b = rule.get("token_group_b", [])
            has_a = any(t.lower() in text_lower for t in tokens_a)
            has_b = any(t.lower() in text_lower for t in tokens_b)
            if has_a and has_b:
                return rule_id, category
        else:
            return rule_id, category

    return None


def scan_wiretap_database(
    db_path: Path,
    watchlist: Dict[str, Any],
    limit_per_author: int = 100,
) -> List[TripwireHit]:
    """
    Scans morning_wiretap.db for tracked authors and rule hits.
    Operates in read-only URI mode to protect against write locking.
    """
    if not db_path.exists():
        return []

    authors = watchlist.get("tracked_authors", [])
    rules = watchlist.get("tripwire_rules", [])
    if not authors:
        return []

    hits: List[TripwireHit] = []
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in authors)
        query = f"""
            SELECT author, message, timestamp_str, epoch_time, channel_key
            FROM chat_telemetry
            WHERE author IN ({placeholders})
            ORDER BY epoch_time ASC
        """
        cursor.execute(query, authors)
        rows = cursor.fetchall()

        for author, message, timestamp_str, epoch_time, channel_key in rows:
            eval_res = evaluate_message_against_rules(message, rules)
            if eval_res:
                rule_id, category = eval_res
                hits.append(
                    TripwireHit(
                        author=author,
                        message=message,
                        timestamp_str=timestamp_str,
                        epoch_time=float(epoch_time),
                        channel_key=channel_key,
                        rule_id=rule_id,
                        category=category,
                    )
                )
    finally:
        conn.close()

    return hits


def generate_hypocrisy_cards(hits: List[TripwireHit]) -> List[HypocrisyCard]:
    """
    Correlates sacrifice/panic pledges with subsequent victory lap messages.
    Calculates flip deltas and generates Barf roast ammo.
    """
    by_author: Dict[str, List[TripwireHit]] = {}
    for h in hits:
        by_author.setdefault(h.author, []).append(h)

    cards: List[HypocrisyCard] = []
    for author, author_hits in by_author.items():
        sacrifices = [
            h
            for h in author_hits
            if h.category in ("FAN_BARTER_SACRIFICE", "DEGEN_PANIC")
        ]
        victories = [h for h in author_hits if h.category == "VICTORY_LAP"]

        if sacrifices and victories:
            first_sac = sacrifices[0]
            last_vic = victories[-1]

            time_diff_hrs = (
                max(0.1, (last_vic.epoch_time - first_sac.epoch_time) / 3600.0)
            )
            flip_delta = round(min(1.0, 0.5 + (0.1 * len(victories))), 2)

            card_id = f"hypo_{author.lstrip('@').lower()}_{int(first_sac.epoch_time)}"
            summary = (
                f"{author} pledged: '{first_sac.message}' during early struggles, "
                f"then celebrated with: '{last_vic.message}'."
            )
            barf_roast = (
                f"LOOK AT {author}! Two weeks ago on {first_sac.channel_key} you were sobbing into "
                f"your keyboard saying '{first_sac.message}', and now you're strutting around saying "
                f"'{last_vic.message}' like you drew up the playbook yourself! Pass the Tums!"
            )

            cards.append(
                HypocrisyCard(
                    card_id=card_id,
                    author=author,
                    sacrifice_quote=first_sac.message,
                    sacrifice_timestamp=first_sac.timestamp_str,
                    sacrifice_channel=first_sac.channel_key,
                    victory_quote=last_vic.message,
                    victory_timestamp=last_vic.timestamp_str,
                    victory_channel=last_vic.channel_key,
                    flip_delta=flip_delta,
                    summary=summary,
                    barf_roast_ammo=barf_roast,
                )
            )

    return cards


def run_pipeline(
    db_path: Path = DEFAULT_DB_PATH,
    watchlist_path: Path = DEFAULT_WATCHLIST_PATH,
    output_vfs: Path = DEFAULT_OUTPUT_VFS,
    output_data: Path = DEFAULT_OUTPUT_DATA,
) -> Dict[str, Any]:
    """Execute the full lore tripwire ingestion and export pipeline."""
    watchlist = load_watchlist(watchlist_path)
    hits = scan_wiretap_database(db_path, watchlist)
    cards = generate_hypocrisy_cards(hits)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_hits": len(hits),
        "total_cards": len(cards),
        "tracked_authors_count": len(watchlist.get("tracked_authors", [])),
        "hypocrisy_cards": [asdict(c) for c in cards],
        "recent_hits": [asdict(h) for h in hits[-20:]],
    }

    output_vfs.parent.mkdir(parents=True, exist_ok=True)
    with open(output_vfs, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    output_data.parent.mkdir(parents=True, exist_ok=True)
    with open(output_data, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="StackLabs Lore Tripwire & Chatter Hypocrisy Engine"
    )
    parser.add_argument(
        "--scan-db",
        action="store_true",
        help="Scan SQLite wiretap database and export telemetry",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to morning_wiretap.db",
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to wiretap_watchlist.json",
    )
    parser.add_argument(
        "--export-vfs",
        type=Path,
        default=DEFAULT_OUTPUT_VFS,
        help="Path to output VFS JSON file",
    )
    parser.add_argument(
        "--export-data",
        type=Path,
        default=DEFAULT_OUTPUT_DATA,
        help="Path to output Data JSON file",
    )

    args = parser.parse_args()

    if args.scan_db:
        result = run_pipeline(
            db_path=args.db_path,
            watchlist_path=args.watchlist,
            output_vfs=args.export_vfs,
            output_data=args.export_data,
        )
        print(f"✅ [Lore Tripwire] Pipeline completed: {result['total_hits']} hits, {result['total_cards']} hypocrisy cards generated.")
        for card in result["hypocrisy_cards"]:
            print(f"  - Card [{card['card_id']}] Author: {card['author']} (Flip Delta: {card['flip_delta']})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
