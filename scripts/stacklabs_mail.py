#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs LLC Unified Email Engine
Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
Account: james@stacklabsllc.com

Capabilities:
  1. CHECK: Read inbox, search keywords/senders, inspect full email bodies (plain + HTML fallback).
  2. DRAFT: Stage ready-to-review emails directly into [Gmail]/Drafts with attachments.
  3. SEND:  Direct outbound dispatch via SMTP with attachments.
"""

import os
import re
import sys
import argparse
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

OPSEC_OUTBOUND_BLOCKLIST = [
    r"\bvfs\b",
    r"virtual file system",
    r"symlink",
    r"inode",
    r"st_ino",
    r"shm_inode",
    r"db_inode",
    r"/dev/shm",
    r"\btmpfs\b",
    r"readlink",
    r"pagecache",
    r"sqlite[\s_]*wal",
    r"\bsqlite\b",
    r"\bposix\b",
]


def enforce_outbound_opsec_gate(subject: str, body_text: str, attachment_path: str = None):
    payloads = [("subject", subject or ""), ("body", body_text or "")]
    if attachment_path and os.path.exists(attachment_path):
        ext = os.path.splitext(attachment_path)[1].lower()
        if ext in {".txt", ".md", ".html", ".json", ".csv", ".py"}:
            with open(attachment_path, "r", errors="replace") as f:
                payloads.append((f"attachment:{os.path.basename(attachment_path)}", f.read()))
    for source_name, text in payloads:
        for pattern in OPSEC_OUTBOUND_BLOCKLIST:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                sys.stderr.write(
                    f"FATAL OPSEC_VIOLATION in {source_name}: matched banned trade-secret primitive '{m.group(0)}' (pattern: {pattern}). Refusing to stage or send.\n"
                )
                sys.exit(1)


def get_credentials():
    env_Path = "/home/james/stacklabs/.env"
    if os.path.exists(env_Path):
        load_dotenv(env_Path, override=False)

    user = os.getenv("STACKLABS_EMAIL_USER", "james@stacklabsllc.com").strip("\"'")
    pwd = os.getenv("STACKLABS_EMAIL_PASS", "").strip("\"'")

    if not user or not pwd:
        sys.stderr.write("ERROR: STACKLABS_EMAIL_USER or STACKLABS_EMAIL_PASS not configured in .env\n")
        sys.exit(1)

    return user, pwd


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
    plain_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_body += decoded
            elif content_type == "text/html" and not html_body:
                soup = BeautifulSoup(decoded, "html.parser")
                html_body = soup.get_text(separator="\n", strip=True)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                soup = BeautifulSoup(decoded, "html.parser")
                html_body = soup.get_text(separator="\n", strip=True)
            else:
                plain_body = decoded
    return (plain_body.strip() or html_body.strip())


def build_message(user, to_addr, subject, body_text, attachment_path=None, cc_addr=None):
    enforce_outbound_opsec_gate(subject, body_text, attachment_path)
    msg = MIMEMultipart()
    msg["From"] = f"James Carroll <{user}>"
    msg["To"] = to_addr
    if cc_addr:
        msg["Cc"] = cc_addr
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)

    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if attachment_path:
        if not os.path.exists(attachment_path):
            raise FileNotFoundError(f"Attachment not found: {attachment_path}")
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)
        print(f"[*] Attached: {filename} ({os.path.getsize(attachment_path)} bytes)")

    return msg


def action_check(args):
    user, pwd = get_credentials()
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)
        mail.select("inbox")
    except Exception as e:
        sys.stderr.write(f"IMAP login failed: {e}\n")
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

    print(f"\n📬 STACKLABS LLC INBOX ({user}) — Total: {total_found} messages\n" + "=" * 70)
    for em in emails_data:
        print(f"ID: {em['id']} | Date: {em['date']}")
        print(f"From: {em['from']}")
        print(f"Subject: {em['subject']}")
        print("-" * 70)
        if args.full:
            print(em['body'])
        else:
            preview = em['body'][:300].replace('\n', ' ')
            print(f"Preview: {preview} [truncated]")
        print("=" * 70 + "\n")

    out_dir = "/home/james/stacklabs/pilot_drops"
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "latest_stacklabs_emails.json")
    md_path = os.path.join(out_dir, "LATEST_STACKLABS_EMAILS.md")

    with open(json_path, "w") as f:
        json.dump(emails_data, f, indent=2)

    with open(md_path, "w") as f:
        f.write("# 📬 LATEST STACKLABS LLC EMAILS\n")
        f.write(f"> **Account**: `{user}` | **Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for em in emails_data:
            f.write(f"### 📨 {em['subject']}\n")
            f.write(f"- **ID**: `{em['id']}`\n")
            f.write(f"- **From**: `{em['from']}`\n")
            f.write(f"- **Date**: `{em['date']}`\n\n")
            f.write("```text\n")
            f.write(em['body'][:1200] + ("\n[truncated]" if len(em['body']) > 1200 else ""))
            f.write("\n```\n\n---\n\n")


def action_draft(args):
    user, pwd = get_credentials()
    body_text = args.body
    if args.body_file and os.path.exists(args.body_file):
        with open(args.body_file, "r") as f:
            body_text = f.read()

    msg = build_message(user, args.to, args.subject, body_text, args.attach, args.cc)
    raw_msg = msg.as_bytes()

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)
        draft_folder = "[Gmail]/Drafts"
        mail.append(draft_folder, r"(\Draft \Seen)", imaplib.Time2Internaldate(time.time()), raw_msg)
        mail.logout()
        print(f"✅ Draft successfully staged in Gmail Drafts for {user}!")
        print(f"   To: {args.to}")
        print(f"   Subject: {args.subject}")
        if args.attach:
            print(f"   Attachment: {args.attach}")
        print("   Ready for Pilot review in Gmail on mobile or desktop.")
    except Exception as e:
        sys.stderr.write(f"Failed to create draft: {e}\n")
        sys.exit(1)


def action_send(args):
    user, pwd = get_credentials()
    body_text = args.body
    if args.body_file and os.path.exists(args.body_file):
        with open(args.body_file, "r") as f:
            body_text = f.read()

    msg = build_message(user, args.to, args.subject, body_text, args.attach, args.cc)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(user, pwd)
        recipients = [args.to]
        if args.cc:
            recipients.append(args.cc)
        server.send_message(msg)
        server.quit()
        print(f"🚀 Email successfully SENT from {user}!")
        print(f"   To: {args.to}")
        print(f"   Subject: {args.subject}")
        if args.attach:
            print(f"   Attachment: {args.attach}")
    except Exception as e:
        sys.stderr.write(f"Failed to send email: {e}\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="StackLabs LLC Email Engine (Check, Draft, Send)")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run: check, draft, send")

    p_check = subparsers.add_parser("check", help="Check inbox and search emails")
    p_check.add_argument("--limit", type=int, default=5, help="Number of emails to fetch (default: 5)")
    p_check.add_argument("--search", type=str, default=None, help="Search query (Subject / From)")
    p_check.add_argument("--full", action="store_true", help="Print full email body")
    p_check.add_argument("--json", action="store_true", help="Print JSON output")

    p_draft = subparsers.add_parser("draft", help="Stage an email draft directly into [Gmail]/Drafts")
    p_draft.add_argument("--to", required=True, help="Recipient email address")
    p_draft.add_argument("--subject", required=True, help="Email subject line")
    p_draft.add_argument("--body", default="", help="Email body text")
    p_draft.add_argument("--body-file", default=None, help="Path to markdown/text file for body content")
    p_draft.add_argument("--attach", default=None, help="Path to file attachment")
    p_draft.add_argument("--cc", default=None, help="Optional CC email address")

    p_send = subparsers.add_parser("send", help="Send an email directly via SMTP")
    p_send.add_argument("--to", required=True, help="Recipient email address")
    p_send.add_argument("--subject", required=True, help="Email subject line")
    p_send.add_argument("--body", default="", help="Email body text")
    p_send.add_argument("--body-file", default=None, help="Path to markdown/text file for body content")
    p_send.add_argument("--attach", default=None, help="Path to file attachment")
    p_send.add_argument("--cc", default=None, help="Optional CC email address")

    args = parser.parse_args()

    if args.command == "check":
        action_check(args)
    elif args.command == "draft":
        action_draft(args)
    elif args.command == "send":
        action_send(args)


if __name__ == "__main__":
    main()
