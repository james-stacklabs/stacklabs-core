#!/usr/bin/env python3
"""
StackLabs Pilot Drops Filename Slugifier & POSIX Sanitizer Daemon
Path: /home/james/stacklabs/scripts/pilot_drops_slugifier.py

Monitors pilot_drops/ and pilot_drops/scratch/ for incoming files with spaces,
Unicode punctuation, or illegal characters, and atomically renames them to clean,
IDE-completable POSIX slugs once write handles settle.
"""

import os
import re
import sys
import time
import logging
import argparse
from pathlib import Path

# Paths
BASE_DIR = Path("/home/james/stacklabs")
PILOT_DROPS_DIR = BASE_DIR / "pilot_drops"
SCRATCH_DIR = PILOT_DROPS_DIR / "scratch"
LOG_PATH = BASE_DIR / "logs" / "pilot_drops_slugifier.log"

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SLUGIFIER] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pilot_drops_slugifier")

IGNORED_EXTENSIONS = {".tmp", ".crdownload", ".part", ".swp", ".lock"}


def slugify_name(filename: str) -> str:
    """Transforms a messy filename into a clean, POSIX-safe slug."""
    path_obj = Path(filename)
    stem = path_obj.stem
    suffix = path_obj.suffix.lower()

    # 1. Replace Unicode dashes (em-dash, en-dash, horizontal bar) with ASCII hyphen
    clean_stem = re.sub(r"[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]", "-", stem)

    # 2. Replace all whitespace sequences with a single underscore
    clean_stem = re.sub(r"\s+", "_", clean_stem)

    # 3. Strip problematic punctuation
    clean_stem = re.sub(r"[^\w\-\.]", "", clean_stem)

    # 4. Collapse mixed dividers around hyphens (e.g. '_-_' -> '-', '_-' -> '-', '-_' -> '-')
    clean_stem = re.sub(r"_+-_+|-_+|_+-", "-", clean_stem)

    # 5. Collapse duplicate underscores and hyphens (__ -> _, -- -> -)
    clean_stem = re.sub(r"_{2,}", "_", clean_stem)
    clean_stem = re.sub(r"-{2,}", "-", clean_stem)

    # 6. Trim leading and trailing hyphens/underscores/dots
    clean_stem = clean_stem.strip("._-")

    if not clean_stem:
        clean_stem = "unnamed_asset"

    return f"{clean_stem}{suffix}"


def is_file_settled(file_path: Path, wait_sec: float = 1.0) -> bool:
    """Verifies that the file is not currently being written by a browser or downloader."""
    if not file_path.is_file():
        return False

    if file_path.name.startswith("."):
        return False

    if file_path.suffix.lower() in IGNORED_EXTENSIONS:
        return False

    try:
        size1 = file_path.stat().st_size
        mtime = file_path.stat().st_mtime
        # If file was modified more than 5 seconds ago and has non-zero size, it has settled
        if time.time() - mtime > 5.0 and size1 > 0:
            return True
        time.sleep(wait_sec)
        size2 = file_path.stat().st_size
        return size1 == size2
    except OSError:
        return False


def sanitize_directory(target_dir: Path, dry_run: bool = False) -> int:
    """Scans target directory and renames files needing sanitization."""
    if not target_dir.exists():
        logger.warning(f"Target directory does not exist: {target_dir}")
        return 0

    renamed_count = 0
    for item in sorted(target_dir.iterdir()):
        if not item.is_file():
            continue

        orig_name = item.name
        if orig_name.startswith(".") or item.suffix.lower() in IGNORED_EXTENSIONS:
            continue

        clean_name = slugify_name(orig_name)
        if clean_name == orig_name:
            continue

        # Check if file has settled
        if not is_file_settled(item, wait_sec=1.0):
            logger.info(f"Skipping in-flight/unsettled file: {orig_name}")
            continue

        dest_path = target_dir / clean_name
        # Handle collision if target already exists
        if dest_path.exists() and dest_path.resolve() != item.resolve():
            counter = 1
            stem = Path(clean_name).stem
            suffix = Path(clean_name).suffix
            while dest_path.exists() and dest_path.resolve() != item.resolve():
                dest_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        logger.info(f"Renaming: '{orig_name}' -> '{dest_path.name}'")
        if not dry_run:
            try:
                os.replace(item, dest_path)
                renamed_count += 1
            except Exception as e:
                logger.error(f"Failed to rename {orig_name} -> {dest_path.name}: {e}")

    return renamed_count


def run_sweep(directories: list, dry_run: bool = False) -> int:
    """Runs a single sanitization pass across all configured dropzones."""
    total_renamed = 0
    for d in directories:
        logger.info(f"Scanning dropzone: {d}")
        total_renamed += sanitize_directory(Path(d), dry_run=dry_run)
    logger.info(f"Sweep complete. Total files sanitized: {total_renamed}")
    return total_renamed


def run_loop(directories: list, interval: float = 3.0):
    """Continuously monitors dropzones and sanitizes incoming files."""
    logger.info("⚡ Pilot Drops Slugifier Daemon activated.")
    logger.info(f"Monitoring: {[str(d) for d in directories]} (Interval: {interval}s)")
    try:
        while True:
            for d in directories:
                sanitize_directory(Path(d))
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Slugifier daemon stopped by operator.")


def main():
    parser = argparse.ArgumentParser(description="Pilot Drops Filename Slugifier & POSIX Sanitizer")
    parser.add_argument("--sweep", action="store_true", help="Run a single sweep and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log proposed renames without mutating files")
    parser.add_argument("--loop", action="store_true", help="Run continuously in background daemon loop")
    parser.add_argument("--interval", type=float, default=3.0, help="Loop poll interval in seconds")
    args = parser.parse_args()

    watch_dirs = [SCRATCH_DIR, PILOT_DROPS_DIR]

    if args.sweep or not args.loop:
        count = run_sweep(watch_dirs, dry_run=args.dry_run)
        sys.exit(0 if count >= 0 else 1)
    else:
        run_loop(watch_dirs, interval=args.interval)


if __name__ == "__main__":
    main()
