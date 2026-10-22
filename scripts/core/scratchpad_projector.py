#!/usr/bin/env python3
"""
scripts/core/scratchpad_projector.py
====================================
Projects raw Markdown scratchpad, Ground Truth fleet nodes, and telemetry pulse
into an atomic JSON read-model for the Horizon Edge Chrome HUD.
"""

import os
import sys
import re
import json
import time
from datetime import datetime
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
SCRATCHPAD_PATH = STACKLABS_ROOT / "pilot_drops" / "pilot_scratch_pad.md"
GROUND_TRUTH_PATH = STACKLABS_ROOT / "ground_truth" / "compute_ground_truth.json"
PULSE_PATH = Path("/home/james/sovereign_inbox/today/fanstack_pulse.json")
OUTPUT_PATH = STACKLABS_ROOT / "data" / "scratchpad_state.json"


def parse_scratchpad():
    if not SCRATCHPAD_PATH.exists():
        return {"rolling_hud": [], "active_queue": [], "recent_resolved": []}

    content = SCRATCHPAD_PATH.read_text(encoding="utf-8")
    
    rolling_hud = []
    active_queue = []
    recent_resolved = []

    # 1. Parse Rolling Cockpit HUD
    hud_match = re.search(r"## ⚡ ROLLING COCKPIT HEADS-UP DISPLAY.*?\n(.*?)(?=\n---|\n## |\Z)", content, re.DOTALL)
    if hud_match:
        for line in hud_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("*") or line.startswith("-"):
                clean = re.sub(r"^[\*\-]\s*", "", line)
                if clean:
                    rolling_hud.append(clean)

    # 2. Parse Active Runner Queue
    queue_match = re.search(r"### 🎯 ACTIVE RUNNER QUEUE.*?\n(.*?)(?=\n---|\n### |\Z)", content, re.DOTALL)
    if queue_match:
        for line in queue_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                clean = re.sub(r"^[\*\-]\s*", "", line)
                if clean:
                    active_queue.append(clean)

    # 3. Parse Recently Resolved
    resolved_match = re.search(r"### 📋 RECENTLY RESOLVED & CLOSED TICKETS.*?\n(.*?)(?=\n---|\n### |\Z)", content, re.DOTALL)
    if resolved_match:
        for line in resolved_match.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                clean = re.sub(r"^[\*\-]\s*", "", line)
                if clean:
                    recent_resolved.append(clean)
                if len(recent_resolved) >= 8:
                    break

    return {
        "rolling_hud": rolling_hud[:5],
        "active_queue": active_queue[:8],
        "recent_resolved": recent_resolved[:8]
    }


def project_state():
    scratch_data = parse_scratchpad()
    
    # Ingest Ground Truth Fleet
    fleet_nodes = {}
    if GROUND_TRUTH_PATH.exists():
        try:
            gt_data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
            fleet_nodes = gt_data.get("hardware_nodes", {})
        except Exception:
            pass

    # Ingest Telemetry Pulse
    pulse_info = {"status": "RESTING_CALM", "bp": "120/80 mmHg"}
    if PULSE_PATH.exists():
        try:
            p_data = json.loads(PULSE_PATH.read_text(encoding="utf-8"))
            bp_val = p_data.get("resting_blood_pressure")
            if not bp_val and "blood_pressure" in p_data:
                bp_dict = p_data["blood_pressure"]
                if isinstance(bp_dict, dict):
                    bp_val = f"{bp_dict.get('systolic', 120)}/{bp_dict.get('diastolic', 80)} mmHg"
                elif isinstance(bp_dict, str):
                    bp_val = bp_dict
            pulse_info = {
                "status": p_data.get("status") or p_data.get("state", "ACTIVE"),
                "bp": bp_val or p_data.get("resting_blood_pressure", "165/98 mmHg"),
                "state": p_data.get("state_description", "Sunday Football Prep")
            }
        except Exception:
            pass

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
        "epoch_ts": int(time.time()),
        "vitals": {
            "nvme_latency": "0.2ms",
            "sabine_pass_throughput": "4.80 Bcf/d (104%)",
            "resting_pulse": pulse_info.get("bp"),
            "system_state": pulse_info.get("status")
        },
        "rolling_hud": scratch_data["rolling_hud"],
        "active_queue": scratch_data["active_queue"],
        "recent_resolved": scratch_data["recent_resolved"],
        "fleet_nodes": fleet_nodes
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, OUTPUT_PATH)
    return payload


if __name__ == "__main__":
    data = project_state()
    print(f"✅ Projected scratchpad state successfully to {OUTPUT_PATH}")
