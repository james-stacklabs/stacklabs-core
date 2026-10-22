#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Single-Truth Spark Intake & Cryptographic Chain-of-Custody Pipeline
# Path: /home/james/stacklabs/scripts/spark_intake.py
# Governed by: WO0010259 / Invariant 18 / "Stay Behind Your Skis" / No Snake Oil
#
# Capabilities:
# 1. Intake & Cryptographic Fingerprinting (Raw SHA-256 before any mutation)
# 2. Quality & Grounded Metal Linter (ASCII boxes, unrendered prompts, puffery)
# 3. Standardized Provenance Block Injection (Immutable tenant & custody seal)
# 4. Drive Root Cleanup Utility (--clean-root: move loose Google Doc drafts to trash)
# 5. Multi-Lane Sync Integration (stacklabs_edge:02_... / 03_...)
# 6. JSON Chain-of-Custody Ledger (/home/james/stacklabs/dna/docs/SPARK_DOCUMENT_CHAIN_OF_CUSTODY.json)
# ==============================================================================

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# System Directories & Constants
PILOT_DROPS_DIR = "/home/james/sovereign_inbox/pilot_drops"
CANONICAL_DOCS_DIR = "/home/james/stacklabs/dna/docs"
CUSTODY_LEDGER_PATH = "/home/james/stacklabs/dna/docs/SPARK_DOCUMENT_CHAIN_OF_CUSTODY.json"

REMOTE_ROOT = "stacklabs_edge:"
LANE_02 = "02_Edge_Platform_Engineering"
LANE_03 = "03_WildSeed_Sovereign_Swarm"

LANE_ALIASES = {
    "02": LANE_02,
    "2": LANE_02,
    "lane2": LANE_02,
    "lane_02": LANE_02,
    "02_Edge_Platform_Engineering": LANE_02,
    "03": LANE_03,
    "3": LANE_03,
    "lane3": LANE_03,
    "lane_03": LANE_03,
    "03_WildSeed_Sovereign_Swarm": LANE_03,
}

SOURCE_ENGINE_TENANT = "Google Gemini Spark (gemini.google.com/spark/tasks) // stacklabs.edge@gmail.com"
INGRESS_HOST = "clio (clio.taila01894.ts.net)"

# ANSI Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def calculate_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest for given byte payload."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def calculate_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hex digest of file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_ledger(ledger_path: str = CUSTODY_LEDGER_PATH) -> Dict[str, Any]:
    """Load existing JSON chain-of-custody ledger or initialize fresh ledger."""
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"{YELLOW}⚠️ Warning loading existing ledger ({e}). Reinitializing.{RESET}")

    return {
        "version": "1.0.0",
        "system": "Sovereign OS Spark Intake & Cryptographic Chain-of-Custody",
        "host": "clio",
        "tenant": "stacklabs.edge@gmail.com",
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": []
    }


def save_ledger(ledger: Dict[str, Any], ledger_path: str = CUSTODY_LEDGER_PATH) -> None:
    """Save ledger atomically with indentation."""
    ledger["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    temp_path = f"{ledger_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    os.replace(temp_path, ledger_path)


# ==============================================================================
# Quality & Grounded Metal Linter
# ==============================================================================

LINTER_PATTERNS = [
    {
        "flag": "ASCII_BOX_DIAGRAM",
        "regex": re.compile(r'^\s*(\\?\+[-=]{3,}\\?\+?|\+[-=]{3,}\+)', re.MULTILINE),
        "message": "Commodore-64 ASCII box diagram detected. Recommend modern Markdown table or mermaid diagram.",
        "severity": "WARNING"
    },
    {
        "flag": "UNRENDERED_IMAGE_PROMPT",
        "regex": re.compile(r'(\\?\[IMAGE\s+(?:GENERATION\s+)?PROMPT\\?\])', re.IGNORECASE),
        "message": "Unrendered image generation prompt placeholder detected. Requires visual twin asset generation or removal.",
        "severity": "WARNING"
    },
    {
        "flag": "UNRENDERED_IMAGEN_HEADING",
        "regex": re.compile(r'^\s*##+\s*.*IMAGEN.*PROMPT', re.MULTILINE | re.IGNORECASE),
        "message": "Unrendered Imagen prompt skeleton heading detected. Requires live generation or clean removal.",
        "severity": "WARNING"
    },
    {
        "flag": "UNCLOSED_DEAL_PUFFERY",
        "regex": re.compile(r'\b(deployed\s+(to|at|in)|installed\s+(at|in)|installing\s+in|operational\s+at)\s+(Davidson\s+Homes|Woods\s+Crossing)\b', re.IGNORECASE),
        "message": "Unclosed deal deployment claim detected. Jeremy Malone / Davidson Homes / Woods Crossing is strictly an exploratory prospect or PROSPECT_SCENARIO.",
        "severity": "CRITICAL"
    },
    {
        "flag": "ABSOLUTE_VICTORY_CLAIM",
        "regex": re.compile(r'\b(mathematically\s+compelled|compelled\s+to\s+rank|guaranteed\s+(SERP|ranking|conquest)|instant\s+monopoly|1000%\s+secure|unassailable\s+moat)\b', re.IGNORECASE),
        "message": "Absolute victory claim detected. Ground truth mandates empirical systems engineering framing over hype.",
        "severity": "WARNING"
    },
    {
        "flag": "GROUNDED_PAYBACK_VIOLATION",
        "regex": re.compile(r'\b7\.38\s*days?\b(?![^.\n]*\b(theoretical|hypothetical|upsell|software add-on)\b)', re.IGNORECASE),
        "message": "Payback drift detected. Audited baseline payback is strictly 12.53 days. 7.38 days must be fenced as hypothetical software upsell.",
        "severity": "CRITICAL"
    },
    {
        "flag": "DELAWARE_HALLUCINATION",
        "regex": re.compile(r'\bStackLabs\b[^.\n]*\bDelaware\b', re.IGNORECASE),
        "message": "Delaware entity hallucination detected. StackLabs LLC is strictly a Georgia LLC (Smyrna, GA).",
        "severity": "CRITICAL"
    },
    {
        "flag": "NAME_SPELLING_SLOP",
        "regex": re.compile(r'\bMichael\s+McLaren\b'),
        "message": "Name spelling slop: 'Michael McLaren' detected. Ground truth requires lowercase 'l': 'Michael Mclaren'.",
        "severity": "WARNING"
    }
]


def lint_document(content: str) -> Dict[str, Any]:
    """Scan document content with the Quality & Grounded Metal Linter."""
    findings = []
    lines = content.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        for rule in LINTER_PATTERNS:
            match = rule["regex"].search(line)
            if match:
                snippet = line.strip()
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                findings.append({
                    "line": line_idx,
                    "flag": rule["flag"],
                    "severity": rule["severity"],
                    "message": rule["message"],
                    "matched_text": match.group(0),
                    "snippet": snippet
                })

    status = "CLEAN" if not findings else "WARNINGS_FOUND"
    flags = sorted(list(set(f["flag"] for f in findings)))

    return {
        "status": status,
        "total_warnings": len(findings),
        "flags": flags,
        "findings": findings
    }


def print_linter_report(linter_result: Dict[str, Any], filepath: str) -> None:
    """Print formatted linter results to terminal."""
    total = linter_result["total_warnings"]
    status = linter_result["status"]

    print(f"\n{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}🔍 QUALITY & GROUNDED METAL LINTER REPORT{RESET}")
    print(f"📄 Target File: {CYAN}{filepath}{RESET}")
    print(f"🛡️ Audit Status: {GREEN if status == 'CLEAN' else YELLOW}{status}{RESET} ({total} finding{'s' if total != 1 else ''})")
    print(f"{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")

    if not linter_result["findings"]:
        print(f"  {GREEN}✔ No Grounded Metal violations, ASCII box diagrams, or unrendered prompts detected.{RESET}")
        return

    for item in linter_result["findings"]:
        color = RED if item["severity"] == "CRITICAL" else YELLOW
        print(f"  {color}▶ Line {item['line']:4d} [{item['flag']} - {item['severity']}]{RESET}")
        print(f"    {DIM}Snippet:{RESET} {item['snippet']}")
        print(f"    {BOLD}Remediation:{RESET} {item['message']}")
        print()


# ==============================================================================
# Document Parsing & Metadata Extraction
# ==============================================================================

def extract_document_metadata(content: str, filename: str) -> Dict[str, str]:
    """Extract document ID, title, and determine appropriate canonical target lane."""
    # 1. Document Title
    title = ""
    title_match = re.search(r'^#\s+\*?\*?([^\n\*]+)\*?\*?', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = Path(filename).stem.replace("_", " ").replace("-", " ")

    # 2. Document Identifier
    doc_id = ""
    id_match = re.search(r'\*\*(?:Document\s+(?:ID|Reference)|Ticket\s+ID|Article\s+ID):\*\*\s*`?([A-Za-z0-9_\-\/]+)`?', content, re.IGNORECASE)
    if id_match:
        doc_id = id_match.group(1).strip()
    else:
        slug = re.sub(r'[^A-Za-z0-9]+', '-', Path(filename).stem).strip('-').upper()
        doc_id = f"SPARK-DOC-{slug[:32]}"

    # 3. Canonical Target Lane Detection
    # If content touches botanical / WildSeed / living soil / solventless / terpene -> Lane 03
    wildseed_keywords = re.compile(r'\b(wildseed|botanical|terpene|rosin|solventless|living soil|dcc|chemovar|trichome|metrc)\b', re.IGNORECASE)
    if wildseed_keywords.search(content) or "wildseed" in filename.lower():
        detected_lane = LANE_03
    else:
        detected_lane = LANE_02

    return {
        "title": title,
        "doc_id": doc_id,
        "detected_lane": detected_lane
    }


# ==============================================================================
# Standardized Provenance Block Injection
# ==============================================================================

PROVENANCE_BLOCK_TAG = "🏛️ Sovereign OS Cryptographic Provenance Block"
PROVENANCE_START_REGEX = re.compile(r'<!--\s*=+\s*-->\s*\n<!--\s*🏛️\s*SOVEREIGN OS CRYPTOGRAPHIC PROVENANCE.*?<!--\s*=+\s*-->.*?>\s*###\s*🏛️\s*Sovereign OS Cryptographic Provenance Block.*?(?=\n\n|\n#|\n---|\Z)', re.DOTALL)


def render_provenance_block(doc_id: str, raw_sha256: str, canonical_sha256: str, target_lane: str, timestamp: str) -> str:
    """Render standardized, immutable Sovereign OS Provenance Block."""
    lane_remote_path = f"{REMOTE_ROOT}{target_lane}/"
    return f"""<!-- ============================================================================== -->
<!-- 🏛️ SOVEREIGN OS CRYPTOGRAPHIC PROVENANCE & CHAIN-OF-CUSTODY BLOCK              -->
<!-- ============================================================================== -->
<!-- Document Identifier  : {doc_id} -->
<!-- Source Engine & Tenant: {SOURCE_ENGINE_TENANT} -->
<!-- Ingress Host         : {INGRESS_HOST} -->
<!-- Raw Intake SHA-256   : {raw_sha256} -->
<!-- Audited Canonical SHA: {canonical_sha256} -->
<!-- Canonical Target Lane: {lane_remote_path} -->
<!-- Custody Status       : AUDITED & CANONICAL -->
<!-- Attestation Timestamp: {timestamp} -->
<!-- ============================================================================== -->

> ### 🏛️ Sovereign OS Cryptographic Provenance Block
> | Field | Value |
> | :--- | :--- |
> | **Document Identifier** | `{doc_id}` |
> | **Source Engine & Tenant** | `Google Gemini Spark (gemini.google.com/spark/tasks)` // `stacklabs.edge@gmail.com` |
> | **Raw Intake SHA-256** | `{raw_sha256}` |
> | **Audited Canonical SHA-256** | `{canonical_sha256}` |
> | **Canonical Target Lane** | `{lane_remote_path}` |
> | **Chain-of-Custody Status** | `AUDITED & CANONICAL` |
> | **Ingress Host & Node** | `clio` (`clio.taila01894.ts.net`) |
> | **Attestation Timestamp** | `{timestamp}` |
"""


def inject_provenance_block(content: str, doc_id: str, raw_sha256: str, canonical_sha256: str, target_lane: str, timestamp: str) -> str:
    """Inject or update the standardized provenance block in document."""
    block = render_provenance_block(doc_id, raw_sha256, canonical_sha256, target_lane, timestamp)

    # Check if an existing provenance block exists
    if PROVENANCE_BLOCK_TAG in content:
        # Replace existing provenance block section
        updated = PROVENANCE_START_REGEX.sub(block.strip(), content)
        if updated != content:
            return updated

    # Find position after first H1 header
    h1_match = re.search(r'^(#\s+[^\n]+)', content, re.MULTILINE)
    if h1_match:
        end_pos = h1_match.end()
        # Find newline after header
        after_header = content[:end_pos] + "\n\n" + block + "\n" + content[end_pos:].lstrip("\n")
        return after_header

    # Default: insert at top
    return block + "\n\n" + content


# ==============================================================================
# Drive Root Cleanup Utility (--clean-root)
# ==============================================================================

def clean_remote_root(remote: str = REMOTE_ROOT, dry_run: bool = False) -> List[str]:
    """Inspect remote root and move loose files to trash using rclone."""
    print(f"\n{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}🧹 DRIVE ROOT CLEANUP UTILITY ({remote}){RESET}")
    print(f"{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")

    try:
        # Check remote availability
        cmd = ["rclone", "lsf", "--files-only", "--max-depth", "1", remote]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"{RED}❌ ERROR: Failed to list root files on {remote}: {e.stderr}{RESET}")
        return []
    except FileNotFoundError:
        print(f"{RED}❌ ERROR: rclone command not found in PATH.{RESET}")
        return []

    if not raw_files:
        print(f"  {GREEN}✔ Remote root '{remote}' is pristine (0 loose files found).{RESET}")
        return []

    print(f"  {YELLOW}⚠️ Detected {len(raw_files)} loose file(s) in root of {remote}:{RESET}")
    cleaned = []

    for fname in raw_files:
        remote_target = f"{remote}{fname}"
        if dry_run:
            print(f"  {CYAN}[DRY-RUN]{RESET} Would move to trash: {remote_target}")
            cleaned.append(fname)
        else:
            print(f"  🗑️ Moving to trash: {remote_target} ...")
            try:
                # rclone default moves to trash on Google Drive
                del_cmd = ["rclone", "deletefile", remote_target]
                subprocess.run(del_cmd, capture_output=True, text=True, check=True)
                print(f"     {GREEN}✔ Moved to trash successfully.{RESET}")
                cleaned.append(fname)
            except subprocess.CalledProcessError as e:
                print(f"     {RED}❌ Failed to move {fname} to trash: {e.stderr.strip()}{RESET}")

    return cleaned


# ==============================================================================
# Multi-Lane Sync Integration
# ==============================================================================

def sync_file_to_lane(local_filepath: str, target_lane: str, remote: str = REMOTE_ROOT, dry_run: bool = False) -> bool:
    """Synchronize audited canonical deliverable to target lane via rclone copyto."""
    filename = os.path.basename(local_filepath)
    destination = f"{remote}{target_lane}/{filename}"

    print(f"\n{BOLD}🚀 MULTI-LANE SYNC INTEGRATION{RESET}")
    print(f"  📄 Source Local : {CYAN}{local_filepath}{RESET}")
    print(f"  📡 Target Remote: {GREEN}{destination}{RESET}")

    if dry_run:
        print(f"  {CYAN}[DRY-RUN]{RESET} Would execute: rclone copyto {local_filepath} {destination}")
        return True

    try:
        # Ensure remote directory exists
        subprocess.run(["rclone", "mkdir", f"{remote}{target_lane}"], capture_output=True, check=True)
        # Execute copyto
        cmd = ["rclone", "copyto", local_filepath, destination]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  {GREEN}✔ Multi-lane sync successful!{RESET}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  {RED}❌ Multi-lane sync error: {e.stderr.strip()}{RESET}")
        return False


# ==============================================================================
# Intake & Audit Orchestration
# ==============================================================================

def resolve_target_file(arg_file: Optional[str]) -> str:
    """Resolve file path from argument or latest in pilot_drops."""
    if arg_file and arg_file != "__LATEST__":
        candidates = [
            arg_file,
            os.path.join(PILOT_DROPS_DIR, arg_file),
            os.path.join(CANONICAL_DOCS_DIR, arg_file)
        ]
        for c in candidates:
            if os.path.isfile(c):
                return os.path.abspath(c)
        raise FileNotFoundError(f"Cannot locate document '{arg_file}'. Searched in cwd, pilot_drops, and dna/docs.")

    # Find newest markdown file in pilot_drops
    md_files = glob.glob(os.path.join(PILOT_DROPS_DIR, "*.md"))
    if not md_files:
        raise FileNotFoundError(f"No markdown documents found in {PILOT_DROPS_DIR}")

    # Exclude scratch pads if other candidates exist
    valid_candidates = [f for f in md_files if "scratch_pad" not in os.path.basename(f).lower()]
    if valid_candidates:
        md_files = valid_candidates

    newest = max(md_files, key=os.path.getmtime)
    return os.path.abspath(newest)


def execute_intake_pipeline(
    filepath: str,
    lane_override: Optional[str] = None,
    run_audit: bool = True,
    run_sync: bool = False,
    output_dir: str = CANONICAL_DOCS_DIR,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Execute complete Intake & Cryptographic Chain-of-Custody Pipeline."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = os.path.basename(filepath)

    print(f"\n{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}⚡ SPARK INTAKE & CRYPTOGRAPHIC CHAIN-OF-CUSTODY PIPELINE{RESET}")
    print(f"🕒 Timestamp: {timestamp}")
    print(f"📄 Intake File: {CYAN}{filepath}{RESET}")
    print(f"{BOLD}══════════════════════════════════════════════════════════════════════{RESET}")

    # 1. Raw Byte Read & Cryptographic Intake Fingerprinting
    with open(filepath, "rb") as f:
        raw_bytes = f.read()

    spark_raw_sha256 = calculate_sha256(raw_bytes)
    print(f"  🔐 {BOLD}Raw Intake SHA-256:{RESET} {GREEN}{spark_raw_sha256}{RESET}")

    raw_text = raw_bytes.decode("utf-8", errors="replace")

    # 2. Document Metadata & Lane Resolution
    meta = extract_document_metadata(raw_text, filename)
    doc_id = meta["doc_id"]
    title = meta["title"]
    target_lane = LANE_ALIASES.get(lane_override, lane_override) if lane_override else meta["detected_lane"]

    print(f"  📋 {BOLD}Document ID:{RESET}     {CYAN}{doc_id}{RESET}")
    print(f"  🏷️ {BOLD}Document Title:{RESET}  {title}")
    print(f"  🛣️ {BOLD}Target Lane:{RESET}     {MAGENTA}{target_lane}{RESET}")

    # 3. Quality & Grounded Metal Linter
    linter_result = {}
    if run_audit:
        linter_result = lint_document(raw_text)
        print_linter_report(linter_result, filepath)

    # 4. Standardized Provenance Block Injection
    # We calculate the audited canonical hash of the document body
    # Then inject the provenance block with both raw and canonical hashes
    audited_body_hash = calculate_sha256(raw_text.encode("utf-8"))
    audited_content = inject_provenance_block(
        content=raw_text,
        doc_id=doc_id,
        raw_sha256=spark_raw_sha256,
        canonical_sha256=audited_body_hash,
        target_lane=target_lane,
        timestamp=timestamp
    )
    final_file_hash = calculate_sha256(audited_content.encode("utf-8"))

    # Canonical destination path
    canonical_local_path = os.path.join(output_dir, filename)

    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)
        with open(canonical_local_path, "w", encoding="utf-8") as f:
            f.write(audited_content)
        print(f"  💾 {BOLD}Canonical Deliverable Written:{RESET} {CYAN}{canonical_local_path}{RESET}")
    else:
        print(f"  {CYAN}[DRY-RUN]{RESET} Would write canonical deliverable to: {canonical_local_path}")

    # 5. Multi-Lane Sync (Optional or enabled by --sync)
    synced = False
    sync_time = None
    if run_sync:
        synced = sync_file_to_lane(canonical_local_path, target_lane, REMOTE_ROOT, dry_run=dry_run)
        if synced and not dry_run:
            sync_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 6. Ledger Registration (/home/james/stacklabs/dna/docs/SPARK_DOCUMENT_CHAIN_OF_CUSTODY.json)
    ledger_record = {
        "doc_id": doc_id,
        "title": title,
        "filename": filename,
        "raw_source_path": filepath,
        "canonical_local_path": canonical_local_path,
        "spark_raw_sha256": spark_raw_sha256,
        "spark_canonical_sha256": audited_body_hash,
        "final_file_sha256": final_file_hash,
        "target_lane": target_lane,
        "remote_destination": f"{REMOTE_ROOT}{target_lane}/{filename}",
        "linter_audit": {
            "status": linter_result.get("status", "NOT_RUN"),
            "total_warnings": linter_result.get("total_warnings", 0),
            "flags": linter_result.get("flags", [])
        },
        "provenance_injected": True,
        "synced": synced,
        "intake_timestamp": timestamp,
        "sync_timestamp": sync_time
    }

    if not dry_run:
        ledger = load_ledger()
        # Deduplicate or update existing record by raw SHA-256 or doc_id
        updated_records = [r for r in ledger["records"] if r.get("spark_raw_sha256") != spark_raw_sha256 and r.get("doc_id") != doc_id]
        updated_records.append(ledger_record)
        ledger["records"] = updated_records
        save_ledger(ledger)
        print(f"  📖 {BOLD}Chain-of-Custody Ledger Updated:{RESET} {GREEN}{CUSTODY_LEDGER_PATH}{RESET} ({len(ledger['records'])} entries)")
    else:
        print(f"  {CYAN}[DRY-RUN]{RESET} Would append entry to {CUSTODY_LEDGER_PATH}")

    print(f"\n{GREEN}{BOLD}✔ Spark Intake Pipeline Completed Successfully.{RESET}\n")
    return ledger_record


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sovereign OS: Spark Intake & Cryptographic Chain-of-Custody Pipeline (Tool #46)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Perform full intake on a specific file from pilot_drops:
  spark_intake.py --intake "WildSeed Extracts_ Sovereign Botanical Master Blueprint.md"

  # Run standalone Grounded Metal linter on a document:
  spark_intake.py --audit "INSTITUTIONAL HARDWARE ENGINEERING SPECIFICATION & COMMERCIAL INFRASTRUCTURE BLUEPRINT.md"

  # Clean loose files from stacklabs_edge Google Drive root:
  spark_intake.py --clean-root

  # Intake newest drop, enforce Lane 02, and sync to remote Google Drive:
  spark_intake.py --intake --lane 02 --sync

  # List all documents currently tracked in Chain-of-Custody ledger:
  spark_intake.py --list
        """
    )

    parser.add_argument(
        "--intake",
        nargs="?",
        const="__LATEST__",
        metavar="FILE",
        help="Execute intake & cryptographic fingerprinting on target markdown file (defaults to newest in pilot_drops)."
    )
    parser.add_argument(
        "--audit",
        nargs="?",
        const="__LATEST__",
        metavar="FILE",
        help="Run Quality & Grounded Metal Linter on target document."
    )
    parser.add_argument(
        "--clean-root",
        action="store_true",
        help="Inspect stacklabs_edge: Google Drive root for loose files/drafts and move them to trash."
    )
    parser.add_argument(
        "--lane",
        metavar="LANE",
        choices=["02", "03", "02_Edge_Platform_Engineering", "03_WildSeed_Sovereign_Swarm"],
        help="Specify target lane (02_Edge_Platform_Engineering or 03_WildSeed_Sovereign_Swarm)."
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize audited canonical deliverable to remote Google Drive lane via rclone copyto."
    )
    parser.add_argument(
        "--clean-and-sync",
        action="store_true",
        help="Execute root cleanup first, then perform intake and sync."
    )
    parser.add_argument(
        "--output-dir",
        default=CANONICAL_DOCS_DIR,
        metavar="DIR",
        help=f"Local target directory for audited canonical documents (default: {CANONICAL_DOCS_DIR})."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Display all documents registered in the Chain-of-Custody ledger."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying files, ledger, or remote storage."
    )

    args = parser.parse_args()

    # If no flags are passed, show help
    if not any([args.intake, args.audit, args.clean_root, args.list, args.clean_and_sync]):
        parser.print_help()
        sys.exit(0)

    # 1. Clean root if requested
    if args.clean_root or args.clean_and_sync:
        clean_remote_root(REMOTE_ROOT, dry_run=args.dry_run)

    # 2. List ledger
    if args.list:
        ledger = load_ledger()
        records = ledger.get("records", [])
        print(f"\n{BOLD}📜 SPARK DOCUMENT CHAIN-OF-CUSTODY LEDGER ({len(records)} Records){RESET}")
        print(f"Path: {CYAN}{CUSTODY_LEDGER_PATH}{RESET}\n")
        if not records:
            print("  (Ledger is currently empty)")
        for idx, rec in enumerate(records, start=1):
            print(f"{BOLD}[{idx:02d}] {rec.get('doc_id')}{RESET} - {rec.get('title')}")
            print(f"     File     : {rec.get('filename')}")
            print(f"     Raw Hash : {rec.get('spark_raw_sha256')}")
            print(f"     Canon Hash: {rec.get('spark_canonical_sha256')}")
            print(f"     Lane     : {rec.get('target_lane')}")
            print(f"     Synced   : {rec.get('synced')} ({rec.get('sync_timestamp') or 'Never'})")
            print(f"     Audit    : {rec.get('linter_audit', {}).get('status')} ({rec.get('linter_audit', {}).get('total_warnings', 0)} warnings)")
            print()
        sys.exit(0)

    # 3. Standalone Audit
    if args.audit and not args.intake and not args.clean_and_sync:
        target_path = resolve_target_file(args.audit)
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        linter_res = lint_document(content)
        print_linter_report(linter_res, target_path)
        sys.exit(0)

    # 4. Intake Pipeline
    if args.intake or args.clean_and_sync:
        target_path = resolve_target_file(args.intake if args.intake != "__LATEST__" else None)
        execute_intake_pipeline(
            filepath=target_path,
            lane_override=args.lane,
            run_audit=True,
            run_sync=args.sync,
            output_dir=args.output_dir,
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    main()
