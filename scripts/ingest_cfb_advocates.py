#!/usr/bin/env python3
"""
Sovereign OS — CFB Top 25 & Cupcake Advocates Ingestion Engine (WO0010094)
Parses all 78 seated advocates from dna/docs/Sovereign_Sports_CFB_Top25_and_Cupcake_Advocates_Registry.md
and deploys them transactionally via FastAPI Forge Deploy (api_client.deploy_persona).
"""

import os
import re
import sys
import json
import time

sys.path.append('/home/james/stacklabs')
from scripts.core import api_client
from scripts.core.api_client import get_team_color

REGISTRY_PATH = "/home/james/stacklabs/dna/docs/Sovereign_Sports_CFB_Top25_and_Cupcake_Advocates_Registry.md"


def parse_registry(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Normalize backslash-escaped markdown formatting
    clean_text = (
        text.replace("\\#", "#")
            .replace("\\[", "[")
            .replace("\\]", "]")
            .replace("\\`", "`")
            .replace("\\*", "*")
            .replace("\\-", "-")
            .replace("\\_", "_")
    )

    blocks = re.split(r"\n(?=#{3,4}\s+@)", clean_text)
    advocate_blocks = blocks[1:]

    advocates = []
    for i, block in enumerate(advocate_blocks):
        header_m = re.match(r"^#{3,4}\s+@([a-zA-Z0-9_]+)", block)
        if not header_m:
            continue
        handle = header_m.group(1).strip()

        # Team
        team_m = re.search(r"-\s+\*\*Team(?:\s*/\s*Scope)?:\*\*\s*(?:`([^`]+)`|([^\n]+))", block)
        team_raw = (team_m.group(1) or team_m.group(2)).strip() if team_m else "UNKNOWN"
        clean_team = team_raw.split("(")[0].replace("`", "").strip().upper()

        # Cadence
        cad_m = re.search(r"-\s+\*\*Interaction Cadence:\*\*\s*`?([a-zA-Z0-9_-]+)`?", block)
        cadence = cad_m.group(1).strip().lower() if cad_m else "pacer"

        # Boggs Level
        boggs_m = re.search(r"-\s+\*\*Boggs Reactivity \(Entropy\):\*\*\s*Level\s*([0-9]+)", block)
        boggs = int(boggs_m.group(1)) if boggs_m else 2

        # Directive / System prompt
        sys_m = re.search(r"-\s+\*\*System Instruction / Directive:\*\*\s*(.+?)(?=\n-\s+\*\*|$)", block, re.DOTALL)
        sys_prompt = sys_m.group(1).strip() if sys_m else ""

        # Display name extraction: 'You are Display Name (@handle)'
        disp_m = re.search(r"You are\s+([^(@\n]+?)\s+\(@", sys_prompt)
        display_name = disp_m.group(1).strip() if disp_m else handle.replace("_", " ").title()

        # Deep lore
        lore_m = re.search(r"-\s+\*\*Deep Lore & Superstitions:\*\*\s*(.+?)(?=\n-\s+\*\*|$)", block, re.DOTALL)
        deep_lore = lore_m.group(1).strip() if lore_m else ""

        # Governance
        gov_m = re.search(r"-\s+\*\*Governance & (?:Alignment Boundaries|Guardrails):\*\*\s*(.+?)(?=\n-\s+\*\*|$|\n---)", block, re.DOTALL)
        governance = gov_m.group(1).strip() if gov_m else ""

        advocates.append({
            "handle": handle,
            "display_name": display_name,
            "team": clean_team,
            "cadence": cadence,
            "boggs_level": boggs,
            "system_prompt": sys_prompt,
            "deep_lore": deep_lore,
            "governance": governance
        })

    return advocates


def ingest_advocates():
    print(f"📡 Loading registry: {REGISTRY_PATH}")
    advocates = parse_registry(REGISTRY_PATH)
    print(f"📋 Parsed {len(advocates)} advocates from registry.")

    if len(advocates) != 78:
        print(f"⚠️ Warning: Expected 78 advocates, found {len(advocates)}")

    success_count = 0
    fail_count = 0

    for idx, adv in enumerate(advocates, 1):
        team = adv["team"]
        color = get_team_color(team, fallback="#00b4d8")
        behavior_notes = f"{adv['cadence']} cfb football advocate"

        # Generate 2 canned takes from directive for live kickoff seeding
        canned_takes = [
            f"Gameday locked in for {team}! Line of scrimmage wins championships.",
            f"Watching closely today. {adv['display_name']} checking in from the gameday feed."
        ]

        try:
            res = api_client.deploy_persona(
                handle=adv["handle"],
                display_name=adv["display_name"],
                team=team,
                system_prompt=adv["system_prompt"],
                deep_lore=adv["deep_lore"],
                behavior_notes=behavior_notes,
                governance=adv["governance"],
                color=color,
                cadence=adv["cadence"],
                boggs_level=adv["boggs_level"],
                avatar_url=f"/api/persona_image/{adv['handle']}",
                canned_takes=canned_takes
            )
            if res.get("status") == "success" or res.get("persona_id"):
                success_count += 1
                if idx % 10 == 0 or idx == len(advocates):
                    print(f"  [{idx}/{len(advocates)}] Deployed @{adv['handle']} ({adv['display_name']} - {team}) - {color}")
            else:
                print(f"  ❌ Failed to deploy @{adv['handle']}: {res}")
                fail_count += 1
        except Exception as e:
            print(f"  ❌ Exception deploying @{adv['handle']}: {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"🎯 INGESTION SUMMARY:")
    print(f"   Successfully Ingested: {success_count} / {len(advocates)}")
    print(f"   Failed Ingestions:     {fail_count}")
    print("=" * 60)
    return success_count == len(advocates)


if __name__ == "__main__":
    success = ingest_advocates()
    sys.exit(0 if success else 1)
