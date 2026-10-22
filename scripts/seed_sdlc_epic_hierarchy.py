"""
Seed script for Sovereign OS SDLC Initiatives, Epics, Features, and Ticket Linkages.
File: /home/james/stacklabs/scripts/seed_sdlc_epic_hierarchy.py
"""
import sqlite3
import os

DB_PATH = 'y:/dna/sovereign_now.db'

INITIATIVES = [
    {
        "initiative_id": "INIT-001",
        "name": "Sovereign OS Core Platform & ITSM Governance",
        "code": "SOV-CORE",
        "description": "Foundational operating system orchestration, Iron-Clad CMDB, JIT Approvals, and Enterprise SDLC hierarchy.",
        "owner": "james",
        "status": "ACTIVE",
        "icon": "🏛️",
        "color": "#00b4d8"
    },
    {
        "initiative_id": "INIT-002",
        "name": "FanStack Multi-Sport Live Media & Real-Time Discourse",
        "code": "FANSTACK",
        "description": "Real-time sports simulation streams, multi-agent AI discourse swarms, Statcast telemetry, and interactive stadiums.",
        "owner": "james",
        "status": "ACTIVE",
        "icon": "⚾",
        "color": "#38bdf8"
    },
    {
        "initiative_id": "INIT-003",
        "name": "Generative Autonomous Intelligence & Digital Economy",
        "code": "GEN-AI",
        "description": "Autonomous Spark innovation pipeline, HoloDex Pro Studio V6.0, Parimutuel wagering escrow, and Smyrna Pawn redemption.",
        "owner": "james",
        "status": "ACTIVE",
        "icon": "✨",
        "color": "#a855f7"
    }
]

EPICS = [
    {
        "epic_id": 1,
        "initiative_id": "INIT-003",
        "epic_key": "EPIC-001",
        "epic_name": "Generative Loot, Accolades & Physical-Digital Collectibles",
        "description": "End-to-end loot forge, 7 tangible 3D physical-digital collectibles, parimutuel prediction escrow, and Smyrna Pawn Shop liquidation counter.",
        "owner": "james",
        "status": "RESOLVED",
        "health": "ON_TRACK",
        "color": "#a855f7",
        "risk_level": "LOW",
        "business_value": "Transforms audience passive viewing into active parimutuel engagement with provably scarce on-chain relics.",
        "architecture_spec_url": "dna/docs/HOLODEX_PRO_STUDIO_V6_OPERATIONS_AND_ARCHITECTURE_MANUAL.md",
        "features": [
            {"feature_key": "FEAT-001-1", "title": "HoloDex Pro Studio V6.0 Multi-Mode Forge (Port 3028)", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-001-2", "title": "In-Game Prediction Market & Loot Staking HUD (Port 3010)", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-001-3", "title": "Smyrna Pawn & Relic Redemption Counter", "status": "RESOLVED", "priority": "P2"},
            {"feature_key": "FEAT-001-4", "title": "Flagship 4D Chrono-Artifacts (Big Hurt Cannon Bat & 1986 Game 6 Card)", "status": "RESOLVED", "priority": "P2"}
        ],
        "ticket_matches": ["WO-2026-0826-GENERATIVE-LOOT-WAGERING", "HoloDex", "Loot", "Prediction", "Pawn"]
    },
    {
        "epic_id": 2,
        "initiative_id": "INIT-002",
        "epic_key": "EPIC-002",
        "epic_name": "Multi-Sport Real-Time Telemetry & M.A.R.D. Engine",
        "description": "Predictive pitch tracking, Statcast play-by-play telemetry, multi-agent sports discourse, NFL Gridiron center, and Blunderdome studio.",
        "owner": "james",
        "status": "RESOLVED",
        "health": "ON_TRACK",
        "color": "#38bdf8",
        "risk_level": "LOW",
        "business_value": "Zero-latency multi-sport entertainment infrastructure bypassing commercial cloud API rate limits with private edge NPUs.",
        "architecture_spec_url": "dna/docs/SOVEREIGN_SPORTS_SUITE_AND_TELEMETRY_MANUAL.md",
        "features": [
            {"feature_key": "FEAT-002-1", "title": "Unified MLB/NFL Live Matchup Data Ingestion", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-002-2", "title": "The Blunderdome NFL Studio & Tactile Soundboard", "status": "RESOLVED", "priority": "P2"},
            {"feature_key": "FEAT-002-3", "title": "Statcast Volatility Dialectic & Real-Time Pitch Trails", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-002-4", "title": "Multi-Agent Discourse Swarm (M.A.R.D. Cartridges)", "status": "RESOLVED", "priority": "P1"}
        ],
        "ticket_matches": ["DFCT-2026-0826-BOGGS-SLIDER-PROPAGATION", "ENHC2026082602", "Blunderdome", "MARD", "Statcast", "Sovereign Sports"]
    },
    {
        "epic_id": 3,
        "initiative_id": "INIT-003",
        "epic_key": "EPIC-003",
        "epic_name": "Autonomous Spark Innovation Pipeline & Swarm Mashups",
        "description": "Autonomous background R&D engine discovering platform capabilities, generating multi-service sandbox mashups, and dispatching work orders.",
        "owner": "james",
        "status": "IN_PROGRESS",
        "health": "ON_TRACK",
        "color": "#ec4899",
        "risk_level": "LOW",
        "business_value": "Self-compounding platform capability expansion synthesizing combinatoric work orders during idle cycles.",
        "architecture_spec_url": "dna/docs/SPARK_MASTER_GOVERNANCE_AND_ARCHITECTURE_BIBLE.md",
        "features": [
            {"feature_key": "FEAT-003-1", "title": "Power Tools & Microservices Ground-Truth Catalog Ingestion", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-003-2", "title": "Decision Derby Real-Time Inbox Sorting Hat & Auto-Routing", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-003-3", "title": "Cognitive Sentinel & Synthetic Entropy Anchor Probes", "status": "RESOLVED", "priority": "P2"},
            {"feature_key": "FEAT-003-4", "title": "Automated Sandbox Mashup Seeder & Proof Generator", "status": "IN_PROGRESS", "priority": "P1"}
        ],
        "ticket_matches": ["WO-Mashup-Autonomous-FanKnot-Ambient-Arena-20260827", "STRY2026082701", "Spark", "Mashup", "Sorting Hat", "Decision Derby"]
    },
    {
        "epic_id": 4,
        "initiative_id": "INIT-001",
        "epic_key": "EPIC-004",
        "epic_name": "Enterprise ITSM Governance & 4-Tier SDLC Architecture",
        "description": "Iron-Clad CMDB topology, JIT Mobile & Email Approvals, Visual Twin Dual Verification, and Multi-Level Epic/Feature Hierarchy.",
        "owner": "james",
        "status": "IN_PROGRESS",
        "health": "ON_TRACK",
        "color": "#00b4d8",
        "risk_level": "LOW",
        "business_value": "Certified ServiceNow-grade architectural governance enforcing zero-drift SDLC traceability across multi-agent sessions.",
        "architecture_spec_url": "dna/docs/SDLC_EPIC_HIERARCHY_ARCHITECTURE_AND_OPERATIONS_MANUAL.md",
        "features": [
            {"feature_key": "FEAT-004-1", "title": "SDLC Epic & Feature Hierarchy Data Model & Rollup Engine", "status": "IN_PROGRESS", "priority": "P1"},
            {"feature_key": "FEAT-004-2", "title": "Interactive Epic Hierarchy Explorer & Drill-down Drawer", "status": "IN_PROGRESS", "priority": "P1"},
            {"feature_key": "FEAT-004-3", "title": "Living Kanban Board Epic Swimlanes & Multi-Project Filters", "status": "IN_PROGRESS", "priority": "P1"},
            {"feature_key": "FEAT-004-4", "title": "Visual Twin Validator & Playwright UAT Suite", "status": "RESOLVED", "priority": "P2"}
        ],
        "ticket_matches": ["WO-2026-0827-SDLC-EPIC-HIERARCHY", "WO-2026-0827-MOBILE-COMMAND-DECK", "CMDB", "Approval", "SDLC", "Kanban"]
    },
    {
        "epic_id": 5,
        "initiative_id": "INIT-001",
        "epic_key": "EPIC-005",
        "epic_name": "GreenStack Botanical Intelligence & Microclimate Ops",
        "description": "Decoupled GreenStack 3.0 botanical tracking engine, 42-strain seed bank, 4x4 spatial canopy grid, VPD/DLI microclimate telemetry, and Project Metsy breeding lab.",
        "owner": "james",
        "status": "RESOLVED",
        "health": "ON_TRACK",
        "color": "#22c55e",
        "risk_level": "LOW",
        "business_value": "Autonomous precision horticulture management with physical sensor calibration and genetic lineage tracking.",
        "architecture_spec_url": "dna/docs/GREENSTACK_3_BOTANICAL_OPS_MANUAL.md",
        "features": [
            {"feature_key": "FEAT-005-1", "title": "42-Strain Genetic Seed Bank & Phenotype Tracking", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-005-2", "title": "4x4 Spatial Canopy Microclimate Telemetry (VPD/DLI/PAR)", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-005-3", "title": "Project Metsy Botanical Breeding Lab & Thermal QR Labels", "status": "RESOLVED", "priority": "P2"}
        ],
        "ticket_matches": ["GreenStack", "GardenStack", "Botanical", "WeedStack"]
    },
    {
        "epic_id": 6,
        "initiative_id": "INIT-002",
        "epic_key": "EPIC-006",
        "epic_name": "Tesseract 4D Shaders & Hypercube Collectibles",
        "description": "Interactive 4D Tesseract baseball card timeline scrubber, WebGL chrono-shaders, and Shea Stadium historical physics playback.",
        "owner": "james",
        "status": "RESOLVED",
        "health": "ON_TRACK",
        "color": "#f59e0b",
        "risk_level": "LOW",
        "business_value": "4-dimensional collectible timeline inspection unlocking nostalgic multi-angle game moment reliving.",
        "architecture_spec_url": "dna/docs/TESSERACT_4D_CARD_STAGE_SPEC.md",
        "features": [
            {"feature_key": "FEAT-006-1", "title": "Next.js 4D Tesseract Card Staging Engine (Port 3026)", "status": "RESOLVED", "priority": "P1"},
            {"feature_key": "FEAT-006-2", "title": "1986 Game 6 Chrono-Rally Parallax Shader & Physics Scrubber", "status": "RESOLVED", "priority": "P2"},
            {"feature_key": "FEAT-006-3", "title": "Tesseract Era Registry & Dynamic Trajectory Projection", "status": "RESOLVED", "priority": "P2"}
        ],
        "ticket_matches": ["Tesseract", "Chrono", "1986", "Parallax"]
    }
]

def seed_hierarchy():
    print(f"Seeding SDLC Hierarchy into {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Seed Initiatives
    for init in INITIATIVES:
        cursor.execute("""
            INSERT OR REPLACE INTO sdlc_initiatives (
                initiative_id, name, code, description, owner, status, icon, color, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            init["initiative_id"], init["name"], init["code"], init["description"],
            init["owner"], init["status"], init["icon"], init["color"]
        ))
    print(f"Seeded {len(INITIATIVES)} initiatives.")

    # 2. Seed Epics & Features
    total_features = 0
    for epic in EPICS:
        cursor.execute("""
            INSERT OR REPLACE INTO sovereign_epics (
                epic_id, initiative_id, epic_key, epic_name, description, owner,
                status, health, color, risk_level, business_value, architecture_spec_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            epic["epic_id"], epic["initiative_id"], epic["epic_key"], epic["epic_name"],
            epic["description"], epic["owner"], epic["status"], epic["health"],
            epic["color"], epic["risk_level"], epic["business_value"], epic["architecture_spec_url"]
        ))

        # Features
        for f in epic.get("features", []):
            cursor.execute("""
                INSERT OR REPLACE INTO sdlc_features (
                    epic_id, feature_key, title, status, priority, owner, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'james', CURRENT_TIMESTAMP)
            """, (epic["epic_id"], f["feature_key"], f["title"], f["status"], f["priority"]))
            total_features += 1

        # Link Tickets based on matches
        for match in epic.get("ticket_matches", []):
            cursor.execute("""
                UPDATE sovereign_tickets 
                SET epic_id = ? 
                WHERE (number LIKE ? OR short_description LIKE ? OR description LIKE ?)
                  AND (epic_id IS NULL OR epic_id = ?)
            """, (epic["epic_id"], f"%{match}%", f"%{match}%", f"%{match}%", epic["epic_id"]))

    print(f"Seeded {len(EPICS)} epics and {total_features} features.")

    # Explicitly ensure current ticket WO-2026-0827-SDLC-EPIC-HIERARCHY is linked to EPIC-004
    cursor.execute("""
        UPDATE sovereign_tickets 
        SET epic_id = 4, feature_id = (SELECT feature_id FROM sdlc_features WHERE feature_key = 'FEAT-004-1')
        WHERE number = 'WO-2026-0827-SDLC-EPIC-HIERARCHY'
    """)

    conn.commit()

    # Query Rollup Summary
    cursor.execute("SELECT epic_key, epic_name, total_features, total_tickets, completed_tickets, completion_pct FROM v_sdlc_epic_rollup")
    rows = cursor.fetchall()
    print("\n--- EPIC ROLLUP SUMMARY ---")
    for r in rows:
        print(f"[{r[0]}] {r[1]} -> Features: {r[2]}, Tickets: {r[3]} ({r[4]} Done, {r[5]}%)")

    conn.close()

if __name__ == '__main__':
    seed_hierarchy()
