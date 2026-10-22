#!/usr/bin/env python3
"""
Sovereign OS: Autonomous Work Order Failure Doctor & Auto-Remediator Daemon
Path: /home/james/stacklabs/scripts/clio_failure_doctor.py

Monitors /home/james/stacklabs/queue/failed/ for failed work orders.
Diagnoses root cause (upstream capacity, compiler/build error, timeout, truncation),
enriches the work order with targeted remediation prescriptions, and automatically
re-stages the ticket into /home/james/stacklabs/queue/incoming/ with bounded retries.
"""

import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

QUEUE_DIR = Path("/home/james/stacklabs/queue")
FAILED = QUEUE_DIR / "failed"
INCOMING = QUEUE_DIR / "incoming"
LOGS = QUEUE_DIR / "logs"
NOTIFY_BIN = "/home/james/stacklabs/scripts/clio-notify.sh"

MAX_RETRIES = 3

def extract_attempt(content: str) -> int:
    m = re.search(r'<!--\s*REMEDIATION_ATTEMPT:\s*(\d+)\s*-->', content)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    return 0

def diagnose_error(error_log_path: Path, full_log_path: Path = None) -> tuple:
    """Analyze error log and return (category, description, extracted_snippet)."""
    text = ""
    if error_log_path and error_log_path.exists():
        try:
            text += error_log_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    if full_log_path and full_log_path.exists():
        try:
            full_text = full_log_path.read_text(encoding="utf-8", errors="ignore")
            text += "\n" + full_text[-5000:]
        except Exception:
            pass

    text_lower = text.lower()

    # 1. Upstream 503 / Capacity Shortage / Timeout
    if "503" in text or "unavailable" in text_lower or "no capacity available" in text_lower:
        return ("CAPACITY_503", "Upstream Model Capacity Shortage (HTTP 503)", "Server capacity shortage detected. Applying backoff.")
    if "print timeout after" in text_lower or "timed out" in text_lower:
        return ("RUNNER_TIMEOUT", "Execution Print Timeout (Stalled Turn)", "Runner hit timeout. Instruction refined for surgical edits.")

    # 2. Build / Compilation / Python errors
    error_lines = []
    capture = False
    for line in text.splitlines():
        if any(err in line for err in ["Error:", "ERR!", "FAILED", "Traceback", "Exception", "SyntaxError", "ModuleNotFoundError"]):
            capture = True
        if capture:
            error_lines.append(line)
            if len(error_lines) > 25:
                break
    snippet = "\n".join(error_lines) if error_lines else text[-1000:]

    if "syntaxerror" in text_lower or "modulenotfounderror" in text_lower or "npm err!" in text_lower:
        return ("BUILD_SYNTAX_ERROR", "Build/Syntax Error", snippet)

    return ("GENERAL_EXECUTION_FAILURE", "General Execution Failure", snippet)

def notify_pilot(ticket_name: str, message: str, status: str = "info"):
    if os.path.exists(NOTIFY_BIN) and os.access(NOTIFY_BIN, os.X_OK):
        try:
            subprocess.run(["bash", NOTIFY_BIN, status, ticket_name, message], timeout=15)
        except Exception as e:
            print(f"[WARN] Notification failed: {e}")

def remediate_and_resubmit(ticket_file: Path):
    if not ticket_file.exists() or not ticket_file.name.endswith(".md"):
        return

    # Skip files already being handled
    time.sleep(2.0)
    if not ticket_file.exists():
        return

    ticket_name = ticket_file.name
    error_log = ticket_file.with_suffix(".error.log")

    try:
        content = ticket_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] Could not read {ticket_file}: {e}")
        return

    current_attempt = extract_attempt(content)
    next_attempt = current_attempt + 1

    if next_attempt > MAX_RETRIES:
        print(f"[DOCTOR] Ticket {ticket_name} reached max retries ({MAX_RETRIES}). Quarantined.")
        notify_pilot(ticket_name, f"🚨 Quarantined after {MAX_RETRIES} remediation attempts. Manual review required.", "failure")
        return

    # Find latest execution log
    base_name = ticket_file.stem
    matching_logs = sorted(LOGS.glob(f"{base_name}_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    full_log = matching_logs[0] if matching_logs else None

    category, desc, snippet = diagnose_error(error_log, full_log)
    print(f"[DOCTOR] Diagnosed {ticket_name} -> {desc} (Attempt {next_attempt}/{MAX_RETRIES})")

    # Clean previous prescription headers if any
    cleaned_content = re.sub(r'<!--\s*REMEDIATION_ATTEMPT:\s*\d+\s*-->.*?---\s*', '', content, flags=re.DOTALL)

    # Build prescription header
    prescription = f"""<!-- REMEDIATION_ATTEMPT: {next_attempt} -->
### 🩺 AUTO-REMEDIATION PRESCRIPTION (Attempt {next_attempt}/{MAX_RETRIES}):
**Diagnosed Failure**: {desc}  
**Error Context**:
```text
{snippet.strip()[:1500]}
```

**Execution Directives for this Run**:
1. Address the diagnosed failure directly before proceeding.
2. Use surgical, minimal diffs. Do not re-read or dump entire trees.
3. Verify changes with a fast local check before declaring resolution.

---

"""
    new_content = prescription + cleaned_content

    # Exponential backoff based on attempt
    backoff_seconds = 15 * (2 ** (next_attempt - 1))
    print(f"[DOCTOR] Applying {backoff_seconds}s backoff before resubmission...")
    time.sleep(backoff_seconds)

    # Move back to incoming
    dest = INCOMING / ticket_name
    try:
        dest.write_text(new_content, encoding="utf-8")
        # Remove from failed
        ticket_file.unlink()
        if error_log.exists():
            error_log.unlink()
        print(f"[DOCTOR] Resubmitted {ticket_name} -> {dest}")
        notify_pilot(ticket_name, f"🔄 Auto-Remediating: {desc}. Re-staged to queue (Attempt {next_attempt}/{MAX_RETRIES}).", "info")
    except Exception as e:
        print(f"[ERROR] Resubmission failed for {ticket_name}: {e}")

class FailedTicketHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".md"):
            return
        remediate_and_resubmit(Path(event.src_path))

def sweep_failed():
    for f in sorted(FAILED.glob("*.md")):
        print(f"[DOCTOR SWEEP] Found existing failed ticket: {f.name}")
        remediate_and_resubmit(f)

def main():
    FAILED.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)

    print("🩺 Sovereign OS Failure Doctor & Auto-Remediator started.")
    print(f"Monitoring: {FAILED}")

    # Process any tickets currently stalled in failed
    sweep_failed()

    event_handler = FailedTicketHandler()
    observer = Observer()
    observer.schedule(event_handler, str(FAILED), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
