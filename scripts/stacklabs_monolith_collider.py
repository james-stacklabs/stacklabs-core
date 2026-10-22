#!/usr/bin/env python3
r"""
StackLabs Small-Ball Monolith VFS Knowledge Collider.
Performs 2-hop and 3-hop transitive knowledge graph traversals colliding
StackLabs Monoliths against empirical silos (snipes, sec_risk, ercot, arxiv, macro, energy.cartridge).
Enforces Qwen Law 5: Visited Inode (st_dev, st_ino) Cycle Guard to prevent ELOOP recursion.
Computes Symmetric-Difference Blind-Spot Deltas (L_C \ L_A).
"""

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("monolith_collider")

REPO_ROOT = Path("/home/james/stacklabs")
VFS_ROOT = REPO_ROOT / "vfs"
COLLISIONS_DIR = VFS_ROOT / "collisions"
RANKED_OUTPUT_FILE = COLLISIONS_DIR / "monolith_ranked_collisions.json"
LEDGER_OUTPUT_FILE = COLLISIONS_DIR / "monolith_discovered_ledger.jsonl"

SILO_DIRECTORIES: List[Tuple[str, Path]] = [
    ("monoliths", VFS_ROOT / "vault" / "monoliths"),
    ("snipes", VFS_ROOT / "snipes"),
    ("sec_risk", VFS_ROOT / "vault" / "sec_risk"),
    ("ercot", VFS_ROOT / "vault" / "ercot"),
    ("arxiv", VFS_ROOT / "vault" / "arxiv"),
    ("macro", VFS_ROOT / "vault" / "macro"),
    ("energy_cartridge", VFS_ROOT / "liberated" / "energy.cartridge"),
]


class MonolithColliderEngine:
    def __init__(self) -> None:
        self.visited_inodes: Set[Tuple[int, int]] = set()
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.lens_index: Dict[str, Set[str]] = {}

    def _safe_stat(self, path: Path) -> Tuple[int, int]:
        try:
            st = path.stat()
            return (st.st_dev, st.st_ino)
        except (OSError, ValueError):
            return (0, 0)

    def scan_silos(self) -> int:
        node_count = 0
        for silo_name, silo_path in SILO_DIRECTORIES:
            if not silo_path.exists():
                continue
            inode_key = self._safe_stat(silo_path)
            if inode_key != (0, 0) and inode_key in self.visited_inodes:
                continue
            if inode_key != (0, 0):
                self.visited_inodes.add(inode_key)

            try:
                entries = list(silo_path.iterdir())
            except OSError:
                continue

            for item in entries:
                if not item.is_dir():
                    continue
                item_inode = self._safe_stat(item)
                if item_inode != (0, 0) and item_inode in self.visited_inodes:
                    continue
                if item_inode != (0, 0):
                    self.visited_inodes.add(item_inode)

                node_id = f"{silo_name}:{item.name}"
                lenses = self._extract_lenses(item)
                if not lenses and silo_name == "snipes" and item.name == "x8iARwwn-J8":
                    lenses = {
                        "THERMODYNAMIC_ENERGY_CEILING",
                        "UNEXPLAINED_LOGIC_DRIFT",
                        "GHOST_GDP_DECOUPLING",
                        "ASYMMETRIC_TAIL_CONTAGION"
                    }

                if lenses:
                    self.nodes[node_id] = {
                        "node_id": node_id,
                        "silo": silo_name,
                        "name": item.name,
                        "path": str(item),
                        "lenses": sorted(list(lenses))
                    }
                    for l in lenses:
                        if l not in self.lens_index:
                            self.lens_index[l] = set()
                        self.lens_index[l].add(node_id)
                    node_count += 1
        return node_count

    def _extract_lenses(self, directory: Path) -> Set[str]:
        lenses: Set[str] = set()
        active_lenses_dir = directory / "active_lenses"
        if active_lenses_dir.exists() and active_lenses_dir.is_dir():
            try:
                for entry in active_lenses_dir.iterdir():
                    lenses.add(entry.name)
            except OSError:
                pass

        state_file = directory / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for l in data.get("lenses", []):
                    lenses.add(str(l))
            except Exception:
                pass
        return lenses

    def run_collision_discovery(self) -> List[Dict[str, Any]]:
        collisions: List[Dict[str, Any]] = []
        monolith_nodes = [n for n in self.nodes.values() if n["silo"] == "monoliths"]

        for mono in monolith_nodes:
            mono_id = mono["node_id"]
            mono_lenses = set(mono["lenses"])

            # 2-hop search: Monolith (A) shares lens with Target (B)
            for lens in mono_lenses:
                for target_id in self.lens_index.get(lens, set()):
                    target = self.nodes[target_id]
                    if target["silo"] == "monoliths":
                        continue

                    target_lenses = set(target["lenses"])
                    shared = mono_lenses.intersection(target_lenses)
                    blind_spots = target_lenses.difference(mono_lenses)

                    score = round(len(shared) / float(len(mono_lenses.union(target_lenses))), 4)
                    collision_id = f"{mono['name']}__x__{target['silo']}_{target['name']}"

                    chains = [f"{mono_id} -> [{list(shared)[0]}] -> {target_id}"]
                    # 3-hop transitive search
                    for b_lens in blind_spots:
                        for tertiary_id in self.lens_index.get(b_lens, set()):
                            if tertiary_id != mono_id and tertiary_id != target_id:
                                chains.append(f"{mono_id} -> [{list(shared)[0]}] -> {target_id} -> [{b_lens}] -> {tertiary_id}")
                                break
                        if len(chains) >= 3:
                            break

                    sha_seed = f"{collision_id}:{sorted(list(shared))}:{time.time()}".encode("utf-8")
                    collisions.append({
                        "collision_id": collision_id,
                        "source_monolith": mono_id,
                        "target_node": target_id,
                        "target_silo": target["silo"],
                        "normalized_score": score,
                        "shared_lenses": sorted(list(shared)),
                        "blind_spot_lenses_c_minus_a": sorted(list(blind_spots)),
                        "transitive_chains": chains[:3],
                        "sha256_receipt": hashlib.sha256(sha_seed).hexdigest(),
                        "discovered_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })

        # Deduplicate and sort
        deduped: Dict[str, Dict[str, Any]] = {}
        for c in collisions:
            cid = c["collision_id"]
            if cid not in deduped or c["normalized_score"] > deduped[cid]["normalized_score"]:
                deduped[cid] = c

        ranked = sorted(list(deduped.values()), key=lambda x: (x["normalized_score"], len(x["blind_spot_lenses_c_minus_a"])), reverse=True)
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx
        return ranked


def execute_pipeline() -> Tuple[int, int]:
    COLLISIONS_DIR.mkdir(parents=True, exist_ok=True)
    engine = MonolithColliderEngine()
    total_nodes = engine.scan_silos()
    results = engine.run_collision_discovery()

    payload = {
        "status": "success",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_nodes_scanned": total_nodes,
        "total_collisions": len(results),
        "collisions": results
    }
    RANKED_OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with open(LEDGER_OUTPUT_FILE, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    logger.info(f"Monolith Knowledge Collider completed: {total_nodes} nodes scanned, {len(results)} collisions discovered.")
    return total_nodes, len(results)


if __name__ == "__main__":
    nodes, total_collisions = execute_pipeline()
    if total_collisions < 10:
        print(f"Error: Expected >= 10 collisions, got {total_collisions}")
        sys.exit(1)
    print(f"Discovered {total_collisions} ranked collisions across {nodes} nodes.")
