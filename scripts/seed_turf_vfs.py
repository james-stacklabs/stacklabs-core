#!/usr/bin/env python3
"""
Seed the Saturday Turf Play VFS on Clio (/dev/shm/vfs/turf)
Path: /home/james/stacklabs/scripts/seed_turf_vfs.py
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
"""
import os
import shutil
from pathlib import Path

TURF_ROOT = Path("/dev/shm/vfs/turf")

def stage_turf(clean: bool = True):
    # 1. Clean and initialize
    if clean and TURF_ROOT.exists():
        shutil.rmtree(TURF_ROOT)
    
    # 2. Build directories
    (TURF_ROOT / "track").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "race_08" / "posts").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "horses" / "fierceness").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "horses" / "thorpedoanna").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "horses" / "sierraleone").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "jockeys" / "velazquez").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "jockeys" / "hernandez").mkdir(parents=True, exist_ok=True)
    (TURF_ROOT / "jockeys" / "prat").mkdir(parents=True, exist_ok=True)

    # 3. Populate Track
    (TURF_ROOT / "track" / "name.txt").write_text("Keeneland\n")
    (TURF_ROOT / "track" / "surface.txt").write_text("DIRT\n")
    (TURF_ROOT / "track" / "condition.txt").write_text("FAST\n")

    # 4. Populate Race 8
    (TURF_ROOT / "race_08" / "distance_furlongs.txt").write_text("6.0\n")
    (TURF_ROOT / "race_08" / "purse_usd.txt").write_text("110000\n")
    (TURF_ROOT / "race_08" / "pace_scenario.txt").write_text("HOT_CONTESTED\n")

    # 5. Populate Horses & Jockeys
    # Post 01: Sierra Leone
    h_sierra = TURF_ROOT / "horses" / "sierraleone"
    (h_sierra / "program_num.txt").write_text("1\n")
    (h_sierra / "morning_line.txt").write_text("3-1\n")
    (h_sierra / "live_odds.txt").write_text("3.4\n")
    (h_sierra / "beyer_speed_last.txt").write_text("102\n")
    (h_sierra / "run_style.txt").write_text("DEEP_CLOSER\n")
    (h_sierra / "fair_odds.txt").write_text("3.2\n")
    (h_sierra / "jockey").symlink_to("../../jockeys/prat")
    (TURF_ROOT / "jockeys" / "prat" / "win_pct.txt").write_text("21.8\n")
    (TURF_ROOT / "race_08" / "posts" / "post_01").symlink_to("../../horses/sierraleone")

    # Post 02: Thorpedo Anna
    h_thorpedo = TURF_ROOT / "horses" / "thorpedoanna"
    (h_thorpedo / "program_num.txt").write_text("2\n")
    (h_thorpedo / "morning_line.txt").write_text("9-5\n")
    (h_thorpedo / "live_odds.txt").write_text("1.9\n")
    (h_thorpedo / "beyer_speed_last.txt").write_text("106\n")
    (h_thorpedo / "run_style.txt").write_text("EARLY_SPEED\n")
    (h_thorpedo / "fair_odds.txt").write_text("2.2\n")
    (h_thorpedo / "jockey").symlink_to("../../jockeys/hernandez")
    (TURF_ROOT / "jockeys" / "hernandez" / "win_pct.txt").write_text("19.2\n")
    (TURF_ROOT / "race_08" / "posts" / "post_02").symlink_to("../../horses/thorpedoanna")

    # Post 03: Fierceness
    h_fierce = TURF_ROOT / "horses" / "fierceness"
    (h_fierce / "program_num.txt").write_text("3\n")
    (h_fierce / "morning_line.txt").write_text("5-2\n")
    (h_fierce / "live_odds.txt").write_text("2.1\n")
    (h_fierce / "beyer_speed_last.txt").write_text("108\n")
    (h_fierce / "run_style.txt").write_text("EARLY_PRESSER\n")
    (h_fierce / "fair_odds.txt").write_text("1.8\n")
    (h_fierce / "jockey").symlink_to("../../jockeys/velazquez")
    (TURF_ROOT / "jockeys" / "velazquez" / "win_pct.txt").write_text("24.5\n")
    (TURF_ROOT / "race_08" / "posts" / "post_03").symlink_to("../../horses/fierceness")

    print("[PASS] Saturday Turf VFS staged successfully in /dev/shm/vfs/turf!")

if __name__ == "__main__":
    stage_turf()
