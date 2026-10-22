-- ============================================================================
-- SOVEREIGN OS — SDLC UNIFICATION MIGRATION
-- Date: 2026-05-20
-- Author: Claude (Auditor on Contract)
-- Purpose: Collapse rm_story, rm_defect, rm_enhancement into one unified
--          sovereign_tickets table with type discrimination.
-- Safe to re-run. Does NOT touch CMDB, game, persona, or sam tables.
-- ============================================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: CREATE THE UNIFIED TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS sovereign_tickets (
    sys_id          TEXT PRIMARY KEY,
    number          TEXT UNIQUE NOT NULL,
    type            TEXT NOT NULL CHECK(type IN ('STRY', 'DFCT', 'ENHC', 'INC')),
    parent_sys_id   TEXT,                        -- NULL for STRY/INC; points to STRY for DFCT/ENHC
    short_description TEXT,
    description     TEXT,
    state           INTEGER DEFAULT 1,           -- 1=Open 2=In Progress 3=Testing 4=Resolved 5=Closed
    priority        INTEGER DEFAULT 3,           -- 1=Critical 2=High 3=Medium 4=Low
    assigned_to     TEXT,
    cmdb_ci         TEXT,
    work_notes      TEXT,
    sys_created_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sys_updated_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STEP 2: MIGRATE rm_story — STRY, DFCT, ENHC records only. Drop all INCs.
-- ============================================================================
INSERT OR IGNORE INTO sovereign_tickets (
    sys_id, number, type, parent_sys_id,
    short_description, description, state, priority,
    assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
)
SELECT
    sys_id,
    number,
    CASE
        WHEN number LIKE 'STRY%' THEN 'STRY'
        WHEN number LIKE 'DFCT%' THEN 'DFCT'
        WHEN number LIKE 'ENHC%' THEN 'ENHC'
    END as type,
    NULL as parent_sys_id,
    short_description,
    description,
    state,
    COALESCE(priority, 3),
    assigned_to,
    cmdb_ci,
    COALESCE(work_notes, ''),
    sys_created_on,
    COALESCE(sys_updated_on, sys_created_on)
FROM rm_story
WHERE number NOT LIKE 'INC%';

-- ============================================================================
-- STEP 3: MIGRATE rm_defect — any records NOT already in sovereign_tickets
-- (handles DFCT0000462 which only lived in rm_defect)
-- ============================================================================
INSERT OR IGNORE INTO sovereign_tickets (
    sys_id, number, type, parent_sys_id,
    short_description, description, state, priority,
    assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
)
SELECT
    sys_id,
    number,
    'DFCT' as type,
    NULL as parent_sys_id,
    short_description,
    description,
    state,
    COALESCE(priority, 3),
    assigned_to,
    cmdb_ci,
    '',
    sys_created_on,
    sys_created_on
FROM rm_defect
WHERE number NOT LIKE 'INC%';

-- ============================================================================
-- STEP 4: MIGRATE rm_enhancement — any records NOT already in sovereign_tickets
-- ============================================================================
INSERT OR IGNORE INTO sovereign_tickets (
    sys_id, number, type, parent_sys_id,
    short_description, description, state, priority,
    assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
)
SELECT
    sys_id,
    number,
    'ENHC' as type,
    NULL as parent_sys_id,
    short_description,
    description,
    state,
    COALESCE(priority, 3),
    assigned_to,
    cmdb_ci,
    '',
    sys_created_on,
    sys_created_on
FROM rm_enhancement;

-- ============================================================================
-- STEP 5: UPDATE sys_attachment to point to sovereign_tickets
-- ============================================================================
UPDATE sys_attachment
SET table_name = 'sovereign_tickets'
WHERE table_name IN ('rm_story', 'rm_defect', 'rm_enhancement');

-- ============================================================================
-- STEP 6: CLEAR the old tables (leave shells intact for portal backend compat)
-- ============================================================================
DELETE FROM rm_story;
DELETE FROM rm_defect;
DELETE FROM rm_enhancement;

-- ============================================================================
-- STEP 7: CREATE INDEXES for portal query performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_tickets_type    ON sovereign_tickets(type);
CREATE INDEX IF NOT EXISTS idx_tickets_state   ON sovereign_tickets(state);
CREATE INDEX IF NOT EXISTS idx_tickets_number  ON sovereign_tickets(number);
CREATE INDEX IF NOT EXISTS idx_tickets_parent  ON sovereign_tickets(parent_sys_id);

COMMIT;
PRAGMA foreign_keys = ON;

-- ============================================================================
-- VERIFICATION — Run these after migration to confirm row counts
-- ============================================================================
-- Expected: sovereign_tickets should contain your STRYs + DFCTs + ENHCs
-- Expected: rm_story, rm_defect, rm_enhancement should all be 0

SELECT '=== SOVEREIGN TICKETS BY TYPE ===' as check_name;
SELECT type, COUNT(*) as count FROM sovereign_tickets GROUP BY type ORDER BY type;

SELECT '=== TOTAL TICKETS ===' as check_name;
SELECT COUNT(*) as total FROM sovereign_tickets;

SELECT '=== OLD TABLES (should all be 0) ===' as check_name;
SELECT 'rm_story'      as tbl, COUNT(*) as remaining FROM rm_story
UNION ALL
SELECT 'rm_defect'     as tbl, COUNT(*) as remaining FROM rm_defect
UNION ALL
SELECT 'rm_enhancement' as tbl, COUNT(*) as remaining FROM rm_enhancement;

SELECT '=== ATTACHMENTS REMAPPED ===' as check_name;
SELECT table_name, COUNT(*) FROM sys_attachment GROUP BY table_name;

SELECT '=== OPEN & IN-PROGRESS TICKETS ===' as check_name;
SELECT number, type, short_description, state, assigned_to
FROM sovereign_tickets
WHERE state IN (1, 2, 3)
ORDER BY type, number;
