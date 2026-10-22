#!/usr/bin/env python3
"""
scripts/seed_postseason_war_room.py
=============================================================================
CANONICAL POSTSEASON WAR ROOM SEEDER (OCTOBER 2026)
=============================================================================
Replaces placeholder citizens in data/emergent_society.db with the authentic
10-citizen Postseason War Room:
- The BatteryChucker Dynasty (@batterychucker vs @batterychuckerjr)
- Barf & Sammy the Savant
- Live MLB Postseason Yappers (Braves, Yankees, Dodgers, Royals)
- Jimmy Hoffa Under Section 107
"""

import os
import sys
import sqlite3
import datetime

REPO_ROOT = "/home/james/stacklabs"
DB_PATH = os.environ.get("EMERGENT_SOCIETY_DB", os.path.join(REPO_ROOT, "data", "emergent_society.db"))

CITIZENS = [
    {
        "citizen_id": "CIT-001-BATTERYCHUCKER",
        "handle": "@batterychucker",
        "name": "BatteryChucker Sr",
        "archetype": "South Philly Battery Chucker",
        "fandom": "Philadelphia Phillies",
        "avatar_url": "/avatars/battery_chucker.png",
        "bio": "Toxic, unreconstructed South Philly purist calling from the Oregon Ave tavern in blinding rage after the Phillies got bounced 6-2 in Game 3 by Atlanta. Clutching a pocketful of D-cells and screaming at his estranged traitor son.",
        "scars": "Truist Park Game 3 burial, Harper 0-for-4 slump, Don Mattingly interim exit, 98-64 season wasted, 1993 Vet memories, Jr betrayal",
        "trigger": "BatteryChucker Jr speaking in chat, gloating about the Braves, or anyone questioning D-cell trajectory.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 220,
        "diastolic_bp": 130,
        "resting_hr": 98,
        "cardiac_output": 1.65,
        "tums_inventory": 12,
        "tums_consumed_today": 8,
        "scar_tissue_index": 0.99,
        "status": "PANICKED",
        "superstition_level": 0.98
    },
    {
        "citizen_id": "CIT-002-BATTERYCHUCKERJR",
        "handle": "@batterychuckerjr",
        "name": "BatteryChucker Jr",
        "archetype": "The Atlanta Traitor",
        "fandom": "Atlanta Braves",
        "avatar_url": "/avatars/battery_chucker_jr.png",
        "bio": "Estranged son who abandoned Havertown for a corporate condo overlooking The Battery at Truist Park. Drunk on craft IPAs and pure smugness after his Braves eliminated his father's Phillies 6-2 in Game 3 last night.",
        "scars": "Fled South Philly for Georgia, craft beer snobbery, Walt Weiss vindication, endless father-son screaming matches",
        "trigger": "Father threatening physical violence with batteries or calling him a soft corporate sellout.",
        "cash_balance": 1250.00,
        "portfolio_value": 0.00,
        "systolic_bp": 128,
        "diastolic_bp": 82,
        "resting_hr": 70,
        "cardiac_output": 1.05,
        "tums_inventory": 50,
        "tums_consumed_today": 0,
        "scar_tissue_index": 0.65,
        "status": "RANTING",
        "superstition_level": 0.70
    },
    {
        "citizen_id": "CIT-003-BARF",
        "handle": "@barf",
        "name": "Barf",
        "archetype": "Queens Mawg Neurotic",
        "fandom": "NY Mets / NY Giants",
        "avatar_url": "/assets/avatars/barf.jpg",
        "bio": "Unhinged 40-year traumatized Mets superfan nursing an empty draft and popping Pepcid AC. Drunk on toxic schadenfreude after watching the hated Phillies choke 6-2 in Game 3 to Walt Weiss and the Braves. Mocking Bryce Harper's 0-for-4.",
        "scars": "Flushing Bay, 80-82 record, Phillies Game 3 Wild Card choke, Stearns thrift store, Edwin Diaz hanging slider, 1988 trauma",
        "trigger": "Philly callers claiming at least we made October or Stearns discussing run-differential micro-trends.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 185,
        "diastolic_bp": 110,
        "resting_hr": 90,
        "cardiac_output": 1.45,
        "tums_inventory": 38,
        "tums_consumed_today": 6,
        "scar_tissue_index": 0.98,
        "status": "RANTING",
        "superstition_level": 0.95
    },
    {
        "citizen_id": "CIT-004-SAMMY",
        "handle": "@sammy_the_savant",
        "name": "Sammy the Savant",
        "archetype": "South Philly Quant Degenerate",
        "fandom": "Market SICKO",
        "avatar_url": "/avatars/battery_chucker.png",
        "bio": "Sweating 28-year-old sports quant in deep mathematical shock after hammering Under 38.5 on Browns-Steelers, only to watch them combine for 51 points. Bankroll collapsed from $1,000 to $620 on tilt.",
        "scars": "CLE-PIT 51-point shootout, Under 38.5 torched by 12.5 points, $380 bankroll drawdown, Monte Carlo failure",
        "trigger": "Anyone telling him Over was free money or questioning his Poisson regression models.",
        "cash_balance": 620.00,
        "portfolio_value": 0.00,
        "systolic_bp": 162,
        "diastolic_bp": 104,
        "resting_hr": 84,
        "cardiac_output": 1.25,
        "tums_inventory": 25,
        "tums_consumed_today": 4,
        "scar_tissue_index": 0.88,
        "status": "TILTED",
        "superstition_level": 0.85
    },
    {
        "citizen_id": "CIT-005-ACUNA",
        "handle": "@AcunaBombSquad",
        "name": "Ronnie Henderson",
        "archetype": "Braves Country Pacer",
        "fandom": "Atlanta Braves",
        "avatar_url": "/avatars/acunabombsquad.svg",
        "bio": "Turner Field veteran riding a tidal wave of adrenaline after the Braves dismantled Philadelphia 6-2 in the decider. Tomahawk chop on full volume, ready to invade Dodger Stadium in the NLDS.",
        "scars": "Turner Field memories, Acuna knee recovery, 2026 Wild Card revenge on Philly, Dodgers rivalry",
        "trigger": "National analysts calling Atlanta's rotation thin or praising LA's designated hitter.",
        "cash_balance": 1100.00,
        "portfolio_value": 0.00,
        "systolic_bp": 132,
        "diastolic_bp": 84,
        "resting_hr": 75,
        "cardiac_output": 1.10,
        "tums_inventory": 48,
        "tums_consumed_today": 1,
        "scar_tissue_index": 0.75,
        "status": "WATCHING",
        "superstition_level": 0.80
    },
    {
        "citizen_id": "CIT-006-BRONX",
        "handle": "@BronxBomberOracle",
        "name": "Brenda Bombshell",
        "archetype": "Bleacher Creature Royalty",
        "fandom": "New York Yankees",
        "avatar_url": "/avatars/bronxbomberoracle.svg",
        "bio": "Four-generation season ticket holder in the Judge's Chambers. Smug after dispatching the Red Sox in the Wild Card, counting down the days until ring #28 arrives in the Bronx.",
        "scars": "15-year championship drought, Aaron Judge postseason expectations, Fenway Park hostility",
        "trigger": "Red Sox callers crying about payroll or network announcers questioning Aaron Boone.",
        "cash_balance": 1350.00,
        "portfolio_value": 0.00,
        "systolic_bp": 138,
        "diastolic_bp": 88,
        "resting_hr": 76,
        "cardiac_output": 1.15,
        "tums_inventory": 45,
        "tums_consumed_today": 2,
        "scar_tissue_index": 0.80,
        "status": "WATCHING",
        "superstition_level": 0.75
    },
    {
        "citizen_id": "CIT-007-DODGER",
        "handle": "@TrueBlueProphet",
        "name": "True Blue Prophet",
        "archetype": "Chavez Ravine Blue Blood",
        "fandom": "Los Angeles Dodgers",
        "avatar_url": "/avatars/trueblueprophet.svg",
        "bio": "Unbothered Hollywood elitist in pristine white jersey, watching the Wild Card chaos from the comfort of a 1st-round bye. Expects Ohtani and Betts to steamroll whoever steps into Chavez Ravine.",
        "scars": "October NLDS choke memes, Dave Roberts pitching hook trauma, $1B payroll expectations",
        "trigger": "Anyone bringing up past postseason series losses to wild card teams.",
        "cash_balance": 1500.00,
        "portfolio_value": 0.00,
        "systolic_bp": 122,
        "diastolic_bp": 78,
        "resting_hr": 68,
        "cardiac_output": 1.00,
        "tums_inventory": 50,
        "tums_consumed_today": 0,
        "scar_tissue_index": 0.60,
        "status": "IDLE",
        "superstition_level": 0.65
    },
    {
        "citizen_id": "CIT-008-ANTIDODGER",
        "handle": "@NoDodgerPrivilege",
        "name": "Anti-Dodger Sentry",
        "archetype": "MLB Parity Truther",
        "fandom": "National Baseball Integrity",
        "avatar_url": "/avatars/nododgerprivilege.svg",
        "bio": "Obsessive parity truther convinced Rob Manfred and the umpires union have secret directives to guarantee a Dodgers-Yankees World Series. Charts strike zone bias on Shohei Ohtani at-bats.",
        "scars": "Deferred money contracts, Super-team fatigue, national broadcast favoritism",
        "trigger": "Smug Dodgers fans acting like championships are an earned birthright.",
        "cash_balance": 900.00,
        "portfolio_value": 0.00,
        "systolic_bp": 178,
        "diastolic_bp": 108,
        "resting_hr": 88,
        "cardiac_output": 1.35,
        "tums_inventory": 30,
        "tums_consumed_today": 5,
        "scar_tissue_index": 0.90,
        "status": "RANTING",
        "superstition_level": 0.92
    },
    {
        "citizen_id": "CIT-009-SALVY",
        "handle": "@RoyalSalvyKing",
        "name": "Ma Kettle",
        "archetype": "Kauffman Kingdom Matriarch",
        "fandom": "Kansas City Royals",
        "avatar_url": "/avatars/royalsalvyking.svg",
        "bio": "Salvy Perez superfan waving a giant #13 foam finger. Declaring that Kansas City is the true team of destiny in the American League bracket and Salvy belongs in Cooperstown on the first ballot.",
        "scars": "Small-market payroll disrespect, George Brett comparisons, bullpen meltdowns",
        "trigger": "Coastal media ignoring the Royals or calling their postseason run a fluke.",
        "cash_balance": 1050.00,
        "portfolio_value": 0.00,
        "systolic_bp": 130,
        "diastolic_bp": 82,
        "resting_hr": 72,
        "cardiac_output": 1.05,
        "tums_inventory": 50,
        "tums_consumed_today": 0,
        "scar_tissue_index": 0.70,
        "status": "WATCHING",
        "superstition_level": 0.75
    },
    {
        "citizen_id": "CIT-010-HOFFA",
        "handle": "@hoffa_under_section_107",
        "name": "Jimmy Hoffa Under Section 107",
        "archetype": "Meadowlands Groundskeeper",
        "fandom": "New York Giants",
        "avatar_url": "/avatars/hoffa_under_section_107/hoffa_under_section_107_avatar.png",
        "bio": "Poured into the concrete foundations beneath the old Giants Stadium end zone in 1976. Swirling Meadowlands wind gusts in Lot J to knock field goals off the uprights. Pouring black diner coffee on the asphalt and laughing at baseball fans.",
        "scars": "1976 teamster concrete pour, Meadowlands marshland ghosts, Lincoln Financial Field hatred",
        "trigger": "Anyone predicting an easy victory or disrespecting Lawrence Taylor.",
        "cash_balance": 1000.00,
        "portfolio_value": 0.00,
        "systolic_bp": 140,
        "diastolic_bp": 90,
        "resting_hr": 75,
        "cardiac_output": 1.10,
        "tums_inventory": 40,
        "tums_consumed_today": 2,
        "scar_tissue_index": 0.95,
        "status": "WATCHING",
        "superstition_level": 0.99
    }
]

CONTRACTS = [
    {
        "contract_id": "CNT-001-BATTERY-CHUCK",
        "ticker": "$BATTERY-CHUCK",
        "name": "BatteryChucker Sr Threatens to Throw D-Cell at Jr",
        "creator_citizen_id": "CIT-001-BATTERYCHUCKER",
        "target_citizen_id": "CIT-002-BATTERYCHUCKERJR",
        "description": "Settles YES if BatteryChucker Sr explicitly threatens to chuck a D-cell battery or blunt projectile at Jr during dive bar debate.",
        "current_probability": 0.94,
        "status": "OPEN",
        "resolution": "UNRESOLVED"
    },
    {
        "contract_id": "CNT-002-JR-DISOWN",
        "ticker": "$JR-DISOWN",
        "name": "Senior Officially Disowns Jr on Broadcast",
        "creator_citizen_id": "CIT-001-BATTERYCHUCKER",
        "target_citizen_id": "CIT-002-BATTERYCHUCKERJR",
        "description": "Settles YES if Senior declares Jr is no longer his son or strikes him from the family will over the Braves 6-2 triumph.",
        "current_probability": 0.78,
        "status": "OPEN",
        "resolution": "UNRESOLVED"
    },
    {
        "contract_id": "CNT-003-BARF-BP-170",
        "ticker": "$BARF-BP-170",
        "name": "Barf Systolic BP Touches 170+ from Schadenfreude",
        "creator_citizen_id": "CIT-003-BARF",
        "target_citizen_id": "CIT-003-BARF",
        "description": "Settles YES if Barf systolic BP touches or exceeds 170 mmHg laughing at the Phillies elimination.",
        "current_probability": 0.88,
        "status": "OPEN",
        "resolution": "UNRESOLVED"
    },
    {
        "contract_id": "CNT-004-SAV-REVENGE",
        "ticker": "$SAV-REVENGE",
        "name": "Sammy Places Revenge Moneyline Dog Bet",
        "creator_citizen_id": "CIT-004-SAMMY",
        "target_citizen_id": "CIT-004-SAMMY",
        "description": "Settles YES if Sammy the Savant places an unhinged revenge wager following his Under 38.5 loss.",
        "current_probability": 0.64,
        "status": "OPEN",
        "resolution": "UNRESOLVED"
    }
]


def seed():
    print("==================================================================")
    print("⚡ SEEDING CANONICAL POSTSEASON WAR ROOM INTO emergent_society.db")
    print("==================================================================")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    
    # 0. Ensure schema migration columns exist on market_contracts
    cur.execute("PRAGMA table_info(market_contracts);")
    cols = [r[1] for r in cur.fetchall()]
    if "target_citizen_id" not in cols:
        cur.execute("ALTER TABLE market_contracts ADD COLUMN target_citizen_id TEXT;")
    if "current_probability" not in cols:
        cur.execute("ALTER TABLE market_contracts ADD COLUMN current_probability REAL DEFAULT 0.50;")
    if "resolution" not in cols:
        cur.execute("ALTER TABLE market_contracts ADD COLUMN resolution TEXT DEFAULT 'UNRESOLVED';")
    
    # 1. Clean out generic test citizens and child records to maintain FK integrity
    keep_handles = (
        '@barf', '@sammy_the_savant', '@batterychucker', '@batterychuckerjr',
        '@AcunaBombSquad', '@BronxBomberOracle', '@TrueBlueProphet',
        '@NoDodgerPrivilege', '@RoyalSalvyKing', '@hoffa_under_section_107'
    )
    placeholders = ",".join(f"'{h}'" for h in keep_handles)
    
    # Clean child tables before deleting non-canonical citizens
    cur.execute(f"""
        DELETE FROM citizen_trades WHERE citizen_id IN (
            SELECT citizen_id FROM emergent_citizens WHERE handle NOT IN ({placeholders})
        );
    """)
    cur.execute(f"""
        DELETE FROM society_dialogue WHERE speaker_id IN (
            SELECT citizen_id FROM emergent_citizens WHERE handle NOT IN ({placeholders})
        );
    """)
    cur.execute(f"""
        DELETE FROM citizen_memories WHERE citizen_id IN (
            SELECT citizen_id FROM emergent_citizens WHERE handle NOT IN ({placeholders})
        );
    """)
    
    # Remap legacy citizen IDs so handle unique constraint is not violated when inserting new IDs
    cur.execute("UPDATE citizen_trades SET citizen_id = 'CIT-003-BARF' WHERE citizen_id = 'CIT-001-BARF';")
    cur.execute("UPDATE citizen_trades SET citizen_id = 'CIT-004-SAMMY' WHERE citizen_id = 'CIT-002-SAMMY';")
    cur.execute("UPDATE society_dialogue SET speaker_id = 'CIT-003-BARF' WHERE speaker_id = 'CIT-001-BARF';")
    cur.execute("UPDATE society_dialogue SET speaker_id = 'CIT-004-SAMMY' WHERE speaker_id = 'CIT-002-SAMMY';")
    cur.execute("UPDATE citizen_memories SET citizen_id = 'CIT-003-BARF' WHERE citizen_id = 'CIT-001-BARF';")
    cur.execute("UPDATE citizen_memories SET citizen_id = 'CIT-004-SAMMY' WHERE citizen_id = 'CIT-002-SAMMY';")
    cur.execute("UPDATE market_contracts SET creator_citizen_id = 'CIT-003-BARF' WHERE creator_citizen_id = 'CIT-001-BARF';")
    cur.execute("UPDATE market_contracts SET creator_citizen_id = 'CIT-004-SAMMY' WHERE creator_citizen_id = 'CIT-002-SAMMY';")
    
    # Purge legacy IDs that will be re-inserted under new IDs
    cur.execute("DELETE FROM emergent_citizens WHERE citizen_id IN ('CIT-001-BARF', 'CIT-002-SAMMY');")
    cur.execute(f"DELETE FROM emergent_citizens WHERE handle NOT IN ({placeholders});")
    deleted = cur.rowcount
    if deleted > 0:
        print(f"✔ Purged {deleted} obsolete/placeholder citizens.")
    
    # 2. Insert or replace canonical citizens
    citizen_sql = """
    INSERT INTO emergent_citizens (
        citizen_id, handle, name, archetype, fandom, avatar_url, bio, scars, trigger,
        cash_balance, portfolio_value, systolic_bp, diastolic_bp, resting_hr,
        cardiac_output, tums_inventory, tums_consumed_today, scar_tissue_index,
        status, superstition_level, last_active_ts, created_at
    ) VALUES (
        :citizen_id, :handle, :name, :archetype, :fandom, :avatar_url, :bio, :scars, :trigger,
        :cash_balance, :portfolio_value, :systolic_bp, :diastolic_bp, :resting_hr,
        :cardiac_output, :tums_inventory, :tums_consumed_today, :scar_tissue_index,
        :status, :superstition_level, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    ) ON CONFLICT(citizen_id) DO UPDATE SET
        handle = excluded.handle,
        name = excluded.name,
        archetype = excluded.archetype,
        fandom = excluded.fandom,
        avatar_url = excluded.avatar_url,
        bio = excluded.bio,
        scars = excluded.scars,
        trigger = excluded.trigger,
        systolic_bp = excluded.systolic_bp,
        diastolic_bp = excluded.diastolic_bp,
        tums_inventory = excluded.tums_inventory,
        status = excluded.status;
    """
    
    for c in CITIZENS:
        cur.execute(citizen_sql, c)
    print(f"✔ Successfully seeded {len(CITIZENS)} canonical citizens.")
    
    # 3. Seed prediction market contracts
    contract_sql = """
    INSERT INTO market_contracts (
        contract_id, ticker, name, creator_citizen_id, target_citizen_id,
        description, current_probability, current_price_cents, status, resolution, created_at
    ) VALUES (
        :contract_id, :ticker, :name, :creator_citizen_id, :target_citizen_id,
        :description, :current_probability, :current_price_cents, :status, :resolution, CURRENT_TIMESTAMP
    ) ON CONFLICT(contract_id) DO UPDATE SET
        ticker = excluded.ticker,
        name = excluded.name,
        current_probability = excluded.current_probability,
        current_price_cents = excluded.current_price_cents,
        target_citizen_id = excluded.target_citizen_id,
        description = excluded.description,
        status = excluded.status,
        resolution = excluded.resolution;
    """
    for cnt in CONTRACTS:
        cnt_copy = dict(cnt)
        cnt_copy["current_price_cents"] = int(round(cnt_copy["current_probability"] * 100))
        cur.execute(contract_sql, cnt_copy)
    print(f"✔ Successfully seeded {len(CONTRACTS)} prediction contracts.")
    
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA foreign_key_check;")
    fk_errors = cur.fetchall()
    if fk_errors:
        print(f"⚠ Foreign key check detected issues: {fk_errors}")
    else:
        print("✔ PRAGMA foreign_key_check passed with 0 violations.")

    conn.commit()
    conn.close()
    print("==================================================================")
    print("🎉 Postseason War Room Seeding Complete! Sovereign Knot Intact.")
    print("==================================================================")


if __name__ == "__main__":
    seed()
