#!/usr/bin/env python3
"""
queue_runner.py - Small Ball Local Queue Runner Daemon.

Monitors `.queue/incoming/` (or `queue/incoming/`) for 4-Quarters Work Orders.
When a ticket is dropped in:
1. Moves it to `processing/`.
2. Executes Quarter 3 bash script blocks (or invokes a local agent CLI if configured).
3. Evaluates execution exit codes with set -eo pipefail.
4. Generates a permanent walkthrough record in `walkthroughs/`.
5. Moves the ticket to `archive/` (or `failed/` on failure).
"""

import os
import sys
import time
import shutil
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

POLL_INTERVAL_SECONDS = 2.0


def extract_q3_blocks(markdown_text: str) -> list[str]:
    """Extract complete contiguous bash blocks from Quarter 3."""
    q3_match = re.search(
        r'#{1,4}\s+.*?QUARTER\s+3.*?(?=#{1,4}\s+.*?QUARTER\s+4|\Z)',
        markdown_text,
        re.DOTALL | re.IGNORECASE
    )
    if not q3_match:
        return []
    
    q3_text = q3_match.group(0)
    # Extract complete code blocks (supports bash/sh, trailing spaces, CRLF)
    return re.findall(r'```(?:bash|sh)[ \t]*\r?\n(.*?)```', q3_text, re.DOTALL)


def resolve_queue_dir(root: Path) -> Path:
    """Support both .queue/ (portable) and queue/ (metal)."""
    if (root / ".queue").exists():
        return root / ".queue"
    if (root / "queue").exists():
        return root / "queue"
    return root / ".queue"


def sweep_orphaned_processing(queue_dir: Path):
    """Recover tickets stranded in processing/ on crash/restart."""
    processing_dir = queue_dir / "processing"
    incoming_dir = queue_dir / "incoming"
    if not processing_dir.exists():
        return
    for stranded in processing_dir.glob("*.md"):
        target = incoming_dir / stranded.name
        if target.exists():
            target.unlink()
        shutil.move(str(stranded), str(target))
        print(f"[*] Recovered orphaned processing ticket: {stranded.name} -> incoming/")


def process_ticket(ticket_path: Path, root: Path, queue_dir: Path, runner_cmd: str | None = None):
    ticket_name = ticket_path.name
    ticket_id = ticket_path.stem
    processing_dir = queue_dir / "processing"
    archive_dir = queue_dir / "archive"
    failed_dir = queue_dir / "failed"
    walkthrough_dir = root / "walkthroughs"

    processing_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    walkthrough_dir.mkdir(parents=True, exist_ok=True)

    processing_path = processing_dir / ticket_name

    print(f"\n[+] Ingesting ticket: {ticket_name}")
    if processing_path.exists():
        processing_path.unlink()
    shutil.move(str(ticket_path), str(processing_path))

    content = processing_path.read_text(encoding="utf-8")
    start_time = datetime.now()
    log_lines = []
    success = True

    # Mode A: Agent Execution (if --runner is passed, e.g. "agy -p" or script with {ticket})
    if runner_cmd:
        print(f"    [AGENT] Invoking runner: {runner_cmd}")
        log_lines.append(f"### Agent Runner: `{runner_cmd}`\n")
        if "{ticket}" in runner_cmd or "{file}" in runner_cmd:
            cmd = runner_cmd.replace("{ticket}", f'"{processing_path}"').replace("{file}", f'"{processing_path}"')
        else:
            cmd = f'{runner_cmd} "$(cat "{processing_path}")"'

        proc = subprocess.run(
            cmd,
            shell=True,
            executable="/bin/bash",
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        log_lines.append(f"```text\n{proc.stdout.strip()}\n```\n")
        log_lines.append(f"**Exit Code**: `{proc.returncode}`\n")
        success = (proc.returncode == 0)

    # Mode B: Quarter 3 Deterministic Script Blocks
    else:
        blocks = extract_q3_blocks(content)
        print(f"    Extracted {len(blocks)} script block(s) from Quarter 3.")

        if not blocks:
            print("    [!] Warning: No executable Quarter 3 bash blocks found.")
            log_lines.append("*(No executable bash blocks found in Quarter 3)*\n")

        for idx, block in enumerate(blocks, start=1):
            block_code = f"set -eo pipefail\n{block.strip()}"
            print(f"    [{idx}/{len(blocks)}] Executing Quarter 3 block...")
            log_lines.append(f"### Verification Block {idx}:\n```bash\n{block.strip()}\n```\n")
            
            proc = subprocess.run(
                block_code,
                shell=True,
                executable="/bin/bash",
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            output = proc.stdout.strip()
            log_lines.append(f"**Output**:\n```text\n{output}\n```\n")
            log_lines.append(f"**Exit Code**: `{proc.returncode}`\n")

            if proc.returncode != 0:
                print(f"    [!] Block {idx} failed with exit code {proc.returncode}")
                success = False
                break

    duration = (datetime.now() - start_time).total_seconds()
    status_str = "SUCCESS" if success else "FAILED"
    print(f"[*] Ticket {ticket_id} completed: {status_str} ({duration:.2f}s)")

    # Generate Walkthrough
    walkthrough_path = walkthrough_dir / f"walkthrough_{ticket_id}.md"
    rel_dest = f"{queue_dir.name}/{'archive' if success else 'failed'}/{ticket_name}"
    walkthrough_content = f"""# Walkthrough: {ticket_id}

> **Status**: {status_str}  
> **Executed At**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}  
> **Duration**: {duration:.2f}s  
> **Original Work Order**: `{rel_dest}`  

---

## Execution Log & Verification

{''.join(log_lines) if log_lines else '*(No explicit execution commands found)*'}

---

## Verdict
- Exit Status: `{status_str}`
- Archived to: `{rel_dest}`
"""
    walkthrough_path.write_text(walkthrough_content, encoding="utf-8")
    print(f"    [✓] Wrote walkthrough: {walkthrough_path.relative_to(root)}")

    # Move ticket to final resting place
    dest_dir = archive_dir if success else failed_dir
    dest_path = dest_dir / ticket_name
    if dest_path.exists():
        dest_path.unlink()
    shutil.move(str(processing_path), str(dest_path))
    print(f"    [✓] Moved ticket to: {dest_path.relative_to(root)}")


def main():
    parser = argparse.ArgumentParser(description="Small Ball Local Queue Runner Daemon")
    parser.add_argument("--runner", type=str, default=None, help="Optional agent runner CLI (e.g. 'agy --dangerously-skip-permissions -p')")
    parser.add_argument("--interval", type=float, default=POLL_INTERVAL_SECONDS, help="Polling interval in seconds")
    args = parser.parse_args()

    root = Path.cwd()
    queue_dir = resolve_queue_dir(root)
    incoming_dir = queue_dir / "incoming"
    processing_dir = queue_dir / "processing"
    archive_dir = queue_dir / "archive"
    failed_dir = queue_dir / "failed"
    walkthrough_dir = root / "walkthroughs"

    # Pre-create queue lifecycle folders
    for d in [incoming_dir, processing_dir, archive_dir, failed_dir, walkthrough_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Workspace-Scoped Concurrency Lock
    lock_file_path = queue_dir / ".runner.lock"
    lock_file = open(lock_file_path, "w")
    if HAS_FCNTL:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[!] Another instance of queue_runner is already active for {queue_dir}. Exiting.")
            sys.exit(0)

    sweep_orphaned_processing(queue_dir)

    print("======================================================")
    print(" ⚾ Small Ball Queue Runner Active")
    print(f" Root:     {root}")
    print(f" Watching: {queue_dir.name}/incoming/")
    print(f" Mode:     {'Agent Runner (' + args.runner + ')' if args.runner else 'Deterministic Quarter 3 Scripts'}")
    print(f" Polling:  Every {args.interval}s (Ctrl+C to stop)")
    print("======================================================")

    try:
        while True:
            tickets = sorted(list(incoming_dir.glob("*.md")))
            for ticket in tickets:
                process_ticket(ticket, root, queue_dir, runner_cmd=args.runner)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[*] Queue runner stopped by user.")


if __name__ == "__main__":
    main()
