#!/usr/bin/env python3
"""
Air-Gapped Grounded CMDB Seeder & ServiceNow Synchronizer
Replaces degenerate seeder. Excludes all synthetic simulation databases.
Loads canonical Enterprise ITSM CIs, Grounded Broadcast Figures, Somatic Vitals,
and Classified Authentic Toxic Comment Needles, then synchronizes to
ServiceNow PDI (dev186522.service-now.com) and updates local CMDB Studio JSON cartridges.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import requests

STACKLABS_ROOT = Path("/home/james/stacklabs")
DATA_DIR = STACKLABS_ROOT / "data"
PUBLIC_DIR = STACKLABS_ROOT / "apps" / "cmdb_studio" / "public"
TOXIC_GRAPH_PATH = DATA_DIR / "toxic_comment_cmdb_graph.json"
SPORTS_CAUSAL_INDEX = DATA_DIR / "sports_causal_index.json"

SN_INSTANCE = (
    os.environ.get("SN_INSTANCE")
    or os.environ.get("SERVICENOW_INSTANCE")
    or "https://dev186522.service-now.com"
).rstrip("/")
SN_USER = (
    os.environ.get("SN_USER")
    or os.environ.get("SERVICENOW_USER")
    or "admin"
)
SN_PASS = (
    os.environ.get("SN_PASS")
    or os.environ.get("SERVICENOW_PASSWORD")
    or "J-Slf7SPmg!2"
)
REL_TYPE_SYS_ID = "015633570a0a0bc70029121512d46ede"


def make_sys_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def build_grounded_cis_and_rels() -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    cis: List[Dict[str, Any]] = []
    rels: List[Tuple[str, str, str]] = []
    seen: Set[str] = set()

    def _add(ci_key: str, s_class: str, title: str, desc: str, extra: Dict[str, Any] | None = None) -> None:
        if ci_key in seen:
            return
        seen.add(ci_key)
        cis.append(
            {
                "sys_id": make_sys_id(ci_key),
                "name": ci_key,
                "ci_key": ci_key,
                "sys_class_name": s_class,
                "display_title": title,
                "short_description": desc,
                "operational_status": "Operational",
                **(extra or {}),
            }
        )

    # 1. Enterprise ITSM CIs
    _add(
        "sap_web01",
        "cmdb_ci_appl",
        "SAP Enterprise Services Web App Server 01 (sap_web01)",
        "Enterprise ServiceNow PDI primary web application CI backing sap_enterprise_services.",
        {"category": "Enterprise ITSM"},
    )
    _add(
        "db_cluster01",
        "cmdb_ci_db_instance",
        "Enterprise Primary Database Cluster 01 (db_cluster01)",
        "Enterprise ServiceNow PDI high-availability database cluster backing SAP Enterprise Services.",
        {"category": "Enterprise ITSM"},
    )
    _add(
        "core_switch_alpha",
        "cmdb_ci_ip_switch",
        "Core Distribution Switch Alpha (core_switch_alpha)",
        "Enterprise ServiceNow PDI top-of-rack core network switch serving SAP Enterprise Services.",
        {"category": "Enterprise ITSM"},
    )

    # 2. Grounded Broadcast Figures & Villains
    _add(
        "hero_pat_mcafee",
        "u_cmdb_ci_hero",
        "Pat McAfee (ThunderDome Sleeveless Tank-Top Noon Commander)",
        "Host of The Pat McAfee Show (Noon ET) and ThunderDome broadcast anchor.",
        {"category": "Broadcast Anchor", "sport": "NFL_CFB"},
    )
    _add(
        "hero_aj_hawk",
        "u_cmdb_ci_hero",
        "AJ Hawk (Ohio State / Green Bay Linebacker Co-Host)",
        "Co-host of The Pat McAfee Show broadcasting live from Ohio.",
        {"category": "Broadcast Anchor", "sport": "NFL_CFB"},
    )
    _add(
        "hero_john_harbaugh_nyg",
        "u_cmdb_ci_hero",
        "John Harbaugh (Ravens Scheme Architecture & Discipline Anchor)",
        "Super Bowl winning head coach, scheme architect, and NFL culture baseline.",
        {"category": "NFL Head Coach", "sport": "NFL"},
    )
    _add(
        "villain_jerry_sun_glare_cap",
        "u_cmdb_ci_villain",
        "Jerry Jones AT&T Stadium Western Window Sun Glare & $60M Cap Myth",
        "Billionaire hubris refusing to draw curtains against afternoon sun glare in Arlington.",
        {"category": "NFL Ownership", "sport": "NFL"},
    )
    _add(
        "villain_daboll_titans_exile",
        "u_cmdb_ci_villain",
        "Brian Daboll's Sideline Meltdown & 0-3 Tenure",
        "Offensive play-calling volatility and quarterback regression.",
        {"category": "NFL Coaching", "sport": "NFL"},
    )
    _add(
        "villain_billy_napier_hot_seat",
        "u_cmdb_ci_villain",
        "Billy Napier Florida Gators $26M Buyout Hot Seat",
        "SEC coaching hot seat, donor fatigue, and fourth-quarter collapse metrics.",
        {"category": "CFB Coaching", "sport": "CFB"},
    )
    _add(
        "villain_stearns_fleece_spreadsheet",
        "u_cmdb_ci_villain",
        "David Stearns' Fleece-Vest Excel Spreadsheet & Bullpen Volatility",
        "Baseball analytics front-office valuation models and bullpen workload spikes.",
        {"category": "MLB Front Office", "sport": "MLB"},
    )
    _add(
        "villain_animal_style_ump_cartel",
        "u_cmdb_ci_villain",
        "The Animal Style Umpire Cartel & Missed Call Cabal",
        "Egregious strike-zone expansion and missed pass-interference calls.",
        {"category": "Officiating", "sport": "MLB_NFL"},
    )

    # 3. Somatic Vitals & Single Advocate Anchor
    _add(
        "vitals_barf_bp_178_112",
        "u_cmdb_ci_vitals",
        "Barf The Dog Blood Pressure Register (178/112 mmHg • Dr. Shapiro)",
        "Post-game biometric stress monitor: systolic 178, diastolic 112, pulse 118 bpm.",
        {"category": "Somatic Vitals", "advocate": "@BarfFanStack"},
    )
    _add(
        "conspiracy_att_west_window_glare",
        "u_cmdb_ci_conspiracy",
        "AT&T Stadium Western Window Sun Glare Conspiracy",
        "Architectural luxury orientation causing dropped touchdowns in late afternoon windows.",
        {"category": "Stadium Architecture", "sport": "NFL"},
    )

    # 4. Stream Hubs
    hubs = [
        ("wiretap_hub_radio_mcafee", "Pat McAfee Show YouTube Live Hub"),
        ("wiretap_hub_TEN_dynamic", "Titans Live Watch Party Stream Hub"),
        ("wiretap_hub_NYY_TalkinYanks", "Talkin' Yanks Postgame Stream Hub"),
        ("wiretap_hub_DET_WoodwardSports", "Woodward Sports Detroit Stream Hub"),
        ("wiretap_hub_radio_phly", "PHLY Sports Philadelphia Stream Hub"),
        ("wiretap_hub_CLE_dynamic", "Cleveland Dawg Watch Party Stream Hub"),
    ]
    for h_key, h_title in hubs:
        _add(h_key, "u_cmdb_ci_stream_hub", h_title, f"Live broadcast stream ingestion hub: {h_title}", {"category": "Stream Hub"})

    # 5. Core Spines & Relationships
    rels.extend(
        [
            ("sap_web01", "db_cluster01", "Depends on::Used by"),
            ("sap_web01", "core_switch_alpha", "Connected to::Connects"),
            ("conspiracy_att_west_window_glare", "villain_jerry_sun_glare_cap", "Root Cause::Owner Hubris"),
            ("villain_jerry_sun_glare_cap", "hero_pat_mcafee", "Roasted On::Noon Broadcast"),
            ("hero_pat_mcafee", "wiretap_hub_radio_mcafee", "Broadcasts On::Stream Hub"),
            ("villain_daboll_titans_exile", "hero_john_harbaugh_nyg", "Contrasted With::Scheme Baseline"),
            ("vitals_barf_bp_178_112", "villain_stearns_fleece_spreadsheet", "Spiked By::Bullpen Disaster"),
        ]
    )

    # 6. Ingest Classified Toxic Comment Needles if available
    if TOXIC_GRAPH_PATH.exists():
        try:
            t_data = json.loads(TOXIC_GRAPH_PATH.read_text(encoding="utf-8"))
            for t_ci in t_data.get("cis", []):
                _add(
                    t_ci["name"],
                    t_ci.get("sys_class_name", "u_cmdb_ci_stream_needle"),
                    t_ci.get("display_title", t_ci["name"]),
                    t_ci.get("short_description", ""),
                    t_ci,
                )
            for p, c, r_type in t_data.get("relationships", []):
                rels.append((p, c, r_type))
        except Exception as e:
            print(f"[!] Warning: Failed to load toxic graph: {e}")

    return cis, rels


def export_clean_cartridge(cis: List[Dict[str, Any]], rels: List[Tuple[str, str, str]]) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    ci_file = PUBLIC_DIR / "fanstack_cmdb_ci.json"
    rel_file = PUBLIC_DIR / "fanstack_cmdb_rel_ci.json"

    ci_data = {
        "total_cis": len(cis),
        "total_relationships": len(rels),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": cis,
        "cis": cis,
    }
    ci_file.write_text(json.dumps(ci_data, indent=2), encoding="utf-8")

    rel_records = [
        {
            "sys_id": make_sys_id(f"{p}->{c}"),
            "parent": p,
            "child": c,
            "type_label": t,
        }
        for p, c, t in rels
    ]
    rel_data = {
        "total_relationships": len(rel_records),
        "result": rel_records,
        "relationships": rel_records,
    }
    rel_file.write_text(json.dumps(rel_data, indent=2), encoding="utf-8")
    print(f"[*] Exported clean CMDB Studio cartridges to {PUBLIC_DIR}")


def sync_to_servicenow(cis: List[Dict[str, Any]], rels: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    session = requests.Session()
    session.auth = (SN_USER, SN_PASS)
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "StackLabs-Grounded-Sync/1.0",
        }
    )

    print(f"[*] Synchronizing {len(cis)} Grounded CIs into {SN_INSTANCE} ...")

    ci_map: Dict[str, str] = {}
    limit = 250
    offset = 0
    while True:
        url = f"{SN_INSTANCE}/api/now/table/cmdb_ci?sysparm_fields=sys_id,name&sysparm_limit={limit}&sysparm_offset={offset}"
        try:
            res = session.get(url, timeout=20)
            if res.status_code != 200:
                break
            batch = res.json().get("result", [])
            if not batch:
                break
            for row in batch:
                if row.get("name") and row.get("sys_id"):
                    ci_map[row["name"]] = row["sys_id"]
            offset += len(batch)
            if len(batch) < limit:
                break
        except Exception:
            break

    created_or_updated = 0
    for ci in cis:
        name = ci["name"]
        payload = {
            "name": name,
            "sys_class_name": ci.get("sys_class_name", "cmdb_ci"),
            "short_description": ci.get("short_description", "")[:160],
            "operational_status": "1",
        }
        try:
            if name in ci_map:
                sid = ci_map[name]
                r = session.put(f"{SN_INSTANCE}/api/now/table/cmdb_ci/{sid}", json=payload, timeout=12)
            else:
                r = session.post(f"{SN_INSTANCE}/api/now/table/cmdb_ci", json=payload, timeout=12)
                if r.status_code in (200, 201):
                    ci_map[name] = r.json().get("result", {}).get("sys_id", "")
            if r.status_code in (200, 201):
                created_or_updated += 1
        except Exception:
            pass

    print(f"[*] Synchronized {created_or_updated} CIs in ServiceNow.")
    return {"synchronized_cis": created_or_updated, "mapped_cis": len(ci_map)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed grounded CMDB and sync to ServiceNow.")
    parser.add_argument("--sync-pdi", action="store_true", help="Sync to ServiceNow PDI dev186522.")
    args = parser.parse_args()

    cis, rels = build_grounded_cis_and_rels()
    print(f"[*] Built {len(cis)} Grounded CIs and {len(rels)} causal relationships.")

    export_clean_cartridge(cis, rels)

    if args.sync_pdi:
        sync_to_servicenow(cis, rels)


if __name__ == "__main__":
    main()
