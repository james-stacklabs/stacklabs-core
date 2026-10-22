#!/usr/bin/env python3
"""
StackLabs LLC Canonical Email Ingress Utility
Checks corporate inbox (james@stacklabsllc.com) via IMAP.
Usage:
    python3 scripts/check_stacklabs_email.py [--limit N] [--full] [--search QUERY] [--save]
"""

import sys
import os
import argparse
import imaplib
import email
from email.header import decode_header
import json
from datetime import datetime
from dotenv import load_dotenv

def decode_mime_words(s):
    if not s:
        return ""
    decoded_chunks = decode_header(s)
    out = ""
    for chunk, enc in decoded_chunks:
        if isinstance(chunk, bytes):
            out += chunk.decode(enc or "utf-8", errors="replace")
        else:
            out += str(chunk)
    return out

def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="replace")
    return body.strip()

def main():
    parser = argparse.ArgumentParser(description="Check StackLabs LLC corporate email.")
    parser.add_argument("--limit", type=int, default=5, help="Number of latest emails to retrieve (default: 5)")
    parser.add_argument("--search", type=str, default=None, help="Search query (Subject / From)")
    parser.add_argument("--full", action="store_true", help="Print full email bodies")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--save", action="store_true", default=True, help="Save to pilot_drops (default: True)")
    args = parser.parse_args()

    # Load credentials from canonical SovereignOS .env
    env_paths = [
        "/home/james/stacklabs/.env",
        "/home/james/stacklabs/.env"
    ]
    for p in env_paths:
        if os.path.exists(p):
            load_dotenv(p, override=False)

    user = os.getenv("STACKLABS_EMAIL_USER")
    pwd = os.getenv("STACKLABS_EMAIL_PASS")

    if not user or not pwd:
        sys.stderr.write("ERROR: STACKLABS_EMAIL_USER or STACKLABS_EMAIL_PASS not found in .env\n")
        sys.exit(1)

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)
        mail.select("inbox")
    except Exception as e:
        sys.stderr.write(f"IMAP Connection failed: {e}\n")
        sys.exit(1)

    if args.search:
        status, messages = mail.search(None, f'(OR FROM "{args.search}" SUBJECT "{args.search}")')
    else:
        status, messages = mail.search(None, "ALL")

    if status != "OK" or not messages[0]:
        print("No messages found.")
        mail.logout()
        return

    msg_ids = messages[0].split()
    total_found = len(msg_ids)
    target_ids = msg_ids[-args.limit:]

    emails_data = []

    for mid in reversed(target_ids):
        res, data = mail.fetch(mid, "(RFC822)")
        for part in data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                subj = decode_mime_words(msg["Subject"])
                sender = decode_mime_words(msg.get("From"))
                date_str = msg.get("Date")
                body = get_email_body(msg)

                emails_data.append({
                    "id": mid.decode(),
                    "date": date_str,
                    "from": sender,
                    "subject": subj,
                    "body": body
                })

    mail.logout()

    if args.json:
        print(json.dumps(emails_data, indent=2))
        return

    print(f"\n📬 STACKLABS LLC INBOX ({user}) — Total: {total_found} messages\n" + "="*70)
    for em in emails_data:
        print(f"ID: {em['id']} | Date: {em['date']}")
        print(f"From: {em['from']}")
        print(f"Subject: {em['subject']}")
        print("-" * 70)
        if args.full:
            print(em['body'])
        else:
            preview = em['body'][:300].replace('\n', ' ')
            print(f"Preview: {preview}...")
        print("=" * 70 + "\n")

    if args.save:
        # Save structured outputs to pilot_drops
        out_dir = "/home/james/stacklabs/pilot_drops"
        os.makedirs(out_dir, exist_ok=True)
        json_path = os.path.join(out_dir, "latest_stacklabs_emails.json")
        md_path = os.path.join(out_dir, "LATEST_STACKLABS_EMAILS.md")

        with open(json_path, "w") as f:
            json.dump(emails_data, f, indent=2)

        with open(md_path, "w") as f:
            f.write(f"# 📬 LATEST STACKLABS LLC EMAILS\n")
            f.write(f"> **Account**: `{user}` | **Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for em in emails_data:
                f.write(f"### 📨 {em['subject']}\n")
                f.write(f"- **ID**: `{em['id']}`\n")
                f.write(f"- **From**: `{em['from']}`\n")
                f.write(f"- **Date**: `{em['date']}`\n\n")
                f.write("```text\n")
                f.write(em['body'][:1200] + ("\n... [truncated]" if len(em['body']) > 1200 else ""))
                f.write("\n```\n\n---\n\n")

if __name__ == "__main__":
    main()
