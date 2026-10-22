#!/home/james/stacklabs/.venv/bin/python3
"""
Surgical patch for WO0011291:
1. Reorders Sniper tab in apps/faas/src/App.tsx so URL Input + Snipe Button and 3-Bullet Brief Results sit ABOVE StreamRadarDeck.
2. Removes model name plastering ('(GEMINI 3.8 FLASH)', 'MODEL: ...') from apps/faas/src/App.tsx and scripts/templates/stream_sniper_studio.html.
"""

from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
APP_TSX = REPO_ROOT / "apps" / "faas" / "src" / "App.tsx"
STUDIO_HTML = REPO_ROOT / "scripts" / "templates" / "stream_sniper_studio.html"


def patch_app_tsx() -> None:
    text = APP_TSX.read_text(encoding="utf-8")

    # 1. Strip model name from Barf card
    text = text.replace(
        "ON-DEMAND BARF HOT TAKE ENGINE (GEMINI 3.8 FLASH)",
        "ON-DEMAND BARF HOT TAKE ENGINE",
    )
    text = text.replace(
        "MODEL: {demandedModel} • WIRETAP GROUNDED",
        "LIVE WIRETAP GROUNDED",
    )
    text = text.replace(
        "Custom Stream Ingress // Direct URL",
        "Snipe Stream URL",
    )
    text = text.replace(
        "Transcribing audio via Faster-Whisper (Artemis CUDA)...",
        "Transcribing audio...",
    )

    # 2. Move StreamRadarDeck below the Results Deck in the Sniper tab so URL Input + 3-Bullet Brief are at the very top
    radar_block = """            {/* Stream Radar Deck (Telemetry HUD + Live Drops) */}
            <StreamRadarDeck
              apiBase={API_BASE}
              onSelectStream={(url) => setStreamUrl(url)}
              onSnipeStream={(url) => {
                setStreamUrl(url);
                setTimeout(() => {
                  handleSnipeStreamWithUrl(url);
                }, 50);
              }}
              onLoadDossier={async (videoId) => {
                try {
                  const res = await fetch(`${API_BASE}/api/snipe/${videoId}`);
                  if (res.ok) {
                    const data = await res.json();
                    setCurrentResult(data);
                    setStreamUrl(data.url || `https://www.youtube.com/watch?v=${videoId}`);
                    setSniperView('brief');
                  }
                } catch (e) {
                  console.error("Failed to load dossier:", e);
                }
              }}
            />"""

    results_end_marker = """              {/* View C: VFS Media Dossier & CI Explorer */}
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

    if radar_block in text and results_end_marker in text:
        text = text.replace(radar_block + "\n\n", "")
        text = text.replace(
            results_end_marker,
            results_end_marker + "\n\n" + radar_block,
        )

    APP_TSX.write_text(text, encoding="utf-8")
    print("Patched App.tsx successfully.")


def patch_studio_html() -> None:
    if not STUDIO_HTML.exists():
        return
    html = STUDIO_HTML.read_text(encoding="utf-8")
    html = html.replace(
        "Pipeline Ready: Downloading ➔ Transcribing on Artemis ➔ Aligning in Gemini 3.8 Flash",
        "Ready to snipe stream",
    )
    html = html.replace("gemini-3.8-flash", "Active")
    html = html.replace("Artemis GTX 1060 CUDA (37.2x • $0.00)", "Local Audio Transcriber")
    STUDIO_HTML.write_text(html, encoding="utf-8")
    print("Patched stream_sniper_studio.html successfully.")


if __name__ == "__main__":
    patch_app_tsx()
    patch_studio_html()
