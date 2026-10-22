#!/usr/bin/env python3
"""
seed_rbac.py — Seeds sys_role and sys_role_permission tables
Sovereign OS — KI-048 compliant (mesh-only access)
"""
import sqlite3, uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

ROLES = [
    # (name, display_name, description, can_be_disabled)
    ("pilot",         "Pilot",          "Full system access. Architect-class.",                  0),
    ("creator",       "Creator",        "FanStack content operator. Full FanStack, no admin.",   1),
    ("stack_manager", "Stack Manager",  "Advocate Stack Manager. Full Advocate & Stack ops.",    1),
    ("patron",        "Patron",         "Authenticated guest. FanStack + HoloLink.",             1),
    ("investor",      "Investor",       "Read-only investor demo access.",                       1),
    ("vet_client",    "Vet Client",     "AetherVet portal access only.",                        1),
    ("garden_client", "Garden Client",  "WildSeed GardenStack access only.",                    1),
    ("observer",      "Observer",       "Read-only FanStack room viewer.",                      1),
]

PERMISSIONS = [
    # (role, service_name, port, access_level)

    # pilot — full everything
    ("pilot", "Sovereign OS Portal / FanStack Hub", 3000, "full"),
    ("pilot", "Sovereign Sports UI",    3010, "full"),
    ("pilot", "Sovereign Cinema UI",    3008, "full"),
    ("pilot", "Sovereign SDLC Portal",  3009, "full"),
    ("pilot", "AetherVet Portal",       3015, "full"),
    ("pilot", "WildSeed GardenStack",   3016, "full"),
    ("pilot", "FanStack Sports Backend", 8000, "full"),
    ("pilot", "FanStack WS Relay",      8008, "full"),
    ("pilot", "FanStack Admin API",     8001, "full"),
    ("pilot", "FanStack Chatbots",      8009, "full"),
    ("pilot", "HoloLink Mesh Relay",    8012, "full"),
    ("pilot", "Sovereign Core API",     8090, "full"),
    ("pilot", "SDLC Ticketing API",     8095, "full"),
    ("pilot", "Sovereign Stream Relay", 8097, "full"),

    # creator — full FanStack ops, no system admin
    ("creator", "Sovereign OS Portal / FanStack Hub", 3000, "full"),
    ("creator", "Sovereign Sports UI",    3010, "full"),
    ("creator", "FanStack WS Relay",      8008, "full"),
    ("creator", "FanStack Admin API",     8001, "full"),
    ("creator", "FanStack Chatbots",      8009, "full"),
    ("creator", "HoloLink Mesh Relay",    8012, "full"),
    ("creator", "Sovereign Stream Relay", 8097, "full"),

    # stack_manager — full advocate/stack ops, no parent admin
    ("stack_manager", "Sovereign OS Portal / FanStack Hub", 3000, "full"),
    ("stack_manager", "Sovereign Sports UI",    3010, "full"),
    ("stack_manager", "FanStack WS Relay",      8008, "full"),
    ("stack_manager", "FanStack Admin API",     8001, "full"),
    ("stack_manager", "FanStack Chatbots",      8009, "full"),
    ("stack_manager", "HoloLink Mesh Relay",    8012, "full"),
    ("stack_manager", "Sovereign Stream Relay", 8097, "full"),
    ("stack_manager", "Sovereign Core API",     8090, "full"),
    ("stack_manager", "SDLC Ticketing API",     8095, "full"),

    # patron
    ("patron", "Sovereign OS Portal / FanStack Hub", 3000, "full"),
    ("patron", "Sovereign Sports UI",    3010, "full"),
    ("patron", "Sovereign Cinema UI",    3008, "full"),
    ("patron", "FanStack WS Relay",      8008, "read"),
    ("patron", "HoloLink Mesh Relay",    8012, "full"),
    ("patron", "Sovereign Stream Relay", 8097, "full"),

    # investor — show floor only
    ("investor", "Sovereign OS Portal / FanStack Hub", 3000, "read"),
    ("investor", "Sovereign Sports UI", 3010, "read"),
    ("investor", "FanStack WS Relay",   8008, "read"),
    ("investor", "HoloLink Mesh Relay", 8012, "read"),

    # vet_client
    ("vet_client", "AetherVet Portal",    3015, "full"),
    ("vet_client", "HoloLink Mesh Relay", 8012, "full"),

    # garden_client
    ("garden_client", "WildSeed GardenStack", 3016, "full"),
    ("garden_client", "HoloLink Mesh Relay",  8012, "full"),

    # observer
    ("observer", "Sovereign OS Portal / FanStack Hub", 3000, "read"),
    ("observer", "Sovereign Sports UI", 3010, "read"),
    ("observer", "FanStack WS Relay",   8008, "read"),
]

conn = sqlite3.connect(DB_PATH, timeout=30.0)
conn.execute("PRAGMA journal_mode=WAL;")
cur = conn.cursor()

# 2A. Create sys_role Table
cur.execute("""
CREATE TABLE IF NOT EXISTS sys_role (
    sys_id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name            TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    description     TEXT,
    can_be_disabled INTEGER DEFAULT 1,   -- 0 = pilot-class, protected
    sys_created_on  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# 2B. Create sys_role_permission Table
cur.execute("""
CREATE TABLE IF NOT EXISTS sys_role_permission (
    sys_id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    role          TEXT NOT NULL,
    service_name  TEXT NOT NULL,
    port          INTEGER NOT NULL,
    access_level  TEXT NOT NULL DEFAULT 'none',  -- 'full', 'read', 'none'
    sys_created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role, port)
);
""")

for name, display, desc, can_disable in ROLES:
    cur.execute("""
        INSERT OR IGNORE INTO sys_role
            (sys_id, name, display_name, description, can_be_disabled)
        VALUES (?, ?, ?, ?, ?)
    """, (uuid.uuid4().hex, name, display, desc, can_disable))

for role, svc, port, level in PERMISSIONS:
    cur.execute("""
        INSERT OR REPLACE INTO sys_role_permission
            (sys_id, role, service_name, port, access_level)
        VALUES (?, ?, ?, ?, ?)
    """, (uuid.uuid4().hex, role, svc, port, level))

conn.commit()
conn.close()
print("✅ RBAC seed complete.")
