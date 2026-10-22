#!/home/james/stacklabs/.venv/bin/python3
"""
Surgical patch for WO0011293:
1. Hardens extract_video_id() and fixes get_snipe_catalog() timestamp sorting in scripts/blueprints/stream_sniper_bp.py so newly sniped videos (e.g. xHWbeRw680k) sort first by mtime/ISO timestamp.
2. Fixes handleSnipeStream() and handleSnipeStreamWithUrl() in apps/faas/src/App.tsx:
   - Removes premature finally { setIsSniping(false) } so isSniping remains true during HTTP 202 polling.
   - Extracts clean 11-char YouTube ID from youtu.be/<id>?is=..., youtube.com/watch?v=<id>, youtube.com/live/<id>, youtube.com/shorts/<id>.
   - Replaces static READY badge with live status badge (SNIPING ID: <id>... -> PARSING TRANSCRIPT... -> COMPLETE or red ERROR: <reason>).
   - Immediately switches currentResult to the newly sniped dossier upon completion.
"""

from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
BP_FILE = REPO_ROOT / "scripts" / "blueprints" / "stream_sniper_bp.py"
APP_TSX = REPO_ROOT / "apps" / "faas" / "src" / "App.tsx"


def patch_backend_blueprint() -> None:
    text = BP_FILE.read_text(encoding="utf-8")

    old_extract = """def extract_video_id(url: str) -> str:
    m = re.search(r'(?:v=|\\/|youtu\\.be\\/)([0-9A-Za-z_-]{11})', url)
    if m:
        return m.group(1)
    if re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
    return hashlib.md5(url.encode()).hexdigest()[:12]"""

    new_extract = """def extract_video_id(url: str) -> str:
    clean = url.strip()
    patterns = [
        r'(?:youtu\\.be\\/|youtube\\.com\\/(?:embed\\/|v\\/|shorts\\/|live\\/))([0-9A-Za-z_-]{11})(?=[?&/#]|$)',
        r'[?&]v=([0-9A-Za-z_-]{11})(?=[&#]|$)',
        r'^([0-9A-Za-z_-]{11})$',
    ]
    for pat in patterns:
        m = re.search(pat, clean)
        if m:
            return m.group(1)
    return hashlib.md5(clean.encode()).hexdigest()[:12]"""

    if old_extract in text:
        text = text.replace(old_extract, new_extract)

    old_sort = """    catalog.sort(key=lambda x: x.get("registered_at", ""), reverse=True)"""
    new_sort = """    for item in catalog:
        vid = item.get("video_id", "")
        brief_p = SNIPES_DIR / vid / "summary_intel_brief.md"
        json_p = SNIPES_DIR / f"{vid}.json"
        mtime = brief_p.stat().st_mtime if brief_p.exists() else (json_p.stat().st_mtime if json_p.exists() else 0.0)
        item["registered_at"] = str(item.get("registered_at", "")).replace("T", " ")
        item["_sort_mtime"] = mtime
    catalog.sort(key=lambda x: (x.get("_sort_mtime", 0.0), x.get("registered_at", "")), reverse=True)"""

    if old_sort in text:
        text = text.replace(old_sort, new_sort)

    BP_FILE.write_text(text, encoding="utf-8")
    print("Patched scripts/blueprints/stream_sniper_bp.py successfully.")


def patch_frontend_app() -> None:
    text = APP_TSX.read_text(encoding="utf-8")

    # 1. Add snipeStatus and snipeError state next to snipeElapsed
    old_state = """  const [snipeStage, setSnipeStage] = useState('');
  const [snipeElapsed, setSnipeElapsed] = useState(0);"""

    new_state = """  const [snipeStage, setSnipeStage] = useState('');
  const [snipeElapsed, setSnipeElapsed] = useState(0);
  const [snipeStatusText, setSnipeStatusText] = useState<string>('READY');
  const [snipeStatusTone, setSnipeStatusTone] = useState<'ready' | 'active' | 'done' | 'error'>('ready');"""

    if old_state in text and "snipeStatusText" not in text:
        text = text.replace(old_state, new_state)

    # 2. Replace handleSnipeStream and handleSnipeStreamWithUrl with unified, non-premature-finally implementation
    start_marker = "  // Handlers\n  const handleSnipeStream = async () => {"
    end_marker = "  const handleDemandBarfHotTake = async () => {"

    if start_marker in text and end_marker in text:
        before = text[:text.index(start_marker)]
        after = text[text.index(end_marker):]

        new_handlers = """  // Extract clean 11-char YouTube ID from youtu.be/<id>?is=..., watch?v=<id>, /live/<id>, /shorts/<id>
  const extractYoutubeIdClient = (rawUrl: string): string | null => {
    const clean = rawUrl.trim();
    const patterns = [
      /(?:youtu\\.be\\/|youtube\\.com\\/(?:embed\\/|v\\/|shorts\\/|live\\/))([0-9A-Za-z_-]{11})(?=[?&/#]|$)/,
      /[?&]v=([0-9A-Za-z_-]{11})(?=[&#]|$)/,
      /^([0-9A-Za-z_-]{11})$/,
    ];
    for (const pat of patterns) {
      const m = clean.match(pat);
      if (m && m[1]) return m[1];
    }
    return null;
  };

  // Handlers
  const executeStreamSnipe = async (rawInputUrl: string) => {
    const trimmed = rawInputUrl.trim();
    if (!trimmed) {
      setSnipeStatusTone('error');
      setSnipeStatusText('ERROR: EMPTY URL');
      return;
    }

    const parsedId = extractYoutubeIdClient(trimmed);
    if (!parsedId) {
      setSnipeStatusTone('error');
      setSnipeStatusText('ERROR: INVALID YOUTUBE URL');
      return;
    }

    const canonicalUrl = `https://www.youtube.com/watch?v=${parsedId}`;
    setStreamUrl(trimmed);
    setIsSniping(true);
    setSnipeProgress(15);
    setSnipeElapsed(0);
    setSnipeStatusTone('active');
    setSnipeStatusText(`SNIPING ID: ${parsedId}...`);
    setSnipeStage(`SNIPING ID: ${parsedId} • Extracting audio track...`);

    const startTime = Date.now();
    const stageTimer = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
      setSnipeElapsed(elapsedSec);
      setSnipeProgress(prev => {
        const next = prev < 30 ? prev + 3 : prev < 75 ? prev + 2 : prev < 95 ? prev + 1 : 95;
        if (next < 35) {
          setSnipeStatusText(`SNIPING ID: ${parsedId}...`);
          setSnipeStage(`SNIPING ID: ${parsedId} • Downloading audio stream...`);
        } else if (next < 80) {
          setSnipeStatusText('PARSING TRANSCRIPT...');
          setSnipeStage(`ID: ${parsedId} • Transcribing & aligning segments...`);
        } else {
          setSnipeStatusText('BUILDING 3-BULLET BRIEF...');
          setSnipeStage(`ID: ${parsedId} • Synthesizing 3-Bullet Intel Brief...`);
        }
        return next;
      });
    }, 1500);

    try {
      const res = await fetch(`${API_BASE}/api/snipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: canonicalUrl })
      });

      if (!res.ok && res.status !== 202) {
        clearInterval(stageTimer);
        const rawText = await res.text();
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = JSON.parse(rawText);
          errMessage = errData.detail || errData.message || errMessage;
        } catch {
          errMessage = rawText.slice(0, 120) || errMessage;
        }
        setSnipeStatusTone('error');
        setSnipeStatusText(`ERROR: ${errMessage.toUpperCase().slice(0, 36)}`);
        setSnipeStage(`Error: ${errMessage}`);
        setIsSniping(false);
        return;
      }

      const data = await res.json();
      if (data.status === 'ready' || (Array.isArray(data.bullets) && data.bullets.length > 0)) {
        clearInterval(stageTimer);
        setSnipeProgress(100);
        setSnipeStatusTone('done');
        setSnipeStatusText(`COMPLETE (${parsedId})`);
        setSnipeStage('COMPLETE • 3-Bullet Brief Loaded');
        setCurrentResult(data);
        setSniperView('brief');
        setIsSniping(false);
        return;
      }

      if (res.status === 202 || data.status === 'processing') {
        const videoId = data.video_id || parsedId;
        setSnipeStatusTone('active');
        setSnipeStatusText(`PARSING TRANSCRIPT (${videoId})...`);
        let attempts = 0;
        const pollInterval = setInterval(async () => {
          attempts += 1;
          try {
            const checkRes = await fetch(`${API_BASE}/api/snipe/${videoId}`);
            if (checkRes.ok && checkRes.status === 200) {
              const pollData = await checkRes.json();
              if (pollData.status === 'ready' || (Array.isArray(pollData.bullets) && pollData.bullets.length > 0)) {
                clearInterval(pollInterval);
                clearInterval(stageTimer);
                setSnipeProgress(100);
                setSnipeStatusTone('done');
                setSnipeStatusText(`COMPLETE (${videoId})`);
                setSnipeStage('COMPLETE • 3-Bullet Brief Loaded');
                setCurrentResult(pollData);
                setSniperView('brief');
                setIsSniping(false);
                return;
              }
            } else if (checkRes.status === 404 && attempts > 6) {
              clearInterval(pollInterval);
              clearInterval(stageTimer);
              setSnipeStatusTone('error');
              setSnipeStatusText(`ERROR: SNIPE FAILED (${videoId})`);
              setIsSniping(false);
              return;
            }
          } catch {
            // continue polling while background worker completes
          }
          if (attempts >= 90) {
            clearInterval(pollInterval);
            clearInterval(stageTimer);
            setSnipeStatusTone('error');
            setSnipeStatusText('ERROR: SNIPE TIMEOUT');
            setIsSniping(false);
          }
        }, 2000);
        return;
      }

      clearInterval(stageTimer);
      setSnipeStatusTone('error');
      setSnipeStatusText(`ERROR: ${(data.detail || data.message || 'PARSE FAILED').toString().toUpperCase().slice(0, 32)}`);
      setIsSniping(false);
    } catch (err: any) {
      clearInterval(stageTimer);
      setSnipeStatusTone('error');
      setSnipeStatusText(`ERROR: ${(err?.message || 'NETWORK FAILURE').toUpperCase().slice(0, 32)}`);
      setIsSniping(false);
    }
  };

  const handleSnipeStream = async () => {
    await executeStreamSnipe(streamUrl);
  };

  const handleSnipeStreamWithUrl = async (targetUrl: string) => {
    await executeStreamSnipe(targetUrl);
  };

"""
        text = before + new_handlers + after

    # 3. Replace the static READY badge in the Sniper card with the live snipeStatusText badge
    old_badge = """                <span className="text-[10px] font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">READY</span>"""
    new_badge = """                <span
                  data-testid="sniper-status-badge"
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    snipeStatusTone === 'error'
                      ? 'text-rose-300 bg-rose-500/15 border-rose-500/40'
                      : snipeStatusTone === 'active'
                      ? 'text-amber-300 bg-amber-500/15 border-amber-500/40 animate-pulse'
                      : snipeStatusTone === 'done'
                      ? 'text-emerald-300 bg-emerald-500/20 border-emerald-500/40'
                      : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  }`}
                >
                  {snipeStatusText}
                </span>"""

    if old_badge in text:
        text = text.replace(old_badge, new_badge)

    APP_TSX.write_text(text, encoding="utf-8")
    print("Patched apps/faas/src/App.tsx successfully.")


if __name__ == "__main__":
    patch_backend_blueprint()
    patch_frontend_app()
