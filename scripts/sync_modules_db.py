import sqlite3
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def run():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    c = conn.cursor()

    # 1. Add category column if not exists
    try:
        c.execute("ALTER TABLE sys_module ADD COLUMN category TEXT DEFAULT 'utility'")
        print("Added category column to sys_module table.")
    except sqlite3.OperationalError:
        print("category column already exists in sys_module.")

    # 2. Add port column if not exists
    try:
        c.execute("ALTER TABLE sys_module ADD COLUMN port INTEGER")
        print("Added port column to sys_module table.")
    except sqlite3.OperationalError:
        print("port column already exists in sys_module.")

    # 3. Define all standard apps/stacks/utilities/configs
    apps = [
        # Active Stacks (11)
        ('fanstack', 'FanStack Creator Portal', 'Sovereign Portal', 'F', '#38bdf8', 1, 'stack', 3009),
        ('fan_portal', 'Fan Portal', 'Sovereign Fan Portal', 'F', '#38bdf8', 1, 'stack', 3010),
        ('sovereign_portal', 'Sovereign OS Portal', 'Central Configuration & Stack Directory', '❖', '#ffffff', 1, 'stack', 3016),
        ('samtracker', 'SamTracker', 'Six Dinner Sam', 'S', '#fbbf24', 1, 'stack', 3004),
        ('catnipwars', 'Catnip Wars', 'Syndicate Sandbox', 'C', '#10b981', 1, 'stack', 7301),
        ('aethervet', 'AetherVet', 'Veterinary Portal', '🩺', '#a78bfa', 1, 'stack', 3015),
        ('clio_cockpit', 'Clio Cockpit Dashboard', 'Hardware & System Command Center', '🛠️', '#f59e0b', 1, 'stack', 3022),
        ('eileen_stack', "Eileen's Stack", 'Storybook Station', '🌱', '#10b981', 1, 'stack', 3017),
        ('barb_stack', "Barb's Stack", 'Smyrna Heights rustic catalog', '🏡', '#fbbf24', 1, 'stack', 3020),
        ('sovereign_cinema', 'Sovereign Cinema', 'Streaming Portal', '🎬', '#8b5cf6', 1, 'stack', 3008),
        ('sovereign_sports', 'Sovereign Sports', 'Live Stream Command', '🛡️', '#00f0ff', 0, 'stack', 3010),

        # Inactive / Decommissioned Stacks (7)
        ('gonzas', 'Gonzas Convenience & Cantina', 'Convenience Store & Cantina', '🏪', '#ff007f', 0, 'stack', 3025),
        ('gardenstack', 'GardenStack', 'Horticulture AI', '🌱', '#10b981', 0, 'stack', 3021),
        ('wild_paws', 'Wild Paws Rescue', 'Art Rescue Sanctuary', '🐾', '#f59e0b', 0, 'stack', 3008),
        ('spite_slice', 'Spite Slice', 'Culinary Vengeance', '🍕', '#ef4444', 0, 'stack', 3019),
        ('card_turpey', 'Card Turpey', 'Predictive Memorabilia', '🃏', '#fb923c', 0, 'stack', 3016),
        ('inkwell_irony', 'Inkwell & Irony', 'Investigations', '🖋️', '#a1a1aa', 0, 'stack', 3018),
        ('stacklabs', 'StackLabs LLC', 'Edge-Native POSIX-Native Software Foundry', '💻', '#00d4ff', 1, 'stack', 3000),
        ('anvil_twine', 'Anvil & Twine', 'Hardware & Craftsmanship', '🛠️', '#f59e0b', 0, 'stack', 3022),

        # Utilities
        ('argus', 'ARGUS Nexus', 'Surveillance Grid', '👁️', '#66fcf1', 1, 'utility', None),
        ('itsm', 'ITSM Operations', 'SDLC & Incidents', '🔧', '#ff0033', 1, 'utility', None),
        ('persona_center', 'Advocate Command Center', 'Deployment & Visuals', '👥', '#059669', 1, 'utility', None),
        ('cinema_remote', 'Cinema Remote', 'Theater Control', '📱', '#6366f1', 1, 'utility', None),
        ('detractor_mailbag', 'Detractor Mailbag', 'Reddit Hate Triage', '🔥', '#f43f5e', 1, 'utility', None),
        ('highlight_heist', 'Universal Media Ingestor', 'Video Downloader', '📥', '#a855f7', 1, 'utility', None),
        ('prospectus', 'Investor Prospectus', 'Confidential Deck', '📄', '#38bdf8', 1, 'utility', None),
        ('presence', 'Telepresence Hub', 'Live Caller Grid', '📞', '#00d4aa', 1, 'utility', None),
        ('voice', 'Voice Heal', 'System Self-Recovery', '🎙️', '#d97706', 1, 'utility', None),
        ('town_simulation', 'Town Square', 'Stack Simulation', '🏡', '#fbbf24', 1, 'utility', None),
        ('holodex', 'Sovereign HoloDex', 'Video Synthesis Engine', '✨', '#a855f7', 1, 'utility', None),
        ('storyboard_deck', 'Storyboard Deck', 'Sequence Planner', '📋', '#38bdf8', 1, 'utility', None),
        ('savant_query', 'Savant Oracle', 'SQL Data Analytics', '📊', '#66fcf1', 1, 'utility', None),
        ('vocal_matrix', 'Vocal Matrix', 'Voice Synthesis Engine', '🗣️', '#f59e0b', 1, 'utility', None),
        ('scruffys', "Scruffy's Tavern", 'Live Chat & Advocate Interactions', '🍻', '#38bdf8', 1, 'utility', 3002),
        ('the_skew', 'The Skew (Live)', 'Daytime Sports Talk & Debate', '🎙️', '#a855f7', 1, 'utility', 8001),
        ('hot_takes', 'Hot Takes', 'High-Intensity Advocate Rants', '🔥', '#ef4444', 1, 'utility', 8000),
        ('stream_sniper', 'Stream Sniper', 'Live Target Acquisition', '🎯', '#f43f5e', 1, 'utility', 5056),
        ('rom_gallery', 'Sovereign Watch Party', 'ROM & Video Archive', '📼', '#fbbf24', 1, 'utility', 3004),
        ('tmi_news_desk', 'TMI News Desk', 'Broadcast Director Triage Dashboard', '🚨', '#ef4444', 1, 'utility', None),
        ('artifact_gallery', 'Media Vault Matrix', 'Consolidated Artifacts', '📦', '#a855f7', 1, 'utility', None),
        ('promo_inbox', 'The Cosmic Sieve', 'Incoming Brand & Agent Messages', '📬', '#38bdf8', 1, 'utility', None),
        ('knowledge_hub', 'Knowledge Hub', 'Integrated Sovereign Knowledge Gateway and documentation lookup', '📚', '#e0bc68', 1, 'utility', None),
        ('optical_ingest', 'Optical Ingest Console', 'Advocate Intake Stream', '📷', '#10b981', 1, 'utility', None),
        ('roll_call', 'Daily Roll Call', 'Morning Agent Check-In', '📋', '#fbbf24', 1, 'utility', 8000),
        ('model_arena', 'Model Battle Arena', 'LLM Performance Testing', '⚔️', '#ef4444', 1, 'utility', None),

        # Configurations
        ('app_directory', 'System Control', 'Sovereign Configuration Hub', '❖', '#ffffff', 1, 'config', 3016),
        ('system_config', 'System Config', 'Theme · Telemetry · More', '⚙️', '#ffffff', 1, 'config', None),
        ('env_indicator', 'Active Env', 'Active Environment', '🖥️', '#38bdf8', 1, 'config', None),
        ('stack_seeder', 'Stack Seeder', 'Brand Onboarding', '🌱', '#10b981', 1, 'config', None)
     ]

    # Module to CMDB Appl sys_id mapping to match pre-existing records and keep consistency
    sys_id_map = {
        'fanstack': 'app_fanstack',
        'fan_portal': 'app_fan_portal',
        'sovereign_portal': 'app_sovereign_portal',
        'samtracker': 'app_samtracker',
        'catnipwars': 'app_catnipwars',
        'aethervet': 'app_aethervet',
        'clio_cockpit': 'app_clio_cockpit',
        'eileen_stack': 'app_eileen_stack',
        'barb_stack': 'app_barb_stack',
        'gonzas': 'app_gonzas_cantina',
        'wild_paws': 'app_wild_paws',
        'spite_slice': 'app_spiteslice',
        'card_turpey': 'app_card_turpey',
        'inkwell_irony': 'app_inkwell_irony',
        'stacklabs': 'app_stacklabs',
        'gardenstack': 'app_gardenstack',
        'sovereign_cinema': 'app_sovereign_cinema',
        'sovereign_sports': 'app_sovereign_sports'
    }

    for m_name, d_name, desc, icon, color, active, cat, port in apps:
        # Check if exists in sys_module
        c.execute("SELECT id FROM sys_module WHERE module_name=?", (m_name,))
        row = c.fetchone()
        if row:
            c.execute("""
                UPDATE sys_module
                SET display_name=?, description=?, icon=?, color=?, active=?, category=?, port=?
                WHERE module_name=?
            """, (d_name, desc, icon, color, active, cat, port, m_name))
        else:
            c.execute("""
                INSERT INTO sys_module (id, module_name, display_name, description, icon, color, active, category, port)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uuid.uuid4().hex, m_name, d_name, desc, icon, color, active, cat, port))

        # Check if it should be synced to CMDB (all stacks, active or inactive)
        if cat == 'stack' or m_name in sys_id_map:
            sys_id = sys_id_map.get(m_name, f"app_{m_name}")
            
            # Ensure hardware link node or general parent runs relation (can be dummy or direct)
            c.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id=?", (sys_id,))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO cmdb_ci (sys_id, name, sys_class_name, operational_status)
                    VALUES (?, ?, 'cmdb_ci_appl', 1)
                """, (sys_id, d_name))
            else:
                c.execute("UPDATE cmdb_ci SET name=? WHERE sys_id=?", (d_name, sys_id))

            c.execute("SELECT sys_id FROM cmdb_ci_appl WHERE sys_id=?", (sys_id,))
            port_str = str(port) if port is not None else ""
            if not c.fetchone():
                c.execute("""
                    INSERT INTO cmdb_ci_appl (sys_id, name, port, status, short_description, icon, active)
                    VALUES (?, ?, ?, 'ONLINE', ?, ?, ?)
                """, (sys_id, d_name, port_str, desc, icon, active))
            else:
                c.execute("""
                    UPDATE cmdb_ci_appl
                    SET name=?, port=?, short_description=?, icon=?, active=?
                    WHERE sys_id=?
                """, (d_name, port_str, desc, icon, active, sys_id))

    # 4. Make sure bistro is deleted
    c.execute("DELETE FROM sys_module WHERE module_name='bistro'")
    c.execute("DELETE FROM cmdb_ci WHERE name LIKE '%bistro%'")

    # 5. Seed default m2m_stack_utility links for fanstack
    fanstack_utilities = [
        'scruffys', 'the_skew', 'hot_takes', 'stream_sniper',
        'holodex', 'rom_gallery', 'artifact_gallery',
        'persona_center', 'promo_inbox', 'savant_query',
        'optical_ingest', 'roll_call', 'model_arena',
        'tmi_news_desk', 'knowledge_hub'
    ]
    for util in fanstack_utilities:
        c.execute("SELECT active FROM m2m_stack_utility WHERE stack_module_name='fanstack' AND utility_module_name=?", (util,))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO m2m_stack_utility (stack_module_name, utility_module_name, active) VALUES ('fanstack', ?, 1)", (util,))
        else:
            c.execute("UPDATE m2m_stack_utility SET active=1 WHERE stack_module_name='fanstack' AND utility_module_name=?", (util,))

    # 6. Seed default m2m_stack_utility links for aethervet
    aethervet_utilities = [
        'itsm', 'voice', 'holodex', 'persona_center',
        'presence', 'savant_query', 'knowledge_hub'
    ]
    for util in aethervet_utilities:
        c.execute("SELECT active FROM m2m_stack_utility WHERE stack_module_name='aethervet' AND utility_module_name=?", (util,))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO m2m_stack_utility (stack_module_name, utility_module_name, active) VALUES ('aethervet', ?, 1)", (util,))
        else:
            c.execute("UPDATE m2m_stack_utility SET active=1 WHERE stack_module_name='aethervet' AND utility_module_name=?", (util,))

    conn.commit()
    conn.close()
    print("Database sync completed successfully!")

if __name__ == '__main__':
    run()
