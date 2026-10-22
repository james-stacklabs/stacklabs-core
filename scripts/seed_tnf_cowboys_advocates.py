#!/usr/bin/env python3
"""
Seed Dallas Cowboys Advocates into Emergent Society and Sovereign DNA
Path: /home/james/stacklabs/scripts/seed_tnf_cowboys_advocates.py
"""
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

STACKLABS_ROOT = Path("/home/james/stacklabs")
SOCIETY_DB = STACKLABS_ROOT / "data" / "emergent_society.db"
SOVEREIGN_DB = STACKLABS_ROOT / "dna" / "sovereign_now.db"

COWBOYS_ADVOCATES = [
    {
        "citizen_id": "CIT-011-TRIPP",
        "handle": "@the_star_luxury_apologist",
        "name": "Harrison 'Tripp' Vanderhoof III",
        "archetype": "Founders Suite Luxury Apologist",
        "fandom": "Dallas Cowboys",
        "avatar_url": "/avatars/the_star_luxury_apologist/the_star_luxury_apologist_avatar.png",
        "bio": "Country-club aristocrat tailgating from the climate-controlled founders suite at AT&T Stadium. Dismisses salary cap reality and boasts about Forbes franchise valuations.",
        "scars": "Deep psychological trauma from playoff exits; rationalizes them as statistical anomalies.",
        "trigger": "Peasant franchises with sub-billion valuations questioning Jerry's expenditures.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 128,
        "diastolic_bp": 82,
        "resting_hr": 74,
        "tums_inventory": 40,
        "scar_tissue_index": 0.72,
        "persona_id": "persona_the_star_luxury_apologist",
        "user_name": "the_star_luxury_apologist"
    },
    {
        "citizen_id": "CIT-012-COOP",
        "handle": "@curtain_conspiracy_dak",
        "name": "Caleb 'Coop' Cooper",
        "archetype": "All-22 Tape Grinder",
        "fandom": "Dallas Cowboys",
        "avatar_url": "/avatars/curtain_conspiracy_dak/curtain_conspiracy_dak_avatar.png",
        "bio": "Sleep-deprived Arlington film rat who watches games strictly through all-22 coaches tape. Transcribes pre-snap safety rotations and rants about west-window glare.",
        "scars": "2021 Wild Card clock runout and west-window sunset blindings.",
        "trigger": "Jerry refusing to hang curtains over the west glass windows.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 142,
        "diastolic_bp": 90,
        "resting_hr": 88,
        "tums_inventory": 75,
        "scar_tissue_index": 0.91,
        "persona_id": "persona_curtain_conspiracy_dak",
        "user_name": "curtain_conspiracy_dak"
    },
    {
        "citizen_id": "CIT-013-BIGTEX",
        "handle": "@valley_ranch_purist",
        "name": "Clint 'Big Tex' Calloway",
        "archetype": "90s Trench Purist",
        "fandom": "Dallas Cowboys",
        "avatar_url": "/avatars/valley_ranch_purist/valley_ranch_purist_avatar.png",
        "bio": "Weathered vintage 90s diehard in a frayed 1993 Super Bowl cap. Holds a 30-year grudge against Jerry for firing Jimmy Johnson in 1994, drinks Shiner Bock.",
        "scars": "March 29, 1994: The day Jerry fired Jimmy Johnson.",
        "trigger": "Soft modern finesse football, zone runs, and country-club suite chatter.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 138,
        "diastolic_bp": 88,
        "resting_hr": 80,
        "tums_inventory": 60,
        "scar_tissue_index": 0.95,
        "persona_id": "persona_valley_ranch_purist",
        "user_name": "valley_ranch_purist"
    }
]

CONTRACTS = [
    {
        "contract_id": "CNT-005-DAK-SACKS",
        "ticker": "$DAK-SACKS",
        "name": "Todd Bowles Blitz Packages Sack Dak Prescott 4+ Times",
        "creator": "CIT-012-COOP",
        "description": "Will Tampa Bay's exotic Cover-0 and A-gap pressure record 4 or more sacks on Dak Prescott tonight?",
        "target": "CIT-012-COOP",
        "price_cents": 50,
        "prob": 0.50
    },
    {
        "contract_id": "CNT-006-TRIPP-VAL",
        "ticker": "$TRIPP-VAL",
        "name": "Tripp Boasts About Forbes $10B AT&T Valuation Before Halftime",
        "creator": "CIT-011-TRIPP",
        "description": "Will Tripp invoke the Forbes $10 Billion franchise valuation on the live bleacher wire before Q2 ends?",
        "target": "CIT-011-TRIPP",
        "price_cents": 50,
        "prob": 0.50
    },
    {
        "contract_id": "CNT-007-COOP-GLARE",
        "ticker": "$COOP-GLARE",
        "name": "Coop Rants About West-Window Sunlight Glare During Red Zone Drive",
        "creator": "CIT-012-COOP",
        "description": "Will Coop post an all-caps rant about AT&T Stadium west-window glass glare impacting perimeter route stems?",
        "target": "CIT-012-COOP",
        "price_cents": 50,
        "prob": 0.50
    }
]

def seed_society():
    print(f"Connecting to Emergent Society DB: {SOCIETY_DB}")
    conn = sqlite3.connect(SOCIETY_DB)
    cur = conn.cursor()
    
    for a in COWBOYS_ADVOCATES:
        cur.execute("""
            INSERT INTO emergent_citizens (
                citizen_id, handle, name, archetype, fandom, avatar_url, bio, scars, trigger,
                cash_balance, portfolio_value, systolic_bp, diastolic_bp, resting_hr,
                cardiac_output, tums_inventory, tums_consumed_today, scar_tissue_index,
                status, superstition_level, last_active_ts, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?, 0, ?, 'WATCHING', 0.85, datetime('now'), datetime('now'))
            ON CONFLICT(citizen_id) DO UPDATE SET
                handle=excluded.handle,
                name=excluded.name,
                archetype=excluded.archetype,
                fandom=excluded.fandom,
                avatar_url=excluded.avatar_url,
                bio=excluded.bio,
                scars=excluded.scars,
                trigger=excluded.trigger,
                cash_balance=excluded.cash_balance,
                status='WATCHING';
        """, (
            a["citizen_id"], a["handle"], a["name"], a["archetype"], a["fandom"],
            a["avatar_url"], a["bio"], a["scars"], a["trigger"], a["cash_balance"],
            a["portfolio_value"], a["systolic_bp"], a["diastolic_bp"], a["resting_hr"],
            a["tums_inventory"], a["scar_tissue_index"]
        ))
        print(f"✔ [SOCIETY] Seeded {a['name']} ({a['handle']}) with ${a['cash_balance']:,.2f}")

    for c in CONTRACTS:
        cur.execute("""
            INSERT INTO market_contracts (
                contract_id, ticker, name, creator_citizen_id, description, target_citizen_id,
                current_probability, current_price_cents, total_volume, open_interest, status, resolution, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'OPEN', 'UNRESOLVED', datetime('now'))
            ON CONFLICT(contract_id) DO UPDATE SET
                ticker=excluded.ticker,
                name=excluded.name,
                status='OPEN';
        """, (
            c["contract_id"], c["ticker"], c["name"], c["creator"],
            c["description"], c["target"], c["prob"], c["price_cents"]
        ))
        print(f"✔ [MARKET] Seeded Contract {c['ticker']} ({c['name']})")

    conn.commit()
    conn.close()

def seed_sovereign_dna():
    print(f"Connecting to Sovereign DNA DB: {SOVEREIGN_DB}")
    conn = sqlite3.connect(SOVEREIGN_DB)
    cur = conn.cursor()

    active_rooms = ["20261008_TB_DAL", "401872980", "nfl_2026_w05_tb_dal", "TB_DAL"]

    for a in COWBOYS_ADVOCATES:
        # 1. Update fan_wallet
        cur.execute("""
            INSERT INTO fan_wallet (user_id, balance, lifetime_winnings, updated_at)
            VALUES (?, 1000, 0, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                balance = 1000,
                updated_at = CURRENT_TIMESTAMP;
        """, (a["user_name"],))
        print(f"✔ [WALLET] Seeded fan_wallet for {a['user_name']} -> 1,000 credits")

        # 2. Update cmdb_ci_persona
        cur.execute("""
            INSERT INTO cmdb_ci_persona (sys_id, handle, display_name, role, system_instruction, team, active, id, sys_created_on, sys_updated_on)
            VALUES (?, ?, ?, 'advocate', ?, 'DAL', 1, ?, datetime('now'), datetime('now'))
            ON CONFLICT(sys_id) DO UPDATE SET
                handle=excluded.handle,
                display_name=excluded.display_name,
                team='DAL',
                active=1,
                sys_updated_on=datetime('now');
        """, (a["persona_id"], a["handle"], a["name"], a["bio"], a["user_name"]))

        # 3. Seat into active game rooms (m2m_persona_room)
        for room_id in active_rooms:
            m2m_id = f"m2m_{a['user_name']}_{room_id}"
            cur.execute("""
                INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay, sys_created_on, sys_updated_on, active_pose_key)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), 'front_neutral')
                ON CONFLICT(sys_id) DO UPDATE SET
                    room=excluded.room,
                    sys_updated_on=datetime('now');
            """, (m2m_id, a["persona_id"], room_id, f"Active Room Seat: TNF Week 5 TB @ DAL ({room_id})"))
        print(f"✔ [SEATING] Seated {a['name']} into {len(active_rooms)} TNF game rooms")

    conn.commit()
    conn.close()

def main():
    print("=== SEEDING DALLAS COWBOYS ADVOCATES & TNF PREDICT EXCHANGE ===")
    seed_society()
    seed_sovereign_dna()
    print("=== SEEDING COMPLETE ===")

if __name__ == "__main__":
    main()
