#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/ingest_swanson_expanded_corpora.py
==========================================
Ingest downloaded multi-corpus datasets into POSIX VFS nodes.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC

Normalizes:
1. FRED Macro Series -> vfs/vault/macro/
2. EIA Energy Data -> vfs/vault/energy/
3. Swanson Canonical Benchmark -> vfs/vault/swanson_benchmark/
4. Wires active causal lenses in vfs/pheromones/lenses/
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path("/home/james/stacklabs")
SOURCES_DIR = REPO_ROOT / "data" / "sources"
VFS_VAULT = REPO_ROOT / "vfs" / "vault"
LENSES_ROOT = REPO_ROOT / "vfs" / "pheromones" / "lenses"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_swanson_corpora")


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


def wire_bidirectional_lens(node_dir: Path, domain: str, slug: str, lens_name: str) -> None:
    lens_target = LENSES_ROOT / lens_name
    active_lenses = node_dir / "active_lenses"
    active_lenses.mkdir(parents=True, exist_ok=True)
    if lens_target.exists():
        atomic_symlink(lens_target, active_lenses / lens_name)
        atomic_symlink(node_dir, lens_target / f"{domain}__{slug}")


def ingest_fred_macro() -> None:
    macro_src = SOURCES_DIR / "macro_fred"
    macro_dst = VFS_VAULT / "macro"
    macro_dst.mkdir(parents=True, exist_ok=True)
    if not macro_src.exists():
        logger.warning(f"Macro source directory {macro_src} missing.")
        return

    for csv_file in sorted(macro_src.glob("*.csv")):
        series_slug = csv_file.stem
        node_dir = macro_dst / series_slug
        node_dir.mkdir(parents=True, exist_ok=True)

        # Parse CSV metadata
        rows: List[Dict[str, str]] = []
        with csv_file.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for r in reader:
                if len(r) >= 2:
                    rows.append({"date": r[0].strip(), "value": r[1].strip()})

        first_val = rows[0] if rows else {"date": "N/A", "value": "N/A"}
        last_val = rows[-1] if rows else {"date": "N/A", "value": "N/A"}

        associated_lenses = ["GHOST_GDP_DECOUPLING", "COGNITIVE_FRICTION_ATROPHY"]
        manifest = {
            "series_slug": series_slug,
            "data_source": "Federal Reserve Economic Data (FRED)",
            "observation_count": len(rows),
            "start_date": first_val["date"],
            "end_date": last_val["date"],
            "latest_reading": last_val["value"],
            "associated_lenses": associated_lenses,
        }

        (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (node_dir / "summary.md").write_text(
            f"# Macroeconomic Series: {series_slug}\n\n"
            f"> **Source**: FRED | **Observations**: {len(rows)}\n"
            f"> **Date Range**: {first_val['date']} to {last_val['date']} (Latest: `{last_val['value']}`)\n\n"
            f"Provides empirical quantitative grounding for macroeconomic transitions and labor displacement.\n",
            encoding="utf-8",
        )

        # Wire bi-directional lens symlinks
        for lens_name in associated_lenses:
            wire_bidirectional_lens(node_dir, "macro", series_slug, lens_name)

        logger.info(f"Ingested FRED Macro series: {series_slug} ({len(rows)} records)")


def ingest_energy_eia() -> None:
    energy_src = SOURCES_DIR / "energy_eia"
    energy_dst = VFS_VAULT / "energy"
    energy_dst.mkdir(parents=True, exist_ok=True)
    if not energy_src.exists():
        logger.warning(f"Energy source directory {energy_src} missing.")
        return

    for report_file in sorted(energy_src.iterdir()):
        if report_file.is_file():
            slug = report_file.stem
            node_dir = energy_dst / slug
            node_dir.mkdir(parents=True, exist_ok=True)

            associated_lenses = ["THERMODYNAMIC_ENERGY_CEILING", "TOPOLOGICAL_CASCADE_FAULT"]
            manifest = {
                "report_slug": slug,
                "data_source": "U.S. Energy Information Administration (EIA)",
                "raw_file": report_file.name,
                "size_bytes": report_file.stat().st_size,
                "associated_lenses": associated_lenses,
            }
            (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            (node_dir / "summary.md").write_text(
                f"# EIA Physical Grid & Energy Telemetry: {slug}\n\n"
                f"> **Source**: U.S. Energy Information Administration (EIA) | **Payload**: `{report_file.name}` ({report_file.stat().st_size:,} bytes)\n\n"
                f"Provides empirical generation, capacity, and natural gas storage bounds for the physical grid ceiling.\n",
                encoding="utf-8",
            )

            for lens_name in associated_lenses:
                wire_bidirectional_lens(node_dir, "energy", slug, lens_name)

            logger.info(f"Ingested EIA Energy report: {slug} ({report_file.stat().st_size} bytes)")


def ingest_swanson_benchmarks() -> None:
    bench_src = SOURCES_DIR / "swanson_benchmark"
    bench_dst = VFS_VAULT / "swanson_benchmark"
    bench_dst.mkdir(parents=True, exist_ok=True)
    if not bench_src.exists():
        logger.warning(f"Swanson benchmark directory {bench_src} missing.")
        return

    for md_file in sorted(bench_src.glob("SWANSON_*.md")):
        slug = md_file.stem
        node_dir = bench_dst / slug
        node_dir.mkdir(parents=True, exist_ok=True)

        content = md_file.read_text(encoding="utf-8")
        (node_dir / "case_study.md").write_text(content, encoding="utf-8")

        associated_lenses = ["ASYMMETRIC_TAIL_CONTAGION", "COGNITIVE_FRICTION_ATROPHY"]
        manifest = {
            "case_slug": slug,
            "literature_source": "Don R. Swanson Classic Medical Literature Benchmarks",
            "associated_lenses": associated_lenses,
        }
        (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        for lens_name in associated_lenses:
            wire_bidirectional_lens(node_dir, "swanson_benchmark", slug, lens_name)

        logger.info(f"Ingested canonical Swanson case: {slug}")


def main() -> int:
    logger.info("Starting Multi-Corpus VFS Ingestion...")
    ingest_fred_macro()
    ingest_energy_eia()
    ingest_swanson_benchmarks()
    logger.info("Multi-Corpus VFS Ingestion Complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
