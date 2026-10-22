#!/usr/bin/env python3
"""
Seed synthetic VFS hierarchy for the 4-pillar declarative voice canvas.
Author: James Carroll (Pilot), Lead Systems Architect.
Target: Clio bare metal (/vfs/canvas/ and /dev/shm/canvas/).
"""

import os
import shutil
from pathlib import Path

VFS_PERSISTENT = Path("/home/james/stacklabs/vfs/canvas")
VFS_SHM = Path("/dev/shm/canvas")

def seed_canvas_tree():
    if VFS_PERSISTENT.exists():
        shutil.rmtree(VFS_PERSISTENT)
    VFS_PERSISTENT.mkdir(parents=True, exist_ok=True)

    # 1. Dora (Off-grid RV / Battery / Systems)
    dora_dir = VFS_PERSISTENT / "dora"
    dora_dir.mkdir(parents=True, exist_ok=True)
    (dora_dir / "summary.txt").write_text("Victron 48V Off-Grid Solar Hub\nBattery: 98.4%\nSolar Ingress: 1,420W\nInverter: PASSIVE_NOMINAL\nShore: DISCONNECTED")
    (dora_dir / "battery_soc.txt").write_text("98.4%")
    (dora_dir / "solar_watts.txt").write_text("1420")
    (dora_dir / "shore_power.txt").write_text("DISCONNECTED")
    (dora_dir / "cabin_temp_f.txt").write_text("71.2")

    # 2. Anna (Weekly Schedule & High School Logistics)
    anna_dir = VFS_PERSISTENT / "anna"
    anna_dir.mkdir(parents=True, exist_ok=True)
    (anna_dir / "summary.txt").write_text("Weekly Academic & Rehearsal Slate\nNext Up: Orchestra Rehearsal 4:30 PM\nSaturday: Solo Festival")
    (anna_dir / "monday.txt").write_text("08:00 AM - AP Calc BC\n01:30 PM - Chamber Strings\n04:30 PM - Rehearsal Hall B")
    (anna_dir / "tuesday.txt").write_text("08:00 AM - AP Chemistry\n03:15 PM - Study Session @ Library")
    (anna_dir / "wednesday.txt").write_text("08:00 AM - AP Calc BC\n04:30 PM - Full Symphony Rehearsal")
    (anna_dir / "weekend.txt").write_text("Saturday: Regional Solo & Ensemble Festival (All Day)")

    # 3. Paloma (Weekly Schedule & Athletic Drills)
    paloma_dir = VFS_PERSISTENT / "paloma"
    paloma_dir.mkdir(parents=True, exist_ok=True)
    (paloma_dir / "summary.txt").write_text("Weekly Soccer, Academics & Training\nNext Up: Club Practice 6:00 PM\nSunday: Match vs Concorde")
    (paloma_dir / "monday.txt").write_text("08:30 AM - Honors Biology\n06:00 PM - Club Soccer Training (Pitch 4)")
    (paloma_dir / "tuesday.txt").write_text("08:30 AM - World History\n04:00 PM - Speed & Agility Drills")
    (paloma_dir / "wednesday.txt").write_text("08:30 AM - Honors Geometry\n06:00 PM - Club Soccer Scrimmage")
    (paloma_dir / "weekend.txt").write_text("Sunday 11:00 AM - League Match vs Concorde Fire")

    # 4. StackLabs (Active Engineering Backlog & Deliverables)
    projects_dir = VFS_PERSISTENT / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    (projects_dir / "summary.txt").write_text("Bare-Metal Edge Engine & VFS SRE\nActive Work Orders: WO0011051, WO0011052\nHardware: Clio x86 NVMe")
    (projects_dir / "task_01.txt").write_text("WO0011048: Purge 2024 Baseball Mocks & Lock Real Oct 10 Slate [DONE]")
    (projects_dir / "task_02.txt").write_text("WO0011051: Purge Cyberpunk Reflex Coprocessor Slop [DONE]")
    (projects_dir / "task_03.txt").write_text("WO0011052: Declarative 4-Pillar Voice VFS Canvas [DONE]")
    (projects_dir / "burn_rate.txt").write_text("35 Watts APU Continuous - Zero Cloud Token Toll")

    if VFS_SHM.exists():
        shutil.rmtree(VFS_SHM)
    shutil.copytree(VFS_PERSISTENT, VFS_SHM)
    print(f"[OK] Seeded 4-pillar VFS tree to {VFS_PERSISTENT} and mirrored to {VFS_SHM}")

if __name__ == "__main__":
    seed_canvas_tree()
