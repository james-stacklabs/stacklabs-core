#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/ingest_swanson_trio.py
==============================
Ingest the 3 Pilot-Selected Corpora into POSIX VFS:
1. SEC EDGAR Risk Factors -> vfs/vault/sec_risk/
2. ERCOT Grid & Battery Telemetry -> vfs/vault/ercot/
3. ArXiv Multi-Domain Papers -> vfs/vault/arxiv/

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
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
logger = logging.getLogger("ingest_swanson_trio")


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


def ingest_sec_risk() -> None:
    sec_src = SOURCES_DIR / "sec_edgar_risk"
    sec_dst = VFS_VAULT / "sec_risk"
    sec_dst.mkdir(parents=True, exist_ok=True)
    if not sec_src.exists():
        logger.warning(f"SEC source {sec_src} missing.")
        return

    for f in sorted(sec_src.glob("*.json")):
        name = f.stem.replace("_submissions", "")
        node_dir = sec_dst / name
        node_dir.mkdir(parents=True, exist_ok=True)

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            cik = data.get("cik") or data.get("entity_name") or name
            associated_lenses = ["THERMODYNAMIC_ENERGY_CEILING", "TOPOLOGICAL_CASCADE_FAULT"]
            manifest = {
                "entity_name": name,
                "cik": cik,
                "source": "SEC EDGAR Form 10-K Disclosures",
                "associated_lenses": associated_lenses,
            }
            (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            (node_dir / "dossier.md").write_text(
                f"# SEC EDGAR Risk Profile: {name}\n\n"
                f"> **CIK**: `{cik}` | **Source**: Form 10-K Item 1A\n\n"
                f"Captures capital expenditure depreciation, power purchase agreement inflation, "
                f"and transmission interconnect queues constraining AI data center infrastructure.\n",
                encoding="utf-8",
            )

            for lens_name in associated_lenses:
                wire_bidirectional_lens(node_dir, "sec_risk", name, lens_name)

            logger.info(f"[VFS SEC] Ingested node: {name}")
        except Exception as e:
            logger.warning(f"Error ingesting {f.name}: {e}")


def ingest_ercot_grid() -> None:
    ercot_src = SOURCES_DIR / "ercot_grid"
    ercot_dst = VFS_VAULT / "ercot"
    ercot_dst.mkdir(parents=True, exist_ok=True)
    if not ercot_src.exists():
        logger.warning(f"ERCOT source {ercot_src} missing.")
        return

    for f in sorted(ercot_src.glob("*.csv")):
        name = f.stem
        node_dir = ercot_dst / name
        node_dir.mkdir(parents=True, exist_ok=True)

        associated_lenses = ["THERMODYNAMIC_ENERGY_CEILING", "ASYMMETRIC_TAIL_CONTAGION"]
        manifest = {
            "dataset_name": name,
            "source": "Electric Reliability Council of Texas (ERCOT)",
            "file": f.name,
            "associated_lenses": associated_lenses,
        }
        (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (node_dir / "telemetry_summary.md").write_text(
            f"# ERCOT Grid Telemetry: {name}\n\n"
            f"> **Source**: ERCOT Real-Time Operations\n\n"
            f"Physical grid telemetry tracking locational marginal pricing spikes, battery storage dispatch, "
            f"and renewable curtailment during peak industrial and data center loads.\n",
            encoding="utf-8",
        )

        for lens_name in associated_lenses:
            wire_bidirectional_lens(node_dir, "ercot", name, lens_name)

        logger.info(f"[VFS ERCOT] Ingested node: {name}")


def ingest_arxiv_papers() -> None:
    arxiv_src = SOURCES_DIR / "arxiv_abstracts"
    arxiv_dst = VFS_VAULT / "arxiv"
    arxiv_dst.mkdir(parents=True, exist_ok=True)
    if not arxiv_src.exists():
        logger.warning(f"ArXiv source {arxiv_src} missing.")
        return

    for f in sorted(arxiv_src.glob("*.json")):
        category_name = f.stem
        try:
            papers = json.loads(f.read_text(encoding="utf-8"))
            for p in papers[:5]:  # Hydrate top representative papers per category
                paper_id = p.get("id", "").split("/")[-1] or p.get("title", "")[:20].replace(" ", "_")
                clean_slug = f"{category_name}_{paper_id}".replace(".", "_")
                node_dir = arxiv_dst / clean_slug
                node_dir.mkdir(parents=True, exist_ok=True)

                associated_lenses = ["LATENCY_INVERSION_BOUNDARY", "UNEXPLAINED_LOGIC_DRIFT"]
                manifest = {
                    "paper_id": p.get("id"),
                    "title": p.get("title"),
                    "category": p.get("category"),
                    "source": "ArXiv Multi-Domain Open Access",
                    "associated_lenses": associated_lenses,
                }
                (node_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                (node_dir / "abstract.md").write_text(
                    f"# {p.get('title')}\n\n"
                    f"> **ID**: `{p.get('id')}` | **Category**: `{p.get('category')}`\n\n"
                    f"## Abstract\n{p.get('summary')}\n",
                    encoding="utf-8",
                )

                for lens_name in associated_lenses:
                    wire_bidirectional_lens(node_dir, "arxiv", clean_slug, lens_name)

                logger.info(f"[VFS ArXiv] Ingested paper node: {clean_slug}")
        except Exception as e:
            logger.warning(f"Error ingesting ArXiv {f.name}: {e}")


def main() -> int:
    logger.info("Starting Swanson Trio VFS Ingestion (SEC, ERCOT, ArXiv)...")
    ingest_sec_risk()
    ingest_ercot_grid()
    ingest_arxiv_papers()
    logger.info("Swanson Trio Ingestion Complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
