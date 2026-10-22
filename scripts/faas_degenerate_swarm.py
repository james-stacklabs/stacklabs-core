#!/usr/bin/env python3
"""
scripts/faas_degenerate_swarm.py
Simulated AI Degenerate Gambler Reaction Engine
Evaluates live weather vs odds and emits real-time meltdowns to FaaS VFS
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 15, 32, 35, 50
"""
import time
import random
from pathlib import Path

VFS_ROOT = Path("/dev/shm/faas_vfs")
CHAOS_DIR = VFS_ROOT / "chaos_center"

DEGEN_PERSONAS = [
    {"name": "@BarfFanStack", "bias": "DOOMER", "style": "Southern collapse & front-office rage"},
    {"name": "@SammyTheSavant", "bias": "QUANT", "style": "Calendar parity & hook tax avoidance"},
    {"name": "@BronxBoosOnly", "bias": "ANGRY", "style": "High-tax manic aggression"},
    {"name": "@MetsFan_86", "bias": "PARANOID", "style": "Existential dread & bullpen PTSD"}
]

def run_degen_loop(cycles: int = 5):
    CHAOS_DIR.mkdir(parents=True, exist_ok=True)
    
    for cycle in range(1, cycles + 1):
        # 1. Read live CFB state
        score_file = VFS_ROOT / "games" / "cfb_uga_bama" / "score_home.txt"
        score_home = score_file.read_text().strip() if score_file.exists() else "24"

        # 2. Read live weather at Bryant-Denny (35487)
        weather_dir = VFS_ROOT / "weather" / "35487"
        wind = weather_dir.joinpath("wind_speed_mph.txt").read_text().strip() if weather_dir.exists() else "12"
        threat = weather_dir.joinpath("hurricane_threat.txt").read_text().strip() if weather_dir.exists() else "NONE"

        # 3. Simulate degen reaction
        persona = random.choice(DEGEN_PERSONAS)
        if threat == "ACTIVE":
            reaction = f"{persona['name']}: Tropical cyclone band pushing 40mph gusts into the uprights! Kickers are dead meat! SMASH THE UNDER!"
            opcode = "SICK"
        elif int(wind) > 15:
            reaction = f"{persona['name']}: Wind is whipping at {wind}mph! Passing game is cooked. My parlay is in the gutter!"
            opcode = "MLTD"
        else:
            reaction = f"{persona['name']}: Clean pocket, calm air. Georgia secondary is asleep! Hammer the live spread!"
            opcode = "HYPD"

        # 4. Emit to VFS fast-path
        (CHAOS_DIR / "last_degen_reaction.txt").write_text(f"{reaction}\n")
        (CHAOS_DIR / "degen_sentiment_opcode.txt").write_text(f"{opcode}\n")
        (CHAOS_DIR / "chat_velocity_eps.txt").write_text(f"{random.randint(120, 240)}\n")

        print(f"[{cycle:02d}] {opcode} | {reaction}")
        time.sleep(0.5)

    print("[PASS] Degenerate swarm successfully emitted active reactions to VFS.")

if __name__ == "__main__":
    run_degen_loop()
