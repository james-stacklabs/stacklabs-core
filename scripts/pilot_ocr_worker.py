#!/usr/bin/env python3
"""
pilot_ocr_worker.py - Standalone Local Clio OCR Extractor & Batch Worker
Operates on Clio (x86_64 AMD Ryzen 7 7735HS) using local AVX2-accelerated Tesseract.
Extracts text from screenshots/images, generates <stem>_ocr.txt, and updates pilot_scratch_pad.md.

Usage:
    /home/james/stacklabs/.venv/bin/python3 scripts/pilot_ocr_worker.py --file <path-to-image>
    /home/james/stacklabs/.venv/bin/python3 scripts/pilot_ocr_worker.py --batch [--force]
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops")
DEFAULT_SCRATCHPAD = DEFAULT_DROPS_DIR / "pilot_scratch_pad.md"
TESSERACT_BIN = "/usr/bin/tesseract"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def run_ocr(image_path: Path, psm: int = 6, timeout: int = 15) -> str:
    """Execute local AVX2 Tesseract on Clio for instant text extraction."""
    if not Path(TESSERACT_BIN).exists():
        raise FileNotFoundError(f"Tesseract binary not found at {TESSERACT_BIN}")

    res = subprocess.run(
        [TESSERACT_BIN, str(image_path), "stdout", "--psm", str(psm)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True
    )
    return res.stdout.strip()


def process_image(
    image_path: Path,
    psm: int = 6,
    append_scratchpad: bool = True,
    scratchpad_path: Path = DEFAULT_SCRATCHPAD
) -> dict:
    """Process a single image: perform OCR, write text file, and append to scratchpad."""
    if not image_path.exists():
        return {"status": "error", "file": str(image_path), "message": "File not found"}

    start_time = time.perf_counter()
    try:
        text = run_ocr(image_path, psm=psm)
    except Exception as e:
        return {"status": "error", "file": str(image_path), "message": str(e)}

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    ocr_filename = f"{image_path.stem}_ocr.txt"
    ocr_path = image_path.parent / ocr_filename

    try:
        ocr_path.write_text(text, encoding="utf-8")
    except Exception as e:
        return {
            "status": "error",
            "file": str(image_path),
            "message": f"Failed to write text output: {e}"
        }

    if append_scratchpad and text:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n### [SCREENSHOT OCR: {image_path.name}] ({timestamp})\n\n{text}\n"
        try:
            scratchpad_path.parent.mkdir(parents=True, exist_ok=True)
            with open(scratchpad_path, "a", encoding="utf-8") as sf:
                sf.write(entry)
        except Exception as e:
            sys.stderr.write(f"Warning: could not append to scratchpad {scratchpad_path}: {e}\n")

    return {
        "status": "success",
        "file": str(image_path),
        "ocr_file": str(ocr_path),
        "length": len(text),
        "elapsed_ms": elapsed_ms,
        "text": text
    }


def process_batch(
    drops_dir: Path,
    psm: int = 6,
    force: bool = False,
    append_scratchpad: bool = True
) -> list:
    """Batch process images in drops_dir."""
    if not drops_dir.exists():
        print(f"Directory not found: {drops_dir}")
        return []

    images = [
        p for p in drops_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    results = []
    print(f"Scanning {drops_dir}: found {len(images)} image(s)...")
    for img in sorted(images):
        ocr_file = img.parent / f"{img.stem}_ocr.txt"
        if ocr_file.exists() and not force:
            print(f"  [SKIP] {img.name} (already OCR'd -> {ocr_file.name})")
            continue

        print(f"  [OCR] Processing {img.name}...", end=" ", flush=True)
        res = process_image(img, psm=psm, append_scratchpad=append_scratchpad)
        if res["status"] == "success":
            print(f"DONE in {res['elapsed_ms']}ms ({res['length']} chars)")
        else:
            print(f"FAILED: {res.get('message')}")
        results.append(res)

    return results


def main():
    parser = argparse.ArgumentParser(description="Local Clio Tesseract OCR Extractor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", "-f", type=Path, help="Path to single image file")
    group.add_argument("--batch", "-b", action="store_true", help="Batch process pilot_drops/ images")
    group.add_argument("--all", "-a", action="store_true", help="Alias for --batch")

    parser.add_argument("--dir", "-d", type=Path, default=DEFAULT_DROPS_DIR, help="Directory for batch scanning")
    parser.add_argument("--psm", type=int, default=6, help="Tesseract Page Segmentation Mode (default: 6)")
    parser.add_argument("--force", action="store_true", help="Force re-OCR even if _ocr.txt exists")
    parser.add_argument("--no-scratchpad", action="store_true", help="Do not append to pilot_scratch_pad.md")

    args = parser.parse_args()

    if args.file:
        res = process_image(
            args.file,
            psm=args.psm,
            append_scratchpad=not args.no_scratchpad
        )
        if res["status"] == "success":
            print(f"[SUCCESS] {res['file']} -> {res['ocr_file']}")
            print(f"Extracted {res['length']} characters in {res['elapsed_ms']}ms")
            print("-" * 50)
            print(res["text"])
            print("-" * 50)
            sys.exit(0)
        else:
            print(f"[ERROR] {res.get('message')}", file=sys.stderr)
            sys.exit(1)
    else:
        results = process_batch(
            drops_dir=args.dir,
            psm=args.psm,
            force=args.force,
            append_scratchpad=not args.no_scratchpad
        )
        success_count = sum(1 for r in results if r["status"] == "success")
        print(f"\nBatch complete: {success_count}/{len(results)} image(s) processed successfully.")


if __name__ == "__main__":
    main()
