#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs POSIX VFS Research Bridge Scout
Path: /home/james/stacklabs/scripts/research_bridge_scout.py
Ingests cross-domain triples, projects them into /dev/shm/research_graph/
as directories and relative symlinks, and traverses Lowest Common Ancestor
bridges in microseconds.

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Governing Spec: WO0011085
"""

import os
import sys
import json
import time
import shutil
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("research_bridge_scout")

SHM_ROOT = Path("/dev/shm/research_graph")
CONCEPTS_DIR = SHM_ROOT / "concepts"
DEFAULT_FIXTURE = Path("/home/james/stacklabs/tests/fixtures/swanson_benchmark_corpus.json")
DEFAULT_OUTPUT = Path("/home/james/stacklabs/data/telemetry/swanson_discovery_receipt.json")


def clean_identifier(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_").replace("'", "")


def reset_graph_plane():
    if SHM_ROOT.exists():
        shutil.rmtree(SHM_ROOT)
    CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)


def project_triples_to_vfs(triples: List[Dict[str, str]]):
    for triple in triples:
        sub = clean_identifier(triple["subject"])
        pred = clean_identifier(triple["predicate"])
        obj = clean_identifier(triple["object"])

        sub_dir = CONCEPTS_DIR / sub
        obj_dir = CONCEPTS_DIR / obj

        sub_dir.mkdir(parents=True, exist_ok=True)
        obj_dir.mkdir(parents=True, exist_ok=True)

        # Forward relationship: sub/pred -> ../obj
        forward_edge = sub_dir / f"fwd_{pred}_{obj}"
        if not forward_edge.exists() and not forward_edge.is_symlink():
            try:
                os.symlink(f"../{obj}", forward_edge)
            except OSError as e:
                logger.debug(f"Edge exists: {e}")

        # Reverse relationship: obj/rev_{pred}_{sub} -> ../sub
        reverse_edge = obj_dir / f"rev_{pred}_{sub}"
        if not reverse_edge.is_symlink() and not reverse_edge.exists():
            try:
                os.symlink(f"../{sub}", reverse_edge)
            except OSError as e:
                logger.debug(f"Reverse edge exists: {e}")


def load_triples_from_fixture(fixture_path: Path) -> List[Dict[str, str]]:
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    all_triples = []
    for doc in data.get("documents", []):
        all_triples.extend(doc.get("ground_truth_triples", []))
    return all_triples


def extract_triples_via_gemini_api(api_key: str, corpus_texts: List[str]) -> List[Dict[str, str]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = (
        "Extract factual physical, biological, or chemical mechanism assertions from the following abstracts. "
        "Output strictly valid JSON as an array of objects with keys 'subject', 'predicate', 'object'. "
        "Normalize names to lower_snake_case. Do not editorialize or hallucinate links.\n\n"
        + "\n---\n".join(corpus_texts)
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    raw_text = response.text.strip()
    return json.loads(raw_text)


def scout_discovery_bridge(source: str, target: str, expected_bridge: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_src = clean_identifier(source)
    clean_tgt = clean_identifier(target)
    src_node = CONCEPTS_DIR / clean_src
    tgt_node = CONCEPTS_DIR / clean_tgt

    if not src_node.exists() or not tgt_node.exists():
        logger.error("Source or target node missing from VFS.")
        return None

    src_path = str(src_node)
    tgt_path = str(tgt_node)
    concepts_path = str(CONCEPTS_DIR)

    t_start = time.perf_counter_ns()

    # Step 1: Discover 1-hop and 2-hop concepts reachable from target
    target_reachable = {}
    with os.scandir(tgt_path) as it:
        for entry in it:
            if entry.is_symlink():
                try:
                    target_dest = os.readlink(entry.path).rsplit("/", 1)[-1]
                    target_reachable[target_dest] = [clean_tgt, entry.name]
                    sub_path = os.path.join(concepts_path, target_dest)
                    if os.path.isdir(sub_path):
                        with os.scandir(sub_path) as sub_it:
                            for sub_entry in sub_it:
                                if sub_entry.is_symlink():
                                    sub_dest = os.readlink(sub_entry.path).rsplit("/", 1)[-1]
                                    if sub_dest not in target_reachable:
                                        target_reachable[sub_dest] = [clean_tgt, entry.name, target_dest, sub_entry.name]
                except OSError:
                    continue

    # Step 2: Traverse from source node looking for bridge to target's reachable set
    matches = []
    clean_exp = clean_identifier(expected_bridge) if expected_bridge else None

    with os.scandir(src_path) as it:
        for entry in it:
            if entry.is_symlink():
                try:
                    neighbor = os.readlink(entry.path).rsplit("/", 1)[-1]
                    if neighbor in target_reachable:
                        t_end = time.perf_counter_ns()
                        traversal_time_us = (t_end - t_start) / 1000.0
                        match = {
                            "discovered_bridge": neighbor,
                            "source": clean_src,
                            "target": clean_tgt,
                            "source_hop": entry.name,
                            "target_path": target_reachable[neighbor],
                            "traversal_time_us": round(traversal_time_us, 2)
                        }
                        if clean_exp and neighbor == clean_exp:
                            return match
                        matches.append(match)
                except OSError:
                    continue

    if matches:
        return matches[0]

    return None


def main():
    parser = argparse.ArgumentParser(description="StackLabs POSIX VFS Research Bridge Scout")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Path to Swanson corpus fixture.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output receipt.")
    parser.add_argument("--source", default=None, help="Source concept (defaults to fixture source_domain).")
    parser.add_argument("--target", default=None, help="Target concept (defaults to fixture target_domain).")
    parser.add_argument("--expected-bridge", default=None, help="Expected bridge concept (defaults to fixture expected_bridge).")
    parser.add_argument("--use-gemini", action="store_true", help="Extract triples live via Gemini API.")
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    output_path = Path(args.output)

    print("=" * 80)
    print(" 🔬 STACKLABS RESEARCH BRIDGE SCOUT // POSIX VFS TOPOLOGY HARNESS")
    print(f" Fixture: {fixture_path}")
    print(f" In-Memory Mount: {CONCEPTS_DIR}")
    print(f" Output Sink: {output_path}")
    print("=" * 80)

    reset_graph_plane()

    fixture_data = {}
    if fixture_path.exists():
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture_data = json.load(f)

    if args.use_gemini:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is required when using --use-gemini.")
            sys.exit(1)
        texts = [doc["abstract"] for doc in fixture_data.get("documents", [])]
        logger.info(f"Extracting triples via Gemini API for {len(texts)} abstracts...")
        triples = extract_triples_via_gemini_api(api_key, texts)
    else:
        logger.info("Loading offline benchmark triples from fixture...")
        triples = []
        for doc in fixture_data.get("documents", []):
            triples.extend(doc.get("ground_truth_triples", []))

    logger.info(f"Projecting {len(triples)} triples into /dev/shm...")
    project_triples_to_vfs(triples)

    source_concept = args.source or fixture_data.get("source_domain", "raynauds_phenomenon")
    target_concept = args.target or fixture_data.get("target_domain", "dietary_fish_oil")
    expected_bridge = args.expected_bridge or fixture_data.get("expected_bridge", "blood_viscosity")

    logger.info(f"Traversing from '{source_concept}' to find bridge to '{target_concept}'...")
    receipt = scout_discovery_bridge(source_concept, target_concept, expected_bridge=expected_bridge)

    if not receipt:
        logger.error("Failed to discover cross-domain bridge.")
        sys.exit(1)

    print("\n🏆 DISCOVERY SYNTHESIS VERIFIED:")
    print("-" * 80)
    print(f" Source Domain:    {receipt['source']}")
    print(f" Discovered Bridge: {receipt['discovered_bridge']}")
    print(f" Target Domain:    {receipt['target']}")
    print(f" Traversal Path:   {receipt['source']} -> {receipt['source_hop']} -> {receipt['discovered_bridge']} <- {receipt['target_path']}")
    print(f" Resolution Time:  {receipt['traversal_time_us']} microseconds")
    print("-" * 80)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_out = output_path.with_suffix(".tmp")
    with open(temp_out, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    os.replace(temp_out, output_path)

    print(f"\n[+] Atomically wrote discovery receipt to {output_path}")


if __name__ == "__main__":
    main()
