#!/home/james/stacklabs/.venv/bin/python3
"""
Patches scripts/templates/cockpit.html to add 1-Click 'Copy NotebookLM File IDs' button
and clickable Google Drive File ID links in the Active NotebookLM & Drive Source Inventory table.
"""

import sys
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
COCKPIT_HTML_PATH = REPO_ROOT / "scripts" / "templates" / "cockpit.html"


def patch_cockpit_html() -> None:
    html = COCKPIT_HTML_PATH.read_text(encoding="utf-8")

    # 1. Add Copy NotebookLM File IDs button next to Refresh Inventory
    old_btns = """          <div class="flex items-center gap-2.5 shrink-0">
            <button onclick="loadDriveSyncStatus()" id="drive-refresh-btn" class="px-3.5 py-2 rounded-lg text-xs font-mono text-zinc-300 hover:text-white bg-black/40 hover:bg-white/5 border border-white/10 transition-colors cursor-pointer">
              Refresh Inventory
            </button>"""

    new_btns = """          <div class="flex items-center gap-2.5 shrink-0 flex-wrap">
            <button onclick="copyNotebookLmPrompt()" id="copy-notebooklm-btn" class="px-3.5 py-2 rounded-lg text-xs font-mono text-emerald-300 hover:text-white bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors cursor-pointer">
              Copy NotebookLM File IDs
            </button>
            <button onclick="loadDriveSyncStatus(true)" id="drive-refresh-btn" class="px-3.5 py-2 rounded-lg text-xs font-mono text-zinc-300 hover:text-white bg-black/40 hover:bg-white/5 border border-white/10 transition-colors cursor-pointer">
              Refresh Inventory
            </button>"""

    if "copy-notebooklm-btn" not in html and old_btns in html:
        html = html.replace(old_btns, new_btns, 1)

    # 2. Update table header STAGING -> DRIVE FILE ID / LINK
    html = html.replace('<th class="py-2 px-2 text-right">STAGING</th>', '<th class="py-2 px-2 text-right">DRIVE FILE ID</th>')

    # 3. Update JS row rendering and add copyNotebookLmPrompt()
    old_js_marker = "    let driveSyncPollTimer = null;"
    end_js_marker = "    async function snipeYouTube() {"
    s_idx = html.find(old_js_marker)
    e_idx = html.find(end_js_marker)
    if s_idx == -1 or e_idx == -1:
        raise RuntimeError("Could not locate Drive Sync JS block in cockpit.html")

    new_drive_js = """    let driveSyncPollTimer = null;
    let latestNotebookLmPrompt = "";

    async function copyNotebookLmPrompt() {
      const btn = document.getElementById('copy-notebooklm-btn');
      if (!latestNotebookLmPrompt) {
        await loadDriveSyncStatus(true);
      }
      if (!latestNotebookLmPrompt) return;
      try {
        await navigator.clipboard.writeText(latestNotebookLmPrompt);
        if (btn) {
          btn.textContent = '✓ Copied 16 Drive File IDs!';
          setTimeout(() => { btn.textContent = 'Copy NotebookLM File IDs'; }, 3000);
        }
      } catch (e) {
        if (btn) {
          btn.textContent = 'Copy Failed';
          setTimeout(() => { btn.textContent = 'Copy NotebookLM File IDs'; }, 3000);
        }
      }
    }

    function renderDriveSyncStatus(data) {
      if (!data || !data.inventory) return;
      const state = data.state || 'IDLE';
      const badge = document.getElementById('drive-sync-state-badge');
      const linterBadge = document.getElementById('drive-sync-linter-badge');
      const metaLine = document.getElementById('drive-sync-meta-line');
      const btn = document.getElementById('sync-trigger-btn');
      const btnLabel = document.getElementById('sync-trigger-label');
      const spinner = document.getElementById('sync-spinner-icon');
      const logDot = document.getElementById('drive-log-dot');
      const taskIdEl = document.getElementById('drive-log-task-id');

      const durSec = ((data.duration_ms || 0) / 1000).toFixed(2);

      if (state === 'RUNNING') {
        if (badge) {
          badge.textContent = `SYNCING (${durSec}s)`;
          badge.className = 'text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse';
        }
        if (btn) btn.disabled = true;
        if (btnLabel) btnLabel.textContent = `Syncing (${durSec}s)...`;
        if (spinner) spinner.classList.remove('hidden');
        if (logDot) logDot.className = 'w-2 h-2 rounded-full bg-blue-400 animate-ping';
      } else if (state === 'SUCCESS') {
        if (badge) {
          badge.textContent = `SYNC COMPLETE (${durSec}s)`;
          badge.className = 'text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
        }
        if (btn) btn.disabled = false;
        if (btnLabel) btnLabel.textContent = 'Trigger Remote Sync';
        if (spinner) spinner.classList.add('hidden');
        if (logDot) logDot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      } else if (state === 'FAILED') {
        if (badge) {
          badge.textContent = `SYNC FAILED (Exit ${data.exit_code ?? -1})`;
          badge.className = 'text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30';
        }
        if (btn) btn.disabled = false;
        if (btnLabel) btnLabel.textContent = 'Retry Remote Sync';
        if (spinner) spinner.classList.add('hidden');
        if (logDot) logDot.className = 'w-2 h-2 rounded-full bg-red-400';
      } else {
        if (badge) {
          badge.textContent = 'IDLE • READY';
          badge.className = 'text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10';
        }
        if (btn) btn.disabled = false;
        if (btnLabel) btnLabel.textContent = 'Trigger Remote Sync';
        if (spinner) spinner.classList.add('hidden');
        if (logDot) logDot.className = 'w-2 h-2 rounded-full bg-emerald-400';
      }

      if (linterBadge) {
        if (data.linter_status === 'FAILED') {
          linterBadge.textContent = 'OPSEC & Linter Gate: BLOCKED';
          linterBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20';
        } else {
          linterBadge.textContent = 'OPSEC & Linter Gate: PASSED';
          linterBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        }
      }

      if (metaLine) {
        const lastTs = data.finished_at || data.started_at || 'Ready on demand';
        const rcText = data.exit_code !== null && data.exit_code !== undefined ? ` • Exit Code: ${data.exit_code}` : '';
        const durText = data.duration_ms ? ` • Duration: ${durSec}s` : '';
        metaLine.textContent = `Last Verified Sync: ${lastTs}${durText}${rcText}`;
      }

      if (taskIdEl && data.task_id) {
        taskIdEl.textContent = data.task_id;
      }

      const inv = data.inventory;
      latestNotebookLmPrompt = inv.notebooklm_prompt || "";

      const sprintSum = document.getElementById('edge-sprint-summary');
      const mycroftSum = document.getElementById('edge-mycroft-summary');
      const folderLbl = document.getElementById('edge-sprint-folder-label');
      const invFolderBadge = document.getElementById('drive-inventory-folder-badge');
      const invCountBadge = document.getElementById('drive-inventory-count-badge');

      if (sprintSum) sprintSum.textContent = `${inv.sprint_count} files (${inv.sprint_size_human})`;
      if (mycroftSum) mycroftSum.textContent = `${inv.mycroft_count} files (${inv.mycroft_size_human})`;
      if (folderLbl) folderLbl.textContent = `StackLabs_Internal/${inv.sprint_folder}`;
      if (invFolderBadge) invFolderBadge.textContent = inv.sprint_folder;
      if (invCountBadge) invCountBadge.textContent = `${inv.sprint_count + inv.mycroft_count} Active Sources`;

      const tbody = document.getElementById('drive-inventory-tbody');
      if (tbody) {
        const rows = [];
        (inv.sprint_files || []).forEach(f => {
          const idHtml = f.drive_file_id
            ? `<a href="${f.drive_url}" target="_blank" rel="noopener" class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:underline" title="Google Drive ID: ${f.drive_file_id}">${f.drive_file_id.slice(0, 10)}…</a>`
            : `<span class="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-zinc-400 border border-white/10">Staged</span>`;
          rows.push(`
            <tr class="hover:bg-white/[0.02]">
              <td class="py-2 px-2 text-white font-semibold truncate max-w-[240px]" title="${f.name}">${f.name}</td>
              <td class="py-2 px-2"><span class="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-300 border border-blue-500/20">Daily Sprint</span></td>
              <td class="py-2 px-2 text-zinc-400">${f.size_human}</td>
              <td class="py-2 px-2 text-zinc-400 text-[11px]">${f.mtime_edt}</td>
              <td class="py-2 px-2 text-right">${idHtml}</td>
            </tr>
          `);
        });
        (inv.mycroft_files || []).forEach(f => {
          const idHtml = f.drive_file_id
            ? `<a href="${f.drive_url}" target="_blank" rel="noopener" class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:underline" title="Google Drive ID: ${f.drive_file_id}">${f.drive_file_id.slice(0, 10)}…</a>`
            : `<span class="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-zinc-400 border border-white/10">Staged</span>`;
          rows.push(`
            <tr class="hover:bg-white/[0.02]">
              <td class="py-2 px-2 text-zinc-200 truncate max-w-[240px]" title="${f.name}">${f.name}</td>
              <td class="py-2 px-2"><span class="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/20">Mycroft GT</span></td>
              <td class="py-2 px-2 text-zinc-400">${f.size_human}</td>
              <td class="py-2 px-2 text-zinc-400 text-[11px]">${f.mtime_edt}</td>
              <td class="py-2 px-2 text-right">${idHtml}</td>
            </tr>
          `);
        });
        tbody.innerHTML = rows.length > 0 ? rows.join('') : '<tr><td colspan="5" class="py-4 text-center text-zinc-500">No sprint or Mycroft sources found.</td></tr>';
      }

      const logBody = document.getElementById('drive-sync-log-body');
      if (logBody && Array.isArray(data.log_lines)) {
        logBody.innerHTML = data.log_lines.map(line => {
          const esc = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          let cls = 'text-zinc-300';
          if (esc.includes('[ERROR]') || esc.includes('[EXCEPTION]') || esc.includes('FAILED')) cls = 'text-red-400 font-semibold';
          else if (esc.includes('[COMPLETE]') || esc.includes('[VERIFIED REMOTE]') || esc.includes('SUCCESS') || esc.includes('PASSED')) cls = 'text-emerald-400';
          else if (esc.includes('[START]') || esc.includes('[PRE-FLIGHT]') || esc.includes('[EXEC]')) cls = 'text-blue-300';
          return `<p class="${cls} leading-relaxed break-words">${esc}</p>`;
        }).join('');
        logBody.scrollTop = logBody.scrollHeight;
      }
    }

    async function loadDriveSyncStatus(refreshIds = false) {
      try {
        const url = refreshIds ? '/api/cockpit/drive_sync/status?refresh_ids=true' : '/api/cockpit/drive_sync/status';
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();
        renderDriveSyncStatus(data);
        if (data.state === 'RUNNING') {
          if (!driveSyncPollTimer) {
            driveSyncPollTimer = setInterval(() => loadDriveSyncStatus(false), 500);
          }
        } else if (driveSyncPollTimer) {
          clearInterval(driveSyncPollTimer);
          driveSyncPollTimer = null;
        }
      } catch (e) {}
    }

    async function triggerRemoteSync() {
      const btn = document.getElementById('sync-trigger-btn');
      const btnLabel = document.getElementById('sync-trigger-label');
      const spinner = document.getElementById('sync-spinner-icon');
      if (btn) btn.disabled = true;
      if (btnLabel) btnLabel.textContent = 'Starting Sync...';
      if (spinner) spinner.classList.remove('hidden');

      try {
        const res = await fetch('/api/cockpit/drive_sync/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sync_all: true })
        });
        await res.json();
        await loadDriveSyncStatus(false);
        if (!driveSyncPollTimer) {
          driveSyncPollTimer = setInterval(() => loadDriveSyncStatus(false), 500);
        }
      } catch (e) {
        if (btn) btn.disabled = false;
        if (btnLabel) btnLabel.textContent = 'Trigger Remote Sync';
        if (spinner) spinner.classList.add('hidden');
      }
    }
"""
    html = html[:s_idx] + new_drive_js + "\n" + html[e_idx:]
    COCKPIT_HTML_PATH.write_text(html, encoding="utf-8")
    print("[OK] Added Copy NotebookLM File IDs button and Drive File ID links to cockpit.html")


if __name__ == "__main__":
    patch_cockpit_html()
