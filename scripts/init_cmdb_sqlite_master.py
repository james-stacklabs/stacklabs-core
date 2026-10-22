#!/usr/bin/env python3
"""
StackLabs Hardened Dual-Plane VFS: Master SQLite WAL Storage Plane
Path: /home/james/stacklabs/scripts/init_cmdb_sqlite_master.py
Author: James Carroll (Pilot) & Cockpit Architect
"""
import sys
import json
import time
import sqlite3
from pathlib import Path

# Defensive path resolution
sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path("/home/james/stacklabs/vfs/cmdb.db")

def init_master_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    
    with conn:
        # 1. Configuration Items (Master CMDB)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cis (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ci_class TEXT NOT NULL,
            operational_status TEXT NOT NULL,
            role TEXT,
            ip_address TEXT,
            env TEXT DEFAULT 'PROD',
            sys_id TEXT UNIQUE,
            sys_mod_count INTEGER DEFAULT 0,
            metadata JSON,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cis_name ON cis(name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cis_sys_id ON cis(sys_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cis_class ON cis(ci_class);")

        # 2. CI Relationships (BSM Topology Graph)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ci_relationships (
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            rel_type TEXT NOT NULL,
            PRIMARY KEY (parent_id, child_id, rel_type),
            FOREIGN KEY (parent_id) REFERENCES cis(id) ON DELETE CASCADE,
            FOREIGN KEY (child_id) REFERENCES cis(id) ON DELETE CASCADE
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_parent ON ci_relationships(parent_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_child ON ci_relationships(child_id);")

        # 3. Active Incident / Change Tickets
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            number TEXT PRIMARY KEY,
            sys_id TEXT UNIQUE,
            priority TEXT NOT NULL,
            state TEXT NOT NULL,
            short_description TEXT NOT NULL,
            cmdb_ci TEXT,
            sys_mod_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cmdb_ci) REFERENCES cis(id)
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_ci ON tickets(cmdb_ci);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_state ON tickets(state);")

        # 4. Atomic Outbox Queue (WAN Synchronization & OCC)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT NOT NULL,
            action TEXT NOT NULL,
            payload JSON NOT NULL,
            expected_mod_count INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            retries INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);")

    return conn

def seed_master_data(conn):
    print("[1/3] Seeding master CMDB footprint into SQLite WAL...")
    t0 = time.perf_counter()
    
    servers = []
    # Seed 5,000 enterprise servers
    for i in range(1, 5001):
        srv_id = f"srv-{i:04d}"
        ip = f"10.240.{(i // 254) % 254 + 1}.{i % 254 + 1}"
        env = "PROD" if i <= 4000 else "STAGING"
        role = "WEB_TIER" if i % 3 == 0 else ("APP_TIER" if i % 3 == 1 else "CACHE_TIER")
        servers.append((srv_id, srv_id, "server", "ONLINE", role, ip, env, f"sys_srv_{i:06d}", 0, json.dumps({"cpu": 16, "ram_gb": 64})))
    
    # Core enterprise anchor nodes
    servers.append(("sea-db-01", "sea-db-01", "database", "ONLINE", "PRIMARY_PAYROLL_DATABASE", "10.240.50.101", "PROD", "sys_sea_db_01", 3, json.dumps({"engine": "PostgreSQL 16", "cluster": "primary"})))
    servers.append(("sap_payroll", "sap_payroll", "business_service", "ONLINE", "CORE_FINANCIAL_SERVICE", "10.240.10.1", "PROD", "sys_sap_payroll", 1, json.dumps({"tier": "P0-MissionCritical"})))
    servers.append(("order_processing", "order_processing", "business_service", "ONLINE", "ECOMMERCE_BACKEND", "10.240.10.2", "PROD", "sys_order_proc", 1, json.dumps({"tier": "P1"})))
    servers.append(("sw-core-01", "sw-core-01", "network_switch", "ONLINE", "CORE_SPINE_SWITCH", "10.250.0.1", "PROD", "sys_sw_core_01", 0, json.dumps({"vendor": "Arista", "bandwidth": "400Gbps"})))
    servers.append(("san-pure-01", "san-pure-01", "storage_volume", "ONLINE", "NVME_ALL_FLASH_ARRAY", "10.250.10.1", "PROD", "sys_san_pure_01", 0, json.dumps({"capacity_tb": 120})))

    with conn:
        conn.executemany("""
        INSERT OR REPLACE INTO cis (id, name, ci_class, operational_status, role, ip_address, env, sys_id, sys_mod_count, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, servers)

    # Seed core dependencies
    relationships = [
        ("sap_payroll", "sea-db-01", "DependsOn"),
        ("sap_payroll", "srv-0001", "RunsOn"),
        ("sap_payroll", "srv-0002", "RunsOn"),
        ("order_processing", "sea-db-01", "DependsOn"),
        ("order_processing", "srv-0003", "RunsOn"),
        ("sea-db-01", "sw-core-01", "ConnectedTo"),
        ("sea-db-01", "san-pure-01", "MountsStorage"),
        ("srv-0001", "sw-core-01", "ConnectedTo"),
        ("srv-0002", "sw-core-01", "ConnectedTo")
    ]
    with conn:
        conn.executemany("""
        INSERT OR REPLACE INTO ci_relationships (parent_id, child_id, rel_type)
        VALUES (?, ?, ?);
        """, relationships)

    # Seed baseline tickets
    tickets = [
        ("INC0000060", "sys_inc_0000060", "1", "1", "SAP Payroll transaction timeout during month-end close", "sap_payroll", 4),
        ("INC-9001", "sys_inc_0009001", "1", "1", "Database transaction log disk volume 99% full on primary DB", "sea-db-01", 1)
    ]
    with conn:
        conn.executemany("""
        INSERT OR REPLACE INTO tickets (number, sys_id, priority, state, short_description, cmdb_ci, sys_mod_count)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, tickets)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    print(f"      Seeded {len(servers)} CIs, {len(relationships)} relationships, and {len(tickets)} tickets in {elapsed_ms:.2f} ms.")

if __name__ == "__main__":
    conn = init_master_database()
    seed_master_data(conn)
    db_size_bytes = DB_PATH.stat().st_size
    print(f"[DONE] SQLite WAL Master initialized at {DB_PATH}")
    print(f"       Disk Footprint: {db_size_bytes / (1024 * 1024):.2f} MB (vs. 14.2 GB tmpfs pagecache bloat).")
    conn.close()
