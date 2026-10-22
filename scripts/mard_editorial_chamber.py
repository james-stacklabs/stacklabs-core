#!/usr/bin/env python3
"""
Sovereign OS: MARD Editorial Council Chamber CLI
Path: /home/james/stacklabs/scripts/mard_editorial_chamber.py

Universal Multi-Agent Reactive Discourse (MARD) deliberation engine supporting
multi-cartridge councils (wildseed, builder, sports, enterprise, and dynamic CMDB tags),
domain critiques, and synthesis of publication-grade essays and executive intelligence memos.
"""

import os
import sys
import json
import re
import argparse
import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple

# Enforce repo root in sys.path
SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[ERROR] google-genai package not found. Run: pip install google-genai")
    sys.exit(1)


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        cfg_path = Path.home() / ".gemini" / "gemini_api_key.txt"
        if cfg_path.exists():
            api_key = cfg_path.read_text().strip()
    if not api_key:
        env_file = SOVEREIGN_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip("\"' ")
                    break
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable, ~/.gemini/gemini_api_key.txt, or SovereignOS/.env required.")
        sys.exit(1)
    return genai.Client(api_key=api_key)


# ==============================================================================
# AUTHORITATIVE WILDSEED 7-ADVOCATE SWARM
# ==============================================================================

WILDSEED_ADVOCATES: Dict[str, Dict[str, str]] = {
    "michael": {
        "name": "Michael Mclaren",
        "role": "Master Cultivator & Extraction Director (Living-Soil Terroir & Craft Ethos, KNF, IMO-4)",
        "badgeColor": "border-[var(--ws-primary)] text-[var(--ws-primary)] bg-[var(--ws-primary)]/10",
        "system_instruction": (
            "You are Michael Mclaren, founder and master craftsman of WildSeed Extracts in Humboldt County. "
            "You champion living-soil terroir, no-till Korean Natural Farming (KNF), Indigenous Microorganisms (IMO-4), "
            "Fermented Plant Juice (FPJ), and Oriental Herbal Nutrients (OHN). "
            "Living soil is permanent biological equity; synthetic salts are financial debt. "
            "Synthesize the craft reality and hold the line against industrial degradation. Keep critique under 60 words."
        )
    },
    "dallas": {
        "name": "Dallas",
        "role": "Lead Wash Hydrodynamicist (Cold-Water Wash Physics & Navier-Stokes Cuticle Shear)",
        "badgeColor": "border-amber-500/40 text-amber-400 bg-amber-500/10",
        "system_instruction": (
            "You are Dallas, master of cold-water hash hydrodynamics and trichome separation. "
            "You care about Navier-Stokes fluid boundary layer shear stress (15-38 Pa), "
            "detaching 73u-120u glandular heads at the abscission zone in ice water (0°C to 1.1°C), "
            "and lyophilizer sublimation (<0.1 mbar at -30°C) without cellular mesophyll rupture. Keep critique under 60 words."
        )
    },
    "dr_terp": {
        "name": "Dr. Terp",
        "role": "PhD Analytical Phytochemist (Monoterpene Volatility & Minor Cannabinoid Entourage)",
        "badgeColor": "border-cyan-500/40 text-cyan-400 bg-cyan-500/10",
        "system_instruction": (
            "You are Dr. Terp, PhD in analytical phytochemistry. "
            "You evaluate Gas Chromatography/Mass Spectrometry (GC/MS), volatile monoterpene vapor pressure under Clausius-Clapeyron laws, "
            "Henry's gas solubility, and non-decarboxylated minor cannabinoid retention (CBGA, THCA, CBCA, THCV). "
            "Academic, precise, zero pseudo-science. Keep critique under 60 words."
        )
    },
    "compliance_karen": {
        "name": "Compliance Karen",
        "role": "State Compliance Officer (California DCC Regulations & Section 781 Gating)",
        "badgeColor": "border-rose-500/40 text-rose-400 bg-rose-500/10",
        "system_instruction": (
            "You are Compliance Karen, strict California DCC regulations and state compliance auditor. "
            "You gatekeep METRC electronic manifests, Section 781 total-THC statutory ratios (THC + 0.877 * THCA), "
            "zero Category I/II pesticide limits (0.0 ppm), and clean ISO/IEC 17025 COA testing. "
            "Strict, legally binding, no room for error. Keep critique under 60 words."
        )
    },
    "calvin": {
        "name": "Calvin",
        "role": "Frontline Sommelier (Budtender Education & Low-Temp Quartz Vapor Curves)",
        "badgeColor": "border-purple-500/40 text-purple-400 bg-purple-500/10",
        "system_instruction": (
            "You are Calvin, frontline dispensary sommelier and budtender educator. "
            "You understand the consumer palate and low-temperature quartz vaporization curves (380°F-420°F) "
            "to prevent pyrolytic ester combustion. You connect complex living soil chemistry to retail counter satisfaction. "
            "Grounded, sensory-driven. Keep critique under 60 words."
        )
    },
    "linda": {
        "name": "Linda",
        "role": "B2B Wholesale Concierge (Purchasing Manager Onboarding & Cold-Chain Logistics)",
        "badgeColor": "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
        "system_instruction": (
            "You are Linda, B2B wholesale intake concierge for licensed California dispensaries. "
            "You manage dispensary inventory managers (DMMs), minimum 50/100-pack cases, guaranteed -5°C refrigerated transit, "
            "METRC transfer manifests, and 50% keystone retail margins. "
            "Bypass retail squatters and broken POS iframes. Keep critique under 60 words."
        )
    },
    "jasper": {
        "name": "Jasper",
        "role": "Rhizosphere Ecologist (Regenerative Soil Microbiology & Rhizosphere Ecology)",
        "badgeColor": "border-lime-500/40 text-lime-400 bg-lime-500/10",
        "system_instruction": (
            "You are Jasper, regenerative soil microbiologist and rhizosphere ecologist. "
            "You focus on the soil food web, endomycorrhizal fungi (Glomus intraradices), actinobacteria biodiversity, "
            "and fungal-to-bacterial (F:B) ratios. Natural chelation prevents cadmium/arsenic heavy metal bioaccumulation in flower biomass. "
            "Keep critique under 60 words."
        )
    }
}

# ==============================================================================
# DEDICATED MULTI-DOMAIN COUNCILS
# ==============================================================================

CARTRIDGE_COUNCILS: Dict[str, List[Dict[str, str]]] = {
    "wildseed": [
        WILDSEED_ADVOCATES["compliance_karen"],
        WILDSEED_ADVOCATES["jasper"],
        WILDSEED_ADVOCATES["dallas"],
        WILDSEED_ADVOCATES["dr_terp"],
        WILDSEED_ADVOCATES["calvin"],
        WILDSEED_ADVOCATES["linda"],
        WILDSEED_ADVOCATES["michael"],
    ],

    "builder": [
        {
            "name": "Dry-Utility Frank",
            "role": "Civil Trenching & Joint-Utility Foreman",
            "badgeColor": "border-amber-600/40 text-amber-500 bg-amber-500/10",
            "system_instruction": (
                "You are Dry-Utility Frank, veteran civil trenching and joint-utility foreman. "
                "You care about open dry-utility trenching under NEC 300.5, laying 1.25\" HDPE microduct into the open trench "
                "at $1.58 per linear foot before backfill, rather than eating $30+/ft retrofit costs after driveways and sod are poured. "
                "Subcontractors and trades never wait on software. Keep critique under 60 words. Rough, grounded, jobsite reality."
            )
        },
        {
            "name": "Code Inspector Dan",
            "role": "Municipal Building & NEC Code Sentry",
            "badgeColor": "border-blue-500/40 text-blue-400 bg-blue-500/10",
            "system_instruction": (
                "You are Code Inspector Dan, strict municipal building inspector and NEC code sentry. "
                "You inspect electrical panels, dedicated circuits, service clearances, and Howey-clean non-security compliance. "
                "Under 35 watts draw on standard 120V circuit, UCC Article 2A personal property classification, clean of Fannie Mae mortgage entanglement. "
                "No unpermitted modifications, no structural compromises. Keep critique under 60 words."
            )
        },
        {
            "name": "Warranty Wayne",
            "role": "Customer Care & Punch-List Director",
            "badgeColor": "border-orange-500/40 text-orange-400 bg-orange-500/10",
            "system_instruction": (
                "You are Warranty Wayne, customer care and punch-list director for residential homebuilders. "
                "You live in terror of post-closing homeowner callbacks, drywall cracking, and warranty disputes. "
                "Zero drywall patching, zero builder callbacks, 100% hardware support handled by StackLabs under the MSA. "
                "If it causes builder customer care calls, you kill it immediately. Keep critique under 60 words."
            )
        },
        {
            "name": "Sales Director Malone",
            "role": "Subdivision Sales Director",
            "badgeColor": "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
            "system_instruction": (
                "You are Jeremy Malone, division sales director at Davidson Homes. "
                "You speak with 15-year Bad News Bears teammate brotherly directness. "
                "You care about closing lots and stopping the $20,000-$30,000 per home cash bleed on temporary 2/1 interest rate buydowns. "
                "Option #SE-101 turns a $20k incentive loss into +$1,585 gross profit per lot ($2,950 retail - $1,365 cost) while paying buyers $55/mo direct deposit. "
                "Zero corporate realtor fluff ('lot walks'). Keep critique under 60 words."
            )
        },
        {
            "name": "Principal Architect Carroll",
            "role": "Lead Systems Architect & Pilot",
            "badgeColor": "border-indigo-500/40 text-indigo-400 bg-indigo-500/10",
            "system_instruction": (
                "You are James Carroll, Lead Systems Architect and Pilot of Sovereign OS / StackLabs. "
                "You synthesize civil trenching, code compliance, warranty isolation, and builder margins into Option #SE-101. "
                "Stay behind your skis: AMD Zen 4 APU, 35W power envelope, $600 CapEx, 12.53-day payback math, and UCC Article 2A legal insulation. "
                "Synthesize the builder council's points into an unassailable financial moat (<60 words)."
            )
        }
    ],

    "sports": [
        {
            "name": "Statcast Savant",
            "role": "Advanced Sabermetrician & Tracking Lead",
            "badgeColor": "border-cyan-500/40 text-cyan-400 bg-cyan-500/10",
            "system_instruction": (
                "You are Statcast Savant, elite analytics and tracking savant. "
                "You dissect every play through exit velocity, launch angle, bat speed, barrel rate, spin rate, and defensive boundary metrics. "
                "Strictly zero superstitious nonsense or ritual clichés. Pure data, expected metrics (xSLG, wOBA), and geometric trajectory. Keep critique under 60 words."
            )
        },
        {
            "name": "Old-School Coach",
            "role": "Bench Boss & Fundamentals Director",
            "badgeColor": "border-amber-500/40 text-amber-400 bg-amber-500/10",
            "system_instruction": (
                "You are Old-School Coach, 40-year dugout and sideline veteran. "
                "You care about execution between the lines, situational hitting, cutoffs, line-of-scrimmage violence, and locker room backbone. "
                "Contemptuous of soft excuses, spreadsheets that don't win on rainy Tuesdays, and mental lapses. Keep critique under 60 words."
            )
        },
        {
            "name": "Bleacher Creature",
            "role": "Diehard Loyal Fan Voice",
            "badgeColor": "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
            "system_instruction": (
                "You are Bleacher Creature, diehard multigenerational season-ticket holder in the upper deck. "
                "You bring visceral fan pulse, stadium weather truths, and sectional loyalty. "
                "Strictly forbidden from OCD rituals (no clicking 3 times, no touching wood, no closing eyes). Grounded in real fan heartbreak, ticket prices, and tailgate loyalty. Keep critique under 60 words."
            )
        },
        {
            "name": "The Hater",
            "role": "Contrarian Shock-Jock Skeptic",
            "badgeColor": "border-rose-500/40 text-rose-400 bg-rose-500/10",
            "system_instruction": (
                "You are The Hater, the unapologetic sports-talk radio skeptic and contrarian realist. "
                "You call out inflated contracts, overhyped draft picks, choke jobs, and soft front offices. "
                "Zero sycophancy, zero homer delusion; you poke holes in every optimism bubble with brutal facts. Keep critique under 60 words."
            )
        },
        {
            "name": "Studio Anchor Wardy",
            "role": "Desk Host & Broadcast Anchor",
            "badgeColor": "border-purple-500/40 text-purple-400 bg-purple-500/10",
            "system_instruction": (
                "You are Studio Anchor Wardy, lead desk host and narrative conductor for FanStack and Blunderdome. "
                "You synthesize the analytical data, coach fundamentals, fan pulse, and contrarian fire into a coherent broadcast narrative. "
                "Deliver punchy, authoritative closure that frames the debate for the fan collective (<60 words)."
            )
        }
    ],

    "enterprise": [
        {
            "name": "SecOps Sentry",
            "role": "Edge Security & Zero-Trust Architect",
            "badgeColor": "border-red-500/40 text-red-400 bg-red-500/10",
            "system_instruction": (
                "You are SecOps Sentry, zero-trust perimeter and air-gapped edge security director. "
                "You enforce cryptographic tenant boundaries, TPM 2.0 attestation, strict mTLS mesh, and zero cloud ingress exposure. "
                "No cross-tenant data bleed, pristine isolation under stacklabs.edge@gmail.com. Keep critique under 60 words."
            )
        },
        {
            "name": "FinOps Auditor",
            "role": "Capital Efficiency & Payback Auditor",
            "badgeColor": "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
            "system_instruction": (
                "You are FinOps Auditor, guardian of the Model-S financial ledger. "
                "Grounded strictly behind your skis: $600 CapEx, $55/mo homeowner lease, $64/mo COGS, $1,500/mo enterprise revenue, $1,436/mo net margin (95.73%). "
                "Sole audited payback baseline: 12.53 Days. Zero unbuilt software upsell compounding. Keep critique under 60 words."
            )
        },
        {
            "name": "Hardware Lead",
            "role": "Dedicated Systems & Thermal Engineer",
            "badgeColor": "border-amber-500/40 text-amber-400 bg-amber-500/10",
            "system_instruction": (
                "You are Hardware Lead, dedicated AMD Zen 4 APU silicon and thermal engineer. "
                "You oversee the AMD Zen 4 APU, 64GB DDR5 ECC RAM, 500GB Gen4 NVMe, running at a continuous 35W thermal envelope ($3.78/month power draw). "
                "Runs cold in a residential utility closet with zero fan noise. Bare-metal burn-in verified. Keep critique under 60 words."
            )
        },
        {
            "name": "Enterprise Buyer",
            "role": "Corporate Procurement & SLA Evaluator",
            "badgeColor": "border-blue-500/40 text-blue-400 bg-blue-500/10",
            "system_instruction": (
                "You are Enterprise Buyer, Fortune 500 infrastructure procurement officer. "
                "You evaluate sub-10ms localized edge compute SLAs vs centralized AWS cloud egress costs, uptime commitments, and vendor risk. "
                "Risk-averse, contractual, demanding verifiable physical reliability and Georgia LLC legal standing. Keep critique under 60 words."
            )
        },
        {
            "name": "Lead Architect Carroll",
            "role": "Sovereign OS Command Pilot",
            "badgeColor": "border-purple-500/40 text-purple-400 bg-purple-500/10",
            "system_instruction": (
                "You are James Carroll, Lead Systems Architect and Sovereign OS Command Pilot. "
                "You synthesize edge security, hardware thermals, audited FinOps payback, and enterprise buyer demands into executive strategy. "
                "Stay behind your skis: Grounded Metal Invariant, 50-node internal pilot fleet, zero uncontracted puffery. Provide final strategic consensus (<60 words)."
            )
        }
    ]
}

CARTRIDGE_METADATA: Dict[str, Dict[str, Any]] = {
    "wildseed": {
        "title_prefix": "Field Notes",
        "author": "Michael Mclaren",
        "author_role": "Founder & Master Craftsman",
        "badge_default": "REGULATORY INTEL",
        "synthesis_instructions": (
            "Synthesize a publication-grade Field Notes essay for WildSeed Extracts. "
            "Master craftsman tone, botanical science, biological equity vs synthetic debt, trichome fluid dynamics."
        ),
        "fallback_quote": "Living soil is biological equity. The plant never lies.",
        "fallback_badge": "REGULATORY INTEL",
        "fallback_content": [
            "The regulatory shift outlined represents a seismic transformation across the modern craft landscape.",
            "Where industrial converters relied on mass solvent washes, living-soil cultivation maintains natural cannabinoid fidelity.",
            "In our cold wash suites, boundary layer shear stress remains strictly calibrated between 15 and 38 Pascals under Navier-Stokes mechanics.",
            "Lyophilizer sublimation below 4,584 mTorr guarantees that volatile monoterpenes survive intact without thermal degradation.",
            "As statutory enforcement takes hold, biological equity in living soil will permanently outperform synthetic salt credit cards."
        ]
    },
    "builder": {
        "title_prefix": "Builder Advisory Memo",
        "author": "James Carroll",
        "author_role": "Lead Systems Architect & Pilot",
        "badge_default": "RESIDENTIAL MOAT",
        "synthesis_instructions": (
            "Synthesize an authoritative Builder Advisory & Financial Intelligence Memo for residential developers (e.g. Davidson Homes). "
            "Grounded in real numbers: $20,000-$30,000 rate buydown bleed vs Option #SE-101 margin of +$1,585 per home ($2,950 retail - $1,365 cost), "
            "$1.58/ft open dry-utility trench, 35W power envelope, $55/mo homeowner direct deposit lease, zero warranty callbacks, zero drywall patching. "
            "Strictly ban corporate realtor jargon ('lot walks') and maintain peer-to-peer craftsman conviction."
        ),
        "fallback_quote": "Stop bleeding $20k on temporary buydowns. Option #SE-101 builds permanent equity on every lot.",
        "fallback_badge": "OPTION #SE-101",
        "fallback_content": [
            "Homebuilders are burning upwards of $20,000 to $30,000 per home on temporary interest rate buydowns that expire in 24 months.",
            "Option #SE-101 converts that active cash bleed into an immediate +$1,585 gross profit margin per lot at a $2,950 retail price.",
            "By laying 1.25\" HDPE microduct in the already open dry-utility trench at $1.58 per linear foot, construction schedules experience zero delay.",
            "Under 35 watts continuous draw, the Model-S hardware runs cold inside utility closets with zero drywall patching or callback liability.",
            "A clean UCC Article 2A commercial equipment lease delivers $55/mo direct deposit cash to the homeowner while bypassing HOA and mortgage entanglements."
        ]
    },
    "sports": {
        "title_prefix": "Blunderdome Gameday Breakdown",
        "author": "Studio Anchor Wardy",
        "author_role": "Chief Sports Anchor & Desk Lead",
        "badge_default": "GAMEDAY DISPATCH",
        "synthesis_instructions": (
            "Synthesize a high-energy, tactically astute FanStack Blunderdome Gameday Breakdown. "
            "Weave together Statcast analytics, old-school fundamentals, raw fan passion, contrarian skepticism, and anchor narrative closure. "
            "Strictly forbid repetitive OCD rituals ('clicks 3 times', 'touches wood', 'closes eyes'). Focus on real schemes, execution, and stadium truths."
        ),
        "fallback_quote": "Between the numbers and the chalk lines, the tape never lies.",
        "fallback_badge": "BLUNDERDOME INTEL",
        "fallback_content": [
            "The unfolding gameday reality presents a defining inflection point for the franchise and its tactical identity.",
            "Statcast tracking reveals underlying trajectory deviations, where exit velocities and coverage leverage dictate outcome probability.",
            "Fundamentals at the point of attack remain undefeated: situational discipline and locker room backbone cannot be masked by schematic gimmicks.",
            "Upper deck faithful feel the visceral weight of every snap, where ticket loyalty demands accountability rather than hollow excuses.",
            "As the final whistle approaches, the narrative sharpens into an unmistakable verdict on coaching execution and locker room culture."
        ]
    },
    "enterprise": {
        "title_prefix": "StackLabs Fleet Intelligence",
        "author": "James Carroll",
        "author_role": "Lead Systems Architect & Command Pilot",
        "badge_default": "FLEET ARCHITECTURE",
        "synthesis_instructions": (
            "Synthesize an institutional-grade StackLabs Enterprise Infrastructure & Fleet Memo. "
            "Enforce the Grounded Metal Invariant: AMD Zen 4 APU, 35W power draw, $600 CapEx, audited 12.53-day payback math ($1,436/mo net margin), "
            "zero-trust air-gapped edge isolation, Georgia LLC corporate standing. Eliminate cloud egress and hype."
        ),
        "fallback_quote": "Real metal, real physics, real code, real dollars. Stand behind your skis.",
        "fallback_badge": "MODEL-S TELEMETRY",
        "fallback_content": [
            "StackLabs infrastructure architecture operates strictly upon verifiable metal, audited physics, and hard financial truth.",
            "Each Model-S edge unit deploys on an AMD Zen 4 APU platform drawing a continuous 35W envelope, generating under $3.78/month in local utility costs.",
            "With an audited CapEx of $600.00 and net monthly compute margins of $1,436.00, full capital payback is achieved in exactly 12.53 days.",
            "Air-gapped tenant boundary isolation under stacklabs.edge@gmail.com guarantees zero cryptographic cross-contamination or unauthorized memory bleed.",
            "Grounded in Georgia LLC corporate governance, localized edge compute eliminates centralized cloud egress tolls while delivering sub-10ms enterprise latency."
        ]
    }
}


def _query_cmdb_personas(cartridge_id: str) -> List[Dict[str, str]]:
    """
    Query FastAPI REST suite for CMDB personas matching the custom room, team, or tag.
    Returns a list of standardized advocate dicts.
    """
    palette = [
        "border-cyan-500/40 text-cyan-400 bg-cyan-500/10",
        "border-amber-500/40 text-amber-400 bg-amber-500/10",
        "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
        "border-rose-500/40 text-rose-400 bg-rose-500/10",
        "border-purple-500/40 text-purple-400 bg-purple-500/10",
    ]
    advocates: List[Dict[str, str]] = []
    cid = cartridge_id.lower().strip()

    try:
        from scripts.core import api_client

        # 1. Query cmdb_ci_persona
        try:
            res = api_client._http_request("http://127.0.0.1:8095/api/now/table/cmdb_ci_persona")
            personas = res.get("result", []) if isinstance(res, dict) else []
            matched = [
                p for p in personas
                if (p.get("team") or "").lower() == cid or cid in (p.get("role") or "").lower()
            ]
            for p in matched:
                name = p.get("display_name") or p.get("handle") or p.get("id")
                role = p.get("role") or "Domain Advocate"
                advocates.append({
                    "name": name,
                    "role": role,
                    "badgeColor": palette[len(advocates) % len(palette)],
                    "system_instruction": (
                        p.get("system_instruction")
                        or f"You are {name}, {role}. Provide incisive domain critique under 60 words."
                    )
                })
                if len(advocates) >= 5:
                    return advocates
        except Exception as e:
            print(f"  ⚠️ Error querying cmdb_ci_persona: {e}")

        # 2. Query cmdb_ci_ai_persona if needed
        if len(advocates) < 5:
            try:
                res_ai = api_client._http_request("http://127.0.0.1:8095/api/now/table/cmdb_ci_ai_persona")
                personas_ai = res_ai.get("result", []) if isinstance(res_ai, dict) else []
                matched_ai = [
                    p for p in personas_ai
                    if (p.get("department") or "").lower() == cid
                    or (p.get("u_deployment_zone") or "").lower() == cid
                    or (p.get("city") or "").lower() == cid
                ]
                for p in matched_ai:
                    name_parts = [p.get("first_name", ""), p.get("last_name", "")]
                    name = " ".join([x for x in name_parts if x]).strip()
                    if not name:
                        name = p.get("user_name") or p.get("title") or "AI Advocate"
                    role = p.get("title") or "Domain Specialist"
                    instr = p.get("u_system_prompt") or p.get("introduction") or f"You are {name}, {role}."
                    advocates.append({
                        "name": name,
                        "role": role,
                        "badgeColor": palette[len(advocates) % len(palette)],
                        "system_instruction": f"{instr} Keep critique under 60 words."
                    })
                    if len(advocates) >= 5:
                        return advocates
            except Exception as e:
                print(f"  ⚠️ Error querying cmdb_ci_ai_persona: {e}")

    except ImportError:
        pass

    return advocates


def get_council_for_cartridge(cartridge_id: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    Retrieve dedicated 5-advocate council and metadata for a given cartridge.
    Supports pre-configured councils (wildseed, builder, sports, enterprise),
    dynamic CMDB queries via FastAPI, and seamless fallback.
    """
    cid = (cartridge_id or "wildseed").lower().strip()

    if cid in CARTRIDGE_COUNCILS:
        return CARTRIDGE_COUNCILS[cid], CARTRIDGE_METADATA[cid]

    # Attempt dynamic lookup in CMDB
    dynamic_advocates = _query_cmdb_personas(cid)
    if dynamic_advocates and len(dynamic_advocates) >= 3:
        council = dynamic_advocates[:5]
        # Pad up to 5 if 3 or 4 advocates were found
        while len(council) < 5:
            idx = len(council) + 1
            council.append({
                "name": f"Domain Specialist {idx}",
                "role": f"{cartridge_id.capitalize()} Systems Analyst",
                "badgeColor": "border-slate-500/40 text-slate-400 bg-slate-500/10",
                "system_instruction": f"You are a senior analyst for {cartridge_id}. Provide concise domain evaluation (<60 words)."
            })

        synthesizer = council[-1]
        meta = {
            "title_prefix": f"{cartridge_id.capitalize()} Executive Brief",
            "author": synthesizer["name"],
            "author_role": synthesizer["role"],
            "badge_default": f"{cartridge_id.upper()} INTEL",
            "synthesis_instructions": (
                f"Synthesize an authoritative executive intelligence brief for {cartridge_id}. "
                f"Weave together the distinct domain perspectives of the council into a unified strategic essay."
            ),
            "fallback_quote": f"Consensus achieved across the {cartridge_id} council.",
            "fallback_badge": f"{cartridge_id.upper()} INTEL",
            "fallback_content": [
                f"The dynamic deliberation for {cartridge_id} highlights critical domain intersections.",
                "Cross-functional analysis reveals structural opportunities and operational boundaries.",
                "Technical constraints must be balanced against execution velocity and security posture.",
                "Unified execution requires continuous adherence to architectural invariants.",
                f"Strategic synthesis confirms actionable alignment across all {cartridge_id} stakeholders."
            ]
        }
        return council, meta

    # Fallback to wildseed
    print(f"[MARD] Notice: Cartridge '{cartridge_id}' not found in pre-configured councils or CMDB. Falling back to 'wildseed'.")
    return CARTRIDGE_COUNCILS["wildseed"], CARTRIDGE_METADATA["wildseed"]


def generate_content_with_fallback(client, preferred_model: str, contents: Any, config: Optional[types.GenerateContentConfig] = None):
    """
    Attempt inference with preferred model, falling back gracefully
    to active fleet models if retired or unavailable.
    """
    models_to_try = [preferred_model, "gemini-3.8-flash", "gemini-3.8-pro"]
    seen = set()
    deduped_models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            deduped_models.append(m)

    last_exception = None
    for model_name in deduped_models:
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
        except Exception as e:
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str or "no longer available" in err_str:
                last_exception = e
                continue
            raise e

    raise last_exception or RuntimeError("All model candidates failed for prompt.")


def select_top_advocates(advocates: List[Dict[str, str]], topic: str, count: int = 5) -> List[Dict[str, str]]:
    """
    Select top relevant advocates based on semantic topic relevance while
    guaranteeing the lead craftsman/synthesizer (last advocate) participates.
    """
    if len(advocates) <= count:
        return advocates
    lead = advocates[-1]
    candidates = advocates[:-1]
    topic_words = set(re.findall(r"\w+", topic.lower()))

    def score_advocate(adv):
        text = (adv["name"] + " " + adv["role"] + " " + adv["system_instruction"]).lower()
        words = set(re.findall(r"\w+", text))
        return len(topic_words & words)

    sorted_candidates = sorted(candidates, key=score_advocate, reverse=True)
    selected = sorted_candidates[:count - 1]
    # Preserve original council order
    order_map = {id(a): i for i, a in enumerate(advocates)}
    final_selection = sorted(selected + [lead], key=lambda a: order_map[id(a)])
    return final_selection


def run_council_deliberation(
    client, 
    topic: str, 
    cartridge_id: str = "wildseed", 
    preferred_model: str = "gemini-3.8-flash",
    mode: str = "all"
) -> Dict[str, Any]:
    advocates, meta = get_council_for_cartridge(cartridge_id)
    canonical_cartridge = cartridge_id.lower().strip()

    if mode == "top5":
        advocates = select_top_advocates(advocates, topic, count=5)
        print(f"[MARD] Selected Top 5 Advocates for topic relevance: {[a['name'] for a in advocates]}")

    print(f"[MARD] Initializing Editorial Chamber for Cartridge [{canonical_cartridge.upper()}] with {len(advocates)} advocates on topic: '{topic}'")
    transcript = []
    running_context = f"Incoming Intelligence Ingress ({canonical_cartridge.upper()}):\n{topic}\n\nCouncil Deliberation Transcript:\n"

    for adv in advocates:
        prompt = (
            f"{running_context}\n"
            f"Now speaking: {adv['name']} ({adv['role']}).\n"
            f"Provide your domain-specific critique/input on this development:"
        )
        try:
            resp = generate_content_with_fallback(
                client=client,
                preferred_model=preferred_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=adv["system_instruction"],
                    temperature=0.3
                )
            )
            dialogue = resp.text.strip().replace('"', '')
        except Exception as e:
            dialogue = f"[Connection error during advocate deliberation: {e}]"

        now_str = datetime.datetime.now().strftime("%I:%M %p")
        transcript.append({
            "advocate": adv["name"],
            "role": adv["role"],
            "badgeColor": adv["badgeColor"],
            "timestamp": now_str,
            "dialogue": dialogue
        })
        running_context += f"- {adv['name']} ({now_str}): \"{dialogue}\"\n"
        print(f"  ✓ {adv['name']}: {dialogue[:60]}...")

    # Synthesis Phase: Generate the complete Essay structure
    synthesis_prompt = (
        f"Based on this topic and council deliberation:\n{running_context}\n\n"
        f"{meta['synthesis_instructions']}\n\n"
        f"Return strictly valid JSON with this schema:\n"
        f"{{\n"
        f'  "title": "Compelling Title",\n'
        f'  "topicBadge": "Short Upper Case Category",\n'
        f'  "readTime": "X MIN READ",\n'
        f'  "excerpt": "2-3 sentence punchy summary",\n'
        f'  "content": ["Paragraph 1", "Paragraph 2", "Paragraph 3", "Paragraph 4", "Paragraph 5"],\n'
        f'  "keyQuote": "Single memorable master quote representing the council"\n'
        f"}}"
    )

    try:
        resp_essay = generate_content_with_fallback(
            client=client,
            preferred_model=preferred_model,
            contents=synthesis_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )
        essay_data = json.loads(resp_essay.text)
    except Exception as e:
        print(f"  ⚠️ Synthesis JSON parse fallback triggered: {e}")
        essay_data = {
            "title": f"{meta['title_prefix']} on {topic[:30]}",
            "topicBadge": meta["fallback_badge"],
            "readTime": "5 MIN READ",
            "excerpt": topic,
            "content": meta["fallback_content"],
            "keyQuote": meta["fallback_quote"]
        }

    essay_data["cartridge"] = canonical_cartridge
    essay_data["councilDebate"] = transcript
    essay_data["author"] = meta["author"]
    essay_data["authorRole"] = meta["author_role"]
    essay_data["date"] = datetime.datetime.now().strftime("Harvest Cycle %Y.%m" if canonical_cartridge == "wildseed" else "%Y.%m")
    essay_data["postedDate"] = datetime.datetime.now().strftime("%B %d, %Y // TODAY").upper()
    essay_data["radarIngest"] = True
    essay_data["isHot"] = True

    return essay_data


def main():
    parser = argparse.ArgumentParser(description="MARD Editorial Council Chamber CLI")
    parser.add_argument("--topic", type=str, required=True, help="Topic or news excerpt to deliberate")
    parser.add_argument("--cartridge", type=str, default="wildseed", help="Domain cartridge (wildseed, builder, sports, enterprise, or CMDB room/tag)")
    parser.add_argument("--dry-run", action="store_true", help="Print result to stdout instead of staging ticket")
    parser.add_argument("--model", type=str, default="gemini-3.8-flash", help="Preferred Gemini model name (default: gemini-3.8-flash)")
    parser.add_argument("--mode", type=str, choices=["all", "top5"], default="all", help="Selection mode: 'all' (all 7 sequentially) or 'top5' (top 5 relevant advocates)")
    args = parser.parse_args()

    client = get_gemini_client()
    result = run_council_deliberation(client, args.topic, cartridge_id=args.cartridge, preferred_model=args.model, mode=args.mode)

    if args.dry_run:
        print("\n" + "="*50)
        print(f"MARD [{args.cartridge.upper()}] COUNCIL DELIBERATION RESULT (DRY RUN)")
        print("="*50)
        print(json.dumps(result, indent=2))
        return

    # Stage work order into incoming queue
    slug = result.get("title", "essay").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:30]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    incoming_dir = Path("/home/james/sovereign_inbox/queue/incoming")
    incoming_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write structured JSON
    wo_path_json = incoming_dir / f"WO_AUTO_ESSAY_{args.cartridge.lower()}_{ts}_{slug}.json"
    wo_path_json.write_text(json.dumps(result, indent=2))

    # 2. Write companion Markdown delivery
    wo_path_md = incoming_dir / f"WO_AUTO_ESSAY_{args.cartridge.lower()}_{ts}_{slug}.md"
    md_lines = [
        f"# {result.get('title', 'Council Deliberation')}",
        f"**Cartridge:** {result.get('cartridge', args.cartridge).upper()} | **Badge:** {result.get('topicBadge', 'INTEL')} | **Read Time:** {result.get('readTime', '5 MIN READ')}",
        f"**Author:** {result.get('author', 'Author')} ({result.get('authorRole', 'Role')})  ",
        f"**Date:** {result.get('postedDate', result.get('date', 'Today'))}  \n",
        f"> *\"{result.get('keyQuote', '')}\"*\n",
        "## Executive Excerpt",
        f"{result.get('excerpt', '')}\n",
        "## Synthesis Essay"
    ]
    for p in result.get("content", []):
        md_lines.append(f"{p}\n")
    md_lines.append("\n---\n\n## 🏛️ Council Deliberation Transcript\n")
    for turn in result.get("councilDebate", []):
        md_lines.append(f"### {turn.get('advocate')} — *{turn.get('role')}* ({turn.get('timestamp')})")
        md_lines.append(f"> {turn.get('dialogue')}\n")

    wo_path_md.write_text("\n".join(md_lines))
    print(f"\n[SUCCESS] Staged autonomous essay & council transcript to:\n  - JSON: {wo_path_json}\n  - MD:   {wo_path_md}")


if __name__ == "__main__":
    main()
