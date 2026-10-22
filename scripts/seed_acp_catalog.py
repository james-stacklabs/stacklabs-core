#!/usr/bin/env python3
"""
ACP Detail Supply (Advance Chemical Products Inc.) SQLite WAL Graph Seeder
Path: /home/james/stacklabs/scripts/seed_acp_catalog.py
Author: James Carroll (Pilot), Lead Systems Architect
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/james/stacklabs/vfs/acp_catalog.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def seed_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.executescript(
        """
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock_marietta INTEGER NOT NULL,
            stock_chamblee INTEGER NOT NULL,
            stock_hoover INTEGER NOT NULL,
            symptoms_keywords TEXT NOT NULL,
            dilution_ratio TEXT DEFAULT '',
            ph_level TEXT DEFAULT '',
            sds_code TEXT DEFAULT '',
            Container_gal REAL DEFAULT 0.0
        ) WITHOUT ROWID;

        CREATE TABLE compatibility_edges (
            parent_sku TEXT NOT NULL,
            child_sku TEXT NOT NULL,
            relationship TEXT NOT NULL,
            notes TEXT NOT NULL,
            PRIMARY KEY (parent_sku, child_sku)
        ) WITHOUT ROWID;
        """
    )

    products = [
        # Machines (Pressure Washers & Polishers)
        (
            "KRZ-K1122TST",
            "Kranzle K1122TST Cold Water Electric Pressure Washer (1400 PSI / 2.1 GPM)",
            "Kranzle",
            "Equipment - Pressure Washer",
            1749.00,
            6,
            3,
            2,
            "kranzle 1122 pressure washer pump electric 110v total stop detail bay",
            "",
            "",
            "",
            0.0,
        ),
        (
            "KRZ-K1622TS",
            "Kranzle K1622TS Commercial Cold Water Pressure Washer (1600 PSI / 1.7 GPM)",
            "Kranzle",
            "Equipment - Pressure Washer",
            1395.00,
            4,
            2,
            1,
            "kranzle 1622 pressure washer commercial portable",
            "",
            "",
            "",
            0.0,
        ),
        (
            "RUP-LHR15III",
            "Rupes LHR15 Mark III BigFoot Random Orbital Polisher (15mm Throw / 5-Inch)",
            "Rupes",
            "Equipment - Polisher",
            465.00,
            14,
            8,
            5,
            "rupes lhr15 mark 3 iii orbital polisher 5 inch 15mm throw",
            "",
            "",
            "",
            0.0,
        ),
        (
            "RUP-HR81MLII",
            "Rupes BigFoot iBrid Nano Long Neck Polisher Kit",
            "Rupes",
            "Equipment - Polisher",
            657.00,
            9,
            4,
            3,
            "rupes ibrid nano long neck tight areas pillars",
            "",
            "",
            "",
            0.0,
        ),
        # Service Dept / Repair Parts
        (
            "KRZ-410501",
            "Kranzle 15mm Water Seal Packing Kit (OEM Pump Rebuild Kit)",
            "Kranzle",
            "Repair Parts - Pressure Washer",
            68.50,
            22,
            9,
            6,
            "kranzle leaking water weep hole losing pressure seal kit packing 1122 1622",
            "",
            "",
            "",
            0.0,
        ),
        (
            "KRZ-41715",
            "Kranzle UL250 Unloader Valve Assembly (Pressure Regulator)",
            "Kranzle",
            "Repair Parts - Pressure Washer",
            142.00,
            11,
            5,
            3,
            "kranzle pulsing surging no pressure unloader valve bypass stuck 1122",
            "",
            "",
            "",
            0.0,
        ),
        (
            "KRZ-41031",
            "Kranzle High-Pressure Check Valve Set (6-Valve + O-Ring Kit)",
            "Kranzle",
            "Repair Parts - Pressure Washer",
            84.00,
            15,
            6,
            4,
            "kranzle hose vibration low pressure check valve o-ring",
            "",
            "",
            "",
            0.0,
        ),
        (
            "KRZ-15039",
            "Kranzle Stainless Steel Glycerin Pressure Gauge (0-3600 PSI)",
            "Kranzle",
            "Repair Parts - Pressure Washer",
            54.00,
            18,
            7,
            4,
            "kranzle broken gauge leaking glycerin needle stuck",
            "",
            "",
            "",
            0.0,
        ),
        (
            "RUP-980.027N",
            "Rupes 5-Inch (125mm) Hook & Loop Replacement Backing Plate (LHR15)",
            "Rupes",
            "Repair Parts - Polisher",
            44.00,
            30,
            12,
            8,
            "rupes lhr15 backing plate pads flying off melted velcro hook loop",
            "",
            "",
            "",
            0.0,
        ),
        (
            "RUP-47.105",
            "Rupes OEM Replacement Carbon Motor Brush Set (Pair)",
            "Rupes",
            "Repair Parts - Polisher",
            24.95,
            26,
            10,
            7,
            "rupes polisher dead intermittent power sparking motor brushes lhr15 lhr21",
            "",
            "",
            "",
            0.0,
        ),
        # Compounds, Pads & Bulk Chemicals
        (
            "KCX-H9.02",
            "Koch Chemie Heavy Cut H9.02 (1 Liter Silicone-Oil-Free Compound)",
            "Koch Chemie",
            "Compounds & Polishes",
            54.95,
            34,
            18,
            12,
            "koch chemie heavy cut h902 deep scratches 1500 grit sanding marks oxidization",
            "Ready to Use",
            "pH 7.0",
            "SDS-KCX-H902",
            0.26,
        ),
        (
            "KCX-M3.02",
            "Koch Chemie Micro Cut M3.02 Anti-Hologram Finishing Polish (1L)",
            "Koch Chemie",
            "Compounds & Polishes",
            49.95,
            29,
            15,
            10,
            "koch chemie micro cut m302 hologram swirl remover black paint soft clearcoat",
            "Ready to Use",
            "pH 7.0",
            "SDS-KCX-M302",
            0.26,
        ),
        (
            "BNS-554M",
            "Buff and Shine Uro-Tec 5-Inch Maroon Medium/Heavy Cut Foam Pad",
            "Buff and Shine",
            "Polishing Pads",
            11.50,
            64,
            30,
            20,
            "buff and shine maroon pad 5 inch rupes 15mm cutting compound",
            "",
            "",
            "",
            0.0,
        ),
        (
            "BNS-556Y",
            "Buff and Shine Uro-Tec 5-Inch Yellow Polishing/Finishing Foam Pad",
            "Buff and Shine",
            "Polishing Pads",
            11.50,
            58,
            28,
            19,
            "buff and shine yellow finishing pad swirl removal soft paint",
            "",
            "",
            "",
            0.0,
        ),
        (
            "ACP-APC-5G",
            "ACP Commercial Super-Concentrate All-Purpose Degreaser (5-Gallon Pail)",
            "ACP House Chemical",
            "Bulk Chemicals - 5 Gal",
            68.00,
            45,
            25,
            18,
            "acp bulk degreaser apc engine bay tires bugs interior 5 gallon concentrate",
            "10:1 Heavy / 20:1 Medium / 32:1 Interior",
            "pH 12.5",
            "SDS-ACP-104",
            5.0,
        ),
        (
            "ACP-FOAM-5G",
            "ACP Hyper-Slick pH-Neutral Snow Foam Car Wash (5-Gallon Pail)",
            "ACP House Chemical",
            "Bulk Chemicals - 5 Gal",
            74.00,
            38,
            22,
            14,
            "acp snow foam cannon soap ph neutral ceramic safe tunnel wash 5 gallon",
            "8:1 Foam Cannon / 128:1 Bucket",
            "pH 7.2",
            "SDS-ACP-201",
            5.0,
        ),
        (
            "ACP-IRON-5G",
            "ACP Fallout & Brake Dust Iron Decontamination Spray (5-Gallon Pail)",
            "ACP House Chemical",
            "Bulk Chemicals - 5 Gal",
            185.00,
            16,
            9,
            6,
            "acp iron remover wheel cleaner purple bleeding fallout clay prep",
            "1:1 Heavy Wheels / 3:1 Paint Decon",
            "pH 6.8",
            "SDS-ACP-309",
            5.0,
        ),
    ]

    conn.executemany(
        """
        INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        products,
    )

    edges = [
        ("KRZ-K1122TST", "KRZ-410501", "REPAIR_PART", "Fixes water weep-hole leak & pressure loss (15mm plunger)"),
        ("KRZ-K1122TST", "KRZ-41715", "REPAIR_PART", "Fixes pressure surging / unloader bypass stall"),
        ("KRZ-K1122TST", "KRZ-41031", "REPAIR_PART", "Fixes hose pulsation & inlet/outlet valve wear"),
        ("KRZ-K1122TST", "KRZ-15039", "REPAIR_PART", "Direct thread replacement stainless pressure gauge"),
        ("KRZ-K1122TST", "ACP-FOAM-5G", "CHEMICAL_PAIR", "Recommended 8:1 foam cannon feed at 1400 PSI"),
        ("KRZ-K1622TS", "KRZ-410501", "REPAIR_PART", "OEM 15mm water seal kit for K1622TS pump head"),
        ("KRZ-K1622TS", "KRZ-41031", "REPAIR_PART", "OEM 6-valve check kit for K1622TS"),
        ("RUP-LHR15III", "RUP-980.027N", "REPAIR_PART", "Direct OEM 125mm (5-inch) backing plate replacement"),
        ("RUP-LHR15III", "RUP-47.105", "REPAIR_PART", "Fixes motor brush wear / intermittent trigger cutoff"),
        ("RUP-LHR15III", "BNS-554M", "PAD_PAIR", "Matched 5-inch Uro-Tec pad for 15mm orbital throw"),
        ("RUP-LHR15III", "BNS-556Y", "PAD_PAIR", "Matched 5-inch finishing pad for 15mm throw"),
        ("KCX-H9.02", "BNS-554M", "PAD_PAIR", "Optimal heavy-cut foam pairing for H9.02"),
        ("KCX-M3.02", "BNS-556Y", "PAD_PAIR", "Optimal anti-hologram finishing pad pairing"),
    ]

    conn.executemany(
        """
        INSERT INTO compatibility_edges VALUES (?, ?, ?, ?)
        """,
        edges,
    )

    conn.commit()
    conn.close()
    print(f"[SEED COMPLETE] Created {DB_PATH} with {len(products)} SKUs and {len(edges)} graph edges.")


if __name__ == "__main__":
    seed_database()
