import sqlite3
import os
import json
import uuid
import time
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sovereign_core.db")

class SovereignCMDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self):
        cursor = self.conn.cursor()
        
        # 1. THE FLEET ROSTER
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fleet_nodes (
                node_id TEXT PRIMARY KEY,
                hardware TEXT,
                agent_class TEXT,
                status TEXT,
                primary_directives TEXT, -- JSON array
                manifest_path TEXT,
                s_value REAL
            )
        ''')

        # 2. BIOLOGICAL ASSET LEDGER
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bio_assets (
                asset_id TEXT PRIMARY KEY,
                name TEXT,
                species TEXT,
                vip_level TEXT,
                tracking_source TEXT, -- JSON array
                lat REAL,
                lng REAL,
                behavioral_state TEXT,
                loki_threat_escalation REAL
            )
        ''')

        # 3. IMMUTABLE TELEMETRY LEDGER
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logistics_ledger (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT,
                event_type TEXT,
                source_node TEXT,
                payload_json TEXT, -- JSON object
                processed_by_supply_prophet BOOLEAN
            )
        ''')

        # 4. THE OMEGA GATE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS omega_gate (
                execution_id TEXT PRIMARY KEY,
                proposed_action TEXT,
                proposing_node TEXT,
                justification TEXT,
                pilot_signature TEXT,
                status TEXT
            )
        ''')

        # SDLC TICKET SYSTEM (Legacy migration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sdlc_tickets (
                ticket_id TEXT PRIMARY KEY,
                ci_id TEXT,
                title TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                created_at TEXT
            )
        ''')

        self.conn.commit()

    # --- FLEET ROSTER METHODS ---
    def register_node(self, node_id, hardware, agent_class, status, primary_directives, manifest_path, s_value=1.0):
        cursor = self.conn.cursor()
        directives_json = json.dumps(primary_directives)
        cursor.execute('''
            INSERT OR REPLACE INTO fleet_nodes (node_id, hardware, agent_class, status, primary_directives, manifest_path, s_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (node_id, hardware, agent_class, status, directives_json, manifest_path, s_value))
        self.conn.commit()
        return {"node_id": node_id, "status": status}

    def get_all_nodes(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM fleet_nodes')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # --- BIO ASSETS METHODS ---
    def update_bio_asset(self, asset_id, name, species, vip_level, tracking_source, lat, lng, behavioral_state, loki_threat=0.0):
        cursor = self.conn.cursor()
        sources_json = json.dumps(tracking_source)
        cursor.execute('''
            INSERT OR REPLACE INTO bio_assets (asset_id, name, species, vip_level, tracking_source, lat, lng, behavioral_state, loki_threat_escalation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (asset_id, name, species, vip_level, sources_json, lat, lng, behavioral_state, loki_threat))
        self.conn.commit()
        return {"asset_id": asset_id, "status": "TRACKED"}

    def get_all_bio_assets(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bio_assets')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # --- LOGISTICS LEDGER ---
    def log_event(self, event_type, source_node, payload):
        cursor = self.conn.cursor()
        event_id = f"LOG-{int(time.time())}-{str(uuid.uuid4()).split('-')[0].upper()[:4]}"
        cursor.execute('''
            INSERT INTO logistics_ledger (event_id, timestamp, event_type, source_node, payload_json, processed_by_supply_prophet)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_id, datetime.now().isoformat(), event_type, source_node, json.dumps(payload), False))
        self.conn.commit()
        return event_id

    # --- OMEGA GATE METHODS ---
    def request_execution(self, proposed_action, proposing_node, justification):
        cursor = self.conn.cursor()
        execution_id = f"EXEC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4()).split('-')[0].upper()[:4]}"
        cursor.execute('''
            INSERT INTO omega_gate (execution_id, proposed_action, proposing_node, justification, pilot_signature, status)
            VALUES (?, ?, ?, ?, NULL, 'AWAITING_Ω_SIGNATURE')
        ''', (execution_id, proposed_action, proposing_node, justification))
        self.conn.commit()
        return execution_id

    # --- SDLC TICKETS ---
    def generate_ticket(self, ci_id, title, description, priority="Low", status="Open"):
        cursor = self.conn.cursor()
        ticket_id = f"INC-{int(time.time())}-{str(uuid.uuid4()).split('-')[0].upper()[:4]}"
        cursor.execute('''
            INSERT INTO sdlc_tickets (ticket_id, ci_id, title, description, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ticket_id, ci_id, title, description, priority, status, datetime.now().isoformat()))
        self.conn.commit()
        return ticket_id

    def get_all_tickets(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sdlc_tickets')
        return [dict(row) for row in cursor.fetchall()]

# Singleton instance
cmdb = SovereignCMDB()
