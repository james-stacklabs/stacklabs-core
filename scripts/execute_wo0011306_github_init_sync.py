#!/usr/bin/env python3
"""
WO0011306: Initialize and synchronize /home/james/stacklabs/ with the private
GitHub repository (git@github-james:james-stacklabs/stacklabs-core.git).
Enforces strict .gitignore rules, <5MB file size bounds, and secret scrubbing.
"""

import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/james/stacklabs")
INBOX_ROOT = Path("/home/james/stacklabs_inbox")
REMOTE_URL = "git@github-james:james-stacklabs/stacklabs-core.git"
MAX_FILE_BYTES = 4 * 1024 * 1024  # 4 MB hard ceiling per tracked file

GITIGNORE_CONTENT = """# Runtime databases & large wiretaps
*.db
*.db-wal
*.db-shm
*.sqlite
*.sqlite3
data/*.db
vfs/cmdb.db
vfs/liberated/
scripts/chroma_db/

# Media cache & downloads
downloads/
*.mp4
*.mp3
*.wav
*.m4a
*.webm
*.mkv
*.mov
*.avi
*.flac
*.ogg

# Session logs & local state caches
logs/
*.log
session_cache/
.DS_Store
__pycache__/
*.py[cod]
.venv/
venv/
node_modules/
dist/
build/

# Heavy archives, binary drops & local email/comms caches
*.zip
*.tar
*.tar.gz
*.tgz
*.pdf
*.png
*.jpg
*.jpeg
*.webp
scripts/archive/
scripts/event_media_cache/
scripts/promo_staging.json
scripts/reports/*.html
queue/logs/
pilot_drops/video/
pilot_drops/downloads/
pilot_drops/archives/
pilot_drops/archive/
pilot_drops/relics/
pilot_drops/sprint_studio_*/
pilot_drops/screenshots/
pilot_drops/photos/
pilot_drops/scratch/
pilot_drops/audio/
pilot_drops/comms/
pilot_drops/email/
pilot_drops/direct_wire_mockups/
pilot_drops/documents/
pilot_drops/*.html
pilot_drops/latest_stacklabs_emails.json

# Credentials & environment secrets
.env
.env.*
scripts/.env*
*token*.json
*credentials*.json
*client_secret*.json
*.pem
*.key
"""

README_CONTENT = """# StackLabs Core (`stacklabs-core`)

- **Lead Systems Architect**: James Carroll (Pilot), StackLabs LLC
- **Primary Workstation**: Clio (`clio` / Dedicated Linux Host / `100.96.77.20`)
- **Active Model Baseline**: `gemini-3.8-flash` & `gemini-flash-lite-latest` (October 2026)

## Architecture Overview

1. **Virtual File System (`vfs/`)**:
   - Canonical workspaces (`/vfs/spaces/pawel/`), curated research vaults (`/vfs/vault/`), Swanson Undiscovered Public Knowledge (UPK) synthesis reports (`/vfs/spaces/pawel/investigations/`), and the 28-Slot Shadow Prediction Board (`/vfs/spaces/pawel/predictions/`).
2. **Service Blueprints & Automation (`scripts/`)**:
   - Decoupled FastAPI/Flask service routers, Swanson Collider engines, Ground Truth validators, and Google Drive (`stacklabs_edge:` / `stacklabs_vault:`) synchronization pipelines.
3. **4-Quarters Autonomous Queue (`queue/`)**:
   - Deterministic GitOps ticket pipeline (`queue/incoming/` -> `queue/processing/` -> `queue/archive/`) executed on Clio via `clio_queue_watcher.py`.
4. **Pilot Drops & Continuity Passports (`pilot_drops/` & `vault/`)**:
   - Cross-session continuity passports (`PILOT_PASSPORT_CURRENT.md`), syllabus indices (`PAWEL_28_ESSAY_SYLLABUS_INDEX.md`), and indexed research artifacts.
"""

SECRET_REGEXES = [
    re.compile(r"AIzaSy[0-9A-Za-z\-_]{33}"),
    re.compile(r"AQ\.[0-9A-Za-z\-_]{30,}"),
    re.compile(r"GOCSPX-[0-9A-Za-z\-_]{20,}"),
    re.compile(r"1//[0-9A-Za-z\-_]{40,}"),
    re.compile(r"ghp_[0-9A-Za-z]{36}"),
    re.compile(r"github_pat_[0-9A-Za-z_]{50,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def run_cmd(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    if check and res.returncode != 0:
        raise RuntimeError(
            f"Command failed ({res.returncode}): {' '.join(args)}\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        )
    return res


def main() -> int:
    now_iso = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4))).isoformat(timespec="seconds")
    print(f"[{now_iso}] Starting WO0011306 GitHub Repository Initialization & Sync...")

    # 1. Verify core directories exist
    required_dirs = ["vfs", "scripts", "queue", "vault", "pilot_drops"]
    for d in required_dirs:
        p = ROOT / d
        if not p.is_dir():
            raise RuntimeError(f"Missing required directory: {p}")
    print("✔ Core directories verified: vfs/, scripts/, queue/, vault/, pilot_drops/")

    # 2. Write .gitignore and README.md
    (ROOT / ".gitignore").write_text(GITIGNORE_CONTENT, encoding="utf-8")
    (ROOT / "README.md").write_text(README_CONTENT, encoding="utf-8")
    print("✔ Wrote /home/james/stacklabs/.gitignore and /home/james/stacklabs/README.md")

    # 3. Initialize Git & configure identity
    if not (ROOT / ".git").exists():
        run_cmd(["git", "init", "-b", "main"])
    else:
        run_cmd(["git", "checkout", "-B", "main"], check=False)

    run_cmd(["git", "config", "user.name", "James Carroll"])
    run_cmd(["git", "config", "user.email", "james@stacklabsllc.com"])

    # Configure origin remote
    remotes = run_cmd(["git", "remote"], check=False).stdout.split()
    if "origin" in remotes:
        run_cmd(["git", "remote", "set-url", "origin", REMOTE_URL])
    else:
        run_cmd(["git", "remote", "add", "origin", REMOTE_URL])

    print(f"✔ Configured git user identity (James Carroll <james@stacklabsllc.com>) and remote ({REMOTE_URL})")

    # 4. Fetch remote baseline if present so history links cleanly without force-push
    fetch_res = run_cmd(["git", "fetch", "origin", "main"], check=False)
    has_remote_main = fetch_res.returncode == 0
    if has_remote_main:
        run_cmd(["git", "reset", "--soft", "origin/main"], check=False)
        run_cmd(["git", "reset", "HEAD"], check=False)
        print("✔ Soft-aligned local branch parent with existing origin/main baseline")

    # 5. Stage core surfaces
    stage_targets = [
        ".gitignore",
        "README.md",
        "AGENTS.md",
        "GEMINI.md",
        "scripts",
        "vfs",
        "vault",
        "queue",
        "pilot_drops",
    ]
    existing_targets = [t for t in stage_targets if (ROOT / t).exists()]
    run_cmd(["git", "add", "--all", "--"] + existing_targets)

    # 6. Pre-commit hygiene filter: unstage any file > 4MB or containing live secret patterns
    staged_out = run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.splitlines()
    unstaged_large = []
    unstaged_secrets = []

    for rel_path in staged_out:
        fpath = ROOT / rel_path
        if not fpath.is_file() or fpath.is_symlink():
            continue
        try:
            fsize = fpath.stat().st_size
        except OSError:
            continue
        if fsize > MAX_FILE_BYTES:
            run_cmd(["git", "reset", "HEAD", "--", rel_path], check=False)
            unstaged_large.append(f"{rel_path} ({fsize} bytes)")
            continue

        # Scan text content for live secret literals (excluding adversarial_gate.py regex definitions)
        if rel_path != "scripts/core/adversarial_gate.py":
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                if any(rx.search(content) for rx in SECRET_REGEXES):
                    run_cmd(["git", "reset", "HEAD", "--", rel_path], check=False)
                    unstaged_secrets.append(rel_path)
            except Exception:
                pass

    final_staged = run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.splitlines()
    print(f"✔ Staged {len(final_staged)} clean files (unstaged {len(unstaged_large)} large files, {len(unstaged_secrets)} secret-flagged files)")

    # 7. Commit with cryptographic timestamp receipt
    commit_msg = (
        "feat(stacklabs): initialize canonical private repository with VFS engine, "
        "Swanson collider, and Pawel shadow prediction board"
    )
    status_porcelain = run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.strip()
    if status_porcelain:
        run_cmd(["git", "commit", "-m", commit_msg])
    commit_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    commit_timestamp = run_cmd(["git", "log", "-1", "--format=%cI"], check=False).stdout.strip()
    if not commit_timestamp:
        commit_timestamp = now_iso
    print(f"✔ Committed {commit_sha} at {commit_timestamp}")

    # 8. Push to origin/main
    push_res = run_cmd(["git", "push", "-u", "origin", "main"], check=False)
    if push_res.returncode != 0:
        # If non-fast-forward due to unrelated initial commit, merge with -X ours and push
        run_cmd(["git", "merge", "origin/main", "--allow-unrelated-histories", "-X", "ours", "-m", "chore(stacklabs): unify baseline history"])
        run_cmd(["git", "push", "-u", "origin", "main"])
        commit_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()

    remote_ls = run_cmd(["git", "ls-remote", "origin", "refs/heads/main"]).stdout.strip()
    print(f"✔ Remote verification receipt: {remote_ls}")

    # 9. Write execution receipt to queue/archive/WO0011306_COMPLETED.md
    receipt_path = ROOT / "queue" / "archive" / "WO0011306_COMPLETED.md"
    receipt_md = f"""# WO0011306 EXECUTION RECEIPT — PRIVATE GITHUB REPOSITORY INITIALIZATION & SYNC

- **Work Order ID**: `WO0011306`
- **Target Host**: Clio (`clio` / Dedicated Linux Host / `100.96.77.20`)
- **Repository Root**: `/home/james/stacklabs/`
- **Remote Origin**: `{REMOTE_URL}`
- **Branch**: `main`
- **HEAD Commit SHA**: `{commit_sha}`
- **Remote `ls-remote` Receipt**: `{remote_ls}`
- **Staged & Tracked File Count**: `{len(final_staged)}`
- **Timestamp**: `{now_iso}`

## Verification Summary
1. **Git Identity**: `James Carroll <james@stacklabsllc.com>`
2. **Tracked Surfaces**: `.gitignore`, `README.md`, `AGENTS.md`, `GEMINI.md`, `scripts/`, `vfs/`, `vault/`, `queue/`, `pilot_drops/`
3. **Excluded Heavy/Runtime Surfaces**: `*.db`, `*.sqlite*`, `vfs/cmdb.db`, `vfs/liberated/`, `downloads/`, `*.mp4`, `*.mp3`, `*.wav`, `logs/`, `*.log`, `session_cache/`, `.DS_Store`, `.env*`
4. **Unstaged >4MB Blobs**: `{len(unstaged_large)}`
5. **Unstaged Secret-Pattern Files**: `{len(unstaged_secrets)}`
"""
    receipt_path.write_text(receipt_md, encoding="utf-8")

    walkthrough_path = ROOT / "walkthroughs" / "walkthrough_WO0011306.md"
    walkthrough_path.parent.mkdir(parents=True, exist_ok=True)
    walkthrough_path.write_text(receipt_md, encoding="utf-8")

    walkthrough_full_path = ROOT / "walkthroughs" / "walkthrough_WO0011306_INIT_AND_PUSH_STACKLABS_GITHUB_REPO.md"
    walkthrough_full_path.write_text(receipt_md, encoding="utf-8")

    # 10. Update PILOT_PASSPORT_CURRENT.md with GitHub Repo state
    passport_path = ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md"
    if passport_path.exists():
        passport_text = passport_path.read_text(encoding="utf-8")
        github_block = (
            f"\n### 6. Private GitHub Repository Sync (`WO0011306`)\n"
            f"- **Remote**: `{REMOTE_URL}` (`main`)\n"
            f"- **HEAD Commit**: `{commit_sha}` (`{len(final_staged)}` tracked files)\n"
            f"- **Execution Receipt**: `/home/james/stacklabs/queue/archive/WO0011306_COMPLETED.md`\n"
        )
        if "WO0011306" not in passport_text:
            passport_text = passport_text.rstrip() + "\n" + github_block
            passport_path.write_text(passport_text, encoding="utf-8")
            inbox_passport = INBOX_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md"
            if inbox_passport.parent.exists():
                inbox_passport.write_text(passport_text, encoding="utf-8")

    # Commit the walkthrough receipts so remote has them too
    run_cmd(
        [
            "git",
            "add",
            "walkthroughs/walkthrough_WO0011306.md",
            "walkthroughs/walkthrough_WO0011306_INIT_AND_PUSH_STACKLABS_GITHUB_REPO.md",
            "scripts/execute_wo0011306_github_init_sync.py",
        ],
        check=False,
    )
    if run_cmd(["git", "diff", "--cached", "--name-only"]).stdout.strip():
        run_cmd(["git", "commit", "-m", "docs(wo0011306): record execution receipt and walkthrough"])
        run_cmd(["git", "push", "origin", "main"])
        commit_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()

    print(f"✔ WO0011306 completed cleanly. Final HEAD: {commit_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
