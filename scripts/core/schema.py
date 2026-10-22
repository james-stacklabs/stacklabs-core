"""DB schema migration helpers. Run at startup to ensure columns/tables exist."""
import sqlite3
import uuid


def ensure_website_columns_exist(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(cmdb_ci_fanstack_room)")
        columns = [col[1] for col in cur.fetchall()]
        
        expected_columns = {
            "website_purpose": "TEXT",
            "website_domain": "TEXT",
            "website_pages": "TEXT",
            "website_features": "TEXT",
            "website_colors": "TEXT",
            "website_typography": "TEXT",
            "website_additional_requirements": "TEXT",
            "postgame_raid_url": "TEXT"
        }
        
        for col_name, col_type in expected_columns.items():
            if col_name not in columns:
                print(f"[MIGRATION] Adding missing column '{col_name}' to 'cmdb_ci_fanstack_room'...")
                cur.execute(f"ALTER TABLE cmdb_ci_fanstack_room ADD COLUMN {col_name} {col_type}")
                conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate database columns: {e}")


def ensure_user_layout_column_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(sys_user)")
        columns = [col[1] for col in cur.fetchall()]
        if "layout_configuration" not in columns:
            print("[MIGRATION] Adding column 'layout_configuration' to 'sys_user'...")
            cur.execute("ALTER TABLE sys_user ADD COLUMN layout_configuration TEXT")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate sys_user layout column: {e}")


def ensure_sys_module_visibility_column_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(sys_module)")
        columns = [col[1] for col in cur.fetchall()]
        if "visible_on_main" not in columns:
            print("[MIGRATION] Adding column 'visible_on_main' to 'sys_module'...")
            cur.execute("ALTER TABLE sys_module ADD COLUMN visible_on_main INTEGER DEFAULT 0")
            conn.commit()
        
        # Check if persona_center exists in sys_module
        cur.execute("SELECT id FROM sys_module WHERE module_name = 'persona_center'")
        row = cur.fetchone()
        if not row:
            print("[MIGRATION] Seeding 'persona_center' module in sys_module...")
            cur.execute("""
                INSERT INTO sys_module (id, module_name, display_name, description, icon, color, active, category, visible_on_main)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1)
            """, (uuid.uuid4().hex, "persona_center", "Advocate Center", "Deployment & Visuals", "Users", "#059669", "utility"))
        else:
            print("[MIGRATION] Setting 'persona_center' visible_on_main to 1...")
            cur.execute("UPDATE sys_module SET visible_on_main = 1 WHERE module_name = 'persona_center'")
        
        # Check if knowledge_hub exists in sys_module
        cur.execute("SELECT id FROM sys_module WHERE module_name = 'knowledge_hub'")
        row = cur.fetchone()
        if not row:
            print("[MIGRATION] Seeding 'knowledge_hub' module in sys_module...")
            cur.execute("""
                INSERT INTO sys_module (id, module_name, display_name, description, icon, color, active, category, visible_on_main)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1)
            """, (uuid.uuid4().hex, "knowledge_hub", "Knowledge Hub", "Integrated Sovereign Knowledge Gateway and documentation lookup", "📚", "#e0bc68", "utility"))
        else:
            cur.execute("UPDATE sys_module SET visible_on_main = 1 WHERE module_name = 'knowledge_hub'")

        # Seed default values for other default visible modules
        default_visible_ids = ['argus', 'itsm', 'system_config', 'app_directory', 'power_tools_utilities', 'stack_seeder', 'stacklabs', 'knowledge_hub']
        for app_id in default_visible_ids:
            cur.execute("UPDATE sys_module SET visible_on_main = 1 WHERE module_name = ?", (app_id,))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate sys_module visibility column: {e}")


def ensure_soundboard_table_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cmdb_ci_media_soundboard_phrase (
                sys_id TEXT PRIMARY KEY,
                persona_id TEXT,
                button_label TEXT,
                text_payload TEXT,
                is_custom INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Seed default phrases for @barf
        barf_id = 'c5fb94a6c5364cc88c7c85aeb47c7e0e'
        cur.execute("SELECT count(*) FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (barf_id,))
        if cur.fetchone()[0] == 0:
            print("[MIGRATION] Seeding default soundboard phrases for @barf...")
            barf_phrases = [
                ("WELFARE STATE", "Are you kidding me?! The Pirates are a welfare baseball state! Bob Nutting is just cashing Steve Cohen's luxury tax checks and pocketing the revenue-sharing instead of buying a bullpen!", 0),
                ("BEDNAR TRADE", "Don't even talk to me about the Bednar trade! That was a complete highway robbery, and it will haunt your franchise for decades!", 0),
                ("PASTRAMI BUDGET", "Your payroll is so cheap you are literally counting pastrami sandwiches and Iron City beers as units of luxury tax grift!", 0),
                ("BOTTOM FEEDERS", "Pittsburgh is the division's bottom feeder where baseball dreams go to die. Enjoy your 100-loss season!", 0),
                ("COHEN CHECKS", "You're welcome for the electricity bills today, Yinzers! Steve Cohen's luxury tax check is the only thing keeping your stadium lights on!", 0)
            ]
            for label, payload, is_custom in barf_phrases:
                cur.execute("""
                    INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
                    VALUES (?, ?, ?, ?, ?)
                """, (uuid.uuid4().hex, barf_id, label, payload, is_custom))
            conn.commit()

        # Seed default phrases for @compliance_karen
        karen_id = '88320beace384ebd8fe3a5130f040b9b'
        cur.execute("SELECT count(*) FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (karen_id,))
        if cur.fetchone()[0] == 0:
            print("[MIGRATION] Seeding default soundboard phrases for @compliance_karen...")
            karen_phrases = [
                ("COMPLIANCE", "Excuse me, but this room is out of compliance! I need to see your active COAs and living soil batch records immediately!", 0),
                ("LOG RE-ROUTE", "Re-routing all chat logs directly to the state compliance registry. Have a nice day!", 0)
            ]
            for label, payload, is_custom in karen_phrases:
                cur.execute("""
                    INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
                    VALUES (?, ?, ?, ?, ?)
                """, (uuid.uuid4().hex, karen_id, label, payload, is_custom))
            conn.commit()

        # Seed default phrases for @keith_fanboy
        keith_id = '261a93a87f514987999ee81cbf49b82a'
        cur.execute("SELECT count(*) FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (keith_id,))
        if cur.fetchone()[0] == 0:
            print("[MIGRATION] Seeding default soundboard phrases for @keith_fanboy...")
            keith_phrases = [
                ("1986 GRIT", "Now that is some 1986 Keith Hernandez grit right there! None of this soft modern baseball stuff!", 0),
                ("COHEN TAX", "Steve Cohen's tax bill is just pocket change to bring us a championship! LGM!", 0)
            ]
            for label, payload, is_custom in keith_phrases:
                cur.execute("""
                    INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
                    VALUES (?, ?, ?, ?, ?)
                """, (uuid.uuid4().hex, keith_id, label, payload, is_custom))
            conn.commit()

        # Seed default phrases for @birds_on_bat
        fredbird_id = 'Fredbird_Fiend'
        cur.execute("SELECT count(*) FROM cmdb_ci_media_soundboard_phrase WHERE persona_id = ?", (fredbird_id,))
        if cur.fetchone()[0] == 0:
            print("[MIGRATION] Seeding default soundboard phrases for @birds_on_bat...")
            fredbird_phrases = [
                ("WELFARE STATE", "It’s charming how New York thinks money buys class. Down here, we don't buy rings; we grow them in our farm system with good old-fashioned corn and text-book fundamental cut-offs.", 0),
                ("TEXTBOOK SACRIFICE", "A tactical strikeout, really. Wore down the pitcher's pitch count by 4. Next batter is perfectly set up for a classic, beautifully executed sacrifice bunt. That’s just smart baseball.", 0),
                ("MIDWEST HOSPITALITY", "Sir, please lower your font size. This is a baseball stadium chat log, not a municipal auction. Take a deep breath, eat some toasted ravioli, and appreciate a clean double play.", 0)
            ]
            for idx, (label, payload, is_custom) in enumerate(fredbird_phrases):
                cur.execute("""
                    INSERT INTO cmdb_ci_media_soundboard_phrase (sys_id, persona_id, button_label, text_payload, is_custom)
                    VALUES (?, ?, ?, ?, ?)
                """, (f"fredbird_rant_{idx+1}", fredbird_id, label, payload, is_custom))
            conn.commit()

        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate soundboard table: {e}")



def ensure_sys_menu_item_table_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sys_menu_item (
                sys_id TEXT PRIMARY KEY,
                stack_origin TEXT,
                target_competitor TEXT,
                item_name TEXT,
                description TEXT,
                cost_credits INTEGER,
                is_spite_special INTEGER
            )
        """)
        cur.execute("SELECT COUNT(*) FROM sys_menu_item WHERE stack_origin='spiteslice'")
        count = cur.fetchone()[0]
        if count == 0:
            print("[MIGRATION] Seeding default sys_menu_item entries...")
            items = [
                (uuid.uuid4().hex, "spiteslice", "davincis", "Vengeance Pepperoni Slice", "Extra spicy pepperoni to spite the corporate competitors.", 100, 0),
                (uuid.uuid4().hex, "spiteslice", "davincis", "Spiteful Sausage & Garlic Pizza", "Loaded with roasted garlic and spicy sausage. Smells strong.", 200, 0),
                (uuid.uuid4().hex, "spiteslice", "davincis", "Grudge Matcha Pizza", "A bitter green tea crust with sweet moscato glaze.", 150, 0),
                (uuid.uuid4().hex, "spiteslice", "other", "Standard Cheese Slice", "Just a plain cheese slice.", 80, 0)
            ]
            cur.executemany("INSERT INTO sys_menu_item (sys_id, stack_origin, target_competitor, item_name, description, cost_credits, is_spite_special) VALUES (?, ?, ?, ?, ?, ?, ?)", items)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate sys_menu_item: {e}")

def ensure_sys_search_directory_table_exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sys_search_directory (
                sys_id          TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                path            TEXT UNIQUE NOT NULL,
                active          INTEGER DEFAULT 1,
                recursive       INTEGER DEFAULT 1,
                file_extensions TEXT DEFAULT '.md,.txt,.json,.tsx,.ts,.py,.sh',
                sys_created_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sys_updated_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("SELECT COUNT(*) FROM sys_search_directory")
        count = cur.fetchone()[0]
        if count == 0:
            print("[MIGRATION] Seeding default sys_search_directory entries...")
            default_dirs = [
                (uuid.uuid4().hex, "Sovereign OS DNA", "/home/james/stacklabs/dna/", 1, 0, ".md,.txt"),
                (uuid.uuid4().hex, "Sovereign OS Docs", "/home/james/stacklabs/dna/docs/", 1, 1, ".md,.txt"),
                (uuid.uuid4().hex, "Sovereign Inbox", "/home/james/sovereign_inbox/", 1, 1, ".md,.txt,.log")
            ]
            cur.executemany("""
                INSERT INTO sys_search_directory (sys_id, name, path, active, recursive, file_extensions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, default_dirs)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate sys_search_directory: {e}")


def ensure_sentinel_voice_incidents_columns_exist(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(sentinel_voice_incidents)")
        columns = [col[1] for col in cur.fetchall()]
        if columns and "ticket_number" not in columns:
            print("[MIGRATION] Adding column 'ticket_number' to 'sentinel_voice_incidents'...")
            cur.execute("ALTER TABLE sentinel_voice_incidents ADD COLUMN ticket_number TEXT")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION WARNING] Failed to migrate sentinel_voice_incidents: {e}")

# Run migrations at import time (same behavior as the original monolith,
# where each ensure_* call followed immediately after its own definition).
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ensure_website_columns_exist(DB_PATH)
ensure_user_layout_column_exists(DB_PATH)
ensure_sys_module_visibility_column_exists(DB_PATH)
ensure_soundboard_table_exists(DB_PATH)
ensure_sys_menu_item_table_exists(DB_PATH)
ensure_sys_search_directory_table_exists(DB_PATH)
ensure_sentinel_voice_incidents_columns_exist(DB_PATH)

