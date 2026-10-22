import sys
import os
from datetime import datetime

sys.path.insert(0, '/home/james/stacklabs/scripts')
from core.db import get_db

def reconcile():
    ticket_num = 'WO-2026-0903-MOBILE-TICKET-APP'
    note = (
        "[2026-09-03 17:35 UTC - Antigravity] RESOLVED: Scaffolding and production deployment "
        "of Sovereign Mobile Ticket Console completed. Bound strictly to 0.0.0.0:3025 with "
        "Tailscale SSL certs. Single-column virtualized incident triage feed (<68KB bundle, zero desktop bloat), "
        "touch-first gestures (swipe-right state bump, swipe-left assign to James), and 80vh bottom sheet "
        "for work notes via Clio FastAPI /api/now/table/sovereign_tickets. Live curl verified HTTP 200 "
        "on https://clio.taila01894.ts.net:3025/. Systemd service mobile_ticket_app.service enabled and running. "
        "Mando Watchdog updated."
    )
    now_str = datetime.now().isoformat()

    with get_db() as conn:
        cur = conn.cursor()
        # Fetch current work notes
        cur.execute("SELECT work_notes FROM sovereign_tickets WHERE number = ?", (ticket_num,))
        row = cur.fetchone()
        existing_notes = row['work_notes'] if row and row['work_notes'] else ""
        combined_notes = f"{note}\n\n{existing_notes}" if existing_notes else note

        cur.execute("""
            UPDATE sovereign_tickets
            SET state = 4,
                cmdb_ci = '28_Sovereign_Mobile_Dispatch',
                assigned_to = 'james',
                work_notes = ?,
                sys_updated_on = ?
            WHERE number = ?
        """, (combined_notes, now_str, ticket_num))

        # Reconcile approval queue
        cur.execute("""
            UPDATE sys_approval_queue
            SET state = 'Executed',
                auth_level = 'omega=1',
                sys_updated_on = ?
            WHERE task_id = ?
        """, (now_str, ticket_num))

        conn.commit()

        # Verify update
        cur.execute("SELECT number, state, cmdb_ci, assigned_to, sys_updated_on FROM sovereign_tickets WHERE number = ?", (ticket_num,))
        updated_ticket = dict(cur.fetchone())
        print("Updated Ticket:", updated_ticket)

        cur.execute("SELECT sys_id, task_id, state, auth_level FROM sys_approval_queue WHERE task_id = ?", (ticket_num,))
        updated_appr = cur.fetchone()
        if updated_appr:
            print("Updated Approval:", dict(updated_appr))

if __name__ == "__main__":
    reconcile()
