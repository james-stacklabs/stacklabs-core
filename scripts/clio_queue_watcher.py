#!/usr/bin/env python3
"""
Sovereign OS: Clio Queue Watcher Daemon
Path: /home/james/stacklabs/scripts/clio_queue_watcher.py

Monitors /home/james/stacklabs/queue/incoming/ for staged tickets
dropped by Artemis or Pegasus, transitions tickets through processing,
invokes clio_agent_exec.sh, and archives to archive/ or failed/.
"""

import os
import shutil
import subprocess
import sys
import time
import threading
import hashlib
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

try:
    from scripts.core.db import get_db
except ImportError:
    get_db = None

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("[ERROR] watchdog library not installed. Install with: pip install watchdog")
    sys.exit(1)

QUEUE_DIR = Path("/home/james/stacklabs/queue")
INCOMING = QUEUE_DIR / "incoming"
PROCESSING = QUEUE_DIR / "processing"
ARCHIVE = QUEUE_DIR / "archive"
FAILED = QUEUE_DIR / "failed"
LOGS = QUEUE_DIR / "logs"
DEFERRED = QUEUE_DIR / "deferred"
REJECTED = QUEUE_DIR / "rejected"

DEFERRED_DIR = DEFERRED
INCOMING_DIR = INCOMING
REJECTED_DIR = REJECTED

EXEC_RUNNER = "/home/james/stacklabs/scripts/clio_agent_exec.sh"

execution_lock = threading.Lock()
archive_hash_cache = {}

def check_deferred_queue():
    if not DEFERRED_DIR.exists():
        DEFERRED_DIR.mkdir(parents=True, exist_ok=True)
    if not REJECTED_DIR.exists():
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)
        
    now = datetime.now(timezone.utc)
    
    for ticket_path in sorted(DEFERRED_DIR.glob("*.md")):
        try:
            content = ticket_path.read_text(encoding="utf-8")
            
            # Check retry depth guardrail (anti-fork bomb)
            depth_match = re.search(r"retry_depth:\s*(\d+)", content)
            if depth_match and int(depth_match.group(1)) > 1:
                print(f"[RECURSION GUARDRAIL] Ejecting {ticket_path.name} to rejected/")
                dest = REJECTED_DIR / ticket_path.name
                if dest.exists() and dest.resolve() != ticket_path.resolve():
                    dest.unlink()
                shutil.move(str(ticket_path), str(dest))
                continue
                
            # Check execute_not_before timestamp
            time_match = re.search(r"execute_not_before:\s*([^\n\r]+)", content)
            if not time_match:
                # If in deferred but no timestamp, promote to incoming
                dest = INCOMING_DIR / ticket_path.name
                if dest.exists() and dest.resolve() != ticket_path.resolve():
                    dest.unlink()
                shutil.move(str(ticket_path), str(dest))
                continue
                
            time_str = time_match.group(1).strip().strip('"').strip("'")
            target_time = datetime.fromisoformat(time_str)
            if target_time.tzinfo is None:
                # Default to local if no tz
                target_time = target_time.astimezone()
                
            if now >= target_time.astimezone(timezone.utc):
                print(f"[TEMPORAL RELEASE] Trigger time reached for {ticket_path.name}. Promoting to incoming/.")
                dest = INCOMING_DIR / ticket_path.name
                if dest.exists() and dest.resolve() != ticket_path.resolve():
                    dest.unlink()
                shutil.move(str(ticket_path), str(dest))
        except Exception as e:
            print(f"[DEFERRED SCAN ERROR] {ticket_path.name}: {e}")

def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""

def get_archived_hashes() -> set:
    """Return set of SHA-256 hashes of all .md files in archive, caching by mtime."""
    global archive_hash_cache
    current_hashes = set()
    if not ARCHIVE.exists():
        return current_hashes

    for f in ARCHIVE.glob("*.md"):
        try:
            mtime = f.stat().st_mtime
            cached = archive_hash_cache.get(f)
            if cached and cached[0] == mtime:
                current_hashes.add(cached[1])
            else:
                h = calculate_sha256(f)
                if h:
                    archive_hash_cache[f] = (mtime, h)
                    current_hashes.add(h)
        except Exception:
            continue
    return current_hashes

def make_clean_slug(filename: str) -> str:
    """Generate a clean, uppercase, hyphenated slug from a filename."""
    stem = Path(filename).stem
    # Strip common work order / ticket prefixes
    cleaned = re.sub(r'^(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO|STRY|INC|DFCT|ENHC|REQ)(?:[\s:_\-]+|$)', '', stem, flags=re.IGNORECASE).strip()
    if not cleaned:
        cleaned = stem
    slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()
    slug = slug[:60].rstrip('-')
    return slug or "PILOT-DROP"

def acquire_next_ticket_number(category: str = "WO", slug: str = "") -> str:
    """
    Acquire the next sequential ticket auto-number from SDLC FastAPI (Port 8095).
    Falls back to direct sys_number query in sovereign_now.db if FastAPI is unreachable.
    """
    cat = (category or "WO").upper().strip()
    params = {"category": cat, "increment": "true"}
    if slug:
        params["slug"] = slug
    query_str = urllib.parse.urlencode(params)
    url = f"http://127.0.0.1:8095/api/tickets/next_number?{query_str}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                cand = data.get("next_number") or data.get("hybrid_id") or ""
                if cand:
                    m = re.match(r'^((?:WO|STRY|INC|DFCT|ENHC|REQ)\d+)', cand, re.IGNORECASE)
                    if m:
                        return m.group(1).upper()
                    return cand.split('-')[0].upper()
    except Exception as e:
        print(f"[WARN] Failed to query FastAPI next_number ({e}). Falling back to local DB...")

    # Fallback to direct DB via get_db()
    if get_db is not None:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT current_number, digits, prefix FROM sys_number WHERE category = ?", (cat,))
                num_row = cursor.fetchone()
                if num_row:
                    curr_val = num_row['current_number']
                    next_val = curr_val + 1
                    digits = num_row['digits'] or 7
                    prefix = num_row['prefix'] or cat
                    auto_number = f"{prefix}{str(next_val).zfill(digits)}"
                    cursor.execute("UPDATE sys_number SET current_number = ?, sys_updated_on = datetime('now') WHERE category = ?", (next_val, cat))
                    conn.commit()
                    return auto_number
                else:
                    cursor.execute("SELECT number FROM sovereign_tickets WHERE number LIKE ? ORDER BY number DESC LIMIT 1", (f"{cat}%",))
                    row = cursor.fetchone()
                    if row:
                        num_part = re.sub(r'[^0-9]', '', str(row['number']))
                        curr_val = int(num_part) if num_part else 10000
                    else:
                        curr_val = 10000
                    next_val = curr_val + 1
                    auto_number = f"{cat}{str(next_val).zfill(7)}"
                    cursor.execute("INSERT INTO sys_number (category, prefix, current_number, digits, sys_created_on, sys_updated_on) VALUES (?, ?, ?, 7, datetime('now'), datetime('now'))", (cat, cat, next_val))
                    conn.commit()
                    return auto_number
        except Exception as db_err:
            print(f"[ERROR] Local DB fallback failed: {db_err}")

    # Ultimate fallback: timestamp
    return f"{cat}{int(time.time())}"

def extract_ticket_id(source: Path) -> str:
    """Extract canonical ticket ID from filename or header lines."""
    # 1. Check filename
    m = re.search(r'\b((?:WO|STRY|INC|DFCT|ENHC|REQ)[-_]?\d+[A-Za-z0-9_-]*)\b', source.name, re.IGNORECASE)
    if m:
        cand = m.group(1)
        sub = re.match(r'^((?:WO|STRY|INC|DFCT|ENHC|REQ)\d+)', cand, re.IGNORECASE)
        if sub:
            return sub.group(1).upper()
        if cand.upper().startswith("WO-"):
            return cand.upper()
        return cand.split('-')[0].upper()

    # 2. Check header lines (first 50 lines)
    try:
        with open(source, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                line_clean = line.replace('*', '').replace('`', '').strip()
                id_match = re.search(r'\b(?:Ticket ID|Ticket|Work Order ID|Task ID|WORK ORDER)\b[\s*:\`]*([A-Za-z0-9\-_]+)', line_clean, re.IGNORECASE)
                if id_match:
                    cand = id_match.group(1).strip()
                    sub = re.match(r'^((?:WO|STRY|INC|DFCT|ENHC|REQ)[-_]?\d+)', cand, re.IGNORECASE)
                    if sub:
                        return sub.group(1).upper().replace('-', '')
                direct_match = re.search(r'\b((?:WO|STRY|INC|DFCT|ENHC|REQ)[-_]?\d+)\b', line_clean, re.IGNORECASE)
                if direct_match:
                    return direct_match.group(1).upper().replace('-', '')
    except Exception:
        pass

    return ""

def is_ticket_resolved(ticket_id: str) -> bool:
    """Check if ticket is resolved (state_int >= 4) via SDLC FastAPI (2-second timeout)."""
    if not ticket_id:
        return False
    url = f"http://127.0.0.1:8095/api/tickets/{ticket_id}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                state_int = data.get("state_int")
                if state_int is not None and state_int >= 4:
                    return True
                status = str(data.get("status", "")).upper()
                if status in ("DONE", "RESOLVED", "CLOSED"):
                    return True
    except Exception:
        pass
    return False

def move_to_archive(source: Path) -> Path:
    """Safely move a file to archive directory, unlinking destination if already present."""
    dest = ARCHIVE / source.name
    if not source.exists():
        return dest
    if dest.exists() and dest.resolve() != source.resolve():
        try:
            dest.unlink()
        except Exception:
            pass
    try:
        shutil.move(str(source), str(dest))
    except Exception as e:
        print(f"[WARN] Failed to move {source.name} to archive: {e}")
    return dest

ATF_VISUAL_TWIN_SCRIPT = Path("/home/james/scripts/atf_visual_twin_audit.py")

def run_atf_visual_twin_gate(target: Path) -> tuple[bool, str]:
    """
    Q4 Verification Gate: Invoke ATF Visual Digital Twin audit if ticket specifies
    visual twin assertions or references contracts in /home/james/contracts/visual_twins/.
    """
    if not ATF_VISUAL_TWIN_SCRIPT.exists() or not target.exists():
        return True, ""

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return True, ""

    # Check if ticket has visual twin directives
    has_twin_directive = any(kw in content.lower() for kw in [
        "visual digital twin", "atf_visual_twin_audit", "visual twin", "visual_twin", "playwright_digital_twin"
    ])
    if not has_twin_directive:
        return True, ""

    print(f"[ATF_GATE] Executing Q4 Playwright Visual Twin Gate for {target.name}...")

    # Extract target URL or static file if specified
    url = None
    m_url = re.search(r'(?:URL|Target URL|Endpoint)[\s*:`]+(https?://[^\s`]+|file://[^\s`]+|/[^\s`]+\.html)', content, re.IGNORECASE)
    if m_url:
        url = m_url.group(1).strip()
    else:
        # Fallback to mock if available
        default_mock = Path("/home/james/contracts/visual_twins/mocks/mock_hero_hud.html")
        if default_mock.exists():
            url = f"file://{default_mock}"
        else:
            url = "file:///home/james/evidence/visual_twins/mock_hero_hud.html"

    # Extract target slug or ticket id
    ticket_id = extract_ticket_id(target) or target.stem
    target_slug = "hero_vector_hud"
    m_target = re.search(r'(?:TARGET|Component|target_slug)[\s*:`]+([A-Za-z0-9_-]+)', content)
    if m_target:
        candidate_slug = m_target.group(1).strip()
        contract_file = Path(f"/home/james/contracts/visual_twins/{candidate_slug}.json")
        if contract_file.exists():
            target_slug = candidate_slug

    cmd = [
        "/home/james/stacklabs/.venv/bin/python3",
        str(ATF_VISUAL_TWIN_SCRIPT),
        "--url", url,
        "--target", target_slug,
        "--ticket", ticket_id
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            print(f"[ATF_GATE] ✅ Visual Twin Gate passed for {target.name}")
            return True, ""
        else:
            err_msg = f"ATF Visual Twin Gate failed with exit code {res.returncode}:\n{res.stdout}\n{res.stderr}"
            return False, err_msg
    except Exception as e:
        return False, f"Failed to execute ATF Visual Twin Gate: {e}"

def process_ticket(source: Path):
    if not source.exists() or not source.name.endswith(".md"):
        return

    with execution_lock:
        if not source.exists() or not source.name.endswith(".md"):
            return

        if (ARCHIVE / source.name).exists() and (ARCHIVE / source.name).resolve() != source.resolve():
            print(f"[DEDUP] Ticket file already present in archive. Skipping: {source.name}")
            try:
                source.unlink()
            except Exception:
                pass
            return

        # 0. Banned/Deprecated Work Order Types (e.g. Mashups)
        if "mashup" in source.name.lower():
            print(f"[REJECT] Banning deprecated mashup file: {source.name} -> archiving")
            try:
                move_to_archive(source)
            except Exception as e:
                print(f"[ERROR] Failed to archive mashup {source.name}: {e}")
            return

        # 1. Content Hash Check
        src_hash = calculate_sha256(source)
        if src_hash and src_hash in get_archived_hashes():
            print(f"[DEDUP] Content hash matches archived file. Auto-archiving: {source.name}")
            try:
                move_to_archive(source)
            except Exception as e:
                print(f"[ERROR] Failed to auto-archive duplicate hash {source.name}: {e}")
            return

        # 2. Auto-Number Detection & Pilot Drop Normalization
        ticket_id = extract_ticket_id(source)
        if not ticket_id:
            clean_slug = make_clean_slug(source.name)
            new_ticket_id = acquire_next_ticket_number(category="WO", slug=clean_slug)
            if new_ticket_id:
                clean_title = clean_slug.replace('-', ' ')
                new_filename = f"{new_ticket_id}-{clean_slug}.md"
                new_path = source.parent / new_filename
                original_name = source.name

                # Prepend official header block if missing
                try:
                    content = source.read_text(encoding='utf-8', errors='ignore')
                    if f"**Ticket ID**: `{new_ticket_id}`" not in content and f"# {new_ticket_id}" not in content:
                        header = (
                            f"# {new_ticket_id}: {clean_title}\n"
                            f"**Ticket ID**: `{new_ticket_id}`  \n"
                            f"**Classification**: Work Order (`WO`)  \n"
                            f"**Auto-Assigned By**: Clio Queue Watcher (Pilot Drop Normalizer)  \n\n"
                            f"---\n\n"
                        )
                        source.write_text(header + content, encoding='utf-8')
                except Exception as e:
                    print(f"[WARN] Failed to inject header into {original_name}: {e}")

                # Rename file in-place to canonical hybrid filename
                try:
                    if new_path != source:
                        if new_path.exists():
                            new_path.unlink()
                        source.rename(new_path)
                        source = new_path
                        print(f"[INGEST] Auto-assigned official ticket ID {new_ticket_id} to Pilot drop: {original_name} -> {new_filename}")
                except Exception as e:
                    print(f"[ERROR] Failed to rename {original_name} to {new_filename}: {e}")

                ticket_id = new_ticket_id

        # 3. Ticket Resolution Check
        if ticket_id and is_ticket_resolved(ticket_id):
            print(f"[DEDUP] Ticket {ticket_id} is already resolved. Auto-archiving: {source.name}")
            try:
                move_to_archive(source)
            except Exception as e:
                print(f"[ERROR] Failed to auto-archive resolved ticket {source.name}: {e}")
            return

        # Archive existence check before ingestion
        if (ARCHIVE / source.name).exists() and (ARCHIVE / source.name).resolve() != source.resolve():
            print(f"[DEDUP] Ticket file already present in archive. Skipping: {source.name}")
            try:
                source.unlink()
            except Exception:
                pass
            return

        # 4. Normal execution
        target = PROCESSING / source.name
        try:
            if target.exists():
                target.unlink()
            shutil.move(str(source), str(target))
            print(f"[INGEST] Moved {source.name} -> {target}")
        except Exception as e:
            print(f"[ERROR] Ingestion move failed for {source.name}: {e}")
            return

        print(f"[EXEC] Running Clio Agent on: {target.name}")
        
        # Execute clio_agent_exec.sh
        cmd = ["bash", EXEC_RUNNER, "--ticket", str(target)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        archive_dest = ARCHIVE / target.name
        failed_dest = FAILED / target.name

        atf_passed = True
        atf_err = ""
        if result.returncode == 0:
            atf_passed, atf_err = run_atf_visual_twin_gate(target)
            if not atf_passed:
                print(f"[ATF_GATE] 🛑 Visual Twin verification failed for {target.name}: {atf_err}")

        if result.returncode == 0 and atf_passed:
            try:
                if target.exists():
                    if archive_dest.exists() and archive_dest.resolve() != target.resolve():
                        archive_dest.unlink()
                    shutil.move(str(target), str(archive_dest))
                    print(f"[SUCCESS] Archived: {target.name}")
                elif archive_dest.exists():
                    print(f"[SUCCESS] Already archived by worker: {target.name}")
                else:
                    print(f"[WARN] Target missing after success: {target.name}")
            except Exception as e:
                print(f"[WARN] Failed to move {target.name} to archive: {e}")
        else:
            try:
                combined_err = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                if not atf_passed and atf_err:
                    combined_err = f"ATF VISUAL TWIN GATE FAILURE:\n{atf_err}\n\n" + combined_err

                # Check if worker already completed and archived ticket before process exit
                if archive_dest.exists() and not target.exists():
                    if failed_dest.exists() and failed_dest.resolve() != archive_dest.resolve():
                        failed_dest.unlink()
                    shutil.move(str(archive_dest), str(failed_dest))
                    error_log = failed_dest.with_suffix(".error.log")
                    error_log.write_text(combined_err)
                    print(f"[FAILURE] Recovered failed ticket {target.name} from archive/ to failed/ (Exit Code {result.returncode})")
                elif target.exists():
                    if failed_dest.exists() and failed_dest.resolve() != target.resolve():
                        failed_dest.unlink()
                    shutil.move(str(target), str(failed_dest))
                    error_log = failed_dest.with_suffix(".error.log")
                    error_log.write_text(combined_err)
                    print(f"[FAILURE] Moved {target.name} to failed (Exit Code {result.returncode})")
                elif failed_dest.exists():
                    print(f"[FAILURE] Already in failed: {target.name}")
                else:
                    print(f"[WARN] Target missing after failure (Exit Code {result.returncode}): {target.name}")
            except Exception as e:
                print(f"[WARN] Failed to move {target.name} to failed: {e}")

class TicketHandler(FileSystemEventHandler):
    def on_closed(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        time.sleep(0.5)  # Grace period for file write sync
        process_ticket(Path(event.src_path))

    def on_created(self, event):
        # Fallback if on_closed isn't triggered by all file copy tools
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        time.sleep(1.0)
        p = Path(event.src_path)
        if p.exists() and p.parent == INCOMING:
            process_ticket(p)

    def on_moved(self, event):
        # Fallback for file moves into incoming
        dest = getattr(event, 'dest_path', '')
        if not dest or not dest.endswith(".md"):
            return
        time.sleep(0.5)
        p = Path(dest)
        if p.exists() and p.parent == INCOMING:
            process_ticket(p)

def sweep_pending():
    """Process any tickets already dropped into incoming prior to daemon start."""
    for item in sorted(INCOMING.glob("*.md")):
        print(f"[SWEEP] Found existing incoming ticket: {item.name}")
        process_ticket(item)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-visual-twin":
        if len(sys.argv) < 3:
            print("Usage: clio_queue_watcher.py --verify-visual-twin <ticket_path>")
            sys.exit(1)
        ticket_file = Path(sys.argv[2])
        ok, msg = run_atf_visual_twin_gate(ticket_file)
        if ok:
            print(f"[ATF_GATE] ✅ Visual Twin Gate passed for {ticket_file.name}")
            sys.exit(0)
        else:
            print(f"[ATF_GATE] 🛑 Visual Twin Gate failed for {ticket_file.name}:\n{msg}")
            sys.exit(1)

    for d in [INCOMING, PROCESSING, ARCHIVE, FAILED, LOGS, DEFERRED_DIR, REJECTED_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print(f"👁️ Clio Queue Watcher started.")
    print(f"Monitoring: {INCOMING}")

    check_deferred_queue()
    sweep_pending()

    event_handler = TicketHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING), recursive=False)
    observer.start()

    start_mtime = Path(__file__).stat().st_mtime

    try:
        while True:
            time.sleep(1)
            try:
                check_deferred_queue()
            except Exception as e:
                print(f"[DEFERRED SCAN ERROR] {e}")

            try:
                if Path(__file__).stat().st_mtime > start_mtime:
                    if execution_lock.locked():
                        continue
                    print(f"[RELOAD] Detected change in {__file__}. Restarting queue watcher...")
                    observer.stop()
                    observer.join()
                    os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception:
                pass
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
