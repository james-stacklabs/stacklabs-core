"""Shared imports, config and helpers extracted from dead_drop_server.py (generated)."""
from pathlib import Path as _P

TEMPLATE_DIR = _P(__file__).resolve().parent / 'templates'


def load_template(name: str) -> str:
    # newline='' keeps the bytes identical to the old inline string
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
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory, abort, Response, make_response, redirect
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
from dotenv import load_dotenv


load_dotenv("/home/james/SovereignOS/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

logger = logging.getLogger("PilotDropGateway")

PILOT_DROPS_DIR = "/home/james/sovereign_inbox/pilot_drops"

INCOMING_DIR = "/home/james/sovereign_inbox/pilot_drops/incoming"

THUMBNAILS_DIR = "/home/james/sovereign_inbox/pilot_drops/.thumbnails"

SUBFOLDERS = ['incoming', 'screenshots', 'photos', 'audio', 'video', 'documents', 'archives']

os.makedirs(PILOT_DROPS_DIR, exist_ok=True)

os.makedirs(INCOMING_DIR, exist_ok=True)

DEFAULT_DROP_KEYS = {"rudnicki2026", "stacklabs2026"}

AUTH_COOKIE_NAME = "stacklabs_drop_auth"

AUTH_SALT = "stacklabs_enterprise_drop_salt_v1"

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

def is_authorized(req) -> bool:
    # 1. Query parameter ?key=
    q_key = req.args.get('key', '').strip()
    if q_key and q_key in get_valid_access_keys():
        return True
    # 2. Cookie stacklabs_drop_auth
    cookie_val = req.cookies.get(AUTH_COOKIE_NAME, '').strip()
    if cookie_val and (cookie_val in get_all_valid_hashes() or cookie_val in get_valid_access_keys()):
        return True
    return False

os.makedirs(THUMBNAILS_DIR, exist_ok=True)

for sub in SUBFOLDERS:
    os.makedirs(os.path.join(PILOT_DROPS_DIR, sub), exist_ok=True)
    os.makedirs(os.path.join(THUMBNAILS_DIR, sub), exist_ok=True)

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
    """
    Resolve target subfolder based on user request or smart auto-routing heuristics.
    Taxonomy: screenshots, photos, audio, video, documents, archives.
    """
    valid_folders = set(SUBFOLDERS)
    if requested_folder and requested_folder.lower() in valid_folders:
        return requested_folder.lower()

    fname_lower = filename.lower()
    ext = os.path.splitext(filename)[1].lower()

    # 1. Screenshots: matches ^Screenshot_ or screencast or Screen_Shot
    if re.search(r'(^screenshot_|screencast|screen_shot)', fname_lower):
        return 'screenshots'

    # 2. Photos: matches ^PXL_ or camera
    if re.search(r'(^pxl_|camera)', fname_lower):
        return 'photos'

    # 3. Audio: {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}
    if ext in {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.aac'}:
        return 'audio'

    # 4. Video: {'.mp4', '.mov', '.webm', '.mkv', '.avi'}
    if ext in {'.mp4', '.mov', '.webm', '.mkv', '.avi'}:
        return 'video'

    # 5. Documents: {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}
    if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.eml', '.txt', '.csv', '.tsv', '.json', '.md', '.srt', '.vtt', '.html'}:
        return 'documents'

    # 6. Archives: {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'}
    if ext in {'.zip', '.tar', '.gz', '.7z', '.bz2', '.tgz'} or fname_lower.endswith('.tar.gz'):
        return 'archives'

    # Default image fallback: route to photos
    if ext in IMAGE_EXTENSIONS:
        return 'photos'

    # Default fallback
    return 'documents'

def optimize_image(input_stream, output_path: str, filename: str, thumb_path: str = None) -> dict:
    """
    Downsample and compress image:
    - Auto-rotates via EXIF transpose.
    - Caps maximum dimension at DOWNSIZE_MAX_DIM (preserving aspect ratio).
    - Compresses to high-efficiency JPEG/WebP/PNG at quality 85.
    """
    raw_data = input_stream.read()
    orig_size = len(raw_data)
    ext = os.path.splitext(filename)[1].lower()

    try:
        img = Image.open(io.BytesIO(raw_data))
        # Auto-rotate according to EXIF metadata (critical for mobile camera portrait shots)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            logger.warning(f"EXIF transpose skipped: {e}")

        orig_w, orig_h = img.size

        # Downsample if larger than threshold
        if max(orig_w, orig_h) > DOWNSIZE_MAX_DIM:
            img.thumbnail((DOWNSIZE_MAX_DIM, DOWNSIZE_MAX_DIM), Image.Resampling.LANCZOS)
        
        new_w, new_h = img.size

        # Save with optimization
        if ext in {'.jpg', '.jpeg', '.dng', '.raw', '.heic', '.tif', '.tiff', '.cr2', '.nef', '.arw', '.bmp'} or (ext == '.png' and img.mode in {'RGB', 'L'}):
            # Save as optimized JPEG
            if img.mode in ('RGBA', 'LA', 'P'):
                # Handle alpha by pasting on neutral dark or converting
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
            # Fallback direct write
            with open(output_path, 'wb') as f:
                f.write(raw_data)
                
        final_size = os.path.getsize(output_path)
        reduction_pct = max(0, round((1.0 - (final_size / max(orig_size, 1))) * 100, 1))

        # Generate thumbnail for UI
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

AUDIO_EXTENSIONS = {'.webm', '.m4a', '.mp3', '.wav', '.aac', '.ogg', '.opus', '.flac'}

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

def transcribe_audio_file(file_path: str) -> str:
    """
    Deterministically transcribes audio:
    Tier 1: Cloud Gemini 3.8 Flash via google.genai SDK
    Tier 2 Fallback: Local Whisper (base.en) in repository venv
    """
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        load_dotenv("/home/james/SovereignOS/.env")
        key = os.getenv("GEMINI_API_KEY")

    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            uploaded = client.files.upload(file=file_path)
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[
                    uploaded,
                    "Transcribe this audio recording verbatim. Provide only the plain text transcription without any commentary, summaries, or quotation marks."
                ]
            )
            transcript = resp.text.strip()
            if transcript:
                logger.info(f"⚡ Successfully transcribed audio via Gemini 3.8 Flash ({len(transcript)} chars)")
                return transcript
        except Exception as ge:
            logger.error(f"Gemini cloud transcription failed, falling back to local Whisper: {ge}")

    # Fallback to local whisper
    try:
        import whisper
        model = whisper.load_model("base.en")
        w_res = model.transcribe(file_path)
        transcript = w_res.get("text", "").strip()
        logger.info(f"⚡ Successfully transcribed audio via local Whisper ({len(transcript)} chars)")
        return transcript
    except Exception as we:
        logger.error(f"Local Whisper transcription failed: {we}")
        return ""
