#!/usr/bin/env python3
"""
=============================================================================
SOVEREIGN OS: TRUE COST SHRINKFLATION SENTINEL & ANOMALY ENGINE
=============================================================================
Script: /home/james/stacklabs/scripts/truecost_anomaly_sentinel.py
Ticket: WO-2026-0909-TRUECOST-ANOMALY-SHRINKFLATION-SENTINEL
CI: 25_TrueCostStack
Host: Clio (100.73.155.70 / clio.taila01894.ts.net)

Autonomous Analytical Anomaly Detectors:
1. Shrinkflation Sentinel: Package downsizing detection with exact unit price delta.
2. Pseudo-Sale Detector: 60-day median baseline comparison exposing artificial markup.
3. Purchasing Restriction Auditor: Fine-print regex chainsaw (Must Buy, Limits, Basket Minimums).
=============================================================================
"""

import os
import sys
import re
import json
import sqlite3
import argparse
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

DB_PATH = os.getenv("SOVEREIGN_DB_PATH", "/home/james/stacklabs/dna/sovereign_now.db")

def get_db_connection(timeout: float = 30.0) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn

def normalize_title(title: str) -> str:
    """Normalize item title for cross-package and brand-line matching."""
    t = title.lower()
    # Remove parenthetical notes e.g. (shrinkflation), (shrunk down from 12 oz!)
    t = re.sub(r'\(.*?\)', '', t)
    # Remove size tokens e.g. 12 oz, 10.8 oz, 18 oz, 1 gallon, 3 lb, 16 oz, 128 fl oz
    t = re.sub(r'\b\d+(?:\.\d+)?\s*(?:oz|fl\s*oz|lbs?|pounds?|count|ct|gal|gallons?)\b', '', t)
    # Remove standard fluff words, roast descriptors, and packaging styles
    t = re.sub(r'\b(?:family size|standard size|value pack|tray|bag|box|sticks?|medium|dark|light|roast|blend|ground)\b', '', t)
    # Normalize whitespace
    return ' '.join(t.split())

def parse_promotional_restrictions(raw_text: str) -> Dict[str, Any]:
    """
    Regex chainsaw extracting quantity thresholds and constraints:
    - min_purchase_qty: 'must buy 5', 'buy 2 for', 'multiples of 2'
    - max_purchase_limit: 'limit 2 per customer', 'max 4'
    - basket_min_spend: 'min $25 basket spend', 'requires additional $25'
    - requires_digital_coupon: boolean
    """
    min_qty = 1
    max_limit = None
    basket_min = None
    coupon_req = False

    if not raw_text:
        return {
            "min_purchase_qty": min_qty,
            "max_purchase_limit": max_limit,
            "basket_min_spend": basket_min,
            "digital_coupon": coupon_req,
            "summary": ""
        }

    # 1. Min purchase / Must buy
    must_buy_match = re.search(r'(?:must\s+buy|buy\s+in\s+multiples\s+of|buy)\s+(\d+)', raw_text, re.IGNORECASE)
    if must_buy_match:
        val = int(must_buy_match.group(1))
        if val > 1:
            min_qty = val

    # 2. Max limit
    limit_match = re.search(r'(?:limit|max(?:imum)?)\s+(\d+)', raw_text, re.IGNORECASE)
    if limit_match:
        max_limit = int(limit_match.group(1))

    # 3. Basket minimum spend
    min_spend_match = re.search(r'(?:min(?:imum)?\s+(?:basket\s+)?spend|spend|requires?\s+(?:an\s+)?additional)\s+\$?(\d+(?:\.\d+)?)', raw_text, re.IGNORECASE)
    if min_spend_match:
        basket_min = float(min_spend_match.group(1))

    # 4. Digital Coupon clip required
    if re.search(r'digital\s*coupon|coupon|app\s*clip', raw_text, re.IGNORECASE):
        coupon_req = True

    # Build summary
    parts = []
    if min_qty > 1:
        parts.append(f"Must Buy {min_qty}")
    if max_limit is not None:
        parts.append(f"Limit {max_limit} per customer")
    if basket_min is not None:
        parts.append(f"Min ${basket_min:.2f} basket spend")
    if coupon_req:
        parts.append("Digital Coupon clip required")

    return {
        "min_purchase_qty": min_qty,
        "max_purchase_limit": max_limit,
        "basket_min_spend": basket_min,
        "digital_coupon": coupon_req,
        "summary": "; ".join(parts) if parts else ""
    }

class TrueCostAnomalySentinel:
    def __init__(self, dry_run: bool = False, store_chain: Optional[str] = None):
        self.dry_run = dry_run
        self.store_chain_filter = store_chain
        self.anomalies_detected: List[Dict[str, Any]] = []

    def run(self) -> List[Dict[str, Any]]:
        print("=================================================================")
        print("  SOVEREIGN OS // TRUE COST ANOMALY SENTINEL DAEMON")
        print(f"  Mode: {'DRY-RUN (Zero DB Mutations)' if self.dry_run else 'LIVE COMMIT (WAL Mode)'}")
        print(f"  Target DB: {DB_PATH}")
        print("=================================================================")

        conn = get_db_connection()
        try:
            # Step 1: Audit and enrich fact_price_history restrictions
            self.audit_price_restrictions(conn)

            # Step 2: Detect Shrinkflation (Downsizing Detection)
            self.detect_shrinkflation(conn)

            # Step 3: Detect Pseudo-Sales (Yo-Yo Markups)
            self.detect_pseudo_sales(conn)

            # Step 4: Detect Basket Hostage & Ration Limits
            self.detect_friction_gates(conn)

            # Step 5: Save anomalies if not dry-run
            if not self.dry_run:
                self.persist_anomalies(conn)
                conn.commit()

            self.print_audit_report()
            return self.anomalies_detected
        finally:
            conn.close()

    def audit_price_restrictions(self, conn: sqlite3.Connection):
        """Parse raw snippets and enrich fact_price_history columns."""
        cur = conn.cursor()
        query = "SELECT entry_id, raw_payload_snippet FROM fact_price_history WHERE raw_payload_snippet IS NOT NULL"
        rows = cur.execute(query).fetchall()

        for row in rows:
            entry_id = row["entry_id"]
            snippet = row["raw_payload_snippet"]
            parsed = parse_promotional_restrictions(snippet)

            if not self.dry_run and (parsed["min_purchase_qty"] > 1 or parsed["max_purchase_limit"] or parsed["basket_min_spend"]):
                cur.execute("""
                    UPDATE fact_price_history
                    SET min_purchase_qty = ?, max_purchase_limit = ?, basket_min_spend = ?
                    WHERE entry_id = ?
                """, (parsed["min_purchase_qty"], parsed["max_purchase_limit"], parsed["basket_min_spend"], entry_id))

    def detect_shrinkflation(self, conn: sqlite3.Connection):
        """
        Shrinkflation Sentinel:
        Compares current package_quantity against historical records for identical UPC
        or brand-line normalized titles.
        """
        cur = conn.cursor()
        products = cur.execute("""
            SELECT product_id, upc_barcode, brand_name, commodity_category, 
                   item_title, package_quantity, unit_of_measure, original_package_quantity
            FROM dim_product
        """).fetchall()

        # Group products by brand and normalized title
        grouped: Dict[str, List[sqlite3.Row]] = {}
        for p in products:
            key = f"{p['brand_name']}::{normalize_title(p['item_title'])}"
            grouped.setdefault(key, []).append(p)

        for key, p_list in grouped.items():
            # Check pairwise package size differences within the same brand product line
            for p_curr in p_list:
                for p_hist in p_list:
                    if p_curr["product_id"] == p_hist["product_id"]:
                        continue

                    hist_size = float(p_hist["package_quantity"])
                    curr_size = float(p_curr["package_quantity"])

                    if curr_size < hist_size and p_curr["unit_of_measure"] == p_hist["unit_of_measure"]:
                        # Fetch latest observed prices for both
                        p_curr_price = cur.execute("""
                            SELECT regular_price, promo_price, computed_unit_price, store_chain, observed_timestamp
                            FROM fact_price_history
                            WHERE product_id = ?
                            ORDER BY observed_timestamp DESC LIMIT 1
                        """, (p_curr["product_id"],)).fetchone()

                        p_hist_price = cur.execute("""
                            SELECT regular_price, promo_price, computed_unit_price, store_chain, observed_timestamp
                            FROM fact_price_history
                            WHERE product_id = ?
                            ORDER BY observed_timestamp DESC LIMIT 1
                        """, (p_hist["product_id"],)).fetchone()

                        if not p_curr_price or not p_hist_price:
                            continue

                        store = p_curr_price["store_chain"]
                        if self.store_chain_filter and store != self.store_chain_filter:
                            continue

                        # Unit calculations
                        hist_unit_price = p_hist_price["regular_price"] / hist_size
                        curr_unit_price = p_curr_price["regular_price"] / curr_size
                        
                        delta_size = round(((hist_size - curr_size) / hist_size) * 100.0, 2)
                        real_inflation = round(((curr_unit_price - hist_unit_price) / hist_unit_price) * 100.0, 2)
                        
                        severity = "HIGH" if real_inflation >= 15.0 or delta_size >= 15.0 else "MEDIUM"
                        notes = (
                            f"Shrinkflation Detected: Package volume downsized from {hist_size:.1f} {p_curr['unit_of_measure']} "
                            f"to {curr_size:.1f} {p_curr['unit_of_measure']} (-{delta_size}%). "
                            f"Regular shelf price changed from ${p_hist_price['regular_price']:.2f} (${hist_unit_price:.4f}/{p_curr['unit_of_measure']}) "
                            f"to ${p_curr_price['regular_price']:.2f} (${curr_unit_price:.4f}/{p_curr['unit_of_measure']}), "
                            f"producing a true unit inflation penalty of +{real_inflation}%."
                        )

                        self.anomalies_detected.append({
                            "product_id": p_curr["product_id"],
                            "upc_barcode": p_curr["upc_barcode"],
                            "store_chain": store,
                            "anomaly_type": "SHRINKFLATION",
                            "severity": severity,
                            "baseline_package_size": hist_size,
                            "observed_package_size": curr_size,
                            "baseline_unit_price": round(hist_unit_price, 4),
                            "observed_unit_price": round(curr_unit_price, 4),
                            "inflation_pct": real_inflation,
                            "promo_restriction_summary": f"Net Weight Down -{delta_size}%",
                            "audit_notes": notes
                        })

                        if not self.dry_run:
                            cur.execute("""
                                UPDATE dim_product
                                SET original_package_quantity = ?, size_reduction_flag = 1
                                WHERE product_id = ?
                            """, (hist_size, p_curr["product_id"]))

    def detect_pseudo_sales(self, conn: sqlite3.Connection):
        """
        Pseudo-Sale ("Yo-Yo" Discount) Detector:
        Computes 60-day median shelf price for product at chain.
        Flags cases where promo_price >= median_regular or current regular_price > 1.15 * median_regular.
        """
        cur = conn.cursor()
        products = cur.execute("SELECT product_id, upc_barcode, item_title, package_quantity, unit_of_measure FROM dim_product").fetchall()

        for p in products:
            prod_id = p["product_id"]
            pkg_size = float(p["package_quantity"] or 1.0)
            uom = p["unit_of_measure"] or "unit"

            # Get distinct stores for this product
            stores = [r[0] for r in cur.execute("SELECT DISTINCT store_chain FROM fact_price_history WHERE product_id = ?", (prod_id,)).fetchall()]

            for store in stores:
                if self.store_chain_filter and store != self.store_chain_filter:
                    continue

                # Fetch all observations ordered by timestamp ascending
                history = cur.execute("""
                    SELECT entry_id, regular_price, promo_price, promo_mechanism, observed_timestamp, raw_payload_snippet
                    FROM fact_price_history
                    WHERE product_id = ? AND store_chain = ?
                    ORDER BY observed_timestamp ASC
                """, (prod_id, store)).fetchall()

                if len(history) < 2:
                    continue

                # Compute baseline median regular price from all but the latest observation
                prior_regs = [h["regular_price"] for h in history[:-1] if h["regular_price"] > 0]
                if not prior_regs:
                    continue

                median_reg = statistics.median(prior_regs)
                latest = history[-1]
                latest_reg = latest["regular_price"]
                latest_promo = latest["promo_price"]
                mechanism = latest["promo_mechanism"] or "none"

                is_pseudo_sale = False
                reasons = []

                # Condition A: regular price was jacked by > 15% before promotion
                markup_ratio = latest_reg / median_reg
                if markup_ratio > 1.15:
                    markup_pct = round((markup_ratio - 1.0) * 100.0, 2)
                    is_pseudo_sale = True
                    reasons.append(f"Regular price jacked by +{markup_pct}% (from ${median_reg:.2f} median to ${latest_reg:.2f}) prior to promotional cycle")

                # Condition B: advertised promo price is >= median regular price
                if mechanism != "none" and latest_promo >= median_reg:
                    is_pseudo_sale = True
                    reasons.append(f"Advertised promo price ${latest_promo:.2f} is greater than or equal to historical regular median (${median_reg:.2f})")

                if is_pseudo_sale:
                    severity = "HIGH" if markup_ratio >= 1.25 or latest_promo >= median_reg else "MEDIUM"
                    inflation_pct = round(((latest_reg - median_reg) / median_reg) * 100.0, 2)
                    baseline_unit = round(median_reg / pkg_size, 4)
                    observed_unit = round(latest_promo / pkg_size, 4)

                    notes = (
                        f"Pseudo-Sale Yo-Yo Markup at {store.upper()}: {'; '.join(reasons)}. "
                        f"Retailer advertised '{mechanism}' but baseline shelf cost was artificially inflated."
                    )

                    self.anomalies_detected.append({
                        "product_id": prod_id,
                        "upc_barcode": p["upc_barcode"],
                        "store_chain": store,
                        "anomaly_type": "PSEUDO_SALE",
                        "severity": severity,
                        "baseline_package_size": pkg_size,
                        "observed_package_size": pkg_size,
                        "baseline_unit_price": baseline_unit,
                        "observed_unit_price": observed_unit,
                        "inflation_pct": inflation_pct,
                        "promo_restriction_summary": f"Base Markup +{inflation_pct}%",
                        "audit_notes": notes
                    })

    def detect_friction_gates(self, conn: sqlite3.Connection):
        """
        Purchasing Friction & Restriction Auditor:
        Detects Basket Hostage ($ min spend) and Ration Limits (strict buy constraints).
        """
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT h.entry_id, h.product_id, h.store_chain, h.regular_price, h.promo_price,
                   h.min_purchase_qty, h.max_purchase_limit, h.basket_min_spend, h.raw_payload_snippet,
                   p.upc_barcode, p.package_quantity, p.unit_of_measure, p.item_title
            FROM fact_price_history h
            JOIN dim_product p ON h.product_id = p.product_id
            WHERE h.basket_min_spend IS NOT NULL OR (h.min_purchase_qty > 1 AND h.max_purchase_limit IS NOT NULL)
        """).fetchall()

        for r in rows:
            store = r["store_chain"]
            if self.store_chain_filter and store != self.store_chain_filter:
                continue

            pkg_size = float(r["package_quantity"] or 1.0)
            uom = r["unit_of_measure"] or "unit"
            promo_price = float(r["promo_price"] or r["regular_price"])
            unit_price = round(promo_price / pkg_size, 4)

            parsed = parse_promotional_restrictions(r["raw_payload_snippet"])

            # Basket Hostage
            if r["basket_min_spend"] and r["basket_min_spend"] > 0:
                spend = r["basket_min_spend"]
                notes = (
                    f"Basket Hostage Constraint: Advertised promo price of ${promo_price:.2f} requires "
                    f"an additional ${spend:.2f} minimum basket spend to unlock savings. Hurdle threshold: ${spend:.2f}."
                )
                self.anomalies_detected.append({
                    "product_id": r["product_id"],
                    "upc_barcode": r["upc_barcode"],
                    "store_chain": store,
                    "anomaly_type": "BASKET_HOSTAGE",
                    "severity": "HIGH" if spend >= 20.0 else "MEDIUM",
                    "baseline_package_size": pkg_size,
                    "observed_package_size": pkg_size,
                    "baseline_unit_price": round(float(r["regular_price"]) / pkg_size, 4),
                    "observed_unit_price": unit_price,
                    "inflation_pct": 0.0,
                    "promo_restriction_summary": parsed["summary"],
                    "audit_notes": notes
                })

            # Ration Limit
            if r["max_purchase_limit"] and r["max_purchase_limit"] <= 2 and r["min_purchase_qty"] >= 4:
                notes = (
                    f"Ration Limit / Purchase Friction Gate: Deal requires purchasing {r['min_purchase_qty']} items "
                    f"to receive promo pricing, yet caps rewards at limit {r['max_purchase_limit']}. High customer friction."
                )
                self.anomalies_detected.append({
                    "product_id": r["product_id"],
                    "upc_barcode": r["upc_barcode"],
                    "store_chain": store,
                    "anomaly_type": "RATION_LIMIT",
                    "severity": "MEDIUM",
                    "baseline_package_size": pkg_size,
                    "observed_package_size": pkg_size,
                    "baseline_unit_price": round(float(r["regular_price"]) / pkg_size, 4),
                    "observed_unit_price": unit_price,
                    "inflation_pct": 0.0,
                    "promo_restriction_summary": parsed["summary"],
                    "audit_notes": notes
                })

    def persist_anomalies(self, conn: sqlite3.Connection):
        """Persist detected anomalies into fact_price_anomaly_log with deduplication."""
        cur = conn.cursor()
        for a in self.anomalies_detected:
            # Check if an identical active anomaly exists within the last 7 days
            cur.execute("""
                SELECT anomaly_id FROM fact_price_anomaly_log
                WHERE product_id = ? AND store_chain = ? AND anomaly_type = ?
                  AND detected_at >= datetime('now', '-7 days')
            """, (a["product_id"], a["store_chain"], a["anomaly_type"]))
            existing = cur.fetchone()

            if existing:
                # Update existing anomaly
                cur.execute("""
                    UPDATE fact_price_anomaly_log
                    SET severity = ?, baseline_package_size = ?, observed_package_size = ?,
                        baseline_unit_price = ?, observed_unit_price = ?, inflation_pct = ?,
                        promo_restriction_summary = ?, audit_notes = ?, detected_at = CURRENT_TIMESTAMP
                    WHERE anomaly_id = ?
                """, (
                    a["severity"], a["baseline_package_size"], a["observed_package_size"],
                    a["baseline_unit_price"], a["observed_unit_price"], a["inflation_pct"],
                    a["promo_restriction_summary"], a["audit_notes"], existing["anomaly_id"]
                ))
            else:
                # Insert new anomaly record
                cur.execute("""
                    INSERT INTO fact_price_anomaly_log (
                        product_id, upc_barcode, store_chain, anomaly_type, severity,
                        baseline_package_size, observed_package_size, baseline_unit_price,
                        observed_unit_price, inflation_pct, promo_restriction_summary,
                        audit_notes, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    a["product_id"], a["upc_barcode"], a["store_chain"], a["anomaly_type"],
                    a["severity"], a["baseline_package_size"], a["observed_package_size"],
                    a["baseline_unit_price"], a["observed_unit_price"], a["inflation_pct"],
                    a["promo_restriction_summary"], a["audit_notes"]
                ))

    def print_audit_report(self):
        print(f"\n[SENTINEL AUDIT COMPLETE] Found {len(self.anomalies_detected)} price anomaly flags:")
        print("-" * 80)
        for i, a in enumerate(self.anomalies_detected, 1):
            print(f"[{i:02d}] {a['anomaly_type']:<15} | Severity: {a['severity']:<6} | Store: {a['store_chain'].upper():<6} | UPC: {a['upc_barcode']}")
            if a['anomaly_type'] == 'SHRINKFLATION':
                print(f"     Size Delta: {a['baseline_package_size']} -> {a['observed_package_size']} | Unit Price Delta: ${a['baseline_unit_price']} -> ${a['observed_unit_price']} (+{a['inflation_pct']}%)")
            elif a['anomaly_type'] == 'PSEUDO_SALE':
                print(f"     Base Shelf Markup: +{a['inflation_pct']}% vs 60-Day Median Regular")
            elif a['anomaly_type'] in ('BASKET_HOSTAGE', 'RATION_LIMIT'):
                print(f"     Friction Summary: {a['promo_restriction_summary']}")
            print(f"     Audit Notes: {a['audit_notes']}")
            print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="True Cost Shrinkflation Sentinel & Price Anomaly Engine")
    parser.add_argument("--dry-run", action="store_true", help="Process historical records and output detected flags without modifying database")
    parser.add_argument("--store-chain", choices=["kroger", "publix", "aldi"], help="Filter by specific store chain")
    args = parser.parse_args()

    sentinel = TrueCostAnomalySentinel(dry_run=args.dry_run, store_chain=args.store_chain)
    sentinel.run()

if __name__ == "__main__":
    main()
