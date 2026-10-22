#!/usr/bin/env python3
"""
Voice Layout Synthesizer: Compiles spoken or textual UI directives into
atomic declarative layout schemas in /dev/shm/retina_layout.json.
Author: James Carroll (Pilot), Lead Systems Architect.
Target: Clio bare metal.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

OUTPUT_SCHEMA = Path("/dev/shm/retina_layout.json")

CANONICAL_TARGETS = {
    "dora": {
        "title": "Dora Systems",
        "badge": "48V Victron",
        "source": "/dev/shm/canvas/dora/summary.txt",
        "drilldown_path": "/dev/shm/canvas/dora"
    },
    "anna": {
        "title": "Anna Schedule",
        "badge": "High School / Strings",
        "source": "/dev/shm/canvas/anna/summary.txt",
        "drilldown_path": "/dev/shm/canvas/anna"
    },
    "paloma": {
        "title": "Paloma Schedule",
        "badge": "Club Soccer / Academics",
        "source": "/dev/shm/canvas/paloma/summary.txt",
        "drilldown_path": "/dev/shm/canvas/paloma"
    },
    "projects": {
        "title": "StackLabs Active",
        "badge": "Metal Backlog",
        "source": "/dev/shm/canvas/projects/summary.txt",
        "drilldown_path": "/dev/shm/canvas/projects"
    }
}

def synthesize_layout(intent_text: str = ""):
    layout_data = {
        "layout": "four_pillar_grid",
        "title": "StackLabs Living Cockpit",
        "timestamp": "2026-10-10T16:25:00-04:00",
        "intent_received": intent_text or "Default 4-Pillar Operations Cockpit",
        "pillars": [
            {
                "id": "pillar_dora",
                "title": CANONICAL_TARGETS["dora"]["title"],
                "badge": CANONICAL_TARGETS["dora"]["badge"],
                "source_file": CANONICAL_TARGETS["dora"]["source"],
                "drilldown_path": CANONICAL_TARGETS["dora"]["drilldown_path"]
            },
            {
                "id": "pillar_anna",
                "title": CANONICAL_TARGETS["anna"]["title"],
                "badge": CANONICAL_TARGETS["anna"]["badge"],
                "source_file": CANONICAL_TARGETS["anna"]["source"],
                "drilldown_path": CANONICAL_TARGETS["anna"]["drilldown_path"]
            },
            {
                "id": "pillar_paloma",
                "title": CANONICAL_TARGETS["paloma"]["title"],
                "badge": CANONICAL_TARGETS["paloma"]["badge"],
                "source_file": CANONICAL_TARGETS["paloma"]["source"],
                "drilldown_path": CANONICAL_TARGETS["paloma"]["drilldown_path"]
            },
            {
                "id": "pillar_projects",
                "title": CANONICAL_TARGETS["projects"]["title"],
                "badge": CANONICAL_TARGETS["projects"]["badge"],
                "source_file": CANONICAL_TARGETS["projects"]["source"],
                "drilldown_path": CANONICAL_TARGETS["projects"]["drilldown_path"]
            }
        ]
    }

    with tempfile.NamedTemporaryFile("w", dir="/dev/shm", delete=False) as tf:
        json.dump(layout_data, tf, indent=2)
        temp_name = tf.name

    os.replace(temp_name, OUTPUT_SCHEMA)
    print(f"[OK] Atomic layout schema emitted to {OUTPUT_SCHEMA}")

if __name__ == "__main__":
    cli_intent = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    synthesize_layout(cli_intent)
