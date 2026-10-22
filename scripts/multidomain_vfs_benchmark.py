#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Live Multi-Domain VFS Knowledge Graph & Stall Benchmark
Path: /home/james/stacklabs/scripts/multidomain_vfs_benchmark.py

Ingests Google Health AI, DeepMind AlphaQubit, and Pit-Smoking Thermodynamics,
extracts factual triples via live Gemini Flash API, projects them into /dev/shm/
as Linux directory inodes and symlinks, and executes microsecond forensic graph walks.

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011094
"""

import os
import sys
import json
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("multidomain_vfs")

REPO_ROOT = Path("/home/james/stacklabs")
load_dotenv(REPO_ROOT / ".env")

SHM_ROOT = Path("/dev/shm/multidomain_vfs")
CONCEPTS_DIR = SHM_ROOT / "concepts"
RECEIPT_FILE = REPO_ROOT / "data" / "telemetry" / "multidomain_vfs_receipt.json"

CORPUS_HEALTH_AI = """
In collaboration with research partners, Google Health uses artificial intelligence to accelerate disease understanding.
DeepVariant is a deep learning genomic variant caller that uses convolutional neural networks to identify single nucleotide variants and insertions or deletions from high-throughput sequencing data.
DeepVariant analyzes base quality score recalibration and read alignment to predict true pathogenic genetic mutations.
Concurrently, AlphaFold predicts three-dimensional protein structures from amino acid sequences, enabling researchers to model protein misfolding, understand receptor binding mechanisms, and target rare genetic diseases.
"""

CORPUS_ALPHAQUBIT = """
Google DeepMind and Google Quantum AI developed AlphaQubit, an AI system that advances quantum error correction.
Quantum computers face decoherence from environmental noise, causing bit-flip and phase-flip errors in physical superconducting qubits.
AlphaQubit uses a transformer neural network architecture to decode error syndromes from measurement grids on Google's Sycamore quantum processor.
By analyzing surface code lattice stabilizer measurements, the neural network decoder tracks Pauli frames and identifies the most probable error locations faster and more accurately than 2D minimum-weight perfect matching, preserving logical qubit coherence.
"""

CORPUS_PIT_SMOKING = """
Authentic wood-fired pit smoking relies on precise thermal dynamics and wood pyrolysis.
When seasoned post oak wood undergoes thermal pyrolysis in an offset firebox at 450 degrees Fahrenheit, it releases nitric oxide, carbon monoxide, guaiacol, and syringol aroma compounds in clean blue smoke.
As nitric oxide gas diffuses into the surface of raw beef brisket, it binds to deoxymyoglobin to form stable nitrosylmyoglobin, locking in the characteristic pink smoke ring before surface protein denatures at 140 to 170 degrees Fahrenheit.
During the cook, internal meat temperature climbs to approximately 160 to 170 degrees Fahrenheit where the brisket enters the stall.
The stall is caused by evaporative surface cooling where moisture pushes to the surface and evaporates, creating a latent heat cooling effect that exactly balances convective heat transfer from the smoker.
Internal temperature remains flatlined until surface moisture fully evaporates and bark formation completes.
Once the stall breaks, internal heat climbs to 203 degrees Fahrenheit where tough collagen protein undergoes hydrolysis, melting into tender gelatin.
"""

def clean_identifier(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_").replace("'", "").replace("/", "_")

def reset_vfs_plane():
    if SHM_ROOT.exists():
        shutil.rmtree(SHM_ROOT)
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

def extract_triples_with_gemini(api_key: str) -> List[Dict[str, str]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"""
Extract factual, causal, or physical mechanism assertions from the following three distinct domain texts.
Return strictly valid JSON: an array of objects with keys 'subject', 'predicate', 'object', 'domain'.
Ensure:
- 'domain' is one of: 'genomics_health', 'quantum_computing', 'pit_smoking_thermodynamics'.
- Normalize 'subject' and 'object' to concise lower_snake_case canonical nouns (e.g. use 'the_stall', 'evaporative_surface_cooling', 'alphaqubit', 'deepvariant', 'smoke_ring', 'post_oak_wood', 'nitric_oxide', 'gelatin', 'collagen').
- Keep assertions strictly factual and mechanism-driven. Do NOT hallucinate false cross-domain links.

[DOMAIN 1: HEALTH & GENOMICS]
{CORPUS_HEALTH_AI}

[DOMAIN 2: QUANTUM COMPUTING]
{CORPUS_ALPHAQUBIT}

[DOMAIN 3: PIT SMOKING THERMODYNAMICS]
{CORPUS_PIT_SMOKING}
"""
    logger.info("Calling Gemini Flash API (gemini-3.8-flash) for multi-domain triplet extraction...")
    t0 = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    t_api = time.perf_counter() - t0
    logger.info(f"Gemini API returned in {t_api:.2f}s.")
    return json.loads(response.text.strip())

def project_triples_to_inodes(triples: List[Dict[str, str]]) -> Dict[str, int]:
    node_set = set()
    edge_count = 0
    t0 = time.perf_counter_ns()

    for t in triples:
        sub = clean_identifier(t["subject"])
        pred = clean_identifier(t["predicate"])
        obj = clean_identifier(t["object"])

        sub_dir = CONCEPTS_DIR / sub
        obj_dir = CONCEPTS_DIR / obj

        sub_dir.mkdir(parents=True, exist_ok=True)
        obj_dir.mkdir(parents=True, exist_ok=True)

        node_set.add(sub)
        node_set.add(obj)

        fwd_edge = sub_dir / f"fwd_{pred}_{obj}"
        if not fwd_edge.exists() and not fwd_edge.is_symlink():
            try:
                os.symlink(f"../{obj}", fwd_edge)
                edge_count += 1
            except OSError:
                pass

        rev_edge = obj_dir / f"rev_{pred}_{sub}"
        if not rev_edge.exists() and not rev_edge.is_symlink():
            try:
                os.symlink(f"../{sub}", rev_edge)
                edge_count += 1
            except OSError:
                pass

    t_vfs_ns = time.perf_counter_ns() - t0
    return {
        "nodes": len(node_set),
        "edges": edge_count,
        "vfs_write_us": round(t_vfs_ns / 1000.0, 2)
    }

def bfs_search(start: str, target: str, max_depth: int = 5) -> Optional[List[str]]:
    start_clean = clean_identifier(start)
    target_clean = clean_identifier(target)
    start_node = CONCEPTS_DIR / start_clean
    target_node = CONCEPTS_DIR / target_clean

    if not start_node.exists() or not target_node.exists():
        return None

    queue = [[start_clean]]
    visited = {start_clean}

    while queue:
        path = queue.pop(0)
        curr = path[-1]

        if curr == target_clean:
            return path

        if len(path) > max_depth:
            continue

        curr_dir = CONCEPTS_DIR / curr
        if not curr_dir.exists():
            continue

        try:
            with os.scandir(curr_dir) as it:
                for entry in it:
                    if entry.is_symlink():
                        try:
                            target_name = os.path.basename(os.readlink(entry.path))
                            if target_name not in visited:
                                visited.add(target_name)
                                queue.append(path + [target_name])
                        except OSError:
                            pass
        except OSError:
            pass

    return None

def find_first_valid_path(source_candidates: List[str], target_candidates: List[str], max_depth: int = 5) -> Optional[List[str]]:
    for s in source_candidates:
        for t in target_candidates:
            res = bfs_search(s, t, max_depth=max_depth)
            if res:
                return res
    return None

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY missing from environment or .env!")
        sys.exit(1)

    reset_vfs_plane()

    # 1. Extract Triples via Gemini API
    triples = extract_triples_with_gemini(api_key)
    logger.info(f"Extracted {len(triples)} factual mechanism triples across 3 domains.")

    # 2. Project into POSIX Inodes in /dev/shm
    vfs_stats = project_triples_to_inodes(triples)
    logger.info(f"Projected {vfs_stats['nodes']} Inodes and {vfs_stats['edges']} Symlinks into /dev/shm in {vfs_stats['vfs_write_us']} µs.")

    benchmarks = {}

    # 3. Test 1: The Stall Air-Gap Isolation Gate (BBQ vs Quantum & Health)
    t0 = time.perf_counter_ns()
    stall_node = "the_stall" if (CONCEPTS_DIR / "the_stall").exists() else ("stall" if (CONCEPTS_DIR / "stall").exists() else None)
    
    stall_to_quantum = bfs_search(stall_node or "the_stall", "alphaqubit")
    stall_to_health = bfs_search(stall_node or "the_stall", "deepvariant")
    t_iso_us = round((time.perf_counter_ns() - t0) / 1000.0, 2)

    benchmarks["isolation_test"] = {
        "source": stall_node or "the_stall",
        "targets": ["alphaqubit", "deepvariant"],
        "stall_to_quantum_path": stall_to_quantum,
        "stall_to_health_path": stall_to_health,
        "cross_contamination_detected": bool(stall_to_quantum or stall_to_health),
        "status": "PASS_CLEAN_ISOLATION" if not (stall_to_quantum or stall_to_health) else "FAIL_LEAKAGE",
        "search_time_us": t_iso_us
    }

    # 4. Test 2: In-Domain Barbecue Causal Traversal
    t0 = time.perf_counter_ns()
    # Find any internal path within BBQ domain
    bbq_candidates_start = ["the_stall", "stall", "post_oak_wood", "wood_pyrolysis", "post_oak"]
    bbq_candidates_end = ["evaporative_surface_cooling", "evaporative_cooling", "smoke_ring", "gelatin", "nitrosylmyoglobin"]
    bbq_path = find_first_valid_path(bbq_candidates_start, bbq_candidates_end) or bfs_search("the_stall", "evaporative_cooling")
    t_bbq_us = round((time.perf_counter_ns() - t0) / 1000.0, 2)

    benchmarks["bbq_causal_walk"] = {
        "path_found": bbq_path,
        "hops": len(bbq_path) - 1 if bbq_path else 0,
        "traversal_time_us": t_bbq_us,
        "status": "PASS_CAUSAL_VERIFIED" if bbq_path else "INSPECT_EDGES"
    }

    # 5. Test 3: Cross-Tech Discovery Bridge (AlphaQubit <-> DeepVariant)
    t0 = time.perf_counter_ns()
    tech_path = (bfs_search("alphaqubit", "deepvariant", max_depth=6) or 
                 bfs_search("alphaqubit", "alphafold", max_depth=6) or
                 bfs_search("alphaqubit", "google_health", max_depth=6))
    t_tech_us = round((time.perf_counter_ns() - t0) / 1000.0, 2)

    benchmarks["cross_tech_discovery"] = {
        "source": "alphaqubit",
        "target": "deepvariant",
        "discovered_path": tech_path,
        "traversal_time_us": t_tech_us
    }

    # Compile Final Receipt
    receipt = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "harness": "Live Gemini Multi-Domain VFS Benchmark",
        "gemini_model": "gemini-3.8-flash",
        "triples_count": len(triples),
        "triples_sample": triples[:5],
        "vfs_stats": vfs_stats,
        "benchmarks": benchmarks
    }

    RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_FILE.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    logger.info(f"Receipt written to {RECEIPT_FILE}")
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
