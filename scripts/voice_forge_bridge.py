#!/usr/bin/env python3
"""
Tool #68 — The Sovereign Voice-to-Forge JIT Pipeline
Path: /home/james/stacklabs/scripts/voice_forge_bridge.py

Autonomous ingestion daemon that monitors voice drops, call recordings, and problem statements.
Transcribes audio via the Dogfooded Multi-Node protocol:
  - Primary: Artemis CUDA (GTX 1060 6GB GDDR5) via transcribe_on_artemis.py
  - Fallback: NotebookLM/Drive .txt or Cloud Gemini (gemini-3.8-flash)
Synthesizes atomic 4-Quarter Work Orders via gemini-3.8-flash in .venv.
Stages drafts in /home/james/stacklabs/queue/needs_review/WO0010XXX-{SLUG}.md.
Registers JIT approvals in sys_approval_queue via FastAPI Port 8095.
When approved via Unified Cockpit, dead_drop_server moves the ticket to queue/incoming/,
igniting Clio's metal forge.
"""

import os
import sys
import time
import json
import re
import logging
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure SovereignOS root is in Python path for script imports
SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

import dotenv
dotenv.load_dotenv(SOVEREIGN_ROOT / ".env")

from google import genai
from google.genai import types
from scripts.core import api_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [VoiceForgeBridge] %(message)s"
)
logger = logging.getLogger("VoiceForgeBridge")

# Directory Configuration (Canonical StackLabs Paths)
VOICE_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops/voice_drops")
PILOT_DROPS_DIR = Path("/home/james/stacklabs/pilot_drops")
NEEDS_REVIEW_DIR = Path("/home/james/stacklabs/queue/needs_review")
INCOMING_DIR = Path("/home/james/stacklabs/queue/incoming")
STATE_FILE = Path("/home/james/stacklabs/pilot_drops/.voice_forge_processed.json")

# Ensure required directories exist
VOICE_DROPS_DIR.mkdir(parents=True, exist_ok=True)
NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
INCOMING_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".webm", ".ogg", ".aac", ".flac"}
TEXT_EXTENSIONS = {".txt"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS.union(TEXT_EXTENSIONS)

DISPATCHER_SCRIPT = Path("/home/james/stacklabs/scripts/transcribe_on_artemis.py")


def get_audio_duration(file_path: Path) -> float:
    """Check audio duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe duration probe failed for {file_path.name}: {e}")
        return 0.0


def transcribe_audio(file_path: Path) -> str:
    """
    Dogfooded Multi-Node Audio Protocol:
    1. Primary: Dispatch to Artemis CUDA (GTX 1060 6GB GDDR5) via transcribe_on_artemis.py (0% Clio APU load).
    2. Fallback: If Artemis is offline, check paired .txt or use Cloud Gemini (gemini-3.8-flash).
    """
    duration = get_audio_duration(file_path)
    logger.info(f"Probing {file_path.name}: duration is {duration:.2f}s")

    # Tier 1: Local Multi-Node CUDA on Artemis
    if DISPATCHER_SCRIPT.exists():
        logger.info(f"Tier 1: Dispatching {file_path.name} to Artemis CUDA (GTX 1060)...")
        expected_transcript = file_path.parent / f"{file_path.stem}_transcript.md"
        cmd = [
            "/home/james/stacklabs/.venv/bin/python3",
            str(DISPATCHER_SCRIPT),
            str(file_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0 and expected_transcript.exists() and expected_transcript.stat().st_size > 10:
                text = expected_transcript.read_text(encoding="utf-8").strip()
                logger.info(f"Artemis CUDA transcode succeeded ({len(text)} chars)")
                return text
            else:
                logger.warning(f"Artemis dispatcher returned {res.returncode}; falling back to Cloud Gemini")
        except Exception as e:
            logger.warning(f"Artemis dispatch error: {e}; falling back to Cloud Gemini")

    # Tier 2: Cloud Gemini headless transcription fallback
    logger.info(f"Tier 2: Checking paired transcript or Cloud Gemini API for {file_path.name}...")
    candidates = [
        file_path.with_suffix(".txt"),
        file_path.parent / f"{file_path.stem}_TRANSCRIPT.txt",
        file_path.parent / f"{file_path.stem}_TRANSCRIPT.md",
        file_path.parent / f"{file_path.stem}_RAW.txt"
    ]
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 50:
            logger.info(f"Found existing paired transcript at {cand.name}")
            return cand.read_text(encoding="utf-8").strip()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY missing; cannot run Cloud Gemini fallback")
        return ""

    try:
        client = genai.Client(api_key=api_key)
        uploaded = client.files.upload(file=str(file_path))
        prompt = (
            "Provide a clean, full, verbatim transcript of this audio memo. "
            "Preserve exact terminology, numbers, analogies, and institutional concepts. "
            "Format as clean markdown with timestamps if multiple distinct topics occur."
        )
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded, prompt]
        )
        text = response.text.strip()
        logger.info(f"Cloud Gemini transcription completed ({len(text)} chars)")
        return text
    except Exception as e:
        logger.error(f"Cloud Gemini transcription failed: {e}")
        return ""


def synthesize_work_order(transcript: str, source_filename: str) -> Dict[str, Any]:
    """
    Prompt gemini-3.8-flash in .venv to synthesize a strict 4-Quarter Work Order.
    Acquires next canonical ticket ID (WO0010XXX) and slug via api_client.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found for work order synthesis")
    client = genai.Client(api_key=api_key)

    prompt = f"""You are the Sovereign OS Architecture & Work Order Synthesizer.
Given the following spoken voice transcript or problem statement from the Pilot (James Carroll), synthesize an atomic 4-Quarter Work Order for the Sovereign OS metal forge.

Operational Invariants & Reality:
- Host 'clio' is the living room workstation engine and metal forge (owns code edits, migrations, builds, systemd daemons).
- Host 'artemis' is the laptop cockpit (zero code on metal).
- Format must strictly follow the Sovereign OS 4-Quarter Work Order convention.
- If the drop is a test or quick verification recording, treat it as a verification and smoke test of the Voice-to-Forge JIT pipeline.

Source Filename: {source_filename}
Transcript:
\"\"\"{transcript}\"\"\"

Generate a valid JSON object matching this schema:
{{
  "slug": "UPPERCASE-HYPHENATED-SLUG (3 to 6 words, e.g. VERIFY-VOICE-FORGE-JIT-INGRESS)",
  "title": "Concise 1-sentence title describing the core deliverable",
  "objective": "Clear paragraph explaining the objective, architectural context, and root cause",
  "mechanics": "Detailed markdown list of step-by-step implementation mechanics with target files and paths",
  "verification": "Detailed markdown list of terminal commands and verification steps on host clio",
  "acceptance_criteria": ["Array of acceptance criteria strings starting with '[ ] '"]
}}
"""

    logger.info("Prompting gemini-3.8-flash to synthesize 4-Quarter Work Order...")
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    data = json.loads(response.text)
    raw_slug = data.get("slug", "AUTONOMOUS-VOICE-TASK").upper().strip().replace(" ", "-")
    slug = re.sub(r"[^A-Z0-9\-]", "", raw_slug).strip("-")
    if not slug:
        slug = "AUTONOMOUS-VOICE-TASK"

    # Acquire canonical hybrid number via FastAPI
    hybrid_id = api_client.get_next_hybrid_number("WO", slug=slug, increment=True)
    ticket_id = hybrid_id.split("-")[0]
    title = data.get("title", f"Voice Drop Task ({slug})")
    objective = data.get("objective", "").strip()
    mechanics = data.get("mechanics", "").strip()
    verification = data.get("verification", "").strip()
    criteria_list = data.get("acceptance_criteria", [])
    if isinstance(criteria_list, list):
        criteria_md = "\n".join(f"- {c if c.startswith('[') else '[ ] ' + c}" for c in criteria_list)
    else:
        criteria_md = str(criteria_list)

    work_order_md = f"""# 📋 WORK ORDER: {hybrid_id}

## 🏛️ Quarter 1: Objective & Architectural Context
- **Ticket ID**: `{ticket_id}`
- **Tool Codename**: Tool #68 — The Sovereign Voice-to-Forge JIT Pipeline (`scripts/voice_forge_bridge.py`)
- **Parent Epic**: `EPIC-SOVEREIGN-AUTONOMOUS-OPERATIONS`
- **Assigned Worker**: `agy` on Clio (Living Room Workhorse / Autonomous Metal Forge)
- **Priority**: `P1`
- **Source Drop**: `{source_filename}`
- **Objective**:
  {objective}

---

## ⚡ Quarter 2: Implementation Mechanics
{mechanics}

---

## 🛠️ Quarter 3: Verification & Execution Commands
{verification}

---

## ✅ Quarter 4: Acceptance Criteria
{criteria_md}
"""

    return {
        "hybrid_id": hybrid_id,
        "ticket_id": ticket_id,
        "slug": slug,
        "title": title,
        "markdown": work_order_md
    }


def stage_work_order_and_register_approval(synthesis: Dict[str, Any], source_file: Path) -> Path:
    """
    Saves synthesized Work Order to queue/needs_review/ and registers JIT approval card
    in sys_approval_queue via FastAPI Port 8095.
    """
    NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    hybrid_id = synthesis["hybrid_id"]
    staged_path = NEEDS_REVIEW_DIR / f"{hybrid_id}.md"
    staged_path.write_text(synthesis["markdown"], encoding="utf-8")
    logger.info(f"Staged draft Work Order to {staged_path}")

    # Register in sys_approval_queue via api_client (FastAPI Port 8095)
    appr = api_client.create_approval(
        task_id=hybrid_id,
        title=f"Voice Drop JIT Approval: {hybrid_id} — {synthesis['title']}",
        plan_markdown=staged_path.as_posix(),
        state="Requested",
        auth_level="needs_pilot_approval",
        assigned_to="james"
    )
    logger.info(f"Registered JIT approval in sys_approval_queue: sys_id={appr.get('sys_id')}, task_id={hybrid_id}")
    return staged_path


def load_state() -> Dict[str, Any]:
    """Load persistent processed state dictionary."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Could not read state file {STATE_FILE}: {e}")
    return {}


def save_state(state: Dict[str, Any]):
    """Persist processed state dictionary."""
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not save state file {STATE_FILE}: {e}")


def seed_existing_files(state: Dict[str, Any]):
    """
    If running for the first time without prior state, mark old archive files
    (older than 3 hours) as processed so they don't unexpectedly trigger.
    Recent files (such as sample 2026-09-30 18.22.36.m4a) remain unseeded.
    """
    now = time.time()
    cutoff_age_seconds = 3 * 3600  # 3 hours
    for d in [VOICE_DROPS_DIR, PILOT_DROPS_DIR]:
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                # If modified before cutoff and not already in state
                try:
                    mtime = p.stat().st_mtime
                    if (now - mtime) > cutoff_age_seconds:
                        if p.name not in state:
                            state[p.name] = {
                                "path": str(p),
                                "seeded_archived": True,
                                "mtime": mtime
                            }
                except Exception:
                    pass
    save_state(state)


def process_file(file_path: Path, state: Dict[str, Any]) -> Optional[Path]:
    """Process a single voice note, call recording, or text drop."""
    logger.info(f"=== Beginning processing: {file_path.name} ===")

    try:
        size = file_path.stat().st_size
    except Exception:
        size = 0

    if size < 50:
        logger.warning(f"File {file_path.name} is too small ({size} bytes); skipping.")
        state[file_path.name] = {
            "path": str(file_path),
            "processed_at": datetime.now().isoformat(),
            "skipped": True,
            "reason": "file_too_small"
        }
        save_state(state)
        return None

    ext = file_path.suffix.lower()

    if ext in TEXT_EXTENSIONS:
        transcript = file_path.read_text(encoding="utf-8").strip()
    elif ext in AUDIO_EXTENSIONS:
        transcript = transcribe_audio(file_path)
    else:
        logger.warning(f"Unsupported file extension {ext} for {file_path.name}")
        return None

    if not transcript or len(transcript) < 5:
        logger.warning(f"Transcript empty or trivial for {file_path.name}; skipping.")
        state[file_path.name] = {
            "path": str(file_path),
            "processed_at": datetime.now().isoformat(),
            "skipped": True,
            "reason": "empty_or_trivial_transcript"
        }
        save_state(state)
        return None

    logger.info(f"Transcript acquired for {file_path.name} ({len(transcript)} chars). Synthesizing work order...")
    synthesis = synthesize_work_order(transcript, file_path.name)
    staged_path = stage_work_order_and_register_approval(synthesis, file_path)

    state[file_path.name] = {
        "path": str(file_path),
        "processed_at": datetime.now().isoformat(),
        "hybrid_id": synthesis["hybrid_id"],
        "staged_file": str(staged_path)
    }
    save_state(state)
    logger.info(f"=== Successfully processed {file_path.name} -> {staged_path.name} ===")
    return staged_path


def scan_and_process_pending(state: Dict[str, Any]) -> List[Path]:
    """Scan watch directories and process any new or modified files."""
    staged = []
    # Priority order: voice_drops first, then pilot_drops root
    for d in [VOICE_DROPS_DIR, PILOT_DROPS_DIR]:
        if not d.exists():
            continue
        # Sort by creation / modification time ascending
        candidates = sorted(
            [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS],
            key=lambda x: x.stat().st_mtime
        )
        for cand in candidates:
            # Skip hidden files or lock files
            if cand.name.startswith("."):
                continue
            # If not in state, or file was modified after processing
            prev_entry = state.get(cand.name)
            if not prev_entry:
                try:
                    res = process_file(cand, state)
                    if res:
                        staged.append(res)
                except Exception as e:
                    logger.error(f"Error processing {cand.name}: {e}", exc_info=True)
    return staged


def main():
    parser = argparse.ArgumentParser(description="Tool #68: Sovereign Voice-to-Forge JIT Pipeline")
    parser.add_argument("--file", type=str, help="Process a specific file immediately")
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--poll-interval", type=int, default=5, help="Poll interval in seconds (default: 5)")
    args = parser.parse_args()

    NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    seed_existing_files(state)

    if args.file:
        target = Path(args.file)
        if not target.exists():
            logger.error(f"File not found: {target}")
            sys.exit(1)
        res = process_file(target, state)
        if res:
            logger.info(f"Target file processed and staged: {res}")
            sys.exit(0)
        else:
            logger.error("Processing failed.")
            sys.exit(1)

    if args.once:
        logger.info("Running single scan of watch directories...")
        staged = scan_and_process_pending(state)
        logger.info(f"Single scan complete. Staged {len(staged)} work orders.")
        sys.exit(0)

    # Daemon mode (default if no specific file or once flag)
    logger.info(f"Starting Voice-to-Forge daemon (poll interval: {args.poll_interval}s)...")
    logger.info(f"Monitoring: {VOICE_DROPS_DIR} & {PILOT_DROPS_DIR}")
    try:
        while True:
            scan_and_process_pending(state)
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")
    except Exception as e:
        logger.critical(f"Daemon crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
