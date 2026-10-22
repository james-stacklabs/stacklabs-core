#!/home/james/stacklabs/.venv/bin/python3
"""
Deterministic patcher to mount vault_explorer_router in scripts/synapse_bus.py
and add the Vault Explorer tab (#tab-vault / #view-vault) to scripts/templates/cockpit.html.
"""

from pathlib import Path

SYNAPSE_PATH = Path("/home/james/stacklabs/scripts/synapse_bus.py")
COCKPIT_HTML_PATH = Path("/home/james/stacklabs/scripts/templates/cockpit.html")


def patch_synapse_bus() -> None:
    text = SYNAPSE_PATH.read_text(encoding="utf-8")
    if "vault_explorer_router" in text:
        print("[patch_synapse_bus] vault_explorer_router already mounted.")
        return

    anchor = """# Mount Drive Sync Telemetry Router
try:
    from scripts.blueprints.drive_sync_api import drive_sync_router
    app.include_router(drive_sync_router)
    logger.info("Successfully mounted drive_sync_router on Port 8088 (/api/cockpit/drive_sync)")
except Exception as e:
    logger.error(f"Failed to mount drive_sync_router on synapse_bus: {e}")"""

    replacement = anchor + """

# Mount Vault Explorer & IDE Brain Harvester Router
try:
    from scripts.blueprints.vault_explorer_api import vault_explorer_router
    app.include_router(vault_explorer_router)
    logger.info("Successfully mounted vault_explorer_router on Port 8088 (/api/cockpit/vault)")
except Exception as e:
    logger.error(f"Failed to mount vault_explorer_router on synapse_bus: {e}")"""

    if anchor not in text:
        raise RuntimeError("Could not locate drive_sync_router mount anchor in scripts/synapse_bus.py")

    SYNAPSE_PATH.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
    print("[patch_synapse_bus] Successfully mounted vault_explorer_router.")


def patch_cockpit_html() -> None:
    html = COCKPIT_HTML_PATH.read_text(encoding="utf-8")
    if 'id="tab-vault"' in html:
        print("[patch_cockpit_html] Vault Explorer tab already present in cockpit.html.")
        return

    # 1. Add Vault Explorer button to top nav bar
    nav_anchor = """      <button onclick="switchTab('crawl')" id="tab-crawl" class="px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 text-zinc-400 hover:text-zinc-200 shrink-0 whitespace-nowrap">
        <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
        <span>Swanson Crawl</span>
      </button>"""

    nav_replacement = nav_anchor + """
      <button onclick="switchTab('vault')" id="tab-vault" class="px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 text-zinc-400 hover:text-zinc-200 shrink-0 whitespace-nowrap">
        <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
        <span>Vault Explorer</span>
      </button>"""

    if nav_anchor not in html:
        raise RuntimeError("Could not find tab-crawl nav anchor in cockpit.html")
    html = html.replace(nav_anchor, nav_replacement, 1)

    # 2. Add <section id="view-vault"> right before </main>
    vault_section = """    <!-- TAB 6: VAULT EXPLORER & IDE BRAIN HARVESTER -->
    <section id="view-vault" class="hidden space-y-5">
      <!-- Top Control & Search Bar -->
      <div class="bg-surface border border-white/10 rounded-xl p-5 space-y-4">
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/5 pb-4">
          <div class="space-y-1">
            <div class="flex items-center gap-3 flex-wrap">
              <h2 class="text-base font-semibold text-white">StackLabs Vault Navigator &amp; IDE Brain Explorer</h2>
              <span id="vault-total-badge" class="text-[11px] font-mono px-2.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">8 Categories</span>
              <span id="vault-latency-badge" class="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">-- ms</span>
            </div>
            <p class="text-xs font-mono text-zinc-400">Unified VFS tree (/home/james/stacklabs/vault_navigator/) • Sprints, Walkthroughs, Plans, IDE Brain, Work Orders, Dossiers, Personas &amp; Ground Truth</p>
          </div>
          <div class="flex items-center gap-2.5 shrink-0 flex-wrap">
            <button onclick="harvestIdeBrainNow()" id="vault-harvest-btn" class="px-3.5 py-2 rounded-lg text-xs font-mono font-semibold text-purple-200 hover:text-white bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/40 transition-colors flex items-center gap-2 cursor-pointer">
              <svg id="vault-harvest-icon" class="w-3.5 h-3.5 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              <span id="vault-harvest-label">Harvest IDE Brain</span>
            </button>
            <button onclick="loadVaultTree()" class="px-3.5 py-2 rounded-lg text-xs font-mono text-zinc-300 hover:text-white bg-black/40 hover:bg-white/5 border border-white/10 transition-colors cursor-pointer">
              Refresh Tree
            </button>
          </div>
        </div>

        <!-- Search Input + Category Filter Pills -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-3 items-center">
          <div class="lg:col-span-5 relative">
            <input type="text" id="vault-search-input" oninput="debounceVaultSearch()" onkeydown="if(event.key==='Enter') runVaultSearch()" placeholder="Search filenames, titles, or full text (e.g. 'Bauers', 'WO0011153', 'barf', 'sprint')..." class="w-full bg-black/50 border border-white/10 focus:border-cyan-500/50 rounded-lg pl-9 pr-20 py-2 text-xs font-mono text-white placeholder-zinc-500 focus:outline-none">
            <svg class="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <button onclick="clearVaultSearch()" class="absolute right-2.5 top-1.5 px-2 py-1 text-[10px] font-mono text-zinc-400 hover:text-white bg-white/5 rounded">Clear</button>
          </div>
          <div id="vault-category-pills" class="lg:col-span-7 flex items-center gap-1.5 flex-wrap">
            <button onclick="selectVaultCategory('ALL')" data-cat="ALL" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-cyan-950/80 border-cyan-500/50 text-cyan-300 cursor-pointer">All (8)</button>
            <button onclick="selectVaultCategory('01_Daily_Sprints')" data-cat="01_Daily_Sprints" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">01 Sprints</button>
            <button onclick="selectVaultCategory('02_Walkthroughs')" data-cat="02_Walkthroughs" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">02 Walkthroughs</button>
            <button onclick="selectVaultCategory('03_Implementation_Plans_and_Specs')" data-cat="03_Implementation_Plans_and_Specs" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">03 Plans</button>
            <button onclick="selectVaultCategory('04_IDE_Brain_Artifacts')" data-cat="04_IDE_Brain_Artifacts" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">04 IDE Brain</button>
            <button onclick="selectVaultCategory('05_Work_Orders')" data-cat="05_Work_Orders" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">05 Work Orders</button>
            <button onclick="selectVaultCategory('06_Executive_Dossiers')" data-cat="06_Executive_Dossiers" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">06 Dossiers</button>
            <button onclick="selectVaultCategory('07_Personas_and_Advocates')" data-cat="07_Personas_and_Advocates" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">07 Personas</button>
            <button onclick="selectVaultCategory('08_Mycroft_Ground_Truth')" data-cat="08_Mycroft_Ground_Truth" class="vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer">08 Ground Truth</button>
          </div>
        </div>
      </div>

      <!-- Main Split Pane: Left Topology Tree + File List (5 Cols) | Right Document Reader (7 Cols) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left Drill-Down Column -->
        <div class="lg:col-span-5 space-y-4">
          <!-- Category & Subfolder Drill-Down Accordion -->
          <div class="bg-surface border border-white/10 rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between border-b border-white/5 pb-2.5">
              <span class="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">1. Category &amp; Folder Topology</span>
              <span id="vault-active-breadcrumb" class="text-[11px] font-mono text-zinc-400 truncate max-w-[220px]">01_Daily_Sprints / LATEST_SPRINT</span>
            </div>
            <div id="vault-tree-container" class="space-y-1.5 max-h-[270px] overflow-y-auto pr-1">
              <p class="text-xs font-mono text-zinc-500 p-2">Loading Vault Navigator tree...</p>
            </div>
          </div>

          <!-- Files in Selected Folder / Search Results -->
          <div class="bg-surface border border-white/10 rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between border-b border-white/5 pb-2.5">
              <span id="vault-filelist-heading" class="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">2. Files in Selected Folder</span>
              <span id="vault-filelist-count" class="text-[11px] font-mono text-zinc-400">0 files</span>
            </div>
            <div id="vault-files-container" class="space-y-1.5 max-h-[420px] overflow-y-auto pr-1">
              <p class="text-xs font-mono text-zinc-500 p-2">Select a folder above or run a search...</p>
            </div>
          </div>
        </div>

        <!-- Right Document Reader Pane -->
        <div class="lg:col-span-7 bg-surface border border-white/10 rounded-xl p-5 flex flex-col justify-between min-h-[680px]">
          <div class="space-y-4">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/10 pb-3">
              <div class="min-w-0">
                <h3 id="vault-reader-title" class="text-sm font-bold text-white font-mono truncate">Select any file from the Vault Tree to inspect</h3>
                <p id="vault-reader-path" class="text-[11px] font-mono text-zinc-500 truncate mt-0.5">/home/james/stacklabs/vault_navigator/</p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span id="vault-reader-meta" class="text-[10px] font-mono px-2 py-0.5 rounded bg-black/40 border border-white/10 text-zinc-400">--</span>
                <button onclick="copyVaultFilePath()" id="vault-copy-path-btn" class="px-2.5 py-1 rounded text-[11px] font-mono text-zinc-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors cursor-pointer">Copy Path</button>
                <button onclick="copyVaultFileContent()" id="vault-copy-content-btn" class="px-2.5 py-1 rounded text-[11px] font-mono text-emerald-300 hover:text-white bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors cursor-pointer">Copy Content</button>
              </div>
            </div>
            <div id="vault-reader-body" class="bg-black/50 border border-white/5 rounded-xl p-4 font-mono text-xs text-zinc-200 overflow-y-auto max-h-[600px] whitespace-pre-wrap leading-relaxed">Select a Daily Sprint file, Walkthrough, Implementation Plan, IDE Brain Artifact, Persona SKILL.md, or Ground Truth document on the left to read its contents here.</div>
          </div>
        </div>
      </div>
    </section>
  </main>"""

    if "  </main>" not in html:
        raise RuntimeError("Could not locate </main> in cockpit.html")
    html = html.replace("  </main>", vault_section, 1)

    # 3. Update switchTab(tab) to support 'vault'
    switch_hide_anchor = "      document.getElementById('view-crawl').classList.add('hidden');"
    switch_hide_rep = switch_hide_anchor + "\n      const vVault = document.getElementById('view-vault'); if (vVault) vVault.classList.add('hidden');"
    html = html.replace(switch_hide_anchor, switch_hide_rep, 1)

    switch_tab_anchor = "      document.getElementById('tab-crawl').className = \"px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 text-zinc-400 hover:text-zinc-200 shrink-0 whitespace-nowrap\";"
    switch_tab_rep = switch_tab_anchor + "\n      const tVault = document.getElementById('tab-vault'); if (tVault) tVault.className = \"px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 text-zinc-400 hover:text-zinc-200 shrink-0 whitespace-nowrap\";"
    html = html.replace(switch_tab_anchor, switch_tab_rep, 1)

    crawl_branch_anchor = """      } else if (tab === 'crawl') {
        document.getElementById('view-crawl').classList.remove('hidden');
        document.getElementById('tab-crawl').className = "px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 bg-white/10 text-white shadow-sm border border-white/10 shrink-0 whitespace-nowrap";
        if (!crawlLoadedOnce) {
          crawlLoadedOnce = true;
          triggerSwansonCrawl();
        }
      }"""

    crawl_branch_rep = crawl_branch_anchor + """ else if (tab === 'vault') {
        document.getElementById('view-vault').classList.remove('hidden');
        document.getElementById('tab-vault').className = "px-3 md:px-4 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-2 bg-white/10 text-white shadow-sm border border-white/10 shrink-0 whitespace-nowrap";
        if (!vaultLoadedOnce) {
          vaultLoadedOnce = true;
          loadVaultTree();
        }
      }"""

    if crawl_branch_anchor not in html:
        raise RuntimeError("Could not find crawl branch in switchTab")
    html = html.replace(crawl_branch_anchor, crawl_branch_rep, 1)

    # 4. Append Vault Explorer JS functions before </script>
    vault_js = """
    let vaultLoadedOnce = false;
    let vaultTreeData = [];
    let vaultSelectedCategory = 'ALL';
    let vaultCurrentFileContent = '';
    let vaultCurrentFilePath = '';
    let vaultSearchTimer = null;

    function escapeHtmlVault(str) {
      return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    async function loadVaultTree() {
      try {
        const res = await fetch('/api/cockpit/vault/tree');
        if (!res.ok) return;
        const data = await res.json();
        vaultTreeData = data.categories || [];
        const totalBadge = document.getElementById('vault-total-badge');
        const latBadge = document.getElementById('vault-latency-badge');
        if (totalBadge) totalBadge.textContent = `${data.total_files || 0} Indexed Files`;
        if (latBadge) latBadge.textContent = `${data.latency_ms || 0} ms`;
        renderVaultTree();
        await openVaultFolder('01_Daily_Sprints', 'LATEST_SPRINT');
      } catch (e) {
        console.error('loadVaultTree error:', e);
      }
    }

    function renderVaultTree() {
      const container = document.getElementById('vault-tree-container');
      if (!container) return;
      const filteredCats = vaultSelectedCategory === 'ALL'
        ? vaultTreeData
        : vaultTreeData.filter(c => c.id === vaultSelectedCategory);

      container.innerHTML = filteredCats.map(cat => {
        const subs = (cat.subfolders || []).slice(0, 25);
        const subButtons = subs.map(sub => `
          <button onclick="openVaultFolder('${cat.id}', '${sub.rel_subcategory}')" class="px-2 py-1 rounded text-[11px] font-mono bg-black/40 hover:bg-cyan-950/60 border border-white/5 hover:border-cyan-500/40 text-zinc-300 hover:text-cyan-200 transition-colors flex items-center gap-1.5 cursor-pointer">
            <span>${escapeHtmlVault(sub.name)}</span>
            <span class="text-[10px] text-zinc-500">(${sub.file_count})</span>
          </button>
        `).join('');

        return `
          <div class="bg-black/30 border border-white/5 rounded-lg p-2.5 space-y-2">
            <div class="flex items-center justify-between cursor-pointer" onclick="openVaultFolder('${cat.id}', '')">
              <div class="flex items-center gap-2 min-w-0">
                <svg class="w-3.5 h-3.5 text-cyan-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
                <span class="text-xs font-mono font-semibold text-white hover:text-cyan-300 truncate">${escapeHtmlVault(cat.label)}</span>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-400 border border-white/5 shrink-0">${cat.file_count} files</span>
            </div>
            ${subs.length > 0 ? `<div class="flex flex-wrap gap-1.5 pl-4 pt-1">${subButtons}</div>` : ''}
          </div>
        `;
      }).join('');
    }

    async function openVaultFolder(category, subcategory) {
      const bc = document.getElementById('vault-active-breadcrumb');
      const heading = document.getElementById('vault-filelist-heading');
      if (bc) bc.textContent = subcategory ? `${category} / ${subcategory}` : category;
      if (heading) heading.textContent = subcategory ? `Files in ${subcategory}` : `Files in ${category}`;

      try {
        const url = `/api/cockpit/vault/folder?category=${encodeURIComponent(category)}&subcategory=${encodeURIComponent(subcategory || '')}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();
        renderVaultFileList(data.files || [], false);
        if (data.files && data.files.length > 0) {
          inspectVaultFile(data.files[0].abs_path);
        }
      } catch (e) {
        console.error('openVaultFolder error:', e);
      }
    }

    function selectVaultCategory(catId) {
      vaultSelectedCategory = catId;
      document.querySelectorAll('.vault-cat-pill').forEach(btn => {
        if (btn.getAttribute('data-cat') === catId) {
          btn.className = "vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-cyan-950/80 border-cyan-500/50 text-cyan-300 cursor-pointer";
        } else {
          btn.className = "vault-cat-pill px-2.5 py-1 rounded text-[11px] font-mono border bg-black/40 border-white/10 text-zinc-400 hover:text-white cursor-pointer";
        }
      });
      renderVaultTree();
      const q = (document.getElementById('vault-search-input')?.value || '').trim();
      if (q) {
        runVaultSearch();
      } else if (catId !== 'ALL') {
        openVaultFolder(catId, '');
      }
    }

    function debounceVaultSearch() {
      if (vaultSearchTimer) clearTimeout(vaultSearchTimer);
      vaultSearchTimer = setTimeout(() => {
        runVaultSearch();
      }, 200);
    }

    function clearVaultSearch() {
      const inp = document.getElementById('vault-search-input');
      if (inp) inp.value = '';
      openVaultFolder(vaultSelectedCategory === 'ALL' ? '01_Daily_Sprints' : vaultSelectedCategory, vaultSelectedCategory === 'ALL' ? 'LATEST_SPRINT' : '');
    }

    async function runVaultSearch() {
      const q = (document.getElementById('vault-search-input')?.value || '').trim();
      const heading = document.getElementById('vault-filelist-heading');
      const latBadge = document.getElementById('vault-latency-badge');
      if (heading) heading.textContent = q ? `Search Results for "${q}"` : 'Recent Files';

      try {
        const url = `/api/cockpit/vault/search?q=${encodeURIComponent(q)}&category=${encodeURIComponent(vaultSelectedCategory)}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();
        if (latBadge) latBadge.textContent = `${data.latency_ms || 0} ms`;
        renderVaultFileList(data.results || [], Boolean(q));
      } catch (e) {
        console.error('runVaultSearch error:', e);
      }
    }

    function renderVaultFileList(files, isSearch) {
      const container = document.getElementById('vault-files-container');
      const countEl = document.getElementById('vault-filelist-count');
      if (countEl) countEl.textContent = `${files.length} files`;
      if (!container) return;

      if (!files.length) {
        container.innerHTML = '<p class="text-xs font-mono text-zinc-500 p-3">No matching files found in this view.</p>';
        return;
      }

      container.innerHTML = files.map(f => {
        const safePath = f.abs_path.replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
        const snip = isSearch && f.snippet
          ? `<div class="text-[11px] font-mono text-emerald-400/90 truncate mt-1">${escapeHtmlVault(f.snippet)}</div>`
          : '';
        return `
          <div onclick="inspectVaultFile('${safePath}')" class="p-2.5 rounded-lg bg-black/30 hover:bg-white/[0.04] border border-white/5 hover:border-cyan-500/40 transition-all cursor-pointer group">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-mono font-semibold text-white group-hover:text-cyan-300 truncate">${escapeHtmlVault(f.title || f.name)}</span>
              <span class="text-[10px] font-mono text-zinc-500 shrink-0">${escapeHtmlVault(f.size_human)}</span>
            </div>
            <div class="flex items-center justify-between gap-2 mt-1 text-[10px] font-mono text-zinc-400">
              <span class="truncate">${escapeHtmlVault(f.rel_path || f.name)}</span>
              <span class="shrink-0 text-zinc-500">${escapeHtmlVault(f.mtime_edt)}</span>
            </div>
            ${snip}
          </div>
        `;
      }).join('');
    }

    async function inspectVaultFile(absPath) {
      const titleEl = document.getElementById('vault-reader-title');
      const pathEl = document.getElementById('vault-reader-path');
      const metaEl = document.getElementById('vault-reader-meta');
      const bodyEl = document.getElementById('vault-reader-body');

      if (bodyEl) bodyEl.textContent = 'Loading file...';
      try {
        const res = await fetch(`/api/cockpit/vault/file?path=${encodeURIComponent(absPath)}`);
        if (!res.ok) {
          if (bodyEl) bodyEl.textContent = 'Error loading file content.';
          return;
        }
        const data = await res.json();
        vaultCurrentFileContent = data.content || '';
        vaultCurrentFilePath = data.abs_path || absPath;
        if (titleEl) titleEl.textContent = data.title || data.name;
        if (pathEl) pathEl.textContent = data.abs_path;
        if (metaEl) metaEl.textContent = `${data.size_human} • ${data.line_count} lines • ${data.mtime_edt}`;
        if (bodyEl) bodyEl.textContent = vaultCurrentFileContent;
      } catch (e) {
        if (bodyEl) bodyEl.textContent = 'Network error loading file.';
      }
    }

    async function harvestIdeBrainNow() {
      const btn = document.getElementById('vault-harvest-btn');
      const label = document.getElementById('vault-harvest-label');
      const icon = document.getElementById('vault-harvest-icon');
      if (btn) btn.disabled = true;
      if (label) label.textContent = 'Harvesting Brain...';
      if (icon) icon.classList.add('animate-spin');

      try {
        const res = await fetch('/api/cockpit/vault/harvest', { method: 'POST' });
        const data = await res.json();
        if (label) label.textContent = `Harvested ${data.brain_markdown_harvested || 0} Docs!`;
        await loadVaultTree();
        await openVaultFolder('04_IDE_Brain_Artifacts', '');
      } catch (e) {
        if (label) label.textContent = 'Harvest Failed';
      } finally {
        if (icon) icon.classList.remove('animate-spin');
        if (btn) btn.disabled = false;
        setTimeout(() => {
          if (label) label.textContent = 'Harvest IDE Brain';
        }, 3500);
      }
    }

    async function copyVaultFilePath() {
      if (!vaultCurrentFilePath) return;
      const btn = document.getElementById('vault-copy-path-btn');
      await navigator.clipboard.writeText(vaultCurrentFilePath);
      if (btn) {
        btn.textContent = '✓ Path Copied';
        setTimeout(() => { btn.textContent = 'Copy Path'; }, 2000);
      }
    }

    async function copyVaultFileContent() {
      if (!vaultCurrentFileContent) return;
      const btn = document.getElementById('vault-copy-content-btn');
      await navigator.clipboard.writeText(vaultCurrentFileContent);
      if (btn) {
        btn.textContent = '✓ Content Copied';
        setTimeout(() => { btn.textContent = 'Copy Content'; }, 2000);
      }
    }
"""

    script_end_anchor = "    loadDriveSyncStatus();\n  </script>"
    if script_end_anchor not in html:
        raise RuntimeError("Could not find loadDriveSyncStatus(); </script> anchor in cockpit.html")
    html = html.replace(script_end_anchor, vault_js + "\n    " + script_end_anchor, 1)

    COCKPIT_HTML_PATH.write_text(html, encoding="utf-8")
    print("[patch_cockpit_html] Successfully added Vault Explorer tab and script handlers.")


if __name__ == "__main__":
    patch_synapse_bus()
    patch_cockpit_html()
