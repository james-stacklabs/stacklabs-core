#!/usr/bin/env python3
"""
StackLabs Rail Interlocking: VFS Topology Seeder & SQLite WAL Master
Path: /home/james/stacklabs/scripts/seed_rail_interlocking.py
Author: James Carroll (Pilot) & Cockpit Architect
Target Silicon: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
"""
import os
import sys
import shutil
import sqlite3
import time
from pathlib import Path

VFS_RAIL = Path("/dev/shm/vfs/rail")
DB_PATH = Path("/home/james/stacklabs/vfs/rail_telemetry.db")

def init_rail_master_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize master SQLite WAL database for rail topology and flight recorder ledger."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rail_blocks (
                id TEXT PRIMARY KEY,
                occupied INTEGER NOT NULL,
                speed_limit_mph INTEGER NOT NULL,
                signal_aspect TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rail_switches (
                id TEXT PRIMARY KEY,
                alignment TEXT NOT NULL,
                locked INTEGER NOT NULL,
                points_detected TEXT NOT NULL,
                facing_block_id TEXT,
                normal_block_id TEXT,
                reverse_block_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rail_trains (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                speed_mph REAL NOT NULL,
                heading TEXT NOT NULL,
                emergency_brake TEXT NOT NULL,
                reserved_block_id TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rail_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source_entity TEXT NOT NULL,
                details TEXT NOT NULL,
                latency_us REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    return conn

def seed_rail_vfs(clean: bool = True):
    """Seed the /dev/shm/vfs/rail hierarchy with blocks, switches, and competing trains."""
    if clean and VFS_RAIL.exists():
        shutil.rmtree(VFS_RAIL)
    
    blocks_dir = VFS_RAIL / "track_blocks"
    switches_dir = VFS_RAIL / "switches"
    trains_dir = VFS_RAIL / "trains"
    
    blocks_dir.mkdir(parents=True, exist_ok=True)
    switches_dir.mkdir(parents=True, exist_ok=True)
    trains_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Track Blocks
    # Block 101: Shared physical block (turnout junction / single main)
    b101 = blocks_dir / "block_101"
    b101.mkdir(parents=True, exist_ok=True)
    (b101 / "occupied.txt").write_text("1\n")
    (b101 / "speed_limit_mph.txt").write_text("45\n")
    (b101 / "signal_aspect.txt").write_text("CLEAR\n")

    # Block 102: Approach block from East
    b102 = blocks_dir / "block_102"
    b102.mkdir(parents=True, exist_ok=True)
    (b102 / "occupied.txt").write_text("0\n")
    (b102 / "speed_limit_mph.txt").write_text("60\n")
    (b102 / "signal_aspect.txt").write_text("APPROACH\n")
    # Relative symlink to next block
    (b102 / "next_block").symlink_to("../block_101")

    # Siding 01: Diverging safety siding
    siding = blocks_dir / "siding_01"
    siding.mkdir(parents=True, exist_ok=True)
    (siding / "occupied.txt").write_text("0\n")
    (siding / "speed_limit_mph.txt").write_text("15\n")
    (siding / "signal_aspect.txt").write_text("RESTRICTING\n")

    # 2. Switches / Turnouts
    sw1 = switches_dir / "turnout_01"
    sw1.mkdir(parents=True, exist_ok=True)
    (sw1 / "alignment.txt").write_text("NORMAL\n")
    (sw1 / "locked.txt").write_text("1\n")
    (sw1 / "points_detected.txt").write_text("NORMAL\n")
    (sw1 / "facing_block").symlink_to("../../track_blocks/block_102")
    (sw1 / "normal_block").symlink_to("../../track_blocks/block_101")
    (sw1 / "reverse_block").symlink_to("../../track_blocks/siding_01")

    # 3. Competing Trains (Head-On Collision Hazard)
    # Train East (NS-9112 eastbound)
    teast = trains_dir / "train_east"
    teast_route = teast / "route"
    teast_route.mkdir(parents=True, exist_ok=True)
    (teast / "id.txt").write_text("NS-9112\n")
    (teast / "speed_mph.txt").write_text("42\n")
    (teast / "heading.txt").write_text("EAST\n")
    (teast / "emergency_brake.txt").write_text("RELEASED\n")
    (teast_route / "01").symlink_to("../../../track_blocks/block_101")

    # Train West (CSX-4004 westbound)
    twest = trains_dir / "train_west"
    twest_route = twest / "route"
    twest_route.mkdir(parents=True, exist_ok=True)
    (twest / "id.txt").write_text("CSX-4004\n")
    (twest / "speed_mph.txt").write_text("38\n")
    (twest / "heading.txt").write_text("WEST\n")
    (twest / "emergency_brake.txt").write_text("RELEASED\n")
    # Same physical block reservation -> Exact Inode Collision!
    (twest_route / "01").symlink_to("../../../track_blocks/block_101")

def seed_rail_master_db(conn: sqlite3.Connection):
    """Populate master DB with initial state matching VFS."""
    with conn:
        conn.execute("DELETE FROM rail_blocks")
        conn.execute("DELETE FROM rail_switches")
        conn.execute("DELETE FROM rail_trains")
        
        conn.executemany("""
            INSERT INTO rail_blocks (id, occupied, speed_limit_mph, signal_aspect)
            VALUES (?, ?, ?, ?)
        """, [
            ("block_101", 1, 45, "CLEAR"),
            ("block_102", 0, 60, "APPROACH"),
            ("siding_01", 0, 15, "RESTRICTING")
        ])
        
        conn.execute("""
            INSERT INTO rail_switches (id, alignment, locked, points_detected, facing_block_id, normal_block_id, reverse_block_id)
            VALUES ('turnout_01', 'NORMAL', 1, 'NORMAL', 'block_102', 'block_101', 'siding_01')
        """)
        
        conn.executemany("""
            INSERT INTO rail_trains (id, name, speed_mph, heading, emergency_brake, reserved_block_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("train_east", "NS-9112", 42.0, "EAST", "RELEASED", "block_101"),
            ("train_west", "CSX-4004", 38.0, "WEST", "RELEASED", "block_101")
        ])

if __name__ == "__main__":
    print("[*] Seeding Rail VFS in /dev/shm/vfs/rail...")
    seed_rail_vfs(clean=True)
    print("[+] Rail VFS initialized.")
    print(f"[*] Initializing Rail SQLite WAL Master in {DB_PATH}...")
    db_conn = init_rail_master_db()
    seed_rail_master_db(db_conn)
    db_conn.close()
    print("[+] Master database initialized and seeded.")
