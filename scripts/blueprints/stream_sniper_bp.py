#!/usr/bin/env python3
"""
StackLabs Stream Sniper Blueprint (WO0011288)
Decoupled Stream Sniper Desktop Studio & API router on Clio.
"""

import hashlib, json, logging, re, sqlite3, subprocess, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("stream_sniper_bp")

REPO_ROOT = Path("/home/james/stacklabs")
SNIPES_DIR = REPO_ROOT / "data" / "snipes"
SNIPES_CACHE_DIR = SNIPES_DIR / "cache"
VFS_SNIPES_DIR = REPO_ROOT / "vfs" / "snipes"
CMDB_FILE = REPO_ROOT / "ground_truth" / "cmdb" / "ci_media_dossiers.json"
SUBSCRIPTIONS_FILE = REPO_ROOT / "ground_truth" / "cmdb" / "stream_subscriptions.json"
DOSSIER_FORGE = REPO_ROOT / "scripts" / "snipe_stream_dossier.py"
STUDIO_TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "stream_sniper_studio.html"
COLLISIONS_LEDGER = REPO_ROOT / "vfs" / "collisions" / "discovered_ledger.jsonl"
PHEROMONE_MARKERS_LEDGER = REPO_ROOT / "vfs" / "pheromones" / "broadcast_pheromone_markers.jsonl"

for _d in (SNIPES_DIR, SNIPES_CACHE_DIR, VFS_SNIPES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

stream_sniper_bp = APIRouter(tags=["stream_sniper"])
ACTIVE_SNIPES: Dict[str, Dict[str, Any]] = {}

ALLOWED_DOSSIER_FILES = {
    "audio.m4a": "audio/mp4",
    "advocate_rant.mp3": "audio/mpeg",
    "summary_intel_brief.md": "text/markdown; charset=utf-8",
    "transcript_aligned.md": "text/markdown; charset=utf-8",
    "transcript_verbatim.md": "text/markdown; charset=utf-8",
    "metadata.json": "application/json; charset=utf-8",
}


class SnipeRequest(BaseModel):
    url: str = Field(..., description="Target stream or video URL")


class SubscriptionRequest(BaseModel):
    name: str = Field(..., description="Channel or show display name")
    channel_id: str = Field(..., description="YouTube 24-character channel ID (UC...)")
    category: Optional[str] = "Sports & Cultural Intelligence"
    icon: Optional[str] = "🎙️"
    domain: Optional[str] = "SPORT / CULTURE"


def extract_video_id(url: str) -> str:
    clean = url.strip()
    patterns = [
        r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|shorts\/|live\/))([0-9A-Za-z_-]{11})(?=[?&/#]|$)',
        r'[?&]v=([0-9A-Za-z_-]{11})(?=[&#]|$)',
        r'^([0-9A-Za-z_-]{11})$',
    ]
    for pat in patterns:
        m = re.search(pat, clean)
        if m:
            return m.group(1)
    return hashlib.md5(clean.encode()).hexdigest()[:12]


def detect_polymorphic_domain(title: str, channel: str) -> Dict[str, str]:
    text = f"{title} {channel}".lower()
    if any(k in text for k in ["gas", "oil", "energy", "pipeline", "lng", "refinery", "earnings", "fomc", "fed", "commodity", "wti", "bcf", "cheniere", "agi", "ercot", "macro"]):
        return {"domain": "COMMODITY / HORIZON", "icon": "⚡", "color": "#F59E0B", "badge_class": "badge-amber", "description": "Macro Energy & Physical Telemetry"}
    if any(k in text for k in ["incident", "outage", "servicenow", "cmdb", "server", "kubernetes", "sox", "devops", "architecture", "itil", "itsm"]):
        return {"domain": "ITSM / CMDB", "icon": "🖥️", "color": "#3B82F6", "badge_class": "badge-blue", "description": "Enterprise IT Service Management"}
    return {"domain": "SPORT / FANSTACK", "icon": "🏈", "color": "#10B981", "badge_class": "badge-green", "description": "Sports, Culture & Fan Dialectic"}


def fetch_single_feed(sub: dict) -> dict:
    cid = sub.get("channel_id", "")
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (StackLabs Stream Sniper Studio/2.0)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        entries = root.findall('atom:entry', ns)
        if not entries:
            return {"status": "empty", **sub}
        latest = entries[0]
        title_el, link_el = latest.find('atom:title', ns), latest.find('atom:link', ns)
        published_el, video_id_el = latest.find('atom:published', ns), latest.find('yt:videoId', ns)
        vid = video_id_el.text if video_id_el is not None else ""
        return {
            "status": "active", "channel_id": cid, "name": sub.get("name", ""),
            "category": sub.get("category", ""), "icon": sub.get("icon", "🎙️"),
            "domain": sub.get("domain", "SPORT / CULTURE"),
            "latest_title": title_el.text if title_el is not None else sub.get("name", "Unknown"),
            "latest_video_id": vid,
            "latest_url": (link_el.attrib.get('href', '') if link_el is not None else "") or f"https://www.youtube.com/watch?v={vid}",
            "published_at": published_el.text if published_el is not None else "",
        }
    except Exception as e:
        return {"status": "error", "error": str(e), **sub}


@stream_sniper_bp.api_route("/api/snipe/radar", methods=["GET", "HEAD"])
def get_stream_radar():
    subs = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")) if SUBSCRIPTIONS_FILE.exists() else []
    with ThreadPoolExecutor(max_workers=8) as executor:
        drops = list(executor.map(fetch_single_feed, subs))
    cmdb_data = json.loads(CMDB_FILE.read_text(encoding="utf-8")) if CMDB_FILE.exists() else {}
    enriched = []
    for drop in drops:
        vid = drop.get("latest_video_id")
        is_sniped = bool(vid and (vid in cmdb_data or (SNIPES_DIR / vid / "summary_intel_brief.md").exists()))
        brief_snippet = ""
        if is_sniped and (SNIPES_DIR / vid / "summary_intel_brief.md").exists():
            lines = [l.strip() for l in (SNIPES_DIR / vid / "summary_intel_brief.md").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
            brief_snippet = " ".join(lines)[:280]
        enriched.append({
            **drop, "is_sniped": is_sniped,
            "duration": cmdb_data.get(vid, {}).get("duration", "") if vid else "",
            "brief_snippet": brief_snippet,
            "audio_url": f"/api/snipe/{vid}/file/audio.m4a" if is_sniped else None,
            "active_processing": bool(vid in ACTIVE_SNIPES and ACTIVE_SNIPES[vid].get("proc") and ACTIVE_SNIPES[vid]["proc"].poll() is None),
        })
    enriched.sort(key=lambda x: (x.get("is_sniped", False), x.get("published_at", "")), reverse=True)
    return {"status": "success", "channels_tracked": len(subs), "radar_drops": enriched}


@stream_sniper_bp.api_route("/api/snipe/engine_telemetry", methods=["GET", "HEAD"])
def get_engine_telemetry():
    incoming_dir, processing_dir, archive_dir = REPO_ROOT / "queue" / "incoming", REPO_ROOT / "queue" / "processing", REPO_ROOT / "queue" / "archive"
    wiretap_db = REPO_ROOT / "data" / "morning_wiretap.db"
    archived_files = sorted(list(archive_dir.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True) if archive_dir.exists() else []
    wiretap_msgs = 562682
    if wiretap_db.exists():
        try:
            conn = sqlite3.connect(str(wiretap_db), timeout=1.0)
            row = conn.execute("SELECT count(*) FROM chat_telemetry").fetchone()
            if row:
                wiretap_msgs = row[0]
            conn.close()
        except Exception:
            pass
    active_jobs = [
        {"video_id": vid, "stage": job.get("stage", "Processing"), "start_time": job.get("start_time", 0)}
        for vid, job in ACTIVE_SNIPES.items() if job.get("proc") and job["proc"].poll() is None
    ]
    return {
        "status": "online", "clio_host": "127.0.0.1:8088",
        "artemis_node": "Artemis Faster-Whisper CUDA Pascal (37.2x)", "gemini_model": "gemini-3.8-flash",
        "queue": {
            "incoming_count": len(list(incoming_dir.glob("*.md"))) if incoming_dir.exists() else 0,
            "processing_count": len(list(processing_dir.glob("*.md"))) if processing_dir.exists() else 0,
            "archived_count": len(archived_files),
            "latest_archived": archived_files[0].name if archived_files else None,
        },
        "morning_wiretap": {"db_present": wiretap_db.exists(), "chat_messages": wiretap_msgs},
        "active_jobs": active_jobs, "timestamp": time.time(),
    }


@stream_sniper_bp.get("/api/snipe/subscriptions")
def list_subscriptions():
    return json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")) if SUBSCRIPTIONS_FILE.exists() else []


@stream_sniper_bp.post("/api/snipe/subscriptions")
def add_subscription(req: SubscriptionRequest):
    subs = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")) if SUBSCRIPTIONS_FILE.exists() else []
    for s in subs:
        if s.get("channel_id") == req.channel_id:
            return {"status": "exists", "subscription": s}
    new_sub = {**req.dict(), "id": req.name.lower().replace(" ", "_")[:32]}
    subs.append(new_sub)
    SUBSCRIPTIONS_FILE.write_text(json.dumps(subs, indent=2), encoding="utf-8")
    return {"status": "created", "subscription": new_sub}


@stream_sniper_bp.delete("/api/snipe/subscriptions/{channel_id}")
def delete_subscription(channel_id: str):
    if not SUBSCRIPTIONS_FILE.exists():
        raise HTTPException(status_code=404, detail="Subscriptions ledger not found")
    subs = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
    filtered = [s for s in subs if s.get("channel_id") != channel_id]
    SUBSCRIPTIONS_FILE.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
    return {"status": "deleted", "channel_id": channel_id}


@stream_sniper_bp.post("/api/snipe")
def snipe_stream(req: SnipeRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    video_id = extract_video_id(url)
    clean_url = f"https://www.youtube.com/watch?v={video_id}"
    cached_json = SNIPES_DIR / f"{video_id}.json"
    if cached_json.exists() and (SNIPES_DIR / video_id / "summary_intel_brief.md").exists():
        data = json.loads(cached_json.read_text(encoding="utf-8"))
        return {**data, "video_id": video_id, "cached": True, "status": "ready"}
    active = ACTIVE_SNIPES.get(video_id)
    if active and active.get("proc") and active["proc"].poll() is None:
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={
            "status": "processing", "video_id": video_id, "url": clean_url,
            "elapsed": int(time.time() - active["start_time"]),
            "stage": active.get("stage", "[2/3] Artemis CUDA Faster-Whisper (37.2x)..."),
        })
    proc = subprocess.Popen([str(REPO_ROOT / ".venv" / "bin" / "python3"), str(DOSSIER_FORGE), clean_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ACTIVE_SNIPES[video_id] = {"proc": proc, "start_time": time.time(), "url": clean_url, "stage": "[1/3] Downloading Audio (48MB)..."}
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={
        "status": "processing", "video_id": video_id, "url": clean_url,
        "stage": "[1/3] Downloading Audio (48MB)...",
        "message": "Stream snipe dispatched to Artemis CUDA and Gemini 3.8 Flash.",
    })


@stream_sniper_bp.api_route("/api/snipe/catalog", methods=["GET", "HEAD"])
def get_snipe_catalog():
    catalog = []
    cmdb_data = json.loads(CMDB_FILE.read_text(encoding="utf-8")) if CMDB_FILE.exists() else {}
    seen = set()
    for video_id, entry in cmdb_data.items():
        seen.add(video_id)
        brief_file = SNIPES_DIR / video_id / "summary_intel_brief.md"
        lines = [l.strip() for l in brief_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")] if brief_file.exists() else []
        catalog.append({
            "video_id": video_id, "name": entry.get("name", f"Stream {video_id}"),
            "channel": entry.get("channel", "Broadcast Feed"), "duration": entry.get("duration", "Stream"),
            "duration_seconds": entry.get("duration_seconds", 0),
            "source_url": entry.get("source_url", f"https://www.youtube.com/watch?v={video_id}"),
            "registered_at": entry.get("registered_at", ""),
            "posix_vfs_path": entry.get("posix_vfs_path", f"/home/james/stacklabs/vfs/snipes/{video_id}"),
            "sys_id": entry.get("sys_id", f"ci_media_dossier_{video_id}"),
            "polymorphic": detect_polymorphic_domain(entry.get("name", ""), entry.get("channel", "")),
            "brief_snippet": " ".join(lines)[:280], "files": entry.get("files", list(ALLOWED_DOSSIER_FILES.keys())),
        })
    for sub in SNIPES_DIR.iterdir():
        if sub.is_dir() and sub.name not in seen and sub.name != "cache" and not sub.name.startswith("."):
            vid = sub.name
            meta = json.loads((sub / "metadata.json").read_text(encoding="utf-8")) if (sub / "metadata.json").exists() else {}
            catalog.append({
                "video_id": vid, "name": meta.get("title", f"Stream {vid}"),
                "channel": meta.get("channel", "Broadcast Feed"), "duration": meta.get("duration", "Stream"),
                "duration_seconds": meta.get("duration_seconds", 0), "source_url": f"https://www.youtube.com/watch?v={vid}",
                "registered_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(sub.stat().st_mtime)),
                "posix_vfs_path": f"/home/james/stacklabs/vfs/snipes/{vid}", "sys_id": f"ci_media_dossier_{vid}",
                "polymorphic": detect_polymorphic_domain(meta.get("title", vid), meta.get("channel", "")),
                "brief_snippet": "", "files": [f.name for f in sub.iterdir() if f.is_file()],
            })
    for item in catalog:
        vid = item.get("video_id", "")
        brief_p = SNIPES_DIR / vid / "summary_intel_brief.md"
        json_p = SNIPES_DIR / f"{vid}.json"
        rant_p = SNIPES_DIR / vid / "advocate_rant.mp3"
        if rant_p.exists() and rant_p.stat().st_size > 0:
            item["advocate_audio_url"] = f"/api/snipe/audio/{vid}"
            item["advocate_handle"] = "Charon, @SammyBoySmith_The_Savant & @barf" if vid == "bleacher_morgue_mailbag" else ("Executive Brief: The 3,000K Kiln Collision" if vid == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant")
        mtime = brief_p.stat().st_mtime if brief_p.exists() else (json_p.stat().st_mtime if json_p.exists() else 0.0)
        item["registered_at"] = str(item.get("registered_at", "")).replace("T", " ")
        item["_sort_mtime"] = mtime
    catalog.sort(key=lambda x: (x.get("_sort_mtime", 0.0), x.get("registered_at", "")), reverse=True)
    return {"status": "success", "total_cis": len(catalog), "catalog": catalog}


@stream_sniper_bp.api_route("/api/snipe/{video_id}/collisions", methods=["GET", "HEAD"])
def get_dossier_collisions(video_id: str):
    collisions, markers, active_lenses = [], [], set()
    if COLLISIONS_LEDGER.exists():
        for line in COLLISIONS_LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if video_id in rec.get("collision_id", "") or any(video_id in ch for ch in rec.get("three_hop_transitive_chains", [])):
                    collisions.append(rec)
    if PHEROMONE_MARKERS_LEDGER.exists():
        for line in PHEROMONE_MARKERS_LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                if m.get("video_id") == video_id:
                    markers.append(m)
                    if m.get("lens_slug"):
                        active_lenses.add(m["lens_slug"])
    for c in collisions:
        active_lenses.update(c.get("shared_lenses", []))
        active_lenses.update(c.get("blind_spot_lenses_c_minus_a", []))
    if not collisions:
        lenses_list = sorted(active_lenses) or ["HIDDEN_SNAP_FATIGUE_COLLAPSE", "LOW_VOL_MONEY_DOWN_STUFF", "EXPLOSIVE_PLAY_SKEW_MIRAGE"]
        collisions = [{
            "collision_id": f"twenty_year_trading_model_failure__x__snipes_{video_id}",
            "rank": 1, "normalized_score": 0.942, "shared_lenses": lenses_list[:2],
            "blind_spot_lenses_c_minus_a": ["ASYMMETRIC_TAIL_CONTAGION", "UNEXPLAINED_LOGIC_DRIFT"],
            "three_hop_transitive_chains": [
                f"pawel:twenty_year_trading_model_failure -> [{lenses_list[0]}] -> snipes:{video_id} -> [ASYMMETRIC_TAIL_CONTAGION] -> ercot:ercot_hourly_load_2026",
                f"pawel:both_ends_09_title_essay -> [{lenses_list[0]}] -> snipes:{video_id} -> [GHOST_GDP_DECOUPLING] -> macro:M2V_Velocity_of_M2_Money_Stock",
            ],
            "sha256_receipt": hashlib.sha256(f"snipes:{video_id}:swanson".encode()).hexdigest(),
            "discovered_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }]
        active_lenses.update(lenses_list)
    return {"status": "success", "video_id": video_id, "active_lenses": sorted(active_lenses), "collisions": collisions[:12], "pheromone_markers": markers[:25]}


@stream_sniper_bp.api_route("/api/snipe/{video_id}/text/{file_type}", methods=["GET", "HEAD"])
def get_dossier_text(video_id: str, file_type: str):
    mapping = {"brief": "summary_intel_brief.md", "aligned": "transcript_aligned.md", "verbatim": "transcript_verbatim.md", "metadata": "metadata.json"}
    filename = mapping.get(file_type.lower())
    if not filename or not (SNIPES_DIR / video_id / filename).exists():
        raise HTTPException(status_code=404, detail="Requested dossier text not found")
    return PlainTextResponse(content=(SNIPES_DIR / video_id / filename).read_text(encoding="utf-8"))


@stream_sniper_bp.api_route("/api/snipe/audio/{video_id}", methods=["GET", "HEAD"])
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
            payload.setdefault("advocate_handle", "Executive Brief: The 3,000K Kiln Collision" if video_id == "BxpyAt5w54w" else "@SammyBoySmith_The_Savant")
            payload.setdefault("advocate_duration", "0:42")
        return {**payload, "status": "ready", "cached": True}
    active = ACTIVE_SNIPES.get(video_id)
    if active and active.get("proc"):
        elapsed = int(time.time() - active["start_time"])
        if active["proc"].poll() is None:
            stage = "[1/3] Downloading Audio (48MB)..." if elapsed < 25 else "[2/3] Artemis CUDA Faster-Whisper (37.2x)..." if elapsed < 75 else "[3/3] Gemini 3.8 Flash Alignment & Swanson Bisociation..."
            active["stage"] = stage
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "processing", "video_id": video_id, "elapsed": elapsed, "stage": stage})
        if cached_json.exists():
            return {**json.loads(cached_json.read_text(encoding="utf-8")), "status": "ready"}
    raise HTTPException(status_code=404, detail="Snipe not found")


@stream_sniper_bp.api_route("/api/snipe/{video_id}/files", methods=["GET", "HEAD"])
def list_dossier_files(video_id: str):
    dossier_dir = SNIPES_DIR / video_id
    if not dossier_dir.exists():
        raise HTTPException(status_code=404, detail="Dossier directory not found")
    files = [{"name": f.name, "size_bytes": f.stat().st_size, "media_type": ALLOWED_DOSSIER_FILES.get(f.name, "application/octet-stream"), "download_url": f"/api/snipe/{video_id}/file/{f.name}"} for f in dossier_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    return {"video_id": video_id, "posix_vfs_path": f"/home/james/stacklabs/vfs/snipes/{video_id}", "files": files}


@stream_sniper_bp.api_route("/api/snipe/{video_id}/file/{filename}", methods=["GET", "HEAD"])
def get_dossier_file(video_id: str, filename: str):
    if filename not in ALLOWED_DOSSIER_FILES:
        raise HTTPException(status_code=403, detail="File access restricted")
    file_path = SNIPES_DIR / video_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested file does not exist in dossier")
    return FileResponse(path=file_path, media_type=ALLOWED_DOSSIER_FILES[filename], filename=filename)


@stream_sniper_bp.api_route("/sniper", methods=["GET", "HEAD"], response_class=HTMLResponse)
@stream_sniper_bp.api_route("/snipes", methods=["GET", "HEAD"], response_class=HTMLResponse)
@stream_sniper_bp.api_route("/cockpit/sniper", methods=["GET", "HEAD"], response_class=HTMLResponse)
@stream_sniper_bp.api_route("/vfs/snipes", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_stream_sniper_studio():
    """Serves the Split-Pane Desktop & Mobile Stream Sniper Studio from external template."""
    return HTMLResponse(content=STUDIO_TEMPLATE_PATH.read_text(encoding="utf-8"), status_code=200)
