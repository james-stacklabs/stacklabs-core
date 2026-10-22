#!/usr/bin/env python3
"""
scripts/seed_gameday_vfs.py
Stages CFB Gameday + MLB Statcast Split Topology in /dev/shm/vfs
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 15, 32, 35
"""
import shutil
from pathlib import Path

VFS_ROOT = Path("/dev/shm/vfs")

def setup_gameday_vfs():
    # 1. Clean or initialize root
    if (VFS_ROOT / "cfb").exists() or (VFS_ROOT / "cfb").is_symlink():
        shutil.rmtree(VFS_ROOT / "cfb", ignore_errors=True)
    if (VFS_ROOT / "mlb").exists() or (VFS_ROOT / "mlb").is_symlink():
        shutil.rmtree(VFS_ROOT / "mlb", ignore_errors=True)

    # =========================================================================
    # PART A: COLLEGE FOOTBALL (CFB) TOPOLOGY
    # =========================================================================
    cfb_game = VFS_ROOT / "cfb" / "games" / "uga_vs_bama"
    cfb_game.mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "cfb" / "teams" / "uga").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "cfb" / "chaos_center").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "cfb" / "blood_pressure").mkdir(parents=True, exist_ok=True)

    # Populate CFB State
    (cfb_game / "score_home.txt").write_text("24\n")
    (cfb_game / "score_away.txt").write_text("21\n")
    (cfb_game / "quarter.txt").write_text("Q4\n")
    (cfb_game / "time_remaining.txt").write_text("02:14\n")
    (cfb_game / "down_and_dist.txt").write_text("3rd & 4\n")
    (cfb_game / "yardline.txt").write_text("BAMA_38\n")
    (cfb_game / "win_prob_pct.txt").write_text("68.4\n")
    
    (VFS_ROOT / "cfb" / "chaos_center" / "velocity_eps.txt").write_text("145\n")
    (VFS_ROOT / "cfb" / "blood_pressure" / "current_pct.txt").write_text("86\n")
    
    # Symlink CFB Possession to UGA
    (VFS_ROOT / "cfb" / "teams" / "uga" / "timeouts.txt").write_text("2\n")
    possession_link = cfb_game / "possession"
    if possession_link.is_symlink() or possession_link.exists():
        possession_link.unlink()
    possession_link.symlink_to("../../teams/uga")

    # =========================================================================
    # PART B: MLB STATCAST TOPOLOGY
    # =========================================================================
    mlb_root = VFS_ROOT / "mlb"
    at_bat = mlb_root / "games" / "live_game" / "at_bat"
    at_bat.mkdir(parents=True, exist_ok=True)
    
    # Players
    alonso = mlb_root / "players" / "alonso_pete"
    (alonso / "splits" / "vs_rhp").mkdir(parents=True, exist_ok=True)
    (alonso / "splits" / "vs_lhp").mkdir(parents=True, exist_ok=True)
    (alonso / "pitch_types" / "slider").mkdir(parents=True, exist_ok=True)
    (alonso / "pitch_types" / "four_seam").mkdir(parents=True, exist_ok=True)
    
    # Alonso Splits
    (alonso / "splits" / "vs_rhp" / "woba.txt").write_text("0.344\n")
    (alonso / "splits" / "vs_lhp" / "woba.txt").write_text("0.388\n")
    (alonso / "pitch_types" / "slider" / "chase_pct.txt").write_text("32.1\n")
    (alonso / "pitch_types" / "four_seam" / "xwoba.txt").write_text("0.410\n")

    # Pitcher (Díaz)
    diaz = mlb_root / "players" / "diaz_edwin" / "fatigue"
    diaz.mkdir(parents=True, exist_ok=True)
    (diaz / "velo_current.txt").write_text("98.1\n")
    (diaz / "release_z_drift_in.txt").write_text("-1.2\n")

    # Live At-Bat State
    (at_bat / "count.txt").write_text("1-2\n")
    (at_bat / "pitch_clock_sec.txt").write_text("09\n")
    
    # Wire Symlinks
    batter_link = at_bat / "batter"
    if batter_link.is_symlink() or batter_link.exists():
        batter_link.unlink()
    batter_link.symlink_to("../../../players/alonso_pete")

    pitcher_link = at_bat / "pitcher"
    if pitcher_link.is_symlink() or pitcher_link.exists():
        pitcher_link.unlink()
    pitcher_link.symlink_to("../../../players/diaz_edwin")

    print("[PASS] Multi-Sport VFS successfully staged in /dev/shm/vfs/")

if __name__ == "__main__":
    setup_gameday_vfs()
