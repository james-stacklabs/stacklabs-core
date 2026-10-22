#!/usr/bin/env python3
"""
Seed the Gameday FaaS VFS on Clio (/dev/shm/faas_vfs)
Path: /home/james/stacklabs/scripts/seed_faas_vfs.py
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
"""
import os
import shutil
from pathlib import Path

VFS_ROOT = Path("/dev/shm/faas_vfs")

def stage_faas_vfs(clean: bool = True):
    if clean and VFS_ROOT.exists():
        shutil.rmtree(VFS_ROOT)
        
    # 1. Base directories
    (VFS_ROOT / "games" / "cfb_uga_bama" / "active_drive").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "games" / "cfb_uga_bama" / "streams").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "chaos_center").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "blood_pressure").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "sports_booking").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "teams" / "uga").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "teams" / "bama").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "players" / "uga_qb").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "streams" / "stream_01").mkdir(parents=True, exist_ok=True)
    (VFS_ROOT / "streams" / "stream_02").mkdir(parents=True, exist_ok=True)

    # 2. Teams & Players
    (VFS_ROOT / "teams" / "uga" / "name.txt").write_text("Georgia Bulldogs\n")
    (VFS_ROOT / "teams" / "uga" / "color_hex.txt").write_text("#BA0C2F\n")
    (VFS_ROOT / "teams" / "uga" / "timeouts.txt").write_text("2\n")

    (VFS_ROOT / "teams" / "bama" / "name.txt").write_text("Alabama Crimson Tide\n")
    (VFS_ROOT / "teams" / "bama" / "color_hex.txt").write_text("#9E1B32\n")
    (VFS_ROOT / "teams" / "bama" / "timeouts.txt").write_text("1\n")

    (VFS_ROOT / "players" / "uga_qb" / "name.txt").write_text("Carson Beck\n")
    (VFS_ROOT / "players" / "uga_qb" / "pass_yards.txt").write_text("312\n")
    (VFS_ROOT / "players" / "uga_qb" / "td_int.txt").write_text("3/1\n")

    # 3. Live Game (cfb_uga_bama)
    g_dir = VFS_ROOT / "games" / "cfb_uga_bama"
    (g_dir / "score_home.txt").write_text("24\n")
    (g_dir / "score_away.txt").write_text("21\n")
    (g_dir / "quarter.txt").write_text("Q4\n")
    (g_dir / "time_remaining.txt").write_text("02:14\n")
    (g_dir / "down_and_distance.txt").write_text("3rd & 4\n")
    (g_dir / "yardline.txt").write_text("BAMA_38\n")
    (g_dir / "win_probability_pct.txt").write_text("68.4\n")
    (g_dir / "active_drive" / "play_call.txt").write_text("SHOTGUN_SLOT_RPO\n")

    # Symlinks in active drive
    (g_dir / "active_drive" / "possession").symlink_to("../../../teams/uga")
    (g_dir / "active_drive" / "qb").symlink_to("../../../players/uga_qb")

    # Streams
    (VFS_ROOT / "streams" / "stream_01" / "url.txt").write_text("http://100.108.185.53:8088/master_grid.m3u8\n")
    (VFS_ROOT / "streams" / "stream_02" / "url.txt").write_text("http://127.0.0.1:5056/hls/sniper.m3u8\n")
    (g_dir / "streams" / "primary_theater").symlink_to("../../../streams/stream_01")
    (g_dir / "streams" / "backup_sniper").symlink_to("../../../streams/stream_02")

    # 4. Chaos Center
    (VFS_ROOT / "chaos_center" / "chat_velocity_eps.txt").write_text("142.5\n")
    (VFS_ROOT / "chaos_center" / "euphoria_spread_pct.txt").write_text("+18.4\n")
    (VFS_ROOT / "chaos_center" / "ref_hate_index_pct.txt").write_text("84.2\n")
    (VFS_ROOT / "chaos_center" / "momentum_delta.txt").write_text("-12.8\n")

    # 5. Live Blood Pressure
    (VFS_ROOT / "blood_pressure" / "current_pct.txt").write_text("88.6\n")
    (VFS_ROOT / "blood_pressure" / "systolic_state.txt").write_text("CRITICAL_HYPERTENSIVE\n")
    (VFS_ROOT / "blood_pressure" / "trigger_cause.txt").write_text("MISSED_FG_Q4_03:12\n")

    # 6. Sports Booking & Kalshi Divergence
    (VFS_ROOT / "sports_booking" / "kalshi_spread.txt").write_text("-3.5\n")
    (VFS_ROOT / "sports_booking" / "live_moneyline.txt").write_text("-165\n")
    (VFS_ROOT / "sports_booking" / "consensus_divergence.txt").write_text("EXPLOITABLE_SHORT\n")
    (VFS_ROOT / "sports_booking" / "hedge_trigger.txt").write_text("ARMED\n")

    print("[PASS] Gameday FaaS VFS staged successfully in /dev/shm/faas_vfs!")

if __name__ == "__main__":
    stage_faas_vfs()
