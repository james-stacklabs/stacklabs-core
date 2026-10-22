#!/usr/bin/env python3
"""
Seed Johnny Carroll / Carroll Craft Woodworking Brand Swarm via Dynamic StackSeeder Engine
Path: /home/james/stacklabs/scripts/seed_johnny_carroll_brand.py
"""
import asyncio
import os
import sys
import shutil
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(SOVEREIGN_ROOT))
load_dotenv(SOVEREIGN_ROOT / ".env")

venv_python = str(SOVEREIGN_ROOT / ".venv" / "bin" / "python3")
if sys.executable != venv_python and os.path.exists(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

from scripts.routers.brand import (
    onboard_brand_stack,
    BrandOnboardRequest,
    CustomAdvocateBlueprint,
)
from core.db import DB_PATH

async def main():
    custom_roster = [
        CustomAdvocateBlueprint(
            name="John Patrick Carroll, Jr.",
            role="Master Cabinetmaker & Proprietor",
            trait="35-year Glendale woodworking veteran, dovetail purist, zero shortcuts",
            avatarEmoji="🪵"
        ),
        CustomAdvocateBlueprint(
            name="Vince DeLuca",
            role="Architectural Coatings & Finish Specialist",
            trait="Catalyzed conversion varnishes, natural walnut oils, multi-stage hand rubbing",
            avatarEmoji="🎨"
        ),
        CustomAdvocateBlueprint(
            name="Eamon Kelly",
            role="Historic Millwork & Pre-War Drafter",
            trait="Forest Hills Tudor moulding profiles, custom radiator enclosures, coffer ceilings",
            avatarEmoji="📐"
        ),
        CustomAdvocateBlueprint(
            name="Marcus Vance",
            role="Countertop & Solid Surface Templater",
            trait="Zero-gap laser templating, quartz and soapstone seamless undermount integration",
            avatarEmoji="🪨"
        ),
        CustomAdvocateBlueprint(
            name="Sal Moretti",
            role="Cabinet Refacing & Practical Modernization Lead",
            trait="Preserves solid 3/4-inch boxes, builds new custom hardwood doors, saves homeowners $30k",
            avatarEmoji="🔨"
        ),
    ]

    req = BrandOnboardRequest(
        brand_name="Carroll Craft Woodworking",
        bar_question=(
            "Johnny Carroll walks into a neighborhood tavern in Glendale, Queens "
            "(or Zum Stammtisch on Myrtle Ave) on a Friday evening after 10 hours at the shop. "
            "He doesn't drink alcohol on the job; he orders an ice-cold club soda with a lime "
            "or a black drip coffee with a splash of cream. Wears fine sawdust on his Carhartt work vest, "
            "a carpenter's pencil tucked behind the right ear, and steel-toe boots. Friendly with the "
            "bartenders and working regulars. If a slick big-box retail kitchen salesperson in a polo shirt "
            "sits down nearby bragging about selling 1/2-inch particle-board and thermofoil peel-and-stick "
            "cabinets that 'look just like real wood,' Johnny chuckles quietly, pulls a scrap of quartersawn "
            "white oak and a hand-cut dovetail joint from his pocket, and explains how wood breathes in "
            "NYC pre-war summer humidity—and why glued particle-board boxes sag, swell, and delaminate within three years."
        ),
        audience=(
            "Homeowners in Glendale, Ridgewood, Middle Village, Forest Hills, and Queens who appreciate real woodcraft, "
            "demand 3/4-inch solid domestic plywood carcasses, and want custom cabinetry built to survive 50+ years."
        ),
        conviction=(
            "Real wood breathes, expands, and endures. If you lean on a cabinet door and the hinge tears out "
            "of particle-board dust, that isn't furniture—it's compressed trash. Every kitchen we build uses "
            "3/4-inch plywood boxes, solid hardwood face frames, and precision dovetails."
        ),
        rivals=(
            "Big-box retail stores selling flat-pack imported MDF cabinets, predatory middleman lead brokers "
            "(Angi, Houzz) taking 30% kickbacks, and fly-by-night subcontractors using peel-and-stick vinyl wrap."
        ),
        aesthetic=(
            "Hand-rubbed walnut espresso (#12100E), warm honey oak (#D4A373), forged brass accents, "
            "dovetail joinery schematics, architectural crown moulding profiles, craftsman serif typography."
        ),
        content_sources=[
            "Architectural Millwork Profiles",
            "Glendale Pre-War Historic Standards",
            "Hardware & Blum Runner Specs"
        ],
        extra_lore=(
            "Shop located at 69-02 68th Street, Glendale, Queens, NY 11385. Over 35 years serving "
            "Queens homeowners, row houses, and pre-war apartment buildings with genuine bench-made cabinetry."
        ),
        generate_avatars=False,
        real_human_renders=False,
        custom_roster=custom_roster,
        website_purpose="Custom architectural cabinetry, millwork, and master woodcraft built to endure 50+ years for Queens homeowners.",
        website_domain="carrollcraftwoodworking.com",
        website_pages="Home, Portfolio Gallery, Historic Pre-War Millwork, Kitchen Cabinet Refacing, Swarm Council, Craft Essays, Consultation",
        website_features="Interactive Before/After Transformations, Material Standards Inspector, Swarm Council Roster, Master Craft Essays",
        website_colors="Walnut Espresso (#12100E), Warm Honey Oak (#D4A373), Forest Green (#2D5A27), Slate (#1E293B)",
        website_typography="Playfair Display (craftsman serif headings), Inter (clean technical body)",
        website_additional_requirements="Zero particle board, zero shortcuts, 100% authentic woodcraft.",
        enable_heel=True,
        heel_name="The Flat-Pack & Particle Board Skeptic",
        heel_handle="particle_board_patrol",
        heel_trait="Cynical, razor-sharp debunker of cheap imported flat-pack kitchen cabinets and hollow retail markup.",
        heel_heresy_stance="90% of retail kitchen showrooms sell compressed sawdust held together with formaldehyde and cheap plastic brackets. If you put a hot soup pot on it and it bubbles, you got robbed.",
        heel_volatility=1.0,
    )

    mock_user = {"user_name": "antigravity", "role": "pilot"}
    print("[STACKSEEDER] Triggering Dynamic Brand Onboard for Carroll Craft Woodworking...")
    res = await onboard_brand_stack(req, user=mock_user)
    print("\n[SUCCESS] Brand Onboard Completed Successfully!")
    domain_name = res.get("domain", "CarrollCraft")
    print(f"Domain: {domain_name}")
    print(f"Brand Name: {res.get('brand_name')}")
    print(f"Advocates Generated: {len(res.get('personas', []))}")
    
    # Copy avatars to 34_CarrollCraft/public/avatars/
    target_avatar_dir = SOVEREIGN_ROOT / "34_CarrollCraft" / "public" / "avatars"
    target_avatar_dir.mkdir(parents=True, exist_ok=True)
    src_avatar_dir = SOVEREIGN_ROOT / "01_Sovereign_Portal" / "public" / "avatars"

    for p in res.get("personas", []):
        username = p.get("username")
        print(f" - {p.get('display_name')} (@{username}): {p.get('role', 'Advocate')}")
        for ext in [".svg", ".png"]:
            src_f = src_avatar_dir / f"{username}{ext}"
            if src_f.exists():
                dst_f = target_avatar_dir / f"{username}{ext}"
                shutil.copy2(src_f, dst_f)
                print(f"   [AVATAR] Copied {src_f.name} -> {dst_f}")

    # Ensure CMDB CI Stack entry exists for Lookbook PDF generator
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    brand_keys = [domain_name.upper(), "CARROLLCRAFT", "CARROLL_CRAFT", "CARROLLCRAFTWOODWORKING"]
    team_filter = ",".join(brand_keys)
    
    for bk in ["CARROLLCRAFT", domain_name.upper()]:
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_stack 
            (brand_key, title, subtitle, description, primary_color, card_bg, team_filter, pdf_name, aesthetic_title, ingest_log, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            bk,
            "GENESIS STACK SEEDING MANIFEST: CARROLL CRAFT WOODWORKING",
            "Master Woodcraft, Glendale Queens Shop Dynamics, 3/4-Inch Solid Plywood Carcasses & Dovetail Joinery",
            "🪵 Hand-rubbed walnut espresso (#12100E), warm honey oak (#D4A373), forged brass accents, dovetail joinery schematics, architectural crown moulding profiles, craftsman serif typography.",
            "#D4A373",
            "#12100E",
            team_filter,
            "John_Patrick_Carroll_Jr_Lookbook.pdf",
            "Carroll Craft Master Woodcraft",
            "Successfully seeded Carroll Craft Woodworking swarm with 5 Advocates + 1 Heel."
        ))

    # Also make sure the personas have the team assigned correctly to both CARROLLCRAFT and domain_name.upper()
    cur.execute("UPDATE persona SET team = ? WHERE team = ?", ("CARROLLCRAFT", domain_name.upper()))
    cur.execute("UPDATE sim_agents SET team = ? WHERE team = ?", ("CARROLLCRAFT", domain_name.upper()))

    conn.commit()
    conn.close()
    print("[CMDB] Registered CMDB CI Stack manifest for CARROLLCRAFT!")

if __name__ == "__main__":
    asyncio.run(main())
