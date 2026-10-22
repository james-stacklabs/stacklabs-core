#!/usr/bin/env python3
"""
Hydrate StackLabs Small-Ball Monoliths into canonical VFS Vault nodes.
Creates directory structure, state.json, text.md, and symlinks to active lenses.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hydrate_monoliths")

REPO_ROOT = Path("/home/james/stacklabs")
MONOLITHS_DIR = REPO_ROOT / "vfs" / "vault" / "monoliths"
LENSES_DIR = REPO_ROOT / "vfs" / "pheromones" / "lenses"

MONOLITHS_DATA: List[Dict[str, Any]] = [
    {
        "slug": "monolith_01_posix_vfs_enterprise",
        "title": "Rewiring the Enterprise into a POSIX VFS: CI = Folder, Edge = Symlink",
        "thesis": "Enterprise ITSM database architectures accumulate massive coordination bloat. By projecting configuration items (CIs) as directories and relationships as filesystem symlinks, transactional queries collapse to sub-microsecond POSIX readdir and stat calls on Linux NVMe pagecache.",
        "lenses": [
            "POSIX_VFS_STATE_PLANE",
            "CI_FOLDER_EDGE_SYMLINK",
            "LATENCY_INVERSION_BOUNDARY",
            "ZERO_RAG_FILESYSTEM_GRAPH"
        ]
    },
    {
        "slug": "monolith_02_latency_boundary_collapses",
        "title": "When the Latency Boundary Collapses: 541ns Zero-Copy Adjacency vs. Vector RAG Drift",
        "thesis": "Vector databases incur high parsing latency, non-deterministic embedding drift, and token tax. Local zero-copy memory mapping and POSIX VFS traversals achieve deterministic sub-microsecond retrieval (541ns) without external API dependencies.",
        "lenses": [
            "LATENCY_INVERSION_BOUNDARY",
            "ZERO_RAG_FILESYSTEM_GRAPH",
            "THERMODYNAMIC_ENERGY_CEILING",
            "ASYMMETRIC_TAIL_CONTAGION"
        ]
    },
    {
        "slug": "monolith_03_ohtani_reconciliation_tax",
        "title": "The Ramp-Up Tax vs. The Reconciliation Tax: The Ohtani Deferred Contract",
        "thesis": "In capital allocation and systems architecture, upfront capital investment is predictable, but ongoing coordination and reconciliation taxes destroy long-term compound yield. The deferred structure mirrors zero-latency state synchronization.",
        "lenses": [
            "GHOST_GDP_DECOUPLING",
            "RECONCILIATION_TAX",
            "OHTANI_DEFERRED_CAPITAL",
            "ASYMMETRIC_TAIL_CONTAGION"
        ]
    },
    {
        "slug": "monolith_04_small_ball_soto_tensor_core",
        "title": "The Small Ball Manifesto: Protecting the $765M Tensor Core at DH & Ring-Buffer Centerfielders",
        "thesis": "High-capital enterprise strategies focus on bloated general-purpose models that waste power. Small Ball architecture relies on specialized micro-workers, commodity x86 local hardware, and ring-buffered streaming queues to preserve core compute assets.",
        "lenses": [
            "SMALL_BALL_ALLOCATOR_MOAT",
            "TENSOR_CORE_PRESERVATION",
            "THERMODYNAMIC_ENERGY_CEILING",
            "UNEXPLAINED_LOGIC_DRIFT"
        ]
    }
]


def ensure_lens(lens_slug: str) -> Path:
    target = LENSES_DIR / lens_slug
    target.mkdir(parents=True, exist_ok=True)
    spec_path = target / "spec.json"
    if not spec_path.exists():
        spec_path.write_text(json.dumps({
            "lens_slug": lens_slug,
            "created_at_utc": "2026-10-22T01:30:00Z",
            "description": f"StackLabs Canonical Lens: {lens_slug}"
        }, indent=2), encoding="utf-8")
    return target


def hydrate_monoliths() -> int:
    MONOLITHS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for m in MONOLITHS_DATA:
        m_dir = MONOLITHS_DIR / m["slug"]
        m_dir.mkdir(parents=True, exist_ok=True)

        state_path = m_dir / "state.json"
        state_data = {
            "id": f"monolith:{m['slug']}",
            "slug": m["slug"],
            "title": m["title"],
            "silo": "monoliths",
            "lenses": m["lenses"],
            "registered_at_utc": "2026-10-22T01:30:00Z"
        }
        state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

        text_path = m_dir / "text.md"
        text_content = f"# {m['title']}\n\n## Abstract & Thesis\n{m['thesis']}\n\n## Canonical Lenses\n"
        for l in m["lenses"]:
            text_content += f"- `{l}`\n"
        text_path.write_text(text_content, encoding="utf-8")

        active_lenses_dir = m_dir / "active_lenses"
        active_lenses_dir.mkdir(parents=True, exist_ok=True)
        for lens_slug in m["lenses"]:
            lens_target = ensure_lens(lens_slug)
            link_path = active_lenses_dir / lens_slug
            if not link_path.exists():
                try:
                    link_path.symlink_to(lens_target)
                except Exception as e:
                    logger.warning(f"Could not symlink {link_path}: {e}")
        count += 1
        logger.info(f"Hydrated monolith node: {m['slug']} ({len(m['lenses'])} lenses)")
    return count


if __name__ == "__main__":
    c = hydrate_monoliths()
    print(f"Successfully hydrated {c} StackLabs Monoliths.")
