#!/usr/bin/env python3
"""
=============================================================================
SOVEREIGN OS: TRUE COST REST API ROUTER
=============================================================================
Router: scripts/routers/truecost.py
Mounted on: Sovereign Core API (Port 8090)
Ticket: WO-2026-0909-TRUECOST-ANOMALY-SHRINKFLATION-SENTINEL
CI: 25_TrueCostStack

Endpoints:
- GET  /api/truecost/anomalies             : Active price anomaly feed
- GET  /api/truecost/product-lineage/{upc} : Product package size & unit cost curve
- GET  /api/truecost/matrix                : Multi-store commodity unit price matrix
- GET  /api/truecost/stats                 : Summary statistics for True Cost Console
- POST /api/truecost/run-sentinel          : Trigger autonomous anomaly audit sweep
=============================================================================
"""

import os
import sys
import sqlite3
import statistics
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

DB_PATH = os.getenv("SOVEREIGN_DB_PATH", "/home/james/stacklabs/dna/sovereign_now.db")

router = APIRouter(prefix="/api/truecost", tags=["True Cost Anomaly Sentinel"])

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/anomalies")
def get_anomalies(
    limit: int = Query(50, ge=1, le=200),
    type: Optional[str] = Query(None, description="Filter: SHRINKFLATION, PSEUDO_SALE, BASKET_HOSTAGE, RATION_LIMIT"),
    store_chain: Optional[str] = Query(None, description="Filter: kroger, publix, aldi"),
    severity: Optional[str] = Query(None, description="Filter: HIGH, MEDIUM, INFO")
) -> List[Dict[str, Any]]:
    """
    Retrieve active retail price anomalies with true unit math and audit rationale.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        query = """
            SELECT a.anomaly_id, a.product_id, a.upc_barcode, a.store_chain, a.anomaly_type,
                   a.severity, a.baseline_package_size, a.observed_package_size,
                   a.baseline_unit_price, a.observed_unit_price, a.inflation_pct,
                   a.promo_restriction_summary, a.audit_notes, a.detected_at,
                   p.brand_name, p.item_title, p.commodity_category, p.unit_of_measure
            FROM fact_price_anomaly_log a
            LEFT JOIN dim_product p ON a.product_id = p.product_id
            WHERE 1=1
        """
        params: List[Any] = []

        if type:
            query += " AND a.anomaly_type = ?"
            params.append(type.upper())
        if store_chain:
            query += " AND a.store_chain = ?"
            params.append(store_chain.lower())
        if severity:
            query += " AND a.severity = ?"
            params.append(severity.upper())

        query += " ORDER BY a.anomaly_id DESC LIMIT ?"
        params.append(limit)

        rows = cur.execute(query, params).fetchall()
        results = []
        for r in rows:
            results.append({
                "anomaly_id": r["anomaly_id"],
                "product_id": r["product_id"],
                "upc_barcode": r["upc_barcode"],
                "brand_name": r["brand_name"] or "Unknown Brand",
                "item_title": r["item_title"] or "Unknown Commodity",
                "commodity_category": r["commodity_category"] or "general_grocery",
                "store_chain": r["store_chain"],
                "anomaly_type": r["anomaly_type"],
                "severity": r["severity"],
                "baseline_package_size": r["baseline_package_size"],
                "observed_package_size": r["observed_package_size"],
                "baseline_unit_price": r["baseline_unit_price"],
                "observed_unit_price": r["observed_unit_price"],
                "inflation_pct": r["inflation_pct"],
                "promo_restriction_summary": r["promo_restriction_summary"],
                "audit_notes": r["audit_notes"],
                "detected_at": r["detected_at"],
                "unit_of_measure": r["unit_of_measure"] or "oz"
            })
        return results
    finally:
        conn.close()

@router.get("/product-lineage/{upc}")
def get_product_lineage(upc: str) -> Dict[str, Any]:
    """
    Returns complete package size timeline and unit cost history curve for auditing.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        # Find product by upc_barcode or product_id
        product = cur.execute("""
            SELECT product_id, upc_barcode, brand_name, is_private_label,
                   commodity_category, item_title, package_quantity, unit_of_measure,
                   original_package_quantity, size_reduction_flag, created_at
            FROM dim_product
            WHERE upc_barcode = ? OR product_id = ?
        """, (upc, upc)).fetchone()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product with UPC / ID '{upc}' not found")

        prod_id = product["product_id"]

        # 1. Price history observations
        price_rows = cur.execute("""
            SELECT entry_id, store_chain, store_location_id, observed_timestamp,
                   regular_price, promo_price, promo_mechanism, computed_unit_price,
                   source_channel, raw_payload_snippet, min_purchase_qty,
                   max_purchase_limit, basket_min_spend
            FROM fact_price_history
            WHERE product_id = ?
            ORDER BY observed_timestamp ASC
        """, (prod_id,)).fetchall()

        # 2. Package size timeline
        timeline = []
        if product["original_package_quantity"]:
            timeline.append({
                "package_quantity": product["original_package_quantity"],
                "unit_of_measure": product["unit_of_measure"],
                "status": "HISTORICAL_BASELINE",
                "is_shrunk": False
            })
        timeline.append({
            "package_quantity": product["package_quantity"],
            "unit_of_measure": product["unit_of_measure"],
            "status": "CURRENT_OBSERVED",
            "is_shrunk": bool(product["size_reduction_flag"])
        })

        # 3. Anomalies for this product
        anomalies_rows = cur.execute("""
            SELECT anomaly_id, anomaly_type, severity, store_chain,
                   baseline_package_size, observed_package_size, baseline_unit_price,
                   observed_unit_price, inflation_pct, promo_restriction_summary,
                   audit_notes, detected_at
            FROM fact_price_anomaly_log
            WHERE product_id = ? OR upc_barcode = ?
            ORDER BY detected_at DESC
        """, (prod_id, product["upc_barcode"])).fetchall()

        anomalies = [dict(a) for a in anomalies_rows]
        price_history = [dict(p) for p in price_rows]

        return {
            "product": dict(product),
            "package_size_timeline": timeline,
            "unit_cost_history": price_history,
            "anomalies": anomalies
        }
    finally:
        conn.close()

@router.get("/matrix")
def get_matrix() -> List[Dict[str, Any]]:
    """
    Returns multi-store commodity unit price matrix with live prices and joined anomalies.
    Provides data directly from SQLite for the True Cost Console.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        products = cur.execute("""
            SELECT product_id, upc_barcode, brand_name, commodity_category,
                   item_title, package_quantity, unit_of_measure, original_package_quantity,
                   size_reduction_flag
            FROM dim_product
        """).fetchall()

        # Fetch all anomalies
        anomalies_map: Dict[str, List[Dict[str, Any]]] = {}
        for a in cur.execute("SELECT * FROM fact_price_anomaly_log").fetchall():
            anomalies_map.setdefault(a["product_id"], []).append(dict(a))

        # Build matrix commodities
        matrix_items = []
        for p in products:
            prod_id = p["product_id"]
            prices = cur.execute("""
                SELECT store_chain, regular_price, promo_price, promo_mechanism,
                       computed_unit_price, min_purchase_qty, max_purchase_limit,
                       basket_min_spend
                FROM fact_price_history
                WHERE product_id = ?
                ORDER BY observed_timestamp DESC
            """, (prod_id,)).fetchall()

            store_data: Dict[str, Dict[str, Any]] = {
                "kroger": {"price": 0.0, "promo": 0.0, "mech": "none", "unitPrice": 0.0, "size": f"{p['package_quantity']} {p['unit_of_measure']}"},
                "publix": {"price": 0.0, "promo": 0.0, "mech": "none", "unitPrice": 0.0, "size": f"{p['package_quantity']} {p['unit_of_measure']}"},
                "aldi": {"price": 0.0, "promo": 0.0, "mech": "none", "unitPrice": 0.0, "size": f"{p['package_quantity']} {p['unit_of_measure']}"}
            }

            for pr in prices:
                chain = pr["store_chain"].lower()
                if chain in store_data and store_data[chain]["unitPrice"] == 0.0:
                    store_data[chain] = {
                        "price": pr["regular_price"],
                        "promo": pr["promo_price"] or pr["regular_price"],
                        "mech": pr["promo_mechanism"] or "none",
                        "unitPrice": pr["computed_unit_price"],
                        "size": f"{p['package_quantity']} {p['unit_of_measure']}"
                    }

            prod_anomalies = anomalies_map.get(prod_id, [])
            shrink_alert = None
            for a in prod_anomalies:
                if a["anomaly_type"] == "SHRINKFLATION":
                    shrink_alert = f"Size Cut {a['baseline_package_size']}{p['unit_of_measure']} -> {a['observed_package_size']}{p['unit_of_measure']}"
                    break

            # Calculate ten-week delta estimate based on anomalies
            ten_week_delta = 0.0
            if prod_anomalies:
                top_anomaly = prod_anomalies[0]
                ten_week_delta = top_anomaly["inflation_pct"]

            matrix_items.append({
                "id": prod_id,
                "upc": p["upc_barcode"],
                "brand": p["brand_name"],
                "title": p["item_title"],
                "category": p["commodity_category"],
                "uom": p["unit_of_measure"],
                "package_quantity": p["package_quantity"],
                "kroger": store_data["kroger"],
                "publix": store_data["publix"],
                "aldi": store_data["aldi"],
                "shrinkflationAlert": shrink_alert,
                "anomalies": prod_anomalies,
                "tenWeekDelta": ten_week_delta
            })

        return matrix_items
    finally:
        conn.close()

@router.get("/stats")
def get_stats() -> Dict[str, Any]:
    """
    Summary metrics for True Cost Console Header and Badges.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        total_commodities = cur.execute("SELECT COUNT(*) FROM dim_product").fetchone()[0]
        observations_today = cur.execute("SELECT COUNT(*) FROM fact_price_history").fetchone()[0]
        total_anomalies = cur.execute("SELECT COUNT(*) FROM fact_price_anomaly_log").fetchone()[0]
        shrinkflation = cur.execute("SELECT COUNT(*) FROM fact_price_anomaly_log WHERE anomaly_type = 'SHRINKFLATION'").fetchone()[0]
        pseudo_sales = cur.execute("SELECT COUNT(*) FROM fact_price_anomaly_log WHERE anomaly_type = 'PSEUDO_SALE'").fetchone()[0]
        friction_gates = cur.execute("SELECT COUNT(*) FROM fact_price_anomaly_log WHERE anomaly_type IN ('BASKET_HOSTAGE', 'RATION_LIMIT')").fetchone()[0]

        return {
            "totalCommodities": total_commodities,
            "observationsToday": observations_today,
            "totalAnomalies": total_anomalies,
            "shrinkflationAlerts": shrinkflation,
            "pseudoSaleAlerts": pseudo_sales,
            "frictionAlerts": friction_gates
        }
    finally:
        conn.close()

@router.post("/run-sentinel")
def trigger_sentinel_sweep(dry_run: bool = False) -> Dict[str, Any]:
    """
    Trigger immediate execution of the True Cost Anomaly Sentinel daemon.
    """
    try:
        from scripts.truecost_anomaly_sentinel import TrueCostAnomalySentinel
    except ImportError:
        import sys
        sys.path.insert(0, "/home/james/stacklabs/scripts")
        from truecost_anomaly_sentinel import TrueCostAnomalySentinel

    sentinel = TrueCostAnomalySentinel(dry_run=dry_run)
    anomalies = sentinel.run()

    return {
        "status": "success",
        "dry_run": dry_run,
        "anomalies_detected": len(anomalies),
        "details": anomalies
    }
