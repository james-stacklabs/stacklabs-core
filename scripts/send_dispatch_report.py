#!/usr/bin/env python3
"""
=============================================================================
SOVEREIGN OS OUTBOUND DISPATCH MAILER
=============================================================================
A permanent, secure utility to dispatch official Sovereign OS reports,
memorandums, and system notifications via SMTP.

Reads canonical SMTP outbound credentials from /home/james/stacklabs/.env.

Usage:
    python3 scripts/send_dispatch_report.py \
      --subject "SYSTEM DISPATCH: Genesis Seeding" \
      --body "Please find the compiled seeding dossier attached." \
      --attachment "/home/james/sovereign_inbox/reports/WeedStack_and_StackLabs_Seeding_Report.pdf"
=============================================================================
"""

import os
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Load central Sovereign OS environment configuration
ENV_PATH = "/home/james/stacklabs/.env"
load_dotenv(ENV_PATH)

def send_dispatch(subject: str, body: str, attachment_path: str = None, recipient: str = None):
    # Fetch SMTP configurations from environment
    sender_email = os.getenv("SOVEREIGN_OUTBOUND_USER", "sovereign.os.v1@gmail.com")
    sender_password = os.getenv("SOVEREIGN_OUTBOUND_PASSWORD")
    
    # Recipient: custom -> env config -> fallback
    default_pilot = os.getenv("PILOT_EMAIL", "james@stacklabsllc.com,stacklabs.edge@gmail.com")
    raw_recipient = recipient if recipient else default_pilot

    if isinstance(raw_recipient, str):
        to_addrs = [e.strip() for e in raw_recipient.split(",") if e.strip()]
    elif isinstance(raw_recipient, (list, tuple)):
        to_addrs = [str(e).strip() for e in raw_recipient if str(e).strip()]
    else:
        to_addrs = [str(raw_recipient).strip()] if raw_recipient else []

    if not to_addrs:
        to_addrs = ["james@stacklabsllc.com", "stacklabs.edge@gmail.com"]

    if not sender_password:
        print("[!] Error: SOVEREIGN_OUTBOUND_PASSWORD not defined in .env!", file=sys.stderr)
        sys.exit(1)

    to_header = ", ".join(to_addrs)
    print(f"[*] Staging automated dispatch memorandum...")
    print(f"    From: {sender_email}")
    print(f"    To:   {to_header}")
    print(f"    Subj: {subject}")

    # Build Multipart Message
    msg = MIMEMultipart()
    msg['From'] = f"Sovereign OS <{sender_email}>"
    msg['To'] = to_header
    msg['Subject'] = subject

    # Inject Body text
    msg.attach(MIMEText(body, 'plain'))

    # Process attachment if provided
    if attachment_path:
        if not os.path.exists(attachment_path):
            print(f"[!] Warning: Attachment not found at {attachment_path}. Sending without attachment.", file=sys.stderr)
        else:
            print(f"[*] Attaching file: {os.path.basename(attachment_path)}")
            try:
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {os.path.basename(attachment_path)}",
                )
                msg.attach(part)
            except Exception as e:
                print(f"[!] Error reading attachment: {e}", file=sys.stderr)
                sys.exit(1)

    # Establish secure connection over SMTP port 587
    try:
        print("[*] Connecting to SMTP server (smtp.gmail.com:587)...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("[*] Authenticating with mail server...")
        server.login(sender_email, sender_password)
        print("[*] Dispatching email message...")
        server.sendmail(sender_email, to_addrs, msg.as_string())
        server.close()
        print("✅ SUCCESS: Sovereign OS dispatch successfully transmitted!")
        return True
    except Exception as e:
        print(f"❌ SMTP Failure: Could not transmit dispatch! Details: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Sovereign OS Outbound Mailer")
    parser.add_argument("--subject", required=True, help="Subject line of the email")
    parser.add_argument("--body", required=True, help="Body text of the email")
    parser.add_argument("--attachment", help="Absolute path to an attachment file")
    parser.add_argument("--to", help="Recipient email address override")
    
    args = parser.parse_args()
    success = send_dispatch(
        subject=args.subject,
        body=args.body,
        attachment_path=args.attachment,
        recipient=args.to
    )
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
