#!/home/james/stacklabs/.venv/bin/python3
"""
Removes the '//' hacker-slash from '🎙️ ADVOCATE WIRE //' in apps/faas/src/App.tsx
so it renders cleanly as 'Advocate Wire:' and supports both BxpyAt5w54w and xHWbeRw680k audio briefs.
Also enriches stream_sniper_bp.py catalog/detail metadata with per-dossier advocate_handle.
"""

import json
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
FAAS_APP = REPO_ROOT / "apps" / "faas" / "src" / "App.tsx"
BP_FILE = REPO_ROOT / "scripts" / "blueprints" / "stream_sniper_bp.py"


def patch_faas_app() -> None:
    text = FAAS_APP.read_text(encoding="utf-8")
    old_block = """                  {((currentResult as any).advocate_audio_url || currentResult.id === 'xHWbeRw680k') && (
                    <div
                      data-testid="sniper-advocate-audio-bar"
                      className="bg-[#0B0D13] border border-emerald-500/30 rounded-lg p-2.5 flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="font-bold text-emerald-400">
                          🎙️ ADVOCATE WIRE // {(currentResult as any).advocate_handle || '@SammyBoySmith_The_Savant'} ({(currentResult as any).advocate_duration || '0:42'})
                        </span>
                        <span className="text-amber-400 uppercase font-semibold">2ND & SNYDER CALLER</span>
                      </div>"""

    new_block = """                  {((currentResult as any).advocate_audio_url || currentResult.id === 'xHWbeRw680k' || currentResult.id === 'BxpyAt5w54w') && (
                    <div
                      data-testid="sniper-advocate-audio-bar"
                      className="bg-[#0B0D13] border border-emerald-500/30 rounded-lg p-2.5 flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="font-bold text-emerald-400">
                          Advocate Wire: {(currentResult as any).advocate_handle || (currentResult.id === 'BxpyAt5w54w' ? 'Executive Brief: The 3,000K Kiln Collision' : '@SammyBoySmith_The_Savant')} ({(currentResult as any).advocate_duration || '0:42'})
                        </span>
                        <span className="text-amber-400 uppercase font-semibold">{currentResult.id === 'BxpyAt5w54w' ? 'COLLISION AUDIO BRIEF' : '2ND & SNYDER CALLER'}</span>
                      </div>"""

    if old_block in text:
        text = text.replace(old_block, new_block)
    else:
        text = text.replace("🎙️ ADVOCATE WIRE //", "Advocate Wire:")

    FAAS_APP.write_text(text, encoding="utf-8")
    print("[OK] Updated apps/faas/src/App.tsx label to 'Advocate Wire:'.")


def patch_blueprint() -> None:
    text = BP_FILE.read_text(encoding="utf-8")
    old_snippet = 'item["advocate_handle"] = "@SammyBoySmith_The_Savant"'
    new_snippet = 'item["advocate_handle"] = "Executive Brief: The 3,000K Kiln Collision" if vid == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant"'
    if old_snippet in text:
        text = text.replace(old_snippet, new_snippet)
    old_detail = 'payload.setdefault("advocate_handle", "@SammyBoySmith_The_Savant")'
    new_detail = 'payload.setdefault("advocate_handle", "Executive Brief: The 3,000K Kiln Collision" if video_id == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant")'
    if old_detail in text:
        text = text.replace(old_detail, new_detail)
    BP_FILE.write_text(text, encoding="utf-8")
    print("[OK] Updated stream_sniper_bp.py per-dossier handle metadata.")


if __name__ == "__main__":
    patch_faas_app()
    patch_blueprint()
