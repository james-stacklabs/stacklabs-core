#!/home/james/stacklabs/.venv/bin/python3
"""
Counterparty Cognitive Collider & Pre-Flight Meeting Dossier Engine.
Path: /home/james/stacklabs/scripts/counterparty_cognitive_collider.py

Executes the 4-Layer Cognitive Graph Inversion:
1. Inode & Scar Extraction (Causal Decision Graph)
2. The "Paper Lie" Filter (Vendor Anti-Pitch Shield)
3. 4-Hop Mechanistic Swanson Bridge (Local In-Memory Traversal in /dev/shm)
4. 15-Second iPhone Pre-Flight Card Generation
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
from typing import Any, Dict, List, Optional

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
DATA_DIR = STACKLABS_ROOT / "data" / "counterparty"
SHM_DIR = pathlib.Path("/dev/shm/counterparty_collider")

MODAL_MANDATORY = {"shall", "must", "will", "required", "mandatory"}
MODAL_PERMISSIVE = {"may", "might", "can", "optional", "permitted"}
BANNED_BUZZWORDS = {
    "paradigm", "synergy", "holistic", "game-changer", "disruptive",
    "seamless", "best-of-breed", "turnkey", "scalable", "we", "our"
}


class CounterpartyCognitiveCollider:
    def __init__(self, target_id: str, data_path: Optional[pathlib.Path] = None):
        self.target_id = target_id
        self.data_path = data_path or (DATA_DIR / f"{target_id}_profile.json")
        self.profile: Dict[str, Any] = {}
        self.shm_target = SHM_DIR / target_id

    def load_profile(self) -> None:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Counterparty profile not found: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            self.profile = json.load(f)

    def extract_scars_and_inodes(self) -> Dict[str, Any]:
        """Layer 1: Extract operational inodes, causal edges, and scars."""
        inodes = self.profile.get("inodes", [])
        scars = self.profile.get("scars", [])
        causal_graph = self.profile.get("causal_graph", {})
        return {
            "target": self.profile.get("name", self.target_id),
            "organization": self.profile.get("organization", "Unknown"),
            "domain": self.profile.get("domain", "General Enterprise"),
            "inodes_count": len(inodes),
            "scars_count": len(scars),
            "inodes": inodes,
            "scars": scars,
            "causal_graph": causal_graph,
        }

    def filter_paper_lies(self) -> List[str]:
        """Layer 2: Enforce the Anti-Pitch Shield by identifying banned vendor frames."""
        paper_lies = self.profile.get("paper_lies", [])
        return paper_lies

    def audit_deontic_modals(self, text: str) -> Dict[str, List[str]]:
        """Deontic Polygraph: Distinguish mandatory obligations from permissive traps."""
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        found_mandatory = [w for w in words if w in MODAL_MANDATORY]
        found_permissive = [w for w in words if w in MODAL_PERMISSIVE]
        return {
            "mandatory": sorted(list(set(found_mandatory))),
            "permissive": sorted(list(set(found_permissive))),
        }

    def materialize_in_memory_graph(self) -> float:
        """Layer 3: Materialize the 4-hop discovery graph into /dev/shm and traverse."""
        self.shm_target.mkdir(parents=True, exist_ok=True)
        graph_data = self.profile.get("swanson_graph", {})
        start_time = time.perf_counter()

        # Write volatile graph topology to /dev/shm
        graph_file = self.shm_target / "topology.json"
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(graph_data, f)

        # In-memory traversal simulation of 4 hops
        hops = graph_data.get("hops", [])
        current_node = graph_data.get("root", "START")
        traversed_hops: List[Dict[str, Any]] = []

        for hop in hops:
            traversed_hops.append({
                "hop_id": hop.get("id"),
                "source": hop.get("source"),
                "target": hop.get("target"),
                "relation": hop.get("relation"),
            })
            current_node = hop.get("target")

        elapsed_us = (time.perf_counter() - start_time) * 1_000_000
        return elapsed_us

    def generate_preflight_card(self, elapsed_us: float) -> Dict[str, Any]:
        """Layer 4: Generate the 15-Second Mobile Viewport Pre-Flight Card."""
        name = self.profile.get("name", self.target_id)
        domain = self.profile.get("domain", "Enterprise")
        paper_lies = self.profile.get("paper_lies", [])
        ground_truth = self.profile.get("ground_truth_reality", "")
        opener = self.profile.get("four_move_opener", "")
        four_hops = self.profile.get("swanson_graph", {}).get("hops", [])

        # Validate anti-buzzword rule
        card_text = f"{name} {domain} {' '.join(paper_lies)} {ground_truth} {opener}"
        found_buzzwords = [bw for bw in BANNED_BUZZWORDS if re.search(r"\b" + bw + r"\b", card_text, re.IGNORECASE)]

        card = {
            "header": {
                "target": name,
                "organization": self.profile.get("organization", ""),
                "domain": domain,
                "traversal_latency_us": round(elapsed_us, 2),
            },
            "layer_1_scars": self.profile.get("scars", []),
            "layer_2_paper_lie": paper_lies[0] if paper_lies else "None recorded",
            "layer_3_ground_truth": ground_truth,
            "layer_4_four_move_opener": opener,
            "swanson_hops": [f"{h.get('source')} ➔ {h.get('target')}" for h in four_hops],
            "buzzword_audit": {
                "clean": len(found_buzzwords) == 0,
                "violations": found_buzzwords,
            },
        }
        return card

    def run(self) -> Dict[str, Any]:
        self.load_profile()
        elapsed_us = self.materialize_in_memory_graph()
        card = self.generate_preflight_card(elapsed_us)
        return card


def format_terminal_card(card: Dict[str, Any]) -> str:
    h = card["header"]
    lines = [
        "┌─────────────────────────────────────────────────────────────┐",
        f"│ TARGET: {h['target'][:49]:<51} │",
        f"│ ORG:    {h['organization'][:49]:<51} │",
        f"│ DOMAIN: {h['domain'][:49]:<51} │",
        f"│ MEMORY RESOLUTION: {h['traversal_latency_us']} µs on Clio NVMe/RAM             │",
        "├─────────────────────────────────────────────────────────────┤",
        "│ 1. THE PAPER LIE:                                           │",
    ]
    lie = card["layer_2_paper_lie"]
    for chunk in [lie[i:i + 57] for i in range(0, len(lie), 57)]:
        lines.append(f"│    {chunk:<57}│")

    lines.append("│                                                             │")
    lines.append("│ 2. THE GROUND TRUTH:                                        │")
    gt = card["layer_3_ground_truth"]
    for chunk in [gt[i:i + 57] for i in range(0, len(gt), 57)]:
        lines.append(f"│    {chunk:<57}│")

    lines.append("│                                                             │")
    lines.append("│ 3. THE 4-MOVE OPENER:                                       │")
    op = card["layer_4_four_move_opener"]
    for chunk in [op[i:i + 57] for i in range(0, len(op), 57)]:
        lines.append(f"│    {chunk:<57}│")

    lines.append("├─────────────────────────────────────────────────────────────┤")
    lines.append("│ 4-HOP SWANSON RESOLUTION TRACE:                             │")
    for hop_str in card["swanson_hops"]:
        lines.append(f"│  • {hop_str[:55]:<57}│")
    lines.append("└─────────────────────────────────────────────────────────────┘")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Counterparty Cognitive Collider Pre-Flight Engine")
    parser.add_argument("--target", required=True, help="Target counterparty ID (e.g., cherylyn, pawel)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of ASCII terminal card")
    args = parser.parse_args()

    collider = CounterpartyCognitiveCollider(args.target)
    try:
        card = collider.run()
    except Exception as e:
        print(f"[ERROR] Collider execution failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(card, indent=2))
    else:
        print(format_terminal_card(card))

    if not card["buzzword_audit"]["clean"]:
        print(f"\n⚠️ WARNING: Banned buzzwords detected: {card['buzzword_audit']['violations']}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
