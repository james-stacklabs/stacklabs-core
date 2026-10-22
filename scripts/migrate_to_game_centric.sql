-- ============================================================
-- FanStack: Game-Centric Schema Migration
-- From: persona-centric CMDB mess
-- To:   game_pk anchor + related lists
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=OFF;

-- ── 1. PERSONA (flat, independent, portable) ─────────────────
CREATE TABLE IF NOT EXISTS persona (
    id            TEXT PRIMARY KEY,
    user_name     TEXT UNIQUE NOT NULL,
    display_name  TEXT,
    team          TEXT,           -- MLB abbrev: SD, SF, ATL, SEA, GLOBAL
    system_prompt TEXT,
    boggs_level   INTEGER DEFAULT 2,
    avatar_url    TEXT,
    color         TEXT,
    cadence       TEXT DEFAULT 'pacer',
    deep_lore     TEXT,
    behavior_notes TEXT,
    governance    TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- ── 2. EXTEND mlb_schedule (already exists) ─────────────────
-- Add room management columns if not present
ALTER TABLE mlb_schedule ADD COLUMN room_state TEXT DEFAULT 'staged';
ALTER TABLE mlb_schedule ADD COLUMN boggs_level INTEGER DEFAULT 2;
ALTER TABLE mlb_schedule ADD COLUMN sim_speed REAL DEFAULT 1.0;

-- ── 3. GAME_PERSONA (who showed up to watch) ─────────────────
CREATE TABLE IF NOT EXISTS game_persona (
    id            TEXT PRIMARY KEY,
    game_pk       TEXT NOT NULL,
    persona_id    TEXT NOT NULL,
    joined_at     TEXT DEFAULT (datetime('now')),
    overlay       TEXT,           -- per-game prompt injection
    seat_state    TEXT DEFAULT 'active'
                  -- active | benched | guest | 8mile | left
);
CREATE INDEX IF NOT EXISTS idx_game_persona_game ON game_persona(game_pk);
CREATE INDEX IF NOT EXISTS idx_game_persona_persona ON game_persona(persona_id);

-- ── 4. GAME_CONTEXT (ambient lore per game) ──────────────────
CREATE TABLE IF NOT EXISTS game_context (
    id            TEXT PRIMARY KEY,
    game_pk       TEXT NOT NULL,
    source        TEXT,           -- 'email','yardbarker','manual','mlb_promo'
    headline      TEXT,
    content       TEXT,
    tags          TEXT,           -- comma-separated: 'bobblehead,PED,rivalry'
    injected_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_game_context_game ON game_context(game_pk);

-- ── 5. GAME_PLAY (Statcast / live feed storage) ───────────────
CREATE TABLE IF NOT EXISTS game_play (
    id            TEXT PRIMARY KEY,
    game_pk       TEXT NOT NULL,
    play_id       TEXT,           -- MLB's own play identifier
    inning        INTEGER,
    half          TEXT,           -- 'top' | 'bottom'
    event_type    TEXT,           -- 'pitch','strikeout','home_run','walk','hit'
    batter        TEXT,
    pitcher       TEXT,
    pitch_speed   REAL,
    pitch_type    TEXT,           -- 'Sinker','Slider','Changeup','4-Seam Fastball'
    description   TEXT,           -- MLB human-readable description
    score_away    INTEGER,
    score_home    INTEGER,
    outs          INTEGER,
    raw_json      TEXT,           -- full payload, never throw away
    recorded_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_game_play_game ON game_play(game_pk);
CREATE INDEX IF NOT EXISTS idx_game_play_inning ON game_play(game_pk, inning);

-- ── 6. GAME_TMI_EVENT (chaos scenarios per game) ─────────────
CREATE TABLE IF NOT EXISTS game_tmi_event (
    id            TEXT PRIMARY KEY,
    game_pk       TEXT NOT NULL,
    name          TEXT,
    description   TEXT,
    payload       TEXT,           -- Madam Moments' full narrative
    icon          TEXT,
    triggered     INTEGER DEFAULT 0,
    triggered_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_game_tmi_game ON game_tmi_event(game_pk);

-- ── 7. MIGRATE PERSONA DATA ───────────────────────────────────
-- Pull from sys_user + cmdb_ci + cmdb_ci_ai_persona
INSERT OR IGNORE INTO persona (
    id, user_name, display_name, team,
    system_prompt, boggs_level,
    cadence, deep_lore, behavior_notes, governance
)
SELECT
    s.sys_id,
    s.user_name,
    s.first_name || COALESCE(' ' || s.last_name, ''),
    ci.assigned_to,
    p.u_system_prompt,
    COALESCE(CAST(p.u_boggs_reactivity AS INTEGER), 2),
    COALESCE(p.u_cadence, 'pacer'),
    p.u_deep_lore,
    p.u_behavior_expectations,
    p.u_governance_boundaries
FROM sys_user s
JOIN cmdb_ci ci
    ON s.user_name = ci.name COLLATE NOCASE
    AND ci.sys_class_name = 'cmdb_ci_ai_persona'
LEFT JOIN cmdb_ci_ai_persona p ON p.sys_id = ci.sys_id
WHERE s.user_name != 'james'
  AND s.user_name != 'antigravity';

-- ── 8. VERIFY ────────────────────────────────────────────────
SELECT count(*) || ' personas migrated' FROM persona;
SELECT count(*) || ' mlb_schedule games available' FROM mlb_schedule;
SELECT team, count(*) as cnt FROM persona GROUP BY team ORDER BY cnt DESC LIMIT 15;
