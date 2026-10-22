"""
Applies the 08272026_sdlc_epic_hierarchy.sql migration to sovereign_now.db
"""
import sqlite3
import os

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def run_migration():
    print(f"Applying migration to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 0. Drop view first so SQLite schema validator doesn't block table renames
    cursor.execute("DROP VIEW IF EXISTS v_sdlc_epic_rollup;")
    
    # 1. Initiatives table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdlc_initiatives (
        initiative_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        description TEXT,
        owner TEXT DEFAULT 'james',
        status TEXT DEFAULT 'ACTIVE',
        icon TEXT DEFAULT '🚀',
        color TEXT DEFAULT '#00b4d8',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Check sovereign_epics / sovereign_epics_new
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sovereign_epics_new'")
    has_new = cursor.fetchone()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sovereign_epics'")
    has_epics = cursor.fetchone()
    
    if has_new and not has_epics:
        print("Renaming sovereign_epics_new to sovereign_epics...")
        cursor.execute("ALTER TABLE sovereign_epics_new RENAME TO sovereign_epics")
    elif not has_epics:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_epics (
            epic_id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiative_id TEXT REFERENCES sdlc_initiatives(initiative_id),
            epic_key TEXT UNIQUE,
            epic_name TEXT NOT NULL,
            description TEXT,
            owner TEXT DEFAULT 'james',
            status TEXT DEFAULT 'IN_PROGRESS',
            health TEXT DEFAULT 'ON_TRACK',
            color TEXT DEFAULT '#00b4d8',
            risk_level TEXT DEFAULT 'LOW',
            business_value TEXT,
            architecture_spec_url TEXT,
            target_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
    # 3. sdlc_features table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sdlc_features (
        feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
        epic_id INTEGER NOT NULL REFERENCES sovereign_epics(epic_id) ON DELETE CASCADE,
        feature_key TEXT UNIQUE,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'OPEN',
        priority TEXT DEFAULT 'P3',
        owner TEXT DEFAULT 'james',
        acceptance_criteria TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 4. Dependencies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sovereign_ticket_dependencies (
        dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
        predecessor_id TEXT NOT NULL,
        successor_id TEXT NOT NULL,
        dependency_type TEXT DEFAULT 'BLOCKS',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(predecessor_id, successor_id, dependency_type)
    );
    """)
    
    # 5. Add feature_id to sovereign_tickets if missing
    cursor.execute("PRAGMA table_info(sovereign_tickets)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'feature_id' not in columns:
        print("Adding feature_id column to sovereign_tickets...")
        cursor.execute("ALTER TABLE sovereign_tickets ADD COLUMN feature_id INTEGER REFERENCES sdlc_features(feature_id)")
    
    # 6. View: v_sdlc_epic_rollup
    cursor.execute("""
    CREATE VIEW IF NOT EXISTS v_sdlc_epic_rollup AS
    SELECT 
        e.epic_id,
        e.epic_key,
        e.epic_name,
        e.initiative_id,
        i.name as initiative_name,
        i.icon as initiative_icon,
        e.description,
        e.owner,
        e.status,
        e.health,
        e.color,
        e.risk_level,
        e.business_value,
        e.architecture_spec_url,
        e.target_date,
        e.created_at,
        e.updated_at,
        COUNT(DISTINCT f.feature_id) as total_features,
        COUNT(DISTINCT t.number) as total_tickets,
        SUM(CASE WHEN t.state IN (4, 5) THEN 1 ELSE 0 END) as completed_tickets,
        SUM(CASE WHEN t.state = 2 THEN 1 ELSE 0 END) as in_progress_tickets,
        SUM(CASE WHEN t.state IN (0, 1) THEN 1 ELSE 0 END) as open_tickets,
        ROUND(
            CASE 
                WHEN COUNT(DISTINCT t.number) = 0 THEN 0.0
                ELSE (SUM(CASE WHEN t.state IN (4, 5) THEN 1.0 ELSE 0.0 END) * 100.0) / COUNT(DISTINCT t.number)
            END, 1
        ) as completion_pct
    FROM sovereign_epics e
    LEFT JOIN sdlc_initiatives i ON i.initiative_id = e.initiative_id
    LEFT JOIN sdlc_features f ON f.epic_id = e.epic_id
    LEFT JOIN sovereign_tickets t ON t.epic_id = e.epic_id
    GROUP BY e.epic_id;
    """)
    
    cursor.execute("""
    INSERT OR REPLACE INTO schema_migrations (version, description, executed_at)
    VALUES ('08272026_01', '08272026_sdlc_epic_hierarchy.sql', CURRENT_TIMESTAMP);
    """)
    
    conn.commit()
    
    # Verification
    cursor.execute("SELECT name, type FROM sqlite_master WHERE name IN ('sdlc_initiatives', 'sovereign_epics', 'sdlc_features', 'sovereign_ticket_dependencies', 'v_sdlc_epic_rollup')")
    verified = cursor.fetchall()
    print(f"✅ Migration applied successfully! Verified elements: {verified}")
    conn.close()

if __name__ == '__main__':
    run_migration()
