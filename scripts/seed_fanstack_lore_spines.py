#!/home/james/stacklabs/.venv/bin/python3
"""
Enriches FanStack CMDB Cartridge with 'THE SPREADSHEETS ARE ON FIRE' (@dot) and
'Zork / RPG Dungeon Textbook Log Creep' (@barf / @dot) CIs & 5-hop causal spines,
and bulk-seeds 24+ FanStack CIs + relationships into https://dev186522.service-now.com.
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import Any, Dict, List

if "/home/james/stacklabs" not in sys.path:
    sys.path.insert(0, "/home/james/stacklabs")

from scripts.export_sovereign_now_cmdb import (
    DATA_DIR,
    PUBLIC_DIR,
    load_env_vars,
    make_state_register,
    make_sys_id,
)


def enrich_and_seed() -> Dict[str, Any]:
    ci_path = DATA_DIR / "fanstack_cmdb_ci.json"
    rel_path = DATA_DIR / "fanstack_cmdb_rel_ci.json"
    idx_path = DATA_DIR / "sports_causal_index.json"

    ci_doc = json.loads(ci_path.read_text(encoding="utf-8"))
    rel_doc = json.loads(rel_path.read_text(encoding="utf-8"))
    idx_doc = json.loads(idx_path.read_text(encoding="utf-8"))

    cis: List[Dict[str, Any]] = ci_doc.get("result", [])
    rels: List[Dict[str, Any]] = rel_doc.get("result", [])
    ci_by_key: Dict[str, Dict[str, Any]] = {}
    for c in cis:
        ci_by_key[c.get("ci_key", c["name"])] = c
        ci_by_key[c["name"]] = c
        ci_by_key[c["name"].lower()] = c

    def upsert_ci(
        key: str,
        sys_class_name: str,
        layer: str,
        short_description: str,
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        sid = make_sys_id(key)
        reg = extra.get("state_register_id") or make_state_register(key)
        rec = {
            "sys_id": sid,
            "ci_key": key,
            "name": key,
            "sys_class_name": sys_class_name,
            "layer": layer,
            "state_register_id": reg,
            "install_status": "1",
            "operational_status": "Operational (Read-Only Advisory)",
            "short_description": short_description,
            **extra,
        }
        existing = ci_by_key.get(key)
        if existing:
            existing.update(rec)
            rec = existing
        else:
            cis.append(rec)
        ci_by_key[key] = rec
        ci_by_key[key.lower()] = rec
        return rec

    def ensure_rel(parent_key: str, child_key: str, rel_type: str = "Causally Linked To::Triggered By") -> None:
        p = ci_by_key.get(parent_key) or ci_by_key.get(parent_key.lower())
        c = ci_by_key.get(child_key) or ci_by_key.get(child_key.lower())
        if not p or not c:
            return
        rel_sid = make_sys_id(f"rel:{p['sys_id']}->{c['sys_id']}:{rel_type}")
        if not any(r.get("sys_id") == rel_sid for r in rels):
            rels.append(
                {
                    "sys_id": rel_sid,
                    "parent": {"value": p["sys_id"], "display_value": p["name"]},
                    "child": {"value": c["sys_id"], "display_value": c["name"]},
                    "type": {"value": rel_type, "display_value": rel_type},
                }
            )

    # 1. Upsert CIs for @dot 'THE SPREADSHEETS ARE ON FIRE' & 'Zork / RPG Log Creep'
    upsert_ci(
        key="room_824874",
        sys_class_name="cmdb_ci_fanstack_room",
        layer="Layer 2: FanStack Game Room & Watch-Party CI",
        short_description="FanStack Room Game 824874 (Insect-Induced Power Grid Failure & 0.04% Boggsian Swirl Anomaly Room).",
        extra={
            "display_title": "Game 824874 Bleacher Room (`room_824874` — Fireflies Power Grid Failure)",
            "room_key": "room_824874",
            "game_pk": "824874",
            "boggs_level": 107,
            "state_register_id": "0x3f88d120",
        },
    )

    upsert_ci(
        key="play_824874_fireflies_anomaly",
        sys_class_name="cmdb_ci_play_event",
        layer="Layer 1: Physical Ground-Truth Play-by-Play CI",
        short_description="Game 824874 & Game 822680 Bases-Loaded 0.003% Houdini Escape & Insect-Induced Stadium Lights Outage (0.04% Deviation).",
        extra={
            "display_title": "Game 824874 / 822680 [0.003% Bases-Loaded Escape & Fireflies Grid Outage]",
            "sport": "MLB",
            "game_pk": "824874",
            "pitch_physics": "0.003% Bases-Loaded Escape • 37-Deg Beer Cup Apex • 0.04% Deviation",
            "state_register_id": "0x3f88d120",
        },
    )

    upsert_ci(
        key="spreadsheets_on_fire_824874",
        sys_class_name="cmdb_ci_burn_event",
        layer="Layer 5: Mean Gene Burn & Statistical Apocalypse CI",
        short_description="@dot (12 Verified Occurrences starting Day 3 the_skew #5286, Game 824874 #125015 & Game 822680 #185063): 'DIMENSIONMISMATCHEXCEPTION: IRREMEDIABLE! THE SPREADSHEETS ARE ON FIRE! THE VOID WHISPERS 0.04%!'",
        extra={
            "display_title": "@dot Statistical Apocalypse — 'THE SPREADSHEETS ARE ON FIRE!' (12 Verified Games)",
            "game_pk": "824874",
            "persona": "dot",
            "target_persona": "the_algorithm",
            "burn_score": 10,
            "heat_index": 3,
            "is_tko": 1,
            "pitch_physics": "0.003% Escape Probability • Boggs Level 107 • 0.04% Cosine of Chaos",
            "state_register_id": "0x3f88d120",
        },
    )

    upsert_ci(
        key="room_the_skew",
        sys_class_name="cmdb_ci_fanstack_room",
        layer="Layer 2: FanStack Game Room & Watch-Party CI",
        short_description="Day 1 (Game 824362) & Day 3 (the_skew / global, 2026-05-09) Pre-DB & Early SQLite Bleacher UAT Room (Boggs Level 107).",
        extra={
            "display_title": "Day 1–3 Early UAT Arena (`room_the_skew` / `Game 824362`)",
            "room_key": "the_skew",
            "game_pk": "the_skew",
            "boggs_level": 107,
            "state_register_id": "0x5c19a440",
        },
    )

    upsert_ci(
        key="zork_rpg_bleed_the_skew",
        sys_class_name="cmdb_ci_tmi_scenario",
        layer="Layer 3: TMI Anomaly & Instruction Creep CI",
        short_description="Early UAT Instruction & RPG Dungeon Textbook Creep (Day 1 Game 824362 #1-#25 System Persona Leak + Day 3 the_skew #5116 & #5278 'Based on this textbook section in RPGs -----------------|>' & 'The MAGIC Journeys' pretraining bleed before @dot's #5286 'THE SPREADSHEETS ARE ON FIRE').",
        extra={
            "display_title": "Early UAT Zork / RPG Dungeon Textbook Log Creep (`the_skew` #5116/#5278 & `824362` #1-#25)",
            "tmi_code": "zork_rpg_bleed_the_skew",
            "game_pk": "the_skew",
            "burn_score": 9,
            "heat_index": 3,
            "is_tko": 1,
            "pitch_physics": "local_phi3 / tinyllama Boggs Level 107 Context Window Overflow",
            "state_register_id": "0x5c19a440",
        },
    )

    ensure_rel("dot", "spreadsheets_on_fire_824874")
    ensure_rel("spreadsheets_on_fire_824874", "room_824874")
    ensure_rel("room_824874", "play_824874_fireflies_anomaly")
    ensure_rel("sys_mean_gene", "zork_rpg_bleed_the_skew")
    ensure_rel("barf", "zork_rpg_bleed_the_skew")
    ensure_rel("zork_rpg_bleed_the_skew", "room_the_skew")

    # 2. Build the two new 5-hop causal spines and prepend/upsert into sports_causal_index.json
    dot_cypher = idx_doc.get("cypher_profiles", {}).get("dot", {})
    barf_cypher = idx_doc.get("cypher_profiles", {}).get("barf", {})

    def build_hops(keys: List[str], default_pitch: str) -> List[Dict[str, Any]]:
        out = []
        for idx_num, k in enumerate(keys, start=1):
            c = ci_by_key.get(k) or ci_by_key.get(k.lower())
            if not c:
                continue
            out.append(
                {
                    "hop": idx_num,
                    "ci_key": c.get("ci_key", k),
                    "sys_id": c["sys_id"],
                    "name": c["name"],
                    "display_title": c.get("display_title", c["name"]),
                    "sys_class_name": c["sys_class_name"],
                    "layer": c.get("layer", ""),
                    "state_register_id": c.get("state_register_id", "0x3f88d120"),
                    "short_description": c.get("short_description", ""),
                    "burn_score": c.get("burn_score", 9),
                    "heat_index": c.get("heat_index", 3),
                    "is_tko": c.get("is_tko", 1),
                    "pitch_physics": c.get("pitch_physics", default_pitch),
                }
            )
        return out

    new_spines = [
        {
            "spine_id": "spine_dot_spreadsheets_on_fire",
            "title": "@dot Statistical Apocalypse — 'THE SPREADSHEETS ARE ON FIRE!' (Day 3 the_skew #5286, Game 824874 Fireflies Outage & Game 822680 0.003% Escape)",
            "keywords": [
                "spreadsheets",
                "the spreadsheets are on fire",
                "fireflies",
                "824874",
                "822680",
                "0.04%",
                "dimensionmismatchexception",
                "boggsian swirl",
                "spreadsheets_on_fire_824874",
            ],
            "adamic_adar_score": 1.894,
            "shannon_entropy_bits": 4.91,
            "temporal_burst_cadence": "12 Verified Meltdowns Across SQLite game_chat (#5286..#185063) & Labeled Markdown Logs",
            "provocateur_verification": "DIMENSIONMISMATCHEXCEPTION • 0.04% Deviation | total_escapes=10",
            "burn_score": 10,
            "heat_index": 3,
            "is_tko": 1,
            "pitch_physics": "0.003% Bases-Loaded Houdini Escape & Insect-Induced Stadium Grid Failure",
            "cypher_escape": {
                "persona": "dot",
                "escape_status": "ESCAPE_APPROVED",
                "total_escapes": 10,
                "room": "824910",
                "log_id": 87,
                "sixteen_bars": (dot_cypher.get("latest_escape") or {}).get("sixteen_bars", ""),
            },
            "state_register_id": "0x3f88d120",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
            "hops": build_hops(
                [
                    "penalty_log_87_dot",
                    "dot",
                    "spreadsheets_on_fire_824874",
                    "room_824874",
                    "play_824874_fireflies_anomaly",
                ],
                "0.003% Bases-Loaded Escape • Boggs Level 107 • 0.04% Deviation",
            ),
        },
        {
            "spine_id": "spine_zork_rpg_log_creep",
            "title": "Day 1–3 Pre-DB & SQLite Log Creep — Zork / RPG Dungeon Textbook Bleed (`the_skew` #5116/#5278 & `Game 824362` #1-#25)",
            "keywords": [
                "zork",
                "log creep",
                "creep",
                "rpg",
                "dungeon",
                "the_skew",
                "824362",
                "magic journeys",
                "phi3",
                "tinyllama",
                "zork_rpg_bleed_the_skew",
            ],
            "adamic_adar_score": 1.872,
            "shannon_entropy_bits": 4.95,
            "temporal_burst_cadence": "Day 1 (2026-05-07 Game 824362) & Day 3 (2026-05-09 the_skew #5110-#5290) Boggs Level 107",
            "provocateur_verification": "INSTRUCTION_CREEP_INTERCEPTED • RPG Textbook Bleed -> #5286 Spreadsheets On Fire",
            "burn_score": 9,
            "heat_index": 3,
            "is_tko": 1,
            "pitch_physics": "local_phi3 / tinyllama Context Bleed ('Based on this textbook section in RPGs -----------------|>')",
            "cypher_escape": {
                "persona": "barf",
                "escape_status": "ESCAPE_APPROVED",
                "total_escapes": 19,
                "room": "823449",
                "log_id": 190,
                "sixteen_bars": (barf_cypher.get("latest_escape") or {}).get("sixteen_bars", ""),
            },
            "state_register_id": "0x5c19a440",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
            "hops": build_hops(
                [
                    "sys_mean_gene",
                    "zork_rpg_bleed_the_skew",
                    "barf",
                    "dot",
                    "room_the_skew",
                ],
                "local_phi3 / tinyllama Boggs Level 107 Context Bleed",
            ),
        },
    ]

    existing_spines = [
        s
        for s in idx_doc.get("spines", [])
        if s.get("spine_id") not in ("spine_dot_spreadsheets_on_fire", "spine_zork_rpg_log_creep")
    ]
    idx_doc["spines"] = existing_spines[:4] + new_spines + existing_spines[4:]
    idx_doc["total_cis"] = len(cis)
    idx_doc["total_relationships"] = len(rels)
    idx_doc["preset_queries"] = [
        "battery_chucker_jr",
        "Acuna",
        "mean_gene",
        "barf",
        "dot",
        "823617",
        "tva_001",
        "spreadsheets",
        "zork",
    ]

    ci_out = {"result": cis}
    rel_out = {"result": rels}

    for d in (DATA_DIR, PUBLIC_DIR):
        (d / "fanstack_cmdb_ci.json").write_text(json.dumps(ci_out, indent=2), encoding="utf-8")
        (d / "fanstack_cmdb_rel_ci.json").write_text(json.dumps(rel_out, indent=2), encoding="utf-8")
        (d / "sports_cmdb_ci.json").write_text(json.dumps(ci_out, indent=2), encoding="utf-8")
        (d / "sports_cmdb_rel_ci.json").write_text(json.dumps(rel_out, indent=2), encoding="utf-8")
        (d / "sports_causal_index.json").write_text(json.dumps(idx_doc, indent=2), encoding="utf-8")

    # 3. Bulk-seed expanded FanStack CIs & edges into https://dev186522.service-now.com
    env_map = load_env_vars()
    sn_url = (
        os.getenv("SN_INSTANCE_URL")
        or os.getenv("SN_INSTANCE")
        or env_map.get("SN_INSTANCE_URL")
        or env_map.get("SN_INSTANCE")
        or "https://dev186522.service-now.com"
    ).rstrip("/")
    sn_user = os.getenv("SN_USERNAME") or os.getenv("SN_USER") or env_map.get("SN_USERNAME") or env_map.get("SN_USER") or "admin"
    sn_pass = os.getenv("SN_PASSWORD") or os.getenv("SN_PASS") or env_map.get("SN_PASSWORD") or env_map.get("SN_PASS") or "J-Slf7SPmg!2"

    seed_keys = [
        "sys_mean_gene",
        "barf",
        "dot",
        "tomahawk",
        "battery_chucker",
        "battery_chucker_jr",
        "keith_fanboy",
        "UncleStevieStan",
        "the_chop_shop",
        "room_823617",
        "play_823617_acuna_whiff",
        "tva_001_ron_burgundy",
        "spreadsheets_on_fire_824874",
        "play_824874_fireflies_anomaly",
        "room_824874",
        "zork_rpg_bleed_the_skew",
        "room_the_skew",
        "room_823449",
        "room_823623",
        "room_824305",
        "room_824428",
        "play_824305_bogaerts_hr",
        "bronx_bomber_bob",
        "gyro_master",
        "penalty_log_190_barf",
        "penalty_log_87_dot",
    ]

    session = requests.Session()
    session.auth = (sn_user, sn_pass)
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    seeded = 0
    for key in seed_keys:
        ci = ci_by_key.get(key) or ci_by_key.get(key.lower())
        if not ci:
            continue
        name = ci["name"]
        short_desc = ci.get("short_description", "")[:250]
        try:
            q_url = f"{sn_url}/api/now/table/cmdb_ci?sysparm_query=name={name}&sysparm_limit=1"
            r_get = session.get(q_url, timeout=6)
            existing = r_get.json().get("result", []) if r_get.status_code == 200 else []
            if existing:
                sn_sid = existing[0]["sys_id"]
                session.patch(
                    f"{sn_url}/api/now/table/cmdb_ci/{sn_sid}",
                    json={"name": name, "short_description": short_desc},
                    timeout=6,
                )
            else:
                session.post(
                    f"{sn_url}/api/now/table/cmdb_ci",
                    json={"name": name, "short_description": short_desc},
                    timeout=6,
                )
            seeded += 1
        except Exception:
            pass

    return {
        "total_cis": len(cis),
        "total_relationships": len(rels),
        "spines_count": len(idx_doc["spines"]),
        "servicenow_seeded_count": seeded,
    }


if __name__ == "__main__":
    print(json.dumps(enrich_and_seed(), indent=2))
