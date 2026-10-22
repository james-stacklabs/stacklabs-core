#!/home/james/stacklabs/.venv/bin/python3
"""
Hydrate Pawel Rudnicki Corpus & Systemic Lenses into POSIX VFS.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC

Ingests Pawel's macroeconomic treatises, the 20-year trading model shock,
and the Both Ends 28-essay syllabus into structured VFS Configuration Items.
Populates cross-disciplinary causal lenses and wires bidirectional symlinks.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set

REPO_ROOT = Path("/home/james/stacklabs")
VFS_ROOT = REPO_ROOT / "vfs"
PAWEL_VAULT = VFS_ROOT / "vault" / "pawel"
LENSES_ROOT = VFS_ROOT / "pheromones" / "lenses"
CMDB_LOGICAL = VFS_ROOT / "cmdb" / "logical"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hydrate_pawel_vfs_corpus")

STRUCTURAL_LENSES: Dict[str, Dict[str, Any]] = {
    "THERMODYNAMIC_ENERGY_CEILING": {
        "title": "Thermodynamic Energy Ceiling & Grid Constraints",
        "description": "Physical 1,100 TWh power grid capacity, cooling limits, and transmission congestion constraining ungrounded software and hyperscaler scaling assumptions.",
        "category": "Thermodynamics & Physical Infrastructure",
    },
    "UNEXPLAINED_LOGIC_DRIFT": {
        "title": "Unexplained Algorithmic Logic Drift & Auditability Loss",
        "description": "Black-box AI modifications to core financial or operational logic that pass backtests but fail human auditability and legal/operational defensibility during regime shift.",
        "category": "Algorithmic Risk & Model Governance",
    },
    "GHOST_GDP_DECOUPLING": {
        "title": "Ghost GDP & Value Circulation Disconnect",
        "description": "Synthetic task compression generating massive paper productivity on corporate ledgers while completely evaporating from human wage circulation loops.",
        "category": "Macroeconomics & Labor Physics",
    },
    "COGNITIVE_FRICTION_ATROPHY": {
        "title": "Cognitive Friction Atrophy & Operational Blindness",
        "description": "Eliminating operational difficulty and struggle in workflows, blinding human allocators and operators to latent structural decay and silent failures.",
        "category": "Human Agency & Epistemic Defense",
    },
    "TOPOLOGICAL_CASCADE_FAULT": {
        "title": "Topological Cascade Fault & Unlogged Dependency Propagation",
        "description": "Upstream configuration or architectural shifts that silently degrade downstream enterprise service nodes without tripping localized health-check alarms.",
        "category": "Distributed Systems & Enterprise CMDB",
    },
    "ASYMMETRIC_TAIL_CONTAGION": {
        "title": "Asymmetric Tail Contagion & Low-Probability Shocks",
        "description": "Non-linear failure dynamics where an unverified micro-dependency or rare event at scale collapses the larger parent infrastructure.",
        "category": "Tail Risk & Systems Fragility",
    },
    "LATENCY_INVERSION_BOUNDARY": {
        "title": "Latency Inversion Boundary & Edge Determination",
        "description": "Relying on multi-second cloud round-trips for sub-millisecond physical or financial decisions where local POSIX read models provide immutable defense.",
        "category": "Silicon Architecture & Latency Boundaries",
    },
}

PAWEL_ENTITIES: List[Dict[str, Any]] = [
    {
        "slug": "pendulum_and_the_algorithm",
        "title": "The Pendulum and the Algorithm: Why AI Makes Human Labor Unnecessary",
        "author": "Pawel Rudnicki",
        "date": "2026-04-19",
        "summary": "Historical analysis of the 90-year labor rule across FDR, LBJ, and Reagan eras. Proves capital no longer needs labor to compound, leading to Ghost GDP and grid-enforced delay.",
        "associated_lenses": [
            "THERMODYNAMIC_ENERGY_CEILING",
            "GHOST_GDP_DECOUPLING",
            "COGNITIVE_FRICTION_ATROPHY",
        ],
    },
    {
        "slug": "twenty_year_trading_model_failure",
        "title": "The 20-Year Trading Model Shock & Downside Defense",
        "author": "Pawel Rudnicki",
        "date": "2026-10-04",
        "summary": "An AI rebuilt parts of a 20-year trading model with 3 lines of unexplainable logic. Works in backtests, but undefensible under adverse market conditions. The core allocator dilemma: capable or feeling capable.",
        "associated_lenses": [
            "UNEXPLAINED_LOGIC_DRIFT",
            "COGNITIVE_FRICTION_ATROPHY",
            "ASYMMETRIC_TAIL_CONTAGION",
        ],
    },
    {
        "slug": "both_ends_02_the_push",
        "title": "Essay 2: The Push (The Origin Dialogue)",
        "author": "Pawel Rudnicki",
        "date": "2026-10-19",
        "summary": "How a few pages written for one reader (James Carroll) turned into Both Ends of the Curve. The human veto, division of labor, and external governance checks.",
        "associated_lenses": [
            "COGNITIVE_FRICTION_ATROPHY",
            "LATENCY_INVERSION_BOUNDARY",
        ],
    },
    {
        "slug": "both_ends_03_the_frictionless_life",
        "title": "Essay 3: The Frictionless Life",
        "author": "Pawel Rudnicki",
        "date": "2026-10-04",
        "summary": "What happens as agents take over tedious tasks. Which difficulties do the actual cognitive work, and the Santa Anita racetrack handicapping failure audit.",
        "associated_lenses": [
            "COGNITIVE_FRICTION_ATROPHY",
            "UNEXPLAINED_LOGIC_DRIFT",
        ],
    },
    {
        "slug": "both_ends_09_title_essay",
        "title": "Essay 9: Both Ends of the Curve",
        "author": "Pawel Rudnicki",
        "date": "2026-10-20",
        "summary": "Why energy comes from both ends of a curve and none from the middle. Bell curves vs. nuclear binding energy curves. Balance living at extremes.",
        "associated_lenses": [
            "THERMODYNAMIC_ENERGY_CEILING",
            "ASYMMETRIC_TAIL_CONTAGION",
        ],
    },
    {
        "slug": "both_ends_12_one_in_a_billion",
        "title": "Essay 12: One in a Billion, Every Day",
        "author": "Pawel Rudnicki",
        "date": "2026-10-20",
        "summary": "Rare events at scale: when something is tried 10 billion times a day, one-in-a-billion failures happen 10 times daily. Asymmetric disaster arithmetic.",
        "associated_lenses": [
            "ASYMMETRIC_TAIL_CONTAGION",
            "TOPOLOGICAL_CASCADE_FAULT",
        ],
    },
    {
        "slug": "both_ends_20_owning_a_piece",
        "title": "Essay 20: Owning a Piece (Local Silicon vs. Cloud Tolls)",
        "author": "Pawel Rudnicki",
        "date": "2026-10-20",
        "summary": "Asks whether small private models on local silicon do for this era what rural electrification did for the 1930s. Immune to centralized cloud toll gates.",
        "associated_lenses": [
            "LATENCY_INVERSION_BOUNDARY",
            "THERMODYNAMIC_ENERGY_CEILING",
            "GHOST_GDP_DECOUPLING",
        ],
    },
]

# Map enterprise CMDB services to causal lenses to establish the Bridge
CMDB_LENS_MAPPINGS: Dict[str, List[str]] = {
    "sap_web01": ["TOPOLOGICAL_CASCADE_FAULT", "UNEXPLAINED_LOGIC_DRIFT"],
    "sap_web02": ["TOPOLOGICAL_CASCADE_FAULT", "ASYMMETRIC_TAIL_CONTAGION"],
    "exchange-ny-02": ["TOPOLOGICAL_CASCADE_FAULT", "LATENCY_INVERSION_BOUNDARY"],
    "apache_linux_ny_100": ["THERMODYNAMIC_ENERGY_CEILING", "TOPOLOGICAL_CASCADE_FAULT"],
}


def atomic_symlink(target_path: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_link = link_path.parent / f".tmp_{link_path.name}_{time.time_ns()}"
    try:
        if tmp_link.is_symlink() or tmp_link.exists():
            tmp_link.unlink()
        rel_target = os.path.relpath(target_path, link_path.parent)
        os.symlink(rel_target, tmp_link)
        os.replace(tmp_link, link_path)
    except Exception as exc:
        if tmp_link.is_symlink() or tmp_link.exists():
            try:
                tmp_link.unlink()
            except OSError:
                pass
        raise exc


def hydrate_lenses() -> None:
    LENSES_ROOT.mkdir(parents=True, exist_ok=True)
    for lens_slug, meta in STRUCTURAL_LENSES.items():
        lens_dir = LENSES_ROOT / lens_slug
        lens_dir.mkdir(parents=True, exist_ok=True)
        meta_file = lens_dir / "meta.json"
        tmp_meta = lens_dir / ".meta.json.tmp"
        tmp_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        os.replace(tmp_meta, meta_file)
        logger.info(f"Hydrated structural lens: {lens_slug}")


def hydrate_pawel_vault() -> None:
    PAWEL_VAULT.mkdir(parents=True, exist_ok=True)
    for ent in PAWEL_ENTITIES:
        slug = ent["slug"]
        ent_dir = PAWEL_VAULT / slug
        ent_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_file = ent_dir / "manifest.json"
        tmp_manifest = ent_dir / ".manifest.json.tmp"
        tmp_manifest.write_text(json.dumps(ent, indent=2), encoding="utf-8")
        os.replace(tmp_manifest, manifest_file)

        thesis_file = ent_dir / "thesis.md"
        tmp_thesis = ent_dir / ".thesis.md.tmp"
        tmp_thesis.write_text(
            f"# {ent['title']}\n\n"
            f"> **Author**: {ent['author']} | **Date**: {ent['date']}\n\n"
            f"## Core Thesis & Abstract\n{ent['summary']}\n\n"
            f"## Active Causal Lenses\n" + "\n".join(f"- `{lens}`" for lens in ent["associated_lenses"]) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_thesis, thesis_file)

        active_lenses_dir = ent_dir / "active_lenses"
        active_lenses_dir.mkdir(parents=True, exist_ok=True)
        for lens_slug in ent["associated_lenses"]:
            lens_target = LENSES_ROOT / lens_slug
            if lens_target.exists():
                atomic_symlink(lens_target, active_lenses_dir / lens_slug)

        logger.info(f"Hydrated Pawel entity: {slug} with {len(ent['associated_lenses'])} lenses")


def wire_cmdb_lenses() -> None:
    if not CMDB_LOGICAL.exists():
        logger.warning(f"CMDB logical root {CMDB_LOGICAL} not found; skipping CMDB lens wiring.")
        return

    for ci_name, lenses in CMDB_LENS_MAPPINGS.items():
        ci_dir = CMDB_LOGICAL / ci_name
        if not ci_dir.exists():
            continue
        active_lenses_dir = ci_dir / "active_lenses"
        active_lenses_dir.mkdir(parents=True, exist_ok=True)
        for lens_slug in lenses:
            lens_target = LENSES_ROOT / lens_slug
            if lens_target.exists():
                atomic_symlink(lens_target, active_lenses_dir / lens_slug)
                atomic_symlink(ci_dir, lens_target / f"cmdb__{ci_name}")
        logger.info(f"Wired CMDB CI {ci_name} to lenses: {lenses}")


def main() -> int:
    logger.info("Starting Pawel VFS & Structural Lens Hydration...")
    hydrate_lenses()
    hydrate_pawel_vault()
    wire_cmdb_lenses()
    logger.info("Hydration complete. Ready for Swanson 2-hop collision pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
