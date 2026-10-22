#!/usr/bin/env python3
"""
StackLabs Enterprise Email CLI
Path: /home/james/stacklabs/scripts/stacklabs_email.py
Author: James Carroll (Lead Systems Architect & Founder, StackLabs LLC)

Unified CLI for checking and drafting corporate email (james@stacklabsllc.com).
Usage:
    python3 scripts/stacklabs_email.py check [--limit N] [--full] [--search QUERY]
    python3 scripts/stacklabs_email.py draft --to <alias|email> [--body "text" | --body-file file.md] [--image path]
"""

import sys
import argparse
from pathlib import Path

# Add scripts and core to path
SCRIPT_DIR = Path(__file__).resolve().parent
CORE_DIR = SCRIPT_DIR / "core"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from email_draft_engine import create_draft, resolve_recipient
import check_stacklabs_email


def handle_check(args):
    """Delegates to check_stacklabs_email main logic."""
    sys.argv = [sys.argv[0]]
    if args.limit:
        sys.argv.extend(["--limit", str(args.limit)])
    if args.search:
        sys.argv.extend(["--search", args.search])
    if args.full:
        sys.argv.append("--full")
    if args.json:
        sys.argv.append("--json")
    check_stacklabs_email.main()


def handle_draft(args):
    """Executes email draft creation via email_draft_engine."""
    body_content = ""
    if args.body_file:
        bf = Path(args.body_file)
        if not bf.exists():
            sys.stderr.write(f"ERROR: Body file {args.body_file} not found.\n")
            sys.exit(1)
        body_content = bf.read_text(encoding="utf-8")
    elif args.body:
        body_content = args.body
    elif not sys.stdin.isatty():
        body_content = sys.stdin.read()
    elif args.dry_run:
        body_content = ""
    else:
        sys.stderr.write("ERROR: No body text provided (--body, --body-file, or stdin).\n")
        sys.exit(1)

    result = create_draft(
        to=args.to,
        subject=args.subject,
        body_text=body_content,
        image_path=args.image,
        reply_to_latest=not args.no_reply_thread,
        purge_existing=not args.keep_drafts,
        dry_run=args.dry_run
    )

    print("\n📬 STACKLABS EMAIL DRAFT ENGINE: EXECUTION COMPLETE")
    print("=" * 60)
    for k, v in result.items():
        print(f"  {k:20}: {v}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="StackLabs LLC Enterprise Email Interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: check
    check_parser = subparsers.add_parser("check", help="Check incoming corporate emails")
    check_parser.add_argument("--limit", type=int, default=5, help="Number of latest emails to retrieve")
    check_parser.add_argument("--search", type=str, default=None, help="Search query (Subject / From)")
    check_parser.add_argument("--full", action="store_true", help="Print full email bodies")
    check_parser.add_argument("--json", action="store_true", help="Output JSON only")

    # Subcommand: draft
    draft_parser = subparsers.add_parser("draft", help="Compose and stage an email draft to [Gmail]/Drafts")
    draft_parser.add_argument("--to", required=True, help="Recipient alias ('pawel', 'jeremy') or email address")
    draft_parser.add_argument("--subject", default=None, help="Subject line (auto-derives from thread if omitted)")
    draft_parser.add_argument("--body", default=None, help="Raw body text (Markdown supported)")
    draft_parser.add_argument("--body-file", default=None, help="Path to markdown body file")
    draft_parser.add_argument("--image", default=None, help="Path to visual asset to attach and embed inline")
    draft_parser.add_argument("--no-reply-thread", action="store_true", help="Do not auto-link In-Reply-To thread headers")
    draft_parser.add_argument("--keep-drafts", action="store_true", help="Do not purge older drafts with same subject")
    draft_parser.add_argument("--dry-run", action="store_true", help="Validate and render without writing to Gmail")

    args = parser.parse_args()

    if args.command == "check":
        handle_check(args)
    elif args.command == "draft":
        handle_draft(args)


if __name__ == "__main__":
    main()
