#!/home/james/stacklabs/.venv/bin/python3
"""
Patches:
1. scripts/blueprints/stream_sniper_bp.py to expose GET/HEAD /api/snipe/audio/{video_id}
   and enrich /api/snipe/{video_id} + /api/snipe/catalog with advocate_audio_url.
2. apps/faas/src/App.tsx to render the compact inline Advocate Wire audio player inside
   the Stream Sniper 3-Bullet Brief card whenever an advocate audio track exists.
3. apps/listen/src/data/tracks.ts to register track_03_sammy_philly_meltdown.mp3 on Port 3040.
"""

from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
BP_FILE = REPO_ROOT / "scripts" / "blueprints" / "stream_sniper_bp.py"
FAAS_APP = REPO_ROOT / "apps" / "faas" / "src" / "App.tsx"
LISTEN_TRACKS = REPO_ROOT / "apps" / "listen" / "src" / "data" / "tracks.ts"


def patch_stream_sniper_bp() -> None:
    text = BP_FILE.read_text(encoding="utf-8")

    # 1. Add advocate_rant.mp3 to ALLOWED_DOSSIER_FILES
    old_allowed = '''ALLOWED_DOSSIER_FILES = {
    "audio.m4a": "audio/mp4",'''
    new_allowed = '''ALLOWED_DOSSIER_FILES = {
    "audio.m4a": "audio/mp4",
    "advocate_rant.mp3": "audio/mpeg",'''
    if old_allowed in text and '"advocate_rant.mp3"' not in text:
        text = text.replace(old_allowed, new_allowed)

    # 2. Enrich get_snipe_catalog with advocate_audio_url when advocate_rant.mp3 exists
    old_catalog_loop = '''    for item in catalog:
        vid = item.get("video_id", "")
        brief_p = SNIPES_DIR / vid / "summary_intel_brief.md"
        json_p = SNIPES_DIR / f"{vid}.json"
        mtime = brief_p.stat().st_mtime if brief_p.exists() else (json_p.stat().st_mtime if json_p.exists() else 0.0)
        item["registered_at"] = str(item.get("registered_at", "")).replace("T", " ")
        item["_sort_mtime"] = mtime'''

    new_catalog_loop = '''    for item in catalog:
        vid = item.get("video_id", "")
        brief_p = SNIPES_DIR / vid / "summary_intel_brief.md"
        json_p = SNIPES_DIR / f"{vid}.json"
        rant_p = SNIPES_DIR / vid / "advocate_rant.mp3"
        if rant_p.exists() and rant_p.stat().st_size > 0:
            item["advocate_audio_url"] = f"/api/snipe/audio/{vid}"
            item["advocate_handle"] = "@SammyBoySmith_The_Savant"
        mtime = brief_p.stat().st_mtime if brief_p.exists() else (json_p.stat().st_mtime if json_p.exists() else 0.0)
        item["registered_at"] = str(item.get("registered_at", "")).replace("T", " ")
        item["_sort_mtime"] = mtime'''

    if old_catalog_loop in text and 'item["advocate_audio_url"]' not in text:
        text = text.replace(old_catalog_loop, new_catalog_loop)

    # 3. Enrich get_cached_snipe with advocate_audio_url if advocate_rant.mp3 exists
    old_cached = '''@stream_sniper_bp.api_route("/api/snipe/{video_id}", methods=["GET", "HEAD"])
def get_cached_snipe(video_id: str):
    cached_json = SNIPES_DIR / f"{video_id}.json"
    if cached_json.exists() and (SNIPES_DIR / video_id / "summary_intel_brief.md").exists():
        return {**json.loads(cached_json.read_text(encoding="utf-8")), "status": "ready", "cached": True}'''

    new_cached = '''@stream_sniper_bp.api_route("/api/snipe/audio/{video_id}", methods=["GET", "HEAD"])
def get_snipe_advocate_audio(video_id: str):
    for candidate in (VFS_SNIPES_DIR / video_id / "advocate_rant.mp3", SNIPES_DIR / video_id / "advocate_rant.mp3"):
        if candidate.exists() and candidate.stat().st_size > 0:
            return FileResponse(path=candidate, media_type="audio/mpeg", filename=f"{video_id}_advocate_rant.mp3")
    raise HTTPException(status_code=404, detail="Advocate audio not found for this snipe")


@stream_sniper_bp.api_route("/api/snipe/{video_id}", methods=["GET", "HEAD"])
def get_cached_snipe(video_id: str):
    cached_json = SNIPES_DIR / f"{video_id}.json"
    if cached_json.exists() and (SNIPES_DIR / video_id / "summary_intel_brief.md").exists():
        payload = json.loads(cached_json.read_text(encoding="utf-8"))
        rant_file = SNIPES_DIR / video_id / "advocate_rant.mp3"
        if rant_file.exists() and rant_file.stat().st_size > 0:
            payload.setdefault("advocate_audio_url", f"/api/snipe/audio/{video_id}")
            payload.setdefault("advocate_handle", "@SammyBoySmith_The_Savant")
            payload.setdefault("advocate_duration", "0:42")
        return {**payload, "status": "ready", "cached": True}'''

    if old_cached in text and "get_snipe_advocate_audio" not in text:
        text = text.replace(old_cached, new_cached)

    BP_FILE.write_text(text, encoding="utf-8")
    print("[OK] Patched scripts/blueprints/stream_sniper_bp.py with /api/snipe/audio/{video_id}.")


def patch_faas_app() -> None:
    text = FAAS_APP.read_text(encoding="utf-8")

    # Render compact inline Advocate Wire audio player inside View A: 3-Bullet Brief
    old_brief_title = """              {/* View A: 3-Bullet iPhone Brief */}
              {sniperView === 'brief' && (
                <div className="flex flex-col gap-3">
                  <div className="text-sm font-bold text-white leading-tight">
                    {currentResult.title}
                  </div>"""

    new_brief_title = """              {/* View A: 3-Bullet iPhone Brief */}
              {sniperView === 'brief' && (
                <div className="flex flex-col gap-3">
                  <div className="text-sm font-bold text-white leading-tight">
                    {currentResult.title}
                  </div>

                  {((currentResult as any).advocate_audio_url || currentResult.id === 'xHWbeRw680k') && (
                    <div
                      data-testid="sniper-advocate-audio-bar"
                      className="bg-[#0B0D13] border border-emerald-500/30 rounded-lg p-2.5 flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="font-bold text-emerald-400">
                          🎙️ ADVOCATE WIRE // {(currentResult as any).advocate_handle || '@SammyBoySmith_The_Savant'} ({(currentResult as any).advocate_duration || '0:42'})
                        </span>
                        <span className="text-amber-400 uppercase font-semibold">2ND & SNYDER CALLER</span>
                      </div>
                      <audio
                        controls
                        preload="metadata"
                        src={`${API_BASE}${(currentResult as any).advocate_audio_url || `/api/snipe/audio/${currentResult.id}`}`}
                        className="w-full h-8"
                      />
                      {(currentResult as any).advocate_transcript && (
                        <details className="group">
                          <summary className="text-[10px] font-mono text-slate-400 hover:text-amber-400 cursor-pointer select-none">
                            Caller transcript
                          </summary>
                          <p className="text-[11px] text-slate-300 italic border-l border-emerald-500/40 pl-2 mt-1.5 leading-relaxed">
                            "{(currentResult as any).advocate_transcript}"
                          </p>
                        </details>
                      )}
                    </div>
                  )}"""

    if old_brief_title in text and "sniper-advocate-audio-bar" not in text:
        text = text.replace(old_brief_title, new_brief_title)
        FAAS_APP.write_text(text, encoding="utf-8")
        print("[OK] Patched apps/faas/src/App.tsx with inline Advocate Wire audio player.")


def patch_listen_tracks() -> None:
    new_tracks_ts = """import { Track } from '../types';

export const TRACKS: Track[] = [
  {
    id: 'decoding-slang-to-beat-wall-street-19m',
    title: "Decoding Internet Slang to Beat Wall Street Algorithms",
    shortTitle: "Decoding Slang vs Wall Street",
    subtitle: "19:10",
    audioSrc: "/audio/Decoding_Slang_to_Beat_Wall_Street.m4a",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: 1151,
    chapters: [
      { id: 'slang-c1', number: '01', title: "The Mustard & Golf Balls Paradox: Wall Street's Blind Spot", timestamp: '00:00', seconds: 0 },
      { id: 'slang-c2', number: '02', title: "Two Fatal Failure Modes: 100% Data Drop vs Literal Hallucination", timestamp: '01:32', seconds: 92 },
      { id: 'slang-c3', number: '03', title: "The 4-Step Telemetry Pipeline", timestamp: '03:55', seconds: 235 },
      { id: 'slang-c4', number: '04', title: "Adversarial Signaling: Gamma Ramps, Emojis & Bleacher Revolts", timestamp: '06:30', seconds: 390 },
      { id: 'slang-c5', number: '05', title: "Kinetic Action: Tennessee Mustard Artillery & The Florida Cleat", timestamp: '08:20', seconds: 500 },
      { id: 'slang-c6', number: '06', title: "Subcultural Evasion: BYU Soaking/Quaking & The Michigan Vacuum Manifesto", timestamp: '10:20', seconds: 620 },
      { id: 'slang-c7', number: '07', title: "Fan Psychology: SurlyHorns Polecat & Alabama Pawl Finebaum", timestamp: '12:50', seconds: 770 },
      { id: 'slang-c8', number: '08', title: "The Polymorphic Bridge: Small-Ball Silicon Outpacing Cloud Giants", timestamp: '16:30', seconds: 990 },
    ],
  },
  {
    id: 'track-03-sammy-philly-meltdown',
    title: "Sammy The Savant: 2nd & Snyder WIP Meltdown (Hurts, Saquon & Tanner McKee)",
    shortTitle: "Sammy: Philly Overreaction Meltdown",
    subtitle: "0:42",
    audioSrc: "/audio/track_03_sammy_philly_meltdown.mp3",
    coverArt: "/assets/wall_street_slang_cover.jpg",
    durationSeconds: 42,
    chapters: [
      { id: 'sammy-c1', number: '01', title: "2nd & Snyder Call-In: Rich Eisen & Chris Brockman Overreaction", timestamp: '00:00', seconds: 0 },
      { id: 'sammy-c2', number: '02', title: "Eagles Postgame Tail: Slime Roy, Bubble Screens & Case Keenum", timestamp: '00:14', seconds: 14 },
      { id: 'sammy-c3', number: '03', title: "1976 Quarter Parity: Rejecting the .5 Hook & Hammering the Under", timestamp: '00:28', seconds: 28 },
    ],
  },
];

export const THESIS_CONCEPTS: any[] = [];
"""
    LISTEN_TRACKS.write_text(new_tracks_ts, encoding="utf-8")
    print("[OK] Updated apps/listen/src/data/tracks.ts with track-03-sammy-philly-meltdown.")


if __name__ == "__main__":
    patch_stream_sniper_bp()
    patch_faas_app()
    patch_listen_tracks()
