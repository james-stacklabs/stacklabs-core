#!/usr/bin/env python3
"""
StackLabs Ground Truth Prompt Packer (Lean Shibboleth Compiler)
Path: /home/james/stacklabs/scripts/pack_ground_truth_context.py
Author: James Carroll (Lead Systems Architect)

Compiles a high-density, ultra-lean Shibboleth Card (< 450 tokens / < 2.5 KB)
from /home/james/stacklabs/data/ground_truth.db.
Replaces the 65 KB nested JSON dump with essential invariant anchors.
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

DB_PATH = Path("/home/james/stacklabs/data/ground_truth.db")
DEFAULT_OUTPUT = Path("/home/james/stacklabs/pilot_drops/GROUND_TRUTH_PROMPT_CONTEXT.md")

def compile_lean_context(db_path: Path = DB_PATH) -> str:
    """Reads shibboleths and core invariants to produce a tight <450 token prompt anchor."""
    now_iso = datetime.now().astimezone().isoformat()

    if not db_path.exists():
        # Fallback if DB not migrated yet
        return f'<GROUND_TRUTH_ANCHOR generated_at="{now_iso}">DB_NOT_MIGRATED</GROUND_TRUTH_ANCHOR>\n'

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Select core root shibboleths (< 450 tokens)
    root_keys = (
        'sports.season',
        'sports.steelers.qb',
        'sports.brewers.record',
        'sports.giants.hc',
        'sports.titans.oc',
        'founder.name',
        'founder.voice',
        'founder.corporate_we_allowed',
        'company.active_clients',
        'company.field_deployments',
        'partners.pawel_rudnicki.ranch',
        'partners.pawel_rudnicki.safe_status',
        'partners.jeremy_malone.status',
        'compute.clio.hardware',
        'compute.clio.local_inference',
        'compute.tailscale.tls_port'
    )
    placeholders = ",".join("?" for _ in root_keys)
    rows = conn.execute(
        f"SELECT key, val FROM ground_truth_kv WHERE key IN ({placeholders}) ORDER BY domain, key",
        root_keys
    ).fetchall()

    conn.close()

    lines = [
        f'<CANONICAL_GROUND_TRUTH generated_at="{now_iso}" engine="sqlite_wal" token_budget="<450">',
        '<!-- StackLabs Bare Metal Ground Truth. Exact empirical facts. Zero JSON bloat. Query CLI: python3 scripts/gt.py get <key> -->',
        "",
        "### 🏛️ CORE REALITY SHIBBOLETHS",
    ]

    for r in rows:
        lines.append(f"- **{r['key']}**: {r['val']}")

    lines.extend([
        "",
        "### ⚡ INDISPUTABLE LAWS & PROTOCOLS",
        "- **The Law of 'I'**: Solo builder voice. Use 'I', 'my', 'the'. Corporate 'we/our' strictly banned.",
        "- **Small Ball on Metal**: High-throughput SQLite WAL and NVMe pagecache. Zero local heavy LLMs on Clio.",
        "- **Campsite Mandate**: Two-call verification required for all mutations. Inspect schema before queries.",
        "- **Zero Plaintext HTTP**: Mandatory Tailscale TLS termination (https://) on all public interfaces.",
        "- **Zero Blind Queries**: Inspect SQLite schemas (PRAGMA table_info, .tables) before executing queries.",
        "",
        "</CANONICAL_GROUND_TRUTH>",
    ])

    return "\n".join(lines) + "\n"

def pack_ground_truth(vault_dir: Path = None, db_path: Path = DB_PATH) -> str:
    """Legacy compatibility alias for compile_lean_context."""
    return compile_lean_context(db_path)

def generate_prompt_context(db_path: Path = DB_PATH, output_path: Path = DEFAULT_OUTPUT, vault_dir: Path = None) -> Path:
    packed_content = compile_lean_context(db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packed_content, encoding="utf-8")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="StackLabs Lean Ground Truth Prompt Packer")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output markdown path")
    parser.add_argument("--db", default=str(DB_PATH), help="Source SQLite DB path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    parser.add_argument("--vault-dir", default=None, help="Legacy vault directory argument")
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    content = compile_lean_context(Path(args.db))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    byte_count = len(content.encode("utf-8"))
    approx_tokens = int(byte_count / 4.2)
    print(f"[PACKER] Generated Lean Ground Truth Context: {out_path} ({byte_count} bytes, ~{approx_tokens} tokens)")

    if args.stdout:
        print(content)

if __name__ == "__main__":
    main()
