#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: TRUE COST HISTORICAL OBSERVATION SEEDER
# Script: /home/james/stacklabs/scripts/seed_truecost_history.py
# Ticket: WO-2026-0909-TRUECOST-ANOMALY-SHRINKFLATION-SENTINEL
# CI: 25_TrueCostStack
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def seed_history():
    print(f"🌱 Seeding historical price observations to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cur = conn.cursor()

    historical_records = [
        # 1. Historical 12oz Starbucks at Publix (prior to downsizing to 10oz)
        (
            "PROD-D5AEF109", "publix", "publix_smyrna_crossings", "2026-07-20T12:00:00Z",
            9.99, 9.99, "none", 0.8325, "circular_json",
            "Starbucks Pike Place Roast Medium Ground Coffee 12 oz Bag - Everyday Regular Price $9.99 ($0.8325/oz).",
            1, None, None
        ),
        # 2. Historical Kerrygold Butter at Publix (baseline regular shelf price was $4.29 before pseudo-sale hike to $5.49)
        (
            "PROD-2BE6BB5E", "publix", "publix_smyrna_crossings", "2026-07-15T12:00:00Z",
            4.29, 4.29, "none", 0.5363, "circular_json",
            "Kerrygold Pure Irish Butter 8 oz - Regular Price $4.29.",
            1, None, None
        ),
        (
            "PROD-2BE6BB5E", "publix", "publix_smyrna_crossings", "2026-08-01T12:00:00Z",
            4.29, 4.29, "none", 0.5363, "circular_json",
            "Kerrygold Pure Irish Butter 8 oz - Regular Price $4.29.",
            1, None, None
        ),
        # 3. Historical Publix Ground Chuck (baseline regular was $5.29 before markup to $6.49)
        (
            "PROD-FD64C17F", "publix", "publix_smyrna_crossings", "2026-07-25T12:00:00Z",
            5.29, 5.29, "none", 0.3306, "circular_json",
            "Publix Ground Chuck 80% Lean 1 lb Tray - Everyday Regular $5.29/lb.",
            1, None, None
        ),
        # 4. Gated Promo with purchasing restrictions (Basket Hostage + Ration Limit)
        (
            "PROD-1F6F4CB9", "kroger", "kroger_smyrna_441", "2026-08-28T12:00:00Z",
            5.99, 2.49, "mega_savings", 0.1383, "email_weekly_blast",
            "Honey Nut Cheerios Mega Savings: Must buy 5 participating items; Limit 2 rewards per customer; Requires minimum spend $25 basket spend; Digital Coupon required.",
            5, 2, 25.0
        ),
        # 5. Pseudo-sale Yo-Yo: Jack regular from $8.99 to $10.99, advertise "Sale $8.99"
        (
            "PROD-D5AEF109", "kroger", "kroger_smyrna_441", "2026-07-10T12:00:00Z",
            8.99, 8.99, "none", 0.7492, "email_weekly_blast",
            "Starbucks Pike Place Roast 12 oz - Regular Shelf Price $8.99.",
            1, None, None
        ),
        (
            "PROD-D5AEF109", "kroger", "kroger_smyrna_441", "2026-08-28T12:00:00Z",
            10.99, 8.99, "weekly_ad", 0.7492, "email_weekly_blast",
            "Starbucks Pike Place Roast 12 oz - Regular $10.99 on sale for $8.99! Limited time savings.",
            1, None, None
        )
    ]

    for rec in historical_records:
        # Check if already present to ensure idempotency
        cur.execute("""
            SELECT COUNT(*) FROM fact_price_history 
            WHERE product_id = ? AND store_chain = ? AND observed_timestamp = ?
        """, (rec[0], rec[1], rec[3]))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO fact_price_history (
                    product_id, store_chain, store_location_id, observed_timestamp,
                    regular_price, promo_price, promo_mechanism, computed_unit_price,
                    source_channel, raw_payload_snippet, min_purchase_qty, max_purchase_limit, basket_min_spend
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rec)
            print(f"  ✓ Inserted history for {rec[0]} at {rec[1]} ({rec[3]})")
        else:
            print(f"  - History already exists for {rec[0]} at {rec[1]} ({rec[3]})")

    conn.commit()
    conn.close()
    print("✨ Historical price seeding completed!")

if __name__ == "__main__":
    seed_history()
