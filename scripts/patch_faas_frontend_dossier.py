#!/home/james/stacklabs/.venv/bin/python3
"""
Surgically patches apps/faas/src/App.tsx to:
1. Import VfsMediaDossierCard and Folder icon.
2. Support 'dossier' mode in sniperView state.
3. Add 'VFS Media Dossier' tab button and 'Open VFS Media Dossier' button.
4. Render VfsMediaDossierCard when sniperView === 'dossier'.
5. Handle asynchronous polling when POST /api/snipe returns HTTP 202 status: 'processing'.
"""
import sys
from pathlib import Path

APP_TSX = Path("/home/james/stacklabs/apps/faas/src/App.tsx")


def patch():
    content = APP_TSX.read_text(encoding="utf-8")

    # 1. Import Folder icon if missing
    if "Folder," not in content:
        content = content.replace("  Target,", "  Target,\n  Folder,")

    # 2. Import VfsMediaDossierCard
    if "VfsMediaDossierCard" not in content:
        content = content.replace(
            "import { PipelineTrackerHUD } from './components/PipelineTrackerHUD';",
            "import { PipelineTrackerHUD } from './components/PipelineTrackerHUD';\nimport { VfsMediaDossierCard } from './components/VfsMediaDossierCard';"
        )

    # 3. Update sniperView state definition
    if "useState<'brief' | 'transcript'>('brief')" in content:
        content = content.replace(
            "useState<'brief' | 'transcript'>('brief')",
            "useState<'brief' | 'transcript' | 'dossier'>('brief')"
        )

    # 4. Patch handleSnipeStream for async polling
    old_fetch_block = """      const res = await fetch(`${API_BASE}/api/snipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: streamUrl.trim() })
      });
      clearInterval(stageTimer);

      if (!res.ok) {
        const rawText = await res.text();
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = JSON.parse(rawText);
          errMessage = errData.detail || errData.message || errMessage;
        } catch {
          errMessage = rawText.slice(0, 200) || errMessage;
        }
        alert('Snipe error: ' + errMessage);
        return;
      }

      const data = await res.json();
      if (data.bullets) {
        setSnipeProgress(100);
        setSnipeStage('3-Bullet Intel Brief ready!');
        setCurrentResult(data);
      } else {
        alert('Snipe error: ' + (data.detail || data.message || 'Failed to parse stream'));
      }"""

    new_fetch_block = """      const res = await fetch(`${API_BASE}/api/snipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: streamUrl.trim() })
      });

      if (!res.ok && res.status !== 202) {
        clearInterval(stageTimer);
        const rawText = await res.text();
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = JSON.parse(rawText);
          errMessage = errData.detail || errData.message || errMessage;
        } catch {
          errMessage = rawText.slice(0, 200) || errMessage;
        }
        alert('Snipe error: ' + errMessage);
        setIsSniping(false);
        return;
      }

      const data = await res.json();
      if (data.status === 'ready' || data.bullets) {
        clearInterval(stageTimer);
        setSnipeProgress(100);
        setSnipeStage('3-Bullet Intel Brief ready!');
        setCurrentResult(data);
        setIsSniping(false);
      } else if (res.status === 202 || data.status === 'processing') {
        const videoId = data.video_id;
        const pollInterval = setInterval(async () => {
          try {
            const checkRes = await fetch(`${API_BASE}/api/snipe/${videoId}`);
            if (checkRes.ok) {
              const pollData = await checkRes.json();
              if (pollData.bullets || pollData.status === 'ready') {
                clearInterval(pollInterval);
                clearInterval(stageTimer);
                setSnipeProgress(100);
                setSnipeStage('3-Bullet Intel Brief & Dossier ready!');
                setCurrentResult(pollData);
                setIsSniping(false);
              } else if (pollData.stage) {
                setSnipeStage(pollData.stage);
              }
            }
          } catch (pollErr) {
            // continue polling
          }
        }, 2500);
      } else {
        clearInterval(stageTimer);
        alert('Snipe error: ' + (data.detail || data.message || 'Failed to parse stream'));
        setIsSniping(false);
      }"""

    if old_fetch_block in content:
        content = content.replace(old_fetch_block, new_fetch_block)

    # 5. Add 3rd tab toggle button for Dossier
    old_toggle_block = """                  <button
                    onClick={() => setSniperView('transcript')}
                    className={`px-3 py-1 rounded transition-colors ${
                      sniperView === 'transcript'
                        ? 'bg-amber-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Full Transcript
                  </button>
                </div>"""

    new_toggle_block = """                  <button
                    onClick={() => setSniperView('transcript')}
                    className={`px-3 py-1 rounded transition-colors ${
                      sniperView === 'transcript'
                        ? 'bg-amber-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Full Transcript
                  </button>
                  <button
                    onClick={() => setSniperView('dossier')}
                    className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                      sniperView === 'dossier'
                        ? 'bg-emerald-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <span>VFS Dossier</span>
                    <span className="text-[9px] px-1 py-0.2 bg-emerald-950/40 rounded border border-emerald-500/30 text-emerald-300">CI</span>
                  </button>
                </div>"""

    if old_toggle_block in content:
        content = content.replace(old_toggle_block, new_toggle_block)

    # 6. Add "Open VFS Media Dossier" button in Brief actions
    old_brief_actions = """                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      onClick={handleCopyBrief}
                      className="flex-1 py-2.5 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors font-mono"
                    >
                      {copiedBrief ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copiedBrief ? 'Copied to Clipboard!' : 'Copy 3-Bullet Brief'}</span>
                    </button>
                    <button
                      onClick={handleExportBrief}
                      className="py-2.5 px-3 rounded-lg bg-[#090B0F] border border-[#242B38] hover:border-amber-500/40 text-slate-300 hover:text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors font-mono"
                      title="Export to OBS / X"
                    >
                      {exportedToast ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
                      <span>{exportedToast ? 'Exported!' : 'Export OBS / X'}</span>
                    </button>
                  </div>"""

    new_brief_actions = """                  {/* Actions */}
                  <div className="flex flex-col gap-2 pt-1">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCopyBrief}
                        className="flex-1 py-2.5 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors font-mono"
                      >
                        {copiedBrief ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        <span>{copiedBrief ? 'Copied to Clipboard!' : 'Copy 3-Bullet Brief'}</span>
                      </button>
                      <button
                        onClick={handleExportBrief}
                        className="py-2.5 px-3 rounded-lg bg-[#090B0F] border border-[#242B38] hover:border-amber-500/40 text-slate-300 hover:text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors font-mono"
                        title="Export to OBS / X"
                      >
                        {exportedToast ? <Check className="w-4 h-4 text-emerald-400" /> : <Share2 className="w-4 h-4" />}
                        <span>{exportedToast ? 'Exported!' : 'Export OBS / X'}</span>
                      </button>
                    </div>
                    <button
                      onClick={() => setSniperView('dossier')}
                      className="w-full py-2 px-3 rounded-lg bg-[#090B0F] border border-emerald-500/40 hover:border-emerald-400 text-emerald-400 hover:text-emerald-300 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors font-mono"
                      title="Open VFS Media Dossier & CI Folder"
                    >
                      <Folder className="w-4 h-4" />
                      <span>Open VFS Media Dossier (CI Files & Audio)</span>
                    </button>
                  </div>"""

    if old_brief_actions in content:
        content = content.replace(old_brief_actions, new_brief_actions)

    # 7. Render VfsMediaDossierCard when sniperView === 'dossier'
    old_transcript_view = """              {/* View B: Full Verbatim Transcript */}
              {sniperView === 'transcript' && (
                <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1 text-xs font-mono">
                  {(currentResult.transcript || []).map((line, idx) => (
                    <div 
                      key={idx} 
                      className={`p-2 rounded border ${
                        line.isKeyMoment 
                          ? 'bg-amber-500/10 border-amber-500/30' 
                          : 'bg-[#090B0F] border-[#242B38]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                        <span className="font-bold text-amber-300">[{line.timestamp}] {line.speaker}</span>
                        {line.isKeyMoment && <span className="text-rose-400 font-bold">KEY QUOTE</span>}
                      </div>
                      <div className="text-slate-200 text-xs">{line.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>"""

    new_transcript_view = """              {/* View B: Full Verbatim Transcript */}
              {sniperView === 'transcript' && (
                <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1 text-xs font-mono">
                  {(currentResult.transcript || []).map((line, idx) => (
                    <div 
                      key={idx} 
                      className={`p-2 rounded border ${
                        line.isKeyMoment 
                          ? 'bg-amber-500/10 border-amber-500/30' 
                          : 'bg-[#090B0F] border-[#242B38]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                        <span className="font-bold text-amber-300">[{line.timestamp}] {line.speaker}</span>
                        {line.isKeyMoment && <span className="text-rose-400 font-bold">KEY QUOTE</span>}
                      </div>
                      <div className="text-slate-200 text-xs">{line.text}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* View C: VFS Media Dossier & CI Explorer */}
              {sniperView === 'dossier' && (
                <VfsMediaDossierCard
                  videoId={currentResult.id}
                  title={currentResult.title}
                  duration={currentResult.duration}
                  source={currentResult.source || (currentResult as any).channel}
                  engine={(currentResult as any).engine}
                  apiBase={API_BASE}
                />
              )}
            </div>"""

    if old_transcript_view in content:
        content = content.replace(old_transcript_view, new_transcript_view)

    APP_TSX.write_text(content, encoding="utf-8")
    print("Successfully patched apps/faas/src/App.tsx with VFS Media Dossier viewer.")


if __name__ == "__main__":
    patch()
