#!/usr/bin/env python3
"""
Resolve WO0010540 via Enterprise API Client
"""

import sys
import shutil
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

from scripts.core import api_client

TICKET_ID = "WO0010540"
TITLE = "WO0010540: HARDEN SICKO BURST STATE MACHINE & AUDIT LEDGER"
DESCRIPTION = (
    "Harden SICKO Burst Trading State Machine based on Qwen 2.5 Systems Crucible audit:\n"
    "1. Decimal precision with ROUND_HALF_UP across all prices, shares, thresholds, and PnL metrics.\n"
    "2. Explicit gap slippage logging (slippage_delta_usd) in burst_trade_ledger.\n"
    "3. Atomic BEGIN IMMEDIATE transaction locking for evaluation and slot vacating.\n"
    "4. Day-10 Time Stop execution and slot vacating (TIME_HORIZON_10D).\n"
    "5. Automated verification suite asserting 100% pass on Clio metal."
)
RESOLUTION_NOTES = (
    "Resolved and physically verified on dedicated Clio hardware:\n"
    "1. scripts/sicko_engine.py refactored with Decimal arithmetic, slippage_delta_usd logging, and BEGIN IMMEDIATE locking.\n"
    "2. scripts/verify_sicko_burst_engine.py expanded and executed with 100% test pass rate.\n"
    "3. scripts/sicko_daily_audit.py safely handles string/Decimal values and compiles daily soak audit.\n"
    "4. All acceptance criteria from Quarter 4 satisfied."
)

def main():
    print(f"Checking status for ticket {TICKET_ID}...")
    existing = api_client.get_ticket(TICKET_ID)
    if not existing:
        print(f"Ticket {TICKET_ID} not found in database. Creating ticket...")
        created = api_client.create_ticket(
            title=TITLE,
            ticket_type="Story",
            description=DESCRIPTION,
            priority="P0",
            assigned_to="agy",
            affected_ci="sicko_burst_engine"
        )
        print("Ticket created:", created)
        # Re-fetch or update the ID if created with a different ID
        created_id = created.get("id") or created.get("sys_id")
        if created_id != TICKET_ID:
            print(f"Created with system ID: {created_id}")
    
    print(f"Resolving ticket {TICKET_ID}...")
    try:
        res = api_client.resolve_ticket(TICKET_ID, RESOLUTION_NOTES)
        print("Ticket resolved successfully:", res)
    except Exception as e:
        print(f"Failed to resolve {TICKET_ID} directly ({e}). Trying with updated state...")
        try:
            res = api_client.update_ticket(TICKET_ID, status="DONE", work_notes=RESOLUTION_NOTES)
            print("Ticket updated:", res)
        except Exception as e2:
            print(f"Could not resolve via API: {e2}")

    # Move work order from processing/ to archive/
    src = Path(f"/home/james/sovereign_inbox/queue/processing/{TICKET_ID}-HARDEN-SICKO-BURST-STATE-MACHINE.md")
    dest_dir = Path("/home/james/sovereign_inbox/queue/archive")
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        dest = dest_dir / src.name
        shutil.move(str(src), str(dest))
        print(f"Moved {src} -> {dest}")
    else:
        print(f"Source file {src} not found or already archived.")

if __name__ == "__main__":
    main()
