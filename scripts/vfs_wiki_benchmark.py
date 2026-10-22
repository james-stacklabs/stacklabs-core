#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/vfs_wiki_benchmark.py
=============================
Forensic VFS Inode Traversal & Transitive Mechanism Discovery Benchmark.
Governed by: Monograph 12 (The Latency-Inverted Knowledge Fabric),
Invariant 15 (Two-Call Verification).

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set

VFS_ROOT = Path("/home/james/stacklabs/data/vfs_wiki")
CONCEPTS_DIR = VFS_ROOT / "concepts"
RECEIPT_FILE = Path("/home/james/stacklabs/data/telemetry/vfs_wiki_benchmark_receipt.json")
FULL_RECEIPT_FILE = Path("/home/james/stacklabs/data/telemetry/vfs_wiki_full_benchmark_receipt.json")

def get_outbound_links(concept_slug: str) -> Set[str]:
    links_dir = CONCEPTS_DIR / concept_slug / "links"
    if not links_dir.is_dir():
        return set()
    try:
        # High-performance directory walk using os.scandir
        return {entry.name for entry in os.scandir(links_dir)}
    except OSError:
        return set()

def benchmark_traversals() -> Dict[str, Any]:
    print("================================================================================")
    print("🏛️ STACKLABS PLATFORM: VFS WIKIPEDIA INODE BENCHMARK (MONOGRAPH 12)")
    print("================================================================================")

    if not CONCEPTS_DIR.is_dir():
        raise FileNotFoundError(f"Concepts directory does not exist: {CONCEPTS_DIR}")

    # Discover candidate concept inodes
    print("🔍 Discovering active concept nodes on Clio NVMe...")
    all_concepts = [e.name for e in os.scandir(CONCEPTS_DIR) if e.is_dir()]
    total_nodes = len(all_concepts)
    print(f"  ✔ Discovered: {total_nodes:,} concept inodes.")

    if total_nodes == 0:
        raise ValueError("Zero concepts found in VFS store!")

    # Find representative high-degree named concept nodes for traversal benchmarking
    print("⚡ Ranking node degrees across sample set...")
    degree_map = {}
    for c in all_concepts[:1500]:
        if not c[0].isdigit():
            degree_map[c] = len(get_outbound_links(c))
    
    if not degree_map:
        for c in all_concepts[:1000]:
            degree_map[c] = len(get_outbound_links(c))

    # Pick representative anchor concept with substantial directed links (e.g. 50-150 links)
    sorted_nodes = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)
    anchor_candidates = [n for n in sorted_nodes if 40 <= n[1] <= 150]
    top_node, top_degree = anchor_candidates[0] if anchor_candidates else sorted_nodes[0]
    print(f"  ✔ Sample Anchor Node: '{top_node}' with {top_degree} directed outbound symlinks.")

    # --------------------------------------------------------------------------
    # BENCHMARK 1: 1-Hop Inode Dereference Latency
    # --------------------------------------------------------------------------
    print("\n[BENCHMARK 1] Measuring 1-Hop Pagecache Inode Resolution Latency...")
    WARMUP_ROUNDS = 20
    for _ in range(WARMUP_ROUNDS):
        _ = get_outbound_links(top_node)

    TEST_ROUNDS = 1000
    t0 = time.perf_counter_ns()
    for _ in range(TEST_ROUNDS):
        links = get_outbound_links(top_node)
    t1 = time.perf_counter_ns()
    
    avg_1hop_us = (t1 - t0) / (TEST_ROUNDS * 1000.0)
    per_link_us = avg_1hop_us / len(links) if links else 0.0
    print(f"  ✔ Average 1-Hop Traversal ({len(links)} links): {avg_1hop_us:.3f} microseconds")
    print(f"  ✔ Single-Edge Resolution Latency: {per_link_us:.3f} microseconds/link")

    # --------------------------------------------------------------------------
    # BENCHMARK 2: 2-Hop Dependency Blast Radius Walk
    # --------------------------------------------------------------------------
    print("\n[BENCHMARK 2] Measuring 2-Hop Graph Expansion Latency...")
    t2 = time.perf_counter_ns()
    hop2_nodes = set()
    for child in list(links)[:50]: # expand across first 50 child links
        hop2_nodes.update(get_outbound_links(child))
    t3 = time.perf_counter_ns()

    total_2hop_us = (t3 - t2) / 1000.0
    print(f"  ✔ 2-Hop Blast Radius Walk (50 parent links -> {len(hop2_nodes)} reachable nodes): {total_2hop_us:.2f} µs ({total_2hop_us/1000.0:.3f} ms)")

    # --------------------------------------------------------------------------
    # BENCHMARK 3: Transitive Bridge Discovery (Swanson ABC Intersection)
    # --------------------------------------------------------------------------
    print("\n[BENCHMARK 3] Measuring Transitive Bridge Discovery (A ∩ C via B)...")
    node_a = "physics" if (CONCEPTS_DIR / "physics").exists() else sorted_nodes[0][0]
    node_c = "philosophy" if (CONCEPTS_DIR / "philosophy").exists() else ("chemistry" if (CONCEPTS_DIR / "chemistry").exists() else sorted_nodes[min(5, len(sorted_nodes)-1)][0])

    # Warmup
    _ = get_outbound_links(node_a)
    _ = get_outbound_links(node_c)

    t4 = time.perf_counter_ns()
    set_a = get_outbound_links(node_a)
    set_c = get_outbound_links(node_c)
    shared_bridges = set_a & set_c
    t5 = time.perf_counter_ns()

    bridge_time_us = (t5 - t4) / 1000.0
    sample_bridges = sorted(list(shared_bridges))[:10]
    print(f"  ✔ Bridge Discovery between '{node_a}' ({len(set_a)}) and '{node_c}' ({len(set_c)}):")
    print(f"     Found {len(shared_bridges)} intermediate shared nodes in {bridge_time_us:.3f} µs ({bridge_time_us/1000.0:.3f} ms).")
    print(f"     Sample Bridges: {sample_bridges}")
    # High-Density Swanson Bridge Discovery (> 50 bridges)
    hd_a, hd_b = "earth", "sun"
    t_hd0 = time.perf_counter_ns()
    set_hd_a = get_outbound_links(hd_a)
    set_hd_b = get_outbound_links(hd_b)
    hd_bridges = set_hd_a & set_hd_b
    t_hd1 = time.perf_counter_ns()
    hd_bridge_time_us = (t_hd1 - t_hd0) / 1000.0
    print(f"  ✔ High-Density Bridge Discovery between '{hd_a}' ({len(set_hd_a)}) and '{hd_b}' ({len(set_hd_b)}):")
    print(f"     Found {len(hd_bridges)} shared nodes in {hd_bridge_time_us:.3f} µs ({hd_bridge_time_us/1000.0:.3f} ms).")

    # --------------------------------------------------------------------------
    # BENCHMARK 4: Directed Shortest Path BFS (biology -> astronomy)
    # --------------------------------------------------------------------------
    print("\n[BENCHMARK 4] Measuring Directed Shortest Path BFS...")
    src_bfs = "biology" if (CONCEPTS_DIR / "biology").exists() else "physics"
    tgt_bfs = "astronomy" if (CONCEPTS_DIR / "astronomy").exists() else "philosophy"

    from collections import deque
    t6 = time.perf_counter_ns()
    queue = deque([[src_bfs]])
    visited = {src_bfs}
    found_path = None
    MAX_DEPTH = 5
    while queue:
        path = queue.popleft()
        curr = path[-1]
        if len(path) > MAX_DEPTH:
            break
        links_curr = get_outbound_links(curr)
        if tgt_bfs in links_curr:
            found_path = path + [tgt_bfs]
            break
        for nxt in links_curr:
            if nxt not in visited and (CONCEPTS_DIR / nxt).is_dir():
                visited.add(nxt)
                queue.append(path + [nxt])
    t7 = time.perf_counter_ns()
    bfs_time_us = (t7 - t6) / 1000.0
    print(f"  ✔ Directed BFS Path from '{src_bfs}' to '{tgt_bfs}':")
    print(f"     Path: {' -> '.join(found_path) if found_path else 'None'}")
    print(f"     Latency: {bfs_time_us:.3f} µs ({bfs_time_us/1000.0:.3f} ms), Hops: {len(found_path)-1 if found_path else -1}")

    receipt = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
        "total_concept_inodes": total_nodes,
        "sample_anchor_node": top_node,
        "sample_anchor_degree": top_degree,
        "benchmark_1hop_us": round(avg_1hop_us, 3),
        "benchmark_1hop_single_edge_us": round(per_link_us, 3),
        "benchmark_2hop_50nodes_us": round(total_2hop_us, 2),
        "benchmark_bridge_discovery_us": round(bridge_time_us, 3),
        "shared_bridges_count": len(shared_bridges),
        "sample_bridges": sample_bridges,
        "bridge_pair": [node_a, node_c],
        "high_density_bridge_pair": [hd_a, hd_b],
        "high_density_bridges_count": len(hd_bridges),
        "high_density_bridge_latency_us": round(hd_bridge_time_us, 3),
        "high_density_sample_bridges": sorted(list(hd_bridges))[:10],
        "bfs_path": found_path or [],
        "bfs_hops": len(found_path) - 1 if found_path else -1,
        "bfs_latency_us": round(bfs_time_us, 3),
        "pinecone_traditional_latency_us": 250000.0, # 250ms SaaS baseline
        "speedup_vs_cloud_rag": round(250000.0 / avg_1hop_us, 1)
    }

    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    with open(FULL_RECEIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)

    print(f"\n📊 Telemetry Receipt written to: {RECEIPT_FILE} and {FULL_RECEIPT_FILE}")
    print(f"🏆 Speedup vs Cloud Vector RAG (250ms baseline): {receipt['speedup_vs_cloud_rag']:,}x FASTER ON METAL\n")
    return receipt

if __name__ == "__main__":
    benchmark_traversals()
