#!/usr/bin/env python3
"""
Bleacher Provocateur Hot Take Ledger & Mind Map Blueprint
Path: /home/james/stacklabs/scripts/blueprints/hot_take_ledger_api.py
Author: James Carroll (Pilot), Lead Systems Architect
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse

PROJECT_ROOT = Path("/home/james/stacklabs")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.bleacher_hot_take_engine import (
    get_db_connection,
    export_mindmap_json,
    settle_hot_take,
    DB_PATH
)

hot_take_ledger_bp = APIRouter(prefix="/api/provocateur", tags=["Bleacher Provocateur Ledger"])


@hot_take_ledger_bp.api_route("/ledger", methods=["GET", "HEAD"])
def get_provocateur_ledger(
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    db_inode = os.stat(DB_PATH).st_ino if DB_PATH.exists() else 0

    with get_db_connection() as conn:
        takes = conn.execute("""
            SELECT t.*, p.display_name, p.classification, p.sharp_score, p.cope_score
            FROM hot_takes t
            JOIN provocateurs p ON t.author = p.handle
            ORDER BY t.dogpile_trigger_count DESC, t.timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()

    latency_us = (time.perf_counter_ns() - t0_ns) / 1000.0

    return {
        "status": "success",
        "latency_us": round(latency_us, 2),
        "db_inode": db_inode,
        "count": len(takes),
        "takes": [dict(t) for t in takes]
    }


@hot_take_ledger_bp.api_route("/profile/{author}", methods=["GET", "HEAD"])
def get_provocateur_profile(author: str) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    with get_db_connection() as conn:
        prov = conn.execute("SELECT * FROM provocateurs WHERE LOWER(handle) = LOWER(?)", (author,)).fetchone()
        if not prov:
            raise HTTPException(status_code=404, detail=f"Provocateur {author} not found")

        takes = conn.execute("SELECT * FROM hot_takes WHERE LOWER(author) = LOWER(?) ORDER BY timestamp DESC", (author,)).fetchall()
        nodes = conn.execute("SELECT * FROM graph_nodes WHERE LOWER(author_handle) = LOWER(?)", (author,)).fetchall()
        edges = conn.execute("SELECT * FROM graph_edges WHERE LOWER(author_handle) = LOWER(?)", (author,)).fetchall()

    latency_us = (time.perf_counter_ns() - t0_ns) / 1000.0

    return {
        "provocateur": dict(prov),
        "takes_count": len(takes),
        "graph_node_count": len(nodes),
        "graph_edge_count": len(edges),
        "latency_us": round(latency_us, 2),
        "takes": [dict(t) for t in takes]
    }


@hot_take_ledger_bp.api_route("/mindmap/{author}", methods=["GET", "HEAD"])
def get_provocateur_mindmap(author: str) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    data = export_mindmap_json(author)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    data["latency_us"] = round((time.perf_counter_ns() - t0_ns) / 1000.0, 2)
    return data


@hot_take_ledger_bp.api_route("/graph/{author}", methods=["GET", "HEAD"])
def get_provocateur_graph(author: str) -> Dict[str, Any]:
    t0_ns = time.perf_counter_ns()
    with get_db_connection() as conn:
        nodes = conn.execute("SELECT * FROM graph_nodes WHERE LOWER(author_handle) = LOWER(?)", (author,)).fetchall()
        edges = conn.execute("SELECT * FROM graph_edges WHERE LOWER(author_handle) = LOWER(?)", (author,)).fetchall()

    return {
        "author": author,
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
        "latency_us": round((time.perf_counter_ns() - t0_ns) / 1000.0, 2)
    }


@hot_take_ledger_bp.api_route("/view", methods=["GET", "HEAD"], response_class=HTMLResponse)
def get_provocateur_view():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StackLabs // Bleacher Provocateur Mind Map & Hot Take Engine</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0B0D13; color: #E2E8F0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    .hairline { border: 1px solid rgba(255, 255, 255, 0.1); }
    .card-bg { background-color: #11141E; }
    .badge-quant { background-color: #064E3B; color: #6EE7B7; border: 1px solid #059669; }
    .badge-cope { background-color: #7F1D1D; color: #FCA5A5; border: 1px solid #DC2626; }
    .badge-pending { background-color: #78350F; color: #FCD34D; border: 1px solid #D97706; }
  </style>
</head>
<body class="p-4 md:p-8 max-w-7xl mx-auto">
  <header class="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-white/10 gap-4">
    <div>
      <div class="text-xs uppercase tracking-widest text-slate-500 font-semibold">StackLabs // Anthropological Telemetry</div>
      <h1 class="text-2xl font-bold text-white tracking-tight mt-1">Bleacher Provocateur Mind Map & Settlement Engine</h1>
    </div>
    <div class="flex items-center gap-3">
      <span class="px-2.5 py-1 text-xs rounded bg-white/5 hairline text-slate-400">SQLite WAL Direct</span>
      <span class="px-2.5 py-1 text-xs rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-400">Zero WAN Mock</span>
    </div>
  </header>

  <main class="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
    <section class="lg:col-span-5 flex flex-col gap-4">
      <div class="card-bg hairline rounded-lg p-4">
        <h2 class="text-sm uppercase tracking-wider text-slate-400 font-bold mb-3 flex justify-between items-center">
          <span>Active Provocateurs</span>
          <span class="text-xs text-slate-500">Sorted by Dogpile Impact</span>
        </h2>
        <div id="provocateur-list" class="flex flex-col gap-2">
          <div class="text-xs text-slate-500 py-4 text-center">Loading provocateurs...</div>
        </div>
      </div>

      <div class="card-bg hairline rounded-lg p-4">
        <h2 class="text-sm uppercase tracking-wider text-slate-400 font-bold mb-3">Recent High-Dogpile Hot Takes</h2>
        <div id="takes-list" class="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
          <div class="text-xs text-slate-500 py-4 text-center">Loading ledger...</div>
        </div>
      </div>
    </section>

    <section class="lg:col-span-7 flex flex-col gap-4">
      <div class="card-bg hairline rounded-lg p-5">
        <div class="flex justify-between items-start mb-4 border-b border-white/10 pb-4">
          <div>
            <div id="active-handle" class="text-xl font-bold text-white">Select a Provocateur</div>
            <div id="active-meta" class="text-xs text-slate-400 mt-1">Click any provocateur on the left to inspect their cognitive mind map.</div>
          </div>
          <div id="active-badge"></div>
        </div>

        <h3 class="text-xs uppercase tracking-wider text-slate-400 font-bold mb-3">Cognitive Mind Map Hierarchy (Obsession Tree)</h3>
        <div id="mindmap-container" class="bg-[#0B0D13] hairline rounded p-4 min-h-[380px] overflow-x-auto text-xs">
          <div class="text-slate-600 text-center py-20">Select a provocateur from the left to render the tree.</div>
        </div>
      </div>
    </section>
  </main>

  <script>
    let activeAuthor = "@BenJames7976";

    async function loadLedger() {
      try {
        const res = await fetch("/api/provocateur/ledger?limit=20");
        const data = await res.json();
        renderTakes(data.takes);
        extractProvocateurs(data.takes);
        if (activeAuthor) loadMindmap(activeAuthor);
      } catch (e) {
        console.error("Ledger fetch error", e);
      }
    }

    function extractProvocateurs(takes) {
      const map = {};
      takes.forEach(t => {
        if (!map[t.author]) {
          map[t.author] = {
            handle: t.author,
            display_name: t.display_name,
            classification: t.classification,
            sharp_score: t.sharp_score,
            cope_score: t.cope_score,
            dogpiles: 0
          };
        }
        map[t.author].dogpiles += t.dogpile_trigger_count;
      });

      const container = document.getElementById("provocateur-list");
      container.innerHTML = Object.values(map).map(p => {
        const badgeClass = p.classification === 'ACCIDENTAL_QUANT' ? 'badge-quant' : (p.classification === 'LUCKY_SOCKS_COPE' ? 'badge-cope' : 'badge-pending');
        return `
          <div onclick="selectAuthor('${p.handle}')" class="cursor-pointer p-3 rounded hairline bg-[#0B0D13] hover:border-slate-500 transition-all flex justify-between items-center">
            <div>
              <div class="text-sm font-semibold text-white">${p.handle}</div>
              <div class="text-xs text-slate-400">${p.display_name} • Dogpile Hits: ${p.dogpiles}</div>
            </div>
            <span class="text-[10px] px-2 py-0.5 rounded font-bold ${badgeClass}">${p.classification}</span>
          </div>
        `;
      }).join("");
    }

    function renderTakes(takes) {
      const container = document.getElementById("takes-list");
      container.innerHTML = takes.map(t => {
        const vClass = t.settlement_verdict === 'VERIFIED_SHARP' ? 'text-emerald-400' : (t.settlement_verdict === 'BUSTER_COPE' ? 'text-rose-400' : 'text-amber-400');
        return `
          <div class="p-2.5 rounded hairline bg-[#0B0D13] text-xs">
            <div class="flex justify-between text-[11px] text-slate-500 mb-1">
              <span>${t.author} • ${t.game_context}</span>
              <span class="text-amber-400/80">Dogpiles: ${t.dogpile_trigger_count}</span>
            </div>
            <div class="text-slate-200">"${t.raw_message}"</div>
            <div class="mt-1.5 flex justify-between items-center text-[10px]">
              <span class="text-slate-500">${t.category}</span>
              <span class="font-bold ${vClass}">${t.settlement_verdict}</span>
            </div>
          </div>
        `;
      }).join("");
    }

    async function selectAuthor(author) {
      activeAuthor = author;
      await loadMindmap(author);
    }

    async function loadMindmap(author) {
      try {
        const res = await fetch(`/api/provocateur/mindmap/${encodeURIComponent(author)}`);
        const data = await res.json();
        document.getElementById("active-handle").innerText = data.name;
        document.getElementById("active-meta").innerText = `${data.display_name} • Total Messages: ${data.total_messages} • Sharp Ratio: ${data.sharp_score}% • Cope Ratio: ${data.cope_score}%`;
        
        const badgeClass = data.classification === 'ACCIDENTAL_QUANT' ? 'badge-quant' : (data.classification === 'LUCKY_SOCKS_COPE' ? 'badge-cope' : 'badge-pending');
        document.getElementById("active-badge").innerHTML = `<span class="px-2.5 py-1 text-xs rounded font-bold ${badgeClass}">${data.classification}</span>`;

        const container = document.getElementById("mindmap-container");
        let html = `<div class="space-y-4">`;
        data.children.forEach(cat => {
          html += `
            <div class="border-l-2 border-white/20 pl-3">
              <div class="text-amber-400 font-bold tracking-wide uppercase text-xs mb-1.5">${cat.name} (${cat.count} takes)</div>
              <div class="space-y-2 pl-2">
          `;
          cat.children.forEach(leaf => {
            const vBadge = leaf.verdict === 'VERIFIED_SHARP' 
              ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-500/30">SHARP CALL</span>'
              : (leaf.verdict === 'BUSTER_COPE' 
                ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-rose-950 text-rose-400 border border-rose-500/30">SUPERSTITIOUS COPE</span>'
                : '<span class="px-1.5 py-0.5 rounded text-[10px] bg-amber-950 text-amber-400 border border-amber-500/30">PENDING SETTLEMENT</span>');

            html += `
              <div class="bg-[#11141E] hairline p-2 rounded flex flex-col md:flex-row md:items-center justify-between gap-2">
                <div class="text-slate-300">"${leaf.name}"</div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="text-[10px] text-slate-500">${leaf.game}</span>
                  ${vBadge}
                </div>
              </div>
            `;
          });
          html += `</div></div>`;
        });
        html += `</div>`;
        container.innerHTML = html;
      } catch (e) {
        console.error("Mindmap error", e);
      }
    }

    loadLedger();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
