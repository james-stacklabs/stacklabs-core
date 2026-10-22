#!/usr/bin/env python3
import sqlite3
import os
import subprocess
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
OUTPUT_PATH = "/home/james/sovereign_inbox/today/OPEN_TICKETS_MOBILE_BRIEFING.md"
REPORTS_PATH = "/home/james/sovereign_inbox/reports/OPEN_TICKETS_MOBILE_BRIEFING_20260815.md"

def generate_briefing():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT number, type, priority, state, cmdb_ci, short_description, description, work_notes, sys_created_on
        FROM sovereign_tickets 
        WHERE state = 1
        ORDER BY priority ASC, sys_created_on DESC
    """)
    rows = cursor.fetchall()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md = []
    md.append("# 📱 SOVEREIGN OS: OPEN TICKETS MOBILE BRIEFING & SPRINT DISPATCH")
    md.append(f"**Date:** {now_str} | **Pilot:** James Carroll (Lead Systems Architect)")
    md.append(f"**Target Objective:** Mobile Architecture Alignment & Errand Sprint Preparation")
    md.append(f"**Total Open Tickets:** {len(rows)} tickets in `state = 1` (Open / New)")
    md.append("\n---\n")
    
    md.append("## 🧭 EXECUTIVE SUMMARY & SPRINT OVERVIEW")
    md.append("This document contains the complete technical briefing for all **9 open work orders, incidents, and stories** in Sovereign OS. Take this document on mobile to review, debate architecture decisions with Gemini, and align on execution strategy before returning to the workstation.")
    md.append("\n### 🎯 SPRINT TICKETS AT A GLANCE\n")
    md.append("| # | Ticket Number | Priority | Affected CI | Title | Domain |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    domains = {
        "WO-2026-GROGU-HOTSPOT-FAILOVER-015": "Edge Networking & Failover",
        "INC9908848": "TMI / Temporal Simulation",
        "INC1983318": "Platform Intake & Governance",
        "INC82057": "Boot Protocol & Amnesia Cure",
        "INC5792869": "Intellectual Property / USPTO",
        "INC5541976": "Intellectual Property / Patent",
        "WO-2026-UNIVERSAL-VOICE-HEAL-MOUNT-028": "Self-Healing & Core API",
        "WO-2026-FANSTACK-ROOM-BUILDER-FIX-027": "FanStack Sports & NFL Ingress",
        "WO-2026-KNOT-BENCH-02": "Sovereign Knot & ServiceNow Interlock"
    }
    
    for i, r in enumerate(rows, 1):
        num, ttype, pri, st, ci, title, desc, notes, created = r
        dom = domains.get(num, "Core Platform")
        md.append(f"| **{i}** | `{num}` | P{pri} | `{ci}` | {title[:45]}... | {dom} |")
        
    md.append("\n---\n")
    
    # Detailed Ticket Sections
    for i, r in enumerate(rows, 1):
        num, ttype, pri, st, ci, title, desc, notes, created = r
        dom = domains.get(num, "Core Platform")
        
        md.append(f"## 🎫 Ticket #{i}: `{num}` ({ttype})")
        md.append(f"- **Title:** **{title}**")
        md.append(f"- **Priority:** `P{pri}` | **State:** `1 (Open)` | **Affected CI:** `{ci}`")
        md.append(f"- **Created:** `{created}` | **Domain:** {dom}")
        md.append("")
        
        # Strategic Breakdown
        md.append("### 🔍 Technical Context & Problem Statement")
        # Clean description
        desc_clean = (desc or "No detailed description provided.").strip()
        md.append(f"```text\n{desc_clean[:1500]}\n```")
        
        md.append("### 🛠️ Proposed Solution & Implementation Blueprint")
        if "GROGU" in num:
            md.append("- **Core Action:** Implement `/home/james/stacklabs/scripts/grogu_network_failover.sh` systemd service on Grogu (RPi 5).")
            md.append("- **Mechanism:** NetworkManager ping watchdog polling 8.8.8.8 over primary home Wi-Fi; automatically activates mobile hotspot connection if 3 consecutive packet losses occur.")
            md.append("- **Safety Rollback:** Automatically restore primary SSID when home gateway beacon returns.")
        elif "9908848" in num:
            md.append("- **Core Action:** Decouple multi-agent timeline state feeds inside `tmi_daemon.py` and `fanstack_chatbots.py`.")
            md.append("- **Mechanism:** Implement temporal state branches allowing advocates to debate speculative timeline scenarios without polluting canonical baseball telemetry.")
        elif "1983318" in num:
            md.append("- **Core Action:** Formalize `/home/james/sovereign_inbox/INTAKE_NEW_STACK.md` standardized template and automated schema scoper.")
            md.append("- **Mechanism:** Provide 1-click stack creation script that validates port allocations, CMDB records, and theme tokens.")
        elif "82057" in num:
            md.append("- **Core Action:** Optimize `sovereign_boot.md` amnesia cure workflow and boot mode flags (`-gd`, `-ts`, `-uat`, `-dr`, `-rc`).")
            md.append("- **Mechanism:** Ensure zero-latency boot diagnostics, hardwired DNA ingestion, and anchor word verification.")
        elif "5792869" in num or "5541976" in num:
            md.append("- **Core Action:** Compile StackLabs IP Presentation Portfolio & Cloud-to-Edge Hydrated DOM Extraction Patent claims.")
            md.append("- **Mechanism:** Generate high-resolution architectural specification PDF and claims index for USPTO provisional filing.")
        elif "VOICE-HEAL" in num:
            md.append("- **Core Action:** Mount Universal Voice Heal microphone component across all 10 micro-frontend app headers.")
            md.append("- **Mechanism:** Connect client-side Web Audio API to `POST http://clio.taila01894.ts.net:8090/api/system/heal/voice` with automatic incident ticket logging (KI-053).")
        elif "FANSTACK-ROOM-BUILDER" in num:
            md.append("- **Core Action:** Fix seated state persona assignment bug in `setup_all_rooms.py` and add NFL schedule / room builder ingress.")
            md.append("- **Mechanism:** Patch `game_persona` foreign key constraint and add NFL SportsRadar / ESPN API slate parser.")
        elif "KNOT-BENCH" in num:
            md.append("- **Core Action:** Finalize ServiceNow Flow Designer 'Guarded CMDB Record Update' interlock integration.")
            md.append("- **Mechanism:** Deploy MID Server script calling Port 3023 Sovereign Knot Consensus Engine ($S = 1.000$) to approve or quarantine CMDB updates.")
        else:
            md.append("- **Core Action:** Execute standard 3-step ITSM resolution pipeline.")
            
        md.append("")
        md.append("### 💬 Mobile Discussion Topics for Gemini")
        if "GROGU" in num:
            md.append("1. *What should the ping timeout and retry interval be on edge nodes to prevent flapping between home Wi-Fi and cellular hotspot?*")
            md.append("2. *Should Tailscale re-authenticate automatically or rely on persistent state keys during dynamic interface switching?*")
        elif "9908848" in num:
            md.append("1. *How should temporal branching be indexed in SQLite so canonical game state and 'what-if' fan debates never conflict?*")
            md.append("2. *What is the optimal token throttle for branching scenario generation under Vertex AI?*")
        elif "1983318" in num:
            md.append("1. *What are the essential mandatory fields for new Stack Intake (Port, Theme, CMDB CI, Target Personas)?*")
            md.append("2. *How should automated folder scaffolding integrate with the Decision Derby watchdog?*")
        elif "82057" in num:
            md.append("1. *Are there any additional sub-flags needed for Game Day (`-gd`) or Sandbox Training (`-ts`) modes?*")
            md.append("2. *How should the session anchor word validation be scored for cognitive sobriety?*")
        elif "5792869" in num or "5541976" in num:
            md.append("1. *How can we best emphasize the novel multi-agent hardware interlock and edge-to-cloud arbitration claims in the patent summary?*")
            md.append("2. *What visual flow diagrams best illustrate the 'Sovereign Knot Consensus' mechanism to patent examiners?*")
        elif "VOICE-HEAL" in num:
            md.append("1. *What voice commands should be recognized out of the box (e.g., 'Restart Relay', 'Fix Scoreboard', 'Heal Chatbots')?*")
            md.append("2. *How should voice feedback be synthesized back to the user (browser TTS or silent badge pulse)?*")
        elif "FANSTACK-ROOM-BUILDER" in num:
            md.append("1. *How should NFL multi-game slates be grouped compared to MLB daily series in the navigation rail?*")
            md.append("2. *What unique persona archetypes should be provisioned for Sunday NFL watch parties?*")
        elif "KNOT-BENCH" in num:
            md.append("1. *How can we demonstrate the quarantine state visually in ServiceNow Flow Designer to enterprise prospects?*")
            md.append("2. *What REST payload schema is most resilient for MID server network blips?*")
        else:
            md.append("1. *What are the primary acceptance criteria and edge cases?*")
            
        md.append("")
        md.append("### ✅ Acceptance & UAT Criteria")
        md.append("- [ ] Code written & tested natively under `antigravity` service account.")
        md.append("- [ ] Blast radius verified; zero regression on active ports.")
        md.append("- [ ] Standalone `walkthrough_[TICKET].md` created in `/home/james/sovereign_inbox/`.")
        md.append("- [ ] `sovereign_tickets.work_notes` updated and ticket transitioned to `state = 4 (Resolved)`.")
        md.append("\n---\n")
        
    md.append("## 🚀 RECOMMENDED SPRINT EXECUTION SEQUENCE")
    md.append("When you return to the workstation, here is the optimal attack order to close all 9 tickets efficiently:")
    md.append("1. **Quick Governance & Ingress Wins (Tickets 4, 3)**: Close `INC82057` (Boot doc) and `INC1983318` (Stack Intake manifest).")
    md.append("2. **Core Feature & Bugfix Deployments (Tickets 8, 7)**: Fix `WO-2026-FANSTACK-ROOM-BUILDER-FIX-027` and mount `WO-2026-UNIVERSAL-VOICE-HEAL-MOUNT-028`.")
    md.append("3. **Edge Infrastructure & Networking (Tickets 1, 2)**: Deploy `WO-2026-GROGU-HOTSPOT-FAILOVER-015` and patch `INC9908848`.")
    md.append("4. **Enterprise Showcase & IP Documentation (Tickets 9, 5, 6)**: Finalize ServiceNow Knot Showcase `WO-2026-KNOT-BENCH-02` and package patent briefs `INC5792869` & `INC5541976`.")
    md.append("\n---\n*Generated autonomously by Antigravity under Sovereign OS Governance & SDLC Invariants.*")
    
    content = "\n".join(md)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(REPORTS_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, "w") as f:
        f.write(content)
        
    with open(REPORTS_PATH, "w") as f:
        f.write(content)
        
    print(f"Generated briefing at {OUTPUT_PATH} and {REPORTS_PATH} ({len(content)} bytes).")

if __name__ == "__main__":
    generate_briefing()
