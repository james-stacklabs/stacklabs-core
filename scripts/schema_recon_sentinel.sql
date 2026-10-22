PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS prospects (
    prospect_id TEXT PRIMARY KEY,
    business_name TEXT NOT NULL,
    vertical TEXT NOT NULL,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'GA',
    postal_code TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    legacy_url TEXT,
    edge_showroom_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    active_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (active_status IN ('PENDING', 'ACTIVE', 'PAUSED', 'CONVERTED'))
);

CREATE TABLE IF NOT EXISTS target_keywords (
    keyword_id TEXT PRIMARY KEY,
    prospect_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    estimated_ticket_value REAL NOT NULL,
    intent_category TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS serp_audit_runs (
    run_id TEXT PRIMARY KEY,
    prospect_id TEXT NOT NULL,
    audit_milestone TEXT NOT NULL,
    executed_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    worker_node TEXT NOT NULL DEFAULT 'clio',
    user_agent TEXT NOT NULL,
    FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS serp_keyword_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    keyword_id TEXT NOT NULL,
    prospect_organic_rank INTEGER,
    prospect_in_local_pack BOOLEAN NOT NULL DEFAULT 0,
    prospect_in_ai_overview BOOLEAN NOT NULL DEFAULT 0,
    ai_overview_present BOOLEAN NOT NULL DEFAULT 0,
    ai_overview_snippet_text TEXT,
    top_competitor_url_1 TEXT,
    top_competitor_url_2 TEXT,
    top_competitor_url_3 TEXT,
    screenshot_full_path TEXT NOT NULL,
    screenshot_aio_path TEXT,
    raw_html_path TEXT NOT NULL,
    html_sha256 TEXT NOT NULL,
    screenshot_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    FOREIGN KEY (run_id) REFERENCES serp_audit_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES target_keywords(keyword_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS needle_movement_events (
    event_id TEXT PRIMARY KEY,
    prospect_id TEXT NOT NULL,
    keyword_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_rank INTEGER,
    new_rank INTEGER,
    narrative_summary TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES target_keywords(keyword_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES serp_audit_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_serp_prospect_keyword ON serp_keyword_results(keyword_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_runs_prospect ON serp_audit_runs(prospect_id, audit_milestone);

CREATE VIEW IF NOT EXISTS serp_keyword_snapshots AS SELECT * FROM serp_keyword_results;
