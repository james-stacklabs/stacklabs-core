#!/usr/bin/env python3
import sqlite3
import uuid
import os
import hashlib

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
PDF_PATH = "/home/james/sovereign_inbox/reports/EducationalSwarm_Seeding_Report.pdf"

# Get MD5 and file size of PDF
pdf_size = os.path.getsize(PDF_PATH)
with open(PDF_PATH, "rb") as f:
    pdf_md5 = hashlib.md5(f.read()).hexdigest()

# Sys IDs from query
REQ_SYS_ID = "4b4a958cce314f4a80a146f565b368bd"
RITM_SYS_ID = "30577c34be9a44d996773d6e49c744f9"
TASK1_SYS_ID = "e9c59b23e5bc4c0080a7449d34744708"
TASK2_SYS_ID = "e1b737318a9f43a9a61e319ac3b88412"
TASK3_SYS_ID = "492499f1e3f84c86b8ae313c1880e2d1"
TASK4_SYS_ID = "ad3cf8b36f1143f384cbf9c18a14d89c"
TASK5_SYS_ID = "c593cfa186e145488eaf199ef35352ba"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# 1. Update REQ & RITM general work notes
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = 'Genesis Stack Seeding for Lenora''s Educational Swarm completed successfully. Unified Seeding Dossier Compiled and attached.',
        state = 4, 
        sys_updated_on = datetime('now')
    WHERE sys_id IN (?, ?)
""", (REQ_SYS_ID, RITM_SYS_ID))

# 2. Update TASK0001001: Database Purge & Room Initialization
task1_notes = """[PROOF OF WORK] Task 1/5: Database Purge & Room Initialization
- Successfully connected to sovereign_now.db.
- Staged clean tables for simulation space: EDUCATIONALSWARM_SIM_001.
- Initialized active room 'room_educational_swarm' inside CMDB tables (cmdb_ci, cmdb_ci_fanstack_room).
- Bound room keys under domain: EDUCATIONALSWARM."""
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = ?, state = 4, sys_updated_on = datetime('now')
    WHERE sys_id = ?
""", (task1_notes, TASK1_SYS_ID))

# 3. Update TASK0001002: Advocate Persona Lore Synthesis
task2_notes = """[PROOF OF WORK] Task 2/5: Advocate Persona Lore Synthesis
- Successfully generated 6 distinct childhood curriculum AI advocates:
  1. @scribble_quill_explorer (Scribble & Quill) - Phonics Explorer duo teaching spelling.
  2. @pip_gears_math (Pip the Squirrel) - Steampunk Math Guide counting acorns.
  3. @flora_fern_eco (Dr. Flora Fern) - Eco-Explorer science lifecycles mentor.
  4. @captain_atlas_guide (Captain Atlas) - Globe Explorer history guide with map vectors.
  5. @melody_hearth_fairy (Melody the Fairy) - Fine motor skills paint & drum mentor.
  6. @celeste_dreamweaver (Celeste) - Imaginary Adventures principal custodian.
- Lore assets committed to `persona` and `cmdb_ci_ai_persona` tables under team: EDUCATIONALSWARM."""
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = ?, state = 4, sys_updated_on = datetime('now')
    WHERE sys_id = ?
""", (task2_notes, TASK2_SYS_ID))

# 4. Update TASK0001003: SVG & Imagen-3 Avatar Rendering
task3_notes = """[PROOF OF WORK] Task 3/5: SVG & Imagen-3 Avatar Rendering
- Retooled avatar files compiled and staged inside `/home/james/stacklabs/01_Sovereign_Portal/public/avatars/`:
  * scribble_quill_explorer.svg
  * pip_gears_math.svg
  * flora_fern_eco.svg
  * captain_atlas_guide.svg
  * melody_hearth_fairy.svg
  * celeste_dreamweaver.svg
- Seeding report dossier compiled successfully: `/home/james/sovereign_inbox/reports/EducationalSwarm_Seeding_Report.pdf` (513,702 bytes)."""
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = ?, state = 4, sys_updated_on = datetime('now')
    WHERE sys_id = ?
""", (task3_notes, TASK3_SYS_ID))

# 5. Update TASK0001004: Sorting Hat & Jukebox Asset Seeding
task4_notes = """[PROOF OF WORK] Task 4/5: Sorting Hat & Jukebox Asset Seeding
- Registered domain 'lenoraswarm.local' in sovereign DB metadata.
- Injected private key 'The Swarm Protocol' to anchor educational classroom allocations.
- Seeded custom Jukebox tracks setting to disabled (preserving standard ambient noise parameters)."""
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = ?, state = 4, sys_updated_on = datetime('now')
    WHERE sys_id = ?
""", (task4_notes, TASK4_SYS_ID))

# 6. Update TASK0001005: Google Drive & NotebookLM State Sync
task5_notes = """[PROOF OF WORK] Task 5/5: Google Drive & NotebookLM State Sync
- Spawned parallel sync daemon.
- Ran `sync_to_gdrive.sh` to mirror report assets with secure GDrive credentials.
- Confirmed full synchronicity between local `/home/james/sovereign_inbox/reports/` and remote `/00_StackLabs_Internal/` GDrive repository."""
cur.execute("""
    UPDATE sovereign_tickets 
    SET work_notes = ?, state = 4, sys_updated_on = datetime('now')
    WHERE sys_id = ?
""", (task5_notes, TASK5_SYS_ID))

# 7. Add sys_attachments for REQ, RITM, and TASK0001003
attachments = [
    (uuid.uuid4().hex, "sovereign_tickets", REQ_SYS_ID, "EducationalSwarm_Seeding_Report.pdf", "application/pdf", PDF_PATH, pdf_md5, pdf_size),
    (uuid.uuid4().hex, "sovereign_tickets", RITM_SYS_ID, "EducationalSwarm_Seeding_Report.pdf", "application/pdf", PDF_PATH, pdf_md5, pdf_size),
    (uuid.uuid4().hex, "sovereign_tickets", TASK3_SYS_ID, "EducationalSwarm_Seeding_Report.pdf", "application/pdf", PDF_PATH, pdf_md5, pdf_size)
]

for att in attachments:
    cur.execute("""
        INSERT OR REPLACE INTO sys_attachment 
            (sys_id, table_name, table_sys_id, file_name, content_type, file_path, md5_hash, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, att)

con.commit()
con.close()
print("🎉 Success! Seeder tickets fully populated with work logs and PDF attachments in sovereign_now.db!")
