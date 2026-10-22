#!/usr/bin/env python3
"""
StackLabs Ground Truth CLI Query & Opcode Tool (gt)
Path: /home/james/stacklabs/scripts/gt.py
Author: James Carroll (Lead Systems Architect)

Deterministic, sub-millisecond lookup tool on dedicated local hardware.
Eliminates prompt bloat by allowing SLMs and agents to query exact keys directly.
Outputs 4-byte emoji bytecode frames via --frame for machine telemetry.
"""

import sys
import sqlite3
import argparse
import time
from pathlib import Path

DB_PATH = Path("/home/james/stacklabs/data/ground_truth.db")

def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"[ERROR] Ground truth database not found at {DB_PATH}. Run migrate_json_ground_truth_to_sqlite.py first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH), timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn

def cmd_get(key: str, emit_frame: bool = False):
    conn = get_connection()
    t0 = time.perf_counter()
    row = conn.execute("SELECT val, is_shibboleth FROM ground_truth_kv WHERE key = ?", (key,)).fetchone()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if not row:
        # Try suffix or prefix match
        row = conn.execute("SELECT key, val FROM ground_truth_kv WHERE key LIKE ? LIMIT 1", (f"%{key}%",)).fetchone()
        if not row:
            print(f"[NOT_FOUND] Key '{key}' not in ground truth database.", file=sys.stderr)
            sys.exit(1)
        val = row["val"]
    else:
        val = row["val"]

    conn.close()

    if emit_frame:
        # Emit Rosetta Stone Bytecode: [state_cmdb: 💾] [nominal: 🟢] [locked: 🎯] [dispatch: 🚀] :: <key>
        frame = f"💾🟢🎯🚀 :: {key}"
        print(f"{frame} -> {val} ({elapsed_ms:.3f}ms)")
    else:
        print(val)

def cmd_shibboleths():
    conn = get_connection()
    rows = conn.execute("SELECT key, val FROM ground_truth_kv WHERE is_shibboleth = 1 ORDER BY domain, key").fetchall()
    conn.close()
    print("=" * 60)
    print("🏛️ CANONICAL STACKLABS SHIBBOLETHS (ZERO-HALLUCINATION ANCHORS)")
    print("=" * 60)
    for r in rows:
        print(f"• {r['key']}: {r['val']}")
    print("=" * 60)

def cmd_search(term: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, val FROM ground_truth_kv WHERE key LIKE ? OR val LIKE ? LIMIT 20",
        (f"%{term}%", f"%{term}%")
    ).fetchall()
    conn.close()
    if not rows:
        print(f"No results found for '{term}'")
        return
    for r in rows:
        print(f"{r['key']} = {r['val']}")

def cmd_frame(key: str):
    """Outputs raw 4-gram emoji frame for the given ground truth key."""
    conn = get_connection()
    row = conn.execute("SELECT val FROM ground_truth_kv WHERE key = ?", (key,)).fetchone()
    if not row:
        row = conn.execute("SELECT val FROM ground_truth_kv WHERE key LIKE ? LIMIT 1", (f"%{key}%",)).fetchone()
    conn.close()
    if not row:
        print(f"💾🔴🧱✂️ :: {key}")
        sys.exit(1)
    print(f"💾🟢🎯🚀 :: {key}")

def main():
    parser = argparse.ArgumentParser(description="StackLabs Ground Truth CLI Query Engine (gt)")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get
    get_p = subparsers.add_parser("get", help="Retrieve exact ground truth value by key")
    get_p.add_argument("key", help="Ground truth dot-notated key")
    get_p.add_argument("--frame", action="store_true", help="Include 4-byte emoji bytecode frame in output")

    # shibboleths
    subparsers.add_parser("shibboleths", help="List all core invariant shibboleths")

    # search
    search_p = subparsers.add_parser("search", help="Search keys or values")
    search_p.add_argument("term", help="Search keyword")

    # frame
    frame_p = subparsers.add_parser("frame", help="Emit raw 4-byte emoji bytecode frame for key")
    frame_p.add_argument("key", help="Ground truth key")

    args = parser.parse_args()

    if args.command == "get":
        cmd_get(args.key, emit_frame=args.frame)
    elif args.command == "shibboleths":
        cmd_shibboleths()
    elif args.command == "search":
        cmd_search(args.term)
    elif args.command == "frame":
        cmd_frame(args.key)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
