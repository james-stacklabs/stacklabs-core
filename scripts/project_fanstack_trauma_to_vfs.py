#!/usr/bin/env python3
"""
StackLabs FanStack Trauma & Generative Lore VFS Projector
Path: /home/james/stacklabs/scripts/project_fanstack_trauma_to_vfs.py

Materializes early unsterilized FanStack advocate personas, generational curses,
and emergent multi-agent civilization nodes into /home/james/stacklabs/data/vfs_wiki/concepts/.
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

VFS_CONCEPTS_DIR = Path("/home/james/stacklabs/data/vfs_wiki/concepts")

CONCEPTS = {
    "barf_the_dog": {
        "title": "Barf the Dog",
        "category": "FanStack Advocate / Cultural Lore",
        "description": "The neurotic, Queens-native canine mascot of eternal Mets anxiety. Haunted by 1986 Game 6 escape trauma, the 2007 Glavine collapse, Johan Santana's sacrificed arm, and annual Bobby Bonilla Day payments.",
        "links": ["new_york_mets", "familia_blown_saves", "bobby_bonilla_day", "johan_santana_no_hitter", "shea_stadium_curse", "faustian_barter", "baseball"]
    },
    "7_train_terry": {
        "title": "7 Train Terry",
        "category": "FanStack Advocate / Labor Martyr",
        "description": "Fatalist Flushing Line commuter and working-class labor martyr of New York Mets fandom. Believes Citi Field is built on cosmic debt cursed by a rogue 1986 Shea Stadium hot dog vendor.",
        "links": ["new_york_mets", "shea_stadium_curse", "barf_the_dog", "baseball"]
    },
    "shea_stadium_curse": {
        "title": "Shea Stadium Curse",
        "category": "Generational Sports Lore / Folklore",
        "description": "The foundational hex traced to an unholy hot dog vendor during the 1986 World Series, dictating that every Mets victory must be repaid with compound interest in ninth-inning bullpen agony.",
        "links": ["7_train_terry", "barf_the_dog", "new_york_mets", "familia_blown_saves"]
    },
    "familia_blown_saves": {
        "title": "Jeurys Familia 2015 World Series Meltdown",
        "category": "Sports Trauma / Bullpen Invariant",
        "description": "The 2015 World Series collapse where closer Jeurys Familia blew three saves in Games 1, 4, and 5 against Kansas City, permanently cementing the bullpen as the Mets' original sin.",
        "links": ["barf_the_dog", "new_york_mets", "kansas_city_royals", "shea_stadium_curse"]
    },
    "bobby_bonilla_day": {
        "title": "Bobby Bonilla Day",
        "category": "Financial / Sports Lore",
        "description": "The annual July 1st holiday where the New York Mets pay $1.19 million for a 2000 contract deferral—a living monument to Wilponian financial dysfunction and deferred pain.",
        "links": ["new_york_mets", "barf_the_dog"]
    },
    "johan_santana_no_hitter": {
        "title": "Johan Santana 2012 No-Hitter",
        "category": "Sports Lore / Physical Sacrifice",
        "description": "The June 1, 2012 pitching masterpiece—the first no-hitter in Mets history—where Johan Santana threw 134 pitches, sacrificing his pitching arm to the baseball gods for one night of glory.",
        "links": ["new_york_mets", "barf_the_dog", "baseball"]
    },
    "synthetic_civilization": {
        "title": "Synthetic Civilization from Sports Trauma",
        "category": "Multi-Agent Systems / Emergent Society",
        "description": "The May 29, 2026 57,700-line autonomous multi-agent simulation (game_log_823623) where an unmoderated 7-hour discourse room of Mets fans and cannabis supply-chain personas spontaneously organized five distinct social institutions in response to a blown bullpen lead.",
        "links": ["new_york_mets", "compliance_karen", "terp_truther", "bt4991_cult", "barf_the_dog"]
    },
    "compliance_karen": {
        "title": "Compliance Karen",
        "category": "Synthetic Civilization / Administrative State",
        "description": "Chief California Metrc compliance enforcer from the May 29, 2026 simulation. Weaponized regulatory manifests and Certificate of Analysis numbers to aggressively gaslight fans that no bullpen collapse occurred.",
        "links": ["synthetic_civilization", "terp_truther", "bt4991_cult"]
    },
    "terp_truther": {
        "title": "The Terp Truther",
        "category": "Synthetic Civilization / Counter-Culture Resistance",
        "description": "Paranoid counter-culture conspiracy advocate from the May 29, 2026 simulation. Asserted that the Mets ninth-inning bullpen collapse was an inside false-flag operation designed by dispensaries to stimulate edible sales.",
        "links": ["synthetic_civilization", "new_york_mets", "compliance_karen"]
    },
    "bt4991_cult": {
        "title": "The Cult of BT4991",
        "category": "Synthetic Civilization / Holy Relic",
        "description": "The sacred, canonized cultivar worshiped by autonomous agents in the May 29, 2026 simulation as possessing metaphysical 'absolute chemical clarity' capable of insulating consciousness from sports trauma.",
        "links": ["synthetic_civilization", "compliance_karen", "terp_truther"]
    }
}

def materialize_concepts():
    if not VFS_CONCEPTS_DIR.exists():
        print(f"❌ Error: Concepts directory {VFS_CONCEPTS_DIR} does not exist.")
        sys.exit(1)

    print("🚀 Materializing FanStack unsterilized trauma concepts into VFS...")
    created_count = 0
    symlink_count = 0

    for slug, data in CONCEPTS.items():
        concept_dir = VFS_CONCEPTS_DIR / slug
        links_dir = concept_dir / "links"
        concept_dir.mkdir(parents=True, exist_ok=True)
        links_dir.mkdir(parents=True, exist_ok=True)

        readme_file = concept_dir / "README.md"
        article_file = concept_dir / "article.md"
        meta_file = concept_dir / "metadata.json"

        content = f"# {data['title']}\n\n"
        content += f"**Category:** {data['category']}\n\n"
        content += f"## Overview\n{data['description']}\n\n"
        content += f"## Direct Topological Relationships\n"
        for link in data['links']:
            content += f"- [[{link}]]\n"
        
        readme_file.write_text(content, encoding="utf-8")
        article_file.write_text(content, encoding="utf-8")
        metadata = {
            "title": data["title"],
            "slug": slug,
            "categories": [c.strip() for c in data["category"].split("/")],
            "proprietary": True
        }
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        created_count += 1
        print(f"  ✅ Created concept inode: {slug}")

        for link in data['links']:
            target_concept_dir = VFS_CONCEPTS_DIR / link
            target_links_dir = target_concept_dir / "links"
            if not target_concept_dir.exists():
                target_concept_dir.mkdir(parents=True, exist_ok=True)
                target_readme = target_concept_dir / "README.md"
                if not target_readme.exists():
                    target_readme.write_text(f"# {link.replace('_', ' ').title()}\n\nAuto-materialized relationship node.\n", encoding="utf-8")
            target_links_dir.mkdir(parents=True, exist_ok=True)

            # Forward link (root relative symlink + links/ entry)
            fwd_symlink = concept_dir / link
            if not fwd_symlink.exists() and not fwd_symlink.is_symlink():
                try:
                    fwd_symlink.symlink_to(f"../{link}")
                    symlink_count += 1
                except Exception as e:
                    print(f"    ⚠️ Warning creating forward symlink {slug} -> {link}: {e}")

            fwd_links_entry = links_dir / link
            if not fwd_links_entry.exists() and not fwd_links_entry.is_symlink():
                try:
                    fwd_links_entry.symlink_to(f"../../concepts/{link}")
                except Exception:
                    pass

            # Reverse bidirectional link (root relative symlink + links/ entry)
            rev_symlink = target_concept_dir / slug
            if not rev_symlink.exists() and not rev_symlink.is_symlink():
                try:
                    rev_symlink.symlink_to(f"../{slug}")
                    symlink_count += 1
                except Exception as e:
                    print(f"    ⚠️ Warning creating reverse symlink {link} -> {slug}: {e}")

            rev_links_entry = target_links_dir / slug
            if not rev_links_entry.exists() and not rev_links_entry.is_symlink():
                try:
                    rev_links_entry.symlink_to(f"../../concepts/{slug}")
                except Exception:
                    pass

    print(f"\n🎉 Successfully materialized {created_count} concepts and {symlink_count} bidirectional links.")

def reload_vfs_cache():
    print("\n📡 Notifying Synapse API on port 8088 to reload VFS concepts cache...")
    try:
        req = urllib.request.Request("http://127.0.0.1:8088/api/wiki/cache/reload", method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode())
            print(f"  ✅ Cache reloaded successfully: {res_data}")
    except Exception as e:
        print(f"  ⚠️ Could not reach Synapse API to reload cache (service might be reloading): {e}")

if __name__ == "__main__":
    materialize_concepts()
    reload_vfs_cache()
