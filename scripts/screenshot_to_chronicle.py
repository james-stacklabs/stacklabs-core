#!/usr/bin/env python3
"""
Sovereign Chronicle Watcher (Tool #56) - Autonomous Screenshot-to-Chronicle Vision Daemon
Path: /home/james/stacklabs/scripts/screenshot_to_chronicle.py (symlinked at /home/james/scripts/screenshot_to_chronicle.py)
System Specification: SL-SPEC-2026-CHRONICLE-VISION-001 / Tool #56
Node: Clio (Forge Master / clio.stacklabs.internal)

Mandate:
Monitors /home/james/stacklabs/pilot_drops/screenshots/ for incoming mobile SMS, RCS,
and chat screenshots. Debounces incoming files, uses Gemini Vision with structured JSON
schema to extract message transcripts, timestamps, and strategic significance, atomically
appends canonical markdown entries to the designated counterparty ledger with auto-incremented
sequence tags (fcntl.flock), and archives images into SQLite audit history.

Counterparty Ledgers:
- Pawel Rudnicki / Jeremy Malone -> /home/james/stacklabs/dna/docs/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md
- Jeff U'Ren -> /home/james/stacklabs_inbox/notebook_sync/11_JeffUren_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEFF_UREN.md
- General / Other -> /home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md
"""

import sys
import os
import re
import time
import json
import base64
import sqlite3
import shutil
import hashlib
import logging
import fcntl
import argparse
from pathlib import Path
from datetime import datetime, timezone
import zoneinfo
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# PATH DEFINITIONS & CANONICAL TARGETS
# ---------------------------------------------------------------------------
BASE_DIR = Path(os.environ.get("SOVEREIGN_ROOT", "/home/james/stacklabs"))
INBOX_DIR = BASE_DIR / "pilot_drops" / "screenshots"
PROCESSED_DIR = INBOX_DIR / "processed"
FAILED_DIR = INBOX_DIR / "failed"
AUDIT_DB_PATH = INBOX_DIR / "chronicle_audit.db"

LEDGER_PAWEL_JEREMY = Path("/home/james/stacklabs/config/governance/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md")
if not LEDGER_PAWEL_JEREMY.exists():
    LEDGER_PAWEL_JEREMY = Path("/home/james/SovereignOS/dna/docs/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md")
LEDGER_JEFF_UREN = Path("/home/james/stacklabs_inbox/notebook_sync/11_JeffUren_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEFF_UREN.md")
LEDGER_WEEKLY_CHRONICLE = Path("/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md")

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DEBOUNCE_STABLE_SECONDS = 1.5
DEBOUNCE_CHECK_INTERVAL = 0.5
MAX_DEBOUNCE_WAIT = 25.0

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Tool#56-VisionDaemon] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SovereignChronicleWatcher")


# ---------------------------------------------------------------------------
# ENVIRONMENT & CREDENTIAL RESOLUTION
# ---------------------------------------------------------------------------
def resolve_gemini_credentials():
    """Resolve API key and active model with fallback support."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # If missing, try loading from sovereign configuration files
    candidate_env_files = [
        Path("/home/james/.config/sovereign/gemini.env"),
        BASE_DIR / ".config" / "sovereign" / "gemini.env",
        BASE_DIR / "SovereignOS" / ".env",
        BASE_DIR / ".env",
    ]

    for env_path in candidate_env_files:
        if not api_key and env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            except Exception as e:
                logger.warning(f"Could not read {env_path}: {e}")

    model = os.environ.get("GEMINI_MODEL", "").strip()
    if not model or model == "gemini-2.0-flash":
        # gemini-2.0-flash was sunsetted by Google API; gemini-3.8-flash is the active canonical model
        model = "gemini-3.8-flash"

    return api_key, model


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# SQLITE AUDIT DATABASE
# ---------------------------------------------------------------------------
def init_audit_db():
    """Initialize SQLite audit history database with WAL mode."""
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(AUDIT_DB_PATH, timeout=10.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chronicle_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                archived_path TEXT,
                file_sha256 TEXT NOT NULL,
                counterparty_name TEXT,
                sequence_tag TEXT,
                target_ledger TEXT,
                message_timestamp TEXT,
                raw_json TEXT,
                status TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_sha256 ON chronicle_audit(file_sha256);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_filename ON chronicle_audit(original_filename);")
        conn.commit()


def is_already_audited(file_sha256: str) -> bool:
    """Check if file hash has already been successfully processed."""
    try:
        with sqlite3.connect(AUDIT_DB_PATH, timeout=5.0) as conn:
            cursor = conn.execute(
                "SELECT id FROM chronicle_audit WHERE file_sha256 = ? AND status IN ('SUCCESS', 'HISTORICAL_BASELINE') LIMIT 1",
                (file_sha256,)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.warning(f"Error querying audit DB: {e}")
        return False


def record_audit(original_name: str, archived_path: Path, sha256: str, counterparty: str,
                 tag: str, ledger: Path, msg_time: str, raw_json: dict, status: str):
    """Insert record into chronicle_audit."""
    try:
        with sqlite3.connect(AUDIT_DB_PATH, timeout=10.0) as conn:
            conn.execute("""
                INSERT INTO chronicle_audit (
                    original_filename, archived_path, file_sha256, counterparty_name,
                    sequence_tag, target_ledger, message_timestamp, raw_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                original_name, str(archived_path) if archived_path else None, sha256,
                counterparty, tag, str(ledger) if ledger else None,
                msg_time, json.dumps(raw_json) if raw_json else None, status
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to record audit row for {original_name}: {e}")


# ---------------------------------------------------------------------------
# GEMINI VISION INFERENCE
# ---------------------------------------------------------------------------
def call_gemini_vision(image_path: Path, max_retries: int = 3) -> dict:
    """Extract structured communication log data from screenshot using Gemini API."""
    api_key, primary_model = resolve_gemini_credentials()
    if not api_key:
        raise ValueError("GEMINI_API_KEY could not be resolved from environment or config files.")

    suffix = image_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/png"

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt_text = (
        "You are the sovereign OCR and Communications Telemetry Engine for StackLabs Sovereign OS.\n"
        "Analyze this mobile screenshot of an RCS, SMS, or chat conversation thread.\n\n"
        "CRITICAL RULES & INVARIANTS:\n"
        "1. Identify the primary counterparty from the contact header or message content:\n"
        "   - 'Pawel Rudnicki' (Lead Syndicate Investor)\n"
        "   - 'Jeremy Malone' (Davidson Homes / Sales Director)\n"
        "   - 'Jeff U'Ren' (Insurance Broker / Operator)\n"
        "   - 'Jim Carroll' (Friday Harbor / Real Estate)\n"
        "   - 'General / Other' (Any other thread or diagnostic)\n"
        "2. Pilot (James Carroll) is typically right-aligned bubbles or outbound sender. Counterparty is left-aligned.\n"
        "3. Transcribe verbatim with high fidelity. Do not hallucinate messages not present in the image.\n"
        "4. Determine direction: 'INBOUND', 'OUTBOUND', or 'INBOUND & OUTBOUND'.\n"
        "5. Provide a crisp 4-10 word title, actor list, verbatim transcript, and 2-4 strategic significance bullet points.\n"
        "6. Return strictly valid JSON conforming to schema."
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "counterparty_name": {
                "type": "STRING",
                "description": "Primary counterparty: 'Pawel Rudnicki', 'Jeremy Malone', 'Jeff U\'Ren', 'Jim Carroll', or 'Other'"
            },
            "thread_type": {"type": "STRING", "description": "e.g. Mobile RCS, SMS, Email, Signal"},
            "direction": {"type": "STRING", "description": "INBOUND, OUTBOUND, or INBOUND & OUTBOUND"},
            "normalized_timestamp": {"type": "STRING", "description": "Human readable date and time e.g. September 26, 2026 (17:15 EDT)"},
            "topic_title": {"type": "STRING", "description": "Concise executive title"},
            "actors": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "transcripts": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "speaker": {"type": "STRING"},
                        "time": {"type": "STRING"},
                        "text": {"type": "STRING"}
                    },
                    "required": ["speaker", "text"]
                }
            },
            "strategic_significance": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "status": {"type": "STRING", "description": "Status summary line"}
        },
        "required": [
            "counterparty_name", "thread_type", "direction",
            "topic_title", "transcripts", "strategic_significance", "status"
        ]
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text},
                    {"inlineData": {"mimeType": mime_type, "data": img_b64}}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }

    models_to_try = [primary_model, "gemini-3.8-flash", "gemini-3.8-flash"]
    seen_models = set()
    ordered_models = []
    for m in models_to_try:
        if m and m not in seen_models:
            seen_models.add(m)
            ordered_models.append(m)

    last_error = None
    for model_name in ordered_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req_data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    candidate_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(candidate_text)
                    parsed["_model_used"] = model_name
                    return parsed
            except urllib.error.HTTPError as he:
                error_body = he.read().decode("utf-8", errors="ignore")
                logger.warning(f"HTTPError {he.code} using model {model_name}: {error_body[:200]}")
                last_error = he
                if he.code == 404:
                    # Model not available, break to try next fallback model
                    break
                time.sleep(1.0 * attempt)
            except Exception as e:
                logger.warning(f"Error attempt {attempt}/{max_retries} with {model_name}: {e}")
                last_error = e
                time.sleep(1.0 * attempt)

    raise RuntimeError(f"All Gemini vision model attempts failed: {last_error}")


# ---------------------------------------------------------------------------
# ROUTING & CANONICAL LEDGER SPLICING
# ---------------------------------------------------------------------------
def resolve_routing(counterparty_name: str) -> dict:
    """Resolve target ledger, tag prefix, and section headers."""
    norm = counterparty_name.strip().lower()
    if "pawel" in norm or "rudnicki" in norm:
        return {
            "type": "pawel",
            "ledger_path": LEDGER_PAWEL_JEREMY,
            "tag_prefix": "LOG-PR",
            "section_header": "## 🏛️ SECTION I: PAWEL RUDNICKI",
            "next_section_header": "## 🚜 SECTION II: JEREMY MALONE"
        }
    elif "jeremy" in norm or "malone" in norm or "davidson" in norm:
        return {
            "type": "jeremy",
            "ledger_path": LEDGER_PAWEL_JEREMY,
            "tag_prefix": "LOG-JM",
            "section_header": "## 🚜 SECTION II: JEREMY MALONE",
            "next_section_header": "## 🦞 3. JIM CARROLL"
        }
    elif "jim" in norm and "carroll" in norm:
        return {
            "type": "jim",
            "ledger_path": LEDGER_PAWEL_JEREMY,
            "tag_prefix": "LOG-JC",
            "section_header": "## 🦞 3. JIM CARROLL",
            "next_section_header": None
        }
    elif "jeff" in norm or "uren" in norm or "u'ren" in norm:
        return {
            "type": "jeff",
            "ledger_path": LEDGER_JEFF_UREN,
            "tag_prefix": "LOG-JU",
            "section_header": "### 2. CANONICAL COMMUNICATIONS & PROBE LOG",
            "next_section_header": "### 3. VOICE & DIALOGUE GOVERNANCE GUIDELINES"
        }
    else:
        return {
            "type": "general",
            "ledger_path": LEDGER_WEEKLY_CHRONICLE,
            "tag_prefix": "LOG-GEN",
            "section_header": None,
            "next_section_header": None
        }


def extract_timestamp_from_filename(filename: str) -> str:
    """Parse timestamp from screenshot filename or fallback to current Eastern time."""
    tz_eastern = zoneinfo.ZoneInfo("America/New_York")
    m = re.search(r"Screenshot_(\d{4})(\d{2})(\d{2})[-_](\d{2})(\d{2})(\d{2})", filename)
    if m:
        try:
            dt = datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6)),
                tzinfo=tz_eastern
            )
            return dt.strftime("%B %d, %Y (%H:%M EDT)")
        except Exception:
            pass
    return datetime.now(tz_eastern).strftime("%B %d, %Y (%H:%M EDT)")


def get_next_sequence_tag(ledger_content: str, tag_prefix: str) -> str:
    """Find highest sequence number and return incremented tag."""
    pattern = rf"\[{re.escape(tag_prefix)}-(\d+)\]"
    matches = re.findall(pattern, ledger_content)
    if not matches:
        return f"[{tag_prefix}-001]"
    highest = max(int(m) for m in matches)
    return f"[{tag_prefix}-{highest + 1:03d}]"


def format_markdown_entry(route: dict, tag: str, filename: str, data: dict) -> str:
    """Format markdown entry conforming to repository conventions."""
    route_type = route["type"]
    time_str = data.get("normalized_timestamp") or extract_timestamp_from_filename(filename)
    title = data.get("topic_title", "Mobile Transmission Sync").strip()
    direction = data.get("direction", "INBOUND & OUTBOUND").strip()
    channel = data.get("thread_type", "Mobile RCS").strip()
    actors = data.get("actors", [])
    transcripts = data.get("transcripts", [])
    strategic = data.get("strategic_significance", [])
    status = data.get("status", "🟢 INBOUND RECEIVED & LOGGED.").strip()

    if route_type == "jeff":
        # Table row for Jeff U'Ren operator dossier
        tz_eastern = zoneinfo.ZoneInfo("America/New_York")
        table_date = datetime.now(tz_eastern).strftime("%Y-%m-%d %H:%M EDT")
        summary_snippets = []
        for t in transcripts:
            spk = t.get("speaker", "Unknown")
            txt = t.get("text", "").replace("\n", " ").strip()
            summary_snippets.append(f'*{spk}:* "{txt}"')
        summary_str = "; ".join(summary_snippets) if summary_snippets else title
        clean_summary = summary_str[:250].replace("|", "/")
        return f"| `{tag}` | {table_date} | {channel} | {direction} | **{title}:** {clean_summary} |"

    # Full structured section for Pawel, Jeremy, Jim, or General
    lines = [
        f"### {tag} {time_str} — {title}",
        f"* **Direction:** {direction} ({channel})"
    ]

    if actors:
        lines.append(f"* **Actors:** {', '.join(actors)}")
    lines.append(f"* **Evidence:** `{filename}`")

    if transcripts:
        lines.append("* **Verbatim Transcript:**")
        for t in transcripts:
            spk = t.get("speaker", "Speaker")
            t_time = f" ({t['time']})" if t.get("time") else ""
            txt = t.get("text", "").strip()
            lines.append(f"  > **{spk}{t_time}:** *\"{txt}\"*  ")

    if strategic:
        lines.append("* **Strategic Significance & Governance Analysis:**")
        for idx, item in enumerate(strategic, start=1):
            lines.append(f"  {idx}. {item}")

    lines.append(f"* **Status:** {status}")
    lines.append("")  # Blank trailing line
    return "\n".join(lines)


def append_to_ledger_atomic(route: dict, filename: str, data: dict) -> tuple:
    """Atomically splice entry into canonical ledger using fcntl.flock(LOCK_EX)."""
    ledger_path = route["ledger_path"]
    tag_prefix = route["tag_prefix"]
    route_type = route["type"]

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not ledger_path.exists():
        ledger_path.write_text(f"# CANONICAL COMMUNICATIONS LOG\n\n", encoding="utf-8")

    with open(ledger_path, "r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            content = f.read()
            seq_tag = get_next_sequence_tag(content, tag_prefix)
            entry_md = format_markdown_entry(route, seq_tag, filename, data)

            if route_type == "jeff":
                # Splice into table before next section
                next_marker = route["next_section_header"]
                if next_marker and next_marker in content:
                    idx = content.find(next_marker)
                    prefix = content[:idx].rstrip()
                    # ensure preceding dashes/spacing
                    if prefix.endswith("---"):
                        prefix = prefix[:-3].rstrip()
                    new_content = prefix + "\n" + entry_md + "\n\n---\n\n" + content[idx:]
                else:
                    new_content = content.rstrip() + "\n" + entry_md + "\n"

            elif route_type in ["pawel", "jeremy"]:
                next_marker = route["next_section_header"]
                if next_marker and next_marker in content:
                    idx = content.find(next_marker)
                    prefix = content[:idx].rstrip()
                    if prefix.endswith("---"):
                        prefix = prefix[:-3].rstrip()
                    new_content = prefix + "\n\n" + entry_md + "\n---\n\n" + content[idx:]
                else:
                    new_content = content.rstrip() + "\n\n" + entry_md + "\n"

            else:
                # General or Jim Carroll: append to appropriate section or bottom
                new_content = content.rstrip() + "\n\n" + entry_md + "\n"

            f.seek(0)
            f.write(new_content)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
            return seq_tag, entry_md
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# SETTLEMENT DEBOUNCE & FILE PROCESSING
# ---------------------------------------------------------------------------
def wait_for_file_settled(file_path: Path) -> bool:
    """Debounce file arrival to ensure complete write before reading."""
    start_time = time.time()
    last_size = -1
    stable_start = None

    while time.time() - start_time < MAX_DEBOUNCE_WAIT:
        if not file_path.exists():
            return False
        try:
            current_size = file_path.stat().st_size
            if current_size == last_size and current_size > 0:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= DEBOUNCE_STABLE_SECONDS:
                    with open(file_path, "rb") as f:
                        f.read(1024)
                    return True
            else:
                last_size = current_size
                stable_start = None
        except (OSError, PermissionError):
            stable_start = None
        time.sleep(DEBOUNCE_CHECK_INTERVAL)

    logger.warning(f"File did not settle within {MAX_DEBOUNCE_WAIT}s: {file_path}")
    return False


def process_screenshot(file_path: Path) -> bool:
    """Process a single screenshot file: OCR, append to ledger, archive."""
    filename = file_path.name
    logger.info(f"Ingesting screenshot: {filename}")

    if not wait_for_file_settled(file_path):
        logger.error(f"Abandoning unsettled file: {filename}")
        return False

    file_sha256 = calculate_sha256(file_path)

    # Check if already processed
    if is_already_audited(file_sha256):
        logger.info(f"File {filename} ({file_sha256[:10]}) already audited. Archiving to processed/.")
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        dest = PROCESSED_DIR / filename
        if dest.exists():
            dest = PROCESSED_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        shutil.move(str(file_path), str(dest))
        return True

    # Check if file name is already referenced in primary ledger
    try:
        if LEDGER_PAWEL_JEREMY.exists():
            current_ledger = LEDGER_PAWEL_JEREMY.read_text(encoding="utf-8")
            if filename in current_ledger:
                logger.info(f"File {filename} already evidenced in {LEDGER_PAWEL_JEREMY.name}. Archiving.")
                PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
                dest = PROCESSED_DIR / filename
                if dest.exists():
                    dest = PROCESSED_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                shutil.move(str(file_path), str(dest))
                record_audit(filename, dest, file_sha256, "ALREADY_LOGGED", "EXISTING",
                             LEDGER_PAWEL_JEREMY, "", {}, "SUCCESS")
                return True
    except Exception as e:
        logger.warning(f"Ledger pre-check anomaly: {e}")

    try:
        # Call Gemini Vision API
        data = call_gemini_vision(file_path)
        counterparty = data.get("counterparty_name", "General / Other")
        msg_time = data.get("normalized_timestamp") or extract_timestamp_from_filename(filename)
        model_used = data.get("_model_used", "unknown")

        # Resolve ledger destination
        route = resolve_routing(counterparty)

        # Atomically append to ledger
        seq_tag, entry_md = append_to_ledger_atomic(route, filename, data)
        logger.info(f"Successfully chiseled {seq_tag} into {route['ledger_path'].name} for {counterparty}")

        # Archive image to processed/
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        dest = PROCESSED_DIR / filename
        if dest.exists():
            timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = PROCESSED_DIR / f"{timestamp_slug}_{filename}"
        shutil.move(str(file_path), str(dest))
        logger.info(f"Moved {filename} -> {dest.name}")

        # Record in SQLite audit history
        record_audit(
            original_name=filename,
            archived_path=dest,
            sha256=file_sha256,
            counterparty=counterparty,
            tag=seq_tag,
            ledger=route["ledger_path"],
            msg_time=msg_time,
            raw_json=data,
            status="SUCCESS"
        )
        return True

    except Exception as e:
        logger.error(f"Processing failed for {filename}: {e}", exc_info=True)
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        failed_dest = FAILED_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        try:
            shutil.move(str(file_path), str(failed_dest))
        except Exception:
            pass

        record_audit(
            original_name=filename,
            archived_path=failed_dest,
            sha256=file_sha256,
            counterparty="UNKNOWN",
            tag="NONE",
            ledger=Path("FAILED"),
            msg_time="",
            raw_json={"error": str(e)},
            status="FAILED"
        )
        return False


# ---------------------------------------------------------------------------
# HISTORICAL SEEDING UTILITY
# ---------------------------------------------------------------------------
def seed_historical_baseline():
    """Audit all current files in INBOX_DIR as baseline to prevent re-processing."""
    init_audit_db()
    files = [f for f in INBOX_DIR.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS]
    logger.info(f"Seeding historical baseline for {len(files)} existing files...")
    count = 0
    for p in files:
        sha = calculate_sha256(p)
        if not is_already_audited(sha):
            record_audit(
                original_name=p.name,
                archived_path=p,
                sha256=sha,
                counterparty="HISTORICAL_BASELINE",
                tag="BASELINE",
                ledger=Path("HISTORICAL"),
                msg_time="",
                raw_json={"note": "Pre-daemon historical baseline"},
                status="HISTORICAL_BASELINE"
            )
            count += 1
    logger.info(f"Seeded {count} files as HISTORICAL_BASELINE in {AUDIT_DB_PATH.name}")


# ---------------------------------------------------------------------------
# WATCHER ENGINE (INOTIFY WITH POLLING FALLBACK)
# ---------------------------------------------------------------------------
def run_watcher(once: bool = False):
    """Run daemon watcher loop."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    init_audit_db()

    logger.info(f"Tool #56 Vision Watcher initialized on: {INBOX_DIR}")

    if once:
        pending = [f for f in sorted(INBOX_DIR.iterdir()) if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS]
        logger.info(f"Running single pass over {len(pending)} files.")
        for p in pending:
            process_screenshot(p)
        return

    # Check for watchdog
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class ScreenshotHandler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory:
                    p = Path(event.src_path)
                    if p.suffix.lower() in VALID_EXTENSIONS and p.parent == INBOX_DIR:
                        process_screenshot(p)

            def on_moved(self, event):
                if not event.is_directory:
                    p = Path(event.dest_path)
                    if p.suffix.lower() in VALID_EXTENSIONS and p.parent == INBOX_DIR:
                        process_screenshot(p)

        observer = Observer()
        observer.schedule(ScreenshotHandler(), path=str(INBOX_DIR), recursive=False)
        observer.start()
        logger.info("Watchdog engine started.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        logger.info("Watchdog library not installed; operating in kernel-stat polling mode.")
        seen_files = set()
        while True:
            try:
                for item in sorted(INBOX_DIR.iterdir()):
                    if item.is_file() and item.suffix.lower() in VALID_EXTENSIONS:
                        if item.name not in seen_files:
                            sha = calculate_sha256(item)
                            if not is_already_audited(sha):
                                process_screenshot(item)
                            seen_files.add(item.name)
                # Cleanup seen set for removed files
                seen_files = {f for f in seen_files if (INBOX_DIR / f).exists()}
            except Exception as e:
                logger.error(f"Polling loop iteration exception: {e}")
            time.sleep(2.0)


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign Chronicle Vision Watcher (Tool #56)")
    parser.add_argument("--once", action="store_true", help="Process pending screenshots and exit")
    parser.add_argument("--file", type=str, help="Process a specific screenshot file")
    parser.add_argument("--seed-baseline", action="store_true", help="Mark all existing screenshots as historical baseline")

    args = parser.parse_args()

    if args.seed_baseline:
        seed_historical_baseline()
    elif args.file:
        init_audit_db()
        target = Path(args.file)
        if target.exists():
            process_screenshot(target)
        else:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        run_watcher(once=args.once)
