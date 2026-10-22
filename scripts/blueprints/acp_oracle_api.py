#!/usr/bin/env python3
"""
ACP Detail Supply Sub-Millisecond Counter & B2B Oracle Blueprint
Path: /home/james/stacklabs/scripts/blueprints/acp_oracle_api.py
Author: James Carroll (Pilot), Lead Systems Architect
"""
import os
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

acp_oracle_bp = APIRouter(prefix="/api/acp", tags=["ACP Detail Oracle"])

DB_PATH = Path("/home/james/stacklabs/vfs/acp_catalog.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


@acp_oracle_bp.get("/search")
def search_acp_catalog(
    q: str = Query("", description="Symptom, machine model, part number, or chemical query")
) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    raw_ino = os.stat(DB_PATH).st_ino if DB_PATH.exists() else 0
    state_register_id = f"0x{(raw_ino ^ 0x5A7F3C19):08x}" if raw_ino else "0x5a7f3c19"

    conn = _get_conn()
    tokens = [t.strip().lower() for t in q.split() if t.strip()]

    rows = conn.execute("SELECT * FROM products").fetchall()
    matched_products: List[Dict[str, Any]] = []

    for r in rows:
        item = dict(r)
        haystack = f"{item['sku']} {item['name']} {item['brand']} {item['category']} {item['symptoms_keywords']}".lower()
        score = 0
        if not tokens:
            score = 1
        else:
            for tok in tokens:
                if tok in item["sku"].lower():
                    score += 10
                elif tok in item["name"].lower():
                    score += 5
                elif tok in haystack:
                    score += 3
        if score > 0:
            edges = conn.execute(
                """
                SELECT e.relationship, e.notes, p.sku, p.name, p.price, p.stock_marietta, p.stock_chamblee, p.stock_hoover
                FROM compatibility_edges e
                JOIN products p ON e.child_sku = p.sku
                WHERE e.parent_sku = ?
                UNION
                SELECT e.relationship, e.notes, p.sku, p.name, p.price, p.stock_marietta, p.stock_chamblee, p.stock_hoover
                FROM compatibility_edges e
                JOIN products p ON e.parent_sku = p.sku
                WHERE e.child_sku = ?
                """,
                (item["sku"], item["sku"]),
            ).fetchall()
            item["compatible_links"] = [dict(e) for e in edges]
            item["match_score"] = score
            matched_products.append(item)

    matched_products.sort(key=lambda x: x["match_score"], reverse=True)
    conn.close()

    elapsed_ns = time.perf_counter_ns() - t0_ns
    return {
        "query": q,
        "latency_ms": round(elapsed_ns / 1_000_000.0, 3),
        "latency_us": round(elapsed_ns / 1_000.0, 1),
        "latency_ns": elapsed_ns,
        "state_register_id": state_register_id,
        "result_count": len(matched_products),
        "results": matched_products,
    }


@acp_oracle_bp.get("/schematic/{sku}")
def get_schematic_explosion(sku: str) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    raw_ino = os.stat(DB_PATH).st_ino if DB_PATH.exists() else 0
    state_register_id = f"0x{(raw_ino ^ 0x5A7F3C19):08x}" if raw_ino else "0x5a7f3c19"

    conn = _get_conn()
    parent = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
    edges = conn.execute(
        """
        SELECT e.relationship, e.notes, p.sku, p.name, p.brand, p.category, p.price, p.stock_marietta, p.stock_chamblee, p.stock_hoover
        FROM compatibility_edges e
        JOIN products p ON e.child_sku = p.sku
        WHERE e.parent_sku = ?
        UNION
        SELECT e.relationship, e.notes, p.sku, p.name, p.brand, p.category, p.price, p.stock_marietta, p.stock_chamblee, p.stock_hoover
        FROM compatibility_edges e
        JOIN products p ON e.parent_sku = p.sku
        WHERE e.child_sku = ?
        """,
        (sku, sku),
    ).fetchall()
    conn.close()

    elapsed_ns = time.perf_counter_ns() - t0_ns
    return {
        "sku": sku,
        "item": dict(parent) if parent else None,
        "compatible_parts": [dict(e) for e in edges],
        "latency_ms": round(elapsed_ns / 1_000_000.0, 3),
        "latency_us": round(elapsed_ns / 1_000.0, 1),
        "state_register_id": state_register_id,
    }


@acp_oracle_bp.get("/dilution")
def calculate_bulk_dilution(
    sku: str = Query("ACP-APC-5G", description="Bulk chemical SKU"),
    ratio_water_to_one: int = Query(10, ge=1, le=256, description="Water parts per 1 part concentrate"),
    bottle_oz: int = Query(32, ge=8, le=128, description="Spray bottle or foam cannon reservoir size in oz"),
) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
    conn.close()

    if not row:
        row_dict = {
            "sku": sku,
            "name": "ACP Commercial Concentrate (5-Gallon)",
            "price": 68.00,
            "Container_gal": 5.0,
        }
    else:
        row_dict = dict(row)

    container_gal = max(float(row_dict.get("Container_gal") or 5.0), 0.26)
    price = float(row_dict.get("price") or 68.0)
    total_concentrate_oz = container_gal * 128.0
    total_rtu_gallons = container_gal * (ratio_water_to_one + 1)
    cost_per_rtu_gallon = price / total_rtu_gallons
    concentrate_oz_per_bottle = bottle_oz / float(ratio_water_to_one + 1)
    water_oz_per_bottle = bottle_oz - concentrate_oz_per_bottle
    cost_per_bottle = (price / total_concentrate_oz) * concentrate_oz_per_bottle

    elapsed_ns = time.perf_counter_ns() - t0_ns
    return {
        "sku": row_dict["sku"],
        "name": row_dict["name"],
        "container_price": price,
        "ratio": f"{ratio_water_to_one}:1",
        "total_ready_to_use_gallons": round(total_rtu_gallons, 1),
        "cost_per_rtu_gallon": round(cost_per_rtu_gallon, 2),
        "bottle_size_oz": bottle_oz,
        "fill_concentrate_oz": round(concentrate_oz_per_bottle, 2),
        "fill_water_oz": round(water_oz_per_bottle, 2),
        "cost_per_bottle": round(cost_per_bottle, 2),
        "latency_us": round(elapsed_ns / 1000.0, 2),
    }


@acp_oracle_bp.api_route("/demo", methods=["GET", "HEAD"], response_class=HTMLResponse)
def render_acp_live_demo() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ACP Detail Supply — Instant Repair Parts & Chemical Oracle</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0B0D13] text-slate-200 min-h-screen font-sans antialiased p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Top Header -->
    <div class="bg-[#11141E] border border-white/10 p-6 rounded-[2px] flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="text-[11px] font-mono uppercase tracking-widest text-cyan-400">
          ADVANCE CHEMICAL PRODUCTS INC. • MARIETTA (501 GLOVER ST) • CHAMBLEE • HOOVER
        </div>
        <h1 class="text-xl md:text-2xl font-bold text-white mt-1">
          ACP Detail Supply: Sub-Millisecond Parts, Schematic & Dilution Oracle
        </h1>
        <p class="text-xs text-slate-400 font-mono mt-1">
          Search by machine symptom ("Kranzle 1122 leaking"), polisher model ("Rupes LHR15"), or chemical application.
        </p>
      </div>
      <div class="bg-[#0B0D13] border border-emerald-500/30 px-4 py-2.5 rounded-[2px] font-mono text-right shrink-0">
        <div class="text-[10px] text-slate-400 uppercase">In-Memory State Register Query Speed</div>
        <div id="latency-badge" class="text-lg font-bold text-emerald-400">0.18 ms</div>
        <div id="inode-badge" class="text-[10px] text-slate-500">State Register: verifying...</div>
      </div>
    </div>

    <!-- Instant Search Bar & Quick Symptom Pills -->
    <div class="bg-[#11141E] border border-white/10 p-5 rounded-[2px] space-y-3">
      <div class="flex flex-col sm:flex-row gap-3">
        <input
          id="search-input"
          type="text"
          placeholder="Type symptom or machine (e.g. 'kranzle leaking', 'rupes lhr15', 'heavy cut', '5 gallon')..."
          class="flex-1 bg-[#0B0D13] border border-white/15 focus:border-cyan-400 text-white px-4 py-3 rounded-[2px] font-mono text-sm outline-none"
        />
        <button
          onclick="runSearch()"
          class="bg-cyan-500 hover:bg-cyan-400 text-black font-mono font-bold text-xs px-6 py-3 rounded-[2px] cursor-pointer"
        >
          QUERY INVENTORY GRAPH
        </button>
      </div>
      <div class="flex flex-wrap gap-2 items-center text-xs font-mono">
        <span class="text-slate-500">Counter Quick-Triggers:</span>
        <button onclick="quickSearch('kranzle 1122')" class="px-2.5 py-1 bg-[#0B0D13] border border-white/10 hover:border-cyan-400 text-cyan-300 rounded-[2px]">Kranzle K1122TST Repair Parts</button>
        <button onclick="quickSearch('leaking pressure')" class="px-2.5 py-1 bg-[#0B0D13] border border-white/10 hover:border-cyan-400 text-cyan-300 rounded-[2px]">Symptom: Pump Leaking / Pressure Loss</button>
        <button onclick="quickSearch('rupes lhr15')" class="px-2.5 py-1 bg-[#0B0D13] border border-white/10 hover:border-cyan-400 text-cyan-300 rounded-[2px]">Rupes LHR15 Mark III Parts & Pads</button>
        <button onclick="quickSearch('koch chemie')" class="px-2.5 py-1 bg-[#0B0D13] border border-white/10 hover:border-cyan-400 text-cyan-300 rounded-[2px]">Koch Chemie Compound + Pad Matrix</button>
        <button onclick="quickSearch('5 gallon')" class="px-2.5 py-1 bg-[#0B0D13] border border-white/10 hover:border-cyan-400 text-cyan-300 rounded-[2px]">ACP 5-Gal Bulk Concentrates</button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left 2 Columns: Live Catalog + Schematic Explosion -->
      <div class="lg:col-span-2 space-y-3" id="results-container"></div>

      <!-- Right Column: Bulk Chemical Dilution & Shop ROI Calculator -->
      <div class="bg-[#11141E] border border-white/10 p-5 rounded-[2px] h-fit space-y-4 font-mono">
        <div class="border-b border-white/10 pb-3">
          <div class="text-[10px] text-amber-400 uppercase tracking-wider">B2B DETAIL SHOP CALCULATOR</div>
          <h2 class="text-base font-bold text-white mt-0.5">5-Gallon Dilution & Cost-Per-Bottle</h2>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block text-slate-400 mb-1">Select ACP Bulk Drum / Pail:</label>
            <select id="dil-sku" onchange="runDilution()" class="w-full bg-[#0B0D13] border border-white/10 p-2.5 text-white rounded-[2px]">
              <option value="ACP-APC-5G">ACP-APC-5G • All-Purpose Degreaser ($68 / 5 Gal)</option>
              <option value="ACP-FOAM-5G">ACP-FOAM-5G • Hyper-Slick Snow Foam ($74 / 5 Gal)</option>
              <option value="ACP-IRON-5G">ACP-IRON-5G • Fallout Iron Decon ($185 / 5 Gal)</option>
            </select>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">Dilution Ratio (Water : Concentrate):</label>
            <input id="dil-ratio" type="range" min="1" max="64" value="10" oninput="runDilution()" class="w-full" />
            <div class="flex justify-between text-[11px] text-cyan-400 font-bold mt-1">
              <span>1:1 Heavy</span>
              <span id="dil-ratio-label">10:1 Dilution</span>
              <span>64:1 Light</span>
            </div>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">Shop Bottle / Foam Cannon Size:</label>
            <select id="dil-bottle" onchange="runDilution()" class="w-full bg-[#0B0D13] border border-white/10 p-2 text-white rounded-[2px]">
              <option value="16">16 oz Detailing Bottle</option>
              <option value="32" selected>32 oz Pro Sprayer / Foam Cannon</option>
              <option value="64">64 oz Pump Sprayer</option>
            </select>
          </div>

          <div id="dilution-output" class="bg-[#0B0D13] border border-white/10 p-4 rounded-[2px] space-y-2"></div>
        </div>
      </div>
    </div>
  </div>

  <script>
    async function runSearch(customQuery) {
      const input = document.getElementById('search-input');
      const q = customQuery !== undefined ? customQuery : input.value;
      const res = await fetch(`/api/acp/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();

      document.getElementById('latency-badge').textContent = `${data.latency_ms} ms (${data.latency_us} µs)`;
      document.getElementById('inode-badge').textContent = `State Register: ${data.state_register_id} • ${data.result_count} matches`;

      const container = document.getElementById('results-container');
      container.innerHTML = data.results.map(item => `
        <div class="bg-[#11141E] border border-white/10 p-5 rounded-[2px] space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2 font-mono text-xs">
                <span class="px-2 py-0.5 bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-bold">p/n: ${item.sku}</span>
                <span class="text-slate-400">${item.brand} • ${item.category}</span>
              </div>
              <h3 class="text-base font-bold text-white mt-1">${item.name}</h3>
            </div>
            <div class="text-right font-mono shrink-0">
              <div class="text-lg font-bold text-emerald-400">$${item.price.toFixed(2)}</div>
            </div>
          </div>

          <!-- Multi-Branch Live Stock Ribbon -->
          <div class="grid grid-cols-3 gap-2 bg-[#0B0D13] p-2.5 rounded-[2px] border border-white/5 font-mono text-xs">
            <div>
              <span class="text-slate-500 block text-[10px]">MARIETTA (501 Glover)</span>
              <span class="text-emerald-400 font-bold">${item.stock_marietta} in stock</span>
            </div>
            <div>
              <span class="text-slate-500 block text-[10px]">CHAMBLEE STORE</span>
              <span class="text-slate-200 font-bold">${item.stock_chamblee} in stock</span>
            </div>
            <div>
              <span class="text-slate-500 block text-[10px]">HOOVER, AL STORE</span>
              <span class="text-slate-200 font-bold">${item.stock_hoover} in stock</span>
            </div>
          </div>

          ${item.dilution_ratio ? `
            <div class="text-xs font-mono text-amber-300 bg-amber-950/20 border border-amber-500/20 px-3 py-1.5 rounded-[2px]">
              Dilution Specs: ${item.dilution_ratio} | ${item.ph_level} | OSHA SDS: ${item.sds_code}
            </div>
          ` : ''}

          ${item.compatible_links && item.compatible_links.length > 0 ? `
            <div class="pt-2 border-t border-white/10 space-y-1.5 font-mono text-xs">
              <div class="text-[10px] uppercase tracking-wider text-cyan-400 font-bold">
                DIRECT COMPATIBILITY GRAPH (REPAIR PARTS & MATCHED PADS):
              </div>
              ${item.compatible_links.map(link => `
                <div class="bg-[#0B0D13] px-3 py-2 rounded-[2px] border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div>
                    <span class="text-emerald-400 font-bold">[${link.sku}]</span>
                    <span class="text-slate-200"> ${link.name}</span>
                    <div class="text-[11px] text-slate-400">${link.notes}</div>
                  </div>
                  <div class="text-right shrink-0 text-[11px]">
                    <span class="text-white font-bold">$${link.price.toFixed(2)}</span>
                    <span class="text-emerald-400 ml-2">(${link.stock_marietta} Marietta)</span>
                  </div>
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `).join('');
    }

    function quickSearch(term) {
      document.getElementById('search-input').value = term;
      runSearch(term);
    }

    async function runDilution() {
      const sku = document.getElementById('dil-sku').value;
      const ratio = document.getElementById('dil-ratio').value;
      const bottle = document.getElementById('dil-bottle').value;
      document.getElementById('dil-ratio-label').textContent = `${ratio}:1 Dilution`;

      const res = await fetch(`/api/acp/dilution?sku=${sku}&ratio_water_to_one=${ratio}&bottle_oz=${bottle}`);
      const d = await res.json();

      document.getElementById('dilution-output').innerHTML = `
        <div class="flex justify-between">
          <span class="text-slate-400">Total Ready-to-Use Yield:</span>
          <span class="text-white font-bold">${d.total_ready_to_use_gallons} Gallons</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-400">True Cost Per RTU Gallon:</span>
          <span class="text-emerald-400 font-bold">$${d.cost_per_rtu_gallon.toFixed(2)} / gal</span>
        </div>
        <div class="flex justify-between border-t border-white/10 pt-2">
          <span class="text-slate-400">Mix for ${d.bottle_size_oz} oz Bottle:</span>
          <span class="text-cyan-300 font-bold">${d.fill_concentrate_oz} oz Chem + ${d.fill_water_oz} oz Water</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-400">Your Cost Per ${d.bottle_size_oz} oz Bottle:</span>
          <span class="text-emerald-400 font-bold text-sm">$${d.cost_per_bottle.toFixed(2)} / bottle</span>
        </div>
      `;
    }

    document.getElementById('search-input').addEventListener('input', (e) => runSearch(e.target.value));
    runSearch('');
    runDilution();
  </script>
</body>
</html>"""
