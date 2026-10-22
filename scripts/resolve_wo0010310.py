#!/usr/bin/env python3
"""
WO0010310 Auto-Resolution Script
Path: /home/james/stacklabs/scripts/resolve_wo0010310.py
"""

import os
import sys
import shutil
import hashlib
import uuid
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))
if str(SOVEREIGN_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT / "scripts"))

from core.db import get_db

TICKET_ID = "WO0010310"
TICKET_TITLE = "WO0010310: DAVINCIS PIZZABOT EDGE SENTINEL"
SLUG = "DAVINCIS-PIZZABOT-EDGE-SENTINEL"
CMDB_CI = "scripts/edge_dispatch_sentinel.py"

def resolve():
    print(f"🚀 [AUTO-RESOLUTION] Resolving ticket {TICKET_ID}...")

    proc_file = Path(f"/home/james/sovereign_inbox/queue/processing/{TICKET_ID}-{SLUG}.md")
    inc_file = Path(f"/home/james/sovereign_inbox/queue/incoming/{TICKET_ID}-{SLUG}.md")
    arc_file = Path(f"/home/james/sovereign_inbox/queue/archive/{TICKET_ID}-{SLUG}.md")

    src_file = None
    if proc_file.exists():
        src_file = proc_file
    elif inc_file.exists():
        src_file = inc_file
    elif arc_file.exists():
        src_file = arc_file

    full_markdown = ""
    if src_file and src_file.exists():
        full_markdown = src_file.read_text(encoding="utf-8")
        print(f"  Loaded source markdown from {src_file} ({len(full_markdown)} bytes)")

    # 1. Update sovereign_tickets directly via core.db
    print("  Applying database resolution and attachment records...")
    t_sys_id = None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (TICKET_ID, TICKET_ID))
        row = cursor.fetchone()
        t_sys_id = row[0] if row else None

        work_notes = (
            "WO0010310 RESOLVED: DaVinci's Smyrna Edge Dispatch Sentinel Pipeline & Swarm Genesis.\n\n"
            "1. Swarm Persona Seeding:\n"
            "   - Seeded 6 personas into persona_truths and persona under domain 'DAVINCIS_SMYRNA':\n"
            "     @barb_baker, @deck_baker_550, @debt_spiral_jason, @south_cobb_courier, @cumberland_corporate, @saas_fleece_vest.\n"
            "   - Verified via GET /api/persona_truths?domain=DAVINCIS_SMYRNA.\n\n"
            "2. Edge Dispatch Sentinel Service (Port 8099):\n"
            "   - Implemented scripts/edge_dispatch_sentinel.py with full REST API and dark-mode KDS HUD.\n"
            "   - Managed via user systemd service davincis-sentinel.service (Active: running).\n"
            "   - 80mm ESC/POS thermal receipt formatting verified for Baker's Pride deck rails.\n\n"
            "3. Power Tool #44 Registration:\n"
            "   - Added Tool #44 specification into Sovereign_Power_Tools_and_Microservices_Catalog.md.\n\n"
            "4. End-to-End Simulation:\n"
            "   - Ingested ORD-SMYRNA-001 (Jersey Devil & Wings, $60.50) -> Advanced to IN_OVEN.\n"
            "   - Ingested ORD-SMYRNA-002 (Cumberland Catering Ziti Drop, $820.00) -> Advanced to IN_OVEN.\n"
            "   - Proof-of-Bake SHA-256 hashes generated and persisted in SQLite WAL.\n\n"
            "5. Pegasus Playwright Visual Twin:\n"
            "   - Captured at 1920x1080: /home/james/stacklabs/pegasus_visual_twin_WO0010310_pizzabot_sentinel.png.\n"
            "   - KI-095 Viewport Compliance PASSED with 0 scrollbars and 0 errors."
        )

        if t_sys_id:
            cursor.execute("""
                UPDATE sovereign_tickets
                SET short_description = ?, description = ?, state = 3, priority = 1, type = 'STRY', 
                    assigned_to = 'clio', cmdb_ci = ?, work_notes = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (TICKET_TITLE, full_markdown, CMDB_CI, work_notes, t_sys_id))
            print(f"✔ sovereign_tickets record updated ({t_sys_id}).")
        else:
            t_sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO sovereign_tickets (
                    sys_id, number, short_description, description, state, priority, type,
                    assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
                ) VALUES (?, ?, ?, ?, 3, 1, 'STRY', 'clio', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_sys_id, TICKET_ID, TICKET_TITLE, full_markdown, CMDB_CI, work_notes))
            print(f"✔ sovereign_tickets record inserted ({t_sys_id}).")

        # Update sys_sdlc_task
        cursor.execute("""
            INSERT INTO sys_sdlc_task (task_id, task_type, state, module_target, short_description)
            VALUES (?, 'story', 'RESOLVED', ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                state = 'RESOLVED',
                short_description = excluded.short_description
        """, (TICKET_ID, CMDB_CI, TICKET_TITLE))

        # Update sys_number for category 'WO'
        cursor.execute("UPDATE sys_number SET current_number = 10310, sys_updated_on = CURRENT_TIMESTAMP WHERE category = 'WO'")
        print("✔ sys_number updated to 10310 for category 'WO'.")

        # Attachment: Work Order Markdown
        fn = f"{TICKET_ID}-{SLUG}.md"
        f_size = len(full_markdown.encode('utf-8'))
        md5_h = hashlib.md5(full_markdown.encode('utf-8')).hexdigest()
        dest_archive_path = f"/home/james/sovereign_inbox/queue/archive/{fn}"

        cursor.execute("SELECT sys_id FROM sys_attachment WHERE table_sys_id = ? AND file_name = ?", (t_sys_id, fn))
        att_row = cursor.fetchone()
        if att_row:
            cursor.execute("""
                UPDATE sys_attachment
                SET file_path = ?, file_size = ?, md5_hash = ?, sys_updated_on = CURRENT_TIMESTAMP
                WHERE sys_id = ?
            """, (dest_archive_path, f_size, md5_h, att_row[0]))
        else:
            att_sys_id = uuid.uuid4().hex
            cursor.execute("""
                INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, file_size, md5_hash, sys_created_on, sys_updated_on)
                VALUES (?, 'sovereign_tickets', ?, ?, 'text/markdown', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (att_sys_id, t_sys_id, fn, dest_archive_path, f_size, md5_h))

        # Attachment: Visual Twin
        twin_path = "/home/james/stacklabs/pegasus_visual_twin_WO0010310_pizzabot_sentinel.png"
        if os.path.exists(twin_path):
            twin_fn = "pegasus_visual_twin_WO0010310_pizzabot_sentinel.png"
            twin_size = os.path.getsize(twin_path)
            with open(twin_path, "rb") as tf:
                twin_md5 = hashlib.md5(tf.read()).hexdigest()

            cursor.execute("SELECT sys_id FROM sys_attachment WHERE table_sys_id = ? AND file_name = ?", (t_sys_id, twin_fn))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, file_size, md5_hash, sys_created_on, sys_updated_on)
                    VALUES (?, 'sovereign_tickets', ?, ?, 'image/png', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (uuid.uuid4().hex, t_sys_id, twin_fn, twin_path, twin_size, twin_md5))
                print(f"✔ Visual twin registered in sys_attachment.")

        # Attachment: Walkthrough
        walk_path = f"/home/james/sovereign_inbox/walkthroughs/walkthrough_{TICKET_ID}.md"
        if os.path.exists(walk_path):
            walk_fn = f"walkthrough_{TICKET_ID}.md"
            walk_size = os.path.getsize(walk_path)
            with open(walk_path, "rb") as wf:
                walk_md5 = hashlib.md5(wf.read()).hexdigest()

            cursor.execute("SELECT sys_id FROM sys_attachment WHERE table_sys_id = ? AND file_name = ?", (t_sys_id, walk_fn))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, file_size, md5_hash, sys_created_on, sys_updated_on)
                    VALUES (?, 'sovereign_tickets', ?, ?, 'text/markdown', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (uuid.uuid4().hex, t_sys_id, walk_fn, walk_path, walk_size, walk_md5))
                print(f"✔ Walkthrough registered in sys_attachment.")

        conn.commit()

    # Move work order to archive
    if src_file and src_file.exists() and src_file != arc_file:
        arc_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_file), str(arc_file))
        print(f"✔ Work order moved to archive: {arc_file}")

    print(f"\n🎉 [COMPLETE] Ticket {TICKET_ID} successfully resolved!")

if __name__ == "__main__":
    resolve()
