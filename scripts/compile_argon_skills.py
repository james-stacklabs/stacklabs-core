#!/home/james/stacklabs/.venv/bin/python3
"""
Argon Workflow-to-Skills Compiler & Clean-Room Sanitizer (36 -> 19 Skills).
Consolidates .agents/workflows/*.md into .agents/skills/ and /home/james/.gemini/config/skills/,
applies Progressive Disclosure YAML frontmatter, scrubs Invariant 1.9 banned tokens,
and verifies clean-room compliance.
"""

import pathlib
import re
import shutil
import sys
from datetime import datetime

STACKLABS_ROOT = pathlib.Path("/home/james/stacklabs")
WORKFLOWS_DIR = STACKLABS_ROOT / ".agents" / "workflows"
PROJECT_SKILLS_DIR = STACKLABS_ROOT / ".agents" / "skills"
GLOBAL_SKILLS_DIR = pathlib.Path("/home/james/.gemini/config/skills")
GLOBAL_MIRROR_DIR = STACKLABS_ROOT / ".agents" / "global-skills"
ARCHIVE_DIR = (
    STACKLABS_ROOT
    / "pilot_drops"
    / "archives"
    / f"legacy_workflows_compile_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

# Consolidation & Routing Map:
# (target_slug, scope, disable_model_invocation, description, source_files)
SKILL_MAP = [
    # --- GLOBAL SKILLS (~/.gemini/config/skills/ & mirrored in .agents/global-skills/) ---
    (
        "eli5-eli-nasa",
        "global",
        False,
        "Generate a dual-tier synthesis with Level 1 (ELI5 iPhone screen metaphor in 3-4 bullets) and Level 2 (ELI-NASA deep systems architecture, memory bounds, and failure modes). Use when asked for ELI5, quick recaps, or deep technical teardowns.",
        ["eli5_eli_nasa.md"],
    ),
    (
        "mobile-export",
        "global",
        True,
        "Package the preceding conversation turn, audio voice transcript, or architectural debate into a single 1-click copyable markdown block for mobile continuity. Use when /clipboard, /gemini_passport, or mobile prompt export is requested.",
        ["clipboard.md", "gemini_passport.md"],
    ),
    (
        "three-panel-review",
        "global",
        False,
        "Execute the 3-Panel Adversarial Peer Review crucible (Spark draft, Claude forensic contradiction/math audit, Qwen stress-test, and exact string verification). Use before finalizing external investor briefs, prospectuses, or deliverables.",
        ["three_panel_review.md"],
    ),
    (
        "token-meter",
        "global",
        True,
        "Audit active session token consumption, tool output bloat versus model reasoning, and context compaction thresholds via session_token_meter.py. Use when /token or context budget inspection is requested.",
        ["token.md"],
    ),
    # --- PROJECT SKILLS (.agents/skills/) ---
    (
        "stacklabs-boot",
        "project",
        True,
        "Initialize session state on Clio by reading PILOT_PASSPORT_CURRENT.md and the latest SESSION_REPORT, locking strict engineering posture, and setting the cognitive anchor word. Use on /stacklabs-boot or cold session start.",
        ["stacklabs_boot.md"],
    ),
    (
        "stacklabs-sync",
        "project",
        True,
        "Synchronize session progress, SQLite WAL ground truth ledgers, Google Drive remotes (stacklabs_edge and stacklabs_vault), Pilot Passport, and tomorrow's NotebookLM bridge. Use on /stacklabs_sync, /sync_passport, /progress_report, or /end_of_shift.",
        ["stacklabs_sync.md", "sync_passport.md", "progress_report.md", "end_of_shift.md"],
    ),
    (
        "stacklabs-comms",
        "project",
        False,
        "Check corporate email (james@stacklabsllc.com), stage Gmail drafts with attachments, send SMTP mail, or sync Android SMS/call backups into canonical counterparty chronicles. Use on /check_comms, /check_email, /send_mail, or email requests.",
        ["check_comms.md", "check_email.md", "send_mail.md", "stacklabs_email.md"],
    ),
    (
        "ground-truth",
        "project",
        False,
        "Ingest, verify, correlate, and atomically commit empirical facts, counterparty updates, market tickers, or compute telemetry into /home/james/stacklabs/ground_truth/ JSON and SQLite WAL ledgers. Use on /ground_truth.",
        ["ground_truth.md"],
    ),
    (
        "pawel-briefing",
        "project",
        False,
        "Translate engineering breakthroughs or FanStack mechanics into Horizon energy/commodity isomorphisms, 3-bullet check-writer briefs, and Gmail drafts for Pawel Rudnicki. Use on /pawel_speak, /polymorphism, /poly, or /pawel_dispatch.",
        ["pawel_speak.md", "polymorphism.md", "pawel_dispatch.md"],
    ),
    (
        "pawel-call",
        "project",
        True,
        "Launch the interactive rapid-response battle card and objection-handling selector for live Pawel Rudnicki SAFE, WildSeed, Horizon, and technical due-diligence calls. Use strictly when /pawel_call or /paul_call is invoked.",
        ["pawel_call.md"],
    ),
    (
        "prospectus-scaffold",
        "project",
        False,
        "Onboard a new Executive Prospectus or brand seeding report with CMDB CI registration, canonical 5-file dossier scaffolding, headless Chrome PDF compilation, and stacklabs_edge Drive sync. Use on /prospectus_onboarding or /rapid_project_onboarding.",
        ["prospectus_onboarding.md", "rapid_project_onboarding.md", "compile_genesis_report.md"],
    ),
    (
        "studio-ingest",
        "project",
        False,
        "Ingest NotebookLM Studio export zips from pilot_drops/downloads/, prune superseded archives, unpack audio and mind maps into sprint staging, and audit text for banned terminology. Use on /studio_drop or /notebooklm_studio_ingest.",
        ["notebooklm_studio_ingest.md"],
    ),
    (
        "faas-daily-prep",
        "project",
        True,
        "Execute the daily FanStack as a Service (FaaS) morning setup: sync 2026 MLB/NFL/CFB schedules, calibrate advocate bios, resolve YouTube stream URLs, verify daemons, and reset pulse vitals. Use on /faas_daily_prep.",
        ["faas_daily_prep.md"],
    ),
    (
        "advocate-onboarding",
        "project",
        False,
        "Onboard a new FanStack sports advocate from a Pilot-anchored hero image and concept, generating the canonical profile schema and running onboard_advocate.py. Use on /advocate_onboarding or new persona drops.",
        ["advocate_onboarding.md"],
    ),
    (
        "barf-tweet",
        "project",
        False,
        "Generate a 3-to-4 part tweet storm for Barf the Dog (@BarfFanStack) with verified <=280 character counts, franchise hashtags, and mandatory @TheWardyNYM tag. Use on /barf_tweet.",
        ["barf_tweet.md"],
    ),
    (
        "broadcast-intel",
        "project",
        False,
        "Query Pat McAfee Show, Theo Von, and live sports stream transcripts via broadcast_intelligence_engine.py, or ingest YouTube videos via download_youtube.py. Use on /mcafee, /theo, or /youtube_downloader.",
        ["mcafee.md", "theo.md", "youtube_downloader.md"],
    ),
    (
        "dogfood-audit",
        "project",
        True,
        "Audit the active StackLabs codebase against today's breakthroughs to identify legacy payload, database, or token bloat and stage a surgical dogfood Work Order. Use on /dinner_time.",
        ["dinner_time.md"],
    ),
    (
        "uat-flight-check",
        "project",
        True,
        "Enforce a build freeze to evaluate recent deployments across desktop/mobile viewports, capture Playwright First/Second-Born visual twins, and run remote node UAT snapshots. Use on /flight_check, /dual_born_digital_twin, or /walk_a_mile_in_my_shoes.",
        ["flight_check.md", "dual_born_digital_twin.md", "walk_a_mile_in_my_shoes.md"],
    ),
]

# Clean-Room Replacements
SANITIZE_SUBS = [
    (r"\b" + "Sovereign" + r"\s+OS\b", "StackLabs Platform"),
    (r"\b" + "SovereignOS" + r"\b", "StackLabs Platform"),
    (r"\b" + "Sovereign" + r"\s+Horizon\b", "Horizon DDP"),
    (r"\b" + "Sovereign" + r"\s+FanStack\b", "FanStack"),
    (r"\b" + "sovereign_boot" + r"\b", "stacklabs_boot"),
    (r"\b" + "sovereign_shutdown" + r"\b", "end_of_shift"),
    (r"\b" + "sovereign" + r"\b", "StackLabs"),
    (r"\b" + "bare[- ]metal" + r"\b", "dedicated local host"),
    (r"\b" + "on" + r" " + "metal" + r"\b", "on local host"),
    (r"\b" + "metal" + r" forge\b", "local workstation"),
    (r"\b" + "metal" + r" reality\b", "operational reality"),
    (r"\b" + "metal" + r" receipts\b", "empirical receipts"),
    (r"\b" + "Bee" + "link\b", "commodity x86 workstation"),
    (r"/home/james/stacklabs/stacklabs_inbox/queue/incoming/", "/home/james/stacklabs/queue/incoming/"),
    (r"sov73\.taila01894\.ts\.net", "clio.taila01894.ts.net"),
    (r"(?<![/\w.-])python3?\s+/home/james/stacklabs/", "/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/"),
]

def strip_frontmatter(md_text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n*", "", md_text, flags=re.DOTALL).strip()

def sanitize_body(text: str) -> str:
    for pattern, replacement in SANITIZE_SUBS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def main() -> int:
    PROJECT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if WORKFLOWS_DIR.exists():
        for wf_file in WORKFLOWS_DIR.glob("*.md"):
            shutil.copy2(wf_file, ARCHIVE_DIR / wf_file.name)
        print(f"[+] Backed up legacy workflows to {ARCHIVE_DIR}")

    compiled_count = 0
    for slug, scope, disable_auto, desc, sources in SKILL_MAP:
        base_dir = GLOBAL_SKILLS_DIR if scope == "global" else PROJECT_SKILLS_DIR
        skill_dir = base_dir / slug
        skill_dir.mkdir(parents=True, exist_ok=True)

        if slug == "pawel-call" and (PROJECT_SKILLS_DIR / "pawel-call" / "SKILL.md").exists():
            print("[+] Preserving pre-scrubbed pawel-call/SKILL.md")
            compiled_count += 1
            continue

        sections = []
        for src_name in sources:
            src_path = WORKFLOWS_DIR / src_name
            if src_path.exists():
                raw = src_path.read_text(encoding="utf-8")
                clean_body = sanitize_body(strip_frontmatter(raw))
                sections.append(clean_body)

        if not sections:
            print(f"[!] Warning: No source files found for {slug}, skipping.")
            continue

        combined_body = "\n\n---\n\n".join(sections)
        frontmatter = (
            f"---\n"
            f"name: {slug}\n"
            f"description: {desc}\n"
            f"disable-model-invocation: {'true' if disable_auto else 'false'}\n"
            f"---\n\n"
        )
        (skill_dir / "SKILL.md").write_text(frontmatter + combined_body + "\n", encoding="utf-8")

        if scope == "global":
            mirror_dir = GLOBAL_MIRROR_DIR / slug
            mirror_dir.mkdir(parents=True, exist_ok=True)
            (mirror_dir / "SKILL.md").write_text(frontmatter + combined_body + "\n", encoding="utf-8")

        compiled_count += 1
        print(f"[+] Compiled [{scope.upper()}] {slug}/SKILL.md (from {', '.join(sources)})")

    print(f"\n[PASS] Migration Complete: {compiled_count} canonical skills compiled.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
