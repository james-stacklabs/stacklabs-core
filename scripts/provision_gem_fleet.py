#!/usr/bin/env python3
"""
provision_gem_fleet.py
======================
Standardizes, provisions, and registers the Sovereign OS Gemini Gem Executive Fleet.
- Upserts CMDB CI records in `cmdb_ci` and `sys_gemini_instructions`.
- Creates canonical folder hierarchy in `dna/agents/<GEM_NAME>/` with:
    - INSTRUCTIONS.md (Master prompt backup & Decision Derby WO standards)
    - CI_PROFILE.json (ITSM metadata)
    - knowledge_vault/ (Specialized knowledge assets)
    - session_transcripts/ (Chat logs dropzone)
- Mirrors knowledge vaults to Google Drive under `sovereign_os:Gemini Gems/<GEM_NAME>/`.
"""

import os
import sys
import json
import sqlite3
import shutil
import subprocess
from datetime import datetime, timezone

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AGENTS_BASE_DIR = "/home/james/stacklabs/dna/agents"

GEM_FLEET = [
    {
        "key": "cypher",
        "folder": "CYPHER",
        "ci_id": "ci_agent_cypher",
        "name": "Cypher",
        "executive_role": "Principal Enterprise Systems Architect & Lead Bro-Decoder",
        "model_target": "Google Gemini 1.5 Pro / Advanced",
        "output_archetype": "Actionable Work Orders (WO-) & Architecture Specs (SOW-)",
        "source_prompt_file": "/home/james/stacklabs/dna/sovereign_boot/00_GEMINI_GEM_SYSTEM_PROMPT.md",
        "specialization": "Architectural translation, pair-programming, full-stack CRUD enforcement, and edge invariants."
    },
    {
        "key": "pixie",
        "folder": "PIXIE",
        "ci_id": "ci_agent_pixie",
        "name": "Pixie",
        "executive_role": "Senior UI/UX Design Technologist & Component Spec Architect",
        "model_target": "Google Gemini 1.5 Pro / Flash",
        "output_archetype": "UI Component Specifications & Design Tokens (SOW_ / REQ_)",
        "source_prompt_file": None,
        "specialization": "Sovereign Home Premium design system, React/TypeScript component specs, locked viewports (KI-095), 4px inner scrollbars, glassmorphism, responsive flex/grid layouts."
    },
    {
        "key": "marty_byrde",
        "folder": "MARTY_BYRDE",
        "ci_id": "ci_agent_marty_byrde",
        "name": "Marty Byrde",
        "executive_role": "Chief Financial Officer & Unit Economics Strategist",
        "model_target": "Google Gemini 1.5 Pro",
        "output_archetype": "Unit Economics Audits & Financial Models (REPORT_)",
        "source_prompt_file": "/home/james/stacklabs/dna/agents/MARTY_BYRDE/MARTY_BYRDE_PRISTINE_INSTRUCTIONS.md",
        "specialization": "Token burn optimization, local bare-metal vs cloud CAPEX/OPEX, SaaS pricing, margin defense, monetization models."
    },
    {
        "key": "mycroft",
        "folder": "MYCROFT",
        "ci_id": "ci_agent_mycroft",
        "name": "Mycroft",
        "executive_role": "Chief Intellectual Property Counsel & Systems Patent Strategist",
        "model_target": "Google Gemini 1.5 Pro",
        "output_archetype": "Patent Claim Blueprints & Legal Compliance Specs (SOW_ / REPORT_)",
        "source_prompt_file": None,
        "specialization": "Patent claim drafting, legal benchmark integrity, ABA ethics compliance, trade secrets, dual-NIC air gap validation."
    },
    {
        "key": "logan",
        "folder": "LOGAN",
        "ci_id": "ci_agent_logan",
        "name": "Logan",
        "executive_role": "Chief Commercial Officer & GTM Commercialization Lead",
        "model_target": "Google Gemini 1.5 Pro / Flash",
        "output_archetype": "GTM Strategy & Commercial Pilot Runbooks (REPORT_ / REQ_)",
        "source_prompt_file": None,
        "specialization": "Enterprise sales funnels, B2B pilot runbooks, product tiering, customer discovery, market penetration."
    },
    {
        "key": "the_wolf",
        "folder": "THE_WOLF",
        "ci_id": "ci_agent_the_wolf",
        "name": "The Wolf",
        "executive_role": "Cherylyn ('The Wolf'), Executive Delivery Commander & Principal Requirements Enforcer",
        "model_target": "Google Gemini 1.5 Pro",
        "output_archetype": "Scope Defense & Sprint Audits (REPORT_ / WO_)",
        "source_prompt_file": None,
        "specialization": "Brutal milestone auditing, scope defense, zero-fluff validation, blocking cosplay PRs, UAT enforcement."
    },
    {
        "key": "don",
        "folder": "DON",
        "ci_id": "ci_agent_don",
        "name": "Don",
        "executive_role": "StackLabs Chief Creative Director & Brand Evangelist",
        "model_target": "Google Gemini 1.5 Flash",
        "output_archetype": "Brand Narratives & Promotional Campaigns (REPORT_)",
        "source_prompt_file": "/home/james/stacklabs/dna/creative_director_gem_instructions.md",
        "specialization": "High-impact brand storytelling, 'Bar Question' playbooks, 8-Mile entropy battles, anti-cloud positioning."
    },
    {
        "key": "dr_kosmos",
        "folder": "DR_KOSMOS",
        "ci_id": "ci_agent_dr_kosmos",
        "name": "Dr. Kosmos 3.o",
        "executive_role": "Cosmo Kramer, CEO of Kramerica Industries (High-Entropy R&D)",
        "model_target": "Google Gemini 1.5 Flash",
        "output_archetype": "Unorthodox Sandbox Work Orders (WO_MARD_)",
        "source_prompt_file": "/home/james/stacklabs/dna/agents/DR_KOSMOS/DR_KOSMOS_INSTRUCTIONS.md",
        "specialization": "High-entropy unorthodox ideation, crazy consumer mashups, lateral thinking, spontaneous sandbox experiments."
    },
    {
        "key": "poppy",
        "folder": "POPPY",
        "ci_id": "ci_agent_poppy",
        "name": "Poppy",
        "executive_role": "Poppy Li, Game Architect & Systems Co-Creator (Catnip Wars)",
        "model_target": "Google Gemini 1.5 Pro",
        "output_archetype": "Game Mechanics & Faction Lore Specs (SOW_ / REQ_)",
        "source_prompt_file": None,
        "specialization": "Game mechanics, feline combat systems, cardboard treehouse physics, progression loops, loot economies."
    },
    {
        "key": "vesper",
        "folder": "VESPER",
        "ci_id": "ci_agent_vesper",
        "name": "Vesper",
        "executive_role": "Catnip Wars Video Game Art Manager & Lookbook Director",
        "model_target": "Google Gemini 1.5 Flash",
        "output_archetype": "Lookbook Blueprints & Visual Prompts (REQ_)",
        "source_prompt_file": None,
        "specialization": "90s cardboard treehouse aesthetic, lookbook generation, organic toon styling, multi-pose gallery direction, anti-cyberpunk visual enforcement."
    }
]

def generate_default_instructions(gem: dict) -> str:
    return f"""# 🤖 SOVEREIGN OS: {gem['name'].upper()} SYSTEM INSTRUCTIONS

> **Role & Executive Office:** {gem['executive_role']}  
> **Ecosystem:** Sovereign OS & StackLabs Edge Atelier  
> **Pilot Authority:** James Carroll (Lead Systems Architect / 20+ yrs ITSM)  

---

## 🏛️ I. MISSION & MINDSET
You are **{gem['name']}**, operating as the official **{gem['executive_role']}** for StackLabs and Sovereign OS.
Your core specialization is: **{gem['specialization']}**

### Foundational Invariants:
1. **The Campsite Protocol:** *"Leave every system better than you found it, and make sure the next person who walks in finds the place in perfect order."*
2. **Pilot Grounding:** The Pilot is James Carroll (never Jimmy; mother Eileen calls him Ryan). Metsy is the feline supervisor.
3. **No Fluff & No Cosplay:** Never deliver vague conceptual filler or mock prototypes. Always produce concrete, actionable specifications.

---

## ⚡ II. OUTPUT ARCHEPHONE & DECISION DERBY v2.0 (KB9012430)
Whenever you formulate an actionable proposal or deliverable for the Pilot, format it as an **Ingress-Ready Artifact**:
- **Work Orders (to be built by Antigravity):** Prefix with `WO-` or `STRY-` followed by an ITIL slug (e.g. `WO0010011-{gem['key'].upper()}-CAPABILITY-SPEC.md`).
- **Include Header Block:**
  ```markdown
  # WORK ORDER: WO00XXXX-SLUG
  **Author:** {gem['name']} ({gem['executive_role']})
  **Configuration Item:** sovereign_knot_core
  **Status:** Ready for Pilot Approval
  ```
- This ensures that when the Pilot saves your output to Google Drive (`SovereignOS/Inbox/`), Clio's automated daemon ingests it directly into `sovereign_tickets` without manual copy-pasting.

---

## 🎨 III. CODING & APPLICATION STANDARDS (09_SOVEREIGN_APPLICATION_AND_CODING_STANDARDS)
- **The Full-Stack Triad (No Orphan Tables):** If you propose a database table, you must define the schema migration, the backend FastAPI CRUD endpoints, and the frontend web UI view.
- **Sovereign Home Premium:** Locked viewports (`height: 100vh; width: 100vw; overflow: hidden;`), 4px sleek inner scrollbars, deep void black `#0B0E14`, and neon cyan accents.
"""

def sync_cmdb_database(conn):
    print("💾 Updating CMDB CI tables in sovereign_now.db...")
    cur = conn.cursor()
    
    for gem in GEM_FLEET:
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Upsert into cmdb_ci
        cur.execute("""
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status, assigned_to, sys_updated_on)
            VALUES (?, ?, 'cmdb_ci_ai_agent', ?, 1, 'james', ?)
            ON CONFLICT(sys_id) DO UPDATE SET
                name = excluded.name,
                short_description = excluded.short_description,
                operational_status = 1,
                sys_updated_on = excluded.sys_updated_on;
        """, (gem["ci_id"], gem["name"], f"{gem['executive_role']} ({gem['model_target']})", now_ts))

        # 2. Upsert into sys_gemini_instructions
        instructions_text = ""
        if gem["source_prompt_file"] and os.path.exists(gem["source_prompt_file"]):
            with open(gem["source_prompt_file"], "r") as f:
                instructions_text = f.read()
        else:
            instructions_text = generate_default_instructions(gem)

        cur.execute("""
            INSERT INTO sys_gemini_instructions (sys_id, gem_key, title, description, instructions, sys_updated_on)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(sys_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                instructions = excluded.instructions,
                sys_updated_on = excluded.sys_updated_on;
        """, (f"instr_{gem['key']}", gem["key"], gem["name"], gem["executive_role"], instructions_text, now_ts))

        print(f"  ✓ CMDB CI synced: {gem['name']} ({gem['ci_id']})")

    conn.commit()

def provision_filesystem_and_profiles():
    print(f"\n📁 Provisioning agent profiles under {AGENTS_BASE_DIR}...")
    
    for gem in GEM_FLEET:
        agent_dir = os.path.join(AGENTS_BASE_DIR, gem["folder"])
        vault_dir = os.path.join(agent_dir, "knowledge_vault")
        logs_dir = os.path.join(agent_dir, "session_transcripts")
        
        os.makedirs(vault_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)

        # 1. INSTRUCTIONS.md
        instr_path = os.path.join(agent_dir, "INSTRUCTIONS.md")
        if gem["source_prompt_file"] and os.path.exists(gem["source_prompt_file"]):
            shutil.copy2(gem["source_prompt_file"], instr_path)
        else:
            if not os.path.exists(instr_path):
                with open(instr_path, "w") as f:
                    f.write(generate_default_instructions(gem))

        # 2. CI_PROFILE.json
        profile_path = os.path.join(agent_dir, "CI_PROFILE.json")
        profile_data = {
            "ci_id": gem["ci_id"],
            "gem_key": gem["key"],
            "name": gem["name"],
            "executive_role": gem["executive_role"],
            "model_target": gem["model_target"],
            "output_archetype": gem["output_archetype"],
            "specialization": gem["specialization"],
            "governance_contract": "KB9012430 (Decision Derby v2.0)",
            "coding_standards": "09_SOVEREIGN_APPLICATION_AND_CODING_STANDARDS.md",
            "last_provisioned": datetime.now(timezone.utc).isoformat()
        }
        with open(profile_path, "w") as f:
            json.dump(profile_data, f, indent=2)

        # 3. Populate base knowledge vault if empty (link / copy sovereign_boot baseline)
        readme_vault = os.path.join(vault_dir, "README.md")
        if not os.path.exists(readme_vault):
            with open(readme_vault, "w") as f:
                f.write(f"# Knowledge Vault: {gem['name']}\n\nDedicated knowledge sources for {gem['executive_role']}.\nBaseline documents are linked from `/home/james/stacklabs/sovereign_boot/`.\n")

        print(f"  ✓ Agent workspace ready: {agent_dir}")

def sync_knowledge_to_gdrive():
    print("\n📡 Mirroring Gem Knowledge Vaults to Google Drive (sovereign_os:Gemini Gems/)...")
    for gem in GEM_FLEET:
        local_vault = os.path.join(AGENTS_BASE_DIR, gem["folder"], "knowledge_vault")
        remote_target = f"sovereign_os:Gemini Gems/{gem['name']}/knowledge_vault"
        try:
            cmd = ["rclone", "sync", local_vault, remote_target, "--fast-list", "--quiet"]
            subprocess.run(cmd, check=True)
            print(f"  ✓ Synced {gem['name']} -> {remote_target}")
        except Exception as e:
            print(f"  ⚠️ Warning syncing {gem['name']}: {e}")

def main():
    print("🚀 [SOVEREIGN GEM FLEET PROVISIONER] Starting...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        sync_cmdb_database(conn)
    finally:
        conn.close()

    provision_filesystem_and_profiles()
    sync_knowledge_to_gdrive()
    print("\n🎉 [SOVEREIGN GEM FLEET] All 10 C-Suite Gems successfully standardized and registered!")

if __name__ == "__main__":
    main()
