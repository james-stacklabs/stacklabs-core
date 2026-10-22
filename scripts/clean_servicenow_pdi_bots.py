#!/usr/bin/env python3
"""
ServiceNow PDI Bot & RPG Relic Purge Tool
Connects to ServiceNow Developer Instance (dev186522.service-now.com)
and scrubs synthetic bot personas, RPG relics, empty room shells,
and orphaned relationships.
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Set, Tuple

import requests

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

BANNED_NAME_TOKENS = [
    "mean_gene",
    "battery_chucker",
    "battery_chucker_jr",
    "unclesteviestan",
    "keith_fanboy",
    "the_chop_shop",
    "zork_rpg",
    "bleed_the_skew",
    "tva_001",
    "tva_002",
    "spreadsheets_on_fire",
    "conspiracy_tmi",
    "cypher_cell",
    "cypher_escape",
    "burn_823",
]

BANNED_CLASSES = {
    "cmdb_ci_tmi_scenario",
    "cmdb_ci_penalty_log",
    "cmdb_ci_burn_event",
}

PRESERVED_NAMES = {
    "sap_web01",
    "db_cluster01",
    "core_switch_alpha",
    "hero_pat_mcafee",
    "hero_aj_hawk",
    "hero_john_harbaugh_nyg",
    "villain_jerry_sun_glare_cap",
    "villain_daboll_titans_exile",
    "vitals_barf_bp_178_112",
    "villain_billy_napier_hot_seat",
    "villain_stearns_fleece_spreadsheet",
    "villain_animal_style_ump_cartel",
    "hero_nick_saban_alpha",
    "hero_ty_schmit_lou_holtz",
    "hero_jackson_chourio_walkoff",
    "hero_sammy_the_savant",
    "conspiracy_att_west_window_glare",
    "conspiracy_wisconsin_faustian_barter",
}

PRESERVED_CLASSES = {
    "cmdb_ci_appl",
    "cmdb_ci_db_instance",
    "cmdb_ci_ip_switch",
    "cmdb_ci_linux_server",
    "cmdb_ci_server",
    "cmdb_ci_network_adapter",
}


def get_auth_session() -> requests.Session:
    session = requests.Session()
    session.auth = (SN_USER, SN_PASS)
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "StackLabs-PDI-Cleaner/1.0",
        }
    )
    return session


def is_bot_ci(ci: Dict[str, Any]) -> Tuple[bool, str]:
    name = str(ci.get("name") or "").lower()
    sys_id = str(ci.get("sys_id") or "")
    s_class = str(ci.get("sys_class_name") or "")
    title = str(ci.get("short_description") or "").lower()

    if name in PRESERVED_NAMES or sys_id in PRESERVED_NAMES:
        return False, "PRESERVED_NAME"
    if s_class in PRESERVED_CLASSES:
        return False, "PRESERVED_CLASS"

    if s_class in BANNED_CLASSES:
        return True, f"BANNED_CLASS_{s_class}"

    if s_class == "cmdb_ci_ai_persona" and name != "barf":
        return True, f"NON_BARF_AI_PERSONA_{name}"

    for token in BANNED_NAME_TOKENS:
        if token in name or token in title:
            return True, f"BANNED_TOKEN_{token}"

    if name == "dot" or name.startswith("dot_"):
        return True, "BANNED_DOT_PERSONA"

    if re.match(r"^room_\d+$", name):
        return True, "EMPTY_STAGED_ROOM"

    if "cypher escape" in title or "total cypher" in title:
        return True, "CYPHER_LORE_IN_TITLE"

    return False, "OK"


def scan_pdi_cis(session: requests.Session) -> List[Dict[str, Any]]:
    print(f"[*] Scanning existing CIs from {SN_INSTANCE}/api/now/table/cmdb_ci ...")
    all_cis: List[Dict[str, Any]] = []
    limit = 250
    offset = 0

    while True:
        url = (
            f"{SN_INSTANCE}/api/now/table/cmdb_ci"
            f"?sysparm_fields=sys_id,name,sys_class_name,short_description"
            f"&sysparm_limit={limit}&sysparm_offset={offset}"
        )
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                print(f"[!] CI fetch error at offset {offset}: HTTP {resp.status_code}")
                break
            batch = resp.json().get("result", [])
            if not batch:
                break
            all_cis.extend(batch)
            offset += len(batch)
            if len(batch) < limit:
                break
        except Exception as e:
            print(f"[!] Exception during CI scan: {e}")
            break

    print(f"[*] Fetched {len(all_cis)} total CIs from ServiceNow PDI.")
    return all_cis


def scan_pdi_relationships(session: requests.Session) -> List[Dict[str, Any]]:
    print(f"[*] Scanning relationships from {SN_INSTANCE}/api/now/table/cmdb_rel_ci ...")
    all_rels: List[Dict[str, Any]] = []
    limit = 250
    offset = 0

    while True:
        url = (
            f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci"
            f"?sysparm_fields=sys_id,parent,child,type"
            f"&sysparm_limit={limit}&sysparm_offset={offset}"
        )
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                print(f"[!] Rel fetch error at offset {offset}: HTTP {resp.status_code}")
                break
            batch = resp.json().get("result", [])
            if not batch:
                break
            all_rels.extend(batch)
            offset += len(batch)
            if len(batch) < limit:
                break
        except Exception as e:
            print(f"[!] Exception during relationship scan: {e}")
            break

    print(f"[*] Fetched {len(all_rels)} total relationships from ServiceNow PDI.")
    return all_rels


def delete_record(session: requests.Session, table: str, sys_id: str) -> bool:
    url = f"{SN_INSTANCE}/api/now/table/{table}/{sys_id}"
    try:
        resp = session.delete(url, timeout=15)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def purge_bot_cis(
    session: requests.Session,
    targets: List[Dict[str, Any]],
    execute: bool = False,
) -> int:
    print(f"[*] Identified {len(targets)} bot / synthetic CIs targeted for deletion.")
    if not execute:
        print("[!] DRY RUN MODE: No records deleted. Pass --execute to purge.")
        return 0

    deleted_count = 0
    t0 = time.perf_counter()

    def _worker(ci: Dict[str, Any]) -> bool:
        sid = ci["sys_id"]
        return delete_record(session, "cmdb_ci", sid)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(_worker, targets))
        deleted_count = sum(1 for r in results if r)

    elapsed = round(time.perf_counter() - t0, 2)
    print(f"[*] Deleted {deleted_count} / {len(targets)} CIs in {elapsed}s.")
    return deleted_count


def purge_orphaned_relationships(
    session: requests.Session,
    rels: List[Dict[str, Any]],
    deleted_sys_ids: Set[str],
    surviving_sys_ids: Set[str],
    execute: bool = False,
) -> int:
    orphaned = []
    for r in rels:
        p = r.get("parent", {})
        c = r.get("child", {})
        p_sid = p.get("value") if isinstance(p, dict) else str(p)
        c_sid = c.get("value") if isinstance(c, dict) else str(c)
        r_sid = r.get("sys_id")

        if (
            p_sid in deleted_sys_ids
            or c_sid in deleted_sys_ids
            or (surviving_sys_ids and (p_sid not in surviving_sys_ids or c_sid not in surviving_sys_ids))
        ):
            orphaned.append(r_sid)

    print(f"[*] Identified {len(orphaned)} orphaned relationships to clean.")
    if not execute:
        return 0

    deleted_rels = 0
    t0 = time.perf_counter()

    def _rel_worker(rsid: str) -> bool:
        return delete_record(session, "cmdb_rel_ci", rsid)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(_rel_worker, orphaned))
        deleted_rels = sum(1 for r in results if r)

    elapsed = round(time.perf_counter() - t0, 2)
    print(f"[*] Deleted {deleted_rels} / {len(orphaned)} orphaned relationships in {elapsed}s.")
    return deleted_rels


def verify_pdi_state(session: requests.Session) -> Dict[str, Any]:
    stats: Dict[str, Any] = {}
    try:
        r_ci = session.get(
            f"{SN_INSTANCE}/api/now/stats/cmdb_ci",
            params={"sysparm_count": "true"},
            timeout=15,
        ).json()
        stats["cmdb_ci_count"] = int(
            r_ci.get("result", {}).get("stats", {}).get("count", 0)
        )
    except Exception as e:
        stats["cmdb_ci_count"] = f"ERR: {e}"

    try:
        r_rel = session.get(
            f"{SN_INSTANCE}/api/now/stats/cmdb_rel_ci",
            params={"sysparm_count": "true"},
            timeout=15,
        ).json()
        stats["cmdb_rel_ci_count"] = int(
            r_rel.get("result", {}).get("stats", {}).get("count", 0)
        )
    except Exception as e:
        stats["cmdb_rel_ci_count"] = f"ERR: {e}"

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrub synthetic bot personas and RPG relics from ServiceNow PDI."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute deletions against ServiceNow PDI. Defaults to dry-run.",
    )
    args = parser.parse_args()

    session = get_auth_session()
    all_cis = scan_pdi_cis(session)

    bot_targets: List[Dict[str, Any]] = []
    surviving_cis: List[Dict[str, Any]] = []
    reason_counts: Dict[str, int] = {}

    for ci in all_cis:
        flagged, reason = is_bot_ci(ci)
        if flagged:
            bot_targets.append(ci)
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        else:
            surviving_cis.append(ci)

    print("\n--- Flagged Bot Breakdown ---")
    for r, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {r}: {count}")

    deleted_ci_count = purge_bot_cis(session, bot_targets, execute=args.execute)
    deleted_sids = {ci["sys_id"] for ci in bot_targets} if args.execute else set()
    surviving_sids = {ci["sys_id"] for ci in surviving_cis}

    all_rels = scan_pdi_relationships(session)
    deleted_rel_count = purge_orphaned_relationships(
        session,
        all_rels,
        deleted_sids,
        surviving_sids,
        execute=args.execute,
    )

    final_stats = verify_pdi_state(session)

    summary = {
        "status": "COMPLETED",
        "mode": "EXECUTE" if args.execute else "DRY_RUN",
        "total_cis_scanned": len(all_cis),
        "bot_cis_flagged": len(bot_targets),
        "bot_cis_deleted": deleted_ci_count,
        "surviving_cis_count": len(surviving_cis),
        "total_rels_scanned": len(all_rels),
        "orphaned_rels_deleted": deleted_rel_count,
        "pdi_verification": final_stats,
    }

    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
