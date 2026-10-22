#!/usr/bin/env python3
"""
compile_massive_notebook_payload.py
Queries the live production sovereign_now.db and harvests raw, unhinged archived game logs,
specifically targeting the high-tension crisis chronicles, out-of-control yaps, and
outage reports (Port 5173 nightmare, Wall of Shame, Hate Mail summaries, etc.).
"""
import os
import sqlite3
import glob
import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
LOGS_DIR = "/home/james/stacklabs/dna/archives/game_logs"
OUTPUT_PATH = "/home/james/stacklabs/dna/notebook_lm_exports/SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE.md"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def compile_payload():
    print(f"Connecting to database: {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    package = []

    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Header
    package.append(f"**LAST SYNC TIME:** {timestamp_str} UTC\n")
    package.append("# 🧠 STACKLABS // SOVEREIGN OS MONOLITHIC DATA PACKAGE")
    package.append("## THE ENCYCLOPEDIC GROUND-TRUTH LEDGER FOR NOTEBOOKLM INGESTION")
    package.append("**CONFIDENTIAL // EYES ONLY // STACKLABS CORE OPERATIONS**")
    package.append(f"**COMPILED ON:** {timestamp_str} UTC via live database cascade\n")

    # 1. PERSONA DATABASE
    print("Harvesting active AI commentating personas...")
    package.append("---")
    package.append("## 👥 SECTION 1: THE CORE COMMENTARY PERSONA DIRECTORY")
    package.append("Every active AI agent registered in the Sovereign M.A.R.D commentator swarm.")

    try:
        personas = cur.execute("SELECT * FROM persona ORDER BY team, user_name").fetchall()
        for p in personas:
            p_dict = dict(p)
            package.append(f"\n### 👤 PERSONA: @{p_dict.get('user_name')} ({p_dict.get('display_name')})")
            package.append(f"*   **Team Alignment:** {p_dict.get('team')}")
            package.append(f"*   **Engine Target:** {p_dict.get('llm_engine')}")
            package.append(f"*   **Boggs Volatility Rating:** {p_dict.get('boggs_level')}/5")
            package.append(f"*   **Cadence Config:** {p_dict.get('cadence')}")
            package.append(f"*   **UI Color Accent:** {p_dict.get('color')}")
            package.append(f"*   **Avatar Path:** {p_dict.get('avatar_url')}")
            
            package.append(f"\n#### 📜 Core Cognitive System Instructions")
            package.append("```text")
            package.append(p_dict.get('system_prompt', 'No prompt set').strip())
            package.append("```")

            package.append(f"\n#### 📖 Deep Backstory & Lore Matrix")
            package.append("```text")
            package.append(p_dict.get('deep_lore', 'No deep lore set').strip())
            package.append("```")

            package.append(f"\n#### 🛡️ Behavioral Governance Rules")
            package.append("```text")
            package.append(p_dict.get('governance', 'No governance boundaries set').strip())
            package.append("```")
            package.append("\n" + "="*40 + "\n")
    except Exception as e:
        package.append(f"❌ Failed to fetch personas: {e}")

    # 2. SDLC TICKETING HISTORIES
    print("Harvesting SDLC tickets...")
    package.append("---")
    package.append("## 🎟️ SECTION 2: THE COMPLETE SDLC RESOLUTION LEDGER")
    package.append("Every historical enhancement, bugfix, and story mapped in sovereign_tickets.")

    try:
        tickets = cur.execute("SELECT * FROM sovereign_tickets ORDER BY sys_created_on DESC").fetchall()
        package.append("| Number | Type | State | Short Description | Created On | Assigned To |")
        package.append("|---|---|---|---|---|---|")
        for t in tickets:
            t_dict = dict(t)
            state_label = "Open" if t_dict.get("state") == "1" else "Resolved"
            desc = t_dict.get("short_description", "").replace("|", "\\|")
            package.append(f"| {t_dict.get('number')} | {t_dict.get('type')} | {state_label} | {desc} | {t_dict.get('sys_created_on')} | {t_dict.get('assigned_to')} |")
        
        package.append("\n\n### Detailed Ticket Scope Blocks")
        for t in tickets:
            t_dict = dict(t)
            package.append(f"\n#### 📋 {t_dict.get('number')}: {t_dict.get('short_description')}")
            package.append(f"*   **System ID:** `{t_dict.get('sys_id')}`")
            package.append(f"*   **Full Description:**")
            package.append("> " + t_dict.get("description", "No description").replace("\n", "\n> "))
            package.append("\n" + "-"*30)
    except Exception as e:
        package.append(f"❌ Failed to fetch tickets: {e}")

    # 3. CMDB ROOMS & AI CIs
    print("Harvesting CMDB Configuration Items...")
    package.append("---")
    package.append("## 🏢 SECTION 3: CMDB REGISTERED CONFIGURATION ITEMS")
    package.append("Every bare-metal system room, active commentator CI, and service boundary.")

    try:
        rooms = cur.execute("SELECT * FROM cmdb_ci_fanstack_room").fetchall()
        for r in rooms:
            r_dict = dict(r)
            package.append(f"\n### 🟢 CMDB FANSTACK ROOM CI: {r_dict.get('room_key')}")
            package.append(f"*   **Name:** {r_dict.get('name')}")
            package.append(f"*   **Sys ID:** `{r_dict.get('sys_id')}`")
            package.append(f"*   **State:** {r_dict.get('room_state')}")
            package.append(f"*   **Sim Speed:** {r_dict.get('sim_speed')}x")
            package.append(f"*   **Telemetry Cadence:** {r_dict.get('u_cadence')}")
            package.append(f"*   **Reactivity Cap:** Boggs {r_dict.get('boggs_level')}")
            
            # Fetch CIs in this room
            personas_in_room = cur.execute("""
                SELECT p.user_name, p.display_name, m.prompt_overlay
                FROM m2m_persona_room m
                JOIN persona p ON p.user_name = m.persona
                WHERE m.room = ?
            """, (r_dict.get('room_key'),)).fetchall()
            
            package.append(f"\n#### Active Commentators in Room CI:")
            for p_r in personas_in_room:
                package.append(f"*   @{p_r['user_name']} ({p_r['display_name']}) - Overlay: *{p_r['prompt_overlay'] or 'None'}*")
            
            package.append("\n" + "-"*30)
    except Exception as e:
        package.append(f"❌ Failed to fetch CMDB rooms: {e}")

    # 4. HIGH-ENTROPY UNHINGED CRISIS LEDGER (THE SPREADSHEETS ARE ON FIRE)
    print("Harvesting unhinged incident and volatility reports...")
    package.append("---")
    package.append("## 🚨 SECTION 4: SYSTEM INSTABILITY, VOLATILITY INCIDENTS, & OPERATIONS CRISES")
    package.append("Raw emergency dispatches, hardware outages, hate mail audits, and server crashes.")

    crisis_logs = [
        "port_5173_nightmare.md",
        "THE_WALL_OF_SHAME.md",
        "crazy_thang.md",
        "barf.md",
        "hate_mail_executive_summary.md",
        "UT_Bro_Report.md"
    ]

    for log_name in crisis_logs:
        log_path = os.path.join(LOGS_DIR, log_name)
        if os.path.exists(log_path):
            print(f"  Harvesting crisis log: {log_name}...")
            package.append(f"\n### 🔥 ARCHIVED INCIDENT REPORT: {log_name}")
            package.append(f"*   **Source Path:** `{log_path}`")
            package.append("\n```text")
            try:
                with open(log_path, "r", encoding="utf-8") as lf:
                    content = lf.read().strip()
                    package.append(content)
            except Exception as le:
                package.append(f"Error reading log: {le}")
            package.append("```\n" + "="*40 + "\n")
        else:
            print(f"  ⚠️ Crisis log not found: {log_name}")

    # 5. MASSIVE PLAY-BY-PLAY CHAT STREAMS
    print("Harvesting play-by-play simulator chat streams...")
    package.append("---")
    package.append("## 📣 SECTION 5: LIVE M.A.R.D SIMULATOR DISCOURSE STREAMING LOGS")
    package.append("High-volume commentator chat streams, 8-Mile verses, and raw postgame transcripts.")

    discourse_logs = [
        "executive_report_48h.md",
        "game_log_823319.md",
        "game_log_824031_20260521.md",
        "wardy_chat_tail_05.md",
        "ANTIGRAVITY_WO_WILDSEED_FANSTACK.md"
    ]

    for log_name in discourse_logs:
        log_path = os.path.join(LOGS_DIR, log_name)
        if os.path.exists(log_path):
            print(f"  Harvesting discourse stream: {log_name}...")
            package.append(f"\n### 💬 DISCOURSE STREAM: {log_name}")
            package.append(f"*   **Source Path:** `{log_path}`")
            package.append("\n```text")
            try:
                with open(log_path, "r", encoding="utf-8") as lf:
                    lines = lf.readlines()
                    # Crop to first 900 lines to remain massive but safe
                    cropped = lines[:900]
                    package.append("".join(cropped).strip())
                    if len(lines) > 900:
                        package.append(f"\n... [TRUNCATED {len(lines)-900} ADDITIONAL LINES OF RAW M.A.R.D FEED] ...")
            except Exception as le:
                package.append(f"Error reading log: {le}")
            package.append("```\n" + "="*40 + "\n")
        else:
            print(f"  ⚠️ Discourse log not found: {log_name}")

    # 6. HISTORICAL SESSION EXECUTIVE REPORTS
    print("Harvesting session executive reports...")
    package.append("---")
    package.append("## 📅 SECTION 6: CHRONOLOGICAL SESSION EXECUTIVE REPORTS")
    package.append("Every historical session executive report tracking active sprints, shipped features, regressions, and blockers.")

    try:
        reports = []
        for r, _, fs in os.walk("/home/james/sovereign_inbox"):
            if "pilot_drops" in r.split(os.sep):
                continue
            for f in fs:
                if f.startswith("SESSION_REPORT_") and f.endswith(".md"):
                    reports.append(os.path.join(r, f))
        
        # Sort in reverse chronological order
        reports.sort(key=os.path.basename, reverse=True)
        
        # Take the most recent 100 reports to keep payload ultra-premium but fast
        for report_path in reports[:100]:
            filename = os.path.basename(report_path)
            print(f"  Harvesting session report: {filename}...")
            package.append(f"\n### 📝 SESSION EXECUTIVE REPORT: {filename}")
            package.append(f"*   **Path:** `{report_path}`")
            package.append("\n```markdown")
            try:
                with open(report_path, "r", encoding="utf-8", errors="ignore") as rf:
                    package.append(rf.read().strip())
            except Exception as re:
                package.append(f"Error reading report: {re}")
            package.append("```\n" + "="*40 + "\n")
    except Exception as e:
        package.append(f"❌ Failed to harvest session reports: {e}")

    # 7. HISTORICAL SDLC TECHNICAL WALKTHROUGHS
    print("Harvesting SDLC technical walkthroughs...")
    package.append("---")
    package.append("## 🛠️ SECTION 7: SDLC TECHNICAL IMPLEMENTATION WALKTHROUGHS")
    package.append("Detailed walkthrough files documenting implemented architectures, DB migrations, and operational changes.")

    try:
        walkthroughs = []
        for r, _, fs in os.walk("/home/james/sovereign_inbox"):
            if "pilot_drops" in r.split(os.sep):
                continue
            for f in fs:
                if f.startswith("walkthrough_") and f.endswith(".md"):
                    walkthroughs.append(os.path.join(r, f))
        
        walkthroughs.sort(key=os.path.basename, reverse=True)
        
        for wt_path in walkthroughs[:100]:
            filename = os.path.basename(wt_path)
            print(f"  Harvesting walkthrough: {filename}...")
            package.append(f"\n### 🔧 SDLC WALKTHROUGH: {filename}")
            package.append(f"*   **Path:** `{wt_path}`")
            package.append("\n```markdown")
            try:
                with open(wt_path, "r", encoding="utf-8", errors="ignore") as wtf:
                    package.append(wtf.read().strip())
            except Exception as we:
                package.append(f"Error reading walkthrough: {we}")
            package.append("```\n" + "="*40 + "\n")
    except Exception as e:
        package.append(f"❌ Failed to harvest walkthroughs: {e}")

    # Write out the massive package
    print(f"Writing monolithic document to: {OUTPUT_PATH}...")
    try:
        monolith_content = "\n".join(package)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
            out.write(monolith_content)
        file_size_kb = os.path.getsize(OUTPUT_PATH) / 1024
        print(f"✅ ULTRAPREMIUM NotebookLM Package written successfully! Size: {file_size_kb:.2f} KB")
        
        # Write out split parts of at most 450,000 characters to prevent NotebookLM limit issues
        chunk_size_limit = 450000
        out_dir = os.path.dirname(OUTPUT_PATH)
        
        # Remove any existing parts first
        for old_part in glob.glob(os.path.join(out_dir, "SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE_PART_*.txt")):
            try:
                os.remove(old_part)
            except Exception:
                pass
                
        # Split content by lines, keeping track of current chunk characters
        chunks = []
        current_chunk = []
        current_len = 0
        
        for line in monolith_content.splitlines():
            line_len = len(line) + 1 # +1 for newline character
            if current_len + line_len > chunk_size_limit and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len
                
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        # Write out chunks
        for i, chunk_content in enumerate(chunks, 1):
            part_path = os.path.join(out_dir, f"SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE_PART_{i}.txt")
            with open(part_path, "w", encoding="utf-8") as pf:
                pf.write(chunk_content)
            print(f"✅ Chunk {i} written to {part_path} (characters: {len(chunk_content)})")
            
    except Exception as e:
        print(f"❌ Failed to write transfer packages: {e}")

if __name__ == "__main__":
    compile_payload()
