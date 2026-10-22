#!/usr/bin/env python3
"""
StackLabs Ground Truth JSON to SQLite WAL Migrator
Path: /home/james/stacklabs/scripts/migrate_json_ground_truth_to_sqlite.py
Author: James Carroll (Lead Systems Architect)

Reads the 4 canonical JSON ledgers from /home/james/stacklabs/ground_truth/
and compiles them into an ultra-fast, indexed SQLite database running in WAL mode:
/home/james/stacklabs/data/ground_truth.db
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

VAULT_DIR = Path("/home/james/stacklabs/ground_truth")
DB_PATH = Path("/home/james/stacklabs/data/ground_truth.db")

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize ground_truth.db with strict schema, indexes, and WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ground_truth_kv (
            key TEXT PRIMARY KEY,
            val TEXT NOT NULL,
            domain TEXT NOT NULL,
            is_shibboleth INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS partners (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            relationship_status TEXT NOT NULL,
            domain_authority TEXT,
            details_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sports_shibboleths (
            entity_key TEXT PRIMARY KEY,
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            role TEXT NOT NULL,
            season INTEGER NOT NULL,
            invariant_rule TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS architectural_laws (
            law_key TEXT PRIMARY KEY,
            rule_text TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_gt_domain ON ground_truth_kv(domain);
        CREATE INDEX IF NOT EXISTS idx_gt_shibboleth ON ground_truth_kv(is_shibboleth);
        """)
    return conn

def flatten_dict(d: dict, prefix: str = "") -> list:
    """Recursively flattens a nested dictionary into dot-notated key-value tuples."""
    items = []
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, full_key))
        elif isinstance(v, list):
            items.append((full_key, json.dumps(v)))
        else:
            items.append((full_key, str(v)))
    return items

def migrate_ledgers(vault_dir: Path = VAULT_DIR, db_path: Path = DB_PATH) -> int:
    conn = init_db(db_path)
    now_iso = datetime.now().astimezone().isoformat()
    total_keys = 0

    # 1. Ingest compute_ground_truth.json
    compute_path = vault_dir / "compute_ground_truth.json"
    if compute_path.exists():
        compute_data = json.loads(compute_path.read_text(encoding="utf-8"))
        kv_pairs = flatten_dict(compute_data, prefix="compute")
        with conn:
            for k, v in kv_pairs:
                conn.execute(
                    "INSERT OR REPLACE INTO ground_truth_kv (key, val, domain, is_shibboleth, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (k, v, "compute", 0, now_iso)
                )
            # Laws
            laws = compute_data.get("indisputable_architectural_laws", {})
            for law_k, law_text in laws.items():
                conn.execute(
                    "INSERT OR REPLACE INTO architectural_laws (law_key, rule_text, updated_at) VALUES (?, ?, ?)",
                    (law_k, str(law_text), now_iso)
                )
        total_keys += len(kv_pairs)

    # 2. Ingest partner_ground_truth.json
    partner_path = vault_dir / "partner_ground_truth.json"
    if partner_path.exists():
        partner_data = json.loads(partner_path.read_text(encoding="utf-8"))
        kv_pairs = flatten_dict(partner_data, prefix="partner")
        with conn:
            for k, v in kv_pairs:
                is_shib = 1 if "spelling_shibboleths" in k else 0
                conn.execute(
                    "INSERT OR REPLACE INTO ground_truth_kv (key, val, domain, is_shibboleth, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (k, v, "partner", is_shib, now_iso)
                )
            # Structured partners
            for slug, pdata in partner_data.get("partners", {}).items():
                name = pdata.get("name", slug)
                status = pdata.get("status", "ACTIVE")
                auth = pdata.get("domain_authority", "")
                conn.execute(
                    "INSERT OR REPLACE INTO partners (slug, name, relationship_status, domain_authority, details_json, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (slug, name, status, auth, json.dumps(pdata), now_iso)
                )
        total_keys += len(kv_pairs)

    # 3. Ingest sports_ground_truth.json
    sports_path = vault_dir / "sports_ground_truth.json"
    if sports_path.exists():
        sports_data = json.loads(sports_path.read_text(encoding="utf-8"))
        kv_pairs = flatten_dict(sports_data, prefix="sports")
        with conn:
            for k, v in kv_pairs:
                is_shib = 1 if ("roster_shibboleths" in k and any(k.endswith(x) for x in ('.role', '.team', '.nlds_moment', '.note'))) else 0
                conn.execute(
                    "INSERT OR REPLACE INTO ground_truth_kv (key, val, domain, is_shibboleth, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (k, v, "sports", is_shib, now_iso)
                )
            # Roster shibboleths table
            for entity_k, rdata in sports_data.get("roster_shibboleths", {}).items():
                pname = rdata.get("name") or rdata.get("player_name") or entity_k.replace("_", " ").title()
                team = rdata.get("team", "")
                role = rdata.get("role", "")
                season = sports_data.get("season", 2026)
                rule = rdata.get("shibboleth_rule") or rdata.get("nlds_moment") or rdata.get("note") or f"{pname} is {role} for {team}"
                conn.execute(
                    "INSERT OR REPLACE INTO sports_shibboleths (entity_key, player_name, team, role, season, invariant_rule, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entity_k, pname, team, role, season, rule, now_iso)
                )
        total_keys += len(kv_pairs)

    # 4. Ingest quant_ground_truth.json
    quant_path = vault_dir / "quant_ground_truth.json"
    if quant_path.exists():
        quant_data = json.loads(quant_path.read_text(encoding="utf-8"))
        kv_pairs = flatten_dict(quant_data, prefix="quant")
        with conn:
            for k, v in kv_pairs:
                conn.execute(
                    "INSERT OR REPLACE INTO ground_truth_kv (key, val, domain, is_shibboleth, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (k, v, "quant", 0, now_iso)
                )
        total_keys += len(kv_pairs)

    # Insert core high-priority root aliases
    root_aliases = [
        ("sports.steelers.qb", "Aaron Rodgers", "sports", 1),
        ("sports.season", "2026", "sports", 1),
        ("sports.brewers.record", "103-59 (#1 NL Seed)", "sports", 1),
        ("sports.giants.hc", "John Harbaugh", "sports", 1),
        ("sports.titans.oc", "Brian Daboll", "sports", 1),
        ("founder.name", "James Carroll", "partner", 1),
        ("founder.voice", "I", "partner", 1),
        ("founder.corporate_we_allowed", "False", "partner", 1),
        ("company.active_clients", "0", "partner", 1),
        ("company.field_deployments", "0", "partner", 1),
        ("partners.pawel_rudnicki.ranch", "SOLD", "partner", 1),
        ("partners.pawel_rudnicki.safe_status", "$125k SAFE in diligence", "partner", 1),
        ("partners.jeremy_malone.status", "Unclosed prospect scenario (PROSPECT_SCENARIO)", "partner", 1),
        ("compute.clio.hardware", "Beelink SER Mini PC (AMD Ryzen 7 7735HS, 32GB RAM, 0.2ms NVMe)", "compute", 1),
        ("compute.clio.local_inference", "PERMANENTLY_BANNED (APU Protected)", "compute", 1),
        ("compute.tailscale.tls_port", "8088 / 443 (Tailscale HTTPS)", "compute", 1),
    ]

    with conn:
        for k, v, dom, shib in root_aliases:
            conn.execute(
                "INSERT OR REPLACE INTO ground_truth_kv (key, val, domain, is_shibboleth, updated_at) VALUES (?, ?, ?, ?, ?)",
                (k, v, dom, shib, now_iso)
            )

    conn.close()
    return total_keys + len(root_aliases)

if __name__ == "__main__":
    print(f"[*] Compiling Canonical Ground Truth to SQLite: {DB_PATH}")
    count = migrate_ledgers()
    print(f"✅ Successfully compiled {count} keys into {DB_PATH} (WAL mode enabled)")
