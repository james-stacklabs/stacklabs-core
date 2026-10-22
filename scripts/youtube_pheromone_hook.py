#!/home/james/stacklabs/.venv/bin/python3
"""
YouTube Pheromone Hook & Real-Time Swanson Collision Terminal Emitter
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC

Ingests local audio transcripts or pulls YouTube media via yt-dlp,
triggers pheromone lens extraction, projects stigmergic markers to VFS,
and prints live Swanson 2-Hop Collision receipts.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.pheromone_lens_engine import (
    get_db_connection,
    ingest_transcript_pheromones,
    init_schema,
)
from scripts.swanson_vfs_collider import (
    VFS_COLLISIONS_ROOT,
    VFS_PHEROMONE_ROOT,
    atomic_symlink,
    run_swanson_collider,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("youtube_pheromone_hook")


def run_post_download_pheromone_hook(
    url: Optional[str] = None,
    transcript_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    sport: str = "CFB",
    show_name: str = "Broadcast Show",
) -> Dict[str, Any]:
    """
    Executes the full continuous ingestion reflex:
    1. Resolves transcript text from disk or pulls captions via yt-dlp.
    2. Runs pheromone lens extraction into SQLite WAL.
    3. Projects entity trails and active lenses to /home/james/stacklabs/vfs/pheromones/.
    4. Triggers 2-Hop Swanson VFS Collider and prints terminal receipt.
    """
    text = ""
    video_id = "LOCAL_INGEST"

    if output_dir:
        out_p = Path(output_dir)
        video_id = out_p.name

    if transcript_path:
        t_path = Path(transcript_path)
        if t_path.exists():
            text = t_path.read_text(encoding="utf-8", errors="replace")

    if not text and url:
        m_id = re.search(r"(?:v=|\/|youtu\.be\/)([A-Za-z0-9_-]{11})", url)
        if m_id:
            video_id = m_id.group(1)
        logger.info(f"Extracting captions for video {video_id} via yt-dlp...")
        try:
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang",
                "en",
                "--sub-format",
                "vtt",
                "-o",
                f"/tmp/ytsub_{video_id}.%(ext)s",
                url,
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            sub_file = Path(f"/tmp/ytsub_{video_id}.en.vtt")
            if sub_file.exists():
                text = sub_file.read_text(encoding="utf-8", errors="replace")
                sub_file.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"yt-dlp caption pull warning: {exc}")

    if not text:
        logger.error("No transcript text found or extracted.")
        return {"markers": [], "swanson_collisions": [], "swanson_vfs_walk_us": 0.0}

    conn = get_db_connection()
    init_schema(conn)

    result = ingest_transcript_pheromones(
        conn,
        text,
        source_show=show_name,
        video_id=video_id,
        sport=sport,
    )
    conn.close()

    print("=" * 84)
    print(f"  🎙️ PHEROMONE INGESTION: {show_name} [{video_id}] ({sport})")
    print(f"  Deposited {result.get('markers_deposited', 0)} markers")
    for m in result.get("markers", [])[:6]:
        print(f"    • [{m['entity_key']}] -> {m['lens_slug']}: \"{m.get('surface_stat_claim', '')}\"")

    if result.get("swanson_collisions"):
        walk_us = result.get("swanson_vfs_walk_us", 0)
        collisions = result.get("swanson_collisions", [])
        print(
            f"  ⚡ SWANSON 2-HOP VFS COLLISIONS ({walk_us} µs walk): "
            f"{len(collisions)} disjoint bridges"
        )
        for sc in collisions[:4]:
            score = sc.get("bisociation_score", 0.0)
            node_a = sc.get("node_a", "")
            node_c = sc.get("node_c", "")
            shared = ", ".join(sc.get("shared_lenses_b", []))
            print(f"    -> [{score:4.2f}] [{node_a}] <==({shared})==> [{node_c}]")
            if sc.get("complementary_lenses_to_test"):
                comp = sc["complementary_lenses_to_test"]
                comp_str = ", ".join(comp) if isinstance(comp, list) else str(comp)
                print(f"       Cross-Pollination Lead: Test {comp_str} across both!")
    print("=" * 84 + "\n")

    return result


def main():
    parser = argparse.ArgumentParser(description="YouTube Pheromone Hook")
    parser.add_argument("--url", type=str, help="YouTube Video URL")
    parser.add_argument("--transcript", type=str, help="Path to transcript file")
    parser.add_argument("--dir", type=str, help="Output or snipe directory")
    parser.add_argument("--sport", type=str, default="CFB", help="Sport code")
    parser.add_argument("--show", type=str, default="CFB Broadcast", help="Show Name")
    args = parser.parse_args()

    run_post_download_pheromone_hook(
        url=args.url,
        transcript_path=args.transcript,
        output_dir=args.dir,
        sport=args.sport,
        show_name=args.show,
    )


if __name__ == "__main__":
    main()
