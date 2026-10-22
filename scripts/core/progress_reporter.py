"""
Sovereign OS: Autonomous Mid-Session Progress Reporter
Path: /home/james/stacklabs/scripts/core/progress_reporter.py

Generates structured, mid-flight progress reports during active sessions.
Adheres to the Pilot's ELI5 + Deep Technical format.
Dual-writes to `today/` and `dna/archives/progress/` and syncs to Cypher via GDrive.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from scripts.core import api_client

INBOX_PATH = "/home/james/sovereign_inbox"
DNA_PROGRESS_ARCHIVE = "/home/james/stacklabs/dna/archives/progress"

def generate_progress_report(
    session_title: str = "Active Sovereign Sprint",
    session_guid: str = "",
    in_flight: str = "",
    decisions_needed: str = "None currently. Sprint is on track.",
    next_steps: Optional[List[str]] = None,
    custom_highlights: Optional[List[Dict[str, str]]] = None,
    trigger_sync: bool = False
) -> str:
    """Generate and dual-write a structured progress report."""
    os.makedirs(DNA_PROGRESS_ARCHIVE, exist_ok=True)
    today_dir = os.path.realpath(os.path.join(INBOX_PATH, "today"))
    os.makedirs(today_dir, exist_ok=True)

    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    now_formatted = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Fetch recently resolved and open tickets from FastAPI
    try:
        all_tickets = api_client.get_tickets()
        resolved_recent = [t for t in all_tickets if t.get("status") in ("RESOLVED", "CLOSED")]
        open_tickets = [t for t in all_tickets if t.get("status") in ("PLANNING", "IN_PROGRESS", "OPEN")]
    except Exception as e:
        resolved_recent = []
        open_tickets = []

    report_lines = [
        f"# Sovereign OS — Mid-Session Progress Report",
        f"**Generated**: {now_formatted}",
        f"",
        f"## 📌 Session Context",
        f"- **Session Title**: {session_title}",
        f"- **Session GUID**: `{session_guid or 'Active-Sprint'}`",
        f"- **Sprint Status**: ACTIVE / IN-PROGRESS",
        f"",
        f"---",
        f"",
        f"## ⚡ Completed Deliverables & Milestones",
    ]

    if custom_highlights:
        for item in custom_highlights:
            report_lines.extend([
                f"### 🚀 {item.get('title', 'Deliverable')}",
                f"#### 🧒 ELI5 (Simple Analogy)",
                f"> {item.get('eli5', 'Feature shipped and operating cleanly.')}",
                f"",
                f"#### ⚙️ Deep Technical Reality",
                f"{item.get('technical', 'Implemented via standard FastAPI and React architecture.')}",
                f"",
                f"#### 💡 Why It Matters",
                f"{item.get('why', 'Improves system reliability and user capabilities.')}",
                f"",
                f"#### 🔮 How It Will Be Used Moving Forward",
                f"{item.get('forward', 'Available across all portals and autonomous schedulers.')}",
                f"",
            ])
    else:
        # Fallback to recent tickets
        for t in resolved_recent[:5]:
            report_lines.append(f"- **{t.get('number', 'TICKET')}**: {t.get('title')} (CI: `{t.get('affected_ci')}`)")

    report_lines.extend([
        f"---",
        f"",
        f"## 🔄 Currently In Flight",
        f"{in_flight or 'Autonomous sprint execution and architecture verification.'}",
        f"",
        f"## 📋 Active Ticket Queue",
    ])

    if open_tickets:
        for ot in open_tickets[:5]:
            report_lines.append(f"- `[{ot.get('number')}]` {ot.get('title')} (`{ot.get('status')}`)")
    else:
        report_lines.append("- *No open blocker tickets in queue.*")

    report_lines.extend([
        f"",
        f"## ❓ Decisions / Feedback Needed from Pilot",
        f"{decisions_needed}",
        f"",
        f"## 🎯 Immediate Next Steps",
    ])

    if next_steps:
        for idx, step in enumerate(next_steps, 1):
            report_lines.append(f"{idx}. {step}")
    else:
        report_lines.append("1. Continue active ticket execution and test validation.")

    report_content = "\n".join(report_lines) + "\n"

    # Dual-write
    today_file = os.path.join(today_dir, f"PROGRESS_REPORT_{timestamp_str}.md")
    dna_file = os.path.join(DNA_PROGRESS_ARCHIVE, f"PROGRESS_REPORT_{timestamp_str}.md")

    with open(today_file, "w") as f:
        f.write(report_content)
    with open(dna_file, "w") as f:
        f.write(report_content)

    print(f"✅ Progress Report dual-written to:")
    print(f"   - {today_file}")
    print(f"   - {dna_file}")

    if trigger_sync:
        print("🚀 Triggering background Google Drive & Cypher sync...")
        os.system("HISTFILE=/dev/null /home/james/stacklabs/scripts/sync_to_gdrive.sh >/dev/null 2>&1 &")

    return today_file

if __name__ == "__main__":
    generate_progress_report(
        session_title="Automated Progress Check",
        in_flight="Standardizing Progress Reports across Sovereign OS",
        trigger_sync=False
    )
