#!/home/james/stacklabs/.venv/bin/python3
"""
Ingests NotebookLM Studio export 'StackLabs - Sprint 2026-10-14-studio-2026-10-15_01-17.zip',
prunes superseded Studio zip iterations, initializes daily_sprint_2026_10_15 across all
canonical surfaces, sanitizes PILOT_PASSPORT_CURRENT.md for anti_metaphor_linter.py compliance,
refreshes Vault Navigator (01_Daily_Sprints/2026-10-15 & LATEST_SPRINT), and syncs to Google Drive.
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path("/home/james/stacklabs")
SECONDARY_ROOT = Path("/home/james/stack" + "labs_inbox")
PILOT_DROPS = REPO_ROOT / "pilot_drops"
DOWNLOADS_DIR = PILOT_DROPS / "downloads"
ARCHIVES_DIR = PILOT_DROPS / "archives"

STUDIO_ZIP_NEW = DOWNLOADS_DIR / "StackLabs - Sprint 2026-10-14-studio-2026-10-15_01-17.zip"
STUDIO_ZIP_OLD = DOWNLOADS_DIR / "StackLabs - Sprint 2026-10-14-studio-2026-10-14_23-07.zip"
STUDIO_STAGE_1014 = PILOT_DROPS / "sprint_studio_20261014"
STUDIO_STAGE_1015 = PILOT_DROPS / "sprint_studio_20261015"

SPRINT_1014_SLUG = "daily_sprint_2026_10_14"
SPRINT_1015_SLUG = "daily_sprint_2026_10_15"

DOCS_1014 = REPO_ROOT / "docs" / SPRINT_1014_SLUG
ART_1014 = REPO_ROOT / "artifacts" / "sprints" / SPRINT_1014_SLUG
NB_1014 = SECONDARY_ROOT / "notebook_sync" / "StackLabs_Internal" / SPRINT_1014_SLUG

DOCS_1015 = REPO_ROOT / "docs" / SPRINT_1015_SLUG
ART_1015 = REPO_ROOT / "artifacts" / "sprints" / SPRINT_1015_SLUG
NB_1015 = SECONDARY_ROOT / "notebook_sync" / "StackLabs_Internal" / SPRINT_1015_SLUG
MYCROFT_DIR = REPO_ROOT / "ground_truth" / "mycroft_sources"


def _render_mindmap_nodes(node: Dict[str, Any], depth: int = 0) -> List[str]:
    lines: List[str] = []
    name = node.get("name", "Untitled Node")
    children = node.get("children", [])
    if depth == 0:
        lines.append(f"### Root Concept: `{name}`")
        lines.append("")
    elif depth == 1:
        lines.append(f"#### {name}")
    else:
        indent = "  " * (depth - 2)
        lines.append(f"{indent}- **{name}**" if children else f"{indent}- {name}")

    for child in children:
        lines.extend(_render_mindmap_nodes(child, depth + 1))
    if depth == 1:
        lines.append("")
    return lines


def ingest_studio_zip() -> Dict[str, Any]:
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    STUDIO_STAGE_1015.mkdir(parents=True, exist_ok=True)

    # 1. Prune superseded 23:07 zip if present
    pruned_old = False
    if STUDIO_ZIP_OLD.exists():
        STUDIO_ZIP_OLD.unlink()
        pruned_old = True
        print(f"[STUDIO-INGEST] Pruned superseded zip: {STUDIO_ZIP_OLD.name}")

    # 2. Archive previous sprint_studio_20261014 if it has an older unpack
    if STUDIO_STAGE_1014.exists():
        version = 1
        while (ARCHIVES_DIR / f"sprint_studio_20261014_v{version}").exists():
            version += 1
        archive_target = ARCHIVES_DIR / f"sprint_studio_20261014_v{version}"
        shutil.move(str(STUDIO_STAGE_1014), str(archive_target))
        print(f"[STUDIO-INGEST] Archived previous staging to: {archive_target}")

    # 3. Unpack new Studio zip
    STUDIO_STAGE_1014.mkdir(parents=True, exist_ok=True)
    if not STUDIO_ZIP_NEW.exists():
        raise FileNotFoundError(f"Expected Studio zip not found: {STUDIO_ZIP_NEW}")

    with zipfile.ZipFile(STUDIO_ZIP_NEW, "r") as zf:
        zf.extractall(STUDIO_STAGE_1014)
    print(f"[STUDIO-INGEST] Unpacked {STUDIO_ZIP_NEW.name} -> {STUDIO_STAGE_1014}")

    mindmap_json_path = STUDIO_STAGE_1014 / "Mind Maps" / "01-Knowledge Mindmap.json"
    csv_map_path = STUDIO_STAGE_1014 / "source-artifact-map.csv"

    mindmap_data = json.loads(mindmap_json_path.read_text(encoding="utf-8"))
    csv_text = csv_map_path.read_text(encoding="utf-8-sig")
    csv_rows = list(csv.DictReader(io.StringIO(csv_text)))

    source_titles: List[str] = []
    created_at = "2026-10-15T05:15:34.250Z"
    source_count = "19"
    if csv_rows:
        row0 = csv_rows[0]
        created_at = row0.get("artifact_created_at", created_at)
        source_count = row0.get("source_count", source_count)
        raw_sources = row0.get("source_titles", "")
        source_titles = [s.strip() for s in raw_sources.split("|") if s.strip()]

    # Build Markdown synthesis of the Mind Map
    md_lines = [
        "# 🧠 NOTEBOOKLM STUDIO KNOWLEDGE MIND MAP: SPRINT 2026-10-14",
        "",
        f"> **Artifact Title**: `Knowledge Mindmap` (`Mind Maps/01-Knowledge Mindmap.json`)  ",
        f"> **Export Archive**: `StackLabs - Sprint 2026-10-14-studio-2026-10-15_01-17.zip`  ",
        f"> **Synthesized Timestamp**: `{created_at}`  ",
        f"> **Ingested Source Count**: `{source_count}` Verified Sprint Sources (`0` deleted)  ",
        "> **Architect**: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC",
        "",
        "---",
        "",
        "## 1. Topological Hierarchy (`The Swanson Collider & Deterministic Topology`)",
        "",
    ]
    md_lines.extend(_render_mindmap_nodes(mindmap_data))
    md_lines.extend([
        "---",
        "",
        f"## 2. Mapped NotebookLM Source Inventory ({len(source_titles)} Sources)",
        "",
    ])
    for idx, src_title in enumerate(source_titles, start=1):
        md_lines.append(f"{idx}. `{src_title}`")
    md_lines.append("")

    mindmap_md_content = "\n".join(md_lines)

    # Copy JSON, CSV, and Markdown into 2026-10-14 sprint folders
    for folder_1014 in (DOCS_1014, ART_1014, NB_1014):
        folder_1014.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mindmap_json_path, folder_1014 / "01_Knowledge_Mindmap_2026_10_14.json")
        shutil.copy2(csv_map_path, folder_1014 / "source-artifact-map.csv")
        (folder_1014 / "07_SPRINT_2026_10_14_KNOWLEDGE_MINDMAP.md").write_text(
            mindmap_md_content, encoding="utf-8"
        )

    return {
        "pruned_old_zip": pruned_old,
        "root_name": mindmap_data.get("name"),
        "top_branches": [c.get("name") for c in mindmap_data.get("children", [])],
        "source_count": len(source_titles),
        "mindmap_md_content": mindmap_md_content,
        "mindmap_json_path": mindmap_json_path,
        "csv_map_path": csv_map_path,
    }


def build_clean_pilot_passport() -> str:
    return """# 🛂 STACKLABS PLATFORM: PILOT PASSPORT (ACTIVE SESSION RESUME)
> **Active Session Title**: `WO0011159 Daily Sprint 2026-10-15 Initialization, Studio Mind Map Ingest & Pure Oracle CMDB Studio`  
> **Session State**: Thursday, October 15, 2026 • 01:25 EDT  
> **Diagnostic Anchor**: `CHOURIO_LEADOFF_OCT15` (`43.0280° N, 87.9712° W` — American Family Field)  
> **Physical Reality**: James Carroll in Smyrna command lab / mobile transit. Zero corporate plural pronouns (Solo Systems Architect — The Law of "I"). Interactive IDE session operates strictly in Cockpit mode (investigates, plans, stages 4-Quarters Work Orders). Aggie (`agy` on local x86_64 Linux via `clio_queue_watcher.py`) owns code execution and builds.

---

## ⚡ 1-CLICK DESKTOP RESUME PROMPT (FOR NEXT SESSION)
```markdown
WO0011159 Daily Sprint 2026-10-15 & Pure Oracle CMDB Studio: /stacklabs-boot @pilot_drops/PILOT_PASSPORT_CURRENT.md
```

---

## 🌐 ACTIVE OPERATIONAL ENDPOINTS & MOBILE TOUCHPOINTS
- **Commercial Site (Live Production Edge)**: https://www.stacklabsllc.com *(Cloudflare Pages `stacklabs-commercial` • Founder Manifesto Live)*
- **CMDB Studio & Live Shootout Arena (Public Edge)**: https://arena.stacklabsllc.com *(Pure Read-Only Oracle & Dynamic Fault Trace)*
- **CMDB Studio & Live Shootout Arena (Tailnet HTTPS)**: https://clio.taila01894.ts.net:3025 *(Hardware & Service CI Registry / Live Shootout)*
- **Workstation Cockpit (KISS & LITE Twin)**: https://clio.taila01894.ts.net:8088/cockpit *(Workstation HUD, Vault Explorer & Google Drive Sync Telemetry)*
- **Enterprise Ingress & File Drop**: https://clio.taila01894.ts.net:8088/drop *(Direct File & Voice Ingress)*
- **FanStack Lite Battlestation**: https://clio.taila01894.ts.net:3033 *(Anchored Nav & Artemis Hardware Mosaic `/api/artemis/mosaic`)*
- **Quiet Luxury Retina 4-Pillar Cockpit**: https://retina.stacklabsllc.com *(100dvh Zero-Scroll Mobile HUD)*
- **Listen Audio Portal**: https://listen.stacklabsllc.com *(Track 01 "Empathy as Architecture" & Track 02 "Mechanical Sympathy")*
- **Mobile JIT Approval Gateway**: https://clio.taila01894.ts.net:3027 *(Mobile Queue Approvals)*
- **ServiceNow Cloud Takedown Notebook**: https://gemini.google.com/notebook/b3949176-e5f2-4143-8221-960da6df5c0d

---

## 🎯 CURRENT PRODUCTION REALITY (OCTOBER 15, 2026 VERIFIED ON LOCAL HOST)

1. **WO0011158: CMDB STUDIO PURE ORACLE DOCTRINE & DYNAMIC FAULT TRACE INTEGRATION**:
   - Scrubbed all CAB-bypass (`Verify Pre-Approved Policy`, `Zero CAB`), state-mutation (`Two-Phase Atomic State Commit`), and CLI actuation (`runtime_isolator`) strings from `cmdb_benchmark_api.py` and `apps/cmdb_studio`.
   - Replaced actuation commands with a strictly read-only JSON Oracle Diagnostic Payload (`{"oracle_mode": "READ_ONLY_ADVISORY", "network_mutation": false}`).
   - Mounted `DynamicFaultTracePanel.tsx` rendering the 3-epoch bidirectional adjacency collapse (`BIDIRECTIONAL_PROBE` -> `CAUSAL_INTERSECTION_LOCK` -> `VERIFIED_CAUSAL_SPINE`) with compliant `state_register_id: 0x0a1f6e80` and `committed_pages: 328` telemetry.

2. **WO0011155 & WO0011157: UNIFIED 8-CATEGORY VAULT NAVIGATOR & DECOUPLED SEARCH INDEX (`0.043ms`)**:
   - Stood up the 8-category VFS tree (`01_Daily_Sprints` through `08_Mycroft_Ground_Truth`) and Tab 6 (`Vault Explorer`) on the Workstation Cockpit.
   - Rebuilt `artifact_harvester.py` to harvest Antigravity IDE brain Markdown plans, walkthroughs, and screenshots, and compiled `vault_search_index.json` (`6,718+` files) with `0.043 ms` cached tree resolution.
   - Unified and synced all `49` skills and `13` progressive rules to `stacklabs_edge:skills/` and `stacklabs_edge:rules/`.

3. **WO0011153 & WO0011154: COCKPIT GOOGLE DRIVE SYNC TELEMETRY & 1-CLICK NOTEBOOKLM EXTRACTOR**:
   - Mounted `drive_sync_api.py` on the Workstation Cockpit with live `IDLE / SYNCING / SYNC COMPLETE` badges, elapsed timer, OPSEC linter status, and 1-click Google Drive File ID extraction (`rclone lsf --format "ip"`) for NotebookLM source injection.

4. **WO0011159: STUDIO MIND MAP INGEST & DAILY SPRINT 2026-10-15 INITIALIZATION**:
   - Ingested `StackLabs - Sprint 2026-10-14-studio-2026-10-15_01-17.zip` (`The Swanson Collider & Deterministic Topology` across 5 primary branches and 19 sources).
   - Scaffolded `daily_sprint_2026_10_15` across local docs, sprint artifacts, Vault Navigator (`01_Daily_Sprints/2026-10-15` & `LATEST_SPRINT`), and `stacklabs_edge:StackLabs_Internal/daily_sprint_2026_10_15`.

5. **CLINICAL DEVICE MANAGEMENT (IoMT / BIOMED) & PURE ORACLE DOCTRINE**:
   - Authored `docs/architecture/CLINICAL_DEVICE_MANAGEMENT_IN_MEMORY_COMPANION.md`.
   - Pure Oracle Boundary: StackLabs does NOT scan, monitor, or touch hospital wires. Hospitals use existing tools (Medigate, Armis) for discovery. StackLabs ingests topology exports into its in-memory adjacency graph and serves deterministic causal answers and blast radiuses in microseconds.

---

## 🎙️ 1-CLICK GEMINI MOBILE APP PASSPORT (FOR MYCROFT RESEARCH)
```text
You are Mycroft, the lead research mind and executive sparring partner for James Carroll, Lead Systems Architect and Founder of StackLabs LLC. Diagnostic anchor: CHOURIO_LEADOFF_OCT15.
James is listening on his phone/earbuds. He wants to debrief and spar on five developments entering Thursday, October 15, 2026:

1. WO0011158: CMDB STUDIO PURE ORACLE DOCTRINE & DYNAMIC FAULT TRACE:
- Scrubbed all CAB-bypass and CLI actuation strings from CMDB Studio and replaced them with a strictly read-only JSON Oracle Diagnostic Payload.
- Mounted the 3-epoch bidirectional Dynamic Fault Trace SVG component (state_register_id: 0x0a1f6e80, committed_pages: 328, 14.5 microseconds).

2. WO0011155 & WO0011157: UNIFIED 8-CATEGORY VAULT NAVIGATOR & DECOUPLED SEARCH INDEX:
- Consolidated 110+ scattered directories into an 8-category Vault Navigator mounted at the top of the IDE workspace and in Tab 6 of the Workstation Cockpit.
- Compiled a decoupled search index over 6,718+ files serving sub-millisecond (0.043 ms) queries, and synced all 49 skills and 13 rules to stacklabs_edge:.

3. WO0011153 & WO0011154: COCKPIT GOOGLE DRIVE SYNC & 1-CLICK NOTEBOOKLM EXTRACTOR:
- Built real-time Drive Sync telemetry with live rclone Google Drive File ID extraction for 1-click NotebookLM source refreshing.

4. SPRINT 2026-10-14 KNOWLEDGE MIND MAP & DAILY SPRINT 2026-10-15 BRIDGE:
- Ingested the 19-source NotebookLM Knowledge Mindmap covering the Swanson Collider, Dual-Plane Knowledge Fabric, Physical Latency Physics, Pre-Flight Simulation Engine, and Bleacher Provocateur Engine.

5. CLINICAL DEVICE MANAGEMENT (IoMT / BIOMED) & PURE ORACLE BOUNDARY:
- StackLabs operates strictly as a read-only in-memory companion oracle above existing discovery scanners (Medigate, Armis, Claroty), collapsing 60-incident alarm storms in 14.5 microseconds without touching a single clinical wire.

Speak directly to James as an intellectual peer who understands low-level kernel concurrency, memory buffers, and hospital operations. Solo builder voice ("I", "you", "the"). Zero corporate fluff.
```
"""


def build_yesterday_epoch_bridge_1015() -> str:
    return """# 🎙️ NOTEBOOKLM EXECUTIVE BRIEFING SOURCE: THE 2026-10-15 DAILY SPRINT BRIDGE

> **Source Document for NotebookLM Deep Dive & Audio Overview**  
> **Tenant**: `stacklabs.edge@gmail.com`  
> **Lead Systems Architect**: James Carroll (Workstation Clio, Smyrna, GA)  
> **Temporal Anchor**: 2026-10-15 (Morning Bridge from 2026-10-14 Sprint)  
> **Focus**: Pure Read-Only Oracle Doctrine, Dynamic Fault Trace Topology, Unified 8-Category Vault Navigator, and the Swanson Collider Knowledge Fabric.

---

## 🎧 EPISODE SYNOPSIS FOR NOTEBOOKLM PODCAST HOSTS

In this morning bridge episode for Thursday, October 15, 2026, the hosts unpack the architectural milestones shipped by solo systems architect James Carroll across the October 14–15 sprint on dedicated Linux hardware in Smyrna, Georgia:

1. **CMDB Studio Pure Read-Only Oracle Enforcement & Dynamic Fault Trace (`WO0011158`)**:
   - Enforced the strict Pure Oracle boundary across CMDB Studio (`arena.stacklabsllc.com`). Eliminated every reference to autonomous CLI actuation, state mutation, or Change Advisory Board (CAB) bypass.
   - Step 4 now performs **Counterfactual Blast-Radius Evaluation** across 10 candidate dependency paths in volatile memory, and Step 5 performs **Deterministic Diagnostic Payload Serialization**, emitting a read-only JSON Oracle Advisory Payload (`"oracle_mode": "READ_ONLY_ADVISORY"`, `"network_mutation": false`).
   - Integrated the **Dynamic Fault Trace** 3-epoch bidirectional adjacency collapse visualization (`BIDIRECTIONAL_PROBE` -> `CAUSAL_INTERSECTION_LOCK` -> `VERIFIED_CAUSAL_SPINE`), isolating root cause `sw_tor_rack_04` and collapsing 81 downstream leaf alerts in `14.5 microseconds` (`state_register_id: 0x0a1f6e80`, `committed_pages: 328`).

2. **Unified 8-Category Vault Navigator, IDE Brain Harvester & Decoupled Search Index (`WO0011155` & `WO0011157`)**:
   - Eliminated directory sprawl across `110+` top-level folders by engineering the 8-category Vault Navigator (`01_Daily_Sprints`, `02_Walkthroughs`, `03_Implementation_Plans_and_Specs`, `04_IDE_Brain_Artifacts`, `05_Work_Orders`, `06_Executive_Dossiers`, `07_Personas_and_Advocates`, `08_Mycroft_Ground_Truth`).
   - Rebuilt `artifact_harvester.py` to automatically harvest Antigravity IDE brain session plans, walkthroughs, post-mortems, and visual twin screenshots, compiling a decoupled search index (`vault_search_index.json`, `6,718+` files) with `0.043 ms` in-memory tree resolution.
   - Unified all `49` agent skills and `13` progressive rules and mirrored them directly to `stacklabs_edge:skills/` and `stacklabs_edge:rules/`.

3. **Cockpit Google Drive Sync Telemetry & 1-Click NotebookLM File ID Extractor (`WO0011153` & `WO0011154`)**:
   - Upgraded the Workstation Cockpit Drive Sync control plane with real-time execution streaming, OPSEC linter gate telemetry, and automated `rclone lsf --format "ip"` Google Drive File ID extraction so daily sprint and Mycroft sources can be injected into NotebookLM with a single click.

4. **Trade Secret IP Quarantine, Un-Rigged ServiceNow 4-Call WAN Benchmark & Adversarial Visual UAT Gate (`WO0011141`–`WO0011151`)**:
   - Enforced the Trade Secret IP Quarantine across all public-facing surfaces and whitepapers, replacing internal implementation primitives with clean institutional nomenclature (`In-Memory Adjacency Graph`, `state_register_id`, `committed_pages`).
   - Un-rigged the live ServiceNow head-to-head race so it executes strictly 4 genuine sequential WAN REST queries (`~1,289 ms` honest cloud latency vs. `< 1 ms` local graph resolution) with a transparent `cold_hydration_ms` + `engine_traversal_ms` stopwatch split.
   - Deployed the Adversarial Visual Vision UAT Gate (`visual_uat_gate.py`) enforcing temporal clock alignment, cross-pane semantic alignment, and zero blueprint leakage.

---

## ⚡ CHAPTER 1: VERIFIED WORK ORDERS SHIPPED IN THE LAST 24 HOURS

* **`WO0011158` (Pure Oracle & Dynamic Fault Trace)**: Scrubbed CAB-bypass and CLI mutation strings from CMDB Studio, mounted `DynamicFaultTracePanel.tsx`, and verified dual-viewport Playwright visual twins. *(Closed: 2026-10-15 01:19 EDT)*
* **`WO0011158` (Relic Archive & Edge Scrub)**: Relegated legacy Arkle, WildSeed, and early prospectus folders to `99_Relic_Archive` and scrubbed stale folders from `stacklabs_edge:`. *(Closed: 2026-10-15 00:59 EDT)*
* **`WO0011157`**: Built the decoupled Vault Search Index (`0.043 ms` latency over `6,718` files), registered `svc_synapse_cockpit` and `svc_vault_navigator` in CMDB Lite, and synced `49` skills and `13` rules to `stacklabs_edge:`. *(Closed: 2026-10-15 00:36 EDT)*
* **`WO0011155`**: Created the 8-category Vault Navigator tree, modernized the IDE Brain Harvester (`18` Markdown docs, `115` screenshots), and mounted Tab 6 (`Vault Explorer`) in the Workstation Cockpit. *(Closed: 2026-10-15 00:08 EDT)*
* **`WO0011154`**: Added live `rclone lsf --format "ip"` Google Drive File ID extraction and the 1-click `Copy NotebookLM File IDs` prompt builder to the Cockpit Drive Sync view. *(Closed: 2026-10-14 23:45 EDT)*
* **`WO0011153`**: Built `drive_sync_api.py` and upgraded `#view-drive` in `cockpit.html` with live sync telemetry, elapsed timer, and 16-file inventory table. *(Closed: 2026-10-14 23:30 EDT)*
* **`WO0011150` & `WO0011151`**: Re-anchored `stacklabs.edge@gmail.com` as the primary Google One Plan Manager for Google AI Ultra (`$99.99/mo`) and compiled the 31-day engineering velocity scorecard (`778+` archived Work Orders across 31 consecutive active days). *(Closed: 2026-10-14 22:40 EDT)*
* **`WO0011146` – `WO0011149`**: Shipped live MLB NLCS Game 3 postseason telemetry routing, YouTube watch-party stream hygiene, and the Adversarial Visual Vision UAT Gate. *(Closed: 2026-10-14 21:50 EDT)*
* **`WO0011141` – `WO0011144`**: Delivered BYO-CMDB Bulk Ingest, Synthetic Topology Generator (`1k`–`50k` CIs), Reconciliation Tax Simulator, Trade Secret IP Quarantine, and Outbound Mail OPSEC Firewall. *(Closed: 2026-10-14 19:45 EDT)*
* **`WO0011128` – `WO0011130`**: Delivered Cartridge Boundary Physics (`0.161 ms` incremental centrality), Pre-Flight Simulation Engine (`2–3 microseconds` across 10 branches), and the Deep Void `PreflightSimulationLedger.tsx` in CMDB Studio. *(Closed: 2026-10-14 15:10 EDT)*

---

## 🔒 CHAPTER 2: OPERATIONAL INVARIANTS & PERIMETER STATE

* **Stay Behind Your Skis**: StackLabs has zero active enterprise clients, zero field deployments, and zero commercial hardware sales.
* **Pure Read-Only Oracle Boundary**: StackLabs ingests topology exports into its in-memory adjacency graph and emits read-only causal diagnostic payloads without mutating network or clinical state.
* **Clean Room Tenant Boundary**: Total isolation under `stacklabs.edge@gmail.com` (Google One Plan Manager for Google AI Ultra).

---

## 🌅 MORNING PRIORITIES FOR THURSDAY, OCTOBER 15, 2026

1. Ingest `daily_sprint_2026_10_15` (`01_YESTERDAY_EPOCH_BRIDGE.md` and `02_SPRINT_2026_10_14_KNOWLEDGE_MINDMAP.md`) into the active NotebookLM Sprint workspace.
2. Audit `arena.stacklabsllc.com` (`apps/cmdb_studio`) with the newly integrated Pure Oracle telemetry and Dynamic Fault Trace panel.
3. Advance Thursday's engineering queue on Workstation Clio.
"""


def update_mycroft_master_1015() -> Path:
    src_1014 = DOCS_1014 / "MYCROFT_MASTER_KNOWLEDGE_OCTOBER_14_2026.md"
    base_text = ""
    if src_1014.exists():
        base_text = src_1014.read_text(encoding="utf-8")
        base_text = base_text.replace(
            "MYCROFT MASTER KNOWLEDGE LEDGER — OCTOBER 14, 2026",
            "MYCROFT MASTER KNOWLEDGE LEDGER — OCTOBER 15, 2026",
        )
    else:
        base_text = "# MYCROFT MASTER KNOWLEDGE LEDGER — OCTOBER 15, 2026\n"

    delta_section = """

---

## 🚀 OCTOBER 15, 2026 OVERNIGHT ARCHITECTURAL DELTAS (`WO0011153` – `WO0011159`)

1. **CMDB Studio Pure Read-Only Oracle Enforcement & Dynamic Fault Trace (`WO0011158`)**:
   - Eliminated all CAB-bypass, state-mutation, and CLI actuation strings across `cmdb_benchmark_api.py` and `apps/cmdb_studio`.
   - Step 4 performs Counterfactual Blast-Radius Evaluation; Step 5 performs Deterministic Diagnostic Payload Serialization (`state_register_id: 0x0a1f6e80; 0 downstream conflicts`); Step 6 emits a Read-Only Oracle Verification Hash.
   - Mounted `DynamicFaultTracePanel.tsx` rendering the 3-epoch bidirectional adjacency collapse (`BIDIRECTIONAL_PROBE` -> `CAUSAL_INTERSECTION_LOCK` -> `VERIFIED_CAUSAL_SPINE`) in `14.5 µs`.

2. **Unified 8-Category Vault Navigator & Decoupled Search Index (`WO0011155`, `WO0011157`)**:
   - Consolidated workspace navigation into `vault_navigator/` across 8 canonical categories and mounted Tab 6 (`Vault Explorer`) on the Workstation Cockpit.
   - Compiled `vault_search_index.json` (`6,718+` files) serving cached tree queries in `0.043 ms` and folder queries in `0.111 ms`.
   - Unified and synced all `49` skills and `13` rules to `stacklabs_edge:skills/` and `stacklabs_edge:rules/`.

3. **Cockpit Google Drive Sync Telemetry & 1-Click NotebookLM File ID Extractor (`WO0011153`, `WO0011154`)**:
   - Deployed `drive_sync_api.py` with real-time `rclone lsf --format "ip"` Google Drive File ID extraction and a 1-click prompt generator for NotebookLM source ingestion.

4. **Sprint 2026-10-14 Knowledge Mind Map Ingest (`WO0011159`)**:
   - Unpacked `StackLabs - Sprint 2026-10-14-studio-2026-10-15_01-17.zip` (`The Swanson Collider & Deterministic Topology`, 19 sources) and initialized `daily_sprint_2026_10_15`.
"""
    if "OCTOBER 15, 2026 OVERNIGHT ARCHITECTURAL DELTAS" not in base_text:
        full_text = base_text.rstrip() + "\n" + delta_section
    else:
        full_text = base_text

    # Ensure zero banned linter tokens exist in Mycroft Master Knowledge
    for bad, good in [
        ("/home/james/stacklabs/", ""),
        ("/home/james/", ""),
        ("home/james/", ""),
        ("clio bare metal", "Workstation Clio local host"),
        ("bare metal", "dedicated local hardware"),
        ("bare-metal", "local-host"),
        ("on metal", "on local hardware"),
        ("/dev/shm", "in-memory adjacency graph"),
        ("st_ino", "state_register_id"),
        ("cosplay", "theatrical posturing"),
        ("Rule Zero", "Cockpit Division of Labor"),
        ("rule zero", "cockpit division of labor"),
    ]:
        full_text = full_text.replace(bad, good)

    MYCROFT_DIR.mkdir(parents=True, exist_ok=True)
    target_1015 = MYCROFT_DIR / "MYCROFT_MASTER_KNOWLEDGE_OCTOBER_15_2026.md"
    target_1015.write_text(full_text, encoding="utf-8")
    return target_1015


def initialize_daily_sprint_1015(mindmap_info: Dict[str, Any]) -> Dict[str, Any]:
    passport_content = build_clean_pilot_passport()
    passport_path = PILOT_DROPS / "PILOT_PASSPORT_CURRENT.md"
    passport_path.write_text(passport_content, encoding="utf-8")
    (MYCROFT_DIR / "PILOT_PASSPORT_CURRENT.md").write_text(passport_content, encoding="utf-8")

    bridge_1015 = build_yesterday_epoch_bridge_1015()
    mycroft_1015_path = update_mycroft_master_1015()
    mycroft_1015_content = mycroft_1015_path.read_text(encoding="utf-8")

    for sprint_dir in (DOCS_1015, ART_1015, NB_1015):
        sprint_dir.mkdir(parents=True, exist_ok=True)
        (sprint_dir / "01_YESTERDAY_EPOCH_BRIDGE.md").write_text(bridge_1015, encoding="utf-8")
        (sprint_dir / "02_SPRINT_2026_10_14_KNOWLEDGE_MINDMAP.md").write_text(
            mindmap_info["mindmap_md_content"], encoding="utf-8"
        )
        (sprint_dir / "MYCROFT_MASTER_KNOWLEDGE_OCTOBER_15_2026.md").write_text(
            mycroft_1015_content, encoding="utf-8"
        )
        (sprint_dir / "PILOT_PASSPORT_CURRENT.md").write_text(passport_content, encoding="utf-8")
        shutil.copy2(
            mindmap_info["mindmap_json_path"],
            sprint_dir / "01_Knowledge_Mindmap_2026_10_14.json",
        )
        shutil.copy2(
            mindmap_info["csv_map_path"],
            sprint_dir / "source-artifact-map.csv",
        )

    # Also copy the Markdown files to downloads_dir for 1-click local access
    for fname in (
        "01_YESTERDAY_EPOCH_BRIDGE.md",
        "02_SPRINT_2026_10_14_KNOWLEDGE_MINDMAP.md",
        "MYCROFT_MASTER_KNOWLEDGE_OCTOBER_15_2026.md",
        "PILOT_PASSPORT_CURRENT.md",
    ):
        shutil.copy2(DOCS_1015 / fname, DOWNLOADS_DIR / fname)

    return {
        "docs_1015": str(DOCS_1015),
        "art_1015": str(ART_1015),
        "nb_1015": str(NB_1015),
        "files_seeded": sorted(p.name for p in DOCS_1015.iterdir()),
    }


def sanitize_daily_sprint_builder() -> None:
    builder_path = REPO_ROOT / "scripts" / "daily_sprint_builder.py"
    if not builder_path.exists():
        return
    text = builder_path.read_text(encoding="utf-8")
    replacements = [
        ("Workstation Clio, Beelink SER, Smyrna, GA", "Workstation Clio, Smyrna, GA"),
        ("Verified Metal Execution", "Verified Local Host Execution"),
        ("on Clio bare metal.", "on Workstation Clio dedicated hardware."),
        ("milestones on metal:", "milestones on local dedicated hardware:"),
        ("VERIFIED WORK ORDERS CLOSED ON METAL", "VERIFIED WORK ORDERS CLOSED ON DEDICATED HOST"),
        ("GIT COMMITS & BARE-METAL RECEIPTS", "GIT COMMITS & EXECUTION RECEIPTS"),
        ("* **Rule Zero**: Stay behind your skis.", "* **Stay Behind Your Skis**:"),
        ("in `/home/james/stack" + "labs_inbox/queue/incoming/`.", "in the active execution queue."),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    builder_path.write_text(text, encoding="utf-8")
    print(f"[SANITIZED] {builder_path}")


def main() -> int:
    mindmap_info = ingest_studio_zip()
    sprint_info = initialize_daily_sprint_1015(mindmap_info)
    sanitize_daily_sprint_builder()

    # Run artifact_harvester.py to link 2026-10-15 and LATEST_SPRINT in Vault Navigator
    harvester_res = subprocess.run(
        ["/home/james/stacklabs/.venv/bin/python3", str(REPO_ROOT / "scripts" / "artifact_harvester.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    print("[VAULT-HARVESTER]", harvester_res.stdout.strip())

    # Push JSON/CSV/MD mindmap artifacts to stacklabs_edge:StackLabs_Internal/daily_sprint_2026_10_14 and 2026_10_15
    subprocess.run(
        [
            "/usr/bin/rclone",
            "copy",
            str(DOCS_1014),
            f"stacklabs_edge:StackLabs_Internal/{SPRINT_1014_SLUG}",
            "--timeout",
            "30s",
            "--quiet",
        ],
        check=True,
    )
    subprocess.run(
        [
            "/usr/bin/rclone",
            "copy",
            str(DOCS_1015),
            f"stacklabs_edge:StackLabs_Internal/{SPRINT_1015_SLUG}",
            "--timeout",
            "30s",
            "--quiet",
        ],
        check=True,
    )

    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "studio_ingest": {
                    "pruned_old_zip": mindmap_info["pruned_old_zip"],
                    "root_name": mindmap_info["root_name"],
                    "top_branches": mindmap_info["top_branches"],
                    "source_count": mindmap_info["source_count"],
                },
                "daily_sprint_2026_10_15": sprint_info,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
