#!/usr/bin/env python3
"""
Degenerate Media Vault Triage & Quarantine Scanner
Path: /home/james/stacklabs/scripts/triage_degenerate_gifs.py

Performs offline forensic triage, SHA-256 fingerprinting, binary header inspection,
and trademark/liability quarantine partitioning for media assets on Clio metal.
"""

import os
import sys
import json
import struct
import hashlib
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Trademark and studio liability triggers (case-insensitive)
TRADEMARK_TRIGGERS = [
    "batman", "joker", "superman", "spiderman", "spider-man",
    "warner", "warnerbros", "wb_", "dc_", "dc-", "dccomics", "dcuniverse",
    "marvel", "mcu", "disney", "pixar", "lucasfilm", "starwars",
    "paramount", "universal", "fox", "twentyfirstcenturyfox",
    "nfl", "espn", "nba", "mlb", "nhl", "pga"
]

# Sensitive or inappropriate content triggers
CONTENT_TRIGGERS = [
    "nsfw", "xxx", "nude", "nudity", "porn", "gore", "leaked", "confidential"
]


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 digest of file reading in 64KB blocks."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect_gif_binary(filepath: Path) -> dict:
    """
    Inspect binary GIF structure:
    - Verifies GIF87a or GIF89a magic signature.
    - Extracts logical screen width and height.
    - Scans for comment extensions (0x21 0xFE).
    - Checks for GIF trailer byte (0x3B).
    """
    result = {
        "is_valid_gif": False,
        "version": None,
        "width": 0,
        "height": 0,
        "has_trailer": False,
        "comments": [],
        "error": None
    }
    try:
        size = filepath.stat().st_size
        if size < 13:
            result["error"] = "File too small for GIF header"
            return result

        with open(filepath, "rb") as f:
            data = f.read(size)

        magic = data[:6].decode("ascii", errors="ignore")
        if magic in ("GIF87a", "GIF89a"):
            result["is_valid_gif"] = True
            result["version"] = magic
            w, h = struct.unpack("<HH", data[6:10])
            result["width"] = w
            result["height"] = h
        else:
            result["error"] = f"Invalid GIF magic: {magic}"
            return result

        if data[-1] == 0x3B:
            result["has_trailer"] = True
        else:
            result["error"] = "Missing GIF trailer byte (0x3B)"

        # Scan for Comment Extension blocks (0x21 0xFE)
        pos = 13
        data_len = len(data)
        while pos < data_len - 2:
            if data[pos] == 0x21 and data[pos + 1] == 0xFE:
                pos += 2
                comment_parts = []
                while pos < data_len:
                    sub_len = data[pos]
                    pos += 1
                    if sub_len == 0:
                        break
                    part = data[pos:pos + sub_len].decode("ascii", errors="ignore")
                    comment_parts.append(part)
                    pos += sub_len
                if comment_parts:
                    result["comments"].append(" ".join(comment_parts).strip())
            else:
                pos += 1

    except Exception as e:
        result["error"] = f"Header parsing exception: {str(e)}"

    return result


def evaluate_asset(filepath: Path, gif_info: dict) -> dict:
    """Evaluate asset risk profile against trademark and content triggers."""
    matched_trademarks = []
    matched_content = []

    text_to_screen = filepath.name.lower()
    for comment in gif_info.get("comments", []):
        text_to_screen += " " + comment.lower()

    for trig in TRADEMARK_TRIGGERS:
        if trig in text_to_screen:
            matched_trademarks.append(trig)

    for trig in CONTENT_TRIGGERS:
        if trig in text_to_screen:
            matched_content.append(trig)

    if not gif_info["is_valid_gif"] or not gif_info["has_trailer"]:
        status = "CORRUPT"
        risk_level = "ERROR"
    elif matched_content:
        status = "QUARANTINED"
        risk_level = "CRITICAL_CONTENT"
    elif matched_trademarks:
        status = "QUARANTINED"
        risk_level = "TRADEMARK_RESTRICTED"
    else:
        status = "CLEAN_BLEACHER"
        risk_level = "LOW_SAFE"

    return {
        "status": status,
        "risk_level": risk_level,
        "matched_trademarks": matched_trademarks,
        "matched_content": matched_content
    }


def triage_media(staging_dir: Path, quarantine_dir: Path, include_dirs: list = None, isolate: bool = False) -> dict:
    """Run full triage pass across staging and optional additional source directories."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    search_dirs = [staging_dir]
    if include_dirs:
        for d in include_dirs:
            p = Path(d)
            if p.exists() and p not in search_dirs:
                search_dirs.append(p)

    assets = []
    quarantined_count = 0
    clean_count = 0
    corrupt_count = 0

    for sdir in search_dirs:
        for file in sdir.glob("*.gif"):
            if not file.is_file():
                continue

            file_hash = compute_sha256(file)
            gif_info = inspect_gif_binary(file)
            eval_res = evaluate_asset(file, gif_info)

            asset_record = {
                "filename": file.name,
                "source_path": str(file),
                "sha256": file_hash,
                "size_bytes": file.stat().st_size,
                "dimensions": f"{gif_info['width']}x{gif_info['height']}",
                "gif_version": gif_info["version"],
                "has_trailer": gif_info["has_trailer"],
                "status": eval_res["status"],
                "risk_level": eval_res["risk_level"],
                "matched_trademarks": eval_res["matched_trademarks"],
                "matched_content": eval_res["matched_content"],
                "comments": gif_info["comments"],
                "error": gif_info["error"],
                "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

            if eval_res["status"] == "QUARANTINED":
                quarantined_count += 1
                if isolate and file.parent != quarantine_dir:
                    dest = quarantine_dir / file.name
                    shutil.copy2(file, dest)
                    asset_record["quarantine_path"] = str(dest)
            elif eval_res["status"] == "CLEAN_BLEACHER":
                clean_count += 1
            else:
                corrupt_count += 1

            assets.append(asset_record)

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_scanned": len(assets),
        "quarantined": quarantined_count,
        "clean_bleacher": clean_count,
        "corrupt": corrupt_count,
        "assets": assets
    }
    return manifest


def generate_markdown_report(manifest: dict, output_report_path: Path):
    """Generate executive Markdown audit report."""
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 🛡️ STACKLABS MEDIA VAULT: FORENSIC AUDIT & QUARANTINE REPORT",
        f"**Audit Timestamp**: `{manifest['timestamp']}`  ",
        "**Node**: Clio Metal Forge (Smyrna, GA)  ",
        f"**Total Scanned**: `{manifest['total_scanned']}` | "
        f"**Quarantined**: `{manifest['quarantined']}` | "
        f"**Clean Bleacher**: `{manifest['clean_bleacher']}` | "
        f"**Corrupt**: `{manifest['corrupt']}`  ",
        "",
        "---",
        "",
        "## 📋 ASSET TRIAGE LEDGER",
        "",
        "| Filename | Dimensions | Size | Status | Risk Level | Detected Triggers | SHA-256 (Truncated) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for a in manifest["assets"]:
        triggers = ", ".join(a["matched_trademarks"] + a["matched_content"]) or "None"
        sha_short = a["sha256"][:12] + "..."
        lines.append(
            f"| `{a['filename']}` | {a['dimensions']} | {a['size_bytes']:,} B | "
            f"**{a['status']}** | `{a['risk_level']}` | {triggers} | `{sha_short}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 🔒 POLICY & AIR-GAP ENFORCEMENT",
        "1. **Quarantined Assets**: All assets flagged with studio trademarks or liability triggers are strictly partitioned to `data/quarantine_archive/`. They must NEVER be bundled into frontend builds or public repositories.",
        "2. **Bleacher Presentation Assets**: Only assets flagged `CLEAN_BLEACHER` are permitted for mapping into 4-byte telemetry reaction frames.",
        "3. **Zero Dynamic Allocation**: SHA-256 digests serve as immutable primary keys for all media metadata."
    ])

    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Degenerate Media Triage & Quarantine Scanner")
    parser.add_argument("--staging-dir", default="/home/james/stacklabs/data/staging_media", help="Staging directory for incoming media")
    parser.add_argument("--quarantine-dir", default="/home/james/stacklabs/data/quarantine_archive", help="Isolated directory for quarantined assets")
    parser.add_argument("--include-dir", action="append", help="Additional directories to scan (e.g. pilot_drops)")
    parser.add_argument("--manifest-out", default="/home/james/stacklabs/data/gif_triage_manifest.json", help="Path to write JSON manifest")
    parser.add_argument("--report-out", default="/home/james/stacklabs/stacklabs_inbox/reports/GIF_VAULT_AUDIT.md", help="Path to write Markdown audit report")
    parser.add_argument("--isolate", action="store_true", help="Copy quarantined files to quarantine archive")

    args = parser.parse_args()

    staging_dir = Path(args.staging_dir)
    quarantine_dir = Path(args.quarantine_dir)
    manifest_path = Path(args.manifest_out)
    report_path = Path(args.report_out)

    manifest = triage_media(staging_dir, quarantine_dir, include_dirs=args.include_dir, isolate=args.isolate)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    generate_markdown_report(manifest, report_path)

    print(f"[OK] Triage scan complete.")
    print(f"     Total Scanned: {manifest['total_scanned']}")
    print(f"     Quarantined:   {manifest['quarantined']}")
    print(f"     Clean:         {manifest['clean_bleacher']}")
    print(f"     Corrupt:       {manifest['corrupt']}")
    print(f"     Manifest:      {manifest_path}")
    print(f"     Report:        {report_path}")


if __name__ == "__main__":
    main()
