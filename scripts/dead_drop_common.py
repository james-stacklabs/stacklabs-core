#!/home/james/stacklabs/.venv/bin/python3
"""Shared imports, VFS personal space helpers, Artemis audio pipeline, and URL sniper bridge for drop.stacklabsllc.com."""
from pathlib import Path as _P

TEMPLATE_DIR = _P(__file__).resolve().parent / 'templates'


def load_template(name: str) -> str:
    with open(TEMPLATE_DIR / name, encoding='utf-8', newline='') as f:
        return f.read()


import os
import io
import re
import sys
import time
import socket
import sqlite3
import logging
import json
import queue
import threading
import uuid
import subprocess
import urllib.request
import urllib.parse
import mimetypes
import shutil
import hashlib
from typing import Dict, List, Any, Optional, Generator, Tuple
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory, abort, Response, make_response, redirect
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
from dotenv import load_dotenv


load_dotenv("/home/james/stacklabs/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

logger = logging.getLogger("PilotDropGateway")

PILOT_DROPS_DIR = "/home/james/stacklabs/pilot_drops"
INCOMING_DIR = "/home/james/stacklabs/pilot_drops/incoming"
THUMBNAILS_DIR = "/home/james/stacklabs/pilot_drops/.thumbnails"
VFS_SPACES_ROOT = "/home/james/stacklabs/vfs/spaces"
SPACE_SUBFOLDERS = ("uploads", "transcripts", "snipes", "audio", "investigations", "predictions")

SUBFOLDERS = ['incoming', 'screenshots', 'photos', 'audio', 'video', 'documents', 'archives', 'episodes']

os.makedirs(PILOT_DROPS_DIR, exist_ok=True)
os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(VFS_SPACES_ROOT, exist_ok=True)

DEFAULT_DROP_KEYS = {
    "1996",
    "1986"
}

AUTH_COOKIE_NAME = "stacklabs_drop_auth"
AUTH_SALT = "stacklabs_enterprise_drop_salt_v1"

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "your", "have", "are", "was", "were",
    "but", "not", "you", "they", "their", "what", "when", "where", "which", "who", "will", "would",
    "could", "should", "about", "into", "over", "after", "before", "under", "between", "through",
    "just", "like", "some", "more", "most", "other", "such", "only", "than", "then", "also", "very",
    "here", "there", "been", "being", "because", "while", "during", "within", "without", "across"
}


def normalize_user_slug(raw_sender: Optional[str] = "") -> str:
    """Normalize sender or ?from= parameter strictly to ^[a-z0-9_-]{2,32}$, defaulting to 'pawel' or 'james'."""
    val = (raw_sender or "").strip().lower()
    if not val or val in ("direct ingress", "anonymous", "default", "guest", "none", "null"):
        return "james"
    if "pawel" in val or "rudnicki" in val:
        return "pawel"
    val = re.sub(r"[^a-z0-9_-]+", "_", val)
    val = re.sub(r"_+", "_", val).strip("_-")
    if len(val) > 32:
        val = val[:32].rstrip("_-")
    if len(val) < 2 or not re.match(r"^[a-z0-9_-]{2,32}$", val):
        return "james"
    return val


def ensure_user_vfs_space(raw_sender: Optional[str] = "james") -> Dict[str, str]:
    """Ensure /home/james/stacklabs/vfs/spaces/<user_slug>/{uploads,transcripts,snipes,audio} exist."""
    slug = normalize_user_slug(raw_sender)
    space_root = os.path.join(VFS_SPACES_ROOT, slug)
    paths: Dict[str, str] = {
        "slug": slug,
        "root": space_root,
        "vfs_display": f"/vfs/spaces/{slug}",
    }
    os.makedirs(space_root, exist_ok=True)
    for sub in SPACE_SUBFOLDERS:
        sub_path = os.path.join(space_root, sub)
        os.makedirs(sub_path, exist_ok=True)
        paths[sub] = sub_path
    os.makedirs(os.path.join(paths["transcripts"], "essays"), exist_ok=True)
    os.makedirs(os.path.join(paths["transcripts"], "quant"), exist_ok=True)
    return paths


def link_or_copy_file(src_path: str, dst_path: str) -> None:
    """Hardlink or copy src_path to dst_path atomically without failing if target exists."""
    if not os.path.exists(src_path):
        return
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    if os.path.abspath(src_path) == os.path.abspath(dst_path):
        return
    if os.path.exists(dst_path):
        try:
            os.remove(dst_path)
        except OSError:
            pass
    try:
        os.link(src_path, dst_path)
    except OSError:
        shutil.copy2(src_path, dst_path)


def get_valid_access_keys() -> set:
    keys = set(DEFAULT_DROP_KEYS)
    env_key = os.environ.get("DROP_ACCESS_KEY")
    if env_key:
        keys.add(env_key.strip())
    return keys


def get_auth_hash(key: str) -> str:
    return hashlib.sha256(f"{AUTH_SALT}:{key.strip()}".encode()).hexdigest()


def get_all_valid_hashes() -> set:
    return {get_auth_hash(k) for k in get_valid_access_keys()}


def is_tailscale_request(req) -> bool:
    """Detect if request originates from Tailscale mesh or direct local loopback."""
    host = (req.host or '').lower()
    is_cf = bool(req.headers.get('CF-Connecting-IP') or req.headers.get('cf-ray'))

    if req.headers.get('Tailscale-User-Login') or req.headers.get('Tailscale-User-Name'):
        return True

    if not is_cf:
        if 'ts.net' in host or host.startswith('100.') or host.startswith('localhost') or host.startswith('127.0.0.1'):
            return True
        remote_ip = req.headers.get('X-Real-IP') or req.remote_addr or ''
        if remote_ip.startswith('100.') or remote_ip in ('127.0.0.1', '::1'):
            return True
    return False


def is_authorized(req) -> bool:
    if is_tailscale_request(req):
        return True
    q_key = req.args.get('key', '').strip()
    if q_key and q_key in get_valid_access_keys():
        return True
    cookie_val = req.cookies.get(AUTH_COOKIE_NAME, '').strip()
    if cookie_val and (cookie_val in get_all_valid_hashes() or cookie_val in get_valid_access_keys()):
        return True
    return False


os.makedirs(THUMBNAILS_DIR, exist_ok=True)

for sub in SUBFOLDERS:
    os.makedirs(os.path.join(PILOT_DROPS_DIR, sub), exist_ok=True)
    os.makedirs(os.path.join(THUMBNAILS_DIR, sub), exist_ok=True)

ensure_user_vfs_space("james")
ensure_user_vfs_space("pawel")

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif',
    '.dng', '.raw', '.heic', '.cr2', '.nef', '.arw'
}

for raw_ext in ['.dng', '.raw', '.heic', '.cr2', '.nef', '.arw', '.tif', '.tiff']:
    mimetypes.add_type('image/jpeg', raw_ext)

DOWNSIZE_MAX_DIM = 1600
DOWNSIZE_QUALITY = 85


def format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def get_unique_filename(target_dir: str, desired_name: str) -> str:
    """Generate a collision-free filename."""
    base, ext = os.path.splitext(desired_name)
    counter = 1
    candidate = desired_name
    while os.path.exists(os.path.join(target_dir, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate


def resolve_target_folder(filename: str, requested_folder: str = None) -> str:
    """Resolve target subfolder based on user request or smart auto-routing heuristics."""
    valid_folders = set(SUBFOLDERS)
    if requested_folder and requested_folder.lower() in valid_folders:
        return requested_folder.lower()

    fname_lower = filename.lower()
    ext = os.path.splitext(filename)[1].lower()

    if re.search(r'(^screenshot_|screencast|screen_shot)', fname_lower):
        return 'screenshots'
    if re.search(r'(^pxl_|camera)', fname_lower):
        return 'photos'
    if ext in {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}:
        return 'audio'
    if ext in {'.mp4', '.mov', '.webm', '.mkv', '.avi'}:
        return 'video'
    if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}:
        return 'documents'
    if ext in {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'} or fname_lower.endswith('.tar.gz'):
        return 'archives'
    if ext in IMAGE_EXTENSIONS:
        return 'photos'
    return 'documents'


def optimize_image(input_stream, output_path: str, filename: str, thumb_path: str = None) -> dict:
    """Downsample and compress image with EXIF transpose."""
    raw_data = input_stream.read()
    orig_size = len(raw_data)
    ext = os.path.splitext(filename)[1].lower()

    try:
        img = Image.open(io.BytesIO(raw_data))
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            logger.warning(f"EXIF transpose skipped: {e}")

        orig_w, orig_h = img.size
        if max(orig_w, orig_h) > DOWNSIZE_MAX_DIM:
            img.thumbnail((DOWNSIZE_MAX_DIM, DOWNSIZE_MAX_DIM), Image.Resampling.LANCZOS)

        new_w, new_h = img.size

        if ext in {'.jpg', '.jpeg', '.dng', '.raw', '.heic', '.tif', '.tiff', '.cr2', '.nef', '.arw', '.bmp'} or (ext == '.png' and img.mode in {'RGB', 'L'}):
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (15, 23, 42))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.save(output_path, 'JPEG', quality=DOWNSIZE_QUALITY, optimize=True)
        elif ext == '.webp':
            img.save(output_path, 'WEBP', quality=DOWNSIZE_QUALITY, method=6)
        elif ext == '.png':
            img.save(output_path, 'PNG', optimize=True)
        else:
            with open(output_path, 'wb') as f:
                f.write(raw_data)

        final_size = os.path.getsize(output_path)
        reduction_pct = max(0, round((1.0 - (final_size / max(orig_size, 1))) * 100, 1))

        try:
            if not thumb_path:
                rel = os.path.relpath(output_path, PILOT_DROPS_DIR)
                thumb_path = os.path.join(THUMBNAILS_DIR, rel)
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            thumb_img = img.copy()
            thumb_img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            thumb_img.convert('RGB').save(thumb_path, 'JPEG', quality=75)
        except Exception as te:
            logger.warning(f"Thumbnail generation error: {te}")

        return {
            "optimized": True,
            "orig_size": orig_size,
            "orig_size_formatted": format_bytes(orig_size),
            "final_size": final_size,
            "final_size_formatted": format_bytes(final_size),
            "reduction_pct": reduction_pct,
            "dimensions": f"{new_w}x{new_h}",
            "orig_dimensions": f"{orig_w}x{orig_h}"
        }
    except Exception as e:
        logger.error(f"Image optimization failed, writing raw: {e}")
        with open(output_path, 'wb') as f:
            f.write(raw_data)
        final_size = os.path.getsize(output_path)
        return {
            "optimized": False,
            "orig_size": orig_size,
            "orig_size_formatted": format_bytes(orig_size),
            "final_size": final_size,
            "final_size_formatted": format_bytes(final_size),
            "reduction_pct": 0.0,
            "dimensions": "unknown",
            "orig_dimensions": "unknown"
        }


try:
    from scripts.dead_drop_templates import PASSCODE_GATE_TEMPLATE, DROP_PORTAL_TEMPLATE
except ImportError:
    from dead_drop_templates import PASSCODE_GATE_TEMPLATE, DROP_PORTAL_TEMPLATE

HTML_TEMPLATE = DROP_PORTAL_TEMPLATE

AUDIO_EXTENSIONS = {'.webm', '.m4a', '.mp3', '.wav', '.aac', '.ogg', '.opus', '.flac', '.mp4', '.mov', '.mkv'}


def get_audio_duration(file_path: str) -> Optional[float]:
    """Inspects audio duration in seconds via ffprobe."""
    try:
        cmd = [
            "/usr/bin/ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return round(float(res.stdout.strip()), 2)
    except Exception as e:
        logger.warning(f"Could not probe audio duration for {file_path}: {e}")
    return None


def ensure_atomic_m4a_for_artemis(file_path: str) -> str:
    """
    Convert uploaded/recorded audio or video container into an atomic .m4a file
    via <stem>.tmp.m4a + os.replace so Artemis Faster-Whisper receives clean AAC audio.
    """
    src = Path(file_path)
    if not src.exists():
        return file_path
    if src.suffix.lower() in {".m4a", ".wav", ".mp3"} and src.stat().st_size > 1024:
        return file_path

    target_m4a = src.with_suffix(".m4a")
    tmp_m4a = src.with_suffix(".tmp.m4a")
    if tmp_m4a.exists():
        try:
            tmp_m4a.unlink()
        except OSError:
            pass

    src_dur = get_audio_duration(str(src)) or 0.0
    cmd = [
        "/usr/bin/ffmpeg", "-y",
        "-i", str(src),
        "-vn",
        "-c:a", "aac",
        "-b:a", "128k",
        str(tmp_m4a)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0 and tmp_m4a.exists() and tmp_m4a.stat().st_size > 512:
            tmp_dur = get_audio_duration(str(tmp_m4a)) or 0.0
            if src_dur <= 0 or abs(tmp_dur - src_dur) <= 2.5:
                os.replace(str(tmp_m4a), str(target_m4a))
                return str(target_m4a)
        if tmp_m4a.exists():
            tmp_m4a.unlink()
    except Exception as exc:
        logger.warning(f"Atomic m4a conversion fallback to raw container for {file_path}: {exc}")
        if tmp_m4a.exists():
            try:
                tmp_m4a.unlink()
            except OSError:
                pass
    return file_path


def transcribe_audio_file(file_path: str, user_slug: str = "james") -> str:
    """
    Deterministically transcribes audio 100% via atomic .tmp.m4a + Artemis CUDA Faster-Whisper (100.108.185.53).
    Zero cloud audio file uploads. Saves verbatim transcript into spaces/<user_slug>/transcripts/.
    """
    space = ensure_user_vfs_space(user_slug)
    prepared_audio = ensure_atomic_m4a_for_artemis(file_path)
    base_name = os.path.basename(file_path)
    space_transcript_path = os.path.join(space["transcripts"], f"{base_name}.transcript.txt")

    dispatcher = "/home/james/stacklabs/scripts/transcribe_on_artemis.py"
    if os.path.exists(dispatcher):
        try:
            cmd = [
                "/home/james/stacklabs/.venv/bin/python3",
                dispatcher,
                prepared_audio,
                "--output",
                space_transcript_path,
                "--model",
                "base.en",
                "--compute",
                "int8_float32"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and os.path.exists(space_transcript_path):
                with open(space_transcript_path, "r", encoding="utf-8") as f:
                    transcript = f.read().strip()
                if transcript:
                    logger.info(f"⚡ Transcribed audio via Artemis CUDA ({len(transcript)} chars) -> {space_transcript_path}")
                    return transcript
            fallback_md = prepared_audio.rsplit(".", 1)[0] + "_transcript.md"
            if os.path.exists(fallback_md):
                with open(fallback_md, "r", encoding="utf-8") as f:
                    transcript = f.read().strip()
                if transcript:
                    with open(space_transcript_path, "w", encoding="utf-8") as sf:
                        sf.write(transcript)
                    return transcript
        except Exception as ae:
            logger.error(f"Artemis transcription failed: {ae}")
    return ""


def collide_transcript_with_user_space(transcript_text: str, user_slug: str = "james", title: str = "") -> List[Dict[str, Any]]:
    """
    Collide a sniped transcript against essays/, quant/, and transcripts/ in /home/james/stacklabs/vfs/spaces/<user_slug>/.
    """
    space = ensure_user_vfs_space(user_slug)
    source_tokens = {
        w.lower() for w in re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{3,}\b", f"{title} {transcript_text[:60000]}")
        if w.lower() not in STOPWORDS
    }
    if not source_tokens:
        return []

    candidate_files: List[Tuple[str, str]] = []
    seen_names = set()

    for sub_rel in ("transcripts/essays", "transcripts/quant", "transcripts", "uploads"):
        folder_path = os.path.join(space["root"], sub_rel)
        if os.path.exists(folder_path):
            for entry in sorted(os.scandir(folder_path), key=lambda e: e.name):
                if entry.is_file() and entry.name.lower().endswith((".txt", ".md", ".json", ".csv")):
                    if entry.name in seen_names:
                        continue
                    seen_names.add(entry.name)
                    candidate_files.append((f"/vfs/spaces/{space['slug']}/{sub_rel}/{entry.name}", entry.path))

    if len(candidate_files) < 3:
        global_vfs = Path("/home/james/stacklabs/vfs")
        for g_file in list(global_vfs.glob("*.md")) + list((global_vfs / "concepts").glob("*.md")):
            if g_file.is_file() and g_file.name not in seen_names:
                seen_names.add(g_file.name)
                rel_vfs = "/vfs/" + str(g_file.relative_to(global_vfs))
                candidate_files.append((rel_vfs, str(g_file)))

    collisions: List[Dict[str, Any]] = []
    for vfs_label, fpath in candidate_files:
        try:
            text = Path(fpath).read_text(encoding="utf-8", errors="ignore")[:50000]
            doc_tokens = {
                w.lower() for w in re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{3,}\b", text)
                if w.lower() not in STOPWORDS
            }
            overlap = sorted(source_tokens.intersection(doc_tokens))
            if len(overlap) >= 2:
                score = round(min(0.99, len(overlap) / max(10.0, float(len(doc_tokens)) * 0.25)), 2)
                first_snippet = re.sub(r"\s+", " ", text).strip()[:200]
                collisions.append({
                    "file": os.path.basename(fpath),
                    "vfs_path": vfs_label,
                    "score": score,
                    "overlap_count": len(overlap),
                    "matched_terms": overlap[:8],
                    "excerpt": first_snippet
                })
        except Exception as exc:
            logger.warning(f"Collision scan skipped {fpath}: {exc}")

    collisions.sort(key=lambda x: (x["overlap_count"], x["score"]), reverse=True)
    return collisions[:6]


def synthesize_snipe_audio_brief(
    video_id: str,
    title: str,
    bullets: List[Dict[str, Any]],
    collisions: List[Dict[str, Any]],
    output_mp3_path: str
) -> Optional[str]:
    """
    Synthesize a ~40-second spoken audio response card via GCP Text-to-Speech (Chirp3-HD) + ffmpeg broadcast mastering.
    """
    os.makedirs(os.path.dirname(output_mp3_path), exist_ok=True)
    load_dotenv("/home/james/stacklabs/.env")

    script_parts = [f"Workspace collision brief for {title}."]
    for idx, b in enumerate(bullets[:3], 1):
        headline = re.sub(r"[*_`#]+", "", str(b.get("headline") or "")).strip()
        quote = re.sub(r"[*_`#]+", "", str(b.get("verbatimQuote") or "")).strip()
        if len(quote) > 130:
            quote = quote[:127].rsplit(" ", 1)[0] + "."
        script_parts.append(f"Point {idx}, at {b.get('timestamp', '00:00')}: {headline}. {quote}")

    if collisions:
        top_col = collisions[0]
        terms_str = ", ".join(top_col.get("matched_terms", [])[:4])
        script_parts.append(
            f"Primary essay collision detected in {top_col.get('file')} matching {terms_str}."
        )

    spoken_text = " ".join(script_parts)
    tmp_wav = output_mp3_path + ".tmp.wav"
    tmp_mp3 = output_mp3_path + ".tmp.mp3"

    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=spoken_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Charon"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.03
        )
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        with open(tmp_wav, "wb") as wf:
            wf.write(response.audio_content)

        cmd = [
            "/usr/bin/ffmpeg", "-y",
            "-i", tmp_wav,
            "-af", "highpass=f=110,lowpass=f=7800,acompressor=threshold=-16dB:ratio=3:attack=5:release=60,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-codec:a", "libmp3lame",
            "-b:a", "128k",
            tmp_mp3
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)
        if res.returncode == 0 and os.path.exists(tmp_mp3) and os.path.getsize(tmp_mp3) > 1024:
            os.replace(tmp_mp3, output_mp3_path)
            logger.info(f"⚡ Synthesized 40s VFS Snipe Audio Brief -> {output_mp3_path}")
            return output_mp3_path
    except Exception as exc:
        logger.warning(f"Chirp3-HD synthesis fallback check for {video_id}: {exc}")
        for p in (tmp_wav, tmp_mp3):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    existing_rant = f"/home/james/stacklabs/data/snipes/{video_id}/advocate_rant.mp3"
    if os.path.exists(existing_rant):
        link_or_copy_file(existing_rant, output_mp3_path)
        return output_mp3_path
    return None


def execute_user_space_snipe(url: str, raw_sender: str = "james") -> Dict[str, Any]:
    """
    Snipe a YouTube/media URL into /home/james/stacklabs/vfs/spaces/<user_slug>/snipes/<video_id>/,
    collide against spaces/<user_slug>/transcripts/{essays,quant}/, write summary_intel_brief.md, and synthesize advocate_rant.mp3.
    """
    from scripts.snipe_stream_dossier import (
        extract_video_id,
        process_stream,
        SNIPES_DIR,
    )

    space = ensure_user_vfs_space(raw_sender)
    user_slug = space["slug"]
    clean_url = (url or "").strip()
    if not clean_url:
        raise ValueError("URL is required")

    video_id = extract_video_id(clean_url)

    # Fast-path if pre-computed symbiote dossier already exists in user's space
    user_snipe_dir = os.path.join(space["snipes"], video_id)
    precomputed_json = os.path.join(user_snipe_dir, "dossier.json")
    precomputed_mp3 = os.path.join(user_snipe_dir, "advocate_rant.mp3")
    if os.path.exists(precomputed_json) and os.path.exists(precomputed_mp3):
        try:
            cached_dossier = json.loads(Path(precomputed_json).read_text(encoding="utf-8"))
            if cached_dossier.get("bullets") and cached_dossier.get("collisions"):
                return cached_dossier
        except Exception:
            pass

    master_dossier_dir = SNIPES_DIR / video_id
    master_json_path = SNIPES_DIR / f"{video_id}.json"

    if not (master_dossier_dir.exists() and (master_dossier_dir / "transcript_aligned.md").exists() and master_json_path.exists()):
        master_dossier_dir = process_stream(clean_url)

    meta = {}
    meta_file = master_dossier_dir / "metadata.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

    intel_data = {}
    if master_json_path.exists():
        intel_data = json.loads(master_json_path.read_text(encoding="utf-8"))

    aligned_path = master_dossier_dir / "transcript_aligned.md"
    aligned_transcript = aligned_path.read_text(encoding="utf-8", errors="ignore") if aligned_path.exists() else ""

    user_transcript_copy = os.path.join(space["transcripts"], f"{video_id}_transcript.md")
    with open(user_transcript_copy, "w", encoding="utf-8") as tf:
        tf.write(aligned_transcript)

    title = meta.get("title") or intel_data.get("title") or f"Stream Dossier {video_id}"
    collisions = collide_transcript_with_user_space(aligned_transcript, user_slug=user_slug, title=title)

    os.makedirs(user_snipe_dir, exist_ok=True)

    bullets = intel_data.get("bullets") or []
    summary_md = f"# Personal VFS Dossier: {title}\n\n"
    summary_md += f"- **Workspace:** `/vfs/spaces/{user_slug}`\n"
    summary_md += f"- **Channel:** {meta.get('channel') or intel_data.get('channel') or 'Broadcast'}\n"
    summary_md += f"- **Duration:** {meta.get('duration') or intel_data.get('duration') or 'Live'}\n"
    summary_md += f"- **Source URL:** {clean_url}\n\n"
    summary_md += "## 3-Bullet Executive Brief\n\n"
    for b in bullets:
        summary_md += f"### [{b.get('timestamp', '00:00')}] {b.get('headline', '')} `{b.get('tag', 'INTEL')}`\n"
        if b.get("verbatimQuote"):
            summary_md += f"> *\"{b.get('verbatimQuote')}\"*\n\n"

    summary_md += "## Cross-Domain Essay & Quant Collisions\n\n"
    if collisions:
        for col in collisions:
            terms_str = ", ".join(col.get("matched_terms", []))
            summary_md += f"- **{col['file']}** (`{col['vfs_path']}`) — Score `{col['score']}` ({col['overlap_count']} shared terms: `{terms_str}`)\n"
    else:
        summary_md += "- Zero prior document collisions in workspace.\n"

    summary_md_path = os.path.join(user_snipe_dir, "summary_intel_brief.md")
    with open(summary_md_path, "w", encoding="utf-8") as sf:
        sf.write(summary_md)

    user_rant_mp3 = os.path.join(user_snipe_dir, "advocate_rant.mp3")
    master_rant_mp3 = str(master_dossier_dir / "advocate_rant.mp3")
    if os.path.exists(master_rant_mp3) and os.path.getsize(master_rant_mp3) > 5000:
        link_or_copy_file(master_rant_mp3, user_rant_mp3)
    else:
        synthesize_snipe_audio_brief(video_id, title, bullets, collisions, user_rant_mp3)
        if os.path.exists(user_rant_mp3):
            link_or_copy_file(user_rant_mp3, master_rant_mp3)

    user_audio_mirror = os.path.join(space["audio"], f"{video_id}_brief.mp3")
    if os.path.exists(user_rant_mp3):
        link_or_copy_file(user_rant_mp3, user_audio_mirror)

    audio_url = f"/drops/spaces/{user_slug}/snipes/{video_id}/advocate_rant.mp3" if os.path.exists(user_rant_mp3) else None
    duration_sec = get_audio_duration(user_rant_mp3) if os.path.exists(user_rant_mp3) else None

    dossier_record = {
        "status": "success",
        "user_slug": user_slug,
        "workspace": f"/vfs/spaces/{user_slug}",
        "video_id": video_id,
        "url": clean_url,
        "title": title,
        "channel": meta.get("channel") or intel_data.get("channel") or "Broadcast",
        "duration": meta.get("duration") or intel_data.get("duration") or "Live",
        "bullets": bullets,
        "collisions": collisions,
        "summary_markdown": summary_md,
        "audio_url": audio_url,
        "audio_duration_seconds": duration_sec,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    with open(os.path.join(user_snipe_dir, "dossier.json"), "w", encoding="utf-8") as df:
        json.dump(dossier_record, df, indent=2)

    return dossier_record


def inspect_user_vfs_space(raw_sender: str = "james") -> Dict[str, Any]:
    """List essays, quant specs, investigations, uploads, transcripts, snipes, and audio inside /home/james/stacklabs/vfs/spaces/<user_slug>/."""
    space = ensure_user_vfs_space(raw_sender)
    slug = space["slug"]

    def _scan_dir(abs_dir: str, rel_prefix: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if not os.path.exists(abs_dir):
            return items
        for entry in sorted(os.scandir(abs_dir), key=lambda e: e.name):
            if entry.is_file() and not entry.name.startswith(".") and not entry.name.endswith(".meta.json"):
                st = entry.stat()
                content_text = ""
                preview = ""
                if entry.name.endswith((".txt", ".md")):
                    try:
                        content_text = Path(entry.path).read_text(encoding="utf-8", errors="ignore").strip()
                        preview = re.sub(r"\s+", " ", content_text)[:220]
                    except Exception:
                        preview = ""
                items.append({
                    "name": entry.name,
                    "size_bytes": st.st_size,
                    "size_formatted": format_bytes(st.st_size),
                    "mtime": st.st_mtime,
                    "vfs_path": f"/vfs/spaces/{slug}/{rel_prefix}/{entry.name}",
                    "url": f"/drops/spaces/{slug}/{rel_prefix}/{entry.name}",
                    "preview": preview,
                    "content": content_text[:16000]
                })
        return items

    essays_list = _scan_dir(os.path.join(space["transcripts"], "essays"), "transcripts/essays")
    quant_list = _scan_dir(os.path.join(space["transcripts"], "quant"), "transcripts/quant")
    uploads_list = _scan_dir(space["uploads"], "uploads")
    transcripts_list = _scan_dir(space["transcripts"], "transcripts")
    audio_list = _scan_dir(space["audio"], "audio")
    predictions_list = _scan_dir(space["predictions"], "predictions")
    for _p_item in predictions_list:
        _first = (_p_item.get("content") or "").splitlines()
        _p_item["title"] = _first[0].lstrip("# ").strip() if _first else _p_item["name"]
        _p_item["sha256"] = hashlib.sha256((_p_item.get("content") or "").encode("utf-8")).hexdigest()

    investigations_list: List[Dict[str, Any]] = []
    inv_root = space["investigations"]
    if os.path.exists(inv_root):
        master_md = os.path.join(inv_root, "00_MASTER_SYNTHESIS_REPORT.md")
        master_mp3 = os.path.join(inv_root, "00_MASTER_SYNTHESIS_BRIEF.mp3")
        if os.path.exists(master_md):
            st = os.stat(master_md)
            raw_bytes = Path(master_md).read_bytes()
            content_text = raw_bytes.decode("utf-8", errors="ignore").strip()
            first_line = content_text.splitlines()[0].lstrip("# ").strip() if content_text else "00_MASTER_SYNTHESIS_REPORT.md"
            investigations_list.append({
                "key": "00_MASTER_SYNTHESIS_REPORT.md",
                "name": "00_MASTER_SYNTHESIS_REPORT.md",
                "title": first_line,
                "size_bytes": st.st_size,
                "size_formatted": format_bytes(st.st_size),
                "mtime": st.st_mtime,
                "vfs_path": f"/vfs/spaces/{slug}/investigations/00_MASTER_SYNTHESIS_REPORT.md",
                "url": f"/drops/spaces/{slug}/investigations/00_MASTER_SYNTHESIS_REPORT.md",
                "audio_url": f"/drops/spaces/{slug}/investigations/00_MASTER_SYNTHESIS_BRIEF.mp3" if os.path.exists(master_mp3) else None,
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "preview": re.sub(r"\s+", " ", content_text)[:220],
                "content": content_text[:24000],
            })
        for entry in sorted(os.scandir(inv_root), key=lambda e: e.name):
            if entry.is_dir() and not entry.name.startswith("."):
                rep_md = os.path.join(entry.path, "report.md")
                brief_mp3 = os.path.join(entry.path, "brief.mp3")
                dossier_json = os.path.join(entry.path, "dossier.json")
                if os.path.exists(rep_md):
                    st = os.stat(rep_md)
                    raw_bytes = Path(rep_md).read_bytes()
                    content_text = raw_bytes.decode("utf-8", errors="ignore").strip()
                    title = entry.name
                    if os.path.exists(dossier_json):
                        try:
                            d_obj = json.loads(Path(dossier_json).read_text(encoding="utf-8"))
                            title = d_obj.get("title") or title
                        except Exception:
                            pass
                    elif content_text:
                        title = content_text.splitlines()[0].lstrip("# ").strip()
                    investigations_list.append({
                        "key": entry.name,
                        "name": f"{entry.name}/report.md",
                        "title": title,
                        "size_bytes": st.st_size,
                        "size_formatted": format_bytes(st.st_size),
                        "mtime": st.st_mtime,
                        "vfs_path": f"/vfs/spaces/{slug}/investigations/{entry.name}/report.md",
                        "url": f"/drops/spaces/{slug}/investigations/{entry.name}/report.md",
                        "audio_url": f"/drops/spaces/{slug}/investigations/{entry.name}/brief.mp3" if os.path.exists(brief_mp3) else None,
                        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        "preview": re.sub(r"\s+", " ", content_text)[:220],
                        "content": content_text[:24000],
                    })
    investigations_list.sort(key=lambda x: x["key"])

    snipes_list: List[Dict[str, Any]] = []
    snipes_root = space["snipes"]
    if os.path.exists(snipes_root):
        for entry in os.scandir(snipes_root):
            if entry.is_dir() and not entry.name.startswith("."):
                d_json = os.path.join(entry.path, "dossier.json")
                rant_mp3 = os.path.join(entry.path, "advocate_rant.mp3")
                summary_md_file = os.path.join(entry.path, "summary_intel_brief.md")
                st = entry.stat()
                if os.path.exists(d_json):
                    try:
                        d_data = json.loads(Path(d_json).read_text(encoding="utf-8"))
                        raw_bullets = d_data.get("bullets") or []
                        if not raw_bullets and d_data.get("summary_bullets"):
                            raw_bullets = [
                                {
                                    "timestamp": f"POINT 0{idx + 1}",
                                    "headline": b_text,
                                    "tag": "SYNTHESIS",
                                }
                                for idx, b_text in enumerate(d_data.get("summary_bullets", []))
                            ]
                        raw_cols = d_data.get("collisions") or []
                        norm_cols = []
                        for c in raw_cols:
                            if "file" in c:
                                norm_cols.append(c)
                            else:
                                norm_cols.append({
                                    "file": c.get("essay_target") or c.get("timestamp") or "Cross-Domain Bridge",
                                    "vfs_path": c.get("timestamp") or "",
                                    "score": "LOCKED",
                                    "overlap_count": 1,
                                    "matched_terms": [c.get("bridge", "")] if c.get("bridge") else [],
                                    "excerpt": c.get("synthesis") or c.get("bridge") or "",
                                })
                        summary_md = d_data.get("summary_markdown") or ""
                        if not summary_md and os.path.exists(summary_md_file):
                            summary_md = Path(summary_md_file).read_text(encoding="utf-8", errors="ignore")
                        dur_sec = d_data.get("audio_duration_seconds") or d_data.get("duration_sec") or 42.0
                        snipes_list.append({
                            "video_id": entry.name,
                            "title": d_data.get("title", entry.name),
                            "channel": d_data.get("channel") or "Swanson Bisociation & Diamond Synthesis",
                            "duration": d_data.get("duration") or f"{int(round(float(dur_sec)))}s",
                            "url": d_data.get("url", ""),
                            "bullets": raw_bullets,
                            "summary_bullets": d_data.get("summary_bullets", []),
                            "collisions": norm_cols,
                            "summary_markdown": summary_md,
                            "vfs_path": f"/vfs/spaces/{slug}/snipes/{entry.name}",
                            "audio_url": f"/drops/spaces/{slug}/snipes/{entry.name}/advocate_rant.mp3" if os.path.exists(rant_mp3) else None,
                            "audio_duration_seconds": dur_sec,
                            "mtime": st.st_mtime
                        })
                    except Exception:
                        pass

    def _snipe_sort_key(item: Dict[str, Any]) -> Tuple[int, str]:
        vid = item.get("video_id", "")
        if vid == "00_master_diamond_synthesis":
            return (0, vid)
        if re.match(r"^0[1-5]_", vid):
            return (1, vid)
        return (2, vid)

    snipes_list.sort(key=_snipe_sort_key)

    return {
        "status": "success",
        "user_slug": slug,
        "workspace": f"/vfs/spaces/{slug}",
        "companion_domain": "bothendsofthecurve.com",
        "counts": {
            "essays": len(essays_list),
            "quant": len(quant_list),
            "investigations": len(investigations_list),
            "predictions": len(predictions_list),
            "uploads": len(uploads_list),
            "transcripts": len(transcripts_list),
            "snipes": len(snipes_list),
            "audio": len(audio_list)
        },
        "essays": essays_list,
        "quant": quant_list,
        "investigations": investigations_list,
        "predictions": predictions_list,
        "uploads": uploads_list,
        "transcripts": transcripts_list,
        "snipes": snipes_list,
        "audio": audio_list
    }


resolve_user_space = ensure_user_vfs_space
get_user_space_inventory = inspect_user_vfs_space
