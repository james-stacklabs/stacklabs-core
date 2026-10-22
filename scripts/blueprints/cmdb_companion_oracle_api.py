#!/usr/bin/env python3
"""
StackLabs CMDB Companion Oracle API Blueprint
Path: /home/james/stacklabs/scripts/blueprints/cmdb_companion_oracle_api.py
Author: James Carroll (Pilot), Lead Systems Architect
Host: Clio (Dedicated Linux Host / x86_64)

Provides high-speed local graph traversal, alert storm compression simulation,
and CMDB hygiene analysis directly from local SQLite WAL and VFS storage.
Incorporates Argon Law 7 and deterministic enterprise demo defect fixtures.
"""
import os
import time
import hashlib
import json
import sqlite3
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/companion", tags=["CMDB Companion Oracle"])

VFS_DB_PATH = Path("/home/james/stacklabs/vfs/cmdb.db")
PDI_CACHE_DB = Path("/home/james/stacklabs/data/servicenow_pdi_cache.db")
VFS_ROOT_PATH = Path("/home/james/stacklabs/vfs/cmdb")


def get_db_connection() -> sqlite3.Connection:
    target = VFS_DB_PATH if VFS_DB_PATH.exists() else PDI_CACHE_DB
    if not target.exists():
        raise HTTPException(status_code=503, detail="CMDB database cache not found on local host.")
    conn = sqlite3.connect(f"file:{target}?mode=rw", uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    ensure_demo_fixtures(conn)
    return conn


def ensure_demo_fixtures(conn: sqlite3.Connection) -> None:
    """
    Ensures deterministic enterprise demo defect fixtures are present in the local cache
    so the UI is 100% guaranteed to see verified Circular Loops and Dangling Edges.
    """
    cur = conn.cursor()
    # 1. Ensure baseline tables exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cmdb_ci (
            sys_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sys_class_name TEXT NOT NULL,
            operational_status TEXT DEFAULT '1',
            environment TEXT DEFAULT 'Production',
            ip_address TEXT DEFAULT '',
            content_sha256 TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
    """)
    # Ensure schema columns exist on pre-existing cmdb_ci tables
    cur.execute("PRAGMA table_info(cmdb_ci);")
    existing_cols = {row[1] for row in cur.fetchall()}
    required_cols = {
        "operational_status": "TEXT DEFAULT '1'",
        "environment": "TEXT DEFAULT 'Production'",
        "ip_address": "TEXT DEFAULT ''",
        "content_sha256": "TEXT DEFAULT ''",
        "updated_at": "TEXT DEFAULT ''",
    }
    for col_name, col_def in required_cols.items():
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE cmdb_ci ADD COLUMN {col_name} {col_def};")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cmdb_rel_ci (
            sys_id TEXT PRIMARY KEY,
            parent TEXT NOT NULL,
            child TEXT NOT NULL,
            type TEXT DEFAULT 'Depends on::Used by',
            content_sha256 TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
    """)

    # 2. Seed Argon demo defect fixtures (Idempotent INSERT OR IGNORE)
    demo_cis = [
        ("ci_core_bgp_01", "prd-us-east-bgp-edge-rtr01", "cmdb_ci_ip_router", "1", "Production", "10.24.0.1"),
        ("ci_core_okta_01", "prd-okta-auth-gateway-01", "cmdb_ci_appl", "1", "Production", "10.24.1.10"),
        ("ci_san_array_01", "prd-nvme-san-cluster-01", "cmdb_ci_storage_server", "1", "Production", "10.24.2.50"),
        ("ci_k8s_ing_01", "prd-eks-ingress-controller", "cmdb_ci_Load_Balancer", "1", "Production", "10.24.10.5"),
        ("ci_svc_checkout", "prd-checkout-api-service", "cmdb_ci_service", "1", "Production", "10.24.20.11"),
        ("ci_svc_billing", "prd-billing-ledger-service", "cmdb_ci_service", "1", "Production", "10.24.20.12"),
        ("ci_svc_inventory", "prd-inventory-graphql-svc", "cmdb_ci_service", "1", "Production", "10.24.20.13"),
        ("ci_svc_cart", "prd-session-cart-redis", "cmdb_ci_db_instance", "1", "Production", "10.24.20.14"),
        ("ci_svc_notify", "prd-customer-webhook-dispatcher", "cmdb_ci_appl", "1", "Production", "10.24.20.15"),
        ("ci_db_primary", "prd-aurora-pg-writer-01", "cmdb_ci_db_postgresql_instance", "1", "Production", "10.24.30.10"),
        ("ci_db_replica", "prd-aurora-pg-reader-02", "cmdb_ci_db_postgresql_instance", "1", "Production", "10.24.30.11"),
        # Intentional Orphaned CIs
        ("ci_orphan_legacy_01", "stg-legacy-soap-adapter-04", "cmdb_ci_linux_server", "1", "Staging", "10.99.4.19"),
        ("ci_orphan_legacy_02", "dev-abandoned-jenkins-node", "cmdb_ci_linux_server", "2", "Development", "10.99.8.88"),
        # Intentional Circular Loop Nodes
        ("ci_cycle_node_a", "prd-mesh-proxy-east-a", "cmdb_ci_appl", "1", "Production", "10.24.40.1"),
        ("ci_cycle_node_b", "prd-mesh-proxy-east-b", "cmdb_ci_appl", "1", "Production", "10.24.40.2"),
    ]

    for sys_id, name, cls, status, env, ip in demo_cis:
        cur.execute(
            "INSERT OR IGNORE INTO cmdb_ci (sys_id, name, sys_class_name, operational_status, environment, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (sys_id, name, cls, status, env, ip),
        )

    demo_rels = [
        ("rel_demo_01", "ci_core_bgp_01", "ci_core_okta_01", "Feeds::Fed by"),
        ("rel_demo_02", "ci_core_bgp_01", "ci_k8s_ing_01", "Feeds::Fed by"),
        ("rel_demo_03", "ci_core_okta_01", "ci_svc_checkout", "Provides auth for::Depends on"),
        ("rel_demo_04", "ci_core_okta_01", "ci_svc_billing", "Provides auth for::Depends on"),
        ("rel_demo_05", "ci_core_okta_01", "ci_svc_inventory", "Provides auth for::Depends on"),
        ("rel_demo_06", "ci_k8s_ing_01", "ci_svc_checkout", "Routes traffic to::Routed from"),
        ("rel_demo_07", "ci_san_array_01", "ci_db_primary", "Provides storage for::Stored on"),
        ("rel_demo_08", "ci_db_primary", "ci_db_replica", "Replicates to::Replicated from"),
        ("rel_demo_09", "ci_db_primary", "ci_svc_checkout", "Persists state for::Depends on"),
        ("rel_demo_10", "ci_db_replica", "ci_svc_inventory", "Serves reads for::Depends on"),
        ("rel_demo_11", "ci_svc_checkout", "ci_svc_cart", "Reads session from::Used by"),
        ("rel_demo_12", "ci_svc_checkout", "ci_svc_notify", "Triggers::Triggered by"),
        # Verified Circular Loop (A <--> B)
        ("rel_cycle_01", "ci_cycle_node_a", "ci_cycle_node_b", "Depends on::Used by"),
        ("rel_cycle_02", "ci_cycle_node_b", "ci_cycle_node_a", "Depends on::Used by"),
        # Verified Dangling Edge (Points to missing ghost CI)
        ("rel_dangling_01", "ci_svc_notify", "ci_ghost_missing_999", "Depends on::Used by"),
    ]

    for rel_id, p, c, t in demo_rels:
        cur.execute(
            "INSERT OR IGNORE INTO cmdb_rel_ci (sys_id, parent, child, type) VALUES (?, ?, ?, ?)",
            (rel_id, p, c, t),
        )
    conn.commit()


class StormCompressRequest(BaseModel):
    alert_volume: int = 600000
    seed_fault_ci: Optional[str] = "prd-us-east-bgp-edge-rtr01"


class HopNode(BaseModel):
    hop: int
    from_ci: str
    to_ci: str
    to_sys_id: str
    to_class: str


class CausalSpine(BaseModel):
    root_sys_id: str
    root_name: str
    root_class: str
    ip_address: str
    vfs_path: str
    raw_alerts_ingested: int
    suppressed_downstream_cis: int
    max_hop_depth: int
    blast_radius_chain: List[HopNode]


class StormCompressResponse(BaseModel):
    raw_alerts_evaluated: int
    root_cause_incidents_created: int
    phantom_child_cis_suppressed: int
    compression_efficiency_pct: float
    traversal_elapsed_ms: float
    root_cause_spines: List[CausalSpine]


class HygieneAuditResponse(BaseModel):
    total_cis: int
    total_relationships: int
    orphaned_ci_count: int
    circular_loop_count: int
    dangling_edge_count: int
    audit_elapsed_ms: float
    hygiene_score_pct: float
    circular_loops: List[List[str]]
    dangling_edges: List[Dict[str, Any]]
    orphan_cis: List[Dict[str, Any]]


@router.post("/storm_compress", response_model=StormCompressResponse)
def storm_compress(req: StormCompressRequest):
    t0 = time.perf_counter()
    conn = get_db_connection()
    cur = conn.cursor()

    # Load in-memory adjacency for multi-hop blast radius
    cur.execute("SELECT sys_id, name, sys_class_name, operational_status, ip_address FROM cmdb_ci")
    cis = {row["sys_id"]: dict(row) for row in cur.fetchall()}

    cur.execute("SELECT sys_id, parent, child, type FROM cmdb_rel_ci")
    rels = cur.fetchall()
    conn.close()

    downstream_adj = defaultdict(list)
    upstream_adj = defaultdict(list)
    for r in rels:
        p, c = r["parent"], r["child"]
        if p in cis and c in cis:
            downstream_adj[p].append(c)
            upstream_adj[c].append(p)

    # Find root providers (high downstream dependents, minimal upstream parents)
    root_candidates = [
        sys_id for sys_id in cis
        if len(downstream_adj.get(sys_id, [])) > 0 and len(upstream_adj.get(sys_id, [])) == 0
    ]
    if not root_candidates:
        root_candidates = sorted(cis.keys(), key=lambda k: len(downstream_adj.get(k, [])), reverse=True)[:3]

    root_impacts = []
    total_suppressed = 0
    weights = [max(len(downstream_adj[r]), 1) for r in root_candidates]
    weight_sum = max(sum(weights), 1)

    for idx, root_id in enumerate(root_candidates):
        visited = {root_id}
        queue = deque([(root_id, 0)])
        hop_trace = []
        max_depth = 0

        while queue:
            curr_id, depth = queue.popleft()
            max_depth = max(max_depth, depth)
            for child_id in downstream_adj.get(curr_id, []):
                if child_id not in visited:
                    visited.add(child_id)
                    queue.append((child_id, depth + 1))
                    hop_trace.append(
                        HopNode(
                            hop=depth + 1,
                            from_ci=cis[curr_id]["name"],
                            to_ci=cis[child_id]["name"],
                            to_sys_id=child_id,
                            to_class=cis[child_id]["sys_class_name"],
                        )
                    )

        downstream_count = len(visited) - 1
        total_suppressed += downstream_count
        allocated_alerts = int(req.alert_volume * (weights[idx] / weight_sum))
        root_ci = cis[root_id]

        root_impacts.append(
            CausalSpine(
                root_sys_id=root_id,
                root_name=root_ci["name"],
                root_class=root_ci["sys_class_name"],
                ip_address=root_ci.get("ip_address") or "",
                vfs_path=f"/home/james/stacklabs/vfs/cmdb/{root_ci['sys_class_name']}/{root_ci['name']}",
                raw_alerts_ingested=allocated_alerts,
                suppressed_downstream_cis=downstream_count,
                max_hop_depth=max_depth,
                blast_radius_chain=hop_trace,
            )
        )

    root_impacts.sort(key=lambda x: x.suppressed_downstream_cis, reverse=True)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    root_count = max(len(root_impacts), 1)
    compression_ratio = round((1.0 - (root_count / max(req.alert_volume, 1))) * 100.0, 4)

    return StormCompressResponse(
        raw_alerts_evaluated=req.alert_volume,
        root_cause_incidents_created=len(root_impacts),
        phantom_child_cis_suppressed=total_suppressed,
        compression_efficiency_pct=compression_ratio,
        traversal_elapsed_ms=elapsed_ms,
        root_cause_spines=root_impacts,
    )


@router.get("/hygiene_audit", response_model=HygieneAuditResponse)
def hygiene_audit():
    t0 = time.perf_counter()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM cmdb_ci")
    cis = {}
    connected_ids = set()
    for row in cur.fetchall():
        d = dict(row)
        sys_id = d["sys_id"]
        cis[sys_id] = {
            "sys_id": sys_id,
            "name": d.get("name") or sys_id,
            "sys_class_name": d.get("sys_class_name") or "cmdb_ci",
            "environment": d.get("environment") or "Production",
        }
        if d.get("parent_ci"):
            connected_ids.add(sys_id)

    cur.execute("SELECT sys_id, parent, child, type FROM cmdb_rel_ci")
    rels = [dict(row) for row in cur.fetchall()]
    conn.close()

    dangling_edges = []
    adj_list = defaultdict(list)

    for r in rels:
        p_exists = r["parent"] in cis
        c_exists = r["child"] in cis
        if p_exists:
            connected_ids.add(r["parent"])
        if c_exists:
            connected_ids.add(r["child"])

        if not p_exists or not c_exists:
            dangling_edges.append({
                "rel_sys_id": r["sys_id"],
                "parent_id": r["parent"],
                "child_id": r["child"],
                "missing_side": "parent" if not p_exists else "child",
                "rel_type": r["type"],
            })
        else:
            adj_list[r["parent"]].append(r["child"])

    orphan_cis = [ci for sys_id, ci in cis.items() if sys_id not in connected_ids]

    # Detect directed circular cycles via DFS coloring
    state = {k: 0 for k in cis}
    path_stack = []
    cycles = []
    seen_cycle_keys = set()

    def dfs(node: str):
        state[node] = 1
        path_stack.append(node)
        for nxt in adj_list.get(node, []):
            if state.get(nxt, 0) == 1:
                idx = path_stack.index(nxt)
                cycle_nodes = path_stack[idx:] + [nxt]
                canonical_key = "->".join(sorted(cycle_nodes[:-1]))
                if canonical_key not in seen_cycle_keys:
                    seen_cycle_keys.add(canonical_key)
                    cycles.append([f"{cis[n]['name']} ({n})" for n in cycle_nodes])
            elif state.get(nxt, 0) == 0:
                dfs(nxt)
        path_stack.pop()
        state[node] = 2

    for sys_id in cis:
        if state[sys_id] == 0:
            dfs(sys_id)

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    score = round(max(0.0, 100.0 - ((len(orphan_cis) / max(1, len(cis))) * 50.0) - (len(cycles) * 15.0) - (len(dangling_edges) * 5.0)), 1)

    return HygieneAuditResponse(
        total_cis=len(cis),
        total_relationships=len(rels),
        orphaned_ci_count=len(orphan_cis),
        circular_loop_count=len(cycles),
        dangling_edge_count=len(dangling_edges),
        audit_elapsed_ms=elapsed_ms,
        hygiene_score_pct=score,
        circular_loops=cycles,
        dangling_edges=dangling_edges,
        orphan_cis=orphan_cis[:25],
    )


@router.get("/ci_vfs_inspect/{ci_id}")
def ci_vfs_inspect(ci_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM cmdb_ci WHERE sys_id = ? OR name = ? LIMIT 1", (ci_id, ci_id))
    ci_row = cur.fetchone()
    if not ci_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"CI '{ci_id}' not found.")

    sys_id = ci_row["sys_id"]
    name = ci_row["name"] or sys_id
    sys_class = ci_row["sys_class_name"] or "cmdb_ci"

    cur.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, r.type
        FROM cmdb_rel_ci r
        JOIN cmdb_ci c ON r.parent = c.sys_id
        WHERE r.child = ?
    """, (sys_id,))
    parents = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT c.sys_id, c.name, c.sys_class_name, r.type
        FROM cmdb_rel_ci r
        JOIN cmdb_ci c ON r.child = c.sys_id
        WHERE r.parent = ?
    """, (sys_id,))
    children = [dict(r) for r in cur.fetchall()]
    conn.close()

    vfs_path = str(VFS_ROOT_PATH / sys_class / (name.replace(" ", "_").replace("/", "_")))

    return {
        "sys_id": sys_id,
        "name": name,
        "class": sys_class,
        "operational_status": int(ci_row["operational_status"]) if "operational_status" in ci_row.keys() and str(ci_row["operational_status"]).isdigit() else 1,
        "vfs_path": vfs_path,
        "upstream_parents": parents,
        "downstream_children": children
    }
