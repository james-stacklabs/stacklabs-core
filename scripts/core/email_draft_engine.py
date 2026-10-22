#!/usr/bin/env python3
"""
StackLabs Enterprise Email Engine & Draft Dispatcher
Path: /home/james/stacklabs/scripts/core/email_draft_engine.py

Enterprise-grade email automation for StackLabs LLC:
1. Resolves partner aliases dynamically from ground_truth/partner_ground_truth.json ('pawel' -> 'paul@rudranchco.com').
2. Auto-discovers latest thread Message-ID for seamless In-Reply-To / References threading.
3. Compiles Markdown bodies to clean, modern HTML with dark-mode terminal log styling.
4. Handles inline image embedding (CID) and attachments with intelligent card sizing and placement.
5. Purges stale thread drafts on demand to maintain zero-clutter inbox hygiene.
6. Full CLI and programmatic Python API.
"""

import os
import sys
import time
import argparse
import imaplib
import json
import re
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

# Path anchors
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = REPO_ROOT / "ground_truth"


def load_credentials() -> Tuple[str, str]:
    """Loads email credentials from SovereignOS / stacklabs .env."""
    env_paths = [
        REPO_ROOT / ".env",
        Path("/home/james/stacklabs/.env"),
        Path("/home/james/stacklabs/.env")
    ]
    for p in env_paths:
        if p.exists():
            load_dotenv(p, override=False)

    user = os.getenv("STACKLABS_EMAIL_USER")
    pwd = os.getenv("STACKLABS_EMAIL_PASS")
    if not user or not pwd:
        raise ValueError("Missing STACKLABS_EMAIL_USER or STACKLABS_EMAIL_PASS in environment.")
    return user, pwd


def resolve_recipient(target: str) -> Tuple[str, str]:
    """
    Resolves a recipient target. If an alias like 'pawel' or 'jeremy' is given,
    resolves from ground_truth/partner_ground_truth.json.
    Returns (display_name, email_address).
    """
    target_clean = target.strip().lower()
    
    # Check ground truth partners
    partner_file = VAULT_DIR / "partner_ground_truth.json"
    if partner_file.exists():
        try:
            with open(partner_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            partners = data.get("partners", {})
            for key, val in partners.items():
                alias = key.lower()
                first_name = alias.split("_")[0]
                if target_clean in (alias, first_name):
                    p_email = val.get("email")
                    if p_email:
                        # Format clean display name
                        name_parts = key.replace("_", " ").title()
                        return f"{name_parts} <{p_email}>", p_email
        except Exception as e:
            sys.stderr.write(f"[WARN] Failed reading partner ground truth: {e}\n")

    # If raw email passed
    if "@" in target:
        if "<" in target and ">" in target:
            raw_email = re.search(r"<([^>]+)>", target).group(1)
            return target, raw_email
        return target, target

    return target, target


def markdown_to_html(md_text: str) -> str:
    """
    Renders clean Markdown text into styled HTML with modern typography,
    dark-mode telemetry blocks, and responsive typography.
    """
    html = md_text

    # Automatically strip top-level metadata headers (e.g. # 📬 GMAIL DRAFT... > To: ... ---)
    html = re.sub(r'^\s*#\s+.*?(?:DRAFT|BRIEF|MEMO|EMAIL).*?\n(?:>.*?\n)*\s*---\s*\n', '', html, flags=re.IGNORECASE)
    html = re.sub(r'^(?:>\s*\*\*(?:To|From|Date|Subject)\*\*:[^\n]*\n)+\s*---\s*\n', '', html, flags=re.IGNORECASE)

    # Escape HTML special chars first except inside pre-existing blocks
    # Convert code blocks ```text ... ``` into dark terminal blocks
    def code_replacer(match):
        code_content = match.group(2).strip()
        return (
            '<div style="background-color: #0b0d13; color: #e2e8f0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; '
            'font-size: 12px; padding: 16px; border-radius: 4px; border: 1px solid #1e2330; margin: 20px 0; line-height: 1.5; overflow-x: auto;">'
            f'<pre style="margin: 0; white-space: pre-wrap;">{code_content}</pre>'
            '</div>'
        )
    html = re.sub(r'```([a-zA-Z0-9_-]*)\n(.*?)```', code_replacer, html, flags=re.DOTALL)

    # Headers
    html = re.sub(r'^### (.*?)$', r'<h3 style="color: #111; margin-top: 18px; margin-bottom: 6px; font-size: 16px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2 style="color: #111; margin-top: 22px; margin-bottom: 8px; font-size: 18px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1 style="color: #111; margin-top: 24px; margin-bottom: 10px; font-size: 20px;">\1</h1>', html, flags=re.MULTILINE)

    # Bold and Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Horizontal rules
    html = re.sub(r'^---+$', r'<hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />', html, flags=re.MULTILINE)

    # Links
    html = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2" style="color: #0284c7; font-weight: bold; text-decoration: underline;">\1</a>', html)
    # Raw URLs not in href
    html = re.sub(r'(?<!href=")(https?://[^\s<]+)', r'<a href="\1" style="color: #0284c7; font-weight: bold; text-decoration: underline;">\1</a>', html)

    # Paragraphs (lines separated by double newlines)
    blocks = html.split('\n\n')
    processed_blocks = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith('<div') or b.startswith('<h') or b.startswith('<hr'):
            processed_blocks.append(b)
        else:
            # Replace single newlines inside paragraph with <br/>
            b_line = b.replace('\n', '<br/>')
            processed_blocks.append(f'<p style="margin: 0 0 14px 0;">{b_line}</p>')

    body_html = '\n'.join(processed_blocks)

    full_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #222; max-width: 720px; margin: 0 auto; padding: 12px;">
{body_html}
</body>
</html>"""
    return full_html


def get_latest_thread_headers(mail: imaplib.IMAP4_SSL, sender_email: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Finds the latest message from sender_email in the INBOX.
    Returns (message_id, subject, references).
    """
    mail.select("inbox")
    status, messages = mail.search(None, f'(FROM "{sender_email}")')
    if status != "OK" or not messages[0]:
        return None, None, None

    msg_ids = messages[0].split()
    latest_id = msg_ids[-1]
    res, data = mail.fetch(latest_id, "(BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT REFERENCES)])")
    
    msg_id = None
    subj = None
    refs = None
    
    for part in data:
        if isinstance(part, tuple):
            header_text = part[1].decode("utf-8", errors="replace")
            for line in header_text.splitlines():
                if line.lower().startswith("message-id:"):
                    msg_id = line.split(":", 1)[1].strip()
                elif line.lower().startswith("subject:"):
                    subj = line.split(":", 1)[1].strip()
                elif line.lower().startswith("references:"):
                    refs = line.split(":", 1)[1].strip()

    return msg_id, subj, refs


def purge_thread_drafts(mail: imaplib.IMAP4_SSL, subject: str) -> int:
    """Purges any existing drafts with matching subject to prevent clutter."""
    mail.select("[Gmail]/Drafts")
    clean_subj = subject.replace('"', '\\"')
    status, existing = mail.search(None, f'(SUBJECT "{clean_subj}")')
    purged = 0
    if status == "OK" and existing[0]:
        for eid in existing[0].split():
            mail.store(eid, "+FLAGS", "\\Deleted")
            purged += 1
        mail.expunge()
    return purged


def inject_inline_image(html_rendered: str, image_cid: str) -> str:
    """
    Injects the inline image card cleanly into the HTML body.
    Supports explicit markers ({{IMAGE}}, <!-- IMAGE -->, cid:) or places the image
    intelligently right before the closing signoff / after the body narrative.
    """
    img_card_html = (
        f'<div style="margin: 24px auto; text-align: center; max-width: 480px;">\n'
        f'  <img src="cid:{image_cid}" alt="Attached Visual Asset" '
        f'style="max-width: 100%; width: 100%; height: auto; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" />\n'
        f'</div>'
    )

    # 1. If explicit cid is already present in rendered HTML, do nothing
    if f"cid:{image_cid}" in html_rendered:
        return html_rendered

    # 2. Check for explicit template placeholders
    for placeholder in ["{{IMAGE}}", "<!-- IMAGE -->", "[IMAGE]"]:
        if placeholder in html_rendered:
            return html_rendered.replace(placeholder, img_card_html)

    # 3. Fallback: Identify signoff block (e.g. Best, Thanks, Regards)
    signoff_pattern = re.compile(r'(<p style="margin: 0 0 14px 0;">\s*(Best|Thanks|Sincerely|Regards|Cheers|Warmly|Respectfully),?\s*(<br/>|\n))', re.IGNORECASE)
    match = signoff_pattern.search(html_rendered)
    if match:
        idx = match.start()
        return html_rendered[:idx] + img_card_html + "\n" + html_rendered[idx:]

    # 4. Fallback: Place before </body>
    body_close = html_rendered.rfind("</body>")
    if body_close != -1:
        return html_rendered[:body_close] + img_card_html + "\n" + html_rendered[body_close:]

    return html_rendered + "\n" + img_card_html


def resolve_attachment_path(att: Optional[str]) -> Optional[Path]:
    """Resolves attachment path directly or relative to REPO_ROOT / docs."""
    if not att:
        return None
    candidates = [
        Path(att),
        REPO_ROOT / att,
        REPO_ROOT / "docs" / att,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def create_draft(
    to: str,
    subject: Optional[str] = None,
    body_text: str = "",
    image_path: Optional[str] = None,
    image_cid: str = "embedded_image",
    attachment_path: Optional[str] = None,
    reply_to_latest: bool = True,
    purge_existing: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Core function to build and dispatch an email draft to [Gmail]/Drafts.
    """
    user, pwd = load_credentials()
    recipient_header, raw_email = resolve_recipient(to)

    thread_msg_id = None
    thread_subject = None
    thread_refs = None

    mail = None
    if not dry_run:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, pwd)

    if reply_to_latest and mail:
        thread_msg_id, thread_subject, thread_refs = get_latest_thread_headers(mail, raw_email)

    # Determine final subject
    final_subject = subject
    if not final_subject:
        if thread_subject:
            final_subject = thread_subject if thread_subject.lower().startswith("re:") else f"Re: {thread_subject}"
        else:
            final_subject = "StackLabs Update"

    # Purge existing drafts
    purged_count = 0
    if purge_existing and mail:
        purged_count = purge_thread_drafts(mail, final_subject)

    # Build MIME message
    msg = MIMEMultipart("mixed")
    msg["To"] = recipient_header
    msg["From"] = f"James Carroll <{user}>"
    msg["Subject"] = final_subject

    if thread_msg_id:
        msg["In-Reply-To"] = thread_msg_id
        if thread_refs:
            msg["References"] = f"{thread_refs} {thread_msg_id}"
        else:
            msg["References"] = thread_msg_id

    # Format HTML
    html_rendered = markdown_to_html(body_text)

    # Inject inline image cleanly
    if image_path and Path(image_path).exists():
        html_rendered = inject_inline_image(html_rendered, image_cid)

    rel_part = MIMEMultipart("related")
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(body_text, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_rendered, "html", "utf-8"))
    rel_part.attach(alt_part)

    # Attach Image
    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        img_part = MIMEImage(img_bytes)
        img_part.add_header("Content-ID", f"<{image_cid}>")
        img_part.add_header("Content-Disposition", "inline", filename=Path(image_path).name)
        rel_part.attach(img_part)

    msg.attach(rel_part)

    # Attach Document / PDF if provided
    resolved_att = resolve_attachment_path(attachment_path)
    if resolved_att:
        with open(resolved_att, "rb") as f:
            att_bytes = f.read()
        subtype = "pdf" if resolved_att.suffix.lower() == ".pdf" else "octet-stream"
        att_part = MIMEApplication(att_bytes, _subtype=subtype)
        att_part.add_header("Content-Disposition", "attachment", filename=resolved_att.name)
        msg.attach(att_part)

    if dry_run:
        return {
            "status": "DRY_RUN",
            "to": recipient_header,
            "subject": final_subject,
            "in_reply_to": thread_msg_id,
            "has_image": bool(image_path and Path(image_path).exists()),
            "attachment": str(resolved_att) if resolved_att else None,
            "html_length": len(html_rendered)
        }

    # Append to IMAP [Gmail]/Drafts
    mail.append("[Gmail]/Drafts", "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    mail.logout()

    return {
        "status": "DRAFT_COMMITTED",
        "to": recipient_header,
        "subject": final_subject,
        "in_reply_to": thread_msg_id,
        "purged_prior_drafts": purged_count,
        "image_attached": bool(image_path and Path(image_path).exists()),
        "attachment_attached": resolved_att.name if resolved_att else None,
        "attachment_bytes": resolved_att.stat().st_size if resolved_att else 0
    }


def main():
    parser = argparse.ArgumentParser(description="StackLabs Canonical Email Draft Engine")
    parser.add_argument("--to", required=True, help="Recipient target (alias e.g. 'pawel' or full email)")
    parser.add_argument("--subject", default=None, help="Subject line (auto-derives from thread if omitted)")
    parser.add_argument("--body", default=None, help="Raw body text (Markdown supported)")
    parser.add_argument("--body-file", default=None, help="Path to markdown body file")
    parser.add_argument("--image", default=None, help="Path to visual asset to attach and embed inline")
    parser.add_argument("--attachment", default=None, help="Path or filename in docs/ to attach (e.g. PDF)")
    parser.add_argument("--no-reply-thread", action="store_true", help="Do not auto-link In-Reply-To thread headers")
    parser.add_argument("--keep-drafts", action="store_true", help="Do not purge older drafts with same subject")
    parser.add_argument("--dry-run", action="store_true", help="Validate and render without writing to Gmail")
    args = parser.parse_args()

    body_content = ""
    if args.body_file:
        bf = Path(args.body_file)
        if not bf.exists():
            sys.stderr.write(f"ERROR: Body file {args.body_file} not found.\n")
            sys.exit(1)
        body_content = bf.read_text(encoding="utf-8")
    elif args.body:
        body_content = args.body.replace('\\n', '\n').replace('\\t', '\t')
    elif not sys.stdin.isatty():
        body_content = sys.stdin.read()
    else:
        sys.stderr.write("ERROR: No body text provided (--body, --body-file, or stdin).\n")
        sys.exit(1)

    result = create_draft(
        to=args.to,
        subject=args.subject,
        body_text=body_content,
        image_path=args.image,
        attachment_path=args.attachment,
        reply_to_latest=not args.no_reply_thread,
        purge_existing=not args.keep_drafts,
        dry_run=args.dry_run
    )

    print("\n📬 STACKLABS EMAIL DRAFT ENGINE: EXECUTION COMPLETE")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k:20}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
