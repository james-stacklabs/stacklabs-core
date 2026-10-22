#!/usr/bin/env python3
"""
StackLabs Proprietary Intelligence VFS Projector
Path: /home/james/stacklabs/scripts/project_proprietary_intelligence_to_vfs.py

Materializes proprietary sports stream lore, allocator networks, and physical infrastructure
into first-class POSIX concept inodes within /home/james/stacklabs/data/vfs_wiki/concepts/.
"""
import os
import sys
import json
import shutil
import urllib.request
from pathlib import Path

CONCEPTS_DIR = Path("/home/james/stacklabs/data/vfs_wiki/concepts")

PROPRIETARY_NODES = [
    {
        "slug": "faustian_barter",
        "title": "Faustian Barter",
        "categories": ["Wisconsin Fan Lore", "Sports Psychology", "October 2026 NLDS"],
        "article": """# Faustian Barter

A **Faustian Barter** in sports phenomenology is the psychological mechanism where a passionate multi-sport fanbase consciously bargains away regular-season success in one sport to secure postseason advancement in another.

### The October 2026 Wisconsin Convergence
During the 2026 National League Division Series (NLDS), Cheesehead TV live chat captured raw existential bargaining from Wisconsin fans tracking both the Green Bay Packers regular season and the 103-win Milwaukee Brewers postseason run:

> *"I’m torn. I bargained a Packer loss for a Brewers win."*  
> — **@MSANDMIKE**, *Cheesehead TV Live Stream (October 2026)*

### Mechanism & Market Impact
This sentiment creates an emotional hedge where defeat in a secondary sport is rationalized as a necessary spiritual sacrifice, muting negative fan sentiment and driving irrational sports betting spreads across Wisconsin sportsbooks.
""",
        "links": ["green_bay_packers", "milwaukee_brewers", "baseball"]
    },
    {
        "slug": "jackson_chourio",
        "title": "Jackson Chourio",
        "categories": ["Milwaukee Brewers", "MLB Players", "October 2026 Postseason"],
        "article": """# Jackson Chourio

**Jackson Chourio** is a Venezuelan professional baseball outfielder for the **Milwaukee Brewers**.

### 2026 NLDS Heroics
In Game 1 of the 2026 NLDS, Chourio faced closer Mason Miller firing 104.2 mph high fastballs. In a historic plate appearance, Chourio generated an 82 mph bat speed to turn around triple-digit heat, lacing a walk-off 2-run single into right-center field to secure the Brewers' opening postseason victory.
""",
        "links": ["milwaukee_brewers", "mason_miller", "baseball", "faustian_barter"]
    },
    {
        "slug": "mason_miller",
        "title": "Mason Miller",
        "categories": ["MLB Players", "Relief Pitchers", "Triple Digit Velocity"],
        "article": """# Mason Miller

**Mason Miller** is an American professional baseball pitcher renowned for elite fastball velocity averaging 101–104 mph.
""",
        "links": ["jackson_chourio", "baseball"]
    },
    {
        "slug": "sabine_pass",
        "title": "Sabine Pass",
        "categories": ["LNG Export Terminals", "Physical Infrastructure", "Gulf Coast Energy"],
        "article": """# Sabine Pass

**Sabine Pass** is the flagship liquefied natural gas (LNG) export terminal located on the Sabine-Neches Waterway at the border of Texas and Louisiana, serving as a primary physical demand sink for US Gulf Coast natural gas flows.
""",
        "links": ["horizon_edge", "natural_gas"]
    },
    {
        "slug": "henry_hub",
        "title": "Henry Hub",
        "categories": ["Natural Gas Pricing", "Physical Infrastructure", "Erath Louisiana"],
        "article": """# Henry Hub

**Henry Hub** is a natural gas distribution hub in Erath, Louisiana, that serves as the official delivery location and pricing benchmark for NYMEX natural gas futures contracts.
""",
        "links": ["pawel_rudnicki", "horizon_edge", "natural_gas"]
    },
    {
        "slug": "stacklabs",
        "title": "StackLabs",
        "categories": ["Enterprise Software", "Systems Architecture", "Smyrna Georgia"],
        "article": """# StackLabs

**StackLabs LLC** is an enterprise software company founded by solo systems architect **James Carroll**, building low-latency deterministic execution engines, in-memory POSIX VFS knowledge graphs, and market microstructure telemetry platforms.
""",
        "links": ["james_carroll", "horizon_edge"]
    },
    {
        "slug": "pawel_rudnicki",
        "title": "Pawel Rudnicki",
        "categories": ["Lead Syndicate Allocator", "Energy Microstructure", "StackLabs Allocators"],
        "article": """# Pawel Rudnicki

**Pawel Rudnicki** is an institutional investor, energy trader, and lead syndicate allocator based in Dallas/Fort Worth, Texas.

### Commercial Engagement with StackLabs
* **Syndicate Role**: Private Investor & Syndicate Lead closing $125k SAFE with StackLabs LLC.
* **Domain Focus**: Physical energy commodity flows, natural gas basis trading, and low-latency infrastructure telemetry.
* **Flagship Project**: **Horizon Edge** — an air-gapped terminal monitoring physical pipeline compressor stations and LNG export terminals.
""",
        "links": ["horizon_edge", "james_carroll", "henry_hub"]
    },
    {
        "slug": "horizon_edge",
        "title": "Horizon Edge",
        "categories": ["Enterprise Software", "Physical Infrastructure", "Energy Trading"],
        "article": """# Horizon Edge

**Horizon Edge** is an enterprise market microstructure platform architected by StackLabs for institutional commodity allocators.

### Core Architecture
* Sub-50ms deterministic physical telemetry.
* Real-time monitoring of FERC regulatory filings, interstate natural gas pipeline flow meters, and Sabine Pass LNG liquefaction trains.
""",
        "links": ["pawel_rudnicki", "sabine_pass", "henry_hub", "natural_gas"]
    },
    {
        "slug": "james_carroll",
        "title": "James Carroll",
        "categories": ["Systems Architecture", "StackLabs Founders"],
        "article": """# James Carroll

**James Carroll** is a solo systems architect and founder of **StackLabs LLC** based in Smyrna, Georgia. Creator of the Swanson Collider and POSIX VFS in-memory knowledge engine.
""",
        "links": ["stacklabs", "pawel_rudnicki", "jeremy_malone"]
    },
    {
        "slug": "jeremy_malone",
        "title": "Jeremy Malone",
        "categories": ["Davidson Homes", "Residential Real Estate", "Middle Tennessee"],
        "article": """# Jeremy Malone

**Jeremy Malone** is Sales Director and Principal Listing Agent for Davidson Homes (Middle Tennessee Division).

### Relationship Ground Truth
30-year brotherly bond with James Carroll dating back to age 15 in Germantown, Tennessee, playing together on the 'Bad News Bears' reject baseball team coached by Eileen Carroll.
""",
        "links": ["davidson_homes", "james_carroll", "baseball"]
    },
    {
        "slug": "davidson_homes",
        "title": "Davidson Homes",
        "categories": ["Homebuilders", "Middle Tennessee", "Construction"],
        "article": """# Davidson Homes

**Davidson Homes** is a prominent residential homebuilder delivering single-family communities across Middle Tennessee and the American Southeast.
""",
        "links": ["jeremy_malone", "construction"]
    }
]

def project_nodes():
    print(f"🏛️ Projecting {len(PROPRIETARY_NODES)} proprietary concept nodes into VFS...")
    
    # First pass: ensure all node directories exist so reciprocal links always resolve
    for item in PROPRIETARY_NODES:
        slug = item["slug"]
        node_dir = CONCEPTS_DIR / slug
        links_dir = node_dir / "links"
        node_dir.mkdir(parents=True, exist_ok=True)
        links_dir.mkdir(parents=True, exist_ok=True)

    # Remove any stale direct links that bypass horizon_edge
    stale_links = [
        CONCEPTS_DIR / "pawel_rudnicki" / "links" / "sabine_pass",
        CONCEPTS_DIR / "sabine_pass" / "links" / "pawel_rudnicki",
        CONCEPTS_DIR / "henry_hub" / "links" / "sabine_pass",
        CONCEPTS_DIR / "sabine_pass" / "links" / "henry_hub",
    ]
    for p in stale_links:
        if p.exists() or p.is_symlink():
            try:
                p.unlink()
            except OSError:
                pass

    for item in PROPRIETARY_NODES:
        slug = item["slug"]
        node_dir = CONCEPTS_DIR / slug
        links_dir = node_dir / "links"
        
        # 1. Write article.md
        article_file = node_dir / "article.md"
        article_file.write_text(item["article"].strip() + "\n", encoding="utf-8")
        
        # 2. Write metadata.json
        meta_file = node_dir / "metadata.json"
        metadata = {
            "title": item["title"],
            "slug": slug,
            "categories": item["categories"],
            "proprietary": True
        }
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        
        # 3. Touch outgoing links
        for target_slug in item["links"]:
            # Link from this node to target
            target_link = links_dir / target_slug
            if not target_link.exists() and not target_link.is_symlink():
                try:
                    target_link.touch()
                except OSError:
                    pass
            
            # Reciprocal link back from target to this node (if target concept exists)
            tgt_node_dir = CONCEPTS_DIR / target_slug
            if tgt_node_dir.is_dir():
                tgt_links_dir = tgt_node_dir / "links"
                tgt_links_dir.mkdir(parents=True, exist_ok=True)
                recip = tgt_links_dir / slug
                if not recip.exists() and not recip.is_symlink():
                    try:
                        recip.touch()
                    except OSError:
                        pass
        
        print(f"  ✔ Projected node: {slug} ({len(item['links'])} bidirectional links)")

    # 4. Trigger in-memory cache reload on Port 8088
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8088/api/wiki/cache/reload",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            print(f"🔄 Reloaded in-memory cache on Port 8088: {data}")
    except Exception as e:
        print(f"⚠ Could not trigger API cache reload (synapse bus might be offline): {e}")

if __name__ == "__main__":
    project_nodes()
