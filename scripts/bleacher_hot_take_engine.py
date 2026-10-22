#!/usr/bin/env python3
"""
Bleacher Provocateur Mind Map Graph & Hot Take Engine
Path: /home/james/stacklabs/scripts/bleacher_hot_take_engine.py
Author: James Carroll (Pilot), Lead Systems Architect
"""

import os
import sys
import re
import json
import time
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = Path("/home/james/stacklabs/vfs/provocateur_graph.db")


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_schema():
    with get_db_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS provocateurs (
                handle TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                total_messages INTEGER DEFAULT 0,
                dogpile_count INTEGER DEFAULT 0,
                sharp_score REAL DEFAULT 0.0,
                cope_score REAL DEFAULT 0.0,
                classification TEXT DEFAULT 'PROSPECT'
            );

            CREATE TABLE IF NOT EXISTS hot_takes (
                id TEXT PRIMARY KEY,
                author TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                game_context TEXT NOT NULL,
                raw_message TEXT NOT NULL,
                category TEXT NOT NULL,
                claim_entity TEXT NOT NULL,
                predicted_event TEXT NOT NULL,
                sentiment REAL DEFAULT 0.0,
                dogpile_trigger_count INTEGER DEFAULT 0,
                settlement_status TEXT DEFAULT 'PENDING',
                settlement_verdict TEXT DEFAULT 'UNRESOLVED',
                settled_at TEXT,
                FOREIGN KEY (author) REFERENCES provocateurs(handle)
            );

            CREATE TABLE IF NOT EXISTS graph_nodes (
                node_id TEXT PRIMARY KEY,
                author_handle TEXT NOT NULL,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (author_handle) REFERENCES provocateurs(handle)
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                edge_id TEXT PRIMARY KEY,
                author_handle TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                polarity REAL DEFAULT 0.0,
                FOREIGN KEY (author_handle) REFERENCES provocateurs(handle),
                FOREIGN KEY (source_id) REFERENCES graph_nodes(node_id),
                FOREIGN KEY (target_id) REFERENCES graph_nodes(node_id)
            );

            CREATE INDEX IF NOT EXISTS idx_takes_author ON hot_takes(author);
            CREATE INDEX IF NOT EXISTS idx_nodes_author ON graph_nodes(author_handle);
            CREATE INDEX IF NOT EXISTS idx_edges_author ON graph_edges(author_handle);
        """)


def categorize_claim(message: str) -> Tuple[str, str, str]:
    msg_lower = message.lower()
    if any(k in msg_lower for k in ["coach", "schotty", "sirianni", "parker", "playcall", "scheme", "coordinator", "blitz"]):
        category = "Coaching Malpractice"
        entity = "Coaching Staff"
        event = "Playcalling failure or defensive breakdown"
    elif any(k in msg_lower for k in ["dak", "asscott", "hurts", "cook", "ferguson", "qb", "fumble", "interception", "pick"]):
        category = "Roster Scapegoats"
        entity = "Key Personnel"
        event = "Player turnover, checkdown, or individual collapse"
    elif any(k in msg_lower for k in ["jerry", "front office", "trade", "contract", "owner", "gm", "cap"]):
        category = "Front Office Conspiracy"
        entity = "Ownership / Front Office"
        event = "Roster construction failure or contractual mismanagement"
    elif any(k in msg_lower for k in ["ref", "penalty", "flag", "rigged", "socks", "curse", "hex", "script", "holding"]):
        category = "Superstition & Officiating"
        entity = "Referees / Mojo"
        event = "External interference or superstitious variance"
    else:
        category = "Bleacher Volatility"
        entity = "General Franchise"
        event = "General negative outcome"
    return category, entity, event


def ingest_provocateur_take(
    author: str,
    display_name: str,
    timestamp: str,
    stream_id: str,
    game_context: str,
    message: str,
    dogpile_triggers: int = 0
) -> str:
    category, entity, event = categorize_claim(message)
    take_id = f"HT-{hashlib.sha256(f'{author}-{timestamp}-{message}'.encode()).hexdigest()[:12]}"
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO provocateurs (handle, display_name, first_seen, last_seen, total_messages, dogpile_count)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(handle) DO UPDATE SET
                last_seen = excluded.last_seen,
                total_messages = provocateurs.total_messages + 1,
                dogpile_count = provocateurs.dogpile_count + excluded.dogpile_count
        """, (author, display_name, now_iso, now_iso, dogpile_triggers))

        conn.execute("""
            INSERT OR REPLACE INTO hot_takes (
                id, author, timestamp, stream_id, game_context, raw_message,
                category, claim_entity, predicted_event, dogpile_trigger_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (take_id, author, timestamp, stream_id, game_context, message, category, entity, event, dogpile_triggers))

        root_id = f"node-{author}-root"
        cat_id = f"node-{author}-cat-{re.sub(r'[^a-zA-Z0-9]', '', category)}"
        claim_id = f"node-{author}-take-{take_id}"

        conn.execute("""
            INSERT OR IGNORE INTO graph_nodes (node_id, author_handle, node_type, label, metadata_json)
            VALUES (?, ?, 'PROVOCATEUR', ?, ?)
        """, (root_id, author, author, json.dumps({"display_name": display_name})))

        conn.execute("""
            INSERT OR IGNORE INTO graph_nodes (node_id, author_handle, node_type, label, metadata_json)
            VALUES (?, ?, 'CATEGORY', ?, ?)
        """, (cat_id, author, category, json.dumps({"category": category})))

        conn.execute("""
            INSERT OR REPLACE INTO graph_nodes (node_id, author_handle, node_type, label, metadata_json)
            VALUES (?, ?, 'HOT_TAKE', ?, ?)
        """, (claim_id, author, message[:64], json.dumps({
            "full_message": message,
            "entity": entity,
            "game_context": game_context,
            "take_id": take_id
        })))

        edge_root_cat = f"edge-{root_id}-{cat_id}"
        conn.execute("""
            INSERT OR REPLACE INTO graph_edges (edge_id, author_handle, source_id, target_id, relation, weight)
            VALUES (?, ?, ?, ?, 'OBSESSED_WITH', 1.0)
        """, (edge_root_cat, author, root_id, cat_id))

        edge_cat_claim = f"edge-{cat_id}-{claim_id}"
        conn.execute("""
            INSERT OR REPLACE INTO graph_edges (edge_id, author_handle, source_id, target_id, relation, weight)
            VALUES (?, ?, ?, ?, 'CLAIMS', 1.0)
        """, (edge_cat_claim, author, cat_id, claim_id))

    return take_id


def settle_hot_take(take_id: str, verdict: str) -> bool:
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with get_db_connection() as conn:
        row = conn.execute("SELECT author FROM hot_takes WHERE id = ?", (take_id,)).fetchone()
        if not row:
            return False
        author = row["author"]

        conn.execute("""
            UPDATE hot_takes
            SET settlement_status = 'SETTLED',
                settlement_verdict = ?,
                settled_at = ?
            WHERE id = ?
        """, (verdict, now_iso, take_id))

        takes = conn.execute("SELECT settlement_verdict FROM hot_takes WHERE author = ? AND settlement_status = 'SETTLED'", (author,)).fetchall()
        sharps = sum(1 for t in takes if t["settlement_verdict"] == "VERIFIED_SHARP")
        copes = sum(1 for t in takes if t["settlement_verdict"] == "BUSTER_COPE")
        total = sharps + copes

        sharp_ratio = (sharps / total) if total > 0 else 0.0
        cope_ratio = (copes / total) if total > 0 else 0.0

        if total >= 3:
            classification = "ACCIDENTAL_QUANT" if sharp_ratio >= 0.60 else ("LUCKY_SOCKS_COPE" if cope_ratio >= 0.60 else "VOLATILE_BLEACHER")
        else:
            classification = "PROSPECT"

        conn.execute("""
            UPDATE provocateurs
            SET sharp_score = ?, cope_score = ?, classification = ?
            WHERE handle = ?
        """, (sharp_ratio, cope_ratio, classification, author))

    return True


def export_mindmap_json(author: str) -> Dict[str, Any]:
    with get_db_connection() as conn:
        prov = conn.execute("SELECT * FROM provocateurs WHERE handle = ?", (author,)).fetchone()
        if not prov:
            return {"name": author, "error": "Not Found"}

        takes = conn.execute("SELECT * FROM hot_takes WHERE author = ? ORDER BY timestamp DESC", (author,)).fetchall()
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for t in takes:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": t["raw_message"],
                "take_id": t["id"],
                "verdict": t["settlement_verdict"],
                "status": t["settlement_status"],
                "game": t["game_context"]
            })

        children = []
        for cat_name, items in categories.items():
            children.append({
                "name": cat_name,
                "count": len(items),
                "children": items
            })

        return {
            "name": prov["handle"],
            "display_name": prov["display_name"],
            "classification": prov["classification"],
            "sharp_score": round(prov["sharp_score"] * 100, 1),
            "cope_score": round(prov["cope_score"] * 100, 1),
            "total_messages": prov["total_messages"],
            "dogpile_count": prov["dogpile_count"],
            "children": children
        }


def export_mindmap_markdown(author: str) -> str:
    data = export_mindmap_json(author)
    if "error" in data:
        return f"# {author}\n- Not Found"
    lines = [
        f"# {data['name']} ({data['display_name']}) [{data['classification']}]",
        f"- Sharp Score: {data['sharp_score']}% | Cope Score: {data['cope_score']}% | Dogpiles: {data['dogpile_count']}"
    ]
    for cat in data.get("children", []):
        lines.append(f"  - **{cat['name']}** ({cat['count']})")
        for leaf in cat.get("children", []):
            lines.append(f"    - [{leaf['verdict']}] \"{leaf['name']}\" ({leaf['game']})")
    return "\n".join(lines)


def seed_demo_data():
    init_schema()
    samples = [
        ("@BenJames7976", "Ben James", "23:30:15", "v42cENAtOpc", "DAL vs TB | Q3 08:12", "Parker and Schotty needs to be fired, this is unwatchable", 5),
        ("@BenJames7976", "Ben James", "23:31:02", "v42cENAtOpc", "DAL vs TB | Q3 06:45", "Pay cut ASScott if u dumbass ASScott glazers want defenders an OLinemen", 8),
        ("@BenJames7976", "Ben James", "23:31:40", "v42cENAtOpc", "DAL vs TB | Q3 04:20", "Z- defensive alignment is an open invitation for 15-yard curls", 4),
        ("@BrianJames", "Brian James", "23:28:10", "v42cENAtOpc", "DAL vs TB | Q2 01:14", "Jerry hired this coach because nobody with real leverage would work here", 6),
        ("@BrianJames", "Brian James", "23:29:45", "v42cENAtOpc", "DAL vs TB | Q3 10:00", "Play Camden Brown more, Turpin fumble proves the depth chart is broken", 3),
        ("@jameswells334", "James Wells", "21:49:23", "v42cENAtOpc", "DAL vs TB | Q1 05:00", "The cowboys are exhausted with all these games, they will get back on track calm down", 2)
    ]
    for author, name, ts, sid, game, msg, dp in samples:
        t_id = ingest_provocateur_take(author, name, ts, sid, game, msg, dp)
        if "Schotty" in msg or "curls" in msg:
            settle_hot_take(t_id, "VERIFIED_SHARP")
        elif "calm down" in msg or "glazers" in msg:
            settle_hot_take(t_id, "BUSTER_COPE")


if __name__ == "__main__":
    seed_demo_data()
    print(f"✔ Initialized and seeded /home/james/stacklabs/vfs/provocateur_graph.db")
    with get_db_connection() as conn:
        p_count = conn.execute("SELECT count(*) as c FROM provocateurs").fetchone()["c"]
        t_count = conn.execute("SELECT count(*) as c FROM hot_takes").fetchone()["c"]
        print(f"✔ Verified Provocateurs: {p_count} | Hot Takes: {t_count}")
