#!/usr/bin/env python3
"""
StackLabs FaaS Telemetry Generator: Dodgers 2026 Capital Crater & Article XVI Escrow
Path: /home/james/stacklabs/scripts/generate_dodgers_capital_telemetry.py
"""

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict

GROUND_TRUTH_PATH = Path("/home/james/stacklabs/ground_truth/sports_ground_truth.json")
VFS_OUTPUT_PATH = Path("/dev/shm/faas_vfs/telemetry/dodgers_capital_crater.json")
DISK_FALLBACK_PATH = Path("/home/james/stacklabs/data/telemetry/dodgers_capital_crater.json")


def _atomic_write_json(target_path: Path, payload: Dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(".json.tmp")
    content = json.dumps(payload, indent=2) + "\n"
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, target_path)


def generate_capital_telemetry() -> Dict[str, Any]:
    """Reads canonical sports_ground_truth.json and projects Dodgers capital crater telemetry."""
    gt_data: Dict[str, Any] = {}
    if GROUND_TRUTH_PATH.exists():
        try:
            gt_data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
        except Exception:
            gt_data = {}

    model = gt_data.get("dodgers_financial_model_2026", {})

    today = datetime.now().date()
    cba_date_str = str(model.get("cba_expiration", "2026-12-01"))
    try:
        y, m, d = (int(x) for x in cba_date_str.split("-"))
        cba_date = date(y, m, d)
    except Exception:
        cba_date = date(2026, 12, 1)

    july_1_deposit_date = date(2027, 7, 1)

    days_to_cba = max(0, (cba_date - today).days)
    days_to_july_1 = max(0, (july_1_deposit_date - today).days)

    exposure_raw = str(model.get("twg_global_federal_probe_exposure", "16B-21B"))
    exposure_formatted = (
        f"${exposure_raw.replace('-', '-$')} in annuity private-credit loans"
        if not exposure_raw.startswith("$")
        else f"{exposure_raw} in annuity private-credit loans"
    )

    payload: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "baseline_revenue": int(model.get("regular_season_revenue", 850000000)),
        "player_expenses_and_cbt": int(model.get("player_expenses_and_cbt", 402000000)),
        "baseline_ebitda": int(model.get("baseline_ebitda", -20000000)),
        "postseason_cash_loss": int(model.get("postseason_sweep_cash_vaporized", -52000000)),
        "adjusted_ebitda": int(model.get("adjusted_2026_ebitda", -72000000)),
        "article_xvi_escrow": {
            "ohtani_annual_pv": int(model.get("article_xvi_annual_escrow_ohtani", 44000000)),
            "total_annual_all_players": int(model.get("total_annual_deferred_escrow", 92000000)),
            "days_until_july_1_deposit": days_to_july_1,
        },
        "cba_expiration": {
            "date": cba_date_str,
            "days_remaining": days_to_cba,
            "proposed_hard_cap": int(model.get("cba_proposed_hard_cap", 245300000)),
        },
        "federal_investigation": {
            "target": "Mark Walter / TWG Global / Delaware Life",
            "agencies": ["DOJ", "SEC", "FBI"],
            "exposure": exposure_formatted,
            "recent_action": "Liquidated LA Lakers equity stake",
        },
        "gate_formula_pivot": (
            "Games 1-4 allocate 60% gate to Players' Pool; "
            "Game 5+ allocates ~85% gate and 100% suites/parking/merch to home club"
        ),
    }

    try:
        _atomic_write_json(VFS_OUTPUT_PATH, payload)
    except Exception:
        pass

    try:
        _atomic_write_json(DISK_FALLBACK_PATH, payload)
    except Exception:
        pass

    return payload


if __name__ == "__main__":
    result = generate_capital_telemetry()
    print(json.dumps(result, indent=2))
