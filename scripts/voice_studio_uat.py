#!/usr/bin/env python3
"""
Voice Studio UAT — Standalone server on port 8888
Run: /home/james/stacklabs/.venv/bin/python3 scripts/voice_studio_uat.py
Open: http://localhost:8888
"""

import os, asyncio, tempfile, subprocess
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

app = FastAPI()

PERSONA_VOICES = {
    "barf":    {"voice": "en-US-ChristopherNeural", "rate": "+15%", "pitch": "-5Hz"},
    "dot":     {"voice": "en-US-AriaNeural",        "rate": "+5%",  "pitch": "+0Hz"},
    "barbara": {"voice": "en-US-JennyNeural",       "rate": "+5%",  "pitch": "+0Hz"},
    "default": {"voice": "en-US-GuyNeural",          "rate": "+10%", "pitch": "+0Hz"},
}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎙️ Voice Studio — Hot Takes UAT</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    font-family: 'Inter', sans-serif;
    background: #0a0a0f;
    color: #e2e8f0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .card {
    background: #13131a;
    border: 1px solid #1e1e2e;
    border-radius: 20px;
    padding: 2.5rem;
    width: 100%;
    max-width: 680px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.5);
  }

  .header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #1e1e2e;
  }

  .badge {
    background: linear-gradient(135deg, #f97316, #ef4444);
    color: white;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
  }

  h1 { font-size: 1.4rem; font-weight: 700; }
  h1 span { color: #f97316; }

  .subtitle { font-size: 0.8rem; color: #64748b; margin-top: 2px; }

  label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: #94a3b8;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .field { margin-bottom: 1.5rem; }

  .drop-zone {
    border: 2px dashed #2d2d3d;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: #f97316;
    background: rgba(249,115,22,0.05);
  }
  .drop-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
  .drop-icon { font-size: 2rem; margin-bottom: 8px; }
  .drop-text { font-size: 0.85rem; color: #64748b; }
  .drop-text strong { color: #e2e8f0; }
  .file-name { margin-top: 8px; font-size: 0.8rem; color: #f97316; font-weight: 600; }

  textarea {
    width: 100%;
    background: #0d0d15;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    line-height: 1.6;
    padding: 1rem;
    resize: vertical;
    min-height: 140px;
    transition: border-color 0.2s;
  }
  textarea:focus { outline: none; border-color: #f97316; }

  select {
    width: 100%;
    background: #0d0d15;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
    font-size: 0.875rem;
    padding: 0.75rem 1rem;
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 1rem center;
  }
  select:focus { outline: none; border-color: #f97316; }

  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

  button {
    width: 100%;
    background: linear-gradient(135deg, #f97316, #ef4444);
    border: none;
    border-radius: 12px;
    color: white;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    padding: 1rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 0.5rem;
  }
  button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(249,115,22,0.3); }
  button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .status {
    margin-top: 1.5rem;
    padding: 1rem 1.25rem;
    border-radius: 10px;
    font-size: 0.85rem;
    display: none;
  }
  .status.processing {
    display: block;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.3);
    color: #a5b4fc;
  }
  .status.success {
    display: block;
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.3);
    color: #86efac;
  }
  .status.error {
    display: block;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    color: #fca5a5;
  }

  .download-btn {
    display: none;
    margin-top: 1rem;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    text-decoration: none;
    color: white;
    font-weight: 700;
    padding: 0.875rem;
    border-radius: 12px;
    text-align: center;
    font-size: 0.95rem;
    transition: all 0.2s;
  }
  .download-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(34,197,94,0.3); }
  .download-btn.visible { display: block; }

  .spinner {
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: none;
  }
  button.loading .spinner { display: block; }
  button.loading .btn-text::after { content: 'Processing...'; }
  button.loading .btn-icon { display: none; }
  button:not(.loading) .btn-text::after { content: 'Dub Video'; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div>
      <h1>🎙️ Voice <span>Studio</span></h1>
      <div class="subtitle">Hot Takes Audio Dubbing — UAT</div>
    </div>
    <div class="badge">UAT</div>
  </div>

  <form id="dubForm">

    <div class="field">
      <label>📹 Flow Video</label>
      <div class="drop-zone" id="dropZone">
        <input type="file" id="videoFile" accept="video/*" required>
        <div class="drop-icon">🎬</div>
        <div class="drop-text"><strong>Drop your Flow video here</strong><br>or click to browse</div>
        <div class="file-name" id="fileName"></div>
      </div>
    </div>

    <div class="field">
      <label>📝 Script</label>
      <textarea id="scriptText" placeholder="Paste the final edited hot take script here..." required></textarea>
    </div>

    <div class="row">
      <div class="field">
        <label>🎭 Persona</label>
        <select id="persona">
          <option value="barf">Barf</option>
          <option value="dot">Dot</option>
          <option value="barbara">Barbara</option>
          <option value="default">Default</option>
        </select>
      </div>
      <div class="field">
        <label>🗣️ Voice Override</label>
        <select id="voiceOverride">
          <option value="">Use persona preset</option>
          <option value="en-US-ChristopherNeural">Christopher — Deep & Authoritative</option>
          <option value="en-US-GuyNeural">Guy — Gritty Sports Radio</option>
          <option value="en-US-EricNeural">Eric — Aggressive Energy</option>
          <option value="en-US-AriaNeural">Aria — Sharp & Direct</option>
          <option value="en-US-JennyNeural">Jenny — Confident & Clear</option>
          <option value="en-US-SaraNeural">Sara — Expressive</option>
        </select>
      </div>
    </div>

    <button type="submit" id="dubBtn">
      <div class="spinner"></div>
      <span class="btn-icon">🎙️</span>
      <span class="btn-text"></span>
    </button>
  </form>

  <div class="status" id="status"></div>
  <a class="download-btn" id="downloadBtn" href="#" download>⬇️ Download Dubbed Video</a>
</div>

<script>
  const fileInput = document.getElementById('videoFile');
  const fileName  = document.getElementById('fileName');
  const dropZone  = document.getElementById('dropZone');
  const form      = document.getElementById('dubForm');
  const dubBtn    = document.getElementById('dubBtn');
  const status    = document.getElementById('status');
  const dlBtn     = document.getElementById('downloadBtn');

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) fileName.textContent = '✅ ' + fileInput.files[0].name;
  });

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    fileInput.files = e.dataTransfer.files;
    if (fileInput.files[0]) fileName.textContent = '✅ ' + fileInput.files[0].name;
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const video  = fileInput.files[0];
    const script = document.getElementById('scriptText').value.trim();
    if (!video || !script) return;

    dubBtn.disabled = true;
    dubBtn.classList.add('loading');
    dlBtn.classList.remove('visible');
    status.className = 'status processing';
    status.textContent = '⚙️ Generating TTS audio and merging with video... this takes ~30 seconds.';

    const fd = new FormData();
    fd.append('video', video);
    fd.append('script', script);
    fd.append('persona', document.getElementById('persona').value);
    fd.append('voice_override', document.getElementById('voiceOverride').value);

    try {
      const res = await fetch('/dub', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Server error ' + res.status);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      dlBtn.href = url;
      dlBtn.download = `hot_take_dubbed_${Date.now()}.mp4`;
      dlBtn.classList.add('visible');
      status.className = 'status success';
      status.textContent = '✅ Done! Click the button below to download your dubbed video.';
    } catch (err) {
      status.className = 'status error';
      status.textContent = '❌ ' + err.message;
    } finally {
      dubBtn.disabled = false;
      dubBtn.classList.remove('loading');
    }
  });
</script>
</body>
</html>"""


def _get_dur(p):
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",p], capture_output=True, text=True)
    return float(r.stdout.strip())

def _merge(video, audio, out):
    dur_v = _get_dur(video)
    dur_a = _get_dur(audio)
    ratio = dur_a / dur_v
    filters, r = [], ratio
    while r > 2.0: filters.append("atempo=2.0"); r /= 2.0
    while r < 0.5: filters.append("atempo=0.5"); r *= 2.0
    filters.append(f"atempo={r:.4f}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f: adj = f.name
    subprocess.run(["ffmpeg","-y","-i",audio,"-filter:a",",".join(filters),adj], check=True, capture_output=True)
    subprocess.run(["ffmpeg","-y","-i",video,"-i",adj,"-c:v","copy","-c:a","aac","-map","0:v:0","-map","1:a:0","-shortest",out], check=True, capture_output=True)
    os.unlink(adj)


@app.get("/", response_class=HTMLResponse)
async def index(): return HTML


@app.post("/dub")
async def dub(video: UploadFile = File(...), script: str = Form(...),
              persona: str = Form("default"), voice_override: str = Form("")):
    import edge_tts
    preset = PERSONA_VOICES.get(persona.lower(), PERSONA_VOICES["default"])
    voice  = voice_override or preset["voice"]
    rate, pitch = preset["rate"], preset["pitch"]

    with tempfile.TemporaryDirectory() as tmp:
        vpath = os.path.join(tmp, "input.mp4")
        with open(vpath, "wb") as f: f.write(await video.read())
        apath = os.path.join(tmp, "tts.mp3")
        await edge_tts.Communicate(script, voice, rate=rate, pitch=pitch).save(apath)
        ts  = datetime.now().strftime("%Y%m%d%H%M%S")
        out = os.path.join(tmp, f"{persona}_dubbed_{ts}.mp4")
        _merge(vpath, apath, out)
        # Copy to inbox before temp dir is cleaned up
        inbox = f"/home/james/sovereign_inbox/daily_{datetime.now().strftime('%m%d%Y')}"
        os.makedirs(inbox, exist_ok=True)
        import shutil
        final = os.path.join(inbox, f"{persona}_dubbed_{ts}.mp4")
        shutil.copy(out, final)
        return FileResponse(final, media_type="video/mp4", filename=f"{persona}_hot_take_{ts}.mp4")


if __name__ == "__main__":
    print("\n🎙️  Voice Studio UAT running at → https://clio.taila01894.ts.net:8888\n")
    uvicorn.run(
        app, host="0.0.0.0", port=8888,
        ssl_keyfile="/home/james/ts_key.pem",
        ssl_certfile="/home/james/ts_cert.pem"
    )
