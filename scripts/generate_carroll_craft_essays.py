#!/usr/bin/env python3
"""
Generate Master Craft Essays for Carroll Craft Woodworking
Path: /home/james/stacklabs/scripts/generate_carroll_craft_essays.py

Convenes the woodcraft council personas to compile:
1. Essay 01: "The Pre-War Humidity Trap: Why Particle Board Sags in Queens & How Solid Woodcraft Survives 100 Years"
2. Essay 02: "Cabinet Refacing vs. Full Gut Demolition: The Homeowner's Guide to Saving $30,000 in Glendale & Forest Hills"
"""

import json
import os
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
CARROLL_CRAFT_DIR = SOVEREIGN_ROOT / "34_CarrollCraft"
DATA_DIR = CARROLL_CRAFT_DIR / "src" / "data"
PUBLIC_ESSAYS_DIR = CARROLL_CRAFT_DIR / "public" / "essays"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_ESSAYS_DIR.mkdir(parents=True, exist_ok=True)

ESSAY_01_MD = """# The Pre-War Humidity Trap: Why Particle Board Sags in Queens & How Solid Woodcraft Survives 100 Years

**By John Patrick Carroll, Jr.**  
*Master Cabinetmaker & Proprietor, Carroll Craft Woodworking (Glendale, Queens)*  
*With contributions from Vince DeLuca (Coatings Specialist), Eamon Kelly (Pre-War Drafter), and @particle_board_patrol*

---

## 1. The Physics of Queens Pre-War Humidity Cycles

If you walk into a 1920s brick row house in Glendale or a classic pre-war co-op off Queens Boulevard in Forest Hills during mid-January, your nose and skin will tell you what the hygrometer confirms: relative humidity (RH) routinely plummets below **18%**. Unregulated cast-iron steam radiators bake the living spaces, boiling the air dry. 

Fast forward to August: tropical Atlantic moisture rolls over Long Island Sound, pushing indoor RH past **85% to 92%** for weeks at a time.

```text
[NYC Seasonal Humidity Delta: Δ72% RH]
January (Steam Radiators): 15% - 20% RH  ───► Dry Shrinkage Stress
August (Summer Ocean Swell): 85% - 92% RH  ───► Severe Moisture Expansion
```

To wood, this swings equilibrium moisture content (EMC) from roughly 4% to over 16%. In other words, every single cubic foot of cellulose in your home is rhythmically expanding and contracting, gasping for air twice a year.

How your cabinetry responds to this hydraulic breathing determines whether your kitchen survives a century or crumbles into a sagging, swollen mess before your child finishes middle school.

---

## 2. Anatomy of Failure: Why Box-Store Particle Board and MDF Self-Destruct

Big-box retail kitchen showrooms and flat-pack imported cabinets rely on medium-density fiberboard (MDF) or low-density particle board (often euphemistically labeled "furniture board" or "engineered composite"). 

Here is what happens under Queens environmental conditions:

1. **Urea-Formaldehyde Glue Hydrolysis**: Particle board is not wood; it is compressed sawdust held together with resin binders. Under repeated cycling of high humidity and heat, the adhesive bonds undergo moisture-induced hydrolysis. The fibers begin to spring back—a permanent, irreversible volume expansion known in wood science as *thickness swelling*.
2. **Creep Deformation Under Load**: Particle board has negligible shear strength across its horizontal span. When loaded with 40 pounds of cast-iron Dutch ovens, Le Creuset cookware, or canned goods, the matrix undergoes viscoelastic creep. A 36-inch particle-board shelf will permanently bow within 18 months.
3. **The 32mm Hinge Tear-Out Catastrophe**: European concealed hinges attach via 5/8-inch screws driven directly into sawdust cores. Once humidity softens the resin, the mechanical grip loosens. When a homeowner leans on an open cabinet door or a toddler tugs on it, the entire hinge plate rips out, leaving an unrepairable crater of pulverized wood dust.
4. **Peel-and-Stick Thermofoil Delamination**: Thermofoil is merely PVC vinyl shrink-wrapped over shaped MDF with heat-activated glue. In a working kitchen near an oven door or a steam kettle, temperatures exceed 140°F. The glue vaporizes, and the vinyl curls back like scorched paper.

> **Voice of the Heel (@particle_board_patrol):**  
> *"Go to any kitchen showroom on Long Island or Queens. Knock on the carcass. If it thuds like a hollow cardboard shoebox and you see raw particle edges behind the sink cutouts, turn around and run. The minute a drainpipe weeps a single teaspoon of water, that sink base mushrooms like a stale biscuit. You paid $25,000 for pressed garbage."*

---

## 3. The Solid Woodcraft Alternative: 3/4-Inch Domestic Plywood & Dovetail Joinery

At Carroll Craft, every kitchen carcass, shelf, and drawer box follows classical cabinetmaker mechanics:

### 3.1. 3/4-Inch Domestic Birch Plywood Carcasses
We construct all cabinet carcasses from **3/4-inch 7-ply domestic maple or Baltic birch plywood**. 
- Alternating cross-grain veneer plies cancel out dimensional movement across both axes.
- Screw holding strength exceeds **240 pounds of perpendicular pull force**—three times that of industrial particle board.
- Marine-grade phenolic or water-resistant PVA bonds ensure that even if a sink pipe drips, the core never delaminates.

### 3.2. Hand-Cut & Machined Dovetail Drawer Boxes
A drawer box is pulled 15,000 times over its lifespan. Butt joints fastened with pin nails or cheap staples fail the moment a drawer catches. 
- We craft our drawer boxes from **5/8-inch solid Eastern hard maple**, joined at all four corners with interlocking **dovetails**.
- The mechanical interlocking geometry means the drawer cannot pull apart without shearing solid timber.
- Underneath, we mount full-extension **Blum Movento soft-close runners**, rated for 100-pound dynamic load capacities.

```text
       Traditional Interlocking Dovetail Joint
       ┌──────┬───┬──────┬───┬──────┐
       │      │ / │      │ / │      │  Mechanical interlock prevents
       │      │/  │      │/  │      │  face withdrawal under tensile load
       └──────┴───┴──────┴───┴──────┘
```

### 3.3. Solid Hardwood Face Frames & Mortise Joinery
Instead of frameless ("European") carcasses that leave fragile edge-banding exposed to knocks, we build **1-1/2-inch wide, 3/4-inch thick solid hardwood face frames** (White Oak, American Black Walnut, or Hard Maple). Pocket-screwed and glued with face biscuits, the face frame acts as an unyielding structural girder, locking the entire cabinet bank into a singular, immovable architectural unit.

---

## 4. Architectural Coatings: Sealing Against the Swamp

Even solid hardwood must be shielded against water vapour transmission. Vince DeLuca, our coatings specialist, explains the finishing chemistry:

> *"Hardware store oil-based polyurethanes take 30 days to fully cure and yellow under Queens window light. We use catalyzed two-component conversion varnishes (2K polyurethanes). It forms a chemical cross-link that seals the wood grain at the molecular level. Boiling pasta water, red wine spills, and oven heat bounce right off. It seals the timber against seasonal moisture absorption while preserving the tactile warmth of real grain."*

---

## 5. Summary: Built for Your Grandchildren

A kitchen should outlast the mortgage. When you install solid woodcraft engineered for the specific thermodynamics of Queens pre-war homes, you never think about sagging shelves, drooping doors, or crumbling screw holes. 

You run your fingers along the smooth, hand-rubbed radius of a solid oak frame, pull open a dovetailed maple drawer that glides like silk, and know that what you built is permanent.
"""

ESSAY_02_MD = """# Cabinet Refacing vs. Full Gut Demolition: The Homeowner's Guide to Saving $30,000 in Glendale & Forest Hills

**By Sal Moretti**  
*Cabinet Refacing & Practical Modernization Lead, Carroll Craft Woodworking*  
*With contributions from John Patrick Carroll, Jr. and Marcus Vance (Stone Integration)*

---

## 1. The Queens Remodeling Trap: Why Full Demolition Costs Double What You Think

If you speak to a general contractor or a big-box design salesman about remodeling your kitchen in Glendale, Middle Village, Ridgewood, or Forest Hills, their immediate recommendation is almost always: *"Gut it to the studs."*

On paper, a complete gut demolition sounds tidy. In physical Queens reality, it is a logistical and financial nightmare:

1. **Street & Dumpster Permits**: Glendale and Ridgewood streets (like 68th Street or Central Ave) are narrow residential corridors. Siting a 20-yard roll-off dumpster requires costly DOT street-occupancy permits, blocked driveway complaints, and ticket exposure.
2. **Pre-War Wall Traps**: Tearing down upper cabinets anchored into 1920s plaster-and-lath walls invariably pulls down crumbling horsehair plaster, exposes uninsulated brick or knob-and-tube wiring, and triggers mandatory NYC DOB filing fees, asbestos testing, and electrical service upgrades.
3. **The 10-Week Microwave Exile**: A full demolition leaves your family cooking microwave dinners in the living room for two to three months while waiting on plumbing rough-ins, drywall taping, flooring patches, and subcontractor delays.
4. **The Invoice Shock**: A full gut kitchen remodel in Queens in 2026 starts at **$65,000 to $95,000**.

---

## 2. The Refacing Blueprint: Preserving the Best Wood in the House

Here is the secret that big-box kitchen salespeople hide: **In many 1920s through 1970s Queens homes, your existing cabinet carcasses are made of better lumber than 95% of new cabinets sold today.**

Back then, carpenters built site-built boxes out of solid 3/4-inch fir plywood or clear yellow pine. Those boxes are plumb, rock-solid, and already adapted to the natural settling of your home's foundation. Tearing them out to replace them with imported 1/2-inch particle-board boxes from a retail chain is throwing gold in the landfill.

```text
┌────────────────────────────────────────────────────────┐
│             THE CARROLL CRAFT REFACING CORE             │
├──────────────────────────┬─────────────────────────────┤
│ WHAT WE PRESERVE:        │ WHAT WE UPGRADE:            │
├──────────────────────────┼─────────────────────────────┤
│ • Sound 3/4" Plywood     │ • 100% Solid Hardwood Doors │
│   Carcase Boxes          │ • Solid Hardwood 5-Piece    │
│ • Existing Floor Plan    │   Drawer Fronts             │
│   & Layout Footprint     │ • 5/8" Solid Maple Dovetail │
│ • Solid Countertop Plumb │   Drawer Boxes              │
│   Line (or Laser-Match)  │ • Blum Soft-Close Hinges    │
│ • Intact Pre-War Wall    │ • 1/4" Solid Wood Exterior  │
│   Structures             │   Carcase Skinning          │
└──────────────────────────┴─────────────────────────────┘
```

---

## 3. The Carroll Craft 5-Step Refacing Process

Our refacing process takes **4 to 5 days on-site** with zero dumpster required and minimal kitchen downtime:

1. **Precision Structural Survey**: We inspect every existing box, shelf, and face frame for plumb, level, and structural integrity. Any sagging shelf or tired bracket is reinforced with solid hardwood cleats.
2. **Hardware Removal**: We remove and recycle all old cabinet doors, drawer boxes, worn hinges, and roller slides.
3. **1/4-Inch Solid Hardwood Skinning**: We reface all exposed cabinet exterior sides, undersides, and face frames with **1/4-inch solid hardwood veneer or real 1/4" plywood skins** (White Oak, Walnut, Cherry, or Painted Hard Maple). We use high-pressure structural adhesives and pin-fasteners to fuse the new wood permanently to the existing frame.
4. **Custom Bench-Built Doors & Dovetailed Drawers**: In our Glendale shop, we custom-craft brand-new shaker, raised-panel, or contemporary slab doors out of solid select hardwood. We fabricate new 5/8-inch dovetailed solid maple drawer boxes and install heavy-duty Blum undermount soft-close slides.
5. **Architectural Crown & Trim Integration**: We install new matching solid hardwood crown moulding scribed tight to your ceiling, light rail trim under wall cabinets, and matching toe kicks.

---

## 4. Head-to-Head Comparison: Refacing vs. Full Gut Demolition

| Metric | Full Gut Demolition | Carroll Craft Refacing | Homeowner Advantage |
| :--- | :--- | :--- | :--- |
| **Typical Cost** | $65,000 – $95,000 | $18,000 – $28,000 | **Saves $35,000+** |
| **On-Site Disruption** | 8 to 12 Weeks | 4 to 5 Days | **Saves 2 Months** |
| **Dumpster Required?** | Yes ($1,200 + DOT Permits) | No (All waste bagged & carted) | Zero Street Parking Loss |
| **Wall & Plaster Damage**| High (Demolition tears lath) | Zero (Boxes stay on the wall) | No Drywalling Delays |
| **Countertop Impact** | Must be smashed & replaced | Can be kept or upgraded cleanly | Preserves existing stone |
| **Material Quality** | Often 1/2" MDF or import box | 3/4" Original Boxes + Solid Oak | 100% Solid Hardwood |
| **Landfill Waste** | 2.5 Tons of Debris | Minimal (~150 lbs hardware/doors) | Sustainable & Green |

---

## 5. Countertop & Stone Integration: Marcus Vance's Rule

A common homeowner concern: *"Can I keep my existing granite or quartz countertop during refacing?"*

Marcus Vance, our templating specialist, explains:

> *"Yes, absolutely. Because the cabinet carcasses never leave the wall or subfloor, your existing countertop remains 100% undisturbed. If you DO want to upgrade your countertop, our zero-gap digital laser templating allows us to coordinate new quartz, quartzite, or soapstone installation seamlessly on day four of the refacing schedule. You get brand-new stone, custom dovetail drawers, and solid wood doors—at half the price of a demolition."*

---

## 6. The Bottom Line for Glendale & Forest Hills Homeowners

Before you sign a contract for a $75,000 demolition that turns your home into a construction zone for the entire summer, look at your existing cabinets.

If the boxes are solid, refacing with real custom bench-made woodcraft gives you a showroom kitchen with solid maple dovetail drawers and hand-finished hardwood doors—and leaves $30,000 in your pocket for your children's college fund, a family vacation, or property investments.
"""

ESSAYS_DATA = [
    {
        "id": "pre-war-humidity-trap",
        "title": "The Pre-War Humidity Trap: Why Particle Board Sags in Queens & How Solid Woodcraft Survives 100 Years",
        "slug": "pre-war-humidity-trap",
        "subtitle": "How steam radiator heat and August swamp moisture destroy box-store cabinets—and the traditional joinery physics that prevent it.",
        "author": "John Patrick Carroll, Jr.",
        "authorRole": "Master Cabinetmaker & Proprietor",
        "readTime": "8 min read",
        "date": "September 2026",
        "badge": "Woodcraft Physics",
        "summary": "An exhaustive analysis of NYC seasonal relative humidity swings (15% in winter to 90% in August), the cellular breakdown of urea-formaldehyde particle board carcasses, and why true 3/4-inch domestic plywood with dovetail joinery endures for generations.",
        "tags": ["Woodcraft Physics", "Pre-War Queens", "Joinery", "Materials Science"],
        "coverImage": "/portfolio/millwork_01.png",
        "contentMarkdown": ESSAY_01_MD,
        "councilQuotes": [
            {
                "name": "John Patrick Carroll, Jr.",
                "handle": "john_carroll_craft",
                "role": "Master Cabinetmaker",
                "quote": "If you lean on a cabinet door and the hinge tears out of particle-board dust, that isn't furniture—it's compressed trash. Wood breathes; you have to build with joinery that breathes with it."
            },
            {
                "name": "Vince DeLuca",
                "handle": "vince_deluca_finishes",
                "role": "Coatings Specialist",
                "quote": "Catalyzed conversion varnishes seal wood at the molecular cross-link level. Boiling pasta steam and grease won't break the barrier."
            },
            {
                "name": "The Flat-Pack Skeptic",
                "handle": "particle_board_patrol",
                "role": "Cabinet Auditor",
                "quote": "90% of retail kitchen showrooms sell compressed sawdust held together with formaldehyde. If you put a hot soup pot on it and it bubbles, you got robbed."
            }
        ]
    },
    {
        "id": "cabinet-refacing-economics",
        "title": "Cabinet Refacing vs. Full Gut Demolition: The Homeowner's Guide to Saving $30,000 in Glendale & Forest Hills",
        "slug": "cabinet-refacing-economics",
        "subtitle": "Why discarding sound 3/4-inch plywood boxes is financial madness, and how precision custom refacing delivers heirloom quality at 1/3 the cost.",
        "author": "Sal Moretti",
        "authorRole": "Cabinet Refacing & Practical Modernization Lead",
        "readTime": "10 min read",
        "date": "September 2026",
        "badge": "Remodeling Economics",
        "summary": "A transparent breakdown of Queens kitchen remodeling economics: navigating narrow streets and dumpster permits, identifying sound pre-war carcass construction, and the step-by-step refacing engineering process that saves homeowners $25k to $40k.",
        "tags": ["Refacing Economics", "Queens Homes", "Kitchen Remodeling", "Cost Analysis"],
        "coverImage": "/portfolio/kitchen_01.png",
        "contentMarkdown": ESSAY_02_MD,
        "councilQuotes": [
            {
                "name": "Sal Moretti",
                "handle": "sal_the_preserver",
                "role": "Refacing Lead",
                "quote": "If your existing boxes are solid 3/4-inch fir or yellow pine from 1950, tearing them out is throwing away the best timber in Queens. Keep the boxes, upgrade the doors, save $35,000."
            },
            {
                "name": "Marcus Vance",
                "handle": "marcus_stone_scribe",
                "role": "Stone Templater",
                "quote": "Because the carcasses never leave the floor, existing granite and quartz remain 100% undisturbed. Or we can laser-fit new stone seamlessly."
            },
            {
                "name": "Eamon Kelly",
                "handle": "eamon_drafts_queens",
                "role": "Pre-War Drafter",
                "quote": "Demolition tears down horsehair plaster and lath in pre-war homes. Refacing respects the building's structural envelope."
            }
        ]
    }
]

def main():
    # Write JSON data
    json_path = DATA_DIR / "essays.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ESSAYS_DATA, f, indent=2)
    print(f"✅ Wrote essays.json to {json_path}")

    # Write Markdown files
    f1 = PUBLIC_ESSAYS_DIR / "01_pre_war_humidity_trap.md"
    with open(f1, "w", encoding="utf-8") as f:
        f.write(ESSAY_01_MD)
    print(f"✅ Wrote {f1}")

    f2 = PUBLIC_ESSAYS_DIR / "02_cabinet_refacing_vs_full_gut.md"
    with open(f2, "w", encoding="utf-8") as f:
        f.write(ESSAY_02_MD)
    print(f"✅ Wrote {f2}")

    print("\n🎉 Master Craft Essays generation complete!")

if __name__ == "__main__":
    main()
