#!/usr/bin/env python3
"""
Surgically patches scripts/templates/cockpit.html to add:
- Reset / Clear button
- In-flight skeleton loading state (fixes state desync)
- Paired presets
- Real 285k concept count
- resetSwansonCrawl() implementation
"""
import sys
from pathlib import Path

TARGET = Path("/home/james/stacklabs/scripts/templates/cockpit.html")
if not TARGET.is_file():
    print(f"Error: {TARGET} not found")
    sys.exit(1)

content = TARGET.read_text(encoding="utf-8")

# 1. Update concept counts
content = content.replace("9,997 Concepts", "285,388 Concepts")
content = content.replace("9,997 mounted concept inodes", "285,388 mounted concept inodes")

# 2. Add Reset Button next to Execute Button
old_btn_block = """          <!-- Execute Button -->
          <div class="md:col-span-3">
            <button onclick="triggerSwansonCrawl()" id="crawl-execute-btn" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-semibold py-2 px-4 rounded-lg transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer">
              <svg id="crawl-spin-icon" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              <span id="crawl-btn-label">Execute Crawl</span>
            </button>
          </div>"""

new_btn_block = """          <!-- Execute Button -->
          <div class="md:col-span-3 flex items-center gap-2">
            <button onclick="triggerSwansonCrawl()" id="crawl-execute-btn" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-semibold py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer">
              <svg id="crawl-spin-icon" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              <span id="crawl-btn-label">Execute Crawl</span>
            </button>
            <button onclick="resetSwansonCrawl()" id="crawl-reset-btn" title="Reset and Clear Crawl" class="p-2 bg-black/40 hover:bg-zinc-800 border border-white/10 hover:border-white/20 text-zinc-400 hover:text-white rounded-lg transition-all flex items-center justify-center cursor-pointer shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              <span class="sr-only">Clear</span>
            </button>
          </div>"""

if old_btn_block in content:
    content = content.replace(old_btn_block, new_btn_block)
    print("✔ Added Reset / Clear button to Execute block")
else:
    print("⚠ Execute button block pattern not matched directly; verifying if already patched")

# 3. Replace single Presets with Paired Presets
old_presets = """          <div class="flex items-center gap-1.5 flex-wrap" id="crawl-presets-container">
            <span class="text-[10px] font-mono text-zinc-500 uppercase mr-1">Presets:</span>
            <button onclick="applyCrawlPreset('physics')" data-preset="physics" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">physics</button>
            <button onclick="applyCrawlPreset('chemistry')" data-preset="chemistry" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-emerald-950/80 border-emerald-500/50 text-emerald-300 transition-colors cursor-pointer">chemistry</button>
            <button onclick="applyCrawlPreset('mars')" data-preset="mars" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">mars</button>
            <button onclick="applyCrawlPreset('earth')" data-preset="earth" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">earth</button>
            <button onclick="applyCrawlPreset('acoustics')" data-preset="acoustics" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">acoustics</button>
            <button onclick="applyCrawlPreset('baseball')" data-preset="baseball" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">baseball</button>
            <button onclick="applyCrawlPreset('nasa')" data-preset="nasa" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">nasa</button>
            <button onclick="applyCrawlPreset('biology')" data-preset="biology" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">biology</button>
          </div>"""

new_presets = """          <div class="flex items-center gap-1.5 flex-wrap" id="crawl-presets-container">
            <span class="text-[10px] font-mono text-zinc-500 uppercase mr-1">Pairs:</span>
            <button onclick="applyCrawlPair('physics', 'chemistry')" data-pair="physics-chemistry" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-emerald-950/80 border-emerald-500/50 text-emerald-300 transition-colors cursor-pointer">Physics ⇄ Chemistry</button>
            <button onclick="applyCrawlPair('lollipop', 'gilligan_s_island')" data-pair="lollipop-gilligan" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">Lollipop ⇄ Gilligan</button>
            <button onclick="applyCrawlPair('baseball', 'acoustics')" data-pair="baseball-acoustics" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">Baseball ⇄ Acoustics</button>
            <button onclick="applyCrawlPair('earth', 'mars')" data-pair="earth-mars" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">Earth ⇄ Mars</button>
            <button onclick="applyCrawlPair('nasa', 'biology')" data-pair="nasa-biology" class="crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer">NASA ⇄ Biology</button>
          </div>"""

if old_presets in content:
    content = content.replace(old_presets, new_presets)
    print("✔ Replaced Presets with Paired Presets")

# 4. Patch JS Controller
old_js_presets = """    function applyCrawlPreset(pill) {
      const tgtInput = document.getElementById('crawl-target-input');
      if (tgtInput) tgtInput.value = pill;
      document.querySelectorAll('.crawl-preset-pill').forEach(btn => {
        if (btn.getAttribute('data-preset') === pill) {
          btn.className = "crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-emerald-950/80 border-emerald-500/50 text-emerald-300 transition-colors cursor-pointer";
        } else {
          btn.className = "crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer";
        }
      });
      triggerSwansonCrawl();
    }"""

new_js_presets = """    function applyCrawlPair(src, tgt) {
      const srcInput = document.getElementById('crawl-source-input');
      const tgtInput = document.getElementById('crawl-target-input');
      if (srcInput) srcInput.value = src;
      if (tgtInput) tgtInput.value = tgt;
      document.querySelectorAll('.crawl-preset-pill').forEach(btn => {
        const pair = btn.getAttribute('data-pair');
        if (pair === `${src}-${tgt}` || pair === `${src}-${tgt.replace('_s_island', '')}`) {
          btn.className = "crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-emerald-950/80 border-emerald-500/50 text-emerald-300 transition-colors cursor-pointer";
        } else {
          btn.className = "crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer";
        }
      });
      triggerSwansonCrawl();
    }

    function resetSwansonCrawl() {
      const srcInput = document.getElementById('crawl-source-input');
      const tgtInput = document.getElementById('crawl-target-input');
      const filterInput = document.getElementById('crawl-filter-input');
      const srcDisplay = document.getElementById('crawl-src-display');
      const tgtDisplay = document.getElementById('crawl-tgt-display');
      const latencyBadge = document.getElementById('crawl-latency-badge');
      const countBadge = document.getElementById('crawl-count-badge');
      const listCount = document.getElementById('crawl-list-count');
      const nodesList = document.getElementById('crawl-nodes-list');
      const proseEmpty = document.getElementById('crawl-prose-empty');
      const proseContent = document.getElementById('crawl-prose-content');
      const proseLoading = document.getElementById('crawl-prose-loading');
      const executeBtn = document.getElementById('crawl-execute-btn');
      const btnLabel = document.getElementById('crawl-btn-label');
      const spinIcon = document.getElementById('crawl-spin-icon');

      if (srcInput) srcInput.value = '';
      if (tgtInput) tgtInput.value = '';
      if (filterInput) filterInput.value = '';
      if (srcDisplay) srcDisplay.textContent = '--';
      if (tgtDisplay) tgtDisplay.textContent = '--';
      if (latencyBadge) latencyBadge.textContent = '-- µs';
      if (countBadge) countBadge.textContent = '--';
      if (listCount) listCount.textContent = '--';

      if (nodesList) {
        nodesList.innerHTML = `
          <div class="p-8 text-center bg-surface rounded-xl border border-white/10 text-xs font-mono text-zinc-500 space-y-2">
            <svg class="w-6 h-6 text-zinc-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <div>Select a preset pair above or enter Source and Target concepts.</div>
          </div>
        `;
      }

      if (proseEmpty) {
        proseEmpty.textContent = 'Select a bridge node or run a crawl to inspect article prose.';
        proseEmpty.classList.remove('hidden');
      }
      if (proseContent) proseContent.classList.add('hidden');
      if (proseLoading) proseLoading.classList.add('hidden');

      if (btnLabel) btnLabel.textContent = 'Execute Crawl';
      if (spinIcon) spinIcon.classList.remove('animate-spin');
      if (executeBtn) executeBtn.disabled = false;

      document.querySelectorAll('.crawl-preset-pill').forEach(btn => {
        btn.className = "crawl-preset-pill text-[11px] font-mono px-2 py-0.5 rounded border bg-black/40 border-white/5 text-zinc-400 hover:text-white hover:border-white/10 transition-colors cursor-pointer";
      });

      crawlActiveSlug = null;
    }"""

if old_js_presets in content:
    content = content.replace(old_js_presets, new_js_presets)
    print("✔ Replaced JS presets with applyCrawlPair & resetSwansonCrawl")

# 5. Patch triggerSwansonCrawl for immediate loading skeleton & in-situ error card
old_trigger = """      if (btnLabel) btnLabel.textContent = 'Traversing Graph...';
      if (spinIcon) spinIcon.classList.add('animate-spin');
      if (executeBtn) executeBtn.disabled = true;

      const srcDisplay = document.getElementById('crawl-src-display');
      const tgtDisplay = document.getElementById('crawl-tgt-display');
      if (srcDisplay) srcDisplay.textContent = src;
      if (tgtDisplay) tgtDisplay.textContent = tgt;

      try {
        const payload = { source: src, target: tgt, mode: mode };
        if (filter) payload.filter = filter;

        let res = await fetch('/api/wiki/swanson_crawl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          res = await fetch('/api/cockpit/wiki/swanson_crawl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
        }

        if (!res.ok) {
          const errData = await res.json();
          alert(`Crawl failed: ${errData.detail || errData.error || 'Concept not found'}`);
          return;
        }

        const data = await res.json();
        renderCrawlResults(data);
      } catch (err) {
        console.error('Swanson Crawl error:', err);
      } finally {"""

new_trigger = """      if (btnLabel) btnLabel.textContent = 'Traversing...';
      if (spinIcon) spinIcon.classList.add('animate-spin');
      if (executeBtn) executeBtn.disabled = true;

      const nodesList = document.getElementById('crawl-nodes-list');
      const countBadge = document.getElementById('crawl-count-badge');
      const latencyBadge = document.getElementById('crawl-latency-badge');
      const listCount = document.getElementById('crawl-list-count');

      // Immediate loading skeleton to prevent state desync
      if (nodesList) {
        nodesList.innerHTML = `
          <div class="p-8 text-center bg-surface/80 rounded-xl border border-emerald-500/20 text-xs font-mono space-y-3 animate-pulse">
            <div class="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <div class="text-emerald-300 font-semibold">Traversing POSIX VFS Graph Topology...</div>
            <div class="text-[11px] text-zinc-500">${mode === 'path' ? 'Computing multi-hop shortest path via BFS' : 'Resolving transitive bridges (A ∩ C)'}</div>
          </div>
        `;
      }
      if (countBadge) countBadge.textContent = 'Traversing...';
      if (latencyBadge) latencyBadge.textContent = '...';
      if (listCount) listCount.textContent = '...';

      const srcDisplay = document.getElementById('crawl-src-display');
      const tgtDisplay = document.getElementById('crawl-tgt-display');
      if (srcDisplay) srcDisplay.textContent = src;
      if (tgtDisplay) tgtDisplay.textContent = tgt;

      try {
        const payload = { source: src, target: tgt, mode: mode };
        if (filter) payload.filter = filter;

        let res = await fetch('/api/wiki/swanson_crawl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          res = await fetch('/api/cockpit/wiki/swanson_crawl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
        }

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData.detail || errData.error || 'Concept not found';
          if (nodesList) {
            nodesList.innerHTML = `
              <div class="p-6 text-center bg-surface rounded-xl border border-amber-500/30 text-xs font-mono space-y-2">
                <div class="text-amber-400 font-semibold">Graph Traversal Halted</div>
                <div class="text-zinc-300 text-xs">${errMsg}</div>
                <div class="text-zinc-500 text-[10px] pt-1">Verify concepts exist in VFS graph. Use autocomplete suggestions.</div>
              </div>
            `;
          }
          if (countBadge) countBadge.textContent = '0 Results';
          if (latencyBadge) latencyBadge.textContent = '--';
          return;
        }

        const data = await res.json();
        renderCrawlResults(data);
      } catch (err) {
        console.error('Swanson Crawl error:', err);
        if (nodesList) {
          nodesList.innerHTML = `
            <div class="p-6 text-center bg-surface rounded-xl border border-red-500/30 text-xs font-mono space-y-2">
              <div class="text-red-400 font-semibold">Network or Traversal Error</div>
              <div class="text-zinc-400 text-xs">Request timed out or backend error occurred.</div>
            </div>
          `;
        }
      } finally {"""

if old_trigger in content:
    content = content.replace(old_trigger, new_trigger)
    print("✔ Patched triggerSwansonCrawl with loading skeleton and in-situ error card")

TARGET.write_text(content, encoding="utf-8")
print(f"✔ Successfully saved {TARGET}")
