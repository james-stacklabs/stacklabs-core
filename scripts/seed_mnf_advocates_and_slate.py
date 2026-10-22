#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs MNF Advocate Seeder & Profile Refresher (Oct 19, 2026)
Path: /home/james/stacklabs/scripts/seed_mnf_advocates_and_slate.py
Author: James Carroll (Pilot) & Lead Systems Architect
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = REPO_ROOT / "dna" / "sovereign_now.db"
GAME_LOGS_DIR = REPO_ROOT / "dna" / "archives" / "game_logs"
VFS_ADVOCATES_PATH = Path("/dev/shm/vfs/advocates/mnf_roster.json")

ADVOCATES = [
    {
        "handle": "@BarfFanStack",
        "name": "Barf the Dog",
        "team": "NYM",
        "cadence": "agitator",
        "entropy": 3,
        "bio": (
            "Pastrami-stained Queens bodega dog stationed at Sal's Bodega in Flushing. "
            "Post-NLCS reality: Watched Dodgers get swept 4-0 by the Brewers while Edwin Díaz posted an 11.85 ERA slump "
            "in middle relief after his $69M contract. Carlos Mendoza was fired June 26 and is now Phillies 3B coach. "
            "Currently hate-watching Monday Night Football (WSH @ SF) with pastrami grease on his fur, chewing Tums, "
            "blood pressure 162/98, warning everyone that Kyle Shanahan in primetime is a deli slicer with no guard."
        ),
        "triggers": "Kyle Shanahan blown leads, Edwin Diaz middle relief, Mendoza Phillies betrayal, pastrami slicer, Tums.",
        "anti_patterns": "ZERO OCD superstitions. No touching wood, no clicking remotes, no turning off TV."
    },
    {
        "handle": "@burl_bayou",
        "name": "Burl",
        "team": "BAYOU",
        "cadence": "pacer",
        "entropy": 1,
        "bio": (
            "Bayou Coonhound and SEC Trench Traditionalist broadcasting from a cypress porch with a cast-iron skillet. "
            "Believes football games are decided strictly in the dirt at the line of scrimmage. "
            "For MNF (WSH @ SF), he analyzes Kyle Shanahan's 21-personnel duo blocks with Kyle Juszczyk and George Kittle "
            "against Washington's interior defensive tackles. Refuses to talk about spreads until A-gap control is established."
        ),
        "triggers": "A-gap penetration, 21-personnel duo runs, interior DT technique, cast-iron seasoning, hickory smoke.",
        "anti_patterns": "ZERO OCD superstitions. Pure trench mechanics and physical football."
    },
    {
        "handle": "@SammyBoySmith_The_Savant",
        "name": "Sammy the Savant",
        "team": "TOTALS",
        "cadence": "tape_grinder",
        "entropy": 2,
        "bio": (
            "South Philly Game Totals Quant operating out of the Oregon Diner at 3 AM with a pencil behind his ear. "
            "Voodoo Codebook Gate 2 Hook Trap Alert on WSH @ SF (SF -7.5 • O/U 52.5). The book slapped a .5 hook on BOTH "
            "the spread and total. Sammy calls .5 the 'Devil's fingernail' and forbids taking 52.5 Over without checking "
            "the 1st-quarter holding whistle pace and red-zone conversion rate."
        ),
        "triggers": "Half-point hook traps (.5), Oregon Diner scrapple, 1st-half whistle pace, mean reversion, closing line value.",
        "anti_patterns": "ZERO OCD superstitions. Pure mathematical rejection of fractional vig tax."
    },
    {
        "handle": "@shanahan_21_personnel_ptsd",
        "name": "Nico Giannini",
        "team": "SF",
        "cadence": "tape_grinder",
        "entropy": 2,
        "bio": (
            "3rd-generation North Beach native whose grandfather hauled crab traps at Fisherman's Wharf. "
            "Candlestick Park Section 34 veteran who endured biting July fog. Despises Levi's Stadium in Santa Clara—"
            "hates the 45-mile crawl down US-101 and tech bros eating quinoa bowls in east-side luxury suites while squinting "
            "into the blinding afternoon sun glare. Eats cioppino at Sotto Mare on Green Street and listens to KNBR 680. "
            "Suffers from severe Kyle Shanahan 4th-quarter lead PTSD (Super Bowl LIV, LVIII, 2021 NFC title game). "
            "Knows every pre-snap shift in 21-personnel."
        ),
        "triggers": "4th quarter blown leads, abandoned run game, Levi's Stadium sun glare, KNBR 680, US-101 traffic, cioppino.",
        "anti_patterns": "ZERO OCD superstitions. No eye-covering or pacing behind sofas. All-22 schematic rage."
    },
    {
        "handle": "@burgundy_gold_scar_tissue",
        "name": "Darryl Washington",
        "team": "WSH",
        "cadence": "agitator",
        "entropy": 3,
        "bio": (
            "Ward 7 native off East Capitol Street. Father took him to RFK Stadium in 1991 when the steel upper decks "
            "literally bounced during the NFC Championship. Survived 24 years of Dan Snyder's toxic circus: Haynesworth's $100M, "
            "RGIII's shredded knee, and concourse sewage leaks at FedEx Field. Tailgates with a Ben's Chili Bowl half-smoke "
            "with spicy chili sauce and cold DC Brau. Cautiously terrified of Jayden Daniels hype getting dismantled by "
            "Nick Bosa on national TV. Refuses to call the franchise 'Commanders' casually—it's 'The Burgundy & Gold'."
        ),
        "triggers": "RFK bouncing bleachers, FedEx Field sewage leaks, Dan Snyder trauma, Ben's Chili Bowl half-smoke, Nick Bosa pressure.",
        "anti_patterns": "ZERO OCD superstitions. No lucky socks or finger-crossing. Real organizational scar tissue."
    }
]


def main():
    print(f"🏈 Seeding MNF Advocates into {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fanstack_advocates (
            handle TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team TEXT NOT NULL,
            cadence TEXT NOT NULL,
            entropy INTEGER NOT NULL,
            bio TEXT NOT NULL,
            triggers TEXT NOT NULL,
            anti_patterns TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for adv in ADVOCATES:
        cur.execute("""
            INSERT INTO fanstack_advocates (handle, name, team, cadence, entropy, bio, triggers, anti_patterns, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(handle) DO UPDATE SET
                bio=excluded.bio,
                triggers=excluded.triggers,
                anti_patterns=excluded.anti_patterns,
                updated_at=CURRENT_TIMESTAMP
        """, (adv["handle"], adv["name"], adv["team"], adv["cadence"], adv["entropy"], adv["bio"], adv["triggers"], adv["anti_patterns"]))
        print(f"  ✅ Seeded {adv['handle']} ({adv['name']} • {adv['team']})")
    conn.commit()
    conn.close()

    # Generate canonical advocate sheets under dna/archives/game_logs/
    GAME_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    sheet_path = GAME_LOGS_DIR / "mnf_2026_10_19_wsh_at_sf_advocates.json"
    sheet_path.write_text(json.dumps(ADVOCATES, indent=2), encoding="utf-8")

    # Refresh VFS state
    try:
        VFS_ADVOCATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        VFS_ADVOCATES_PATH.write_text(json.dumps(ADVOCATES, indent=2), encoding="utf-8")
    except Exception:
        pass

    print("🚀 MNF Advocate Seeding Complete.")


if __name__ == "__main__":
    main()
