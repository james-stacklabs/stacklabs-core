#!/usr/bin/env python3
# ==============================================================================
# SOVEREIGN OS: TRUE COST PRICE ANOMALY SCHEMA MIGRATION RUNNER
# Script: /home/james/stacklabs/scripts/apply_truecost_anomaly_migration.py
# Ticket: WO-2026-0909-TRUECOST-ANOMALY-SHRINKFLATION-SENTINEL
# CI: 25_TrueCostStack
# ==============================================================================
import sqlite3
import os
import sys

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MIGRATION_FILE = "/home/james/stacklabs/dna/migrations/055__CREATE_TRUECOST_PRICE_ANOMALY_LEDGER.sql"
EXECUTED_DIR = "/home/james/stacklabs/dna/migrations/executed"

def apply_migration():
    print(f"🚀 [SCHEMA MIGRATION] Applying {MIGRATION_FILE} to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    cur = conn.cursor()

    # 1. Create table fact_price_anomaly_log if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fact_price_anomaly_log (
        anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        upc_barcode TEXT NOT NULL,
        store_chain TEXT NOT NULL,
        anomaly_type TEXT CHECK(anomaly_type IN ('SHRINKFLATION', 'PSEUDO_SALE', 'BASKET_HOSTAGE', 'RATION_LIMIT')),
        severity TEXT CHECK(severity IN ('HIGH', 'MEDIUM', 'INFO')) DEFAULT 'MEDIUM',
        baseline_package_size REAL,
        observed_package_size REAL,
        baseline_unit_price REAL,
        observed_unit_price REAL,
        inflation_pct REAL,
        promo_restriction_summary TEXT,
        audit_notes TEXT NOT NULL,
        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
    );
    """)
    print("  ✓ Ensured table fact_price_anomaly_log exists.")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_prod ON fact_price_anomaly_log(product_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_type ON fact_price_anomaly_log(anomaly_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_detected ON fact_price_anomaly_log(detected_at);")
    print("  ✓ Ensured anomaly indices exist.")

    # 2. Add columns to dim_product idempotently
    dim_cols = [c[1] for c in cur.execute("PRAGMA table_info(dim_product);").fetchall()]
    if "original_package_quantity" not in dim_cols:
        cur.execute("ALTER TABLE dim_product ADD COLUMN original_package_quantity REAL;")
        print("  ✓ Added column original_package_quantity to dim_product.")
    else:
        print("  - Column original_package_quantity already present in dim_product.")

    if "size_reduction_flag" not in dim_cols:
        cur.execute("ALTER TABLE dim_product ADD COLUMN size_reduction_flag BOOLEAN NOT NULL DEFAULT 0;")
        print("  ✓ Added column size_reduction_flag to dim_product.")
    else:
        print("  - Column size_reduction_flag already present in dim_product.")

    # 3. Add columns to fact_price_history idempotently
    hist_cols = [c[1] for c in cur.execute("PRAGMA table_info(fact_price_history);").fetchall()]
    if "min_purchase_qty" not in hist_cols:
        cur.execute("ALTER TABLE fact_price_history ADD COLUMN min_purchase_qty INTEGER DEFAULT 1;")
        print("  ✓ Added column min_purchase_qty to fact_price_history.")
    else:
        print("  - Column min_purchase_qty already present in fact_price_history.")

    if "max_purchase_limit" not in hist_cols:
        cur.execute("ALTER TABLE fact_price_history ADD COLUMN max_purchase_limit INTEGER;")
        print("  ✓ Added column max_purchase_limit to fact_price_history.")
    else:
        print("  - Column max_purchase_limit already present in fact_price_history.")

    if "basket_min_spend" not in hist_cols:
        cur.execute("ALTER TABLE fact_price_history ADD COLUMN basket_min_spend REAL;")
        print("  ✓ Added column basket_min_spend to fact_price_history.")
    else:
        print("  - Column basket_min_spend already present in fact_price_history.")

    conn.commit()
    conn.close()
    print("✨ [SCHEMA MIGRATION] Migration 055 completed successfully!")

    # Record copy in executed directory
    os.makedirs(EXECUTED_DIR, exist_ok=True)
    target = os.path.join(EXECUTED_DIR, os.path.basename(MIGRATION_FILE))
    with open(MIGRATION_FILE, "r") as src, open(target, "w") as dst:
        dst.write(src.read())
    print(f"📁 Archived ledger in {target}")

if __name__ == "__main__":
    apply_migration()
