#!/usr/bin/env python3
"""
Authentic Toxic Comment CMDB Ingestion & Classification Pipeline
Ingests authentic live stream chat messages from data/morning_wiretap.db,
evaluates high-heat volatility via regex and sentiment heuristics,
and generates structured 3-tier CMDB topologies linking Broadcast Hubs,
Toxic Outrage Needles, and Impacted Entity CIs.
Strictly air-gapped from simulation databases.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

STACKLABS_ROOT = Path("/home/james/stacklabs")
DATA_DIR = STACKLABS_ROOT / "data"
WIRETAP_DB = DATA_DIR / "morning_wiretap.db"
OUTPUT_GRAPH = DATA_DIR / "toxic_comment_cmdb_graph.json"
CMDB_STUDIO_DIR = STACKLABS_ROOT / "apps" / "cmdb_studio" / "public"

CATEGORIES = {
    "COACH_HOT_SEAT": {
        "pattern": re.compile(
            r"\b(fire|fired|hot[- ]seat|buyout|coach|coaching|bench|daboll|napier|eberflus|sirianni|mccarthy|stefanski|head coach|schemes?)\b",
            re.IGNORECASE,
        ),
        "target_ci": "villain_daboll_titans_exile",
        "alt_target": "villain_billy_napier_hot_seat",
    },
    "BLOWN_CALL_REF_HEX": {
        "pattern": re.compile(
            r"\b(refs?|referee|umpire|zebras?|holding|phantom|missed call|blown call|strike zone|bad call|rigged|flag|penalt(y|ies))\b",
            re.IGNORECASE,
        ),
        "target_ci": "villain_animal_style_ump_cartel",
        "alt_target": "villain_animal_style_ump_cartel",
    },
    "OWNERSHIP_HUBRIS": {
        "pattern": re.compile(
            r"\b(jerry|jerry jones|curtains?|sun glare|glare|roof|billionaire|owner|front office|cashman|wilpon|tepper|boehly)\b",
            re.IGNORECASE,
        ),
        "target_ci": "villain_jerry_sun_glare_cap",
        "alt_target": "conspiracy_att_west_window_glare",
    },
    "PLAYER_MELTDOWN_SLANDER": {
        "pattern": re.compile(
            r"\b(washed|bum|trash|interception|pick[- ]6|fumble|blown save|meatball|choke|butcher|kimbrel|diaz|strikeout|drops?)\b",
            re.IGNORECASE,
        ),
        "target_ci": "villain_stearns_fleece_spreadsheet",
        "alt_target": "vitals_barf_bp_178_112",
    },
    "FRANCHISE_DOOMERISM": {
        "pattern": re.compile(
            r"\b(season over|0-3|cursed|poverty franchise|sell the team|hopeless|agony|pain|disaster|unhinged|jets|giants|titans)\b",
            re.IGNORECASE,
        ),
        "target_ci": "villain_daboll_titans_exile",
        "alt_target": "villain_jerry_sun_glare_cap",
    },
}

HUB_MAP = {
    "radio_mcafee": "wiretap_hub_radio_mcafee",
    "TEN_dynamic": "wiretap_hub_TEN_dynamic",
    "NYY_TalkinYanks": "wiretap_hub_NYY_TalkinYanks",
    "DET_WoodwardSports": "wiretap_hub_DET_WoodwardSports",
    "radio_phly": "wiretap_hub_radio_phly",
    "CLE_DawgWatchParty": "wiretap_hub_CLE_dynamic",
    "MOST_dynamic": "wiretap_hub_radio_mcafee",
}


def make_sys_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def compute_toxicity_score(msg: str) -> Tuple[int, int]:
    length = len(msg)
    if length < 10:
        return 0, 0

    caps_count = sum(1 for c in msg if c.isupper())
    caps_ratio = caps_count / length
    exclamations = msg.count("!")
    question_marks = msg.count("?")

    score = 4
    if caps_ratio > 0.4:
        score += 3
    elif caps_ratio > 0.15:
        score += 1

    if exclamations >= 2:
        score += 2
    elif exclamations == 1:
        score += 1

    if question_marks >= 2:
        score += 1
    elif question_marks == 1:
        score += 1

    if length >= 40:
        score += 1

    heat_index = min(10, max(1, int(score * 1.1)))
    return min(10, score), heat_index


def classify_message(msg: str) -> Tuple[str | None, str]:
    for cat_name, conf in CATEGORIES.items():
        if conf["pattern"].search(msg):
            target = conf["target_ci"]
            if "napier" in msg.lower() or "florida" in msg.lower() or "gator" in msg.lower():
                target = conf["alt_target"]
            return cat_name, target
    return None, "villain_jerry_sun_glare_cap"


def harvest_authentic_chat_needles(limit: int = 150) -> List[Dict[str, Any]]:
    if not WIRETAP_DB.exists():
        print(f"[!] Database {WIRETAP_DB} does not exist.")
        return []

    conn = sqlite3.connect(str(WIRETAP_DB))
    cur = conn.cursor()

    query = """
        SELECT id, channel_key, stream_id, author, message, timestamp_str
        FROM chat_telemetry
        WHERE length(message) BETWEEN 18 AND 220
          AND channel_key NOT IN ('bloomberg', 'foxfriends', 'gma')
          AND message NOT LIKE '%http%'
          AND message NOT LIKE '%subscribe%'
          AND message NOT LIKE '%discord%'
        ORDER BY id DESC
        LIMIT 60000
    """
    rows = cur.execute(query).fetchall()
    conn.close()

    needles: List[Dict[str, Any]] = []
    seen_sigs: Set[str] = set()

    for r_id, chan, s_id, author, msg, ts in rows:
        clean_msg = re.sub(r"\s+", " ", str(msg)).strip()
        sig = clean_msg[:40].lower()
        if sig in seen_sigs:
            continue

        cat, target_ci = classify_message(clean_msg)
        if not cat:
            continue

        tox_score, heat = compute_toxicity_score(clean_msg)
        if tox_score < 5:
            continue

        seen_sigs.add(sig)
        needles.append(
            {
                "id": r_id,
                "channel_key": str(chan),
                "stream_id": str(s_id),
                "author": str(author or "stream_watcher"),
                "message": clean_msg,
                "timestamp": str(ts),
                "category": cat,
                "target_ci": target_ci,
                "toxicity_score": tox_score,
                "heat_index": heat,
            }
        )
        if len(needles) >= limit:
            break

    return needles


def build_topology_graph(needles: List[Dict[str, Any]]) -> Dict[str, Any]:
    cis: List[Dict[str, Any]] = []
    rels: List[Tuple[str, str, str]] = []
    seen_cis: Set[str] = set()

    def _add_ci(ci_key: str, s_class: str, title: str, desc: str, extra: Dict[str, Any]) -> None:
        if ci_key in seen_cis:
            return
        seen_cis.add(ci_key)
        cis.append(
            {
                "sys_id": make_sys_id(ci_key),
                "name": ci_key,
                "ci_key": ci_key,
                "sys_class_name": s_class,
                "display_title": title,
                "short_description": desc,
                "operational_status": "Operational (Live Stream Telemetry)",
                **extra,
            }
        )

    for n in needles:
        ci_key = f"needle_toxic_{n['id']}_{re.sub(r'[^a-z0-9]+', '_', n['author'].lower()).strip('_')[:14]}"
        hub_key = HUB_MAP.get(n["channel_key"], "wiretap_hub_radio_mcafee")

        _add_ci(
            ci_key,
            "u_cmdb_ci_stream_needle",
            f"[{n['category']} • {n['channel_key']}]: {n['message'][:54]}...",
            f"Authentic YouTube Live Chat Outrage Needle (#{n['id']} on {n['channel_key']}): @{n['author']} -> \"{n['message']}\"",
            {
                "category": n["category"],
                "author": n["author"],
                "channel_key": n["channel_key"],
                "stream_id": n["stream_id"],
                "toxicity_score": n["toxicity_score"],
                "heat_index": n["heat_index"],
                "timestamp": n["timestamp"],
            },
        )

        rels.append((ci_key, hub_key, "Captured On::Stream Hub"))
        rels.append((ci_key, n["target_ci"], "Provokes Outrage::Impacted CI"))

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_toxic_needles": len(needles),
        "total_cis": len(cis),
        "total_relationships": len(rels),
        "cis": cis,
        "relationships": rels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract authentic toxic comments and generate CMDB topology."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Maximum toxic needles to classify.",
    )
    args = parser.parse_args()

    print("[*] Harvesting authentic live-stream chat needles from morning_wiretap.db ...")
    needles = harvest_authentic_chat_needles(limit=args.limit)
    print(f"[*] Classified {len(needles)} high-heat toxic comments.")

    graph = build_topology_graph(needles)
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GRAPH.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"[*] Wrote topology graph to {OUTPUT_GRAPH} ({len(graph['cis'])} CIs, {len(graph['relationships'])} edges).")


if __name__ == "__main__":
    main()
