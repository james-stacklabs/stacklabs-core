#!/usr/bin/env python3
"""
StackLabs Ground Truth Updater & Ingestion CLI
Path: /home/james/stacklabs/scripts/update_ground_truth.py (symlinked to SovereignOS/scripts/update_ground_truth.py)

Enables deterministic, atomic mutation of Canonical Ground Truth ledgers:
1. Ingests structured updates via CLI flags or Python API.
2. Validates mutations against strict Pydantic v2 schemas.
3. Burns 0 write cycles if payload SHA-256 matches existing state.
4. Executes atomic .tmp rename commits on state deltas.
5. Automatically triggers pack_ground_truth_context.py and optional Google Drive sync.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure scripts directory on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ground_truth_daemon import (
    VAULT_DIR,
    MODEL_MAPPING,
    atomic_commit,
    sync_to_drive,
    ComputeGroundTruth,
    PartnerGroundTruth,
    QuantGroundTruth,
    SportsGroundTruth,
)
import pack_ground_truth_context

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("update_ground_truth")

LEDGER_ALIAS = {
    "compute": "compute_ground_truth.json",
    "partner": "partner_ground_truth.json",
    "partners": "partner_ground_truth.json",
    "quant": "quant_ground_truth.json",
    "sports": "sports_ground_truth.json",
}


def set_nested_value(d: Dict[str, Any], path: str, value: Any) -> None:
    """Sets a nested dictionary key using a dotted path (e.g. 'partners.pawel_rudnicki.note')."""
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value


def update_ledger(
    ledger_name: str,
    path: Optional[str] = None,
    value: Optional[Any] = None,
    payload_dict: Optional[Dict[str, Any]] = None,
    sync_drive: bool = False,
) -> bool:
    """Updates a ledger atomically and triggers verification & prompt packing."""
    target_filename = LEDGER_ALIAS.get(ledger_name.lower(), ledger_name)
    if not target_filename.endswith(".json"):
        target_filename += ".json"

    file_path = VAULT_DIR / target_filename
    if not file_path.exists():
        logger.error(f"❌ Ledger not found: {file_path}")
        return False

    try:
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"❌ Failed to parse existing JSON in {file_path}: {e}")
        return False

    # Apply mutation
    if path and value is not None:
        set_nested_value(raw_data, path, value)
    elif payload_dict:
        raw_data.update(payload_dict)
    else:
        logger.error("❌ Either --path and --value or --payload must be provided.")
        return False

    # Schema validation
    model_cls = MODEL_MAPPING.get(target_filename)
    if model_cls:
        try:
            model_cls.model_validate(raw_data)
        except Exception as e:
            logger.error(f"❌ Schema validation failed for {target_filename}: {e}")
            return False

    # Atomic commit
    committed, status = atomic_commit(file_path, raw_data, model_cls)
    if status == "NO_CHANGE":
        logger.info(f"ℹ️ [NO_CHANGE] Payload matches existing state. 0 NVMe write cycles burned.")
        return True

    logger.info(f"✅ [COMMITTED] Successfully updated {target_filename} (atomic .tmp swap)")

    # Repack prompt context
    try:
        pack_ground_truth_context.generate_prompt_context()
        logger.info("📦 [PACKER] Repacked GROUND_TRUTH_PROMPT_CONTEXT.md")
    except Exception as e:
        logger.warning(f"⚠️ Failed to repack prompt context: {e}")

    # Mirror to Drive if requested
    if sync_drive:
        logger.info("☁️ [DRIVE] Mirroring updated vault to stacklabs_edge and stacklabs_vault...")
        sync_to_drive(VAULT_DIR)

    return True


def main():
    parser = argparse.ArgumentParser(description="StackLabs Ground Truth Vault Updater")
    parser.add_argument("--ledger", required=True, help="Target ledger (compute, partner, quant, sports, or filename)")
    parser.add_argument("--path", help="Dotted path for field insertion (e.g. 'partners.stephen.status')")
    parser.add_argument("--value", help="JSON string or scalar value to set at path")
    parser.add_argument("--json-file", help="Path to JSON file containing patch dictionary")
    parser.add_argument("--sync-drive", action="store_true", help="Mirror vault to Google Drive immediately")

    args = parser.parse_args()

    val = None
    if args.value is not None:
        try:
            val = json.loads(args.value)
        except Exception:
            val = args.value

    payload_dict = None
    if args.json_file:
        try:
            payload_dict = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"❌ Failed to read --json-file {args.json_file}: {e}")
            sys.exit(1)

    success = update_ledger(
        ledger_name=args.ledger,
        path=args.path,
        value=val,
        payload_dict=payload_dict,
        sync_drive=args.sync_drive,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
