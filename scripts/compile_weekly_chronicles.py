#!/usr/bin/env python3
"""
Sovereign OS: Weekly Epoch Chronicles & Dynamic Kortex In-Place Sync Compiler
Governed by: WO0010167-COMPILE-WEEKLY-CHRONICLES-AND-STREAMLINE-NOTEBOOKLM-SOURCES
Target: /home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/

1. Scans:
   - /home/james/stacklabs/dna/archives/sessions/SESSION_REPORT_*.md
   - /home/james/stacklabs_inbox/today/SESSION_REPORT_*.md
   - /home/james/stacklabs_inbox/daily_*/SESSION_REPORT_*.md
   - /home/james/stacklabs_inbox/walkthroughs/walkthrough_*.md (and archive/)
2. Groups files by ISO calendar week (YYYY_Www).
3. Writes:
   - Historical weeks: SESSION_CHRONICLE_YYYY_Www.md and WALKTHROUGHS_YYYY_Www.md
   - Active week: SESSION_CHRONICLE_CURRENT_WEEK.md and WALKTHROUGHS_CURRENT_WEEK.md
4. Copies master payloads (Codebase parts 1-8, DB parts 1-7, DNA, Whitepapers).
5. Generates 00_EPOCH_INGESTION_MANIFEST.txt explaining high-density ~45 source structure.
"""

import os
import sys
import glob
import re
import shutil
from datetime import datetime, timezone

# Ensure SovereignOS scripts are in sys.path
BASE_DIR = "/home/james/stacklabs"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from scripts.core import api_client
except ImportError:
    api_client = None

INBOX_DIR = "/home/james/stacklabs_inbox"
TARGET_NOTEBOOK_DIR = os.path.join(INBOX_DIR, "notebook_sync", "StackLabs_Internal")
EPOCH_DIR = os.path.join(TARGET_NOTEBOOK_DIR, "epoch_sources")

PAYLOAD_EXPORT_DIR = os.path.join(BASE_DIR, "dna", "notebook_lm_exports")
DNA_FILE = os.path.join(BASE_DIR, "dna", "SOVEREIGN_DNA.md")
DOCS_DIR = os.path.join(BASE_DIR, "dna", "docs")

DATE_YMD_REGEX = re.compile(r'(202[4-9])-?(\d{2})-?(\d{2})')
DATE_MDY_REGEX = re.compile(r'(\d{2})(\d{2})(202[4-9])')
DATE_CONTENT_REGEX = re.compile(r'\b(202[4-9])[-_\.](\d{2})[-_\.](\d{2})\b')

def parse_date_from_file(filepath, ticket_map=None):
    """Robustly extract creation/event date from filename, ticket metadata, content, or mtime."""
    fname = os.path.basename(filepath)

    # 1. Ticket metadata for walkthroughs
    if ticket_map and fname.startswith("walkthrough_") and fname.endswith(".md"):
        ticket_id = fname[len("walkthrough_"):-len(".md")].strip()
        if ticket_id in ticket_map:
            t = ticket_map[ticket_id]
            t_date = t.get("updated_at") or t.get("created_at")
            if t_date:
                try:
                    return datetime.fromisoformat(t_date.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

    # 2. Filename YYYY-MM-DD or YYYYMMDD
    m = DATE_YMD_REGEX.search(fname)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass

    # 3. Filename MMDDYYYY e.g. 06062026
    m = DATE_MDY_REGEX.search(fname)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except Exception:
            pass

    # 4. Content header scan
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            head = "".join([f.readline() for _ in range(50)])
            m = DATE_CONTENT_REGEX.search(head)
            if m:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        pass

    # 5. File modification timestamp
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath))
    except Exception:
        return datetime.now()

def slugify(text):
    clean = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', clean)

def extract_session_summary(content, filename):
    m = re.search(r'##\s*What Actually Shipped\s*\n+1\.\s*\*?\*?([^\n\*]+)\*?\*?', content, re.IGNORECASE)
    if m:
        return m.group(1).strip(' :.-')
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return filename

def extract_walkthrough_info(content, filename):
    ticket_id = filename[len("walkthrough_"):-len(".md")].strip() if (filename.startswith("walkthrough_") and filename.endswith(".md")) else filename
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = m.group(1).strip() if m else f"Walkthrough {ticket_id}"
    m2 = re.search(r'##\s*🎯?\s*(?:Executive )?Summary\s*\n+([^\n#]+)', content, re.IGNORECASE)
    summary = m2.group(1).strip() if m2 else ""
    return ticket_id, title, summary

def main():
    print("=" * 80)
    print("🏛️ SOVEREIGN OS: COMPILING WEEKLY EPOCH CHRONICLES & DYNAMIC KORTEX SOURCES")
    print(f"Target Staging: {EPOCH_DIR}")
    print("=" * 80)

    os.makedirs(EPOCH_DIR, exist_ok=True)

    # 1. Fetch ticket map from FastAPI if reachable
    ticket_map = {}
    if api_client:
        try:
            tickets = api_client.get_tickets()
            for t in tickets:
                tid = t.get("id") or t.get("number")
                if tid:
                    ticket_map[tid] = t
            print(f"✔ Retrieved {len(ticket_map)} tickets from SDLC API for metadata enrichment.")
        except Exception as e:
            print(f"⚠️ Could not retrieve tickets from API ({e}), proceeding with file telemetry.")

    now = datetime.now()
    curr_year, curr_week, _ = now.isocalendar()
    current_week_key = f"{curr_year}_W{curr_week:02d}"
    print(f"Current Active ISO Calendar Week: {current_week_key}")

    # 2. Collect session reports
    session_paths = (
        glob.glob(os.path.join(BASE_DIR, "dna", "archives", "sessions", "SESSION_REPORT_*.md")) +
        glob.glob(os.path.join(INBOX_DIR, "today", "SESSION_REPORT_*.md")) +
        glob.glob(os.path.join(INBOX_DIR, "daily_*", "SESSION_REPORT_*.md"))
    )

    # Deduplicate session reports by filename, keeping latest mtime
    session_file_map = {}
    for p in session_paths:
        fname = os.path.basename(p)
        if fname not in session_file_map or os.path.getmtime(p) > os.path.getmtime(session_file_map[fname]):
            session_file_map[fname] = p

    print(f"✔ Scanned {len(session_paths)} session reports (deduplicated to {len(session_file_map)} unique files).")

    session_weeks = {}
    for fname, path in session_file_map.items():
        dt = parse_date_from_file(path)
        y, w, _ = dt.isocalendar()
        week_key = f"{y}_W{w:02d}"
        session_weeks.setdefault(week_key, []).append((dt, fname, path))

    # 3. Collect walkthroughs
    walkthrough_paths = (
        glob.glob(os.path.join(INBOX_DIR, "walkthroughs", "walkthrough_*.md")) +
        glob.glob(os.path.join(INBOX_DIR, "walkthroughs", "archive", "walkthrough_*.md"))
    )
    walkthrough_file_map = {}
    for p in walkthrough_paths:
        fname = os.path.basename(p)
        if fname not in walkthrough_file_map or os.path.getmtime(p) > os.path.getmtime(walkthrough_file_map[fname]):
            walkthrough_file_map[fname] = p

    print(f"✔ Scanned {len(walkthrough_paths)} walkthrough files (deduplicated to {len(walkthrough_file_map)} unique files).")

    walkthrough_weeks = {}
    for fname, path in walkthrough_file_map.items():
        dt = parse_date_from_file(path, ticket_map=ticket_map)
        y, w, _ = dt.isocalendar()
        week_key = f"{y}_W{w:02d}"
        walkthrough_weeks.setdefault(week_key, []).append((dt, fname, path))

    # 4. Generate Session Chronicles
    all_weeks = sorted(set(list(session_weeks.keys()) + list(walkthrough_weeks.keys())))
    print(f"Generating Chronicles across {len(all_weeks)} calendar epochs...")

    for week_key in all_weeks:
        reports = session_weeks.get(week_key, [])
        if not reports and week_key != current_week_key:
            continue

        # Sort reports chronologically
        reports.sort(key=lambda x: (x[0], x[1]))

        is_current = (week_key == current_week_key)
        out_fname = "SESSION_CHRONICLE_CURRENT_WEEK.md" if is_current else f"SESSION_CHRONICLE_{week_key}.md"
        out_path = os.path.join(EPOCH_DIR, out_fname)

        min_date_str = reports[0][0].strftime("%Y-%m-%d") if reports else "N/A"
        max_date_str = reports[-1][0].strftime("%Y-%m-%d") if reports else "N/A"
        latest_report_dt = reports[-1][0].strftime("%Y-%m-%d %H:%M:%S") if reports else now.strftime("%Y-%m-%d")

        lines = []
        if is_current:
            lines.append(f"# 🏛️ Sovereign OS: Session Chronicle — Week {week_key} (Current Active Week)")
            lines.append("> **Dynamic Kortex In-Place Sync Source**: Add this file once to NotebookLM.")
            lines.append("> When new daily sessions complete, click **Sync** in the Kortex browser extension to update in place.")
        else:
            lines.append(f"# 🏛️ Sovereign OS: Session Chronicle — Week {week_key} (Sealed Historical Epoch)")
            lines.append(f"> **Status**: Sealed Immutable Historical Epoch ({week_key}).")

        lines.append("")
        lines.append(f"- **Epoch Identifier:** `{week_key}`")
        if is_current:
            lines.append(f"- **Last Updated:** `{latest_report_dt}`")
        lines.append(f"- **Total Session Reports:** `{len(reports)}`")
        lines.append(f"- **Date Range:** `{min_date_str}` to `{max_date_str}`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📑 Table of Contents")
        lines.append("")

        report_entries = []
        for dt, fname, rpath in reports:
            try:
                with open(rpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
            except Exception as e:
                content = f"Error reading report: {e}"

            summary = extract_session_summary(content, fname)
            anchor = slugify(f"{fname}")
            report_entries.append((dt, fname, anchor, summary, content))
            lines.append(f"- [{fname}](#{anchor}) — *{summary}*")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📜 Compiled Session Reports")
        lines.append("")

        for dt, fname, anchor, summary, content in report_entries:
            lines.append(f'<a id="{anchor}"></a>')
            lines.append(f"### {fname} — {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"**Highlight:** {summary}")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        new_content = "\n".join(lines)
        if not os.path.exists(out_path) or open(out_path, "r", encoding="utf-8", errors="ignore").read() != new_content:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  ✔ Written: {out_fname} ({len(reports)} reports, {os.path.getsize(out_path):,} bytes)")
        else:
            pass

    # 5. Generate Walkthrough Chronicles
    for week_key in all_weeks:
        w_items = walkthrough_weeks.get(week_key, [])
        if not w_items and week_key != current_week_key:
            continue

        w_items.sort(key=lambda x: (x[0], x[1]))

        is_current = (week_key == current_week_key)
        out_fname = "WALKTHROUGHS_CURRENT_WEEK.md" if is_current else f"WALKTHROUGHS_{week_key}.md"
        out_path = os.path.join(EPOCH_DIR, out_fname)

        latest_w_dt = w_items[-1][0].strftime("%Y-%m-%d %H:%M:%S") if w_items else now.strftime("%Y-%m-%d")

        lines = []
        if is_current:
            lines.append(f"# 🏆 Sovereign OS: Ticket Walkthroughs & Closures — Week {week_key} (Current Active Week)")
            lines.append("> **Dynamic Kortex In-Place Sync Source**: Add this file once to NotebookLM.")
            lines.append("> When new tickets close, click **Sync** in the Kortex browser extension to update in place.")
        else:
            lines.append(f"# 🏆 Sovereign OS: Ticket Walkthroughs & Closures — Week {week_key} (Sealed Historical Epoch)")
            lines.append(f"> **Status**: Sealed Immutable Historical Epoch ({week_key}).")

        lines.append("")
        lines.append(f"- **Epoch Identifier:** `{week_key}`")
        if is_current:
            lines.append(f"- **Last Updated:** `{latest_w_dt}`")
        lines.append(f"- **Total Closed Walkthroughs:** `{len(w_items)}`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📑 Table of Contents")
        lines.append("")

        w_entries = []
        for dt, fname, wpath in w_items:
            try:
                with open(wpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
            except Exception as e:
                content = f"Error reading walkthrough: {e}"

            ticket_id, title, summary = extract_walkthrough_info(content, fname)
            anchor = slugify(f"{fname}")
            w_entries.append((dt, fname, ticket_id, title, summary, anchor, content))
            desc = f" — {summary}" if summary else ""
            lines.append(f"- [{ticket_id}: {title}](#{anchor}){desc}")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📜 Compiled Ticket Walkthroughs & Implementation Artifacts")
        lines.append("")

        for dt, fname, ticket_id, title, summary, anchor, content in w_entries:
            lines.append(f'<a id="{anchor}"></a>')
            lines.append(f"### {ticket_id}: {title}")
            lines.append(f"- **File:** `{fname}`")
            lines.append(f"- **Resolved / Recorded:** `{dt.strftime('%Y-%m-%d %H:%M:%S')}`")
            if summary:
                lines.append(f"- **Summary:** {summary}")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        new_content = "\n".join(lines)
        if not os.path.exists(out_path) or open(out_path, "r", encoding="utf-8", errors="ignore").read() != new_content:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  ✔ Written: {out_fname} ({len(w_items)} walkthroughs, {os.path.getsize(out_path):,} bytes)")
        else:
            pass

    # 6. Copy core master payloads into epoch_sources/
    print("Copying core master payloads into epoch_sources/...")

    def stage_file(src, dst_path, name):
        if not os.path.exists(src):
            print(f"  ⚠️ Missing: {name}")
            return False
        if os.path.exists(dst_path):
            try:
                if os.path.getsize(src) == os.path.getsize(dst_path) and int(os.path.getmtime(src)) <= int(os.path.getmtime(dst_path)):
                    return True
            except Exception:
                pass
        shutil.copy2(src, dst_path)
        print(f"  ✔ Staged: {name} ({os.path.getsize(src):,} bytes)")
        return True

    # 6.1 Codebase Parts 1-8
    for i in range(1, 9):
        target_name = f"SOVEREIGN_CODEBASE_PART_{i}.md"
        src = os.path.join(PAYLOAD_EXPORT_DIR, target_name)
        if not os.path.exists(src):
            src = os.path.join(TARGET_NOTEBOOK_DIR, target_name)
        stage_file(src, os.path.join(EPOCH_DIR, target_name), target_name)

    # 6.2 Massive DB Transfer Packages 1-7
    for i in range(1, 8):
        target_name = f"SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE_PART_{i}.txt"
        src = os.path.join(PAYLOAD_EXPORT_DIR, target_name)
        if not os.path.exists(src):
            src = os.path.join(TARGET_NOTEBOOK_DIR, target_name)
        stage_file(src, os.path.join(EPOCH_DIR, target_name), target_name)

    # 6.3 Constitutional & Core Specs
    core_docs = [
        ("SOVEREIGN_DNA.md", DNA_FILE),
        ("Sovereign_Power_Tools_and_Microservices_Catalog.md", os.path.join(DOCS_DIR, "Sovereign_Power_Tools_and_Microservices_Catalog.md")),
        ("SOVEREIGN_AMBIENT_EDGE_APPLIANCE_WHITEPAPER.md", os.path.join(DOCS_DIR, "SOVEREIGN_AMBIENT_EDGE_APPLIANCE_WHITEPAPER.md")),
        ("SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.md", os.path.join(DOCS_DIR, "SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.md")),
    ]

    for dest_name, src_path in core_docs:
        if os.path.exists(src_path):
            stage_file(src_path, os.path.join(EPOCH_DIR, dest_name), dest_name)
        else:
            alt = os.path.join(TARGET_NOTEBOOK_DIR, dest_name)
            stage_file(alt, os.path.join(EPOCH_DIR, dest_name), dest_name)

    # 7. Generate 00_EPOCH_INGESTION_MANIFEST.txt
    print("Generating 00_EPOCH_INGESTION_MANIFEST.txt...")
    epoch_files = sorted(os.listdir(EPOCH_DIR))
    source_files = [f for f in epoch_files if f != "00_EPOCH_INGESTION_MANIFEST.txt"]

    active_sources = [f for f in source_files if "CURRENT_WEEK" in f]
    codebase_sources = [f for f in source_files if f.startswith("SOVEREIGN_CODEBASE_PART_")]
    db_sources = [f for f in source_files if f.startswith("SOVEREIGN_OS_INTERNAL_MASSIVE_DATA_TRANSFER_PACKAGE_PART_")]
    foundation_sources = [f for f in source_files if f in ["SOVEREIGN_DNA.md", "Sovereign_Power_Tools_and_Microservices_Catalog.md", "SOVEREIGN_AMBIENT_EDGE_APPLIANCE_WHITEPAPER.md", "SOVEREIGN_KNOT_ARCHITECTURE_WHITE_PAPER.md"]]
    historical_sources = [f for f in source_files if f not in active_sources and f not in codebase_sources and f not in db_sources and f not in foundation_sources]

    manifest_lines = [
        "=" * 80,
        "STACKLABS LLC: NOTEBOOKLM EPOCH MASTER INGESTION MANIFEST",
        f"Date: {now.strftime('%Y-%m-%d')}",
        "Generated By: Sovereign Epoch Compilation Engine (scripts/compile_weekly_chronicles.py)",
        f"Target Local Staging: {EPOCH_DIR}",
        "Target Remote GDrive: stacklabs_edge:StackLabs_Internal/epoch_sources/",
        "Target Notebook: https://notebooklm.google.com/notebook/30ab3645-0681-45ed-9214-3f538c02c21c",
        "=" * 80,
        "",
        "HIGH-DENSITY KORTEX ARCHITECTURE OVERVIEW:",
        "NotebookLM caps every notebook at 500 sources, but allows up to 500,000 words per source.",
        "Instead of maintaining over 1,700 fragmented daily files that exhaust source limits,",
        "the Sovereign OS Epoch Engine consolidates all operational history into dense weekly chronicles.",
        f"Total sources in this epoch package: {len(source_files)} (well under the 500-source limit).",
        "",
        "DYNAMIC KORTEX IN-PLACE SYNC WORKFLOW (FOR THE PILOT):",
        "1. In NotebookLM, add the two rolling active files ONCE:",
        "   - SESSION_CHRONICLE_CURRENT_WEEK.md",
        "   - WALKTHROUGHS_CURRENT_WEEK.md",
        "2. As daily sessions and ticket closures occur, changes append to these active files",
        "   and automatically push to Google Drive during sync runs.",
        "3. In NotebookLM, simply click 'Sync' via the Kortex browser extension to update",
        "   the sources in place with zero file-picker friction.",
        "4. At the end of each ISO week, the active chronicles seal into historical records",
        "   (SESSION_CHRONICLE_YYYY_Www.md and WALKTHROUGHS_YYYY_Www.md), and a new rolling",
        "   CURRENT_WEEK chronicle begins.",
        "",
        "-" * 80,
        f"SOURCE INVENTORY ({len(source_files)} TOTAL SOURCES):",
        "-" * 80,
        "",
        f"1. ROLLING ACTIVE WEEK CHRONICLES ({len(active_sources)} SOURCES - SYNC IN-PLACE VIA KORTEX):",
    ]
    for s in active_sources:
        sz = os.path.getsize(os.path.join(EPOCH_DIR, s))
        manifest_lines.append(f"   * {s:<36} ({sz:>10,} bytes)")

    manifest_lines.append("")
    manifest_lines.append(f"2. SOVEREIGN CODEBASE MASTER PAYLOADS ({len(codebase_sources)} SOURCES):")
    for s in codebase_sources:
        sz = os.path.getsize(os.path.join(EPOCH_DIR, s))
        manifest_lines.append(f"   * {s:<36} ({sz:>10,} bytes)")

    manifest_lines.append("")
    manifest_lines.append(f"3. SOVEREIGN MASSIVE DATABASE TRANSFER PACKAGES ({len(db_sources)} SOURCES):")
    for s in db_sources:
        sz = os.path.getsize(os.path.join(EPOCH_DIR, s))
        manifest_lines.append(f"   * {s:<36} ({sz:>10,} bytes)")

    manifest_lines.append("")
    manifest_lines.append(f"4. SOVEREIGN CONSTITUTIONAL & TECHNICAL FOUNDATIONS ({len(foundation_sources)} SOURCES):")
    for s in foundation_sources:
        sz = os.path.getsize(os.path.join(EPOCH_DIR, s))
        manifest_lines.append(f"   * {s:<36} ({sz:>10,} bytes)")

    manifest_lines.append("")
    manifest_lines.append(f"5. SEALED HISTORICAL EPOCH CHRONICLES ({len(historical_sources)} SOURCES):")
    for s in historical_sources:
        sz = os.path.getsize(os.path.join(EPOCH_DIR, s))
        manifest_lines.append(f"   * {s:<36} ({sz:>10,} bytes)")

    manifest_lines.append("")
    manifest_lines.append("=" * 80)
    manifest_lines.append("END OF MANIFEST")
    manifest_lines.append("=" * 80)

    manifest_path = os.path.join(EPOCH_DIR, "00_EPOCH_INGESTION_MANIFEST.txt")
    manifest_text = "\n".join(manifest_lines) + "\n"
    if not os.path.exists(manifest_path) or open(manifest_path, "r", encoding="utf-8", errors="ignore").read() != manifest_text:
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_text)
        print(f"✔ Written: 00_EPOCH_INGESTION_MANIFEST.txt ({len(source_files)} sources cataloged).")
    else:
        pass
    print(f"🟢 Epoch sources compilation complete. Total sources in staging: {len(source_files) + 1}")

if __name__ == "__main__":
    main()
