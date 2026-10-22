#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Topological Cartridge Loader & Shard Registry.
Path: /home/james/stacklabs/scripts/vfs_cartridge_loader.py
Author: James Carroll (Pilot) & Lead Systems Architect

Dynamically attaches, verifies, and merges external domain cartridges
(e.g., Colab-extracted PubMed, USPTO, FERC, SEC EDGAR shards) into the
master SQLite WAL knowledge store at /home/james/stacklabs/vfs/vfs_wiki.db.
Supports incremental microsecond boundary degree updates and full zero-drift recomputes.
"""

import sys
import sqlite3
import argparse
import time
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path

MASTER_DB_PATH = Path("/home/james/stacklabs/vfs/vfs_wiki.db")
DEFAULT_API_RELOAD_URL = "http://127.0.0.1:8088/api/wiki/cache/reload"


def list_cartridges(master_db: Path):
    if not master_db.is_file():
        print(f"Error: Master database does not exist at {master_db}")
        sys.exit(1)

    conn = sqlite3.connect(str(master_db))
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, node_count, edge_count, loaded_at FROM cartridges ORDER BY loaded_at ASC")
    rows = cursor.fetchall()
    conn.close()

    print("====================================================================")
    print("📦 STACKLABS ACTIVE TOPOLOGICAL CARTRIDGES")
    print("====================================================================")
    if not rows:
        print("Zero cartridges registered.")
        return

    for name, desc, nodes, edges, loaded in rows:
        print(f"  • {name}")
        print(f"      Description: {desc}")
        print(f"      Nodes:       {nodes:,}")
        print(f"      Edges:       {edges:,}")
        print(f"      Loaded At:   {loaded}")
    print("====================================================================")


def info_cartridge(cart_path: Path):
    if not cart_path.is_file():
        print(f"Error: Cartridge file not found: {cart_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(cart_path))
    cursor = conn.cursor()
    
    meta = {}
    try:
        cursor.execute("SELECT key, value FROM cartridge_meta")
        meta = dict(cursor.fetchall())
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM concepts")
    node_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM edges")
    edge_count = cursor.fetchone()[0]
    conn.close()

    print("====================================================================")
    print(f"🔍 CARTRIDGE INSPECTION: {cart_path.name}")
    print("====================================================================")
    print(f"  Name:        {meta.get('name', cart_path.stem)}")
    print(f"  Description: {meta.get('description', 'Standalone Cartridge')}")
    print(f"  Domain:      {meta.get('domain', 'Generic')}")
    print(f"  Nodes:       {node_count:,}")
    print(f"  Edges:       {edge_count:,}")
    print(f"  File Size:   {cart_path.stat().st_size / (1024 * 1024):.2f} MB")
    print("====================================================================")


def notify_plane2_cache(url: str = DEFAULT_API_RELOAD_URL):
    try:
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                print(f"  ✔ Plane 2 cache reload notified successfully via {url}.")
    except Exception:
        print(f"  ℹ Plane 2 API service not reachable on {url} (skipping cache reload).")


def update_degrees_incremental(conn_master: sqlite3.Connection, touched_sids: set[int]) -> float:
    t0 = time.perf_counter()
    if not touched_sids:
        return 0.0
    cur = conn_master.cursor()
    params = [(sid, sid) for sid in touched_sids]
    cur.executemany("""
    UPDATE concepts
    SET degree = (SELECT COUNT(*) FROM edges WHERE source_id = ?)
    WHERE id = ?
    """, params)
    conn_master.commit()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms


def update_degrees_full(conn_master: sqlite3.Connection) -> tuple[float, int]:
    t0 = time.perf_counter()
    cur = conn_master.cursor()
    cur.execute("SELECT source_id, COUNT(*) FROM edges GROUP BY source_id")
    counts = cur.fetchall()
    
    cur.execute("UPDATE concepts SET degree = 0")
    cur.executemany("UPDATE concepts SET degree = ? WHERE id = ?", [(cnt, sid) for sid, cnt in counts])
    conn_master.commit()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms, len(counts)


def load_cartridge(master_db: Path, cart_path: Path, degree_mode: str = "both", notify_api: bool = False):
    if not master_db.is_file():
        print(f"Error: Master database does not exist at {master_db}")
        sys.exit(1)
    if not cart_path.is_file():
        print(f"Error: Cartridge file not found at {cart_path}")
        sys.exit(1)

    t0 = time.perf_counter()
    conn_master = sqlite3.connect(str(master_db))
    conn_master.execute("PRAGMA journal_mode = WAL;")
    conn_master.execute("PRAGMA synchronous = OFF;")
    conn_master.execute("PRAGMA busy_timeout = 10000;")

    # Read cartridge metadata
    conn_cart = sqlite3.connect(str(cart_path))
    cur_cart = conn_cart.cursor()
    meta = {}
    try:
        cur_cart.execute("SELECT key, value FROM cartridge_meta")
        meta = dict(cur_cart.fetchall())
    except Exception:
        pass
    cart_name = meta.get("name", cart_path.stem)
    cart_desc = meta.get("description", f"Imported from {cart_path.name}")

    print(f"⚡ Attaching and reconciling cartridge: '{cart_name}'...")

    # Step 1: Reconcile Concepts
    cur_cart.execute("SELECT slug, title, article, metadata_json FROM concepts")
    cart_concepts = cur_cart.fetchall()
    
    cur_master = conn_master.cursor()
    cur_master.executemany("""
    INSERT INTO concepts (slug, title, degree, article, metadata_json)
    VALUES (?, ?, 0, ?, ?)
    ON CONFLICT(slug) DO UPDATE SET
        title = excluded.title,
        article = CASE WHEN excluded.article != '' THEN excluded.article ELSE concepts.article END
    """, cart_concepts)
    conn_master.commit()
    print(f"  ✔ Reconciled {len(cart_concepts):,} concept nodes.")

    # Build master slug to ID map
    cur_master.execute("SELECT slug, id FROM concepts")
    master_slug_to_id = dict(cur_master.fetchall())

    # Build cart ID to slug map
    cur_cart.execute("SELECT id, slug FROM concepts")
    cart_id_to_slug = dict(cur_cart.fetchall())

    # Step 2: Ingest Edges
    cur_cart.execute("SELECT source_id, target_id, rel_type FROM edges")
    cart_edges = cur_cart.fetchall()
    conn_cart.close()

    master_edge_batch = []
    touched_sids = set()
    for c_src, c_tgt, rel in cart_edges:
        s_slug = cart_id_to_slug.get(c_src)
        t_slug = cart_id_to_slug.get(c_tgt)
        if s_slug and t_slug:
            m_src = master_slug_to_id.get(s_slug)
            m_tgt = master_slug_to_id.get(t_slug)
            if m_src and m_tgt and m_src != m_tgt:
                master_edge_batch.append((m_src, m_tgt, rel))
                touched_sids.add(m_src)

    cur_master.executemany("""
    INSERT OR IGNORE INTO edges (source_id, target_id, rel_type)
    VALUES (?, ?, ?)
    """, master_edge_batch)
    conn_master.commit()
    print(f"  ✔ Ingested {len(master_edge_batch):,} directed edges ({len(touched_sids):,} source nodes touched).")

    # Step 3: Register Cartridge Record
    cur_master.execute("""
    INSERT OR REPLACE INTO cartridges (name, description, node_count, edge_count)
    VALUES (?, ?, ?, ?)
    """, (cart_name, cart_desc, len(cart_concepts), len(master_edge_batch)))
    conn_master.commit()

    # Step 4: Degree Recalculation
    inc_degrees = None
    if degree_mode in ("incremental", "both"):
        inc_ms = update_degrees_incremental(conn_master, touched_sids)
        print(f"  ✔ Incremental degree update completed in {inc_ms:.3f} ms.")
        if degree_mode == "both":
            cur_master.execute("SELECT id, degree FROM concepts WHERE degree > 0")
            inc_degrees = dict(cur_master.fetchall())

    if degree_mode in ("full", "both"):
        full_ms, non_zero_count = update_degrees_full(conn_master)
        print(f"  ✔ Full degree recompute completed in {full_ms:.3f} ms ({non_zero_count:,} active nodes).")
        if degree_mode == "both" and inc_degrees is not None:
            cur_master.execute("SELECT id, degree FROM concepts WHERE degree > 0")
            full_degrees = dict(cur_master.fetchall())
            assert inc_degrees == full_degrees, "Mathematical drift detected between incremental and full degree counts!"
            print("  ✔ Zero mathematical drift verified (incremental_degrees == full_degrees).")

    conn_master.close()
    elapsed = time.perf_counter() - t0
    print(f"✔ Successfully loaded cartridge '{cart_name}' in {elapsed:.2f}s.")

    if notify_api:
        notify_plane2_cache()


def main():
    parser = argparse.ArgumentParser(description="StackLabs Topological Cartridge Manager")
    parser.add_argument("--db-path", type=Path, default=MASTER_DB_PATH, help="Master SQLite WAL database")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("list", help="List registered cartridges")
    
    info_p = subparsers.add_parser("info", help="Inspect an external cartridge file")
    info_p.add_argument("file", type=Path, help="Path to .cartridge.db")

    load_p = subparsers.add_parser("load", help="Load an external cartridge into master store")
    load_p.add_argument("file", type=Path, help="Path to .cartridge.db")
    load_p.add_argument("--degree-mode", choices=["incremental", "full", "both"], default="both", help="Degree calculation mode")
    load_p.add_argument("--notify-api", action="store_true", help="Notify Plane 2 API server to reload cache")

    args = parser.parse_args()

    if args.subcommand == "list":
        list_cartridges(args.db_path)
    elif args.subcommand == "info":
        info_cartridge(args.file)
    elif args.subcommand == "load":
        load_cartridge(args.db_path, args.file, degree_mode=args.degree_mode, notify_api=args.notify_api)


if __name__ == "__main__":
    main()
