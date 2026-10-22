#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs 4-Panel Essay & Quant Symbiote Workbench Templates (drop.stacklabsllc.com)
Path: /home/james/stacklabs/scripts/dead_drop_templates.py
"""

PASSCODE_GATE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>STACKLABS • Personal VFS Symbiote Workbench</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { darkMode: 'class' };
    function setTheme(mode) {
      if (mode === 'dark') {
        document.documentElement.classList.add('dark');
        localStorage.setItem('stacklabs_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('stacklabs_theme', 'light');
      }
      updateThemeToggleUI(mode);
    }
    function toggleTheme() {
      const isDark = document.documentElement.classList.contains('dark');
      setTheme(isDark ? 'light' : 'dark');
    }
    function updateThemeToggleUI(mode) {
      const el = document.getElementById('themeToggleText');
      if (!el) return;
      if (mode === 'dark') {
        el.innerHTML = '<span class="text-slate-400">LITE</span> <span class="text-slate-600">/</span> <span class="text-emerald-400 font-semibold">DARK</span>';
      } else {
        el.innerHTML = '<span class="text-[#2E7D32] font-semibold">LITE</span> <span class="text-slate-400">/</span> <span class="text-slate-500">DARK</span>';
      }
    }
    (function() {
      const saved = localStorage.getItem('stacklabs_theme') || 'dark';
      if (saved === 'dark') document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    })();
  </script>
  <style>
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4 bg-[#F4F5F7] dark:bg-[#0B0D13] text-[#212121] dark:text-[#F2F4F7] transition-colors duration-150">
  <div class="max-w-md w-full">
    <div class="rounded-[2px] border-l-[6px] border-l-[#388E3C] dark:border-l-[#10B981] bg-[#FFFFFF] dark:bg-[#11141E] border-y border-r border-[#E0E0E0] dark:border-white/10 shadow-sm p-6 sm:p-8 space-y-6">
      <div class="flex items-center justify-between border-b border-[#E0E0E0] dark:border-white/10 pb-4">
        <span class="text-xs font-mono uppercase tracking-wider text-[#2E7D32] dark:text-emerald-400">Workspace Gate</span>
        <button id="themeToggleBtn" type="button" onclick="toggleTheme()" class="px-2.5 py-1 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[11px] font-mono uppercase tracking-wider cursor-pointer">
          <span id="themeToggleText">LITE / DARK</span>
        </button>
      </div>
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-[#1E293B] dark:text-[#F2F4F7]">STACKLABS •</h1>
        <p class="text-xs font-mono text-[#616161] dark:text-slate-400 mt-1">Essay & Quant Symbiote Workbench</p>
      </div>
      <form id="authForm" method="POST" action="/?{% if from_arg %}from={{ from_arg }}{% endif %}" class="space-y-4">
        <div>
          <label for="passcode" class="block text-[11px] font-mono uppercase tracking-wider text-[#616161] dark:text-slate-400 mb-1.5">Access Key</label>
          <input type="password" id="passcode" name="passcode" required autofocus placeholder="Enter access key..." class="w-full bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 focus:border-[#00796B] dark:focus:border-[#10B981] rounded-[2px] px-3.5 py-2.5 text-sm text-[#212121] dark:text-white font-mono outline-none">
        </div>
        {% if error %}
        <div class="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 rounded-[2px] text-xs text-red-700 dark:text-red-400 font-mono">{{ error }}</div>
        {% endif %}
        <div id="jsError" class="hidden p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 rounded-[2px] text-xs text-red-700 dark:text-red-400 font-mono">
          <span id="jsErrorText">Invalid access key.</span>
        </div>
        <button type="submit" id="authBtn" class="w-full py-3 px-6 rounded-[2px] bg-[#00796B] hover:bg-[#00695C] dark:bg-[#059669] dark:hover:bg-[#047857] text-white font-mono font-medium uppercase tracking-wider text-xs cursor-pointer">
          Unlock Workspace
        </button>
      </form>
      <div class="pt-4 border-t border-[#E0E0E0] dark:border-white/10 text-[10px] font-mono text-center text-[#757575] dark:text-slate-500 uppercase tracking-wider">
        PERSISTENT POSIX VFS WORKSPACE • SHA-256 BIT-PERFECT PROVENANCE
      </div>
    </div>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      updateThemeToggleUI(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    });
    const form = document.getElementById('authForm');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const val = document.getElementById('passcode').value.trim();
      if (!val) return;
      try {
        const res = await fetch('/api/auth', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ key: val })
        });
        const data = await res.json();
        if (res.ok && data.status === 'authenticated') {
          const fromParam = new URLSearchParams(window.location.search).get('from');
          window.location.href = fromParam ? `/?from=${encodeURIComponent(fromParam)}` : '/';
        } else {
          document.getElementById('jsErrorText').innerText = data.message || 'Invalid access key.';
          document.getElementById('jsError').classList.remove('hidden');
        }
      } catch (err) {
        form.submit();
      }
    });
  </script>
</body>
</html>
"""

DROP_PORTAL_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>STACKLABS • Essay & Quant Symbiote Workbench</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = { darkMode: 'class' };
    function setTheme(mode) {
      if (mode === 'dark') {
        document.documentElement.classList.add('dark');
        localStorage.setItem('stacklabs_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('stacklabs_theme', 'light');
      }
      updateThemeToggleUI(mode);
    }
    function toggleTheme() {
      const isDark = document.documentElement.classList.contains('dark');
      setTheme(isDark ? 'light' : 'dark');
    }
    function updateThemeToggleUI(mode) {
      const el = document.getElementById('themeToggleText');
      if (!el) return;
      if (mode === 'dark') {
        el.innerHTML = '<span class="text-slate-400">LITE</span> <span class="text-slate-600">/</span> <span class="text-emerald-400 font-semibold">DARK</span>';
      } else {
        el.innerHTML = '<span class="text-[#2E7D32] font-semibold">LITE</span> <span class="text-slate-400">/</span> <span class="text-slate-500">DARK</span>';
      }
    }
    (function() {
      const saved = localStorage.getItem('stacklabs_theme') || 'dark';
      if (saved === 'dark') document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    })();
  </script>
  <style>
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="min-h-screen py-6 px-3 sm:px-6 bg-[#F4F5F7] dark:bg-[#0B0D13] text-[#212121] dark:text-[#F2F4F7] transition-colors duration-150">

  <div class="max-w-6xl w-full mx-auto space-y-5">
    <!-- Top Header Bar (Zero Mobile Overlap) -->
    <header class="rounded-[2px] border-l-[6px] border-l-[#388E3C] dark:border-l-[#10B981] bg-[#FFFFFF] dark:bg-[#11141E] border-y border-r border-[#E0E0E0] dark:border-white/10 p-4 sm:p-6 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-xl sm:text-2xl font-semibold tracking-tight text-[#1E293B] dark:text-[#F2F4F7]">
              STACKLABS <span class="text-[#00796B] dark:text-[#10B981]">•</span>
            </h1>
            <span class="px-2 py-0.5 rounded-[2px] bg-[#E8F5E9] dark:bg-emerald-950/50 border border-[#C8E6C9] dark:border-emerald-800/60 text-[#2E7D32] dark:text-emerald-400 text-[10px] font-mono uppercase tracking-wider">
              Symbiote Workbench
            </span>
          </div>
          <p class="text-xs font-mono text-[#616161] dark:text-slate-400 mt-1">
            Essay & Market Quant VFS • Companion to <span class="text-[#00796B] dark:text-emerald-400">bothendsofthecurve.com</span>
          </p>
        </div>

        <!-- Non-Overlapping Header Controls -->
        <div class="flex flex-wrap items-center gap-2">
          <span id="activeWorkspaceBadge" class="px-2.5 py-1.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#00796B] dark:text-emerald-400 text-xs font-mono font-medium">
            Workspace: /vfs/spaces/{{ active_slug or 'pawel' }}
          </span>
          <button id="themeToggleBtn" type="button" onclick="toggleTheme()" class="px-3 py-1.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-xs font-mono uppercase tracking-wider transition cursor-pointer hover:border-[#00796B] dark:hover:border-[#10B981]">
            <span id="themeToggleText">LITE / DARK</span>
          </button>
        </div>
      </div>

      <!-- Workspace Switcher Row -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 border-t border-[#E0E0E0] dark:border-white/10">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[11px] font-mono uppercase tracking-wider text-[#616161] dark:text-slate-400">Active Space:</span>
          <button type="button" onclick="switchUserSpace('pawel')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] text-[#212121] dark:text-slate-200 cursor-pointer">pawel</button>
          <button type="button" onclick="switchUserSpace('james')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] text-[#212121] dark:text-slate-200 cursor-pointer">james</button>
          <button type="button" onclick="switchUserSpace('stephen')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] text-[#212121] dark:text-slate-200 cursor-pointer">stephen</button>
        </div>
        <div class="flex items-center gap-2">
          <input type="text" id="spaceSlugInput" value="{{ active_slug or 'pawel' }}" placeholder="workspace_slug" class="w-36 bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 focus:border-[#00796B] dark:focus:border-[#10B981] rounded-[2px] px-2.5 py-1 text-xs font-mono text-[#212121] dark:text-white outline-none">
          <button type="button" onclick="switchUserSpace(document.getElementById('spaceSlugInput').value)" class="px-3 py-1 rounded-[2px] bg-[#00796B] dark:bg-[#059669] text-white text-[11px] font-mono uppercase tracking-wider cursor-pointer">
            Load Workspace
          </button>
        </div>
      </div>
    </header>

    <!-- 4-PANEL SYMBIOTE WORKBENCH GRID -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">

      <!-- PANEL 1: ESSAY, QUANT & INVESTIGATIONS VFS EXPLORER -->
      <section class="rounded-[2px] bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 p-5 space-y-4 shadow-sm flex flex-col justify-between">
        <div class="space-y-3">
          <div class="flex items-center justify-between border-b border-[#E0E0E0] dark:border-white/10 pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase tracking-wider text-[#00796B] dark:text-emerald-400">Panel 01</span>
              <h2 class="text-sm font-semibold uppercase tracking-wider text-[#1E293B] dark:text-white">Essay, Quant & Investigations VFS Explorer</h2>
            </div>
            <div class="flex items-center gap-2">
              <span id="vfsSpaceSummaryCounts" class="text-[11px] font-mono text-[#616161] dark:text-slate-400">Loading...</span>
              <button type="button" onclick="loadUserVfsSpace()" class="px-2 py-1 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[10px] font-mono uppercase text-[#00796B] dark:text-emerald-400 cursor-pointer">
                Refresh Workspace
              </button>
            </div>
          </div>

          <!-- Subfolder Filter Tabs -->
          <div class="flex flex-wrap gap-1.5">
            <button type="button" id="vfsTabEssays" onclick="switchVfsTab('essays')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#00796B] dark:bg-[#059669] text-white cursor-pointer">
              Essays (/essays/)
            </button>
            <button type="button" id="vfsTabQuant" onclick="switchVfsTab('quant')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">
              Market Quant (/quant/)
            </button>
            <button type="button" id="tab-investigations" onclick="switchVfsTab('investigations')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">
              Investigations (/investigations/)
            </button>
            <button type="button" id="tab-predictions" onclick="switchVfsTab('predictions')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">
              Predictions (/predictions/)
            </button>
            <button type="button" id="vfsTabSnipes" onclick="switchVfsTab('snipes')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">
              Snipes (/snipes/)
            </button>
            <button type="button" id="vfsTabUploads" onclick="switchVfsTab('uploads')" class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">
              Uploads (/uploads/)
            </button>
          </div>

          <!-- Active Directory File List -->
          <div id="vfsExplorerList" class="space-y-2 max-h-72 overflow-y-auto pr-1 font-mono text-xs"></div>
        </div>

        <!-- Closed-by-default Collapsible Inline Document Reader -->
        <details id="vfsInlineReaderDrawer" class="rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 p-3 mt-3">
          <summary class="cursor-pointer font-mono text-[11px] uppercase tracking-wider text-[#00796B] dark:text-emerald-400 flex items-center justify-between">
            <span id="vfsReaderTitle">Inline VFS Document Reader (Select a file above)</span>
            <span class="text-[10px] text-slate-400">Expand / Collapse</span>
          </summary>
          <div id="vfsReaderAudioBox" class="hidden mt-3 pt-2 border-t border-[#E0E0E0] dark:border-white/10">
            <audio id="vfsReaderAudioPlayer" controls class="w-full h-8"></audio>
          </div>
          <pre id="vfsReaderBody" class="mt-3 pt-3 border-t border-[#E0E0E0] dark:border-white/10 text-xs font-mono text-[#212121] dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto"></pre>
        </details>
      </section>

      <!-- PANEL 2: UNIVERSAL INGRESS (VOICE, URL SNIPER, 500MB DROP) -->
      <section class="rounded-[2px] bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 p-5 space-y-4 shadow-sm">
        <div class="flex items-center justify-between border-b border-[#E0E0E0] dark:border-white/10 pb-3">
          <div>
            <span class="text-[10px] font-mono uppercase tracking-wider text-[#00796B] dark:text-emerald-400">Panel 02</span>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-[#1E293B] dark:text-white">Universal Ingress</h2>
          </div>
          <span class="text-[11px] font-mono text-[#616161] dark:text-slate-400">/vfs/spaces/<span class="activeSlugInline">{{ active_slug or 'pawel' }}</span></span>
        </div>

        <!-- 2A. Snipe URL to My VFS -->
        <div class="p-3.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-medium uppercase tracking-wider text-[#00796B] dark:text-emerald-400">Snipe URL to My VFS</span>
            <span class="text-[10px] font-mono text-[#757575] dark:text-slate-400">Auto-Collisions + 40s Audio Brief</span>
          </div>
          <form id="snipeUrlForm" class="flex flex-col sm:flex-row gap-2">
            <input type="url" id="snipeUrlInput" required placeholder="Paste YouTube or broadcast URL..." class="flex-1 bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 focus:border-[#00796B] dark:focus:border-[#10B981] rounded-[2px] px-3 py-2 text-xs font-mono text-[#212121] dark:text-white outline-none">
            <button type="submit" id="snipeUrlBtn" class="px-4 py-2 rounded-[2px] bg-[#00796B] hover:bg-[#00695C] dark:bg-[#059669] dark:hover:bg-[#047857] text-white text-xs font-mono font-medium uppercase tracking-wider cursor-pointer whitespace-nowrap">
              Snipe to VFS
            </button>
          </form>
          <div id="snipeStatusBox" class="hidden p-2.5 rounded-[2px] bg-[#E8F5E9] dark:bg-emerald-950/30 border border-[#C8E6C9] dark:border-emerald-800/40 text-xs font-mono text-[#2E7D32] dark:text-emerald-400">
            Transcribing stream, colliding against workspace essays, and synthesizing audio brief...
          </div>
          <div id="snipeErrorBox" class="hidden p-2.5 rounded-[2px] bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 text-xs font-mono text-red-700 dark:text-red-400"></div>
        </div>

        <!-- 2B. 1-Tap Voice Monologue -->
        <div id="voiceRecorderWidget" class="p-3.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10">
          <div id="voiceIdleView" class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
            <div>
              <div class="text-xs font-mono font-medium text-[#212121] dark:text-slate-200 uppercase">1-Tap Voice Monologue</div>
              <div class="text-[11px] text-[#757575] dark:text-slate-400 font-mono">Dictate notes directly into /transcripts/</div>
            </div>
            <button type="button" id="startRecordBtn" class="w-full sm:w-auto px-4 py-2 rounded-[2px] bg-[#00796B] hover:bg-[#00695C] dark:bg-[#059669] dark:hover:bg-[#047857] text-white text-xs font-mono font-medium uppercase tracking-wider cursor-pointer">
              Record Voice Monologue
            </button>
          </div>
          <div id="voiceRecordingView" class="hidden flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
              <span class="text-xs font-mono uppercase text-emerald-600 dark:text-emerald-400">Recording</span>
              <span id="voiceTimer" class="text-xs font-mono font-bold">00:00</span>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" id="cancelRecordBtn" class="px-2.5 py-1 rounded-[2px] border border-[#E0E0E0] dark:border-white/10 text-xs font-mono uppercase cursor-pointer">Cancel</button>
              <button type="button" id="stopRecordBtn" class="px-3.5 py-1.5 rounded-[2px] bg-[#00796B] dark:bg-[#059669] text-white text-xs font-mono uppercase cursor-pointer">Stop & Transcribe</button>
            </div>
          </div>
          <div id="voiceProcessingView" class="hidden text-xs font-mono text-[#00796B] dark:text-emerald-400">
            Transcribing voice memo into personal VFS space...
          </div>
        </div>

        <!-- 2C. 500MB File Dropzone -->
        <form id="dropForm" class="space-y-3">
          <div id="dropZone" class="border-2 border-dashed border-[#BDBDBD] dark:border-white/15 hover:border-[#00796B] dark:hover:border-[#10B981] bg-[#FAFAFA] dark:bg-[#0B0D13] rounded-[2px] p-4 transition cursor-pointer text-center">
            <input type="file" id="fileInput" name="file" class="hidden" required>
            <div id="dropPrompt">
              <p class="text-xs font-mono font-medium text-[#212121] dark:text-slate-200">Drag & drop PDF, Markdown, CSV, or Audio/Video (up to 500MB)</p>
              <span class="inline-block mt-2 px-3 py-1 rounded-[2px] text-[11px] font-mono text-[#00796B] dark:text-emerald-300 bg-[#E0F2F1] dark:bg-emerald-950/60 border border-[#B2DFDB] dark:border-emerald-800/40">
                Browse Files
              </span>
            </div>
            <div id="fileSelectedView" class="hidden flex items-center justify-between p-2 bg-[#FFFFFF] dark:bg-[#11141E] border border-[#00796B] dark:border-emerald-500/50 rounded-[2px] text-xs font-mono">
              <span id="selectedFileName" class="truncate text-[#00796B] dark:text-emerald-300"></span>
              <span id="selectedFileSize" class="text-[11px] text-slate-400 ml-2"></span>
              <span id="audioTagBadge" class="hidden text-[10px] px-1.5 py-0.5 bg-emerald-950 text-emerald-400 rounded-[2px]">AUDIO</span>
              <button type="button" id="removeFileBtn" class="ml-2 text-slate-400 hover:text-red-400 cursor-pointer">Clear</button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input type="text" id="sender" name="sender" value="{{ sender_prefill or active_slug or 'pawel' }}" placeholder="Workspace slug" class="bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 rounded-[2px] px-3 py-2 text-xs font-mono text-[#212121] dark:text-white outline-none">
            <input type="text" id="memo" name="memo" placeholder="Optional note or citation tag..." class="bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 rounded-[2px] px-3 py-2 text-xs font-mono text-[#212121] dark:text-white outline-none">
          </div>

          <div id="progressContainer" class="hidden space-y-1">
            <div class="flex justify-between text-[10px] font-mono text-[#00796B] dark:text-emerald-400">
              <span id="progressStatus">Uploading...</span>
              <span id="progressPct">0%</span>
            </div>
            <div class="w-full h-1.5 bg-[#E0E0E0] dark:bg-[#0B0D13] rounded-[2px] overflow-hidden">
              <div id="progressBar" class="h-full bg-[#00796B] dark:bg-[#059669]" style="width: 0%"></div>
            </div>
          </div>

          <div id="uploadError" class="hidden p-2.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 rounded-[2px] text-xs text-red-700 dark:text-red-400 font-mono">
            <span id="uploadErrorText">Upload failed</span>
          </div>

          <button type="submit" id="submitBtn" class="w-full py-2.5 px-5 rounded-[2px] bg-[#00796B] hover:bg-[#00695C] dark:bg-[#059669] dark:hover:bg-[#047857] text-white font-mono font-medium uppercase tracking-wider text-xs cursor-pointer">
            Send Files
          </button>
        </form>

        <!-- Upload Receipt Card -->
        <div id="receiptCard" class="hidden p-4 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#00796B] dark:border-emerald-700/60 space-y-3 text-xs font-mono">
          <div class="flex items-center justify-between">
            <span class="text-[#2E7D32] dark:text-emerald-400 font-semibold uppercase">Saved to Personal VFS</span>
            <span id="receiptSize" class="text-slate-400"></span>
          </div>
          <div id="receiptFilename" class="text-[#00796B] dark:text-emerald-300 truncate"></div>
          <div id="receiptWorkspacePath" class="text-[11px] text-slate-400 truncate"></div>
          <div id="receiptSha256" class="text-[10px] text-slate-500 break-all"></div>
          <div id="receiptAudioSection" class="hidden space-y-2 pt-2 border-t border-[#E0E0E0] dark:border-white/10">
            <audio id="receiptAudioPlayer" controls class="w-full h-8"></audio>
            <div id="receiptTranscriptText" class="text-xs whitespace-pre-wrap max-h-36 overflow-y-auto"></div>
          </div>
          <button type="button" id="resetBtn" class="w-full py-1.5 px-3 rounded-[2px] bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 text-xs font-mono uppercase cursor-pointer">
            Upload Another File
          </button>
        </div>
      </section>

      <!-- PANEL 3: CROSS-DOMAIN COLLISION MATRIX -->
      <section class="rounded-[2px] bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 p-5 space-y-4 shadow-sm">
        <div class="flex items-center justify-between border-b border-[#E0E0E0] dark:border-white/10 pb-3">
          <div>
            <span class="text-[10px] font-mono uppercase tracking-wider text-[#00796B] dark:text-emerald-400">Panel 03</span>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-[#1E293B] dark:text-white">Cross-Domain Collision Matrix</h2>
          </div>
          <span id="snipeResultPath" class="text-[10px] font-mono px-2 py-0.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#00796B] dark:text-emerald-400">
            /vfs/spaces/{{ active_slug or 'pawel' }}/snipes/BxpyAt5w54w
          </span>
        </div>

        <div id="snipeResultCard" class="space-y-4">
          <div>
            <div id="snipeResultChannel" class="text-[10px] font-mono uppercase tracking-wider text-[#616161] dark:text-slate-400">
              StarTalk (Neil deGrasse Tyson) • 60:14
            </div>
            <h3 id="snipeResultTitle" class="text-sm font-semibold text-[#1E293B] dark:text-white mt-0.5">
              StarTalk Cosmic Queries: Weirdness of Science ⇄ Both Ends of the Curve
            </h3>
          </div>

          <!-- Inline 42-Second Spoken Audio Brief -->
          <div id="snipeAudioContainer" class="p-3 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-[#00796B] dark:text-emerald-400">
              <span>Spoken Collision Brief</span>
              <span id="snipeAudioDuration">42s</span>
            </div>
            <audio id="snipeAudioPlayer" controls src="/drops/spaces/pawel/snipes/BxpyAt5w54w/advocate_rant.mp3" class="w-full h-9 mt-1"></audio>
          </div>

          <!-- 3 Timestamped Essay Collisions -->
          <div class="space-y-2">
            <div class="text-[11px] font-mono uppercase tracking-wider text-[#616161] dark:text-slate-400">Timestamped Stream-to-Essay Collisions</div>
            <ul id="snipeBulletsList" class="space-y-2.5 text-xs text-[#212121] dark:text-slate-200"></ul>
          </div>

          <!-- Matched VFS Essay Nodes -->
          <div class="space-y-1.5 pt-2 border-t border-[#E0E0E0] dark:border-white/10">
            <div class="text-[11px] font-mono uppercase tracking-wider text-[#616161] dark:text-slate-400">Matched Personal VFS Essay Nodes</div>
            <div id="snipeCollisionsList" class="space-y-1.5 text-xs font-mono"></div>
          </div>

          <!-- Closed-by-default Full Collision Markdown Drawer -->
          <details class="rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 p-3">
            <summary class="cursor-pointer font-mono text-[11px] uppercase tracking-wider text-[#00796B] dark:text-emerald-400 flex items-center justify-between">
              <span>Full Collision Dossier Markdown</span>
              <span class="text-[10px] text-slate-400">Expand / Collapse</span>
            </summary>
            <pre id="snipeSummaryMarkdown" class="mt-3 pt-3 border-t border-[#E0E0E0] dark:border-white/10 text-xs font-mono text-[#212121] dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto"></pre>
          </details>
        </div>
      </section>

      <!-- PANEL 4: COMPANION EXPORT BRIDGE (BOTHENDSOFTHECURVE.COM) -->
      <section class="rounded-[2px] bg-[#FFFFFF] dark:bg-[#11141E] border border-[#E0E0E0] dark:border-white/10 p-5 space-y-4 shadow-sm flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-[#E0E0E0] dark:border-white/10 pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase tracking-wider text-[#00796B] dark:text-emerald-400">Panel 04</span>
              <h2 class="text-sm font-semibold uppercase tracking-wider text-[#1E293B] dark:text-white">Companion Export Bridge</h2>
            </div>
            <span class="text-[11px] font-mono text-[#00796B] dark:text-emerald-400">bothendsofthecurve.com</span>
          </div>

          <p class="text-xs text-[#616161] dark:text-slate-300 leading-relaxed">
            Export timestamped cross-domain collision receipts, verbatim quotes, and spoken audio brief links formatted to drop directly into <span class="font-mono text-[#00796B] dark:text-emerald-400">bothendsofthecurve.com</span> essays and research notes.
          </p>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <button type="button" onclick="copyCompanionExport('markdown')" id="btnCopyMarkdown" class="py-2.5 px-3 rounded-[2px] bg-[#00796B] hover:bg-[#00695C] dark:bg-[#059669] dark:hover:bg-[#047857] text-white text-xs font-mono uppercase tracking-wider cursor-pointer text-center">
              Copy Markdown
            </button>
            <button type="button" onclick="copyCompanionExport('json')" id="btnCopyJson" class="py-2.5 px-3 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] text-xs font-mono uppercase tracking-wider cursor-pointer text-center">
              Copy JSON
            </button>
            <button type="button" onclick="copyCompanionExport('audio')" id="btnCopyAudio" class="py-2.5 px-3 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] text-xs font-mono uppercase tracking-wider cursor-pointer text-center">
              Copy Audio Link
            </button>
          </div>

          <!-- Closed-by-default Export Payload Preview Drawer -->
          <details class="rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 p-3">
            <summary class="cursor-pointer font-mono text-[11px] uppercase tracking-wider text-[#00796B] dark:text-emerald-400 flex items-center justify-between">
              <span>Preview Export Snippet for bothendsofthecurve.com</span>
              <span class="text-[10px] text-slate-400">Expand / Collapse</span>
            </summary>
            <pre id="companionExportPreview" class="mt-3 pt-3 border-t border-[#E0E0E0] dark:border-white/10 text-xs font-mono text-[#212121] dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto"></pre>
          </details>
        </div>

        <div class="p-3 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 flex items-center justify-between text-[11px] font-mono text-[#616161] dark:text-slate-400">
          <span>Active Corpus: 7 Essays • 3 Quant Specs</span>
          <span id="exportStatusBadge" class="text-[#00796B] dark:text-emerald-400">Ready</span>
        </div>
      </section>

    </div>

    <!-- Canonical Footer -->
    <footer class="pt-4 pb-2 border-t border-[#E0E0E0] dark:border-white/10 text-center">
      <div class="text-[11px] font-mono uppercase tracking-wider text-[#757575] dark:text-slate-400">
        PERSISTENT POSIX VFS WORKSPACE • SHA-256 BIT-PERFECT PROVENANCE
      </div>
    </footer>
  </div>

  <script>
    let currentSlug = "{{ active_slug or 'pawel' }}";
    let currentSpaceData = null;
    let activeVfsTab = 'essays';
    let activeSnipeDossier = null;

    function sanitizeSlugClient(raw) {
      let s = (raw || '').trim().toLowerCase();
      if (s.includes('pawel') || s.includes('rudnicki')) return 'pawel';
      s = s.replace(/[^a-z0-9_-]+/g, '_').replace(/_+/g, '_').replace(/^[_-]+|[_-]+$/g, '');
      if (s.length < 2) s = 'pawel';
      return s.slice(0, 32);
    }

    function switchUserSpace(rawSlug) {
      currentSlug = sanitizeSlugClient(rawSlug);
      document.getElementById('spaceSlugInput').value = currentSlug;
      document.getElementById('sender').value = currentSlug;
      document.getElementById('activeWorkspaceBadge').textContent = `Workspace: /vfs/spaces/${currentSlug}`;
      document.querySelectorAll('.activeSlugInline').forEach(el => { el.textContent = currentSlug; });
      const url = new URL(window.location.href);
      url.searchParams.set('from', currentSlug);
      window.history.replaceState({}, '', url);
      loadUserVfsSpace();
    }

    function switchVfsTab(tab) {
      activeVfsTab = tab;
      const tabs = {
        essays: document.getElementById('vfsTabEssays'),
        quant: document.getElementById('vfsTabQuant'),
        investigations: document.getElementById('tab-investigations'),
        predictions: document.getElementById('tab-predictions'),
        snipes: document.getElementById('vfsTabSnipes'),
        uploads: document.getElementById('vfsTabUploads')
      };
      const activeCls = 'px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#00796B] dark:bg-[#059669] text-white cursor-pointer';
      const inactiveCls = 'px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer';
      Object.keys(tabs).forEach(k => {
        if (tabs[k]) tabs[k].className = (k === tab) ? activeCls : inactiveCls;
      });
      renderVfsExplorerList();
    }

    function openInlineReader(name, vfsPath, content, audioUrl) {
      document.getElementById('vfsReaderTitle').textContent = `${name} (${vfsPath})`;
      document.getElementById('vfsReaderBody').textContent = content || '(Empty file)';
      const audioBox = document.getElementById('vfsReaderAudioBox');
      const audioPlayer = document.getElementById('vfsReaderAudioPlayer');
      if (audioBox && audioPlayer) {
        if (audioUrl) {
          audioBox.classList.remove('hidden');
          audioPlayer.src = audioUrl;
        } else {
          audioBox.classList.add('hidden');
          audioPlayer.src = '';
        }
      }
      const drawer = document.getElementById('vfsInlineReaderDrawer');
      if (drawer) drawer.open = true;
    }

    function renderVfsExplorerList() {
      const listEl = document.getElementById('vfsExplorerList');
      if (!listEl || !currentSpaceData) return;

      if (activeVfsTab === 'snipes') {
        const snipes = currentSpaceData.snipes || [];
        if (snipes.length === 0) {
          listEl.innerHTML = '<div class="text-slate-500 p-2">No sniped dossiers in this workspace yet.</div>';
          return;
        }
        listEl.innerHTML = snipes.map((s, idx) => `
          <div onclick="selectSnipeByIndex(${idx})" class="p-2.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] cursor-pointer space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-[#00796B] dark:text-emerald-400">${s.title}</span>
              <span class="text-[10px] text-slate-400">${s.duration || ''}</span>
            </div>
            <div class="text-[10px] text-slate-500">${s.vfs_path}</div>
          </div>
        `).join('');
        return;
      }

      if (activeVfsTab === 'investigations') {
        const invs = currentSpaceData.investigations || [];
        if (invs.length === 0) {
          listEl.innerHTML = '<div class="text-slate-500 p-2">No investigations in /investigations/ yet.</div>';
          return;
        }
        listEl.innerHTML = invs.map((item, idx) => `
          <div onclick="selectVfsFile('investigations', ${idx})" class="p-2.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] cursor-pointer space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-[#00796B] dark:text-emerald-400">${item.title || item.name}</span>
              <span class="text-[10px] text-slate-400">${item.size_formatted || ''}</span>
            </div>
            <div class="text-[10px] text-slate-500">${item.vfs_path}</div>
            ${item.audio_url ? `<div onclick="event.stopPropagation()" class="pt-1"><audio controls preload="none" src="${item.audio_url}" class="w-full h-8"></audio></div>` : ''}
          </div>
        `).join('');
        return;
      }

      const items = currentSpaceData[activeVfsTab] || [];
      if (items.length === 0) {
        listEl.innerHTML = `<div class="text-slate-500 p-2">No items in /${activeVfsTab}/ yet.</div>`;
        return;
      }
      listEl.innerHTML = items.map((item, idx) => `
        <div onclick="selectVfsFile('${activeVfsTab}', ${idx})" class="p-2.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 hover:border-[#00796B] dark:hover:border-[#10B981] cursor-pointer space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-medium text-[#00796B] dark:text-emerald-400">${item.name}</span>
            <span class="text-[10px] text-slate-400">${item.size_formatted}</span>
          </div>
          ${item.preview ? `<div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">${item.preview}</div>` : ''}
        </div>
      `).join('');
    }

    function selectVfsFile(tabKey, idx) {
      if (!currentSpaceData || !currentSpaceData[tabKey] || !currentSpaceData[tabKey][idx]) return;
      const item = currentSpaceData[tabKey][idx];
      openInlineReader(item.title || item.name, item.vfs_path, item.content || item.preview, item.audio_url || null);
    }

    function selectSnipeByIndex(idx) {
      if (!currentSpaceData || !currentSpaceData.snipes || !currentSpaceData.snipes[idx]) return;
      renderSnipeDossier(currentSpaceData.snipes[idx]);
    }

    function renderSnipeDossier(data) {
      if (!data) return;
      activeSnipeDossier = data;
      document.getElementById('snipeResultChannel').textContent = `${data.channel || 'Broadcast'} • ${data.duration || ''}`;
      document.getElementById('snipeResultTitle').textContent = data.title || data.video_id;
      document.getElementById('snipeResultPath').textContent = data.vfs_path || `${data.workspace || '/vfs/spaces/' + currentSlug}/snipes/${data.video_id}`;

      const audioContainer = document.getElementById('snipeAudioContainer');
      const audioPlayer = document.getElementById('snipeAudioPlayer');
      if (data.audio_url) {
        audioContainer.classList.remove('hidden');
        audioPlayer.src = data.audio_url;
        document.getElementById('snipeAudioDuration').textContent = data.audio_duration_seconds ? `${Math.round(data.audio_duration_seconds)}s` : '42s';
      } else {
        audioContainer.classList.add('hidden');
      }

      const bulletsUl = document.getElementById('snipeBulletsList');
      bulletsUl.innerHTML = (data.bullets || []).map((b, i) => `
        <li class="p-3 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 space-y-1">
          <div class="flex items-center justify-between text-[11px] font-mono text-[#00796B] dark:text-emerald-400">
            <span>0${i + 1} • [${b.timestamp || '00:00'}]</span>
            <span>${b.tag || 'COLLISION'}</span>
          </div>
          <div class="font-semibold text-xs text-[#1E293B] dark:text-white">${b.headline || ''}</div>
          ${b.verbatimQuote ? `<div class="text-[11px] text-slate-600 dark:text-slate-300 italic">"${b.verbatimQuote}"</div>` : ''}
          ${b.essay_link ? `<div class="text-[11px] font-mono text-[#00796B] dark:text-emerald-400 pt-1">⇄ ${b.essay_link}</div>` : ''}
        </li>
      `).join('');

      const colDiv = document.getElementById('snipeCollisionsList');
      const cols = data.collisions || [];
      colDiv.innerHTML = cols.length === 0
        ? '<div class="text-slate-500">No prior document collisions in workspace.</div>'
        : cols.map(c => `
            <div class="p-2.5 rounded-[2px] bg-[#FAFAFA] dark:bg-[#0B0D13] border border-[#E0E0E0] dark:border-white/10 space-y-1">
              <div class="flex justify-between text-[#00796B] dark:text-emerald-400">
                <span>${c.file}</span>
                <span>Score: ${c.score} (${c.overlap_count} shared terms)</span>
              </div>
              <div class="text-[10px] text-slate-400">Matched: ${(c.matched_terms || []).join(', ')}</div>
              ${c.excerpt ? `<div class="text-[11px] text-slate-300">${c.excerpt}</div>` : ''}
            </div>
          `).join('');

      const mdPre = document.getElementById('snipeSummaryMarkdown');
      if (mdPre) mdPre.textContent = data.summary_markdown || '';

      const exportPre = document.getElementById('companionExportPreview');
      if (exportPre) exportPre.textContent = data.summary_markdown || JSON.stringify(data, null, 2);
    }

    function copyCompanionExport(mode) {
      if (!activeSnipeDossier) return;
      let text = '';
      if (mode === 'markdown') {
        text = activeSnipeDossier.summary_markdown || '';
      } else if (mode === 'json') {
        text = JSON.stringify(activeSnipeDossier, null, 2);
      } else if (mode === 'audio') {
        text = window.location.origin + (activeSnipeDossier.audio_url || '');
      }
      navigator.clipboard.writeText(text).then(() => {
        const badge = document.getElementById('exportStatusBadge');
        if (badge) {
          badge.textContent = `Copied ${mode.toUpperCase()}`;
          setTimeout(() => { badge.textContent = 'Ready'; }, 2000);
        }
      });
    }

    async function loadUserVfsSpace() {
      try {
        const res = await fetch(`/api/drop/space/${encodeURIComponent(currentSlug)}`);
        if (!res.ok) return;
        const data = await res.json();
        currentSpaceData = data;
        const c = data.counts || {essays: 0, quant: 0, investigations: 0, snipes: 0, uploads: 0};
        document.getElementById('vfsSpaceSummaryCounts').textContent =
          `${c.essays || 0} essays • ${c.quant || 0} quant • ${c.investigations || 0} investigations • ${c.predictions || 0} predictions • ${c.snipes || 0} snipes`;
        const invBtn = document.getElementById('tab-investigations');
        if (invBtn) invBtn.textContent = `INVESTIGATIONS (${c.investigations || 0})`;
        const predBtn = document.getElementById('tab-predictions');
        if (predBtn) predBtn.textContent = `PREDICTIONS (${c.predictions || 0})`;
        const essaysBtn = document.getElementById('vfsTabEssays');
        if (essaysBtn) essaysBtn.textContent = `ESSAYS (${c.essays || 0})`;
        const quantBtn = document.getElementById('vfsTabQuant');
        if (quantBtn) quantBtn.textContent = `QUANT (${c.quant || 0})`;
        const snipesBtn = document.getElementById('vfsTabSnipes');
        if (snipesBtn) snipesBtn.textContent = `SNIPES (${c.snipes || 0})`;
        const uploadsBtn = document.getElementById('vfsTabUploads');
        if (uploadsBtn) uploadsBtn.textContent = `UPLOADS (${c.uploads || 0})`;
        renderVfsExplorerList();
        if (data.snipes && data.snipes.length > 0 && !activeSnipeDossier) {
          renderSnipeDossier(data.snipes[0]);
        }
      } catch (e) {
        console.error('Workspace load error:', e);
      }
    }

    document.addEventListener('DOMContentLoaded', () => {
      updateThemeToggleUI(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
      const fromParam = new URLSearchParams(window.location.search).get('from');
      switchUserSpace(fromParam || currentSlug || 'pawel');
    });

    // URL Sniper Handler
    const snipeUrlForm = document.getElementById('snipeUrlForm');
    const snipeUrlInput = document.getElementById('snipeUrlInput');
    const snipeUrlBtn = document.getElementById('snipeUrlBtn');
    const snipeStatusBox = document.getElementById('snipeStatusBox');
    const snipeErrorBox = document.getElementById('snipeErrorBox');

    snipeUrlForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const targetUrl = snipeUrlInput.value.trim();
      if (!targetUrl) return;

      snipeUrlBtn.disabled = true;
      snipeUrlBtn.textContent = 'Sniping...';
      snipeStatusBox.classList.remove('hidden');
      snipeErrorBox.classList.add('hidden');

      try {
        const res = await fetch('/api/drop/snipe', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url: targetUrl, sender: currentSlug })
        });
        const data = await res.json();
        snipeStatusBox.classList.add('hidden');
        snipeUrlBtn.disabled = false;
        snipeUrlBtn.textContent = 'Snipe to VFS';

        if (!res.ok || data.status !== 'success') {
          throw new Error(data.error || 'Snipe failed');
        }
        renderSnipeDossier(data);
        loadUserVfsSpace();
      } catch (err) {
        snipeStatusBox.classList.add('hidden');
        snipeUrlBtn.disabled = false;
        snipeUrlBtn.textContent = 'Snipe to VFS';
        snipeErrorBox.textContent = err.message || 'Failed to snipe URL.';
        snipeErrorBox.classList.remove('hidden');
      }
    });

    // File Dropzone & Voice Dictation Logic
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const dropPrompt = document.getElementById('dropPrompt');
    const fileSelectedView = document.getElementById('fileSelectedView');
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFileSize = document.getElementById('selectedFileSize');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const dropForm = document.getElementById('dropForm');
    const submitBtn = document.getElementById('submitBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressPct = document.getElementById('progressPct');
    const progressStatus = document.getElementById('progressStatus');
    const uploadError = document.getElementById('uploadError');
    const uploadErrorText = document.getElementById('uploadErrorText');
    const receiptCard = document.getElementById('receiptCard');
    const resetBtn = document.getElementById('resetBtn');
    const senderInput = document.getElementById('sender');

    const AUDIO_EXTS = ['.webm', '.m4a', '.mp3', '.wav', '.aac', '.ogg', '.opus', '.flac'];
    function isAudioFile(filename, mimeType) {
      if (!filename) return false;
      const dot = filename.lastIndexOf('.');
      const ext = dot !== -1 ? filename.substring(dot).toLowerCase() : '';
      return AUDIO_EXTS.includes(ext) || (mimeType && mimeType.startsWith('audio/'));
    }

    function formatBytes(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDuration(sec) {
      if (!sec) return '00:00';
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function setSelectedFile(file) {
      if (!file) return;
      selectedFileName.textContent = file.name;
      selectedFileSize.textContent = formatBytes(file.size);
      const audioBadge = document.getElementById('audioTagBadge');
      if (isAudioFile(file.name, file.type)) audioBadge.classList.remove('hidden');
      else audioBadge.classList.add('hidden');
      dropPrompt.classList.add('hidden');
      fileSelectedView.classList.remove('hidden');
      uploadError.classList.add('hidden');
    }

    function clearSelectedFile() {
      fileInput.value = '';
      dropPrompt.classList.remove('hidden');
      fileSelectedView.classList.add('hidden');
    }

    dropZone.addEventListener('click', (e) => {
      if (e.target.closest('#removeFileBtn')) return;
      fileInput.click();
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) setSelectedFile(fileInput.files[0]);
    });
    removeFileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      clearSelectedFile();
    });
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
      dropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); });
    });
    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        setSelectedFile(e.dataTransfer.files[0]);
      }
    });

    // Voice Recorder
    let mediaRecorder = null;
    let audioChunks = [];
    let recordTimerInterval = null;
    let recordStartTime = 0;

    const startRecordBtn = document.getElementById('startRecordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const cancelRecordBtn = document.getElementById('cancelRecordBtn');
    const voiceIdleView = document.getElementById('voiceIdleView');
    const voiceRecordingView = document.getElementById('voiceRecordingView');
    const voiceProcessingView = document.getElementById('voiceProcessingView');
    const voiceTimer = document.getElementById('voiceTimer');

    function resetVoiceWidget() {
      clearInterval(recordTimerInterval);
      voiceTimer.textContent = '00:00';
      voiceRecordingView.classList.add('hidden');
      voiceProcessingView.classList.add('hidden');
      voiceIdleView.classList.remove('hidden');
    }

    async function startRecording() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        let options = {};
        if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          options = { mimeType: 'audio/webm;codecs=opus' };
        }
        mediaRecorder = new MediaRecorder(stream, options);
        mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };
        mediaRecorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          clearInterval(recordTimerInterval);
          if (audioChunks.length === 0) { resetVoiceWidget(); return; }
          const mimeType = mediaRecorder.mimeType || 'audio/webm';
          const audioBlob = new Blob(audioChunks, { type: mimeType });
          const audioFile = new File([audioBlob], `voice_memo_${Date.now()}.webm`, { type: mimeType });
          uploadMonologueFile(audioFile);
        };
        mediaRecorder.start(1000);
        recordStartTime = Date.now();
        voiceIdleView.classList.add('hidden');
        voiceRecordingView.classList.remove('hidden');
        recordTimerInterval = setInterval(() => {
          voiceTimer.textContent = formatDuration(Math.floor((Date.now() - recordStartTime) / 1000));
        }, 1000);
      } catch (err) {
        uploadErrorText.textContent = 'Microphone unavailable: ' + err.message;
        uploadError.classList.remove('hidden');
        resetVoiceWidget();
      }
    }

    if (startRecordBtn) startRecordBtn.addEventListener('click', startRecording);
    if (stopRecordBtn) stopRecordBtn.addEventListener('click', () => {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        voiceRecordingView.classList.add('hidden');
        voiceProcessingView.classList.remove('hidden');
        mediaRecorder.stop();
      }
    });
    if (cancelRecordBtn) cancelRecordBtn.addEventListener('click', () => {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.onstop = () => { mediaRecorder.stream.getTracks().forEach(t => t.stop()); };
        mediaRecorder.stop();
      }
      resetVoiceWidget();
    });

    function uploadMonologueFile(audioFile) {
      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('sender', senderInput.value.trim() || currentSlug);
      formData.append('memo', document.getElementById('memo').value.trim());

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/upload', true);
      xhr.onload = () => {
        resetVoiceWidget();
        if (xhr.status >= 200 && xhr.status < 300) {
          const resp = JSON.parse(xhr.responseText);
          if (resp.status === 'success') {
            renderReceipt(resp, audioFile);
            loadUserVfsSpace();
          }
        } else {
          uploadErrorText.textContent = `Upload failed (${xhr.status})`;
          uploadError.classList.remove('hidden');
        }
      };
      xhr.send(formData);
    }

    function renderReceipt(resp, fileObj) {
      document.getElementById('receiptFilename').textContent = resp.filename || (fileObj ? fileObj.name : 'file');
      document.getElementById('receiptSize').textContent = resp.size_formatted || '';
      document.getElementById('receiptWorkspacePath').textContent = `${resp.workspace || '/vfs/spaces/' + currentSlug}/uploads/${resp.filename}`;
      document.getElementById('receiptSha256').textContent = resp.sha256 || '';

      const audioSection = document.getElementById('receiptAudioSection');
      const audioPlayer = document.getElementById('receiptAudioPlayer');
      const transcriptText = document.getElementById('receiptTranscriptText');
      if (resp.is_audio) {
        audioSection.classList.remove('hidden');
        audioPlayer.src = resp.audio_url || '';
        transcriptText.textContent = resp.transcript || '(Transcript saved to workspace)';
      } else {
        audioSection.classList.add('hidden');
      }
      dropForm.classList.add('hidden');
      receiptCard.classList.remove('hidden');
    }

    dropForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) return;
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('sender', senderInput.value.trim() || currentSlug);
      formData.append('memo', document.getElementById('memo').value.trim());

      submitBtn.disabled = true;
      progressContainer.classList.remove('hidden');
      uploadError.classList.add('hidden');

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/upload', true);
      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          const pct = Math.round((evt.loaded / evt.total) * 100);
          progressBar.style.width = pct + '%';
          progressPct.textContent = pct + '%';
        }
      };
      xhr.onload = () => {
        submitBtn.disabled = false;
        if (xhr.status >= 200 && xhr.status < 300) {
          const resp = JSON.parse(xhr.responseText);
          renderReceipt(resp, file);
          loadUserVfsSpace();
        } else {
          uploadErrorText.textContent = `Upload error (${xhr.status})`;
          uploadError.classList.remove('hidden');
        }
      };
      xhr.send(formData);
    });

    resetBtn.addEventListener('click', () => {
      clearSelectedFile();
      progressContainer.classList.add('hidden');
      receiptCard.classList.add('hidden');
      dropForm.classList.remove('hidden');
    });
  </script>
</body>
</html>
"""
