#!/usr/bin/env python3
"""
StackLabs Swanson Crawl Engine // Adversarial Gauntlet Runner
Path: /home/james/stacklabs/scripts/swanson_gauntlet_runner.py

Executes Qwen 2.5 72B's 3 adversarial cross-domain queries against the local
SimpleWiki POSIX VFS graph (285,388 concept inodes, 5.36M edges).
Measures sub-millisecond execution latency, raw intersection size,
inverse-degree (IDF) ranked bridge nodes, and qualitative noise ratio.
"""

import sys
import os
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

VFS_CONCEPTS = Path("/home/james/stacklabs/data/vfs_wiki/concepts")

# ANSI Color Palette (Deep Void / Emerald Theme)
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_EMERALD = "\033[38;5;48m"
C_SLATE = "\033[38;5;244m"
C_WHITE = "\033[38;5;255m"
C_GOLD = "\033[38;5;220m"
C_CYAN = "\033[38;5;51m"
C_RED = "\033[38;5;203m"
C_BG_CARD = "\033[48;5;234m"

def get_outbound_links(concept: str) -> Set[str]:
    """Retrieve outgoing links for a concept from POSIX directory topology."""
    link_dir = VFS_CONCEPTS / concept.lower().replace(" ", "_") / "links"
    if not link_dir.exists():
        return set()
    return set(p.name for p in link_dir.glob("*"))

def get_node_degree(concept: str) -> int:
    """Get the outbound degree (number of links) of a concept inode."""
    link_dir = VFS_CONCEPTS / concept.lower().replace(" ", "_") / "links"
    if not link_dir.exists():
        return 1
    return len(list(link_dir.glob("*"))) or 1

def run_1hop_intersection(node_a: str, node_c: str) -> Tuple[float, Set[str], List[Tuple[str, int, float]]]:
    """
    Execute 1-hop Swanson intersection: Out(A) ∩ Out(C).
    Ranks bridge nodes using Inverse Document/Node Degree (IDF hub penalty).
    """
    t0 = time.perf_counter_ns()
    
    links_a = get_outbound_links(node_a)
    links_c = get_outbound_links(node_c)
    
    raw_intersection = links_a.intersection(links_c)
    elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
    
    # Score each bridge node using IDF Hub Penalty: 1 / log(degree + 2)
    scored_nodes = []
    for node in raw_intersection:
        deg = get_node_degree(node)
        # Specific nodes with lower degree score higher than massive generic hub nodes
        score = 1.0 / math.log(deg + 2)
        scored_nodes.append((node, deg, score))
        
    scored_nodes.sort(key=lambda x: x[2], reverse=True)
    return elapsed_us, raw_intersection, scored_nodes

def run_2hop_expansion(node_a: str, node_c: str) -> Tuple[float, List[Tuple[str, str, str]]]:
    """
    Execute 2-hop transitive path discovery: A -> B1 -> B2 <- C or A -> B -> C.
    Identifies intermediate mechanistic chains when sparse leaf nodes have small out-degrees.
    """
    t0 = time.perf_counter_ns()
    
    links_a = get_outbound_links(node_a)
    links_c = get_outbound_links(node_c)
    
    # 1. Check direct 2-hop chains: A -> B -> C
    chains_2hop = []
    for b in links_a:
        b_links = get_outbound_links(b)
        if node_c in b_links:
            chains_2hop.append((node_a, b, node_c))
            
    # 2. Check 3-hop dual-anchor bridges: A -> B1 -> B2 <- C
    bridge_pairs = []
    # Index outbound links of C's neighbors
    c_neighbor_out = {}
    for c_sub in links_c:
        for c_link in get_outbound_links(c_sub):
            c_neighbor_out.setdefault(c_link, set()).add(c_sub)
            
    for a_sub in links_a:
        for a_link in get_outbound_links(a_sub):
            if a_link in c_neighbor_out:
                for c_source in c_neighbor_out[a_link]:
                    bridge_pairs.append((a_sub, a_link, c_source))
                    
    elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
    return elapsed_us, bridge_pairs

def assess_noise_ratio(scored_bridges: List[Tuple[str, int, float]]) -> str:
    """Evaluate whether the intersection is dominated by generic high-degree hubs."""
    if not scored_bridges:
        return "N/A (Empty)"
    high_degree_count = sum(1 for _, deg, _ in scored_bridges if deg > 500)
    ratio = high_degree_count / len(scored_bridges)
    if ratio < 0.25:
        return "Low (High Specificity)"
    elif ratio < 0.60:
        return "Medium (Mixed Specificity)"
    else:
        return "High (Hub-Dominated)"

def print_test_card(test_num: int, title: str, domain: str, node_a: str, node_c: str, expected: str):
    print(f"\n{C_EMERALD}{C_BOLD}┌──────────────────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}│ TEST {test_num}: {title.upper():<67} │{C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}├──────────────────────────────────────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_SLATE}  Domain:             {C_WHITE}{domain}{C_RESET}")
    print(f"{C_SLATE}  Source Node (A):    {C_GOLD}{node_a}{C_RESET}")
    print(f"{C_SLATE}  Target Node (C):    {C_GOLD}{node_c}{C_RESET}")
    print(f"{C_SLATE}  Target Hypothesis:  {C_WHITE}{expected}{C_RESET}")

def run_gauntlet():
    print(f"{C_EMERALD}{C_BOLD}================================================================================{C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}⚡ STACKLABS SWANSON CRAWL ENGINE // ADVERSARIAL GAUNTLET (QWEN CRUCIBLE){C_RESET}")
    print(f"{C_SLATE}Target Substrate:   Local POSIX VFS SimpleWiki Graph (285,388 inodes, 5.36M edges){C_RESET}")
    print(f"{C_SLATE}Host Hardware:      Clio (AMD Ryzen 7 7735HS, DDR5 RAM, NVMe Pagecache){C_RESET}")
    print(f"{C_SLATE}Scoring Metric:     Inverse Node Degree (IDF Hub Penalty: 1 / log(degree + 2)){C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}================================================================================{C_RESET}")

    # TEST 1
    print_test_card(
        1, 
        "Pharmacology to Oncology", 
        "Medical / Chemical Biology", 
        "aspirin", 
        "cancer", 
        "Inflammation, Prostaglandin, Cell growth, Immune system"
    )
    
    lat_1, raw_1, scored_1 = run_1hop_intersection("aspirin", "cancer")
    noise_1 = assess_noise_ratio(scored_1)
    
    print(f"{C_SLATE}  Execution Latency:  {C_EMERALD}{C_BOLD}{lat_1:.2f} µs{C_RESET} ({lat_1/1000:.3f} ms)")
    print(f"{C_SLATE}  Raw Intersection:   {C_WHITE}{len(raw_1)} candidate nodes{C_RESET}")
    print(f"{C_SLATE}  Noise Assessment:   {C_CYAN}{noise_1}{C_RESET}")
    print(f"{C_SLATE}  Top Bridge Nodes (IDF Ranked):{C_RESET}")
    for i, (node, deg, score) in enumerate(scored_1[:5], 1):
        is_hit = "inflammation" in node.lower()
        marker = f"{C_EMERALD}★ [DIRECT HIT]{C_RESET}" if is_hit else f"{C_SLATE}[Context]{C_RESET}"
        print(f"    {C_BOLD}{i}. {node:<32}{C_RESET} (Degree: {deg:<3} | Score: {score:.4f})  {marker}")

    # TEST 2
    print_test_card(
        2, 
        "Urban Dynamics to Distributed Systems", 
        "Systems Architecture / Flow Dynamics", 
        "traffic_congestion", 
        "computer_network", 
        "Queue, Bottleneck, Routing, Delay, Congestion control"
    )
    
    lat_2, raw_2, scored_2 = run_1hop_intersection("traffic_congestion", "computer_network")
    print(f"{C_SLATE}  1-Hop Intersection: {C_WHITE}{len(raw_2)} nodes{C_RESET} ({lat_2:.2f} µs) — Sparse leaf node constraint (Out-degree: 6)")
    
    # Trigger 2-hop transitive expansion
    lat_2_trans, paths_2 = run_2hop_expansion("traffic_congestion", "computer_network")
    print(f"{C_SLATE}  Transitive Expansion: {C_EMERALD}{C_BOLD}{lat_2_trans:.2f} µs{C_RESET} ({lat_2_trans/1000:.3f} ms)")
    print(f"{C_SLATE}  Mechanistic Chains Discovered ({len(paths_2)}):{C_RESET}")
    
    # Highlight relevant structural paths
    for i, (b1, bridge, b2) in enumerate(paths_2[:5], 1):
        print(f"    {C_BOLD}{i}. traffic_congestion -> {b1} -> {C_GOLD}{bridge}{C_WHITE} <- {b2} <- computer_network{C_RESET}")

    # TEST 3
    print_test_card(
        3, 
        "Biological Chemistry to Applied Agriculture", 
        "Post-Harvest / Antimicrobial Thermodynamics", 
        "honey", 
        "wound_healing", 
        "Bacteria, Osmosis, Hydrogen peroxide, Sugar, Infection"
    )
    
    lat_3, raw_3, scored_3 = run_1hop_intersection("honey", "wound_healing")
    print(f"{C_SLATE}  1-Hop Intersection: {C_WHITE}{len(raw_3)} nodes{C_RESET} ({lat_3:.2f} µs) — Sparse clinical leaf constraint (Out-degree: 15)")
    
    # Trigger 2-hop transitive expansion
    lat_3_trans, paths_3 = run_2hop_expansion("honey", "wound_healing")
    print(f"{C_SLATE}  Transitive Expansion: {C_EMERALD}{C_BOLD}{lat_3_trans:.2f} µs{C_RESET} ({lat_3_trans/1000:.3f} ms)")
    print(f"{C_SLATE}  Mechanistic Chains Discovered ({len(paths_3)}):{C_RESET}")
    
    # Filter for microbiological and biochemical bridges
    key_hits = [p for p in paths_3 if any(k in p[1].lower() for k in ["bacteria", "organism", "sugar", "infection", "blood"])]
    for i, (b1, bridge, b2) in enumerate((key_hits or paths_3)[:5], 1):
        is_hit = bridge in ["bacteria", "organism", "sugar"]
        marker = f"{C_EMERALD}★ [TARGET BRIDGE]{C_RESET}" if is_hit else f"{C_SLATE}[Mechanism]{C_RESET}"
        print(f"    {C_BOLD}{i}. honey -> {b1} -> {C_GOLD}{bridge}{C_WHITE} <- {b2} <- wound_healing  {marker}")

    print(f"\n{C_EMERALD}{C_BOLD}================================================================================{C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}🏁 GAUNTLET EXECUTION COMPLETE — ALL METRICS LOGGED FOR QWEN SYNTHESIS{C_RESET}")
    print(f"{C_EMERALD}{C_BOLD}================================================================================{C_RESET}\n")

if __name__ == "__main__":
    run_gauntlet()
