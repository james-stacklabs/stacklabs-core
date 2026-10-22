#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic Verification Harness for WO0011134:
Adamic-Adar Centrality, Stub Floor (deg >= 2), and Temporal Wormhole Masking.
"""

import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path("/home/james/stacklabs")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.blueprints.vfs_wiki_api import (
    CrawlRequest,
    compute_adamic_adar,
    compute_effective_hub_ceiling,
    execute_swanson_crawl,
    get_wiki_stats,
    is_temporal_or_container_node,
)

RECEIPT_PATH = ROOT_DIR / "data" / "telemetry" / "adamic_adar_verification_receipt.json"


def run_verification() -> int:
    t0 = time.perf_counter()

    # 1. Verify Root Cellar 1-Hop Intersection (vegetable n food_preservation)
    rc_res = execute_swanson_crawl(
        CrawlRequest(
            source="vegetable",
            target="food_preservation",
            mode="bridges",
            dampen_super_hubs=True,
            max_hub_degree=5000,
            min_bridge_degree=2,
            exclude_temporal_containers=True,
        )
    )
    bridges = rc_res["bridges"]
    if not bridges:
        print("FAIL: Zero bridges returned for vegetable n food_preservation")
        return 1

    top_slug = bridges[0]["slug"]
    bottom_slug = bridges[-1]["slug"]
    degrees = [b["degree"] for b in bridges]
    scores = [b["adamic_adar_score"] for b in bridges]

    assert top_slug == "decomposition", f"Expected 'decomposition' at index 0, got '{top_slug}'"
    assert bottom_slug == "human", f"Expected 'human' at last index, got '{bottom_slug}'"
    assert degrees == sorted(degrees), f"Degrees not sorted ascending: {degrees}"
    assert scores == sorted(scores, reverse=True), f"Adamic-Adar scores not descending: {scores}"
    assert all(d >= 2 for d in degrees), "Stub node (deg < 2) leaked into bridges"

    # 2. Verify Temporal & Container Wormhole Masking (September 4 / Gilligan's Island bug)
    temporal_samples = [
        ("september_4", True),
        ("september_4_1967", True),
        ("1967", True),
        ("1967_in_television", True),
        ("list_of_indian_state_vegetables", True),
        ("category:living_people", True),
        ("decomposition", False),
        ("gilligan's_island", False),
        ("vxworks", False),
    ]
    for slug, expected in temporal_samples:
        actual = is_temporal_or_container_node(slug)
        assert actual == expected, f"is_temporal_or_container_node('{slug}') == {actual}, expected {expected}"

    # Verify september_4 is excluded when crawling between concepts linked by september_4
    path_res = execute_swanson_crawl(
        CrawlRequest(
            source="gilligan's_island",
            target="estonia",
            mode="path",
            exclude_temporal_containers=True,
        )
    )
    assert "september_4" not in path_res["path"], "Temporal wormhole 'september_4' leaked into path!"

    # 3. Verify Relative Hub Ceiling & Stub Floor Math
    small_cartridge_cap = compute_effective_hub_ceiling(5000, 0.05, domain_size=200)
    large_corpus_cap = compute_effective_hub_ceiling(5000, 0.05, domain_size=285409)
    assert small_cartridge_cap == 10, f"Expected 10 for 200-node cartridge, got {small_cartridge_cap}"
    assert large_corpus_cap == 5000, f"Expected 5000 for 285k corpus, got {large_corpus_cap}"
    assert compute_adamic_adar(0) == 0.0
    assert compute_adamic_adar(1) == 0.0
    assert compute_adamic_adar(24) == 0.3147

    stats = get_wiki_stats()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    receipt = {
        "ticket": "WO0011134",
        "status": "VERIFIED",
        "elapsed_ms": elapsed_ms,
        "stats": stats,
        "root_cellar_verification": {
            "source": "vegetable",
            "target": "food_preservation",
            "latency_us": rc_res["latency_us"],
            "total_bridges": rc_res["total_bridges"],
            "top_3_bridges": bridges[:3],
            "bottom_bridge": bridges[-1],
        },
        "temporal_wormhole_verification": {
            "september_4_masked": is_temporal_or_container_node("september_4"),
            "year_1967_masked": is_temporal_or_container_node("1967"),
            "gilligan_to_estonia_path": path_res["path"],
            "september_4_in_path": "september_4" in path_res["path"],
        },
        "domain_normalization_verification": {
            "cartridge_200_nodes_cap": small_cartridge_cap,
            "corpus_285k_nodes_cap": large_corpus_cap,
        },
    }

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
