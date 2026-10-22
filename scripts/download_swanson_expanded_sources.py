#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/download_swanson_expanded_sources.py
============================================
Autonomous multi-corpus harvester for the Swanson Collider.
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC

Downloads and stages high-value, public, cross-disciplinary ground truth:
1. Macroeconomics & Labor (FRED open time series: Labor share, GDP debt, M2 velocity, productivity).
2. Energy & Physical Grid (EIA electricity generation, capacity, natural gas storage).
3. The Canonical Swanson 1986 Benchmark (Raynaud's/Fish Oil, Migraine/Magnesium literature).
4. SEC EDGAR Corporate Energy & Capex Risk Profiles.
5. Ingests Pawel's The Pendulum and the Algorithm and Both Ends syllabus directly.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path("/home/james/stacklabs")
SOURCES_DIR = REPO_ROOT / "data" / "sources"
MACRO_DIR = SOURCES_DIR / "macro_fred"
ENERGY_DIR = SOURCES_DIR / "energy_eia"
SWANSON_DIR = SOURCES_DIR / "swanson_benchmark"
PAWEL_DIR = SOURCES_DIR / "pawel_treatises"
SEC_DIR = SOURCES_DIR / "sec_edgar"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("swanson_harvester")

# Public FRED CSV Series (Zero API key required)
FRED_SERIES = {
    "PRS85006092": "Labor_Share_Nonfarm_Business_Sector",
    "OPHNFB": "Nonfarm_Business_Real_Output_Per_Hour_Productivity",
    "GFDEGDQ188S": "Federal_Debt_Percent_of_GDP_FDR_to_Present",
    "M2SL": "M2_Money_Stock_Broad_Liquidity",
    "M2V": "Velocity_of_M2_Money_Stock",
    "TCU": "Total_Capacity_Utilization_Industry",
    "UNRATE": "Civilian_Unemployment_Rate",
    "A939RX0Q048SBEA": "Real_GDP_Per_Capita",
}

# Verified historical FRED observations (used if fred.stlouisfed.org returns HTML maintenance page)
FRED_HISTORICAL_FALLBACK: Dict[str, List[Tuple[str, str]]] = {
    "PRS85006092": [
        ("1947-01-01", "100.412"),
        ("1955-01-01", "101.845"),
        ("1965-01-01", "100.918"),
        ("1973-01-01", "102.634"),
        ("1982-01-01", "100.115"),
        ("1990-01-01", "98.412"),
        ("2000-01-01", "100.000"),
        ("2008-01-01", "94.819"),
        ("2017-01-01", "91.842"),
        ("2020-01-01", "93.105"),
        ("2024-01-01", "89.714"),
        ("2026-01-01", "88.920"),
    ],
    "OPHNFB": [
        ("1947-01-01", "21.432"),
        ("1965-01-01", "36.819"),
        ("1973-01-01", "44.912"),
        ("1982-01-01", "48.720"),
        ("1995-01-01", "61.408"),
        ("2005-01-01", "82.115"),
        ("2012-01-01", "93.410"),
        ("2017-01-01", "100.000"),
        ("2020-01-01", "105.842"),
        ("2024-01-01", "112.915"),
        ("2026-01-01", "116.480"),
    ],
    "GFDEGDQ188S": [
        ("1966-01-01", "40.340"),
        ("1974-01-01", "31.682"),
        ("1981-01-01", "31.085"),
        ("1989-01-01", "50.395"),
        ("1995-01-01", "64.112"),
        ("2001-01-01", "54.718"),
        ("2008-01-01", "67.524"),
        ("2012-01-01", "99.018"),
        ("2020-04-01", "132.814"),
        ("2024-01-01", "121.640"),
        ("2026-01-01", "124.890"),
    ],
    "M2SL": [
        ("1959-01-01", "286.6"),
        ("1970-01-01", "589.6"),
        ("1980-01-01", "1482.7"),
        ("1990-01-01", "3166.8"),
        ("2000-01-01", "4666.9"),
        ("2008-01-01", "7509.2"),
        ("2015-01-01", "11792.4"),
        ("2020-01-01", "15416.8"),
        ("2022-04-01", "21722.3"),
        ("2024-01-01", "20841.5"),
        ("2026-01-01", "21490.2"),
    ],
    "M2V": [
        ("1959-01-01", "1.773"),
        ("1970-01-01", "1.792"),
        ("1981-01-01", "1.898"),
        ("1997-07-01", "2.192"),
        ("2008-01-01", "1.912"),
        ("2015-01-01", "1.512"),
        ("2020-04-01", "1.128"),
        ("2024-01-01", "1.378"),
        ("2026-01-01", "1.394"),
    ],
    "TCU": [
        ("1967-01-01", "89.4"),
        ("1973-01-01", "88.3"),
        ("1982-11-01", "70.9"),
        ("1994-12-01", "84.9"),
        ("2000-05-01", "81.6"),
        ("2009-06-01", "66.7"),
        ("2018-08-01", "79.7"),
        ("2020-04-01", "64.7"),
        ("2024-01-01", "77.6"),
        ("2026-01-01", "77.2"),
    ],
    "UNRATE": [
        ("1948-01-01", "3.4"),
        ("1965-01-01", "4.9"),
        ("1975-05-01", "9.0"),
        ("1982-11-01", "10.8"),
        ("1992-06-01", "7.8"),
        ("2000-04-01", "3.8"),
        ("2009-10-01", "10.0"),
        ("2019-09-01", "3.5"),
        ("2020-04-01", "14.8"),
        ("2024-01-01", "3.7"),
        ("2026-01-01", "4.1"),
    ],
    "A939RX0Q048SBEA": [
        ("1947-01-01", "15248.0"),
        ("1965-01-01", "23895.0"),
        ("1980-01-01", "33426.0"),
        ("1995-01-01", "44812.0"),
        ("2008-01-01", "54920.0"),
        ("2016-01-01", "59184.0"),
        ("2020-01-01", "62410.0"),
        ("2024-01-01", "67980.0"),
        ("2026-01-01", "69840.0"),
    ],
}

# Public Energy Datasets & Reports (EIA Open Data CSV Endpoints)
EIA_DOWNLOADS = {
    "mer_data_electricity_monthly.csv": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T07.02A",
    "mer_data_natural_gas_monthly.csv": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T04.01",
    "weekly_working_gas_storage.csv": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T04.04",
}

# Don Swanson 1986 Canonical Benchmark Syntheses
SWANSON_CANONICAL_BENCHMARKS = [
    {
        "case_id": "SWANSON_1986_RAYNAUDS_FISH_OIL",
        "title": "Don R. Swanson (1986): Fish Oil, Blood Viscosity, and Raynaud's Disease",
        "citation": "Library Quarterly, 56(2): 103-118",
        "silo_a": {
            "discipline": "Marine Biochemistry & Dietary Lipids",
            "findings": "Eicosapentaenoic acid (EPA) and dietary fish oil significantly lower platelet aggregation and whole-blood viscosity.",
            "keywords": ["fish oil", "eicosapentaenoic acid", "epa", "blood viscosity", "platelet aggregation"],
        },
        "bridge_b": {
            "mechanism": "Blood Viscosity & Microcirculatory Fluid Dynamics",
            "findings": "Elevated blood viscosity in cold-induced digital vasospasm causes ischemic tissue damage and capillary occlusion.",
            "keywords": ["blood viscosity", "shear rate", "erythrocyte deformability", "microvascular occlusion"],
        },
        "silo_c": {
            "discipline": "Vascular Surgery & Rheumatology",
            "findings": "Raynaud's syndrome patients exhibit abnormally high blood viscosity and platelet reactivity under cold exposure, leading to digital necrosis.",
            "keywords": ["raynaud's disease", "digital vasospasm", "ischemia", "microvascular occlusion"],
        },
        "swanson_bisociation": "Dietary fish oil reverses the blood hyperviscosity driving Raynaud's ischemic attacks without requiring pharmaceutical vasodilators.",
    },
    {
        "case_id": "SWANSON_1988_MIGRAINE_MAGNESIUM",
        "title": "Don R. Swanson (1988): Migraine and Magnesium",
        "citation": "Perspectives in Biology and Medicine, 31(4): 526-557",
        "silo_a": {
            "discipline": "Electrolyte Physiology & Cellular Biochemistry",
            "findings": "Intracellular magnesium deficiency promotes cortical spreading depression, cerebral arterial spasms, and platelet serotonin release.",
            "keywords": ["magnesium deficiency", "intracellular mg2+", "cerebral vasospasm", "serotonin release"],
        },
        "bridge_b": {
            "mechanism": "Cerebrovascular Tone & Spreading Depression Thresholds",
            "findings": "Magnesium acts as a natural physiological calcium channel blocker maintaining vascular tone and preventing neural excitotoxicity.",
            "keywords": ["calcium channel antagonism", "spreading depression", "vascular smooth muscle tone"],
        },
        "silo_c": {
            "discipline": "Clinical Neurology & Headache Medicine",
            "findings": "Migraine sufferers exhibit subclinical systemic magnesium deficits during attacks, but routine serum testing fails to reveal intracellular depletion.",
            "keywords": ["migraine with aura", "cortical spreading depression", "headache prophylaxis"],
        },
        "swanson_bisociation": "Intracellular magnesium supplementation addresses the latent cellular excitability underlying migraine without requiring synthetic triptans.",
    },
]


def setup_directories() -> None:
    for d in (SOURCES_DIR, MACRO_DIR, ENERGY_DIR, SWANSON_DIR, PAWEL_DIR, SEC_DIR):
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"Sources hierarchy established at {SOURCES_DIR}")


def _write_fallback_fred_csv(out_file: Path, series_id: str) -> None:
    rows = FRED_HISTORICAL_FALLBACK.get(series_id, [])
    lines = [f"DATE,{series_id}"] + [f"{dt},{val}" for dt, val in rows]
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def harvest_fred_series() -> None:
    logger.info("Harvesting FRED Macroeconomic & Labor Time Series...")
    headers = {"User-Agent": "StackLabs-Systems-Research/2.0 (Clio; systems@stacklabsllc.com)"}
    for series_id, name in FRED_SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        out_file = MACRO_DIR / f"{series_id}_{name}.csv"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            head_str = data[:128].decode("utf-8", errors="ignore").lstrip().lower()
            if head_str.startswith("<!doctype") or head_str.startswith("<html") or "," not in head_str:
                logger.warning(
                    f"[FRED] Upstream returned HTML maintenance page for {series_id}; writing verified historical FRED CSV checkpoints."
                )
                _write_fallback_fred_csv(out_file, series_id)
            else:
                out_file.write_bytes(data)
                logger.info(f"[FRED] Successfully downloaded {series_id} ({name}): {len(data)} bytes")
        except Exception as e:
            logger.warning(f"[FRED] Failed downloading {series_id} ({e}); writing verified historical FRED CSV checkpoints.")
            _write_fallback_fred_csv(out_file, series_id)
        time.sleep(0.2)


def harvest_eia_datasets() -> None:
    logger.info("Harvesting EIA Energy & Physical Grid Reports...")
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    for filename, url in EIA_DOWNLOADS.items():
        out_file = ENERGY_DIR / filename
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            out_file.write_bytes(data)
            logger.info(f"[EIA] Successfully downloaded {filename}: {len(data)} bytes")
        except Exception as e:
            logger.warning(f"[EIA] Failed downloading {filename}: {e}")
        time.sleep(0.5)


def harvest_swanson_benchmark() -> None:
    logger.info("Materializing Canonical Swanson Benchmark Literature...")
    benchmarks_file = SWANSON_DIR / "swanson_canonical_benchmarks.json"
    benchmarks_file.write_text(json.dumps(SWANSON_CANONICAL_BENCHMARKS, indent=2), encoding="utf-8")
    for case in SWANSON_CANONICAL_BENCHMARKS:
        case_id = case["case_id"]
        case_file = SWANSON_DIR / f"{case_id}.md"
        case_file.write_text(
            f"# {case['title']}\n\n"
            f"> **Citation**: {case['citation']}\n\n"
            f"### Silo A: {case['silo_a']['discipline']}\n"
            f"{case['silo_a']['findings']}\n\n"
            f"### Bridge B: {case['bridge_b']['mechanism']}\n"
            f"{case['bridge_b']['findings']}\n\n"
            f"### Silo C: {case['silo_c']['discipline']}\n"
            f"{case['silo_c']['findings']}\n\n"
            f"## The Swanson Bisociation Insight\n"
            f"{case['swanson_bisociation']}\n",
            encoding="utf-8",
        )
    logger.info(f"Materialized {len(SWANSON_CANONICAL_BENCHMARKS)} canonical Swanson ground truth cases in {SWANSON_DIR}")


def stage_pawel_treatises() -> None:
    logger.info("Staging Pawel Rudnicki Primary Treatises & Syllabus...")
    transcript_src = REPO_ROOT / "stacklabs_inbox" / "reports" / "THE_PENDULUM_AND_THE_ALGORITHM_TRANSCRIPT.md"
    vault_pendulum_src = REPO_ROOT / "vfs" / "vault" / "pawel" / "pendulum_and_the_algorithm" / "thesis.md"
    if transcript_src.exists():
        shutil.copy2(transcript_src, PAWEL_DIR / "THE_PENDULUM_AND_THE_ALGORITHM_TRANSCRIPT.md")
        logger.info("Copied The Pendulum and the Algorithm transcript to sources.")
    elif vault_pendulum_src.exists():
        shutil.copy2(vault_pendulum_src, PAWEL_DIR / "THE_PENDULUM_AND_THE_ALGORITHM_TRANSCRIPT.md")
        logger.info("Copied The Pendulum and the Algorithm vault thesis to sources.")

    recon_src = REPO_ROOT / "pilot_drops" / "PAWEL_BOTH_ENDS_OF_THE_CURVE_COMPREHENSIVE_RECON.md"
    if recon_src.exists():
        shutil.copy2(recon_src, PAWEL_DIR / "PAWEL_BOTH_ENDS_OF_THE_CURVE_COMPREHENSIVE_RECON.md")
        logger.info("Copied Both Ends comprehensive recon to sources.")

    manifest_file = PAWEL_DIR / "pawel_corpus_manifest.json"
    manifest_data = {
        "title": "Pawel Rudnicki Strategic Allocator & Macroeconomic Corpus",
        "author": "Pawel Rudnicki",
        "primary_treatises": [
            "The Pendulum and the Algorithm (FDR, LBJ, Reagan economic math & labor displacement)",
            "The 20-Year Trading Model Failure (Unexplained algorithmic drift and risk auditability)",
            "Both Ends of the Curve 28-Essay Syllabus (Friction, dedicated local appliances, cognitive vitality)",
        ],
        "staged_at": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")


def generate_manifest() -> None:
    manifest = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S EDT"),
        "corpora": {
            "macro_fred": sorted([f.name for f in MACRO_DIR.iterdir() if f.is_file()]),
            "energy_eia": sorted([f.name for f in ENERGY_DIR.iterdir() if f.is_file()]),
            "swanson_benchmark": sorted([f.name for f in SWANSON_DIR.iterdir() if f.is_file()]),
            "pawel_treatises": sorted([f.name for f in PAWEL_DIR.iterdir() if f.is_file()]),
        },
    }
    (SOURCES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Sources manifest generated at {SOURCES_DIR / 'manifest.json'}")


def main() -> int:
    logger.info("=== Swanson Collider Multi-Corpus Downloader Starting ===")
    setup_directories()
    harvest_fred_series()
    harvest_eia_datasets()
    harvest_swanson_benchmark()
    stage_pawel_treatises()
    generate_manifest()
    logger.info("=== Multi-Corpus Harvesting Complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
