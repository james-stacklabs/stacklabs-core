#!/usr/bin/env python3
"""
Seed StackLabs LLC Brand Swarm via Dynamic StackSeeder Engine
Path: /home/james/stacklabs/scripts/seed_stacklabs_brand.py
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(SOVEREIGN_ROOT))
load_dotenv(SOVEREIGN_ROOT / ".env")

venv_python = str(SOVEREIGN_ROOT / ".venv" / "bin" / "python3")
if sys.executable != venv_python and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

from scripts.routers.brand import onboard_brand_stack, BrandOnboardRequest

async def main():
    req = BrandOnboardRequest(
        brand_name="StackLabs LLC",
        bar_question=(
            "StackLabs walks into a neighborhood tavern at 4:30 PM. It doesn't drink alcohol. "
            "It orders a hot black coffee in a heavy ceramic mug—or a tall, ice-cold Arnold Palmer sweating on a napkin "
            "if it's eating a burger at the bar. Sits down, plugs in a charger, and pulls up terminal logs, compiler output, "
            "and raw systemd traces. Friendly with the working staff and leaves a 30% cash tip because physical labor is the "
            "only thing that's real. If a tech-bro in a fleece vest sits down nearby bragging about raising a $5M seed round "
            "to burn on OpenAI API wrappers, StackLabs quietly laughs, pulls up their unit economics on a scratchpad, and shows "
            "them why they'll be bankrupt in 14 months before closing the laptop and walking out."
        ),
        audience="Independent operators, technical founders, and enterprise engineering leads who need deterministic systems, extreme cloud COGS reduction, and zero hallucination risk.",
        conviction="Software must be deterministic. Hardware must have unit economics in cash. If an autonomous system doesn't have the spine to say 'NO' when an architectural invariant is breached, it has no business running in production.",
        rivals="Monolithic cloud hyperscalers charging $40k/mo for basic token wrappers, VC-funded 'AI demo' startups with zero unit economics, and generic agencies that sell empty retainers.",
        aesthetic="industrial brutalist engineering, terminal monospace, JetBrains Mono, obsidian slate, hairline dividers, zero neon, zero glassmorphism, zero buzzwords",
        content_sources=["SDLC System Invariants", "Low-Latency Telemetry Feeds", "Cloud COGS Audit Ledgers"],
        extra_lore="Headquartered in Smyrna, Georgia. Operates on dedicated StackLabs Nodes and low-latency edge architecture. Completely immune to venture capital vaporware.",
        generate_avatars=True,
        real_human_renders=False,
        website_purpose="The sovereign engineering laboratory for deterministic software, extreme cloud COGS reduction, and local edge architecture.",
        website_domain="stacklabsllc.com",
        website_pages="Home (Sovereign Foundations), Architectural Invariants, Unit Economics (The $1.50 COGS Model), Anti-Sycophancy Engine, Research & Benchmarks.",
        website_features="Terminal Monospace Viewport, Real-Time Edge Latency Telemetry, Architectural State Machine Visualizer, Zero-Tracker Fast Load.",
        website_colors="Obsidian void (#0B0E14), slate surface (#1E293B), hairline border (#334155), terminal text (#F8FAFC), amber accent (#F59E0B)",
        website_typography="JetBrains Mono (monospace terminal headings) and Inter (highly readable technical body text)",
        website_additional_requirements="Zero glassmorphism, zero neon glows, pure semantic HTML, sub-20ms edge response.",
        enable_heel=True,
        heel_name="The Cynical Systems Auditor",
        heel_handle="anti_hype_sentry",
        heel_trait="Ruthlessly allergic to AI hype, VC slides, and token inflation. Demands raw traces before acknowledging features.",
        heel_heresy_stance="99% of enterprise AI is a glorified database query with a 1000x cost markup. If you can't run it locally or prove its deterministic bounds, it belongs in /dev/null.",
        heel_volatility=1.0
    )
    
    mock_user = {"user_name": "antigravity", "role": "pilot"}
    print("[STACKSEEDER] Triggering Dynamic Brand Onboard for StackLabs LLC...")
    res = await onboard_brand_stack(req, user=mock_user)
    print("\n[SUCCESS] Brand Onboard Completed Successfully!")
    print(f"Domain: {res.get('domain')}")
    print(f"Brand Name: {res.get('brand_name')}")
    print(f"Advocates Generated: {len(res.get('personas', []))}")
    for p in res.get("personas", []):
        print(f" - {p.get('display_name')} (@{p.get('username')}): {p.get('role', 'Advocate')}")

if __name__ == "__main__":
    asyncio.run(main())
