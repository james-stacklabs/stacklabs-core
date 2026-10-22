#!/usr/bin/env python3
"""
scripts/sync_canonical_communications.py — Tool #56: StackLabs Canonical Communications Ingress Daemon
====================================================================================================
Polls Google Workspace IMAP (james@stacklabsllc.com) for high-value partner/creator/investor
communications, deduplicates by Message-ID, and appends directly to canonical ledgers
and the weekly session chronicle.
"""

import os
import sys
import time
import email
import imaplib
import json
import fcntl
import argparse
import subprocess
from email.header import decode_header
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load StackLabs environment
load_dotenv(dotenv_path="/home/james/stacklabs/.env", override=True)

USER = os.getenv("STACKLABS_EMAIL_USER", "james@stacklabsllc.com")
PASSWORD = os.getenv("STACKLABS_EMAIL_PASS", "")
IMAP_SERVER = os.getenv("STACKLABS_IMAP_SERVER", "imap.gmail.com")

STATE_FILE = "/home/james/stacklabs/data/processed_email_ids.json"
CHRONICLE_PATH = "/home/james/stacklabs_inbox/notebook_sync/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md"
ALT_CHRONICLE_PATH = "/home/james/stacklabs/StackLabs_Internal/epoch_sources/SESSION_CHRONICLE_CURRENT_WEEK.md"
SYNC_SCRIPT = "/home/james/stacklabs/scripts/sync_to_gdrive.sh"

ENTITY_ROUTING = {
    "wardy": {
        "patterns": ["wardy", "tyler", "wardynym"],
        "ledger": "/home/james/stacklabs_inbox/notebook_sync/09_WardyNYM_Creator_Prospectus/06_CANONICAL_COMMUNICATIONS_LOG_TYLER_WARD.md",
        "name": "Tyler Ward (WardyNYM)"
    },
    "pawel": {
        "patterns": ["pawel", "rudnicki", "rudnickipawel"],
        "ledger": "/home/james/stacklabs_inbox/notebook_sync/03_WildSeed_\x53overeign_Swarm/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md",
        "repo_ledger": "/home/james/stacklabs/dna/docs/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md",
        "name": "Pawel Rudnicki"
    },
    "jeremy": {
        "patterns": ["jeremy", "malone", "davidson"],
        "ledger": "/home/james/stacklabs_inbox/notebook_sync/06_Davidson_Malone_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEREMY_MALONE.md",
        "name": "Jeremy Malone"
    },
    "jeff": {
        "patterns": ["jeff", "uren", "u'ren"],
        "ledger": "/home/james/stacklabs_inbox/notebook_sync/11_JeffUren_Prospectus/01_CANONICAL_COMMUNICATIONS_LOG_AND_OPERATOR_DOSSIER_JEFF_UREN.md",
        "name": "Jeff U'Ren"
    },
    "google": {
        "patterns": ["google.com", "googlecloud", "cloudplatform"],
        "ledger": "/home/james/stacklabs_inbox/notebook_sync/02_Edge_Platform_Engineering/13_CANONICAL_COMMUNICATIONS_LOG_PAWEL_AND_JEREMY.md",
        "name": "Google Cloud Platform / Google for Startups"
    }
}


def load_processed_ids() -> set:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"[-] Warning reading {STATE_FILE}: {e}")
            return set()
    return set()


def save_processed_ids(ids_set: set) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids_set)), f, indent=2)
    except Exception as e:
        print(f"[-] Warning writing {STATE_FILE}: {e}")


def decode_mime_header(header_val: str) -> str:
    if not header_val:
        return ""
    try:
        decoded_parts = decode_header(header_val)
        result = []
        for text, encoding in decoded_parts:
            if isinstance(text, bytes):
                result.append(text.decode(encoding or "utf-8", errors="ignore"))
            else:
                result.append(str(text))
        return "".join(result).strip()
    except Exception:
        return str(header_val).strip()


def extract_body(msg) -> str:
    body = ""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        break
                elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_text = payload.decode(charset, errors="ignore")
                        soup = BeautifulSoup(html_text, "html.parser")
                        body = soup.get_text(separator="\n", strip=True)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content_type = msg.get_content_type()
                raw_text = payload.decode(charset, errors="ignore")
                if content_type == "text/html":
                    soup = BeautifulSoup(raw_text, "html.parser")
                    body = soup.get_text(separator="\n", strip=True)
                else:
                    body = raw_text
    except Exception as e:
        print(f"[-] Warning parsing body: {e}")
    return body.strip()


def identify_entity(from_addr: str, to_addr: str, subject: str):
    combined = f"{from_addr} {to_addr} {subject}".lower()
    for key, data in ENTITY_ROUTING.items():
        for pat in data["patterns"]:
            if pat in combined:
                return key, data
    return None, None


def append_to_ledger(ledger_path: str, entity_name: str, direction: str, timestamp_str: str,
                     subject: str, body: str, from_addr: str, to_addr: str,
                     repo_ledger: str = None, dry_run: bool = False):
    entry = f"""
---

### [{direction.upper()} EMAIL] {subject}
* **Timestamp:** {timestamp_str}
* **From:** `{from_addr}`
* **To:** `{to_addr}`
* **Entity:** {entity_name}
* **Channel:** StackLabs Corporate Gmail (`james@stacklabsllc.com`)

```text
{body}
```
"""
    if dry_run:
        print(f"[DRY-RUN] Would append to {ledger_path}:\n{entry[:200]}...")
        return

    # 1. Target Entity Ledger
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(entry)
                fcntl.flock(f, fcntl.LOCK_UN)
            print(f"[+] Appended to ledger: {ledger_path}")
        except Exception as e:
            print(f"[-] Error writing ledger {ledger_path}: {e}")
    else:
        print(f"[-] Target ledger not found: {ledger_path}")

    # 2. Repo Canonical Mirror (e.g. Pawel Rudnicki)
    if repo_ledger and os.path.exists(repo_ledger):
        try:
            with open(repo_ledger, "a", encoding="utf-8") as rf:
                fcntl.flock(rf, fcntl.LOCK_EX)
                rf.write(entry)
                fcntl.flock(rf, fcntl.LOCK_UN)
            print(f"[+] Appended to repo mirror ledger: {repo_ledger}")
        except Exception as re:
            print(f"[-] Error writing repo mirror ledger {repo_ledger}: {re}")

    # 3. Weekly Master Chronicle & Latest Daily Session Report
    chronicle_entry = f"""
---

### [{direction.upper()} EMAIL] {subject}
* **Timestamp:** {timestamp_str}
* **From:** `{from_addr}`
* **To:** `{to_addr}`
* **Entity:** {entity_name}
* **Channel:** StackLabs Corporate Gmail (`james@stacklabsllc.com`)

```text
{body}
```
"""
    import glob
    latest_reports = sorted(glob.glob("/home/james/stacklabs_inbox/today/SESSION_REPORT_20*.md"))
    if not latest_reports:
        latest_reports = sorted(glob.glob("/home/james/stacklabs_inbox/today/SESSION_REPORT_*.md"))
    if latest_reports:
        try:
            with open(latest_reports[-1], "a", encoding="utf-8") as rf:
                fcntl.flock(rf, fcntl.LOCK_EX)
                rf.write(chronicle_entry)
                fcntl.flock(rf, fcntl.LOCK_UN)
            print(f"[+] Appended to latest session report: {latest_reports[-1]}")
        except Exception as re:
            print(f"[-] Error writing session report: {re}")

    for c_path in [CHRONICLE_PATH, ALT_CHRONICLE_PATH]:
        if os.path.exists(c_path):
            try:
                with open(c_path, "a", encoding="utf-8") as cf:
                    fcntl.flock(cf, fcntl.LOCK_EX)
                    cf.write(chronicle_entry)
                    fcntl.flock(cf, fcntl.LOCK_UN)
                print(f"[+] Appended to weekly chronicle: {c_path}")
            except Exception as ce:
                print(f"[-] Error writing weekly chronicle {c_path}: {ce}")


def sync_mailbox(folder_name: str, direction: str = "INBOUND", dry_run: bool = False) -> int:
    processed_ids = load_processed_ids()
    new_ids = set(processed_ids)
    ingested_count = 0

    if not PASSWORD:
        print(f"[-] STACKLABS_EMAIL_PASS is not set in .env. Skipping IMAP sync for {folder_name}.", file=sys.stderr)
        return 0

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(USER, PASSWORD)

        # Select folder (handling quotes or plain names)
        status, _ = mail.select(f'"{folder_name}"')
        if status != "OK":
            status, _ = mail.select(folder_name)
        if status != "OK":
            print(f"[-] Could not select folder {folder_name} (status: {status})")
            return 0

        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages or not messages[0]:
            return 0

        msg_ids = messages[0].split()
        # Scan the most recent 25 messages
        for m_id in msg_ids[-25:]:
            res, data = mail.fetch(m_id, "(RFC822)")
            if res != "OK" or not data or not data[0]:
                continue
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            message_id = msg.get("Message-ID", "").strip()
            if not message_id:
                # Fallback to pseudo-ID if Message-ID missing
                date_header = msg.get("Date", "")
                subject_header = msg.get("Subject", "")
                message_id = f"hash_{hash(date_header + subject_header)}"

            if message_id in processed_ids:
                continue

            from_addr = decode_mime_header(msg.get("From", ""))
            to_addr = decode_mime_header(msg.get("To", ""))
            subject = decode_mime_header(msg.get("Subject", "(No Subject)"))
            date_str = msg.get("Date", "")

            entity_key, entity_data = identify_entity(from_addr, to_addr, subject)
            if not entity_data:
                # Mark as processed so we don't re-examine
                new_ids.add(message_id)
                continue

            body = extract_body(msg)
            dir_label = "OUTBOUND" if USER.lower() in from_addr.lower() else "INBOUND"

            print(f"[+] High-value comm found: {dir_label} -> {entity_data['name']} ({subject})")
            append_to_ledger(
                ledger_path=entity_data["ledger"],
                entity_name=entity_data["name"],
                direction=dir_label,
                timestamp_str=date_str,
                subject=subject,
                body=body,
                from_addr=from_addr,
                to_addr=to_addr,
                repo_ledger=entity_data.get("repo_ledger"),
                dry_run=dry_run
            )

            new_ids.add(message_id)
            ingested_count += 1

        if not dry_run and new_ids != processed_ids:
            save_processed_ids(new_ids)

    except imaplib.IMAP4.error as e:
        print(f"[-] IMAP authentication/protocol error on {folder_name}: {e}")
    except Exception as e:
        print(f"[-] Unexpected error during IMAP sync on {folder_name}: {e}")
    finally:
        if mail:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass

    return ingested_count


def run_sync_cycle(dry_run: bool = False) -> int:
    print(f"[*] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling StackLabs Canonical Communications for {USER}...")
    total_ingested = 0
    # 1. Sync Sent Mail
    total_ingested += sync_mailbox("[Gmail]/Sent Mail", direction="OUTBOUND", dry_run=dry_run)
    # 2. Sync Inbox
    total_ingested += sync_mailbox("INBOX", direction="INBOUND", dry_run=dry_run)

    # 3. Google Drive Sync if updates found
    if total_ingested > 0 and not dry_run and os.path.exists(SYNC_SCRIPT):
        print(f"[*] Triggering Google Drive cloud sync after {total_ingested} new comm(s)...")
        try:
            subprocess.run(["/bin/bash", SYNC_SCRIPT], check=False)
        except Exception as e:
            print(f"[-] Google Drive sync error: {e}")

    return total_ingested


def main():
    parser = argparse.ArgumentParser(
        description="Tool #56: StackLabs Canonical Communications Ingress Daemon & MacroDroid SMS Bridge"
    )
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true", default=False, help="Run a single sync pass and exit (default)")
    parser.add_argument("--dry-run", action="store_true", help="Inspect emails without writing to ledgers or state")

    args = parser.parse_args()

    if args.daemon:
        print(f"[*] Starting StackLabs Canonical Communications Ingress Daemon (Interval: {args.interval}s)...")
        while True:
            try:
                run_sync_cycle(dry_run=args.dry_run)
            except Exception as e:
                print(f"[-] Error in sync cycle: {e}")
            time.sleep(args.interval)
    else:
        run_sync_cycle(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
